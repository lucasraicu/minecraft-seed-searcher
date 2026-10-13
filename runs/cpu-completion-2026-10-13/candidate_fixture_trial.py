#!/usr/bin/env python3
"""Bounded candidate-heavy native fixture timing, parity and budget receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.seeds import seed_from_index

HERE = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--build", type=Path, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ledger", type=Path, default=HERE / "timing_budget.json")
    p.add_argument("--count", type=int, default=96)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--threads", type=int, default=34)
    p.add_argument("--natural-positive", action="store_true")
    args = p.parse_args()
    if not 1 <= args.count <= 512 or not 1 <= args.repeats <= 10 or args.count * args.repeats > 50000:
        raise ValueError("Fixture trial must stay within 50,000 processed inputs")
    if args.output.exists():
        raise ValueError("Fresh fixture receipt required")
    ledger = json.loads(args.ledger.read_text())
    spent = ledger["measured_cli_seconds"] + ledger["measured_profile_seconds"]
    if spent >= ledger["hard_cap_seconds"]:
        raise RuntimeError("Shared hard cap exhausted")
    cfg = two_group_blueprint_config()
    prototype = Prototype(args.build, cfg)
    seeds = ([seed_from_index(2_028_375)] * args.count if args.natural_positive
             else list(range(4_000_000, 4_000_000 + args.count)))
    fixtures = None if args.natural_positive else [(0, 0, 0)] * args.count
    repetitions = []
    start = time.monotonic()
    try:
        for i in range(args.repeats):
            with prototype.sweep(seeds, threads=args.threads, fixtures=fixtures,
                                 complete=not args.natural_positive,
                                 retention="survivors" if args.natural_positive else "full") as batch:
                rows = batch.summary()
                direct_hash = digest(rows)
                predicted = sum(a["qualification"] == "PREDICTED" for row in rows for a in row["anchors"])
                if predicted != args.count:
                    raise RuntimeError(f"Expected {args.count} predicted fixture candidates, got {predicted}")
                repetitions.append({"native_seconds": batch.native_seconds, "record_digest": direct_hash,
                                    "predicted": predicted})
            if time.monotonic() - start > ledger["hard_cap_seconds"] - spent:
                raise RuntimeError("Shared hard cap reached during fixture trial")
    finally:
        wall = time.monotonic() - start
        ledger["measured_profile_seconds"] += wall
        ledger["total_measured_seconds"] = ledger["measured_cli_seconds"] + ledger["measured_profile_seconds"]
        identity = json.loads((args.build / "identity.json").read_text())
        event = {"kind": "candidate_fixture_trial", "label": args.label,
                 "count": args.count, "repeats": args.repeats, "threads": args.threads,
                 "natural_positive": args.natural_positive,
                 "build": str(args.build.resolve()), "extension_sha256": identity["extension_sha256"],
                 "wall_seconds": wall, "completed_repeats": len(repetitions)}
        ledger["events"].append(event)
        args.ledger.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"event": event, "repetitions": repetitions,
            "median_native_seconds": statistics.median(x["native_seconds"] for x in repetitions) if repetitions else None,
            "all_candidate_native_summary_passed": len(repetitions) == args.repeats,
            "note": "A separate parity gate compares exact Python objects on small natural and fixture sets."}, indent=2, sort_keys=True) + "\n")
    print(args.output.read_text())


if __name__ == "__main__":
    main()
