"""Unit tests for additive catalog-query-v2 request validation."""
import pytest
from seed_search.catalog import request
from seed_search.catalog.request import UnsupportedFeatureError
from seed_search.catalog import registry


def make_valid_v2_request():
    return {
        "request_revision": "catalog-query-v2",
        "edition": "bedrock",
        "game_build_id": "research:MC_26_50",
        "catalog_snapshot_id": "snap-v2-test",
        "world_settings_id": "default",
        "dimension": "overworld",
        "anchor_mode": "recommended",
        "border_side": 2048,
        "evidence_policy": "predicted_observations_v2",
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
                "feature": "structure.fortress",
                "at_least": 1,
                "importance": 5,
                "scope": {"kind": "near_base", "radius": 128},
            },
            {
                "rule": "preferred",
                "kind": "structure_count",
                "feature": "structure.stronghold",
                "at_least": 1,
                "importance": 3,
                "scope": {"kind": "inside_border"},
            },
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.cherry_grove", "biome.plains"],
                "importance": 1,
                "scope": {"kind": "near_base", "radius": 256},
            },
            {
                "rule": "required",
                "kind": "biome_witness",
                "any_of": ["biome.crimson_forest", "biome.warped_forest"],
                "scope": {"kind": "near_base", "radius": 64},
            },
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.basalt_deltas"],
                "importance": 5,
                "scope": {"kind": "inside_border"},
            },
        ],
    }


def test_valid_v2_request_passes_and_returns_deep_copy():
    req = make_valid_v2_request()
    validated = request.validate_request_v2(
        req,
        snapshot_id="snap-v2-test",
        game_build_id="research:MC_26_50",
        world_settings_id="default",
    )
    assert validated == req
    assert validated is not req

    # Mutation does not affect validated copy
    req["rows"].append({
        "rule": "required",
        "kind": "structure_count",
        "feature": "structure.village",
        "at_least": 2,
        "scope": {"kind": "inside_border"},
    })
    assert len(validated["rows"]) == 6


def test_v2_anchor_modes():
    req = make_valid_v2_request()
    for mode in ("origin", "recommended", "world_spawn_estimated", "world_spawn_observed"):
        req["anchor_mode"] = mode
        res = request.validate_request_v2(req)
        assert res["anchor_mode"] == mode

    req["anchor_mode"] = "spawn"  # v1 legacy name, not allowed in v2
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req)


def test_v2_border_sides():
    req = make_valid_v2_request()
    for side in (2048, 4096, 8192):
        req["border_side"] = side
        res = request.validate_request_v2(req)
        assert res["border_side"] == side

    for bad in (1024, 512, "2048", True):
        req["border_side"] = bad
        with pytest.raises(UnsupportedFeatureError):
            request.validate_request_v2(req)


def test_v2_revisions_and_constants():
    req = make_valid_v2_request()

    req_bad_rev = dict(req, request_revision="catalog-query-v1")
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req_bad_rev)

    req_bad_pol = dict(req, evidence_policy="predicted_observations_v1")
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req_bad_pol)

    req_bad_ed = dict(req, edition="java")
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req_bad_ed)

    req_bad_dim = dict(req, dimension="nether")
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req_bad_dim)


def test_v2_identity_mismatches_and_non_research_build():
    req = make_valid_v2_request()

    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(dict(req, game_build_id="release:1.20"))

    with pytest.raises(ValueError, match="Request identity mismatch"):
        request.validate_request_v2(req, snapshot_id="other-snap")

    with pytest.raises(ValueError, match="Request identity mismatch"):
        request.validate_request_v2(req, game_build_id="research:OTHER")

    with pytest.raises(ValueError, match="Request identity mismatch"):
        request.validate_request_v2(req, world_settings_id="amplified")


def test_v2_max_12_rows():
    req = make_valid_v2_request()
    row = {
        "rule": "required",
        "kind": "structure_count",
        "feature": "structure.village",
        "at_least": 1,
        "scope": {"kind": "inside_border"},
    }
    req["rows"] = [row] * 12
    res = request.validate_request_v2(req)
    assert len(res["rows"]) == 12

    req["rows"] = [row] * 13
    with pytest.raises(ValueError, match="At most twelve rows"):
        request.validate_request_v2(req)


