"""Comprehensive tests for catalog retention engine and merge semantics."""
from decimal import Decimal
import hashlib
import json
import pytest

from seed_search.catalog import codec, models, registry, scoring
from seed_search.catalog.retention import (
    ALL_OBJECTIVE_IDS,
    DEFAULT_CAPACITIES,
    DIVERSITY_BITS,
    DIVERSITY_PROFILES,
    MODES,
    PAIR_LANDMARKS,
    POLICY_REVISION,
    REFERENCE_SALT,
    SIDES,
    compare_key,
    merge,
    objective_family,
    retain,
)

DUMMY_NATIVE_HASH = "a" * 64
DUMMY_SOURCE_HASH = "b" * 64
DUMMY_OBS_ID = "c" * 64


def make_ident(seed="12345", model_id="MC_26_50", world_settings_id="default"):
    return models.identity(
        seed=seed,
        model_id=model_id,
        world_settings_id=world_settings_id,
        native_sha256=DUMMY_NATIVE_HASH,
        source_sha256=DUMMY_SOURCE_HASH,
    )


def make_summary(
    ident,
    anchor=(0, 0),
    border_side=2048,
    counts=None,
    struct_d2=None,
    biome_d2=None,
    complete=None,
    obs_id=DUMMY_OBS_ID,
):
    wid = models.world_id(ident)
    lid = codec.layout_id(obs_id, anchor, border_side)
    summary = {
        "revision": models.SUMMARY_REVISION,
        "observation_id": obs_id,
        "world_id": wid,
        "layout_id": lid,
        "seed": ident["seed"],
        "anchor": list(anchor),
        "border_side": border_side,
        "counts": counts if counts is not None else [[0, 0, 0, 0] for _ in range(14)],
        "structure_nearest_d2": struct_d2 if struct_d2 is not None else [codec.MISSING] * 14,
        "biome_nearest_d2": biome_d2 if biome_d2 is not None else [codec.MISSING] * 9,
        "biome_witness_refs": [codec.MISSING] * 9,
        "complete": complete if complete is not None else [[False, False, False, False] for _ in range(23)],
    }
    return codec.validate_summary(summary)


# 1. Fixed Cap Counts and Total Materialization
def test_fixed_cap_counts_and_total_materialization():
    assert len(ALL_OBJECTIVE_IDS) == 6931
    assert set(DEFAULT_CAPACITIES) == {
        "structure_count",
        "structure_proximity",
        "biome_proximity",
        "biome_landmark_pairs",
        "profiles",
        "diversity",
        "reference_sample",
    }
    assert DEFAULT_CAPACITIES["structure_count"] == 100
    assert DEFAULT_CAPACITIES["structure_proximity"] == 100
    assert DEFAULT_CAPACITIES["biome_proximity"] == 100
    assert DEFAULT_CAPACITIES["biome_landmark_pairs"] == 50
    assert DEFAULT_CAPACITIES["profiles"] == 100
    assert DEFAULT_CAPACITIES["diversity"] == 1
    assert DEFAULT_CAPACITIES["reference_sample"] == 10000

    high_bound = (
        336 * 100
        + 84 * 100
        + 54 * 100
        + 216 * 50
        + 96 * 100
        + 6144 * 1
        + 10000
    )
    assert high_bound == 83944

    # Run on empty population
    res = retain([], [])
    assert res["policy_revision"] == POLICY_REVISION
    assert res["experiment"] is False
    assert res["capacities"] == DEFAULT_CAPACITIES
    assert len(res["objectives"]) == 6931
    assert all(res["objectives"][oid] == [] for oid in ALL_OBJECTIVE_IDS)
    assert res["world_ids"] == []
    assert res["pins"] == []

    # Custom capacity override: experiment=True, never mutate global POLICY
    orig_pol_str = json.dumps(registry.POLICY, sort_keys=True)
    res_exp = retain([], [], capacities={"diversity": 0})
    assert res_exp["experiment"] is True
    assert res_exp["capacities"]["diversity"] == 0
    assert res_exp["capacities"]["structure_count"] == 100
    assert json.dumps(registry.POLICY, sort_keys=True) == orig_pol_str


