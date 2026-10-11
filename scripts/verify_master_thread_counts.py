"""Check every supported native thread count against identical serial arrays."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from seed_search.backend import Backend,configure_native_threads,native_runtime


def run():
    if not native_runtime()['openmp']:raise RuntimeError('OpenMP build required for this verification')
    points=np.array([[x,z] for z in range(-129,129,8) for x in range(-133,131,8)],np.int32)
    rows=[];reference={}
    try:
        for threads in range(1,37):
            configure_native_threads(threads)
            for seed in (-1,9,4294979641):
                start=time.perf_counter()
                with Backend(seed) as b:
                    arrays=[b.land(points),*b.heights(points,8),*b.grid(-133,-129,33,33,8).values()]
                digest=hashlib.sha256()
                for a in arrays:digest.update(a.tobytes())
                value=digest.hexdigest()
                if threads==1:reference[seed]=value
                assert reference[seed]==value,(threads,seed)
                rows.append({'threads':threads,'seed':str(seed),'all_arrays_sha256':value,'seconds':time.perf_counter()-start})
            print(json.dumps({'verified_native_threads':threads}),flush=True)
    finally:configure_native_threads(1)
    out=Path(__file__).resolve().parents[1]/'runs/master-implementation-2026-10-10/all-native-thread-counts.json'
    out.write_text(json.dumps({'status':'PASS','native_thread_counts':list(range(1,37)),'rows':rows,
          'scope':'All three production OpenMP outer loops above their parallel batch threshold; three cold seeds per count; timings are correctness diagnostics, not throughput selection'},indent=2)+'\n')


if __name__=='__main__':run()
