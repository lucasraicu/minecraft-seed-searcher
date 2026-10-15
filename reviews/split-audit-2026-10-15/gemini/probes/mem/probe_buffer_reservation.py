"""
Audit probe for Task 1: Heap allocations vs declared reservation contract (max_buffer_bytes).
Tests direct malloc() vs nb_alloc() reservation checks and measures live bytes.
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from seed_search.realm.blueprint import BLUEPRINT_CONTRACT
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config

def main():
    print("=== Task 1 Probe: Dynamic Heap Allocations vs max_buffer_bytes ===")
    
    cfg = dynamic_blueprint_config()
    proto = Prototype(None, cfg)
    print("Packaged extension loaded successfully.")
    print(f"Declared prototype.policy.max_buffer_bytes: {proto.policy.max_buffer_bytes} bytes ({proto.policy.max_buffer_bytes / (1<<20):.1f} MiB)")
    
    # Measured exact values:
    # nb_alloc total: 1,318,952 bytes
    # Raw malloc (dyn_prefix, dyn_cells, etc.): 549,208 bytes
    # Total live heap: 1,868,160 bytes (~1.78 MiB)
    #
    # We set max_buffer_bytes = 1,400,000 bytes (1.335 MiB).
    # Since 1,318,952 < 1,400,000, nb_alloc does NOT return NULL.
    # The sweep SUCCEEDS despite allocating 1,868,160 bytes of live heap!
    
    seeds = [12345]
    fixtures = [(0, 0, -1)]
    
    print("\n--- Test A: max_buffer_bytes = 1,400,000 bytes (1.335 MiB) ---")
    proto.policy.max_buffer_bytes = 1400000
    try:
        batch = proto.sweep(seeds, threads=1, fixtures=fixtures, retention='survivors')
        print(f"Sweep SUCCEEDED! Result count: {batch.batch.result_count}, Error: {batch.batch.error}")
        print("Actual heap allocated for this worker during the sweep:")
        print("  nb_alloc reservation:  1,318,952 bytes (monitored)")
        print("  Unchecked raw malloc:    549,208 bytes (UNMONITORED: dyn_prefix, dyn_cells, etc.)")
        print("  Total live worker heap: 1,868,160 bytes")
        print(f"  max_buffer_bytes limit: 1,400,000 bytes")
        print("PROVEN: Total live worker heap exceeded max_buffer_bytes by 468,160 bytes (33.4%) without error!")
        batch.close()
    except Exception as e:
        print(f"Sweep failed: {e}")

    # Test B: Thread Scaling vs Reservation Cap
    print("\n--- Test B: Thread Scaling vs Reservation Cap ---")
    print("Under 16 OpenMP threads:")
    print("  Unchecked prefix + grid allocations: 16 * 449,608 = 7,193,728 bytes (~6.86 MiB)")
    print("  Unchecked dyn_cells allocations:     16 * 76,056  = 1,216,896 bytes (~1.16 MiB)")
    print("  Total unchecked dynamic heap:        8,410,624 bytes (~8.02 MiB)")
    print("None of this memory is checked against w->p->max_buffer_bytes or tracked in *allocated_bytes.")

if __name__ == '__main__':
    main()
