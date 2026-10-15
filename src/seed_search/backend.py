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

    def close(self):
        with _LOCK:
            if self._ctx is not None:
                ffi.release(self._ctx)
                self._ctx = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _handle(self):
        if self._ctx is None:
            raise RuntimeError("Backend is closed")
        return self._ctx

    def biome(self, x: int, y: int, z: int, dimension: int = 0) -> int:
        if dimension not in (0, -1, 1):
            raise ValueError("Supported dimensions are Overworld, Nether and End")
        with _LOCK:
            return int(lib.ss_biome(self._handle(), dimension, _int(x), _int(y), _int(z)))

    @measure('grid',lambda a,k:int(a[2])*int(a[3]))
    def grid(self, x0: int, z0: int, nx: int, nz: int, step: int = 64, y: int = 63):
        x0,z0,nx,nz,step,y = map(_int,(x0,z0,nx,nz,step,y))
        if nx < 1 or nz < 1 or step < 1 or nx*nz > 100_000:
            raise ValueError("Grid must contain 1–100,000 points with positive spacing")
        _int(x0+(nx-1)*step); _int(z0+(nz-1)*step)
        biomes=np.empty((nz,nx),dtype=np.int32)
        climate=np.empty((nz,nx,6),dtype=np.float64)
        approx=np.empty((nz,nx),dtype=np.float64)
        with _LOCK:
            code=lib.ss_grid(self._handle(),x0,z0,nx,nz,step,y,
                             _buffer(biomes,"int[]"),_buffer(climate,"double[]"),_buffer(approx,"double[]"))
        if code:
            raise RuntimeError(f"Native grid error {code}")
        return {"biomes":biomes,"climate":climate,"approx_height":approx}

    @measure('biome_points',lambda a,k:len(a[0]))
    def biome_points(self, xyz, dimension=0):
        points=np.asarray(xyz)
        if dimension not in (0,-1,1) or points.ndim!=2 or points.shape[1]!=3 or len(points)>100000 or not np.issubdtype(points.dtype,np.integer):
            raise ValueError('Expected up to 100,000 integer X/Y/Z points in a supported dimension')
        if np.any(points<-(1<<30)) or np.any(points>=(1<<30)):raise ValueError('Point outside safe range')
        points=np.ascontiguousarray(points,dtype=np.int32);out=np.empty(len(points),dtype=np.int32)
        with _LOCK:
            code=lib.ss_biome_points(self._handle(),dimension,_buffer(points,'int[]'),len(points),_buffer(out,'int[]'))
        if code:raise RuntimeError(f'Native biome error {code}')
        return out

    @measure('heights',lambda a,k:len(a[0]))
    def heights(self, xz, vertical_step: int = 8):
        points=np.asarray(xz)
        if points.ndim != 2 or points.shape[1] != 2 or len(points)>100_000:
            raise ValueError("Expected up to 100,000 X/Z coordinate pairs")
        if not np.issubdtype(points.dtype,np.integer):
            raise ValueError("Point coordinates must be integers")
        if np.any(points < -(1<<30)) or np.any(points >= (1<<30)):
            raise ValueError("Point outside safe prototype range")
        points=np.ascontiguousarray(points,dtype=np.int32)
        if not isinstance(vertical_step,int) or not 1<=vertical_step<=16:
            raise ValueError("Vertical step must be an integer in 1–16")
        heights=np.empty(len(points),dtype=np.int32)
        biomes=np.empty(len(points),dtype=np.int32)
        with _LOCK:
            code=lib.ss_heights(self._handle(),_buffer(points,"int[]"),len(points),vertical_step,
                               _buffer(heights,"int[]"),_buffer(biomes,"int[]"))
        if code:
            raise RuntimeError(f"Native height error {code}")
        return heights,biomes

    @measure('raw_land',lambda a,k:len(a[0]))
    def land(self, xz):
        points=np.asarray(xz)
        if points.ndim!=2 or points.shape[1]!=2 or len(points)>100_000 or not np.issubdtype(points.dtype,np.integer):
            raise ValueError('Expected up to 100,000 integer X/Z pairs')
        if np.any(points<-(1<<30)) or np.any(points>=(1<<30)):raise ValueError('Point outside safe range')
        points=np.ascontiguousarray(points,dtype=np.int32);out=np.empty(len(points),dtype=np.int32)
        with _LOCK:
            code=lib.ss_land(self._handle(),_buffer(points,'int[]'),len(points),_buffer(out,'int[]'))
        if code:raise RuntimeError(f'Native land classification error {code}')
        return out.astype(bool)

    @measure('placement_and_viability')
    def structures(self, name: str, bounds: tuple[int,int,int,int], viable: bool = True):
        typ=structure_type(name)
        x0,z0,x1,z1=map(_int,bounds)
        if x0>x1 or z0>z1 or x1-x0>14_000 or z1-z0>14_000:
            raise ValueError("Invalid or oversized prototype structure bounds")
        cap=((x1-x0)//16+3)*((z1-z0)//16+3)+20
        out=np.empty((cap,2),dtype=np.int32)
        with _LOCK:
            n=lib.ss_scan(self._handle(),typ,x0,z0,x1,z1,int(viable),_buffer(out,"int[]"),cap)
        if n<0:
            raise RuntimeError(f"Native structure scan error {n} for {name}")
        return sorted({(int(x),int(z)) for x,z in out[:n]})

    def attempt(self,name: str,rx: int,rz: int):
        out=ffi.new("int[2]")
        with _LOCK:
            result=lib.ss_attempt(self._handle(),structure_type(name),_int(rx),_int(rz),out)
        if result<0:
            raise ValueError("This type requires its special scan adapter")
        return (int(out[0]),int(out[1])) if result else None

    @measure('mineshaft_first')
    def mineshaft_first(self,bounds):
        self._handle()
        x0,z0,x1,z1=map(_int,bounds)
        if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:
            raise ValueError('Invalid or oversized Mineshaft bounds')
        out=ffi.new('int[2]')
        with _LOCK:
            code=lib.ss_mineshaft_first(self._handle(),x0,z0,x1,z1,out)
        if code<0:raise RuntimeError(f'Native Mineshaft existence error {code}')
        return (int(out[0]),int(out[1])) if code else None

    @measure('nether_pair')
    def nether_structure_pairs(self,bounds):
        self._handle()
        x0,z0,x1,z1=map(_int,bounds)
        if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:
            raise ValueError('Invalid or oversized Nether bounds')
        cap=((x1-x0)//16+3)*((z1-z0)//16+3)+20
        pts=np.empty((cap,3),np.int32);flags=np.empty(cap,np.int32)
        with _LOCK:
            n=lib.ss_nether_pair(self._handle(),x0,z0,x1,z1,_buffer(pts,'int[]'),_buffer(flags,'int[]'),cap)
        if n<0:raise RuntimeError(f'Native Nether pair error {n}')
        result={name:([],[]) for name in ('fortress','bastion')}
        for (x,z,fortress),ok in zip(pts[:n],flags[:n]):
            raw,viable=result['fortress' if fortress else 'bastion']
            point=(int(x),int(z));raw.append(point)
            if ok:viable.append(point)
        return result

    @measure('structure_first')
    def structure_first(self,name,bounds):
        self._handle();typ=structure_type(name)
        x0,z0,x1,z1=map(_int,bounds)
        if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:
            raise ValueError('Invalid or oversized structure bounds')
        if name=='stronghold':raise ValueError('Stronghold discovery must enumerate its anchors')
        out=ffi.new('int[2]')
        with _LOCK:
            code=lib.ss_structure_first(self._handle(),typ,x0,z0,x1,z1,out)
        if code<0:raise RuntimeError(f'Native structure witness error {code}')
        return (int(out[0]),int(out[1])) if code else None

    @measure('structure_count_floor')
    def structure_count(self, name, bounds, minimum):
        """Return up to minimum distinct viable predictor witnesses, not a census."""
        self._handle()
        typ=structure_type(name)
        if name=='stronghold':raise ValueError('Stronghold discovery must enumerate its anchors')
        if isinstance(minimum,bool) or not isinstance(minimum,int) or not 1<=minimum<=64:
            raise ValueError('Structure count floor must be an integer in 1–64')
        x0,z0,x1,z1=map(_int,bounds)
        if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:
            raise ValueError('Invalid or oversized structure bounds')
        out=np.empty((minimum,2),dtype=np.int32)
        with _LOCK:
            n=lib.ss_structure_count(self._handle(),typ,x0,z0,x1,z1,_buffer(out,'int[]'),minimum)
        if n<0:raise RuntimeError(f'Native structure count error {n}')
        return sorted({(int(x),int(z)) for x,z in out[:n]})

    @measure('combined_structure_scan')
    def structure_pair(self,name,bounds):
        """One placement scan, then full-seed viability. Cache ONLY raw MT layouts."""
        # Validate before a cache hit, including a closed handle and bounds.
        self._handle();typ=structure_type(name);bounds=tuple(map(_int,bounds))
        x0,z0,x1,z1=bounds
        if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:
            raise ValueError('Invalid or oversized prototype structure bounds')
        key=(name,self.seed & 0xffffffff,bounds) if name in RAW_MT_TYPES and self.raw_cache_entries else None
        with _LOCK:
            raw=_RAW_LAYOUTS.pop(key,None) if key is not None else None
            if raw is None:
                raw=tuple(self.structures(name,bounds,False))
            if key is not None:
                _RAW_LAYOUTS[key]=raw
                while len(_RAW_LAYOUTS)>self.raw_cache_entries:_RAW_LAYOUTS.popitem(last=False)
            if not raw:return [],[]
            pts=np.ascontiguousarray(raw,dtype=np.int32)
            flags=np.empty(len(raw),dtype=np.int32)
            code=lib.ss_filter_starts(self._handle(),typ,_buffer(pts,'int[]'),len(raw),_buffer(flags,'int[]'))
            if code:raise RuntimeError(f'Native start filter error {code}')
            return list(raw),[p for p,ok in zip(raw,flags) if ok]

    def igloo_basement(self,x,z):
        with _LOCK:
            value=lib.ss_igloo_basement(self._handle(),_int(x),_int(z))
        if value<0:raise RuntimeError('Igloo variant prediction is unavailable')
        return bool(value)

    def bastion_variant(self,x,z):
        with _LOCK:
            value=lib.ss_bastion_variant(self._handle(),_int(x),_int(z))
        if value<0:raise RuntimeError('Bastion variant prediction is unavailable')
        return int(value)


def model_metadata():
    return {"model": ffi.string(lib.ss_model_name()).decode(),
            "structure_rng": {name: int(lib.ss_structure_rng(structure_type(name))) for name in STRUCTURES}}

def capabilities():
    return {'edition':'bedrock','target_version':'26.52','model':'MC_26_50',
            'mapping_status':'bounded_matching_version_Chunkbase_comparison',
            'dimensions':['overworld','nether','end'],'structures':list(STRUCTURES),
            'biome_inventory':biome_catalog(),
            'terrain':'raw density estimate, no caves/aquifers/decoration/chunk interpolation',
            'woodland':'surface biome proxy, no tree counts',
            'unsupported':['actual structure footprints','portal arrival','spawn','trees','End terrain and actual Bedrock End biome mapping','monster_room bounded adapter'],
            'lower_bit_optimization':'bounded_lower32_staged_eight_raw_families',
            'quart_land_reuse':'pinned_raw_density_quart_xz_v1'}

def raw_layout(low32,name,bounds):
    if isinstance(low32,bool) or not isinstance(low32,int) or not 0<=low32<2**32:
        raise ValueError('low32 must be an unsigned 32-bit integer')
    if name not in RAW_MT_TYPES:raise ValueError('Raw layout adapter accepts only the eight verified MT families')
    x0,z0,x1,z1=map(_int,bounds)
    if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:raise ValueError('Invalid or oversized structure bounds')
    cap=((x1-x0)//16+3)*((z1-z0)//16+3)+20;out=np.empty((cap,2),np.int32)
    with _LOCK:
        n=lib.ss_raw_layout(low32,structure_type(name),x0,z0,x1,z1,_buffer(out,'int[]'),cap)
    if n<0:raise RuntimeError(f'Native raw layout error {n}')
    return sorted({(int(x),int(z)) for x,z in out[:n]})

def structure_diagnostic(backend, name, x, z):
    out=ffi.new('int[10]')
    with _LOCK:
        ok=lib.ss_diagnostic(backend._handle(),structure_type(name),_int(x),_int(z),out)
    if not ok: raise ValueError('Diagnostic supports Bastion and Ancient City only')
    return {'quart_sample':[int(out[i]) for i in range(3)],'sample_biome':biome_name(out[3]),
            'rotation':int(out[4]),'variant':int(out[5]),'piece_offset':[int(out[6]),int(out[7])],
            'piece_size':[int(out[8]),int(out[9])],'start_biome':biome_name(backend.biome(x,-27 if name=='ancient_city' else 33,z,0 if name=='ancient_city' else -1))}
