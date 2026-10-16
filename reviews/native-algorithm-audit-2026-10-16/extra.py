import sys,json,subprocess,random
from pathlib import Path
base=Path(__file__).resolve().parent
jobs=[(a,34,16384,32000000+r*131072,131072) for r in range(3) for a in ('baseline','stream','tight')];random.Random(21).shuffle(jobs)
with (base/'extra.jsonl').open('w') as f:
 for job in jobs:
  p=subprocess.run([sys.executable,str(base/'measure.py'),*map(str,job)],capture_output=True,text=True)
  row=json.loads(p.stdout.strip().splitlines()[-1]) if not p.returncode else dict(job=job,error=p.stderr)
  f.write(json.dumps(row)+'\n');f.flush();print(json.dumps(row),flush=True)
