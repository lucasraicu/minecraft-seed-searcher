#!/usr/bin/env python3
"""Run a sequential AB/BA pair over one identical bounded v2 cohort."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TRIAL = HERE / "bounded_cli_trial.py"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("tuning", "final"), required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--pair-index", type=int, default=0)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--control-build", type=Path, required=True)
    p.add_argument("--selected-build", type=Path, required=True)
    p.add_argument("--control-config", type=Path, default=ROOT / "config/realm.yaml")
    p.add_argument("--selected-config", type=Path, default=ROOT / "config/realm.yaml")
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--start-index", type=int, required=True)
    p.add_argument("--control-threads", type=int, default=16)
    p.add_argument("--control-batch", type=int, default=4096)
    p.add_argument("--selected-threads", type=int, required=True)
    p.add_argument("--selected-batch", type=int, required=True)
    p.add_argument("--budget-ledger", type=Path, default=HERE / "timing_budget.json")
    args = p.parse_args()

    if args.mode == "final":
        if args.pair_index not in range(5):
            raise ValueError("Final comparison has exactly five pair indices (0–4)")
        if args.count != 100_000 or args.start_index != 12_345_670_000:
            raise ValueError("Final comparison is fixed to the untouched 100000-input held-out interval")
    elif args.count > 50_000 or args.start_index < 3_000_000 or args.start_index + args.count > 3_050_000:
        raise ValueError("Tuning pairs are limited to [3000000,3050000), at most 50000 inputs")

    order = ["control", "selected"] if args.pair_index % 2 == 0 else ["selected", "control"]
    builds = {"control": args.control_build.resolve(), "selected": args.selected_build.resolve()}
    settings = {
        "control": (args.control_threads, args.control_batch),
        "selected": (args.selected_threads, args.selected_batch),
    }
    configs = {"control": args.control_config.resolve(), "selected": args.selected_config.resolve()}
    import yaml
    control_policy = yaml.safe_load(configs["control"].read_text())
    selected_policy = yaml.safe_load(configs["selected"].read_text())
    control_order = control_policy["search"].pop("structure_order")
    selected_order = selected_policy["search"].pop("structure_order")
    control_after = control_policy["search"].pop("stronghold_after_structure_count",2)
    selected_after = selected_policy["search"].pop("stronghold_after_structure_count",2)
    if control_policy != selected_policy:
        raise ValueError("Pair config differs beyond structure evaluation order")
    root = args.output_root.resolve()
    pair_dir = root / args.label / f"pair-{args.pair_index:02d}"
    if pair_dir.exists():
        raise ValueError(f"Fresh pair directory required: {pair_dir}")
    pair_dir.mkdir(parents=True)
    arms = {}
    for arm in order:
        threads, batch = settings[arm]
        run_dir = pair_dir / arm / "run"
        receipt = pair_dir / arm / "receipt.json"
        command = [
            sys.executable, str(TRIAL), "--mode", args.mode, "--arm", arm,
            "--native-build", str(builds[arm]), "--run", str(run_dir), "--receipt", str(receipt),
            "--config", str(configs[arm]),
            "--count", str(args.count), "--start-index", str(args.start_index),
            "--threads", str(threads), "--batch-size", str(batch),
            "--pair", str(args.pair_index), "--budget-ledger", str(args.budget_ledger.resolve()),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
        (pair_dir / f"{arm}.harness.stdout.log").write_text(completed.stdout)
        (pair_dir / f"{arm}.harness.stderr.log").write_text(completed.stderr)
        if completed.returncode:
            raise subprocess.CalledProcessError(completed.returncode, command, completed.stdout, completed.stderr)
        arms[arm] = json.loads(receipt.read_text())
    if arms["control"]["event"]["start_index"] != arms["selected"]["event"]["start_index"]:
        raise RuntimeError("Paired arms did not use the same cohort start")
    if arms["control"]["event"]["count"] != arms["selected"]["event"]["count"]:
        raise RuntimeError("Paired arms did not use the same cohort size")
    result = {
        "schema": "pre-sweep-v2-paired-trial-v1", "mode": args.mode,
        "label": args.label, "pair_index": args.pair_index, "order": order,
        "count": args.count, "start_index": args.start_index,
        "control_config": str(configs["control"]), "selected_config": str(configs["selected"]),
        "control_order": control_order, "selected_order": selected_order,
        "control_stronghold_after": control_after, "selected_stronghold_after": selected_after,
        "control": {"wall_seconds": arms["control"]["event"]["wall_seconds"],
                    "external_cli_rate": arms["control"]["external_cli_rate"],
                    "checkpointed_input_rate": arms["control"]["checkpointed_input_rate"],
                    "extension_sha256": arms["control"]["event"]["extension_sha256"]},
        "selected": {"wall_seconds": arms["selected"]["event"]["wall_seconds"],
                     "external_cli_rate": arms["selected"]["external_cli_rate"],
                     "checkpointed_input_rate": arms["selected"]["checkpointed_input_rate"],
                     "extension_sha256": arms["selected"]["event"]["extension_sha256"]},
        "speedup_control_over_selected": arms["control"]["event"]["wall_seconds"] / arms["selected"]["event"]["wall_seconds"],
    }
    (pair_dir / "pair.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
