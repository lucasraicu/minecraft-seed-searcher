import numpy as np
import pytest

from seed_search.realm.biomes import raster_variant_fit, classify
from seed_search.realm.config import default_config
from seed_search.realm.raster import Raster


def surface(spacing=1):
    rows=[{'x':0,'z':0,'y':71,'name':'minecraft:forest','status':'OBSERVED'},
          {'x':spacing,'z':0,'y':90,'name':'minecraft:taiga','status':'OBSERVED'}]
    return Raster((0,0,2*spacing,spacing),spacing,np.full((1,2),70),metadata={
        'source':'actual','surface_biome_observations':rows,'surface_biome_evidence':'actual_api_string_names',
        'surface_biome_coverage_complete':True,'stable_sampled_observations':True,
        'surface_biome_query_policy':'one_cell_above_exposed_surface'})


def test_actual_string_names_need_no_native_id_mapping():
    fit,status,provenance=raster_variant_fit(surface(),'v1')
    assert fit==pytest.approx(100*2/6) and status=='VERIFIED'
    assert provenance['raw_names']==['forest','taiga']


def test_sparse_surface_samples_do_not_certify_complete_biome_fit():
    fit,status,provenance=raster_variant_fit(surface(8),'v1')
    assert fit>0 and status=='PARTIAL'
    assert provenance['complete_sample_lattice']


@pytest.mark.parametrize('change',[
    lambda r:r.metadata['surface_biome_observations'].pop(),
    lambda r:r.metadata['surface_biome_observations'][0].update(status='QUERY_FAILED'),
    lambda r:r.metadata['surface_biome_observations'][0].update(name='minecraft:unknown_new_biome'),
    lambda r:r.metadata.update(stable_sampled_observations=False),
])
def test_missing_unmapped_or_unstable_surface_is_not_verified(change):
    raster=surface();change(raster)
    assert raster_variant_fit(raster,'v1')[1]=='PARTIAL'


def test_conflicting_and_off_lattice_rows_do_not_inflate_coverage():
    raster=surface(8)
    raster.metadata['surface_biome_observations'] += [
        {'x':1,'z':0,'name':'forest','status':'OBSERVED'},
        {'x':0,'z':0,'name':'jungle','status':'OBSERVED'}]
    fit,status,p=raster_variant_fit(raster,'v1')
    assert status=='PARTIAL' and p['observed_cells']==2
    assert p['conflicting_coordinates']==[[0,0]]


def test_string_names_without_actual_evidence_are_not_used():
    raster=surface();raster.metadata['source']='prediction'
    assert raster_variant_fit(raster,'v1')[:2]==(0.,'UNKNOWN')


def test_numeric_mapping_requires_target_release_and_full_lattice():
    raster=Raster((0,0,1,1),1,[[70]],biomes=[[4]],metadata={'source':'actual','biome_evidence':'actual_generated'})
    assert raster_variant_fit(raster,'v1')[1]=='PARTIAL'
    raster.metadata['biome_mapping_version']='26.52'
    assert raster_variant_fit(raster,'v1')[1]=='VERIFIED'


def test_bedrock_raw_names_count_distinct_wooded_families_and_neutral_savanna():
    names=['minecraft:forest_hills','minecraft:birch_forest_mutated','minecraft:cold_taiga',
           'minecraft:mega_taiga','minecraft:roofed_forest','minecraft:jungle_edge','minecraft:cherry_grove']
    cfg=default_config()['biomes']
    detected=classify(names,cfg,verified=True)
    assert detected['wooded_family_count']==5 and detected['wooded_bonus']==15
    after=classify(names+['minecraft:savanna_mutated','minecraft:savanna_plateau_mutated'],cfg,verified=True)
    assert after['score']==detected['score']
    assert after['wooded_families']==detected['wooded_families']


def test_bedrock_wooded_badlands_is_optional_badlands_not_custom_forest():
    result=classify(['minecraft:mesa_plateau_stone'],default_config()['biomes'],verified=True)
    assert result['wooded_family_count']==0 and result['family_bonuses']=={'badlands':2}
