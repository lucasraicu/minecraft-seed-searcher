"""Compare current SIMD arithmetic with pre-84a83ba scalar arithmetic only.

Both libraries use the same current generator/biome code. This checks numerical
preservation, not Bedrock agreement. See noise_*_build.log and wrapper sources.
"""
from pathlib import Path
import ctypes
import json
import random
import struct
import time

ROOT=Path(__file__).resolve().parent
libs=[]
for mode in ('scalar','simd'):
    lib=ctypes.CDLL(str(ROOT/f'noise_{mode}.dylib'), mode=ctypes.RTLD_LOCAL)
    lib.prepare.argtypes=[ctypes.c_ulonglong]
    lib.biome.argtypes=[ctypes.c_int]*3
    lib.biome.restype=ctypes.c_int
    lib.climate.argtypes=[ctypes.c_int,ctypes.c_double,ctypes.c_double,ctypes.c_double]
    lib.climate.restype=ctypes.c_double
    lib.dark_filter.argtypes=[ctypes.c_int,ctypes.c_int]
    lib.dark_filter.restype=ctypes.c_int
    libs.append(lib)
rng=random.Random(20261016)
result={'seed':20261016,'arithmetic_control':'pre-84a83ba noise.c, -ffp-contract=off; both use current other vendor files','biome_samples':0,'biome_mismatches':0,'dark_filter_samples':0,'dark_filter_mismatches':0,'raw_climate_samples':0,'raw_climate_bit_mismatches':0,'float32_climate_mismatches':0,'max_absolute_climate_delta':0.0,'first_raw_difference':None,'first_biome_difference':None}
t0=time.perf_counter()
for si in range(64):
    seed=rng.getrandbits(64)
    for lib in libs:lib.prepare(seed)
    for pi in range(2048):
        x,z=rng.randrange(-2000,2000),rng.randrange(-2000,2000)
        y=(63,-48,0,160)[pi%4]
        a,b=(lib.biome(x,y,z) for lib in libs)
        result['biome_samples']+=1
        result['biome_mismatches']+=a!=b
        if a!=b and result['first_biome_difference'] is None:
            result['first_biome_difference']={'seed':str(seed),'coordinate':[x,y,z],'scalar':a,'simd':b}
        fa,fb=(lib.dark_filter(x,z) for lib in libs)
        result['dark_filter_samples']+=1
        result['dark_filter_mismatches']+=fa!=fb
        if pi%8==0:
            for slot in range(6):
                ca,cb=(lib.climate(slot,x/4,0,z/4) for lib in libs)
                result['raw_climate_samples']+=1
                delta=abs(ca-cb)
                result['max_absolute_climate_delta']=max(result['max_absolute_climate_delta'],delta)
                result['raw_climate_bit_mismatches']+=struct.pack('d',ca)!=struct.pack('d',cb)
                result['float32_climate_mismatches']+=struct.pack('f',ca)!=struct.pack('f',cb)
                if ca!=cb and result['first_raw_difference'] is None:
                    result['first_raw_difference']={'seed':str(seed),'coordinate':[x/4,0,z/4],'slot':slot,'scalar':ca,'simd':cb,'absolute_delta':delta}
result['wall_seconds']=time.perf_counter()-t0
(ROOT/'noise_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
