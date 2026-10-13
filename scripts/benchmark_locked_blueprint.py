"""Bounded, counterbalanced CLI comparisons for the versioned locked blueprint."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from seed_search.realm.config import blueprint_config,locked_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.store import canonical
from seed_search.seeds import seed_from_index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--count',type=int,default=50000)
    parser.add_argument('--trials',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.count<=100000 or not 2<=args.trials<=5:parser.error('Bounded count 1–100,000; trials 2–5')
    if args.output.exists():parser.error('A fresh evidence directory is required')
    full_count=min(10000,args.count)
    projected=args.trials*(2*full_count+3*args.count)*65536
    free=shutil.disk_usage(ROOT).free
    if free<projected+(16<<30):raise RuntimeError('Insufficient disk reserve')
    args.output.mkdir(parents=True)
    key=120267001000
    prototypes={'historical_two_miss':Prototype(args.native,blueprint_config()),
                'locked_one_miss':Prototype(args.native,locked_blueprint_config()),
                'locked_two_miss':Prototype(args.native,locked_blueprint_config())}
    observations=[];fingerprints={}
    for phase in ('native_only','compact_cli','full_cli'):
        arms=list(prototypes) if phase!='full_cli' else ['locked_native_full','locked_python_full']
        count=args.count if phase!='full_cli' else full_count
        for trial in range(args.trials):
            for arm in arms[trial%len(arms):]+arms[:trial%len(arms)]:
                tag=f'{phase}-{arm}-{trial}';receipt=args.output/f'{tag}.json'
                if phase=='native_only':
                    proto=prototypes[arm];elapsed=0.;receipts=[]
                    for start in range(0,count,4096):
                        seeds=[seed_from_index(i,key) for i in range(start,min(count,start+4096))]
                        with proto.sweep(seeds,32,retention='survivors',max_misses=1 if arm=='locked_one_miss' else 2) as batch:
                            elapsed+=batch.native_seconds;receipts.append(batch.retention_receipt())
                    row={'wall_seconds':elapsed,'input_seeds_per_second':count/elapsed,
                         'fingerprint':hashlib.sha256(canonical(receipts).encode()).hexdigest(),
                         'retained_inputs':sum(r['retained_inputs'] for r in receipts)}
                    receipt.write_text(json.dumps(row,indent=2)+'\n')
                else:
                    cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--entrypoint','--arm',
                         'python' if arm=='locked_python_full' else 'native' if phase=='full_cli' else 'native-near',
                         '--native',str(args.native.resolve()),'--run',str((args.output/tag).resolve()),
                         '--receipt',str(receipt.resolve()),'--count',str(count),'--key',str(key),'--workers','36',
                         '--threads','16' if phase=='full_cli' else '32']
                    if arm.startswith('locked'):cmd+=['--locked']
                    if phase=='compact_cli':cmd+=['--max-misses','1' if arm=='locked_one_miss' else '2']
                    child=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                    (args.output/f'{tag}.log').write_text(child.stdout+child.stderr);child.check_returncode()
                    row=json.loads(receipt.read_text())
                parity_key=(phase,'same_locked_full_policy' if phase=='full_cli' else arm)
                if parity_key in fingerprints:assert row['fingerprint']==fingerprints[parity_key],(phase,arm,'semantic or durable task parity')
                else:fingerprints[parity_key]=row['fingerprint']
                observation={**row,'phase':phase,'comparison_arm':arm,'trial':trial,'count':count,'key':key}
                observations.append(observation)
                print(json.dumps({k:observation[k] for k in ('phase','comparison_arm','trial','input_seeds_per_second')}),flush=True)
    medians={phase:{arm:statistics.median(r['input_seeds_per_second'] for r in observations if r['phase']==phase and r['comparison_arm']==arm)
                    for arm in dict.fromkeys(r['comparison_arm'] for r in observations if r['phase']==phase)}
             for phase in dict.fromkeys(r['phase'] for r in observations)}
    result={'scope':'Separate policy change from equal-policy native/Python full persistence. Native-only excludes SQL; compact includes atomic FULL range receipts.',
            'distinct_inputs':args.count,'contained_full_cohort_is_not_extra_distinct_volume':True,'key':key,
            'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30},
            'observations':observations,'median_rates':medians,'semantic_differences':0,
            'locked_full_native_speedup':medians['full_cli']['locked_native_full']/medians['full_cli']['locked_python_full']}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'median_rates':medians,'locked_full_native_speedup':result['locked_full_native_speedup']}))


if __name__=='__main__':main()
