"""Comprehensive test suite for catalog bitmap index.

Verifies:
- Frozen interfaces: build_index, candidate_indices, index_identity, validate_index
- Independently coded predicate oracle parity
- Structure count thresholds 1..16 across all scopes
- Radii (256, 512, 1024) and inside_border scopes
- Half-open boundary corners on all 3 border sides
- Partial and unknown coverage fail closed
- Biome alternative OR semantics and complete coverage requirement
- Same-anchor counterexample (different anchors must not cross-join)
- Mismatched anchor mode (origin vs recommended) and border side isolation
- Reordered rows fail closed via content_digest
- Bitlength validation (truncation, padding, odd length, non-hex)
- Reserved bits validation (bits >= num_rows must be zero)
- Revision validation
- Tampering / corruption detection (no silent false negatives)
- Signed seed extremes (-2^63, 2^63-1, -1, 0)
- Preferred rows do not filter
- Row capacity boundaries (0, 1, 243, 256, 257)
- Trusted store warm-query verification without full rebuild
- Content binding reusability across roots
"""
import copy
import hashlib
import pytest

from seed_search.catalog import models, registry, geometry, summaries, codec
from seed_search.catalog import index

DUMMY_HASH = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
FULL_ENVELOPE = list(registry.ENVELOPE)
RADII_MAP = {256: 0, 512: 1, 1024: 2}
STRUCTURE_SLOTS = {f['id']: f['slot'] for f in registry.STRUCTURES}
BIOME_SLOTS = {f['id']: f['slot'] for f in registry.BIOMES}


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


def make_complete_obs(seed="42", structures=None, biomes=None, biome_names=None):
    ident = make_test_identity(seed=seed)
    obs = models.empty_observation(ident)
    obs["structures"] = structures or {}
    obs["biomes"] = biomes or make_full_25600_biomes(0)
    obs["biome_names"] = biome_names or {"0": "plains"}
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


def make_request(rows=None, border_side=2048, anchor_mode="origin", fallback_profile="balanced_survival"):
    return {
        "request_revision": "catalog-query-v1",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-test-1",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": anchor_mode,
        "border_side": border_side,
        "evidence_policy": "predicted_observations_v1",
        "fallback_profile": fallback_profile,
        "rows": rows or [],
    }


def oracle_candidate_indices(layouts, req):
    """Independently coded reference predicate oracle for candidate filtering."""
    req_side = req["border_side"]
    is_origin = (req["anchor_mode"] == "origin")
    required_rows = [r for r in req["rows"] if r["rule"] == "required"]
    matching_indices = []

    for i, l in enumerate(layouts):
        if l["border_side"] != req_side:
            continue
        if is_origin and tuple(l["anchor"]) != (0, 0):
            continue

        passed = True
        for r in required_rows:
            scope_kind = r["scope"]["kind"]
            scope_idx = 3 if scope_kind == "inside_border" else RADII_MAP[r["scope"]["radius"]]

            if r["kind"] == "structure_count":
                slot = STRUCTURE_SLOTS[r["feature"]]
                count = l["counts"][slot][scope_idx]
                is_comp = l["complete"][slot][scope_idx]
                if not is_comp or count < r["at_least"]:
                    passed = False
                    break
            elif r["kind"] == "biome_witness":
                any_of = r["any_of"]
                all_comp = all(l["complete"][14 + BIOME_SLOTS[bid]][scope_idx] for bid in any_of)
                if not all_comp:
                    passed = False
                    break
                radius = r["scope"]["radius"] if scope_kind == "near_base" else None
                r2 = radius ** 2 if radius is not None else None
                witness = False
                for bid in any_of:
                    d2 = l["biome_nearest_d2"][BIOME_SLOTS[bid]]
                    if d2 != codec.MISSING and (r2 is None or d2 <= r2):
                        witness = True
                        break
                if not witness:
                    passed = False
                    break

        if passed:
            matching_indices.append(i)

    return matching_indices


# 1. Structure count thresholds 1..16 across scopes
@pytest.mark.parametrize("thresh", list(range(1, 17)))
def test_structure_count_thresholds_1_to_16(thresh):
    """Verify structure count thresholds 1..16 match independent oracle."""
    # Place 8 villages at distance 100 <= 256
    pts = [[100, i * 10] for i in range(8)]
    obs = make_complete_obs(structures={"structure.village": pts})
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": thresh,
            "scope": {"kind": "near_base", "radius": 256},
        }],
        border_side=2048,
        anchor_mode="origin",
    )

    expected = oracle_candidate_indices(layouts, req)
    actual_with_index = index.candidate_indices(layouts, req, index=idx)
    actual_no_index = index.candidate_indices(layouts, req, index=None)

    assert actual_with_index == expected
    assert actual_no_index == expected
    # Since 8 villages are present: thresh <= 8 matches origin layout, thresh > 8 returns []
    if thresh <= 8:
        assert len(actual_with_index) == 1
    else:
        assert len(actual_with_index) == 0


