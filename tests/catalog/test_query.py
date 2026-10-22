"""Comprehensive test suite for catalog summaries and query engine.

Covers:
- counts within radius vs border
- same-anchor counterexample (combining facts from two anchors must not match)
- biome alternative OR semantics and binary utility
- all 3 border sides and boundary edge behavior
- unknown vs 0 coverage
- counts > 16 without clipping
- codec pack/unpack 364-byte roundtrip for all 243 layouts
- canonical tie-breaking and per-world deduplication BEFORE top-K
- fallback profile scoring when no preferred rows exist
- observation identity validation
"""
import pytest
from seed_search.catalog import models, codec, registry, geometry
from seed_search.catalog import summaries, query

DUMMY_HASH = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
FULL_ENVELOPE = list(registry.ENVELOPE)


def make_test_identity(seed="42", model_id="MC_26_50"):
    return models.identity(
        seed=seed,
        model_id=model_id,
        native_sha256=DUMMY_HASH,
        source_sha256=DUMMY_HASH,
    )


def make_full_25600_biomes(default_raw_id=0):
    return [
        [x, 63, z, default_raw_id]
        for x in range(-5120, 5120, 64)
        for z in range(-5120, 5120, 64)
    ]


def make_base_obs(seed="42", structures=None, biomes=None, biome_names=None, coverage=None):
    ident = make_test_identity(seed=seed)
    obs = models.empty_observation(ident)
    obs["structures"] = structures or {}
    obs["biomes"] = biomes or []
    obs["biome_names"] = biome_names or {}
    obs["coverage"] = coverage or {}
    return obs


def make_complete_obs(seed="42", structures=None, biomes=None, biome_names=None):
    obs = make_base_obs(seed=seed, structures=structures, biomes=biomes, biome_names=biome_names)
    if not obs["biomes"]:
        obs["biomes"] = make_full_25600_biomes(0)
    if not obs["biome_names"]:
        obs["biome_names"] = {"0": "plains"}
    for f in registry.STRUCTURES:
        obs["structures"].setdefault(f["id"], [])
        obs["coverage"][f["id"]] = {
            "status": "complete",
            "bounds": FULL_ENVELOPE,
            "method_id": "predictor_viable_starts_v1",
        }
    for b in registry.BIOMES:
        obs["coverage"][b["id"]] = {
            "status": "complete",
            "bounds": FULL_ENVELOPE,
            "method_id": "predictor_world_lattice_y63_stride64_v1",
        }
    return obs


def test_summarize_243_layouts_and_codec_roundtrip():
    """Verify summarize produces 243 layouts and each packs/unpacks to 364 bytes."""
    obs = make_complete_obs(
        seed="12345",
        structures={"structure.village": [[100, 100], [-200, 300]]},
    )
    layouts = summaries.summarize(obs)
    assert len(layouts) == 243

    for l in layouts:
        codec.validate_summary(l)
        packed = codec.pack_summary(l)
        assert len(packed) == 364
        meta = codec.summary_metadata(l)
        unpacked = codec.unpack_summary(packed, meta)
        assert unpacked["counts"] == l["counts"]
        assert unpacked["structure_nearest_d2"] == l["structure_nearest_d2"]
        assert unpacked["biome_nearest_d2"] == l["biome_nearest_d2"]
        assert unpacked["biome_witness_refs"] == l["biome_witness_refs"]
        assert unpacked["complete"] == l["complete"]


def test_counts_within_radius_vs_border_and_monotonicity():
    """Verify count increases monotonically with nested scopes and radius vs border."""
    # Anchor (0,0). Place villages at various distances:
    # (100, 0) -> dist 100 <= 256
    # (300, 0) -> dist 300 <= 512, > 256
    # (600, 0) -> dist 600 <= 1024, > 512
    # (1500, 0) -> dist 1500 > 1024, but inside border 4096 (1500 < 2048)
    obs = make_complete_obs(
        seed="101",
        structures={
            "structure.village": [[100, 0], [300, 0], [600, 0], [1500, 0]]
        },
    )
    layouts = summaries.summarize(obs)
    origin_4096 = next(l for l in layouts if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 4096)
    v_counts = origin_4096["counts"][0]  # slot 0: village
    assert v_counts[0] == 1  # radius 256
    assert v_counts[1] == 2  # radius 512
    assert v_counts[2] == 3  # radius 1024
    assert v_counts[3] == 4  # inside border 4096

    # Verify all rows in all 243 layouts are monotonic
    for l in layouts:
        for row in l["counts"]:
            assert row == sorted(row)


