"""Counterbalanced actual CLI rates for full evidence and explicit compact retention."""
import argparse,json,statistics,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--heldout',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
count=100000 if a.heldout else 10000;keys=[120263001000] if a.heldout else [120260001000,120261001000,120262001000]
arms=['python','native','native-strict','native-near'];projected=count*len(keys)*3*len(arms)*65536
free=shutil.disk_usage(a.output).free
if free<projected+(16<<30):raise RuntimeError('Benchmark disk budget exceeds reserve')
result={'scope':'Actual CLI process startup, baseline work, FULL SQLite commit, drain and close; no terrain/BDS',
        'count_per_cohort':count,'distinct_inputs':count*len(keys),'trials':3,'keys':keys,
        'threads':{'native':16,'native-strict':32,'native-near':32},
        'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30},'cohorts':[]}
expected={}
for c,key in enumerate(keys):
 cohort={'cohort':c,'key':key,'trials':[]};result['cohorts'].append(cohort)
 for trial in range(3):
  order=arms[trial%4:]+arms[:trial%4]
  for arm in order:
   tag=f'{arm}-c{c}-t{trial}';receipt=a.output/f'{tag}.json'
   cmd=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),'--entrypoint','--arm',arm,'--native',str(a.native.resolve()),'--run',str((a.output/tag).resolve()),'--receipt',str(receipt.resolve()),'--count',str(count),'--key',str(key),'--threads',str(16 if arm=='native' else 32),'--workers','36']
   r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);(a.output/f'{tag}.log').write_text(r.stdout+r.stderr);r.check_returncode()
   row=json.loads(receipt.read_text());row['trial']=trial;cohort['trials'].append(row)
   parity_key=(c,'full' if arm in ('python','native') else arm)
   if parity_key in expected:assert expected[parity_key]==row['fingerprint'],(tag,'semantic record/task parity')
   else:expected[parity_key]=row['fingerprint']
   print(r.stdout.strip(),flush=True);(a.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
result['aggregate_input_seeds_per_second']={arm:count*len(keys)/sum(statistics.median(r['wall_seconds'] for r in c['trials'] if r['arm']==arm) for c in result['cohorts']) for arm in arms}
result['paired_full_cohort_speedups']=[statistics.median(r['wall_seconds'] for r in c['trials'] if r['arm']=='python')/statistics.median(r['wall_seconds'] for r in c['trials'] if r['arm']=='native') for c in result['cohorts']]
result['full_performance_gate']=all(x>=1.2 for x in result['paired_full_cohort_speedups'])
(a.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['aggregate_input_seeds_per_second']),flush=True)
