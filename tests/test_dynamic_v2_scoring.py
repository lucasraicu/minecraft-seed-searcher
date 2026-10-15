"""Comprehensive test suite for dynamic-envelope-1664-v2 player scoring and pipeline."""
from fractions import Fraction
import numpy as np
import pytest

from scripts.build_blueprint_batch import build
from seed_search.backend import biome_catalog
from seed_search.realm.blueprint import (
    DYNAMIC_V2_LUXURIES,
    dynamic_v2_score,
    evaluate_dynamic_seed,
    evaluate_seed,
)
from seed_search.realm.config import (
    DYNAMIC_REVISION,
    DYNAMIC_V2_REVISION,
    dynamic_blueprint_config,
    dynamic_v2_blueprint_config,
    validate_blueprint_config,
    validate_config,
)
from seed_search.realm.dynamic import (
    DYNAMIC_V2_CENTROID_WEIGHTS,
    candidate_centers,
    hub_bonus_v2,
    hub_village_v2,
    scenic_pair_bonus_v2,
    village_spread_bonus_v2,
    weighted_radial_v2,
)
from seed_search.realm.native_batch import NAMES, Prototype, semantic_record

IDS = {row['name']: row['id'] for row in biome_catalog()}

BASELINE_TARGETS = {
    'mansion': 1, 'stronghold': 1, 'monument': 1, 'village': 9,
    'trial_chamber': 8, 'ancient_city': 4, 'desert_pyramid': 3,
    'jungle_temple': 3, 'outpost': 2, 'fortress': 2, 'bastion': 2,
    'ruined_portal': 7, 'shipwreck': 6, 'mineshaft': 15,
}


# ---------------------------------------------------------------------------
# Section 8.1 & 8.2: Floors, Targets, Deficits
# ---------------------------------------------------------------------------

def test_v2_config_floors_and_strict_targets():
    cfg = dynamic_v2_blueprint_config()
    validate_config(cfg)
    validate_blueprint_config(cfg)
    assert cfg['screening_revision'] == DYNAMIC_V2_REVISION
    assert cfg['search']['max_misses'] == 3
    assert cfg['search']['centroid_weights']['ruined_portal'] == 0
    assert cfg['search']['centroid_weights']['shipwreck'] == 0
    assert cfg['terrain']['variants'] == []

    strict = {'stronghold', 'mansion', 'monument', 'outpost', 'fortress', 'bastion'}
    for s in strict:
        goal = cfg['structures']['minimum_counts'].get(s) or cfg['structures']['nether_minimum_counts'].get(s)
        floor = cfg['structures']['hard_floors'][s]
        assert goal == floor, f"Strict category {s} has goal {goal} != floor {floor}"


def test_v2_deficit_deduction_portal_shipwreck_vs_others():
    # Ruined portal deficit is -5 per category
    score_p, comp_p, def_p = dynamic_v2_score({**BASELINE_TARGETS, 'ruined_portal': 5})
    assert def_p == ['ruined_portal']
    assert comp_p['deficit_penalty'] == 5
    assert score_p == -5

    score_p6, comp_p6, def_p6 = dynamic_v2_score({**BASELINE_TARGETS, 'ruined_portal': 6})
    assert def_p6 == ['ruined_portal']
    assert comp_p6['deficit_penalty'] == 5
    assert score_p6 == -5

    # Shipwreck deficit is -5 per category
    score_s, comp_s, def_s = dynamic_v2_score({**BASELINE_TARGETS, 'shipwreck': 4})
    assert def_s == ['shipwreck']
    assert comp_s['deficit_penalty'] == 5
    assert score_s == -5

    # Both together: 10 points deducted
    score_ps, comp_ps, def_ps = dynamic_v2_score({**BASELINE_TARGETS, 'ruined_portal': 5, 'shipwreck': 4})
    assert set(def_ps) == {'ruined_portal', 'shipwreck'}
    assert comp_ps['deficit_penalty'] == 10
    assert score_ps == -10

    # Other categories deduct -10
    score_v, comp_v, def_v = dynamic_v2_score({**BASELINE_TARGETS, 'village': 8})
    assert def_v == ['village']
    assert comp_v['deficit_penalty'] == 10
    assert score_v == -10

    # 3 deficits: portal (5) + shipwreck (5) + village (10) = 20 deduction
    score_3, comp_3, def_3 = dynamic_v2_score({**BASELINE_TARGETS, 'ruined_portal': 5, 'shipwreck': 4, 'village': 8})
    assert len(def_3) == 3
    assert comp_3['deficit_penalty'] == 20
    assert score_3 == -20


