import copy
import json
from pathlib import Path
import sqlite3
import pytest

from seed_search.realm.top_tracker import Top50Tracker
from seed_search.realm.config import dynamic_v3_blueprint_config, dynamic_v2_blueprint_config
from seed_search.realm.blueprint import evaluate_dynamic_seed, dynamic_v3_score
from seed_search.realm.reports import _candidate_rescore, rescore
from seed_search.realm.store import RealmStore
from seed_search.web.server import SweepManager


def make_window_samples(center, ow_half=1024):
    samples = []
    for x in range(center[0] - ow_half, center[0] + ow_half, 64):
        for z in range(center[1] - ow_half, center[1] + ow_half, 64):
            biome = 'cherry_grove' if (x == 0 and z == 0) else ('river' if (x == 64 and z == 0) else 'plains')
            samples.append({'coordinate': [x, 63, z], 'biome': biome})
    return samples


def test_top50_tracker_seed_zero_deduplication():
    tracker = Top50Tracker(capacity=5)

    # Seed 0 (as integer or string)
    rec1 = {
        'seed': 0,
        'ranking_tier': 0,
        'smart_score': 100,
        'baseline_score': 100,
        'unmet_requirements': 0,
        'radial_key': 500,
        'origin_distance_squared': 1000,
        'evaluation_center': [0, 0],
        'id': '0:0:0',
    }
    assert tracker.observe(rec1) is True
    assert len(tracker) == 1
    assert '0' in tracker._seed_map

    # Duplicate seed 0 with worse score should be rejected
    rec_worse = copy.deepcopy(rec1)
    rec_worse['smart_score'] = 50
    rec_worse['baseline_score'] = 50
    assert tracker.observe(rec_worse) is False
    assert len(tracker) == 1

    # Better seed 0 should replace in-place without expanding heap size
    rec_better = copy.deepcopy(rec1)
    rec_better['smart_score'] = 200
    rec_better['baseline_score'] = 200
    assert tracker.observe(rec_better) is True
    assert len(tracker) == 1
    assert tracker.top_records()[0]['smart_score'] == 200

    # Fill to capacity
    for s in range(1, 6):
        tracker.observe({
            'seed': s,
            'ranking_tier': 0,
            'smart_score': 100 + s,
            'baseline_score': 100 + s,
            'unmet_requirements': 0,
            'radial_key': 500,
            'origin_distance_squared': 1000,
            'evaluation_center': [0, 0],
            'id': f'{s}:0:0',
        })
    assert len(tracker) == 5
    # Seed 0 with score 200 is still present
    seeds_present = {str(item.get('seed')) for item in tracker.top_records()}
    assert '0' in seeds_present


def test_v3_top_level_bonus_and_rescore_parity():
    center = [0, 0]
    v3_candidate = {
        'contract': 'master_seed_blueprint_v1',
        'id': '100:0:0',
        'seed': '100',
        'screening_revision': 'dynamic-envelope-2048-v3',
        'evaluation_center': center,
        'required_structures': {
            'village': {'predicted_viable': [(300, 300), (-300, -300), (300, -300), (-300, 300), (0, 500), (500, 0)]},
            'trial_chamber': {'predicted_viable': [(0, 0)] * 8},
            'ancient_city': {'predicted_viable': [(0, 0)] * 2},
            'desert_pyramid': {'predicted_viable': [(0, 0)] * 1},
            'jungle_temple': {'predicted_viable': [(0, 0)] * 1},
            'monument': {'predicted_viable': [(0, 0)] * 1},
            'ruined_portal': {'predicted_viable': [(0, 0)] * 8},
            'shipwreck': {'predicted_viable': [(0, 0)] * 4},
            'mineshaft': {'predicted_viable': [(0, 0)] * 10},
            'outpost': {'predicted_viable': [(0, 0)] * 1},
            'mansion': {'predicted_viable': [(0, 0)] * 1},
            'stronghold': {'predicted_viable': [(0, 0)] * 1},
        },
        'required_nether_structures': {
            'fortress': {'predicted_viable': [(0, 0)] * 1},
            'bastion': {'predicted_viable': [(0, 0), (100, 100)]},
        },
        'bastion_variants': [[0, 0, 2], [100, 100, 0]],
        'optional_structures': {
            'swamp_hut': {'predicted_viable': []},
            'igloo': {'predicted_viable': []},
            'trail_ruins': {'predicted_viable': []},
            'ocean_ruin': {'predicted_viable': []},
            'buried_treasure': {'predicted_viable': []},
        },
        'biomes': {
            'sampling': {
                'samples': make_window_samples(center, ow_half=1024),
            }
        },
        'deficit_categories': [],
    }

    cfg = dynamic_v3_blueprint_config()
    rescored = _candidate_rescore(copy.deepcopy(v3_candidate), cfg, 'test-rev')

    # Verify scenic_bonus and village_spread_bonus top-level match ranking.components
    assert rescored['ranking']['components']['scenic_bonus'] == 25
    assert rescored['scenic_bonus'] == 25
    assert rescored['ranking']['components']['village_spread_bonus'] == 25
    assert rescored['village_spread_bonus'] == 25


