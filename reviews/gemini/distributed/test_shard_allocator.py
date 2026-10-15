"""
Unit Test Suite for Distributed Shard Allocator & Capacity Preflight Tool.

Tests all validation guards, boolean rejection, non-integer inputs, zero/negative shard sizes,
negative ranges, 64-bit overflow, while loop safety, disjoint partitioning, CLI command emission,
and storage estimation alignment with resources.disk_policy.

NOTE: As per operational instructions, execution of this suite is deferred to Codex after benchmarking.
"""

import pytest
from SHARD_ALLOCATOR import (
    LIMIT64,
    ShardSpec,
    _validate_int,
    validate_range,
    validate_shard_size,
    validate_intervals,
    union_coverage,
    estimate_storage_bytes,
    generate_shards,
    emit_cli_commands,
    generate_validation_plan_schedule,
)


class TestNumericValidationGuards:
    """Tests for strict integer validation rejecting booleans, floats, None, and strings."""

    @pytest.mark.parametrize("bad_val", [True, False])
    def test_validate_int_rejects_booleans(self, bad_val):
        with pytest.raises(TypeError, match="cannot be a boolean"):
            _validate_int(bad_val, "test_param")

    @pytest.mark.parametrize("bad_val", [12.5, 0.0, -1.5, 1e9, float("inf"), float("nan")])
    def test_validate_int_rejects_floats(self, bad_val):
        with pytest.raises(TypeError, match="must be an integer"):
            _validate_int(bad_val, "test_param")

    @pytest.mark.parametrize("bad_val", [None, "100", "0", [1], {"a": 1}])
    def test_validate_int_rejects_non_integers(self, bad_val):
        with pytest.raises(TypeError, match="must be an integer"):
            _validate_int(bad_val, "test_param")

    def test_validate_int_enforces_bounds(self):
        assert _validate_int(10, "val", min_val=0, max_val=20) == 10
        assert _validate_int(0, "val", min_val=0) == 0
        assert _validate_int(20, "val", max_val=20) == 20

        with pytest.raises(ValueError, match="must be >= 0"):
            _validate_int(-1, "val", min_val=0)

        with pytest.raises(ValueError, match="must be <= 20"):
            _validate_int(21, "val", max_val=20)


class TestRangeAndShardSizeValidation:
    """Tests for validate_range and validate_shard_size guards."""

    @pytest.mark.parametrize("bad_start", [True, False, 1.5, "0", None])
    def test_validate_range_rejects_invalid_start_types(self, bad_start):
        with pytest.raises(TypeError):
            validate_range(bad_start, 100)

    @pytest.mark.parametrize("bad_count", [True, False, 10.5, "100", None])
    def test_validate_range_rejects_invalid_count_types(self, bad_count):
        with pytest.raises(TypeError):
            validate_range(0, bad_count)

    def test_validate_range_rejects_negative_values(self):
        with pytest.raises(ValueError, match="start must be >= 0"):
            validate_range(-1, 100)
        with pytest.raises(ValueError, match="count must be >= 0"):
            validate_range(0, -1)

    def test_validate_range_overflow_64bit(self):
        # Exceeds LIMIT64
        with pytest.raises(ValueError, match="exceeds 64-bit limit"):
            validate_range(LIMIT64, 1)
        with pytest.raises(ValueError, match="exceeds 64-bit limit"):
            validate_range(LIMIT64 - 5, 6)

        # Boundary checks that must pass
        assert validate_range(0, LIMIT64) == (0, LIMIT64)
        assert validate_range(LIMIT64 - 10, 10) == (LIMIT64 - 10, 10)
        assert validate_range(0, 0) == (0, 0)

    @pytest.mark.parametrize("bad_size", [True, False, 10.5, "5000", None])
    def test_validate_shard_size_rejects_invalid_types(self, bad_size):
        with pytest.raises(TypeError):
            validate_shard_size(bad_size)

    @pytest.mark.parametrize("bad_size", [0, -1, -100])
    def test_validate_shard_size_rejects_zero_and_negative(self, bad_size):
        with pytest.raises(ValueError, match="shard_size must be >= 1"):
            validate_shard_size(bad_size)

    def test_validate_shard_size_accepts_positive(self):
        assert validate_shard_size(1) == 1
        assert validate_shard_size(10_000_000) == 10_000_000


