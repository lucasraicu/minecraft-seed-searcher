"""Probe to audit retained survivor record evidence completeness and parity."""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config, validate_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.blueprint import evaluate_seed
from test_dynamic_baseline import DynamicFixtureBackend

def main():
    build_dir = Path("/tmp/dynamic-ffi-audit-build")
    build_dir.mkdir(exist_ok=True)
    build(build_dir)
    cfg = dynamic_blueprint_config()
    validate_config(cfg)
    proto = Prototype(build_dir, cfg)

    # Test 1: Full survivor with no missing structures (missing=-1)
    # under retention='survivors' and retention='full'
    print("=== Testing survivor retention with missing=-1 ===")
    with proto.sweep([42], fixtures=[(0, 0, -1)], retention='survivors', max_misses=2) as batch:
        survivor_records = batch.retained_records(start_index=100)
        receipt = batch.retention_receipt()
    
    print(f"Retained count: {len(survivor_records)}")
    print(f"Receipt: {receipt}")
    rec = survivor_records[0]
    anchor = rec['anchors'][0]
    print(f"Anchor keys: {sorted(anchor.keys())}")
    print(f"Required structures: {list(anchor['required_structures'].keys())}")
    print(f"Optional structures: {list(anchor['optional_structures'].keys())}")
    print(f"Qualification: {anchor.get('qualification')}")
    print(f"Deficit categories: {anchor.get('deficit_categories')}")
    print(f"Score: {anchor.get('baseline_score_observed')}")
    print(f"Retention metadata: {anchor.get('retention')}")

    # Check optional structures in anchor
    for opt_name, opt_ob in anchor['optional_structures'].items():
        print(f"Optional {opt_name}: viable={len(opt_ob['predicted_viable'])}, raw={len(opt_ob['raw'])}, complete={opt_ob.get('complete')}, count_is_complete={opt_ob.get('count_is_complete')}")

    # Compare against full retention
    with proto.sweep([42], fixtures=[(0, 0, -1)], retention='full') as batch_full:
        full_records = batch_full.records(start_index=100)
    full_anchor = full_records[0]['anchors'][0]

    # Check differences between full and survivor records
    print("\n=== Differences between full and survivor records ===")
    all_keys = set(anchor.keys()) | set(full_anchor.keys())
    for k in sorted(all_keys):
        if k not in anchor:
            print(f"Key missing in survivor: {k}")
        elif k not in full_anchor:
            print(f"Key only in survivor: {k}")
        elif anchor[k] != full_anchor[k]:
            print(f"Key difference for {k}: survivor={type(anchor[k])} full={type(full_anchor[k])}")

    # Test 2: Deficit test (e.g. missing 1 village, slot 5)
    print("\n=== Testing survivor retention with missing village (slot 5) ===")
    with proto.sweep([43], fixtures=[(0, 0, 5)], fixture_masks=[0], retention='survivors', max_misses=2) as batch_def:
        retained_def = batch_def.retained_records(start_index=200)
    rec_def = retained_def[0]
    anc_def = rec_def['anchors'][0]
    print(f"Deficit categories: {anc_def.get('deficit_categories')}")
    print(f"Qualification: {anc_def.get('qualification')}")
    print(f"Pending reasons: {anc_def.get('pending_reasons')}")
    print(f"Retention: {anc_def.get('retention')}")

if __name__ == '__main__':
    main()
