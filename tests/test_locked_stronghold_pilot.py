"""Exact selected-center borders and safe raw gate skip behavior."""
from scripts.pilot_locked_stronghold import exact_bounds, gated_viability
from seed_search.realm.bounds import contains, nether_square, square
import pytest


@pytest.mark.parametrize('center', [(4, 4), (-4, -4), (1999, -2000), (0, 0)])
def test_locked_center_native_bounds_match_fractional_border(center):
    bounds = exact_bounds(center)
    for name, actual in (('overworld', square(center, 1536)), ('nether', nether_square(center, 896))):
        b = bounds[name]
        for x in (b[0]-1, b[0], b[2], b[2]+1):
            for z in (b[1]-1, b[1], b[3], b[3]+1):
                assert contains((x, z), actual) == (b[0] <= x <= b[2] and b[1] <= z <= b[3])


def test_raw_negative_skips_full64_viability_only_for_that_locked_border(monkeypatch):
    class Backend:
        seed = -1
        def nether_structure_pairs(self, bounds):
            raise AssertionError('Raw negative must avoid viability work')
    monkeypatch.setattr('scripts.pilot_locked_stronghold.raw_presence', lambda low, bounds: False)
    assert not gated_viability(Backend(), exact_bounds((-4, -4)))


def test_raw_positive_still_checks_full64_biome_viability(monkeypatch):
    class Backend:
        seed = 12345
        def nether_structure_pairs(self, bounds):
            return {'fortress': ([(0, 0)], [(0, 0)]), 'bastion': ([(1, 1)], [])}
    monkeypatch.setattr('scripts.pilot_locked_stronghold.raw_presence', lambda low, bounds: True)
    assert not gated_viability(Backend(), exact_bounds((4, 4)))
