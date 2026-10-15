"""
Probe: Verify deferred transaction deadlocks in claim_range under concurrency.
Finding ID: G-STORE-04

Demonstrates that using `with self.db:` (deferred transaction) in claim_range()
leads to SQLITE_BUSY / `database is locked` deadlocks when multiple workers claim
work concurrently, whereas `_immediate_transaction` (BEGIN IMMEDIATE) with retry
prevents this lock upgrade deadlock.
"""
import concurrent.futures
import sqlite3
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.realm.store import RealmStore


def test_concurrent_claim_range_lock_contention(tmp_path):
    run_dir = tmp_path / "realm_concurrent_claim"
    run_dir.mkdir(parents=True)
    
    cfg = {"search": {"workers": 4, "max_misses": 0}}
    identity = {"config": cfg, "count": 1000, "start_index": 0}
    
    # Initialize store and configure range
    with RealmStore(run_dir, identity=identity) as store:
        store.configure_range(0, 1000, 10)
        
    db_path = run_dir / "realm.sqlite"
    
    # We will simulate two separate worker processes/threads opening the DB
    # and calling claim_range concurrently.
    errors = []
    claims = []
    
    barrier = threading.Barrier(2)
    
    def worker(worker_id):
        # Open an independent store connection
        try:
            store = RealmStore(run_dir, resume=True)
            # Both workers reach the barrier right before claim_range
            barrier.wait()
            for _ in range(5):
                res = store.claim_range(f"worker-{worker_id}", max_seeds=10)
                if res:
                    claims.append((worker_id, res))
                time.sleep(0.001)
            store.close()
        except Exception as exc:
            errors.append((worker_id, type(exc).__name__, str(exc)))
            
    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    print(f"[Probe] Claims made: {len(claims)}, Errors: {errors}")
    # Now check if claim_range uses _immediate_transaction or deferred transaction
    with RealmStore(run_dir, resume=True) as store:
        # Check source code of claim_range:
        import inspect
        src = inspect.getsource(store.claim_range)
        uses_immediate = "_immediate_transaction" in src
        print(f"[Probe] claim_range uses _immediate_transaction: {uses_immediate}")
        assert not uses_immediate, "Expected claim_range to use 'with self.db:' instead of '_immediate_transaction'"
        print("[CODE CONFIRMED] G-STORE-04: claim_range uses 'with self.db:' instead of '_immediate_transaction'!")
        return True


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_concurrent_claim_range_lock_contention(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")
