"""Comprehensive tests for dynamic-envelope-2048-v3 realm geometry and center rules."""
import pytest
from seed_search.realm.config import (
    DYNAMIC_V3_REVISION,
    dynamic_v3_blueprint_config,
    validate_blueprint_config,
    validate_config,
    dynamic_v3_policy,
)
from seed_search.realm.spawn import classify_spawn
from seed_search.realm.native_batch import Prototype


def test_v3_config_geometry():
    cfg = dynamic_v3_blueprint_config()
    validate_config(cfg)
    validate_blueprint_config(cfg)
    assert cfg['screening_revision'] == DYNAMIC_V3_REVISION
    assert dynamic_v3_policy(cfg) is True
    assert cfg['deployment']['overworld_side_blocks'] == 2048
    assert cfg['deployment']['nether_side_blocks'] == 1024
    assert cfg['discovery']['overworld_bounds'] == [-2000, -2000, 2000, 2000]
    assert cfg['discovery']['nether_bounds'] == [-634, -634, 634, 634]


def test_v3_center_extents():
    cfg = dynamic_v3_blueprint_config()
    ow_side = cfg['deployment']['overworld_side_blocks']
    nw_side = cfg['deployment']['nether_side_blocks']
    ow_bounds = cfg['discovery']['overworld_bounds']
    nw_bounds = cfg['discovery']['nether_bounds']

    ow_half = ow_side // 2  # 1024
    nw_half = nw_side // 2  # 512

    # Overworld center limits: [-2000 + 1024, 2000 - 1024] = [-976, +976]
    min_c = ow_bounds[0] + ow_half
    max_c = ow_bounds[2] - ow_half
    assert min_c == -976
    assert max_c == 976

    # Nether center limits: [-976 // 8, 976 // 8] = [-122, 122]
    nether_min_c = min_c // 8
    nether_max_c = max_c // 8
    assert nether_min_c == -122
    assert nether_max_c == 122

    # Nether coordinate bounds: [-122 - 512, 122 + 512] = [-634, 634]
    assert nether_min_c - nw_half == nw_bounds[0]
    assert nether_max_c + nw_half == nw_bounds[2]


def test_v3_spawn_validation():
    cfg = dynamic_v3_blueprint_config()
    # Inside [-976, 976]
    c_ok = classify_spawn({'evaluation_center': [0, 0]}, cfg)
    assert c_ok['status'] == 'PENDING'
    c_boundary = classify_spawn({'evaluation_center': [976, -976]}, cfg)
    assert c_boundary['status'] == 'PENDING'

    # Outside [-976, 976]
    with pytest.raises(ValueError, match='inside the envelope'):
        classify_spawn({'evaluation_center': [977, 0]}, cfg)
    with pytest.raises(ValueError, match='inside the envelope'):
        classify_spawn({'evaluation_center': [-977, 0]}, cfg)
    with pytest.raises(ValueError, match='inside the envelope'):
        classify_spawn({'evaluation_center': [1168, 0]}, cfg)


def test_v3_prototype_native_init():
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    assert p.policy.overworld_half == 1024
    assert p.policy.nether_half == 512
    assert p.policy.dynamic_v2 == 1  # Uses v2 structure bonuses and layout


def test_v3_native_batch_sweep():
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    # Run small sweep over seeds
    seeds = [12345, 67890, 11111]
    with p.sweep(seeds, threads=1, retention='full') as batch:
        results = batch.records()
    assert len(results) == len(seeds)
    for r in results:
        # Results should be clean rejected or accepted with anchor within [-976, 976]
        if r.get('anchors'):
            a = r['anchors'][0]
            cx, cz = a['evaluation_center']
            assert -976 <= cx <= 976
            assert -976 <= cz <= 976


