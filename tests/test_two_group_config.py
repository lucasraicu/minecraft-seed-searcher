"""The new policy is versioned separately from existing origin checkpoints."""
import copy
from pathlib import Path

import pytest
import yaml

from seed_search.realm.config import (
    ORIGIN_REVISION, TWO_GROUP_REVISION, origin_blueprint_config,
    two_group_blueprint_config, origin_policy, stronghold_after, validate_config,
)


def test_current_yaml_matches_two_group_policy():
    cfg=yaml.safe_load(Path('config/realm.yaml').read_text())
    validate_config(cfg)
    assert cfg['screening_revision']==TWO_GROUP_REVISION
    assert cfg['structures']==two_group_blueprint_config()['structures']
    assert cfg['search']['max_misses']==2
    assert origin_policy(cfg)


def test_historical_origin_identity_and_counts_are_preserved():
    cfg=origin_blueprint_config()
    validate_config(cfg)
    assert cfg['screening_revision']==ORIGIN_REVISION
    assert cfg['structures']['minimum_counts']['trial_chamber']==5
    assert 'hard_floors' not in cfg['structures']


def test_stronghold_placement_is_persisted_and_old_v2_runs_replay():
    current=two_group_blueprint_config()
    assert stronghold_after(current)==4
    old=copy.deepcopy(current)
    old['search']['structure_order']=['ruined_portal','trial_chamber','outpost',
                                     'desert_pyramid','jungle_temple','mansion',
                                     'ancient_city','village','mineshaft']
    old['search'].pop('stronghold_after_structure_count')
    validate_config(old)
    assert stronghold_after(old)==2
    current['search']['stronghold_after_structure_count']=2
    with pytest.raises(ValueError,match='Stronghold placement'):
        validate_config(current)


def test_full_v2_direct_and_replay_keep_complete_evidence_with_late_stronghold(prototype):
    from test_blueprint_batch_prototype import FixtureBackend, NAMES
    from seed_search.realm.blueprint import evaluate_seed
    cfg=prototype.cfg

    class PolicyFixtureBackend(FixtureBackend):
        def structure_pair(self,name,bounds):
            if name=='stronghold':
                return ([],[]) if self.missing==28 else ([(16,0),(32,0)],[(16,0),(32,0)])
            slot=NAMES.index(name)
            goal=(cfg['structures']['nether_minimum_counts'].get(name) or
                  cfg['structures']['minimum_counts'].get(name,1))
            n=goal-1 if self.missing==slot else goal+2
            points=[(bounds[0]+800+i*16,bounds[1]+800) for i in range(n)]
            return points,points

    for missing in (-1,28):
        with prototype.sweep([1],fixtures=[(0,0,missing)],complete=True) as batch:
            direct=batch.records()[0]['anchors'][0]
        replay=evaluate_seed(0,1,cfg,backend_factory=lambda _,m=missing:PolicyFixtureBackend((0,0,m)),short_circuit=False)['anchors'][0]
        for field in ('qualification','fatal_reasons','deficit_categories','pending_reasons',
                      'required_structures','required_nether_structures','ranking','baseline_score_complete'):
            assert direct[field]==replay[field]


@pytest.mark.parametrize('budget',[True,-1,9,2.5,None])
def test_budget_requires_bounded_category_integer(budget):
    cfg=two_group_blueprint_config()
    cfg['search']['max_misses']=budget
    with pytest.raises(ValueError,match='max_misses'):
        validate_config(cfg)


def test_hard_floor_cannot_be_relaxed():
    cfg=copy.deepcopy(two_group_blueprint_config())
    cfg['structures']['hard_floors']['ancient_city']=0
    with pytest.raises(ValueError,match='floors'):
        validate_config(cfg)


@pytest.fixture(scope='module')
def prototype(tmp_path_factory):
    from seed_search.realm.native_batch import Prototype
    from scripts.build_blueprint_batch import build
    directory=tmp_path_factory.mktemp('two-group-native')
    build(directory)
    return Prototype(directory,two_group_blueprint_config())


@pytest.mark.parametrize('slot,goal,floor',[
    (0,1,0),(4,2,1),(5,7,5),(6,10,8),(7,7,5),(9,20,17),(10,2,1),(11,3,2),
])
def test_flexible_exact_floor_and_below(prototype,slot,goal,floor):
    if floor:
        with prototype.sweep([1,2],fixtures=[(0,0,slot)]*2,
                             fixture_deltas=[goal-floor,goal-floor+1],complete=True) as batch:
            rows=batch.records()
        first,second=[r['anchors'][0] for r in rows]
        assert first['qualification']=='PREDICTED'
        assert first['deficit_categories']
        assert second['qualification']=='PENDING'
        assert second['fatal_reasons']
    else:
        with prototype.sweep([1],fixtures=[(0,0,slot)],complete=True) as batch:
            row=batch.records()[0]['anchors'][0]
        assert row['qualification']=='PREDICTED'
        assert row['deficit_categories']==['mansion']


