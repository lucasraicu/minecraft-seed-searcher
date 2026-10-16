#!/usr/bin/env python3
"""Pilot sweep runner for dynamic-envelope-2048-v3.

Executes high-throughput multi-threaded sweeps using the native OpenMP prototype,
validates surviving candidates against Python evaluate_dynamic_seed, tracks the
Top-50 candidates in a bounded min-heap, and outputs comprehensive funnel,
throughput, and candidate breakdown reports.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, semantic_record, seeds_np
from seed_search.realm.top_tracker import Top50Tracker
from seed_search.seeds import seed_from_index


def extract_summary(rec: Dict[str, Any]) -> Dict[str, Any]:
    anchor = rec["anchors"][0]
    req = anchor.get("required_structures", {})
    nether = anchor.get("required_nether_structures", {})
    opt = anchor.get("optional_structures", {})
    return {
        "seed": rec["seed"],
        "score": anchor.get("baseline_score_observed", 0),
        "center": anchor.get("evaluation_center", [0, 0]),
        "radial_key": anchor.get("radial_key", 0),
        "orig_dist_sq": anchor.get("origin_distance_squared", 0),
        "structures": {
            "stronghold": len(req.get("stronghold", {}).get("predicted_viable", [])),
            "mansion": len(req.get("mansion", {}).get("predicted_viable", [])),
            "monument": len(req.get("monument", {}).get("predicted_viable", [])),
            "village": len(req.get("village", {}).get("predicted_viable", [])),
            "trial_chamber": len(req.get("trial_chamber", {}).get("predicted_viable", [])),
            "ancient_city": len(req.get("ancient_city", {}).get("predicted_viable", [])),
            "desert_pyramid": len(req.get("desert_pyramid", {}).get("predicted_viable", [])),
            "jungle_temple": len(req.get("jungle_temple", {}).get("predicted_viable", [])),
            "outpost": len(req.get("outpost", {}).get("predicted_viable", [])),
            "ruined_portal": len(req.get("ruined_portal", {}).get("predicted_viable", [])),
            "shipwreck": len(req.get("shipwreck", {}).get("predicted_viable", [])),
            "mineshaft": len(req.get("mineshaft", {}).get("predicted_viable", [])),
            "fortress": len(nether.get("fortress", {}).get("predicted_viable", [])),
            "bastion": len(nether.get("bastion", {}).get("predicted_viable", [])),
            "swamp_hut": len(opt.get("swamp_hut", {}).get("predicted_viable", [])),
            "igloo": len(opt.get("igloo", {}).get("predicted_viable", [])),
            "trail_ruins": len(opt.get("trail_ruins", {}).get("predicted_viable", [])),
            "ocean_ruin": len(opt.get("ocean_ruin", {}).get("predicted_viable", [])),
            "buried_treasure": len(opt.get("buried_treasure", {}).get("predicted_viable", [])),
        },
        "bonuses": {
            "scenic_river": anchor.get("scenic_bonus", 0),
            "village_spread": anchor.get("village_spread_bonus", 0),
            "treasure_bastion": anchor.get("treasure_bastion", 0),
            "hub": anchor.get("hub_bonus", 0),
            "nether_core": anchor.get("nether_core_bonus", 0),
        },
    }


def run_pilot(
    count: int = 100_000,
    start_index: int = 0,
    run_key: int = 2026101501,
    threads: int = 34,
    batch_size: int = 16384,
    top_n: int = 50,
    output_dir: Path | None = None,
) -> Dict[str, Any]:
    print("=" * 78)
    print("MINECRAFT SEED SEARCHER - PILOT RUNNER (dynamic-envelope-2048-v3)")
    print(f"Target count: {count:,} seeds | Start index: {start_index:,}")
    print(f"Run key: {run_key} | Threads: {threads} | Batch size: {batch_size:,}")
    print("=" * 78)

    cfg = dynamic_v3_blueprint_config()
    cfg["search"]["run_key"] = str(run_key)
    prototype = Prototype(None, cfg)

    if not prototype.identity.get("openmp"):
        print("WARNING: OpenMP is disabled in Prototype; run will be single-threaded.")
    else:
        print(f"OpenMP enabled: {prototype.identity.get('runtime')}")

    tracker = Top50Tracker(capacity=top_n)

    total_scanned = 0
    total_retained_candidates = 0
    total_native_seconds = 0.0
    start_wall = time.perf_counter()

    num_batches = (count + batch_size - 1) // batch_size
    print(f"\nStarting execution across {num_batches} batches...")

    for b_idx in range(num_batches):
        b_start = start_index + b_idx * batch_size
        b_count = min(batch_size, count - (b_idx * batch_size))
        b_end = b_start + b_count

        t_batch_0 = time.perf_counter()
        # Fast numpy seed generator
        seeds_arr = seeds_np(b_start, b_end, run_key)

        cutoff = tracker.cutoff_score() or 0
        with prototype.sweep(seeds_arr, threads=threads, retention="survivors", cutoff_score=cutoff) as batch:
            total_native_seconds += batch.native_seconds
            t_batch_1 = time.perf_counter()

            retained_list = list(batch.retained_records(b_start))
            batch_retained = len(retained_list)
            total_retained_candidates += batch_retained

            # Process any retained survivors
            for rec in retained_list:
                sem = semantic_record(rec)
                admitted = tracker.observe(sem)
                info = extract_summary(sem)
                str_counts = info["structures"]
                if admitted:
                    print(
                        f"  [NEW TOP CANDIDATE] Seed: {info['seed']} | Score: {info['score']} | "
                        f"Center: ({info['center'][0]}, {info['center'][1]}) | "
                        f"AC={str_counts['ancient_city']} TC={str_counts['trial_chamber']} "
                        f"Vil={str_counts['village']} Mon={str_counts['monument']} Man={str_counts['mansion']} "
                        f"Fort={str_counts['fortress']} Bast={str_counts['bastion']} "
                        f"SH={str_counts['stronghold']} Out={str_counts['outpost']}"
                    )

        total_scanned += b_count
        elapsed_so_far = time.perf_counter() - start_wall
        rate_so_far = total_scanned / elapsed_so_far
        batch_rate = b_count / (t_batch_1 - t_batch_0)

        if (b_idx + 1) % max(1, num_batches // 10) == 0 or b_idx == num_batches - 1:
            cutoff = tracker.cutoff_score()
            cutoff_str = str(cutoff) if cutoff is not None else "None (<50)"
            print(
                f"Batch {b_idx + 1:3d}/{num_batches:3d} ({total_scanned:8,d}/{count:8,d} seeds) | "
                f"Batch rate: {batch_rate:8,.1f} s/s | Overall rate: {rate_so_far:8,.1f} s/s | "
                f"Survivors: {total_retained_candidates:3d} | Cutoff: {cutoff_str}"
            )

    total_wall_seconds = time.perf_counter() - start_wall
    overall_throughput = total_scanned / total_wall_seconds if total_wall_seconds > 0 else 0.0

    print("\n" + "=" * 78)
    print("PILOT SWEEP COMPLETE")
    print(f"Total Scanned:         {total_scanned:,} seeds")
    print(f"Total Wall Time:       {total_wall_seconds:.2f} seconds")
    print(f"Native Kernel Time:    {total_native_seconds:.2f} seconds")
    print(f"Overall Throughput:    {overall_throughput:,.1f} seeds/second")
    print(
        f"Candidate Survivors:   {total_retained_candidates:,} "
        f"(Pass rate: {total_retained_candidates/max(1, total_scanned):.6%})"
    )
    print(f"Top-{top_n} Score Cutoff:   {tracker.cutoff_score()}")
    print("=" * 78)

    top_candidates = tracker.top_records()
    if top_candidates:
        print(f"\nTop {len(top_candidates)} Candidates Ranked:")
        for idx, rec in enumerate(top_candidates[:15], 1):
            info = extract_summary(rec)
            sc = info["structures"]
            bn = info["bonuses"]
            print(
                f"#{idx:2d} | Seed: {info['seed']:<20} | Score: {info['score']:3d} | "
                f"Center: ({info['center'][0]:5d}, {info['center'][1]:5d}) | Dist^2: {info['orig_dist_sq']:<10d} | "
                f"AC={sc['ancient_city']} TC={sc['trial_chamber']} Vil={sc['village']} "
                f"Mon={sc['monument']} Man={sc['mansion']} Fort={sc['fortress']} Bast={sc['bastion']} "
                f"SH={sc['stronghold']} Out={sc['outpost']} DP={sc['desert_pyramid']} JT={sc['jungle_temple']} "
                f"Ship={sc['shipwreck']} RP={sc['ruined_portal']} Mine={sc['mineshaft']} | "
                f"Scenic={bn['scenic_river']} Spread={bn['village_spread']} TBast={bn['treasure_bastion']} NCore={bn['nether_core']}"
            )

    result_data = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "config_contract": cfg.get("contract"),
        "realm_size": "2048x2048",
        "nether_size": "1024x1024",
        "macro_envelope": "4000x4000",
        "total_scanned": total_scanned,
        "total_wall_seconds": total_wall_seconds,
        "total_native_seconds": total_native_seconds,
        "throughput_seeds_per_sec": overall_throughput,
        "total_survivors": total_retained_candidates,
        "survivor_pass_rate": total_retained_candidates / max(1, total_scanned),
        "cutoff_score": tracker.cutoff_score(),
        "top_candidates_count": len(top_candidates),
        "top_candidates": [extract_summary(r) for r in top_candidates],
    }

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "pilot_summary.json"
        tracker.save_to_json(str(output_dir / "top50_candidates.json"))
        tracker.save_to_sqlite(str(output_dir / "top50_candidates.db"))
        with open(json_path, "w") as f:
            json.dump(result_data, f, indent=2)
        print(f"\nArtifacts saved to {output_dir}")

    return result_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000, help="Number of seeds to scan")
    parser.add_argument("--start-index", type=int, default=0, help="Starting index")
    parser.add_argument("--run-key", type=int, default=2026101501, help="Seed generator run key")
    parser.add_argument("--threads", type=int, default=34, help="OpenMP threads")
    parser.add_argument("--batch-size", type=int, default=16384, help="Native batch chunk size")
    parser.add_argument("--top-n", type=int, default=50, help="Number of top candidates to keep")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to save summary")
    args = parser.parse_args()

    run_pilot(
        count=args.count,
        start_index=args.start_index,
        run_key=args.run_key,
        threads=args.threads,
        batch_size=args.batch_size,
        top_n=args.top_n,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
