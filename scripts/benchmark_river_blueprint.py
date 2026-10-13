"""Bounded actual-CLI river revision benchmark and preceding locked-policy control."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from seed_search.realm.config import locked_blueprint_config,river_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.store import canonical
from seed_search.seeds import seed_from_index


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--count',type=int,default=50000);p.add_argument('--trials',type=int,default=3)
    args=p.parse_args()
    if not 1<=args.count<=100000 or not 2<=args.trials<=5:p.error('Bounded count 1–100000 and 2–5 trials')
    if args.output.exists():p.error('Fresh directory required')
    full_count=min(5000,args.count);projected=args.trials*(2*args.count+2*full_count)*65536
    free=shutil.disk_usage(ROOT).free
    if free<projected+(16<<30):raise RuntimeError('Insufficient disk reserve')
    args.output.mkdir(parents=True);key=120267001000;observations=[];fingerprints={}
    prototypes={'locked_one_miss':Prototype(args.native,locked_blueprint_config()),'river_one_miss':Prototype(args.native,river_blueprint_config())}
    for phase in ('native_only','compact_cli','full_cli'):
        arms=list(prototypes) if phase!='full_cli' else ['river_native_full','river_python_full']
        count=args.count if phase!='full_cli' else full_count
        for trial in range(args.trials):
            for arm in arms[trial%len(arms):]+arms[:trial%len(arms)]:
                tag=f'{phase}-{arm}-{trial}';receipt=args.output/f'{tag}.json'
                if phase=='native_only':
                    elapsed=0.;receipts=[]
                    for start in range(0,count,4096):
                        seeds=[seed_from_index(i,key) for i in range(start,min(count,start+4096))]
                        with prototypes[arm].sweep(seeds,32,retention='survivors',max_misses=1) as batch:
                            elapsed+=batch.native_seconds;receipts.append(batch.retention_receipt())
                    row={'wall_seconds':elapsed,'input_seeds_per_second':count/elapsed,
                         'fingerprint':hashlib.sha256(canonical(receipts).encode()).hexdigest(),
                         'retained_inputs':sum(r['retained_inputs'] for r in receipts)}
                    receipt.write_text(json.dumps(row,indent=2)+'\n')
                else:
                    cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--entrypoint','--arm',
                         'python' if arm=='river_python_full' else 'native' if phase=='full_cli' else 'native-near',
                         '--native',str(args.native.resolve()),'--run',str((args.output/tag).resolve()),'--receipt',str(receipt.resolve()),
                         '--count',str(count),'--key',str(key),'--workers','36','--threads','16' if phase=='full_cli' else '32',
                         '--river' if arm.startswith('river') else '--locked']
                    if phase=='compact_cli':cmd+=['--max-misses','1']
                    child=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                    (args.output/f'{tag}.log').write_text(child.stdout+child.stderr);child.check_returncode();row=json.loads(receipt.read_text())
                parity_key=(phase,'same_river_full_policy' if phase=='full_cli' else arm)
                if parity_key in fingerprints:assert row['fingerprint']==fingerprints[parity_key],(phase,arm,'semantic/durable task parity')
                else:fingerprints[parity_key]=row['fingerprint']
                observations.append({**row,'phase':phase,'comparison_arm':arm,'trial':trial,'count':count,'key':key})
                print(json.dumps({k:observations[-1][k] for k in ('phase','comparison_arm','trial','input_seeds_per_second')}),flush=True)
    medians={phase:{arm:statistics.median(o['input_seeds_per_second'] for o in observations if o['phase']==phase and o['comparison_arm']==arm)
                for arm in dict.fromkeys(o['comparison_arm'] for o in observations if o['phase']==phase)}
             for phase in dict.fromkeys(o['phase'] for o in observations)}
    result={'scope':'Native C only versus atomic FULL compact CLI; same-policy full-evidence native/Python. Terrain and BDS excluded.',
            'distinct_inputs':args.count,'contained_full_cohort_is_not_extra_distinct_volume':True,'key':key,
            'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30},
            'observations':observations,'median_rates':medians,'semantic_differences':0,
            'river_full_native_speedup':medians['full_cli']['river_native_full']/medians['full_cli']['river_python_full']}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