def test_same_anchor_counterexample():
    """Combining true facts from two different anchors must not invent a match."""
    # Village at (976, 0), Desert pyramid at (-976, 0).
    # Anchor (976, 0) has village near 512, but pyramid is ~1952 away.
    # Anchor (-976, 0) has pyramid near 512, but village is ~1952 away.
    # A query requiring BOTH on the same layout should find NO match!
    obs = make_complete_obs(
        seed="999",
        structures={
            "structure.village": [[976, 0]],
            "structure.desert_pyramid": [[-976, 0]],
        },
    )
    layouts = summaries.summarize(obs)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "recommended",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "required",
                "kind": "structure_count",
                "feature": "structure.village",
                "at_least": 1,
                "scope": {"kind": "near_base", "radius": 512},
            },
            {
                "rule": "required",
                "kind": "structure_count",
                "feature": "structure.desert_pyramid",
                "at_least": 1,
                "scope": {"kind": "near_base", "radius": 512},
            },
        ],
    }

    results = query.search(layouts, req, snapshot_id="snap-1")
    assert results == []  # Cannot combine different anchors!


def test_biome_alternatives_or_and_binary_utility():
    """Biome alternatives OR together; utility earned once; distance_tie chooses nearest."""
    biomes = make_full_25600_biomes(0)
    # Set sample at (0, 63, 128) to cherry_grove (raw 1)
    # Set sample at (0, 63, 256) to mushroom_fields (raw 2)
    # Origin anchor (0, 0): cherry distance is 128, mushroom distance is 256
    for pt in biomes:
        if pt[0] == 0 and pt[2] == 128:
            pt[3] = 1
        elif pt[0] == 0 and pt[2] == 256:
            pt[3] = 2

    biome_names = {"0": "ocean", "1": "cherry_grove", "2": "mushroom_fields"}
    obs = make_complete_obs(seed="50", biomes=biomes, biome_names=biome_names)
    layouts = summaries.summarize(obs)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.cherry_grove", "biome.mushroom_fields"],
                "importance": 5,
                "scope": {"kind": "near_base", "radius": 512},
            }
        ],
    }

    results = query.search(layouts, req, snapshot_id="snap-1")
    assert len(results) == 1
    res = results[0]
    assert res["score"] == 100.0
    assert res["utility_units"] == 5 * query.LCM
    # Distance tie uses nearest alternative (cherry at distance 128)
    # isqrt(128^2 * 10^12) // 512 = 128000000 // 512 = 250000
    assert res["distance_tie"] == 250000


def test_all_3_sides_and_half_open_edges():
    """Verify half-open edge [lo, hi) on all three border sizes 2048, 4096, 8192."""
    # Center (0, 0):
    # For side 2048: [-1024, 1024). Point (-1024, 0) is IN, (1024, 0) is OUT.
    # For side 4096: [-2048, 2048). Point (1024, 0) is IN, (-2048, 0) is IN, (2048, 0) is OUT.
    # For side 8192: [-4096, 4096). Point (2048, 0) is IN, (-4096, 0) is IN, (4096, 0) is OUT.
    obs = make_complete_obs(
        seed="777",
        structures={
            "structure.village": [
                [-1024, 0],
                [1024, 0],
                [-2048, 0],
                [2048, 0],
                [-4096, 0],
                [4096, 0],
            ]
        },
    )
    layouts = summaries.summarize(obs)
    origin_2048 = next(l for l in layouts if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 2048)
    origin_4096 = next(l for l in layouts if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 4096)
    origin_8192 = next(l for l in layouts if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 8192)

    # In 2048: only [-1024, 0] is inside. [1024, 0] is outside.
    assert origin_2048["counts"][0][3] == 1

    # In 4096: [-1024, 0], [1024, 0], [-2048, 0] are inside. [2048, 0] is outside.
    assert origin_4096["counts"][0][3] == 3

    # In 8192: [-1024, 0], [1024, 0], [-2048, 0], [2048, 0], [-4096, 0] are inside. [4096, 0] is outside.
    assert origin_8192["counts"][0][3] == 5


