#!/usr/bin/env python3
"""Find the exact seed that passed all 14 hard floors in the 100k sweep."""
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

N = 100_000
seeds = seeds_np(0, N, 2026101501)
batch_size = 1000

for offset in range(0, N, batch_size):
    chunk = seeds[offset:offset + batch_size]
    p.lib.nb_diag_reset()
    with p.sweep(chunk, threads=34, retention="survivors"):
        out = p.ffi.new("uint64_t[12]")
        p.lib.nb_diag_get(out)
        if out[9] > 0:
            print(f"Seed found in chunk [{offset}, {offset+batch_size}): out[9]={out[9]}")
            # Identify individual seed
            for sub_i, s in enumerate(chunk):
                p.lib.nb_diag_reset()
                with p.sweep([s], threads=1, retention="survivors"):
                    p.lib.nb_diag_get(out)
                    if out[9] > 0:
                        print(f"EXACT SEED INDEX: {offset + sub_i} | SEED: {s}")
                        break
            break

