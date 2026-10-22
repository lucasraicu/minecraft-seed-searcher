#!/usr/bin/env python3
"""Bounded optimized-center validation using saved fixed-cohort observations only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,verify_no_symlinks
from seed_search.catalog.realm_evaluation import evaluate_large_realms
from seed_search.catalog.registry import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--split',choices=('all','held_out'),default='all')
    args=parser.parse_args()
    if not 10<=args.seconds<=600:raise ValueError('Explicit allowance10..600seconds')
    root=verify_no_symlinks(args.input.absolute())
    progress=strict_json_loads((root/'progress.json').read_bytes())
    calibration=strict_json_loads(args.calibration.read_bytes())
    if not progress.get('complete') or progress['cohort_id']!=calibration['cohort_id']:
        raise ValueError('Require complete matching fixed cohort')
    store=ArtifactStore(root/'objects');cid=digest(calibration)
    source_sha=hashlib.sha256(Path(sys.modules[evaluate_large_realms.__module__].__file__).read_bytes()).hexdigest()
    cohort=[r for r in progress['worlds'] if args.split=='all' or r['split']==args.split]
    if args.output.exists() and not args.resume:raise ValueError('Existing output requires explicit --resume')
    state=strict_json_loads(args.output.read_bytes()) if args.output.exists() else dict(
        revision='catalog-calibration-optimized-validation-v1',calibration_id=cid,
        cohort_id=progress['cohort_id'],evaluator_sha256=source_sha,split=args.split,worlds=[],allocations=[])
    if state['calibration_id']!=cid or state.get('evaluator_sha256')!=source_sha or state.get('split')!=args.split:raise ValueError('Frozen thresholds changed')
    started=time.monotonic();deadline=started+args.seconds;stop=threading.Event()
    resource.setrlimit(resource.RLIMIT_CPU,(args.seconds+5,args.seconds+10));os.nice(10)
    def watchdog():
        while not stop.wait(.2):
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            if rss>4<<30 or time.monotonic()>deadline+2:os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    state['allocations'].append(dict(seconds=args.seconds,started_utc=time.time(),explicit_resume=args.resume))
    atomic_json(args.output,state)
    try:
        for row in cohort[len(state['worlds']):]:
            if time.monotonic()>=deadline-5:break
            obs=store.get_json(row['artifact'])
            if digest(obs)!=row['observation_id']:raise ValueError('Saved facts changed')
            result=evaluate_large_realms(obs,calibration,seconds=5,max_centers=1024)
            state['worlds'].append(dict(world_id=row['world_id'],seed=row['seed'],split=row['split'],
                observation_id=row['observation_id'],evaluation=result))
            atomic_json(args.output,state)
            if len(state['worlds'])%10==0:
                print(json.dumps(dict(completed=len(state['worlds']),elapsed=round(time.monotonic()-started,2))),flush=True)
        state.update(complete=len(state['worlds'])==len(cohort),last_elapsed_seconds=time.monotonic()-started)
        state['summary']={split:{str(side):dict(n=sum(r['split']==split for r in state['worlds']),
            qualifying=sum(r['split']==split and r['evaluation']['sizes'][str(side)]['status']=='match' for r in state['worlds']),
            budget_limited=sum(r['split']==split and r['evaluation']['sizes'][str(side)]['search_budget_exhausted'] for r in state['worlds']))
            for side in (4096,8192)} for split in ('development','held_out')}
        atomic_json(args.output,state)
        print(json.dumps(dict(completed=len(state['worlds']),complete=state['complete'],summary=state['summary'])),flush=True)
    finally:stop.set()


if __name__=='__main__':main()
