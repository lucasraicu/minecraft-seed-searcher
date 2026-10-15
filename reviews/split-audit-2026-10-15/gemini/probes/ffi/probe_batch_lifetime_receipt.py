"""Probe to audit Batch lifetime, destructor/GC leak behavior, and receipt discovered_anchors accounting."""
import gc
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.native_batch import Prototype

def main():
    build_dir = Path("/tmp/dynamic-ffi-audit-build")
    cfg = dynamic_blueprint_config()
    proto = Prototype(build_dir, cfg)

    # Check 1: Batch lifetime and close/context manager
    print("=== Check 1: Batch context manager and close behavior ===")
    b = proto.sweep([123], fixtures=[(0, 0, -1)], retention='survivors', max_misses=2)
    assert b.pointer is not None
    ptr_val = int(proto.ffi.cast("uintptr_t", b.pointer))
    print(f"Batch allocated at pointer: {hex(ptr_val)}")

    # Verify context manager
    with b as ctx:
        assert ctx is b
        recs = ctx.retained_records(0)
        assert len(recs) == 1
    
    # After exiting with block, b.close() should have run
    assert b.pointer is None, "Batch.pointer should be None after with block exit"
    print("Batch successfully closed on context manager exit.")

    # Try calling methods on closed batch
    try:
        b.retained_records(0)
        assert False, "Should have raised ValueError on closed batch"
    except ValueError as e:
        print(f"Closed batch rejected retained_records: {e}")

    try:
        b.retention_receipt()
        assert False, "Should have raised ValueError on closed batch"
    except ValueError as e:
        print(f"Closed batch rejected retention_receipt: {e}")

    # Check 2: Destructor / GC behavior when close() is NOT called
    print("\n=== Check 2: GC behavior when close() is omitted ===")
    has_del = hasattr(b.__class__, '__del__')
    print(f"Batch class defines __del__: {has_del}")
    # Without __del__ or weakref.finalize, dropping a Batch leaks the C allocation!

    # Check 3: Receipt discovered_anchors accounting in dynamic mode
    print("\n=== Check 3: Receipt discovered_anchors in dynamic mode ===")
    with proto.sweep([42], fixtures=[(0, 0, -1)], retention='survivors', max_misses=2) as batch:
        receipt = batch.retention_receipt()
        native = batch.pointer.results[0]
        print(f"Native discovery strongholds (r.discovery.n): {native.discovery.n}")
        print(f"Native nanchors: {native.nanchors}")
        print(f"Verdict anchors (v.anchors): {batch.pointer.verdicts[0].anchors}")
        print(f"Verdict retained (v.retained): {batch.pointer.verdicts[0].retained}")
        print(f"Receipt discovered_anchors: {receipt['discovered_anchors']}")
        print(f"Receipt retained_anchors: {receipt['retained_anchors']}")

        # In dynamic mode, r.discovery.n is the count of strongholds discovered in [-2000, 2000],
        # but v.anchors recorded r.nanchors (1) instead of r.discovery.n (2)!
        if native.discovery.n != receipt['discovered_anchors']:
            print(f"DISCREPANCY CONFIRMED: r.discovery.n ({native.discovery.n}) != receipt.discovered_anchors ({receipt['discovered_anchors']})")

if __name__ == '__main__':
    main()
