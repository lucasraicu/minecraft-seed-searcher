"""Five-minute bounded reuse of an already-benchmarked input cohort; private outputs."""
from pathlib import Path
import importlib.util,os,json,sys,time,threading,subprocess,urllib.request,concurrent.futures,statistics
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';sys.path.insert(0,str(R/'src'))
old=B.parent/'current-framework-benchmark-20261022/measure_personal.py';spec=importlib.util.spec_from_file_location('sustained_personal',old);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.P=B/'sustained';m.P.mkdir()
SID='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d';port=18001
source=json.loads((B/'QUERIES.json').read_text());request=next(c['request']for c in source['cases']if c['name']=='mixed-variants')
thermal=subprocess.run(['pmset','-g','therm'],capture_output=True,text=True,timeout=5)
server_log=(E/'private-http.log').open('w');server=subprocess.Popen([sys.executable,'-m','seed_search.catalog.http_server','--root',str(B/'catalog-copy'),'--port',str(port),'--query-processes','2'],env=dict(os.environ,PYTHONPATH=str(R/'src'),PYTHONDONTWRITEBYTECODE='1'),stdout=server_log,stderr=subprocess.STDOUT,start_new_session=True)
rows=[];queries=[];extractions=[];stop=threading.Event();executor=concurrent.futures.ThreadPoolExecutor(max_workers=3)
def ask(client):
 sequence=0
 while not stop.is_set():
  req=json.loads(json.dumps(request));req['rows'][0]['at_least']=1+sequence%8;body=dict(request=req,page_size=5)
  started=time.monotonic();wire=urllib.request.Request(f'http://127.0.0.1:{port}/api/catalog/query',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(wire,timeout=12)as response:value=json.load(response);assert response.status==200
  ended=time.monotonic();assert ended-started<10 and value['ok']
  queries.append(dict(client=client,sequence=sequence,started=started,ended=ended,seconds=ended-started,result_cache_hit=value['stats']['result_cache_hit'],matched=value['matched_worlds']))
  sequence+=1
 return sequence

def extract_records():
 seed=json.loads((B/'catalog-seeds.json').read_text())[0]
 for i in range(3):
  if stop.is_set():break
  started=time.monotonic();target=B/f'sustained-record-{i}.json'
  with(E/f'sustained-record-{i}.log').open('w')as log:
   charged=json.loads((E/'RECORD_REPLAY.json').read_text())['cumulative_extraction_seconds']+sum(x['seconds']for x in extractions)
   assert charged<600
   result=subprocess.run([sys.executable,str(B/'measure_world.py'),str(B/f'sustained-world-{i}'),json.dumps([seed]),str(target)],env=dict(os.environ,READINESS_SOURCE=str(R),PROFILE='0'),stdout=log,stderr=subprocess.STDOUT,timeout=min(120,600-charged))
  ended=time.monotonic();assert result.returncode==0,(i,result.returncode)
  extractions.append(dict(started=started,ended=ended,seconds=ended-started,report=str(target)))
 return len(extractions)

try:
 deadline=time.monotonic()+180
 while True:
  assert server.poll()is None,'Private HTTP initialization failed'
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/catalog/capabilities',timeout=2)as response:assert json.load(response)['ok'];break
  except(OSError,TimeoutError):
   if time.monotonic()>deadline:raise TimeoutError('Private HTTP readiness')
   time.sleep(.2)
 # Complete HTTP board requests include serialization and transport, not just service calls.
 board_body=source['products'][0]['request'];http_boards=[]
 for i in range(3):
  wire=urllib.request.Request(f'http://127.0.0.1:{port}/api/catalog/product-results',data=json.dumps(board_body).encode(),headers={'Content-Type':'application/json'});t=time.monotonic()
  with urllib.request.urlopen(wire,timeout=10)as response:value=json.load(response)
  assert value['results']==source['products'][0]['results']['results'];http_boards.append(time.monotonic()-t)
 expected=None
 for arm in ('control','active'):
  futures=[]
  if arm=='active':futures=[executor.submit(ask,0),executor.submit(ask,1),executor.submit(extract_records)]
  start=time.monotonic();sequence=0
  while time.monotonic()-start<150:
   run_started=time.monotonic()
   row=m.one_run(sequence,arm,start=0,public=B/'sustained-handoff'if arm=='active'else None)
   row.update(started=run_started,ended=time.monotonic())
   if expected is None:expected=row['fingerprint']
   assert row['fingerprint']==expected,'Sustained semantic/receipt mismatch'
   rows.append(dict(row,arm=arm));sequence+=1
  duration=time.monotonic()-start
  print(arm,'seconds',duration,'iterations',sequence,flush=True)
  if arm=='active':
   stop.set()
   for f in futures:f.result(timeout=130)
 from seed_search.catalog.harvest import HarvestQueue
 with HarvestQueue(B/'sustained-handoff')as q:backpressure=q.status()
 assert sum(v for k,v in backpressure['jobs'].items()if k in ('pending','active'))<=100
 from seed_search.catalog.registry import digest
 overlap=lambda a,b:max(0,min(a['ended'],b['ended'])-max(a['started'],b['started']))
 active_rows=[r for r in rows if r['arm']=='active']
 exposure=dict(extraction_seconds=sum(overlap(r,e)for r in active_rows for e in extractions),query_seconds_by_client={str(c):sum(overlap(r,q)for r in active_rows for q in queries if q['client']==c)for c in(0,1)},active_personal_seconds=sum(r['ended']-r['started']for r in active_rows))
 assert exposure['extraction_seconds']>0 and all(v>0 for v in exposure['query_seconds_by_client'].values())
 report=dict(exposure=exposure,status='PASS',rows=rows,queries=queries,extractions=extractions,http_board_seconds=http_boards,http_board_median=statistics.median(http_boards),median_input_seed_rates={arm:statistics.median(r['input_seeds_per_second']for r in rows if r['arm']==arm)for arm in ('control','active')},exact_same_receipts_scores_results=True,cohort=dict(count=m.COUNT,start=0,run_key=m.KEY,repeated_existing_benchmark_cohort=True),backpressure=backpressure,thermal=dict(exit_status=thermal.returncode,stdout=thermal.stdout,stderr=thermal.stderr),scope='2x150s bounded full persisted framework screening; same already-benchmarked cohort repeated,notnewunique-search throughput;active two privateHTTPqueryworkers plus3full existing-world extractions;natural full100heap not claimed')
 (E/'SUSTAINED.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
 stop.set();executor.shutdown(wait=True,cancel_futures=True)
 if server.poll()is None:
  server.terminate()
  try:server.wait(timeout=10)
  except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
 server_log.close()
