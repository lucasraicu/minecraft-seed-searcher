#!/usr/bin/env python3
"""Run one bounded, identity-checked v2 CLI trial and append its wall time."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
METRICS = {
    "stage_seconds", "native_work", "worker_cpu_seconds", "total_seconds",
    "worker_pid", "worker_peak_rss_bytes", "prototype",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proc_tree(root_pid: int):
    output = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,rss=,pcpu="],
        check=True, capture_output=True, text=True, timeout=3,
    ).stdout
    rows = {}
    for line in output.splitlines():
        pid, parent, rss, cpu = line.split()
        rows[int(pid)] = (int(parent), int(rss), float(cpu))
    selected = {root_pid}
    while True:
        extended = selected | {pid for pid, (parent, _, _) in rows.items() if parent in selected}
        if extended == selected:
            break
        selected = extended
    if root_pid not in rows:
        return None
    return {
        "rss_bytes": sum(rows[pid][1] * 1024 for pid in selected if pid in rows),
        "cpu_percent": sum(rows[pid][2] for pid in selected if pid in rows),
        "pids": sorted(pid for pid in selected if pid in rows),
    }


def load_ledger(path: Path):
    if path.is_file():
        return json.loads(path.read_text())
    return {
        "schema": "pre-sweep-v2-timing-budget-v1",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_seconds": 900,
        "hard_cap_seconds": 1200,
        "measured_cli_seconds": 0.0,
        "measured_profile_seconds": 0.0,
        "events": [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("tuning", "pgo-training", "final"), required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--native-build", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--threads", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--pair", type=int)
    parser.add_argument("--llvm-profile-file", type=Path)
    parser.add_argument("--budget-ledger", type=Path, default=HERE / "timing_budget.json")
    args = parser.parse_args()

    cfg_path = ROOT / "config/realm.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    if cfg.get("screening_revision") != "origin-fixed-2048-two-group-v2":
        raise ValueError("The benchmark requires the pinned corrected v2 policy")
    if cfg.get("search", {}).get("max_misses") != 2 or str(cfg["search"].get("run_key")) != "0":
        raise ValueError("The benchmark requires run_key=0 and B=2")
    if args.mode == "tuning" and (args.count > 50_000 or args.start_index < 2_000_000 or args.start_index + args.count > 2_050_000):
        raise ValueError("Tuning is limited to [2000000,2050000), at most 50000 inputs")
    if args.mode == "pgo-training" and (args.count > 50_000 or args.start_index < 1_000_000 or args.start_index + args.count > 1_050_000):
        raise ValueError("PGO training is limited to [1000000,1050000), at most 50000 inputs")
    if args.mode == "final" and (args.count != 100_000 or args.start_index != 9_000_000_000):
        raise ValueError("Each final arm must cover exactly 100000 held-out inputs")
    if args.mode == "final" and args.pair not in range(5):
        raise ValueError("Final runs must belong to one of the five counterbalanced pairs")
    if not 1 <= args.threads <= 36 or args.batch_size not in (256, 512, 1024, 2048, 4096, 8192, 16384):
        raise ValueError("Thread or batch setting is outside the bounded matrix")
    if args.run.exists():
        raise ValueError(f"Fresh output directory required: {args.run}")
    build = args.native_build.resolve()
    identity_path = build / "identity.json"
    build_identity = json.loads(identity_path.read_text())
    baseline_identity = json.loads((HERE / "control-native/identity.json").read_text())
    native_inputs = {k: v for k, v in build_identity["inputs"].items() if k != "scripts/build_blueprint_batch.py"}
    baseline_native_inputs = {k: v for k, v in baseline_identity["inputs"].items() if k != "scripts/build_blueprint_batch.py"}
    if any(baseline_native_inputs.get(k) != v for k, v in native_inputs.items() if k in baseline_native_inputs):
        raise ValueError("Native/bridge/vendor source identity differs from frozen v2 control")
    if any(k not in native_inputs for k in baseline_native_inputs):
        raise ValueError("Native build omits a hashed control source input")
    if build_identity.get("config_digest") not in (None, hashlib.sha256(cfg_path.read_bytes()).hexdigest()):
        raise ValueError("Build identity has a mismatched policy config digest")

    args.run = args.run.resolve()
    args.receipt = args.receipt.resolve()
    ledger_path = args.budget_ledger.resolve()
    ledger = load_ledger(ledger_path)
    spent_before = float(ledger["measured_cli_seconds"]) + float(ledger["measured_profile_seconds"])
    if spent_before >= ledger["hard_cap_seconds"]:
        raise RuntimeError("Shared profiling/benchmark hard cap is exhausted")

    args.run.mkdir(parents=True)
    command = [
        sys.executable, "-m", "seed_search", "--config", str(cfg_path), "scan",
        "--count", str(args.count), "--start-index", str(args.start_index),
        "--output", str(args.run), "--executor", "native", "--native-build", str(build),
        "--native-threads", str(args.threads), "--native-batch-size", str(args.batch_size),
        "--retention", "survivors", "--max-misses", "2", "--prediction-scale",
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
        environment[name] = "1"
    if args.llvm_profile_file:
        args.llvm_profile_file.parent.mkdir(parents=True, exist_ok=True)
        environment["LLVM_PROFILE_FILE"] = str(args.llvm_profile_file.resolve())

    resource_samples = []
    stop_sample = threading.Event()
    process_holder = {}

    def sample_loop():
        while not stop_sample.is_set():
            process = process_holder.get("process")
            if process is not None:
                try:
                    sample = proc_tree(process.pid)
                    if sample:
                        sample["wal_bytes"] = sum(p.stat().st_size for p in args.run.glob("*-wal") if p.exists())
                        resource_samples.append(sample)
                except (OSError, subprocess.SubprocessError, ValueError):
                    pass
            stop_sample.wait(0.5)

    watcher = threading.Thread(target=sample_loop, daemon=True)
    watcher.start()
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process_holder["process"] = process
    try:
        stdout, stderr = process.communicate(timeout=max(1, int(ledger["hard_cap_seconds"] - spent_before)))
        return_code = process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return_code = process.returncode or 124
    wall_seconds = time.monotonic() - started
    stop_sample.set()
    watcher.join()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    (args.receipt.with_suffix(".stdout.log")).write_text(stdout)
    (args.receipt.with_suffix(".stderr.log")).write_text(stderr)

    event = {
        "kind": "cli_trial", "mode": args.mode, "arm": args.arm,
        "pair": args.pair, "count": args.count, "start_index": args.start_index,
        "threads": args.threads, "batch_size": args.batch_size,
        "native_build": str(build), "extension_sha256": build_identity["extension_sha256"],
        "wall_seconds": wall_seconds, "exit_code": return_code,
    }
    ledger["events"].append(event)
    ledger["measured_cli_seconds"] = float(ledger["measured_cli_seconds"]) + wall_seconds
    ledger["last_cli_inputs_per_second"] = args.count / wall_seconds if return_code == 0 and wall_seconds else None
    ledger["total_measured_seconds"] = ledger["measured_cli_seconds"] + float(ledger["measured_profile_seconds"])
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")

    if return_code != 0:
        args.receipt.write_text(json.dumps({"event": event, "command": command}, indent=2) + "\n")
        raise subprocess.CalledProcessError(return_code, command, stdout, stderr)
    result = json.loads(stdout)
    if int(result.get("completed_seeds", -1)) != args.count:
        raise RuntimeError(f"CLI completed {result.get('completed_seeds')} of {args.count} inputs")

    from seed_search.realm.native_batch import semantic_record
    from seed_search.realm.store import RealmStore, canonical

    with RealmStore(args.run, resume=True) as store:
        identity = store.identity
        if identity.get("native", {}).get("extension_sha256") != build_identity["extension_sha256"]:
            raise RuntimeError("Persisted native identity differs from selected build")
        if identity.get("config") != cfg:
            raise RuntimeError("Persisted resolved policy differs from config/realm.yaml")
        cursor = args.start_index
        for first, end, status in store.db.execute("SELECT start,end,status FROM ranges ORDER BY start"):
            first_i, end_i = int(first), int(end)
            if status != "complete" or first_i != cursor:
                raise RuntimeError("Checkpoint coverage has a gap or unfinished range")
            cursor = end_i
        if cursor != args.start_index + args.count:
            raise RuntimeError("Checkpoint coverage does not equal requested input interval")
        if store.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity_check failed")
        input_decisions = hashlib.sha256()
        receipts = 0
        for (receipt_text,) in store.db.execute("SELECT receipt FROM retention_receipts ORDER BY start"):
            receipt = json.loads(receipt_text)
            input_decisions.update(receipt["input_decisions_sha256"].encode())
            receipts += int(receipt["inputs"])
        if receipts != args.count:
            raise RuntimeError("Retention receipts do not cover every scanned input")
        record_hash = hashlib.sha256()
        retained_inputs = anchors = predicted = 0
        for record in store.iter_results():
            retained_inputs += 1
            anchors += len(record["anchors"])
            predicted += sum(anchor["qualification"] == "PREDICTED" for anchor in record["anchors"])
            record_hash.update(canonical(semantic_record(record)).encode())
        pipeline = store.get_state("native_pipeline") or {}
        table_rows = {
            name: int(store.db.execute(f"SELECT count(*) FROM {name}").fetchone()[0])
            for name in ("seeds", "candidates", "discovery_tasks", "inventory_work", "variant_tasks")
        }
        db_identity = identity
        status = store.status()
        execution = result.get("execution", {})

    sqlite_bytes = sum(path.stat().st_size for path in args.run.glob("realm.sqlite*"))
    receipt = {
        "schema": "pre-sweep-v2-cli-trial-v1", "event": event,
        "command": command, "policy_config_sha256": sha256(cfg_path),
        "source_digest": build_identity["source_digest"],
        "build_identity_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "builder_script_sha256": build_identity["inputs"].get("scripts/build_blueprint_batch.py"),
        "runtime_sha256": build_identity.get("runtime_sha256"),
        "status": result, "checkpointed_completed_inputs": int(status["completed_seeds"]),
        "checkpointed_input_rate": execution.get("checkpointed_scanned_inputs_per_second"),
        "external_cli_rate": args.count / wall_seconds,
        "internal_wall_seconds": execution.get("wall_seconds"),
        "service_seconds": pipeline.get("service_seconds"),
        "batch_latencies_seconds": pipeline.get("batch_latencies_seconds"),
        "peak_process_tree_rss_bytes": max((x["rss_bytes"] for x in resource_samples), default=None),
        "peak_wal_bytes": max((x.get("wal_bytes", 0) for x in resource_samples), default=0),
        "resource_sample_count": len(resource_samples),
        "sqlite_bytes": sqlite_bytes, "sqlite_bytes_per_input": sqlite_bytes / args.count,
        "retention_receipt_inputs": receipts,
        "input_decisions_receipt_sha256": input_decisions.hexdigest(),
        "retained_inputs": retained_inputs, "retained_anchors": anchors,
        "predicted_anchors": predicted, "record_semantics_sha256": record_hash.hexdigest(),
        "table_rows": table_rows, "sqlite_integrity": "ok",
        "resource_samples": resource_samples,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({key: receipt[key] for key in (
        "external_cli_rate", "checkpointed_input_rate", "peak_process_tree_rss_bytes",
        "sqlite_bytes", "retained_inputs", "input_decisions_receipt_sha256",
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
