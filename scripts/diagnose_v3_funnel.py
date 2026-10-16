#!/usr/bin/env python3
"""Diagnostic tool to inspect stage-by-stage funnel pass rates for dynamic-v3."""
from __future__ import annotations

import argparse
from collections import Counter
import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.backend import Backend
from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.seeds import seed_from_index


def diagnose(count: int = 5000, start_index: int = 0, run_key: int = 2026101501):
    cfg = dynamic_v3_blueprint_config()
    cfg["search"]["run_key"] = str(run_key)
    floors = cfg["structures"]["hard_floors"]

    print("=" * 78)
    print(f"DIAGNOSING V3 FILTER FUNNEL ON {count:,} SEEDS (single-seed detailed probe)")
    print("=" * 78)

    counts_total = Counter()
    macro_viable_counts = {k: [] for k in floors}
    macro_viable_pass = Counter()
    survivors = 0

    t0 = time.perf_counter()

    ow_macro = tuple(cfg["discovery"]["overworld_bounds"])
    nw_macro = tuple(cfg["discovery"]["nether_bounds"])

    for i in range(count):
        seed = seed_from_index(start_index + i, run_key)
        counts_total["scanned"] += 1

        # Macro observations via Backend
        counts = {}
        with Backend(seed) as b:
            for name in floors:
                bounds = nw_macro if name in ("fortress", "bastion") else ow_macro
                st = b.structures(name, bounds)
                counts[name] = len(st)

        all_floors_met_macro = True
        for name, floor in floors.items():
            c = counts.get(name, 0)
            if c >= floor:
                macro_viable_pass[name] += 1
            else:
                all_floors_met_macro = False

        if all_floors_met_macro:
            counts_total["macro_all_floors"] += 1

        # Evaluate full dynamic pipeline with short_circuit=False
        res = evaluate_dynamic_seed(i, seed, cfg, short_circuit=False)
        if res.get("anchors"):
            survivors += 1
            anchor = res["anchors"][0]
            print(f"FOUND QUALIFYING SEED at index {i}: {seed} (Score: {anchor['baseline_score_observed']})")

    t1 = time.perf_counter()

    print("\n--- MACRO-ENVELOPE PASS RATES (Structures existing anywhere in 4000x4000) ---")
    for name, floor in floors.items():
        passed = macro_viable_pass[name]
        pct = (passed / count) * 100
        print(f"  {name:<16}: floor={floor:2d} | passed: {passed:5d}/{count:5d} ({pct:6.2f}%)")

    print("\n--- JOINT PASS RATES ---")
    print(f"  All 14 floors present in 4000x4000 macro-envelope: {counts_total['macro_all_floors']}/{count} "
          f"({counts_total['macro_all_floors']/count*100:.3f}%)")
    print(f"  Final realm survivors (all 14 floors + all biomes in ONE 2048x2048 realm): {survivors}/{count} "
          f"({survivors/count*100:.4f}%)")
    print(f"Elapsed: {t1-t0:.2f}s ({(count/(t1-t0)):.1f} seeds/sec)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    args = parser.parse_args()
    diagnose(args.count)