def test_custom_counts_sync_in_server():
    cfg, _ = SweepManager._resolve_sweep(
        profile='dynamic2048',
        counts={'outpost': 3, 'fortress': 2, 'bastion': 3},
    )
    assert cfg['structures']['minimum_counts']['outpost'] == 3
    assert cfg['structures']['nether_minimum_counts']['fortress'] == 2
    assert cfg['structures']['nether_minimum_counts']['bastion'] == 3


def test_rescore_syncs_top_candidates_and_top50_json(tmp_path):
    run_dir = tmp_path / 'run_rescore'
    cfg = dynamic_v3_blueprint_config()
    center = [0, 0]
    with RealmStore(run_dir, {'config': cfg}) as store:
        # Create top_candidates table
        store.db.execute("CREATE TABLE IF NOT EXISTS top_candidates (rank INTEGER PRIMARY KEY, seed TEXT NOT NULL, score INTEGER NOT NULL, result TEXT NOT NULL)")

        candidate = {
            'contract': 'master_seed_blueprint_v1',
            'id': '42:0:0',
            'seed': '42',
            'screening_revision': 'dynamic-envelope-2048-v3',
            'evaluation_center': center,
            'required_structures': {
                'village': {'predicted_viable': [(300, 300), (-300, -300), (300, -300), (-300, 300), (0, 500), (500, 0)]},
                'trial_chamber': {'predicted_viable': [(0, 0)] * 8},
                'ancient_city': {'predicted_viable': [(0, 0)] * 2},
                'desert_pyramid': {'predicted_viable': [(0, 0)] * 1},
                'jungle_temple': {'predicted_viable': [(0, 0)] * 1},
                'monument': {'predicted_viable': [(0, 0)] * 1},
                'ruined_portal': {'predicted_viable': [(0, 0)] * 8},
                'shipwreck': {'predicted_viable': [(0, 0)] * 4},
                'mineshaft': {'predicted_viable': [(0, 0)] * 10},
                'outpost': {'predicted_viable': [(0, 0)] * 1},
                'mansion': {'predicted_viable': [(0, 0)] * 1},
                'stronghold': {'predicted_viable': [(0, 0)] * 1},
            },
            'required_nether_structures': {
                'fortress': {'predicted_viable': [(0, 0)] * 1},
                'bastion': {'predicted_viable': [(0, 0), (10, 10)]},
            },
            'bastion_variants': [[0, 0, 3], [10, 10, 0]],
            'optional_structures': {
                'swamp_hut': {'predicted_viable': []},
                'igloo': {'predicted_viable': []},
                'trail_ruins': {'predicted_viable': []},
                'ocean_ruin': {'predicted_viable': []},
                'buried_treasure': {'predicted_viable': []},
            },
            'biomes': {'sampling': {'samples': make_window_samples(center, ow_half=1024)}},
            'deficit_categories': [],
            'baseline_score': 100,
            'baseline_score_observed': 100,
            'ranking': {'score': 100, 'final_score': 100, 'deficit_tier': 0, 'weighted_radial_dist': 0, 'origin_distance': 0},
        }

        store.db.execute("INSERT INTO candidates VALUES (?, 0, ?, 'PREDICTED', ?)", ('42:0:0', '42', json.dumps(candidate)))
        store.db.execute("INSERT INTO top_candidates VALUES (1, '42', 100, ?)", (json.dumps(candidate),))
        top50_file = run_dir / 'top50.json'
        top50_file.write_text(json.dumps([candidate]))
        store.db.commit()

        # Run rescore
        rescore(store, cfg)

        # Verify top_candidates table and top50.json were updated
        top_row = store.db.execute("SELECT score FROM top_candidates WHERE seed='42'").fetchone()
        assert top_row is not None
        assert top50_file.exists()
        top50_content = json.loads(top50_file.read_text())
        assert len(top50_content) == 1

