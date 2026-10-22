"""Shared900s/4GiB/3GiB resource ledger for profiling-owned processes only."""
from pathlib import Path
import json,os,subprocess,sys,time
import psutil
B=Path(__file__).parent;ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher');name=sys.argv[1];assert name in ['world-pair','storage','queries','readmodels','query-counters','fixed-replay']
ledger=B/'RESOURCES.json';state=json.loads(ledger.read_text()) if ledger.exists() else dict(phases=[],limits=dict(wall_seconds=900,rss_bytes=4<<30,output_bytes=3<<30));assert name not in [x['phase'] for x in state['phases']]
start=time.monotonic();charged=sum(x['wall_seconds'] for x in state['phases']);peak=0;failure=None;last=[]
script=B/('run_world_pair.py' if name=='world-pair' else 'run_fixed_replay.py' if name=='fixed-replay' else 'measure_query_counters.py' if name=='query-counters' else 'measure_'+name+'.py')
with (B/(name+'.log')).open('w') as log:
 proc=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(script)],cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),stdout=log,stderr=subprocess.STDOUT)
 parent=psutil.Process(proc.pid)
 try:
  while proc.poll() is None:
   try:
    last=parent.children(recursive=True);rss=sum(p.memory_info().rss for p in [parent,*last] if p.is_running());peak=max(peak,rss);size=sum(p.stat().st_size for p in B.rglob('*') if p.is_file())
    if charged+time.monotonic()-start>900 or rss>4<<30 or size>3<<30:failure='Cumulative wall/RSS/output limit';break
   except (psutil.Error,FileNotFoundError):pass
   time.sleep(.25)
 finally:
  if proc.poll() is None:
   for child in reversed(last):
    try:child.kill()
    except psutil.Error:pass
   proc.kill()
  code=proc.wait(timeout=5)
row=dict(phase=name,exit_status=code,failure=failure,wall_seconds=time.monotonic()-start,peak_owned_rss_bytes=peak,output_bytes=sum(p.stat().st_size for p in B.rglob('*') if p.is_file()));state['phases'].append(row);state['charged_seconds']=sum(x['wall_seconds'] for x in state['phases']);ledger.write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(row),flush=True)
if code or failure:raise SystemExit(1)
