"""Unit tests for additive catalog-summary-v2 and legacy observation projection."""
import pytest
from seed_search.catalog import models, registry, geometry
from seed_search.catalog import summaries

DUMMY_HASH = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
FULL_ENVELOPE = list(registry.ENVELOPE)
NETHER_ENVELOPE = [-640, -640, 640, 640]


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


def make_valid_v2_obs(
    seed="42",
    structures=None,
    ow_biomes=None,
    nether_biomes=None,
    biome_names=None,
    coverage=None,
    anchors=None,
):
    ident = make_test_identity(seed=seed)
    structs = structures or {}
    for f in registry.FEATURES_V2:
        if f["kind"] == "structure_count":
            structs.setdefault(f["id"], [])

    ow_b = ow_biomes if ow_biomes is not None else make_full_25600_biomes(0)
    nether_b = nether_biomes if nether_biomes is not None else [
        [0, 64, 0, 10],
        [100, 64, 100, 11],
        [-50, 64, -50, 12],
    ]
    bnames = biome_names or {
        "0": "plains",
        "1": "cherry_grove",
        "10": "nether_wastes",
        "11": "crimson_forest",
        "12": "warped_forest",
    }

    cov = coverage or {}
    for f in registry.FEATURES_V2:
        if f["id"] not in cov:
            dim_bounds = FULL_ENVELOPE if f["dimension"] == "overworld" else NETHER_ENVELOPE
            method = "predictor_world_lattice_y63_stride64_v1" if f["kind"] == "biome_witness" else "predictor_viable_starts_v1"
            status = "complete" if f["kind"] == "structure_count" and f["id"] != "structure.stronghold" else "partial"
            cov[f["id"]] = {
                "status": status,
                "bounds": dim_bounds,
                "method_id": method,
            }

    anc = anchors or [
        {
            "mode": "world_spawn_estimated",
            "coordinate": [128, -64],
            "source_id": DUMMY_HASH,
        }
    ]

    return {
        "revision": "catalog-observation-v2",
        "registry_revision": registry.REGISTRY_REVISION_V2,
        "identity": ident,
        "bounds": {
            "overworld": FULL_ENVELOPE,
            "nether": NETHER_ENVELOPE,
        },
        "structures": structs,
        "biomes": {
            "overworld": ow_b,
            "nether": nether_b,
        },
        "biome_names": bnames,
        "coverage": cov,
        "anchors": anc,
        "realm": None,
        "metrics": {"duration_ms": 123},
        "errors": {},
    }


def test_legacy_observation_v2_projection_and_validation():
    """Verify v2 observation projects into a valid v1 observation."""
    obs_v2 = make_valid_v2_obs(
        seed="101",
        structures={
            "structure.village": [[100, 200], [6000, 6000]],  # 6000 is outside ENVELOPE
            "structure.stronghold": [[500, 500]],               # v2 only
            "structure.fortress": [[30, 40]],                   # nether
        },
    )

    obs_v2['bounds']['overworld'] = [-7000,-7000,7000,7000]
    v1_obs = summaries.legacy_observation_v2(obs_v2)
    # Must be validated by v1 validator
    models.validate_observation(v1_obs)

    assert v1_obs["revision"] == "catalog-observation-v1"
    assert v1_obs["identity"] == obs_v2["identity"]
    assert v1_obs["bounds"] == FULL_ENVELOPE

    # Only 14 v1 structures present
    assert set(v1_obs["structures"].keys()) <= {f["id"] for f in registry.STRUCTURES}
    assert "structure.stronghold" not in v1_obs["structures"]
    assert "structure.fortress" not in v1_obs["structures"]

    # Outside ENVELOPE start [6000, 6000] was dropped
    assert v1_obs["structures"]["structure.village"] == [[100, 200]]

    # Biomes projected to 25600 lattice samples
    assert len(v1_obs["biomes"]) == 25600
    assert all(pt[1] == 63 for pt in v1_obs["biomes"])

    # Metrics/errors copied
    assert v1_obs["metrics"] == {"duration_ms": 123}
    assert v1_obs["errors"] == {}

    # Original v2 obs not mutated
    assert len(obs_v2["structures"]["structure.village"]) == 2


