"""Bounded same-policy filter-order comparison with durable compact CLI timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import yaml

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from seed_search.realm.config import outpost_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.store import canonical
from seed_search.seeds import seed_from_index

ORDERS={
 'mansion_first':['mansion','outpost','desert_pyramid','jungle_temple','ancient_city','village','ruined_portal','trial_chamber','mineshaft'],
 'portal_outpost':['ruined_portal','outpost','mansion','desert_pyramid','jungle_temple','ancient_city','village','trial_chamber','mineshaft'],
 'prior_plus_outpost':['ruined_portal','trial_chamber','mansion','outpost','desert_pyramid','jungle_temple','ancient_city','village','mineshaft'],
}
EXTRA_ORDERS={
 'portal_outpost':ORDERS['portal_outpost'],
 'pyramid_before_mansion':['ruined_portal','outpost','desert_pyramid','jungle_temple','mansion','ancient_city','village','trial_chamber','mineshaft'],
 'temple_before_mansion':['ruined_portal','outpost','jungle_temple','desert_pyramid','mansion','ancient_city','village','trial_chamber','mineshaft'],
}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--count',type=int,default=50000);p.add_argument('--trials',type=int,default=3)
    p.add_argument('--key',type=int,default=120267003000)
    p.add_argument('--explore',action='store_true',help='Compare profiled cheap rare filters before Mansion')
    a=p.parse_args()
    if a.output.exists() or not 1<=a.count<=100000 or not 3<=a.trials<=5:p.error('Fresh path; count 1–100000, trials 3–5')
    free=shutil.disk_usage(ROOT).free;projected=3*a.trials*a.count*65536
    if free<projected+(16<<30):raise RuntimeError('Insufficient disk reserve')
    a.output.mkdir(parents=True);prototypes={};rows=[];fingerprints={};key=a.key
    orders=EXTRA_ORDERS if a.explore else ORDERS
    for arm,order in orders.items():
        cfg=outpost_blueprint_config();cfg['search']['structure_order']=order
        (a.output/f'{arm}.yaml').write_text(yaml.safe_dump(cfg))
        prototypes[arm]=Prototype(a.native,cfg)
    for phase in ('native_only','compact_cli'):
        for trial in range(a.trials):
            arms=list(orders);arms=arms[trial%3:]+arms[:trial%3]
            for arm in arms:
                tag=f'{phase}-{arm}-{trial}';receipt=a.output/f'{tag}.json'
                if phase=='native_only':
                    seconds=0.;receipts=[]
                    for start in range(0,a.count,4096):
                        seeds=[seed_from_index(i,key) for i in range(start,min(a.count,start+4096))]
                        with prototypes[arm].sweep(seeds,32,retention='survivors',max_misses=1) as b:
                            seconds+=b.native_seconds;receipts.append(b.retention_receipt())
                    row={'wall_seconds':seconds,'input_seeds_per_second':a.count/seconds,
                         'fingerprint':hashlib.sha256(canonical(receipts).encode()).hexdigest()}
                    receipt.write_text(json.dumps(row,indent=2)+'\n')
                else:
                    cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--entrypoint','--arm','native-near',
                         '--policy-config',str((a.output/f'{arm}.yaml').resolve()),'--max-misses','1',
                         '--native',str(a.native.resolve()),'--run',str((a.output/tag).resolve()),'--receipt',str(receipt.resolve()),
                         '--count',str(a.count),'--key',str(key),'--threads','32']
                    child=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                    (a.output/f'{tag}.log').write_text(child.stdout+child.stderr);child.check_returncode()
                    row=json.loads(receipt.read_text())
                # Complete decision receipts are order independent. Retained
                # records may report pending reasons in policy order, so their
                # durable fingerprints are compared across repetitions per arm.
                comparison=phase if phase=='native_only' else (phase,arm)
                if comparison in fingerprints:assert row['fingerprint']==fingerprints[comparison]
                else:fingerprints[comparison]=row['fingerprint']
                rows.append({**row,'phase':phase,'order':arm,'trial':trial,'count':a.count,'key':key})
                (a.output/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
                print(json.dumps({k:rows[-1][k] for k in ('phase','order','trial','input_seeds_per_second')}),flush=True)
    medians={phase:{arm:statistics.median(r['input_seeds_per_second'] for r in rows if r['phase']==phase and r['order']==arm)
                    for arm in orders} for phase in ('native_only','compact_cli')}
    result={'scope':'Same outpost-v3 policy; C-only and FULL durable compact baseline; no terrain/BDS',
            'orders':orders,'observations':rows,'median_rates':medians,'distinct_inputs':a.count,'key':key,
            'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30}}
    (a.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
