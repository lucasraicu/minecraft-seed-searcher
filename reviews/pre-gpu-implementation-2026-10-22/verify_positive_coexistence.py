"""Reuse the earlier known-positive cohort to cover retained-record persistence."""
from pathlib import Path
import sys,os,json,time,subprocess,urllib.request,threading,concurrent.futures,importlib.util
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';old=B.parent/'current-framework-benchmark-20261022'
spec=importlib.util.spec_from_file_location('positive_personal',old/'measure_personal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.P=B/'positive';m.P.mkdir(exist_ok=True)
previous=json.loads((old/'personal-results.json').read_text());expected=next(r['fingerprint']for r in previous['rows']if r['trial']==1 and r['arm']=='personal_only');assert expected['records']==1
source=json.loads((B/'QUERIES.json').read_text());request=next(c['request']for c in source['cases']if c['name']=='mixed-variants');port=18002
log=(E/'positive-http-v2.log').open('w');server=subprocess.Popen([sys.executable,'-m','seed_search.catalog.http_server','--root',str(B/'catalog-copy'),'--port',str(port),'--query-processes','2'],env=dict(os.environ,PYTHONPATH=str(R/'src')),stdout=log,stderr=subprocess.STDOUT,start_new_session=True);process=None;stop=threading.Event();queries=[];pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)
def ask(client):
 while not stop.is_set():
  started=time.monotonic();wire=urllib.request.Request(f'http://127.0.0.1:{port}/api/catalog/query',data=json.dumps(dict(request=request,page_size=5)).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(wire,timeout=12)as response:body=json.load(response);assert response.status==200
  queries.append(dict(client=client,started=started,ended=time.monotonic(),matched_worlds=body['matched_worlds']))
try:
 limit=time.monotonic()+120
 while True:
  assert server.poll()is None
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/catalog/capabilities',timeout=2):break
  except(OSError,TimeoutError):assert time.monotonic()<limit;time.sleep(.2)
 control=json.loads((E/'positive-coexistence.log').read_text().splitlines()[0]);control['fingerprint']=json.loads((E/'POSITIVE_ATTEMPT1.json').read_text())['actual'];assert control['fingerprint']==expected
 seed=json.loads((B/'catalog-seeds.json').read_text())[0];report=B/'positive-world.json';world=B/'positive-world';extraction_start=time.monotonic()
 with(E/'positive-world.log').open('w')as worldlog:
  process=subprocess.Popen([sys.executable,str(B/'measure_world.py'),str(world),json.dumps([seed]),str(report)],env=dict(os.environ,READINESS_SOURCE=str(R),PROFILE='0'),stdout=worldlog,stderr=subprocess.STDOUT)
  limit=time.monotonic()+15
  while not list(world.rglob('*.settings.json')):assert process.poll()is None and time.monotonic()<limit;time.sleep(.02)
  futures=[pool.submit(ask,i)for i in range(2)];start=time.monotonic();active=m.one_run(0,'positive-active',start=m.COUNT);end=time.monotonic();stop.set()
  for f in futures:f.result(timeout=12)
  assert process.wait(timeout=120)==0
 extraction_end=time.monotonic();assert json.loads(json.dumps(active['fingerprint']))==expected
 overlaps={str(c):sum(max(0,min(end,q['ended'])-max(start,q['started']))for q in queries if q['client']==c)for c in(0,1)};assert all(v>0 for v in overlaps.values())
 public=json.loads(report.read_text());assert public['status']=='PASS'
 out=dict(status='PASS',control=control,active=active,same_as_prior_positive_fingerprint=True,retained_personal_records=1,active_interval=[start,end],query_overlap_seconds=overlaps,queries=queries,extraction_seconds=extraction_end-extraction_start,public=public,scope='One supplemented matched pair on already-benchmarked262144-input positivecohort;notadditionaluniqueseedsearch orfull100naturalheap benchmark')
 (E/'POSITIVE_COEXISTENCE.json').write_text(json.dumps(out,indent=2)+'\n');print('known-positive cohort coexistence PASS',flush=True)
finally:
 stop.set();pool.shutdown(wait=True,cancel_futures=True)
 for p in(process,server):
  if p is not None and p.poll()is None:
   p.terminate()
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
 log.close()
