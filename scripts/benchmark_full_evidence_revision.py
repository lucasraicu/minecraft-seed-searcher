"""Counterbalanced production CLI comparison against a retained source control."""
import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--native',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--count',type=int,default=30000)
    a=p.parse_args()
    if a.output.exists() or not 1<=a.count<=100000:p.error('Fresh output; count 1–100000 required')
    control_count=min(a.count,5000)
    if shutil.disk_usage(ROOT).free<(6*a.count+6*control_count)*65536+(16<<30):raise RuntimeError('Insufficient disk reserve')
    a.output.mkdir(parents=True);rows=[];fingerprints={};origins={}
    for name,source in [('before',a.before.resolve()),('after',ROOT)]:
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(source/'src'),str(source))))
        actual=subprocess.check_output([sys.executable,'-c','import seed_search.realm.native_encoding as m; print(m.__file__)'],cwd=source,env=env,text=True).strip()
        assert Path(actual).resolve()==source/'src/seed_search/realm/native_encoding.py',(name,actual)
        origins[name]=actual
    for phase,count,arms in [('revision',a.count,['before','after']),('python',control_count,['after','python'])]:
        for trial in range(3):
            for arm in arms[trial%2:]+arms[:trial%2]:
                tag=f'{phase}-{arm}-{trial}';receipt=a.output/f'{tag}.json'
                cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--source',str(a.before.resolve() if arm=='before' else ROOT),
                     '--entrypoint','--arm','python' if arm=='python' else 'native',
                     '--native',str(a.native.resolve()),'--policy-config',str(a.config.resolve()),
                     '--run',str((a.output/tag).resolve()),'--receipt',str(receipt.resolve()),
                     '--count',str(count),'--key','120290003000','--threads','16','--batch','4096','--workers','36']
                result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                (a.output/f'{tag}.log').write_text(result.stdout+result.stderr);result.check_returncode()
                row=json.loads(receipt.read_text())
                if phase in fingerprints:assert row['fingerprint']==fingerprints[phase],(phase,arm,'durable parity')
                else:fingerprints[phase]=row['fingerprint']
                rows.append({'phase':phase,'control':arm,'trial':trial,**row})
                payload={'source_origins':origins,'rows':rows}
                (a.output/'results.json').write_text(json.dumps(payload,indent=2)+'\n')
                print(phase,arm,trial,row['input_seeds_per_second'],flush=True)
    print({f'{phase}-{arm}':statistics.median(r['input_seeds_per_second'] for r in rows if r['phase']==phase and r['control']==arm)
           for phase,arms in [('revision',['before','after']),('python',['after','python'])] for arm in arms})


if __name__=='__main__':main()
