# Approved runtime guard implementation
User approved NEXT_FIX_PLAN.md after completed audit and neutral High reviewc24d96ebc15c. Codex owns native files and integration; worker owns ONLY backend.py, realm/native_identity.py, tests/test_native_runtime_guard.py.
Actual failure: importing scripts.predictor_storage_probe (sys.path.insert(0,ROOT/src)) before backend can select stale primary extension. Direct Backend constructed native handles without preflight. Explicit native_runtime currently validates sources. Primary extensions intentionally stale and MUST NOT rebuild or replace.
Design: direct Backend must validate before ss_create. Cache successful validation for immutable loaded runtime per process, NOT disk hashing per seed; failed validations never cache. native_runtime explicit job/session preflight revalidates and invalidates stale cache on failure. PID/fork and different loaded ffi/lib must not share validation. Document source-change boundary and wheel behavior (no editable source expected, valid embedded hex digest still required). Do not pretend cached validation detects future disk changes automatically. Preserve native_runtime existing returned contract. No native operations before fail. Keep tests using fakes/subprocess source imports so stale primary lib does not block test isolation. Reproduce storage-helper-first import order using a new interpreter/fake _native plus actual backend sources, then validate good runtime after helper import. No per-seed fulltree scans. Acceptance check may use absolute repo .venv interpreter but executes from isolated snapshot cwd. Use provided run-command N wrappers exactly, not raw terminal commands. No dependencies copied/installed. No delegates, network, BDS, builds, notifications, primary writes. Final response concise with test evidence and contract limits.

