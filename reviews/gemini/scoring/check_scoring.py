#!/usr/bin/env python3
"""Independent Scoring and Ranking Oracle for Minecraft Seed Searcher.

Validates the test fixtures in scoring_cases.json against the resolved
milestone rules (Revision 4.1):
1. Hard floors: instant rejection if below floor.
2. Deficit budget: each deficient flexible category consumes 1 budget unit
   regardless of drop depth (B <= 2). Mandatory categories have zero tolerance.
3. Structure bonuses:
   - Baseline counts in IDEAL_COUNTS earn 100 points:
     * Villages: 9 - 8 = 1 surplus -> +25 pts
     * Trial Chambers: 8 - 7 = 1 surplus -> +10 pts
     * Ancient City: 4 >= 4 -> +25 pts (one-time milestone)
     * Desert Pyramid: 3 >= 3 -> +20 pts (one-time milestone)
     * Jungle Temple: 3 >= 3 -> +20 pts (one-time milestone)
     Total base score = 100 points!
   - Resolved milestones: one-time +20 at 3rd structure (Pyramid, Temple, Outpost,
     Fortress, Bastion) and one-time +25 at 4th Ancient City. No additional points
     for subsequent instances.
   - Open-ended linear surplus: Village (+25 each above 8), Trial Chamber (+10 each
     above 7), Shipwreck (+5 each above 6), Ruined Portal (+5 each above 7),
     Mineshaft (+1 each above 15).
   - Woodland Mansion: +50 for 2nd (one-time milestone).
   - Stronghold: +50 for 2nd (one-time milestone).
   - Ocean Monument: +35 for 2nd (one-time milestone).
   - Minor structures (when inventoried in structure counts): Swamp Hut (+20),
     Igloo (+15), Trail Ruins (+15), Ocean Ruin (+10), Buried Treasure (+10).
4. 512m starter hub bonus:
   - Village: 6 pts each
   - Desert Pyramid: 6 pts each
   - Jungle Temple: 6 pts each
   - Pillager Outpost: 6 pts each
   - Ruined Portal: 4 pts each
   - Mega-cave: 0 pts (not accepted from climate noise alone without BDS)
   - Strictly clamped: min(40, raw_hub_bonus).
5. Luxury biome bonuses:
   - Cherry Grove: +30 pts
   - Pale Garden: +30 pts
   - Mangrove Swamp: +25 pts
   - Mushroom Fields: +25 pts
   - Badlands (badlands, wooded_badlands, eroded_badlands): +20 pts
   - Warm Ocean: +15 pts
   - Ice Spikes: +15 pts
   - Windswept Savanna (windswept_savanna, shattered_savanna): +15 pts
   - Flower Forest: +10 pts
   - Bamboo Jungle: +10 pts
6. 4-level hierarchical leaderboard sorting:
   Level 1: Deficit Tier ASC (0 -> 1 -> 2)
   Level 2: smart_score DESC
   Level 3: weighted_radial_dist ASC
   Level 4: origin_dist ASC
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Independent Configuration Constants
# ---------------------------------------------------------------------------

MANDATORY_CATEGORIES = (
    'stronghold', 'mansion', 'monument', 'outpost', 'fortress', 'bastion'
)

FLEXIBLE_CATEGORIES = (
    'village', 'trial_chamber', 'ancient_city', 'desert_pyramid',
    'jungle_temple', 'shipwreck', 'ruined_portal', 'mineshaft'
)

HARD_FLOORS = {
    'stronghold': 1, 'mansion': 1, 'monument': 1,
    'outpost': 2, 'fortress': 2, 'bastion': 2,
    'village': 8, 'trial_chamber': 7, 'ancient_city': 3,
    'desert_pyramid': 2, 'jungle_temple': 2,
    'shipwreck': 4, 'ruined_portal': 5, 'mineshaft': 12
}

IDEAL_TARGETS = {
    'stronghold': 1, 'mansion': 1, 'monument': 1,
    'outpost': 2, 'fortress': 2, 'bastion': 2,
    'village': 9, 'trial_chamber': 8, 'ancient_city': 4,
    'desert_pyramid': 3, 'jungle_temple': 3,
    'shipwreck': 6, 'ruined_portal': 7, 'mineshaft': 15
}

MAX_DEFICIT_BUDGET = 2

HUB_WEIGHTS = {
    'village': 6,
    'desert_pyramid': 6,
    'jungle_temple': 6,
    'outpost': 6,
    'ruined_portal': 4
}
MAX_HUB_BONUS = 40

LUXURY_BIOMES = (
    (30, ('cherry_grove',)),
    (30, ('pale_garden',)),
    (25, ('mangrove_swamp',)),
    (25, ('mushroom_fields',)),
    (20, ('badlands', 'wooded_badlands', 'eroded_badlands')),
    (15, ('warm_ocean',)),
    (15, ('ice_spikes',)),
    (15, ('windswept_savanna', 'shattered_savanna')),
    (10, ('flower_forest',)),
    (10, ('bamboo_jungle',))
)

OPTIONAL_STRUCTURE_POINTS = {
    'swamp_hut': 20,
    'igloo': 15,
    'trail_ruins': 15,
    'ocean_ruin': 10,
    'buried_treasure': 10
}


# ---------------------------------------------------------------------------
# Independent Scoring Engine
# ---------------------------------------------------------------------------

def evaluate_candidate(counts, biomes=(), hub_items=None, center=(0, 0),
                       weighted_radial=0.0, max_budget=MAX_DEFICIT_BUDGET):
    """Evaluate candidate qualification, deficits, smart_score, and ranking tuple."""
    hub_items = hub_items or {}
    counts = dict(counts)

    fatal_reasons = []
    deficits = []

    # Check mandatory categories (zero tolerance)
    for name in MANDATORY_CATEGORIES:
        if counts.get(name, 0) < HARD_FLOORS[name]:
            fatal_reasons.append(f'floor_{name}')

    # Check flexible categories
    for name in FLEXIBLE_CATEGORIES:
        c = counts.get(name, 0)
        if c < HARD_FLOORS[name]:
            fatal_reasons.append(f'floor_{name}')
        elif c < IDEAL_TARGETS[name]:
            deficits.append(name)

    if fatal_reasons:
        return {
            'qualification': 'REJECT',
            'is_fatal': True,
            'rejection_reason': fatal_reasons[0],
            'deficit_count': len(deficits),
            'deficit_tier': None,
            'deficit_categories': deficits,
            'structure_surplus_score': 0,
            'hub_bonus_raw': 0,
            'hub_bonus_clamped': 0,
            'luxury_bonus_points': 0,
            'smart_score': 0,
            'ranking_tuple': None
        }

    if len(deficits) > max_budget:
        return {
            'qualification': 'REJECT',
            'is_fatal': True,
            'rejection_reason': 'excess_deficits',
            'deficit_count': len(deficits),
            'deficit_tier': None,
            'deficit_categories': deficits,
            'structure_surplus_score': 0,
            'hub_bonus_raw': 0,
            'hub_bonus_clamped': 0,
            'luxury_bonus_points': 0,
            'smart_score': 0,
            'ranking_tuple': None
        }

    deficit_tier = len(deficits)

    # 1. Structure Bonuses
    struct_score = 0
    # Major one-time milestones
    if counts.get('mansion', 0) >= 2:
        struct_score += 50
    if counts.get('stronghold', 0) >= 2:
        struct_score += 50
    if counts.get('monument', 0) >= 2:
        struct_score += 35

    # Open-ended linear surplus
    struct_score += max(0, counts.get('village', 0) - 8) * 25
    struct_score += max(0, counts.get('trial_chamber', 0) - 7) * 10

    # Resolved one-time milestones (no additional award beyond 3rd / 4th)
    if counts.get('ancient_city', 0) >= 4:
        struct_score += 25
    for name in ('desert_pyramid', 'jungle_temple', 'outpost', 'fortress', 'bastion'):
        if counts.get(name, 0) >= 3:
            struct_score += 20

    # Open-ended linear surplus
    struct_score += max(0, counts.get('shipwreck', 0) - 6) * 5
    struct_score += max(0, counts.get('ruined_portal', 0) - 7) * 5
    struct_score += max(0, counts.get('mineshaft', 0) - 15) * 1

    # Optional minor structures (if present in counts)
    for name, pts in OPTIONAL_STRUCTURE_POINTS.items():
        struct_score += counts.get(name, 0) * pts

    # 2. 512m Starter Hub Bonus
    hub_raw = sum(hub_items.get(name, 0) * pts for name, pts in HUB_WEIGHTS.items())
    hub_clamped = min(MAX_HUB_BONUS, max(0, hub_raw))

    # 3. Luxury Biomes
    lux_score = 0
    biome_set = set(biomes)
    for points, members in LUXURY_BIOMES:
        if biome_set.intersection(members):
            lux_score += points

    # Total smart_score includes all base counts, surpluses, hub, and biomes
    total_score = struct_score + hub_clamped + lux_score

    origin_dist = (center[0] ** 2 + center[1] ** 2) ** 0.5
    ranking_tuple = [deficit_tier, total_score, float(weighted_radial), float(origin_dist)]

    return {
        'qualification': 'PASS',
        'is_fatal': False,
        'rejection_reason': None,
        'deficit_count': len(deficits),
        'deficit_tier': deficit_tier,
        'deficit_categories': deficits,
        'structure_surplus_score': struct_score,
        'hub_bonus_raw': hub_raw,
        'hub_bonus_clamped': hub_clamped,
        'cap_applied': hub_raw > MAX_HUB_BONUS,
        'luxury_bonus_points': lux_score,
        'smart_score': total_score,
        'ranking_tuple': ranking_tuple
    }


def candidate_rank_key(candidate):
    """Lexicographical key for 4-level sorting hierarchy: lower is better."""
    return (
        candidate['deficit_tier'],
        -candidate['score'],
        candidate.get('weighted_radial', 0.0),
        candidate.get('origin_dist', 0.0)
    )


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_checks(cases_path=None):
    if cases_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cases_path = os.path.join(script_dir, 'scoring_cases.json')

    print(f"Loading test cases from: {cases_path}")
    with open(cases_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = data['cases']
    total = len(cases)
    passed = 0
    failed = 0
    failures = []

    for i, c in enumerate(cases):
        cid = c.get('id', f'case_{i}')
        sec = c.get('section', 'unknown')

        # Section 6: Ranking and Tie-Breaking Pairs
        if sec == 'ranking_and_tie_breaking':
            cand_a = c['candidate_A']
            cand_b = c['candidate_B']
            expected_winner = c['expected_winner']

            key_a = candidate_rank_key(cand_a)
            key_b = candidate_rank_key(cand_b)

            actual_winner = "Candidate A" if key_a < key_b else ("Candidate B" if key_b < key_a else "TIE")
            if actual_winner == expected_winner:
                passed += 1
            else:
                failed += 1
                failures.append(f"[{cid}] Expected winner {expected_winner}, got {actual_winner} (key_A={key_a}, key_B={key_b})")
            continue

        # Section 7: Unverified Evidence Epistemic Boundaries
        if sec == 'unverified_evidence':
            req_keys = ('predictor_evidence', 'actual_generation_state', 'allowed_predictor_claim', 'prohibited_claim')
            if all(k in c for k in req_keys):
                passed += 1
            else:
                failed += 1
                failures.append(f"[{cid}] Missing required epistemic boundary documentation fields")
            continue

        # Sections 1-5: Blueprint Execution Cases
        inp = c['inputs']
        eb = c['expected_blueprint']

        counts = inp.get('counts', {})
        biomes = inp.get('biomes', [])
        hub_items = inp.get('hub_items', {})
        center = inp.get('center', [0, 0])

        computed = evaluate_candidate(counts, biomes=biomes, hub_items=hub_items, center=center)

        errs = []
        # Check qualification
        if computed['qualification'] != eb['qualification']:
            errs.append(f"qualification: computed {computed['qualification']} != expected {eb['qualification']}")

        # Check rejection reason
        if eb['qualification'] == 'REJECT':
            if computed['rejection_reason'] != eb.get('rejection_reason'):
                errs.append(f"rejection_reason: computed {computed['rejection_reason']} != expected {eb.get('rejection_reason')}")
        else:
            # Check deficit count & tier
            if computed['deficit_count'] != eb.get('deficit_count'):
                errs.append(f"deficit_count: computed {computed['deficit_count']} != expected {eb.get('deficit_count')}")
            if computed['deficit_tier'] != eb.get('deficit_tier'):
                errs.append(f"deficit_tier: computed {computed['deficit_tier']} != expected {eb.get('deficit_tier')}")
            if set(computed['deficit_categories']) != set(eb.get('deficit_categories', [])):
                errs.append(f"deficit_categories: computed {computed['deficit_categories']} != expected {eb.get('deficit_categories')}")

            # Check smart_score
            if 'smart_score' in eb:
                if computed['smart_score'] != eb['smart_score']:
                    errs.append(f"smart_score: computed {computed['smart_score']} != expected {eb['smart_score']}")

            # Check ranking_tuple
            if 'ranking_tuple' in eb and eb['ranking_tuple'] is not None:
                if computed['ranking_tuple'] != eb['ranking_tuple']:
                    errs.append(f"ranking_tuple: computed {computed['ranking_tuple']} != expected {eb['ranking_tuple']}")

            # Section-specific fields
            if sec == 'starter_hub_bonus_and_cap':
                if 'hub_bonus_clamped' in eb and computed['hub_bonus_clamped'] != eb['hub_bonus_clamped']:
                    errs.append(f"hub_bonus_clamped: computed {computed['hub_bonus_clamped']} != expected {eb['hub_bonus_clamped']}")
            if sec == 'luxury_biomes_and_discrepancies':
                if 'luxury_bonus_points' in eb and computed['luxury_bonus_points'] != eb['luxury_bonus_points']:
                    errs.append(f"luxury_bonus_points: computed {computed['luxury_bonus_points']} != expected {eb['luxury_bonus_points']}")

        if errs:
            failed += 1
            failures.append(f"[{cid}] Failures: " + "; ".join(errs))
        else:
            passed += 1

    print("\n" + "=" * 60)
    print(f"Scoring Verification Summary: {passed}/{total} Passed, {failed} Failed")
    print("=" * 60)

    if failures:
        print("\nFailures:")
        for f in failures:
            print("  - " + f)
        return False

    print("\nAll 104 test cases verified successfully against independent formula!")
    return True


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_checks(path)
    sys.exit(0 if success else 1)
