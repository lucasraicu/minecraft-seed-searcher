"""Fail closed when a private native artifact predates this source checkout."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


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


def validate_compiled_sources(ffi, lib):
    expected=native_source_fingerprint()
    actual=ffi.string(lib.ss_source_fingerprint()).decode() if hasattr(lib,'ss_source_fingerprint') else ''
    if len(actual)!=64 or (expected is not None and actual!=expected):
        raise ValueError('Compiled native sources changed; rebuild the active engine')


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
