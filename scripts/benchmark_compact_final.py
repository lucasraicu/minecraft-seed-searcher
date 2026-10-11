"""Counterbalanced reference/eligibility pilots and bounded thread schedules."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path('runs/compact-implementation-2026-10-10')

def invoke(name,**options):
 root=ROOT/name
 command=[sys.executable,'scripts/benchmark_compact_implementation.py','--output',str(root)]
 for key,value in options.items():command += ['--'+key.replace('_','-'),str(value)]
 with (ROOT/'final-pilots.log').open('a') as log:
  result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:raise SystemExit(result.returncode)
 print(name,flush=True)
 return json.loads((root/'benchmark.json').read_text())

def main():
 for cohort,start in [('tuning',0),('holdout',100000)]:
  records={'reference':[],'eligibility':[]}
  for trial in range(3):
   for arm in (('reference','eligibility') if trial%2==0 else ('eligibility','reference')):
    options=dict(start=start,trials=1,mode='complete' if arm=='reference' else 'eligibility')
    if arm=='reference':options['package']=str((ROOT/'reference/src').resolve())
    name=f'final-{arm}-border-{cohort}/rep-{trial}'
    r=invoke(name,**options)[0];r.update(trial=trial,path=str(ROOT/name/'trial-0'));records[arm].append(r)
  for arm,rows in records.items():(ROOT/f'final-{arm}-border-{cohort}'/'benchmark.json').write_text(json.dumps(rows,indent=2)+'\n')
  invoke(f'final-eligibility-world-{cohort}',start=start,mode='eligibility',lattice='world',refinement=128)
 invoke('final-complete-border',mode='complete')
 for workers,threads in [(9,4),(2,18)]:
  invoke(f'final-schedule-{workers}x{threads}',mode='eligibility',lattice='world',refinement=128,workers=workers,threads=threads)

if __name__=='__main__':main()
