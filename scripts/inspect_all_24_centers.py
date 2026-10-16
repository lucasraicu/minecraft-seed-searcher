#!/usr/bin/env python3
"""Check all 24 candidate centers for seed 7468236279383609753."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.backend import Backend
from seed_search.realm.blueprint import BiomeSampler, biome_palette
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import candidate_centers, OVERWORLD_NAMES, NETHER_NAMES, OPTIONAL_NAMES, PaletteIndex, overworld_bounds, nether_palette

seed = 7468236279383609753
cfg = dynamic_v3_blueprint_config()

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
    print(f"Total candidate centers meeting all 14 hard floors: {len(candidates)}")

    sampler = BiomeSampler(backend)
    pindex = PaletteIndex(sampler, cfg['biomes'], v2=True, overworld_half=ow_half, nether_half=nw_half)

    for i, c in enumerate(candidates):
        bounds = overworld_bounds(c.center, ow_half)
        ow_pal = biome_palette(sampler, bounds, cfg['biomes'], complete=True)
        ow_valid = len(ow_pal['missing_families']) == 0
        nw_pal = nether_palette(sampler, c.center, nw_half)
        nw_valid = len(nw_pal['missing_families']) == 0
        print(f"Center {i+1:2d} ({c.center[0]:5d}, {c.center[1]:5d}) | OW Biomes: {ow_valid} (Missing: {ow_pal['missing_families']}) | NW Biomes: {nw_valid} (Missing: {nw_pal['missing_families']})")
