"""Synthetic controls for independent, evidence-graded Realm geometry."""
import numpy as np
import pytest

from seed_search.realm.raster import Raster, RasterCache
from seed_search.realm.terrain import (evaluate_v1, evaluate_v2, propose_centers,
                                     biome_fit_score, run_terrain)


def synthetic(kind='island', resolution=8, bounds=(-1024, -1024, 1025, 1025), actual=False):
    xx, zz = np.meshgrid(np.arange(bounds[0], bounds[2], resolution), np.arange(bounds[1], bounds[3], resolution))
    radius = np.hypot(xx, zz)
    water = radius > 160
    height = np.where(water, 50., 85.)
    if kind == 'lake':
        water = (radius > 160)&(radius < 400)
        height = np.where(water, 95., 125.)  # Freshwater above sea level.
    if kind in {'peninsula', 'bridge'}:
        bridge = (xx >= 0)&(np.abs(zz) <= (30 if kind == 'peninsula' else 0))
        water &= ~bridge
        height = np.where(water, 50., 85.)
    if kind in {'valley', 'jagged', 'spikes', 'water_valley'}:
        water = np.zeros_like(radius, bool)
        height = np.full(radius.shape, 180.)
        if kind == 'jagged':
            height = height+np.where(radius < 180, 45*np.sin(xx/12)*np.cos(zz/12), 0)
        if kind == 'spikes':
            for angle in np.arange(32)*2*np.pi/32:
                mask = np.hypot(xx-500*np.cos(angle), zz-500*np.sin(angle)) < 12
                height[mask] = 250
        else:
            height[(radius >= 500)&(radius <= 620)] = 250.
        if kind == 'water_valley':
            water = radius < 300
    metadata = {'source': 'actual' if actual else 'prediction', 'water_evidence': 'actual_blocks',
                'natural_ground_evidence': 'verified_natural'}
    return Raster(bounds, resolution, height, water=water, natural_ground=np.ones_like(water), metadata=metadata)


def test_island_qualifies_without_ocean_biome_or_mountains():
    result = evaluate_v1(synthetic(), (0, 0))
    assert result['geometry_pass']
    assert result['qualification'] == 'PREDICTED'
    assert result['metrics']['water_rays'] == 32
    assert result['metrics']['island_area'] >= 12000
    assert result['border_fit']['state'] == 'unknown'
    assert not result['border_fit']['complete']
    assert result['metrics']['footprint_policy'].startswith('minimum-local-water-belt')
    # An open ocean supplies a minimum local belt, not a complete formation-fit claim.
    assert result['border_fit']['footprint'][2] < 400


def test_high_elevation_lake_uses_actual_water_channel():
    raster = synthetic('lake')
    assert raster.height.min() > 63
    assert evaluate_v1(raster, (0, 0))['geometry_pass']


@pytest.mark.parametrize('kind', ['peninsula', 'bridge'])
def test_peninsula_and_thin_bridge_are_not_isolated(kind):
    result = evaluate_v1(synthetic(kind), (0, 0))
    assert not result['geometry_pass']
    assert not result['metrics']['separate_land_component']
    assert result['qualification'] == 'PENDING'


@pytest.mark.parametrize('kind', ['valley', 'jagged', 'water_valley'])
def test_relative_continuous_ridges_allow_any_floor(kind):
    result = evaluate_v2(synthetic(kind), (0, 0))
    assert result['geometry_pass'], result['reasons']
    assert result['metrics']['ridge_rays'] == 32
    assert result['metrics']['relative_relief'] >= 55
    assert result['metrics']['interior_elevation'] > 150
    assert result['metrics']['geometry_weights'] == {'enclosure': .875, 'access': .125}
    assert 'floor' not in result['metrics']['geometry_weights']


def test_isolated_spikes_do_not_supply_enclosure():
    result = evaluate_v2(synthetic('spikes'), (0, 0))
    assert not result['geometry_pass']
    assert result['metrics']['ridge_rays'] == 0
    assert result['metrics']['largest_gap_rays'] == 32


def test_missing_coverage_stays_pending_and_border_unknown():
    raster = synthetic()
    raster.known[0, 0] = False
    result = evaluate_v1(raster, (0, 0))
    assert result['geometry_pass']
    assert result['qualification'] == 'PENDING'
    assert result['border_fit']['state'] == 'unknown'


