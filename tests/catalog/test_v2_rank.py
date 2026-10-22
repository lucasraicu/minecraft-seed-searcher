"""Unit tests for additive catalog-query-v2 ranking engine (rank_v2).

Covers:
- sameanchor crossdim (Overworld and Nether conditions bound to the same anchor)
- 64vs256Nether (Nether radii and dimension-specific distance tie normalization)
- negativeprojection preserved (Python floor division // 8 and unsigned 64-bit seed order)
- partialstrongholdpositive (incomplete coverage with observed count >= at_least passes)
- missingbiomepending (unseen biome yields pending unresolved candidate, does not displace match)
- zeroPreferred oldfallback parity (exact parity with scoring.profile_units)
- deterministicunique-worldties/paginationkeys (best anchor per world, tie breaking, keep_keys)
"""
import json
import math
import pytest
from decimal import Decimal

from seed_search.catalog import models, codec, registry, scoring
from seed_search.catalog import query
from seed_search.catalog.query import rank_v2

DUMMY_HASH = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
LCM = 720720


def make_v2_feature_dict(feature_overrides=None):
    """Build a default 31-feature dictionary for a catalog-summary-v2 row."""
    features = {}
    for f in registry.FEATURES_V2:
        fid = f["id"]
        dim = f["dimension"]
        kind = f["kind"]
        if kind == "structure_count":
            features[fid] = {
                "dimension": dim,
                "counts": [0, 0, 0, 0],
                "complete": [True, True, True, True],
                "nearest_d2": None,
                "witness": None,
            }
        else:
            features[fid] = {
                "dimension": dim,
                "counts": [0, 0, 0, 0],
                "complete": [False, False, False, False],
                "nearest_d2": None,
                "witness": None,
            }
    if feature_overrides:
        for fid, override in feature_overrides.items():
            if fid in features:
                features[fid].update(override)
            else:
                features[fid] = override
    return features


def make_v2_summary(
    seed="42",
    world_id="world-1",
    anchor=(0, 0),
    nether_anchor=None,
    anchor_modes=("origin", "recommended"),
    border_side=2048,
    layout_id=None,
    feature_overrides=None,
    legacy_overrides=None,
):
    """Build a synthetic catalog-summary-v2 dictionary for testing."""
    ax, az = anchor
    nax, naz = nether_anchor if nether_anchor is not None else (ax // 8, az // 8)
    lid = layout_id or f"layout-{world_id}-{ax}-{az}-{border_side}"

    legacy = {
        "revision": "catalog-summary-v1",
        "observation_id": DUMMY_HASH,
        "world_id": world_id,
        "layout_id": lid,
        "seed": str(seed),
        "anchor": [ax, az],
        "border_side": border_side,
        "counts": [[0, 0, 0, 0] for _ in range(14)],
        "structure_nearest_d2": [codec.MISSING] * 14,
        "biome_nearest_d2": [codec.MISSING] * 9,
        "biome_witness_refs": [codec.MISSING] * 9,
        "complete": [[True, True, True, True] for _ in range(23)],
    }
    if legacy_overrides:
        legacy.update(legacy_overrides)

    features = make_v2_feature_dict(feature_overrides)

    return {
        "revision": "catalog-summary-v2",
        "registry_revision": registry.REGISTRY_REVISION_V2,
        "source_observation_id": DUMMY_HASH,
        "world_id": world_id,
        "seed": str(seed),
        "anchor": [ax, az],
        "nether_anchor": [nax, naz],
        "anchor_modes": list(anchor_modes),
        "border_side": border_side,
        "layout_id": lid,
        "features": features,
        "legacy": legacy,
    }


def make_v2_request(
    rows,
    anchor_mode="recommended",
    border_side=2048,
    fallback_profile="balanced_survival",
):
    """Build a validated catalog-query-v2 request payload."""
    return {
        "request_revision": "catalog-query-v2",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-v2-test",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": anchor_mode,
        "border_side": border_side,
        "evidence_policy": "predicted_observations_v2",
        "fallback_profile": fallback_profile,
        "rows": rows,
    }


def test_sameanchor_crossdim():
    """Verify that every required condition binds the SAME summary across OW and Nether."""
    req = make_v2_request([
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
            "feature": "structure.fortress",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": 128},
        },
    ])

    # World 1: Anchor (0, 0) has village in OW radius 512 AND fortress in Nether radius 128
    s1 = make_v2_summary(
        world_id="world-1",
        anchor=(0, 0),
        feature_overrides={
            "structure.village": {
                "counts": [0, 1, 1, 1],
                "nearest_d2": 40000,
                "complete": [True, True, True, True],
            },
            "structure.fortress": {
                "counts": [0, 1, 1, 1],
                "nearest_d2": 10000,
                "complete": [True, True, True, True],
            },
        },
    )

    # World 2: Anchor (0, 0) has village in OW, but fortress count is 0
    s2_a = make_v2_summary(
        world_id="world-2",
        anchor=(0, 0),
        feature_overrides={
            "structure.village": {
                "counts": [0, 1, 1, 1],
                "nearest_d2": 40000,
                "complete": [True, True, True, True],
            },
            "structure.fortress": {
                "counts": [0, 0, 0, 0],
                "nearest_d2": None,
                "complete": [True, True, True, True],
            },
        },
    )
    # World 2: Anchor (256, 256) has fortress in Nether, but village count is 0
    s2_b = make_v2_summary(
        world_id="world-2",
        anchor=(256, 256),
        feature_overrides={
            "structure.village": {
                "counts": [0, 0, 0, 0],
                "nearest_d2": None,
                "complete": [True, True, True, True],
            },
            "structure.fortress": {
                "counts": [0, 1, 1, 1],
                "nearest_d2": 10000,
                "complete": [True, True, True, True],
            },
        },
    )

    res = rank_v2([s1, s2_a, s2_b], req)
    assert res["matched_worlds"] == 1
    assert len(res["results"]) == 1
    assert res["results"][0]["world_id"] == "world-1"
    assert res["results"][0]["anchor"] == [0, 0]
    assert res["results"][0]["nether_anchor"] == [0, 0]
    # World 2 failed because neither anchor satisfied both OW and Nether requirements together
    assert res["unresolved_candidates"] == []