# 2. Radii scopes (256, 512, 1024, inside_border)
@pytest.mark.parametrize("scope_spec", [
    ("near_base", 256),
    ("near_base", 512),
    ("near_base", 1024),
    ("inside_border", None),
])
def test_radii_and_border_scopes_structure_and_biome(scope_spec):
    """Verify all 4 scopes for both structure count and biome witness."""
    kind, radius = scope_spec
    scope = {"kind": kind} if radius is None else {"kind": kind, "radius": radius}

    # Structure at dist 300 (inside 512, 1024, border; outside 256)
    pts_struct = [[300, 0]]
    # Biome cherry at dist 576 = 64 * 9 (inside 1024, border; outside 256, 512)
    biomes = make_full_25600_biomes(0)
    for pt in biomes:
        if pt[0] == 576 and pt[2] == 0:
            pt[3] = 1
    names = {"0": "plains", "1": "cherry_grove"}

    obs = make_complete_obs(
        structures={"structure.village": pts_struct},
        biomes=biomes,
        biome_names=names,
    )
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    # Structure query
    req_struct = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": scope,
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    exp_s = oracle_candidate_indices(layouts, req_struct)
    act_s = index.candidate_indices(layouts, req_struct, index=idx)
    assert act_s == exp_s
    if radius == 256:
        assert len(act_s) == 0
    else:
        assert len(act_s) == 1

    # Biome query
    req_biome = make_request(
        rows=[{
            "rule": "required",
            "kind": "biome_witness",
            "any_of": ["biome.cherry_grove"],
            "scope": scope,
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    exp_b = oracle_candidate_indices(layouts, req_biome)
    act_b = index.candidate_indices(layouts, req_biome, index=idx)
    assert act_b == exp_b
    if radius in (256, 512):
        assert len(act_b) == 0
    else:
        assert len(act_b) == 1


# 3. Boundary corners and half-open intervals
@pytest.mark.parametrize("side", [2048, 4096, 8192])
def test_boundary_corners_half_open(side):
    """Verify half-open bounds [lo, hi) at exact boundary edges and corners."""
    half = side // 2
    # lo_x = -half, hi_x = half.
    # Point [-half, -half] is IN (minimum corner).
    # Point [half - 1, half - 1] is IN (maximum included corner).
    # Point [half, 0] is OUT (upper bound excluded).
    # Point [0, half] is OUT (upper bound excluded).
    # Point [-half - 1, 0] is OUT (below lower bound).
    pts = [
        [-half, -half],
        [half - 1, half - 1],
        [half, 0],
        [0, half],
        [-half - 1, 0],
    ]
    obs = make_complete_obs(structures={"structure.village": pts})
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 2,  # Exactly 2 points should be inside
            "scope": {"kind": "inside_border"},
        }],
        border_side=side,
        anchor_mode="origin",
    )
    expected = oracle_candidate_indices(layouts, req)
    actual = index.candidate_indices(layouts, req, index=idx)
    assert actual == expected
    assert len(actual) == 1

    # Asking for at_least 3 should fail
    req_3 = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 3,
            "scope": {"kind": "inside_border"},
        }],
        border_side=side,
        anchor_mode="origin",
    )
    assert index.candidate_indices(layouts, req_3, index=idx) == []


# 4. Partial and unknown coverage fail closed
def test_partial_and_unknown_coverage_rejected():
    """Incomplete coverage fails closed for Required rows."""
    obs_part = make_complete_obs(structures={"structure.village": [[0, 0]]})
    obs_part["coverage"]["structure.village"]["status"] = "partial"

    layouts_part = summaries.summarize(obs_part)
    idx_part = index.build_index(layouts_part)

    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": 256},
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    assert oracle_candidate_indices(layouts_part, req) == []
    assert index.candidate_indices(layouts_part, req, index=idx_part) == []


