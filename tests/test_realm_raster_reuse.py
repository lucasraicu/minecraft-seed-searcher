"""Exact sampled-coordinate reuse, with bounded storage and deterministic controls."""
import numpy as np
import pytest

from seed_search.realm.raster import Raster, RasterCache


class Predictor:
    def __init__(self, seed='42', build='reference'):
        self.seed = seed
        self.cache_identity = {'build': build}
        self.queried = []
        self.grid_points = []

    @staticmethod
    def values(xs, zs, nomination=False):
        xs, zs = np.asarray(xs), np.asarray(zs)
        height = (xs*3+zs*7).astype(float) + (100 if nomination else 0)
        height[(xs % 5 == 0)&(zs % 7 == 0)] = np.nan
        biome = (xs*31+zs*17)%53
        return height, biome

    def heights(self, points, vertical_step):
        self.queried.append(points.copy())
        return self.values(points[:, 0], points[:, 1])

    def grid(self, x0, z0, nx, nz, step):
        xx, zz = np.meshgrid(x0+np.arange(nx)*step, z0+np.arange(nz)*step)
        self.grid_points.append(np.column_stack((xx.ravel(), zz.ravel())))
        h, b = self.values(xx, zz, nomination=True)
        return {'approx_height': h, 'biomes': b}


def assert_identical(actual, reference):
    np.testing.assert_array_equal(actual.height, reference.height)
    np.testing.assert_array_equal(actual.biomes, reference.biomes)
    np.testing.assert_array_equal(actual.known, reference.known)
    assert actual.bounds == reference.bounds
    assert actual.resolution == reference.resolution
    assert actual.quality() == reference.quality()


def independent(bounds, resolution, stage='height'):
    return RasterCache().sample(Predictor(), '42', bounds, resolution, stage=stage)


def test_overlapping_window_matches_uncached_all_channels_and_queries_only_missing():
    provider = Predictor(); cache = RasterCache()
    cache.sample(provider, '42', (0, 0, 32, 32), 4)
    actual = cache.sample(provider, '42', (4, 4, 36, 36), 4)
    assert_identical(actual, independent((4, 4, 36, 36), 4))
    assert cache.reused_points == 49
    assert len(provider.queried[1]) == 15
    assert all(x == 32 or z == 32 for x, z in provider.queried[1])
    assert cache.queried_points == 64+15


def test_different_resolutions_reuse_only_their_exact_cartesian_intersection():
    provider = Predictor(); cache = RasterCache()
    cache.sample(provider, '42', (-8, -8, 25, 25), 8)
    actual = cache.sample(provider, '42', (0, -4, 33, 29), 4)
    assert_identical(actual, independent((0, -4, 33, 29), 4))
    assert actual.metadata['sampling_reuse'] == {'exact_points_reused': 16, 'points_queried': 65}
    old = {(x, z) for x, z in provider.queried[0]}
    assert not old.intersection(map(tuple, provider.queried[1]))


def test_lattice_phase_mismatch_does_not_interpolate_neighbor_values():
    provider = Predictor(); cache = RasterCache()
    cache.sample(provider, '42', (0, 0, 32, 32), 8)
    actual = cache.sample(provider, '42', (1, 1, 33, 33), 8)
    assert_identical(actual, independent((1, 1, 33, 33), 8))
    assert cache.reused_points == 0
    assert len(provider.queried[1]) == 16


def test_multiple_cached_tiles_cover_one_larger_lattice_exactly():
    provider = Predictor(); cache = RasterCache()
    cache.sample(provider, '42', (0, 0, 16, 32), 4)
    cache.sample(provider, '42', (16, 0, 32, 32), 4)
    actual = cache.sample(provider, '42', (0, 0, 32, 32), 4)
    assert_identical(actual, independent((0, 0, 32, 32), 4))
    assert len(provider.queried) == 2
    assert actual.metadata['sampling_reuse']['points_queried'] == 0


