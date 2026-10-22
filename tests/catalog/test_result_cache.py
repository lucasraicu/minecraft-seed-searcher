"""Cache hits preserve exact cursors, immutable pages and snapshot integrity."""
import pytest
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.service import CatalogService,ServiceError
from seed_search.catalog.evaluation import heldout_cases
from tests.catalog.test_integrated_pilot import sample,bind


def test_cached_pages_cannot_mutate_sort_boundaries_and_remain_pinned(tmp_path):
    root=tmp_path/'pilot';observations=[];layouts=[]
    for seed in (0,1,2):
        obs,rows=sample(seed);observations.append(obs);layouts.extend(rows)
    with SegmentedCatalog(root) as store:
        sid=store.publish(observations,layouts);info=store.info(sid)
    service=CatalogService(root,secret=b'cache-test');request=bind(heldout_cases()['cases'][0]['template'],info)
    first=service.query(dict(request=request,page_size=1))
    assert not first['stats']['result_cache_hit']
    original_seed=first['results'][0]['seed'];first['results'][0]['seed']='mutated'
    again=service.query(dict(request=request,page_size=1))
    assert again['stats']['result_cache_hit'] and again['stats']['decoded_layouts']==0
    assert again['results'][0]['seed']==original_seed
    second=service.query(dict(request=request,page_size=1,cursor=first['next_cursor']))
    assert second['results'][0]['world_id']!=again['results'][0]['world_id']
    service.result_cache.clear();service.result_size=0
    rebuilt=service.query(dict(request=request,page_size=1,cursor=first['next_cursor']))
    assert rebuilt['results']==second['results']
    assert service.result_size<=service.result_bytes
    with SegmentedCatalog(root) as store:
        store.conn.execute('UPDATE observation_ref SET observation_id=? WHERE snapshot_id=?',('f'*64,sid))
    with pytest.raises(ServiceError,match='membership changed'):service.query(dict(request=request))


def test_zero_cache_budget_forces_exact_rerank(tmp_path):
    root=tmp_path/'pilot';obs,rows=sample(7)
    with SegmentedCatalog(root) as store:sid=store.publish([obs],rows);info=store.info(sid)
    service=CatalogService(root,cache_bytes=0)
    request=bind(heldout_cases()['cases'][0]['template'],info)
    assert not service.query(dict(request=request))['stats']['result_cache_hit']
    assert not service.query(dict(request=request))['stats']['result_cache_hit']
    assert not service.result_cache
