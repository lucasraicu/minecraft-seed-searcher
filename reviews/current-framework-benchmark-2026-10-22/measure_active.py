"""Counterbalanced current personal search vs current full public pipeline+queries."""
from pathlib import Path
import concurrent.futures,json,os,signal,statistics,subprocess,sys,threading,time,urllib.request
from measure_personal import one_run,COUNT,P
SID='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d'

def request(trial,client,seq):
 row=dict(rule='preferred',importance=3,kind='structure_count',feature=['structure.village','structure.bastion_treasure'][client],at_least=1+trial*3+seq,scope=dict(kind='near_base',radius=1024 if client==0 else 256))
 return dict(request=dict(request_revision='catalog-query-v3',edition='bedrock',dimension='overworld',game_build_id='research:26.50',world_settings_id='default',catalog_snapshot_id=SID,evidence_policy='predicted_observations_v3',fallback_profile='balanced_survival',border_side=[4096,8192][client],anchor_mode='recommended',rows=[row]),page_size=5)

def active(trial,seed):
 root=P/f'active-world-{trial}';report=P/f'active-world-{trial}.json';stop=threading.Event();ready=[threading.Event(),threading.Event()]
 executor=concurrent.futures.ThreadPoolExecutor(max_workers=2);process=None;queries=[]
 def query(client):
  out=[];seq=0
  while not stop.is_set() or not out:
   start=time.monotonic();ready[client].set();req=urllib.request.Request('http://127.0.0.1:3001/api/catalog/query',data=json.dumps(request(trial,client,seq)).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=12) as r:code=r.status;data=json.load(r)
   elapsed=time.monotonic()-start
   out.append(dict(client=client,sequence=seq,started=start,ended=time.monotonic(),seconds=elapsed,status=code,matched=data.get('matched_worlds'),stats=data.get('stats')))
   assert elapsed<10 and code==200 and data['matched_worlds']==222
   assert seq<10,'Query-loop bound';seq+=1
  return out
 with (P/f'active-world-{trial}.log').open('w') as log:
  try:
   process=subprocess.Popen([sys.executable,str(P/'measure_catalog.py'),str(root),json.dumps([seed]),str(report)],stdout=log,stderr=subprocess.STDOUT)
   limit=time.monotonic()+20
   while not list(root.rglob('*.settings.json')):
    assert process.poll() is None,'Public extraction exited before synchronization';assert time.monotonic()<limit,'Extraction synchronization timeout';time.sleep(.01)
   futures=[executor.submit(query,i) for i in range(2)]
   assert all(x.wait(2) for x in ready)
   start=time.monotonic();personal=one_run(trial,'active_catalog',public=P/f'active-handoff-{trial}');end=time.monotonic();stop.set()
   queries=[row for f in futures for row in f.result(timeout=12)]
   assert process.wait(timeout=120)==0,'Public replay failed; inspect owned log'
   public=json.loads(report.read_text());row=public['rows'][0]
   overlap=max(0,min(end,row['extraction_ended'])-max(start,row['extraction_started']))
   duration=end-start
   query_overlap={str(client):sum(max(0,min(end,q['ended'])-max(start,q['started'])) for q in queries if q['client']==client) for client in range(2)}
   assert overlap>0 and all(x>0 for x in query_overlap.values())
   personal.update(personal_interval=[start,end],extraction_overlap_seconds=overlap,extraction_overlap_fraction=overlap/duration,query_overlap_seconds=query_overlap,query_overlap_fraction={c:x/duration for c,x in query_overlap.items()},public=public,queries=queries)
   return personal
  finally:
   stop.set();executor.shutdown(wait=True)
   if process is not None and process.poll() is None:
    process.terminate()
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)

def main():
 signal.alarm(350);rows=[];seeds=json.loads((P/'catalog-seeds.json').read_text())
 for trial in range(3):
  pair=[]
  for arm in (('active_baseline','active_catalog') if trial%2==0 else ('active_catalog','active_baseline')):
   row=one_run(trial,arm) if arm=='active_baseline' else active(trial,seeds[trial%2]);rows.append(row);pair.append(row)
  assert pair[0]['fingerprint']==pair[1]['fingerprint'],('Semantic parity failed',trial)
  (P/'active-results.json').write_text(json.dumps(dict(rows=rows),indent=2)+'\n')
 report=dict(status='PASS',rows=rows,median_rates={arm:statistics.median(x['input_seeds_per_second'] for x in rows if x['arm']==arm) for arm in ['active_baseline','active_catalog']},paired_wall_ratios=[next(x['wall_seconds'] for x in rows if x['trial']==i and x['arm']=='active_catalog')/next(x['wall_seconds'] for x in rows if x['trial']==i and x['arm']=='active_baseline') for i in range(3)])
 (P/'active-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['median_rates']),flush=True)

if __name__=='__main__':main()