class TestShardSpec:
    """Tests for ShardSpec dataclass invariants."""

    def test_shard_spec_valid(self):
        spec = ShardSpec(
            shard_id=1,
            name="shard-0001",
            start_index=0,
            count=1000,
            end_index=1000,
            node_id="node-01",
            output_dir="runs/shard-0001",
            policy="dynamic-envelope-1664-v1",
            run_key="0",
        )
        assert spec.shard_id == 1
        assert spec.start_index == 0
        assert spec.end_index == 1000
        assert spec.count == 1000
        assert spec.policy == "dynamic-envelope-1664-v1"
        assert spec.run_key == "0"
        d = spec.to_dict()
        assert d["shard_id"] == 1
        assert d["start_index"] == 0

    def test_shard_spec_rejects_booleans(self):
        with pytest.raises(TypeError):
            ShardSpec(
                shard_id=True,
                name="shard-0001",
                start_index=0,
                count=1000,
                end_index=1000,
                node_id="node-01",
                output_dir="runs/shard-0001",
            )

    def test_shard_spec_rejects_mismatched_end_index(self):
        with pytest.raises(ValueError, match="end_index .* must equal start_index \\+ count"):
            ShardSpec(
                shard_id=1,
                name="shard-0001",
                start_index=0,
                count=1000,
                end_index=999,
                node_id="node-01",
                output_dir="runs/shard-0001",
            )

    def test_shard_spec_rejects_zero_or_negative_count(self):
        with pytest.raises(ValueError, match="count must be positive"):
            ShardSpec(
                shard_id=1,
                name="shard-0001",
                start_index=0,
                count=0,
                end_index=0,
                node_id="node-01",
                output_dir="runs/shard-0001",
            )


class TestValidateIntervals:
    """Tests for validate_intervals and non-overlapping invariants."""

    def test_valid_disjoint_intervals(self):
        intervals = [(0, 10), (10, 20), (25, 30)]
        is_valid, errors = validate_intervals(intervals)
        assert is_valid is True
        assert len(errors) == 0

    def test_empty_intervals_valid(self):
        is_valid, errors = validate_intervals([])
        assert is_valid is True
        assert len(errors) == 0

    def test_detects_overlap(self):
        intervals = [(0, 15), (10, 20)]
        is_valid, errors = validate_intervals(intervals)
        assert is_valid is False
        assert any("Collision/Overlap detected" in e for e in errors)

    def test_detects_out_of_bounds_and_inverted(self):
        # start >= end
        is_valid, errors = validate_intervals([(10, 10)])
        assert is_valid is False
        assert any("out of bounds" in e for e in errors)

        # inverted: start > end
        is_valid, errors = validate_intervals([(20, 10)])
        assert is_valid is False

        # exceeds LIMIT64
        is_valid, errors = validate_intervals([(LIMIT64 - 5, LIMIT64 + 1)])
        assert is_valid is False

    def test_detects_booleans_in_intervals(self):
        is_valid, errors = validate_intervals([(True, 10)])
        assert is_valid is False
        assert any("start coordinate cannot be bool" in e for e in errors)

        is_valid, errors = validate_intervals([(0, False)])
        assert is_valid is False
        assert any("end coordinate cannot be bool" in e for e in errors)

    def test_strict_mode_raises(self):
        with pytest.raises(TypeError):
            validate_intervals([(True, 10)], strict=True)

        with pytest.raises(ValueError):
            validate_intervals([(0, 15), (10, 20)], strict=True)


class TestUnionCoverage:
    """Tests for union_coverage formal interval aggregation."""

    def test_empty_coverage(self):
        assert union_coverage([]) == 0

    def test_disjoint_coverage(self):
        assert union_coverage([(0, 10), (20, 30)]) == 20

    def test_contiguous_coverage(self):
        assert union_coverage([(0, 10), (10, 25)]) == 25

    def test_overlapping_coverage(self):
        # [0, 10) and [5, 15) union is [0, 15) -> 15
        assert union_coverage([(0, 10), (5, 15)]) == 15

    def test_rejects_booleans(self):
        with pytest.raises(TypeError):
            union_coverage([(True, 10)])

    def test_rejects_out_of_bounds(self):
        with pytest.raises(ValueError):
            union_coverage([(LIMIT64 - 5, LIMIT64 + 10)])


