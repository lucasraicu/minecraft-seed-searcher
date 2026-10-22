"""Read models keep source integrity and same-anchor unknown semantics."""
import copy
import pytest
from test_automation_query import catalog,request
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest,REGISTRY_V2
from seed_search.catalog.ingestion import atomic_json
from seed_search.catalog.read_views import pack_masks,candidate_layouts,structure_rules,filtered_summaries
from seed_search.catalog.query import rank_v2
from seed_search.catalog.service import CatalogService


def paged(catalog):
 service,sid=catalog;store=AutomationStore(service.root);m=store.snapshot(sid);m['generation']+=1;sid=digest(m)
 store._PAGE_THRESHOLD_BYTES=1;store._PAGE_ITEM_LIMIT=1
 artifact=store._write_manifest(m,compression_level=1)
 atomic_json(store.snapshots_dir/(sid+'.json'),dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=m['generation'],artifact=artifact))
 return service,sid,store,m


def test_board_warm_view_verifies_unrelated_pages_and_isolates_response(catalog,monkeypatch):
 service,sid,store,m=paged(catalog)
 body=dict(revision='catalog-product-request-v2',snapshot_id=sid,product_id='preset.v2.nether_duo',page_size=1)
 original=service.product_results(body);assert len(original['results'])==1
 original['results'][0]['seed']='mutated'
 monkeypatch.setattr(AutomationStore,'snapshot',lambda *_:pytest.fail('Warm board reparsed full manifest'))
 assert service.product_results(body)['results'][0]['seed']=='1'
 metadata,_=service._read_view_get(('verified-board-view-v1',sid));refs=metadata['artifacts'];assert len(refs)>1
 ref=refs[-1];p=store.artifacts.root/ref['relative_key'];wire=p.read_bytes();p.write_bytes(wire[:-1]+bytes([wire[-1]^1]))
 with pytest.raises(ValueError,match='sha256 mismatch'):service.product_results(body)


def test_boards_reject_rebound_snapshot_and_tiny_cache_falls_back(catalog):
 service,sid=catalog;store=AutomationStore(service.root)
 body=dict(revision='catalog-product-request-v2',snapshot_id=sid,product_id='preset.v2.nether_duo')
 expected=service.product_results(body)
 tiny=CatalogService(service.root,cache_bytes=1);assert tiny.product_results(body)==expected;assert tiny.cache_size==0
 binding=store._binding(sid);binding['generation']+=1;atomic_json(store.snapshots_dir/(sid+'.json'),binding)
 with pytest.raises(ValueError,match='binding changed'):service.product_results(body)


def test_masks_keep_unknown_and_require_same_anchor():
 features=[f for f in REGISTRY_V2['features']if f['kind']=='structure_count'];a=features[0]['id'];b=features[1]['id']
 rows=[]
 for lid,ca,cb,complete in [('x',5,0,True),('y',0,5,True),('pending',0,0,False),('both',5,5,True)]:
  rows.append(dict(layout_id=lid,features={f['id']:dict(counts=[ca if f['id']==a else cb if f['id']==b else 0]*4,complete=[complete]*4)for f in features}))
 h,c=pack_masks(rows,REGISTRY_V2)
 assert candidate_layouts(h,c,[(a,0,1),(b,0,1)])=={'pending','both'}
 assert candidate_layouts(h,c,[(a,3,33)])=={'pending'}
 rows[-1]['features'][a]['counts']=[300]*4;h,c=pack_masks(rows,REGISTRY_V2)
 assert 'both'in candidate_layouts(h,c,[(a,0,200)])


def test_prefilter_full_original_scorer_parity_and_rehash_warm_projection(catalog):
 service,sid=catalog;store=AutomationStore(service.root);m=service._query_snapshot(store,sid);req=request(service,sid)
 oracle=rank_v2(store.iter_query_summaries(m,2048,'world_spawn_estimated',lazy_features=True),req,keep_keys=True)
 for _ in range(2):assert rank_v2(filtered_summaries(service,store,m,req,lambda:None),req,keep_keys=True)==oracle
 assert any(k[0]=='typed-structure-mask-v1'for k in service.cache)
 entry=m['worlds'][0];ref=entry['summary_artifacts']['2048'];p=store.artifacts.root/ref['relative_key'];wire=p.read_bytes();p.write_bytes(wire[:-1]+bytes([wire[-1]^1]))
 with pytest.raises(ValueError,match='sha256 mismatch'):list(filtered_summaries(service,store,m,req,lambda:None))


def test_unknown_biome_any_and_preferences_never_exclude(catalog):
 service,sid=catalog;req=request(service,sid)
 req['rows']=[dict(rule='required',kind='biome_witness',any_of=['biome.forest','biome.plains'],scope={'kind':'near_base','radius':256}),dict(req['rows'][0],rule='preferred',importance=3)]
 assert structure_rules(req,REGISTRY_V2)==[]
 store=AutomationStore(service.root);m=service._query_snapshot(store,sid)
 a=rank_v2(store.iter_query_summaries(m,2048,'world_spawn_estimated',lazy_features=True),req,keep_keys=True)
 b=rank_v2(filtered_summaries(service,store,m,req,lambda:None),req,keep_keys=True)
 assert a==b and b['unresolved_worlds']==2


def test_read_view_serialized_budget_and_mutation_isolation():
 service=CatalogService(cache_bytes=2048)
 for i in range(100):service._read_view_put(('view',i),({'ids':[i]*15},b'x'*100))
 assert service.cache_size<=service.cache_bytes
 h,c=service._read_view_get(('view',99));h['ids'][0]=-1
 assert service._read_view_get(('view',99))[0]['ids'][0]==99
 assert service._read_view_get(('view',0))is None


def test_pinned_board_cursor_survives_concurrent_current_publication(catalog):
 service,sid=catalog;store=AutomationStore(service.root)
 body=dict(revision='catalog-product-request-v2',snapshot_id=sid,product_id='preset.v2.nether_duo',page_size=1)
 first=service.product_results(body);assert first['next_cursor']
 m=store.snapshot(sid);m['generation']+=1;new_sid=digest(m);artifact=store._write_manifest(m)
 binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=new_sid,generation=m['generation'],artifact=artifact)
 atomic_json(store.snapshots_dir/(new_sid+'.json'),binding);atomic_json(store.current_path,binding)
 old_second=service.product_results(dict(body,cursor=first['next_cursor']))
 assert old_second['snapshot_id']==sid and old_second['results'][0]['seed']=='2'
 from seed_search.catalog.service import ServiceError
 with pytest.raises(ServiceError,match='Cursor'):service.product_results(dict(body,snapshot_id=new_sid,cursor=first['next_cursor']))