# 2. All 7 Families Admission and Ranking
def test_all_7_families_admission_and_ranking():
    ident = make_ident(seed="1001")
    wid = models.world_id(ident)

    # Prepare features for all 7 families:
    # Structure 0 (village): count near 256=2, inside border=4, nearest_d2=10000 (<= 256^2 = 65536)
    counts = [[0, 0, 0, 0] for _ in range(14)]
    counts[0] = [2, 3, 3, 4]
    struct_d2 = [codec.MISSING] * 14
    struct_d2[0] = 10000

    # Biome 0 (cherry grove): nearest_d2=20000 (<= 256^2)
    biome_d2 = [codec.MISSING] * 9
    biome_d2[0] = 20000

    # Complete all features for scope 0, 1, 2, 3
    complete = [[True, True, True, True] for _ in range(23)]

    summary = make_summary(
        ident,
        anchor=(0, 0),
        border_side=2048,
        counts=counts,
        struct_d2=struct_d2,
        biome_d2=biome_d2,
        complete=complete,
    )

    res = retain([summary], [ident])

    # Family 1: structure_count (village, scope 0, border 2048, origin)
    sc_obj = "structure_count:structure.village:0:2048:origin"
    assert len(res["objectives"][sc_obj]) == 1
    m_sc = res["objectives"][sc_obj][0]
    assert m_sc["world_id"] == wid
    assert m_sc["rank"][0] == -2  # -count
    assert m_sc["rank"][1] == 10000  # nearestD2

    # Family 2: structure_proximity (village, border 2048, origin)
    sp_obj = "structure_proximity:structure.village:2048:origin"
    assert len(res["objectives"][sp_obj]) == 1
    m_sp = res["objectives"][sp_obj][0]
    assert m_sp["rank"][0] == 10000  # nearestD2
    assert m_sp["rank"][1] == -4  # -insidecount

    # Family 3: biome_proximity (cherry grove, border 2048, origin)
    bp_obj = "biome_proximity:biome.cherry_grove:2048:origin"
    assert len(res["objectives"][bp_obj]) == 1
    m_bp = res["objectives"][bp_obj][0]
    assert m_bp["rank"][0] == 20000  # nearestD2

    # Family 4: biome_landmark_pairs (cherry grove + village, border 2048, origin)
    blp_obj = "biome_landmark_pairs:biome.cherry_grove:structure.village:2048:origin"
    assert len(res["objectives"][blp_obj]) == 1
    m_blp = res["objectives"][blp_obj][0]
    assert m_blp["rank"][0] == -3  # -landmark count near 512
    assert m_blp["rank"][1] == 20000  # biome nearestD2
    assert m_blp["rank"][2] == 10000  # landmark nearestD2

    # Family 5: profiles (balanced_survival, border 2048, origin)
    p_obj = "profiles:balanced_survival:2048:origin"
    assert len(res["objectives"][p_obj]) == 1
    m_p = res["objectives"][p_obj][0]
    assert isinstance(m_p["rank"][0], str)  # Exact decimal string
    assert Decimal(m_p["rank"][0]) < 0

    # Family 6: diversity
    # Bit 0 (cherry) is present (d2 <= 1024^2), Bit 4 (village) is present (count[0][2] = 3 >= 1)
    # Cell integer = (1 << 0) | (1 << 4) = 1 | 16 = 17
    div_obj = "diversity:17:balanced_survival:2048:origin"
    assert len(res["objectives"][div_obj]) == 1
    m_div = res["objectives"][div_obj][0]
    assert Decimal(m_div["rank"][0]) < 0

    # Family 7: reference_sample
    ref_obj = "reference_sample"
    assert len(res["objectives"][ref_obj]) == 1
    m_ref = res["objectives"][ref_obj][0]
    assert m_ref["world_id"] == wid
    assert m_ref["layout_id"] is None
    assert len(m_ref["rank"][0]) == 64  # SHA256 hex digest

    assert res["world_ids"] == [wid]