class TestGenerateShards:
    """Tests for generate_shards partition generation and edge cases."""

    def test_generate_shards_exact_partition(self):
        shards = generate_shards(
            total_seeds=100_000_000,
            shard_size=10_000_000,
            start_offset=0,
            policy="dynamic-envelope-1664-v1",
            run_key="0",
        )
        assert len(shards) == 10
        intervals = [(s.start_index, s.end_index) for s in shards]
        is_valid, errors = validate_intervals(intervals)
        assert is_valid is True
        assert union_coverage(intervals) == 100_000_000
        assert shards[0].start_index == 0
        assert shards[0].end_index == 10_000_000
        assert shards[-1].end_index == 100_000_000
        assert shards[0].policy == "dynamic-envelope-1664-v1"
        assert shards[0].run_key == "0"

    def test_generate_shards_uneven_partition(self):
        shards = generate_shards(total_seeds=25, shard_size=10, start_offset=100)
        assert len(shards) == 3
        counts = [s.count for s in shards]
        assert counts == [10, 10, 5]
        intervals = [(s.start_index, s.end_index) for s in shards]
        is_valid, errors = validate_intervals(intervals)
        assert is_valid is True
        assert union_coverage(intervals) == 25

    def test_generate_shards_zero_total_seeds(self):
        shards = generate_shards(total_seeds=0, shard_size=10)
        assert shards == []

    @pytest.mark.parametrize("bad_val", [True, False])
    def test_generate_shards_rejects_booleans(self, bad_val):
        with pytest.raises(TypeError):
            generate_shards(total_seeds=bad_val, shard_size=10)
        with pytest.raises(TypeError):
            generate_shards(total_seeds=100, shard_size=bad_val)
        with pytest.raises(TypeError):
            generate_shards(total_seeds=100, shard_size=10, start_offset=bad_val)

    @pytest.mark.parametrize("bad_val", [10.5, "100", None])
    def test_generate_shards_rejects_non_integers(self, bad_val):
        with pytest.raises(TypeError):
            generate_shards(total_seeds=bad_val, shard_size=10)
        with pytest.raises(TypeError):
            generate_shards(total_seeds=100, shard_size=bad_val)
        with pytest.raises(TypeError):
            generate_shards(total_seeds=100, shard_size=10, start_offset=bad_val)

    @pytest.mark.parametrize("bad_size", [0, -1, -500])
    def test_generate_shards_rejects_zero_or_negative_shard_size(self, bad_size):
        with pytest.raises(ValueError, match="shard_size must be >= 1"):
            generate_shards(total_seeds=100, shard_size=bad_size)

    def test_generate_shards_rejects_negative_ranges(self):
        with pytest.raises(ValueError, match="total_seeds must be >= 0"):
            generate_shards(total_seeds=-10, shard_size=5)
        with pytest.raises(ValueError, match="start must be >= 0"):
            generate_shards(total_seeds=10, shard_size=5, start_offset=-1)

    def test_generate_shards_rejects_64bit_overflow(self):
        with pytest.raises(ValueError, match="exceeds 64-bit limit"):
            generate_shards(total_seeds=100, shard_size=10, start_offset=LIMIT64)
        with pytest.raises(ValueError, match="exceeds 64-bit limit"):
            generate_shards(total_seeds=10, shard_size=5, start_offset=LIMIT64 - 5)

    def test_generate_shards_at_64bit_boundary(self):
        # Starts near LIMIT64 and ends exactly at LIMIT64
        shards = generate_shards(total_seeds=30, shard_size=10, start_offset=LIMIT64 - 30)
        assert len(shards) == 3
        assert shards[-1].end_index == LIMIT64
        intervals = [(s.start_index, s.end_index) for s in shards]
        is_valid, errors = validate_intervals(intervals)
        assert is_valid is True
        assert union_coverage(intervals) == 30


class TestEmitCLICommands:
    """Tests for emit_cli_commands verifying explicit --policy, --run-key, and disjoint ranges."""

    def test_emit_cli_commands_includes_policy_and_run_key(self):
        shards = generate_shards(
            total_seeds=20_000_000,
            shard_size=10_000_000,
            start_offset=0,
            policy="dynamic-envelope-1664-v1",
            run_key="0",
        )
        script = emit_cli_commands(
            shards,
            policy="dynamic-envelope-1664-v1",
            run_key="0",
            threads=16,
            batch_size=4096,
            max_misses=2,
        )

        assert "#!/usr/bin/env bash" in script
        assert "config/realm_1664.yaml" in script
        assert "--config" in script and "run_key" in script
        assert "--start-index 0" in script
        assert "--count 10000000" in script
        assert "--start-index 10000000" in script
        assert "--native-threads 16" in script
        assert "--native-batch-size 4096" in script
        assert "--max-misses 2" in script
        assert "Range: [0, 10,000,000)" in script
        assert "Range: [10,000,000, 20,000,000)" in script

    def test_emit_cli_commands_custom_policy_and_key(self):
        shards = generate_shards(
            total_seeds=5_000,
            shard_size=5_000,
            start_offset=100,
            policy="config/custom-test.yaml",
            run_key="42",
        )
        script = emit_cli_commands(shards, policy="config/custom-test.yaml", run_key="42")
        assert "config/custom-test.yaml" in script
        assert "42" in script and "run_key" in script
        assert "--start-index 100" in script

    @pytest.mark.parametrize("bad_threads", [True, 0, 35, 10.5, None])
    def test_emit_cli_commands_rejects_invalid_threads(self, bad_threads):
        shards = generate_shards(total_seeds=100, shard_size=50)
        with pytest.raises((TypeError, ValueError)):
            emit_cli_commands(shards, threads=bad_threads)

    @pytest.mark.parametrize("bad_batch", [True, 0, -1, 20000, None])
    def test_emit_cli_commands_rejects_invalid_batch_size(self, bad_batch):
        shards = generate_shards(total_seeds=100, shard_size=50)
        with pytest.raises((TypeError, ValueError)):
            emit_cli_commands(shards, batch_size=bad_batch)


