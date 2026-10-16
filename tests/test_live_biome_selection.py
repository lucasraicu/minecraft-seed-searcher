"""Live v2 palette selection preserves stable native surface/cave bits."""
import copy
import pytest

from test_dynamic_v2_scoring import native_v2, DynamicV2FixtureBackend
from seed_search.realm.config import dynamic_v2_blueprint_config, dynamic_blueprint_config, validate_config, baseline_requirements
from seed_search.realm.blueprint import PALETTE, evaluate_seed
from seed_search.realm.native_batch import Prototype, semantic_record
from seed_search.web.server import SweepManager


@pytest.mark.parametrize('family', list(PALETTE))
def test_unselected_missing_family_no_longer_rejects(native_v2, family):
    cfg=dynamic_v2_blueprint_config()
    slot=13+list(PALETTE).index(family)
    with native_v2.sweep([456],fixtures=[(0,0,slot)],retention='survivors') as batch:
        assert batch.retained_records()==[]
    cfg['biomes']['required_families'].remove(family)
    native=Prototype(native_v2.directory,cfg)
    with native.sweep([456],fixtures=[(0,0,slot)],retention='survivors') as batch:
        rows=batch.retained_records()
        assert rows and rows[0]['anchors']
        assert family not in rows[0]['anchors'][0]['biomes']['required_families']
        assert rows[0]['anchors'][0]['biomes']['missing_families']==[]
    assert baseline_requirements(cfg)==31


@pytest.mark.parametrize('selected', [[], ['deep_dark'], ['forest','lush_caves'], ['deep_dark','plains']])
def test_subset_matches_independent_selector(native_v2,selected):
    cfg=dynamic_v2_blueprint_config();cfg['biomes']['required_families']=selected
    native=Prototype(native_v2.directory,cfg)
    with native.sweep([456],fixtures=[(0,0,-1)]) as batch:
        actual=batch.records()[0]
    reference=evaluate_seed(0,456,cfg,backend_factory=lambda _:DynamicV2FixtureBackend(cfg=cfg))
    assert semantic_record(actual)==semantic_record(reference)
    assert actual['anchors'][0]['biomes']['required_families']==selected


@pytest.mark.parametrize('bad', [['unsupported'],['plains','plains'],[None], 'plains',None])
def test_invalid_selection_rejected(bad):
    cfg=dynamic_v2_blueprint_config();cfg['biomes']['required_families']=bad
    with pytest.raises(ValueError):validate_config(cfg)


def test_historical_palette_stays_fixed():
    cfg=dynamic_blueprint_config();cfg['biomes']['required_families']=[]
    with pytest.raises(ValueError):validate_config(cfg)


def test_preview_carries_exact_selection():
    for selected in ([],['forest','deep_dark']):
        result=SweepManager().preview_sweep(biomes=selected)
        assert result['ok']
        assert result['effectiveConfig']['biomes']['required_families']==selected
        assert result['launch']['controls']['biomes']==selected
