"""Unit tests for generalization biome audit probe helper.

Covers exact INTERFACES.md requirements:
- Malformed inputs and schema validation
- Missing and error rows
- Duplicate coordinates and orphan observations
- Explicit aliases and cycle/ambiguity detection
- Minecraft namespace stripping
- Non-comparable End classes
- Negative coordinates and coordinate boundary limits
- Cave biomes and absence of cave masking
- Lack of cross-height matching
- Unknown_* labels yielding unknown
- Input immutability and source order preservation
- summarize_biomes aggregation without accuracy percentages
"""

import copy
import pytest

from scripts.generalization_biome_probe import (
    INT32_MAX,
    INT32_MIN,
    Y_MAX,
    Y_MIN,
    compare_biomes,
    summarize_biomes,
)


class TestSchemaValidation:
    """Tests for malformed inputs and schema strictness."""

    def test_predictions_must_be_list(self):
        with pytest.raises(ValueError, match="predictions must be a list"):
            compare_biomes({"position": [0, 64, 0]}, [])

    def test_observations_must_be_list(self):
        with pytest.raises(ValueError, match="observations must be a list"):
            compare_biomes([], {"x": 0, "y": 64, "z": 0})

    def test_prediction_must_be_dict(self):
        with pytest.raises(ValueError, match="must be a dict"):
            compare_biomes(["not_a_dict"], [])

    def test_prediction_exact_fields_required(self):
        # Missing sample_group
        with pytest.raises(ValueError, match="exact fields"):
            compare_biomes([{"position": [0, 64, 0], "biome_name": "plains"}], [])

        # Extra field
        with pytest.raises(ValueError, match="exact fields"):
            compare_biomes(
                [{
                    "position": [0, 64, 0],
                    "biome_name": "plains",
                    "sample_group": "group_a",
                    "extra_field": 123,
                }],
                [],
            )

    def test_prediction_coordinate_types(self):
        # Boolean is rejected (strict int)
        with pytest.raises(ValueError, match="strict integer"):
            compare_biomes(
                [{"position": [True, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        with pytest.raises(ValueError, match="strict integer"):
            compare_biomes(
                [{"position": [0, False, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        # Float is rejected
        with pytest.raises(ValueError, match="strict integer"):
            compare_biomes(
                [{"position": [0, 64.5, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        # String is rejected
        with pytest.raises(ValueError, match="strict integer"):
            compare_biomes(
                [{"position": ["0", 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )

    def test_prediction_coordinate_bounds(self):
        # Y out of bounds (< -64 or > 319)
        with pytest.raises(ValueError, match="outside allowed range"):
            compare_biomes(
                [{"position": [0, -65, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        with pytest.raises(ValueError, match="outside allowed range"):
            compare_biomes(
                [{"position": [0, 320, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        # X and Z signed 32-bit bounds
        with pytest.raises(ValueError, match="outside allowed range"):
            compare_biomes(
                [{"position": [INT32_MIN - 1, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        with pytest.raises(ValueError, match="outside allowed range"):
            compare_biomes(
                [{"position": [INT32_MAX + 1, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        with pytest.raises(ValueError, match="outside allowed range"):
            compare_biomes(
                [{"position": [0, 64, INT32_MIN - 1], "biome_name": "plains", "sample_group": "g"}],
                [],
            )
        with pytest.raises(ValueError, match="outside allowed range"):
            compare_biomes(
                [{"position": [0, 64, INT32_MAX + 1], "biome_name": "plains", "sample_group": "g"}],
                [],
            )

    def test_observation_must_have_either_id_or_error(self):
        # Neither id nor error
        with pytest.raises(ValueError, match="either non-null 'id' or 'error'"):
            compare_biomes(
                [{"position": [0, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [{"x": 0, "y": 64, "z": 0}],
            )
        # Both id and error
        with pytest.raises(ValueError, match="cannot have both"):
            compare_biomes(
                [{"position": [0, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [{"x": 0, "y": 64, "z": 0, "id": "plains", "error": "timeout"}],
            )

    def test_observation_numeric_id_rejected(self):
        # Numeric ID conversion is explicitly prohibited; id must be str
        with pytest.raises(ValueError, match="must be a non-empty str"):
            compare_biomes(
                [{"position": [0, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [{"x": 0, "y": 64, "z": 0, "id": 1}],
            )

    def test_observation_coordinate_strictness(self):
        # Bool coordinate in observation rejected
        with pytest.raises(ValueError, match="strict integer"):
            compare_biomes(
                [{"position": [0, 64, 0], "biome_name": "plains", "sample_group": "g"}],
                [{"x": 0, "y": True, "z": 0, "id": "plains"}],
            )


class TestDuplicatesAndOrphans:
    """Tests for duplicate coordinates and orphan observation detection."""

    def test_duplicate_xyz_in_predictions(self):
        preds = [
            {"position": [10, 64, 20], "biome_name": "plains", "sample_group": "g1"},
            {"position": [10, 64, 20], "biome_name": "forest", "sample_group": "g2"},
        ]
        with pytest.raises(ValueError, match="Duplicate XYZ in predictions"):
            compare_biomes(preds, [])

    def test_duplicate_xyz_in_observations(self):
        preds = [
            {"position": [10, 64, 20], "biome_name": "plains", "sample_group": "g1"},
        ]
        obs = [
            {"x": 10, "y": 64, "z": 20, "id": "plains"},
            {"x": 10, "y": 64, "z": 20, "id": "plains"},
        ]
        with pytest.raises(ValueError, match="Duplicate XYZ in observations"):
            compare_biomes(preds, obs)

    def test_orphan_observed_xyz_raises(self):
        preds = [
            {"position": [0, 64, 0], "biome_name": "plains", "sample_group": "g1"},
        ]
        obs = [
            {"x": 0, "y": 64, "z": 0, "id": "plains"},
            {"x": 100, "y": 64, "z": 100, "id": "desert"},  # No corresponding prediction
        ]
        with pytest.raises(ValueError, match="Orphan observed XYZ"):
            compare_biomes(preds, obs)


class TestMissingAndErrorRows:
    """Tests for missing observations and explicit observation errors."""

    def test_missing_observation_yields_unknown(self):
        preds = [
            {"position": [100, 64, 200], "biome_name": "plains", "sample_group": "holdout"},
        ]
        rows = compare_biomes(preds, [])
        assert len(rows) == 1
        r = rows[0]
        assert r["position"] == [100, 64, 200]
        assert r["sample_group"] == "holdout"
        assert r["predicted_name"] == "plains"
        assert r["observed_name"] is None
        assert r["canonical_predicted"] == "plains"
        assert r["canonical_observed"] is None
        assert r["outcome"] == "unknown"
        assert "missing observation" in r["reason"]

    def test_explicit_observation_error_yields_error(self):
        preds = [
            {"position": [100, 64, 200], "biome_name": "plains", "sample_group": "holdout"},
        ]
        obs = [
            {"x": 100, "y": 64, "z": 200, "error": "BDS ScriptAPI timeout"},
        ]
        rows = compare_biomes(preds, obs)
        assert len(rows) == 1
        r = rows[0]
        assert r["position"] == [100, 64, 200]
        assert r["sample_group"] == "holdout"
        assert r["predicted_name"] == "plains"
        assert r["observed_name"] is None
        assert r["canonical_predicted"] == "plains"
        assert r["canonical_observed"] is None
        assert r["outcome"] == "error"
        assert "BDS ScriptAPI timeout" in r["reason"]


class TestAliasesAndNamespace:
    """Tests for explicit aliases, namespace stripping, cycle detection, and ambiguity."""

    def test_minecraft_namespace_stripping(self):
        preds = [
            {"position": [0, 64, 0], "biome_name": "minecraft:plains", "sample_group": "test"},
            {"position": [1, 64, 1], "biome_name": "forest", "sample_group": "test"},
        ]
        obs = [
            {"x": 0, "y": 64, "z": 0, "id": "plains"},
            {"x": 1, "y": 64, "z": 1, "id": "minecraft:forest"},
        ]
        rows = compare_biomes(preds, obs)
        assert rows[0]["canonical_predicted"] == "plains"
        assert rows[0]["canonical_observed"] == "plains"
        assert rows[0]["outcome"] == "match"

        assert rows[1]["canonical_predicted"] == "forest"
        assert rows[1]["canonical_observed"] == "forest"
        assert rows[1]["outcome"] == "match"

    def test_only_minecraft_namespace_stripped(self):
        preds = [
            {"position": [0, 64, 0], "biome_name": "custom:plains", "sample_group": "test"},
        ]
        obs = [
            {"x": 0, "y": 64, "z": 0, "id": "plains"},
        ]
        rows = compare_biomes(preds, obs)
        assert rows[0]["canonical_predicted"] == "custom:plains"
        assert rows[0]["canonical_observed"] == "plains"
        assert rows[0]["outcome"] == "mismatch"

    def test_explicit_nether_aliases(self):
        aliases = {
            "hell": "nether_wastes",
            "soulsand_valley": "soul_sand_valley",
        }
        preds = [
            {"position": [0, 64, 0], "biome_name": "hell", "sample_group": "nether"},
            {"position": [10, 64, 10], "biome_name": "soul_sand_valley", "sample_group": "nether"},
        ]
        obs = [
            {"x": 0, "y": 64, "z": 0, "id": "minecraft:nether_wastes"},
            {"x": 10, "y": 64, "z": 10, "id": "soulsand_valley"},
        ]
        rows = compare_biomes(preds, obs, aliases=aliases)
        assert rows[0]["canonical_predicted"] == "nether_wastes"
        assert rows[0]["canonical_observed"] == "nether_wastes"
        assert rows[0]["outcome"] == "match"

        assert rows[1]["canonical_predicted"] == "soul_sand_valley"
        assert rows[1]["canonical_observed"] == "soul_sand_valley"
        assert rows[1]["outcome"] == "match"

    def test_transitive_alias_chaining(self):
        aliases = {"old_name": "mid_name", "mid_name": "new_name"}
        preds = [{"position": [0, 64, 0], "biome_name": "old_name", "sample_group": "test"}]
        obs = [{"x": 0, "y": 64, "z": 0, "id": "new_name"}]
        rows = compare_biomes(preds, obs, aliases=aliases)
        assert rows[0]["canonical_predicted"] == "new_name"
        assert rows[0]["canonical_observed"] == "new_name"
        assert rows[0]["outcome"] == "match"

    def test_alias_cycle_rejected(self):
        # Direct self-loop
        with pytest.raises(ValueError, match="Cycle detected in aliases"):
            compare_biomes([], [], aliases={"plains": "plains"})

        # Normalized self-loop
        with pytest.raises(ValueError, match="Cycle detected in aliases"):
            compare_biomes([], [], aliases={"minecraft:plains": "plains"})

        # 2-cycle
        with pytest.raises(ValueError, match="Cycle detected in aliases"):
            compare_biomes([], [], aliases={"a": "b", "b": "a"})

        # 3-cycle
        with pytest.raises(ValueError, match="Cycle detected in aliases"):
            compare_biomes([], [], aliases={"a": "b", "b": "c", "c": "a"})

    def test_ambiguous_normalized_aliases_rejected(self):
        with pytest.raises(ValueError, match="Ambiguous normalized alias"):
            compare_biomes([], [], aliases={"minecraft:plains": "forest", "plains": "desert"})


class TestNonComparableEndClasses:
    """Tests for explicit non-comparable End terrain classes."""

    def test_non_comparable_labels_yield_not_comparable(self):
        non_comp = ("the_end_highlands", "the_end_midlands", "end_barrens", "the_end_island")
        preds = [
            {"position": [1000, 64, 1000], "biome_name": "the_end_highlands", "sample_group": "end"},
            {"position": [2000, 64, 2000], "biome_name": "end_barrens", "sample_group": "end"},
        ]
        obs = [
            {"x": 1000, "y": 64, "z": 1000, "id": "minecraft:the_end"},
            {"x": 2000, "y": 64, "z": 2000, "id": "the_end"},
        ]
        rows = compare_biomes(preds, obs, non_comparable=non_comp)
        assert rows[0]["outcome"] == "not_comparable"
        assert rows[0]["predicted_name"] == "the_end_highlands"
        assert rows[0]["canonical_predicted"] == "the_end_highlands"
        assert rows[0]["observed_name"] == "minecraft:the_end"
        assert rows[0]["canonical_observed"] == "the_end"

        assert rows[1]["outcome"] == "not_comparable"

    def test_non_comparable_on_observed_side(self):
        non_comp = ("custom_unsupported_biome",)
        preds = [{"position": [0, 64, 0], "biome_name": "plains", "sample_group": "test"}]
        obs = [{"x": 0, "y": 64, "z": 0, "id": "custom_unsupported_biome"}]
        rows = compare_biomes(preds, obs, non_comparable=non_comp)
        assert rows[0]["outcome"] == "not_comparable"
        assert "observed" in rows[0]["reason"]


class TestUnknownLabels:
    """Tests for Unknown_* labels yielding unknown outcome."""

    def test_predicted_unknown_yields_unknown(self):
        preds = [{"position": [0, 64, 0], "biome_name": "Unknown_54", "sample_group": "test"}]
        obs = [{"x": 0, "y": 64, "z": 0, "id": "plains"}]
        rows = compare_biomes(preds, obs)
        assert rows[0]["outcome"] == "unknown"
        assert rows[0]["canonical_predicted"] == "Unknown_54"
        assert rows[0]["canonical_observed"] == "plains"

    def test_observed_unknown_yields_unknown(self):
        preds = [{"position": [0, 64, 0], "biome_name": "plains", "sample_group": "test"}]
        obs = [{"x": 0, "y": 64, "z": 0, "id": "minecraft:Unknown_12"}]
        rows = compare_biomes(preds, obs)
        assert rows[0]["outcome"] == "unknown"
        assert rows[0]["canonical_observed"] == "Unknown_12"

    def test_both_unknown_still_unknown(self):
        preds = [{"position": [0, 64, 0], "biome_name": "Unknown_12", "sample_group": "test"}]
        obs = [{"x": 0, "y": 64, "z": 0, "id": "Unknown_12"}]
        rows = compare_biomes(preds, obs)
        assert rows[0]["outcome"] == "unknown"


class TestCoordinatesAndBoundaries:
    """Tests for negative coordinates and coordinate boundary limits."""

    def test_extreme_negative_and_positive_coordinates(self):
        preds = [
            {"position": [INT32_MIN, Y_MIN, INT32_MIN], "biome_name": "plains", "sample_group": "edge"},
            {"position": [INT32_MAX, Y_MAX, INT32_MAX], "biome_name": "ice_spikes", "sample_group": "edge"},
            {"position": [-123456, -64, -654321], "biome_name": "deep_dark", "sample_group": "subsurface"},
        ]
        obs = [
            {"x": INT32_MIN, "y": Y_MIN, "z": INT32_MIN, "id": "plains"},
            {"x": INT32_MAX, "y": Y_MAX, "z": INT32_MAX, "id": "ice_spikes"},
            {"x": -123456, "y": -64, "z": -654321, "id": "deep_dark"},
        ]
        rows = compare_biomes(preds, obs)
        assert len(rows) == 3
        assert all(r["outcome"] == "match" for r in rows)


class TestCavesAndLackOfCrossHeightMatching:
    """Tests for caves, absence of cave masking, and strict lack of cross-height matching."""

    def test_cave_biome_matches_when_identical(self):
        preds = [{"position": [100, -20, 200], "biome_name": "lush_caves", "sample_group": "cave"}]
        obs = [{"x": 100, "y": -20, "z": 200, "id": "lush_caves"}]
        rows = compare_biomes(preds, obs)
        assert rows[0]["outcome"] == "match"

    def test_no_cave_masking_disagreement_is_mismatch(self):
        # Cave disagreement must NOT be masked as match
        preds = [{"position": [100, -20, 200], "biome_name": "plains", "sample_group": "surface_pred"}]
        obs = [{"x": 100, "y": -20, "z": 200, "id": "dripstone_caves"}]
        rows = compare_biomes(preds, obs)
        assert rows[0]["outcome"] == "mismatch"
        assert "predicted 'plains' != observed 'dripstone_caves'" in rows[0]["reason"]

    def test_lack_of_cross_height_matching_orphan_raises(self):
        # Observation at different height with no prediction at that height is an orphan
        preds = [{"position": [50, 64, 50], "biome_name": "plains", "sample_group": "surface"}]
        obs = [{"x": 50, "y": 10, "z": 50, "id": "dripstone_caves"}]
        with pytest.raises(ValueError, match="Orphan observed XYZ"):
            compare_biomes(preds, obs)

    def test_distinct_heights_evaluated_independently(self):
        # When two distinct heights are predicted at same X, Z:
        preds = [
            {"position": [50, 64, 50], "biome_name": "plains", "sample_group": "surface"},
            {"position": [50, 10, 50], "biome_name": "dripstone_caves", "sample_group": "cave"},
        ]
        # Only cave observation provided
        obs = [{"x": 50, "y": 10, "z": 50, "id": "dripstone_caves"}]
        rows = compare_biomes(preds, obs)

        # Row 0 (Y=64) has missing observation -> unknown (does NOT borrow Y=10)
        assert rows[0]["position"] == [50, 64, 50]
        assert rows[0]["outcome"] == "unknown"
        assert rows[0]["observed_name"] is None

        # Row 1 (Y=10) matches exact observation
        assert rows[1]["position"] == [50, 10, 50]
        assert rows[1]["outcome"] == "match"


class TestImmutabilityAndOrder:
    """Tests that inputs are never mutated and source order is strictly preserved."""

    def test_never_mutate_inputs_and_preserve_order(self):
        preds = [
            {"position": [2, 64, 2], "biome_name": "taiga", "sample_group": "g2"},
            {"position": [0, 64, 0], "biome_name": "plains", "sample_group": "g1"},
            {"position": [1, 64, 1], "biome_name": "desert", "sample_group": "g1"},
        ]
        obs = [
            {"x": 1, "y": 64, "z": 1, "id": "desert", "block": "sand", "dimension": "overworld"},
            {"x": 0, "y": 64, "z": 0, "id": "plains", "block": "grass_block"},
            {"x": 2, "y": 64, "z": 2, "id": "taiga"},
        ]
        preds_clone = copy.deepcopy(preds)
        obs_clone = copy.deepcopy(obs)

        rows = compare_biomes(preds, obs)

        # Check immutability
        assert preds == preds_clone
        assert obs == obs_clone

        # Check source order preserved from predictions
        assert rows[0]["position"] == [2, 64, 2]
        assert rows[1]["position"] == [0, 64, 0]
        assert rows[2]["position"] == [1, 64, 1]


class TestSummarizeBiomes:
    """Tests for summarize_biomes aggregation and strict absence of population claims."""

    def test_summarize_counts(self):
        rows = [
            {
                "position": [0, 64, 0],
                "sample_group": "surface",
                "predicted_name": "plains",
                "observed_name": "plains",
                "canonical_predicted": "plains",
                "canonical_observed": "plains",
                "outcome": "match",
                "reason": "canonical names match",
            },
            {
                "position": [1, 64, 1],
                "sample_group": "surface",
                "predicted_name": "plains",
                "observed_name": "forest",
                "canonical_predicted": "plains",
                "canonical_observed": "forest",
                "outcome": "mismatch",
                "reason": "mismatch",
            },
            {
                "position": [2, 64, 2],
                "sample_group": "cave",
                "predicted_name": "deep_dark",
                "observed_name": None,
                "canonical_predicted": "deep_dark",
                "canonical_observed": None,
                "outcome": "unknown",
                "reason": "missing observation",
            },
            {
                "position": [3, 64, 3],
                "sample_group": "end",
                "predicted_name": "the_end_highlands",
                "observed_name": "the_end",
                "canonical_predicted": "the_end_highlands",
                "canonical_observed": "the_end",
                "outcome": "not_comparable",
                "reason": "non-comparable",
            },
        ]
        summary = summarize_biomes(rows)

        assert summary["total"] == 4

        # by_group
        assert summary["by_group"]["surface"]["match"] == 1
        assert summary["by_group"]["surface"]["mismatch"] == 1
        assert summary["by_group"]["cave"]["unknown"] == 1
        assert summary["by_group"]["end"]["not_comparable"] == 1

        # by_name
        assert summary["by_name"]["plains"]["match"] == 1
        assert summary["by_name"]["plains"]["mismatch"] == 1
        assert summary["by_name"]["deep_dark"]["unknown"] == 1
        assert summary["by_name"]["the_end_highlands"]["not_comparable"] == 1

        # Strict rejection of accuracy/population percentage fields
        assert "accuracy" not in summary
        assert "population_conclusion" not in summary
        assert "percentage" not in summary

    def test_summarize_empty_rows(self):
        summary = summarize_biomes([])
        assert summary == {"total": 0, "by_group": {}, "by_name": {}}

    def test_summarize_invalid_input(self):
        with pytest.raises(ValueError, match="rows must be a list"):
            summarize_biomes("not_a_list")
        with pytest.raises(ValueError, match="must be a dict"):
            summarize_biomes(["not_a_dict"])
        with pytest.raises(ValueError, match="missing required key"):
            summarize_biomes([{"sample_group": "g"}])
