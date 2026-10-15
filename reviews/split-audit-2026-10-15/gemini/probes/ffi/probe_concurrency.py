"""Probe to audit call-local policy isolation under concurrent calls through a shared Prototype."""
import concurrent.futures
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config, validate_config
from seed_search.realm.native_batch import Prototype

def worker_full(proto, seeds, tid):
    for i in range(5):
        with proto.sweep(seeds, threads=1, retention='full') as batch:
            recs = batch.records()
            assert len(recs) == len(seeds)
            assert batch.retention == 'full'
            assert batch.max_misses == 0

def worker_survivors(proto, seeds, fixtures, tid):
    for i in range(5):
        with proto.sweep(seeds, threads=1, fixtures=fixtures, retention='survivors', max_misses=2) as batch:
            recs = batch.retained_records()
            assert batch.retention == 'survivors'
            assert batch.max_misses == 2

def main():
    build_dir = Path("/tmp/dynamic-ffi-audit-build")
    cfg = dynamic_blueprint_config()
    proto = Prototype(build_dir, cfg)

    seeds1 = [1000 + i for i in range(16)]
    seeds2 = [2000 + i for i in range(16)]
    fixtures2 = [(0, 0, -1)] * 16

    print("Launching concurrent workers against shared Prototype...")
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for tid in range(4):
            futures.append(executor.submit(worker_full, proto, seeds1, tid))
        for tid in range(4):
            futures.append(executor.submit(worker_survivors, proto, seeds2, fixtures2, tid))
        
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception as e:
                errors.append(e)
                print(f"Worker error: {e}")

    if not errors:
        print("PASS: Concurrent calls through shared Prototype completed without exceptions.")
    else:
        print(f"FAIL: {len(errors)} errors occurred during concurrent sweep.")

if __name__ == '__main__':
    main()