def test_unknown_vs_zero_coverage():
    """Distinguish complete 0 count vs partial/unknown coverage."""
    # Observation 1: Complete coverage with 0 ancient cities
    obs_complete = make_complete_obs(seed="10", structures={"structure.village": [[0, 0]]})

    # Observation 2: Partial coverage for ancient city
    obs_partial = make_complete_obs(seed="20", structures={"structure.village": [[0, 0]]})
    obs_partial["coverage"]["structure.ancient_city"] = {
        "status": "partial",
        "bounds": FULL_ENVELOPE,
        "method_id": "predictor_viable_starts_v1",
    }

    # Observation 3: Unknown raw biome name forces all biome completion to False
    obs_unknown_biome = make_complete_obs(seed="30")
    obs_unknown_biome["biome_names"]["999"] = "unknown_biome_test"

    l_comp = summaries.summarize(obs_complete)
    l_part = summaries.summarize(obs_partial)
    l_unk_bio = summaries.summarize(obs_unknown_biome)

    origin_comp = next(l for l in l_comp if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 2048)
    origin_part = next(l for l in l_part if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 2048)
    origin_unk_bio = next(l for l in l_unk_bio if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 2048)

    # In l_comp: ancient city is complete with 0 count
    assert origin_comp["complete"][2] == [True, True, True, True]  # slot 2: ancient_city
    assert origin_comp["counts"][2][3] == 0

    # In l_part: ancient city is partial
    assert origin_part["complete"][2] == [False, False, False, False]

    # In l_unk_bio: all biomes complete must be False
    for b in range(9):
        assert origin_unk_bio["complete"][14 + b] == [False, False, False, False]

    # Required query on incomplete feature rejects
    req_required = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "required",
                "kind": "structure_count",
                "feature": "structure.ancient_city",
                "at_least": 1,
                "scope": {"kind": "inside_border"},
            }
        ],
    }
    assert query.search([origin_comp], req_required, snapshot_id="snap-1") == []
    assert query.search([origin_part], req_required, snapshot_id="snap-1") == []

    # Preferred query: complete 0 gives score 0 labeled known; partial gives score 0 labeled unknown
    req_preferred = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "structure_count",
                "feature": "structure.ancient_city",
                "at_least": 1,
                "importance": 5,
                "scope": {"kind": "inside_border"},
            }
        ],
    }
    res_comp = query.search([origin_comp], req_preferred, snapshot_id="snap-1")
    assert len(res_comp) == 1
    assert res_comp[0]["contributions"][0]["status"] == "known"

    res_part = query.search([origin_part], req_preferred, snapshot_id="snap-1")
    assert len(res_part) == 1
    assert res_part[0]["contributions"][0]["status"] == "unknown"


def test_counts_above_16_not_clipped():
    """Counts > 16 must not be clipped in summary payload or query scoring."""
    points = [[i * 16, i * 16] for i in range(25)]  # 25 villages near (0, 0)
    obs = make_complete_obs(seed="123", structures={"structure.village": points})
    layouts = summaries.summarize(obs)
    origin_2048 = next(l for l in layouts if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 2048)
    assert origin_2048["counts"][0][3] == 25

    # Preferred rule with at_least 16 gets full credit
    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "structure_count",
                "feature": "structure.village",
                "at_least": 16,
                "importance": 5,
                "scope": {"kind": "inside_border"},
            }
        ],
    }
    res = query.search([origin_2048], req, snapshot_id="snap-1")
    assert res[0]["score"] == 100.0
    assert res[0]["utility_units"] == 5 * query.LCM
    assert res[0]["contributions"][0]["count"] == 25


