"""Catalog ingestion coordinator for 100-world validation stage.

Build schema accepted in controls['build']:
{
    'identity': {
        'edition': 'bedrock',
        'game_build_id': 'research:<model_id>',
        'world_settings_id': '<world_settings_id>',
        'model_id': '<model_id>',
        'native_sha256': '<64 hex chars>',
        'source_sha256': '<64 hex chars>',
        'registry_revision': '<registry_revision>',
        'extractor_revision': '<extractor_revision>',
    },
    'source_sha256': {
        '<relative_filepath>': '<64 hex chars>',
        ...
    }
}
"""
from __future__ import annotations

import contextlib
import ctypes
import fcntl
import json
import os
from pathlib import Path
import resource
import selectors
import hashlib
import signal
import statistics
import struct
import subprocess
import sys
import time
from typing import Any, Callable, Sequence

from .coverage import BIOME_METHOD, STRUCTURE_METHOD
from .models import FEATURE_IDS, validate_identity, validate_observation
from .registry import canonical_json
from .validation_contracts import cohort, validate_controls

_HAS_PSUTIL = False
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    pass

_LIBPROC = None
if sys.platform == 'darwin':
    try:
        _LIBPROC = ctypes.CDLL('/usr/lib/libproc.dylib')
    except Exception:
        _LIBPROC = None


def _reject_constant(constant: str) -> None:
    raise ValueError(f"Strict finite JSON: non-finite constant not allowed: {constant}")


def strict_json_loads(data: str | bytes) -> Any:
    """Parse JSON with strict finite number rules (no NaN, Infinity, -Infinity)."""
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return json.loads(data, parse_constant=_reject_constant)


def strict_json_dumps(value: Any, *, indent: int | None = 2) -> bytes:
    """Serialize value to strict finite JSON UTF-8 bytes."""
    return json.dumps(
        value,
        indent=indent,
        sort_keys=True,
        separators=(',', ': ') if indent else (',', ':'),
        allow_nan=False,
    ).encode('utf-8')


def verify_no_symlinks(path: Path | str) -> Path:
    """Verify that a path and its path components contain no symlinks."""
    p = Path(os.path.abspath(os.fspath(path)))
    cur = p
    checked = []
    while cur != cur.parent:
        checked.append(cur)
        cur = cur.parent
    for component in reversed(checked):
        if os.path.islink(component):
            raise ValueError(f"Symlink rejected in path component: {component}")
    return p


def atomic_json(path: Path | str, value: Any) -> None:
    """Write strict finite JSON value atomically via temporary file and replace."""
    atomic_bytes(path, strict_json_dumps(value))