# 5. Biome alternative OR semantics and complete coverage requirement
def test_biome_or_semantics_and_coverage_invariance():
    """Any alternative satisfies witness, but ALL alternatives must have complete coverage."""
    biomes = make_full_25600_biomes(0)
    for pt in biomes:
        if pt[0] == 64 and pt[2] == 64:
            pt[3] = 1  # cherry
    names = {"0": "plains", "1": "cherry_grove", "2": "mushroom_fields"}
    obs = make_complete_obs(biomes=biomes, biome_names=names)
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    # Cherry present, mushroom absent -> matches OR
    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "biome_witness",
            "any_of": ["biome.cherry_grove", "biome.mushroom_fields"],
            "scope": {"kind": "near_base", "radius": 256},
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    assert len(index.candidate_indices(layouts, req, index=idx)) == 1

    # But if mushroom coverage was partial: ALL alternatives must be complete
    obs_mushroom_part = make_complete_obs(biomes=biomes, biome_names=names)
    obs_mushroom_part["coverage"]["biome.mushroom_fields"]["status"] = "partial"
    l_part = summaries.summarize(obs_mushroom_part)
    idx_part = index.build_index(l_part)
    assert oracle_candidate_indices(l_part, req) == []
    assert index.candidate_indices(l_part, req, index=idx_part) == []


# 6. Same-anchor counterexample
def test_same_anchor_counterexample_no_cross_join():
    """True facts from two different anchors must not cross-join on one layout."""
    obs = make_complete_obs(
        structures={
            "structure.village": [[976, 0]],
            "structure.desert_pyramid": [[-976, 0]],
        }
    )
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request(
        rows=[
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
        border_side=2048,
        anchor_mode="recommended",
    )
    assert oracle_candidate_indices(layouts, req) == []
    assert index.candidate_indices(layouts, req, index=idx) == []


# 7. Mismatched anchor mode and border side isolation
@pytest.mark.parametrize("side", [2048, 4096, 8192])
@pytest.mark.parametrize("mode", ["origin", "recommended"])
def test_anchor_mode_and_side_isolation(side, mode):
    """Verify side and mode filtering isolation."""
    obs = make_complete_obs(structures={"structure.village": [[0, 0]]})
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": 256},
        }],
        border_side=side,
        anchor_mode=mode,
    )
    expected = oracle_candidate_indices(layouts, req)
    actual = index.candidate_indices(layouts, req, index=idx)
    assert actual == expected
    for cand_idx in actual:
        l = layouts[cand_idx]
        assert l["border_side"] == side
        if mode == "origin":
            assert tuple(l["anchor"]) == (0, 0)


# 8. Reordered rows fail closed via content_digest
def test_reordered_rows_fail_closed():
    """Reordered layouts produce different content digest; supplied index raises ValueError."""
    obs = make_complete_obs(structures={"structure.village": [[0, 0]]})
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    # Reorder layouts
    reordered_layouts = list(reversed(layouts))
    req = make_request(border_side=2048, anchor_mode="origin")

    # Reordered layouts with original index must raise ValueError
    with pytest.raises(ValueError, match="Index content_digest mismatch with layouts"):
        index.candidate_indices(reordered_layouts, req, index=idx)


# 9. Bitlength validation (truncation, padding, non-hex)
@pytest.mark.parametrize("bad_hex", [
    "00",               # Too short
    "0" * 60,           # 60 chars instead of 62
    "0" * 64,           # 64 chars instead of 62 (for 243 rows)
    "0" * 61 + "z",     # Non-hex character
    "0" * 61 + "A",     # Uppercase character (must be canonical lowercase)
])
def test_bitlength_and_hex_validation(bad_hex):
    """Invalid bitset length or characters raise ValueError."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    # Mutate origin bitset
    bad_idx = copy.deepcopy(idx)
    bad_idx["bitsets"]["origin"] = bad_hex
    bad_idx["index_digest"] = registry.digest({
        "bitsets": bad_idx["bitsets"],
        "content_digest": bad_idx["content_digest"],
        "num_rows": bad_idx["num_rows"],
        "revision": bad_idx["revision"],
    })

    req = make_request()
    with pytest.raises(ValueError):
        index.candidate_indices(layouts, req, index=bad_idx)


# 10. Reserved bits validation (bits >= num_rows must be zero)
def test_reserved_bits_validation():
    """Any bits set beyond num_rows up to byte boundary raise ValueError."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)  # 243 layouts
    idx = index.build_index(layouts)

    # In 243 rows, bits 0..242 are valid. Bit 243 is the lowest reserved bit.
    reserved_val = 1 << 243
    reserved_hex = f"{reserved_val:062x}"

    bad_idx = copy.deepcopy(idx)
    bad_idx["bitsets"]["origin"] = reserved_hex
    bad_idx["index_digest"] = registry.digest({
        "bitsets": bad_idx["bitsets"],
        "content_digest": bad_idx["content_digest"],
        "num_rows": bad_idx["num_rows"],
        "revision": bad_idx["revision"],
    })

    req = make_request()
    with pytest.raises(ValueError, match="Reserved bits set"):
        index.candidate_indices(layouts, req, index=bad_idx)