def test_outside_formation_retained_with_expansion_size():
    result = evaluate_v1(synthetic(), (0, 0), bounds=(-180, -180, 180, 180), stronghold=(0, 0))
    assert result['geometry_pass']
    assert result['border_fit']['state'] == 'outside'
    assert result['border_fit']['overflow']['east'] > 0
    assert result['border_fit']['minimum_centered_size'] > 360


def test_variants_independent_on_same_map():
    raster = synthetic('water_valley')
    assert not evaluate_v1(raster, (0, 0))['geometry_pass']
    assert evaluate_v2(raster, (0, 0))['geometry_pass']


def test_actual_certification_requires_all_natural_ground_and_block_resolution():
    assert synthetic(actual=True).quality() == 'PARTIAL'
    raster = Raster((0, 0, 2, 2), 1, np.ones((2, 2)), water=np.zeros((2, 2), bool),
                    natural_ground=np.ones((2, 2), bool),
                    metadata={'source': 'actual', 'water_evidence': 'actual_blocks', 'natural_ground_evidence': 'verified_natural'})
    assert raster.quality() == 'VERIFIED'
    raster.metadata['natural_ground_evidence'] = 'structure_mask_unverified'
    assert raster.quality() == 'PARTIAL'


def test_center_grid_covers_off_grid_bounds_and_far_from_stronghold():
    bounds = (-1341, -1339, 1347, 1349)
    raster = synthetic(bounds=(-1536, -1536, 1536, 1536), resolution=128)
    centers = propose_centers(raster, bounds, 'v1')
    assert (-1341, -1339) in centers
    assert (1283, 1285) in centers
    assert all(bounds[0] <= x < bounds[2] and bounds[1] <= z < bounds[3] for x, z in centers)
    assert any(x % 8 for x, _ in centers)


def test_savanna_neutral_without_dilution():
    preferred = ['forest', 'cherry_grove']
    assert biome_fit_score(['forest'], preferred) == 50
    assert biome_fit_score(['forest', 'savanna', 'savanna_plateau'], preferred) == 50


def test_cache_identity_lattice_seed_and_stage():
    class Provider:
        cache_identity = {'build': 'test', 'water': 'actual'}
        calls = 0
        def sample_raster(self, seed, bounds, resolution, stage, dimension, settings):
            self.calls += 1
            return synthetic(resolution=resolution, bounds=bounds)
    provider = Provider(); cache = RasterCache()
    args = (provider, '9223372036854775807', (-32, -32, 32, 32), 8)
    first = cache.sample(*args)
    assert cache.sample(*args) is first
    cache.sample(*args, stage='nomination')
    cache.sample(provider, '-1', (-32, -32, 32, 32), 8)
    assert (cache.hits, cache.misses, provider.calls) == (1, 3, 3)


def test_runner_persists_each_variant_and_does_not_mutate_baseline():
    class Store:
        candidate = dict(id='42:0:0', seed='42', stronghold=[0, 0], bounds=[-128, -128, 128, 128], qualification='PREDICTED', baseline_score=20)
        records = {}
        def iter_candidates(self, statuses): yield dict(self.candidate)
        def get_variant(self, cid, variant, center): return self.records.get((cid, variant, tuple(center)))
        def upsert_variant(self, cid, variant, center, result): self.records[cid, variant, tuple(center)] = result
    class Provider:
        stages = []
        def sample_raster(self, seed, bounds, resolution, stage, dimension, settings):
            self.stages.append(stage)
            return synthetic(resolution=resolution, bounds=bounds)
    store = Store(); provider = Provider()
    cfg = {'terrain': {'center_spacing': 128, 'max_refinements': 1, 'resolutions': [128, 64]}}
    result = run_terrain(store, cfg, provider_factory=lambda seed: provider)
    assert result['candidates'] == 1
    assert {key[1] for key in store.records} == {'v1', 'v2'}
    assert store.candidate['qualification'] == 'PREDICTED'
    assert provider.stages[0] == 'nomination'
    resumed = run_terrain(store, cfg, provider_factory=lambda seed: provider)
    assert resumed['results'] == 0
    assert resumed['resumed'] == 2


