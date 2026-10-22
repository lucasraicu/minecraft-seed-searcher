"""Matched complete service calls and exhaustive current boards; private copied data."""
from pathlib import Path
import json,sys,time,statistics,copy
R=Path(__file__).resolve().parents[2];B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';E=Path(__file__).parent
mode=sys.argv[1];sys.path.insert(0,str((B/'reference'if mode=='before'else R)/'src'))
from seed_search.catalog.service import CatalogService
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.query import rank_v3
from seed_search.catalog.products import product_registry_v2
from seed_search.catalog.retention import automation_primary_objectives_v3
from seed_search.catalog.registry import digest
SID='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d'
source=json.loads((B/'QUERIES.json').read_text());service=CatalogService(B/'catalog-copy',secret=b'fixed-readiness-benchmark-secret');store=AutomationStore(service.root)
start=time.perf_counter();manifest=service._query_snapshot(store,SID);prime=time.perf_counter()-start

def timed(f):
 t=time.perf_counter();value=f();return value,time.perf_counter()-t

def cleared():
 with service.cache_lock:service.result_cache.clear();service.result_size=0

records=[]
for case in source['cases']:
 req=case['request'];trials=[];expected=None
 for i in range(3):
  cleared();v,elapsed=timed(lambda:service.query(dict(request=req,page_size=50)))
  stable={k:x for k,x in v.items()if k not in ('stats','next_cursor')}
  if expected is None:expected=stable
  assert stable==expected
  trials.append(elapsed)
  assert not v['stats']['result_cache_hit']
 # Walk API cursors and retain full order, not just first-page or row count.
 page=v;all_rows=list(page['results']);cursor=page['next_cursor']
 while cursor:
  page=service.query(dict(request=req,page_size=50,cursor=cursor));all_rows.extend(page['results']);cursor=page['next_cursor']
 records.append(dict(name=case['name'],request=req,trials_seconds=trials,median_seconds=statistics.median(trials),all_results=all_rows,unresolved_candidates=v['unresolved_candidates'],matched_worlds=v['matched_worlds'],unresolved_worlds=v['unresolved_worlds']))
 print(mode,case['name'],trials,flush=True)
products=[]
for case in source['products']:
 trials=[]
 for i in range(3):v,elapsed=timed(lambda:service.product_results(case['request']));trials.append(elapsed);assert v['results']==case['results']['results']
 products.append(dict(request=case['request'],trials_seconds=trials,median_seconds=statistics.median(trials)))
board_proofs=[]
if mode=='after':
 full=store.snapshot(SID);caps=automation_primary_objectives_v3()
 for product in product_registry_v2()['products']:
  if product['availability_status']!='predicted':continue
  pid=product['id'];all_members=[r['member']for r in full['memberships']if r['objective_id']==pid];k=caps[pid]
  for view in ('primary','reserve'):
   expected=all_members[:k]if view=='primary'else all_members[k:2*k]
   expected=[dict(m,candidate_role=view,evidence_status='predicted')for m in expected]
   body=dict(revision='catalog-product-request-v2',snapshot_id=SID,product_id=pid,view=view,page_size=50)
   value=service.product_results(body);actual=list(value['results']);cursor=value['next_cursor'];pages=1
   while cursor:
    value=service.product_results(dict(body,cursor=cursor));actual.extend(value['results']);cursor=value['next_cursor'];pages+=1
   assert actual==expected,(pid,view)
   assert value['matched_worlds']==len(expected)
   assert value['evaluation_counts']==full.get('product_status',{}).get(pid)
   assert value['primary_count']==min(k,len(all_members))and value['reserve_count']==max(0,len(all_members)-k)
   board_proofs.append(dict(product_id=pid,view=view,rows=len(actual),pages=pages,ordered_digest=digest(actual)))
 print('all boards',len(board_proofs),'PASS',flush=True)
report=dict(status='PASS',mode=mode,context_prime_seconds=prime,cases=records,products=products,all_board_views=board_proofs,index_cache_bytes=service.cache_size,index_cache_limit=service.cache_bytes,result_cache_bytes=service.result_size,result_cache_limit=service.result_bytes,scope='Complete service request/cursors with original integrity guards; filesystem warm;222realworlds;result uncached each timed trial;notnetworkHTTP/productionSLA')
(E/f'SERVING_{mode.upper()}.json').write_text(json.dumps(report,indent=2)+'\n');service.close()
if mode=='after':
 before=json.loads((E/'SERVING_BEFORE.json').read_text())
 for a,b in zip(before['cases'],records):
  for key in ('name','all_results','unresolved_candidates','matched_worlds','unresolved_worlds'):assert a[key]==b[key],(a['name'],key)
 assert service.cache_size<=service.cache_bytes
 (E/'SERVING_PARITY.json').write_text(json.dumps(dict(status='PASS',complete_order_witnesses_unknowns=True,queries=len(records),board_views=len(board_proofs),snapshot_id=SID),indent=2)+'\n')