@pytest.mark.parametrize('slot',[1,2,12,28])
@pytest.mark.parametrize('budget',[0,2,8])
def test_strict_absence_never_spends_budget(prototype,slot,budget):
    with prototype.sweep([1],fixtures=[(0,0,slot)],retention='survivors',max_misses=budget) as batch:
        assert batch.pointer.result_count==0


@pytest.mark.parametrize('deficits,kept',[([],True),([0],True),([0,6],True),([0,6,10],False)])
def test_category_budget_is_independent_of_biomes(prototype,deficits,kept):
    mask=sum(1<<slot for slot in deficits)
    with prototype.sweep([1],fixtures=[(0,0,-1)],fixture_masks=[mask],
                         retention='survivors',max_misses=2) as batch:
        assert bool(batch.pointer.result_count)==kept
        if kept:
            row=batch.retained_records()[0]['anchors'][0]
            assert row['qualification']=='PREDICTED'
            assert len(row['deficit_categories'])==len(deficits)


def test_missing_biome_is_fatal_even_with_unused_category_budget(prototype):
    with prototype.sweep([1],fixtures=[(0,0,13)],retention='survivors',max_misses=8) as batch:
        assert batch.pointer.result_count==0


def test_deficit_survivor_persists_and_resumes(prototype,tmp_path):
    from seed_search.realm.store import RealmStore
    with prototype.sweep([1],fixtures=[(0,0,6)],retention='survivors',max_misses=2) as batch:
        records=batch.retained_records()
        receipt=batch.retention_receipt()
    anchor=records[0]['anchors'][0]
    assert anchor['qualification']=='PREDICTED'
    assert anchor['deficit_categories']==['trial_chamber']
    assert anchor['baseline_score_complete']
    identity={'config':prototype.cfg,'retention':{'mode':'survivors','max_misses':2}}
    with RealmStore(tmp_path,identity) as store:
        store.configure_range(0,1,1)
        assert store.claim_range('v2')==(0,1)
        prepared=store.prepare_retained_range(0,1,records,receipt)
        assert store.complete_prepared(prepared,lease=('v2',1))
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    with RealmStore(tmp_path,resume=True) as store:
        assert store.status()['completed_seeds']==1
        saved=store.get_candidate(anchor['id'])
        assert saved['qualification']=='PREDICTED'
        assert saved['deficit_categories']==['trial_chamber']
        from types import SimpleNamespace
        from seed_search.realm.marine import evaluate_marine_stage
        raster=SimpleNamespace(resolution=min(prototype.cfg['terrain']['resolutions']),
                               metadata={},biomes=None,shape=(1,1))
        precheck={'model_geometry_pass':True,'metrics':{'known_fraction':1.0},'evidence':'PREDICTED'}
        _,patch=evaluate_marine_stage(saved,prototype.cfg,raster,precheck)
        assert patch['marine_stage']['status']=='PENDING'
        store.upsert_candidate(patch)
        after=store.get_candidate(anchor['id'])
        assert after['qualification']=='PREDICTED'
        assert after['baseline_score']==saved['baseline_score']
        assert after['marine_stage']['reason']=='ocean_evidence_unavailable'
        changed=copy.deepcopy(after['required_structures'])
        changed['stronghold']['raw']=[[16,0],[24,0]]
        store.upsert_candidate({'id':anchor['id'],'required_structures':changed})
        from seed_search.realm.reports import export
        export(store)
        import csv
        with (tmp_path/'results/current/structure_starts.csv').open() as handle:
            starts=list(csv.DictReader(handle))
        assert any(row['structure']=='stronghold' and row['x']=='16' for row in starts)
        assert any(row['structure']=='stronghold' and row['x']=='24' and row['predicted_viable']=='False' for row in starts)
        assert all(row['y']=='' for row in starts)
        assert (tmp_path/'results/structure_starts.csv').is_symlink()
        assert store.claim_range('resume') is None