def test_v2_radii_per_dimension():
    req = make_valid_v2_request()

    # Overworld structure with Nether radii must be rejected
    for bad_r in (64, 128):
        req["rows"] = [{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.village",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": bad_r},
        }]
        with pytest.raises(UnsupportedFeatureError):
            request.validate_request_v2(req)

    # Nether structure with Overworld radii must be rejected
    for bad_r in (512, 1024):
        req["rows"] = [{
            "rule": "required",
            "kind": "structure_count",
            "feature": "structure.fortress",
            "at_least": 1,
            "scope": {"kind": "near_base", "radius": bad_r},
        }]
        with pytest.raises(UnsupportedFeatureError):
            request.validate_request_v2(req)

    # Overworld biome with Nether radius
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": ["biome.cherry_grove"],
        "importance": 3,
        "scope": {"kind": "near_base", "radius": 64},
    }]
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req)

    # Nether biome with Overworld radius
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": ["biome.warped_forest"],
        "importance": 3,
        "scope": {"kind": "near_base", "radius": 512},
    }]
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req)


def test_v2_biome_alternatives_rules():
    req = make_valid_v2_request()

    # Mixed dimension biomes rejected
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": ["biome.plains", "biome.nether_wastes"],
        "importance": 1,
        "scope": {"kind": "inside_border"},
    }]
    with pytest.raises(UnsupportedFeatureError, match="Mixed"):
        request.validate_request_v2(req)

    # Duplicate biome alternative rejected
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": ["biome.plains", "biome.plains"],
        "importance": 1,
        "scope": {"kind": "inside_border"},
    }]
    with pytest.raises(ValueError, match="Duplicate"):
        request.validate_request_v2(req)

    # Unknown biome rejected
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": ["biome.unknown_space"],
        "importance": 1,
        "scope": {"kind": "inside_border"},
    }]
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req)

    # Empty any_of rejected
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": [],
        "importance": 1,
        "scope": {"kind": "inside_border"},
    }]
    with pytest.raises(ValueError):
        request.validate_request_v2(req)

    # Overworld biomes max 9
    ow_biomes = [f["id"] for f in registry.FEATURES_V2 if f["kind"] == "biome_witness" and f["dimension"] == "overworld"]
    assert len(ow_biomes) == 9
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": ow_biomes,
        "importance": 1,
        "scope": {"kind": "inside_border"},
    }]
    res = request.validate_request_v2(req)
    assert len(res["rows"]) == 1

    # Nether biomes max 5
    nether_biomes = [f["id"] for f in registry.FEATURES_V2 if f["kind"] == "biome_witness" and f["dimension"] == "nether"]
    assert len(nether_biomes) == 5
    req["rows"] = [{
        "rule": "preferred",
        "kind": "biome_witness",
        "any_of": nether_biomes,
        "importance": 1,
        "scope": {"kind": "inside_border"},
    }]
    res = request.validate_request_v2(req)
    assert len(res["rows"]) == 1


def test_v2_rejects_bools_in_numeric_fields():
    req = make_valid_v2_request()

    # at_least = True
    req["rows"] = [{
        "rule": "required",
        "kind": "structure_count",
        "feature": "structure.village",
        "at_least": True,
        "scope": {"kind": "inside_border"},
    }]
    with pytest.raises(ValueError):
        request.validate_request_v2(req)

    # importance = True
    req["rows"] = [{
        "rule": "preferred",
        "kind": "structure_count",
        "feature": "structure.village",
        "at_least": 1,
        "importance": True,
        "scope": {"kind": "inside_border"},
    }]
    with pytest.raises(ValueError):
        request.validate_request_v2(req)

    # radius = True
    req["rows"] = [{
        "rule": "required",
        "kind": "structure_count",
        "feature": "structure.village",
        "at_least": 1,
        "scope": {"kind": "near_base", "radius": True},
    }]
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request_v2(req)


def test_load_request_v2_duplicate_keys():
    json_text = '''{
        "request_revision": "catalog-query-v2",
        "request_revision": "catalog-query-v2"
    }'''
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        request.load_request_v2(json_text)


def test_v1_validate_request_unchanged_and_rejects_v2():
    req_v2 = make_valid_v2_request()
    # v1 validator must reject v2 request
    with pytest.raises(UnsupportedFeatureError):
        request.validate_request(req_v2)
