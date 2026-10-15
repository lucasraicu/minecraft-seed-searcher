"""
Probe: Verify complete_range ignores lease ownership.
Finding ID: G-STORE-03

Tests that complete_range() does not pass a lease parameter, allowing
unauthorized commits when a range is in 'retry' status or owned by another worker.
"""
import copy
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.realm.store import RealmStore


def test_complete_range_bypasses_lease(tmp_path):
    run_dir = tmp_path / "realm_complete_range_lease"
    run_dir.mkdir(parents=True)
    
    cfg = {"search": {"workers": 1, "max_misses": 0}}
    identity = {"config": cfg, "count": 10, "start_index": 0}
    
    with RealmStore(run_dir, identity=identity) as store:
        store.configure_range(0, 10, 10)
        
        # 1. Range claimed by worker-1
        store.claim_range("worker-1")
        row = store.db.execute("SELECT status, worker, attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
        print(f"[Probe] Initially claimed by: {row}")
        assert row == ("in_progress", "worker-1", 1)
        
        # 2. Crash recovery occurs: status becomes 'retry', worker becomes NULL
        recovered = store.recover_assignments()
        assert recovered == 1
        row = store.db.execute("SELECT status, worker, attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
        print(f"[Probe] After recovery: {row}")
        assert row == ("retry", None, 1)
        
        # 3. Another worker (worker-2) claims the range
        store.claim_range("worker-2")
        row = store.db.execute("SELECT status, worker, attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
        print(f"[Probe] Reclaimed by worker-2: {row}")
        assert row == ("in_progress", "worker-2", 2)
        
        # 4. Now, the old worker-1 (or rogue caller) calls complete_range()!
        # complete_range does not pass lease, so complete_prepared receives lease=None.
        batch = [{
            "index": i,
            "seed": str(i),
            "anchors": [],
            "counts": {"anchors": 0}
        } for i in range(10)]
        
        # This SHOULD fail because worker-1's lease was revoked/reassigned to worker-2.
        # But because complete_range has lease=None, it succeeds!
        committed = store.complete_range(0, 10, batch)
        print(f"[Probe] complete_range returned: {committed}")
        
        row_final = store.db.execute("SELECT status, worker, attempts FROM ranges WHERE start='00000000000000000000'").fetchone()
        print(f"[Probe] Final range state: {row_final}")
        
        if committed is True and row_final[0] == "complete":
            print("[BUG CONFIRMED] G-STORE-03: complete_range bypassed lease ownership and committed!")
            return True
        return False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_complete_range_bypasses_lease(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")
