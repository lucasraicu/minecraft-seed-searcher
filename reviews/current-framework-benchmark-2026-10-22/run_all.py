"""One cumulative600s/4GiB/1GiB monitor; terminates only owned benchmark tree."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
import psutil
P=Path(__file__).parent;ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher');PY=ROOT/'.venv/bin/python'
start=time.monotonic();peak=0;cpu_peak=0;phases=[];failure=None
# Actual immutable files, not service-created lock/SQLite journal metadata.
live=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/treasure-activation-approved-20261022/catalog')
immutable={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['automation/objects','automation/snapshots','automation/generations'] for p in (live/folder).rglob('*') if p.is_file()}
immutable[str(live/'automation/current.json')]=hashlib.sha256((live/'automation/current.json').read_bytes()).hexdigest()
(P/'IMMUTABLE_PRE_HASHES.json').write_text(json.dumps(immutable)+'\n')
seeds=json.loads((P/'catalog-seeds.json').read_text())
commands=[['measure_personal.py'],['measure_catalog.py',str(P/'serial-worlds'),json.dumps(seeds),str(P/'catalog-results.json')],['measure_active.py']]
for args in commands:
 phase=time.monotonic();proc=None;last=[];phase_peak=0
 with (P/(args[0]+'.log')).open('w') as log:
  proc=subprocess.Popen([str(PY),str(P/args[0]),*args[1:]],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
  owned=psutil.Process(proc.pid)
  while proc.poll() is None:
   try:
    last=owned.children(recursive=True);rss=sum(p.memory_info().rss for p in [owned,*last] if p.is_running());peak=max(peak,rss);phase_peak=max(phase_peak,rss)
    size=sum(p.stat().st_size for p in P.rglob('*') if p.is_file())
    if rss>4<<30 or size>1<<30 or time.monotonic()-start>600:failure='Aggregate RSS/output/cumulative wall budget exceeded';break
   except (psutil.Error,FileNotFoundError):pass
   time.sleep(.1)
  if proc.poll() is None:
   for child in reversed(last):
    try:child.kill()
    except psutil.Error:pass
   proc.kill()
  code=proc.wait(timeout=5)
 phases.append(dict(script=args[0],exit_status=code,wall_seconds=time.monotonic()-phase,peak_owned_rss_bytes=phase_peak))
 (P/'RESOURCES.json').write_text(json.dumps(dict(phases=phases,failure=failure,cumulative_wall_seconds=time.monotonic()-start,peak_owned_rss_bytes=peak),indent=2)+'\n')
 print(json.dumps(phases[-1]),flush=True)
 if code or failure:raise SystemExit(1)
print('All phases complete',flush=True)
