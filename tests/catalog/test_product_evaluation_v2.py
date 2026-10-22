"""Synthetic geometry fixtures; these are not generated Minecraft worlds."""
import copy
from fractions import Fraction
import pytest

from seed_search.catalog.models import identity
from seed_search.catalog.registry import FEATURES_V2,REGISTRY_REVISION_V2,digest
from seed_search.catalog.product_evaluation import (
    DEFINITIONS,FAMILIES,evaluate_products,minimum_circle,product_offers,
)


def observation():
    ident=identity('123',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64)
    bounds=dict(overworld=[-5120,-5120,5120,5120],nether=[-640,-640,640,640])
    structs={f['id']:[[0,0]] for f in FEATURES_V2 if f['kind']=='structure_count'}
    obs=dict(revision='catalog-observation-v2',registry_revision=REGISTRY_REVISION_V2,
        identity=ident,bounds=bounds,structures=structs,biomes=dict(overworld=[],nether=[]),
        biome_names={},coverage={},anchors=[dict(mode='world_spawn_estimated',coordinate=[0,0],source_id='c'*64)],
        realm=None,metrics={},errors={})
    for f in FEATURES_V2:
        if f['kind']=='structure_count':obs['coverage'][f['id']]=dict(status='complete',bounds=bounds[f['dimension']],method_id='predictor_viable_starts_v1')
    return obs


def add_biomes(obs,names,dimension='overworld',y=63):
    for name in names:
        bid=len(obs['biome_names'])+1
        obs['biome_names'][str(bid)]=name
        obs['biomes'][dimension].append([bid,y,0,bid])


def rows(obs):return {r['product_id']:r for r in evaluate_products(obs)}


def test_circle_exact_support_and_diameter_vs_center():
    assert minimum_circle([(0,0),(256,0)])[0]==128**2
    assert minimum_circle([(0,0),(257,0)])[0]>128**2
    # The centroid of a triangle is not generally its minimum-circle center.
    r,x,z=minimum_circle([(0,0),(4,0),(1,1)])
    assert (r,x,z)==(4,2,0)
    assert minimum_circle([(0,0),(4,0),(2,4)])[0]==Fraction(25,4)
    assert minimum_circle([(0,0),(0,2),(2,0),(2,2)])[0]==2


def test_all_sixteen_presets_have_executable_positive_geometry():
    obs=observation();obs['structures']['structure.shipwreck'].append([1,0])
    add_biomes(obs,['cherry_grove','meadow','bamboo_jungle','ice_spikes','badlands','mushroom_fields'])
    add_biomes(obs,['warped_forest'],dimension='nether',y=64)
    result=rows(obs)
    assert len(result)==36
    for p in DEFINITIONS['presets']:
        assert result[p['id']]['status']=='match',result[p['id']]
        assert result[p['id']]['witnesses']
    assert len(product_offers(list(result.values())))>=16


def test_thresholds_and_missing_scope_are_not_rounded_or_clipped():
    obs=observation();obs['structures']['structure.desert_pyramid']=[[150,0]]
    key='preset.v2.temple_rush'
    assert rows(obs)[key]['status']=='match'
    obs['structures']['structure.desert_pyramid']=[[151,0]]
    assert rows(obs)[key]['status']=='no_match'
    obs['coverage']['structure.desert_pyramid']['status']='partial'
    assert rows(obs)[key]['status']=='pending'
    obs['coverage']['structure.village']['bounds']=[-100,-100,100,100]
    assert rows(obs)['record.v2.village_density']['status']=='pending'


def test_partial_positive_counts_are_lower_bounds_and_no_spawn_fallback():
    obs=observation();obs['coverage']['structure.village']['status']='partial'
    assert rows(obs)['preset.v2.mansion_village']['status']=='match'
    assert rows(obs)['record.v2.village_density']['status']=='pending'
    obs['anchors']=[]
    assert all(r['status']=='pending' for r in rows(obs).values())


def test_negative_projection_and_dimension_specific_distance():
    obs=observation();obs['anchors'][0]['coordinate']=[-1,-9]
    obs['structures']['structure.fortress']=[[199,-2]]
    obs['structures']['structure.bastion']=[[-1,-2]]
    row=rows(obs)['preset.v2.nether_duo']
    assert row['status']=='match' and row['anchor']['nether']==[-1,-2]
    assert max(w['distance_squared'] for w in row['witnesses'])==200**2
    obs['structures']['structure.fortress']=[[200,-2]]
    assert rows(obs)['preset.v2.nether_duo']['status']=='no_match'


