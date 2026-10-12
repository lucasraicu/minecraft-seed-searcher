"""Independent exhaustive controls for the pilot's capacity/area solver."""
import random

from scripts.pilot_common_centers import rectangle_profiles, point_feasible
from scripts.pilot_possible_stronghold_centers import possible_centers


def brute(groups, profiles, domain):
    x0, z0, x1, z1 = domain
    return {name: [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)
                   if point_feasible(groups, requirements, (x, z))]
            for name, requirements in profiles.items()}


def test_exact_slabs_match_exhaustive_integer_centers_and_capacity():
    rng = random.Random(11102026)
    domain = (-4, -3, 5, 4)
    for _ in range(100):
        groups = {}
        for name in ('a', 'b', 'c'):
            rectangles = []
            for _ in range(rng.randrange(8)):
                x0, x1 = sorted((rng.randrange(-8, 9), rng.randrange(-8, 9)))
                z0, z1 = sorted((rng.randrange(-8, 9), rng.randrange(-8, 9)))
                rectangles.append((x0, z0, x1, z1))
            groups[name] = rectangles
        profiles = {'one': {'a': 1, 'b': 1}, 'capacity': {'a': 3, 'b': 1, 'c': 2}}
        expected = brute(groups, profiles, domain)
        actual = rectangle_profiles(groups, profiles, domain)
        for name, points in expected.items():
            assert actual[name]['area'] == len(points)
            assert actual[name]['fraction'] == len(points) / 80
            assert actual[name]['witness'] == (list(points[0]) if points else None)


def test_individual_presence_does_not_imply_one_common_center():
    groups = {'a': [(-4, -4, -1, 4)], 'b': [(1, -4, 4, 4)]}
    assert rectangle_profiles(groups, {'both': {'a': 1, 'b': 1}}, (-4, -4, 4, 4))['both']['area'] == 0


def test_capacity_retains_distinct_slots_with_identical_clipped_rectangles():
    groups = {'feature': [(-10, -10, 10, 10)] * 4}
    results = rectangle_profiles(groups, {'four': {'feature': 4}, 'five': {'feature': 5}}, (0, 0, 1, 1))
    assert results['four']['area'] == 4
    assert results['five']['area'] == 0


def test_touching_inclusive_rectangles_have_one_shared_center():
    groups = {'a': [(-2, -2, 0, 0)], 'b': [(0, 0, 2, 2)]}
    result = rectangle_profiles(groups, {'both': {'a': 1, 'b': 1}}, (-2, -2, 2, 2))['both']
    assert result['area'] == 1
    assert result['witness'] == [0, 0]


def test_possible_stronghold_centers_include_shifted_villages_and_regional_halo():
    class FakeBackend:
        calls = []
        def attempt(self, name, rx, rz):
            self.calls.append((name, rx, rz))
            return {(0, 0): (1800, 1800), (-1, -1): (-1800, -1800),
                    (1, 1): (5000, 5000)}.get((rx, rz))
    backend = FakeBackend()
    result = possible_centers(backend, [(8, 8), (-1996, -1996), (2003, 2003), (2004, 2004)])
    assert result == [(-2000, -2000), (-1800, -1800), (4, 4), (1800, 1800), (1999, 1999)]
    assert len(backend.calls) == 16
    assert all(name == 'stronghold' for name, _, _ in backend.calls)
