import hashlib
import json
from pathlib import Path

import pytest
import yaml

from seed_search.config import load_config
from seed_search.preflight import benchmark, compare_observations, points_grid


def test_benchmark_rejects_unbounded_seed_count_before_sampling(tmp_path):
    cfg, hash_ = load_config("runs/sweep-readiness/config/sweep.yaml")
    with pytest.raises(ValueError, match="limited"):
        benchmark(cfg, hash_, tmp_path, count=11)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("change", ["large_search", "negative_weight"])
def test_config_rejects_invalid_search_settings(tmp_path, change):
    cfg, _ = load_config("runs/sweep-readiness/config/sweep.yaml")
    if change == "large_search":
        cfg["search"]["large_search_enabled"] = True
    else:
        keys = list(cfg["score_weights"])
        cfg["score_weights"][keys[0]] = -1
        cfg["score_weights"][keys[1]] += 16
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):
        load_config(path)


def test_border_samples_include_both_edges():
    points = points_grid(-1504, -1504, 3008, 16)
    assert len(points) == 189**2
    assert points.min(axis=0).tolist() == [-1504, -1504]
    assert points.max(axis=0).tolist() == [1504, 1504]


def test_empty_observation_packet_does_not_certify_model(tmp_path):
    path = tmp_path / "observations.json"
    path.write_text(json.dumps({"game_version": "26.52", "seed": "12345",
                               "observation_source": "phone_actual_game",
                               "points": [{"x": 0, "z": 0}]}))
    result = compare_observations(path, tmp_path / "comparison.json")
    assert result["observed_points"] == 0
    assert result["points"][0]["height_error"] is None
    assert result["compatibility"] == "pending_full_fixture_review"
    assert result["large_search_enabled"] is False


def test_other_game_version_not_accepted_as_target_evidence(tmp_path):
    path = tmp_path / "observations.json"
    path.write_text(json.dumps({"game_version": "26.50", "seed": "12345",
                               "observation_source": "phone_actual_game"}))
    with pytest.raises(ValueError, match="target-version"):
        compare_observations(path, tmp_path / "comparison.json")


def test_pinned_backend_files_match_recorded_hashes():
    manifest = json.loads(Path("vendor/backend.json").read_text())
    root = Path("vendor/cubiomes-bedrock")
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
