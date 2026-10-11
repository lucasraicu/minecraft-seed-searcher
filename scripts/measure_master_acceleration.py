"""Equal-workload native threading and whole-terrain acceptance measurements."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[key]='1'
import argparse
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from multiprocessing import get_context
import hashlib
import json
from pathlib import Path
import statistics
import time
import numpy as np
from seed_search.backend import Backend,configure_native_threads
from seed_search.realm.runner import process_tree_resources

OUT=Path(__file__).resolve().parents[1]/'runs/master-implementation-2026-10-10'


def query(job):
    index,threads=job;configure_native_threads(threads)
    seed=(-1,12345,4294979641)[index%3]
    points=np.array([[x,z] for z in range(-512,512,16) for x in range(-512,512,16)],np.int32)
    start=time.perf_counter();cpu=time.process_time();digest=hashlib.sha256()
    with Backend(seed) as backend:
        arrays=[backend.land(points),*backend.heights(points,8),*backend.grid(-512,-512,32,32,32).values()]
        for array in arrays:digest.update(array.tobytes())
    return {'index':index,'sha256':digest.hexdigest(),'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu}


def thread_trials(full_capacity=False):
    profiles=((36,1),(18,2),(12,3),(9,4),(6,6),(4,9),(3,12),(2,18),(1,36),(30,1),(16,2),(6,3),(4,4)) if full_capacity else ((30,1),(18,1),(12,1),(6,2),(6,3),(4,4),(8,2),(12,2),(14,2),(16,2))
    jobs=36 if full_capacity else 30
    rows=[];reference=None
    for trial in range(3):
        for workers,threads in profiles if trial%2==0 else reversed(profiles):
            start=time.perf_counter();rss=0;cpu=0.;results=[]
            with ProcessPoolExecutor(max_workers=workers,mp_context=get_context('spawn')) as pool:
                pending={pool.submit(query,(index,threads)) for index in range(jobs)}
                while pending:
                    ready,pending=wait(pending,timeout=.5,return_when=FIRST_COMPLETED)
                    results.extend(f.result() for f in ready)
                    sample=process_tree_resources()
                    if not sample['available']:raise RuntimeError('Trial resource monitor unavailable')
                    rss=max(rss,sample['rss_bytes']);cpu=max(cpu,sample['cpu_percent'])
            elapsed=time.perf_counter()-start
            digests=[r['sha256'] for r in sorted(results,key=lambda r:r['index'])]
            if reference is None:reference=digests
            assert reference==digests,'Process/native threading changed arrays'
            row={'trial':trial,'processes':workers,'native_threads':threads,'seconds':elapsed,
                 'worker_cpu_seconds':sum(r['cpu_seconds'] for r in results),'peak_process_tree_rss_bytes':rss,
                 'combined_with_8gib_reservation_bytes':rss+(8<<30),'peak_sampled_cpu_percent':cpu}
            rows.append(row);print(json.dumps(row),flush=True)
    summary=[]
    for p,t in profiles:
        samples=[r['seconds'] for r in rows if r['processes']==p and r['native_threads']==t]
        summary.append({'processes':p,'native_threads':t,'median_seconds':statistics.median(samples),'min_seconds':min(samples),'max_seconds':max(samples)})
    result={'rows':rows,'summary':summary,'arrays_equal':True,
            'scope':f'{jobs} fixed column workloads, spawn included, three alternating trials; no concurrent BDS; reservation is budget accounting, not a mixed-load certificate'}
    (OUT/('full-capacity-thread-trials.json' if full_capacity else 'thread-trials.json')).write_text(json.dumps(result,indent=2)+'\n')


def terrain_trials(full_capacity=False):
    from verify_master_native import module
    from seed_search import _native
    import seed_search.backend as wrapper
    from seed_search.realm.cli import load
    from seed_search.realm.store import RealmStore
    from seed_search.realm.terrain import run_terrain
    import seed_search.realm.terrain as terrain
    import sqlite3
    source=OUT.parent/'realm-implementation-2026-10-10/worker-scaling-10000/workers-30/realm.sqlite'
    with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as db:
        raw=db.execute("SELECT result FROM candidates WHERE qualification='PREDICTED' ORDER BY id LIMIT 1").fetchone()[0]
    candidate=json.loads(raw)
    record=json.loads((OUT/'reference-probe.json').read_text());reference=module(record['path'],record['module'])
    original=(wrapper.ffi,wrapper.lib);rows=[];golden=None
    original_proposals=terrain.propose_centers
    terrain.propose_centers=lambda *a,**k:original_proposals(*a,**k)[:1]
    try:
        for trial in range(3):
            profiles=(('openmp4',_native,4,'rotation'),('openmp18',_native,18,'rotation'),('openmp36',_native,36,'rotation')) if full_capacity else (('reference',reference,1,'rotation'),('optimized',_native,1,'rotation'),('openmp4',_native,4,'rotation'),('priority4',_native,4,'priority'))
            for name,native,threads,scheduler in profiles if trial%2==0 else reversed(profiles):
                wrapper.ffi,wrapper.lib=native.ffi,native.lib
                configure_native_threads(threads)
                cfg=load();cfg['search']['native_threads_per_worker']=threads;cfg['terrain'].update(scheduler=scheduler,maximum_refinements_per_anchor=1,resolutions=[128,64,32,16])
                out=OUT/f'terrain-{"capacity" if full_capacity else "bounded"}-{name}-{trial}'
                with RealmStore(out,{'config':cfg,'imported_candidate_sha256':hashlib.sha256(raw.encode()).hexdigest()}) as store:
                    store.configure_range(0,1,1);store.claim_range('import');store.complete_range(0,1,[{'index':0,'seed':candidate['seed'],'anchors':[candidate]}])
                    providers=[]
                    def factory(seed):
                        value=Backend(seed);providers.append(value);return value
                    start=time.perf_counter();cpu=time.process_time()
                    summary=run_terrain(store,cfg,('v1','v2'),provider_factory=factory,provider_identity={'provider':'matched-native-reference','query':'raw-density','source':'prediction'})
                    elapsed=time.perf_counter()-start;cpu=time.process_time()-cpu
                    variants=list(store.iter_variants())
                    # Schedule/provider reuse counters are operational metadata.
                    semantics=[]
                    for row in variants:
                        result={k:v for k,v in row['result'].items() if k not in ('provider','sampling_schedule')}
                        semantics.append({**row,'result':result})
                    if golden is None:golden=semantics
                    assert golden==semantics,'Whole-terrain semantic output changed'
                    row={'variant':name,'trial':trial,'seconds':elapsed,'cpu_seconds':cpu,'summary':summary,'native_work':[p.native_work for p in providers]}
                    rows.append(row);print(json.dumps({k:row[k] for k in ('variant','trial','seconds','cpu_seconds')}),flush=True)
    finally:
        wrapper.ffi,wrapper.lib=original;configure_native_threads(1)
        terrain.propose_centers=original_proposals
    summaries={name:{'median_seconds':statistics.median(r['seconds'] for r in rows if r['variant']==name),
                     'samples':[r['seconds'] for r in rows if r['variant']==name]} for name in dict.fromkeys(r['variant'] for r in rows)}
    (OUT/('terrain-capacity-trials.json' if full_capacity else 'terrain-trials.json')).write_text(json.dumps({'rows':rows,'summary':summaries,'semantic_outputs_equal':True,
          'scope':'One fixed saved anchor, both variants, first proposed center per variant, identical bounded resolutions/refinement count; imported historical baseline is timing input only'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('threads','terrain'))
    parser.add_argument('--full-capacity',action='store_true')
    args=parser.parse_args()
    if args.command=='threads':thread_trials(args.full_capacity)
    else:terrain_trials(args.full_capacity)
