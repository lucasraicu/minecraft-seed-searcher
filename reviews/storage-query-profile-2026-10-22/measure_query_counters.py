"""Counter-only query attribution without cProfile, resolving microbench GC confounds."""
from common import *
from instrument import Probe
from seed_search.catalog.service import CatalogService
from seed_search.catalog.store import AutomationStore
service=CatalogService(DATA);store=AutomationStore(DATA);_,prime=timed(lambda:service._query_snapshot(store,SID));out=[]
for name,req in [cases()[1],cases()[2]]:
 probe=Probe().start()
 try:value,m=timed(lambda:service.query(dict(request=req,page_size=5)))
 finally:counters=probe.stop()
 assert value['ok'] and not value['stats']['result_cache_hit'];out.append(dict(name=name,timing=m,counters=counters,matched_worlds=value['matched_worlds']))
save('QUERY_COUNTERS.json',dict(status='PASS',prime=prime,cases=out,scope='Counter-only instrumentation,no cProfile;inclusive nested counters not additive'))
print('counter-only attribution complete',flush=True)