def test_canonical_ties_and_deduplication_before_top_k():
    """Verify tie-breaking: utility, distance_tie, unsigned seed, anchor, layout_id; dedupe worlds BEFORE limit."""
    # Create two worlds:
    # World 1: seed -1 (unsigned = 2^64-1)
    # World 2: seed 1  (unsigned = 1)
    # Both have village at (100, 100).
    obs1 = make_complete_obs(seed="-1", structures={"structure.village": [[100, 100]]})
    obs2 = make_complete_obs(seed="1", structures={"structure.village": [[100, 100]]})

    l1 = summaries.summarize(obs1)
    l2 = summaries.summarize(obs2)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "recommended",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "structure_count",
                "feature": "structure.village",
                "at_least": 1,
                "importance": 5,
                "scope": {"kind": "near_base", "radius": 512},
            }
        ],
    }

    # Combined 486 layouts from both worlds
    all_layouts = l1 + l2
    results = query.search(all_layouts, req, snapshot_id="snap-1", limit=1)
    # limit=1 must return exactly 1 world
    assert len(results) == 1
    # Seed 1 has smaller unsigned 64-bit value than seed -1 (1 < 18446744073709551615)
    assert results[0]["seed"] == "1"

    # limit=5 must return both worlds, each represented ONCE
    results5 = query.search(all_layouts, req, snapshot_id="snap-1", limit=5)
    assert len(results5) == 2
    assert [r["seed"] for r in results5] == ["1", "-1"]


def test_no_preferred_rows_uses_fallback_profile():
    """Verify declared fallback profile scoring when no preferred rows exist."""
    # World with 3 villages and 2 trial chambers in near1024
    pts_village = [[100, 0], [200, 0], [300, 0]]
    pts_trial = [[-100, 0], [-200, 0]]
    obs = make_complete_obs(
        seed="404",
        structures={
            "structure.village": pts_village,
            "structure.trial_chamber": pts_trial,
        },
    )
    layouts = summaries.summarize(obs)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "village_life",
        "rows": [],
    }

    results = query.search(layouts, req, snapshot_id="snap-1")
    assert len(results) == 1
    res = results[0]
    # village_life coefficients: V:5, T:0, A:0, O:0, E:1, B:1, H:5, R:0. Sum = 12.
    # V count = 3. V utility = min(3, 6) * (LCM // 6) = 3 * 120120 = 360360.
    # E count = 2 distinct structure types (village, trial_chamber). E utility = 2 * (LCM // 14) = 2 * 51480 = 102960.
    # Nearest village distance = 100.
    # norm_d = 100 * 10^6 // 1024 = 97656.
    # H = (1000000 - 97656) * LCM // 1000000 = 902344 * 720720 // 1000000 = 650337.
    assert res["score"] > 0
    assert len(res["contributions"]) == 8  # V, T, A, O, E, B, H, R


def test_observations_argument_validation():
    """Verify observations parameter validates compatible game_build_id and world_settings_id."""
    obs = make_complete_obs(seed="700")
    layouts = summaries.summarize(obs)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [],
    }

    # Successful validation
    res = query.search(layouts, req, snapshot_id="snap-1", observations=[obs])
    assert len(res) == 1

    # Incompatible build ID in request
    req_bad_build = dict(req, game_build_id="research:OTHER")
    with pytest.raises(ValueError, match="Incompatible game_build_id"):
        query.search(layouts, req_bad_build, snapshot_id="snap-1", observations=[obs])

    # Incompatible observation layout reference
    other_obs = make_complete_obs(seed="701")
    with pytest.raises(ValueError, match="references unknown observation"):
        query.search(layouts, req, snapshot_id="snap-1", observations=[other_obs])