# ---------------------------------------------------------------------------
# Section 8.3 A: Core Structure Surplus Bonuses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('count,expected_score,expected_deficits', [
    (8, -10, ['village']),
    (9, 0, []),
    (10, 25, []),
    (11, 35, []),
    (12, 40, []),
    (13, 40, []),
])
def test_village_core_milestones(count, expected_score, expected_deficits):
    score, comp, deficits = dynamic_v2_score({**BASELINE_TARGETS, 'village': count})
    assert score == expected_score
    assert deficits == expected_deficits
    bonus = 25 if count >= 10 else 0
    if count >= 11: bonus += 10
    if count >= 12: bonus += 5
    assert comp['core_surplus'] == bonus


@pytest.mark.parametrize('count,expected_score,expected_deficits', [
    (7, -10, ['trial_chamber']),
    (8, 0, []),
    (9, 10, []),
    (10, 20, []),
    (11, 30, []),
    (12, 30, []),
])
def test_trial_chamber_core_milestones(count, expected_score, expected_deficits):
    score, comp, deficits = dynamic_v2_score({**BASELINE_TARGETS, 'trial_chamber': count})
    assert score == expected_score
    assert deficits == expected_deficits
    bonus = min(30, max(0, (count - 8) * 10))
    assert comp['core_surplus'] == bonus


@pytest.mark.parametrize('count,expected_score,expected_deficits', [
    (3, -10, ['ancient_city']),
    (4, 0, []),
    (5, 25, []),
    (6, 25, []),
])
def test_ancient_city_core_milestones(count, expected_score, expected_deficits):
    score, comp, deficits = dynamic_v2_score({**BASELINE_TARGETS, 'ancient_city': count})
    assert score == expected_score
    assert deficits == expected_deficits
    assert comp['core_surplus'] == (25 if count >= 5 else 0)


@pytest.mark.parametrize('struct,target,cap', [
    ('desert_pyramid', 3, 20),
    ('jungle_temple', 3, 20),
])
def test_temple_core_milestones(struct, target, cap):
    # Floor: 2 -> deficit -10
    s2, _, d2 = dynamic_v2_score({**BASELINE_TARGETS, struct: target - 1})
    assert s2 == -10
    assert d2 == [struct]
    # Target: 3 -> 0
    s3, _, d3 = dynamic_v2_score({**BASELINE_TARGETS, struct: target})
    assert s3 == 0
    assert d3 == []
    # Count >= 4: +20
    s4, c4, d4 = dynamic_v2_score({**BASELINE_TARGETS, struct: target + 1})
    assert s4 == cap
    assert c4['core_surplus'] == cap
    # Count 5: capped at +20
    s5, c5, d5 = dynamic_v2_score({**BASELINE_TARGETS, struct: target + 2})
    assert s5 == cap
    assert c5['core_surplus'] == cap