def test_legacy_observation_v2_incomplete_lattice_demotes_to_partial():
    """Missing full lattice in v2 causes v1 biome coverage to be partial, never complete."""
    obs_v2 = make_valid_v2_obs(
        seed="202",
        ow_biomes=[[0, 63, 0, 0]],  # Only 1 sample instead of 25600
    )
    v1_obs = summaries.legacy_observation_v2(obs_v2)
    models.validate_observation(v1_obs)

    for b in registry.BIOMES:
        assert v1_obs["coverage"][b["id"]]["status"] == "partial"


def test_summarize_v2_row_count_and_anchors():
    """Verify 81 grid anchors x 3 border sides + 1 spawn anchor x 3 border sides = 246 rows."""
    obs_v2 = make_valid_v2_obs(
        seed="303",
        structures={"structure.village": [[100, 100]]},
        anchors=[{
            "mode": "world_spawn_estimated",
            "coordinate": [-128, 256],
            "source_id": DUMMY_HASH,
        }],
    )

    layouts = summaries.summarize_v2(obs_v2)
    assert len(layouts) == (81 + 1) * 3  # 246 rows

    # Verify origin anchor modes
    origin_rows = [l for l in layouts if l["anchor"] == [0, 0]]
    assert len(origin_rows) == 3
    for l in origin_rows:
        assert l["anchor_modes"] == ["origin", "recommended"]
        assert l["nether_anchor"] == [0, 0]

    # Verify regular grid anchor modes
    grid_rows = [l for l in layouts if l["anchor"] == [256, 256]]
    assert len(grid_rows) == 3
    for l in grid_rows:
        assert l["anchor_modes"] == ["recommended"]
        assert l["nether_anchor"] == [32, 32]

    # Verify spawn anchor modes and negative floor division
    spawn_rows = [l for l in layouts if l["anchor"] == [-128, 256]]
    assert len(spawn_rows) == 3
    for l in spawn_rows:
        assert l["anchor_modes"] == ["world_spawn_estimated"]
        assert l["nether_anchor"] == [-16, 32]


def test_summarize_v2_nether_negative_floor_coordinates():
    """Nether coordinates must use Python floor//8 including negative values."""
    obs_v2 = make_valid_v2_obs(
        seed="404",
        anchors=[
            {"mode": "world_spawn_observed", "coordinate": [-1, -9], "source_id": DUMMY_HASH},
        ],
    )
    layouts = summaries.summarize_v2(obs_v2)
    spawn_neg = [l for l in layouts if l["anchor"] == [-1, -9]]
    assert len(spawn_neg) == 3
    for l in spawn_neg:
        # -1 // 8 == -1, -9 // 8 == -2
        assert l["nether_anchor"] == [-1, -2]


def test_summarize_v2_all_31_features_present():
    """Every summary row contains all 31 features with exact required schema."""
    obs_v2 = make_valid_v2_obs(seed="505")
    layouts = summaries.summarize_v2(obs_v2)
    row = layouts[0]

    assert row["revision"] == "catalog-summary-v2"
    assert row["registry_revision"] == registry.REGISTRY_REVISION_V2
    assert row["source_observation_id"] == registry.digest(obs_v2)
    assert row["world_id"] == models.world_id(obs_v2["identity"])
    assert row["seed"] == "505"

    features = row["features"]
    assert len(features) == 31
    for f in registry.FEATURES_V2:
        fid = f["id"]
        assert fid in features
        feat_data = features[fid]
        assert feat_data["dimension"] == f["dimension"]
        assert isinstance(feat_data["counts"], list) and len(feat_data["counts"]) == 4
        assert isinstance(feat_data["complete"], list) and len(feat_data["complete"]) == 4
        assert feat_data["counts"] == sorted(feat_data["counts"])


def test_summarize_v2_nether_structure_and_window():
    """Nether structures use nether_anchor [x//8, z//8], fixed 1024 window, and radii 64/128/256."""
    # Place fortress at Nether (10, 20) and bastion at Nether (100, 100)
    # Overworld anchor (0, 0) -> Nether anchor (0, 0)
    # fortress distance d = sqrt(100 + 400) = sqrt(500) ~ 22.36 <= 64
    # bastion distance d = sqrt(10000 + 10000) = sqrt(20000) ~ 141.42 (<= 256, > 128)
    obs_v2 = make_valid_v2_obs(
        seed="606",
        structures={
            "structure.fortress": [[10, 20]],
            "structure.bastion": [[100, 100]],
        },
    )
    layouts = summaries.summarize_v2(obs_v2)
    origin_2048 = next(l for l in layouts if l["anchor"] == [0, 0] and l["border_side"] == 2048)

    fortress = origin_2048["features"]["structure.fortress"]
    assert fortress["dimension"] == "nether"
    assert fortress["counts"] == [1, 1, 1, 1]  # <= 64, <= 128, <= 256, <= 1024 window
    assert fortress["nearest_d2"] == 500

    bastion = origin_2048["features"]["structure.bastion"]
    assert bastion["dimension"] == "nether"
    assert bastion["counts"] == [0, 0, 1, 1]  # > 128, <= 256, <= 1024 window
    assert bastion["nearest_d2"] == 20000