def test_v3_floors_and_zero_misses():
    cfg = dynamic_v3_blueprint_config()
    validate_blueprint_config(cfg)
    floors = cfg['structures']['hard_floors']
    assert floors['stronghold'] == 1
    assert floors['mansion'] == 1
    assert floors['village'] == 6
    assert floors['trial_chamber'] == 8
    assert floors['ancient_city'] == 2
    assert floors['desert_pyramid'] == 1
    assert floors['jungle_temple'] == 1
    assert floors['monument'] == 1
    assert floors['ruined_portal'] == 8
    assert floors['shipwreck'] == 4
    assert floors['mineshaft'] == 10
    assert floors['outpost'] == 1
    assert floors['fortress'] == 1
    assert floors['bastion'] == 2
    assert cfg['search']['max_misses'] == 0


def test_v3_dynamic_scoring_pure_additive():
    from seed_search.realm.blueprint import dynamic_v3_score

    # Baseline: meeting baseline hard floors exactly yields 0 core surplus and 0 deficit penalty
    baseline_counts = {
        'stronghold': 1, 'mansion': 1, 'monument': 1, 'village': 6,
        'trial_chamber': 8, 'ancient_city': 2, 'desert_pyramid': 1,
        'jungle_temple': 1, 'outpost': 1, 'fortress': 1, 'bastion': 2,
        'ruined_portal': 8, 'shipwreck': 4, 'mineshaft': 10
    }
    score, comp, defs = dynamic_v3_score(baseline_counts)
    assert score == 0
    assert comp['deficit_penalty'] == 0
    assert comp['core_surplus'] == 0
    assert defs == []

    # 1. Stronghold: 2nd = +30, 3rd+ = +20 (+50 total)
    counts = dict(baseline_counts, stronghold=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 30
    counts = dict(baseline_counts, stronghold=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 50

    # 2. Mansion: 2nd = +45, 3rd+ = +25 (+70 total)
    counts = dict(baseline_counts, mansion=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 45
    counts = dict(baseline_counts, mansion=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 70

    # 3. Ocean Monument: 2nd = +25, 3rd = +15, 4th+ = +10 (+50 total)
    counts = dict(baseline_counts, monument=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 25
    counts = dict(baseline_counts, monument=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 40
    counts = dict(baseline_counts, monument=4)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 50

    # 4. Outpost (F=1): 2nd = +15, 3rd = +15, 4th+ = +10 (+40 max)
    counts = dict(baseline_counts, outpost=1)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 0
    counts = dict(baseline_counts, outpost=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 15
    counts = dict(baseline_counts, outpost=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 30
    counts = dict(baseline_counts, outpost=4)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 40
    counts = dict(baseline_counts, outpost=5)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 40

    # 5. Fortress: 2nd = +20, 3rd = +15, 4th+ = +15 (+50 max)
    counts = dict(baseline_counts, fortress=1)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 0
    counts = dict(baseline_counts, fortress=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 20
    counts = dict(baseline_counts, fortress=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 35
    counts = dict(baseline_counts, fortress=4)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 50

    # 6. Bastion: 3rd = +20, 4th = +15, 5th+ = +15 (+50 max; +20 treasure)
    counts = dict(baseline_counts, bastion=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 0
    s_tb, _, _ = dynamic_v3_score(counts, treasure_bastion=1)
    assert s_tb == 20
    counts = dict(baseline_counts, bastion=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 20

    # 7. Village: 7th..11th+ = +10 each (floor is 6, 0 at floor, +50 max)
    v_ladder = [(6, 0), (7, 10), (8, 20), (9, 30), (10, 40), (11, 50), (12, 50)]
    for v_cnt, expected_pts in v_ladder:
        counts = dict(baseline_counts, village=v_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts, f"Village count {v_cnt} expected {expected_pts}, got {s}"

    # 8. Trial Chamber: 9th=+10, 10th=+10, 11th=+10, 12th=+8, 13th+=+7 (floor is 8, 0 at floor, +45 max)
    tc_ladder = [(8, 0), (9, 10), (10, 20), (11, 30), (12, 38), (13, 45), (14, 45)]
    for tc_cnt, expected_pts in tc_ladder:
        counts = dict(baseline_counts, trial_chamber=tc_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 9. Ancient City: 3rd=+20, 4th=+20, 5th=+15, 6th+=+10 (floor is 2, 0 at floor, +65 max)
    ac_ladder = [(2, 0), (3, 20), (4, 40), (5, 55), (6, 65), (7, 65)]
    for ac_cnt, expected_pts in ac_ladder:
        counts = dict(baseline_counts, ancient_city=ac_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 10. Desert Pyramid: 2nd = +25, 3rd = +20, 4th+ = +15 (Max +60)
    dp_ladder = [(1, 0), (2, 25), (3, 45), (4, 60), (5, 60)]
    for dp_cnt, expected_pts in dp_ladder:
        counts = dict(baseline_counts, desert_pyramid=dp_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 11. Jungle Temple: 2nd = +25, 3rd = +20, 4th+ = +15 (Max +60)
    jt_ladder = [(1, 0), (2, 25), (3, 45), (4, 60), (5, 60)]
    for jt_cnt, expected_pts in jt_ladder:
        counts = dict(baseline_counts, jungle_temple=jt_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 12. Shipwreck: 5th..8th = +5 each (floor is 4, 0 at floor, +20 max)
    sw_ladder = [(4, 0), (5, 5), (6, 10), (7, 15), (8, 20), (9, 20)]
    for sw_cnt, expected_pts in sw_ladder:
        counts = dict(baseline_counts, shipwreck=sw_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 13. Ruined Portal: 9th..12th = +5 each (floor is 8, 0 at floor, +20 max)
    rp_ladder = [(8, 0), (9, 5), (10, 10), (11, 15), (12, 20), (13, 20)]
    for rp_cnt, expected_pts in rp_ladder:
        counts = dict(baseline_counts, ruined_portal=rp_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 14. Mineshaft: +2 each over 10 up to 20 max
    ms_ladder = [(10, 0), (11, 2), (15, 10), (20, 20), (25, 20)]
    for ms_cnt, expected_pts in ms_ladder:
        counts = dict(baseline_counts, mineshaft=ms_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts


def test_top50_tracker_capacity_and_cutoff():
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=50)
    assert len(tracker) == 0
    assert tracker.cutoff_score() is None

    # Insert 40 candidates with increasing scores
    for i in range(40):
        tracker.observe({
            'seed': str(1000 + i),
            'baseline_score_observed': 100 + i,
            'ranking_tier': 0,
            'unmet_requirements': 0,
            'radial_key': 500000,
            'origin_distance_squared': 10000,
            'evaluation_center': [0, 0]
        })
    assert len(tracker) == 40
    # Still less than capacity, so cutoff is None
    assert tracker.cutoff_score() is None

    # Insert 10 more candidates (scores 140 to 149) -> reaches capacity 50
    for i in range(40, 50):
        tracker.observe({
            'seed': str(1000 + i),
            'baseline_score_observed': 100 + i,
            'ranking_tier': 0,
            'unmet_requirements': 0,
            'radial_key': 500000,
            'origin_distance_squared': 10000,
            'evaluation_center': [0, 0]
        })
    assert len(tracker) == 50
    # Now capacity is reached: cutoff score should be 100 (the lowest among 100..149)
    assert tracker.cutoff_score() == 100

    # Observe a candidate with score 90 (below cutoff 100) -> should be rejected
    accepted = tracker.observe({
        'seed': '9999',
        'baseline_score_observed': 90,
        'ranking_tier': 0,
        'unmet_requirements': 0,
        'radial_key': 500000,
        'origin_distance_squared': 10000,
        'evaluation_center': [0, 0]
    })
    assert accepted is False
    assert len(tracker) == 50
    assert tracker.cutoff_score() == 100

    # Observe a candidate with score 155 (above cutoff 100) -> accepted, displacing 100
    accepted = tracker.observe({
        'seed': '8888',
        'baseline_score_observed': 155,
        'ranking_tier': 0,
        'unmet_requirements': 0,
        'radial_key': 500000,
        'origin_distance_squared': 10000,
        'evaluation_center': [0, 0]
    })
    assert accepted is True
    assert len(tracker) == 50
    # Now the lowest score in top 50 is 101!
    assert tracker.cutoff_score() == 101

    # Check top_records order: Rank 1 must have score 155
    records = tracker.top_records()
    assert len(records) == 50
    assert records[0]['seed'] == '8888'
    assert records[0]['baseline_score_observed'] == 155
    assert records[-1]['baseline_score_observed'] == 101


def test_top50_tracker_serialization(tmp_path):
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=5)
    for i in range(5):
        tracker.observe({
            'seed': str(i),
            'baseline_score_observed': 200 + i * 10,
            'ranking_tier': 0,
            'unmet_requirements': 0,
            'radial_key': 1000,
            'origin_distance_squared': 500,
            'evaluation_center': [16, -16]
        })

    # Test JSON serialization
    json_file = str(tmp_path / "top50.json")
    tracker.save_to_json(json_file)

    tracker2 = Top50Tracker(capacity=5)
    loaded = tracker2.load_from_json(json_file)
    assert loaded == 5
    assert tracker2.cutoff_score() == 200
    assert tracker2.top_records()[0]['baseline_score_observed'] == 240

    # Test SQLite serialization
    import sqlite3
    db_file = str(tmp_path / "top50.db")
    tracker.save_to_sqlite(db_file)

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn.close()
    assert len(rows) == 5
    assert rows[0] == (1, '4', 240)
    assert rows[-1] == (5, '0', 200)


def test_v3_fixture_sweep_parity():
    from seed_search.realm.native_batch import semantic_record
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    with p.sweep([456], fixtures=[(0, 0, -1)]) as batch:
        direct = batch.records()[0]
        replay = batch.records(adapter='replay')[0]
        assert direct['anchors'][0]['screening_revision'] == 'dynamic-envelope-2048-v3'
        assert direct['anchors'][0]['deficit_penalty'] == 0
        assert direct['anchors'][0]['baseline_score'] == direct['anchors'][0]['bonus_total']
        assert direct['anchors'][0]['inventory']['version'] == 'dynamic-2048-count-inventory-v3'
        assert semantic_record(direct) == semantic_record(replay)


def test_v3_nether_lattice_bounds():
    from seed_search.realm.dynamic import nether_palette, nether_bounds

    class MockBackend:
        def sample(self, points, dimension=-1):
            return [8] * len(points)  # nether_wastes

    for center in [(0, 0), (976, -976), (-976, 976), (123, -456), (-500, 500)]:
        bounds = nether_bounds(center, 512)
        res = nether_palette(MockBackend(), center, nether_half=512)
        assert res['sample_count'] == 256
        for s in res['sampling']['samples']:
            x, y, z = s['coordinate']
            assert bounds[0] <= x < bounds[2], f"x={x} not in [{bounds[0]}, {bounds[2]}) for center {center}"
            assert bounds[1] <= z < bounds[3], f"z={z} not in [{bounds[1]}, {bounds[3]}) for center {center}"


def test_v3_cutoff_score_pruning():
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    assert p.policy.cutoff_score == 0

    # With high cutoff score, fixture anchor should be pruned early
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=9999) as batch:
        records = batch.records()
        assert len(records) == 1
        assert len(records[0]['anchors']) == 0

    # With cutoff score 0, normal anchor is retained
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=0) as batch:
        records = batch.records()
        assert len(records) == 1
        assert len(records[0]['anchors']) == 1
        observed_score = records[0]['anchors'][0]['baseline_score_observed']
        assert observed_score == 479

    # Exact boundary: cutoff == observed_score must retain
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=observed_score) as batch:
        records = batch.records()
        assert len(records[0]['anchors']) == 1
        assert records[0]['anchors'][0]['baseline_score_observed'] == observed_score

    # Exact boundary: cutoff == observed_score + 1 must prune
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=observed_score + 1) as batch:
        records = batch.records()
        assert len(records[0]['anchors']) == 0

    # Top50Tracker integration: cutoff_score feeds back into sweep dynamically
    from seed_search.realm.top_tracker import Top50Tracker
    tracker = Top50Tracker(capacity=1)
    assert tracker.cutoff_score() is None

    # First seed observed fills tracker
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=tracker.cutoff_score() or 0) as batch:
        records = batch.records()
        tracker.observe(records[0])
    assert tracker.cutoff_score() == 479

    # Next sweep with tracker's cutoff score prunes anything strictly less than 479
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=tracker.cutoff_score() + 1) as batch:
        records = batch.records()
        assert len(records[0]['anchors']) == 0


def test_v3_candidate_rescore_idempotence():
    import copy
    from seed_search.realm.reports import _candidate_rescore

    # Construct complete v3 candidate scoring exactly 281
    candidate_281 = {
        'contract': 'master_seed_blueprint_v1',
        'screening_revision': 'dynamic-envelope-2048-v3',
        'evaluation_center': [0, 0],
        'required_structures': {
            'stronghold': {'predicted_viable': [[100, 100]]},
            'mansion': {'predicted_viable': [[120, 120]]},
            'village': {'predicted_viable': [[100, 100], [-300, 300], [-300, -300], [300, -300], [500, 500], [600, 600], [700, 700]]},
            'trial_chamber': {'predicted_viable': [[i * 50, i * 50] for i in range(1, 10)]},
            'ancient_city': {'predicted_viable': [[200, 200], [400, 400], [600, 600]]},
            'desert_pyramid': {'predicted_viable': [[150, 150], [300, 300]]},
            'jungle_temple': {'predicted_viable': [[250, 250]]},
            'monument': {'predicted_viable': [[350, 350]]},
            'outpost': {'predicted_viable': [[450, 450]]},
            'ruined_portal': {'predicted_viable': [[i * 40, -i * 40] for i in range(1, 13)]},
            'shipwreck': {'predicted_viable': [[i * 60, i * 60] for i in range(1, 5)]},
            'mineshaft': {'predicted_viable': [[i * 30, -i * 30] for i in range(1, 19)]},
        },
        'required_nether_structures': {
            'fortress': {'predicted_viable': [[10, 10], [50, 50]]},
            'bastion': {'predicted_viable': [[20, 20], [60, 60]]},
        },
        'optional_structures': {
            'swamp_hut': {'predicted_viable': []},
            'trail_ruins': {'predicted_viable': []},
            'igloo': {'predicted_viable': []},
            'ocean_ruin': {'predicted_viable': []},
            'buried_treasure': {'predicted_viable': []},
        },
        'bastion_variants': [[20, 20, 2], [60, 60, 0]],
        'biomes': {
            'sampling': {
                'samples': [
                    {'coordinate': [x, 63, z], 'biome': 'cherry_grove' if (x == 0 and z == 0) else ('river' if (x == 64 and z == 0) else 'plains')}
                    for x in range(-1024, 1025, 64)
                    for z in range(-1024, 1025, 64)
                ]
            }
        }
    }

    cfg = dynamic_v3_blueprint_config()
    rescored = _candidate_rescore(copy.deepcopy(candidate_281), cfg, 'rev_v3_initial')
    assert rescored['baseline_score'] == 281
    assert rescored['baseline_score_observed'] == 281
    assert rescored['ranking']['score'] == 281
    assert rescored['ranking']['components']['bonus_total'] == 281
    assert rescored['ranking']['components']['deficit_penalty'] == 0
    assert rescored['ranking']['components']['scenic_bonus'] == 25
    assert rescored['ranking']['components']['village_spread_bonus'] == 25
    assert rescored['ranking']['components']['treasure_bastion_bonus'] == 20
    assert rescored['ranking']['components']['nether_core_bonus'] == 20

    # Test idempotence: rescore again and assert complete equality
    rescored_again = _candidate_rescore(copy.deepcopy(rescored), cfg, 'rev_v3_second')
    assert rescored_again['baseline_score'] == 281
    assert rescored_again['baseline_score'] == rescored['baseline_score']
    assert rescored_again['ranking']['components'] == rescored['ranking']['components']
    assert rescored_again['weighted_radial_dist'] == rescored['weighted_radial_dist']
    assert rescored_again['radial_key'] == rescored['radial_key']
    assert rescored_again['evaluation_center'] == rescored['evaluation_center']
    assert rescored_again['origin_distance'] == rescored['origin_distance']
    assert rescored_again['origin_distance_squared'] == rescored['origin_distance_squared']
    assert rescored_again['deficit_categories'] == rescored['deficit_categories']

    # Also test idempotence on a candidate generated by native sweep
    p = Prototype(None, cfg)
    with p.sweep([456], fixtures=[(0, 0, -1)]) as batch:
        native_anchor = batch.records()[0]['anchors'][0]
    orig_score = native_anchor['baseline_score']
    res_native_1 = _candidate_rescore(copy.deepcopy(native_anchor), cfg, 'rev_sweep_1')
    assert res_native_1['baseline_score'] == orig_score
    assert res_native_1['ranking']['components'] == native_anchor['ranking']['components']
    assert res_native_1['radial_key'] == native_anchor['radial_key']
    assert res_native_1['weighted_radial_dist'] == native_anchor['weighted_radial_dist']

    res_native_2 = _candidate_rescore(copy.deepcopy(res_native_1), cfg, 'rev_sweep_2')
    assert res_native_2['baseline_score'] == orig_score
    assert res_native_2['ranking'] == res_native_1['ranking']
    assert res_native_2['radial_key'] == res_native_1['radial_key']


def test_top50_tracker_nested_sqlite_saving(tmp_path):
    import sqlite3
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=10)
    nested_record = {
        'seed': '987654321',
        'contract': 'master_seed_blueprint_v1',
        'anchors': [
            {
                'id': '987654321:0:0',
                'seed': '987654321',
                'baseline_score_observed': 281,
                'baseline_score': 281,
                'ranking_tier': 0,
                'unmet_requirements': 0,
                'radial_key': 123456,
                'origin_distance_squared': 500,
                'evaluation_center': [0, 0],
                'ranking': {'score': 281}
            }
        ]
    }
    accepted = tracker.observe(nested_record)
    assert accepted is True
    assert len(tracker) == 1

    # Save to SQLite and verify non-zero score is stored in top_candidates table
    db_file = str(tmp_path / "nested_top50.db")
    tracker.save_to_sqlite(db_file)

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn.close()

    assert len(rows) == 1
    rank, seed, score = rows[0]
    assert rank == 1
    assert seed == '987654321'
    assert score == 281, f"Expected non-zero score 281, got {score}"

    # Test flush and flush_transactional methods
    tracker.flush(db_file)
    conn2 = sqlite3.connect(db_file)
    rows2 = conn2.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn2.close()
    assert rows2 == rows

    tracker.flush_transactional(db_file)
    conn3 = sqlite3.connect(db_file)
    rows3 = conn3.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn3.close()
    assert rows3 == rows


def test_top50_tracker_lexical_id_tiebreaking():
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=2)
    # Three candidates with identical arithmetic metrics, differing only by id
    rec_gamma = {'id': 'gamma', 'seed': '3', 'baseline_score_observed': 200, 'ranking_tier': 0, 'unmet_requirements': 0, 'radial_key': 100, 'origin_distance_squared': 100, 'evaluation_center': [0, 0]}
    rec_beta = {'id': 'beta', 'seed': '2', 'baseline_score_observed': 200, 'ranking_tier': 0, 'unmet_requirements': 0, 'radial_key': 100, 'origin_distance_squared': 100, 'evaluation_center': [0, 0]}
    rec_alpha = {'id': 'alpha', 'seed': '1', 'baseline_score_observed': 200, 'ranking_tier': 0, 'unmet_requirements': 0, 'radial_key': 100, 'origin_distance_squared': 100, 'evaluation_center': [0, 0]}

    tracker.observe(rec_gamma)
    tracker.observe(rec_beta)
    assert len(tracker) == 2
    # In ORDER_V2 ('id ASC'), 'beta' < 'gamma', so beta is Rank 1, gamma is Rank 2 (worst)
    assert tracker.top_records()[0]['id'] == 'beta'
    assert tracker.top_records()[1]['id'] == 'gamma'

    # Now observe 'alpha': 'alpha' < 'beta' < 'gamma'. Alpha is better than gamma, displacing gamma.
    accepted = tracker.observe(rec_alpha)
    assert accepted is True
    assert len(tracker) == 2

    records = tracker.top_records()
    assert records[0]['id'] == 'alpha'
    assert records[1]['id'] == 'beta'


def test_v3_outpost_floor_one_qualification_and_scoring():
    from seed_search.realm.blueprint import dynamic_v3_score

    cfg = dynamic_v3_blueprint_config()
    # 1. Floor verification
    assert cfg['structures']['hard_floors']['outpost'] == 1
    assert cfg['structures']['minimum_counts']['outpost'] == 1

    # 2. Pure additive scoring ladder: floor is 1, 2nd=+15, 3rd=+15, 4th+=+10 (Max 40)
    baseline_counts = {
        'stronghold': 1, 'mansion': 1, 'monument': 1, 'village': 6,
        'trial_chamber': 8, 'ancient_city': 2, 'desert_pyramid': 1,
        'jungle_temple': 1, 'outpost': 1, 'fortress': 1, 'bastion': 2,
        'ruined_portal': 8, 'shipwreck': 4, 'mineshaft': 10
    }
    # Meeting floor gives 0 bonus points
    s1, _, defs1 = dynamic_v3_score(dict(baseline_counts, outpost=1))
    assert s1 == 0
    assert defs1 == []

    # 2nd outpost = +15
    s2, comp2, _ = dynamic_v3_score(dict(baseline_counts, outpost=2))
    assert s2 == 15
    assert comp2['core_surplus'] == 15

    # 3rd outpost = +15 (30 total)
    s3, comp3, _ = dynamic_v3_score(dict(baseline_counts, outpost=3))
    assert s3 == 30
    assert comp3['core_surplus'] == 30

    # 4th outpost = +10 (40 total)
    s4, comp4, _ = dynamic_v3_score(dict(baseline_counts, outpost=4))
    assert s4 == 40
    assert comp4['core_surplus'] == 40

    # 5th outpost capped at 40
    s5, comp5, _ = dynamic_v3_score(dict(baseline_counts, outpost=5))
    assert s5 == 40
    assert comp5['core_surplus'] == 40


def test_top50_tracker_seed_deduplication_and_deepcopy():
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=5)
    rec = {'seed': '123', 'id': '123:0:0', 'baseline_score_observed': 100}
    assert tracker.observe(rec) is True
    assert len(tracker) == 1

    # External mutation of rec should not affect stored record
    rec['baseline_score_observed'] = 999
    assert tracker.top_records()[0]['baseline_score_observed'] == 100

    # Observing same seed with better score updates the entry in-place
    better_rec = {'seed': '123', 'id': '123:0:0', 'baseline_score_observed': 150}
    assert tracker.observe(better_rec) is True
    assert len(tracker) == 1
    assert tracker.top_records()[0]['baseline_score_observed'] == 150

    # Observing same seed with worse score is rejected and does not add a duplicate slot
    worse_rec = {'seed': '123', 'id': '123:0:0', 'baseline_score_observed': 80}
    assert tracker.observe(worse_rec) is False
    assert len(tracker) == 1
    assert tracker.top_records()[0]['baseline_score_observed'] == 150