def test_v2_bonus_boundaries_use_fixed_targets():
    from seed_search.realm.blueprint import smart_score
    def obs(n):return {'predicted_viable':[[i,0] for i in range(n)]}
    structures={name:obs(count) for name,count in {
        'stronghold':2,'mansion':2,'trial_chamber':12,'village':9,'ruined_portal':8,
        'mineshaft':22,'ancient_city':4,'outpost':2,'desert_pyramid':2,'jungle_temple':2,
    }.items()}
    nether={'fortress':obs(4),'bastion':obs(5)}
    bonus=smart_score(structures,nether,{'shipwreck':obs(6),'monument':obs(2)},
                      two_group=True,locked=True,origin=True,coastal_footprint_verified=True,
                      biome_names=['cherry_grove','badlands','mushroom_fields'],
                      metrics={'river_highway_connected':True,'mega_ravine_hub':True})['bonuses']
    assert bonus=={'mansion':100,'stronghold':50,'mega_ravine_hub':35,'river_highway':35,
                   'ancient_city':50,'fortress':40,'bastion':40,'monument':25,'trial_chamber':20,
                   'village':10,'ruined_portal':5,'mineshaft':2,'outpost':10,'desert_pyramid':10,
                   'jungle_temple':10,'shipwreck':5,'cherry_grove':15,'badlands':15,'mushroom_fields':15}


def test_spawn_actual_initial_player_predicates_and_radius():
    from seed_search.realm.spawn import classify_spawn
    cfg=two_group_blueprint_config()
    candidate={'seed':'-1','evaluation_center':[0,0],'qualification':'PREDICTED'}
    assert classify_spawn(candidate,cfg)['status']=='PENDING'
    evidence={'seed':'-1','placement_kind':'initial_player',
              'source':{'kind':'actual_generation','provider':'bds','version':cfg['game']['bds_version']},
              'coordinates':[100,63,0],'biome':'plains','dry':True,'solid_support':True,'headroom':True}
    assert classify_spawn(candidate,cfg,evidence)['status']=='VERIFIED'
    assert classify_spawn(candidate,cfg,{**evidence,'coordinates':[101,63,0]})['status']=='FAILED'
    assert classify_spawn(candidate,cfg,{**evidence,'coordinates':[0,62,0]})['status']=='FAILED'
    assert classify_spawn(candidate,cfg,{**evidence,'biome':'ocean'})['status']=='FAILED'
    assert classify_spawn(candidate,cfg,{**evidence,'biome':'minecraft:deep_ocean'})['status']=='FAILED'
    assert classify_spawn(candidate,cfg,{**evidence,'headroom':None})['status']=='PENDING'
    with pytest.raises(ValueError,match='Initial-player'):
        classify_spawn(candidate,cfg,{**evidence,'placement_kind':'world_spawn_metadata'})


def test_custom_ideals_above_fixed_floors_bind_native(prototype):
    from seed_search.realm.native_batch import Prototype
    cfg=two_group_blueprint_config()
    cfg['structures']['minimum_counts']['trial_chamber']=8
    cfg['structures']['nether_minimum_counts']['fortress']=1
    validate_config(cfg)
    custom=Prototype(prototype.directory,cfg)
    with custom.sweep([0],fixtures=[(0,0,6)],retention='survivors',max_misses=2) as batch:
        assert batch.pointer.result_count==0  # custom ideal 8, fixture 7 violates fixed floor 8
    with custom.sweep([0],fixtures=[(0,0,-1)],retention='survivors',max_misses=2) as batch:
        assert batch.retained_records()[0]['anchors'][0]['qualification']=='PREDICTED'


def test_v2_native_default_budget_and_mismatched_override(prototype,tmp_path):
    from seed_search.realm.native_batch import run_native_scan
    with prototype.sweep([0],fixtures=[(0,0,6)],retention='survivors') as batch:
        assert batch.retained_records()[0]['anchors'][0]['deficit_categories']==['trial_chamber']
        assert batch.max_misses==2
    with pytest.raises(ValueError,match='must match the resolved config'):
        run_native_scan(prototype.cfg,tmp_path,1,native_build=prototype.directory,
                        retention='survivors',max_misses=3)


def test_v2_rescore_keeps_baseline_separate_from_marine_bonus():
    from seed_search.realm.reports import _candidate_rescore
    cfg=two_group_blueprint_config()
    def obs(n):return {'predicted_viable':[[i,0] for i in range(n)]}
    candidate={'contract':'master_seed_blueprint_v1','screening_revision':cfg['screening_revision'],
               'required_structures':{'stronghold':obs(1),'mansion':obs(1)},
               'required_nether_structures':{},'optional_structures':{'shipwreck':obs(6)},
               'biomes':None,'marine_stage':{'status':'PREDICTED'},'baseline_score_complete':True,
               'pending_reasons':['count_trial_chamber'],'deficit_categories':['trial_chamber'],
               'fatal_reasons':[],'biome_failures':[]}
    updated=_candidate_rescore(candidate,cfg,'revision-test')
    assert updated['baseline_score']==50
    assert updated['combined_score']==55
    assert updated['baseline_score_uncertainty']['pending_prediction_requirements']==[]
    assert updated['score_revision']=='revision-test'
