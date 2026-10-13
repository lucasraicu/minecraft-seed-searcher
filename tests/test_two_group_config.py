"""The new policy is versioned separately from existing origin checkpoints."""
import copy
from pathlib import Path

import pytest
import yaml

from seed_search.realm.config import (
    ORIGIN_REVISION, TWO_GROUP_REVISION, origin_blueprint_config,
    two_group_blueprint_config, origin_policy, validate_config,
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


def test_unimplemented_v2_screening_fails_explicitly():
    from seed_search.realm.native_batch import Prototype
    from seed_search.realm.blueprint import evaluate_seed
    cfg=two_group_blueprint_config()
    with pytest.raises(ValueError,match='hard-floor enforcement'):
        Prototype(None,cfg)
    with pytest.raises(ValueError,match='hard-floor enforcement'):
        evaluate_seed(0,0,cfg)