# 3. Adversarial Multi-Anchor and World Deduplication BEFORE Top-K
def test_adversarial_multi_anchor_and_world_dedup():
    ident = make_ident(seed="2002")
    wid = models.world_id(ident)

    # Anchor (0, 0) has 1 village
    counts_origin = [[0, 0, 0, 0] for _ in range(14)]
    counts_origin[0] = [1, 1, 1, 1]
    comp = [[True, True, True, True] for _ in range(23)]
    sum_origin = make_summary(
        ident,
        anchor=(0, 0),
        border_side=2048,
        counts=counts_origin,
        struct_d2=[10000] + [codec.MISSING] * 13,
        complete=comp,
    )

    # Anchor (256, 256) has 8 villages
    counts_rec = [[0, 0, 0, 0] for _ in range(14)]
    counts_rec[0] = [8, 8, 8, 8]
    sum_rec = make_summary(
        ident,
        anchor=(256, 256),
        border_side=2048,
        counts=counts_rec,
        struct_d2=[5000] + [codec.MISSING] * 13,
        complete=comp,
    )

    res = retain([sum_origin, sum_rec], [ident])

    # Origin mode: picks anchor (0, 0) with count 1
    sc_orig = "structure_count:structure.village:3:2048:origin"
    assert len(res["objectives"][sc_orig]) == 1
    assert res["objectives"][sc_orig][0]["layout_id"] == sum_origin["layout_id"]
    assert res["objectives"][sc_orig][0]["rank"][0] == -1

    # Recommended mode: evaluates both, picks anchor (256, 256) with count 8
    sc_rec = "structure_count:structure.village:3:2048:recommended"
    assert len(res["objectives"][sc_rec]) == 1
    assert res["objectives"][sc_rec][0]["layout_id"] == sum_rec["layout_id"]
    assert res["objectives"][sc_rec][0]["rank"][0] == -8

    # World wid appears ONLY ONCE in recommended mode (dedup before K)
    assert len([m for m in res["objectives"][sc_rec] if m["world_id"] == wid]) == 1


# 4. Duplicate Layout and Identity Conflicts
def test_duplicate_layout_and_identity_conflicts():
    ident1 = make_ident(seed="3001")
    ident2_dup = make_ident(seed="3001")

    # Duplicate seed/world_id in identities raises ValueError
    with pytest.raises(ValueError, match="Duplicate identity or seed conflict"):
        retain([], [ident1, ident2_dup])

    # Mixed edition or settings in identities raises ValueError
    ident_diff_settings = make_ident(seed="3002", world_settings_id="custom")
    with pytest.raises(ValueError, match="Mixed settings/build/revision"):
        retain([], [ident1, ident_diff_settings])

    # Duplicate layout (same world, anchor, border_side) raises ValueError
    sum1 = make_summary(ident1, anchor=(0, 0), border_side=2048)
    sum1_dup = make_summary(ident1, anchor=(0, 0), border_side=2048)
    with pytest.raises(ValueError, match="Duplicate layout conflict"):
        retain([sum1, sum1_dup], [ident1])

    # Layout with unknown world raises ValueError
    ident_unknown = make_ident(seed="9999")
    sum_unknown = make_summary(ident_unknown, anchor=(0, 0), border_side=2048)
    with pytest.raises(ValueError, match="Layout references unknown world_id"):
        retain([sum_unknown], [ident1])


