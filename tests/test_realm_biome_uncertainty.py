from seed_search.realm.biomes import classify
from seed_search.realm.config import default_config


def test_prediction_observations_do_not_bound_actual_presence_or_score():
    result=classify(['forest','taiga','cherry_grove','pale_garden'],default_config()['biomes'])
    bounds=result['uncertainty']
    assert result['qualification']=='PREDICTED'
    assert bounds['domain']=='prediction_model_only'
    assert bounds['wooded_family_count_interval']==[4,5]
    assert bounds['wooded_bonus_interval']==[10,15]
    assert bounds['actual_generation_score_interval'][0]==0
    assert bounds['score_interval'][0]==result['score']


def test_verified_samples_keep_unseen_families_possible():
    result=classify(['forest','taiga'],default_config()['biomes'],verified=True)
    bounds=result['uncertainty']
    assert result['qualification']=='VERIFIED'
    assert bounds['domain']=='actual_generated_surface'
    assert bounds['wooded_family_count_interval']==[2,5]
    assert bounds['actual_generation_score_interval']==bounds['score_interval']
    assert bounds['possible_wooded_families']==['cherry','dark_pale','forest','jungle','taiga']


def test_exhaustive_verified_surface_closes_intervals_and_confirms_absence():
    result=classify(['forest','savanna','desert'],default_config()['biomes'],complete=True,verified=True)
    bounds=result['uncertainty']
    assert result['qualification']=='FAILED'
    assert bounds['wooded_family_count_interval']==[1,1]
    assert bounds['score_interval']==[3,3]
    assert bounds['possible_wooded_families']==['forest']


def test_exhaustive_prediction_cannot_close_actual_uncertainty():
    result=classify(['forest'],default_config()['biomes'],complete=True)
    assert result['qualification']=='PENDING'
    assert result['uncertainty']['wooded_family_count_interval']==[1,5]
    assert not result['uncertainty']['exhaustive_verified']


def test_savanna_does_not_change_any_reward_bounds():
    policy=default_config()['biomes']
    before=classify(['forest','taiga'],policy)
    after=classify(['forest','taiga','savanna','savanna_plateau','windswept_savanna'],policy)
    assert before['uncertainty']==after['uncertainty']
    assert before['score']==after['score']


def test_unknown_biome_mapping_cannot_establish_wooded_absence():
    result=classify(['forest','unknown_255'],default_config()['biomes'],complete=True,verified=True)
    assert result['qualification']=='PENDING'
    assert not result['uncertainty']['mapping_complete']
    assert result['uncertainty']['wooded_family_count_interval']==[1,5]
    assert not result['uncertainty']['exhaustive_verified']


def test_unrecognized_string_name_cannot_establish_wooded_absence():
    result=classify(['forest','minecraft:new_unmapped_woodland'],default_config()['biomes'],complete=True,verified=True)
    assert result['qualification']=='PENDING'
    assert not result['uncertainty']['mapping_complete']
    assert result['uncertainty']['wooded_family_count_interval']==[1,5]
    assert result['unmapped_names']==['new_unmapped_woodland']
