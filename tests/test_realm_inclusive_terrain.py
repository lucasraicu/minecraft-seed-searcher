"""Historical island/mountain controls and the active coastal profile boundary."""
from pathlib import Path

import numpy as np
import pytest
import yaml

from seed_search.realm.config import origin_blueprint_config, river_blueprint_config, locked_blueprint_config, blueprint_config, default_config, validate_config
from seed_search.realm.raster import Raster
from seed_search.realm.terrain import evaluate_v1, evaluate_v2, V1, V2


def grid(bounds=(-768, -768, 768, 768), resolution=8):
    xx, zz = np.meshgrid(np.arange(bounds[0], bounds[2], resolution),
                         np.arange(bounds[1], bounds[3], resolution))
    return bounds, resolution, xx, zz


def island(kind):
    bounds, step, xx, zz = grid()
    land = np.hypot(xx, zz) <= (160 if kind in ('small', 'archipelago') else 400)
    if kind == 'irregular':
        land = (xx / 600) ** 2 + (zz / 180) ** 2 <= 1
    if kind == 'archipelago':
        for x, z in ((-500, 0), (500, 0), (0, -500), (0, 500)):
            land |= np.hypot(xx - x, zz - z) <= 130
    if kind == 'peninsula':
        land |= (xx >= 0) & (np.abs(zz) <= 16)
    return Raster(bounds, step, np.where(land, 85., 50.), water=~land)


def mountains(kind, resolution=8):
    bounds, step, xx, zz = grid((-896, -896, 897, 897), resolution)
    radius = np.hypot(xx, zz)
    angle = np.degrees(np.arctan2(zz, xx)) % 360
    height = np.full(xx.shape, 100.)
    raised = np.zeros(xx.shape, bool)
    if kind in ('separate', 'rough', 'spikes'):
        mountain_radius = 12 if kind == 'spikes' else 135
        for bearing in np.arange(8) * 2 * np.pi / 8:
            raised |= np.hypot(xx - 420 * np.cos(bearing),
                              zz - 420 * np.sin(bearing)) <= mountain_radius
        if kind == 'rough':
            height += np.where(radius < 180, 35 * np.sin(xx / 12) * np.cos(zz / 12), 0)
    elif kind == 'open_pass':
        raised = (radius >= 350) & (radius <= 470) & (angle >= 90)
    elif kind == 'one_side':
        raised = (radius >= 350) & (radius <= 470) & (angle < 120)
    elif kind == 'gentle':
        height += radius / 100
    elif kind == 'flat':
        pass
    else:
        raise ValueError(kind)
    height[raised] = 145
    return Raster(bounds, step, height, water=np.zeros(xx.shape, bool))


def test_default_and_explicit_active_profiles_have_same_terrain_preferences():
    from seed_search.realm.cli import load
    cfg = load(None)
    explicit = yaml.safe_load((Path(__file__).parents[1] / 'config/realm.yaml').read_text())
    assert cfg['terrain']['variants'] == explicit['terrain']['variants'] == []
    for profile in (cfg, explicit):
        validate_config(profile)
        assert 'v1' not in profile['terrain']
        assert 'v2' not in profile['terrain']


def test_historical_default_preserves_island_and_mountain_preferences():
    cfg = default_config()
    validate_config(cfg)
    assert cfg['terrain']['variants'] == ['v1', 'v2']
    assert cfg['terrain']['v1']['area'] == 250000
    assert cfg['terrain']['v2']['enclosure_policy'] == 'surrounding_mountains'


@pytest.mark.parametrize('kind', ['large', 'irregular'])
def test_large_non_circular_main_islands_are_accepted(kind):
    result = evaluate_v1(island(kind), (0, 0), thresholds=default_config()['terrain']['v1'])
    assert result['geometry_pass'], result['reasons']
    assert result['metrics']['island_area'] >= 250000
    if kind == 'irregular':
        assert result['metrics']['hull_span'] > 1000
        assert result['metrics']['equivalent_diameter'] < 800


@pytest.mark.parametrize('kind', ['small', 'archipelago', 'peninsula'])
def test_small_island_disconnected_total_and_land_bridge_do_not_pass(kind):
    raster = island(kind)
    result = evaluate_v1(raster, (0, 0), thresholds=default_config()['terrain']['v1'])
    assert not result['geometry_pass']
    if kind == 'archipelago':
        assert raster.cell_areas()[~raster.water_mask()].sum() > 250000
        assert result['metrics']['island_area'] < 100000


@pytest.mark.parametrize('kind', ['separate', 'rough', 'open_pass'])
@pytest.mark.parametrize('resolution', [8, 16, 32])
def test_substantial_surrounding_mountains_and_open_passes_are_accepted(kind, resolution):
    result = evaluate_v2(mountains(kind, resolution), (0, 0),
                         thresholds=default_config()['terrain']['v2'])
    assert result['geometry_pass'], result['reasons']
    assert not result['metrics']['ridge_continuity_policy']['arc_shape_required']
    if kind == 'rough':
        assert result['metrics']['interior_roughness'] > 10


@pytest.mark.parametrize('kind', ['flat', 'gentle', 'one_side', 'spikes'])
def test_inclusive_policy_still_requires_substantial_surrounding_relief(kind):
    result = evaluate_v2(mountains(kind), (0, 0), thresholds=default_config()['terrain']['v2'])
    assert not result['geometry_pass']


def test_legacy_continuous_arc_policy_is_still_selectable():
    raster = mountains('separate')
    assert not evaluate_v2(raster, (0, 0), thresholds=V2)['geometry_pass']
    assert evaluate_v2(raster, (0, 0), thresholds=default_config()['terrain']['v2'])['geometry_pass']
    # Historical low-level controls retain their original size preference.
    assert evaluate_v1(island('small'), (0, 0), thresholds=V1)['geometry_pass']


def test_unknown_coverage_is_not_promoted_by_broader_preferences():
    raster = mountains('separate')
    raster.known[100, 100] = False
    result = evaluate_v2(raster, (0, 0), thresholds=default_config()['terrain']['v2'])
    assert result['qualification'] == 'PENDING'
    assert not result['border_fit']['complete']


def test_enclosure_policy_validation_and_historical_fallback():
    cfg = default_config()
    cfg['terrain']['v2']['enclosure_policy'] = 'anything'
    with pytest.raises(ValueError, match='enclosure_policy'):
        validate_config(cfg)
    cfg['terrain']['v2'] = {k: v for k, v in V2.items() if k != 'enclosure_policy'}
    validate_config(cfg)
    result = evaluate_v2(mountains('separate'), (0, 0), thresholds=cfg['terrain']['v2'])
    assert result['metrics']['ridge_continuity_policy']['arc_shape_required']
