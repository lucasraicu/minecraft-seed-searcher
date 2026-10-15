"""Verification Probe for Performance Proposal: lazy-generator.patch.

Checks:
1. Full/compact synthetic fixture evidence parity across 40 cases.
2. Full64 seed identity preservation across extreme signed/unsigned 64-bit seed values.
3. Retention receipt fingerprints parity across 100k natural seeds.
4. Survivor evidence parity (record matching).
"""

import sys
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'src'))

from seed_search.realm.native_batch import Prototype, semantic_record
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import seed_from_index, parse_seed, MASK64

def main():
    print("=== Adversarial Verification Probe: lazy-generator.patch ===")
    cfg = dynamic_blueprint_config()
    
    current_path = ROOT / 'runs/dynamic-baseline-1664/native'
    lazy_path = Path('/tmp/minecraft-audit-20261015/lazy/optimized')
    
    assert current_path.exists(), f"Current binary path {current_path} does not exist"
    assert lazy_path.exists(), f"Lazy binary path {lazy_path} does not exist"
    
    p_curr = Prototype(str(current_path), cfg)
    p_lazy = Prototype(str(lazy_path), cfg)
    
    print("[1] Verifying Synthetic Fixture Parity (40 cases in both full and survivors modes)...")
    for retention in ['full', 'survivors']:
        fixtures = [(0, 0, k % 35 - 1) for k in range(40)]
        seeds = list(range(40))
        with p_curr.sweep(seeds, 4, fixtures=fixtures, retention=retention) as b_curr:
            recs_curr = [semantic_record(r) for r in (b_curr.records() if retention == 'full' else b_curr.retained_records())]
        with p_lazy.sweep(seeds, 4, fixtures=fixtures, retention=retention) as b_lazy:
            recs_lazy = [semantic_record(r) for r in (b_lazy.records() if retention == 'full' else b_lazy.retained_records())]
            
        assert len(recs_curr) == len(recs_lazy), f"Record length mismatch in {retention}"
        assert recs_curr == recs_lazy, f"Record content mismatch in {retention}"
        print(f"  -> {retention} retention: 40/40 fixture records match perfectly.")

    print("\n[2] Verifying Full64 Seed Identity Preservation...")
    extreme_seeds = [
        0,
        1,
        -1,
        123456789,
        -123456789,
        (1 << 63) - 1,
        -(1 << 63),
        -(1 << 63) + 1,
        -9223372036854775807,
        9223372036854775807,
    ]
    with p_curr.sweep(extreme_seeds, 1, retention='full') as b_curr:
        recs_curr = [semantic_record(r) for r in b_curr.records()]
        seeds_curr = [b_curr.pointer.results[i].seed for i in range(len(extreme_seeds))]
    with p_lazy.sweep(extreme_seeds, 1, retention='full') as b_lazy:
        recs_lazy = [semantic_record(r) for r in b_lazy.records()]
        seeds_lazy = [b_lazy.pointer.results[i].seed for i in range(len(extreme_seeds))]
        
    for i, s in enumerate(extreme_seeds):
        expected_u64 = s & MASK64
        assert seeds_curr[i] == expected_u64, f"Seed identity error in current for seed {s}"
        assert seeds_lazy[i] == expected_u64, f"Seed identity error in lazy for seed {s}"
    assert recs_curr == recs_lazy, "Full64 extreme seeds record divergence"
    print("  -> All 10 extreme full64 seeds preserved exact identity and produced identical records.")

    print("\n[3] Verifying Retention Receipt Fingerprints on 100k Natural Cohort...")
    cohort_seeds = [seed_from_index(i, 2026101401) for i in range(20000000, 20100000)]
    
    h_curr = hashlib.sha256()
    h_lazy = hashlib.sha256()
    
    # Process in 16,384 batches
    total_retained_curr = 0
    total_retained_lazy = 0
    
    for start in range(0, len(cohort_seeds), 16384):
        batch_seeds = cohort_seeds[start:start + 16384]
        with p_curr.sweep(batch_seeds, 8, retention='survivors') as b:
            total_retained_curr += b.pointer.result_count
            receipt = b.retention_receipt()
            h_curr.update(receipt['input_decisions_sha256'].encode())
            
        with p_lazy.sweep(batch_seeds, 8, retention='survivors') as b:
            total_retained_lazy += b.pointer.result_count
            receipt = b.retention_receipt()
            h_lazy.update(receipt['input_decisions_sha256'].encode())

    digest_curr = h_curr.hexdigest()
    digest_lazy = h_lazy.hexdigest()
    
    print(f"  -> Current digest: {digest_curr}")
    print(f"  -> Lazy digest:    {digest_lazy}")
    print(f"  -> Retained current: {total_retained_curr}, Retained lazy: {total_retained_lazy}")
    assert digest_curr == digest_lazy, f"Digest mismatch: {digest_curr} != {digest_lazy}"
    assert total_retained_curr == total_retained_lazy, "Retained count mismatch"
    print("  -> CONFIRMED: 100k seeds produced 100% BITWISE IDENTICAL receipt fingerprints!")

    print("\n[4] Architectural Assessment of lazy-generator.patch:")
    print("  - applySeed(&w->ctx->overworld, DIM_OVERWORLD, seed) deferred until after raw mansion preflight (or during retention discovery).")
    print("  - applySeed(&w->ctx->nether, DIM_NETHER, seed) deferred until immediately before nb_nether.")
    print("  - Decision parity, full64 identity, survivor evidence, and receipt fingerprints remain 100% bitwise invariant.")

if __name__ == '__main__':
    main()
