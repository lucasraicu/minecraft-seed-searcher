"""Measure the private complete native baseline and the complete persisted path.

Run sequentially without competing compilation/tests. All profiles use the same
three disjoint cohorts. Repetitions do not increase distinct input count.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import threading
import time

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS',
            'NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from scripts.blueprint_batch_prototype import Prototype, persist_scan, semantic_record
from scripts.benchmark_blueprint import summarize_results
from seed_search.realm.capabilities import identity as production_identity, report
from seed_search.realm.config import blueprint_config
from seed_search.realm.runner import run_scan, process_tree_resources
from seed_search.realm.store import RealmStore, canonical
from seed_search.seeds import seed_from_index

KEYS=(120260001000,120261001000,120262001000)


def write(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


class Monitor:
    def __init__(self):self.stop=threading.Event();self.peak=0
    def __enter__(self):
        def sample():
            while not self.stop.is_set():
                resources=process_tree_resources()
                if resources['available']:self.peak=max(self.peak,resources['rss_bytes'])
                self.stop.wait(.25)
        self.thread=threading.Thread(target=sample,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join()


def fingerprint(store):
    digest=hashlib.sha256();seeds=anchors=0
    for row in store.iter_results():
        digest.update(canonical(semantic_record(row)).encode());seeds+=1;anchors+=len(row['anchors'])
    return {'semantic_sha256':digest.hexdigest(),'seeds':seeds,'anchors':anchors}


def native(args,prototype):
    out={'scope':'Native C complete blueprint baseline batch calls, including context setup, generation, '
         'all discovered anchors and result-buffer allocation; excludes Python result reconstruction, '
         'IPC, persistence, terrain and BDS. Diagnostic extraction happens outside timed calls.',
         'count_per_cohort':args.count,'distinct_inputs':args.count*3,'keys':KEYS,
         'prototype_identity':prototype.identity,'production_identity':production_identity(),'profiles':[]}
    expected={}
    for threads in args.threads:
        profile={'threads':threads,'cohorts':[]}
        # Warm startup on a reused subset. Do not count it as new evidence.
        with prototype.sweep([seed_from_index(i,KEYS[0]) for i in range(64)],threads):pass
        for cohort,key in enumerate(KEYS):
            seeds=[seed_from_index(i,key) for i in range(args.count)];trials=[]
            for trial in range(args.trials):
                native_seconds=0.;digest=hashlib.sha256();counts=Counter();effective=set()
                with Monitor() as monitor:
                    for start in range(0,args.count,args.batch_size):
                        with prototype.sweep(seeds[start:start+args.batch_size],threads) as batch:
                            native_seconds+=batch.native_seconds;effective.add(batch.pointer.effective_threads)
                            summary=batch.summary();digest.update(canonical(summary).encode())
                            for row in summary:
                                counts['inputs']+=1;counts['anchors']+=len(row['anchors'])
                                counts['unresolved_discovery']+=int(not row['anchors'])
                                counts['qualified_seeds']+=int(any(a['qualification']=='PREDICTED' for a in row['anchors']))
                                for a in row['anchors']:
                                    counts['qualified_anchors']+=int(a['qualification']=='PREDICTED')
                                    counts['biome_entered']+=int(a['biome_evaluated'])
                row={'trial':trial,'native_seconds':native_seconds,'input_seeds_per_second':args.count/native_seconds,
                     'peak_process_tree_rss_bytes':monitor.peak,'effective_threads':sorted(effective),
                     'decision_sha256':digest.hexdigest(),'counts':dict(counts)}
                if cohort in expected:assert row['decision_sha256']==expected[cohort]
                else:expected[cohort]=row['decision_sha256']
                assert effective=={threads};trials.append(row)
                print(json.dumps({'phase':'native','threads':threads,'cohort':cohort,**row}),flush=True)
            profile['cohorts'].append({'cohort':cohort,'key':key,'trials':trials})
        profile['median_aggregate_input_seeds_per_second']=args.count*3/sum(statistics.median(t['native_seconds'] for t in c['trials']) for c in profile['cohorts'])
        out['profiles'].append(profile);write(args.output/'native-throughput.json',out)
    return out


def persisted(args,prototype):
    cfg=blueprint_config()
    out={'scope':'Fresh finite scans, same seeds and complete RealmStore evidence schema. Current Python '
         'uses 30 spawned processes, batch32; private native uses one Python parent, OpenMP and requested '
         'batch size. Includes full checkpoint lifecycle and record persistence; no terrain/BDS.',
         'distinct_inputs':args.count*3,'count_per_cohort':args.count,'keys':KEYS,
         'prototype_identity':prototype.identity,'production_identity':production_identity(),'cohorts':[]}
    for cohort,key in enumerate(KEYS):
        cfg['search']['run_key']=str(key);trials=[];expected=None
        for trial in range(args.trials):
            arms=('python','native') if trial%2==0 else ('native','python')
            for arm in arms:
                run=args.output/f'{arm}-c{cohort}-t{trial}'
                if run.exists():raise ValueError(f'Fresh benchmark path required: {run}')
                if arm=='python':
                    run.mkdir();write(run/'compatibility.json',report(cfg))
                    start=time.perf_counter()
                    with Monitor() as monitor:
                        status=run_scan(cfg,run,args.count,workers=30,identity={'config':cfg,'benchmark':'native-prototype-comparison','backend':production_identity(),'count':args.count},allow_prediction_scale=True)
                    seconds=time.perf_counter()-start
                    row={'wall_seconds':seconds,'input_seeds_per_second':args.count/seconds,'status':status,
                         'peak_process_tree_rss_bytes':monitor.peak}
                else:
                    with Monitor() as monitor:
                        row=persist_scan(prototype,run,args.count,run_key=key,threads=args.persist_threads,batch_size=args.persist_batch_size)
                    row['peak_process_tree_rss_bytes']=monitor.peak
                assert row['status']['completed_seeds']==args.count
                with RealmStore(run,resume=True) as store:
                    fp=fingerprint(store);summary=summarize_results(store.iter_results(),cfg)
                if expected is not None:assert fp==expected,(cohort,trial,arm,'full record parity')
                else:expected=fp
                row.update(trial=trial,arm=arm,fingerprint=fp,summary=summary,
                           sqlite_bytes=sum(p.stat().st_size for p in run.glob('realm.sqlite*')))
                trials.append(row);print(json.dumps({'phase':'persisted','cohort':cohort,'trial':trial,'arm':arm,
                    'seconds':row['wall_seconds'],'input_seeds_per_second':row['input_seeds_per_second'],
                    'semantic_sha256':fp['semantic_sha256']}),flush=True)
            write(args.output/'persisted-throughput.json',{**out,'cohorts':out['cohorts']+[{'cohort':cohort,'key':key,'trials':trials}]})
        out['cohorts'].append({'cohort':cohort,'key':key,'trials':trials})
    out['aggregate_input_seeds_per_second']={arm:args.count*3/sum(statistics.median(t['wall_seconds'] for t in c['trials'] if t['arm']==arm) for c in out['cohorts']) for arm in ('python','native')}
    out['native_vs_python_speedup']=out['aggregate_input_seeds_per_second']['native']/out['aggregate_input_seeds_per_second']['python']
    write(args.output/'persisted-throughput.json',out);return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['native','persisted']);p.add_argument('--native',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--count',type=int,default=10000)
    p.add_argument('--trials',type=int,default=3);p.add_argument('--threads',type=int,nargs='+',default=[1,18,36])
    p.add_argument('--batch-size',type=int,default=4096);p.add_argument('--persist-threads',type=int,default=18)
    p.add_argument('--persist-batch-size',type=int,default=256)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    prototype=Prototype(args.native,blueprint_config())
    result=native(args,prototype) if args.phase=='native' else persisted(args,prototype)
    print(json.dumps({'completed':args.phase,'distinct_inputs':result['distinct_inputs']}))


if __name__=='__main__':main()
