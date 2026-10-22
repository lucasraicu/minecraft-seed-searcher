#!/usr/bin/env python3
"""Player utility metric extractor for 15–20 player multiplayer survival realms.

Extracts objective, player-centric utility features independent of search score:
- D_daily: Commute distance to daily hubs (nearest Village, Nether Portal, Trial Chamber).
- D_milestone: Commute distance to milestone structures (Stronghold, Ancient City, Mansion).
- A_build: Square aggregated sampled-flat cells within 256m of center (slope <= 2 blocks per 16m step, Y >= 63).
  (Note: measures aggregated flat grid cells, not contiguous land parcels, exact spawn, or physical habitability).
- R_diversity: Multiplayer resource saturation index for 15–20 active players.
"""
import argparse
import json
import math
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from seed_search.backend import Backend


def dist(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def min_dist(center: Tuple[int, int], points: List[Tuple[int, int]], default: float = 1448.0) -> float:
    if not points:
        return default
    return min(dist(center, p) for p in points)


def extract_player_metrics(backend, cx: int, cz: int, num_players: int = 20) -> Dict:
    center = (cx, cz)
    bounds = (cx - 1024, cz - 1024, cx + 1024, cz + 1024)
    sh_bounds = (cx - 2048, cz - 2048, cx + 2048, cz + 2048)

    villages = backend.structures('village', bounds)
    chambers = backend.structures('trial_chamber', bounds)
    portals = backend.structures('ruined_portal', bounds)
    strongholds = backend.structures('stronghold', sh_bounds)
    ancient_cities = backend.structures('ancient_city', bounds)
    mansions = backend.structures('mansion', bounds)

    # 1. Daily Commute Index (meters)
    d_v = min_dist(center, villages)
    d_p = min_dist(center, portals)
    d_tc = min_dist(center, chambers)
    d_daily = 0.50 * d_v + 0.30 * d_p + 0.20 * d_tc

    # 2. Milestone Commute Index (meters)
    d_sh = min_dist(center, strongholds)
    d_ac = min_dist(center, ancient_cities)
    d_m = min_dist(center, mansions)
    d_milestone = 0.40 * d_sh + 0.30 * d_ac + 0.30 * d_m

    # 3. Square aggregated sampled-flat cells near center (radius 256m)
    grid_coords = []
    step = 16
    for x in range(cx - 256, cx + 256 + 1, step):
        for z in range(cz - 256, cz + 256 + 1, step):
            grid_coords.append((x, z))

    pts = np.array(grid_coords, dtype=np.int32)
    heights, biomes = backend.heights(pts, vertical_step=4)
    h_map = {(x, z): h for (x, z), h in zip(grid_coords, heights)}

    flat_cells = 0
    total_grid_points = len(grid_coords)
    for x in range(cx - 256, cx + 256, step):
        for z in range(cz - 256, cz + 256, step):
            h0 = h_map.get((x, z), 0)
            hx = h_map.get((x + step, z), 0)
            hz = h_map.get((x, z + step), 0)
            # Above water (Y >= 63) and slope <= 2 blocks per 16m step
            if h0 >= 63 and abs(hx - h0) <= 2 and abs(hz - h0) <= 2:
                flat_cells += 1

    # Approximate buildable hectares from aggregated sampled-flat cells:
    # 1 grid cell = 16x16 = 256 m^2 = 0.0256 ha
    buildable_hectares = round(flat_cells * (step * step) / 10000.0, 2)
    flat_fraction = round(flat_cells / max(1, total_grid_points), 3)

    # 4. Multiplayer Resource Saturation (Index 0.0 to 1.0)
    # Target: 1 village per 3 players, 1 trial chamber per 2.5 players, at least 1 stronghold/city/portal
    v_sat = min(1.0, len(villages) / max(1, num_players / 3.0))
    tc_sat = min(1.0, len(chambers) / max(1, num_players / 2.5))
    sh_sat = 1.0 if strongholds else 0.0
    ac_sat = min(1.0, len(ancient_cities) / 2.0)
    resource_diversity = round(0.35 * v_sat + 0.30 * tc_sat + 0.20 * sh_sat + 0.15 * ac_sat, 3)

    return {
        'center': [cx, cz],
        'commute_metrics': {
            'nearest_village_m': round(d_v, 1),
            'nearest_portal_m': round(d_p, 1),
            'nearest_chamber_m': round(d_tc, 1),
            'd_daily_index': round(d_daily, 1),
            'nearest_stronghold_m': round(d_sh, 1),
            'nearest_city_m': round(d_ac, 1),
            'nearest_mansion_m': round(d_m, 1),
            'd_milestone_index': round(d_milestone, 1),
        },
        'terrain_metrics': {
            'metric_type': 'square_aggregated_sampled_flat_cells',
            'notes': 'Aggregated flat grid cells; does not measure contiguous parcels, exact spawn point, or building habitability',
            'sampled_flat_cells_count': flat_cells,
            'total_sampled_cells': total_grid_points,
            'sampled_flat_cell_hectares': buildable_hectares,
            'sampled_flat_fraction': flat_fraction,
            'flat_buildable_hectares': buildable_hectares,
            'flat_fraction_near_spawn': flat_fraction
        },
        'multiplayer_metrics': {
            'target_players': num_players,
            'village_count': len(villages),
            'chamber_count': len(chambers),
            'stronghold_count': len(strongholds),
            'ancient_city_count': len(ancient_cities),
            'mansion_count': len(mansions),
            'resource_diversity_index': resource_diversity
        },
        'utility_vector': [
            round(d_daily, 2),
            round(d_milestone, 2),
            buildable_hectares,
            resource_diversity
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, required=True, help='Candidate world seed')
    parser.add_argument('--center-x', type=int, default=0, help='Evaluation center X')
    parser.add_argument('--center-z', type=int, default=0, help='Evaluation center Z')
    parser.add_argument('--players', type=int, default=20, help='Player count for multiplayer realm')
    parser.add_argument('--output', type=Path, required=True, help='Output JSON report path')
    args = parser.parse_args()

    with Backend(args.seed) as b:
        metrics = extract_player_metrics(b, args.center_x, args.center_z, args.players)
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2) + '\n')
    print(f"Player metrics written to: {args.output}")
    print(f"Daily Commute: {metrics['commute_metrics']['d_daily_index']}m | Milestone Commute: {metrics['commute_metrics']['d_milestone_index']}m | Buildable: {metrics['terrain_metrics']['flat_buildable_hectares']} ha")


if __name__ == '__main__':
    main()

