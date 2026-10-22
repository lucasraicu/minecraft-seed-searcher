High neutral focused code review, approved/runtimeguard implemented by Codex. Review ONLYcodebelow for concrete supported-use correctnessbugs. Contract: an immutable process/job accepts cachedruntime; native_runtime() explicitly revalidates defaultforceTrue beforeNEWjob, does not continuouslymonitor future sourceedits. Cached_backend/_handle/raw_layout/sweep_raw/biome_catalog callensure_runtime_validated first; close stillpossibleafterfailure. No nativehandle usebeforeguard. Strongcache refsavoidIDreuse, atforkreset avoidsdeadlock. Tests13pass: actualhelperfirstsubprocess,fakebad/good,multiworkerconcurrencyfailedfreshpreflight,1000handlesonehash,forkwhileparentlockheld,missing/malformedidentity/wheel,oldhandleblockedafterpreflightfailure. RealO3runtime validates andrestoresvillage afterutilityhelperimport. No importpathoverridefromstoragehelper now; CLIfallback appendedonly__main__. Previouslargerreview65abc6114967 timedout; no result/claims. Don't re-evaluate projectplan or suggestcontinuouswatching asperthiscontract. No tools/readers/commands/network/edits/agents. <=450words final RUNTIME_GUARD_REVIEW; eitherconcreteblockingbug withtrace or noidentifiedblocker andlimits.

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

