import pytest
from seed_search.catalog.harvest_native import _refinement_biome_index,_refinement_biome_pending
from seed_search.catalog.product_evaluation import DEFINITIONS,FAMILIES,biome_points
from seed_search.catalog.models import identity,empty_observation_v2


def definitions():
    return [p for p in DEFINITIONS['presets'] if p['biomes']]+[p for p in DEFINITIONS['records'] if p['kind']=='biome_sampler']


@pytest.mark.parametrize('scenario',['empty','wrong_height','overworld','nether','caves','complete'])
def test_indexed_pending_matches_exact_existing_witness_predicate(scenario):
    obs=empty_observation_v2(identity('1',model_id='26.50',native_sha256='a'*64,source_sha256='b'*64))
    for record,group in [(False,FAMILIES['features']),(True,FAMILIES['record_families'])]:
        for family,members in group.items():
            dimension='nether' if family in ('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas') else 'overworld'
            cave=family in FAMILIES['cave_families'];level=-48 if cave else 64 if dimension=='nether' else 63
            if scenario=='empty' or (scenario=='overworld' and (dimension!='overworld' or cave)) or (scenario=='nether' and dimension!='nether') or (scenario=='caves' and not cave):continue
            if scenario=='wrong_height':level=20
            bid=len(obs['biome_names']);obs['biome_names'][str(bid)]=members[0]
            obs['biomes'][dimension].append([0,level,0,bid])
    index=_refinement_biome_index(obs)
    for p in definitions():
        record=p.get('kind')=='biome_sampler';families=FAMILIES['record_families'] if record else p['biomes']
        expected=not all(biome_points(obs,f,p['dimension'],[0,0],p['radius'],record=record) for f in families)
        assert _refinement_biome_pending(p,[0,0],index)==expected


def test_inclusive_boundary_and_no_cross_dimension_substitution():
    p=next(p for p in definitions() if p['id']=='preset.v2.cherry_haven')
    dimension=p['dimension'];family=p['biomes'][0];name=FAMILIES['features'][family][0]
    index={'overworld':{name:[(150,63,0)]},'nether':{}}
    assert not _refinement_biome_pending(p,[0,0],index)
    index[dimension][name]=[(151,63,0)]
    assert _refinement_biome_pending(p,[0,0],index)
    index={'overworld':{},'nether':{name:[(0,63,0)]}}
    assert _refinement_biome_pending(p,[0,0],index)