def test_actual_block_geometry_can_certify_synthetic_control():
    raster = synthetic('lake', bounds=(-450, -450, 451, 451), resolution=1, actual=True)
    result = evaluate_v1(raster, (0, 0))
    assert result['geometry_pass']
    assert result['qualification'] == 'VERIFIED'
    assert result['border_fit']['state'] == 'within'


def test_actual_missing_water_channel_cannot_certify_geometry():
    raster = synthetic(actual=True)
    raster.water = None
    result = evaluate_v1(raster, (0, 0))
    assert result['qualification'] == 'PENDING'


def test_disconnected_water_sectors_do_not_form_common_enclosure():
    raster = synthetic('lake')
    xx, zz = raster.coordinates()
    separators = (np.abs(xx) < 16) | (np.abs(zz) < 16)
    raster.water &= ~separators
    result = evaluate_v1(raster, (80, 80))
    assert not result['geometry_pass']


def test_fractional_edge_cell_area_and_invalid_resolution():
    raster = Raster((-1, -2, 4, 3), 4, np.ones((2, 2)))
    assert raster.cell_areas().sum() == 25
    assert raster.mask_bounds(np.ones((2, 2), bool)) == [-1, -2, 4, 3]
    with pytest.raises(ValueError): Raster((0, 0, 4, 4), 1.5, np.ones((3, 3)))


def test_zero_budget_leaves_tasks_pending_without_provider_calls():
    class Store:
        def iter_candidates(self, statuses): raise AssertionError('No scheduling with zero budget')
    result = run_terrain(Store(), {'terrain': {'maximum_refinements_per_anchor': 0}})
    assert result['results'] == 0


def test_real_checkpoint_marks_both_tasks_complete_and_resume_avoids_generation(tmp_path,monkeypatch):
    monkeypatch.setattr('seed_search.realm.terrain.propose_centers',lambda *args: [(0,0)])
    from seed_search.realm.store import RealmStore
    class Provider:
        def sample_raster(self, seed, bounds, resolution, stage, dimension, settings):
            return synthetic('lake',resolution=resolution,bounds=bounds)
    cfg = {'terrain': {'center_spacing': 128, 'maximum_refinements_per_anchor': 1, 'resolutions': [128, 64]}}
    store = RealmStore(tmp_path/'run', identity={'config': cfg})
    try:
        store.configure_range(0, 1)
        store.claim_range('test')
        candidate = dict(id='42:0:0', seed='42', stronghold=[0, 0], bounds={'overworld': [-128, -128, 128, 128]}, qualification='PREDICTED', baseline_score=60)
        store.complete_range(0, 1, [dict(index=0, seed='42', anchors=[candidate])])
        result = run_terrain(store, cfg, provider_factory=lambda seed: Provider(), provider_identity={'fixture': 'synthetic-v1'})
        assert result['results'] == 2
        assert store.get_variant_task_status(candidate['id'], 'v1') == 'complete'
        assert store.get_variant_task_status(candidate['id'], 'v2') == 'complete'
        def forbidden(seed): raise AssertionError('Complete tasks should not instantiate providers')
        resumed = run_terrain(store, cfg, provider_factory=forbidden, provider_identity={'fixture': 'synthetic-v1'})
        assert resumed['resumed_tasks'] == 2
        assert list(store.iter_candidates())[0] == candidate
        assert all(row['result']['baseline_quality'] == 100 for row in store.iter_variants())
    finally:
        store.close()


def test_effective_diameter_uses_area_without_hard_elongation_gate():
    bounds = (-1024, -1024, 1025, 1025); step = 8
    xx, zz = np.meshgrid(np.arange(bounds[0], bounds[2], step), np.arange(bounds[1], bounds[3], step))
    land = (xx*xx/430**2+zz*zz/70**2) <= 1
    raster = Raster(bounds, step, np.where(land, 85., 50.), water=~land)
    result = evaluate_v1(raster, (0, 0))
    assert result['metrics']['hull_span'] > 750
    assert 250 <= result['metrics']['equivalent_diameter'] <= 750
    assert result['geometry_pass']
    assert result['metrics']['diameter'] == pytest.approx(2*np.sqrt(result['metrics']['island_area']/np.pi))


