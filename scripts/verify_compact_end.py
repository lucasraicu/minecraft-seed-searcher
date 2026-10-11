"""End point/batch differential against the pre-optimization correct adapter."""
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
from seed_search.backend import Backend,configure_native_threads
from seed_search.realm.sampling import grid_points

ROOT=Path('runs/compact-implementation-2026-10-10')

def main():
 spec=importlib.util.spec_from_file_location('saved_end._native',ROOT/'end-before.abi3.so')
 old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);rng=np.random.default_rng(103)
 sets=[grid_points((-2000,-2000,2000,2000),64,63,'world'),
       grid_points((-2000,-2000,2000,2000),128,63,'world'),
       rng.integers([-2200,-64,-2200],[2201,320,2201],size=(1024,3),dtype=np.int32),
       np.array([[x,63,z] for x in (-1041,-1025,-1024,-1023,-17,-1,0,1,15,16,17,1023,1024,1025) for z in (-1041,-1025,-17,-1,0,1,16,17,1025)],np.int32),
       np.array([[x,63,x] for x in range(-12000,12000,37)],np.int32)]
 records=[];checks=0
 for seed in (-1,0,12345,-2**63,7980124511283784280):
  ctx=old.lib.ss_create(seed&((1<<64)-1))
  for points in sets:
   expected=np.empty(len(points),np.int32);begin=time.perf_counter()
   assert old.lib.ss_biome_points(ctx,1,old.ffi.from_buffer('int[]',points),len(points),old.ffi.from_buffer('int[]',expected))==0
   reference=time.perf_counter()-begin
   for threads in (1,4,18):
    configure_native_threads(threads)
    with Backend(seed) as backend:
     begin=time.perf_counter();actual=backend.biome_points(points,1);elapsed=time.perf_counter()-begin
     assert np.array_equal(actual,expected)
     scalar=np.array([backend.biome(*map(int,p),1) for p in points])
     assert np.array_equal(scalar,expected);checks+=len(points)*2
    records.append({'seed':str(seed),'points':len(points),'threads':threads,'reference_seconds':reference,'current_seconds':elapsed})
  old.lib.ss_destroy(ctx)
 configure_native_threads(1)
 (ROOT/'end-parity.json').write_text(json.dumps({'checks':checks,'differences':0,'records':records,
    'scope':'Correct pre-optimization End predictor oracle; no actual Bedrock biome-name claim'},indent=2)+'\n')
 print(f'PASS: {checks} End scalar/batch comparisons',flush=True)

if __name__=='__main__':main()
