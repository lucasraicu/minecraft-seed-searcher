#!/usr/bin/env python3
"""Exact semantic gate for immutable pre-sweep v2 native builds."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.native_batch import Prototype, semantic_record

ROOT = Path(__file__).resolve().parents[3]
RUNS = Path(__file__).resolve().parent
ARMS = (
    "control-native",
    "control-cpu-native",
    "control-lto",
    "control-cpu-native-lto",
    "control-chunk64",
    "control-chunk128",
    "control-pgo",
)
NATURAL_SEEDS = [0, -1, -(1 << 63), (1 << 63) - 1, 12345, (1 << 32) + 12345]
FIXTURE_MISSING = [-1, 0, 6, 28]
EXPECTED_QUALIFICATION = ["PREDICTED", "PREDICTED", "PREDICTED", "PENDING"]


def digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def semantic_rows(rows):
    return [semantic_record(row) for row in rows]


def main():
    cfg = two_group_blueprint_config()
    report = {
        "policy_revision": cfg["screening_revision"],
        "config_sha256": digest(cfg),
        "natural_seeds": [str(seed) for seed in NATURAL_SEEDS],
        "fixture_missing_values": FIXTURE_MISSING,
        "expected_fixture_qualification": EXPECTED_QUALIFICATION,
        "arms": {},
    }
    report_path = RUNS / "parity_gate.json"
    reference_native_inputs = None
    for arm in ARMS:
        build_dir = RUNS / arm
        identity = json.loads((build_dir / "identity.json").read_text())
        native_inputs = {k: v for k, v in identity["inputs"].items() if k != "scripts/build_blueprint_batch.py"}
        if reference_native_inputs is None:
            reference_native_inputs = native_inputs
        elif native_inputs != reference_native_inputs:
            raise RuntimeError(f"{arm}: native/bridge/vendor source identity differs from comparison arms")
        if not identity.get("openmp"):
            raise RuntimeError(f"{arm}: OpenMP runtime did not load")
        prototype = Prototype(build_dir, cfg)
        with prototype.sweep(NATURAL_SEEDS, threads=2) as batch:
            natural_direct = semantic_rows(batch.records())
            natural_replay = semantic_rows(batch.records(adapter="replay"))
        natural_python = [
            semantic_record(evaluate_seed(i, seed, cfg))
            for i, seed in enumerate(NATURAL_SEEDS)
        ]
        if natural_direct != natural_replay:
            raise RuntimeError(f"{arm}: direct/replay natural record mismatch")
        if natural_direct != natural_python:
            raise RuntimeError(f"{arm}: native/Python natural record mismatch")

        fixture_seeds = [101, 102, 103, 104]
        fixtures = [(0, 0, missing) for missing in FIXTURE_MISSING]
        with prototype.sweep(fixture_seeds, threads=2, fixtures=fixtures, complete=True) as batch:
            fixture_direct = semantic_rows(batch.records())
            fixture_replay = semantic_rows(batch.records(adapter="replay"))
        fixture_qualification = [row["anchors"][0]["qualification"] for row in fixture_direct]
        if fixture_direct != fixture_replay:
            raise RuntimeError(f"{arm}: direct/replay complete fixture mismatch")
        if fixture_qualification != EXPECTED_QUALIFICATION:
            raise RuntimeError(f"{arm}: unexpected fixture qualification {fixture_qualification}")

        with prototype.sweep(
            fixture_seeds,
            threads=2,
            fixtures=fixtures,
            retention="survivors",
            max_misses=2,
        ) as batch:
            compact_count = batch.pointer.result_count
            retained = semantic_rows(batch.retained_records())
        retained_qualifications = [row["anchors"][0]["qualification"] for row in retained]
        if compact_count != 3 or retained_qualifications != ["PREDICTED"] * 3:
            raise RuntimeError(f"{arm}: compact retention mismatch: {compact_count}, {retained_qualifications}")

        report["arms"][arm] = {
            "build_identity_sha256": digest(identity),
            "extension_sha256": identity["extension_sha256"],
            "source_digest": identity["source_digest"],
            "builder_script_sha256": identity["inputs"]["scripts/build_blueprint_batch.py"],
            "runtime_sha256": identity["runtime_sha256"],
            "natural_record_sha256": digest(natural_direct),
            "natural_records": len(natural_direct),
            "natural_native_python_replay_exact": True,
            "complete_fixture_record_sha256": digest(fixture_direct),
            "fixture_qualification": fixture_qualification,
            "compact_retained_inputs": compact_count,
            "compact_retained_qualifications": retained_qualifications,
            "status": "PASS",
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report["status"] = "PASS"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "arms": report["arms"]}, sort_keys=True))


if __name__ == "__main__":
    main()
