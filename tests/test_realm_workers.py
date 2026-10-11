import copy
from concurrent.futures.process import BrokenProcessPool
import json
import os
from pathlib import Path

import pytest

from seed_search.realm.runner import THREAD_ENV, _scan_lock, process_tree_resources, run_scan
from seed_search.realm.store import LIMIT, RealmStore

# Importable functions let spawned processes test the real multiprocessing boundary.
def fake_evaluator(index, seed, cfg):
    if cfg.get("crash_once"):
        marker = Path(cfg["crash_once"])
        if index == 2 and not marker.exists():
            marker.write_text("crashed")
            os._exit(7)
    return {"index": index, "seed": str(seed), "anchors": [
        {"id": f"{seed}:1:2", "seed": str(seed), "stronghold": [1, 2], "qualification": "PREDICTED"},
        {"id": f"{seed}:3:4", "seed": str(seed), "stronghold": [3, 4], "qualification": "PENDING"}],
        "stage_seconds": {}, "counts": {"anchors": 2}, "total_seconds": 0,
        "threads": {key: os.environ.get(key) for key in THREAD_ENV}}


EVALUATOR = "test_realm_workers:fake_evaluator"


def test_manifest_real_worker_boundary_and_resume(tmp_path):
    cfg = config()
    cfg['search'].update(sequence='manifest', manifest_seeds=['-1', '0', '12345'])
    path = tmp_path/'manifest'
    run_scan(cfg, path, 3, evaluator=EVALUATOR, stop_after=1)
    run_scan(cfg, path, 3, evaluator=EVALUATOR, resume=True)
    assert [r['seed'] for r in results(path)[0]] == ['-1', '0', '12345']
    with pytest.raises(ValueError, match='manifest'):
        run_scan(cfg, tmp_path/'too-long', 4, evaluator=EVALUATOR)
    cfg['search']['manifest_seeds'] = ['0', '0']
    with pytest.raises(ValueError, match='manifest'):
        run_scan(cfg, tmp_path/'duplicates', 2, evaluator=EVALUATOR)


def config():
    return {"search": {"workers": 2, "max_workers": 36, "batch_size": 3, "sequence": "permutation", "run_key": "test", "pilot_limit": 1000, "mode": "prediction", "memory_target_gib": 25, "memory_ceiling_gib": 30}}


def results(path):
    with RealmStore(path, resume=True) as store:
        return list(store.iter_results()), list(store.iter_candidates())


def test_worker_reproducibility_bounds_and_resume(tmp_path):
    cfg = config()
    first, second = tmp_path / "one", tmp_path / "two"
    state = run_scan(cfg, first, 11, workers=1, evaluator=EVALUATOR, stop_after=4)
    assert state["completed_seeds"] == 4
    changed = copy.deepcopy(cfg)
    changed["search"].update(workers=3, batch_size=2)
    state = run_scan(changed, first, 11, resume=True, evaluator=EVALUATOR)
    assert state["completed_seeds"] == 11
    assert state["worker_statistics"]["max_outstanding_batches"] <= 3
    assert all(worker["peak_rss_bytes"] > 0 for worker in state["worker_statistics"]["workers"].values())
    run_scan(cfg, second, 11, evaluator=EVALUATOR)
    assert results(first) == results(second)
    assert all(set(r["threads"].values()) == {"1"} for r in results(first)[0])
    with RealmStore(first, resume=True) as store:
        rows = [(int(a), int(b), status) for a, b, status in store.db.execute("SELECT start,end,status FROM ranges ORDER BY start")]
        assert rows[0][0] == 0 and rows[-1][1] == 11
        assert all(a[1] == b[0] for a, b in zip(rows, rows[1:]))
        assert all(row[2] == "complete" for row in rows)


def test_hard_worker_crash_and_resume(tmp_path):
    cfg = config()
    cfg["crash_once"] = str(tmp_path / "crashed")
    cfg["search"].update(workers=1, batch_size=2)
    run = tmp_path / "run"
    with pytest.raises(BrokenProcessPool):
        run_scan(cfg, run, 8, evaluator=EVALUATOR)
    with RealmStore(run, resume=True) as store:
        assert store.status()["completed_seeds"] == 2
        assert store.status()["ranges"].get("retry") == 1
    state = run_scan(cfg, run, 8, resume=True, evaluator=EVALUATOR)
    assert state["completed_seeds"] == 8
    assert len(results(run)[1]) == 16
    with RealmStore(run, resume=True) as store:
        assert store.db.execute("SELECT attempts FROM ranges WHERE start='00000000000000000000'").fetchone()[0] == 1


