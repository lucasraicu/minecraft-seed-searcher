import copy
import time

from seed_search.catalog.models import identity, empty_observation_v2
from seed_search.catalog.realm_evaluation import BiomeIndex, RealmScene, evaluate_large_realms
from seed_search.realm.blueprint import PALETTE, DYNAMIC_V3_LUXURIES


def observation():
    return empty_observation_v2(identity('17', model_id='26.50', native_sha256='a'*64, source_sha256='b'*64))


def test_prefix_matches_direct_lattice_with_negative_and_open_edges():
    obs=observation()
    obs['bounds']={d:[-128,-128,128,128] for d in ('overworld','nether')}
    obs['biome_names']={'0':'plains','1':'desert','2':'lush_caves','3':'nether_wastes','4':'mushroom_fields'}
    obs['biomes']['overworld']=[[x,y,z,(x//64+z//64)%3 if y in (63,160) else 2]
        for y in (-48,0,63,160) for z in range(-128,128,64) for x in range(-128,128,64)]
    obs['biomes']['nether']=[[x,64,z,3] for z in range(-128,128,64) for x in range(-128,128,64)]
    index=BiomeIndex(obs)
    for box in ([-128,-128,128,128],[-65,-1,1,128],[-64,-64,64,64]):
        expected={(x,z) for x,y,z,b in obs['biomes']['overworld'] if y in (63,160) and b==0 and box[0]<=x<box[2] and box[1]<=z<box[3]}
        assert index.counts('overworld',box)['plains']==len(expected)
        assert index.complete('overworld',box)
    missing=copy.deepcopy(obs)
    missing['biome_names']['0']='unknown_0'
    assert not BiomeIndex(missing).complete('overworld',[-128,-128,128,128])
    missing=copy.deepcopy(obs)
    missing['biomes']['overworld'].pop()
    assert not BiomeIndex(missing).complete('overworld',[-128,-128,128,128])


def test_unknown_inventory_stays_pending_and_negative_projection_is_floor():
    obs=observation()
    calibration={'thresholds':{'sizes':{'4096':{'village':{'base_levels':[6,7], 'thresholds':[24,28]}}}}}
    obs['structures']['structure.fortress']=[[-513,-514],[511,510]]
    obs['structures']['structure.bastion']=[[-1,-2]]
    scene=RealmScene(obs,calibration)
    row=scene.evaluate([-1,-9],4096,time.monotonic()+5)
    assert row['status']=='pending' and row['score_complete'] is False
    assert row['counts']['fortress']==1 and row['counts']['bastion']==1
    assert scene.complete('unrecorded',[-1,-1,1,1]) is False


def test_both_large_sizes_receive_candidate_budget(monkeypatch):
    import seed_search.catalog.realm_evaluation as module
    class FakeScene:
        def __init__(self,*args):pass
        def evaluate(self,center,side,deadline):
            return dict(status='match',center=list(center),score=side//32,missing=0,shortfall=0)
        def axis_events(self,*args):return []
    monkeypatch.setattr(module,'RealmScene',FakeScene)
    result=evaluate_large_realms(observation(),{'thresholds':{}},max_centers=81,seconds=.1)
    assert set(result['sizes'])=={'4096','8192'}
    assert all(row['candidates_evaluated']==81 for row in result['sizes'].values())
    assert result['nether_side']==1024 and result['luxury_side']=='selected_overworld'


def test_score_uses_existing_caps_and_partial_facts_do_not_qualify():
    obs=observation()
    names=('mansion','stronghold','monument','village','trial_chamber','ancient_city','desert_pyramid','outpost',
           'ruined_portal','shipwreck','mineshaft','jungle_temple','swamp_hut','trail_ruins','igloo','ocean_ruin','buried_treasure')
    calibration={'thresholds':{'sizes':{'4096':{name:{'base_levels':[0,25], 'thresholds':[0,25]} for name in names}}}}
    for name in names+('fortress','bastion'):
        if name not in ('ocean_ruin','buried_treasure'):
            obs['structures']['structure.'+name]=[[i*2,0] for i in range(30)]
            obs['coverage']['structure.'+name]={'status':'complete','bounds':obs['bounds']['nether' if name in ('fortress','bastion') else 'overworld']}
    obs['realm']={'inventory':{name:dict(status='complete',bounds=obs['bounds']['nether' if name=='bastion_variant' else 'overworld'],
        points=[[i*2,0,2] if name=='bastion_variant' else [i*2,0] for i in range(30)]) for name in ('ocean_ruin','buried_treasure','igloo_basement','bastion_variant')}}
    class Biomes:
        luxuries=DYNAMIC_V3_LUXURIES
        surface={}
        def counts(self,dimension,box):
            return {**{name:1 for name in PALETTE},**{'luxury.'+str(i):1 for i in range(10)},
                    **{name:1 for name in ('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas')}}
        def complete(self,*args):return True
    scene=RealmScene(obs,calibration);scene.biomes=Biomes()
    # Sparse dict is enough for the scenic helper's read-only indexed accesses.
    from collections import defaultdict
    scene.biomes.surface=defaultdict(lambda:'unknown')
    row=scene.evaluate([0,0],4096,time.monotonic()+5)
    assert row['status']=='match' and row['score_complete']
    assert row['score']==sum(row['group_scores'].values())<=1250
    assert row['group_scores']['nether']==140
    assert row['group_scores']['luxury_biomes']==265
    assert row['group_scores']['overworld']<=845
    obs['coverage']['structure.village']['status']='partial'
    assert scene.evaluate([0,0],4096,time.monotonic()+5)['status']=='pending'


def test_spread_graph_matches_exhaustive_rule_and_handles_dense_small_cluster():
    from itertools import combinations
    import random
    rng=random.Random(42)
    for _ in range(30):
        points=sorted({(rng.randrange(-400,400),rng.randrange(-400,400)) for i in range(14)})
        q=lambda p:(p[0]>=0,p[1]>=0)
        expected=next((group for group in combinations(points,3) if len({q(p) for p in group})==3 and all((a[0]-b[0])**2+(a[1]-b[1])**2>=256**2 for a,b in combinations(group,2))),None)
        actual=RealmScene._spread(points,[0,0],time.monotonic()+2)
        assert actual==(bool(expected),expected)
    cluster=[(x,z) for x in range(-5,5) for z in range(-5,5)]
    assert RealmScene._spread(cluster,[0,0],time.monotonic()+2)==(False,None)


def test_scenic_mapping_preserves_legacy_helper_at_off_origin_center():
    from seed_search.realm.dynamic import scenic_pair_bonus_v2
    obs=observation();obs['biome_names']={'0':'plains','1':'river'}
    obs['biomes']['overworld']=[[-1024,63,768,0],[-960,63,768,1]]
    index=BiomeIndex(obs)
    bonus,scenic,river=scenic_pair_bonus_v2(index.surface,[-1000,760],overworld_half=1024)
    assert bonus==20 and scenic==(-1024,768) and river==(-960,768)
