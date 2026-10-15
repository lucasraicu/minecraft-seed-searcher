"""
Probe: Verify SQLite connection thread confinement and preparation thread safety.
Finding ID: G-STORE-07

Verifies that store.db enforces thread confinement (check_same_thread=True),
that passing store to the preparer thread in native_batch.py violates thread
isolation boundaries if store.db is ever touched, and tests whether preparation
runs cleanly off-thread without database access.
"""
import concurrent.futures
import sqlite3
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.realm.store import RealmStore


def test_thread_confinement_and_preparation(tmp_path):
    run_dir = tmp_path / "realm_thread_confinement"
    run_dir.mkdir(parents=True)
    
    cfg = {"search": {"workers": 1, "max_misses": 0}}
    identity = {"config": cfg, "count": 10, "start_index": 0}
    
    with RealmStore(run_dir, identity=identity) as store:
        # 1. Verify that self.db enforces check_same_thread=True
        error_caught = False
        def access_from_other_thread():
            nonlocal error_caught
            try:
                store.db.execute("SELECT 1")
            except sqlite3.ProgrammingError as exc:
                print(f"[Probe] Expected ProgrammingError caught when accessing store.db from another thread: {exc}")
                error_caught = True
                
        t = threading.Thread(target=access_from_other_thread)
        t.start()
        t.join()
        assert error_caught, "Expected sqlite3.ProgrammingError on cross-thread connection access"
        
        # 2. Verify that prepare_range runs cleanly on an off-thread worker
        # without touching self.db
        batch = [{
            "index": i,
            "seed": str(i),
            "anchors": [],
            "counts": {"test": 1}
        } for i in range(5)]
        
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(store.prepare_range, 0, 5, batch)
        prepared = future.result()
        pool.shutdown()
        
        assert prepared.start == 0 and prepared.end == 5
        print(f"[Probe] prepare_range executed successfully on thread without touching store.db.")
        
        # 3. Demonstrate the hazard: in native_batch.py line 485:
        # preparer.submit(prepare, native_future, first, end, store)
        # store is passed across thread boundary. If a helper or debug hook
        # invokes store.get_state('schema') or store.status():
        def dangerous_preparer_hook():
            try:
                return store.get_state("range")
            except sqlite3.ProgrammingError as exc:
                return f"CRASH: {exc}"
                
        hook_future = concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(dangerous_preparer_hook)
        res = hook_future.result()
        print(f"[Probe] Cross-thread call to store.get_state() resulted in: {res}")
        assert "CRASH" in res
        
        print("[AUDIT CONFIRMED] G-STORE-07: RealmStore.db is strictly thread-confined. Passing store instance to preparer thread creates fragile coupling across thread boundaries.")
        return True


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_thread_confinement_and_preparation(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")
