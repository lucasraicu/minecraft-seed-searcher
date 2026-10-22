import sqlite3
import json
from pathlib import Path
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import run_native_scan


def test_top_k_integration_e2e(tmp_path):
    cfg = dynamic_v3_blueprint_config()
    out = tmp_path / "scan_top_k"

    # Run a small scan with top_k=5 within pilot limit (count <= 1000)
    status = run_native_scan(
        cfg,
        out,
        count=1000,
        start_index=0,
        native_threads=1,
        native_batch_size=250,
        retention="survivors",
        top_k=5
    )

    assert status['top_k'] == 5
    top50_json = out / "top50.json"
    assert top50_json.is_file(), "top50.json should have been written"

    with open(top50_json) as f:
        records = json.load(f)
    assert isinstance(records, list)

    # Check SQLite table in realm.sqlite
    db_path = out / "realm.sqlite"
    assert db_path.is_file()
    conn = sqlite3.connect(db_path)
    table_exists = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='top_candidates'"
    ).fetchone()[0]
    assert table_exists == 1, "top_candidates table must exist in realm.sqlite"
    conn.close()


def test_top_k_resume_preserves_tracker(tmp_path):
    cfg = dynamic_v3_blueprint_config()
    out = tmp_path / "scan_resume"

    # Scan with stop_after=250 within pilot limit
    status1 = run_native_scan(
        cfg,
        out,
        count=1000,
        start_index=0,
        stop_after=250,
        native_threads=1,
        native_batch_size=250,
        retention="survivors",
        top_k=5
    )
    assert status1['completed_seeds'] == 250
    assert status1['top_k'] == 5

    # Resume scan of remaining seeds with stop_after=250
    status2 = run_native_scan(
        cfg,
        out,
        count=1000,
        start_index=0,
        resume=True,
        stop_after=250,
        native_threads=1,
        native_batch_size=250,
        retention="survivors",
        top_k=5
    )

    assert status2['completed_seeds'] == 500
    assert status2['top_k'] == 5
    top50_json = out / "top50.json"
    assert top50_json.is_file()


def test_top_k_pruning_admissibility():
    """Verify that native cutoff_score pruning preserves exact top candidate set."""
    from seed_search.realm.native_batch import Prototype
    from seed_search.realm.top_tracker import Top50Tracker

    cfg = dynamic_v3_blueprint_config()
    proto = Prototype(None, cfg)

    # 1. Sweep without cutoff to collect true baseline candidates
    with proto.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=0) as b_full:
        recs_full = b_full.records()
        observed_score = recs_full[0]['anchors'][0]['baseline_score_observed']
        from seed_search.realm.blueprint import dynamic_v3_score
        anchor = recs_full[0]['anchors'][0]
        counts = {name: len(row['coordinates'])
                  for group in ('required_structures', 'required_nether_structures')
                  for name, row in anchor[group].items()}
        optional = {name: len(row['coordinates']) for name, row in anchor['optional_structures'].items()}
        independent = dynamic_v3_score(counts, anchor['biomes']['raw_names'],
            hub=anchor['hub_bonus'], scenic=anchor['scenic_bonus'],
            village_spread=anchor['village_spread_bonus'], treasure_bastion=anchor['treasure_bastion'],
            optional_counts=optional, targets=anchor['configured_targets'],
            nether_core=anchor['nether_core_bonus'])[0]
        assert observed_score == independent == 484

    # 2. Seed the tracker from the independently verified current fixture.
    tracker = Top50Tracker(capacity=1)
    tracker.observe(recs_full[0])
    assert tracker.cutoff_score() == observed_score

    # A seed meeting the independently verified cutoff is retained
    with proto.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=tracker.cutoff_score()) as b_retained:
        recs_retained = b_retained.records()
        assert len(recs_retained[0]['anchors']) == 1
        assert recs_retained[0]['anchors'][0]['baseline_score_observed'] == observed_score

    # A cutoff strictly above the seed's potential safely prunes without crash or corruption
    with proto.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=observed_score + 1) as b_pruned:
        recs_pruned = b_pruned.records()
        assert len(recs_pruned[0]['anchors']) == 0
