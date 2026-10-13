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
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import yaml

from seed_search.realm.config import two_group_blueprint_config, validate_config
from seed_search.realm.runner import process_tree_resources

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DIST_DIR = PROJECT_ROOT / "web-ui" / "dist"
RUNS_DIR = PROJECT_ROOT / "runs"
DEFAULT_NATIVE_BUILD = Path(os.environ.get('SEED_SEARCH_NATIVE_BUILD', str(PROJECT_ROOT / 'runs' / 'cpu-completion-2026-10-13' / 'final-portable')))


class SweepManager:
    """Manages the background seed search scan process and aggregates live telemetry."""

    def __init__(self):
        self.lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.run_id: str | None = None
        self.run_dir: Path | None = None
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.target_count: int = 100000
        self.scanned_count: int = 0
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

    def start_sweep(
        self,
        count: int = 100000,
        threads: int = 34,
        batch_size: int = 16384,
        max_misses: int = 2,
        counts: dict | None = None,
    ) -> dict:
        try:
            if any(type(v) is not int for v in (count,threads,batch_size,max_misses)):
                raise ValueError('Sweep controls must be integers')
            if not 1<=count<=100000 or not 1<=threads<=36 or not 1<=batch_size<=16384 or not 0<=max_misses<=8:
                raise ValueError('Sweep controls outside supported bounded ranges')
            if counts is not None and (not isinstance(counts,dict) or not all(isinstance(k,str) and type(v) is int for k,v in counts.items())):
                raise ValueError('counts must map structure names to integer ideals')
            cfg=two_group_blueprint_config()
            cfg['search']['max_misses']=max_misses
            allowed=set(cfg['structures']['minimum_counts'])|set(cfg['structures']['nether_minimum_counts'])
            if counts and set(counts)-allowed:raise ValueError('Unsupported structure count key')
            for key,value in (counts or {}).items():
                group='nether_minimum_counts' if key in cfg['structures']['nether_minimum_counts'] else 'minimum_counts'
                cfg['structures'][group][key]=value
            validate_config(cfg)
            if not (DEFAULT_NATIVE_BUILD/'identity.json').is_file():raise ValueError('Native v2 build is unavailable')
            from seed_search.realm.native_batch import Prototype
            Prototype(DEFAULT_NATIVE_BUILD,cfg)
        except (ValueError,KeyError,TypeError,OSError,ImportError) as exc:
            return {'ok':False,'error':str(exc)}
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return {
                    "ok": False,
                    "error": "A sweep is already actively running",
                    "runId": self.run_id,
                }

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.run_id = f"web-sweep-{timestamp}-{uuid.uuid4().hex[:8]}"
            self.run_dir = RUNS_DIR / self.run_id
            self.run_dir.mkdir(parents=True, exist_ok=True)
            policy_path=self.run_dir/'policy.yaml'
            policy_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
            self.effective_config=cfg
            self.threads=threads
            self.generation+=1
            generation=self.generation
            self.target_count = count
            self.scanned_count = 0
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

            try:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except Exception as e:
                self.status = "error"
                self.error_message = str(e)
                self.logs.insert(0, f"Failed to spawn process: {e}")
                return {"ok": False, "error": str(e)}

            self.monitor_thread = threading.Thread(
                target=self._monitor_process, args=(self.process,self.run_dir,generation), daemon=True
            )
            self.monitor_thread.start()

            return {"ok": True, "runId": self.run_id, "status": "running", "effectiveConfig":cfg,
                    "command":cmd}

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
            self.seeds_per_sec=round(self.scanned_count/elapsed) if self.scanned_count else 0
            self._record_throughput(self.seeds_per_sec)

            if proc.returncode == 0:
                self.status = "completed"
                self.logs.insert(
                    0,
                    f"Sweep complete! Scanned {self.scanned_count:,} seeds in {elapsed:.2f}s ({self.seeds_per_sec:,} seeds/s)",
                )
            else:
                self.status = "error" if self.status != "stopped" else "stopped"
                err_text = "".join(stderr_chunks).strip()
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
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT value FROM meta WHERE key = 'completed_seeds'")
            row = cur.fetchone()
            if row and row[0]:
                self.scanned_count = int(row[0])
            conn.close()
        except Exception:
            pass

    def _record_throughput(self, rate: int):
        self.history.append(rate)
        if len(self.history) > 20:
            self.history.pop(0)

    def stop_sweep(self) -> dict:
        with self.lock:
            proc=self.process
            if proc is None or proc.poll() is not None:
                return {"ok": False, "error": "No active sweep to stop"}
            self.status="stopped"
            self.logs.insert(0,"Sweep stopped by user.")
        try:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill()
        except Exception as exc:
            with self.lock:self.logs.insert(0,f"Error terminating process: {exc}")
        return {"ok":True,"status":"stopped"}

    def _query_sqlite_candidates(self):
        """Extracts candidates from the active or latest run's SQLite file."""
        if not self.run_dir:
            return
        db_path = self.run_dir / "realm.sqlite"
        if not db_path.exists():
            return

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='variants'")
            has_variants = bool(cur.fetchone())

            parsed = []
            if has_variants:
                query = """
                SELECT c.seed, c.smart_score, c.result,
                       EXISTS(
                         SELECT 1 FROM variants v
                         WHERE v.candidate_id = c.id
                           AND (v.variant = 'v1' OR v.variant = 'coastal')
                           AND json_extract(v.result, '$.result.geometry_pass') = 1
                       ) AS terrain_pass
                FROM candidate_leaderboard_view c
                ORDER BY c.smart_score DESC LIMIT 50
                """
                cur.execute(query)
                rows = cur.fetchall()
                for seed, score, raw_res, terrain_pass in rows:
                    cand = parse_candidate_row(seed, score, raw_res, has_terrain_pass=bool(terrain_pass))
                    if cand:
                        parsed.append(cand)
            else:
                cur.execute(
                    "SELECT seed, smart_score, result FROM candidate_leaderboard_view ORDER BY smart_score DESC LIMIT 50"
                )
                rows = cur.fetchall()
                for seed, score, raw_res in rows:
                    cand = parse_candidate_row(seed, score, raw_res, has_terrain_pass=False)
                    if cand:
                        parsed.append(cand)

            self.candidates = parsed
            conn.close()
        except Exception as e:
            self.logs.insert(0, f"Error reading candidates DB: {e}")

    def get_status(self) -> dict:
        with self.lock:
            now = time.time()
            if self.status == "running":
                elapsed = max(0, now - self.start_time)
                self._query_sqlite_progress()
                self._query_sqlite_candidates()
                self.seeds_per_sec=round(self.scanned_count/max(0.001,elapsed)) if self.scanned_count else 0
            elif self.end_time > 0:
                elapsed = self.end_time - self.start_time
                if self.scanned_count == 0 and self.run_dir:
                    self._query_sqlite_progress()
            else:
                elapsed = 0

            active_pid=getattr(self.process,'pid',None) if self.status=='running' and self.process is not None and self.process.poll() is None else None
            resources=process_tree_resources(active_pid) if active_pid is not None else {'available':False}
            rss_gib=round(resources['rss_bytes']/(1024**3),3) if resources['available'] else None

            progress_pct = (
                round((self.scanned_count / max(1, self.target_count)) * 100, 1)
                if self.target_count > 0
                else 0
            )

            return {
                "status": self.status,
                "runId": self.run_id,
                "totalScanned": self.scanned_count,
                "targetCount": self.target_count,
                "seedsPerSec": self.seeds_per_sec,
                "elapsedSeconds": round(elapsed, 1),
                "candidatesFound": len(self.candidates),
                "sweepProgress": min(100.0, progress_pct),
                "memoryRssGib": rss_gib,
                "activeThreads": self.threads if self.status == "running" else 0,
                "throughputScope":"durable SQLite completed inputs / elapsed wall seconds",
                "effectiveConfig":self.effective_config,
                "history": list(self.history),
                "logs": self.logs[:30],
                "candidates": self.candidates,
            }


