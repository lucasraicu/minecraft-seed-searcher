import copy
import random
import pytest
from seed_search.catalog.models import identity,empty_observation
from seed_search.catalog.registry import ENVELOPE,STRUCTURES,PROFILES,digest
from seed_search.catalog.summaries import summarize
from seed_search.catalog.query import search
from seed_search.catalog.view import SnapshotView
from seed_search.catalog.scoring import profile_units
from seed_search.catalog.evaluation import heldout_cases,evaluate,metrics


@pytest.fixture(scope='module')
def snapshot():
    observations=[];layouts=[]
    for seed in (0,-1,27):
        obs=empty_observation(identity(seed,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
        for slot,f in enumerate(STRUCTURES):
            obs['structures'][f['id']]=[[seed%31,slot*16],[400,0]]
            obs['coverage'][f['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_viable_starts_v1'}
        observations.append(obs);layouts.extend(summarize(obs))
    return {'snapshot_id':'view-test','observations':observations,'layouts':layouts}


def request():
    return dict(request_revision='catalog-query-v1',edition='bedrock',game_build_id='research:MC_26_50',
        catalog_snapshot_id='view-test',world_settings_id='default',dimension='overworld',anchor_mode='recommended',
        border_side=2048,evidence_policy='predicted_observations_v1',fallback_profile='balanced_survival',rows=[])


def test_immutable_view_matches_checked_query_and_defends_mutation(snapshot):
    view=SnapshotView.from_snapshot(snapshot);rng=random.Random(42)
    for _ in range(70):
        q=request();q['border_side']=rng.choice((2048,4096,8192));q['anchor_mode']=rng.choice(('origin','recommended'))
        q['rows']=[{'rule':'preferred','importance':5,'kind':'structure_count','feature':rng.choice(STRUCTURES)['id'],
            'at_least':rng.randrange(1,17),'scope':{'kind':'near_base','radius':rng.choice((256,512,1024))}}]
        assert view.search(q)==search(snapshot['layouts'],q,snapshot_id='view-test',observations=snapshot['observations'])
    copied=copy.deepcopy(snapshot);view2=SnapshotView.from_snapshot(copied);expected=view2.search(request())
    copied['layouts'][0]['counts'][0]=[100]*4
    assert view2.search(request())==expected
    with pytest.raises(TypeError):view2._layouts[0]['counts'][0][0]=3
    with pytest.raises(AttributeError):view2.snapshot_id='changed'
    with pytest.raises(ValueError):view.search(request(),world_ids={'not-a-world'})
    assert view.search(request(),world_ids=set())==[]


def test_shared_retention_profile_matches_existing_query(snapshot):
    layout=snapshot['layouts'][0]
    for profile in PROFILES:
        q=request();q['border_side']=layout['border_side'];q['fallback_profile']=profile
        expected=search([layout],q,snapshot_id='view-test')[0]
        units,maximum,_=profile_units(layout,profile)
        assert int(units)==expected['utility_units']
        assert float(units*100/maximum)==pytest.approx(expected['score'])


def test_heldout_is_fixed_and_covers_scope():
    a=heldout_cases();b=heldout_cases();assert a==b and len(a['cases'])==200
    assert len({c['category'] for c in a['cases']})==8
    assert {c['template']['border_side'] for c in a['cases']}=={2048,4096,8192}
    assert {c['template']['anchor_mode'] for c in a['cases']}=={'origin','recommended'}


def test_metrics_exclude_empty_and_expose_no_result_penalty(snapshot):
    view=SnapshotView.from_snapshot(snapshot);base=heldout_cases();base['cases']=base['cases'][:4];base['sha256']=digest(base['cases'])
    all_metrics,cache=evaluate(view,view.world_ids,base)
    assert all_metrics['discriminating'] is False
    assert all_metrics['summary']['mean_top10_recall']==1
    empty,_=evaluate(view,set(),base,reference_results=cache)
    assert empty['summary']['nonempty_preservation']==0
    assert empty['summary']['mean_normalized_score_regret']==1
    bad=dict(cache,snapshot_id='other')
    with pytest.raises(ValueError):evaluate(view,set(),base,reference_results=bad)
    assert metrics([{'reference_count':0,'retained_count':0}])['nonempty_preservation'] is None
