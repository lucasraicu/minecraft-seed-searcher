"""Counterbalanced full persisted adoption gates, including original source control."""
import argparse
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
KEYS=(120260001000,120261001000,120262001000)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--control',type=Path,required=True)
    p.add_argument('--count',type=int,default=10000);p.add_argument('--trials',type=int,default=3)
    p.add_argument('--heldout',action='store_true',help='Exactly one additional 100,000-input cohort, not three cohorts')
    p.add_argument('--threads',type=int,default=16);p.add_argument('--batch',type=int,default=4096)
    p.add_argument('--workers',type=int,default=30)
    p.add_argument('--arms',nargs='+',choices=['python-original','python30','python','native'],default=['python-original','python30','python','native'])
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if not 1<=args.count<=100000 or not 1<=args.trials<=3:p.error('Bounded count/trials required')
    count=100000 if args.heldout else args.count;keys=(120263001000,) if args.heldout else KEYS
    projected=count*len(keys)*args.trials*len(args.arms)*65536
    free=shutil.disk_usage(args.output).free;reserve=16<<30
    if free<projected+reserve:raise RuntimeError('Benchmark disk preflight exceeds free-space reserve')
    manifest={'scope':'Complete durable inputs; startup, queues, final drain and close included; diagnostic parity outside timer',
        'count_per_cohort':count,'distinct_inputs':count*len(keys),'keys':keys,'trials':args.trials,
        'arms':args.arms,'threads':args.threads,'batch':args.batch,'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':reserve},
        'semantic_exclusions':['stage_seconds','native_work','worker_cpu_seconds','total_seconds','worker_pid','worker_peak_rss_bytes','prototype'],'cohorts':[]}
    expected={}
    for cohort,key in enumerate(keys):
        entries=[]
        for trial in range(args.trials):
            arms=args.arms[trial%len(args.arms):]+args.arms[:trial%len(args.arms)]
            for arm in arms:
                tag=f'{arm}-c{cohort}-t{trial}';receipt=args.output/f'{tag}.json';run=args.output/tag
                cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--arm',arm,
                    '--source',str(args.control.resolve() if arm=='python-original' else ROOT),
                    '--native',str(args.native.resolve()),'--run',str(run.resolve()),'--receipt',str(receipt.resolve()),
                    '--count',str(count),'--key',str(key),'--threads',str(args.threads),'--batch',str(args.batch),'--workers',str(30 if arm in ('python-original','python30') else args.workers)]
                result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                (args.output/f'{tag}.log').write_text(result.stdout+result.stderr);result.check_returncode()
                row=json.loads(receipt.read_text());row['trial']=trial
                if cohort in expected:assert row['fingerprint']==expected[cohort],(tag,'complete evidence/task parity')
                else:expected[cohort]=row['fingerprint']
                entries.append(row);print(result.stdout.strip(),flush=True)
                partial={**manifest,'cohorts':manifest['cohorts']+[{'key':key,'cohort':cohort,'trials':entries}]}
                (args.output/'results.json').write_text(json.dumps(partial,indent=2)+'\n')
        manifest['cohorts'].append({'key':key,'cohort':cohort,'trials':entries})
    rates={arm:count*len(keys)/sum(statistics.median(r['wall_seconds'] for r in c['trials'] if r['arm']==arm) for c in manifest['cohorts']) for arm in args.arms}
    manifest['aggregate_input_seeds_per_second']=rates
    manifest['paired_cohort_speedups']=[statistics.median(r['wall_seconds'] for r in c['trials'] if r['arm']=='python')/statistics.median(r['wall_seconds'] for r in c['trials'] if r['arm']=='native') for c in manifest['cohorts']] if {'python','native'}<=set(args.arms) else []
    if manifest['paired_cohort_speedups']:manifest['performance_gate']=all(x>=1.2 for x in manifest['paired_cohort_speedups'])
    (args.output/'results.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(rates))


if __name__=='__main__':main()
