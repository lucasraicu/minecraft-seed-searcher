"""Validate native identity at load/job boundaries, without hashing per seed.

Backend construction caches successful validation for an immutable loaded runtime
in this process. Source edits during a session require explicit native_runtime()
preflight at the next job boundary; this cache cannot monitor later disk edits.
Wheels without C sources require a well-formed embedded build digest, rather than
claiming comparison with an unavailable checkout. No implicit rebuild occurs.
"""
import hashlib
import os
from pathlib import Path
import re
import threading

ROOT = Path(__file__).resolve().parents[3]
_VALIDATION_LOCK = threading.RLock()
# Strong references prevent id reuse from accepting a different ffi/lib pair.
_VALIDATED_RUNTIMES = {}


def _after_fork():
    global _VALIDATION_LOCK, _VALIDATED_RUNTIMES
    _VALIDATION_LOCK = threading.RLock()
    _VALIDATED_RUNTIMES = {}


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=_after_fork)


def native_source_fingerprint():
    """Location-independent fingerprint embedded in both compiled extensions."""
    import json
    paths = [*ROOT.glob('native/*.c'), *ROOT.glob('native/*.h'), *ROOT.glob('native/*.inc'),
             *ROOT.glob('vendor/cubiomes-bedrock/*.c'), *ROOT.glob('vendor/cubiomes-bedrock/*.h'),
             *ROOT.glob('vendor/cubiomes-bedrock/tables/*.h')]
    # A wheel has no editable C checkout; its extension is built with its sources.
    if not paths:return None
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()


def validate_compiled_sources(ffi, lib, *, force=True):
    """Fresh explicit preflight by default; invalidate even if validation raises.

    Holding one lock through validation prevents concurrent forced validation and
    cached constructors from racing. The hot path only checks process/object IDs.
    """
    key = (os.getpid(), id(ffi), id(lib))
    with _VALIDATION_LOCK:
        if not force and key in _VALIDATED_RUNTIMES:
            return
        _VALIDATED_RUNTIMES.pop(key, None)
        expected = native_source_fingerprint()
        try:
            ptr = lib.ss_source_fingerprint()
            actual = ffi.string(ptr).decode('ascii') if ptr != ffi.NULL else ''
        except (AttributeError, TypeError, UnicodeError):
            actual = ''
        if not re.fullmatch(r'[0-9a-fA-F]{64}', actual) or (expected is not None and actual != expected):
            raise ValueError('Compiled native sources changed; rebuild the active engine')
        _VALIDATED_RUNTIMES[key] = (ffi, lib)


def ensure_runtime_validated(ffi, lib):
    """Validate once per loaded runtime/process; failures are never cached."""
    validate_compiled_sources(ffi, lib, force=False)


def validate_native_sources(identity):
    inputs = identity.get('inputs')
    required = ('native/blueprint_batch.h', 'native/blueprint_batch.inc',
                'native/blueprint_dynamic.inc', 'vendor/cubiomes-bedrock/noise.c')
    if not isinstance(inputs, dict) or any(name not in inputs for name in required):
        raise ValueError('Native source manifest unavailable; rebuild the active engine')
    stale = []
    for name, digest in inputs.items():
        path = (ROOT / name).resolve()
        if (not path.is_relative_to(ROOT) or not path.is_file() or
                hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            stale.append(name)
    if stale:
        raise ValueError('Stale native source inputs; rebuild the active engine: ' + ', '.join(stale))


def compatible_native_build(directory):
    import json
    try:
        identity = json.loads((Path(directory) / 'identity.json').read_text())
        validate_native_sources(identity)
        extension = Path(identity['extension'])
        return (extension.resolve().is_relative_to(Path(directory).resolve()) and
                hashlib.sha256(extension.read_bytes()).hexdigest() == identity['extension_sha256'])
    except (ValueError, KeyError, OSError, TypeError):
        return False