def test_64vs256_nether():
    """Verify Nether radii 64 vs 256 and dimension-specific distance normalization."""
    # Fortress is at d=100 (d2=10000). Radius 64: count 0. Radius 128 & 256: count 1.
    s = make_v2_summary(
        world_id="world-nether",
        anchor=(0, 0),
        feature_overrides={
            "structure.fortress": {
                "counts": [0, 1, 1, 1],
                "nearest_d2": 10000,
                "complete": [True, True, True, True],
            },
        },
    )

    # Request with radius 64: should fail (0 < 1 and complete is True)
    req_64 = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.fortress",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": 64},
        },
    ])
    res_64 = rank_v2([s], req_64)
    assert res_64["matched_worlds"] == 0
    assert len(res_64["results"]) == 0

    # Request with radius 256: should pass
    req_256 = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.fortress",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": 256},
        },
    ])
    res_256 = rank_v2([s], req_256)
    assert res_256["matched_worlds"] == 1
    assert len(res_256["results"]) == 1
    # Check normalizer for radius 256: isqrt(10000 * 10^12) // 256 = 100_000_000 // 256 = 390625
    expected_dist = math.isqrt(10000 * 10**12) // 256
    assert res_256["results"][0]["distance_tie"] == expected_dist

    # Request with inside_border for fortress: normalizer must be 512
    req_inside = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.fortress",
            "at_least": 1,
            "scope": {"kind": "inside_border"},
        },
    ])
    res_inside = rank_v2([s], req_inside)
    assert res_inside["matched_worlds"] == 1
    expected_dist_inside = math.isqrt(10000 * 10**12) // 512
    assert res_inside["results"][0]["distance_tie"] == expected_dist_inside


