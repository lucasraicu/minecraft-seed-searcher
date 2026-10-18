"""Small architecture probes; does not load the native backend or run BDS."""
import ast
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify():
    script = ROOT / "scripts/bds_verify_finalist.py"
    tree = ast.parse(script.read_text())
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_finalist"
    )

    class StubBackend:
        def __init__(self, seed):
            self.seed = seed

        def structures(self, name, bounds):
            return [(0, 0)]

    namespace = {
        "Backend": StubBackend,
        "evaluate_finalist_accuracy": lambda *args: {"certified": True},
        "is_docker_available": lambda: False,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(script), "exec"), namespace)
    verdict = namespace["verify_finalist"](123, 0, 0, skip_docker=True)
    assert verdict["tier_b_bds_ground_truth"]["status"] == "SKIPPED"
    assert verdict["final_verdict"] == "CERTIFIED"

    near, far = [128, 200, 300], [128, 900, 950]
    assert min(near) == min(far) and len(near) == len(far)
    assert sum(d <= 512 for d in near) == 3
    assert sum(d <= 512 for d in far) == 1

    axes = [-976, -768, -512, -256, 0, 256, 512, 768, 976]
    incomplete = [(x, z) for x in axes for z in axes if x + 1024 >= 2000 or z + 1024 >= 2000]
    assert len(incomplete) == 17
    size = struct.calcsize("<QhhHBBQI18B18B")
    assert size == 64

    config = ast.parse((ROOT / "src/seed_search/realm/config.py").read_text())
    v3 = next(node for node in config.body if isinstance(node, ast.FunctionDef) and node.name == "dynamic_v3_blueprint_config")
    floors = next(
        ast.literal_eval(node.value) for node in v3.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
        and any(isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                and target.slice.value == "hard_floors" for target in node.targets)
    )
    assert len(floors) == 13

    anchor_facts = [(True, False), (False, True)]
    assert any(v for v, b in anchor_facts) and any(b for v, b in anchor_facts)
    assert not any(v and b for v, b in anchor_facts)

    sources = [
        "PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md", "DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md",
        "IMPLEMENTATION_PLAN.md", "MASTER_SEED_BLUEPRINT.md", "native/blueprint_dynamic.inc",
        "native/blueprint_batch.h", "native/filters.inc", "src/seed_search/realm/config.py",
        "scripts/bds_verify_finalist.py", "scripts/calibrate_player_weights.py",
    ]
    return {
        "scope": "Arithmetic and isolated source control flow; no actual-world or performance validation",
        "certification_with_stubbed_passing_heuristic_and_skipped_docker": verdict,
        "lossy_distance_summary_counterexample": {"near": near, "far": far, "query": "at least 3 within 512"},
        "cross_anchor_conjunction_counterexample": {"anchor_facts_village_cherry": anchor_facts, "matching_anchor": False},
        "catalog_record_bytes": size,
        "pilot_anchor_count": 70384 * 81,
        "production_anchor_count": 36000000 * 81,
        "anchors_incomplete_at_positive_closed_circle_boundary": len(incomplete),
        "raw_36m_worlds_64_bytes_GB": 36000000 * 64 / 1e9,
        "raw_36m_worlds_81_anchors_64_bytes_GB": 36000000 * 81 * 64 / 1e9,
        "illustrative_count_bytes_per_anchor": 14 * 3 * 2,
        "illustrative_pilot_count_GB": 70384 * 81 * 14 * 3 * 2 / 1e9,
        "illustrative_36m_world_count_GB": 36000000 * 81 * 14 * 3 * 2 / 1e9,
        "36b_screen_at_100m_per_second_seconds": 36000000000 / 100000000,
        "3_6m_cpu_at_100k_per_second_seconds": 3600000 / 100000,
        "3_6m_cpu_at_50k_per_second_seconds": 3600000 / 50000,
        "v3_hard_floor_count": len(floors),
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources},
    }


if __name__ == "__main__":
    result = verify()
    destination = Path(__file__).with_name("checks.json")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Review probes passed; wrote {destination.relative_to(ROOT)}")
