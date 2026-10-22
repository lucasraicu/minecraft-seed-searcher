"""Segmented serving against an exhaustive oracle, including cross-leaf worlds."""
import copy
import json
import pytest
from seed_search.catalog.models import identity,empty_observation,world_id
from seed_search.catalog.registry import STRUCTURES,ENVELOPE
from seed_search.catalog.summaries import summarize
from seed_search.catalog.query import search
from seed_search.catalog.service import CatalogService,ServiceError
from seed_search.catalog.evaluation import heldout_cases


def sample(seed):
    obs=empty_observation(identity(seed,model_id='pilot-test',native_sha256='a'*64,source_sha256='b'*64))
    for i,f in enumerate(STRUCTURES):
        obs['structures'][f['id']]=[[int(seed)%100,i*8],[256,0],[400,100]]
        obs['coverage'][f['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_viable_starts_v1'}
    return obs,[r for r in summarize(obs) if r['anchor'] in ([0,0],[256,0],[-256,0])]


def bind(template,info):
    return dict(template,catalog_snapshot_id=info['snapshot_id'],game_build_id=info['header']['game_build_id'],
                world_settings_id=info['header']['world_settings_id'])


def test_indexed_global_ranks_and_cursor_pages_match_exhaustive(tmp_path):
    from seed_search.catalog.segments import SegmentedCatalog
    observations=[];layouts=[]
    for seed in (-1,0,1,17,27,79,-(1<<63),(1<<63)-1):
        obs,rows=sample(seed);observations.append(obs);layouts.extend(rows)
    root=tmp_path/'pilot'
    with SegmentedCatalog(root,leaf_entries=4,fanout=2) as store:
        sid=store.publish(observations,layouts);info=store.info(sid)
        assert store.audit(sid)['passed']
    service=CatalogService(root,secret=b'test-key',query_seconds=30)
    corpus=heldout_cases()
    for case in corpus['cases'][:70]:
        request=bind(case['template'],info)
        expected=search(layouts,request,snapshot_id=sid,limit=50,observations=observations)
        actual=[];cursor=None
        while True:
            body=dict(request=request,page_size=3)
            if cursor:body['cursor']=cursor
            result=service.query(body);actual.extend(result['results']);cursor=result['next_cursor']
            assert result['matched_worlds']==len(expected)
            if not cursor:break
        assert [(r['world_id'],r['layout_id'],r['score']) for r in actual]==[(r['world_id'],r['layout_id'],r['score']) for r in expected]
    request=bind(corpus['cases'][0]['template'],info);first=service.query(dict(request=request,page_size=2))
    assert first['next_cursor']
    # Rebuild caches and publish new worlds while the cursor remains pinned.
    service.cache.clear();service.cache_size=0
    service.result_cache.clear();service.result_size=0
    extra,extra_rows=sample(99)
    with SegmentedCatalog(root) as store:new_sid=store.publish([extra],extra_rows,parent=sid)
    second=service.query(dict(request=request,page_size=2,cursor=first['next_cursor']))
    assert second['snapshot_id']==sid and new_sid!=sid
    assert not {r['world_id'] for r in first['results']}&{r['world_id'] for r in second['results']}
    with pytest.raises(ServiceError):service.query(dict(request=request,page_size=3,cursor=first['next_cursor']))
    detail=service.detail(sid,first['results'][0]['world_id'],first['results'][0]['layout_id'])
    assert detail['identity']['seed']==first['results'][0]['seed']
    assert detail['layout']['anchor']==first['results'][0]['anchor']
    with SegmentedCatalog(root) as store:
        selected=list(store.iter_segments(sid,layout_key=(first['results'][0]['world_id'],first['results'][0]['layout_id'])))
        assert sum(len(segment['layouts']) for segment in selected)==1
    with pytest.raises(ServiceError):service.detail(sid,world_id(extra['identity']),first['results'][0]['layout_id'])


def test_timeout_is_explicit_and_never_returns_partial_ranking(tmp_path):
    from seed_search.catalog.segments import SegmentedCatalog
    obs,rows=sample(1);root=tmp_path/'pilot'
    with SegmentedCatalog(root) as store:sid=store.publish([obs],rows);info=store.info(sid)
    request=bind(heldout_cases()['cases'][0]['template'],info)
    with pytest.raises(ServiceError,match='allowance'):
        CatalogService(root,query_seconds=0).query(dict(request=request))
