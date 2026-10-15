#!/usr/bin/env python3
"""
Distributed Shard Allocator & Capacity Preflight Tool for Minecraft Seed Sweeps.

Target Policy: dynamic-envelope-1664-v1
Author: Task 4: Distributed sweep and benchmark runbook

Features:
- Generates provably disjoint half-open intervals [start_index, start_index + count).
- Verifies interval coverage, non-overlapping properties, and boundary invariants.
- Strict input validation rejecting booleans, non-integers, floats, negative ranges, and 64-bit overflow.
- Computes conservative storage estimates aligned with resources.disk_policy:
  * Compact ('survivors'): defaults to 32 projected bytes/input.
  * Full ('full'): defaults to 65,536 projected bytes/input.
  * Separates conservative policy projections from detailed analytical models.
- Emits exact, copy-pasteable CLI commands for multi-node deployments with explicit per-shard YAML policy and run key.
- Generates the 5-pair counterbalanced validation test suite schedule.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass
import json
import math
import shlex
import sys
from typing import Any, Dict, List, Optional, Tuple

LIMIT64: int = 1 << 64


def _validate_int(
    val: Any,
    name: str,
    *,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
) -> int:
    """Validate that val is a strict integer (rejecting booleans, floats, None, strings, etc.)."""
    if isinstance(val, bool):
        raise TypeError(f"{name} cannot be a boolean (got {val!r})")
    if not isinstance(val, int):
        raise TypeError(f"{name} must be an integer (got {type(val).__name__}: {val!r})")
    if min_val is not None and val < min_val:
        raise ValueError(f"{name} must be >= {min_val} (got {val})")
    if max_val is not None and val > max_val:
        raise ValueError(f"{name} must be <= {max_val} (got {val})")
    return val


def validate_range(start: int, count: int) -> Tuple[int, int]:
    """Validate a half-open range [start, start + count) within [0, 2^64).

    Rejects:
    - Booleans explicitly
    - Non-integers, floats, None
    - Negative start (< 0)
    - Negative count (< 0)
    - Ranges exceeding 2^64 (start + count > LIMIT64)
    """
    _validate_int(start, "start", min_val=0, max_val=LIMIT64)
    _validate_int(count, "count", min_val=0, max_val=LIMIT64)
    if start + count > LIMIT64:
        raise ValueError(
            f"Range [{start}, {start + count}) exceeds 64-bit limit [0, 2^64) "
            f"(start + count = {start + count} > {LIMIT64})"
        )
    return start, count


def validate_shard_size(shard_size: int) -> int:
    """Validate shard size is a strict positive integer.

    Rejects:
    - Booleans explicitly
    - Non-integers, floats, None
    - Non-positive values (shard_size <= 0)
    """
    return _validate_int(shard_size, "shard_size", min_val=1, max_val=LIMIT64)


@dataclass(frozen=True)
class ShardSpec:
    shard_id: int
    name: str
    start_index: int
    count: int
    end_index: int
    node_id: str
    output_dir: str
    policy: str = "dynamic-envelope-1664-v1"
    run_key: str = "0"

    def __post_init__(self):
        _validate_int(self.shard_id, "shard_id", min_val=1)
        if isinstance(self.name, bool) or not isinstance(self.name, str) or not self.name.strip():
            raise TypeError("name must be a non-empty string")
        validate_range(self.start_index, self.count)
        if self.count <= 0:
            raise ValueError(f"count must be positive for ShardSpec, got {self.count}")
        _validate_int(self.end_index, "end_index", min_val=1, max_val=LIMIT64)
        if self.end_index != self.start_index + self.count:
            raise ValueError(
                f"end_index ({self.end_index}) must equal start_index + count "
                f"({self.start_index + self.count})"
            )
        if isinstance(self.node_id, bool) or not isinstance(self.node_id, str):
            raise TypeError("node_id must be a string")
        if isinstance(self.output_dir, bool) or not isinstance(self.output_dir, str):
            raise TypeError("output_dir must be a string")
        if isinstance(self.policy, bool) or not isinstance(self.policy, str):
            raise TypeError("policy must be a string")
        if isinstance(self.run_key, bool) or not isinstance(self.run_key, (str, int)):
            raise TypeError("run_key must be a string or integer")

    def to_dict(self) -> dict:
        return {
            "shard_id": self.shard_id,
            "name": self.name,
            "start_index": self.start_index,
            "count": self.count,
            "end_index": self.end_index,
            "node_id": self.node_id,
            "output_dir": self.output_dir,
            "policy": self.policy,
            "run_key": str(self.run_key),
        }


def validate_intervals(
    intervals: List[Tuple[int, int]],
    strict: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate that half-open intervals [start, end) are non-overlapping and within 64-bit limits.

    Validates:
    - Coordinates are strict integers (rejects booleans, floats, None).
    - Intervals satisfy 0 <= start < end <= 2^64.
    - No collisions or overlaps exist between intervals.

    If strict=True, raises TypeError or ValueError on the first violation.
    Otherwise, returns (is_valid, errors).
    """
    errors: List[str] = []
    if not intervals:
        return True, []

    validated_intervals: List[Tuple[int, int]] = []

    for i, item in enumerate(intervals):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            msg = f"Interval {i} is not a 2-tuple: {item!r}"
            if strict:
                raise TypeError(msg)
            errors.append(msg)
            continue
        start, end = item
        if isinstance(start, bool) or not isinstance(start, int):
            msg = f"Interval {i} start coordinate cannot be {type(start).__name__}: {start!r}"
            if strict:
                raise TypeError(msg)
            errors.append(msg)
            continue
        if isinstance(end, bool) or not isinstance(end, int):
            msg = f"Interval {i} end coordinate cannot be {type(end).__name__}: {end!r}"
            if strict:
                raise TypeError(msg)
            errors.append(msg)
            continue

        if start < 0 or end > LIMIT64 or start >= end:
            msg = f"Interval {i} [{start}, {end}) out of bounds [0, 2^64) or start >= end"
            if strict:
                raise ValueError(msg)
            errors.append(msg)
            continue

        validated_intervals.append((start, end))

    if errors:
        return False, errors

    # Sort by start index
    sorted_intervals = sorted(validated_intervals, key=lambda x: x[0])

    for i in range(1, len(sorted_intervals)):
        prev_start, prev_end = sorted_intervals[i - 1]
        start, end = sorted_intervals[i]
        if start < prev_end:
            msg = f"Collision/Overlap detected: [{prev_start}, {prev_end}) overlaps with [{start}, {end})"
            if strict:
                raise ValueError(msg)
            errors.append(msg)

    return len(errors) == 0, errors


