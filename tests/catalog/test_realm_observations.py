"""Unit stub tests for internal Realm observations."""
import copy
import pytest
from seed_search.catalog.realm_observations import (
    extract_realm_inventory,
    validate_realm_inventory,
    INVENTORY_KEYS,
    ENTRY_KEYS,
    STATUSES,
    METHOD_OCEAN_RUIN,
    METHOD_BURIED_TREASURE,
    METHOD_IGLOO_BASEMENT,
    METHOD_BASTION_VARIANT,
)


class StubBackend:
    def __init__(self, *, structures_data=None, igloo_basement_map=None, bastion_variant_map=None,
                 raise_on=None):
        self.structures_data = dict(structures_data or {})
        self.igloo_basement_map = dict(igloo_basement_map or {})
        self.bastion_variant_map = dict(bastion_variant_map or {})
        self.raise_on = set(raise_on or ())
        self.calls = []

    def structures(self, name, inclusive_bounds, viable=True):
        self.calls.append(("structures", name, inclusive_bounds, viable))
        if name in self.raise_on:
            raise RuntimeError(f"Backend structure error for {name}")
        return list(self.structures_data.get(name, []))

    def igloo_basement(self, x, z):
        self.calls.append(("igloo_basement", x, z))
        if (x, z) in self.raise_on or "igloo_basement" in self.raise_on:
            raise RuntimeError(f"Igloo basement query failed for ({x}, {z})")
        return bool(self.igloo_basement_map.get((x, z), False))

    def bastion_variant(self, x, z):
        self.calls.append(("bastion_variant", x, z))
        if (x, z) in self.raise_on or "bastion_variant" in self.raise_on:
            raise RuntimeError(f"Bastion variant query failed for ({x}, {z})")
        return int(self.bastion_variant_map.get((x, z), 0))


def make_test_obs(*, ow_bounds=(-5120, -5120, 5120, 5120), nether_bounds=(-640, -640, 640, 640),
                  igloos=None, bastions=None, igloo_status="complete", bastion_status="complete",
                  realm=None):
    return {
        "revision": "catalog-observation-v2",
        "registry_revision": "test",
        "identity": {"seed": "12345"},
        "bounds": {
            "overworld": list(ow_bounds),
            "nether": list(nether_bounds),
        },
        "structures": {
            "structure.igloo": list(igloos) if igloos is not None else [],
            "structure.bastion": list(bastions) if bastions is not None else [],
        },
        "coverage": {
            "structure.igloo": {"status": igloo_status, "bounds": list(ow_bounds), "method_id": "test"},
            "structure.bastion": {"status": bastion_status, "bounds": list(nether_bounds), "method_id": "test"},
        },
        "realm": realm,
    }


def test_queries_and_signatures():
    backend = StubBackend(
        structures_data={
            "ocean_ruin": [[100, 200], [-500, -300]],
            "buried_treasure": [[50, -50]],
        },
        igloo_basement_map={(100, 100): True, (200, 200): False},
        bastion_variant_map={(-100, -100): 2},
    )
    obs = make_test_obs(
        igloos=[[100, 100], [200, 200]],
        bastions=[[-100, -100]],
    )

    returned_obs = extract_realm_inventory(obs, backend)
    assert returned_obs is obs
    assert "realm" in obs and isinstance(obs["realm"], dict)
    assert "inventory" in obs["realm"]

    inv = obs["realm"]["inventory"]
    assert set(inv.keys()) == set(INVENTORY_KEYS)

    for k in INVENTORY_KEYS:
        entry = inv[k]
        assert set(entry.keys()) == ENTRY_KEYS
        assert entry["status"] == "complete"
        assert entry["errors"] == []

    assert inv["ocean_ruin"]["method_id"] == METHOD_OCEAN_RUIN
    assert inv["ocean_ruin"]["points"] == [[-500, -300], [100, 200]]

    assert inv["buried_treasure"]["method_id"] == METHOD_BURIED_TREASURE
    assert inv["buried_treasure"]["points"] == [[50, -50]]

    assert inv["igloo_basement"]["method_id"] == METHOD_IGLOO_BASEMENT
    assert inv["igloo_basement"]["points"] == [[100, 100]]

    assert inv["bastion_variant"]["method_id"] == METHOD_BASTION_VARIANT
    assert inv["bastion_variant"]["points"] == [[-100, -100, 2]]

    # Check backend calls made
    calls = backend.calls
    assert ("structures", "ocean_ruin", (-5120, -5120, 5119, 5119), True) in calls
    assert ("structures", "buried_treasure", (-5120, -5120, 5119, 5119), True) in calls
    assert ("igloo_basement", 100, 100) in calls
    assert ("igloo_basement", 200, 200) in calls
    assert ("bastion_variant", -100, -100) in calls

    # Standalone validation without backend calls
    backend_calls_before = len(backend.calls)
    validated = validate_realm_inventory(obs)
    assert validated == inv
    assert len(backend.calls) == backend_calls_before


