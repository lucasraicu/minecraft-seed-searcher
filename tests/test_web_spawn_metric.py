"""Spawn radius is an evidence metric, independent of terrain qualification."""
import pytest

from seed_search.web.server import parse_candidate_row


def candidate(point=None, center=None):
    return parse_candidate_row('1', 0, {
        'evaluation_center': center or [0, 0],
        'qualification': 'PREDICTED',
        'spawn_stage': {'coordinates': point, 'status': 'PENDING'},
    })


def test_unknown_spawn_is_not_within_radius():
    row = candidate()
    assert row['spawnDistance'] is None
    assert row['spawnWithin100'] is None
    assert row['baselineStatus'] == 'PREDICTED'


def test_radius_uses_unrounded_distance_and_hub():
    row = candidate([60, 64, 80])
    assert row['spawnDistance'] == 100
    assert row['spawnWithin100'] is True
    row = candidate([100.04, 64, 0])
    assert row['spawnDistance'] == 100
    assert row['spawnWithin100'] is False
    row = candidate([160, 64, 80], [100, 0])
    assert row['spawnWithin100'] is True
    assert row['spawnDistanceToOrigin'] > 100
    assert row['baselineStatus'] == 'PREDICTED'


@pytest.mark.parametrize('point', [[float('nan'), 64, 0], [0, float('inf'), 0], [True, 64, 0], [0, 0]])
def test_invalid_spawn_coordinates_stay_unknown(point):
    row = candidate(point)
    assert row['spawnPoint'] is None
    assert row['spawnDistance'] is None
    assert row['spawnWithin100'] is None
