"""Bounded, parent-written full64 Realm discovery with recoverable range leases."""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from contextlib import contextmanager
import fcntl
import hashlib
import importlib
import json
import math
from multiprocessing import get_context
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from time import monotonic

from ..seeds import seed_from_index
from .config import memory_budget_gib
from .store import LIMIT, RealmStore, canonical, index_key
from .resources import disk_policy, disk_status, WorkspaceCapacityError

THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS")


@contextmanager
def _scan_lock(output):
    """OS-released advisory lock prevents concurrent scanners stealing live leases."""
    Path(output).mkdir(parents=True, exist_ok=True)
    with (Path(output) / ".realm-scan.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another Realm scanner owns this run") from exc
        try:
            lock.seek(0)
            lock.truncate()
            lock.write(str(os.getpid()))
            lock.flush()
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


@contextmanager
def _numerical_threads():
    previous = {key: os.environ.get(key) for key in THREAD_ENV}
    for key in THREAD_ENV:
        os.environ[key] = "1"
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _seed(index, search):
    if search.get('sequence') == 'manifest':
        from ..seeds import parse_seed
        values = search.get('manifest_seeds', [])
        if not 0 <= index < len(values):
            raise ValueError('Seed index outside frozen manifest')
        return parse_seed(values[index])
    if search.get("sequence", "permutation") == "sequential":
        return index if index < 1 << 63 else index - LIMIT
    key = search.get("run_key", "0")
    # Keep numeric historical run keys compatible; textual keys have a stable hash.
    try:
        key = int(key)
    except (ValueError, TypeError):
        key = int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:8], "big")
    return seed_from_index(index, key)


def _evaluate_batch(evaluator, start, end, cfg):
    from ..backend import configure_native_threads
    configure_native_threads(cfg['search'].get('native_threads_per_worker',1))
    module, name = evaluator.split(":", 1)
    evaluate = getattr(importlib.import_module(module), name)
    started = time.perf_counter()
    cpu_started = time.process_time()
    results = [evaluate(index, _seed(index, cfg["search"]), cfg) for index in range(start, end)]
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"results": results, "pid": os.getpid(), "wall_seconds": time.perf_counter() - started,
            "cpu_seconds": time.process_time() - cpu_started,
            "worker_peak_rss_bytes": int(peak if sys.platform == "darwin" else peak * 1024)}


def _validate_batch_seeds(start, end, results, search):
    """Check worker output against the assigned sequence before recording coverage."""
    for result in results:
        index = result.get("index")
        if isinstance(index, bool) or not isinstance(index, int) or not start <= index < end:
            raise ValueError("Worker returned an index outside its assigned range")
        if result.get("seed") != str(_seed(index, search)):
            raise ValueError("Worker returned a seed that differs from its assigned sequence")


def process_tree_resources(root_pid=None):
    """Sum RSS and instantaneous CPU for parent plus descendants (shared pages count twice)."""
    root_pid = root_pid or os.getpid()
    try:
        output = subprocess.run(["ps", "-axo", "pid=,ppid=,rss=,pcpu="], check=True, capture_output=True, text=True, timeout=5).stdout
        rows = {}
        for line in output.splitlines():
            pid, parent, rss, cpu = line.split()
            rows[int(pid)] = (int(parent), int(rss), float(cpu))
        selected = {root_pid}
        while True:
            children = {pid for pid, (parent, _, _) in rows.items() if parent in selected}
            extended = selected | children
            if extended == selected:
                break
            selected = extended
        processes = [{"pid": pid, "rss_bytes": rows[pid][1] * 1024, "cpu_percent": rows[pid][2]} for pid in sorted(selected) if pid in rows]
        if root_pid not in rows:
            raise ValueError('Requested process is absent from resource snapshot')
        return {
            "available": True,
            "rss_bytes": sum(row["rss_bytes"] for row in processes),
            "cpu_percent": sum(row["cpu_percent"] for row in processes),
            "processes": processes,
            "shared_memory_caveat": "RSS sum can double-count shared pages",
            "sampled_at": time.time(),
        }
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if root_pid == os.getpid():
            ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            rss_bytes = ru if sys.platform == "darwin" else ru * 1024
            return {
                "available": False,
                "rss_bytes": rss_bytes,
                "cpu_percent": 0.0,
                "processes": [{"pid": root_pid, "rss_bytes": rss_bytes, "cpu_percent": 0.0}],
                "fallback": "rusage_self",
                "scope": "SELF high-water diagnostic only; descendants unobserved",
                "error": str(exc),
                "sampled_at": time.time(),
            }
        return {"available": False, "error": str(exc), "sampled_at": time.time()}


