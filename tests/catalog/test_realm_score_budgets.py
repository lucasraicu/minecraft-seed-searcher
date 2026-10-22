"""Protect user-frozen budgets while larger-world count schedules are calibrated."""
import json
from seed_search.realm.blueprint import dynamic_v3_score,DYNAMIC_V3_LUXURIES
from seed_search.catalog.registry import CONTRACT_ROOT


def test_existing_personal_score_preserves_exact_three_group_ceilings():
    policy=json.loads((CONTRACT_ROOT.parent/'v2'/'realm_scoring.json').read_text())
    names={name for _,members in DYNAMIC_V3_LUXURIES for name in members}
    structures={name:1000 for name in ('mansion','stronghold','monument','village','trial_chamber',
        'ancient_city','desert_pyramid','outpost','fortress','bastion','ruined_portal',
        'shipwreck','mineshaft','jungle_temple','swamp_hut','trail_ruins','igloo','ocean_ruin','buried_treasure')}
    score,components,_=dynamic_v3_score(structures,names,hub=45,scenic=1,village_spread=1,
                                      treasure_bastion=1,nether_core=20)
    without_nether=dict(structures,fortress=1,bastion=2)
    ow_lux,_,_=dynamic_v3_score(without_nether,names,hub=45,scenic=1,village_spread=1)
    ow,_,_=dynamic_v3_score(without_nether,(),hub=45,scenic=1,village_spread=1)
    assert policy['total']==score==1250
    assert policy['groups']=={'overworld':ow,'luxury_biomes':ow_lux-ow,'nether':score-ow_lux}
    assert policy['groups']=={'overworld':845,'luxury_biomes':265,'nether':140}
    assert policy['sizes']['2048']['calibration_required'] is False
    assert all(policy['sizes'][s]['policy']=='frozen_empirical_count_schedule_v1' for s in ('4096','8192'))
    from seed_search.catalog.realm_evaluation import load_calibration
    active=load_calibration()
    assert active['status']=='active' and active['activation_evidence']['thresholds_frozen_before_expansion']
    assert active['activation_evidence']['original_holdout_qualifiers']=={'4096':0,'8192':0}
    assert active['activation_evidence']['positive_controls']=={'4096':2,'8192':19}
