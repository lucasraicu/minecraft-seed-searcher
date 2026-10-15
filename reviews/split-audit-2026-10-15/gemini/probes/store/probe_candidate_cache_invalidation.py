"""
Probe: Verify candidate cache invalidation bug in WebSearchHandler / SweepManager.
Finding ID: G-STORE-01

Tests that updating candidate score, qualification, or metadata in-place via UPDATE
(e.g., store.upsert_candidate) fails to invalidate the web server's candidate cache
because (count, max(rowid)) remains unchanged.
"""
import copy
import json
import sqlite3
import sys
from pathlib import Path

# Add project root and src to path
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.realm.store import RealmStore
from seed_search.web.server import SweepManager, parse_candidate_row


def test_stale_candidate_cache_on_in_place_update(tmp_path):
    run_dir = tmp_path / "web-sweep-20261015-120000-abcd1234"
    run_dir.mkdir(parents=True)
    
    cfg = {"search": {"workers": 1, "max_misses": 2}}
    identity = {"config": cfg, "count": 1000, "start_index": 0, "execution": "native"}
    
    # 1. Initialize store and create a candidate
    with RealmStore(run_dir, identity=identity) as store:
        store.configure_range(0, 10, 1)
        store.claim_range("w1", max_seeds=1)
        
        cand = {
            "id": "12345:100:200",
            "seed": "12345",
            "index": 0,
            "stronghold": [100, 200],
            "qualification": "PREDICTED",
            "baseline_score": 55.0,
            "baseline_score_observed": 55.0,
            "required_structures": {
                "stronghold": {"predicted_viable": [[100, 200]]}
            },
            "biomes": {"raw_names": ["plains", "forest"]}
        }
        batch = [{
            "index": 0,
            "seed": "12345",
            "anchors": [cand],
            "counts": {"anchors": 1}
        }]
        store.complete_range(0, 1, batch)
        
    # 2. Web server SweepManager binds and reads candidates
    manager = SweepManager()
    manager.run_dir = run_dir
    manager.run_id = run_dir.name
    manager.status = "running"
    
    # First query loads candidate with score 55.0
    manager._query_sqlite_candidates()
    assert len(manager.candidates) == 1, "Expected 1 candidate loaded"
    initial_score = manager.candidates[0]["score"]
    initial_qualification = manager.candidates[0]["baselineStatus"]
    assert initial_score == 55.0
    assert initial_qualification == "PREDICTED"
    initial_sig = manager._last_candidates_sig
    print(f"[Probe] Initial sig: {initial_sig}")
    print(f"[Probe] Initial candidate score: {initial_score}, qualification: {initial_qualification}")
    
    # 3. Simulate external in-place update (e.g. BDS verification, terrain score update, or inventory work)
    with RealmStore(run_dir, resume=True) as store:
        # Update qualification to VERIFIED and update score to 99.0
        updated_cand = dict(cand)
        updated_cand["qualification"] = "VERIFIED"
        updated_cand["baseline_score"] = 99.0
        updated_cand["baseline_score_observed"] = 99.0
        updated_cand["surface_biome_verification"] = {
            "status": "PARTIAL",
            "observation": {"source": "actual", "actual": True, "operation": "surface_points_v1", "status": "PARTIAL"},
            "classification": {"raw_names": ["plains", "forest"], "uncertainty": {"domain": "actual_generated_surface"}}
        }
        store.upsert_candidate(updated_cand, allow_qualification_change=True)
        
    # Verify in DB that it really was updated
    with sqlite3.connect(f"file:{run_dir / 'realm.sqlite'}?mode=ro", uri=True) as conn:
        row = conn.execute("SELECT qualification, result FROM candidates WHERE id=?", (cand["id"],)).fetchone()
        db_qual = row[0]
        db_cand = json.loads(row[1])
        assert db_qual == "VERIFIED"
        assert db_cand["baseline_score"] == 99.0
        print(f"[Probe] SQLite DB verified: qualification={db_qual}, score={db_cand['baseline_score']}")
        
        # Check count(*), max(rowid)
        cur = conn.cursor()
        cur.execute("SELECT count(*), max(rowid) FROM candidates")
        cand_sig_after = cur.fetchone()
        print(f"[Probe] SQLite count, max(rowid) after update: {cand_sig_after}")
        
    # 4. Web server calls _query_sqlite_candidates() again
    manager._query_sqlite_candidates()
    cached_cand = manager.candidates[0]
    cached_score = cached_cand["score"]
    cached_qualification = cached_cand["baselineStatus"]
    cached_sig = manager._last_candidates_sig
    
    print(f"[Probe] After query_sqlite_candidates(): sig={cached_sig}")
    print(f"[Probe] Cached candidate score: {cached_score}, qualification: {cached_qualification}")
    
    # Check if STALE:
    is_stale = (cached_score == initial_score and cached_qualification == initial_qualification)
    if is_stale:
        print("[BUG CONFIRMED] G-STORE-01: Manager served stale candidate data from cache!")
        print(f"  Expected: score=99.0, qualification=VERIFIED")
        print(f"  Actual:   score={cached_score}, qualification={cached_qualification}")
        return True
    else:
        print("[FAIL] Manager somehow invalidated cache.")
        return False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_stale_candidate_cache_on_in_place_update(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")