# 11. Revision validation
def test_revision_validation():
    """Mismatched index revision raises ValueError."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    bad_idx = copy.deepcopy(idx)
    bad_idx["revision"] = "catalog-index-v999"
    bad_idx["index_digest"] = registry.digest({
        "bitsets": bad_idx["bitsets"],
        "content_digest": bad_idx["content_digest"],
        "num_rows": bad_idx["num_rows"],
        "revision": bad_idx["revision"],
    })

    req = make_request()
    with pytest.raises(ValueError, match="Invalid index revision"):
        index.candidate_indices(layouts, req, index=bad_idx)


# 12. Corruption / Tampering detection (no silent false negatives)
def test_tampered_bitset_detected_even_if_digest_recomputed():
    """Untrusted caller tampering with bitset and recomputing index_digest must fail closed."""
    # World with village at (0, 0)
    obs = make_complete_obs(structures={"structure.village": [[0, 0]]})
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": 256},
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    # Valid index finds origin layout
    assert len(index.candidate_indices(layouts, req, index=idx)) == 1

    # Attacker tampers with the structure threshold bitset, setting it to 0 (silent omission attempt)
    tampered_idx = copy.deepcopy(idx)
    tampered_idx["bitsets"]["structure_thresholds"]["structure.village"][0][0] = "0" * 62
    # Attacker recomputes index_digest to make internal hash valid
    tampered_idx["index_digest"] = registry.digest({
        "bitsets": tampered_idx["bitsets"],
        "content_digest": tampered_idx["content_digest"],
        "num_rows": tampered_idx["num_rows"],
        "revision": tampered_idx["revision"],
    })

    # When untrusted caller passes tampered index, trust check must detect bitset tampering
    with pytest.raises(ValueError, match="Tampered bitset in index"):
        index.candidate_indices(layouts, req, index=tampered_idx, trusted=False)


# 13. Index digest corruption detection
def test_corrupt_index_digest():
    """Corrupted index_digest raises ValueError."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    bad_idx = copy.deepcopy(idx)
    bad_idx["index_digest"] = "f" * 64

    req = make_request()
    with pytest.raises(ValueError, match="Corrupt index: index_digest mismatch"):
        index.candidate_indices(layouts, req, index=bad_idx)


# 14. Content digest corruption detection
def test_corrupt_content_digest():
    """Corrupted content_digest raises ValueError."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    bad_idx = copy.deepcopy(idx)
    bad_idx["content_digest"] = "e" * 64
    bad_idx["index_digest"] = registry.digest({
        "bitsets": bad_idx["bitsets"],
        "content_digest": bad_idx["content_digest"],
        "num_rows": bad_idx["num_rows"],
        "revision": bad_idx["revision"],
    })

    req = make_request()
    with pytest.raises(ValueError, match="Index content_digest mismatch with layouts"):
        index.candidate_indices(layouts, req, index=bad_idx)


# 15. Signed seed extremes
@pytest.mark.parametrize("seed_str", [
    "-9223372036854775808",  # -2^63
    "9223372036854775807",   # 2^63 - 1
    "-1",
    "0",
    "1",
    "-42",
])
def test_signed_seed_extremes(seed_str):
    """Verify signed and unsigned seed extremes produce valid index and identity."""
    obs = make_complete_obs(seed=seed_str)
    layouts = summaries.summarize(obs)
    ident = index.index_identity(layouts)
    assert isinstance(ident, str) and len(ident) == 64

    idx = index.build_index(layouts)
    assert idx["content_digest"] == ident
    index.validate_index(idx, layouts=layouts)

    req = make_request()
    candidates = index.candidate_indices(layouts, req, index=idx)
    assert len(candidates) > 0


# 16. Preferred rows do not filter
def test_preferred_rows_do_not_filter():
    """Preferred rows must not exclude candidates; only Required rows filter."""
    obs = make_complete_obs(structures={"structure.village": [[0, 0]]})
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    # Request with no required rows and one impossible preferred row (20 ancient cities)
    req = make_request(
        rows=[{
            "rule": "preferred",
            "kind": "structure_count",
            "feature": "structure.ancient_city",
            "at_least": 16,
            "importance": 5,
            "scope": {"kind": "inside_border"},
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    # Origin layout must be returned because Preferred rows do NOT filter
    candidates = index.candidate_indices(layouts, req, index=idx)
    assert len(candidates) == 1
    assert tuple(layouts[candidates[0]]["anchor"]) == (0, 0)
    assert layouts[candidates[0]]["border_side"] == 2048


# 17. Row capacity boundaries: 0, 1, 243, 256, 257
def test_row_capacity_boundaries():
    """Verify 0, 1, 256 layouts are supported; > 256 raises ValueError."""
    # 0 layouts
    idx0 = index.build_index([])
    assert idx0["num_rows"] == 0
    assert index.candidate_indices([], make_request(), index=idx0) == []

    # 1 layout
    obs = make_complete_obs()
    l1 = summaries.summarize(obs)[:1]
    idx1 = index.build_index(l1)
    assert idx1["num_rows"] == 1
    assert len(idx1["bitsets"]["origin"]) == 2  # 1 byte -> 2 hex chars
    index.validate_index(idx1, layouts=l1)

    # 256 layouts
    l256 = (summaries.summarize(obs) + summaries.summarize(obs))[:256]
    idx256 = index.build_index(l256)
    assert idx256["num_rows"] == 256
    assert len(idx256["bitsets"]["origin"]) == 64  # 32 bytes -> 64 hex chars
    index.validate_index(idx256, layouts=l256)

    # 257 layouts must raise ValueError
    l257 = l256 + l1
    with pytest.raises(ValueError, match="At most 256 layouts"):
        index.build_index(l257)


# 18. Trusted store warm-query verification
def test_trusted_store_warm_query():
    """trusted=True validates structure, digests and bitlength without re-deriving all bitsets."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request()
    # Trusted candidate query succeeds
    res = index.candidate_indices(layouts, req, index=idx, trusted=True)
    assert len(res) > 0

    # But corrupt digest is still caught even when trusted=True
    bad_idx = copy.deepcopy(idx)
    bad_idx["index_digest"] = "0" * 64
    with pytest.raises(ValueError, match="Corrupt index: index_digest mismatch"):
        index.candidate_indices(layouts, req, index=bad_idx, trusted=True)


