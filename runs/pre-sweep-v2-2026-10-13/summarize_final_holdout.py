#!/usr/bin/env python3
"""Validate and summarize the five frozen, paired heldout v2 trials."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics

from seed_search.realm.store import RealmStore

HERE = Path(__file__).resolve().parent
EXPECTED_START = 9_000_000_000
EXPECTED_COUNT = 100_000


def percentile_nearest_rank(values, probability):
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1))
    return ordered[index]


def bootstrap_geomean_ci(ratios):
    # Exact paired bootstrap distribution for five pairs, resampling pairs
    # with replacement (5**5 = 3,125 draws).
    samples = [
        math.exp(sum(math.log(ratios[i]) for i in picks) / len(picks))
        for picks in itertools.product(range(len(ratios)), repeat=len(ratios))
    ]
    return {
        "method": "exact paired bootstrap, resample five pair ratios with replacement",
        "draws": len(samples),
        "interval": "95% percentile, nearest-rank endpoints",
        "lower": percentile_nearest_rank(samples, 0.025),
        "upper": percentile_nearest_rank(samples, 0.975),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE / "final-heldout")
    parser.add_argument("--label", default="o3-ch16-34t-16384")
    parser.add_argument("--output", type=Path, default=HERE / "final-heldout-summary.json")
    args = parser.parse_args()

    pair_root = args.root.resolve() / args.label
    pairs = []
    for index in range(5):
        pair_dir = pair_root / f"pair-{index:02d}"
        summary_path = pair_dir / "pair.json"
        if not summary_path.is_file():
            raise FileNotFoundError(f"Missing final pair {index}: {summary_path}")
        summary = json.loads(summary_path.read_text())
        if summary.get("mode") != "final" or summary.get("pair_index") != index:
            raise RuntimeError(f"Pair metadata mismatch in {summary_path}")
        if summary.get("count") != EXPECTED_COUNT or summary.get("start_index") != EXPECTED_START:
            raise RuntimeError(f"Heldout cohort mismatch in {summary_path}")
        expected_order = ["control", "selected"] if index % 2 == 0 else ["selected", "control"]
        if summary.get("order") != expected_order:
            raise RuntimeError(f"Pair order is not counterbalanced for pair {index}")
        arms = {}
        for arm in ("control", "selected"):
            receipt = json.loads((pair_dir / arm / "receipt.json").read_text())
            event = receipt["event"]
            if event.get("exit_code") != 0 or event.get("count") != EXPECTED_COUNT or event.get("start_index") != EXPECTED_START:
                raise RuntimeError(f"Incomplete or wrong cohort in pair {index} {arm}")
            if receipt.get("checkpointed_completed_inputs") != EXPECTED_COUNT or receipt.get("retention_receipt_inputs") != EXPECTED_COUNT:
                raise RuntimeError(f"Checkpoint/receipt coverage mismatch in pair {index} {arm}")
            if receipt.get("sqlite_integrity") != "ok":
                raise RuntimeError(f"SQLite integrity failure in pair {index} {arm}")
            if event.get("threads") != (16 if arm == "control" else 34):
                raise RuntimeError(f"Unexpected thread setting in pair {index} {arm}")
            if event.get("batch_size") != (4096 if arm == "control" else 16384):
                raise RuntimeError(f"Unexpected batch setting in pair {index} {arm}")
            with RealmStore(pair_dir / arm / "run", resume=True) as store:
                pipeline = store.get_state("native_pipeline") or {}
            arms[arm] = {"receipt": receipt, "pipeline": pipeline}
        c = arms["control"]["receipt"]
        s = arms["selected"]["receipt"]
        if c["event"]["extension_sha256"] != s["event"]["extension_sha256"]:
            raise RuntimeError(f"Final arms used different native builds in pair {index}")
        if c.get("record_semantics_sha256") != s.get("record_semantics_sha256"):
            raise RuntimeError(f"Retained semantic records differ in pair {index}")
        external_ratio = c["event"]["wall_seconds"] / s["event"]["wall_seconds"]
        checkpoint_ratio = c["checkpointed_input_rate"] and s["checkpointed_input_rate"]
        checkpoint_ratio = (s["checkpointed_input_rate"] / c["checkpointed_input_rate"]) if checkpoint_ratio else None
        pairs.append({
            "pair_index": index,
            "order": summary["order"],
            "control_external_wall_seconds": c["event"]["wall_seconds"],
            "selected_external_wall_seconds": s["event"]["wall_seconds"],
            "control_external_cli_inputs_per_second": c["external_cli_rate"],
            "selected_external_cli_inputs_per_second": s["external_cli_rate"],
            "control_checkpointed_inputs_per_second": c["checkpointed_input_rate"],
            "selected_checkpointed_inputs_per_second": s["checkpointed_input_rate"],
            "external_speedup_control_over_selected": external_ratio,
            "checkpointed_rate_ratio_selected_over_control": checkpoint_ratio,
            "control_peak_process_tree_rss_bytes": c.get("peak_process_tree_rss_bytes"),
            "selected_peak_process_tree_rss_bytes": s.get("peak_process_tree_rss_bytes"),
            "control_resource_sample_count": c.get("resource_sample_count"),
            "selected_resource_sample_count": s.get("resource_sample_count"),
            "control_sqlite_bytes": c.get("sqlite_bytes"),
            "selected_sqlite_bytes": s.get("sqlite_bytes"),
            "control_peak_wal_bytes": c.get("peak_wal_bytes"),
            "selected_peak_wal_bytes": s.get("peak_wal_bytes"),
            "control_service_seconds": c.get("service_seconds"),
            "selected_service_seconds": s.get("service_seconds"),
            "control_pipeline_limits": {key: arms["control"]["pipeline"].get(key) for key in ("batches", "cpu_slots", "max_outstanding_batches", "max_native_buffer_bytes_per_batch", "max_prepared_bytes", "max_prepared_owned_estimate_bytes")},
            "selected_pipeline_limits": {key: arms["selected"]["pipeline"].get(key) for key in ("batches", "cpu_slots", "max_outstanding_batches", "max_native_buffer_bytes_per_batch", "max_prepared_bytes", "max_prepared_owned_estimate_bytes")},
            "control_retained_inputs": c.get("retained_inputs"),
            "selected_retained_inputs": s.get("retained_inputs"),
            "control_retained_anchors": c.get("retained_anchors"),
            "selected_retained_anchors": s.get("retained_anchors"),
            "record_semantics_sha256": c.get("record_semantics_sha256"),
            "extension_sha256": c["event"]["extension_sha256"],
        })

    ratios = [pair["external_speedup_control_over_selected"] for pair in pairs]
    checkpointed = [pair["checkpointed_rate_ratio_selected_over_control"] for pair in pairs if pair["checkpointed_rate_ratio_selected_over_control"] is not None]
    geomean = math.exp(sum(math.log(value) for value in ratios) / len(ratios))
    service_medians = {}
    for arm in ("control", "selected"):
        keys = pairs[0][f"{arm}_service_seconds"] or {}
        service_medians[arm] = {
            key: statistics.median(pair[f"{arm}_service_seconds"][key] for pair in pairs)
            for key in keys
        }
    identity_path = HERE / "final-runtime-identity.json"
    runtime_identity = json.loads(identity_path.read_text()) if identity_path.is_file() else None
    positive_path = HERE / "positive-natural-service/receipt.json"
    positive_service = None
    if positive_path.is_file():
        positive = json.loads(positive_path.read_text())
        event = positive["event"]
        status = positive.get("status", {})
        if event.get("mode") != "tuning" or event.get("count") != 1 or not 2_000_000 <= event.get("start_index", -1) < 2_050_000:
            raise RuntimeError("Positive service run must be a separate one-input tuning-cohort observation")
        if status.get("candidate_counts", {}).get("PREDICTED") != 1 or positive.get("retained_inputs") != 1:
            raise RuntimeError("Positive natural service input did not retain one predicted candidate")
        positive_service = {
            "receipt_path": str(positive_path.relative_to(HERE)),
            "seed_index": event["start_index"],
            "count": event["count"],
            "threads": event["threads"],
            "batch_size": event["batch_size"],
            "external_wall_seconds": event["wall_seconds"],
            "external_cli_inputs_per_second": positive["external_cli_rate"],
            "checkpointed_inputs_per_second": positive["checkpointed_input_rate"],
            "retained_inputs": positive["retained_inputs"],
            "retained_anchors": positive["retained_anchors"],
            "candidate_counts": status.get("candidate_counts"),
            "service_seconds": positive.get("service_seconds"),
            "sqlite_integrity": positive.get("sqlite_integrity"),
            "record_semantics_sha256": positive.get("record_semantics_sha256"),
            "extension_sha256": event["extension_sha256"],
            "note": "Separate previously observed tuning-cohort natural positive; excluded from all heldout pair statistics.",
        }
    report = {
        "schema": "pre-sweep-v2-final-heldout-summary-v1",
        "mode": "final",
        "policy": "config/realm.yaml corrected v2, run_key=0, B=2",
        "cohort": {"start_index": EXPECTED_START, "count_per_arm": EXPECTED_COUNT, "end_index_exclusive": EXPECTED_START + EXPECTED_COUNT},
        "counterbalanced_pairs": pairs,
        "runtime_identity": None if runtime_identity is None else {
            "identity_path": "final-runtime-identity.json",
            "runtime_source_digest": runtime_identity["runtime_source_digest"],
            "git_head": runtime_identity["git_head"],
            "native_build_identity_sha256": runtime_identity["native_build_identity_sha256"],
            "native_extension_sha256": runtime_identity["native_extension_sha256"],
            "native_source_digest": runtime_identity["native_source_digest"],
            "openmp_runtime_sha256": runtime_identity["openmp_runtime_sha256"],
        },
        "positive_candidate_service_separate_from_heldout": positive_service,
        "external_cli": {
            "primary_metric": "per-pair external CLI wall time; selected speedup is control wall / selected wall",
            "control_median_seconds": statistics.median(p["control_external_wall_seconds"] for p in pairs),
            "selected_median_seconds": statistics.median(p["selected_external_wall_seconds"] for p in pairs),
            "control_wall_range_seconds": [min(p["control_external_wall_seconds"] for p in pairs), max(p["control_external_wall_seconds"] for p in pairs)],
            "selected_wall_range_seconds": [min(p["selected_external_wall_seconds"] for p in pairs), max(p["selected_external_wall_seconds"] for p in pairs)],
            "paired_geometric_mean_speedup_control_over_selected": geomean,
            "median_paired_speedup_control_over_selected": statistics.median(ratios),
            "paired_ratio_range": [min(ratios), max(ratios)],
            "paired_bootstrap_95_percentile_ci": bootstrap_geomean_ci(ratios),
        },
        "checkpointed_throughput": {
            "control_median_inputs_per_second": statistics.median(p["control_checkpointed_inputs_per_second"] for p in pairs),
            "selected_median_inputs_per_second": statistics.median(p["selected_checkpointed_inputs_per_second"] for p in pairs),
            "selected_over_control_rate_ratio_median": statistics.median(checkpointed),
            "note": "Reported separately from external CLI wall time; do not substitute it for the primary end-to-end metric.",
        },
        "service_stage_medians_seconds": {
            "control": service_medians["control"],
            "selected": service_medians["selected"],
            "note": "These are overlapping service timers; report each separately and do not sum them into a wall-time decomposition.",
        },
        "validation": {
            "all_five_pairs_have_exact_100k_cohort": True,
            "orders_alternate_AB_BA": True,
            "checkpoint_and_retention_receipts_cover_each_input": True,
            "sqlite_integrity_ok": True,
            "native_build_identical_within_pairs": True,
            "retained_semantic_records_equal_within_pairs": True,
            "heldout_retained_inputs_per_arm": [pair[f"{arm}_retained_inputs"] for pair in pairs for arm in ("control", "selected")],
            "heldout_had_zero_retained_candidates": all(pair[f"{arm}_retained_inputs"] == 0 for pair in pairs for arm in ("control", "selected")),
            "positive_natural_candidate_service_measured_separately": positive_service is not None,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"pairs": len(pairs), "geomean_speedup": geomean, "bootstrap_ci": report["external_cli"]["paired_bootstrap_95_percentile_ci"]}, sort_keys=True))


if __name__ == "__main__":
    main()