# 5. K Ties and Canonical Tail Breaking
def test_k_ties_canonical_tail():
    # 3 worlds with identical village count (5) and distance (40000)
    # They differ in seed:
    # Seed "10" -> unsigned 10
    # Seed "20" -> unsigned 20
    # Seed "30" -> unsigned 30
    ident1 = make_ident(seed="30")
    ident2 = make_ident(seed="10")
    ident3 = make_ident(seed="20")

    counts = [[0, 0, 0, 0] for _ in range(14)]
    counts[0] = [5, 5, 5, 5]
    struct_d2 = [40000] + [codec.MISSING] * 13
    comp = [[True, True, True, True] for _ in range(23)]

    s1 = make_summary(ident1, counts=counts, struct_d2=struct_d2, complete=comp)
    s2 = make_summary(ident2, counts=counts, struct_d2=struct_d2, complete=comp)
    s3 = make_summary(ident3, counts=counts, struct_d2=struct_d2, complete=comp)

    # Restrict capacity to K=2
    res = retain([s1, s2, s3], [ident1, ident2, ident3], capacities={"structure_count": 2})

    sc_obj = "structure_count:structure.village:3:2048:origin"
    members = res["objectives"][sc_obj]
    assert len(members) == 2
    # Seed 10 comes first, then seed 20, seed 30 is dropped
    assert members[0]["world_id"] == models.world_id(ident2)
    assert members[1]["world_id"] == models.world_id(ident3)


# 6. Unsigned 64-bit Extremes Ordering
def test_unsigned_extremes_ordering():
    # Signed seeds:
    # "0" -> unsigned 0
    # "1" -> unsigned 1
    # "-9223372036854775808" -> unsigned 2^63 (9223372036854775808)
    # "-1" -> unsigned 2^64 - 1 (18446744073709551615)
    seeds = ["-1", "1", "-9223372036854775808", "0"]
    idents = [make_ident(seed=s) for s in seeds]

    counts = [[0, 0, 0, 0] for _ in range(14)]
    counts[0] = [5, 5, 5, 5]
    comp = [[True, True, True, True] for _ in range(23)]

    layouts = [make_summary(ident, counts=counts, complete=comp) for ident in idents]

    res = retain(layouts, idents)
    sc_obj = "structure_count:structure.village:3:2048:origin"
    members = res["objectives"][sc_obj]

    # Expected order of unsigned seeds: 0, 1, 2^63, 2^64-1
    returned_wids = [m["world_id"] for m in members]
    expected_order = [
        models.world_id(idents[3]),  # seed 0
        models.world_id(idents[1]),  # seed 1
        models.world_id(idents[2]),  # seed -9223372036854775808
        models.world_id(idents[0]),  # seed -1
    ]
    assert returned_wids == expected_order


# 7. Specialists with Unrelated Unknowns
def test_specialists_with_unrelated_unknowns():
    ident = make_ident(seed="7001")
    wid = models.world_id(ident)

    # Only village is complete; all other structures & biomes are incomplete/unknown
    counts = [[0, 0, 0, 0] for _ in range(14)]
    counts[0] = [3, 4, 5, 6]
    struct_d2 = [codec.MISSING] * 14
    struct_d2[0] = 50000

    comp = [[False, False, False, False] for _ in range(23)]
    comp[0] = [True, True, True, True]  # Village complete

    s = make_summary(ident, counts=counts, struct_d2=struct_d2, complete=comp)

    res = retain([s], [ident])

    # Qualifies for village objectives!
    sc_obj = "structure_count:structure.village:2:2048:origin"
    assert len(res["objectives"][sc_obj]) == 1
    assert res["objectives"][sc_obj][0]["world_id"] == wid

    sp_obj = "structure_proximity:structure.village:2048:origin"
    assert len(res["objectives"][sp_obj]) == 1
    assert res["objectives"][sp_obj][0]["world_id"] == wid

    # But does NOT qualify for ancient_city or biomes
    sc_ac = "structure_count:structure.ancient_city:2:2048:origin"
    assert len(res["objectives"][sc_ac]) == 0


# 8. Profile Coverage Strictness
def test_profile_coverage_strictness():
    ident = make_ident(seed="8001")

    # Trial adventurer requires village, trials, ancient city, structure palette, biomes
    # If ancient city is incomplete, trial adventurer cannot admit this world
    counts = [[0, 0, 0, 0] for _ in range(14)]
    comp = [[True, True, True, True] for _ in range(23)]
    comp[2] = [False, False, False, False]  # Ancient city (slot 2) incomplete!

    s = make_summary(ident, counts=counts, complete=comp)
    res = retain([s], [ident])

    prof_obj = "profiles:trial_adventurer:2048:origin"
    assert len(res["objectives"][prof_obj]) == 0