def test_negativeprojection_preserved():
    """Verify negative coordinate Python floor division and unsigned 64-bit seed order."""
    # Anchor [-256, -512] -> Nether anchor [-32, -64]
    s_neg1 = make_v2_summary(
        seed="-1",  # unsigned 64-bit pattern: 18446744073709551615
        world_id="world-neg1",
        anchor=(-256, -512),
        feature_overrides={
            "structure.village": {
                "counts": [1, 1, 1, 1],
                "nearest_d2": 100,
                "complete": [True, True, True, True],
            },
        },
    )
    # Anchor [-5, -9] -> Nether anchor [-1, -2] via Python floor division
    s_neg2 = make_v2_summary(
        seed="1",  # unsigned 64-bit pattern: 1
        world_id="world-pos1",
        anchor=(-5, -9),
        feature_overrides={
            "structure.village": {
                "counts": [1, 1, 1, 1],
                "nearest_d2": 100,
                "complete": [True, True, True, True],
            },
        },
    )

    req = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "inside_border"},
        },
    ])

    res = rank_v2([s_neg1, s_neg2], req, keep_keys=True)
    assert res["matched_worlds"] == 2
    # Verify floor division nether anchors
    cand_by_wid = {c["world_id"]: c for c in res["results"]}
    assert cand_by_wid["world-neg1"]["nether_anchor"] == [-32, -64]
    assert cand_by_wid["world-pos1"]["nether_anchor"] == [-1, -2]

    # Verify tie-breaking: both have identical utility and distance tie.
    # world-pos1 (seed 1, unsigned 1) must sort BEFORE world-neg1 (seed -1, unsigned 2^64-1).
    assert res["results"][0]["world_id"] == "world-pos1"
    assert res["results"][1]["world_id"] == "world-neg1"


def test_partialstrongholdpositive():
    """Verify that incomplete stronghold coverage passes when observed count >= at_least,
    and contributes explicit lowerbound units in Preferred."""
    s = make_v2_summary(
        world_id="world-sh",
        anchor=(0, 0),
        feature_overrides={
            "structure.stronghold": {
                "counts": [1, 1, 1, 1],
                "nearest_d2": 50000,
                "complete": [False, False, False, False],  # incomplete coverage
            },
        },
    )

    # Required stronghold condition passes because observed count >= 1
    req_req = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.stronghold",
            "at_least": 1,
            "scope": {"kind": "inside_border"},
        },
    ])
    res_req = rank_v2([s], req_req)
    assert res_req["matched_worlds"] == 1
    assert len(res_req["results"]) == 1
    assert res_req["results"][0]["world_id"] == "world-sh"

    # Preferred condition with incomplete stronghold contributes explicit lowerbound units
    req_pref = make_v2_request([
        {
            "rule": "preferred",
            "kind": "structure_count",
            "feature": "structure.stronghold",
            "at_least": 2,
            "importance": 3,
            "scope": {"kind": "inside_border"},
        },
    ])
    res_pref = rank_v2([s], req_pref)
    assert res_pref["matched_worlds"] == 1
    cand = res_pref["results"][0]
    expected_units = 3 * (1 * LCM // 2)  # min(count=1, at_least=2) / 2
    assert cand["utility_units"] == expected_units
    assert len(cand["contributions"]) == 1
    c = cand["contributions"][0]
    assert c["feature"] == "structure.stronghold"
    assert c["count"] == 1
    assert c["at_least"] == 2
    assert c["complete"] is False
    assert c["status"] == "unknown"
    assert c["positive_witness"] is True
    assert c["utility_units"] == expected_units


def test_missingbiomepending():
    """Verify that unseen biome yields pending unresolved candidate without displacing confirmed matches."""
    req = make_v2_request([
        {
            "rule": "required",
            "kind": "biome_witness",
            "any_of": ["biome.cherry_grove"],
            "scope": {"kind": "near_base", "radius": 512},
        },
    ])

    # World 1: cherry_grove is unseen, complete is False
    s1 = make_v2_summary(
        world_id="world-pending",
        anchor=(0, 0),
        feature_overrides={
            "biome.cherry_grove": {
                "counts": [0, 0, 0, 0],
                "nearest_d2": None,
                "complete": [False, False, False, False],
            },
        },
    )

    # World 2: cherry_grove has positive witness
    s2 = make_v2_summary(
        world_id="world-confirmed",
        anchor=(0, 0),
        feature_overrides={
            "biome.cherry_grove": {
                "counts": [0, 1, 1, 1],
                "nearest_d2": 90000,
                "complete": [False, False, False, False],
            },
        },
    )

    # Query with World 1 only: should be pending in unresolved_candidates
    res1 = rank_v2([s1], req)
    assert res1["matched_worlds"] == 0
    assert len(res1["results"]) == 0
    assert len(res1["unresolved_candidates"]) == 1
    pending_cand = res1["unresolved_candidates"][0]
    assert pending_cand["world_id"] == "world-pending"
    assert pending_cand["status"] == "pending"
    assert "cherry_grove" in pending_cand["reason"]

    # Query with both worlds: World 2 confirmed, World 1 pending. World 1 must NOT displace World 2.
    res2 = rank_v2([s1, s2], req)
    assert res2["matched_worlds"] == 1
    assert len(res2["results"]) == 1
    assert res2["results"][0]["world_id"] == "world-confirmed"
    assert len(res2["unresolved_candidates"]) == 1
    assert res2["unresolved_candidates"][0]["world_id"] == "world-pending"

    # Definite failed required alongside pending required is no_match, not pending
    s_failed = make_v2_summary(
        world_id="world-def-fail",
        anchor=(0, 0),
        feature_overrides={
            "structure.village": {
                "counts": [0, 0, 0, 0],
                "nearest_d2": None,
                "complete": [True, True, True, True],  # complete + 0 => definite fail
            },
            "biome.cherry_grove": {
                "counts": [0, 0, 0, 0],
                "nearest_d2": None,
                "complete": [False, False, False, False],
            },
        },
    )
    req_both = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "inside_border"},
        },
        {
            "rule": "required",
            "kind": "biome_witness",
            "any_of": ["biome.cherry_grove"],
            "scope": {"kind": "near_base", "radius": 512},
        },
    ])
    res_fail = rank_v2([s_failed], req_both)
    assert res_fail["matched_worlds"] == 0
    assert len(res_fail["results"]) == 0
    # Definite failed anchor is completely excluded from unresolved_candidates
    assert len(res_fail["unresolved_candidates"]) == 0


