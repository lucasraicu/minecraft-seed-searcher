"""Counterbalanced current existing-world record replay, bounded cumulative time."""
from pathlib import Path
import json,os,subprocess,sys,time,statistics,resource
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022'
seed=json.loads((B/'catalog-seeds.json').read_text())[0];previous=json.loads((E/'RECORD_REPLAY.json').read_text());(E/'RECORD_REPLAY_ATTEMPT1.json').write_text(json.dumps(previous,indent=2)+'\n');rows=[x for x in previous['rows']if x['exit_status']==0];total=previous['cumulative_extraction_seconds']
for trial in range(3):
 for mode in (('before','after')if trial%2==0 else('after','before')):
  if any(x['trial']==trial and x['mode']==mode for x in rows):continue
  destination=B/f'record-v2-{trial}-{mode}';target=B/f'record-v2-{trial}-{mode}.json'
  started=time.monotonic()
  with (E/f'record-v2-{trial}-{mode}.log').open('w')as log:
   result=subprocess.run([sys.executable,str(B/'measure_world.py'),str(destination),json.dumps([seed]),str(target)],env=dict(os.environ,READINESS_SOURCE=str(B/'reference'if mode=='before'else R),PROFILE='0',PYTHONDONTWRITEBYTECODE='1'),stdout=log,stderr=subprocess.STDOUT,timeout=min(120,600-total))
  elapsed=time.monotonic()-started;total+=elapsed
  entry=dict(trial=trial,mode=mode,seconds=elapsed,exit_status=result.returncode,report=str(target));rows.append(entry)
  (E/'RECORD_REPLAY.json').write_text(json.dumps(dict(status='RUNNING',rows=rows,cumulative_extraction_seconds=total,cap_seconds=600),indent=2)+'\n')
  assert result.returncode==0,(entry,(E/f'record-v2-{trial}-{mode}.log').read_text()[-3000:])
  value=json.loads(target.read_text());entry['pipeline']=value
  print(trial,mode,elapsed,flush=True)
report=dict(status='PASS',rows=rows,cumulative_extraction_seconds=total,cap_seconds=600,seed=seed,distinct_existing_worlds=1,median_seconds={mode:statistics.median(x['seconds']for x in rows if x['mode']==mode)for mode in ('before','after')},scope='3counterbalanced paired fullrecords ononeexistingworld;no newseedsearch;wallbudget-limited8192 metadata maydiffer;fixed-observationderivationparity separate;notpopulation throughput')
(E/'RECORD_REPLAY.json').write_text(json.dumps(report,indent=2)+'\n')
