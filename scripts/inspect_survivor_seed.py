#!/usr/bin/env python3
"""Detailed inspection of candidate seed -3336796033057908633 discovered in 2M pilot."""
from __future__ import annotations

import json
import pprint
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.backend import Backend
from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import (
    candidate_centers,
    OVERWORLD_NAMES,
    NETHER_NAMES,
    OPTIONAL_NAMES,
    PaletteIndex,
    overworld_bounds,
    nether_bounds,
)
from seed_search.realm.blueprint import BiomeSampler, biome_palette
from seed_search.realm.dynamic import nether_palette

seed = -3336796033057908633
cfg = dynamic_v3_blueprint_config()

print(f"Inspecting seed {seed} under dynamic-envelope-2048-v3...")
res = evaluate_dynamic_seed(0, seed, cfg, short_circuit=False)

print("\n--- EVALUATION SUMMARY ---")
anchors = res.get("anchors", [])
print(f"Anchors found: {len(anchors)}")

for idx, a in enumerate(anchors):
    print(f"\nAnchor #{idx+1}:")
    print(f"  Center: {a.get('evaluation_center')}")
    print(f"  Baseline Score Observed: {a.get('baseline_score_observed')}")
    print(f"  Origin Distance Squared: {a.get('origin_distance_squared')}")
    print(f"  Radial Key: {a.get('radial_key')}")
    print(f"  Deficit Count: {a.get('deficit_count')}")
    print(f"  Scenic River Bonus: {a.get('scenic_bonus')}")
    print(f"  Village Spread Bonus: {a.get('village_spread_bonus')}")
    print(f"  Treasure Bastion Bonus: {a.get('treasure_bastion')}")
    print(f"  Hub Bonus: {a.get('hub_bonus')}")

    req = a.get("required_structures", {})
    nether = a.get("nether_structures", {})
    opt = a.get("optional_structures", {})

    print("\n  Required Structures in Realm:")
    for k, v in req.items():
        coords = v.get("predicted_viable", [])
        print(f"    {k:16s}: {len(coords):2d}  coords: {coords}")

    print("\n  Nether Structures in Realm:")
    for k, v in nether.items():
        coords = v.get("predicted_viable", [])
        print(f"    {k:16s}: {len(coords):2d}  coords: {coords}")

    print("\n  Optional Structures in Realm:")
    for k, v in opt.items():
        coords = v.get("predicted_viable", [])
        if coords:
            print(f"    {k:16s}: {len(coords):2d}  coords: {coords}")

with Backend(seed) as backend:
    sampler = BiomeSampler(backend)
    ow_half = cfg['deployment']['overworld_side_blocks'] // 2
    nw_half = cfg['deployment']['nether_side_blocks'] // 2
    for idx, a in enumerate(anchors):
        center = tuple(a.get('evaluation_center'))
        bounds = overworld_bounds(center, ow_half)
        ow_pal = biome_palette(sampler, bounds, cfg['biomes'], complete=True)
        nw_pal = nether_palette(sampler, center, nw_half)
        print(f"\nAnchor #{idx+1} Center {center}:")
        print(f"  Overworld Missing Families: {ow_pal.get('missing_families')}")
        print(f"  Overworld Luxury Families:  {ow_pal.get('luxury_families')}")
        print(f"  Nether Missing Families:    {nw_pal.get('missing_families')}")
        print(f"  Nether Luxury Families:     {nw_pal.get('luxury_families')}")

# Save full anchor JSON to inspect
out_path = ROOT / "runs" / "candidate_seed_3336796033057908633.json"
with open(out_path, "w") as f:
    json.dump(res, f, indent=2)
print(f"\nSaved full evaluation receipt to {out_path}")

