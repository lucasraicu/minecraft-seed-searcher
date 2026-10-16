"""Tests for scripts/shard_campaign.py cluster sharding and campaign management."""
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.shard_campaign import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TOTAL_SEEDS,
    DEFAULT_32BIT_SEEDS,
    LIMIT32,
    ShardSpec,
    build_merge_command,
    generate_scripts,
    partition_campaign,
    run_self_tests,
    validate_partition,
)

ROOT = Path(__file__).resolve().parents[1]


def test_partition_default_36b_4nodes():
    shards = partition_campaign(total_seeds=36_000_000_000, nodes=4, chunk_size=100_000_000)
    assert len(shards) == 4
    for i in range(4):
        assert shards[i].node_id == i
        assert shards[i].start_index == i * 9_000_000_000
        assert shards[i].end_index == (i + 1) * 9_000_000_000
        assert shards[i].count == 9_000_000_000
        assert shards[i].chunks == 90
        assert shards[i].output_dir == f"runs/campaign_shard_{i}"
        assert f"--start-index {i * 9_000_000_000}" in shards[i].cli_command
        assert "--count 9000000000" in shards[i].cli_command

    valid, errors = validate_partition(shards, 36_000_000_000)
    assert valid, f"Validation errors: {errors}"
    assert len(errors) == 0


def test_partition_360_nodes_one_chunk_each():
    shards = partition_campaign(total_seeds=36_000_000_000, nodes=360, chunk_size=100_000_000)
    assert len(shards) == 360
    for i in range(360):
        assert shards[i].node_id == i
        assert shards[i].start_index == i * 100_000_000
        assert shards[i].end_index == (i + 1) * 100_000_000
        assert shards[i].count == 100_000_000
        assert shards[i].chunks == 1

    valid, errors = validate_partition(shards, 36_000_000_000)
    assert valid, f"Validation errors: {errors}"


def test_validation_detects_gap_and_overlap():
    shards = partition_campaign(total_seeds=1_000_000, nodes=2, chunk_size=100_000)
    valid, errors = validate_partition(shards, 1_000_000)
    assert valid

    # Inject a gap: second shard starts at 600,000 instead of 500,000
    gap_shards = [
        shards[0],
        ShardSpec(
            node_id=1, nodes=2, start_index=600_000, end_index=1_000_000,
            count=400_000, chunks=4, output_dir="runs/test_1", threads=34, config="config/realm_1664.yaml"
        ),
    ]
    valid_gap, gap_errors = validate_partition(gap_shards, 1_000_000)
    assert not valid_gap
    assert any("Gap detected" in e for e in gap_errors)

    # Inject an overlap: second shard starts at 400,000 instead of 500,000
    overlap_shards = [
        shards[0],
        ShardSpec(
            node_id=1, nodes=2, start_index=400_000, end_index=1_000_000,
            count=600_000, chunks=6, output_dir="runs/test_1", threads=34, config="config/realm_1664.yaml"
        ),
    ]
    valid_overlap, overlap_errors = validate_partition(overlap_shards, 1_000_000)
    assert not valid_overlap
    assert any("Overlap detected" in e for e in overlap_errors)


def test_generate_scripts(tmp_path):
    shards = partition_campaign(total_seeds=400_000_000, nodes=4, chunk_size=100_000_000)
    paths = generate_scripts(shards, target_dir=tmp_path)
    assert len(paths) == 4
    for i, p in enumerate(paths):
        assert p.is_file()
        assert p.name == f"run_shard_{i}.sh"
        assert p.stat().st_mode & 0o111  # Executable
        content = p.read_text()
        assert f"--start-index {i * 100_000_000}" in content
        assert "--count 100000000" in content
        assert f"--output \"runs/campaign_shard_{i}\"" in content


def test_merge_command():
    shards = partition_campaign(total_seeds=400_000_000, nodes=2, chunk_size=100_000_000)
    cmd = build_merge_command(shards, master_output="runs/master_test")
    assert "python scripts/merge_runs.py" in cmd
    assert "runs/campaign_shard_0/realm.sqlite" in cmd
    assert "runs/campaign_shard_1/realm.sqlite" in cmd
    assert "--output runs/master_test" in cmd


def test_cli_validate():
    proc = subprocess.run([sys.executable, "scripts/shard_campaign.py", "--validate"], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "ALL MATHEMATICAL SELF-TESTS PASSED" in proc.stdout


def test_cli_generate_scripts(tmp_path):
    proc = subprocess.run([
        sys.executable, "scripts/shard_campaign.py",
        "--nodes", "4",
        "--total-seeds", "36000000000",
        "--generate-scripts",
        "--scripts-dir", str(tmp_path),
    ], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0
    assert (tmp_path / "run_shard_0.sh").is_file()
    assert (tmp_path / "run_shard_3.sh").is_file()


def test_partition_strided_full_32bit_4nodes():
    shards = partition_campaign(nodes=4, sequence="strided", low32=12345, chunk_size=100_000_000)
    assert len(shards) == 4
    assert sum(s.count for s in shards) == LIMIT32
    assert shards[0].start_index == 0
    assert shards[0].end_index == 1_100_000_000
    assert shards[0].count == 1_100_000_000
    assert shards[0].chunks == 11
    assert shards[3].end_index == LIMIT32
    assert shards[3].count == 994_967_296
    assert shards[3].chunks == 10

    for s in shards:
        assert s.sequence == "strided"
        assert s.low32 == 12345
        assert "--sequence strided" in s.cli_command
        assert "--low32 12345" in s.cli_command

    valid, errors = validate_partition(shards, LIMIT32)
    assert valid, f"Validation errors: {errors}"
    assert len(errors) == 0


def test_partition_strided_custom_subspace():
    total = 1_000_000
    shards = partition_campaign(
        total_seeds=total, nodes=3, chunk_size=50_000,
        sequence="strided", low32=0xDEADBEEF,
    )
    assert len(shards) == 3
    assert sum(s.count for s in shards) == total
    valid, errors = validate_partition(shards, total)
    assert valid, f"Validation errors: {errors}"
    assert len(errors) == 0


def test_partition_strided_exceeds_bounds_rejected():
    with pytest.raises(ValueError, match="exceeds 32-bit bounds"):
        partition_campaign(total_seeds=LIMIT32 + 1, sequence="strided")

    with pytest.raises(ValueError, match="exceeds 32-bit bounds"):
        partition_campaign(total_seeds=10, start_offset=LIMIT32, sequence="strided")


def test_cli_validate_strided():
    proc = subprocess.run(
        [sys.executable, "scripts/shard_campaign.py", "--validate", "--sequence", "strided", "--low32", "12345"],
        cwd=ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert "ALL MATHEMATICAL SELF-TESTS PASSED" in proc.stdout
    assert "Custom CLI configuration: 4 nodes, 4,294,967,296 seeds (strided)" in proc.stdout


def test_cli_generate_scripts_strided(tmp_path):
    proc = subprocess.run([
        sys.executable, "scripts/shard_campaign.py",
        "--nodes", "2",
        "--sequence", "strided",
        "--low32", "4294967295",
        "--total-seeds", "2000000",
        "--generate-scripts",
        "--scripts-dir", str(tmp_path),
    ], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0
    s0 = tmp_path / "run_shard_0.sh"
    s1 = tmp_path / "run_shard_1.sh"
    assert s0.is_file()
    assert s1.is_file()
    c0 = s0.read_text()
    assert "--sequence strided" in c0
    assert "--low32 4294967295" in c0
    assert "--start-index 0" in c0
    assert "--count 1000000" in c0

