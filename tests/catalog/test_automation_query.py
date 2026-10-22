"""V2 HTTP service contract against real immutable CAS and source-bound snapshots."""
import pytest
from seed_search.catalog.models import identity,empty_observation_v2,world_id
from seed_search.catalog.registry import digest
from seed_search.catalog.summaries import summarize_v2
from seed_search.catalog.product_evaluation import evaluate_products,product_offers
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
from seed_search.catalog.service import CatalogService,ServiceError


@pytest.fixture
def catalog(tmp_path):
    store=AutomationStore(tmp_path)
    objectives={'sample':100,'preset.v2.nether_duo':100}
    with HarvestQueue(tmp_path) as q:
        ledger=AutomationLedger(q,policy_revision='c'*64,objectives=objectives)
        for seed in ('1','2'):
            obs=empty_observation_v2(identity(seed,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
            obs['anchors']=[dict(mode='world_spawn_estimated',coordinate=[0,0],source_id='f'*64)]
            obs['structures']={'structure.stronghold':[[8,0]],'structure.fortress':[[0,0]],'structure.bastion':[[1,0]]}
            rows=summarize_v2(obs);wid=world_id(obs['identity']);artifact=store.stage(obs,rows)
            evaluations=evaluate_products(obs)
            receipt=dict(world_id=wid,identity=obs['identity'],observation_id=digest(obs),artifact=artifact,evaluations=evaluations,replay={})
            offers=[dict(objective_id='sample',rank=[int(seed)],member=dict(world_id=wid,source_observation_id=digest(obs)))]
            offers += [o for o in product_offers(evaluations) if o['objective_id']=='preset.v2.nether_duo']
            ledger.offer(receipt,offers)
        sid=store.publish(ledger)
    service=CatalogService(tmp_path,secret=b'fixed-test-secret')
    yield service,sid
    service.close()


def request(service,sid):
    header=service.status()['header']
    return dict(request_revision='catalog-query-v2',edition='bedrock',dimension='overworld',
        game_build_id=header['game_build_id'],world_settings_id='default',catalog_snapshot_id=sid,
        evidence_policy='predicted_observations_v2',fallback_profile='balanced_survival',
        border_side=2048,anchor_mode='world_spawn_estimated',rows=[
            dict(rule='required',kind='structure_count',feature='structure.stronghold',at_least=1,scope={'kind':'near_base','radius':256}),
            dict(rule='required',kind='structure_count',feature='structure.bastion',at_least=1,scope={'kind':'near_base','radius':64})])


def test_pinned_v2_query_paginates_and_rejects_changed_request(catalog):
    service,sid=catalog;req=request(service,sid)
    first=service.query({'request':req,'page_size':1});assert first['matched_worlds']==2
    assert first['results'][0]['seed']=='1';assert first['next_cursor']
    second=service.query({'request':req,'page_size':1,'cursor':first['next_cursor']})
    assert second['results'][0]['seed']=='2' and second['next_cursor'] is None
    assert second['stats']['result_cache_hit'] is True
    altered=dict(req,border_side=4096)
    with pytest.raises(ServiceError,match='Cursor'):service.query({'request':altered,'page_size':1,'cursor':first['next_cursor']})


def test_products_dimensions_detail_and_legacy_snapshots(catalog):
    service,sid=catalog
    assert service.status()['revision']=='catalog-snapshot-v2'
    assert len(service.capabilities()['registry_v2']['features'])==31
    assert service.snapshots()['snapshots'][0]['snapshot_id']==sid
    registry=service.products();assert registry['revision']=='catalog-products-v2'
    assert service.products(sid)['revision']=='catalog-products-v2'
    assert service.products('f'*64)['revision']=='catalog-products-v1'
    assert not any(p['kind']=='research' for p in registry['products'])
    assert len([p for p in registry['products'] if p['pillar_id']=='presets'])==16
    products=service.product_results(dict(revision='catalog-product-request-v2',snapshot_id=sid,product_id='preset.v2.nether_duo'))
    assert len(products['results'])==2 and products['scope']['dimension']=='nether'
    assert products['evaluation_counts']=={'match':2,'no_match':0,'pending':0}
    result=service.query({'request':request(service,sid)})['results'][0]
    detail=service.detail(sid,result['world_id'],result['layout_id'])
    assert detail['layout']['anchor_mode']=='world_spawn_estimated'
    assert detail['anchor_sources'][0]['source_id']=='f'*64
    assert detail['nether_bounds']==[-512,-512,512,512]
    assert 'structure.bastion' in detail['nether_structures']
    assert 'structure.bastion' not in detail['structures']
    assert 'structure.stronghold' in detail['structures']


def test_snapshot_traversal_and_request_identity_are_rejected(catalog):
    service,sid=catalog;req=request(service,sid)
    with pytest.raises(ValueError):service.query({'request':dict(req,catalog_snapshot_id='../configuration')})
    with pytest.raises(ValueError):service.query({'request':dict(req,game_build_id='research:other')})
