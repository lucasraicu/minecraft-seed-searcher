"""Counterbalanced cache and indexed-ranking comparison using bounded fresh runs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import blueprint_config
from seed_search.realm.store import RealmStore,canonical
from seed_search.realm.leaderboard import TIER,MISSES,SCORE,ORDER
from seed_search.seeds import seed_from_index


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cached',required=True,type=Path);p.add_argument('--uncached',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--count',type=int,default=50000)
    p.add_argument('--trials',type=int,default=3);args=p.parse_args()
    if not 1<=args.count<=100000 or not 2<=args.trials<=5:p.error('Count 1–100,000 and trials 2–5 required')
    if args.output.exists():p.error('Fresh output required')
    projected=2*args.trials*(args.count+min(10000,args.count))*65536
    free=shutil.disk_usage(ROOT).free
    if free<projected+(16<<30):raise RuntimeError('Disk preflight exceeds reserve')
    args.output.mkdir(parents=True)
    builds={'uncached':args.uncached.resolve(),'cached':args.cached.resolve()}
    prototypes={arm:Prototype(path,blueprint_config()) for arm,path in builds.items()}
    key=120266001000;observations=[];expected={};ranking=[]
    for phase,count in [('native_only',min(10000,args.count)),('compact_cli',args.count),('full_cli',min(10000,args.count))]:
        for trial in range(args.trials):
            for arm in (('uncached','cached') if trial%2==0 else ('cached','uncached')):
                tag=f'{phase}-{arm}-{trial}';receipt=args.output/f'{tag}.json'
                if phase=='native_only':
                    wall=0.;digests=[]
                    for first in range(0,count,4096):
                        seeds=[seed_from_index(i,key) for i in range(first,min(count,first+4096))]
                        with prototypes[arm].sweep(seeds,32,retention='survivors',max_misses=2) as batch:
                            wall+=batch.native_seconds;digests.append(batch.retention_receipt())
                    fingerprint=hashlib.sha256(canonical(digests).encode()).hexdigest()
                    row={'wall_seconds':wall,'input_seeds_per_second':count/wall,'fingerprint':fingerprint}
                    receipt.write_text(json.dumps(row,indent=2)+'\n')
                else:
                    cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--entrypoint','--arm','native-near' if phase=='compact_cli' else 'native',
                         '--native',str(builds[arm]),'--run',str((args.output/tag).resolve()),'--receipt',str(receipt.resolve()),
                         '--count',str(count),'--key',str(key),'--threads','32' if phase=='compact_cli' else '16']
                    child=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                    (args.output/f'{tag}.log').write_text(child.stdout+child.stderr);child.check_returncode()
                    row=json.loads(receipt.read_text());fingerprint=row['fingerprint']
                if phase in expected:assert fingerprint==expected[phase],(phase,arm,'semantic/task parity')
                else:expected[phase]=fingerprint
                observation={**row,'phase':phase,'comparison_arm':arm,'trial':trial,'count':count,'key':key}
                observations.append(observation)
                print(json.dumps({k:observation[k] for k in ('phase','comparison_arm','trial','input_seeds_per_second')}),flush=True)
    run=args.output/'full_cli-cached-0'
    with RealmStore(run,resume=True) as store:
        indexed=f'SELECT id,smart_score FROM candidate_leaderboard_view ORDER BY {ORDER} LIMIT 20'
        reference=f'SELECT id,{SCORE} FROM candidates NOT INDEXED ORDER BY ({TIER}),({MISSES}),({SCORE}) DESC,id LIMIT 20'
        plan=[r[3] for r in store.db.execute('EXPLAIN QUERY PLAN '+indexed)]
        assert not any('TEMP B-TREE' in r for r in plan)
        for trial in range(10):
            values={}
            for arm,sql in ([('reference',reference),('indexed',indexed)] if trial%2==0 else [('indexed',indexed),('reference',reference)]):
                start=time.perf_counter();rows=store.db.execute(sql).fetchall();elapsed=time.perf_counter()-start
                values[arm]=rows;ranking.append({'arm':arm,'trial':trial,'seconds':elapsed,'rows':rows})
            assert values['reference']==values['indexed']
        candidates=store.db.execute('SELECT count(*) FROM candidates').fetchone()[0]
    rates={phase:{arm:statistics.median(r['input_seeds_per_second'] for r in observations if r['phase']==phase and r['comparison_arm']==arm) for arm in builds} for phase,_ in [('native_only',0),('compact_cli',0),('full_cli',0)]}
    sql_medians={arm:statistics.median(r['seconds'] for r in ranking if r['arm']==arm) for arm in ('reference','indexed')}
    result={'scope':'Native-only separated from complete actual CLI/FULL persistence; same retention and evidence within paired arms',
            'distinct_inputs':args.count,'nested_subcohorts_are_not_extra_distinct_inputs':True,'key':key,
            'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30},
            'builds':{arm:prototype.identity for arm,prototype in prototypes.items()},'observations':observations,
            'median_rates':rates,'speedups':{phase:v['cached']/v['uncached'] for phase,v in rates.items()},'semantic_differences':0,
            'leaderboard':{'candidate_rows':candidates,'limit':20,'plan':plan,'trials':ranking,'median_seconds':sql_medians,'speedup':sql_medians['reference']/sql_medians['indexed'],'row_differences':0}}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'rates':rates,'speedups':result['speedups'],'ranking_seconds':sql_medians}),flush=True)


if __name__=='__main__':main()
