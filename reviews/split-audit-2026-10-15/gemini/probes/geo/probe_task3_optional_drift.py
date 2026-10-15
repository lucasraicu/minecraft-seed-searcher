"""Probe Task 3: Demonstrate optional structure count divergence between Python and C.
When an optional structure falls between unsnapped (cx, cz) and snapped (xx, zz) bounds.
"""
import math
from src.seed_search.realm.dynamic import candidate_centers, overworld_bounds, nether_bounds, CENTROID_WEIGHTS
from src.seed_search.realm.bounds import contains
from src.seed_search.realm.blueprint import dynamic_score

def main():
    # Setup a minimal synthetic inventory where an equivalence cell snaps from 0 to 16.
    # Suppose we have a village at (800, 0) with weight 3, pull x towards positive.
    # Cell is [0, 64) -> lo=0, hi=63. Nearest zero is cx=0.
    # Snapped center will be 16.
    # Put an igloo at (840, 0).
    # Unsnapped window [0-832, 0+832) = [-832, 832): 840 is OUTSIDE.
    # Snapped window [16-832, 16+832) = [-816, 848): 840 is INSIDE.
    
    inventories = {
        'stronghold': [(0, 0)],
        'mansion': [(0, 0)],
        'village': [(800, 0), (700, 0), (600, 0)],
        'trial_chamber': [(0, 0)],
        'ancient_city': [(0, 0)],
        'desert_pyramid': [(0, 0)],
        'jungle_temple': [(0, 0)],
        'monument': [(0, 0)],
        'ruined_portal': [(0, 0)],
        'shipwreck': [(0, 0)],
        'mineshaft': [(0, 0)],
        'outpost': [(0, 0), (0, 0)],
        'fortress': [(0, 0)],
        'bastion': [(0, 0)],
        'igloo': [(840, 0)],  # Optional structure!
        'swamp_hut': [],
        'trail_ruins': [],
        'ocean_ruin': [],
        'buried_treasure': [],
    }
    
    floors = {'stronghold': 1, 'mansion': 1, 'monument': 1, 'outpost': 2, 'fortress': 1, 'bastion': 1}
    ideals = {}
    weights = {'village': 1, 'trial_chamber': 1, 'ancient_city': 1, 'desert_pyramid': 1, 'jungle_temple': 1, 'outpost': 1}
    
    candidates = candidate_centers(inventories, floors, ideals, weights, max_misses=2)
    print(f"Found {len(candidates)} candidate cells.")
    
    for cand in candidates:
        snapped_x, snapped_z = cand.center
        py_igloo_count = cand.counts.get('igloo', 0)
        
        # Now evaluate actual igloo count at the SNAPPED center (as C does in native/blueprint_dynamic.inc:454)
        c_style_igloo_count = sum(contains(p, overworld_bounds(cand.center)) for p in inventories['igloo'])
        
        if py_igloo_count != c_style_igloo_count:
            print(f"DIVERGENCE DETECTED!")
            print(f"  Candidate snapped center: ({snapped_x}, {snapped_z})")
            print(f"  Python candidate.counts['igloo']: {py_igloo_count}")
            print(f"  C-style snapped count['igloo']:  {c_style_igloo_count}")
            print(f"  Score difference: {15 * (c_style_igloo_count - py_igloo_count)} points")
            break

if __name__ == '__main__':
    main()