def test_summarize_v2_stronghold_positive_counts_with_unknown_coverage():
    """Stronghold with partial/unknown coverage retains positive counts but complete is False."""
    obs_v2 = make_valid_v2_obs(
        seed="707",
        structures={"structure.stronghold": [[100, 100]]},
    )
    obs_v2["coverage"]["structure.stronghold"]["status"] = "partial"

    layouts = summaries.summarize_v2(obs_v2)
    origin_2048 = next(l for l in layouts if l["anchor"] == [0, 0] and l["border_side"] == 2048)

    sh = origin_2048["features"]["structure.stronghold"]
    assert sh["counts"] == [1, 1, 1, 1]
    assert sh["nearest_d2"] == 20000
    assert sh["complete"] == [False, False, False, False]


def test_summarize_v2_biomes_binary_presence_and_complete_false():
    """Biome features have 0/1 presence, witness [x, y, z], and complete is always False."""
    # Cherry grove sample at (0, 63, 100)
    # Crimson forest sample at (10, 64, 20)
    ow_biomes = make_full_25600_biomes(0)  # plains
    for pt in ow_biomes:
        if pt[0] == 0 and pt[2] == 128:
            pt[3] = 1  # cherry_grove

    nether_biomes = [
        [10, 64, 20, 11],  # crimson_forest
    ]

    obs_v2 = make_valid_v2_obs(
        seed="808",
        ow_biomes=ow_biomes,
        nether_biomes=nether_biomes,
    )
    layouts = summaries.summarize_v2(obs_v2)
    origin_2048 = next(l for l in layouts if l["anchor"] == [0, 0] and l["border_side"] == 2048)

    cherry = origin_2048["features"]["biome.cherry_grove"]
    assert cherry["counts"] == [1, 1, 1, 1]  # dist 128 <= 256
    assert cherry["witness"] == [0, 63, 128]
    assert cherry["nearest_d2"] == 128 * 128
    assert cherry["complete"] == [False, False, False, False]

    crimson = origin_2048["features"]["biome.crimson_forest"]
    assert crimson["counts"] == [1, 1, 1, 1]  # dist sqrt(500) <= 64
    assert crimson["witness"] == [10, 64, 20]
    assert crimson["nearest_d2"] == 500
    assert crimson["complete"] == [False, False, False, False]


def test_summarize_v2_spawn_outside_coverage_not_complete():
    """Estimated spawn outside coverage bounds must not claim complete counts."""
    obs_v2 = make_valid_v2_obs(
        seed="909",
        structures={"structure.village": [[100, 100]]},
        anchors=[{
            "mode": "world_spawn_estimated",
            "coordinate": [10000, 10000],  # Well outside FULL_ENVELOPE [-5120..5120]
            "source_id": DUMMY_HASH,
        }],
    )

    layouts = summaries.summarize_v2(obs_v2)
    spawn_layout = next(l for l in layouts if l["anchor"] == [10000, 10000])

    village = spawn_layout["features"]["structure.village"]
    # A distant start is outside this anchor's border; unknown is not a completed zero.
    assert village["counts"][3] == 0
    # But complete MUST BE FALSE because coverage bounds do not contain this box
    assert village["complete"] == [False, False, False, False]


def test_summarize_v2_legacy_field_matches_summarize_at():
    """Verify legacy field matches existing v1 summarize_at projection."""
    obs_v2 = make_valid_v2_obs(
        seed="1111",
        structures={"structure.village": [[50, 50]]},
    )
    legacy_obs = summaries.legacy_observation_v2(obs_v2)
    legacy_at_origin = [row for row in summaries.summarize(legacy_obs) if row["anchor"]==[0,0]]

    layouts = summaries.summarize_v2(obs_v2)
    origin_2048 = next(l for l in layouts if l["anchor"] == [0, 0] and l["border_side"] == 2048)
    expected_legacy = next(l for l in legacy_at_origin if l["border_side"] == 2048)

    assert origin_2048["legacy"] == expected_legacy
