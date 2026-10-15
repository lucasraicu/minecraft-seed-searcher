"""
Web UI Backend Server for Bedrock Seed Searcher.
Serves static frontend assets and provides live sweep orchestration APIs.
Endpoints:
  POST /api/sweep/start   - Spawns real native C11 OpenMP seed sweep
  GET  /api/sweep/status  - Live telemetry, seeds/sec, progress, candidates, logs
  POST /api/sweep/stop    - Terminates running sweep subprocess
  GET  /api/candidates    - Retrieves discovered candidates
  GET  /api/system/info   - Hardware and engine specs
"""

import http.server
import json
import math
import os
import platform
import re
import resource
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yaml

from seed_search.realm.config import dynamic_blueprint_config, marine_baseline_blueprint_config, two_group_blueprint_config, validate_config
from seed_search.realm.runner import process_tree_resources

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DIST_DIR = PROJECT_ROOT / "web-ui" / "dist"
RUNS_DIR = PROJECT_ROOT / "runs"
DEFAULT_NATIVE_BUILD = Path(os.environ.get('SEED_SEARCH_NATIVE_BUILD', str(PROJECT_ROOT / 'runs' / 'dynamic-baseline-1664' / 'native')))


class SweepManager:
    """Manages the background seed search scan process and aggregates live telemetry."""

    def __init__(self):
        self.lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.run_id: str | None = None
        self.run_dir: Path | None = None
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.target_count: int = 10000000
        self.scanned_count: int = 0
        self.resume_baseline = 0
        self.start_index = 0
        self.seeds_per_sec: float = 0.0
        self.status: str = "idle"  # idle | running | completed | stopped | error
        self.error_message: str | None = None
        self.logs: list[str] = [
            f"Server initialized. Native build: {DEFAULT_NATIVE_BUILD}",
            f"Host: {platform.processor() or platform.machine()} • target Bedrock 26.52 predictor",
        ]
        self.candidates: list[dict] = []
        self.history: list[int] = [0] * 12
        self.monitor_thread: threading.Thread | None = None
        self.generation = 0
        self.threads = 0
        self.effective_config: dict | None = None
        self._runs_cache: dict[str, tuple[tuple[float, float], dict, int, dict]] = {}
        self._biome_grid_cache: dict = {}
        self._bind_latest_run()

    def _view_run(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r'web-sweep-[0-9]{8}-[0-9]{6}(?:-[0-9a-f]{8})?', run_id):
            raise ValueError('Invalid saved run ID')
        directory = RUNS_DIR / run_id
        db = directory / 'realm.sqlite'
        if directory.is_symlink() or directory.resolve().parent != RUNS_DIR.resolve() or db.is_symlink() or not db.is_file():
            raise ValueError('Saved checkpoint must be a direct run directory')
        with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as conn:
            values = {key: json.loads(value) for key, value in conn.execute(
                "SELECT key,value FROM meta WHERE key IN ('identity','completed_seeds')")}
        identity = values.get('identity')
        if not isinstance(identity, dict):
            raise ValueError('Saved checkpoint identity is unavailable')
        count, first, completed = identity.get('count'), identity.get('start_index'), values.get('completed_seeds', 0)
        if (type(count) is not int or count < 1 or type(first) is not int or first < 0
                or first + count > 2**64 or type(completed) is not int or not 0 <= completed <= count):
            raise ValueError('Invalid saved range')
        return directory, identity, completed

    def _bind_latest_run(self):
        if not RUNS_DIR.exists():
            return
        entries = sorted((p for p in RUNS_DIR.glob('web-sweep-*') if p.is_dir()), key=lambda p: p.name, reverse=True)
        for directory in entries:
            result = self.select_run(directory.name)
            if result['ok']:
                break

    def select_run(self, run_id: str) -> dict:
        with self.lock:
            if ((self.process is not None and self.process.poll() is None) or self.status == 'stopping'):
                return {'ok': False, 'error': 'Stop active processing before switching runs'}
            try:
                directory, identity, completed = self._view_run(run_id)
            except (ValueError, TypeError, OSError, sqlite3.Error) as exc:
                return {'ok': False, 'error': str(exc)}
            self.run_dir, self.run_id = directory, run_id
            self.target_count, self.start_index = identity['count'], identity['start_index']
            self.scanned_count = completed
            self.effective_config = identity.get('config')
            self.status = 'completed' if completed == self.target_count else 'paused'
            self.start_time = self.end_time = self.seeds_per_sec = 0
            self.error_message = None
            self.generation += 1
            self.candidates = []
            self._last_candidates_sig = None
            self._query_sqlite_progress()
            self._query_sqlite_candidates()
            self.logs.insert(0, f'Viewing {run_id}: {completed:,} durable inputs')
            return {'ok': True, 'runId': run_id, 'status': self.status, 'scannedCount': completed}

    def start_sweep(
        self,
        count: int = 10000000,
        threads: int = 34,
        batch_size: int = 16384,
        max_misses: int = 2,
        counts: dict | None = None,
        start_index: int | str = 0,
        profile: str = 'dynamic1664',
    ) -> dict:
        try:
            if any(type(v) is not int for v in (count,threads,batch_size,max_misses)):
                raise ValueError('Sweep controls must be integers')
            if isinstance(start_index,str) and re.fullmatch(r'[0-9]{1,20}',start_index):start_index=int(start_index)
            if type(start_index) is not int or not 0<=start_index<2**64 or start_index+count>2**64:
                raise ValueError('Invalid full64 starting index or range')
            if not 1<=count<=2**53-1 or not 1<=threads<=34 or not 1<=batch_size<=16384 or not 0<=max_misses<=8:
                raise ValueError('Sweep controls outside supported bounded ranges')
            if counts is not None and (not isinstance(counts,dict) or not all(isinstance(k,str) and type(v) is int for k,v in counts.items())):
                raise ValueError('counts must map structure names to integer ideals')
            profiles={'dynamic1664':dynamic_blueprint_config,'marine2048':marine_baseline_blueprint_config,'twoGroup2048':two_group_blueprint_config}
            if profile not in profiles:raise ValueError('Unknown search profile')
            cfg=profiles[profile]()
            cfg['search']['max_misses']=max_misses
            allowed=set(cfg['structures']['minimum_counts'])|set(cfg['structures']['nether_minimum_counts'])
            if counts and set(counts)-allowed:raise ValueError('Unsupported structure count key')
            for key,value in (counts or {}).items():
                group='nether_minimum_counts' if key in cfg['structures']['nether_minimum_counts'] else 'minimum_counts'
                cfg['structures'][group][key]=value
            validate_config(cfg)
            if not (DEFAULT_NATIVE_BUILD/'identity.json').is_file():raise ValueError('Native search build is unavailable; rebuild the active engine')
            from seed_search.realm.native_batch import Prototype
            Prototype(DEFAULT_NATIVE_BUILD,cfg)
            from seed_search.realm.resources import disk_policy
            limits=disk_policy(cfg['search'],retention='survivors')
            projected=count*limits['projected_bytes_per_seed']
            free=shutil.disk_usage(RUNS_DIR if RUNS_DIR.exists() else PROJECT_ROOT).free
            if projected>limits['run_disk_limit_bytes'] or free<limits['free_disk_reserve_bytes']+projected:
                raise ValueError('Projected finite shard exceeds disk budget; use a smaller shard')
        except (ValueError,KeyError,TypeError,OSError,ImportError,RuntimeError) as exc:
            return {'ok':False,'error':str(exc)}
        with self.lock:
            if (self.process is not None and self.process.poll() is None) or self.status == "stopping":
                return {
                    "ok": False,
                    "error": "A sweep is already actively running" if self.status != "stopping" else "A sweep is currently stopping",
                    "runId": self.run_id,
                }

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.run_id = f"web-sweep-{timestamp}-{uuid.uuid4().hex[:8]}"
            self.run_dir = RUNS_DIR / self.run_id
            dir_created = False
            try:
                self.run_dir.mkdir(parents=True, exist_ok=True)
                dir_created = True
                policy_path = self.run_dir / 'policy.yaml'
                policy_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
                self.effective_config = cfg
                self.threads = threads
                self.generation += 1
                generation = self.generation
                self.target_count = count
                self.scanned_count = 0
                self.resume_baseline = 0
                self.start_index = start_index
                self.history = [0] * 12
                self.seeds_per_sec = 0.0
                self.status = "running"
                self.error_message = None
                self.start_time = time.time()
                self.end_time = 0.0
                self.candidates = []

                # Choose python executable
                venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
                python_bin = str(venv_python) if venv_python.exists() else sys.executable

                cmd = [
                    python_bin,
                    "-m",
                    "seed_search",
                    "--config",
                    str(policy_path),
                    "scan",
                    "--count",
                    str(count),
                    "--start-index",
                    str(start_index),
                    "--output",
                    str(self.run_dir),
                    "--executor",
                    "native",
                    "--native-build",
                    str(DEFAULT_NATIVE_BUILD),
                    "--native-threads",
                    str(threads),
                    "--native-batch-size",
                    str(batch_size),
                    "--retention",
                    "survivors",
                    "--max-misses",
                    str(max_misses),
                    "--prediction-scale",
                ]

                env = os.environ.copy()
                src_path = str(PROJECT_ROOT / "src")
                env["PYTHONPATH"] = (
                    f"{src_path}:{env.get('PYTHONPATH', '')}"
                    if "PYTHONPATH" in env
                    else src_path
                )

                msg = f"Spawning native sweep: {count:,} seeds across {threads} OpenMP threads (batch={batch_size})"
                self.logs.insert(0, msg)

                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                self.monitor_thread = threading.Thread(
                    target=self._monitor_process, args=(self.process, self.run_dir, generation), daemon=True
                )
                self.monitor_thread.start()

                return {
                    "ok": True,
                    "runId": self.run_id,
                    "status": "running",
                    "effectiveConfig": cfg,
                    "command": cmd,
                }
            except Exception as e:
                self.status = "error"
                self.error_message = str(e)
                self.process = None
                self.logs.insert(0, f"Failed to start sweep: {e}")
                if dir_created and self.run_dir and self.run_dir.exists():
                    shutil.rmtree(self.run_dir, ignore_errors=True)
                return {"ok": False, "error": str(e)}

    def _saved_run(self, run_id):
        if not isinstance(run_id,str) or not re.fullmatch(r"web-sweep-[0-9]{8}-[0-9]{6}-[0-9a-f]{8}",run_id):
            raise ValueError("Invalid saved run ID")
        directory=RUNS_DIR/run_id
        if directory.is_symlink() or directory.resolve().parent!=RUNS_DIR.resolve():
            raise ValueError("Saved run must be a direct run directory")
        db=directory/'realm.sqlite'
        if not db.is_file() or db.is_symlink():raise ValueError("Saved checkpoint is unavailable")
        with sqlite3.connect(f"file:{db}?mode=ro",uri=True) as conn:
            values={key:json.loads(value) for key,value in conn.execute(
                "SELECT key,value FROM meta WHERE key IN ('identity','completed_seeds','native_pipeline')")}
        identity=values.get('identity')
        if not isinstance(identity,dict) or identity.get('execution')!='native':
            raise ValueError("Saved run is not a native sweep")
        cfg=identity['config'];validate_config(cfg)
        count=identity['count'];first=identity['start_index'];completed=values.get('completed_seeds',0)
        if (type(count) is not int or not 1<=count<=2**53-1 or type(first) is not int
                or not 0<=first<2**64 or first+count>2**64 or type(completed) is not int
                or not 0<=completed<=count):raise ValueError("Invalid saved range")
        from seed_search.realm.native_batch import Prototype
        from seed_search.realm.cli import make_identity
        from seed_search.realm.store import semantic_identity
        build=identity.get('native_build')
        if not build or Path(build).resolve()!=DEFAULT_NATIVE_BUILD.resolve():
            raise ValueError("Saved sweep uses a different native build")
        prototype=Prototype(DEFAULT_NATIVE_BUILD,cfg)
        current=make_identity(cfg,count,first)
        current.update(execution='native',native=prototype.identity,native_build=str(DEFAULT_NATIVE_BUILD.resolve()),
                       evaluator='seed_search.realm.native_batch:run_native_scan',retention=identity.get('retention'))
        if semantic_identity(current)!=semantic_identity(identity):
            raise ValueError("Saved sweep configuration or computation identity changed")
        return directory,identity,completed,values.get('native_pipeline') or {}

    def list_runs(self):
        runs=[]
        if not RUNS_DIR.exists():return {'runs':runs}
        entries=sorted((p for p in RUNS_DIR.glob('web-sweep-*') if p.is_dir()),key=lambda p:p.name,reverse=True)[:50]
        for directory in entries:
            try:
                dir_mtime = directory.stat().st_mtime
                db_path = directory / 'realm.sqlite'
                db_mtime = db_path.stat().st_mtime if db_path.is_file() else 0.0
                wal = directory / 'realm.sqlite-wal'
                cache_key = (dir_mtime, db_mtime, wal.stat().st_mtime_ns if wal.exists() else 0)
                cached = self._runs_cache.get(directory.name)
                if cached is not None and cached[0] == cache_key:
                    _, identity, completed, pipeline = cached
                else:
                    _, identity, completed, pipeline = self._saved_run(directory.name)
                    self._runs_cache[directory.name] = (cache_key, identity, completed, pipeline)
                runs.append({'runId':directory.name,'completedSeeds':completed,'targetCount':identity['count'],
                             'startIndex':str(identity['start_index']),
                             'resumable':completed<identity['count'] and not (self.status=='running' and directory==self.run_dir)})
            except (ValueError,KeyError,TypeError,OSError,ImportError,sqlite3.Error):
                self._runs_cache.pop(directory.name, None)
                continue
        return {'runs':runs}

    def resume_sweep(self, run_id):
        with self.lock:
            if not run_id:
                return {'ok': False, 'error': 'No run specified to continue'}
            if (self.process is not None and self.process.poll() is None) or self.status == 'stopping':
                return {'ok':False,'error':'A sweep is already actively running' if self.status != 'stopping' else 'A sweep is currently stopping','runId':self.run_id}
            try:
                directory,identity,completed,pipeline=self._saved_run(run_id)
                if completed>=identity['count']:raise ValueError('Saved sweep is already complete')
                from seed_search.realm.resources import disk_policy,disk_status
                disk_status(directory,disk_policy(identity['config']['search'],retention=identity.get('retention',{}).get('mode','full')),remaining_seeds=identity['count']-completed)
                threads=pipeline.get('threads',34)
                if type(threads) is not int or not 1<=threads<=34:raise ValueError('Invalid saved thread count')
                self.run_id=run_id;self.run_dir=directory;self.target_count=identity['count']
                self.start_index=identity['start_index'];self.scanned_count=completed;self.resume_baseline=completed
                self.effective_config=identity['config'];self.threads=threads;self.generation+=1
                self.start_time=time.time();self.end_time=0.;self.seeds_per_sec=0.;self.history=[0]*12
                self.status='running';self.error_message=None
                self._last_candidates_sig=None
                self._query_sqlite_candidates()
                python=PROJECT_ROOT/'.venv'/'bin'/'python'
                cmd=[str(python) if python.exists() else sys.executable,'-m','seed_search','resume',
                     '--run',str(directory),'--native-build',str(DEFAULT_NATIVE_BUILD),'--prediction-scale']
                env=os.environ.copy();env['PYTHONPATH']=str(PROJECT_ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
                self.process=subprocess.Popen(cmd,cwd=str(PROJECT_ROOT),env=env,stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE,text=True)
                self.logs.insert(0,f'Continuing sweep {run_id} from seed {completed:,}...')
                self.monitor_thread=threading.Thread(target=self._monitor_process,
                    args=(self.process,directory,self.generation),daemon=True)
                self.monitor_thread.start()
                return {'ok':True,'runId':run_id,'status':'running','effectiveConfig':self.effective_config,'command':cmd}
            except (ValueError,KeyError,TypeError,OSError,ImportError,sqlite3.Error,RuntimeError) as exc:
                if self.status=='running':self.status='error';self.error_message=str(exc)
                return {'ok':False,'error':str(exc)}

    def pause_sweep(self) -> dict:
        """Pauses the active sweep gracefully, letting the active batch/seed complete before stopping."""
        with self.lock:
            proc = self.process
            if proc is None or proc.poll() is not None or self.status not in ("running",):
                return {"ok": False, "error": "No active sweep to pause"}
            self.status = "paused"
            self.logs.insert(0, "Pausing sweep: waiting for current seed/batch to complete cleanly...")
            try:
                import signal
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=6.0)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
            except Exception as exc:
                self.status = 'error'
                self.error_message = f'Failed to pause owned process: {exc}'
                return {'ok': False, 'error': self.error_message}
            if proc.poll() is None:
                self.status = 'error'
                return {'ok': False, 'error': 'Owned scan has not exited'}
            self.status = 'paused'
            self.process = None
            self._query_sqlite_progress()
            self._query_sqlite_candidates()
            self.logs.insert(0, f'Sweep paused at {self.scanned_count:,} durable inputs; unfinished leases remain retryable')
            return {'ok': True, 'status': 'paused', 'scannedCount': self.scanned_count, 'runId': self.run_id}

    def _monitor_process(self,proc,run_dir,generation):
        """Reads stdout/stderr asynchronously and updates progress."""
        if not proc or not proc.stdout or not proc.stderr:
            return
        stdout_chunks = []
        stderr_chunks=[]
        def drain(stream,output):
            for line in stream:
                output.append(line)
                if len(output)>200:del output[:-200]
        out_thread=threading.Thread(target=drain,args=(proc.stdout,stdout_chunks),daemon=True)
        err_thread=threading.Thread(target=drain,args=(proc.stderr,stderr_chunks),daemon=True)
        out_thread.start();err_thread.start()
        proc.wait()
        out_thread.join();err_thread.join()

        with self.lock:
            if generation!=self.generation or run_dir!=self.run_dir:return
            self.end_time = time.time()
            elapsed = max(0.001, self.end_time - self.start_time)
            # Sync from SQLite
            self._query_sqlite_progress()
            self._query_sqlite_candidates()
            self.seeds_per_sec=round(max(0,self.scanned_count-self.resume_baseline)/elapsed)
            self._record_throughput(self.seeds_per_sec)

            if proc.returncode == 0 and self.status not in ("paused", "stopped", "stopping"):
                self.status = "completed"
                self.logs.insert(
                    0,
                    f"Sweep complete! Scanned {self.scanned_count:,} seeds in {elapsed:.2f}s ({self.seeds_per_sec:,} seeds/s)",
                )
            else:
                if self.status not in ("stopped", "paused"):
                    self.status = "error"
                    err_text = "".join(stderr_chunks).strip()
                    self.error_message = err_text[-1000:] or f"Process exited with code {proc.returncode}"
                    self.logs.insert(
                        0,
                        f"Process exited with code {proc.returncode}. {err_text[:200]}",
                    )

    def _query_sqlite_progress(self):
        """Queries realm.sqlite for exact progress."""
        if not self.run_dir:
            return
        db_path = self.run_dir / "realm.sqlite"
        if not db_path.exists():
            return
        conn = None
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT value FROM meta WHERE key = 'completed_seeds'")
            row = cur.fetchone()
            if row and row[0]:
                self.scanned_count = int(row[0])
        except Exception:
            pass
        finally:
            if conn:
                try: conn.close()
                except Exception: pass

    def _record_throughput(self, rate: int):
        self.history.append(rate)
        if len(self.history) > 20:
            self.history.pop(0)

    def stop_sweep(self) -> dict:
        with self.lock:
            proc = self.process
            if proc is None and self.status == 'paused':
                self.status = 'stopped'
                return {'ok': True, 'status': 'stopped'}
            if proc is None or proc.poll() is not None or self.status in ("stopped", "stopping"):
                return {"ok": False, "error": "No active sweep to stop"}
            verifying=self.status=='bds_verifying'
            self.status = "stopping"
            self.logs.insert(0, "Stopping owned verification job." if verifying else "Sweep stopped by user.")
            try:
                if verifying:
                    import signal
                    proc.send_signal(signal.SIGINT)
                    try:proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:proc.kill()
                else:proc.kill()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    pass
            except Exception as exc:
                self.status = 'error'
                self.error_message = f'Failed to stop owned process: {exc}'
                self.logs.insert(0, self.error_message)
                return {'ok': False, 'error': self.error_message}
            if proc.poll() is None:
                self.status = 'error'
                self.error_message = 'Owned process has not exited; retry stop before starting another run'
                return {'ok': False, 'error': self.error_message}
            self.status = 'stopped'
            self.process = None
            return {'ok': True, 'status': 'stopped'}

    def _query_sqlite_candidates(self):
        """Extracts candidates from the active or latest run's SQLite file."""
        if not self.run_dir:
            return
        db_path = self.run_dir / "realm.sqlite"
        if not db_path.exists():
            return

        conn = None
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()

            # Dirtiness check before re-parsing
            cur.execute("SELECT count(*), max(rowid) FROM candidates")
            cand_sig = cur.fetchone()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='variants'")
            has_variants = bool(cur.fetchone())
            var_sig = None
            if has_variants:
                cur.execute("SELECT count(*), max(rowid) FROM variants")
                var_sig = cur.fetchone()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='observations'")
            has_obs = bool(cur.fetchone())
            obs_sig = None
            if has_obs:
                cur.execute("SELECT count(*), max(rowid) FROM observations")
                obs_sig = cur.fetchone()

            sig = (str(self.run_dir), cand_sig, var_sig, obs_sig)
            if getattr(self, '_last_candidates_sig', None) == sig and self.candidates:
                return
            self._last_candidates_sig = sig

            from seed_search.realm.leaderboard import order_for
            order = order_for(conn)
            cur.execute(f"""
                SELECT id, seed, smart_score, result,
                       ranking_tier, unmet_requirements
                FROM candidate_leaderboard_view
                ORDER BY {order} LIMIT 250
            """)
            top_rows = cur.fetchall()

            v_map = {}
            if has_variants and top_rows:
                top_ids = [row[0] for row in top_rows]
                placeholders = ','.join('?' for _ in top_ids)
                cur.execute(f"""
                    SELECT candidate_id,
                           json_extract(result, '$.result.geometry_pass') as geometry_pass,
                           json_extract(result, '$.result.geometry_score') as geometry_score,
                           json_extract(result, '$.result.metrics.mainland_fraction') as mainland_fraction,
                           json_extract(result, '$.result.reasons') as reasons,
                           json_extract(result, '$.result.metrics') as raw_metrics
                    FROM variants
                    WHERE (variant = 'v1' OR variant = 'coastal') AND candidate_id IN ({placeholders})
                    ORDER BY geometry_pass DESC, geometry_score DESC
                """, top_ids)
                for cid, g_pass, g_score, m_frac, r_reasons, r_metrics in cur.fetchall():
                    if cid in v_map: continue
                    if g_pass == 1:
                        st = 'passed'
                    elif g_pass == 0 and (g_score is not None and g_score >= 50.0 or (m_frac is not None and m_frac >= 0.50)):
                        st = 'near_miss'
                    elif g_pass == 0:
                        st = 'failed'
                    else:
                        st = 'pending'
                    try:
                        reasons_list = json.loads(r_reasons) if r_reasons else []
                    except Exception:
                        reasons_list = []
                    try:
                        m_obj = json.loads(r_metrics) if r_metrics else {}
                    except Exception:
                        m_obj = {}

                    t_metrics = None
                    if m_obj or m_frac is not None:
                        t_metrics = {
                            'mainlandFraction': round(float(m_obj.get('mainland_fraction', m_frac)), 3) if m_frac is not None else None,
                            'oceanEdge': m_obj.get('ocean_edges'),
                            'flatAreaBlocks': m_obj.get('flat_area_blocks'),
                            'riverCorridor': m_obj.get('river_corridor_model_pass') or m_obj.get('river_highway_connected'),
                        }

                    v_map[cid] = {
                        'status': st,
                        'geometry_score': g_score,
                        'reasons': reasons_list,
                        'mainland_fraction': m_frac,
                        'metrics': t_metrics,
                    }

            parsed = []
            for cid, seed, score, raw_res, ranking_tier, unmet_reqs in top_rows:
                v_info = v_map.get(cid, {})
                cand = parse_candidate_row(
                    seed, score, raw_res,
                    has_terrain_pass=v_info.get('status', 'pending'),
                    ranking_tier=ranking_tier,
                    unmet_requirements=unmet_reqs,
                    terrain_geometry_score=v_info.get('geometry_score'),
                    terrain_reasons=v_info.get('reasons'),
                    terrain_mainland_fraction=v_info.get('mainland_fraction'),
                    terrain_metrics_arg=v_info.get('metrics'),
                )
                if cand:
                    parsed.append(cand)

            self.candidates = parsed
        except Exception as e:
            self.logs.insert(0, f"Error reading candidates DB: {e}")
        finally:
            if conn:
                try: conn.close()
                except Exception: pass

    def get_status(self) -> dict:
        with self.lock:
            now = time.time()
            if self.status == "running":
                elapsed = max(0, now - self.start_time)
                self._query_sqlite_progress()
                self._query_sqlite_candidates()
                if self.status == "running":
                    self.seeds_per_sec=round(max(0,self.scanned_count-self.resume_baseline)/max(0.001,elapsed))
                else:
                    self.seeds_per_sec = 0
            elif self.end_time > 0:
                elapsed = self.end_time - self.start_time
                if self.scanned_count == 0 and self.run_dir:
                    self._query_sqlite_progress()
            else:
                elapsed = 0

            active_pid = getattr(self.process, 'pid', None) if self.status == 'running' and self.process is not None and self.process.poll() is None else None
            resources = process_tree_resources(active_pid) if active_pid is not None else {'available': False}
            if resources.get('available'):
                rss_gib = round(resources['rss_bytes'] / (1024**3), 3)
            else:
                rss_gib = None

            progress_pct = (
                round((self.scanned_count / max(1, self.target_count)) * 100, 1)
                if self.target_count > 0
                else 0
            )

            return {
                "status": self.status,
                "error": self.error_message,
                "runId": self.run_id,
                "totalScanned": self.scanned_count,
                "targetCount": self.target_count,
                "startIndex": str(self.start_index),
                "resumedFrom": self.resume_baseline,
                "seedsPerSec": self.seeds_per_sec,
                "elapsedSeconds": round(elapsed, 1),
                "candidatesFound": len(self.candidates),
                "candidateScope": "bounded displayed pool: top 250 baseline records",
                "sweepProgress": min(100.0, progress_pct),
                "memoryRssGib": rss_gib,
                "activeThreads": self.threads if self.status == "running" else 0,
                "throughputScope":"new durable SQLite completed inputs / current invocation wall seconds",
                "effectiveConfig":self.effective_config,
                "history": list(self.history),
                "logs": self.logs[:30],
                "candidates": self.candidates,
            }

    def verify_bds_candidate(self, seed: str | int | None = None, candidate_id: str | None = None) -> dict:
        """Start an owned real surface-point job; never promote Realm eligibility."""
        with self.lock:
            point_path=None
            if (self.process is not None and self.process.poll() is None) or self.status in ('stopping','bds_verifying'):
                return {'ok':False,'error':'Pause active processing before verifying a candidate'}
            try:
                if not self.run_dir or not (self.run_dir/'realm.sqlite').is_file():
                    raise ValueError('Select a saved run first')
                if not isinstance(candidate_id,str) or not candidate_id:
                    raise ValueError('An exact candidateId is required')
                from seed_search.seeds import parse_seed
                with sqlite3.connect(f'file:{self.run_dir / "realm.sqlite"}?mode=ro',uri=True) as conn:
                    row=conn.execute('SELECT result FROM candidates WHERE id=?',(candidate_id,)).fetchone()
                if not row:raise ValueError('Candidate does not belong to the selected run')
                candidate=json.loads(row[0])
                if seed is not None and parse_seed(seed)!=parse_seed(candidate['seed']):
                    raise ValueError('Seed and candidate identity differ')
                if candidate.get('qualification') not in ('PREDICTED','VERIFIED'):
                    raise ValueError('Candidate must pass the predictor baseline first')
                witnesses=(candidate.get('biomes') or {}).get('witnesses') or {}
                points=sorted({(p[0],p[2]) for w in witnesses.values()
                               if isinstance(w,dict) and isinstance(p:=w.get('coordinate'),list)
                               and len(p)==3 and p[1]==63 and all(type(v) is int for v in p)})[:16]
                if not points:raise ValueError('Candidate has no explicit Y=63 witness points to verify')
                # The CLI revalidates containment, image/tooling identity, attempt budget,
                # provider locking and cache identity before publishing observations.
                point_path=self.run_dir/f'web-surface-points-{uuid.uuid4().hex}.json'
                point_path.write_text(json.dumps(points)+'\n')
                python=PROJECT_ROOT/'.venv'/'bin'/'python'
                cmd=[str(python) if python.exists() else sys.executable,'-m','seed_search',
                     'verify-biomes','--run',str(self.run_dir),'--candidate',candidate_id,'--points',str(point_path)]
                env=os.environ.copy();env['PYTHONPATH']=str(PROJECT_ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
                previous=self.status
                self.generation+=1
                proc=subprocess.Popen(cmd,cwd=str(PROJECT_ROOT),env=env,stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT,text=True)
                self.process=proc;self.status='bds_verifying';self.error_message=None
                self.logs.insert(0,f'BDS surface job started for {candidate_id}: {len(points)} explicit points')
                self.monitor_thread=threading.Thread(target=self._monitor_verification,
                    args=(proc,self.run_dir,self.generation,previous,point_path),daemon=True)
                self.monitor_thread.start()
                return {'ok':True,'status':'bds_verifying','candidateId':candidate_id,'points':len(points),
                        'scope':'Surface point observations only; structures, loot, portal room and player spawn remain unverified'}
            except (ValueError,TypeError,KeyError,OSError,sqlite3.Error) as exc:
                if point_path is not None:point_path.unlink(missing_ok=True)
                return {'ok':False,'error':str(exc)}

    def _monitor_verification(self,proc,run_dir,generation,previous,point_path):
        # Drain continuously with bounded memory so a verbose Docker failure cannot
        # block the worker or exhaust the web process. The provider owns timeouts.
        output=[]
        try:
            if proc.stdout:
                for line in proc.stdout:
                    output.append(line[-2000:])
                    if len(output)>40:del output[:-40]
            code=proc.wait()
            with self.lock:
                if generation!=self.generation or run_dir!=self.run_dir or self.process is not proc:return
                self.process=None
                if self.status=='bds_verifying':self.status=previous
                self._last_candidates_sig = None
                self._query_sqlite_candidates()
                if code:
                    self.error_message=''.join(output)[-2000:] or f'BDS surface job exited {code}'
                    self.logs.insert(0,'BDS surface job failed; no Realm certification was issued: '+self.error_message[-300:])
                else:
                    self.logs.insert(0,'BDS surface job finished; inspect measured point evidence. Full Realm verification remains pending.')
        finally:
            point_path.unlink(missing_ok=True)


def parse_candidate_row(
    seed: str,
    score: float,
    raw_res: str,
    has_terrain_pass: bool | str | None = 'pending',
    ranking_tier: int | None = None,
    unmet_requirements: int | None = None,
    terrain_geometry_score: float | None = None,
    terrain_reasons: list | None = None,
    terrain_mainland_fraction: float | None = None,
    terrain_metrics_arg: dict | None = None,
) -> dict | None:
    """Parses a candidate row into the full Web UI SeedCandidate schema."""
    try:
        data = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    req_overworld = (data.get("required_structures") or {})
    req_nether = (data.get("required_nether_structures") or {})
    opt_structures = (data.get("optional_structures") or {})
    actual_strongholds = req_overworld.get('stronghold', {}).get('predicted_viable', [])
    stronghold = actual_strongholds[0] if actual_strongholds else None
    center = data.get('evaluation_center')
    if not isinstance(center, list) or len(center) != 2:
        center = [0, 0]

    STRUCTURE_METAS = {
        "stronghold": {"name": "Stronghold Portal", "icon": "🏰", "color": "#10b981", "dim": "overworld"},
        "mansion": {"name": "Woodland Mansion", "icon": "🏛️", "color": "#8b5cf6", "dim": "overworld"},
        "village": {"name": "Village", "icon": "🏡", "color": "#f59e0b", "dim": "overworld"},
        "trial_chamber": {"name": "Trial Chamber", "icon": "⚔️", "color": "#eab308", "dim": "overworld"},
        "ancient_city": {"name": "Ancient City", "icon": "🏙️", "color": "#06b6d4", "dim": "overworld"},
        "outpost": {"name": "Pillager Outpost", "icon": "🏹", "color": "#f43f5e", "dim": "overworld"},
        "desert_pyramid": {"name": "Desert Pyramid", "icon": "🏺", "color": "#e0a96d", "dim": "overworld"},
        "pyramid": {"name": "Desert Pyramid", "icon": "🏺", "color": "#e0a96d", "dim": "overworld"},
        "jungle_temple": {"name": "Jungle Temple", "icon": "🌿", "color": "#22c55e", "dim": "overworld"},
        "monument": {"name": "Ocean Monument", "icon": "🏛️", "color": "#0ea5e9", "dim": "overworld"},
        "ruined_portal": {"name": "Ruined Portal", "icon": "🚪", "color": "#a855f7", "dim": "overworld"},
        "shipwreck": {"name": "Shipwreck", "icon": "⛵", "color": "#38bdf8", "dim": "overworld"},
        "mineshaft": {"name": "Abandoned Mineshaft", "icon": "⛏️", "color": "#94a3b8", "dim": "overworld"},
        "fortress": {"name": "Nether Fortress", "icon": "🏯", "color": "#ef4444", "dim": "nether"},
        "bastion": {"name": "Bastion Remnant", "icon": "🐖", "color": "#d97706", "dim": "nether"},
        "swamp_hut": {"name": "Witch Hut", "icon": "🧙‍♀️", "color": "#14b8a6", "dim": "overworld"},
        "igloo": {"name": "Igloo Basement", "icon": "🧊", "color": "#38bdf8", "dim": "overworld"},
        "trail_ruins": {"name": "Trail Ruins", "icon": "🏺", "color": "#a855f7", "dim": "overworld"},
        "ocean_ruin": {"name": "Ocean Ruin", "icon": "🌊", "color": "#06b6d4", "dim": "overworld"},
        "buried_treasure": {"name": "Buried Treasure", "icon": "💎", "color": "#facc15", "dim": "overworld"},
    }

    spawn_evidence = data.get('spawn_stage') or {}
    point = spawn_evidence.get('coordinates') if isinstance(spawn_evidence, dict) else None
    spawn_point = [point[0], point[2]] if isinstance(point, list) and len(point) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in point) else None
    spawn_distance_exact = math.hypot(spawn_point[0] - center[0], spawn_point[1] - center[1]) if spawn_point else None
    spawn_dist = round(spawn_distance_exact, 1) if spawn_distance_exact is not None else None
    spawn_dist_origin = round(math.hypot(spawn_point[0], spawn_point[1]), 1) if spawn_point else None

    structures = []
    idx = 1

    # Overworld structures
    for stype, sdata in req_overworld.items():
        coords_list = sdata.get("predicted_viable", [])
        meta = STRUCTURE_METAS.get(stype, {"name": stype.title(), "icon": "📍", "color": "#ffffff", "dim": "overworld"})
        for c in coords_list:
            if len(c) >= 2:
                x, z = c[0], c[1]
                dist = round(math.hypot(x - center[0], z - center[1]), 1)
                dist_origin = round(math.hypot(x, z), 1)
                dist_spawn = round(math.hypot(x - spawn_point[0], z - spawn_point[1]), 1) if spawn_point else None
                structures.append({
                    "id": f"s-{idx}",
                    "type": stype,
                    "name": meta["name"],
                    "x": x,
                    "z": z,
                    "y": None,
                    "dimension": meta["dim"],
                    "icon": meta["icon"],
                    "color": meta["color"],
                    "viable": True,
                    "distanceToHub": dist,
                    "distanceToOrigin": dist_origin,
                    "distanceToSpawn": dist_spawn,
                    "distanceUnits": "overworld horizontal blocks",
                    "hubKind": "world_origin" if center == [0, 0] else "evaluation_center",
                    "evidenceStatus": sdata.get('data_status', 'PREDICTED'),
                })
                idx += 1

    # Nether structures
    for stype, sdata in req_nether.items():
        coords_list = sdata.get("predicted_viable", [])
        meta = STRUCTURE_METAS.get(stype, {"name": stype.title(), "icon": "📍", "color": "#ffffff", "dim": "nether"})
        for c in coords_list:
            if len(c) >= 2:
                x, z = c[0], c[1]
                dist = round(math.hypot(x - center[0] / 8, z - center[1] / 8), 1)
                dist_origin = round(math.hypot(x, z), 1)
                dist_spawn = round(math.hypot(x - spawn_point[0] / 8, z - spawn_point[1] / 8), 1) if spawn_point else None
                structures.append({
                    "id": f"s-{idx}",
                    "type": stype,
                    "name": meta["name"],
                    "x": x,
                    "z": z,
                    "y": None,
                    "dimension": meta["dim"],
                    "icon": meta["icon"],
                    "color": meta["color"],
                    "viable": True,
                    "distanceToHub": dist,
                    "distanceToOrigin": dist_origin,
                    "distanceToSpawn": dist_spawn,
                    "distanceUnits": "nether horizontal blocks",
                    "hubKind": "evaluation_center_scaled_to_nether",
                    "evidenceStatus": sdata.get('data_status', 'PREDICTED'),
                })
                idx += 1

    # Optional structures
    for stype, sdata in opt_structures.items():
        coords_list = sdata.get("predicted_viable", [])
        meta = STRUCTURE_METAS.get(stype, {"name": stype.title(), "icon": "📍", "color": "#ffffff", "dim": "overworld"})
        for c in coords_list:
            if len(c) >= 2:
                x, z = c[0], c[1]
                dist = round(math.hypot(x - center[0], z - center[1]), 1)
                dist_origin = round(math.hypot(x, z), 1)
                dist_spawn = round(math.hypot(x - spawn_point[0], z - spawn_point[1]), 1) if spawn_point else None
                structures.append({
                    "id": f"s-{idx}",
                    "type": stype,
                    "name": meta["name"],
                    "x": x,
                    "z": z,
                    "y": None,
                    "dimension": meta["dim"],
                    "icon": meta["icon"],
                    "color": meta["color"],
                    "viable": True,
                    "distanceToHub": dist,
                    "distanceToOrigin": dist_origin,
                    "distanceToSpawn": dist_spawn,
                    "distanceUnits": "overworld horizontal blocks",
                    "hubKind": "world_origin" if center == [0, 0] else "evaluation_center",
                    "evidenceStatus": sdata.get('data_status', 'PREDICTED'),
                })
                idx += 1
    biomes = data.get('biomes') or {}
    verified = data.get('actual_generation_verification') or {}
    terrain = data.get('terrain_status') or {}
    terrain_source = terrain.get('score_generation_source') or terrain.get('source') if isinstance(terrain, dict) else None
    terrain_metrics = terrain_metrics_arg or (terrain.get('metrics') if isinstance(terrain, dict) and ((isinstance(terrain_source, dict) and terrain_source.get('kind') == 'actual_generation') or terrain.get('provider')) else None)
    actual_verified = False  # No supported provider currently certifies a whole Realm.
    surface_evidence=data.get('surface_biome_verification') or {}
    classification=surface_evidence.get('classification') or {}
    observation=surface_evidence.get('observation') or {}
    observed_names=classification.get('raw_names') or []
    has_surface_evidence=(observation.get('source')=='actual' and observation.get('actual') is True and
        observation.get('operation')=='surface_points_v1' and observation.get('status')=='PARTIAL' and
        (classification.get('uncertainty') or {}).get('domain')=='actual_generated_surface' and
        bool(observed_names))

    # Terrain evidence: 'passed', 'near_miss', 'failed', 'pending'
    if isinstance(has_terrain_pass, str):
        st = has_terrain_pass.strip().lower()
        if st == 'passed':
            terrain_passed = True
            terrain_status_str = 'passed'
        elif st == 'near_miss':
            terrain_passed = False
            terrain_status_str = 'near_miss'
        elif st == 'failed':
            terrain_passed = False
            terrain_status_str = 'failed'
        else:
            terrain_passed = None
            terrain_status_str = 'pending'
    elif has_terrain_pass is True:
        terrain_passed = True
        terrain_status_str = 'passed'
    elif has_terrain_pass is False:
        terrain_passed = False
        terrain_status_str = 'failed'
    else:
        terrain_passed = None
        terrain_status_str = 'pending'

    if terrain_status_str == 'passed':
        terrain_type = "Ocean Continent"
    elif terrain_status_str == 'near_miss':
        terrain_type = "Coastal Continent (Near-Miss)"
    elif terrain_status_str == 'failed':
        terrain_type = "Terrain Rejected"
    else:
        terrain_type = "Baseline Survivor"
    marine_status = (data.get('marine_stage') or {}).get('status', data.get('marine_status', 'DEFERRED'))

    if terrain_metrics is None and terrain_mainland_fraction is not None:
        terrain_metrics = {"mainlandFraction": round(float(terrain_mainland_fraction), 3)}
    elif isinstance(terrain_metrics, dict) and terrain_mainland_fraction is not None:
        terrain_metrics["mainlandFraction"] = round(float(terrain_mainland_fraction), 3)

    return {
        "id": str(data.get('id') or f'cand-{seed}'),
        "seed": str(seed),
        "score": round(float(score), 1) if score is not None else None,
        "rankingTier": ranking_tier,
        "unmetRequirements": unmet_requirements,
        "weightedRadialDistance": data.get("weighted_radial_dist"),
        "originDistance": data.get("origin_distance"),
        "strongholdAnchor": stronghold,
        "evaluationCenter": center,
        "playableBounds": data.get("bounds"),
        "predictedStrongholds": actual_strongholds,
        "spawnPoint": spawn_point,
        "spawnDistance": spawn_dist,
        "spawnWithin100": spawn_distance_exact <= 100 if spawn_distance_exact is not None else None,
        "spawnDistanceUnits": "horizontal blocks from hub",
        "spawnDistanceToOrigin": spawn_dist_origin,
        "spawnEvidence": spawn_evidence if isinstance(spawn_evidence, dict) else None,
        "spawnStatus": spawn_evidence.get('status', 'PENDING') if isinstance(spawn_evidence, dict) else 'PENDING',
        "chunkbaseUrl": None,
        "terrainType": terrain_type,
        "terrainPassed": terrain_passed,
        "terrainStatus": terrain_status_str,
        "terrainEvidence": terrain_status_str,
        "terrainGeometryScore": round(float(terrain_geometry_score), 1) if terrain_geometry_score is not None else None,
        "terrainReasons": terrain_reasons or [],
        "terrainMetrics": terrain_metrics,
        "structures": structures,
        "ravines": data.get('ravines', []) if (data.get('ravine_evidence') or {}).get('kind') == 'actual_generation' else [],
        "caveClusters": data.get('cave_clusters', []) if (data.get('cave_evidence') or {}).get('kind') == 'actual_generation' else [],
        "biomes": biomes.get('raw_names', []) if isinstance(biomes, dict) else [],
        "biomeWitnesses": biomes.get('witnesses') if isinstance(biomes, dict) else None,
        "netherBiomeWitnesses": (data.get("nether_biomes") or {}).get("witnesses"),
        "biomeSamples": [s for s in (biomes.get('sampling') or {}).get('samples', []) if isinstance(s, dict)][:300] if isinstance(biomes, dict) else [],
        "bdsVerified": actual_verified,
        "bdsAccuracy": verified.get('metrics') if actual_verified else None,
        "baselineStatus": data.get('baseline_qualification', data.get('qualification', 'PENDING')),
        "marineStatus": marine_status,
        "actualGenerationStatus": "PARTIAL" if has_surface_evidence else "PENDING",
        "surfaceVerification": {'status':'PARTIAL' if has_surface_evidence else 'PENDING',
            'observedBiomes':observed_names if has_surface_evidence else [],
            'observationId':surface_evidence.get('observation_id'),
            'scope':'Surface point presence only; whole Realm remains unverified'} if surface_evidence else None,
        "screeningRevision": data.get('screening_revision'),
        "discoveredAt": time.strftime("%H:%M:%S"),
        "provenance": "live",
    }


