"""
Audit probe for Task 4: In-flight batch bounds in src/seed_search/realm/native_batch.py.
Verifies whether the actual number of concurrently active batches exceeds the configured inflight limit by 1.
"""
import sys
import time
import tempfile
import shutil
from pathlib import Path
from collections import deque

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.native_batch import Prototype, run_native_scan, persist_pipeline
from seed_search.realm.store import RealmStore

def test_inflight_queue_logic():
    print("=== Task 4 Probe: In-Flight Batch Bounds Audit ===")
    
    # Model and trace the exact queuing loop from native_batch.py:
    # Lines 501-532:
    #   while len(pending)<inflight and submit(store):pass
    #   while pending:
    #       first,end,attempt,future,queued,native_future=pending.popleft()
    #       while len(pending)<inflight and submit(store):pass
    #       ...
    #       store.complete_prepared(...)
    #       native_futures.discard(native_future)
    
    for inflight_limit in [2, 3]:
        print(f"\n--- Testing Configured inflight = {inflight_limit} ---")
        
        pending = deque()
        native_futures = set()
        active_uncompleted_batches = set()
        max_concurrent_active = 0
        max_len_pending = 0
        
        batch_counter = 0
        total_batches = 10
        
        def mock_submit():
            nonlocal batch_counter, max_len_pending
            if batch_counter >= total_batches:
                return False
            batch_id = batch_counter
            batch_counter += 1
            
            # Simulated submission:
            native_future = f"native_future_{batch_id}"
            native_futures.add(native_future)
            active_uncompleted_batches.add(batch_id)
            future = f"prepared_future_{batch_id}"
            pending.append((batch_id, future, native_future))
            
            max_len_pending = max(max_len_pending, len(pending))
            return True

        # Initial queue fill: line 501
        while len(pending) < inflight_limit and mock_submit():
            pass
        
        print(f"After initial submit loop: len(pending)={len(pending)}, active_batches={len(active_uncompleted_batches)}")
        
        # Main loop: line 502
        while pending:
            # Line 503: Pop oldest batch to process
            batch_id, future, native_future = pending.popleft()
            
            # Line 504: IMMEDIATELY refill pending BEFORE popped batch is processed!
            while len(pending) < inflight_limit and mock_submit():
                pass
            
            # Check concurrency right while popped batch is being prepared and written:
            # Lines 505-521: The popped batch is resolving, preparing, writing to DB.
            current_concurrent_active = len(active_uncompleted_batches)
            max_concurrent_active = max(max_concurrent_active, current_concurrent_active)
            current_native_futures = len(native_futures)
            
            print(f"  Processing batch {batch_id}: len(pending)={len(pending)}, len(native_futures)={current_native_futures}, active_batches={current_concurrent_active}")
            
            # Line 522: Only now is the batch complete and native_future discarded
            active_uncompleted_batches.remove(batch_id)
            native_futures.discard(native_future)
            
            # Line 532: refill again if needed
            while len(pending) < inflight_limit and mock_submit():
                pass
        
        print(f"\nResult for inflight = {inflight_limit}:")
        print(f"  Configured inflight limit:       {inflight_limit}")
        print(f"  Reported max_pending:            {max_len_pending}")
        print(f"  Actual peak concurrent active:   {max_concurrent_active}")
        print(f"  Actual peak native_futures:      {max_concurrent_active}")
        
        if max_concurrent_active == inflight_limit + 1:
            print(f"  CONFIRMED: Actual in-flight batches exceeded limit by 1 ({max_concurrent_active} > {inflight_limit})!")
        else:
            print("  DID NOT EXCEED")

def test_live_scan_inflight():
    print("\n=== Live Pipeline Scan In-Flight Test ===")
    
    cfg = dynamic_blueprint_config()
    proto = Prototype(None, cfg)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_run'
        
        print("Running live scan with inflight=2, count=8, batch_size=2...")
        try:
            result = persist_pipeline(
                proto, db_path, count=8, batch_size=2, threads=1, inflight=2,
                retention='survivors'
            )
            print(f"Scan finished. Newly committed: {result['newly_committed']}")
            print(f"Reported max_outstanding_batches: {result['max_outstanding_batches']}")
        except RuntimeError as e:
            if "Process-tree monitoring unavailable" in str(e):
                print(f"Live process tree inspection note: {e} (run with BypassSandbox on macOS to bypass sandboxed ps)")
            else:
                raise

if __name__ == '__main__':
    test_inflight_queue_logic()
    test_live_scan_inflight()
