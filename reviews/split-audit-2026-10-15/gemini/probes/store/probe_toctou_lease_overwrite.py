"""
Probe: Verify TOCTOU lease validation race and overwrite in complete_prepared.
Finding ID: G-STORE-02

Demonstrates that lease check at lines 423-429 occurs outside the transaction
(line 435), and the subsequent UPDATE at line 443 does not check status/lease
in its WHERE clause. A stale worker can overwrite a recovered/reassigned range,
causing double counting of completed_seeds and counts in compact retention mode.
"""
import copy
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.realm.store import RealmStore


def test_toctou_lease_overwrite_and_double_counting(tmp_path):
    run_dir = tmp_path / "realm_toctou_run"
    run_dir.mkdir(parents=True)
    
    cfg = {"search": {"workers": 1, "max_misses": 0}}
    identity = {
        "config": cfg,
        "count": 20,
        "start_index": 0,
        "retention": {"mode": "survivors", "max_misses": 0}
    }
    
    # 1. Initialize store with compact survivors retention
    with RealmStore(run_dir, identity=identity) as store:
        store.configure_range(0, 20, 10)
        
        # Worker A claims range [0, 10]
        claim_a = store.claim_range("worker-A", max_seeds=10)
        assert claim_a == (0, 10)
        
        # Prepare valid compact batch with 0 survivors (common case)
        receipt_a = {
            "version": "native-retention-receipt-v1",
            "inputs": 10,
            "retained_inputs": 0,
            "retained_anchors": 0,
            "discovered_anchors": 0,
            "input_decisions_sha256": "0" * 64
        }
        prepared_a = store.prepare_retained_range(0, 10, [], receipt_a)
        
        # Verify attempt number for worker A is 1
        row = store.db.execute("SELECT attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
        attempt_a = row[0]
        assert attempt_a == 1
        
        # 2. Worker A prepares to commit with lease ('worker-A', 1)
        # We hook capacity_check to simulate a context switch / slow check where
        # another process recovers assignments and Worker B claims the range!
        def slow_capacity_check(bytes_needed):
            print("[Probe] Inside capacity_check: simulating recovery and reassignment to Worker B...")
            # Simulate crash recovery while Worker A was checking capacity
            recovered = store.recover_assignments()
            assert recovered == 1
            # Worker B claims the range
            claim_b = store.claim_range("worker-B", max_seeds=10)
            assert claim_b == (0, 10)
            row_b = store.db.execute("SELECT status, worker, attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
            print(f"[Probe] Range in DB is now: status={row_b[0]}, worker={row_b[1]}, attempts={row_b[2]}")
            assert row_b == ("in_progress", "worker-B", 2)
            
        # Worker A calls complete_prepared with lease ('worker-A', 1)
        # Since line 428 checked lease BEFORE capacity_check:
        # capacity_check runs, reassignment happens, and then line 435 executes with self.db!
        committed_a = store.complete_prepared(prepared_a, lease=("worker-A", 1), capacity_check=slow_capacity_check)
        print(f"[Probe] Stale Worker A complete_prepared returned: {committed_a}")
        
        # Check ranges table after Worker A committed:
        row_after = store.db.execute("SELECT status, worker, attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
        print(f"[Probe] Range in DB after stale Worker A commit: {row_after}")
        
        # Completed seeds after Worker A:
        completed_after_a = store.get_state("completed_seeds")
        print(f"[Probe] completed_seeds after Worker A: {completed_after_a}")
        
        # Now Worker B finishes its work (attempt 2) and calls complete_prepared:
        receipt_b = {
            "version": "native-retention-receipt-v1",
            "inputs": 10,
            "retained_inputs": 0,
            "retained_anchors": 0,
            "discovered_anchors": 0,
            "input_decisions_sha256": "1" * 64  # slightly different digest
        }
        prepared_b = store.prepare_retained_range(0, 10, [], receipt_b)
        
        try:
            store.complete_prepared(prepared_b, lease=("worker-B", 2))
            print("[Probe] Worker B also committed!")
        except Exception as exc:
            print(f"[Probe] Worker B failed to commit with error: {type(exc).__name__}: {exc}")
            
        # Check completed_seeds:
        total_completed = store.get_state("completed_seeds")
        print(f"[Probe] Final completed_seeds: {total_completed}")
        
        if row_after[0] == "complete" and row_after[1] is None:
            print("[BUG CONFIRMED] G-STORE-02: Stale Worker A committed and hijacked Worker B's active lease!")
            print(f"  Worker B had active lease ('worker-B', 2), but Worker A ('worker-A', 1) overwritten it to complete!")
            return True
        return False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_toctou_lease_overwrite_and_double_counting(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")