def test_bounds_validation_and_dimensions():
    backend = StubBackend()
    obs = make_test_obs()
    extract_realm_inventory(obs, backend)
    inv = obs["realm"]["inventory"]

    # Overworld features use OW bounds; Nether uses Nether bounds
    assert inv["ocean_ruin"]["bounds"] == [-5120, -5120, 5120, 5120]
    assert inv["buried_treasure"]["bounds"] == [-5120, -5120, 5120, 5120]
    assert inv["igloo_basement"]["bounds"] == [-5120, -5120, 5120, 5120]
    assert inv["bastion_variant"]["bounds"] == [-640, -640, 640, 640]

    # Out of bounds point in inventory raises ValueError
    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["ocean_ruin"]["points"] = [[5120, 0]]  # 5120 is >= hiX
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)

    # Nether point outside Nether bounds raises ValueError
    bad_obs2 = copy.deepcopy(obs)
    bad_obs2["structures"]["structure.bastion"] = [[1000, 0]]
    bad_obs2["realm"]["inventory"]["bastion_variant"]["points"] = [[1000, 0, 1]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs2)

    # Incompatible bounds list
    bad_obs3 = copy.deepcopy(obs)
    bad_obs3["bounds"]["overworld"] = [100, 100, 50, 50]  # inverted
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs3)


def test_deduplication_and_sorting():
    # Backend returns out-of-order and duplicate points
    backend = StubBackend(
        structures_data={
            "ocean_ruin": [[300, 400], [100, 200], [300, 400], [-50, -50], [100, 200]],
            "buried_treasure": [],
        }
    )
    obs = make_test_obs()
    extract_realm_inventory(obs, backend)

    pts = obs["realm"]["inventory"]["ocean_ruin"]["points"]
    assert pts == [[-50, -50], [100, 200], [300, 400]]

    # Unsorted points in inventory are rejected by validate_realm_inventory
    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["ocean_ruin"]["points"] = [[100, 200], [-50, -50]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)

    # Duplicate points in inventory are rejected by validate_realm_inventory
    bad_obs2 = copy.deepcopy(obs)
    bad_obs2["realm"]["inventory"]["ocean_ruin"]["points"] = [[100, 200], [100, 200]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs2)


def test_resume_skip_and_incompatible_resurvey():
    backend1 = StubBackend(
        structures_data={"ocean_ruin": [[10, 20]], "buried_treasure": [[30, 40]]},
        igloo_basement_map={(100, 100): True},
        bastion_variant_map={(-50, -50): 1},
    )
    obs = make_test_obs(igloos=[[100, 100]], bastions=[[-50, -50]])
    extract_realm_inventory(obs, backend1)

    # Resume with a second backend that has raise_on for everything
    backend2 = StubBackend(
        raise_on={"ocean_ruin", "buried_treasure", "igloo_basement", "bastion_variant"}
    )
    # Re-running on unchanged complete obs should skip backend entirely
    resumed_obs = extract_realm_inventory(obs, backend2)
    assert len(backend2.calls) == 0
    assert resumed_obs["realm"]["inventory"]["ocean_ruin"]["points"] == [[10, 20]]

    # If bounds change, it resurveys (triggering backend and thus exception/failure)
    changed_bounds_obs = copy.deepcopy(obs)
    changed_bounds_obs["bounds"]["overworld"] = [-2048, -2048, 2048, 2048]
    # Keep igloo inside new bounds
    extract_realm_inventory(changed_bounds_obs, backend2)
    assert changed_bounds_obs["realm"]["inventory"]["ocean_ruin"]["status"] == "failed"

    # If an existing completed record has invalid corrupted data, it must not be trusted
    corrupted_obs = copy.deepcopy(obs)
    corrupted_obs["realm"]["inventory"]["ocean_ruin"]["points"] = [[99999999, 99999999]]  # out of bounds
    backend3 = StubBackend(structures_data={"ocean_ruin": [[10, 20]], "buried_treasure": [[30, 40]]})
    extract_realm_inventory(corrupted_obs, backend3)
    # Backend was called to resurvey rather than blindly trusting the invalid record
    assert ("structures", "ocean_ruin", (-5120, -5120, 5119, 5119), True) in backend3.calls