## Current native_identity.py
```python
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

```
## Current backend preamble/Backend constructor
```python
from __future__ import annotations

import threading
import time
from functools import wraps
from collections import OrderedDict
import numpy as np
from .seeds import parse_seed, MASK64
from ._native import ffi, lib

STRUCTURES = ("trial_chamber", "stronghold", "mineshaft", "ancient_city", "village",
              "ruined_portal", "shipwreck", "monument", "outpost", "fortress", "bastion",
              "desert_pyramid", "jungle_temple", "swamp_hut", "igloo", "ocean_ruin", "mansion",
              "buried_treasure", "trail_ruins", "abandoned_camp", "ruined_portal_nether", "end_city")
# Serializes wrapper access in a Python process; multiprocessing remains parallel.
_LOCK = threading.RLock()
# These pinned-version families use a uint32_t MT placement seed. Stronghold's
# village path, Mineshaft and Trial Chamber are deliberately excluded.
RAW_MT_TYPES=frozenset(('village','ancient_city','ruined_portal','shipwreck','monument','outpost','fortress','bastion'))
_RAW_LAYOUTS=OrderedDict()
_NATIVE_THREADS=1

def native_runtime():
    from .realm.native_identity import validate_compiled_sources
    validate_compiled_sources(ffi,lib)
    import hashlib
    from pathlib import Path
    ptr=lib.ss_openmp_library()
    path=Path(ffi.string(ptr).decode()) if ptr!=ffi.NULL else None
    return {'openmp':bool(lib.ss_openmp_enabled()),
            'runtime_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path else None,
            'policy':'outer-columns-static-min256-v1'}

def configure_native_threads(threads=1):
    """Set defaults for new handles; numerical-library thread limits stay separate."""
    global _NATIVE_THREADS
    if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=36:
        raise ValueError('Native threads must be 1–36')
    with _LOCK:
        if threads>1 and not lib.ss_openmp_enabled():
            raise ValueError('Native threading requires an explicitly built OpenMP runtime')
        _NATIVE_THREADS=threads


def measure(operation,points=None):
    """Inclusive API timing; counters describe executed work, not eligibility."""
    def decorate(fn):
        @wraps(fn)
        def wrapped(self,*args,**kwargs):
            t=time.perf_counter()
            try:return fn(self,*args,**kwargs)
            finally:
                row=self.native_work.setdefault(operation,{'calls':0,'points':0,'seconds':0.})
                row['calls']+=1;row['seconds']+=time.perf_counter()-t
                if points is not None:
                    try:row['points']+=points(args,kwargs)
                    except (IndexError,TypeError,ValueError):pass
        return wrapped
    return decorate

def _int(value: int) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool):
        raise ValueError("Coordinates and sizes must be integers")
    value = int(value)
    if not -(1 << 30) <= value < (1 << 30):
        raise ValueError("Coordinate outside safe prototype range")
    return value

def _buffer(array, ctype):
    return ffi.from_buffer(ctype, array)

def biome_name(biome: int) -> str:
    ptr = lib.ss_biome_name(int(biome))
    return ffi.string(ptr).decode() if ptr != ffi.NULL else f"unknown_{biome}"


def biome_catalog():
    """Distinguish version-active IDs from legacy names and internal End classes."""
    result=[]
    for value in range(256):
        dimension=ffi.new('int[1]');generates=ffi.new('int[1]')
        exists=lib.ss_biome_catalog(value,dimension,generates)
        name=biome_name(value)
        if exists or not name.startswith('unknown_'):
            result.append({'id':value,'name':name,'version_active':bool(exists),
                           'generates':bool(generates[0]),'dimension':int(dimension[0]),
                           'provenance':'pinned predictor ID; not an actual Bedrock string mapping'})
    return result

def structure_type(name: str) -> int:
    if name not in STRUCTURES:
        raise ValueError(f"Unsupported structure: {name}")
    return int(lib.ss_structure_type(name.encode()))

def sweep_raw(start,count,families,threads=1,mode="reference"):
    modes={"reference":0,"presence":1,"capped":2,"complete":3}
    if mode not in modes:raise ValueError("Unknown raw count mode")
    """Bounded generator-free raw placement counts; never full64 eligibility."""
    if (isinstance(start,bool) or not isinstance(start,int) or not 0<=start<=2**32 or
        isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=65536 or start+count>2**32):
        raise ValueError('Raw range must fit lower32 and contain at most 65536 inputs')
    if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=36:
        raise ValueError('Invalid raw native thread count')
    if not 1<=len(families)<=8 or any(name not in RAW_MT_TYPES for name,bounds in families):
        raise ValueError('Raw sweep supports 1–8 reviewed MT families')
    types=np.array([structure_type(name) for name,bounds in families],np.int32)
    bounds=np.array([[ _int(v) for v in b] for name,b in families],np.int32)
    if bounds.shape!=(len(families),4):raise ValueError('Raw bounds need four inclusive coordinates')
    out=np.empty((count,len(families)),np.int32)
    with _LOCK:
        status=lib.ss_sweep_raw_mode(start,count,_buffer(types,'int[]'),_buffer(bounds,'int[]'),len(families),threads,
                                _buffer(out,'int[]'),out.size,modes[mode])
    if status!=0:raise ValueError('Raw sweep invalid runtime, regions or output capacity')
    return out

class Backend:
    def __init__(self, seed: str | int, raw_cache_entries: int = 0):
        self.native_work={}
        self.seed = parse_seed(seed)
        if isinstance(raw_cache_entries,bool) or not isinstance(raw_cache_entries,int) or not 0<=raw_cache_entries<=256:
            raise ValueError('Raw layout cache must contain 0–256 entries')
        self.raw_cache_entries=raw_cache_entries
        with _LOCK:
            ptr = lib.ss_create(self.seed & MASK64)
            if ptr != ffi.NULL and _NATIVE_THREADS>1:
                if lib.ss_set_threads(ptr,_NATIVE_THREADS)!=0:
                    lib.ss_destroy(ptr)
                    raise ValueError('Native thread configuration unavailable')
        if ptr == ffi.NULL:
            raise MemoryError("Could not allocate generator")
        self._ctx = ffi.gc(ptr, lib.ss_destroy)


```
