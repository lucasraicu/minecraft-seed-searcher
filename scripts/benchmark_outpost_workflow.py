"""Fresh full-evidence native/Python control and adopted compact CLI comparison."""
import argparse
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import yaml

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from seed_search.realm.config import outpost_blueprint_config,river_blueprint_config


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--count',type=int,default=50000);p.add_argument('--trials',type=int,default=3)
    p.add_argument('--key',type=int,default=120270003000)
    a=p.parse_args()
    if a.output.exists() or not 1<=a.count<=100000 or not 3<=a.trials<=5:p.error('Fresh output; count 1–100000; trials 3–5')
    full=min(5000,a.count);free=shutil.disk_usage(ROOT).free;projected=a.trials*(2*a.count+2*full)*65536
    if free<projected+(16<<30):raise RuntimeError('Insufficient disk reserve')
    a.output.mkdir(parents=True);rows=[];expected={};key=a.key
    for arm,cfg in (('outpost',outpost_blueprint_config()),('river',river_blueprint_config())):
        (a.output/f'{arm}.yaml').write_text(yaml.safe_dump(cfg))
    for phase,arms,count in [('compact',['outpost','river'],a.count),('full',['native','python'],full)]:
        for trial in range(a.trials):
            for arm in arms[trial%2:]+arms[:trial%2]:
                tag=f'{phase}-{arm}-{trial}';receipt=a.output/f'{tag}.json'
                cfg='river' if phase=='compact' and arm=='river' else 'outpost'
                cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--entrypoint','--arm',
                     'native-near' if phase=='compact' else arm,'--policy-config',str((a.output/f'{cfg}.yaml').resolve()),
                     '--native',str(a.native.resolve()),'--run',str((a.output/tag).resolve()),'--receipt',str(receipt.resolve()),
                     '--count',str(count),'--key',str(key),'--threads','32' if phase=='compact' else '16','--workers','36']
                if phase=='compact':cmd+=['--max-misses','1']
                child=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                (a.output/f'{tag}.log').write_text(child.stdout+child.stderr);child.check_returncode()
                row=json.loads(receipt.read_text());comparison=(phase,cfg)
                if comparison in expected:assert row['fingerprint']==expected[comparison],(phase,arm,'record/task parity')
                else:expected[comparison]=row['fingerprint']
                rows.append({**row,'phase':phase,'comparison_arm':arm,'trial':trial})
                (a.output/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
                print(json.dumps({k:rows[-1][k] for k in ('phase','comparison_arm','trial','input_seeds_per_second')}),flush=True)
    summary={phase:{arm:statistics.median(r['input_seeds_per_second'] for r in rows if r['phase']==phase and r['comparison_arm']==arm)
                    for arm in dict.fromkeys(r['comparison_arm'] for r in rows if r['phase']==phase)} for phase in ('compact','full')}
    result={'observations':rows,'median_rates':summary,'distinct_inputs':a.count,'full_cohort_contained':True,'key':key,
            'full_semantic_differences':0,'scope':'FULL durable baseline CLI, terrain/BDS excluded; compact policy change is not isolated code speedup',
            'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30}}
    (a.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
