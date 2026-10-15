"""Probe to test race conditions in Prototype encoder caching across concurrent threads."""
import concurrent.futures
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import outpost_blueprint_config, validate_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.native_encoding import locked_records
from seed_search.realm.store import RealmStore

def worker(proto, seeds, fixtures, synthetic, store, tid, results):
    for i in range(10):
        with proto.sweep(seeds, threads=1, fixtures=fixtures if synthetic else None, retention='full') as batch:
            recs = locked_records(batch, start_index=tid*1000 + i*len(seeds), store=store)
            assert len(recs) == len(seeds)
            for r in recs:
                if hasattr(r, 'summary'):
                    row = json.loads(r.summary)
                    proto_meta = row.get('prototype')
                else:
                    proto_meta = r.get('prototype')
                if proto_meta:
                    if proto_meta.get('synthetic') != synthetic:
                        results.append(f"Thread {tid} synthetic mismatch: expected {synthetic}, got {proto_meta.get('synthetic')}")

def main():
    build_dir = Path("/tmp/dynamic-ffi-audit-build")
    cfg = outpost_blueprint_config()
    proto = Prototype(build_dir, cfg)

    import shutil
    db_path = Path("reviews/split-audit-2026-10-15/gemini/probes/ffi/tmp_store_run")
    if db_path.exists(): shutil.rmtree(db_path)
    store = RealmStore(db_path, identity={'config': cfg})

    seeds_real = [1000 + i for i in range(8)]
    seeds_synth = [2000 + i for i in range(8)]
    fixtures = [(0, 0, 1)] * 8

    print("Testing concurrent locked_records calls with synthetic vs real batches...")
    errors = []
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f1 = [executor.submit(worker, proto, seeds_real, None, False, store, 0, results) for _ in range(2)]
        f2 = [executor.submit(worker, proto, seeds_synth, fixtures, True, store, 1, results) for _ in range(2)]
        for f in concurrent.futures.as_completed(f1 + f2):
            try:
                f.result()
            except Exception as e:
                errors.append(e)
                print(f"Error: {e}")

    store.close()
    if results:
        print(f"FAILED with {len(results)} metadata cross-contamination errors:")
        for res in results[:5]:
            print(f"  {res}")
    elif errors:
        print(f"FAILED: {len(errors)} errors")
    else:
        print("Completed without errors.")

if __name__ == '__main__':
    main()
