#!/usr/bin/env python3
"""Multi-Node Cluster Sharding and Campaign Partitioning Tool.

Partitions large seed campaigns (e.g. 36 Billion seeds) across N cluster nodes,
allocates disjoint non-overlapping seed index ranges aligned to chunk boundaries,
generates executable node runner shell scripts, and produces merge commands for
scripts/merge_runs.py.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import List, Optional, Tuple
import shlex

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

LIMIT64: int = 1 << 64
DEFAULT_TOTAL_SEEDS: int = 36_000_000_000
DEFAULT_CHUNK_SIZE: int = 100_000_000
DEFAULT_THREADS: int = 34
DEFAULT_NODES: int = 4
DEFAULT_OUTPUT_DIR: str = "runs/campaign_shard_{node_id}"
DEFAULT_CONFIG: str = "config/realm.yaml"


def campaign_budget(config: str, override: Optional[int] = None) -> int:
    from seed_search.realm.cli import load
    from seed_search.realm.config import validate_config
    cfg = load(config)
    budget = cfg['search']['max_misses'] if override is None else override
    cfg['search']['max_misses'] = budget
    validate_config(cfg)
    return budget


@dataclass(frozen=True)
class ShardSpec:
    node_id: int
    nodes: int
    start_index: int
    end_index: int
    count: int
    chunks: int
    output_dir: str
    threads: int
    config: str
    batch_size: int = 4096
    max_misses: Optional[int] = None

    def __post_init__(self):
        if self.max_misses is None:
            object.__setattr__(self, 'max_misses', campaign_budget(self.config))

    @property
    def cli_command(self) -> str:
        return (
            f"python -m seed_search --config {shlex.quote(self.config)} scan \\\n"
            f"  --executor native \\\n"
            f"  --native-threads {self.threads} \\\n"
            f"  --native-batch-size {self.batch_size} \\\n"
            f"  --retention survivors \\\n"
            f"  --max-misses {self.max_misses} \\\n"
            f"  --prediction-scale \\\n"
            f"  --start-index {self.start_index} \\\n"
            f"  --count {self.count} \\\n"
            f"  --output {shlex.quote(self.output_dir)}"
        )

    def render_script(self) -> str:
        return f"""#!/usr/bin/env bash
# ==============================================================================
# Minecraft Seed Searcher - Campaign Shard {self.node_id} of {self.nodes}
# Seed Index Range: [{self.start_index:,}, {self.end_index:,})
# Total Seeds: {self.count:,} ({self.chunks} chunk{'s' if self.chunks != 1 else ''})
# Output Directory: {self.output_dir}
# OpenMP Threads: {self.threads}
# ==============================================================================
set -euo pipefail