# 9. Scope Edges
def test_scope_edges():
    ident = make_ident(seed="9001")

    # Boundary at 256^2 = 65536
    # Exact 65536 is admitted to structure_proximity
    comp = [[True, True, True, True] for _ in range(23)]
    s_edge = make_summary(
        ident,
        anchor=(0, 0),
        border_side=2048,
        struct_d2=[65536] + [codec.MISSING] * 13,
        complete=comp,
    )
    res = retain([s_edge], [ident])
    assert len(res["objectives"]["structure_proximity:structure.village:2048:origin"]) == 1

    # 65537 is outside 256 radius -> rejected
    ident2 = make_ident(seed="9002")
    s_outside = make_summary(
        ident2,
        anchor=(0, 0),
        border_side=2048,
        struct_d2=[65537] + [codec.MISSING] * 13,
        complete=comp,
    )
    res2 = retain([s_outside], [ident2])
    assert len(res2["objectives"]["structure_proximity:structure.village:2048:origin"]) == 0


# 10. Counts Greater than 16 (No uint32 clipping)
def test_counts_greater_than_16():
    ident1 = make_ident(seed="10001")
    ident2 = make_ident(seed="10002")

    counts1 = [[0, 0, 0, 0] for _ in range(14)]
    counts1[0] = [16, 16, 16, 16]

    counts2 = [[0, 0, 0, 0] for _ in range(14)]
    counts2[0] = [45, 45, 45, 45]  # count > 16

    comp = [[True, True, True, True] for _ in range(23)]
    s1 = make_summary(ident1, counts=counts1, complete=comp)
    s2 = make_summary(ident2, counts=counts2, complete=comp)

    res = retain([s1, s2], [ident1, ident2])
    sc_obj = "structure_count:structure.village:3:2048:origin"
    members = res["objectives"][sc_obj]
    assert len(members) == 2
    # Count 45 ranks before Count 16
    assert members[0]["world_id"] == models.world_id(ident2)
    assert members[0]["rank"][0] == -45
    assert members[1]["world_id"] == models.world_id(ident1)
    assert members[1]["rank"][0] == -16


# 11. Pins Validation and Outside Capacity Union
def test_pins_validation_and_union():
    ident1 = make_ident(seed="11001")
    ident2 = make_ident(seed="11002")
    wid1 = models.world_id(ident1)
    wid2 = models.world_id(ident2)

    # Capacity 0 for all layout families
    caps_zero = {k: 0 for k in DEFAULT_CAPACITIES}
    caps_zero["reference_sample"] = 0

    # Pinned wid2 must be retained even with capacity 0!
    res = retain([], [ident1, ident2], capacities=caps_zero, pins=[wid2])
    assert res["pins"] == [wid2]
    assert res["world_ids"] == [wid2]

    # Pin not in population raises ValueError
    with pytest.raises(ValueError, match="Invalid pin not in population"):
        retain([], [ident1], pins=["0" * 64])


# 12. Hash Sampling Failure Worlds
def test_hash_sampling_failure_worlds():
    # World with failure receipt (no layouts at all)
    fail_ident = make_ident(seed="12001")
    fail_wid = models.world_id(fail_ident)

    res = retain([], [fail_ident])

    # Cannot enter any layout objective
    for oid, members in res["objectives"].items():
        if oid != "reference_sample":
            assert len(members) == 0

    # But DOES enter reference_sample!
    ref_members = res["objectives"]["reference_sample"]
    assert len(ref_members) == 1
    assert ref_members[0]["world_id"] == fail_wid
    assert ref_members[0]["layout_id"] is None
    assert res["world_ids"] == [fail_wid]