@pytest.mark.parametrize('struct,target,bonus', [
    ('mansion', 1, 50),
    ('stronghold', 1, 35),
    ('monument', 1, 35),
    ('outpost', 2, 20),
    ('fortress', 2, 20),
    ('bastion', 2, 20),
])
def test_strict_structure_core_surplus(struct, target, bonus):
    s_target, c_target, d_target = dynamic_v2_score({**BASELINE_TARGETS, struct: target})
    assert s_target == 0
    assert d_target == []
    assert c_target['core_surplus'] == 0

    s_surplus, c_surplus, d_surplus = dynamic_v2_score({**BASELINE_TARGETS, struct: target + 1})
    assert s_surplus == bonus
    assert d_surplus == []
    assert c_surplus['core_surplus'] == bonus

    # Capped at target + 1 bonus
    s_more, c_more, _ = dynamic_v2_score({**BASELINE_TARGETS, struct: target + 5})
    assert s_more == bonus
    assert c_more['core_surplus'] == bonus


@pytest.mark.parametrize('count,expected_bonus', [
    (15, 0), (16, 1), (17, 2), (18, 3), (19, 4), (20, 5), (21, 5),
])
def test_mineshaft_core_milestones(count, expected_bonus):
    score, comp, deficits = dynamic_v2_score({**BASELINE_TARGETS, 'mineshaft': count})
    assert score == expected_bonus
    assert comp['core_surplus'] == expected_bonus


def test_core_bonuses_sum_to_340():
    all_max_core = {
        'mansion': 2, 'stronghold': 2, 'monument': 2, 'village': 12,
        'trial_chamber': 11, 'ancient_city': 5, 'desert_pyramid': 4,
        'jungle_temple': 4, 'outpost': 3, 'fortress': 3, 'bastion': 3,
        'ruined_portal': 9, 'shipwreck': 8, 'mineshaft': 20,
    }
    score, comp, deficits = dynamic_v2_score(all_max_core)
    assert deficits == []
    assert comp['core_surplus'] == 340


# ---------------------------------------------------------------------------
# Section 8.3 B: Optional Structures and Treasure Bastion
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('struct,counts,expected', [
    ('swamp_hut', [0, 1, 2, 3], [0, 20, 30, 30]),
    ('trail_ruins', [0, 1, 2, 3], [0, 15, 25, 25]),
    ('ocean_ruin', [0, 1, 2, 3], [0, 10, 20, 20]),
    ('buried_treasure', [0, 1, 2, 3, 4, 5], [0, 6, 12, 18, 24, 24]),
    ('igloo', [0, 1, 2, 3], [0, 10, 15, 15]),
])
def test_optional_structure_schedules(struct, counts, expected):
    for n, exp in zip(counts, expected):
        _, comp, _ = dynamic_v2_score({**BASELINE_TARGETS, struct: n})
        assert comp['optional_bonus'] == exp, f"{struct} at {n} got {comp['optional_bonus']} != {exp}"


def test_treasure_bastion_variant_bonus():
    _, comp_f, _ = dynamic_v2_score(BASELINE_TARGETS, treasure_bastion=0)
    assert comp_f['treasure_bastion_bonus'] == 0

    _, comp_t, _ = dynamic_v2_score(BASELINE_TARGETS, treasure_bastion=1)
    assert comp_t['treasure_bastion_bonus'] == 15


def test_optional_and_treasure_sum_to_129():
    all_optional = {
        'swamp_hut': 2, 'trail_ruins': 2, 'ocean_ruin': 2,
        'buried_treasure': 4, 'igloo': 2,
    }
    _, comp, _ = dynamic_v2_score({**BASELINE_TARGETS, **all_optional}, treasure_bastion=1)
    assert comp['optional_bonus'] == 129
    assert comp['treasure_bastion_bonus'] == 15


# ---------------------------------------------------------------------------
# Section 8.3 C: Luxury Biomes
# ---------------------------------------------------------------------------