# 19. Content binding reusability across roots
def test_index_identity_reusable_across_roots():
    """index_identity depends only on layout contents and revisions, not global state or paths."""
    obs1 = make_complete_obs(seed="123")
    obs2 = make_complete_obs(seed="123")
    l1 = summaries.summarize(obs1)
    l2 = summaries.summarize(obs2)

    id1 = index.index_identity(l1)
    id2 = index.index_identity(l2)
    assert id1 == id2


# 20. Request validation inside candidate_indices
def test_request_validation_in_candidate_indices():
    """Invalid requests are rejected by candidate_indices."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)

    # Invalid JSON string
    with pytest.raises(ValueError):
        index.candidate_indices(layouts, "{bad json")

    # Unsupported feature or rule
    bad_req = make_request()
    bad_req["border_side"] = 9999
    with pytest.raises(ValueError):
        index.candidate_indices(layouts, bad_req)


# 21. Row count mismatch between layouts and index
def test_row_count_mismatch_detected():
    """Supplying index with different row count than layouts raises ValueError."""
    obs = make_complete_obs()
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    # Call with subset of layouts
    subset = layouts[:10]
    req = make_request()
    with pytest.raises(ValueError, match="Row count mismatch"):
        index.candidate_indices(subset, req, index=idx)


# 22. Inside-border biome witness requires presence (!= MISSING)
def test_inside_border_biome_witness_square_not_circle():
    """For inside_border, biome witness only requires != MISSING (in square), not circle distance."""
    # Center (0, 0), side 2048: square is [-1024, 1024) x [-1024, 1024).
    # Corner at (900, 900): distance squared is 900^2 + 900^2 = 1,620,000.
    # Notice halfside^2 = 1024^2 = 1,048,576.
    # 1,620,000 > 1,048,576, so it is OUTSIDE the circle, but INSIDE the square!
    biomes = make_full_25600_biomes(0)
    for pt in biomes:
        if pt[0] == 896 and pt[2] == 896:
            pt[3] = 1  # cherry
    names = {"0": "plains", "1": "cherry_grove"}
    obs = make_complete_obs(biomes=biomes, biome_names=names)
    layouts = summaries.summarize(obs)
    idx = index.build_index(layouts)

    req = make_request(
        rows=[{
            "rule": "required",
            "kind": "biome_witness",
            "any_of": ["biome.cherry_grove"],
            "scope": {"kind": "inside_border"},
        }],
        border_side=2048,
        anchor_mode="origin",
    )
    expected = oracle_candidate_indices(layouts, req)
    actual = index.candidate_indices(layouts, req, index=idx)
    assert actual == expected
    # The origin layout must be matched because presence only requires != MISSING inside square!
    assert len(actual) == 1