def _scale_gate(cfg, output, count, allow_prediction_scale):
    search = cfg["search"]
    if count <= search.get("pilot_limit", 1000):
        return
    if not allow_prediction_scale:
        raise ValueError("Scan exceeds pilot_limit; explicitly allow prediction scale and persist compatibility.json")
    path = Path(output) / "compatibility.json"
    if not path.is_file():
        raise ValueError("Prediction scale requires persisted compatibility.json")
    report = json.loads(path.read_text())
    if not isinstance(report, dict) or not isinstance(report.get("features"), dict):
        raise ValueError("Invalid persisted compatibility report")
    expected = {"target_version": "26.52", "bds_version": "1.26.52.3", "prediction_model": "MC_26_50"}
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Compatibility report does not match the pinned Realm provider")
    if search.get("mode", "prediction") != "prediction":
        raise ValueError("Large actual-generation search is not certified by the prediction runner")


def run_scan(cfg, output, count, start_index=0, workers=None, resume=False, identity=None,
             evaluator="seed_search.realm.baseline:evaluate_seed", stop_after=None, progress=None,
             allow_prediction_scale=False, progress_interval_seconds=10, *, execution="python",
             native_build=None, native_threads=16, native_batch_size=4096, retention="full", max_misses=None):
    """Run a finite interval; stop_after limits newly committed seeds in this invocation.

    A worker error stops dispatch, drains other submitted batches, and leaves the failed
    lease retryable. KeyboardInterrupt similarly stops dispatch and drains running work.
    No executor has more than `workers` outstanding batches.
    Progress aggregates are built at most once per interval (first commit is immediate).
    Set progress_interval_seconds=0 for a callback on every committed batch.
    """
    if execution not in ('python','native'):raise ValueError('Unknown baseline executor')
    if execution=='native':
        if workers is not None:raise ValueError('Use native_threads for the native executor, not workers')
        if evaluator!='seed_search.realm.baseline:evaluate_seed':raise ValueError('Native execution requires the blueprint evaluator')
        from .native_batch import run_native_scan
        return run_native_scan(cfg,output,count,start_index,resume,identity,native_build=native_build,
            native_threads=native_threads,native_batch_size=native_batch_size,stop_after=stop_after,
            progress=progress,allow_prediction_scale=allow_prediction_scale,retention=retention,max_misses=max_misses)
    if native_build is not None or retention!='full' or max_misses:raise ValueError('Native build or compact retention requires execution=native')
    index_key(start_index)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or start_index + count > LIMIT:
        raise ValueError("Invalid finite full64 seed count")
    if stop_after is not None and (isinstance(stop_after, bool) or not isinstance(stop_after, int) or stop_after < 0):
        raise ValueError("Invalid stop_after")
    if isinstance(progress_interval_seconds, bool) or not isinstance(progress_interval_seconds, (int, float)) or not math.isfinite(progress_interval_seconds) or progress_interval_seconds < 0:
        raise ValueError("Invalid progress interval")
    search = cfg["search"]
    workers = search.get("workers", 12) if workers is None else workers
    maximum = search.get("max_workers", 36)
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= min(maximum, 36):
        raise ValueError("Realm workers must be between 1 and max_workers (at most 36)")
    if search.get("sequence", "permutation") not in {"sequential", "permutation", "manifest"}:
        raise ValueError("Unknown full64 seed sequence")
    if search.get('sequence') == 'manifest':
        from ..seeds import parse_seed
        manifest = search.get('manifest_seeds')
        if (not isinstance(manifest, list) or not 1 <= len(manifest) <= 10000
                or any(not isinstance(v, str) or str(parse_seed(v)) != v for v in manifest)
                or len(set(manifest)) != len(manifest) or start_index+count > len(manifest)):
            raise ValueError('Invalid or insufficient canonical full64 seed manifest')
    if search.get("numeric_threads_per_worker", 1) != 1:
        raise ValueError("Realm numerical threads per worker must equal 1")
    from ..backend import configure_native_threads
    native_threads=search.get('native_threads_per_worker',1)
    configure_native_threads(native_threads)
    if workers*native_threads>36:
        raise ValueError('Process/native thread product must fit 36 logical CPUs')
    if not isinstance(evaluator, str) or ":" not in evaluator:
        raise ValueError("Evaluator must be an importable module:function")
    bds_enabled = cfg.get("bds", {}).get("enabled", False) or cfg.get("verification", {}).get("provider") == "bds"
    target_gib, ceiling_gib, reserve_gib = memory_budget_gib(search, docker_reserve_default=8 if bds_enabled else 0)
    disk_limits=disk_policy(search)
    target, ceiling, docker_reserve = (value * (1 << 30) for value in (target_gib, ceiling_gib, reserve_gib))
    _scale_gate(cfg, output, count, allow_prediction_scale)
    if identity is None:
        identity = {"config": cfg, "count": count, "start_index": start_index, "evaluator": evaluator}
    with _scan_lock(output), RealmStore(output, identity, resume) as store:
        store.configure_range(start_index, start_index + count, search.get("batch_size", 32))
        recovered = store.recover_assignments()
        stats = store.get_state("worker_statistics") or {"batches": 0, "worker_seconds": 0.0, "workers": {}}
        stats.update({"requested_workers": workers, "numerical_threads": 1, "native_threads":native_threads,
                      "recovered_assignments": recovered, "max_outstanding_batches": 0})
        started = time.perf_counter()
        committed, dispatched = 0, 0
        interrupted, stopping, failure = False, False, None
        last_progress = None
        peak_rss = (store.get_state("memory") or {}).get("peak_process_tree_rss_bytes", 0)
        latest_memory = {}
        last_disk_sample=0.
        latest_disk={}

        def sample_disk(force=False,additional_bytes=0):
            nonlocal last_disk_sample,latest_disk,stopping,failure
            if not force and time.monotonic()-last_disk_sample<10:return
            try:
                completed=store.db.execute('SELECT count(*) FROM seeds').fetchone()[0]
                # Use an observed upper estimate after 128 commits. WAL/startup
                # overhead remains included rather than subtracted optimistically.
                latest_disk=disk_status(store.run,disk_limits,additional_bytes=additional_bytes,
                                        remaining_seeds=count-completed,completed_seeds=completed)
                last_disk_sample=time.monotonic()
                store.set_state('workspace_disk',latest_disk)
            except WorkspaceCapacityError as exc:
                stopping=True;failure=failure or exc
                store.set_state('workspace_disk_failure',{'error':str(exc),'sampled_at':time.time()})

        def sample_memory():
            nonlocal peak_rss, latest_memory, stopping, failure
            sample = process_tree_resources()
            if sample.get("available"):
                peak_rss = max(peak_rss, sample["rss_bytes"])
                combined = sample["rss_bytes"] + docker_reserve
                sample.update({"combined_budget_estimate_bytes": combined, "above_target": combined > target})
                if combined > ceiling:
                    stopping = True
                    if failure is None:
                        failure = RuntimeError("Process-tree RSS plus Docker reserve exceeded memory ceiling; scan checkpoint retained")
            else:
                stopping = True
                stats["last_monitor_failure"] = {"error": sample.get("error", "Process-tree monitoring unavailable"),
                                                 "sampled_at": sample.get("sampled_at", time.time())}
                if failure is None:
                    failure = RuntimeError("Process-tree monitoring unavailable; new dispatch stopped and scan checkpoint retained")
            latest_memory = {**sample, "peak_process_tree_rss_bytes": peak_rss, "docker_reserved_bytes": docker_reserve, "target_bytes": target, "ceiling_bytes": ceiling, "units": "bytes; GiB=2**30 bytes"}
            store.set_state("memory", latest_memory)

        with _numerical_threads():
            with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as pool:
                pending = {}
                while True:
                    sample_memory()
                    sample_disk()
                    if latest_memory.get("above_target"):
                        capacity = len(pending)
                        if not pending and not stopping:
                            stopping=True
                            failure=RuntimeError('Memory remains above working target after drain; checkpoint retained')
                    else:
                        capacity = workers
                    while not stopping and len(pending) < capacity:
                        budget = None if stop_after is None else stop_after - dispatched
                        if budget is not None and budget <= 0:
                            break
                        lease = store.claim_range(len(pending), max_seeds=budget)
                        if lease is None:
                            break
                        first, end = lease
                        try:
                            future = pool.submit(_evaluate_batch, evaluator, first, end, cfg)
                        except Exception as exc:
                            failure, stopping = exc, True
                            break
                        pending[future] = lease
                        dispatched += end - first
                        stats["max_outstanding_batches"] = max(stats["max_outstanding_batches"], len(pending))
                    if not pending:
                        break
                    try:
                        ready, _ = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                    except KeyboardInterrupt:
                        stopping, interrupted = True, True
                        continue
                    for future in ready:
                        first, end = pending.pop(future)
                        try:
                            batch = future.result()
                            _validate_batch_seeds(first, end, batch["results"], search)
                            # Current payload bounds protect the reserve before a
                            # commit; assigned work remains retryable on failure.
                            store.complete_range(first, end, batch["results"],
                                capacity_check=lambda payload_bytes: disk_status(store.run,disk_limits,additional_bytes=payload_bytes))
                        except Exception as exc:
                            failure, stopping = failure or exc, True
                            continue
                        committed += end - first
                        stats["batches"] += 1
                        stats["worker_seconds"] += batch["wall_seconds"]
                        stats["worker_cpu_seconds"] = stats.get("worker_cpu_seconds", 0.0) + batch["cpu_seconds"]
                        stages = stats.setdefault("stage_seconds", {})
                        for result in batch["results"]:
                            for stage, seconds in result.get("stage_seconds", {}).items():
                                stages[stage] = stages.get(stage, 0.0) + seconds
                        pid = str(batch["pid"])
                        worker = stats["workers"].setdefault(pid, {"batches": 0, "seeds": 0, "wall_seconds": 0.0})
                        worker["batches"] += 1
                        worker["seeds"] += end - first
                        worker["wall_seconds"] += batch["wall_seconds"]
                        worker["cpu_seconds"] = worker.get("cpu_seconds", 0.0) + batch["cpu_seconds"]
                        worker["peak_rss_bytes"] = max(worker.get("peak_rss_bytes", 0), batch["worker_peak_rss_bytes"])
                        store.set_state("worker_statistics", stats)
                        now = monotonic()
                        if progress is not None and (last_progress is None or now - last_progress >= progress_interval_seconds):
                            last_progress = now
                            try:
                                progress(store.status())
                            except KeyboardInterrupt:
                                stopping, interrupted = True, True
                            except Exception as exc:
                                failure, stopping = failure or exc, True
        store.recover_assignments()
        stats.update({"invocation_seconds": time.perf_counter() - started, "invocation_completed_seeds": committed, "interrupted": interrupted, "error": str(failure) if failure else None})
        store.set_state("worker_statistics", stats)
        sample_memory()
        status = store.status()
        status["interrupted"] = interrupted
        if failure is not None:
            raise failure
        return status