def test_luxury_biomes_individual_and_aliases():
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['cherry_grove'])[0] == 25
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['pale_garden'])[0] == 25
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['mushroom_fields'])[0] == 25
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['badlands'])[0] == 20
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['wooded_badlands'])[0] == 20
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['eroded_badlands'])[0] == 20
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['warm_ocean'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['ice_spikes'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['savanna'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['savanna_plateau'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['windswept_savanna'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['shattered_savanna'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['old_growth_pine_taiga'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['old_growth_spruce_taiga'])[0] == 15
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['flower_forest'])[0] == 10
    assert dynamic_v2_score(BASELINE_TARGETS, biome_names=['bamboo_jungle'])[0] == 10


def test_luxury_biomes_no_duplicate_awards():
    # Combining savanna aliases awards 15 once
    score, _, _ = dynamic_v2_score(BASELINE_TARGETS, biome_names=['savanna', 'savanna_plateau', 'windswept_savanna'])
    assert score == 15

    # Combining old-growth taiga variants awards 15 once
    score, _, _ = dynamic_v2_score(BASELINE_TARGETS, biome_names=['old_growth_pine_taiga', 'old_growth_spruce_taiga'])
    assert score == 15

    # Mangrove alone: 0. Swamp + Mangrove: 0.
    score_m, _, _ = dynamic_v2_score(BASELINE_TARGETS, biome_names=['mangrove_swamp'])
    assert score_m == 0
    score_sm, _, _ = dynamic_v2_score(BASELINE_TARGETS, biome_names=['swamp', 'mangrove_swamp'])
    assert score_sm == 0


def test_luxury_biomes_total_cap_175():
    all_biomes = [
        'cherry_grove', 'pale_garden', 'mushroom_fields', 'badlands',
        'warm_ocean', 'ice_spikes', 'savanna', 'old_growth_pine_taiga',
        'flower_forest', 'bamboo_jungle'
    ]
    score, comp, _ = dynamic_v2_score(BASELINE_TARGETS, biome_names=all_biomes)
    assert comp['luxury_biomes'] == 175


# ---------------------------------------------------------------------------
# Section 8.3 D: Starter Hub Contribution
# ---------------------------------------------------------------------------

def test_hub_village_distances():
    assert hub_village_v2({'village': [(256, 0)]}, (0, 0)) == (256, 0)
    assert hub_bonus_v2({'village': [(256, 0)]}, (0, 0)) == 10
    assert hub_bonus_v2({'village': [(0, 256)]}, (0, 0)) == 10
    assert hub_bonus_v2({'village': [(181, 181)]}, (0, 0)) == 10

    assert hub_village_v2({'village': [(257, 0)]}, (0, 0)) == (257, 0)
    assert hub_bonus_v2({'village': [(257, 0)]}, (0, 0)) == 6
    assert hub_bonus_v2({'village': [(512, 0)]}, (0, 0)) == 6

    assert hub_village_v2({'village': [(513, 0)]}, (0, 0)) is None
    assert hub_bonus_v2({'village': [(513, 0)]}, (0, 0)) == 0

    assert hub_village_v2({'village': [(10, 10), (300, 0)]}, (0, 0)) == (10, 10)
    assert hub_bonus_v2({'village': [(10, 10), (300, 0)]}, (0, 0)) == 10


def test_hub_bonus_total_and_cap():
    other_lots = {
        'desert_pyramid': [(100, 100)] * 10,
        'ruined_portal': [(200, 200)] * 10,
    }
    assert hub_bonus_v2(other_lots, (0, 0)) == 30

    lots_with_close_village = dict(other_lots, village=[(50, 50)])
    assert hub_bonus_v2(lots_with_close_village, (0, 0)) == 40

    lots_with_mid_village = dict(other_lots, village=[(300, 0)])
    assert hub_bonus_v2(lots_with_mid_village, (0, 0)) == 36


# ---------------------------------------------------------------------------
# Section 8.3 E: Scenic Pairing & Village Distribution
# ---------------------------------------------------------------------------

def test_scenic_pair_distance_and_exclusion():
    grid = np.full((63, 63), 'dark_forest', dtype=object)
    grid[31, 31] = 'cherry_grove'  # (0, 0), dist to center = 0 <= 192
    grid[31, 32] = 'river'         # (64, 0), dist to scenic = 64 <= 128

    bonus, s_pt, r_pt = scenic_pair_bonus_v2(grid, (0, 0))
    assert bonus == 20
    assert s_pt == (0, 0)
    assert r_pt == (64, 0)

    # frozen_river exclusion
    grid_frozen = np.full((63, 63), 'dark_forest', dtype=object)
    grid_frozen[31, 31] = 'cherry_grove'
    grid_frozen[31, 32] = 'frozen_river'
    assert scenic_pair_bonus_v2(grid_frozen, (0, 0))[0] == 0

    # Scenic > 192 from center -> fails (ix=35 is 256 blocks away)
    grid_far = np.full((63, 63), 'dark_forest', dtype=object)
    grid_far[31, 35] = 'cherry_grove'
    grid_far[31, 35] = 'river'
    assert scenic_pair_bonus_v2(grid_far, (0, 0))[0] == 0


def test_village_spread_quadrants_and_separation():
    center = (0, 0)
    v0 = (300, 300)
    v1 = (-300, 300)
    v2 = (-300, -300)
    points, triple = village_spread_bonus_v2([v0, v1, v2], center)
    assert points == 15
    assert triple is not None

    # Exactly 256 separation passes
    v_q0 = (256, 0)   # Q0
    v_q1 = (-256, 0)  # Q1
    v_q2 = (0, -256)  # Q2
    pts_exact, _ = village_spread_bonus_v2([v_q0, v_q1, v_q2], center)
    assert pts_exact == 15

    # Fewer than 3 quadrants occupied -> fails
    pts_fewer, _ = village_spread_bonus_v2([(100, 100), (200, 200), (300, 300)], center)
    assert pts_fewer == 0

    # 3 quadrants occupied, but one pair separation < 256 -> fails
    v_close1 = (10, 10)    # Q0
    v_close2 = (-10, 10)   # Q1, dist = 20 < 256
    v_far = (-300, -300)   # Q2
    pts_close, _ = village_spread_bonus_v2([v_close1, v_close2, v_far], center)
    assert pts_close == 0


def test_arithmetic_ceiling_719():
    all_max_core = {
        'mansion': 2, 'stronghold': 2, 'monument': 2, 'village': 12,
        'trial_chamber': 11, 'ancient_city': 5, 'desert_pyramid': 4,
        'jungle_temple': 4, 'outpost': 3, 'fortress': 3, 'bastion': 3,
        'ruined_portal': 9, 'shipwreck': 8, 'mineshaft': 20,
    }
    all_optional = {
        'swamp_hut': 2, 'trail_ruins': 2, 'ocean_ruin': 2,
        'buried_treasure': 4, 'igloo': 2,
    }
    all_biomes = [
        'cherry_grove', 'pale_garden', 'mushroom_fields', 'badlands',
        'warm_ocean', 'ice_spikes', 'savanna', 'old_growth_pine_taiga',
        'flower_forest', 'bamboo_jungle'
    ]
    counts = {**all_max_core, **all_optional}
    score, comp, deficits = dynamic_v2_score(
        counts,
        biome_names=all_biomes,
        hub=40,
        scenic=20,
        village_spread=15,
        treasure_bastion=1,
    )
    assert deficits == []
    assert comp['core_surplus'] == 340
    assert comp['optional_bonus'] == 129
    assert comp['treasure_bastion_bonus'] == 15
    assert comp['luxury_biomes'] == 175
    assert comp['hub_bonus'] == 40
    assert comp['scenic_bonus'] == 20
    assert comp['village_spread_bonus'] == 15
    assert score == 719


# ---------------------------------------------------------------------------
# Section 8.4: Selection Parity & Score-First Ordering
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def native_v2(tmp_path_factory):
    path = tmp_path_factory.mktemp('dynamic-v2-native')
    build(path)
    return Prototype(path, dynamic_v2_blueprint_config())


class DynamicV2FixtureBackend:
    surface = ('plains', 'desert', 'forest', 'taiga', 'jungle', 'swamp', 'snowy_plains',
               'dark_forest', 'jagged_peaks', 'stony_shore')
    caves = ('lush_caves', 'dripstone_caves', 'deep_dark')

    def __init__(self, missing=-1, extra_mask=0, depth=1, x=0, z=0, cfg=None):
        self.missing = missing
        self.extra_mask = extra_mask
        self.depth = depth
        self.x = x
        self.z = z
        self.cfg = cfg or dynamic_v2_blueprint_config()
        self.native_work = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def absent(self, slot):
        return self.missing == slot or bool(self.extra_mask & (1 << slot))

    def structure_pair(self, name, bounds):
        if name == 'stronghold':
            points = [] if self.absent(28) else [(16, 0), (32, 0)]
            return points, points
        if name in ('swamp_hut', 'igloo', 'trail_ruins', 'ocean_ruin', 'buried_treasure'):
            return [], []
        cfg = self.cfg
        slot = NAMES.index(name)
        goal = (cfg['structures']['minimum_counts'].get(name) or
                cfg['structures']['nether_minimum_counts'].get(name))
        n = max(0, goal - self.depth) if self.absent(slot) else goal + 2
        points = [(bounds[0] + 800 + i * 16 + self.x, bounds[1] + 800 + self.z) for i in range(n)]
        return points, points

    def igloo_basement(self, x, z):
        return False

    def bastion_variant(self, x, z):
        return 1

    def nether_structure_pairs(self, bounds):
        return {name: self.structure_pair(name, bounds) for name in ('fortress', 'bastion')}

    def biome_points(self, points, dimension=0):
        values = []
        if dimension == -1:
            names = ('nether_wastes', 'crimson_forest', 'warped_forest', 'soul_sand_valley', 'basalt_deltas')
            return np.array([IDS[names[(int(x) // 64 + int(z) // 64) % 5]] for x, y, z in points], dtype=np.int32)
        for x, y, z in points:
            if x % 64 or z % 64:
                name = 'cherry_grove' if self.absent(27) or x == self.x + 32 else 'dark_forest'
            else:
                cave = y in (-48, 0)
                if self.absent(26):
                    name = 'dark_forest' if cave else 'lush_caves'
                else:
                    choices = self.caves if cave else self.surface
                    k = (int(x) // 64 + int(z) // 64) % len(choices)
                    name = choices[k]
            values.append(IDS[name])
        return np.array(values, dtype=np.int32)


def test_native_v2_python_selection_agreement(native_v2):
    cfg = dynamic_v2_blueprint_config()
    with native_v2.sweep([456], fixtures=[(0, 0, -1)]) as batch:
        direct = batch.records()[0]
        replay = batch.records(adapter='replay')[0]
        assert semantic_record(direct) == semantic_record(replay)

    reference = evaluate_seed(0, 456, cfg, backend_factory=lambda _: DynamicV2FixtureBackend())
    assert semantic_record(direct) == semantic_record(reference)

    anchor = direct['anchors'][0]
    oracle = reference['anchors'][0]
    assert anchor['evaluation_center'] == oracle['evaluation_center']
    assert anchor['baseline_score'] == oracle['baseline_score']
    assert anchor['deficit_categories'] == oracle['deficit_categories']


def test_native_v2_worker_reuse(native_v2):
    with native_v2.sweep([101, 202, 101], fixtures=[(0, 0, -1), (0, 0, 5), (0, 0, -1)]) as batch:
        records = batch.records()
        assert len(records) == 3
        a0 = records[0]['anchors'][0]
        a2 = records[2]['anchors'][0]
        assert a0['evaluation_center'] == a2['evaluation_center']
        assert a0['baseline_score'] == a2['baseline_score']
        assert a0['deficit_categories'] == a2['deficit_categories']
        assert a0['ranking'] == a2['ranking']
        assert records[1]['anchors'][0]['deficit_categories'] == ['village']