def union_coverage(intervals: List[Tuple[int, int]]) -> int:
    """Compute formal interval union coverage matching scripts/merge_runs.py.

    Rejects invalid types, booleans, negative coordinates, or out-of-bound intervals.
    """
    if not intervals:
        return 0

    for i, item in enumerate(intervals):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TypeError(f"Interval {i} is not a 2-tuple: {item!r}")
        start, end = item
        _validate_int(start, f"Interval {i} start", min_val=0, max_val=LIMIT64)
        _validate_int(end, f"Interval {i} end", min_val=0, max_val=LIMIT64)
        if start > end:
            raise ValueError(f"Interval {i} start ({start}) exceeds end ({end})")

    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: List[Tuple[int, int]] = []
    for start, end in sorted_intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum(end - start for start, end in merged)


def estimate_storage_bytes(
    count: int,
    retention: str = "survivors",
    batch_size: int = 4096,
    projected_bytes_per_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Estimate physical disk footprint aligned with src/seed_search/realm/resources.py rules.

    Aligns conservative policy projections with resources.disk_policy:
    - Compact ('survivors') defaults to 32 projected bytes/input.
    - Full ('full') defaults to 65,536 projected bytes/input.

    Separates conservative policy projections from detailed analytical models.
    """
    _validate_int(count, "count", min_val=0, max_val=LIMIT64)
    _validate_int(batch_size, "batch_size", min_val=1)

    if retention not in ("survivors", "full"):
        raise ValueError(f"Unsupported retention mode: {retention!r}. Must be 'survivors' or 'full'.")

    # Align with resources.disk_policy defaults
    if projected_bytes_per_seed is None:
        rate = 32 if retention == "survivors" else 65536
    else:
        rate = _validate_int(projected_bytes_per_seed, "projected_bytes_per_seed", min_val=1)

    # Conservative policy projection (resources.disk_policy contract)
    projected_bytes = count * rate
    projected_gib = projected_bytes / (1 << 30)
    projected_mb = projected_bytes / (1024 * 1024)

    # Analytical / measured usage model (separated from conservative policy projection)
    if count == 0:
        analytical_bytes = 0
    elif retention == "full":
        data_bytes = count * 65536
        wal_bytes = 128 * (1024 * 1024)
        analytical_bytes = data_bytes + wal_bytes
    else:
        num_batches = math.ceil(count / batch_size)
        receipt_bytes = num_batches * 128
        range_bytes = num_batches * 64
        expected_survivors = math.ceil(count * 0.00005)
        candidate_bytes = expected_survivors * 1536
        wal_bytes = 128 * (1024 * 1024)
        analytical_bytes = receipt_bytes + range_bytes + candidate_bytes + wal_bytes

    analytical_gib = analytical_bytes / (1 << 30)
    analytical_mb = analytical_bytes / (1024 * 1024)

    return {
        "count": count,
        "retention": retention,
        "batch_size": batch_size,
        "projected_bytes_per_seed": rate,
        "projected_bytes": projected_bytes,
        "projected_gib": projected_gib,
        "projected_mb": projected_mb,
        "analytical_bytes": analytical_bytes,
        "analytical_gib": analytical_gib,
        "analytical_mb": analytical_mb,
        # Default total_bytes / total_mb / total_gib for backward compatibility
        "total_bytes": projected_bytes,
        "total_gib": projected_gib,
        "total_mb": projected_mb,
    }


def generate_shards(
    total_seeds: int,
    shard_size: int,
    start_offset: int = 0,
    node_prefix: str = "node",
    output_prefix: str = "runs/shard",
    policy: str = "dynamic-envelope-1664-v1",
    run_key: str = "0",
) -> List[ShardSpec]:
    """Partition total_seeds into disjoint ShardSpecs.

    Validates:
    - total_seeds: strict non-negative int within [0, 2^64]
    - shard_size: strict positive int (shard_size > 0)
    - start_offset: strict non-negative int
    - start_offset + total_seeds <= 2^64

    Guards all loops against infinite iteration.
    """
    _validate_int(total_seeds, "total_seeds", min_val=0, max_val=LIMIT64)
    validate_shard_size(shard_size)
    validate_range(start_offset, total_seeds)
    if isinstance(node_prefix, bool) or not isinstance(node_prefix, str):
        raise TypeError("node_prefix must be a string")
    if isinstance(output_prefix, bool) or not isinstance(output_prefix, str):
        raise TypeError("output_prefix must be a string")
    if isinstance(policy, bool) or not isinstance(policy, str):
        raise TypeError("policy must be a string")
    if isinstance(run_key, bool) or not isinstance(run_key, (str, int)):
        raise TypeError("run_key must be a string or integer")

    if (total_seeds+shard_size-1)//shard_size>100000:
        raise ValueError('More than 100000 shards requested; increase shard_size')
    shards: List[ShardSpec] = []
    current = start_offset
    remaining = total_seeds
    shard_idx = 0

    while remaining > 0:
        count = min(remaining, shard_size)
        # Explicit guard against non-positive count to prevent infinite loops
        if count <= 0:
            raise ValueError(f"Shard count calculation resulted in non-positive value: {count}")
        spec = ShardSpec(
            shard_id=shard_idx + 1,
            name=f"shard-{shard_idx + 1:04d}",
            start_index=current,
            count=count,
            end_index=current + count,
            node_id=f"{node_prefix}-{(shard_idx % 6) + 1:02d}",
            output_dir=f"{output_prefix}-{shard_idx + 1:04d}",
            policy=policy,
            run_key=str(run_key),
        )
        shards.append(spec)
        current += count
        remaining -= count
        shard_idx += 1

    return shards


def emit_cli_commands(
    shards: List[ShardSpec],
    native_build: str = "runs/node-native-1664",
    threads: int = 16,
    batch_size: int = 4096,
    max_misses: int = 2,
    policy: str = "dynamic-envelope-1664-v1",
    run_key: str = "0",
) -> str:
    """Generate exact bash commands to run the allocated shards.

    Emits --config arguments with explicit search.run_key in per-shard YAML,
    with disjoint half-open ranges [start, start + count).
    """
    _validate_int(threads, "threads", min_val=1, max_val=34)
    _validate_int(batch_size, "batch_size", min_val=1, max_val=16384)
    _validate_int(max_misses, "max_misses", min_val=0)
    if isinstance(policy, bool) or not isinstance(policy, str) or not policy.strip():
        raise TypeError("policy must be a non-empty string")
    if isinstance(run_key, bool) or not isinstance(run_key, (str, int)):
        raise TypeError("run_key must be a string or integer")

    policy_files={'dynamic-envelope-1664-v1':'config/realm_1664.yaml',
        'origin-fixed-2048-two-group-marine-v3':'config/realm_2048_marine.yaml',
        'origin-fixed-2048-two-group-v2':'config/realm_2048_two_group.yaml'}
    lines=["#!/usr/bin/env bash", "# Generate explicit shard YAMLs, then launch finite prediction scans.", "set -euo pipefail"]
    initializer=("import sys,yaml;from pathlib import Path;from seed_search.realm.config import validate_config;"
        "cfg=yaml.safe_load(Path(sys.argv[1]).read_text());cfg['search']['run_key']=sys.argv[2];"
        "cfg['search']['max_misses']=int(sys.argv[3]);validate_config(cfg);"
        "p=Path(sys.argv[4]);p.parent.mkdir(parents=True,exist_ok=True);"
        "p.write_text(yaml.safe_dump(cfg,sort_keys=False))")
    for shard in shards:
        if not isinstance(shard,ShardSpec):raise TypeError('Expected ShardSpec')
        chosen=shard.policy or policy
        source=policy_files.get(chosen,chosen)
        if not source.endswith(('.yaml','.yml')):raise ValueError('Policy must name a supported revision or YAML path')
        key=str(shard.run_key if shard.run_key is not None else run_key)
        if not key.isdigit() or not 0<=int(key)<LIMIT64:raise ValueError('run_key must be a decimal uint64')
        filename=shard.output_dir+'.policy.yaml'
        label=f'{shard.name} on {shard.node_id} (Range: [{shard.start_index:,}, {shard.end_index:,}))'
        lines.append('# '+label.replace('\n',' ').replace('\r',' '))
        lines.append(shlex.join(['python','-c',initializer,source,key,str(max_misses),filename]))
        lines.append(shlex.join(['python','-m','seed_search','--config',filename,'scan',
            '--executor','native','--native-build',native_build,'--native-threads',str(threads),
            '--native-batch-size',str(batch_size),'--retention','survivors','--max-misses',str(max_misses),
            '--prediction-scale','--start-index',str(shard.start_index),'--count',str(shard.count),'--output',shard.output_dir]))
    return "\n".join(lines)+"\n"


def generate_validation_plan_schedule(
    base_start: int = 50_000,
    pair_count: int = 100_000,
    num_pairs: int = 5,
) -> List[dict]:
    """Generate the schedule for the 5-pair counterbalanced validation experiment."""
    _validate_int(base_start, "base_start", min_val=0, max_val=LIMIT64)
    _validate_int(pair_count, "pair_count", min_val=1, max_val=LIMIT64)
    _validate_int(num_pairs, "num_pairs", min_val=1, max_val=1000)
    validate_range(base_start, pair_count * num_pairs)

    schedule = []
    for pair_idx in range(num_pairs):
        interval_start = base_start + pair_idx * pair_count
        interval_end = interval_start + pair_count
        # Counterbalanced ordering: Even pairs Control -> Selected; Odd pairs Selected -> Control
        order = ["control", "selected"] if pair_idx % 2 == 0 else ["selected", "control"]
        schedule.append({
            "pair": pair_idx + 1,
            "interval": [interval_start, interval_end],
            "count": pair_count,
            "execution_order": order,
            "arms": {
                "control": {
                    "threads": 16,
                    "batch_size": 4096,
                    "output": f"runs/val-pair-{pair_idx + 1}-control",
                },
                "selected": {
                    "threads": "TBD (Tuner Winner <= 34)",
                    "batch_size": "TBD (4096 or 8192)",
                    "output": f"runs/val-pair-{pair_idx + 1}-selected",
                },
            },
        })
    return schedule


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: allocate
    p_alloc = subparsers.add_parser("allocate", help="Allocate disjoint shards for a distributed sweep")
    p_alloc.add_argument("--total-seeds", type=int, default=100_000_000, help="Total seeds to sweep (default: 100M)")
    p_alloc.add_argument("--shard-size", type=int, default=10_000_000, help="Seeds per shard (default: 10M)")
    p_alloc.add_argument("--start-offset", type=int, default=0, help="Starting index offset (default: 0)")
    p_alloc.add_argument("--policy", default="dynamic-envelope-1664-v1", help="Target search policy (default: dynamic-envelope-1664-v1)")
    p_alloc.add_argument("--run-key", default="0", help="Run key invariant (default: '0')")
    p_alloc.add_argument("--emit-script", action="store_true", help="Print shell commands")

    # Subcommand: preflight
    p_pref = subparsers.add_parser("preflight", help="Calculate disk and memory requirements")
    p_pref.add_argument("--count", type=int, default=10_000_000, help="Seed count to evaluate")
    p_pref.add_argument("--retention", choices=["survivors", "full"], default="survivors")
    p_pref.add_argument("--batch-size", type=int, default=4096, help="Batch size (default: 4096)")

    # Subcommand: validation-plan
    subparsers.add_parser("validation-plan", help="Display the 5-pair counterbalanced validation plan")

    args = parser.parse_args()

    if args.command == "allocate":
        shards = generate_shards(
            args.total_seeds,
            args.shard_size,
            args.start_offset,
            policy=args.policy,
            run_key=args.run_key,
        )
        intervals = [(s.start_index, s.end_index) for s in shards]
        is_valid, errors = validate_intervals(intervals)
        cov = union_coverage(intervals)

        print(f"=======================================================")
        print(f"  SHARD ALLOCATION REPORT: {args.total_seeds:,} Seeds")
        print(f"=======================================================")
        print(f"Target Policy   : {args.policy}")
        print(f"Run Key         : {args.run_key}")
        print(f"Total Shards    : {len(shards)}")
        print(f"Shard Size      : {args.shard_size:,} seeds")
        print(f"Disjoint Check  : {'PASS (Mutually Disjoint)' if is_valid else 'FAIL'}")
        print(f"Union Coverage  : {cov:,} seeds (Expected: {args.total_seeds:,})")
        print(f"=======================================================\n")

        if not is_valid:
            print("Errors detected:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

        for s in shards:
            est = estimate_storage_bytes(s.count, "survivors")
            print(
                f"  [{s.name}] Node: {s.node_id} | Range: [{s.start_index:>12,}, {s.end_index:>12,}) | "
                f"Policy Proj: {est['projected_mb']:.1f} MB | Analytical: {est['analytical_mb']:.1f} MB"
            )

        if args.emit_script:
            print("\n" + "=" * 55)
            print("  BASH LAUNCH SCRIPT")
            print("=" * 55)
            print(emit_cli_commands(shards, policy=args.policy, run_key=args.run_key))

    elif args.command == "preflight":
        surv_est = estimate_storage_bytes(args.count, "survivors", batch_size=args.batch_size)
        full_est = estimate_storage_bytes(args.count, "full", batch_size=args.batch_size)
        print(f"=======================================================")
        print(f"  STORAGE PREFLIGHT ESTIMATE: {args.count:,} Seeds")
        print(f"=======================================================")
        print(f"Compact Mode (survivors, B=2):")
        print(f"  Policy Projection (32 B/seed)   : {surv_est['projected_mb']:.1f} MB ({surv_est['projected_gib']:.3f} GiB)")
        print(f"  Detailed Analytical Model       : {surv_est['analytical_mb']:.1f} MB ({surv_est['analytical_gib']:.3f} GiB)")
        print(f"Full Retention Mode:")
        print(f"  Policy Projection (64 KiB/seed) : {full_est['projected_gib']:.2f} GiB ({full_est['projected_mb']:.1f} MB)")
        print(f"  Detailed Analytical Model       : {full_est['analytical_gib']:.2f} GiB ({full_est['analytical_mb']:.1f} MB)")
        print(f"\nResource Limits (from src/seed_search/realm/resources.py):")
        print(f"  Free Disk Reserve Required: 16.000 GiB (17,179,869,184 bytes)")
        print(f"  Run Disk Limit Cap        : 128.000 GiB (137,438,953,472 bytes)")
        print(f"=======================================================")

    elif args.command == "validation-plan":
        plan = generate_validation_plan_schedule()
        print(f"=======================================================")
        print(f"  5-PAIR COUNTERBALANCED VALIDATION SCHEDULE")
        print(f"  Target: Held-Out Range [50,000, 550,000) (500k Seeds)")
        print(f"=======================================================")
        print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