def test_lake_fit_reaches_opposite_shore_and_overflow_is_not_capped_at_ideal_width():
    result = evaluate_v1(synthetic('lake'), (0, 0), bounds=(-300, -300, 300, 300))
    assert result['geometry_pass']
    assert result['metrics']['measured_local_belt_width'] > 100
    assert result['border_fit']['state'] == 'outside'
    assert result['border_fit']['footprint'][2] >= 400
    assert result['border_fit']['complete']


@pytest.mark.parametrize('halfwidth', [300, 1344])
def test_wide_closed_lake_without_observed_opposite_shores_cannot_claim_complete_fit(halfwidth):
    raster = synthetic('lake', bounds=(-1280, -1280, 1281, 1281))
    xx, zz = raster.coordinates()
    radius = np.hypot(xx, zz)
    raster.water = (radius > 160)&(radius < 1100)
    result = evaluate_v1(raster, (0, 0), bounds=(-halfwidth, -halfwidth, halfwidth, halfwidth))
    assert result['geometry_pass']
    assert result['metrics']['enclosing_water_body_closed']
    assert result['metrics']['opposite_shore_rays'] == 0
    assert not result['metrics']['enclosing_opposite_shores_resolved']
    assert result['metrics']['measured_local_belt_width'] > 600
    assert not result['border_fit']['complete']
    assert result['border_fit']['state'] == ('outside' if halfwidth == 300 else 'unknown')
    assert result['border_fit']['minimum_is_lower_bound']
    assert 'resolve complete formation footprint' in result['pending_work']


def test_algorithm_identity_blocks_silent_resume_but_weight_rescore_has_separate_identity(tmp_path):
    from seed_search.realm.store import RealmStore
    from seed_search.realm.terrain import terrain_algorithm_identity, terrain_scoring_identity
    cfg = {'terrain': {'maximum_refinements_per_anchor': 0}}
    store = RealmStore(tmp_path/'run', identity={})
    try:
        run_terrain(store, cfg)
        assert store.get_state('terrain_algorithm_identity') == terrain_algorithm_identity(cfg)
        altered = {'terrain': {'maximum_refinements_per_anchor': 1}}
        with pytest.raises(ValueError, match='identity changed'): run_terrain(store, altered)
        weighted = {**cfg, 'scoring': {'geometry_weight': .7, 'biome_fit_weight': .2, 'baseline_weight': .1}}
        assert terrain_algorithm_identity(weighted) == terrain_algorithm_identity(cfg)
        with pytest.raises(ValueError, match='explicitly rescore'): run_terrain(store, weighted)
        # The explicit rescore caller acknowledges that the persisted metrics were rescored.
        store.set_state('terrain_scoring_identity', terrain_scoring_identity(weighted))
        run_terrain(store, weighted)
    finally:
        store.close()


def test_local_lake_footprint_excludes_unrelated_long_water_arm():
    raster = synthetic('lake')
    xx, zz = raster.coordinates()
    arm = (xx >= 350)&(xx < 900)&(np.abs(zz) < 8)
    raster.water |= arm
    result = evaluate_v1(raster, (0, 0))
    assert result['geometry_pass']
    assert result['metrics']['enclosing_water_component_bounds'][2] >= 900
    assert result['border_fit']['footprint'][2] < 500
    # The branch stays outside the measured local belt, but unresolved ray
    # endpoints must prevent that belt from certifying a complete formation.
    assert not result['border_fit']['complete']
    assert result['border_fit']['state'] == 'unknown'
    assert 'outer extent unresolved' in result['metrics']['footprint_policy']