def test_sequential_signed_end_and_graceful_cancellation(tmp_path):
    cfg = config()
    cfg["search"].update(sequence="sequential", workers=1, batch_size=1)
    def interrupt(_):
        raise KeyboardInterrupt
    state = run_scan(cfg, tmp_path / "end", 3, start_index=LIMIT - 3, evaluator=EVALUATOR, progress=interrupt)
    assert state["interrupted"] and state["completed_seeds"] == 1
    state = run_scan(cfg, tmp_path / "end", 3, start_index=LIMIT - 3, evaluator=EVALUATOR, resume=True)
    assert state["completed_seeds"] == 3
    assert [r["seed"] for r in results(tmp_path / "end")[0]] == ["-3", "-2", "-1"]
    with pytest.raises(ValueError):
        run_scan(cfg, tmp_path / "bad", 2, start_index=LIMIT - 1, evaluator=EVALUATOR)


def test_scale_gate_and_resource_measurement(tmp_path):
    cfg = config()
    cfg["search"]["pilot_limit"] = 2
    with pytest.raises(ValueError, match="pilot_limit"):
        run_scan(cfg, tmp_path, 3, evaluator=EVALUATOR)
    with pytest.raises(ValueError, match="compatibility.json"):
        run_scan(cfg, tmp_path, 3, evaluator=EVALUATOR, allow_prediction_scale=True)
    (tmp_path / "compatibility.json").write_text(json.dumps({"target_version": "26.52", "bds_version": "1.26.52.3", "prediction_model": "MC_26_50", "large_search_ready": False, "features": {}}))
    state = run_scan(cfg, tmp_path, 3, evaluator=EVALUATOR, allow_prediction_scale=True)
    assert state["completed_seeds"] == 3
    memory = process_tree_resources()
    assert memory["available"] and memory["rss_bytes"] > 0
    assert any(row["pid"] == os.getpid() for row in memory["processes"])


def test_memory_ceiling_retains_retryable_checkpoint(tmp_path, monkeypatch):
    from seed_search.realm import runner
    cfg = config()
    cfg["search"]["docker_reserve_gib"] = 8
    monkeypatch.setattr(runner, "process_tree_resources", lambda: {"available": True, "rss_bytes": 23 * (1 << 30), "cpu_percent": 0, "processes": []})
    with pytest.raises(RuntimeError, match="memory ceiling"):
        run_scan(cfg, tmp_path, 3, evaluator=EVALUATOR)
    with RealmStore(tmp_path, resume=True) as store:
        assert store.status()["completed_seeds"] == 0
        assert store.status()["memory"]["docker_reserved_bytes"] == 8 * (1 << 30)
    monkeypatch.setattr(runner, "process_tree_resources", lambda: {"available": True, "rss_bytes": 1 << 30, "cpu_percent": 0, "processes": []})
    assert run_scan(cfg, tmp_path, 3, evaluator=EVALUATOR, resume=True)["completed_seeds"] == 3


def test_concurrent_scanner_lock_releases_after_exit(tmp_path):
    cfg = config()
    with _scan_lock(tmp_path):
        with pytest.raises(ValueError, match="Another Realm scanner"):
            run_scan(cfg, tmp_path, 1, evaluator=EVALUATOR)
        assert not (tmp_path / "realm.sqlite").exists()
    assert run_scan(cfg, tmp_path, 1, evaluator=EVALUATOR)["completed_seeds"] == 1


def test_progress_throttle_precedes_database_aggregation(tmp_path, monkeypatch):
    from seed_search.realm import runner
    cfg = config()
    cfg['search'].update(workers=1, batch_size=1)
    monkeypatch.setattr(runner, 'monotonic', lambda: 100.0)
    original = RealmStore.status
    status_calls = []
    def counted_status(store):
        status_calls.append(store.run)
        return original(store)
    monkeypatch.setattr(RealmStore, 'status', counted_status)
    throttled = []
    state = run_scan(cfg, tmp_path / 'throttled', 7, evaluator=EVALUATOR, progress=throttled.append)
    assert state['completed_seeds'] == 7
    assert len(throttled) == 1 and throttled[0]['completed_seeds'] == 1
    assert len(status_calls) == 2  # First progress aggregation and final returned status.
    status_calls.clear()
    every_batch = []
    run_scan(cfg, tmp_path / 'every', 7, evaluator=EVALUATOR, progress=every_batch.append, progress_interval_seconds=0)
    assert [item['completed_seeds'] for item in every_batch] == list(range(1, 8))
    assert len(status_calls) == 8
    assert results(tmp_path / 'throttled') == results(tmp_path / 'every')
