#!/usr/bin/env python3
"""One-process memory reuse observation over 49,664 inputs, including positives."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.seeds import seed_from_index

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--build", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ledger", type=Path, default=HERE / "timing_budget.json")
    args = p.parse_args()
    if args.output.exists():
        raise ValueError("Fresh receipt required")
    ledger = json.loads(args.ledger.read_text())
    spent = ledger["measured_cli_seconds"] + ledger["measured_profile_seconds"]
    if spent >= ledger["hard_cap_seconds"]:
        raise RuntimeError("Shared hard cap exhausted")
    prototype = Prototype(args.build, two_group_blueprint_config())
    pid = os.getpid()
    samples = []
    started = time.monotonic()
    try:
        for batch_index in range(97):
            first = 3_000_000 + batch_index * 512
            seeds = [seed_from_index(i) for i in range(first, first + 512)]
            seeds[0]=seed_from_index(2_028_375)
            with prototype.sweep(seeds, threads=34, retention="survivors") as batch:
                retained = batch.pointer.result_count
                native_seconds = batch.native_seconds
                records=batch.retained_records()
                if not any(r['seed']==str(seeds[0]) for r in records):
                    raise RuntimeError('Known positive absent from memory check')
            rss_kib = int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)], text=True).strip())
            samples.append({"first_index": first, "completed": 512,
                            "retained": retained, "native_seconds": native_seconds,
                            "rss_after_free_bytes": rss_kib * 1024})
            time.sleep(0.5)
            if time.monotonic() - started > ledger["hard_cap_seconds"] - spent:
                raise RuntimeError("Shared hard cap reached during soak")
    finally:
        wall = time.monotonic() - started
        ledger["measured_profile_seconds"] += wall
        ledger["total_measured_seconds"] = ledger["measured_cli_seconds"] + ledger["measured_profile_seconds"]
        identity = json.loads((args.build / "identity.json").read_text())
        event = {"kind": "memory_soak", "inputs": 49664, "batches": 97,
                 "build": str(args.build.resolve()), "extension_sha256": identity["extension_sha256"],
                 "wall_seconds": wall, "completed_batches": len(samples)}
        ledger["events"].append(event)
        args.ledger.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"event": event, "samples": samples,
                "rss_after_free_range_bytes": [min(s["rss_after_free_bytes"] for s in samples),
                                               max(s["rss_after_free_bytes"] for s in samples)] if samples else None},
            indent=2, sort_keys=True) + "\n")
    print(args.output.read_text())


if __name__ == "__main__":
    main()