def test_shipwrecks_must_be_distinct_and_biomes_have_height_roles():
    obs=observation()
    assert rows(obs)['preset.v2.village_two_shipwrecks']['status']=='no_match'
    add_biomes(obs,['cherry_grove'],y=160)
    assert rows(obs)['preset.v2.cherry_haven']['status']=='pending'
    add_biomes(obs,['cherry_grove'],y=63)
    assert rows(obs)['preset.v2.cherry_haven']['status']=='match'


def test_all_seventeen_record_products_and_cluster_rules():
    obs=observation()
    obs['structures']['structure.swamp_hut']=[[0,0],[10,0],[0,10],[10,10]]
    obs['structures']['structure.monument']=[[0,0],[10,0],[0,10]]
    for family,names in FAMILIES['record_families'].items():
        add_biomes(obs,[names[0]],y=-48 if family in FAMILIES['cave_families'] else 63)
    result=rows(obs)
    assert all(result[p['id']]['status']=='match' for p in DEFINITIONS['records'])
    assert result['record.v2.monument_cluster']['rank'][0]==-3
    assert result['record.v2.biome_sampler']['metric']['families']==14
    # A circle of radius100 is not the promised pairwise100 cluster.
    for f in obs['structures']:obs['structures'][f]=[]
    for f,p in zip(['village','outpost','mansion','trial_chamber'],[[100,0],[-100,0],[0,100],[0,-100]]):
        obs['structures']['structure.'+f]=[p]
    assert rows(obs)['record.v2.four_type_cluster']['status']!='match'


def test_realm_uses_exact_existing_config_and_center():
    from seed_search.realm.config import dynamic_v3_blueprint_config
    obs=observation()
    anchor=dict(qualification='PREDICTED',baseline_score_complete=True,baseline_score=336.0,
                evaluation_center=[137,-19],ranking=dict(components={'core':20}))
    obs['realm']=dict(config_digest=digest(dynamic_v3_blueprint_config()),evaluation=dict(anchors=[anchor]))
    r=rows(obs)['realm.v2.qualified']
    assert r['status']=='match' and r['anchor']['overworld']==[137,-19] and r['rank']==[-336]
    obs['realm']['config_digest']='0'*64
    assert rows(obs)['realm.v2.qualified']['status']=='pending'


def test_larger_boards_require_compatible_evidence_and_share_original_total_capacity():
    from seed_search.catalog.products import product_registry_v2
    from seed_search.catalog.retention import automation_objectives
    result=rows(observation())
    boards=[DEFINITIONS['realm'],*DEFINITIONS['realm_sizes']]
    assert [b['capacity'] for b in boards]==[3334,3333,3333]
    assert sum(b['capacity'] for b in boards)==10000
    assert all(result[b['id']]['status']=='pending' and result[b['id']]['reason']=='size_calibration_source_mismatch' for b in boards[1:])
    registry=product_registry_v2()['products']
    assert all(next(p for p in registry if p['id']==b['id'])['availability_status']=='predicted' for b in boards[1:])
    objectives=automation_objectives()
    assert len(objectives)==7027 and sum(objectives.values())==105644


def test_launch_registry_omits_removed_terrain_products_without_changing_retention():
    from seed_search.catalog.products import product_registry,product_registry_v2
    from seed_search.catalog.retention import automation_objectives
    removed={'record.'+name for name in ('direct_drop','badlands_spine','mega_cherry',
                                        'triple_mineshaft','deep_dark_void')}
    legacy={p['id'] for p in product_registry()['products']}
    current=product_registry_v2()['products']
    active_ids={p['id'] for p in current}
    assert removed<=legacy  # Historical definitions/links remain recognizable.
    assert removed.isdisjoint(active_ids)
    assert {p['id'] for p in current if p['kind']=='record'}=={p['id'] for p in DEFINITIONS['records']}
    assert len([p for p in current if p['kind']=='preset'])==16
    assert len([p for p in current if p['kind']=='record'])==17
    assert len([p for p in current if p['kind']=='realm'])==3
    assert not any(p['kind']=='research' for p in current)
    objectives=automation_objectives()
    assert len(objectives)==7027 and sum(objectives.values())==105644
    assert removed.isdisjoint(objectives)
