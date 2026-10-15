"""Marine counts are strict v3 predictor requirements; v2 stays historical."""
from pathlib import Path

import pytest
import yaml

from seed_search.realm.config import (
    TWO_GROUP_MARINE_REVISION, marine_baseline_blueprint_config,
    two_group_blueprint_config, validate_config,
)
from seed_search.realm.native_batch import Prototype, semantic_record


@pytest.fixture(scope='module')
def native_build(tmp_path_factory):
    from scripts.build_blueprint_batch import build
    path=tmp_path_factory.mktemp('marine-baseline-native')
    build(path)
    return path


def test_current_file_and_policy_have_strict_marine_counts():
    cfg=yaml.safe_load(Path('config/realm_2048_marine.yaml').read_text())
    validate_config(cfg)
    assert cfg['screening_revision']==TWO_GROUP_MARINE_REVISION
    assert cfg['structures']['hard_floors']['monument']==1
    assert cfg['structures']['hard_floors']['shipwreck']==3
    assert cfg['structures']['deferred_until_coastal_terrain']==[]
    for name in ('stronghold','monument','shipwreck'):
        altered=marine_baseline_blueprint_config()
        altered['structures']['minimum_counts'][name]-=1
        with pytest.raises(ValueError,match='strict target'):
            validate_config(altered)


@pytest.mark.parametrize('missing,reason',[(3,'monument'),(8,'shipwreck')])
def test_marine_misses_reject_even_with_flexible_budget(native_build,missing,reason):
    prototype=Prototype(native_build,marine_baseline_blueprint_config())
    with prototype.sweep([1],fixtures=[(0,0,missing)],complete=True) as batch:
        direct=batch.records()[0]
        replay=batch.records(adapter='replay')[0]
        assert semantic_record(direct)==semantic_record(replay)
        anchor=direct['anchors'][0]
        assert anchor['qualification']=='PENDING'
        assert anchor['marine_stage']['status']=='PENDING'
        assert anchor['fatal_reasons']==['floor_'+reason]
        assert anchor['deficit_categories']==[]
        assert anchor['pending_reasons']==['count_'+reason]
        assert anchor['required_structures'][reason]['count_is_complete']
    with prototype.sweep([1],fixtures=[(0,0,missing)],retention='survivors') as batch:
        assert batch.pointer.result_count==0


def test_survivor_has_full_marine_inventory_and_legacy_v2_stays_deferred(native_build):
    current=Prototype(native_build,marine_baseline_blueprint_config())
    with current.sweep([1],fixtures=[(0,0,-1)],retention='survivors') as batch:
        anchor=batch.retained_records()[0]['anchors'][0]
        assert anchor['qualification']=='PREDICTED'
        assert anchor['marine_stage']['status']=='PREDICTED'
        assert anchor['deferred_requirements']==[]
        assert all(anchor['required_structures'][name]['count_is_complete'] for name in ('monument','shipwreck'))
        assert anchor['retention']['requirements_total']==26
    legacy=Prototype(native_build,two_group_blueprint_config())
    with legacy.sweep([1],fixtures=[(0,0,3)],retention='survivors') as batch:
        anchor=batch.retained_records()[0]['anchors'][0]
        assert anchor['qualification']=='PREDICTED'
        assert anchor['marine_stage']['status']=='DEFERRED'
        assert anchor['retention']['requirements_total']==24


def test_flexible_deficit_keeps_complete_marine_evidence_and_replay_parity(native_build):
    prototype=Prototype(native_build,marine_baseline_blueprint_config())
    with prototype.sweep([1],fixtures=[(0,0,4)]) as batch:
        direct=batch.records()[0]
        replay=batch.records(adapter='replay')[0]
        assert semantic_record(direct)==semantic_record(replay)
        anchor=direct['anchors'][0]
        assert anchor['qualification']=='PREDICTED'
        assert anchor['deficit_categories']==['ancient_city']
        assert all(anchor['required_structures'][name]['count_is_complete'] for name in ('monument','shipwreck'))


@pytest.mark.parametrize('slot', [3,8])
def test_native_rejects_malformed_marine_policy(native_build,slot):
    prototype=Prototype(native_build,marine_baseline_blueprint_config())
    prototype.policy.goals[slot]+=1
    with pytest.raises(RuntimeError,match='policy error'):
        prototype.sweep([1],fixtures=[(0,0,-1)])


def test_stronghold_target_is_not_silently_ignored():
    cfg=marine_baseline_blueprint_config()
    cfg['structures']['minimum_counts']['stronghold']=2
    with pytest.raises(ValueError,match='strict target'):
        validate_config(cfg)