# Locate python binary (prefer .venv if present)
if [[ -z "${{PYTHON:-}}" ]]; then
  if [[ -f ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python"
  fi
fi

echo "=============================================================================="
echo "Starting Campaign Shard {self.node_id}/{self.nodes}"
echo "Seed Range: [{self.start_index:,}, {self.end_index:,}) ({self.count:,} seeds)"
echo "Output: {self.output_dir}"
echo "Threads: {self.threads}"
echo "=============================================================================="

mkdir -p {shlex.quote(self.output_dir)}

"$PYTHON" -m seed_search --config {shlex.quote(self.config)} scan \\
  --executor native \\
  --native-threads {self.threads} \\
  --native-batch-size {self.batch_size} \\
  --retention survivors \\
  --max-misses {self.max_misses} \\
  --prediction-scale \\
  --start-index {self.start_index} \\
  --count {self.count} \\
  --output "{self.output_dir}"

echo "=============================================================================="
echo "Shard {self.node_id} scan finished successfully."
echo "Checkpoint database: {self.output_dir}/realm.sqlite"
echo "=============================================================================="
"""


def partition_campaign(
    total_seeds: int = DEFAULT_TOTAL_SEEDS,
    nodes: int = DEFAULT_NODES,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    threads: int = DEFAULT_THREADS,
    output_dir_pattern: str = DEFAULT_OUTPUT_DIR,
    config: str = DEFAULT_CONFIG,
    batch_size: int = 4096,
    max_misses: Optional[int] = None,
    start_offset: int = 0,
) -> List[ShardSpec]:
    max_misses = campaign_budget(config, max_misses)
    if nodes <= 0:
        raise ValueError(f"Nodes must be >= 1, got {nodes}")
    if total_seeds < 0:
        raise ValueError(f"total_seeds must be >= 0, got {total_seeds}")
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
    if start_offset < 0 or start_offset + total_seeds > LIMIT64:
        raise ValueError(f"Campaign range [{start_offset}, {start_offset + total_seeds}) exceeds 64-bit bounds [0, 2^64)")

    if total_seeds == 0:
        shards = []
        for i in range(nodes):
            out = output_dir_pattern.format(node_id=i) if "{node_id}" in output_dir_pattern else f"{output_dir_pattern}_{i}"
            shards.append(ShardSpec(
                node_id=i, nodes=nodes, start_index=start_offset, end_index=start_offset,
                count=0, chunks=0, output_dir=out, threads=threads, config=config,
                batch_size=batch_size, max_misses=max_misses,
            ))
        return shards

    total_chunks = (total_seeds + chunk_size - 1) // chunk_size

    shards: List[ShardSpec] = []
    if total_chunks >= nodes:
        base_chunks = total_chunks // nodes
        rem_chunks = total_chunks % nodes
        
        current_chunk = 0
        for i in range(nodes):
            num_chunks = base_chunks + (1 if i < rem_chunks else 0)
            chunk_start = current_chunk
            chunk_end = current_chunk + num_chunks
            
            node_start = start_offset + chunk_start * chunk_size
            node_end = min(start_offset + chunk_end * chunk_size, start_offset + total_seeds)
            if num_chunks == 0:
                node_end = node_start
            node_count = node_end - node_start
            
            out = output_dir_pattern.format(node_id=i) if "{node_id}" in output_dir_pattern else f"{output_dir_pattern}_{i}"
            shards.append(ShardSpec(
                node_id=i, nodes=nodes, start_index=node_start, end_index=node_end,
                count=node_count, chunks=num_chunks, output_dir=out, threads=threads,
                config=config, batch_size=batch_size, max_misses=max_misses,
            ))
            current_chunk = chunk_end
    else:
        base_seeds = total_seeds // nodes
        rem_seeds = total_seeds % nodes
        
        current_seed = start_offset
        for i in range(nodes):
            node_count = base_seeds + (1 if i < rem_seeds else 0)
            node_start = current_seed
            node_end = current_seed + node_count
            num_chunks = (node_count + chunk_size - 1) // chunk_size if node_count > 0 else 0
            
            out = output_dir_pattern.format(node_id=i) if "{node_id}" in output_dir_pattern else f"{output_dir_pattern}_{i}"
            shards.append(ShardSpec(
                node_id=i, nodes=nodes, start_index=node_start, end_index=node_end,
                count=node_count, chunks=num_chunks, output_dir=out, threads=threads,
                config=config, batch_size=batch_size, max_misses=max_misses,
            ))
            current_seed = node_end

    return shards


def validate_partition(shards: List[ShardSpec], total_seeds: int, start_offset: int = 0) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not shards:
        if total_seeds > 0:
            errors.append(f"No shards allocated for total_seeds={total_seeds}")
        return len(errors) == 0, errors

    expected_start = start_offset
    total_coverage = 0

    intervals: List[Tuple[int, int]] = []
    for s in shards:
        if s.start_index < 0 or s.end_index > LIMIT64:
            errors.append(f"Shard {s.node_id} range [{s.start_index}, {s.end_index}) out of bounds")
        if s.end_index < s.start_index:
            errors.append(f"Shard {s.node_id} end ({s.end_index}) < start ({s.start_index})")
        if s.count != (s.end_index - s.start_index):
            errors.append(f"Shard {s.node_id} count ({s.count}) != end - start ({s.end_index - s.start_index})")

        # Check continuity: shard i must start exactly where shard i-1 ended
        if s.start_index != expected_start:
            if s.start_index > expected_start:
                errors.append(f"Gap detected between {expected_start} and {s.start_index} (before shard {s.node_id})")
            else:
                errors.append(f"Overlap detected between {s.start_index} and {expected_start} (at shard {s.node_id})")

        expected_start = s.end_index
        total_coverage += s.count
        if s.count > 0:
            intervals.append((s.start_index, s.end_index))

    if expected_start != start_offset + total_seeds:
        errors.append(f"Final end {expected_start} does not match expected {start_offset + total_seeds}")

    if total_coverage != total_seeds:
        errors.append(f"Sum of shard counts ({total_coverage}) != total_seeds ({total_seeds})")

    # Pairwise disjointness check
    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            s1, e1 = intervals[i]
            s2, e2 = intervals[j]
            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            if overlap_start < overlap_end:
                errors.append(f"Intervals [{s1}, {e1}) and [{s2}, {e2}) overlap in [{overlap_start}, {overlap_end})")

    # Formal interval union verification matching scripts/merge_runs.py
    try:
        from scripts.merge_runs import union_intervals, compute_interval_coverage
        if intervals:
            merged = union_intervals(intervals)
            if len(merged) != 1 or merged[0] != (start_offset, start_offset + total_seeds):
                errors.append(f"union_intervals returned {merged}, expected [({start_offset}, {start_offset + total_seeds})]")
            cov = compute_interval_coverage(intervals)
            if cov != total_seeds:
                errors.append(f"compute_interval_coverage returned {cov}, expected {total_seeds}")
    except Exception as exc:
        errors.append(f"Failed to run merge_runs union validation: {exc}")

    return len(errors) == 0, errors


def run_self_tests() -> bool:
    test_cases = [
        ("Default 36B Campaign (4 nodes, 100M chunks)", 36_000_000_000, 4, 100_000_000),
        ("8-Node Cluster (36B seeds, 100M chunks)", 36_000_000_000, 8, 100_000_000),
        ("16-Node Cluster (36B seeds, 100M chunks)", 36_000_000_000, 16, 100_000_000),
        ("32-Node Cluster (36B seeds, 100M chunks)", 36_000_000_000, 32, 100_000_000),
        ("64-Node Cluster (36B seeds, 100M chunks)", 36_000_000_000, 64, 100_000_000),
        ("360-Node Cluster (1 chunk of 100M seeds each)", 36_000_000_000, 360, 100_000_000),
        ("Single Node Campaign (36B seeds)", 36_000_000_000, 1, 100_000_000),
        ("Odd Prime Seed Count (1,000,000,007 seeds, 7 nodes, 10M chunks)", 1_000_000_007, 7, 10_000_000),
        ("Non-Divisible Seeds (1,234,567 seeds, 3 nodes, 50,000 chunks)", 1_234_567, 3, 50_000),
        ("Fewer Chunks than Nodes (250 seeds, 5 nodes, 100 chunks)", 250, 5, 100),
        ("Small Campaign (10 seeds, 3 nodes, 2 chunks)", 10, 3, 2),
        ("Single Seed Campaign (1 seed, 4 nodes, 1 chunk)", 1, 4, 1),
        ("Zero Seeds Campaign (0 seeds, 4 nodes, 100M chunks)", 0, 4, 100_000_000),
    ]

    all_passed = True
    print("=" * 80)
    print("RUNNING MATHEMATICAL CLUSTER SHARDING SELF-TESTS")
    print("=" * 80)

    for name, total, nodes, chunk in test_cases:
        shards = partition_campaign(total_seeds=total, nodes=nodes, chunk_size=chunk)
        valid, errors = validate_partition(shards, total)
        if valid:
            print(f"[PASS] {name:<60} | Coverage: {total:,} | Gaps: 0 | Overlaps: 0")
        else:
            all_passed = False
            print(f"[FAIL] {name}")
            for err in errors:
                print(f"       ERROR: {err}")

    print("=" * 80)
    if all_passed:
        print("ALL MATHEMATICAL SELF-TESTS PASSED (0 gaps, 0 overlaps, 100% domain coverage)")
    else:
        print("SELF-TESTS FAILED!")
    print("=" * 80)
    return all_passed


def generate_scripts(
    shards: List[ShardSpec],
    target_dir: Path = Path("."),
    node_id: Optional[int] = None,
) -> List[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    
    selected_shards = shards if node_id is None else [s for s in shards if s.node_id == node_id]
    if node_id is not None and not selected_shards:
        raise ValueError(f"No shard found matching node_id={node_id}")

    for s in selected_shards:
        script_path = target_dir / f"run_shard_{s.node_id}.sh"
        script_path.write_text(s.render_script())
        os.chmod(script_path, 0o755)
        generated.append(script_path)
    return generated


def build_merge_command(
    shards: List[ShardSpec],
    master_output: str = "runs/campaign_master",
    multiline: bool = False,
) -> str:
    inputs = [f"{s.output_dir}/realm.sqlite" for s in shards]
    if multiline:
        formatted_inputs = " \\\n    ".join(inputs)
        return (
            f"python scripts/merge_runs.py \\\n"
            f"  --inputs \\\n"
            f"    {formatted_inputs} \\\n"
            f"  --output {master_output}"
        )
    return f"python scripts/merge_runs.py --inputs {' '.join(inputs)} --output {master_output}"


def main():
    parser = argparse.ArgumentParser(
        description="Partition large seed campaigns across multi-node clusters and generate runner scripts."
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=DEFAULT_NODES,
        help=f"Number of cluster nodes (default: {DEFAULT_NODES})",
    )
    parser.add_argument(
        "--node-id",
        type=int,
        default=None,
        help="Specific node ID (0 to N-1) to run or generate for (default: all nodes)",
    )
    parser.add_argument(
        "--total-seeds",
        type=int,
        default=DEFAULT_TOTAL_SEEDS,
        help=f"Total seeds in campaign (default: {DEFAULT_TOTAL_SEEDS:,})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size in seeds (default: {DEFAULT_CHUNK_SIZE:,})",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help=f"OpenMP threads per node (default: {DEFAULT_THREADS})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Base runs directory pattern (default: '{DEFAULT_OUTPUT_DIR}')",
    )
    parser.add_argument(
        "--generate-scripts",
        action="store_true",
        help="Generate executable shell scripts (run_shard_{node_id}.sh) for all nodes with the exact CLI sweep command.",
    )
    parser.add_argument(
        "--merge-command",
        action="store_true",
        help="Print the exact python scripts/merge_runs.py command to aggregate all node outputs into a single master leaderboard.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run built-in mathematical self-tests verifying that the union of all node shards covers [0, total_seeds) with 0 overlap and 0 gaps.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG,
        help=f"Seed search policy YAML configuration (default: '{DEFAULT_CONFIG}')",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4096,
        help="Native batch size (default: 4096)",
    )
    parser.add_argument(
        "--max-misses",
        type=int,
        default=None,
        help="Override the configured deficit budget (default: resolved policy value)",
    )
    parser.add_argument(
        "--master-output",
        type=str,
        default="runs/campaign_master",
        help="Master aggregated leaderboard output directory (default: 'runs/campaign_master')",
    )
    parser.add_argument(
        "--scripts-dir",
        type=Path,
        default=Path("."),
        help="Destination directory for generated shell scripts (default: current directory)",
    )

    args = parser.parse_args()

    if args.validate:
        success = run_self_tests()
        if not success:
            sys.exit(1)
        # If custom parameters were provided, also validate that specific partitioning
        if (args.nodes != DEFAULT_NODES or
            args.total_seeds != DEFAULT_TOTAL_SEEDS or
            args.chunk_size != DEFAULT_CHUNK_SIZE):
            custom_shards = partition_campaign(
                total_seeds=args.total_seeds,
                nodes=args.nodes,
                chunk_size=args.chunk_size,
                threads=args.threads,
                output_dir_pattern=args.output_dir,
                config=args.config,
                batch_size=args.batch_size,
                max_misses=args.max_misses,
            )
            v, errs = validate_partition(custom_shards, args.total_seeds)
            if v:
                print(f"[PASS] Custom CLI configuration: {args.nodes} nodes, {args.total_seeds:,} seeds, chunk {args.chunk_size:,} -> 0 gaps, 0 overlaps")
            else:
                print(f"[FAIL] Custom CLI configuration validation failed: {errs}")
                sys.exit(1)
        if not args.generate_scripts and not args.merge_command:
            return

    if args.node_id is not None and not (0 <= args.node_id < args.nodes):
        print(f"Error: --node-id must be between 0 and {args.nodes - 1}, got {args.node_id}", file=sys.stderr)
        sys.exit(1)

    shards = partition_campaign(
        total_seeds=args.total_seeds,
        nodes=args.nodes,
        chunk_size=args.chunk_size,
        threads=args.threads,
        output_dir_pattern=args.output_dir,
        config=args.config,
        batch_size=args.batch_size,
        max_misses=args.max_misses,
    )

    valid, errors = validate_partition(shards, args.total_seeds)
    if not valid:
        print("Error: Generated partition failed mathematical validation:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("CLUSTER CAMPAIGN PARTITION SUMMARY")
    print(f"Total Seeds:     {args.total_seeds:,}")
    print(f"Cluster Nodes:   {args.nodes}")
    print(f"Chunk Size:      {args.chunk_size:,} seeds")
    print(f"OpenMP Threads:  {args.threads} per node")
    print(f"Config Policy:   {args.config}")
    print(f"Coverage:        100.0% ([0, {args.total_seeds:,})) | 0 gaps | 0 overlaps")
    print("=" * 80)

    for s in shards:
        if args.node_id is not None and s.node_id != args.node_id:
            continue
        print(f"Node {s.node_id:2d}: Range [{s.start_index:12,}, {s.end_index:12,}) | Seeds: {s.count:12,} ({s.chunks:3d} chunks) -> Output: {s.output_dir}")

    print("=" * 80)

    if args.generate_scripts:
        paths = generate_scripts(shards, target_dir=args.scripts_dir, node_id=args.node_id)
        print(f"Generated {len(paths)} executable runner script(s):")
        for p in paths:
            print(f"  - {p} (chmod +x)")
        print("=" * 80)

    if args.merge_command or not args.generate_scripts:
        print("AGGREGATE MERGE COMMAND:")
        print(build_merge_command(shards, master_output=args.master_output, multiline=True))
        print("=" * 80)


if __name__ == "__main__":
    main()
