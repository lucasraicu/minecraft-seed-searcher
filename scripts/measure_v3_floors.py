#!/usr/bin/env python3
"""Measure exact stage-by-stage drop-offs for dynamic-v3 using native diagnostic counters."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, seeds_np

STAGE_NAMES = [
    "1. Inputs scanned",
    "2. Passed Step 1A PRNG preflight",
    "3. Passed Mansion dark forest filter",
    "4. Passed Mansion macro viability",
    "5. Passed Stronghold macro discovery",
    "6. Passed Outpost macro viability",
    "7. Passed Nether (Fortress & Bastion)",
    "8. Passed All 14 Structures macro",
    "9. Had candidate sliding cells",
    "10. Had cells satisfying hard floors",
    "11. Had cells satisfying biomes",
    "12. Reached anchor qualification",
]


def measure_floors(
    count: int = 50_000,
    threads: int | None = None,
    run_key: int = 2026101501,
    native_build: Path | str | None = None,
):
    if threads is None:
        threads = min(34, os.cpu_count() or 4)

    if native_build is None:
        p2048 = ROOT / "runs/dynamic-baseline-2048/native"
        p1664 = ROOT / "runs/dynamic-baseline-1664/native"
        native_build = p2048 if (p2048 / "identity.json").exists() else p1664

    cfg = dynamic_v3_blueprint_config()
    seeds = seeds_np(0, count, run_key)

    p = Prototype(Path(native_build), cfg)
    p.lib.nb_diag_reset()

    print("=" * 82)
    print(f"STAGE-BY-STAGE V3 FUNNEL MEASUREMENT ON {count:,} SEEDS ({threads} threads)")
    print(f"Native build: {native_build}")
    print("=" * 82)

    t0 = time.perf_counter()
    with p.sweep(seeds, threads=threads, retention="survivors") as batch:
        retained = len(list(batch.retained_records(0)))
    t1 = time.perf_counter()

    out = p.ffi.new("uint64_t[12]")
    p.lib.nb_diag_get(out)

    elapsed = t1 - t0
    rate = count / elapsed if elapsed > 0 else 0.0

    print(f"{'Stage':<42} | {'Count':>9} | {'Cumulative %':>12} | {'Marginal %':>10}")
    print("-" * 82)

    prev = count
    for i in range(12):
        c = out[i]
        cum_pct = (c / count) * 100.0 if count > 0 else 0.0
        marg_pct = (c / prev) * 100.0 if prev > 0 else 0.0
        prev = c
        print(f"{STAGE_NAMES[i]:<42} | {c:9,d} | {cum_pct:11.4f}% | {marg_pct:9.2f}%")

    print("=" * 82)
    print(f"Retained survivors : {retained:,} ({retained / count * 100:.5f}%)")
    print(f"Execution time     : {elapsed:.2f}s ({rate:,.1f} seeds/sec)")
    print("=" * 82)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=50_000, help="Number of seeds to measure (default: 50,000)")
    parser.add_argument("--threads", type=int, default=None, help="Thread count (default: min(34, cpu_count))")
    parser.add_argument("--run-key", type=int, default=2026101501, help="Seed run key")
    parser.add_argument("--native-build", type=str, default=None, help="Path to native build directory")
    args = parser.parse_args()

    measure_floors(
        count=args.count,
        threads=args.threads,
        run_key=args.run_key,
        native_build=args.native_build,
    )


if __name__ == "__main__":
    main()

