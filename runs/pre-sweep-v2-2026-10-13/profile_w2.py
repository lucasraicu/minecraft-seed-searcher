#!/usr/bin/env python3
"""Bounded C-only stage/biome profile; adds measured time to shared ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STAGE_NAMES = [
    "stronghold_discovery_and_delayed_query",
    "mansion_floor", "jungle_temple_floor", "desert_pyramid_floor", "monument_floor",
    "ancient_city_floor", "village_floor", "trial_chamber_floor", "ruined_portal_floor",
    "shipwreck_floor", "mineshaft_floor", "nether_fortress_bastion_screen",
    "biome_palette", "full_inventory_overall",
    "inventory_mansion", "inventory_jungle_temple", "inventory_desert_pyramid",
    "inventory_monument", "inventory_ancient_city", "inventory_village",
    "inventory_trial_chamber", "inventory_ruined_portal", "inventory_shipwreck",
    "inventory_mineshaft", "inventory_fortress", "inventory_bastion", "inventory_outpost",
    "forced_profile_fortress", "forced_profile_bastion", "outpost_floor",
]


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def aggregate(samples, count_name):
    out = {"calls": 0, "total_seconds": 0.0, "max_seconds": 0.0, "max_coordinate": None}
    for sample in samples:
        timing = getattr(sample, count_name)
        out["calls"] += int(timing.count)
        out["total_seconds"] += float(timing.total_seconds)
        if float(timing.max_seconds) > out["max_seconds"]:
            out["max_seconds"] = float(timing.max_seconds)
            out["max_coordinate"] = [int(timing.max_x), int(timing.max_y), int(timing.max_z)]
    if out["calls"]:
        out["mean_seconds"] = out["total_seconds"] / out["calls"]
    else:
        out["mean_seconds"] = None
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-build", type=Path, required=True)
    parser.add_argument("--count", type=int, default=512)
    parser.add_argument("--start-index", type=int, default=2_000_000)
    parser.add_argument("--threads", type=int, default=34)
    parser.add_argument("--positive-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "w2-profile.json")
    parser.add_argument("--budget-ledger", type=Path, default=HERE / "timing_budget.json")
    args = parser.parse_args()
    if not 1 <= args.count <= 510 or args.start_index < 2_000_000 or args.start_index + args.count > 2_050_000:
        raise ValueError("Profile is limited to at most 510 distinct tuning-cohort inputs")

    cfg_path = ROOT / "config/realm.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    if cfg.get("screening_revision") != "origin-fixed-2048-two-group-v2" or cfg["search"]["max_misses"] != 2:
        raise ValueError("W2 profile requires the pinned v2 B=2 configuration")
    build = args.profile_build.resolve()
    build_identity = json.loads((build / "identity.json").read_text())
    if not build_identity.get("profiling"):
        raise ValueError("Expected the diagnostic-only --profile build")

    # Derive a few real v2 predicted survivors from the already measured tuning
    # cohort so the diagnostic includes positive inventory and serialization work.
    from seed_search.realm.store import RealmStore
    positives = []
    with RealmStore(args.positive_run, resume=True) as store:
        for record in store.iter_results():
            if record.get("seed") is not None:
                positives.append(int(record["seed"]))
            if len(positives) == 2:
                break
    if not positives:
        raise RuntimeError("The tuning cohort yielded no retained natural positive for the profile")

    from seed_search.realm.config import two_group_blueprint_config
    from seed_search.realm.native_batch import Prototype
    from seed_search.seeds import seed_from_index
    prototype = Prototype(build, two_group_blueprint_config())
    prototype.policy.retention = 1
    prototype.policy.max_misses = 2
    prototype.policy.complete = 0
    seeds = [seed_from_index(index, 0) for index in range(args.start_index, args.start_index + args.count)]
    seeds.extend(value for value in positives if value not in set(seeds))
    if len(seeds) > 512:
        raise RuntimeError("Distinct natural inputs plus positives exceed profile ABI bound")
    values = prototype.ffi.new("uint64_t[]", [value & ((1 << 64) - 1) for value in seeds])

    started = time.monotonic()
    profile = prototype.lib.nb_profile_sweep(values, len(seeds), prototype.policy, args.threads)
    elapsed = time.monotonic() - started
    if profile == prototype.ffi.NULL:
        raise RuntimeError("C diagnostic profile returned NULL")
    try:
        samples = [profile.samples[i] for i in range(len(seeds))]
        # CFFI indexes an array field directly, unlike scalar struct members.
        stages = {}
        for index, name in enumerate(STAGE_NAMES):
            metric = {"calls": 0, "total_seconds": 0.0, "max_seconds": 0.0, "max_coordinate": None}
            for sample in samples:
                timing = sample.stages[index]
                metric["calls"] += int(timing.count)
                metric["total_seconds"] += float(timing.total_seconds)
                if float(timing.max_seconds) > metric["max_seconds"]:
                    metric["max_seconds"] = float(timing.max_seconds)
                    metric["max_coordinate"] = [int(timing.max_x), int(timing.max_y), int(timing.max_z)]
            metric["mean_seconds"] = metric["total_seconds"] / metric["calls"] if metric["calls"] else None
            stages[str(index)] = {"name": name, **metric}
        cache_queries = sum(int(sample.mansion_queries) for sample in samples)
        cache_hits = sum(int(sample.mansion_cache_hits) for sample in samples)
        families = list(cfg["biomes"]["required_families"])
        biome_families = {}
        for index, name in enumerate(families):
            biome_families[name] = {
                "calls": sum(int(sample.biome_families[index].count) for sample in samples),
                "total_seconds": sum(float(sample.biome_families[index].total_seconds) for sample in samples),
            }
        biome_y = {}
        for index, y in enumerate(cfg["biomes"]["sample_y_levels"]):
            biome_y[str(y)] = {
                "calls": sum(int(sample.biome_y[index].count) for sample in samples),
                "total_seconds": sum(float(sample.biome_y[index].total_seconds) for sample in samples),
            }
        biome_ids = []
        from seed_search.backend import biome_catalog
        names_by_id = {int(row["id"]): row["name"] for row in biome_catalog()}
        for biome_id in range(256):
            calls = sum(int(sample.biome_ids[biome_id].count) for sample in samples)
            total = sum(float(sample.biome_ids[biome_id].total_seconds) for sample in samples)
            if calls:
                biome_ids.append({"id": biome_id, "name": names_by_id.get(biome_id, "unknown"), "calls": calls, "total_seconds": total})
        biome_ids.sort(key=lambda row: row["total_seconds"], reverse=True)
        batch_status = profile.batch[0]
        if int(batch_status.error):
            raise RuntimeError(f"Diagnostic batch error {int(batch_status.error)}")
    finally:
        prototype.lib.nb_profile_free(profile)

    ledger_path = args.budget_ledger.resolve()
    ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {
        "schema": "pre-sweep-v2-timing-budget-v1", "target_seconds": 900,
        "hard_cap_seconds": 1200, "measured_cli_seconds": 0.0,
        "measured_profile_seconds": 0.0, "events": [],
    }
    if float(ledger["measured_cli_seconds"]) + float(ledger["measured_profile_seconds"]) + elapsed > float(ledger["hard_cap_seconds"]):
        raise RuntimeError("W2 profile would exceed the shared hard cap")
    event = {
        "kind": "w2_native_profile", "wall_seconds": elapsed, "count": len(seeds),
        "sampled_distinct_inputs": args.count, "positive_natural_inputs": len(positives),
        "threads": args.threads, "source_digest": build_identity["source_digest"],
    }
    ledger["events"].append(event)
    ledger["measured_profile_seconds"] = float(ledger["measured_profile_seconds"]) + elapsed
    ledger["total_measured_seconds"] = ledger["measured_cli_seconds"] + ledger["measured_profile_seconds"]
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")

    output = {
        "schema": "pre-sweep-v2-w2-profile-v1", "event": event,
        "config_sha256": hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
        "build_identity_sha256": hashlib.sha256((build / "identity.json").read_bytes()).hexdigest(),
        "extension_sha256": build_identity["extension_sha256"],
        "runtime_sha256": build_identity.get("runtime_sha256"),
        "builder_script_sha256": build_identity["inputs"].get("scripts/build_blueprint_batch.py"),
        "stages": stages, "mansion_cache": {"queries": cache_queries, "hits": cache_hits,
            "hit_rate": cache_hits / cache_queries if cache_queries else None},
        "biome_families": biome_families, "biome_y": biome_y,
        "top_biome_ids": biome_ids[:20],
        "non_additive_notes": {
            "inventory_substages": "Stages 14–26 are nested inside full_inventory_overall (stage 13); do not sum them into stage total.",
            "biome_histograms": "Family, Y-level and biome-ID totals overlap and are not mutually additive.",
            "stronghold": "The diagnostic reports early plus delayed Stronghold query time together; active retention-mode control flow delays it until two cheap structure slots pass.",
            "profile_overhead": "Fine-grain C timing is diagnostic and is not used for throughput claims.",
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"profile_seconds": elapsed, "inputs": len(seeds), "positive_natural_inputs": len(positives)}, sort_keys=True))


if __name__ == "__main__":
    main()