def test_zeroPreferred_oldfallback_parity():
    """Verify exact parity with scoring.profile_units and legacy query when zero Preferred rows exist."""
    req = make_v2_request([], fallback_profile="balanced_survival")

    # Construct summary with legacy observation layout
    legacy_counts = [[0, 0, 0, 0] for _ in range(14)]
    legacy_counts[0][2] = 2  # 2 villages within 1024
    legacy_counts[1][2] = 1  # 1 temple within 1024
    legacy_structure_d2 = [codec.MISSING] * 14
    legacy_structure_d2[0] = 64 * 64
    legacy_biome_d2 = [codec.MISSING] * 9
    legacy_biome_d2[0] = 100 * 100  # plains within 1024

    legacy_overrides = {
        "counts": legacy_counts,
        "structure_nearest_d2": legacy_structure_d2,
        "biome_nearest_d2": legacy_biome_d2,
        "complete": [[True, True, True, True] for _ in range(23)],
    }

    s = make_v2_summary(
        world_id="world-fallback",
        anchor=(0, 0),
        legacy_overrides=legacy_overrides,
    )

    res = rank_v2([s], req)
    assert res["matched_worlds"] == 1
    cand = res["results"][0]

    # Compute expected using scoring.profile_units directly
    exp_units, exp_max, _ = scoring.profile_units(s["legacy"], "balanced_survival")
    assert cand["utility_units"] == int(exp_units)
    assert cand["score"] == pytest.approx(float(exp_units * 100 / exp_max), rel=1e-6)
    assert len(cand["contributions"]) == 8
    features = [c["feature"] for c in cand["contributions"]]
    assert features == list("VTAOEBHR")