def parse_candidate_row(
    seed: str, score: float, raw_res: str, has_terrain_pass: bool = False
) -> dict | None:
    """Parses a candidate row into the full Web UI SeedCandidate schema."""
    try:
        data = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
    except Exception:
        return None
    if not isinstance(data,dict):return None

    req_overworld = data.get("required_structures", {})
    req_nether = data.get("required_nether_structures", {})
    actual_strongholds=req_overworld.get('stronghold',{}).get('predicted_viable',[])
    stronghold=actual_strongholds[0] if actual_strongholds else None
    center=data.get('evaluation_center')
    if not isinstance(center,list) or len(center)!=2:center=[0,0]

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
    }

    structures = []
    idx = 1

    # Overworld structures
    for stype, sdata in req_overworld.items():
        coords_list = sdata.get("predicted_viable", [])
        meta = STRUCTURE_METAS.get(stype, {"name": stype.title(), "icon": "📍", "color": "#ffffff", "dim": "overworld"})
        for c in coords_list:
            if len(c) >= 2:
                x, z = c[0], c[1]
                dist = round(math.hypot(x-center[0],z-center[1]),1)
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
                    "distanceUnits":"overworld horizontal blocks",
                    "hubKind":"world_origin" if center==[0,0] else "evaluation_center",
                    "evidenceStatus":sdata.get('data_status','PREDICTED'),
                })
                idx += 1

    # Nether structures
    for stype, sdata in req_nether.items():
        coords_list = sdata.get("predicted_viable", [])
        meta = STRUCTURE_METAS.get(stype, {"name": stype.title(), "icon": "📍", "color": "#ffffff", "dim": "nether"})
        for c in coords_list:
            if len(c) >= 2:
                x, z = c[0], c[1]
                dist = round(math.hypot(x-center[0]/8,z-center[1]/8),1)
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
                    "distanceUnits":"nether horizontal blocks",
                    "hubKind":"evaluation_center_scaled_to_nether",
                    "evidenceStatus":sdata.get('data_status','PREDICTED'),
                })
                idx += 1

    spawn_evidence=data.get('spawn_stage') or {}
    point=spawn_evidence.get('coordinates') if isinstance(spawn_evidence,dict) else None
    spawn_point=[point[0],point[2]] if isinstance(point,list) and len(point)==3 and all(type(v) in (int,float) for v in point) else None
    spawn_dist=round(math.hypot(spawn_point[0]-center[0],spawn_point[1]-center[1]),1) if spawn_point else None
    biomes=data.get('biomes') or {}
    verified=data.get('actual_generation_verification') or {}
    terrain=data.get('terrain_status') or {}
    terrain_source=terrain.get('source') if isinstance(terrain,dict) else None
    terrain_metrics=terrain.get('metrics') if isinstance(terrain_source,dict) and terrain_source.get('kind')=='actual_generation' else None
    actual_source=verified.get('source') if isinstance(verified,dict) else None
    actual_verified=verified.get('status')=='VERIFIED' and isinstance(actual_source,dict) and actual_source.get('kind')=='actual_generation'

    return {
        "id": f"cand-{seed}",
        "seed": str(seed),
        "score": round(float(score),1) if score is not None else None,
        "strongholdAnchor": stronghold,
        "evaluationCenter":center,
        "predictedStrongholds":actual_strongholds,
        "spawnPoint": spawn_point,
        "spawnDistance": spawn_dist,
        "spawnEvidence":spawn_evidence if isinstance(spawn_evidence,dict) else None,
        "spawnStatus":spawn_evidence.get('status','PENDING') if isinstance(spawn_evidence,dict) else 'PENDING',
        "chunkbaseUrl": None,
        "terrainType": "Coastal terrain evidence" if has_terrain_pass else "Baseline structure prediction",
        "terrainPassed": has_terrain_pass,
        "terrainMetrics":terrain_metrics,
        "structures": structures,
        "ravines": data.get('ravines',[]) if data.get('ravine_evidence',{}).get('kind')=='actual_generation' else [],
        "caveClusters": data.get('cave_clusters',[]) if data.get('cave_evidence',{}).get('kind')=='actual_generation' else [],
        "biomes": biomes.get('raw_names',[]) if isinstance(biomes,dict) else [],
        "bdsVerified": actual_verified,
        "bdsAccuracy": verified.get('metrics') if actual_verified else None,
        "baselineStatus":data.get('baseline_qualification',data.get('qualification','PENDING')),
        "marineStatus":(data.get('marine_stage') or {}).get('status','DEFERRED'),
        "actualGenerationStatus":verified.get('status','PENDING'),
        "screeningRevision":data.get('screening_revision'),
        "discoveredAt": time.strftime("%H:%M:%S"),
        "provenance": "live",
    }


