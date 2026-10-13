#!/usr/bin/env python3
"""Exact semantic gate for immutable pre-sweep v2 native builds."""
from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path
import yaml

from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.native_batch import Prototype, semantic_record

RUNS = Path(__file__).resolve().parent
NATURAL_SEEDS = [0, -1, -(1 << 63), (1 << 63) - 1, 12345, (1 << 32) + 12345]
FIXTURE_MISSING = [-1, 0, 6, 28]
EXPECTED_QUALIFICATION = ["PREDICTED", "PREDICTED", "PREDICTED", "PENDING"]


def digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def semantic_rows(rows):
    return [semantic_record(row) for row in rows]


def decision_rows(rows):
    return [{"index": row["index"], "seed": row["seed"],
             "anchors": [{"qualification": a["qualification"],
                          "score": a["baseline_score_observed"],
                          "deficit_categories": a.get("deficit_categories"),
                          "fatal_reasons": a.get("fatal_reasons"),
                          "biome_failures": a.get("biome_failures")}
                         for a in row["anchors"]]}
            for row in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, action="append", required=True)
    parser.add_argument("--config", type=Path, action="append")
    parser.add_argument("--output", type=Path, default=RUNS / "parity_gate.json")
    args = parser.parse_args()
    if args.config and len(args.config) != len(args.build):
        parser.error("Provide one --config per --build")
    configs = [yaml.safe_load(path.read_text()) for path in args.config] if args.config else [two_group_blueprint_config()] * len(args.build)
    report = {
        "policy_revision": "origin-fixed-2048-two-group-v2",
        "natural_seeds": [str(seed) for seed in NATURAL_SEEDS],
        "fixture_missing_values": FIXTURE_MISSING,
        "expected_fixture_qualification": EXPECTED_QUALIFICATION,
        "arms": {},
    }
    report_path = args.output
    for build_dir, cfg in zip(args.build, configs):
        arm = build_dir.name
        identity = json.loads((build_dir / "identity.json").read_text())
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
        if decision_rows(natural_direct) != decision_rows(natural_python):
            raise RuntimeError(f"{arm}: native/Python natural decision mismatch")

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
            "config_sha256": digest(cfg),
            "extension_sha256": identity["extension_sha256"],
            "source_digest": identity["source_digest"],
            "builder_script_sha256": identity["inputs"]["scripts/build_blueprint_batch.py"],
            "runtime_sha256": identity["runtime_sha256"],
            "natural_record_sha256": digest(natural_direct),
            "natural_records": len(natural_direct),
            "natural_native_python_decisions_equal": True,
            "natural_native_replay_exact": True,
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