def test_errorstatus_and_independent_features():
    backend = StubBackend(
        structures_data={"buried_treasure": [[30, 40]]},
        raise_on={"ocean_ruin"},  # only ocean_ruin fails
        igloo_basement_map={(100, 100): True},
        bastion_variant_map={(-50, -50): 3},
    )
    obs = make_test_obs(igloos=[[100, 100]], bastions=[[-50, -50]])
    extract_realm_inventory(obs, backend)

    inv = obs["realm"]["inventory"]
    # ocean_ruin failed
    assert inv["ocean_ruin"]["status"] == "failed"
    assert inv["ocean_ruin"]["points"] == []
    assert len(inv["ocean_ruin"]["errors"]) == 1
    assert inv["ocean_ruin"]["errors"] == ["RuntimeError"]  # bounded category, no arbitrary provider text

    # independent features succeeded
    assert inv["buried_treasure"]["status"] == "complete"
    assert inv["buried_treasure"]["points"] == [[30, 40]]
    assert inv["igloo_basement"]["status"] == "complete"
    assert inv["bastion_variant"]["status"] == "complete"

    # Inventory with failed feature still passes validation
    validate_realm_inventory(obs)


def test_unknown_and_partial_source_coverage():
    backend = StubBackend(
        igloo_basement_map={(100, 100): True},
        bastion_variant_map={(-50, -50): 1},
    )
    # Source coverage is 'partial' for igloo, 'unknown' for bastion
    obs = make_test_obs(
        igloos=[[100, 100]],
        bastions=[[-50, -50]],
        igloo_status="partial",
        bastion_status="unknown",
    )
    extract_realm_inventory(obs, backend)

    inv = obs["realm"]["inventory"]
    # Must be 'partial', never 'complete'
    assert inv["igloo_basement"]["status"] == "partial"
    assert inv["igloo_basement"]["points"] == [[100, 100]]

    assert inv["bastion_variant"]["status"] == "partial"
    assert inv["bastion_variant"]["points"] == [[-50, -50, 1]]

    # validate_realm_inventory accepts this partial inventory
    validate_realm_inventory(obs)

    # But if someone manually sets status to 'complete' while source coverage is partial, validation fails
    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["igloo_basement"]["status"] = "complete"
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)


def test_subset_validation_rejects_foreign_coordinates():
    backend = StubBackend(
        igloo_basement_map={(100, 100): True},
        bastion_variant_map={(-50, -50): 0},
    )
    obs = make_test_obs(igloos=[[100, 100]], bastions=[[-50, -50]])
    extract_realm_inventory(obs, backend)

    # Add a foreign point to igloo_basement not in public igloos
    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["igloo_basement"]["points"].append([999, 999])
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)

    # Add a foreign point to bastion_variant not in public bastions
    bad_obs2 = copy.deepcopy(obs)
    bad_obs2["realm"]["inventory"]["bastion_variant"]["points"].append([999, 999, 0])
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs2)


