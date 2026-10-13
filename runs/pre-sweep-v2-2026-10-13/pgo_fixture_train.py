#!/usr/bin/env python3
"""Exercise positive and pending v2 fixtures on an instrumented PGO build."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MISSING = [-1, 0, 6, 28]
EXPECTED = ["PREDICTED", "PREDICTED", "PREDICTED", "PENDING"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--profile-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "pgo-fixtures.json")
    parser.add_argument("--budget-ledger", type=Path, default=HERE / "timing_budget.json")
    args = parser.parse_args()

    build = args.build.resolve()
    profile_file = args.profile_file.resolve()
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    identity = json.loads((build / "identity.json").read_text())
    if not identity.get("pgo_generate"):
        raise ValueError("Fixture training requires a --pgo-generate build")

    code = r'''
import hashlib, json, sys
from pathlib import Path
from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.native_batch import Prototype, semantic_record

def digest(value):
    import json
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

build = Path(sys.argv[1])
cfg = two_group_blueprint_config()
p = Prototype(build, cfg)
seeds = [101, 102, 103, 104]
missing = [-1, 0, 6, 28]
fixtures = [(0, 0, value) for value in missing]
with p.sweep(seeds, threads=2, fixtures=fixtures, complete=True) as batch:
    direct = [semantic_record(row) for row in batch.records()]
    replay = [semantic_record(row) for row in batch.records(adapter="replay")]
if direct != replay:
    raise RuntimeError("PGO fixture direct/replay semantic mismatch")
qualification = [row["anchors"][0]["qualification"] for row in direct]
expected = ["PREDICTED", "PREDICTED", "PREDICTED", "PENDING"]
if qualification != expected:
    raise RuntimeError(f"unexpected PGO fixture qualification: {qualification}")
print(json.dumps({"status": "PASS", "count": len(direct), "missing": missing,
    "qualification": qualification, "record_sha256": digest(direct)}, sort_keys=True))
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
    environment["LLVM_PROFILE_FILE"] = str(profile_file)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
        environment[name] = "1"
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-c", code, str(build)], cwd=ROOT, env=environment,
        check=False, capture_output=True, text=True,
    )
    elapsed = time.monotonic() - started
    (args.output.with_suffix(".stdout.log")).write_text(proc.stdout)
    (args.output.with_suffix(".stderr.log")).write_text(proc.stderr)
    if proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    raw_files = sorted(profile_file.parent.glob(profile_file.name.replace("%p", "*")))
    if not raw_files:
        raise RuntimeError("LLVM emitted no raw PGO profile")

    ledger_path = args.budget_ledger.resolve()
    ledger = json.loads(ledger_path.read_text())
    if float(ledger["measured_cli_seconds"]) + float(ledger["measured_profile_seconds"]) + elapsed > float(ledger["hard_cap_seconds"]):
        raise RuntimeError("PGO fixture training would exceed the shared hard cap")
    event = {
        "kind": "pgo_positive_fixture_training", "wall_seconds": elapsed,
        "count": result["count"], "qualification": result["qualification"],
        "record_sha256": result["record_sha256"], "extension_sha256": identity["extension_sha256"],
        "profile_raw_files": [str(path) for path in raw_files],
    }
    ledger["events"].append(event)
    ledger["measured_profile_seconds"] = float(ledger["measured_profile_seconds"]) + elapsed
    ledger["total_measured_seconds"] = ledger["measured_cli_seconds"] + ledger["measured_profile_seconds"]
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    report = {
        "schema": "pre-sweep-v2-pgo-fixture-training-v1", "event": event,
        "source_digest": identity["source_digest"], "build_identity_sha256": hashlib.sha256((build / "identity.json").read_bytes()).hexdigest(),
        "builder_script_sha256": identity["inputs"].get("scripts/build_blueprint_batch.py"),
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(event, sort_keys=True))


if __name__ == "__main__":
    main()
