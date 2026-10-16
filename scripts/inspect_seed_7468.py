#!/usr/bin/env python3
"""Detailed inspection of seed 7468236279383609753 under dynamic-v3."""
from __future__ import annotations

import pprint
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.backend import Backend
from seed_search.realm.blueprint import evaluate_dynamic_seed, PALETTE
from seed_search.realm.config import dynamic_v3_blueprint_config

seed = 7468236279383609753
cfg = dynamic_v3_blueprint_config()

print(f"Inspecting seed {seed}...")
# Evaluate with short_circuit=False
res = evaluate_dynamic_seed(39881, seed, cfg, short_circuit=False)

print("\n--- RESULTS OVERVIEW ---")
print("Anchors found:", len(res.get("anchors", [])))
print("Counts:", res.get("counts"))

# Let's inspect what candidate centers existed
from seed_search.realm.dynamic import candidate_centers, OVERWORLD_NAMES, NETHER_NAMES, OPTIONAL_NAMES, PaletteIndex, overworld_bounds, nether_bounds
with Backend(seed) as backend:
    ow_macro = tuple(cfg['discovery']['overworld_bounds'])
    nw_macro = tuple(cfg['discovery']['nether_bounds'])
    all_points = {}
    for name in OVERWORLD_NAMES + OPTIONAL_NAMES:
        all_points[name] = backend.structures(name, ow_macro)
    for name in NETHER_NAMES:
        all_points[name] = backend.structures(name, nw_macro)
    all_points['stronghold'] = backend.structures('stronghold', ow_macro)

    ow_half = cfg['deployment']['overworld_side_blocks'] // 2
    nw_half = cfg['deployment']['nether_side_blocks'] // 2
    all_ideals = {**cfg['structures']['minimum_counts'], **cfg['structures']['nether_minimum_counts']}
    floors = cfg['structures']['hard_floors']

    candidates = candidate_centers(all_points, floors, all_ideals, cfg['search']['density_weights'], max_misses=0, overworld_half=ow_half, nether_half=nw_half)
    print(f"\nCandidate centers meeting all 14 hard floors simultaneously: {len(candidates)}")
    for i, c in enumerate(candidates):
        print(f"\nCandidate {i+1}: Center=({c.center[0]}, {c.center[1]})")
        print("Structure counts:", c.counts)

        from seed_search.realm.blueprint import BiomeSampler
        sampler = BiomeSampler(backend)
        pindex = PaletteIndex(sampler, cfg['biomes'], v2=True, overworld_half=ow_half, nether_half=nw_half)
        ow_valid = pindex.valid(c.center)
        print("Overworld 13 biomes valid:", ow_valid)
        from seed_search.realm.blueprint import biome_palette
        from seed_search.realm.dynamic import nether_palette
        bounds = overworld_bounds(c.center, ow_half)
        ow_pal = biome_palette(sampler, bounds, cfg['biomes'], complete=True)
        print("Missing Overworld families:", ow_pal['missing_families'])
        nw_pal = nether_palette(sampler, c.center, nw_half)
        print("Missing Nether families:", nw_pal['missing_families'])

        print("Nether 5 biomes valid:", nether_valid)