def atomic_bytes(path: Path | str, encoded: bytes) -> None:
    """Publish already-encoded immutable bytes with the same durable boundary."""
    if not isinstance(encoded, bytes):
        raise TypeError('Atomic payload must be immutable bytes')
    target = verify_no_symlinks(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    verify_no_symlinks(target.parent)

    tmp_path = target.with_name(f".{target.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp_path, 'wb') as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        verify_no_symlinks(tmp_path)
        verify_no_symlinks(target)
        os.replace(tmp_path, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _get_process_creation_meta(pid: int) -> dict[str, Any]:
    meta: dict[str, Any] = {"pid": pid}
    if _HAS_PSUTIL:
        try:
            p = psutil.Process(pid)
            meta["create_time"] = p.create_time()
            meta["cmd"] = p.cmdline()
            return meta
        except Exception:
            pass
    if _LIBPROC is not None:
        try:
            buf = ctypes.create_string_buffer(256)
            res = _LIBPROC.proc_pidinfo(pid, 3, 0, buf, len(buf))
            if res > 0:
                start_sec, start_usec = struct.unpack_from("QQ", buf, 120)
                meta["create_time"] = start_sec + (start_usec / 1_000_000.0)
                return meta
        except Exception:
            pass
    try:
        res = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            meta["create_time"] = res.stdout.strip()
            return meta
    except Exception:
        pass
    meta["create_time"] = None
    return meta


def tree_bytes(root):
    total=0
    for path in Path(root).rglob('*'):
        if path.is_symlink():raise ValueError('Symlink in output tree')
        try:
            if path.is_file():total+=path.stat().st_size
        except FileNotFoundError:
            pass  # An owned atomic temporary was renamed between stat calls.
    return total


def _get_checkpoint_size(path: Path) -> int:
    if path.exists():
        try:
            return path.stat().st_size
        except OSError:
            pass
    return 0


def _get_process_rss(pid: int) -> int:
    """Return RSS in bytes for pid."""
    if _HAS_PSUTIL:
        try:
            return psutil.Process(pid).memory_info().rss
        except Exception:
            pass
    if _LIBPROC is not None:
        try:
            buf = ctypes.create_string_buffer(256)
            res = _LIBPROC.proc_pidinfo(pid, 4, 0, buf, len(buf))
            if res > 0:
                _, resident_size = struct.unpack_from("QQ", buf, 0)
                return resident_size
        except Exception:
            pass
    try:
        res = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            return int(res.stdout.strip()) * 1024
    except Exception:
        pass
    return 0


def _get_aggregate_rss(child_pid: int) -> int:
    from ..realm.runner import process_tree_resources
    sample = process_tree_resources(os.getpid())
    if not sample['available']:
        raise RuntimeError('Aggregate RSS monitoring unavailable; refusing dispatch')
    return sample['rss_bytes']


def _kill_process_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    except OSError:
        pass


def _ensure_no_descendants(pgid: int) -> None:
    for _ in range(3):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except OSError:
            pass
        time.sleep(0.01)


def _verify_process_ownership(pid: int, pgid: int, lease: dict[str, Any]) -> bool:
    try:
        cur_pgid = os.getpgid(pid)
        if cur_pgid != pgid:
            return False
    except OSError:
        return False

    expected_create_time = lease.get("create_time")
    if expected_create_time is None:
        return False

    current_meta = _get_process_creation_meta(pid)
    current_time = current_meta.get("create_time")
    if current_time is None:
        return False

    if isinstance(expected_create_time, (int, float)) and isinstance(current_time, (int, float)):
        return abs(current_time - expected_create_time) < 0.000001
    return str(expected_create_time) == str(current_time)


@contextlib.contextmanager
def _flock_root(root: Path):
    lock_file = root / ".coordinator.lock"
    verify_no_symlinks(lock_file.parent)
    if lock_file.exists():
        verify_no_symlinks(lock_file)
    fd = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise RuntimeError(f"Coordinator already active on root {root}: {exc}") from exc
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def _validate_child_observation(
    checkpoint_path: Path,
    expected_seed: str,
    expected_build_identity: dict[str, Any],
) -> tuple[str, str | None, dict[str, str]]:
    """Validate observation JSON at checkpoint_path against models schema and build identity."""
    verify_no_symlinks(checkpoint_path)
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = f.read()
    obs = strict_json_loads(data)
    validate_observation(obs)

    obs_id = obs['identity']
    if obs_id['seed'] != str(expected_seed):
        raise ValueError(f"Seed mismatch in observation: expected {expected_seed}, got {obs_id['seed']}")
    for k, v in expected_build_identity.items():
        if obs_id.get(k) != v:
            raise ValueError(f"Build identity mismatch for field '{k}': expected {v}, got {obs_id.get(k)}")

    coverage = obs.get('coverage', {})
    progress: dict[str, str] = {}
    all_23_complete = True
    for feat in FEATURE_IDS:
        cov = coverage.get(feat)
        expected_method = BIOME_METHOD if feat.startswith('biome.') else STRUCTURE_METHOD
        if cov and cov.get('status') == 'complete' and cov.get('method_id') == expected_method:
            progress[feat] = 'complete'
        elif cov and cov.get('status') in ('partial', 'complete', 'unknown', 'failed'):
            progress[feat] = cov.get('status')
            all_23_complete = False
        else:
            progress[feat] = 'unknown'
            all_23_complete = False

    if all_23_complete:
        return 'complete', None, progress
    return 'partial', 'incomplete_features', progress


def ingest(root,controls,*,resume=False,stop_after=100,command_factory,poll_seconds=.05):
    """Cumulative bounded extraction with cleanup across every launch boundary."""
    owned=[]
    try:
        return _ingest(root,controls,resume=resume,stop_after=stop_after,
                       command_factory=command_factory,poll_seconds=poll_seconds,_owned=owned)
    finally:
        for proc in owned:
            _kill_process_group(proc.pid);_ensure_no_descendants(proc.pid)
            proc.wait(timeout=5)
            for stream in (proc.stdin,proc.stdout,proc.stderr):
                if stream is not None:stream.close()


def _ingest(
    root: Path | str,
    controls: dict[str, Any],
    *,
    resume: bool = False,
    stop_after: int = 100,
    command_factory: Callable[[int, str, str], Sequence[str]],
    poll_seconds: float = 0.05,
    _owned: list,
) -> dict[str, Any]:
    """Ingest up to stop_after worlds from cohort under controls constraints.

    Returns strict finite JSON report mapping controls, receipts, and summary.
    """
    validate_controls(controls)
    if type(stop_after) is not int or not 0 <= stop_after <= 100:
        raise ValueError('stop_after must be in 0..100')
    if not isinstance(poll_seconds, (int,float)) or not 0.001 <= poll_seconds <= 1:
        raise ValueError('poll_seconds must be in .001..1')
    validate_identity(dict(controls['build']['identity'],seed=controls['cohort'][0]))
    root_path = verify_no_symlinks(root)
    root_path.mkdir(parents=True, exist_ok=True)
    verify_no_symlinks(root_path)

    controls_path = root_path / "controls.json"
    ledger_path = root_path / "ledger.json"

    with _flock_root(root_path):
        if not resume:
            if controls_path.exists() or ledger_path.exists():
                raise FileExistsError("Fresh root cannot overwrite existing controls.json or ledger.json; use resume=True")
            atomic_json(controls_path, controls)

            expected_cohort = controls['cohort']
            receipts = [
                {
                    "index": i,
                    "seed": str(seed),
                    "status": "pending",
                    "exit": None,
                    "stopreason": None,
                    "wall": 0.0,
                    "cpu": None,
                    "checkpoint": str(root_path / f"world_{i}_{seed}.json"),
                    "progress": {},
                    "peak_rss": 0,
                    "attempts": 0,
                }
                for i, seed in enumerate(expected_cohort)
            ]
            ledger = {
                "cumulative_extract_seconds": 0.0,
                "cumulative_job_seconds": 0.0,
                "active_lease": None,
                "receipts": receipts,
            }
            atomic_json(ledger_path, ledger)
        else:
            if not controls_path.exists() or not ledger_path.exists():
                raise FileNotFoundError("Cannot resume: controls.json or ledger.json not found in root")
            verify_no_symlinks(controls_path); verify_no_symlinks(ledger_path)
            stored_controls = strict_json_loads(controls_path.read_text(encoding='utf-8'))
            if canonical_json(stored_controls) != canonical_json(controls):
                raise ValueError("Controls mismatch on resume: stored controls do not match supplied controls")
            ledger = strict_json_loads(ledger_path.read_text(encoding='utf-8'))

            for index,(r,seed) in enumerate(zip(ledger['receipts'],controls['cohort'])):
                if r['index']!=index or r['seed'] != seed or Path(r['checkpoint']) != root_path / f"world_{r['index']}_{seed}.json":
                    raise ValueError('Receipt/cohort or checkpoint path mismatch')
            if len(ledger['receipts']) != 100:
                raise ValueError('Invalid receipt count')
            for key,limit in (('cumulative_extract_seconds',controls['extract_seconds']),('cumulative_job_seconds',controls['job_seconds'])):
                value=ledger[key]
                if type(value) not in (int,float) or not 0<=value<=limit:
                    raise ValueError('Invalid durable budget')

            # Check if active lease was left from an interrupted / crashed parent
            active_lease = ledger.get("active_lease")
            if active_lease:
                lease_pid = active_lease.get("pid")
                lease_pgid = active_lease.get("pgid")
                lease_idx = active_lease.get("index")
                is_alive = False
                if lease_pid:
                    try:
                        os.kill(lease_pid, 0)
                        is_alive = True
                    except ProcessLookupError:
                        is_alive = False
                    except PermissionError:
                        raise RuntimeError(
                            f"Active lease PID {lease_pid} is owned by another process/user; refusing to kill arbitrary PID"
                        )
                if is_alive:
                    if not _verify_process_ownership(lease_pid, lease_pgid, active_lease):
                        raise RuntimeError(
                            f"Active lease PID {lease_pid} is alive but creation metadata does not match owned process group; refusing to kill"
                        )
                    _kill_process_group(lease_pgid)
                    _ensure_no_descendants(lease_pgid)

                # Recover receipt for lease_idx
                # Conservative: crashed reservation is NOT refunded on resume!
                if 0 <= lease_idx < len(ledger["receipts"]):
                    r = ledger["receipts"][lease_idx]
                    ckpt = Path(r["checkpoint"])
                    if ckpt.exists():
                        try:
                            status, stopreason, progress = _validate_child_observation(
                                ckpt, r["seed"], controls['build']['identity']
                            )
                            r["status"] = status
                            r["stopreason"] = stopreason or "coordinator_interrupted"
                            r["progress"] = progress
                        except Exception as exc:
                            r["status"] = "failed"
                            r["stopreason"] = f"coordinator_interrupted: {type(exc).__name__}"
                    else:
                        r["status"] = "failed"
                        r["stopreason"] = "coordinator_interrupted"

                ledger["active_lease"] = None
                atomic_json(ledger_path, ledger)

        stopped_reason: str | None = None
        max_extract = float(controls['extract_seconds'])
        max_job = float(controls['job_seconds'])
        max_rss = int(controls['rss_bytes'])
        max_output = int(controls['output_bytes'])
        max_record = float(controls['record_seconds'])
        build_id = controls['build']['identity']

        if stop_after > 10:
            attempted_10 = [r for r in ledger["receipts"][:10] if r["attempts"] > 0]
            if len(attempted_10) == 10:
                timings = [r["wall"] for r in attempted_10 if r["wall"] > 0]
                worst_time = max(timings, default=0.0)
                median_time = statistics.median(timings) if timings else 0.0
                unit_time = max(worst_time, median_time)
                remaining_count = len(ledger["receipts"]) - 10
                projected_cost = remaining_count * unit_time
                rem_ext = max_extract - ledger["cumulative_extract_seconds"]
                rem_job = max_job - ledger["cumulative_job_seconds"]
                if projected_cost > rem_ext or projected_cost > rem_job:
                    stopped_reason = "budget_predicted"
                    return {"controls": controls, "receipts": ledger["receipts"], "summary": _summary(ledger, stopped_reason)}
        for idx, receipt in enumerate(ledger["receipts"]):
            if idx >= stop_after:
                stopped_reason = "stop_after"
                break

            # Never silently reuse a damaged completed checkpoint.
            if receipt["status"] == "complete":
                checkpoint=verify_no_symlinks(receipt['checkpoint'])
                if receipt.get('checkpoint_sha256') and hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=receipt['checkpoint_sha256']:
                    raise ValueError('Completed checkpoint checksum mismatch')
                status,_,_=_validate_child_observation(checkpoint,receipt['seed'],build_id)
                if status!='complete':raise ValueError('Completed checkpoint lost complete coverage')
                continue

            # Skip worlds that exceeded bounded retries (e.g. 2 attempts)
            if receipt["status"] in ("partial", "failed") and receipt["attempts"] >= 2:
                continue

            # Check remaining budget
            remaining_extract = max_extract - ledger["cumulative_extract_seconds"]
            remaining_job = max_job - ledger["cumulative_job_seconds"]
            if remaining_extract <= 0 or remaining_job <= 0:
                stopped_reason = "budget_exceeded"
                break

            reserve_amount = min(max_record, remaining_extract, remaining_job)
            if reserve_amount <= 0:
                stopped_reason = "budget_exceeded"
                break

            # Persist reservation BEFORE command construction/spawn. A child startup
            # gate prevents native work before its ownership lease is durable.
            # Conservative reservation before starting child process
            ledger["cumulative_extract_seconds"] += reserve_amount
            ledger["cumulative_job_seconds"] += reserve_amount
            receipt["status"] = "active"
            receipt["attempts"] += 1

            checkpoint_file = Path(receipt["checkpoint"])
            verify_no_symlinks(checkpoint_file.parent)
            if checkpoint_file.exists():
                verify_no_symlinks(checkpoint_file)

            argv = list(command_factory(idx, receipt["seed"], str(checkpoint_file)))

            atomic_json(ledger_path,ledger)
            ru_before = resource.getrusage(resource.RUSAGE_CHILDREN)
            start_wall = time.monotonic()

            proc = subprocess.Popen(
                [sys.executable, '-m', 'seed_search.catalog.ingestion', json.dumps(argv)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            _owned.append(proc)
            child_pid = proc.pid
            child_pgid = os.getpgid(child_pid)
            create_meta = _get_process_creation_meta(child_pid)

            ledger["active_lease"] = {
                "index": idx,
                "seed": receipt["seed"],
                "pid": child_pid,
                "pgid": child_pgid,
                "cmd": argv,
                "start_time": time.time(),
                "create_time": create_meta.get("create_time"),
                "reserved": reserve_amount,
            }
            try:
                atomic_json(ledger_path, ledger)
                if create_meta.get('create_time') is None:
                    raise RuntimeError('Child creation metadata unavailable')
                proc.stdin.write(b'G'); proc.stdin.flush(); proc.stdin.close()
            except BaseException:
                _kill_process_group(child_pgid); proc.wait(timeout=5)
                raise

            selector=selectors.DefaultSelector(); output_tail=bytearray(); stream_bytes=0
            for stream in (proc.stdout,proc.stderr):
                os.set_blocking(stream.fileno(),False); selector.register(stream,selectors.EVENT_READ)
            def drain():
                nonlocal stream_bytes
                for key,_ in selector.select(0):
                    data=os.read(key.fileobj.fileno(),65536)
                    if data:
                        stream_bytes+=len(data);output_tail.extend(data);del output_tail[:-65536]
                    else:selector.unregister(key.fileobj)
            child_stopreason: str | None = None
            peak_rss = 0
            output_bytes = 0

            try:
                while proc.poll() is None:
                    drain()
                    elapsed = time.monotonic() - start_wall

                    # 1. Wall timeout per world record
                    if elapsed >= reserve_amount or elapsed >= max_record:
                        child_stopreason = "wall_timeout"
                        _kill_process_group(child_pgid)
                        break

                    # 2. Cumulative budget check
                    cur_cumulative_extract = (ledger["cumulative_extract_seconds"] - reserve_amount) + elapsed
                    cur_cumulative_job = (ledger["cumulative_job_seconds"] - reserve_amount) + elapsed
                    if cur_cumulative_extract >= max_extract or cur_cumulative_job >= max_job:
                        child_stopreason = "budget_exceeded"
                        _kill_process_group(child_pgid)
                        break

                    # 3. Output byte cap check
                    output_bytes = max(_get_checkpoint_size(checkpoint_file),
                        tree_bytes(root_path)) + stream_bytes
                    if output_bytes > max_output:
                        child_stopreason = "output_limit"
                        _kill_process_group(child_pgid)
                        break

                    # 4. RSS check
                    agg_rss = _get_aggregate_rss(child_pid)
                    peak_rss = max(peak_rss, agg_rss)
                    if agg_rss > max_rss:
                        child_stopreason = "memory_limit"
                        _kill_process_group(child_pgid)
                        break

                    time.sleep(poll_seconds)

                _ensure_no_descendants(child_pgid)
                proc.wait(timeout=5)
                for _ in range(32):
                    if not selector.get_map(): break
                    drain()
                output_bytes += stream_bytes
                if output_bytes > max_output and child_stopreason is None:
                    child_stopreason = "output_limit"

                exit_code = proc.returncode
                elapsed_wall = time.monotonic() - start_wall
                ru_after = resource.getrusage(resource.RUSAGE_CHILDREN)
                cpu_time = (ru_after.ru_utime - ru_before.ru_utime) + (ru_after.ru_stime - ru_before.ru_stime)

            except BaseException as exc:
                _kill_process_group(child_pgid)
                _ensure_no_descendants(child_pgid)
                proc.wait(timeout=5)
                receipt["status"] = "failed"
                receipt["stopreason"] = f"exception: {type(exc).__name__}"
                ledger["active_lease"] = None
                atomic_json(ledger_path, ledger)
                raise
            finally:
                selector.close();proc.stdout.close();proc.stderr.close()

            _ensure_no_descendants(child_pgid)

            _owned.clear()

            # Refund unused reservation on normal completion of world run
            refund = max(0.0, reserve_amount - elapsed_wall)
            ledger["cumulative_extract_seconds"] -= refund
            ledger["cumulative_job_seconds"] -= refund
            ledger["active_lease"] = None

            # Validate checkpoint
            world_status = "failed"
            world_progress: dict[str, str] = {}
            if not checkpoint_file.exists():
                world_status = "failed"
                world_stopreason = child_stopreason or (f"exit_{exit_code}" if exit_code != 0 else "missing_checkpoint")
            else:
                try:
                    v_status, v_reason, v_progress = _validate_child_observation(
                        checkpoint_file, receipt["seed"], build_id
                    )
                    world_progress = v_progress
                    if v_status == "complete" and exit_code == 0 and child_stopreason is None:
                        world_status = "complete"
                        world_stopreason = None
                    else:
                        world_status = "partial"
                        world_stopreason = child_stopreason or v_reason or (f"exit_{exit_code}" if exit_code != 0 else None)
                except Exception as exc:
                    world_status = "failed"
                    world_stopreason = child_stopreason or f"invalid_observation: {type(exc).__name__}"

            receipt["status"] = world_status
            receipt["exit"] = exit_code
            receipt["stopreason"] = world_stopreason
            receipt["wall"] = round(elapsed_wall, 4)
            receipt["cpu"] = round(cpu_time, 4)
            receipt["progress"] = world_progress
            receipt["peak_rss"] = peak_rss
            receipt['checkpoint_sha256'] = hashlib.sha256(checkpoint_file.read_bytes()).hexdigest() if checkpoint_file.exists() else None
            receipt['output_bytes'] = stream_bytes
            receipt['output_tail'] = output_tail.decode('utf-8',errors='replace')

            atomic_json(ledger_path, ledger)

            if child_stopreason in ('budget_exceeded','memory_limit','output_limit'):
                stopped_reason = child_stopreason
                break

        summary = _summary(ledger,stopped_reason)

        report = {
            "controls": controls,
            "receipts": ledger["receipts"],
            "summary": summary,
        }
        return report


def _summary(ledger, stopped_reason):
    counts={status:sum(r['status']==status for r in ledger['receipts'])
            for status in ('complete','partial','failed','pending','active')}
    return dict(total_seeds=len(ledger['receipts']),completed=counts.pop('complete'),**counts,
                cumulative_extract_seconds=round(ledger['cumulative_extract_seconds'],4),
                cumulative_job_seconds=round(ledger['cumulative_job_seconds'],4),stopped_reason=stopped_reason)


if __name__ == '__main__':
    # Private gated launch. EOF before durable lease prevents untracked extraction.
    command=json.loads(sys.argv[1])
    if sys.stdin.buffer.read(1) != b'G':raise SystemExit(3)
    resource.setrlimit(resource.RLIMIT_FSIZE,(16<<20,16<<20))
    os.execvpe(command[0],command,os.environ)
