#!/usr/bin/env python3
"""Instrumented test to count how many seeds pass each gate in the pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, seeds_np

cfg = dynamic_v3_blueprint_config()
p = Prototype(None, cfg)

# Run 10,000 seeds
N = 10_000
seeds = seeds_np(0, N, 2026101501)

print(f"Sweeping {N:,} seeds with complete=False, retention='survivors'...")
with p.sweep(seeds, threads=34, retention="survivors") as batch:
    print(f"Batch completed in {batch.native_seconds:.3f}s")
    print(f"Discovered anchors: {batch.pointer.discovered_anchors}")
    print(f"Retained anchors:   {batch.pointer.retained_anchors}")
    print(f"Result count:       {batch.pointer.result_count}")

    # Inspect verdicts
    anchors_count = 0
    for i in range(batch.pointer.count):
        v = batch.pointer.verdicts[i]
        if v.anchors > 0:
            anchors_count += 1
            print(f"Seed index {i} had {v.anchors} anchors, retained: {v.retained}")

    print(f"Seeds with discovered anchors > 0: {anchors_count}/{N}")