# 13. Partition Merge Parity and Reversed Input Invariance
def test_partition_merge_parity_and_reversed_input():
    idents = [make_ident(seed=str(i)) for i in range(13000, 13006)]
    comp = [[True, True, True, True] for _ in range(23)]
    layouts = []
    for i, ident in enumerate(idents):
        counts = [[0, 0, 0, 0] for _ in range(14)]
        counts[0] = [i + 1, i + 1, i + 1, i + 1]
        layouts.append(make_summary(ident, counts=counts, struct_d2=[1000 * (i + 1)] + [codec.MISSING] * 13, complete=comp))

    pins = [models.world_id(idents[0])]

    # 1. Full one-shot retention
    full_res = retain(layouts, idents, pins=pins)

    # 2. Partition A (first 3 worlds) and Partition B (last 3 worlds)
    sel_a = retain(layouts[:3], idents[:3], pins=pins)
    sel_b = retain(layouts[3:], idents[3:], pins=[])

    merged_res = merge([sel_a, sel_b])
    assert merged_res == full_res

    # 3. Reversed input invariance
    rev_res = retain(list(reversed(layouts)), list(reversed(idents)), pins=pins)
    assert rev_res == full_res


# 14. Merge Conflict Handling
def test_merge_conflicts():
    ident = make_ident(seed="14001")
    comp = [[True, True, True, True] for _ in range(23)]
    s = make_summary(ident, complete=comp)

    sel1 = retain([s], [ident])

    # Conflicting capacities
    sel2 = retain([s], [ident], capacities={"diversity": 0})
    with pytest.raises(ValueError, match="Conflicting capacities"):
        merge([sel1, sel2])

    # Conflicting rank for same world
    sel_tampered = retain([s], [ident])
    sc_obj = "structure_count:structure.village:0:2048:origin"
    if sel_tampered["objectives"][sc_obj]:
        sel_tampered["objectives"][sc_obj][0]["rank"][0] = -99999
        with pytest.raises(ValueError, match="Conflicting rank/layout"):
            merge([sel1, sel_tampered])


# 15. Decimal Numeric Comparison in Merge
def test_decimal_numeric_comparison_in_merge():
    # String comparison vs Decimal numeric comparison:
    # Lexically: "-2.5" < "-9.5" is True (because '2' < '9')
    # Numerically: Decimal("-9.5") < Decimal("-2.5") is True (-9.5 is smaller than -2.5)
    assert "-2.5" < "-9.5"
    assert Decimal("-9.5") < Decimal("-2.5")

    obj = "profiles:balanced_survival:2048:origin"
    ident_a = make_ident(seed="15001")
    ident_b = make_ident(seed="15002")
    wid_a = models.world_id(ident_a)
    wid_b = models.world_id(ident_b)

    # sel_a has rank -2.5, sel_b has rank -9.5
    sel_a = retain([], [ident_a], capacities={"profiles": 1})
    sel_b = retain([], [ident_b], capacities={"profiles": 1})

    sel_a["objectives"][obj] = [{"world_id": wid_a, "layout_id": "a" * 64, "rank": ["-2.5", 1, 0, 0, "a" * 64]}]
    sel_b["objectives"][obj] = [{"world_id": wid_b, "layout_id": "b" * 64, "rank": ["-9.5", 2, 0, 0, "b" * 64]}]

    merged = merge([sel_a, sel_b])
    # Capacity K=1: numerically -9.5 < -2.5, so wid_b must win!
    assert len(merged["objectives"][obj]) == 1
    assert merged["objectives"][obj][0]["world_id"] == wid_b
    assert merged["objectives"][obj][0]["rank"][0] == "-9.5"