def test_seed_build_settings_stage_and_provider_kind_are_separate_scopes():
    provider = Predictor(); cache = RasterCache()
    bounds = (0, 0, 16, 16)
    cache.sample(provider, '42', bounds, 4)
    for replacement, seed, settings, stage in (
        (Predictor('43'), '43', {}, 'height'),
        (Predictor(build='other'), '42', {}, 'height'),
        (provider, '42', {'world': 'other'}, 'height'),
        (provider, '42', {}, 'nomination'),
    ):
        actual = cache.sample(replacement, seed, (4, 4, 20, 20), 4, settings=settings, stage=stage)
        assert actual.metadata['sampling_reuse']['exact_points_reused'] == 0
    with pytest.raises(ValueError, match='seed differs'):
        cache.sample(provider, '43', bounds, 4)
    with pytest.raises(ValueError, match='Overworld'):
        cache.sample(provider, '42', bounds, 4, dimension='nether')


def test_lru_eviction_removes_all_coordinate_reuse_payloads():
    provider = Predictor(); cache = RasterCache(maximum_entries=1)
    first = (0, 0, 16, 16); unrelated = (100, 100, 116, 116)
    cache.sample(provider, '42', first, 4)
    cache.sample(provider, '42', unrelated, 4)
    actual = cache.sample(provider, '42', first, 4)
    assert actual.metadata['sampling_reuse']['exact_points_reused'] == 0
    assert len(provider.queried) == 3
    assert len(cache.entries) == len(cache.scopes) == len(cache.sampling_axes) == 1


def test_nomination_overlap_uses_only_2d_grid_and_matches_uncached():
    provider = Predictor(); cache = RasterCache()
    cache.sample(provider, '42', (0, 0, 32, 32), 4, stage='nomination')
    actual = cache.sample(provider, '42', (4, 4, 36, 36), 4, stage='nomination')
    assert_identical(actual, independent((4, 4, 36, 36), 4, 'nomination'))
    assert cache.reused_points == 49
    assert sum(len(points) for points in provider.grid_points) == 64+15
    assert not provider.queried


def test_actual_raster_provider_is_not_reused_even_for_same_bounds():
    class Actual:
        calls = 0
        cache_identity = {'build': 'actual-changing-fluid'}
        def sample_raster(self, seed, bounds, resolution, **kwargs):
            self.calls += 1
            shape = ((bounds[3]-bounds[1]+resolution-1)//resolution, (bounds[2]-bounds[0]+resolution-1)//resolution)
            return Raster(bounds, resolution, np.full(shape, self.calls), water=np.full(shape, self.calls%2 == 0), metadata={'source': 'actual'})
    provider = Actual(); cache = RasterCache()
    first = cache.sample(provider, '42', (0, 0, 16, 16), 4)
    second = cache.sample(provider, '42', (0, 0, 16, 16), 4)
    third = cache.sample(provider, '42', (4, 4, 20, 20), 4)
    assert provider.calls == 3
    assert first.height[0, 0] == 1 and second.height[0, 0] == 2 and third.height[0, 0] == 3
    assert not first.water.any() and second.water.all()
    assert cache.reused_points == cache.queried_points == 0
    assert not cache.sampling_axes


@pytest.mark.parametrize('failure_metadata', [
    {'failed': True}, {'unsupported': True}, {'reason': 'Budget exhausted'},
])
def test_provider_missing_response_without_actual_source_can_recover(failure_metadata):
    class Recovering:
        calls = 0
        cache_identity = {'build': 'recoverable-actual'}
        def sample_raster(self, seed, bounds, resolution, **kwargs):
            self.calls += 1
            shape = ((bounds[3]-bounds[1]+resolution-1)//resolution,
                     (bounds[2]-bounds[0]+resolution-1)//resolution)
            if self.calls == 1:
                return Raster(bounds, resolution, np.full(shape, np.nan), metadata=failure_metadata)
            return Raster(bounds, resolution, np.full(shape, 80.),
                          water=np.zeros(shape, bool), metadata={'source': 'actual'})
    provider = Recovering(); cache = RasterCache()
    first = cache.sample(provider, '42', (0, 0, 16, 16), 4)
    recovered = cache.sample(provider, '42', (0, 0, 16, 16), 4)
    assert provider.calls == 2
    assert not first.known.any()
    assert recovered.known.all()
    assert recovered.metadata['source'] == 'actual'
    assert cache.hits == 0


def test_fractional_bounds_are_rejected_instead_of_rounding_to_neighbor_coordinates():
    with pytest.raises(ValueError, match='integer block'):
        RasterCache().sample(Predictor(), '42', (-.5, 0, 15.5, 16), 4)