def test_deterministic_unique_world_ties_and_pagination():
    """Verify deduplication to best qualifying anchor per world, tie breaking, and keep_keys."""
    req = make_v2_request([
        {
            "rule": "preferred",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 2,
            "importance": 5,
            "scope": {"kind": "near_base", "radius": 512},
        },
    ])

    # World 1 has 3 anchors:
    # Anchor 1: count 1 (utility 5 * 360360 = 1801800), d2=100
    s1_1 = make_v2_summary(
        world_id="world-1",
        anchor=(0, 0),
        feature_overrides={
            "structure.village": {"counts": [0, 1, 1, 1], "nearest_d2": 100, "complete": [True, True, True, True]},
        },
    )
    # Anchor 2: count 2 (utility 5 * 720720 = 3603600), d2=400
    s1_2 = make_v2_summary(
        world_id="world-1",
        anchor=(256, 256),
        feature_overrides={
            "structure.village": {"counts": [0, 2, 2, 2], "nearest_d2": 400, "complete": [True, True, True, True]},
        },
    )
    # Anchor 3: count 2 (utility 3603600), d2=900 (worse distance tie than Anchor 2)
    s1_3 = make_v2_summary(
        world_id="world-1",
        anchor=(-256, -256),
        feature_overrides={
            "structure.village": {"counts": [0, 2, 2, 2], "nearest_d2": 900, "complete": [True, True, True, True]},
        },
    )

    # World 2 has 1 anchor: count 2, d2=200
    s2 = make_v2_summary(
        world_id="world-2",
        anchor=(0, 0),
        feature_overrides={
            "structure.village": {"counts": [0, 2, 2, 2], "nearest_d2": 200, "complete": [True, True, True, True]},
        },
    )

    # World 3 has 1 anchor: count 2, d2=300
    s3 = make_v2_summary(
        world_id="world-3",
        anchor=(0, 0),
        feature_overrides={
            "structure.village": {"counts": [0, 2, 2, 2], "nearest_d2": 300, "complete": [True, True, True, True]},
        },
    )

    # Run with limit=2 and keep_keys=True
    res = rank_v2([s1_1, s1_2, s1_3, s2, s3], req, limit=2, keep_keys=True)
    assert res["matched_worlds"] == 3  # full unique world population before limit
    assert len(res["results"]) == 2    # truncated to limit=2

    # World 1 best anchor selected should be s1_2 (anchor [256, 256])
    # Ranking order: s2 (d2=200) < s3 (d2=300) < s1_2 (d2=400)
    assert res["results"][0]["world_id"] == "world-2"
    assert res["results"][1]["world_id"] == "world-3"
    assert "_sort_key" in res["results"][0]

    # Run with limit=10 and keep_keys=False
    res_all = rank_v2([s1_1, s1_2, s1_3, s2, s3], req, limit=10, keep_keys=False)
    assert res_all["matched_worlds"] == 3
    assert len(res_all["results"]) == 3
    assert res_all["results"][2]["world_id"] == "world-1"
    assert res_all["results"][2]["anchor"] == [256, 256]
    assert "_sort_key" not in res_all["results"][0]


def test_rank_v2_candidate_shape_and_inputs():
    """Verify required candidate fields, typed fields, and input validation."""
    s = make_v2_summary(
        world_id="world-shape",
        anchor=(256, -512),
        border_side=2048,
        feature_overrides={"structure.village": {"counts": [1, 1, 1, 1]}},
    )
    req = make_v2_request([
        {
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "inside_border"},
        },
    ])

    res = rank_v2([s], req)
    cand = res["results"][0]
    required_fields = [
        "world_id", "seed", "layout_id", "anchor", "nether_anchor",
        "border_side", "border", "bounds", "score", "utility_units",
        "distance_tie", "contributions", "counts", "structure_nearest_d2",
        "biome_nearest_d2", "complete", "feature_counts", "feature_complete",
    ]
    for rf in required_fields:
        assert rf in cand, f"Missing candidate field {rf}"
    assert cand["anchor"] == [256, -512]
    assert cand["nether_anchor"] == [32, -64]
    assert cand["bounds"] == [256 - 1024, -512 - 1024, 256 + 1024, -512 + 1024]
    assert len(cand["feature_counts"]) == 31
    assert len(cand["feature_complete"]) == 31

    # Request as JSON string
    req_json = json.dumps(req)
    res_from_str = rank_v2([s], req_json)
    assert res_from_str["matched_worlds"] == 1

    # Validation errors
    with pytest.raises(ValueError):
        rank_v2([s], req, limit=0)
    with pytest.raises(ValueError):
        rank_v2([s], req, limit="invalid")
    with pytest.raises(ValueError):
        rank_v2([s], {"invalid": "payload"})