def test_bastion_variants_and_no_invented_zero():
    # Bastion 1 succeeds (variant 3), Bastion 2 fails
    backend = StubBackend(
        bastion_variant_map={(-100, -100): 3},
        raise_on={(-200, -200)},
    )
    obs = make_test_obs(bastions=[[-200, -200], [-100, -100]])
    extract_realm_inventory(obs, backend)

    inv = obs["realm"]["inventory"]
    assert inv["bastion_variant"]["status"] == "partial"
    # Bastion 2 was NOT invented as 0; only Bastion 1 is in points!
    assert inv["bastion_variant"]["points"] == [[-100, -100, 3]]
    assert len(inv["bastion_variant"]["errors"]) == 1

    # Validate partial inventory succeeds
    validate_realm_inventory(obs)

    # If marked complete with missing bastion variant, validate_realm_inventory raises ValueError
    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["bastion_variant"]["status"] = "complete"
    bad_obs["realm"]["inventory"]["bastion_variant"]["errors"] = []
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)


def test_strict_invalid_coordinate_types():
    backend = StubBackend()
    obs = make_test_obs()
    extract_realm_inventory(obs, backend)

    # Boolean coordinate
    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["ocean_ruin"]["points"] = [[True, 100]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)

    # Float coordinate
    bad_obs2 = copy.deepcopy(obs)
    bad_obs2["realm"]["inventory"]["ocean_ruin"]["points"] = [[10.5, 100]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs2)

    # String coordinate
    bad_obs3 = copy.deepcopy(obs)
    bad_obs3["realm"]["inventory"]["ocean_ruin"]["points"] = [["10", 100]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs3)

    # Boolean variant
    bad_obs4 = copy.deepcopy(obs)
    bad_obs4["structures"]["structure.bastion"] = [[-100, -100]]
    bad_obs4["realm"]["inventory"]["bastion_variant"]["points"] = [[-100, -100, True]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs4)

    # Variant out of range (4)
    bad_obs5 = copy.deepcopy(obs)
    bad_obs5["structures"]["structure.bastion"] = [[-100, -100]]
    bad_obs5["realm"]["inventory"]["bastion_variant"]["points"] = [[-100, -100, 4]]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs5)


def test_fresh_realm_none_and_other_keys_preserved():
    backend = StubBackend()
    # obs with realm = None
    obs1 = make_test_obs(realm=None)
    extract_realm_inventory(obs1, backend)
    assert isinstance(obs1["realm"], dict)
    assert "inventory" in obs1["realm"]

    # obs with existing custom realm keys
    obs2 = make_test_obs(realm={"custom_score": 1234, "notes": "persisted"})
    extract_realm_inventory(obs2, backend)
    assert obs2["realm"]["custom_score"] == 1234
    assert obs2["realm"]["notes"] == "persisted"
    assert "inventory" in obs2["realm"]


def test_credential_strings_rejected():
    backend = StubBackend()
    obs = make_test_obs()
    extract_realm_inventory(obs, backend)

    bad_obs = copy.deepcopy(obs)
    bad_obs["realm"]["inventory"]["ocean_ruin"]["status"] = "failed"
    bad_obs["realm"]["inventory"]["ocean_ruin"]["errors"] = ["Bearer eyJhbGciOi..."]
    with pytest.raises(ValueError):
        validate_realm_inventory(bad_obs)


def test_known_positive_witnesses_retained_on_partial():
    # Run 1: Igloo 1 succeeds with basement, Igloo 2 has no basement
    backend1 = StubBackend(
        igloo_basement_map={(100, 100): True, (200, 200): False},
    )
    obs = make_test_obs(igloos=[[100, 100], [200, 200]], igloo_status="partial")
    extract_realm_inventory(obs, backend1)
    assert obs["realm"]["inventory"]["igloo_basement"]["points"] == [[100, 100]]

    # Run 2: Igloo 1 backend query fails, but Igloo 1 was already known positive witness
    backend2 = StubBackend(
        raise_on={(100, 100)},
        igloo_basement_map={(200, 200): False},
    )
    extract_realm_inventory(obs, backend2)
    # Positive witness for Igloo 1 was retained!
    assert obs["realm"]["inventory"]["igloo_basement"]["points"] == [[100, 100]]
    assert obs["realm"]["inventory"]["igloo_basement"]["status"] == "partial"
    assert len(obs["realm"]["inventory"]["igloo_basement"]["errors"]) == 1