# Global singleton manager
MANAGER = SweepManager()


class WebSearchHandler(http.server.SimpleHTTPRequestHandler):
    """Handles static UI requests and dynamic sweep orchestration endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def end_headers(self):
        origin = self.headers.get('Origin')
        server_port = getattr(getattr(self, "server", None), "server_port", 3000)
        allowed_ports = {3000, 5173, server_port}
        allowed = {f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in allowed_ports}
        if origin in allowed:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        origin = self.headers.get('Origin')
        server_port = getattr(getattr(self, "server", None), "server_port", 3000)
        allowed_ports = {3000, 5173, server_port}
        allowed = {f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in allowed_ports}
        self.send_response(200 if origin in allowed else 403)
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/api/sweep/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = MANAGER.get_status()
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        elif path == "/api/sweep/runs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MANAGER.list_runs()).encode("utf-8"))
            return

        elif path == "/api/candidates":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"candidates": MANAGER.candidates}).encode("utf-8"))
            return

        elif path == "/api/candidate/biome-grid":
            params = parse_qs(url.query)
            seed_param = params.get("seed", [None])[0]
            dim_param = params.get("dimension", ["overworld"])[0].lower()
            if not seed_param:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "seed parameter required"}).encode("utf-8"))
                return
            try:
                from seed_search.seeds import parse_seed
                from seed_search.backend import Backend, biome_name
                seed_int = parse_seed(seed_param)
                if dim_param not in ('overworld','nether'):raise ValueError('dimension must be overworld or nether')
                cx=float(params.get('centerX',['0'])[0]);cz=float(params.get('centerZ',['0'])[0])
                side=int(params.get('side',['2048'])[0])
                if not all(math.isfinite(value) and abs(value)<=1000000 for value in (cx,cz)):
                    raise ValueError('Invalid map center')
                if side not in (832,896,1024,1536,1664,2048):raise ValueError('Unsupported map side')
                x0=math.ceil(cx-side/2);z0=math.ceil(cz-side/2);n=side//32+1
                cache_key = (seed_int, dim_param, cx, cz, side)
                cached = MANAGER._biome_grid_cache.get(cache_key)
                if cached is None:
                    if dim_param not in ('overworld', 'nether'):
                        raise ValueError('dimension must be overworld or nether')
                    with Backend(seed_int) as backend:
                        points = [(x0+x*32,63,z0+z*32) for z in range(n) for x in range(n)]
                        biomes_arr = backend.biome_points(points, dimension=0 if dim_param == 'overworld' else -1).reshape(n, n)
                    unique_ids = list(set(int(x) for x in biomes_arr.flatten()))
                    names_map = {str(uid): biome_name(uid) for uid in unique_ids}
                    cached = {
                        "ok": True,
                        "seed": str(seed_param),
                        "dimension": dim_param,
                        "evidence": "PREDICTED",
                        "center": [cx,cz],
                        "bounds": {"x0": x0, "z0": z0, "nx": n, "nz": n, "step": 32},
                        "grid": biomes_arr.tolist(),
                        "approx_height": None,
                        "names": names_map,
                    }
                    if len(MANAGER._biome_grid_cache) > 20:
                        MANAGER._biome_grid_cache.pop(next(iter(MANAGER._biome_grid_cache)))
                    MANAGER._biome_grid_cache[cache_key] = cached
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(cached).encode("utf-8"))
            except Exception as exc:
                self.send_response(400 if isinstance(exc, ValueError) else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"))
            return

        elif path == "/api/system/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            info = {
                "cpu": platform.processor() or platform.machine(),
                "platform": platform.platform(),
                "nativeBuild": str(DEFAULT_NATIVE_BUILD),
                "nativeBuildReady": DEFAULT_NATIVE_BUILD.exists(),
                "defaultBatchSize": 16384,
                "defaultThreads": 34,
                "defaultMaxMisses": 2,
            }
            self.wfile.write(json.dumps(info).encode("utf-8"))
            return

        # Fallback to serving static frontend
        super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path

        def reject(message, code=400):
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': message}).encode('utf-8'))

        sec_fetch_site = self.headers.get("Sec-Fetch-Site")
        if sec_fetch_site and sec_fetch_site.strip().lower() == "cross-site":
            reject("Cross-site request blocked", 403)
            return

        server_port = getattr(getattr(self, "server", None), "server_port", 3000)
        allowed_hosts = {
            "localhost:3000",
            "127.0.0.1:3000",
            f"localhost:{server_port}",
            f"127.0.0.1:{server_port}",
            "localhost:5173",
            "127.0.0.1:5173",
        }
        if server_port == 80:
            allowed_hosts.update({"localhost", "127.0.0.1"})

        def extract_host(header_val: str) -> str:
            val = header_val.strip()
            parsed = urlparse(val if "://" in val else f"http://{val}")
            return parsed.netloc or parsed.path.split("/")[0]

        origin = self.headers.get("Origin")
        if origin:
            if extract_host(origin) not in allowed_hosts:
                reject("Origin is not allowed", 403)
                return

        referer = self.headers.get("Referer")
        if referer:
            if extract_host(referer) not in allowed_hosts:
                reject("Referer is not allowed", 403)
                return

        if path not in ('/api/sweep/start', '/api/sweep/stop', '/api/sweep/resume', '/api/sweep/select-run', '/api/sweep/pause', '/api/sweep/continue', '/api/bds/verify'):
            reject('Unknown endpoint', 404)
            return

        cl_header = self.headers.get('Content-Length')
        if path in ('/api/sweep/stop', '/api/sweep/pause', '/api/sweep/continue') and (cl_header is None or cl_header.strip() in ('', '0')):
            req_data = {}
        else:
            try:
                if cl_header is None or not cl_header.strip().isdigit():
                    raise ValueError('Missing or invalid Content-Length header')
                content_length = int(cl_header.strip())
                if content_length == 0 and path in ('/api/sweep/stop', '/api/sweep/pause', '/api/sweep/continue'):
                    req_data = {}
                else:
                    if content_length < 2 or content_length > 16384:
                        raise ValueError('JSON body must be 2–16384 bytes')
                    req_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
                if not isinstance(req_data, dict):
                    raise ValueError('JSON body must be an object')
                allowed = (
                    {'count', 'startIndex', 'threads', 'batchSize', 'maxMisses', 'counts', 'profile'}
                    if path == '/api/sweep/start'
                    else {'runId'}
                    if path in ('/api/sweep/resume', '/api/sweep/select-run', '/api/sweep/continue')
                    else {'seed', 'candidateId'}
                    if path == '/api/bds/verify'
                    else set()
                )
                if set(req_data) - allowed:
                    raise ValueError('Unsupported request field')
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                reject(str(exc))
                return

        if path == "/api/sweep/start":
            count = req_data.get("count", 10000000)
            threads = req_data.get("threads", 34)
            batch_size = req_data.get("batchSize", 16384)
            max_misses = req_data.get("maxMisses", 2)

            result = MANAGER.start_sweep(
                count=count,
                threads=threads,
                batch_size=batch_size,
                max_misses=max_misses,
                counts=req_data.get('counts'),
                start_index=req_data.get('startIndex',0),
                profile=req_data.get('profile','dynamic1664'),
            )
            self.send_response(200 if result.get("ok") else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        elif path in ("/api/sweep/resume", "/api/sweep/continue"):
            result = MANAGER.resume_sweep(req_data.get("runId", MANAGER.run_id) if path == "/api/sweep/continue" else req_data.get("runId"))
            self.send_response(200 if result.get("ok") else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        elif path == "/api/sweep/pause":
            result = MANAGER.pause_sweep()
            self.send_response(200 if result.get("ok") else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        elif path == "/api/sweep/select-run":
            result = MANAGER.select_run(req_data.get("runId"))
            self.send_response(200 if result.get("ok") else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        elif path == "/api/bds/verify":
            result = MANAGER.verify_bds_candidate(
                seed=req_data.get("seed"),
                candidate_id=req_data.get("candidateId"),
            )
            self.send_response(200 if result.get("ok") else 400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        elif path == "/api/sweep/stop":
            result = MANAGER.stop_sweep()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_server(port: int = 3000, host: str = '127.0.0.1', auto_continue: bool = False):
    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, WebSearchHandler)
    print(f"Seed Searcher Web Server running at http://{host}:{port}/")
    print(f"📁 Serving static files from {DIST_DIR}")
    print(f"Native build: {DEFAULT_NATIVE_BUILD}")
    if auto_continue or os.environ.get('SEED_SEARCH_AUTO_CONTINUE') == '1' or '--continue' in sys.argv:
        print("Auto-continuing latest sweep run to finish...")
        res = MANAGER.resume_sweep(MANAGER.run_id)
        print(f"Sweep resume status: {res}")
    import signal
    previous_handler = None
    if threading.current_thread() is threading.main_thread():
        previous_handler = signal.getsignal(signal.SIGTERM)
        def terminate_server(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, terminate_server)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        MANAGER.stop_sweep()
        httpd.server_close()
        if previous_handler is not None:
            signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    port = 3000
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
    auto_cont = "--continue" in sys.argv or os.environ.get("SEED_SEARCH_AUTO_CONTINUE") == "1"
    run_server(port, os.environ.get('SEED_SEARCH_WEB_HOST', '127.0.0.1'), auto_continue=auto_cont)
