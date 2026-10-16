#!/usr/bin/env python3
"""Read native diagnostic funnel counters on 100,000 seeds."""
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

# Reset counters
p.lib.nb_diag_reset()

N = 100_000
seeds = seeds_np(0, N, 2026101501)

print(f"Sweeping {N:,} seeds with dynamic-envelope-2048-v3 in chunks of 16,384...")
batch_size = 16384
for offset in range(0, N, batch_size):
    chunk = seeds[offset:offset + batch_size]
    with p.sweep(chunk, threads=34, retention="survivors") as batch:
        pass

# Read counters
out = p.ffi.new("uint64_t[12]")
p.lib.nb_diag_get(out)

labels = [
    ("Total Inputs", out[0]),
    ("Pass Raw Nether/Outpost/Mansion Preflight", out[1]),
    ("Pass Mansion Dark Forest Phase 1/2 Check", out[2]),
    ("Pass Mansion Macro Viable Check (>=1)", out[3]),
    ("Pass Stronghold Macro Discovery (>=1)", out[4]),
    ("Pass Outpost Macro Viable Check (>=1)", out[5]),
    ("Pass Nether Macro Viable (Fortress & Bastion >=1)", out[6]),
    ("Pass All 9 Remaining Structure Macro Floors", out[7]),
    ("Generated Candidate Grid Cells (>0 cells)", out[8]),
    ("Had >=1 Cell Meeting ALL 14 Hard Floors Simultaneously", out[9]),
    ("Had >=1 Cell Meeting All Floors + All Biomes Simultaneously", out[10]),
    ("Reached Final Anchor Selection", out[11]),
]

print("\n" + "=" * 78)
print("DYNAMIC-V3 NATIVE FUNNEL DIAGNOSTICS (100,000 SEEDS)")
print("=" * 78)
prev = out[0]
for name, val in labels:
    pct_total = (val / out[0]) * 100 if out[0] > 0 else 0.0
    pct_stage = (val / prev) * 100 if prev > 0 else 0.0
    print(f"  {name:<60}: {val:7,d} ({pct_total:6.2f}% of total, {pct_stage:6.2f}% of prev)")
    prev = val
print("=" * 78)
