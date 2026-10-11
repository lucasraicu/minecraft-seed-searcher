import math

import pytest

from seed_search.config import load_config
from seed_search.observations import compare_structures, inside_border, landscape_observations
from seed_search.preflight import compare_observations


class DiagnosticBackend:
    def __init__(self):
        self.calls = []

    def structures(self, name, bounds, viable=True):
        self.calls.append((name, bounds, viable))
        return [(100, 200)] if viable else [(100, 200), (116, 207)]


def test_locate_offsets_and_visit_evidence_stay_separate():
    cfg, _ = load_config("runs/sweep-readiness/config/sweep.yaml")
    backend = DiagnosticBackend()
    data = {"border_center": [0, 0], "structures": [
        {"type": "trial_chamber", "actual_x": 116, "actual_z": 207,
         "actual_generated": False, "notes": "Inspected prediction was absent."}]}
    row = compare_structures(backend, data, cfg)[0]
    assert row["nearest_viable_prediction"]["delta_xz"] == [-16, -7]
    assert row["nearest_viable_prediction"]["horizontal_offset_blocks"] == math.hypot(16, 7)
    assert row["nearest_placement_attempt"]["horizontal_offset_blocks"] == 0
    assert row["actual_generated"] is False
    assert row["manual_review_required"] is True
    assert row["prediction_window_bounds"] == [-140, -49, 372, 463]
    assert {call[2] for call in backend.calls} == {True, False}


def test_unvisited_structure_never_triggers_a_prediction_scan():
    cfg, _ = load_config("runs/sweep-readiness/config/sweep.yaml")
    backend = DiagnosticBackend()
    row = compare_structures(backend, {"structures": [{"type": "fortress"}]}, cfg)[0]
    assert row["status"] == "unvisited"
    assert row["actual_generated"] is None
    assert row["nearest_viable_prediction"] is None
    assert row["actual_reported_position_inside_border"] is None
    assert backend.calls == []


@pytest.mark.parametrize("row", [
    {"type": "fortress", "dimension": "overworld"},
    {"type": "bastion", "actual_x": 8},
    {"type": "bastion", "actual_generated": True},
    {"type": "village", "actual_x": True, "actual_z": 0},
    {"type": "mineshaft", "actual_x": 0, "actual_z": 0, "actual_generated": "yes"},
])
def test_invalid_structure_observations_rejected(row):
    cfg, _ = load_config("runs/sweep-readiness/config/sweep.yaml")
    with pytest.raises(ValueError):
        compare_structures(DiagnosticBackend(), {"structures": [row]}, cfg)


def test_nether_square_corner_and_center_conversion():
    cfg, _ = load_config("runs/sweep-readiness/config/sweep.yaml")
    center = (80, -160)
    corner = (506, 476)  # Nether center (10, -20) plus 496 on both axes.
    assert inside_border(corner, "fortress", center, cfg) is True
    assert math.hypot(corner[0] - 10, corner[1] + 20) > 500
    assert inside_border((507, 476), "bastion", center, cfg) is False
    assert inside_border((1584, 1344), "trial_chamber", center, cfg) is True
    assert inside_border((1585, 1344), "trial_chamber", center, cfg) is False


def test_bridge_observation_requires_a_location_and_preserves_connection():
    bridge = {"x": -100, "z": 100, "actual_connection_present": True, "notes": "Visited natural land bridge."}
    assert landscape_observations({"landscape": {"known_bridge_example": bridge}})["known_bridge_example"] == bridge
    with pytest.raises(ValueError, match="known_bridge_example"):
        landscape_observations({"landscape": {"known_bridge_example": True}})


def test_corrected_user_fixture_uses_the_observed_coordinate_and_stays_pending(tmp_path):
    result = compare_observations("fixtures/bedrock-26.52/seed-12345.user-observations.json", tmp_path / "comparison.json")
    observed = {(p["x"], p["z"]): p for p in result["points"]}
    assert observed[(0, 0)]["surface_kind_matches"] is True
    assert observed[(256, -256)]["actual_ground_y"] == 147
    assert observed[(256, -256)]["predicted_ground_y"] == 146
    assert observed[(256, -256)]["actual_tree_description"] == "wooded spruce area"
    assert observed[(256, 256)]["actual_ground_y"] == 91
    assert observed[(256, 256)]["predicted_ground_y"] == 90
    assert observed[(256, 256)]["actual_tree_top_y"] == 101
    assert observed[(-256, -256)]["actual_ground_y"] is None
    assert result["observed_points"] == 3
    assert result["observed_structure_positions"] == 6
    assert result["visited_structure_positions"] == 1
    structures={r["type"]:r for r in result["structures"] if r["actual_generated"] is None}
    expected={"trial_chamber":([-3689,3513],[-3672,3512],True),
              "stronghold":([-5134,5522],[-5132,5524],False),
              "mineshaft":([-3680,3312],[-3672,3320],True),
              "fortress":([64,816],[72,824],False),
              "bastion":([-680,-168],[-680,-168],False)}
    for name,(actual,predicted,in_border) in expected.items():
        row=structures[name]
        assert row["actual_position_xz"]==actual
        assert row["nearest_viable_prediction"]["position"]==predicted
        assert row["actual_reported_position_inside_border"] is in_border
        assert row["predicted_start_inside_border"] is in_border
        assert row["actual_y"] is None
        assert row["actual_generated"] is None
        assert row["manual_review_required"] is True
    absent=next(r for r in result["structures"] if r["actual_position_xz"] == [-152,120])
    assert absent["actual_generated"] is False
    assert absent["nearest_viable_prediction"] is None
    assert absent["nearest_placement_attempt"] is None
    assert absent["manual_review_required"] is True
    assert result["large_search_enabled"] is False
    assert result["compatibility"] == "pending_full_fixture_review"
