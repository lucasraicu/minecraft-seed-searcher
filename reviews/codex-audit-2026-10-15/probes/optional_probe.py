from pathlib import Path
import sys
sys.path[:0]=[str(Path.cwd()/'src'),str(Path.cwd()/'tests'),'/tmp/minecraft-audit-20261015']
import audit_optional as a
from seed_search.realm.native_batch import Prototype,Batch
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.blueprint import evaluate_dynamic_seed
from test_dynamic_baseline import DynamicFixtureBackend
p=Prototype('runs/dynamic-baseline-1664/native',dynamic_blueprint_config())
policy=a.ffi.new('NBPolicy *');a.ffi.buffer(policy)[:]=bytes(p.ffi.buffer(p.policy));policy.retention=1;policy.max_misses=2
seeds=a.ffi.new('uint64_t[]',[123]);fixtures=a.ffi.new('NBFixture[]',[(0,0,-1,0,1)])
b=a.lib.nb_fixture_sweep(seeds,fixtures,1,policy,1)
assert b!=a.ffi.NULL and not b.error
c=b.results[0].anchors[0]
print('C selected',c.x,c.z,'score',c.score,'huts',c.optional[0].viable.n)
a.lib.nb_free(b)
class OptionalFixture(DynamicFixtureBackend):
 def structure_pair(self,name,bounds):
  if name=='swamp_hut':return [(56,-800)],[(56,-800)]
  return super().structure_pair(name,bounds)
r=evaluate_dynamic_seed(0,123,dynamic_blueprint_config(),backend_factory=lambda _:OptionalFixture())['anchors'][0]
print('Python selected',r['evaluation_center'],'score',r['baseline_score'],'huts',r['optional_structures']['swamp_hut']['predicted_viable'])
from dataclasses import replace
import seed_search.realm.dynamic as d
from seed_search.realm.bounds import contains
original=d.candidate_centers
def recounted(inventories,*args,**kwargs):
 return [replace(row,counts={**row.counts,**{n:sum(contains(pt,d.overworld_bounds(row.center)) for pt in inventories.get(n,())) for n in d.OPTIONAL_NAMES}}) for row in original(inventories,*args,**kwargs)]
d.candidate_centers=recounted
r=evaluate_dynamic_seed(0,123,dynamic_blueprint_config(),backend_factory=lambda _:OptionalFixture())['anchors'][0]
print('Python with optional recount',r['evaluation_center'],'score',r['baseline_score'])
assert r['evaluation_center']==[-752,-816] and r['baseline_score']==434