class TestStorageEstimatesAlignedWithDiskPolicy:
    """Tests for estimate_storage_bytes aligning conservative estimates with resources.disk_policy."""

    def test_compact_retention_defaults_to_32_bytes_per_seed(self):
        count = 10_000_000
        est = estimate_storage_bytes(count, retention="survivors")

        assert est["count"] == count
        assert est["retention"] == "survivors"
        assert est["projected_bytes_per_seed"] == 32
        assert est["projected_bytes"] == count * 32
        assert est["total_bytes"] == count * 32
        assert est["projected_mb"] == pytest.approx((count * 32) / (1024 * 1024), rel=1e-3)
        # Verify detailed analytical model is separated and calculated
        assert "analytical_bytes" in est
        assert est["analytical_bytes"] > 0
        assert est["analytical_bytes"] != est["projected_bytes"]

    def test_full_retention_defaults_to_65536_bytes_per_seed(self):
        count = 1_000_000
        est = estimate_storage_bytes(count, retention="full")

        assert est["count"] == count
        assert est["retention"] == "full"
        assert est["projected_bytes_per_seed"] == 65536
        assert est["projected_bytes"] == count * 65536
        assert est["total_bytes"] == count * 65536
        assert "analytical_bytes" in est

    def test_custom_projected_bytes_per_seed(self):
        count = 500_000
        est = estimate_storage_bytes(count, retention="survivors", projected_bytes_per_seed=64)
        assert est["projected_bytes_per_seed"] == 64
        assert est["projected_bytes"] == 500_000 * 64

    @pytest.mark.parametrize("bad_val", [True, False, 10.5, "1000", None])
    def test_storage_estimate_rejects_booleans_and_non_integers(self, bad_val):
        with pytest.raises(TypeError):
            estimate_storage_bytes(bad_val, retention="survivors")
        with pytest.raises(TypeError):
            estimate_storage_bytes(1000, batch_size=bad_val)
        if bad_val is None:
            # None is the documented sentinel for the retention-specific default.
            assert estimate_storage_bytes(1000, projected_bytes_per_seed=None)["projected_bytes_per_seed"] == 32
        else:
            with pytest.raises(TypeError):
                estimate_storage_bytes(1000, projected_bytes_per_seed=bad_val)

    def test_storage_estimate_rejects_negative_or_invalid_values(self):
        with pytest.raises(ValueError, match="count must be >= 0"):
            estimate_storage_bytes(-1)
        with pytest.raises(ValueError, match="batch_size must be >= 1"):
            estimate_storage_bytes(100, batch_size=0)
        with pytest.raises(ValueError, match="Unsupported retention mode"):
            estimate_storage_bytes(100, retention="invalid_mode")


class TestValidationPlanSchedule:
    """Tests for generate_validation_plan_schedule."""

    def test_generate_schedule_counterbalanced_structure(self):
        schedule = generate_validation_plan_schedule(base_start=50_000, pair_count=100_000, num_pairs=5)
        assert len(schedule) == 5

        # Check disjoint intervals
        intervals = [tuple(p["interval"]) for p in schedule]
        is_valid, errors = validate_intervals(intervals)
        assert is_valid is True
        assert intervals[0] == (50_000, 150_000)
        assert intervals[1] == (150_000, 250_000)
        assert intervals[4] == (450_000, 550_000)

        # Check counterbalanced alternating order
        assert schedule[0]["execution_order"] == ["control", "selected"]
        assert schedule[1]["execution_order"] == ["selected", "control"]
        assert schedule[2]["execution_order"] == ["control", "selected"]
        assert schedule[3]["execution_order"] == ["selected", "control"]
        assert schedule[4]["execution_order"] == ["control", "selected"]

    @pytest.mark.parametrize("bad_val", [True, False, 1.5, "50000", None])
    def test_generate_schedule_rejects_invalid_types(self, bad_val):
        with pytest.raises(TypeError):
            generate_validation_plan_schedule(base_start=bad_val)
        with pytest.raises(TypeError):
            generate_validation_plan_schedule(pair_count=bad_val)
        with pytest.raises(TypeError):
            generate_validation_plan_schedule(num_pairs=bad_val)
