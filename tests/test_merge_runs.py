"""Tests for scripts/merge_runs.py authoritative schema, validation, and interval union."""
import json
import sqlite3
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.merge_runs import merge_runs, union_intervals, compute_interval_coverage
from seed_search.realm.store import RealmStore, canonical, index_key


def test_union_intervals_disjoint_and_overlapping():
    assert union_intervals([]) == []
    assert union_intervals([(0, 100), (100, 200)]) == [(0, 200)]
    assert union_intervals([(0, 100), (50, 150)]) == [(0, 150)]
    assert union_intervals([(0, 100), (0, 100)]) == [(0, 100)]
    assert union_intervals([(200, 300), (0, 100)]) == [(0, 100), (200, 300)]
    assert compute_interval_coverage([(0, 100), (50, 150), (100, 200)]) == 200


def test_merge_runs_authoritative_schema_and_idempotence(tmp_path):
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    master = tmp_path / "master"

    # Create run1 with RealmStore
    ident1 = {
        "config": {"search": {"pilot_limit": 100}},
        "config_sha256": "policy_hash_abc",
        "native_build": "/usr/lib/native",
    }
    with RealmStore(run1, identity=ident1) as store1:
        store1.configure_range(0, 100, batch_size=100)
        # Add range
        store1.db.execute("INSERT OR REPLACE INTO ranges VALUES (?, ?, 'complete', 'worker1', 1, 'digest1')",
                          (index_key(0), index_key(100)))
        cand1 = {
            "id": "123:0:0",
            "seed": "123",
            "index": 0,
            "qualification": "PREDICTED",
            "stronghold": [0, 0],
            "bounds": [-100, -100, 100, 100],
        }
        store1.db.execute("INSERT INTO candidates VALUES (?, ?, ?, ?, ?)",
                          (cand1["id"], index_key(0), "123", "PREDICTED", canonical(cand1)))
        store1.db.commit()

    # Create run2 with matching policy and disjoint range
    ident2 = dict(ident1)
    with RealmStore(run2, identity=ident2) as store2:
        store2.configure_range(100, 250, batch_size=150)
        store2.db.execute("INSERT OR REPLACE INTO ranges VALUES (?, ?, 'complete', 'worker2', 1, 'digest2')",
                          (index_key(100), index_key(250)))
        cand2 = {
            "id": "456:100:100",
            "seed": "456",
            "index": 100,
            "qualification": "PREDICTED",
            "stronghold": [100, 100],
            "bounds": [-100, -100, 100, 100],
        }
        store2.db.execute("INSERT INTO candidates VALUES (?, ?, ?, ?, ?)",
                          (cand2["id"], index_key(100), "456", "PREDICTED", canonical(cand2)))
        store2.db.commit()

    # Initial merge
    summary = merge_runs([run1, run2], master)
    assert summary["merged_sources"] == 2
    assert summary["total_seeds_scanned"] == 250
    assert summary["total_candidates"] == 2
    assert summary["incompatible_records"] == []

    # Check master schema tables exist
    master_db = master / "realm.sqlite"
    conn = sqlite3.connect(master_db)
    cur = conn.cursor()
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "ranges" in tables
    assert "candidates" in tables
    assert "merged_source_runs" in tables
    assert "candidate_leaderboard_view" in {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()}

    # Check idempotent second merge with identical runs
    summary2 = merge_runs([run1, run2], master)
    assert summary2["total_seeds_scanned"] == 250
    assert summary2["total_candidates"] == 2
    assert summary2["incompatible_records"] == []
    conn.close()


def test_merge_runs_policy_hash_mismatch(tmp_path):
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    master = tmp_path / "master"

    with RealmStore(run1, identity={"config_sha256": "hash_A"}) as store1:
        store1.configure_range(0, 100)

    with RealmStore(run2, identity={"config_sha256": "hash_B"}) as store2:
        store2.configure_range(100, 200)

    with pytest.raises(ValueError, match="Policy hash mismatch"):
        merge_runs([run1, run2], master)


def test_merge_runs_native_build_mismatch(tmp_path):
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    master = tmp_path / "master"

    with RealmStore(run1, identity={"config_sha256": "hash_A", "native_build": "build_v1"}) as store1:
        store1.configure_range(0, 100)

    with RealmStore(run2, identity={"config_sha256": "hash_A", "native_build": "build_v2"}) as store2:
        store2.configure_range(100, 200)

    with pytest.raises(ValueError, match="Native build identity mismatch"):
        merge_runs([run1, run2], master)


def test_merge_runs_rejects_and_reports_incompatible_records(tmp_path):
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    master = tmp_path / "master"

    ident = {"config_sha256": "hash_shared"}
    with RealmStore(run1, identity=ident) as store1:
        store1.configure_range(0, 100)
        cand1 = {"id": "conflicting_id", "seed": "123", "qualification": "PREDICTED", "payload": "A"}
        store1.db.execute("INSERT INTO candidates VALUES (?, ?, ?, ?, ?)",
                          ("conflicting_id", index_key(0), "123", "PREDICTED", canonical(cand1)))
        store1.db.commit()

    with RealmStore(run2, identity=ident) as store2:
        store2.configure_range(100, 200)
        # Conflicting qualification and payload for same ID
        cand2 = {"id": "conflicting_id", "seed": "123", "qualification": "FAILED", "payload": "B"}
        store2.db.execute("INSERT INTO candidates VALUES (?, ?, ?, ?, ?)",
                          ("conflicting_id", index_key(100), "123", "FAILED", canonical(cand2)))
        store2.db.commit()

    # Non-strict mode reports incompatible records without crashing
    summary = merge_runs([run1, run2], master, strict=False)
    assert len(summary["incompatible_records"]) == 1
    assert summary["incompatible_records"][0]["id"] == "conflicting_id"
    assert summary["total_candidates"] == 1  # conflicting record from run2 rejected

    # Strict mode raises error
    with pytest.raises(ValueError, match="incompatible records"):
        merge_runs([run1, run2], master, strict=True)
