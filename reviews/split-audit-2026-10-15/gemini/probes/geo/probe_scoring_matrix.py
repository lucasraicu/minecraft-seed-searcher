"""Probe: Comprehensive validation of dynamic scoring matrix across C, Python, and Blueprint.
"""
from src.seed_search.realm.blueprint import dynamic_score, DYNAMIC_LUXURIES

def evaluate_c_formula(n, strong, bonus_mask, hub, optional_counts):
    # n is array of 13 counts:
    # 0: mansion, 1: jungle, 2: desert, 3: monument, 4: ancient_city, 5: village,
    # 6: trial_chamber, 7: ruined_portal, 8: shipwreck, 9: mineshaft,
    # 10: fortress, 11: bastion, 12: outpost
    score = (
        (50 if n[0] >= 2 else 0) +
        (50 if strong >= 2 else 0) +
        (25 * (n[5] - 8) if n[5] > 8 else 0) +
        (10 * (n[6] - 7) if n[6] > 7 else 0) +
        (25 if n[4] >= 4 else 0) +
        (20 if n[2] >= 3 else 0) +
        (20 if n[1] >= 3 else 0) +
        (20 if n[12] >= 3 else 0) +
        (20 if n[10] >= 3 else 0) +
        (20 if n[11] >= 3 else 0) +
        (30 if n[3] >= 2 else 0) +
        (5 * (n[8] - 6) if n[8] > 6 else 0) +
        (5 * (n[7] - 7) if n[7] > 7 else 0) +
        (n[9] - 15 if n[9] > 15 else 0) +
        hub
    )
    points = [30, 20, 25, 30, 25, 10, 10, 15, 15, 15]
    for i in range(10):
        if bonus_mask & (1 << i):
            score += points[i]
    opt_points = [20, 15, 15, 10, 10]
    for k in range(5):
        score += opt_points[k] * optional_counts[k]
    return score

def main():
    NAMES = ['mansion', 'jungle_temple', 'desert_pyramid', 'monument', 'ancient_city',
             'village', 'trial_chamber', 'ruined_portal', 'shipwreck', 'mineshaft',
             'fortress', 'bastion', 'outpost']
    OPT_NAMES = ['swamp_hut', 'igloo', 'trail_ruins', 'ocean_ruin', 'buried_treasure']
    
    # Run test cases
    test_cases = [
        # Baseline minimal counts
        ({name: 1 for name in NAMES}, 1, 0, 0, [0]*5),
        # 2nd Stronghold & 2nd Mansion
        ({'stronghold': 2, 'mansion': 2}, 2, 0, 0, [0]*5),
        # Surplus Villages (9, 10, 11)
        ({'village': 9}, 1, 0, 0, [0]*5),
        ({'village': 10}, 1, 0, 0, [0]*5),
        # Surplus Trial Chambers (8, 9)
        ({'trial_chamber': 8}, 1, 0, 0, [0]*5),
        ({'trial_chamber': 9}, 1, 0, 0, [0]*5),
        # Milestones: AC >= 4, Desert >= 3, Jungle >= 3, Outpost >= 3, Fortress >= 3, Bastion >= 3
        ({'ancient_city': 4}, 1, 0, 0, [0]*5),
        ({'desert_pyramid': 3}, 1, 0, 0, [0]*5),
        ({'jungle_temple': 3}, 1, 0, 0, [0]*5),
        ({'outpost': 3}, 1, 0, 0, [0]*5),
        ({'fortress': 3}, 1, 0, 0, [0]*5),
        ({'bastion': 3}, 1, 0, 0, [0]*5),
        ({'bastion': 4}, 1, 0, 0, [0]*5),  # verify milestone non-linearity
        # 2nd Monument
        ({'monument': 2}, 1, 0, 0, [0]*5),
        # Shipwrecks: 6, 7, 8
        ({'shipwreck': 6}, 1, 0, 0, [0]*5),
        ({'shipwreck': 7}, 1, 0, 0, [0]*5),
        ({'shipwreck': 8}, 1, 0, 0, [0]*5),
        # Portals: 7, 8, 9
        ({'ruined_portal': 7}, 1, 0, 0, [0]*5),
        ({'ruined_portal': 8}, 1, 0, 0, [0]*5),
        # Mineshafts: 15, 16, 17
        ({'mineshaft': 15}, 1, 0, 0, [0]*5),
        ({'mineshaft': 16}, 1, 0, 0, [0]*5),
        # Optional structures
        ({'swamp_hut': 2}, 1, 0, 0, [2, 0, 0, 0, 0]),
        ({'igloo': 1, 'trail_ruins': 1}, 1, 0, 0, [0, 1, 1, 0, 0]),
        ({'ocean_ruin': 3, 'buried_treasure': 2}, 1, 0, 0, [0, 0, 0, 3, 2]),
        # Hub bonus
        ({}, 1, 0, 24, [0]*5),
        ({}, 1, 0, 50, [0]*5),  # cap at 40
        # Luxury biomes
        ({}, 1, 0b1000000001, 0, [0]*5),  # cherry_grove (30) + windswept_savanna (15) = 45
    ]
    
    mismatches = 0
    for idx, (counts_dict, strong, bonus_mask, hub, opt_counts) in enumerate(test_cases):
        n = [counts_dict.get(name, 0) for name in NAMES]
        for k, opt_name in enumerate(OPT_NAMES):
            counts_dict[opt_name] = opt_counts[k]
        counts_dict['stronghold'] = strong
        
        # biomes list from bonus_mask
        biomes = []
        for i, (pts, members) in enumerate(DYNAMIC_LUXURIES):
            if bonus_mask & (1 << i):
                biomes.append(members[0])
                
        c_score = evaluate_c_formula(n, strong, bonus_mask, min(40, max(0, hub)), opt_counts)
        py_score = dynamic_score(counts_dict, biomes, hub)
        
        if c_score != py_score:
            print(f"Mismatch in case {idx}: C={c_score}, Py={py_score}")
            mismatches += 1
            
    print(f"Total test cases: {len(test_cases)}, mismatches: {mismatches}")

if __name__ == '__main__':
    main()
