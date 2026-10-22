from common import *
import cProfile,collections,pstats,signal
from instrument import Probe,stats_json
from seed_search.catalog.service import CatalogService
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.query import rank_v3
from seed_search.catalog.products import product_registry_v2
signal.alarm(300);store=AutomationStore(DATA);service=CatalogService(DATA);manifest,prime=timed(lambda:service._query_snapshot(store,SID));records=[];oracles={}
def clear():
 with service.cache_lock:service.result_cache.clear();service.result_size=0
for name,req in cases():
 trials=[];expected=None
 for i in range(3):
  clear();value,cold=timed(lambda:service.query(dict(request=req,page_size=5)));warm_value,warm=timed(lambda:service.query(dict(request=req,page_size=5)))
  assert not value['stats']['result_cache_hit'] and warm_value['stats']['result_cache_hit'];assert canonical_result(value)==canonical_result(warm_value)
  if expected is not None:assert canonical_result(value)==expected
  expected=canonical_result(value);trials.append(dict(trial=i,result_cold=cold,result_warm=warm,matched_worlds=value['matched_worlds']))
 rows=list(store.iter_query_summaries(manifest,req['border_side'],req['anchor_mode'],lazy_features=True));oracle,score=timed(lambda:rank_v3(iter(rows),req,limit=1000,keep_keys=True,registry=manifest['registry']))
 shown=[{k:v for k,v in row.items() if k!='_sort_key'} for row in oracle['results'][:5]];assert shown==expected['results'];assert oracle['matched_worlds']==expected['matched_worlds']
 oracles[name]=oracle;records.append(dict(name=name,request=req,trials=trials,predecoded_row_count=len(rows),predecoded_score=score));del rows
 print(name,'complete',flush=True)
# Product paths currently rebuild and validate the entire manifest even for one page.
counts=collections.Counter(x['objective_id'] for x in store.snapshot(SID)['memberships']);eligible={p['id'] for p in product_registry_v2()['products'] if p['availability_status']=='predicted'}
pid=next(p for p,n in counts.most_common() if p in eligible and n>=40)
products=[]
for view in ['primary','reserve']:
 body=dict(revision='catalog-product-request-v2',snapshot_id=SID,product_id=pid,page_size=5,view=view)
 trials=[];expected=None
 for i in range(3):
  value,m=timed(lambda:service.product_results(body));assert value['ok'];expected=expected or value['results'];assert expected==value['results'];trials.append(m)
 products.append(dict(request=body,trials=trials,results=value))
# Real current detail representation.
first=oracles['broad-recommended']['results'][0];detail=[]
for i in range(2):
 value,m=timed(lambda:service.detail(SID,first['world_id'],first['layout_id']));assert value['ok'];detail.append(m)
# Offline profile diagnostic uses its own increased deadline only; no live config change.
profile_service=CatalogService(DATA,query_seconds=120);profile_service._query_snapshot(store,SID)
req=dict(cases())['broad-recommended'];probe=Probe().start();profile=cProfile.Profile();profile.enable();t=time.monotonic();cpu=time.process_time()
try:value=profile_service.query(dict(request=req,page_size=5))
finally:profile.disable();elapsed=time.monotonic()-t;pcpu=time.process_time()-cpu;counters=probe.stop();profile.dump_stats(B/'query.prof')
assert value['results']==[{k:v for k,v in x.items() if k!='_sort_key'} for x in oracles['broad-recommended']['results'][:5]]
save('QUERY_PROFILE.json',dict(wall_seconds=elapsed,cpu_seconds=pcpu,counters=counters,profile=stats_json(B/'query.prof')))
# Profile precomputed-product path independently.
profile=cProfile.Profile();profile.enable();t=time.monotonic();v=profile_service.product_results(products[0]['request']);profile.disable();profile.dump_stats(B/'product.prof');save('PRODUCT_PROFILE.json',dict(wall_seconds=time.monotonic()-t,profile=stats_json(B/'product.prof')))
save('QUERIES.json',dict(status='PASS',context_cache_prime=prime,cases=records,products=products,detail=detail,profile_scope='Offline increased deadline120s only for instrumentation;unprofiled queries use10s;application cache cold/result warm are not disk-cold'))
save('ORACLES.json',oracles);service.close();profile_service.close();print('Queries/profile pass',flush=True)
