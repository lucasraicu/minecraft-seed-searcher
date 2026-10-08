"""Same-workload uncached/cached comparisons; excludes report generation."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
import json
import time
import seed_search.search as search
from seed_search.backend import Backend
from seed_search.cache import CachedBackend
from seed_search.config import load_config
from seed_search.preflight import save_json

if __name__=='__main__':
    cfg,_=load_config('runs/sweep-readiness/config/sweep.yaml')
    cfg['search']['maximum_refined_centers_per_seed']=3
    rows=[];ignored={'stage_seconds','total_seconds','worker_pid','worker_peak_rss_mb'}
    for seed,order in [(12853964,[Backend,CachedBackend]),(0,[CachedBackend,Backend])]:
        result={}
        for kind in order:
            search.Backend=kind;t=time.perf_counter();r=search.analyze_seed((0,seed,cfg));elapsed=time.perf_counter()-t
            result[kind.__name__]={'elapsed_seconds':elapsed,'prediction':{k:v for k,v in r.items() if k not in ignored}}
            print(seed,kind.__name__,elapsed,flush=True)
        a=result['Backend'];b=result['CachedBackend']
        rows.append({'seed':str(seed),'uncached_seconds':a['elapsed_seconds'],'cached_seconds':b['elapsed_seconds'],
                     'exact_prediction_equal':a['prediction']==b['prediction'],
                     'centers':len(a['prediction']['candidates'])})
    save_json('runs/landscape-expansion/cache-ab.json',{'scope':'Two unchanged legacy workloads, 32 preliminary/3 refined budget, one process, alternating order, no reports',
              'rows':rows,'all_predictions_equal':all(r['exact_prediction_equal'] for r in rows),
              'summed_uncached_seconds':sum(r['uncached_seconds'] for r in rows),'summed_cached_seconds':sum(r['cached_seconds'] for r in rows)})