# 16. Independent Known Serial Oracle
def test_independent_known_serial_oracle():
    """Verify retention against an independent serial oracle."""
    idents = [make_ident(seed=str(s)) for s in (10, 20, 30, 40)]
    comp = [[True, True, True, True] for _ in range(23)]

    # World 0 (seed 10): 2 villages, nearest 1000
    # World 1 (seed 20): 5 villages, nearest 500
    # World 2 (seed 30): 5 villages, nearest 200 (beats World 1 on distance)
    # World 3 (seed 40): 0 villages
    counts0 = [[2, 2, 2, 2]] + [[0, 0, 0, 0] for _ in range(13)]
    counts1 = [[5, 5, 5, 5]] + [[0, 0, 0, 0] for _ in range(13)]
    counts2 = [[5, 5, 5, 5]] + [[0, 0, 0, 0] for _ in range(13)]
    counts3 = [[0, 0, 0, 0] for _ in range(14)]

    s0 = make_summary(idents[0], counts=counts0, struct_d2=[1000] + [codec.MISSING] * 13, complete=comp)
    s1 = make_summary(idents[1], counts=counts1, struct_d2=[500] + [codec.MISSING] * 13, complete=comp)
    s2 = make_summary(idents[2], counts=counts2, struct_d2=[200] + [codec.MISSING] * 13, complete=comp)
    s3 = make_summary(idents[3], counts=counts3, struct_d2=[codec.MISSING] * 14, complete=comp)

    res = retain([s0, s1, s2, s3], idents, capacities={"structure_count": 2})

    obj = "structure_count:structure.village:3:2048:origin"
    winners = res["objectives"][obj]
    assert len(winners) == 2
    # Oracle: World 2 (-5, 200) beats World 1 (-5, 500); World 0 (-2) and World 3 (0) are dropped
    assert winners[0]["world_id"] == models.world_id(idents[2])
    assert winners[1]["world_id"] == models.world_id(idents[1])


# 17. 100 Population with Failure Receipts & Hash Reference Only
def test_100_population_with_failure_receipts():
    """Simulate a 100-world population including failure receipts."""
    idents = [make_ident(seed=str(i)) for i in range(100)]
    comp_full = [[True, True, True, True] for _ in range(23)]
    comp_none = [[False, False, False, False] for _ in range(23)]

    layouts = []
    # 0..19: Failure receipts (no layouts at all)
    # 20..39: Zero-complete layouts (all complete=False)
    for i in range(20, 40):
        layouts.append(make_summary(idents[i], complete=comp_none))
    # 40..99: Fully completed layouts
    for i in range(40, 100):
        counts = [[0, 0, 0, 0] for _ in range(14)]
        counts[0] = [i, i, i, i]
        layouts.append(make_summary(idents[i], counts=counts, struct_d2=[i * 10] + [codec.MISSING] * 13, complete=comp_full))

    res = retain(layouts, idents)

    # Failure receipt worlds (0..19) and zero-complete worlds (20..39)
    # can NEVER enter any layout-based family
    zero_complete_wids = {models.world_id(idents[i]) for i in range(40)}
    for oid, members in res["objectives"].items():
        if oid != "reference_sample":
            admitted_wids = {m["world_id"] for m in members}
            assert not (admitted_wids & zero_complete_wids), f"Fake positive in {oid}"

    # But reference_sample admits across ALL 100 identities
    ref_members = res["objectives"]["reference_sample"]
    assert len(ref_members) == 100
    ref_wids = {m["world_id"] for m in ref_members}
    assert ref_wids == {models.world_id(ident) for ident in idents}

    # Verify partition merge parity on 100 worlds (partition 50/50)
    sel_1 = retain(layouts[:30], idents[:50])
    sel_2 = retain(layouts[30:], idents[50:])
    merged = merge([sel_1, sel_2])
    assert merged == res


# 18. Exact JSON Reproducibility
def test_json_exact_reproducibility():
    ident = make_ident(seed="16001")
    comp = [[True, True, True, True] for _ in range(23)]
    s = make_summary(ident, complete=comp)

    res = retain([s], [ident])
    dumped = json.dumps(res, sort_keys=True)
    loaded = json.loads(dumped)

    assert loaded["policy_revision"] == res["policy_revision"]
    assert loaded["world_ids"] == res["world_ids"]
    assert len(loaded["objectives"]) == 6931