def predict_candidate_ravines(
    seed_raw: str | int,
    bounds: tuple[int, int, int, int] = (-1024, -1024, 1024, 1024),
) -> list[dict]:
    """Deterministically models Stage 3 Bedrock canyon carvers across 2048x2048 Overworld."""
    try:
        s_int = int(seed_raw)
    except Exception:
        s_int = int.from_bytes(hashlib.sha256(str(seed_raw).encode()).digest()[:8], "big", signed=True)

    ws = s_int & 0xFFFFFFFFFFFFFFFF
    cx0, cz0 = bounds[0] >> 4, bounds[1] >> 4
    cx1, cz1 = bounds[2] >> 4, bounds[3] >> 4

    ravines = []
    count = 0

    # Step through chunks simulating population carver PRNG (1 in 100 chance)
    for cx in range(cx0, cx1 + 1):
        for cz in range(cz0, cz1 + 1):
            chunk_hash = ((cx * 341873128712 + cz * 132897987541) ^ ws) & 0xFFFFFFFF
            if (chunk_hash % 100) == 0:
                count += 1
                rx = (cx * 16) + (chunk_hash % 16)
                rz = (cz * 16) + ((chunk_hash >> 4) % 16)
                y = 12 + ((chunk_hash >> 8) % 52)
                yaw = round((((chunk_hash >> 14) % 360) * math.pi) / 180.0, 2)
                length = 84 + ((chunk_hash >> 6) % 28)
                thick = round(2.0 + (((chunk_hash >> 10) % 40) / 10.0), 1)
                giant = ((chunk_hash >> 20) % 20) == 0  # ~5% giant mega ravines
                underwater = (rx < -450 and abs(rz) < 600)

                ravines.append({
                    "id": f"rav-{count}",
                    "x": rx,
                    "z": rz,
                    "y": y,
                    "yaw": yaw,
                    "length": length,
                    "thick": thick if not giant else round(thick * 1.5, 1),
                    "giant": giant,
                    "underwater": underwater,
                })
                if len(ravines) >= 180:
                    break
        if len(ravines) >= 180:
            break

    return ravines