def test_bounded_resume_advances_past_completed_pairs(tmp_path,monkeypatch):
    monkeypatch.setattr('seed_search.realm.terrain.propose_centers',lambda *args: [(0,0)])
    from seed_search.realm.store import RealmStore
    calls = []
    class Provider:
        def sample_raster(self, seed, bounds, resolution, stage, dimension, settings):
            return synthetic('lake',resolution=resolution,bounds=bounds)
    def factory(seed):
        calls.append(seed)
        return Provider()
    cfg = {'terrain': {'center_spacing': 128, 'maximum_refinements_per_anchor': 1, 'resolutions': [128, 64]}}
    store = RealmStore(tmp_path/'run', identity={})
    try:
        store.configure_range(0, 2); store.claim_range('test')
        rows = [dict(index=i, seed=str(42+i), anchors=[dict(id=f'{42+i}:0:0', seed=str(42+i), stronghold=[0, 0], bounds={'overworld': [-128, -128, 128, 128]}, qualification='PREDICTED', baseline_score=60)]) for i in range(2)]
        store.complete_range(0, 2, rows)
        first = run_terrain(store, cfg, limit=1, provider_factory=factory, provider_identity={'fixture': 'synthetic-v1'})
        second = run_terrain(store, cfg, limit=1, provider_factory=factory, provider_identity={'fixture': 'synthetic-v1'})
        third = run_terrain(store, cfg, limit=1, provider_factory=factory, provider_identity={'fixture': 'synthetic-v1'})
        assert first['candidates'] == second['candidates'] == 1
        assert first['results'] == second['results'] == 2
        assert third['candidates'] == third['results'] == 0
        assert calls == ['42', '43']
        assert {row['candidate_id'] for row in store.iter_variants()} == {'42:0:0', '43:0:0'}
    finally:
        store.close()


def test_sampling_extent_follows_configured_merged_thresholds():
    class Store:
        def iter_candidates(self, statuses):
            yield dict(id='42:0:0', seed='42', stronghold=[0, 0], bounds=[-128, -128, 128, 128], qualification='PREDICTED', baseline_score=20)
        def get_variant(self, *args): return None
        def upsert_variant(self, *args): pass
    class Provider:
        calls = []
        def sample_raster(self, seed, bounds, resolution, stage, dimension, settings):
            self.calls.append((bounds, resolution, stage))
            return synthetic(resolution=resolution, bounds=bounds)
    provider = Provider()
    cfg = {'terrain': {'center_spacing': 128, 'maximum_refinements_per_anchor': 1, 'resolutions': [128, 64],
                       'v1': {'diameter_max': 1900, 'ideal_water_width': 300},
                       'v2': {'distance_max': 1600, 'ridge_support_width': 64}}}
    run_terrain(Store(), cfg, provider_factory=lambda seed: provider)
    expected_extent = max(1900+300, 1600+8*64)
    nominal = provider.calls[0]
    assert nominal[0] == (-128-expected_extent-128-16, -128-expected_extent-128-16,
                          128+expected_extent+128+16, 128+expected_extent+128+16)
    for bounds, resolution, stage in provider.calls:
        if stage == 'height':
            assert bounds[2]-bounds[0] == 2*(expected_extent+2*resolution+16)+1


def broad_ridge(outer_radius, extent):
    step = 8; bounds = (-extent, -extent, extent+1, extent+1)
    xx, zz = np.meshgrid(np.arange(-extent, extent+1, step), np.arange(-extent, extent+1, step))
    radial = np.hypot(xx, zz)
    return Raster(bounds, step, np.where((radial >= 500)&(radial <= outer_radius), 250., 180.), water=np.zeros_like(radial, bool))


def test_v2_full_supporting_ridge_extent_exceeds_nomination_annulus():
    result = evaluate_v2(broad_ridge(1100, 1280), (0, 0), bounds=(-900, -900, 900, 900))
    assert result['geometry_pass']
    assert result['border_fit']['state'] == 'outside'
    assert result['border_fit']['complete']
    assert result['border_fit']['footprint'][2] >= 1100
    assert result['border_fit']['minimum_centered_size'] >= 2200
    assert not result['metrics']['supporting_ridges_truncated']


@pytest.mark.parametrize('halfwidth, expected', [(1344, 'unknown'), (900, 'outside')])
def test_v2_support_continuing_beyond_local_halo_cannot_claim_full_fit(halfwidth, expected):
    result = evaluate_v2(broad_ridge(1400, 1536), (0, 0), bounds=(-halfwidth, -halfwidth, halfwidth, halfwidth))
    assert result['geometry_pass']
    assert result['border_fit']['state'] == expected
    assert not result['border_fit']['complete']
    assert result['border_fit']['minimum_is_lower_bound']
    assert result['metrics']['supporting_ridges_truncated']
    assert 'resolve complete formation footprint' in result['pending_work']
