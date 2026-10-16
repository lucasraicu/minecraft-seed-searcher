"""Unit tests for the hardened NumPy buffer contract and zero-survivor fast-path."""
import sys
import numpy as np
import pytest

from test_blueprint_batch_prototype import prototype, FixtureBackend
from seed_search.realm.store import RealmStore


def test_reject_float64_array(prototype):
    seeds = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    with pytest.raises(TypeError, match="NumPy seed array must be int64 or uint64"):
        prototype.sweep(seeds)


def test_reject_float32_array(prototype):
    seeds = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    with pytest.raises(TypeError, match="NumPy seed array must be int64 or uint64"):
        prototype.sweep(seeds)


def test_reject_int32_array(prototype):
    seeds = np.array([100, 200, 300], dtype=np.int32)
    with pytest.raises(TypeError, match="NumPy seed array must be int64 or uint64"):
        prototype.sweep(seeds)


def test_reject_uint32_array(prototype):
    seeds = np.array([100, 200, 300], dtype=np.uint32)
    with pytest.raises(TypeError, match="NumPy seed array must be int64 or uint64"):
        prototype.sweep(seeds)


def test_reject_2d_array(prototype):
    seeds = np.array([[100, 200], [300, 400]], dtype=np.int64)
    with pytest.raises(ValueError, match="NumPy seed array must be 1-dimensional"):
        prototype.sweep(seeds)


def test_reject_3d_array(prototype):
    seeds = np.zeros((2, 2, 2), dtype=np.int64)
    with pytest.raises(ValueError, match="NumPy seed array must be 1-dimensional"):
        prototype.sweep(seeds)


def test_reject_non_contiguous_array(prototype):
    base = np.array([10, 20, 30, 40, 50, 60], dtype=np.int64)
    sliced = base[::2]  # Step of 2 -> non-contiguous
    assert not sliced.flags["C_CONTIGUOUS"]
    with pytest.raises(ValueError, match="NumPy seed array must be C-contiguous"):
        prototype.sweep(sliced)


def test_reject_wrong_endian_array(prototype):
    wrong_endian = ">" if sys.byteorder == "little" else "<"
    seeds = np.array([100, 200, 300], dtype=f"{wrong_endian}i8")
    with pytest.raises(ValueError, match="NumPy seed array must have native byte order"):
        prototype.sweep(seeds)


def test_successful_sweep_int64(prototype):
    seeds = np.array([12345, -987654321, 2**63 - 1, -2**63], dtype=np.int64)
    with prototype.sweep(seeds) as batch:
        summary = batch.summary()
        assert len(summary) == 4
        assert [s["seed"] for s in summary] == [str(int(s)) for s in seeds]
        records = batch.records(0)
        assert len(records) == 4
        assert [r["seed"] for r in records] == [str(int(s)) for s in seeds]


def test_successful_sweep_uint64(prototype):
    # Unsigned 64-bit representations
    seeds = np.array([12345, 18446744072721897295, 2**63 - 1], dtype=np.uint64)
    with prototype.sweep(seeds) as batch:
        summary = batch.summary()
        assert len(summary) == 3
        # In summary, values >= 2^63 are converted to signed string
        expected = []
        for s in seeds:
            v = int(s)
            expected.append(str(v if v < (1 << 63) else v - (1 << 64)))
        assert [s["seed"] for s in summary] == expected


def test_successful_sweep_with_synthetic_fixtures(prototype):
    seeds = np.array([42, -42], dtype=np.int64)
    fixtures = [(0, 0, -1), (100, 200, 5)]
    with prototype.sweep(seeds, fixtures=fixtures, retention="survivors", max_misses=2) as batch:
        receipt = batch.retention_receipt()
        assert receipt["inputs"] == 2
        assert receipt["version"] == "native-retention-receipt-v1"


def test_zero_survivor_sqlite_fast_path(tmp_path, prototype):
    """Verify zero-survivor fast path commits efficiently and stores receipt."""
    cfg = prototype.cfg
    with RealmStore(tmp_path, {"config": cfg, "retention": {"mode": "survivors", "max_misses": 2}}) as store:
        store.configure_range(100, 200, 100)
        claimed = store.claim_range("worker-1")
        assert claimed == (100, 200)

        receipt = {
            "version": "native-retention-receipt-v1",
            "inputs": 100,
            "retained_inputs": 0,
            "retained_anchors": 0,
            "discovered_anchors": 5,
            "input_decisions_sha256": "e" * 64,
        }
        prepared = store.prepare_retained_range(100, 200, [], receipt)
        assert len(prepared.candidate_rows) == 0
        assert len(prepared.seed_rows) == 0

        # Complete the range
        committed = store.complete_prepared(prepared, lease=("worker-1", 1))
        assert committed is True

        # Check status and DB contents
        st = store.status()
        assert st["completed_seeds"] == 100
        assert st["saved_seed_rows"] == 0

        # Receipt must be present in retention_receipts table
        row = store.db.execute("SELECT start, end, receipt, digest FROM retention_receipts WHERE start=?", (f"{100:020d}",)).fetchone()
        assert row is not None
        assert row[1] == f"{200:020d}"
        assert row[3] == prepared.digest

        # Ranges table must be complete
        r_row = store.db.execute("SELECT status, worker, digest FROM ranges WHERE start=?", (f"{100:020d}",)).fetchone()
        assert r_row[0] == "complete"
        assert r_row[1] is None
        assert r_row[2] == prepared.digest

        # Idempotent retry returns False
        assert store.complete_prepared(prepared) is False