def test_required_rows_not_scored_utility_and_contribute_to_distance_tie():
    """Required rows are NOT scored for utility, but ALL rows contribute to distance_tie."""
    obs = make_complete_obs(
        seed="888",
        structures={
            "structure.village": [[100, 0]],
            "structure.trial_chamber": [[200, 0]],
        },
    )
    layouts = summaries.summarize(obs)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "required",
                "kind": "structure_count",
                "feature": "structure.village",
                "at_least": 1,
                "scope": {"kind": "near_base", "radius": 512},
            },
            {
                "rule": "preferred",
                "kind": "structure_count",
                "feature": "structure.trial_chamber",
                "at_least": 1,
                "importance": 3,
                "scope": {"kind": "near_base", "radius": 512},
            },
        ],
    }

    results = query.search(layouts, req, snapshot_id="snap-1")
    assert len(results) == 1
    res = results[0]
    # Only preferred row contributes to utility units: 3 * LCM
    assert res["utility_units"] == 3 * query.LCM
    assert res["score"] == 100.0
    # Both required and preferred contribute to distance_tie
    # Village: dist 100, norm 512 -> isqrt(100^2 * 10^12) // 512 = 100_000_000 // 512 = 195312
    # Trial: dist 200, norm 512 -> isqrt(200^2 * 10^12) // 512 = 200_000_000 // 512 = 390625
    expected_tie = (100_000_000 // 512) + (200_000_000 // 512)
    assert res["distance_tie"] == expected_tie


def test_partial_biome_inventory_and_counts_allowed():
    """Partial witnesses are saved, but incomplete Preferred scope earns no utility."""
    # Only 1 sample: cherry_grove at (64, 63, 64)
    biomes = [[64, 63, 64, 1]]
    biome_names = {"1": "cherry_grove"}
    obs = make_base_obs(seed="555", biomes=biomes, biome_names=biome_names)
    for b in registry.BIOMES:
        obs["coverage"][b["id"]] = {
            "status": "partial",
            "bounds": FULL_ENVELOPE,
            "method_id": "predictor_world_lattice_y63_stride64_v1",
        }

    layouts = summaries.summarize(obs)
    origin_2048 = next(l for l in layouts if tuple(l["anchor"]) == (0, 0) and l["border_side"] == 2048)

    # Cherry slot 0 has witness at index 0 and d2 = 64^2 + 64^2 = 8192
    assert origin_2048["biome_nearest_d2"][0] == 8192
    assert origin_2048["biome_witness_refs"][0] == 0
    # But complete must be False for all scopes
    assert origin_2048["complete"][14] == [False, False, False, False]

    # Query asking for preferred cherry witness: witness found earns credit
    req_cherry = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.cherry_grove"],
                "importance": 5,
                "scope": {"kind": "near_base", "radius": 256},
            }
        ],
    }
    res_cherry = query.search([origin_2048], req_cherry, snapshot_id="snap-1")
    assert len(res_cherry) == 1
    assert res_cherry[0]["score"] == 0.0
    assert res_cherry[0]['contributions'][0]['status'] == 'unknown'

    # Query asking for preferred mushroom fields (not in samples): score 0, labeled unknown
    req_mushroom = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "origin",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.mushroom_fields"],
                "importance": 5,
                "scope": {"kind": "near_base", "radius": 256},
            }
        ],
    }
    res_mushroom = query.search([origin_2048], req_mushroom, snapshot_id="snap-1")
    assert len(res_mushroom) == 1
    assert res_mushroom[0]["score"] == 0.0
    assert res_mushroom[0]["contributions"][0]["status"] == "unknown"


def test_anchor_coordinate_tie_breaking():
    """Tied utility and distance tie break by anchor X, then anchor Z."""
    # World with village at (0, 0).
    # Layout with anchor (-256, 0) and anchor (256, 0) both have village at distance 256.
    # anchor (-256, 0) should beat anchor (256, 0) because -256 < 256.
    obs = make_complete_obs(
        seed="1234",
        structures={"structure.village": [[0, 0]]},
    )
    layouts = summaries.summarize(obs)

    # Pick the two layouts for side 2048
    l_neg = next(l for l in layouts if tuple(l["anchor"]) == (-256, 0) and l["border_side"] == 2048)
    l_pos = next(l for l in layouts if tuple(l["anchor"]) == (256, 0) and l["border_side"] == 2048)

    req = {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "recommended",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": "balanced_survival",
        "rows": [
            {
                "rule": "preferred",
                "kind": "structure_count",
                "feature": "structure.village",
                "at_least": 1,
                "importance": 5,
                "scope": {"kind": "near_base", "radius": 512},
            }
        ],
    }

    # World deduplication picks the best layout for world
    res = query.search([l_pos, l_neg], req, snapshot_id="snap-1", limit=1)
    assert len(res) == 1
    assert res[0]["anchor"] == [-256, 0]