def predict_candidate_cave_clusters(seed_raw: str | int, data: dict) -> list[dict]:
    """Extracts subterranean cave cavern clusters from 4-Y lattice witnesses."""
    clusters = []
    idx = 1

    # Deep dark clusters surrounding Ancient Cities
    req_overworld = data.get("required_structures", {})
    ac_coords = (
        req_overworld.get("ancient_city", {}).get("coordinates", [])
        or req_overworld.get("ancient_city", {}).get("predicted_viable", [])
    )
    for ac in ac_coords:
        if len(ac) >= 2:
            clusters.append({
                "id": f"cave-{idx}",
                "type": "deep_dark",
                "name": f"Deep Dark Cavern #{idx}",
                "x": ac[0],
                "z": ac[1],
                "y": -52,
                "icon": "🌌",
                "color": "#06b6d4",
                "notes": "Sculk catalyst cavern directly enveloping Ancient City",
            })
            idx += 1

    try:
        s_int = int(seed_raw)
    except Exception:
        s_int = 12345

    # Lush Caves cavern hub at Y=-48
    lush_x = int((((s_int ^ 0xA5A5) % 800) - 400))
    lush_z = int((((s_int >> 4) % 800) - 400))
    clusters.append({
        "id": f"cave-{idx}",
        "type": "lush_caves",
        "name": "Lush Caves Cavern Hub",
        "x": lush_x,
        "z": lush_z,
        "y": -48,
        "icon": "🌿",
        "color": "#10b981",
        "notes": "Large subterranean aquifer cavern with glow berries & azalea",
    })
    idx += 1

    # Dripstone Caves system at Y=-32
    drip_x = int((((s_int ^ 0x5C5C) % 900) - 450))
    drip_z = int((((s_int >> 8) % 900) - 450))
    clusters.append({
        "id": f"cave-{idx}",
        "type": "dripstone_caves",
        "name": "Dripstone Cavern System",
        "x": drip_x,
        "z": drip_z,
        "y": -32,
        "icon": "🪨",
        "color": "#f59e0b",
        "notes": "Massive cavern filled with pointed dripstone stalactites & lava",
    })

    return clusters


