"""Observe the unchanged pipeline before proposing optimizations."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse
import collections
import time
import numpy as np
import seed_search.search as search
from seed_search.backend import Backend
from seed_search.config import load_config
from seed_search.preflight import save_json


class ObservedBackend(Backend):
    def __init__(self,seed):
        super().__init__(seed)
        self.seen=collections.defaultdict(set)
        self.stats=collections.defaultdict(lambda: {'calls':0,'points':0,'repeated_points':0,'native_seconds':0.0})
        global observer
        observer=self

    def observe(self,name,points,call):
        points=np.asarray(points)
        # Vectorized keys; coordinate domain is signed int32.
        keys=(points[:,0].astype(np.int64)<<32)|(points[:,1].astype(np.int64)&0xffffffff)
        values=keys.tolist();seen=self.seen[name];st=self.stats[name]
        st['calls']+=1;st['points']+=len(points)
        st['repeated_points']+=sum(v in seen for v in values)
        seen.update(values)
        t=time.perf_counter();r=call();st['native_seconds']+=time.perf_counter()-t
        return r

    def heights(self,p,vertical_step=8):
        return self.observe(f'height_stride_{vertical_step}',p,lambda:super(ObservedBackend,self).heights(p,vertical_step))

    def land(self,p):
        return self.observe('exact_land',p,lambda:super(ObservedBackend,self).land(p))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,default=12853964)
    parser.add_argument('--output',default='runs/landscape-expansion/baseline-12853964.json')
    args=parser.parse_args();cfg,h=load_config();search.Backend=ObservedBackend
    r=search.analyze_seed((0,args.seed,cfg))
    audit={'seed':str(args.seed),'config_sha256':h,'pipeline_unchanged':True,
           'operations':dict(observer.stats),'stage_seconds':r['stage_seconds'],
           'total_seconds_with_audit_overhead':r['total_seconds'],
           'cross_operation_exact_land_and_stride1_overlap':len(observer.seen['exact_land']&observer.seen['height_stride_1']),
           'counts':r['counts'],'result':r}
    save_json(args.output,audit)
    print({k:v for k,v in audit.items() if k!='result'},flush=True)
