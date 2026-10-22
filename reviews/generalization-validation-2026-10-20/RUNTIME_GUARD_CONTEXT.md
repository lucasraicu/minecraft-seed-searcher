# Actual runtime-guard evidence

Source snippets for neutral plan critique; no implementation authorized.

```python
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


```

Storage helper import-side effect, before any native_backend import:
```python
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
```