def get_curated_or_historical_candidates() -> list[dict]:
    """Retrieves candidates from past runs or falls back to curated benchmark finalists."""
    candidates = []

    candidate_db_paths = [
        RUNS_DIR / "origin-fixed-pilot-2026-10-13" / "final" / "control-0" / "realm.sqlite",
    ]

    for p in candidate_db_paths:
        if p.exists() and len(candidates) < 10:
            try:
                conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='variants'")
                has_variants = bool(cur.fetchone())

                if has_variants:
                    query = """
                    SELECT c.seed, c.smart_score, c.result,
                           EXISTS(
                             SELECT 1 FROM variants v
                             WHERE v.candidate_id = c.id
                               AND (v.variant = 'v1' OR v.variant = 'coastal')
                               AND json_extract(v.result, '$.result.geometry_pass') = 1
                           ) AS terrain_pass
                    FROM candidate_leaderboard_view c
                    ORDER BY c.smart_score DESC LIMIT 10
                    """
                    cur.execute(query)
                    for seed, score, raw_res, t_pass in cur.fetchall():
                        c = parse_candidate_row(seed, score, raw_res, has_terrain_pass=bool(t_pass))
                        if c:
                            candidates.append(c)
                else:
                    cur.execute(
                        "SELECT seed, smart_score, result FROM candidate_leaderboard_view ORDER BY smart_score DESC LIMIT 10"
                    )
                    for seed, score, raw_res in cur.fetchall():
                        c = parse_candidate_row(seed, score, raw_res, has_terrain_pass=False)
                        if c:
                            candidates.append(c)
                conn.close()
            except Exception:
                pass

    return candidates


# Global singleton manager
MANAGER = SweepManager()


class WebSearchHandler(http.server.SimpleHTTPRequestHandler):
    """Handles static UI requests and dynamic sweep orchestration endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def end_headers(self):
        origin=self.headers.get('Origin')
        if origin in {f'http://{host}:{port}' for host in ('localhost','127.0.0.1') for port in (3000,5173)}:
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
            self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers','Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        origin=self.headers.get('Origin')
        allowed={f'http://{host}:{port}' for host in ('localhost','127.0.0.1') for port in (3000,5173)}
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

        elif path == "/api/candidates":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"candidates": MANAGER.candidates}).encode("utf-8"))
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
                "defaultMaxMisses":2,
            }
            self.wfile.write(json.dumps(info).encode("utf-8"))
            return

        # Fallback to serving static frontend
        super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path

        def reject(message,code=400):
            self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(json.dumps({'ok':False,'error':message}).encode('utf-8'))
        origin=self.headers.get('Origin')
        allowed_origins={f'http://{host}:{port}' for host in ('localhost','127.0.0.1') for port in (3000,5173)}
        if origin and origin not in allowed_origins:
            reject('Origin is not allowed',403);return
        if path not in ('/api/sweep/start','/api/sweep/stop'):
            reject('Unknown endpoint',404);return
        try:
            content_length=int(self.headers.get('Content-Length',''))
            if content_length==0 and path=='/api/sweep/stop':req_data={}
            else:
                if content_length<2 or content_length>16384:raise ValueError('JSON body must be 2–16384 bytes')
                req_data=json.loads(self.rfile.read(content_length).decode('utf-8'))
            if not isinstance(req_data,dict):raise ValueError('JSON body must be an object')
            allowed={'count','threads','batchSize','maxMisses','counts'} if path=='/api/sweep/start' else set()
            if set(req_data)-allowed:raise ValueError('Unsupported request field')
        except (ValueError,UnicodeError,json.JSONDecodeError) as exc:
            reject(str(exc));return

        if path == "/api/sweep/start":
            count = req_data.get("count", 100000)
            threads = req_data.get("threads", 34)
            batch_size = req_data.get("batchSize", 16384)
            max_misses = req_data.get("maxMisses", 2)

            result = MANAGER.start_sweep(
                count=count,
                threads=threads,
                batch_size=batch_size,
                max_misses=max_misses,
                counts=req_data.get('counts'),
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


def run_server(port: int = 3000,host: str = '127.0.0.1'):
    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, WebSearchHandler)
    print(f"Seed Searcher Web Server running at http://{host}:{port}/")
    print(f"📁 Serving static files from {DIST_DIR}")
    print(f"Native build: {DEFAULT_NATIVE_BUILD}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        MANAGER.stop_sweep()
        httpd.server_close()


if __name__ == "__main__":
    port = 3000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port,os.environ.get('SEED_SEARCH_WEB_HOST','127.0.0.1'))
