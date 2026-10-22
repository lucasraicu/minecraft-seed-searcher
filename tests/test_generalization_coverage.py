"""Guard against interpreting attempts or grouped queries as feature validation."""
from scripts.generalization_coverage import coverage


def test_errors_unattempted_biomes_and_grouped_temples_stay_unverified():
    manifest = dict(worlds=[dict(seed='1', predictions=[dict(dimension='nether', biome_name='warped_forest')],
        structures=[dict(dimension='overworld', structure_type='desert_pyramid'),
                    dict(dimension='overworld', structure_type='village')])])
    inventory = [dict(name='warped_forest', dimension=-1, version_active=True, generates=True),
                 dict(name='deep_dark', dimension=0, version_active=True, generates=True),
                 dict(name='legacy', dimension=0, version_active=False, generates=True)]
    results = dict(manifest_sha256='frozen', biome_rows=[dict(dimension='nether', predicted_name='warped_forest',
        seed='1', cohort='blind', outcome='error')], structure_rows=[dict(dimension='overworld',
        case_id='temple-1', structure_type='desert_pyramid', seed='1', cohort='blind', disposition='retained', outcome='reference_exact'),
        dict(dimension='overworld', structure_type='village', seed='1', cohort='targeted',
             case_id='village-1', disposition='rejected', outcome='reference_exact')])
    value = coverage(manifest, inventory, results)
    assert len(value['biomes']) == 2
    assert all(r['status'] == 'missing_matching_witness' for r in value['biomes'])
    structures = {r['name']: r for r in value['structures']}
    assert structures['desert_pyramid']['status'] == 'grouped_subtype_unresolved'
    village = structures['village']
    assert village['status'] == 'over_rejection_observed'
    assert village['matching_reference_seeds'] == ['1']
    assert village['by_cohort_and_disposition']['targeted']['rejected'] == {'reference_exact': 1}
    assert village['by_cohort_and_disposition']['blind']['retained'] == {}
    assert value['generated_count'] is None and value['exhaustive_count'] is None
