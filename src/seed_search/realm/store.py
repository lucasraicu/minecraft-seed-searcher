"""Parent-owned Realm checkpoint; seed coverage and baseline records commit together."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from ..seeds import parse_seed

LIMIT = 1 << 64
SCHEMA = 1
SCHEDULING_FIELDS = frozenset({"workers", "max_workers", "batch_size", "native_threads_per_worker"})
_CANONICAL_ENCODER = json.JSONEncoder(sort_keys=True, separators=(",", ":"), allow_nan=False)


class TerrainCapacityError(RuntimeError):
    """A durable raster cannot fit its configured logical cap or disk reserve."""



def canonical(value):
    # JSONEncoder keeps traversal/circular-reference state local to encode().
    # Reuse its immutable options without changing bytes or retry identities.
    return _CANONICAL_ENCODER.encode(value)


def semantic_identity(identity):
    """Scheduling can change on resume; seed sequence, code and evidence cannot."""
    if not isinstance(identity, dict):
        return identity
    result = {}
    for key, value in identity.items():
        if key in {"config", "cfg"} and isinstance(value, dict):
            cfg = dict(value)
            if isinstance(cfg.get("search"), dict):
                cfg["search"] = {k: v for k, v in cfg["search"].items() if k not in SCHEDULING_FIELDS}
            result[key] = cfg
        elif key not in {"scheduling", "config_sha256"}:
            result[key] = value
    config = result.get("config", result.get("cfg"))
    if config is not None:
        result["config_sha256"] = hashlib.sha256(canonical(config).encode()).hexdigest()
    elif "config_sha256" in identity:
        result["config_sha256"] = identity["config_sha256"]
    return result


def index_key(index):
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= LIMIT:
        raise ValueError("Index must be an unsigned 64-bit boundary")
    return f"{index:020d}"


_PREPARATION_TOKEN = object()


@dataclass(frozen=True, init=False)
class PreparedRange:
    """Immutable, owned durable rows produced only by validated preparation."""
    start: int
    end: int
    seed_rows: tuple
    candidate_rows: tuple
    inventory_rows: tuple
    discovery_rows: tuple
    variant_rows: tuple
    counts: tuple
    digest: str
    payload_bytes: int
    policy: tuple
    timings: tuple
    receipt: str | None
    _token: object

    def __init__(self, *args, **kwargs):
        raise TypeError('Use RealmStore.prepare_range for validated rows')

    def __reduce__(self):
        # Spawned preparers return owned immutable rows, never a connection or
        # native pointer. Restore the process-local validation provenance token.
        return (_restore_prepared, (tuple(getattr(self, field) for field in self.__dataclass_fields__ if field != '_token'),))


def _restore_prepared(fields):
    prepared=object.__new__(PreparedRange)
    for name,value in zip(PreparedRange.__dataclass_fields__, (*fields,_PREPARATION_TOKEN), strict=True):
        object.__setattr__(prepared,name,value)
    return prepared


class RealmStore:
    _canonical_candidate_reference = staticmethod(canonical)
    def __init__(self, run, identity=None, resume=False):
        self.run = Path(run)
        path = self.run / "realm.sqlite"
        if path.exists() and not resume:
            raise ValueError("Realm run already exists; use resume or another output")
        if resume and not path.exists():
            raise ValueError("No Realm checkpoint exists to resume")
        self.run.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        # Keep complete WAL/FULL durability. A larger bounded page cache avoids
        # spilling dirty pages repeatedly during full-record batches; checkpoints
        # amortize I/O across 64 MiB of WAL instead of the default 4 MiB.
        self.db.execute("PRAGMA cache_size=-131072")
        self.db.execute("PRAGMA wal_autocheckpoint=16384")
        self.db.execute("PRAGMA journal_size_limit=134217728")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS ranges(start TEXT PRIMARY KEY, end TEXT NOT NULL,
                status TEXT NOT NULL, worker TEXT, attempts INTEGER NOT NULL DEFAULT 1,
                digest TEXT);
            CREATE INDEX IF NOT EXISTS ranges_status ON ranges(status,start);
            CREATE TABLE IF NOT EXISTS retention_receipts(start TEXT PRIMARY KEY, end TEXT NOT NULL,
                receipt TEXT NOT NULL, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS seeds(idx TEXT PRIMARY KEY, seed TEXT NOT NULL, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, idx TEXT NOT NULL,
                seed TEXT NOT NULL, qualification TEXT NOT NULL, result TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS candidate_status ON candidates(qualification,id);
            CREATE INDEX IF NOT EXISTS candidate_idx ON candidates(idx);
            CREATE TABLE IF NOT EXISTS variants(candidate_id TEXT NOT NULL, variant TEXT NOT NULL,
                center TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(candidate_id,variant,center));
            CREATE TABLE IF NOT EXISTS variant_tasks(candidate_id TEXT NOT NULL, variant TEXT NOT NULL,
                status TEXT NOT NULL, PRIMARY KEY(candidate_id,variant));
            CREATE INDEX IF NOT EXISTS variant_task_status ON variant_tasks(variant,status);
            CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, candidate_id TEXT, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS discovery_tasks(idx TEXT NOT NULL, structure TEXT NOT NULL,
                status TEXT NOT NULL, worker TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                result TEXT, PRIMARY KEY(idx,structure));
            CREATE INDEX IF NOT EXISTS discovery_task_status ON discovery_tasks(status,idx,structure);
            CREATE TABLE IF NOT EXISTS terrain_pools(revision TEXT PRIMARY KEY, identity TEXT NOT NULL,
                statuses TEXT NOT NULL, members INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS terrain_pool_members(revision TEXT NOT NULL, candidate_id TEXT NOT NULL,
                PRIMARY KEY(revision,candidate_id));
            CREATE TABLE IF NOT EXISTS terrain_work(unit_id TEXT PRIMARY KEY, revision TEXT NOT NULL,
                candidate_id TEXT NOT NULL, variant TEXT NOT NULL, status TEXT NOT NULL,
                priority REAL NOT NULL, payload TEXT NOT NULL, sampling_key TEXT NOT NULL,
                worker TEXT, attempts INTEGER NOT NULL DEFAULT 0, result TEXT, digest TEXT);
            CREATE INDEX IF NOT EXISTS terrain_work_queue ON terrain_work(revision,candidate_id,variant,status,priority,unit_id);
            CREATE INDEX IF NOT EXISTS terrain_work_pool_variant ON terrain_work(revision,variant,candidate_id);
            CREATE TABLE IF NOT EXISTS terrain_work_attempts(unit_id TEXT NOT NULL, attempt INTEGER NOT NULL,
                worker TEXT NOT NULL, digest TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(unit_id,attempt));
            CREATE TABLE IF NOT EXISTS terrain_observation_bytes(id TEXT PRIMARY KEY, bytes INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS terrain_priority_queue(unit_id TEXT PRIMARY KEY, revision TEXT NOT NULL,
                variant TEXT NOT NULL, enqueue_ordinal INTEGER NOT NULL, score REAL NOT NULL,
                hints TEXT NOT NULL, last_epoch TEXT);
            CREATE INDEX IF NOT EXISTS terrain_priority_rank ON terrain_priority_queue(revision,variant,score DESC,enqueue_ordinal,unit_id);
            CREATE INDEX IF NOT EXISTS terrain_priority_age ON terrain_priority_queue(revision,variant,enqueue_ordinal,unit_id);
            CREATE TABLE IF NOT EXISTS inventory_work(unit_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL,
                kind TEXT NOT NULL, identity TEXT NOT NULL, status TEXT NOT NULL, worker TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, result TEXT, digest TEXT);
            CREATE INDEX IF NOT EXISTS inventory_work_pending ON inventory_work(status,candidate_id,kind);
        """)
        if not resume:
            with self.db:
                self._set("schema", SCHEMA)
                self._set("identity", identity)
                self._set("completed_seeds", 0)
                self._set("counts", {})
                self._set("range_digest_version", 2)
        self.identity = self.get_state("identity")
        saved_config = (self.identity or {}).get("config", (self.identity or {}).get("cfg", {}))
        self.active_variants = tuple(saved_config.get("terrain", {}).get("variants", ("v1", "v2")))
        self._inventory_backend_digest = hashlib.sha256(canonical((self.identity or {}).get('backend')).encode()).hexdigest()
        self._digest_version = self.get_state('range_digest_version')
        self._preparation_policy = (self._digest_version, self._inventory_backend_digest, self.active_variants)
        self.last_range_timings = {}
        self.retention = (self.identity or {}).get('retention', {'mode':'full','max_misses':0})
        if self.retention.get('mode') not in {'full','survivors'}:
            self.close();raise ValueError('Unknown saved retention mode')
        if self.get_state("schema") != SCHEMA:
            self.close()
            raise ValueError("Unsupported Realm checkpoint schema")
        if resume and identity is not None and semantic_identity(identity) != semantic_identity(self.identity):
            self.close()
            raise ValueError("Incompatible resume: semantic configuration, code, sequence or evidence changed")
        from .leaderboard import install
        install(self.db)

    def _set(self, key, value):
        self.db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, canonical(value)))

    def get_state(self, key):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_state(self, key, value):
        with self.db:
            self._set(key, value)

    def configure_range(self, start, end, batch_size=32):
        index_key(start)
        index_key(end)
        if start > end or isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid finite range or batch size")
        existing = self.get_state("range")
        if existing is not None and existing != [start, end]:
            raise ValueError("Resume range differs from checkpoint")
        with self.db:
            if existing is None:
                self._set("range", [start, end])
                self._set("next_index", start)
            self._set("batch_size", batch_size)

    def claim_range(self, worker, max_seeds=None):
        """Claim one retry or one new bounded range. Only the parent calls this."""
        if max_seeds is not None and (isinstance(max_seeds, bool) or not isinstance(max_seeds, int) or max_seeds < 1):
            raise ValueError("Invalid range claim limit")
        with self.db:
            row = self.db.execute("SELECT start,end FROM ranges WHERE status='retry' ORDER BY start LIMIT 1").fetchone()
            if row:
                if max_seeds is not None and int(row[1]) - int(row[0]) > max_seeds:
                    split = index_key(int(row[0]) + max_seeds)
                    self.db.execute("UPDATE ranges SET end=? WHERE start=?", (split, row[0]))
                    self.db.execute("INSERT INTO ranges(start,end,status,attempts) VALUES (?,?,'retry',0)", (split, row[1]))
                    row = (row[0], split)
                self.db.execute("UPDATE ranges SET status='in_progress',worker=?,attempts=attempts+1 WHERE start=?", (str(worker), row[0]))
                return tuple(map(int, row))
            bounds = self.get_state("range")
            if bounds is None:
                raise ValueError("Configure the finite scan range before claiming work")
            start = self.get_state("next_index")
            if start >= bounds[1]:
                return None
            end = min(bounds[1], start + min(self.get_state("batch_size"), max_seeds or self.get_state("batch_size")))
            self.db.execute("INSERT INTO ranges(start,end,status,worker) VALUES (?,?,?,?)", (index_key(start), index_key(end), "in_progress", str(worker)))
            self._set("next_index", end)
            return start, end

    def recover_assignments(self):
        with self.db:
            cursor = self.db.execute("UPDATE ranges SET status='retry',worker=NULL WHERE status='in_progress'")
        return cursor.rowcount

    def prepare_range(self, start, end, results):
        if self.retention['mode']!='full':raise ValueError('Compact checkpoints require retained preparation')
        return self._prepare_range(start,end,results)

    def prepare_retained_range(self,start,end,results,receipt):
        """Sparse retained evidence; a complete range decision receipt is mandatory."""
        if self.retention['mode']!='survivors' or self._digest_version!=2:
            raise ValueError('Retained preparation requires a compact v2 checkpoint')
        if not isinstance(receipt,dict) or receipt.get('version')!='native-retention-receipt-v1':raise ValueError('Invalid retention receipt')
        for key in ('inputs','retained_inputs','retained_anchors','discovered_anchors'):
            if isinstance(receipt.get(key),bool) or not isinstance(receipt.get(key),int) or receipt[key]<0:raise ValueError('Invalid receipt counts')
        digest=receipt.get('input_decisions_sha256')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('Invalid decision digest')
        results=list(results)
        from .config import baseline_requirements
        from .config import two_group_policy
        policy=self.identity.get('config',{})
        group=two_group_policy(policy)
        requirements_total=baseline_requirements(policy)
        if receipt['inputs']!=end-start or receipt['retained_inputs']!=len(results) or receipt['retained_anchors']!=sum(len(r.get('anchors',[])) for r in results) or receipt['discovered_anchors']<receipt['retained_anchors']:
            raise ValueError('Receipt coverage mismatch')
        for result in results:
            if not result.get('anchors'):raise ValueError('Compact rows require retained anchors')
            for candidate in result['anchors']:
                label=candidate.get('retention',{});pending=candidate.get('pending_reasons')
                unmet=candidate.get('deficit_categories') if group else pending
                if (not isinstance(pending,list) or not isinstance(unmet,list) or len(set(pending))!=len(pending) or
                    len(set(unmet))!=len(unmet) or len(unmet)>self.retention['max_misses'] or
                    (group and (candidate.get('fatal_reasons') or candidate.get('biome_failures') or candidate.get('baseline_qualification')!='PREDICTED')) or
                    label.get('unmet_requirements')!=len(unmet) or
                    label.get('allowed_unmet_requirements')!=self.retention['max_misses'] or
                    label.get('requirements_total')!=requirements_total or label.get('classification')!=('PREDICTED_SURVIVOR' if group else 'NEAR_MISS' if pending else 'PREDICTED_SURVIVOR') or
                    candidate.get('qualification')!=('PREDICTED' if group else 'PENDING' if pending else 'PREDICTED') or
                    not candidate.get('biomes') or any(o.get('inventory_status')!='COMPLETE' for o in candidate.get('required_structures',{}).values())):
                    raise ValueError('Invalid retained eligibility or evidence')
        return self._prepare_range(start,end,results,receipt=receipt)

    def _prepare_range(self, start, end, results, *, receipt=None):
        """Validate and encode once, outside the writer's transaction.

        This method uses cached immutable policy and no SQLite calls; preparation
        may run off the connection thread. The dictionary API uses it too.
        """
        index_key(start); index_key(end)
        if end < start: raise ValueError('Invalid finite range')
        started = time.perf_counter()
        from .native_encoding import candidate_encoding, summary_encoding
        results = list(results)
        if receipt is None and len(results) != end - start:
            raise ValueError("Incomplete worker batch")
        by_index = {}
        seed_rows, candidate_rows, batch_counts = [], [], {}
        encoding_seconds = 0.; payload_bytes = 0
        candidate_objects = {}
        for result in results:
            idx = result.get("index")
            if isinstance(idx, bool) or not isinstance(idx, int) or not start <= idx < end or idx in by_index:
                raise ValueError("Duplicate or out-of-range worker index")
            seed = result.get("seed")
            if not isinstance(seed, str) or str(parse_seed(seed)) != seed:
                raise ValueError("Worker seed must be a canonical signed decimal string")
            by_index[idx] = result
            anchors = {}
            anchor_ids = []
            for candidate in result.get("anchors", []):
                point = candidate.get("stronghold")
                if not isinstance(point, (list, tuple)) or len(point) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in point):
                    raise ValueError("Invalid candidate Stronghold")
                cid = f"{seed}:{point[0]}:{point[1]}"
                if candidate.get("id") != cid or candidate.get("seed") != seed:
                    raise ValueError("Candidate id/seed/Stronghold mismatch")
                qualification = candidate.get("qualification")
                if qualification not in {"PREDICTED", "PENDING", "FAILED", "VERIFIED"}:
                    raise ValueError("Unknown candidate qualification")
                stamp = time.perf_counter()
                payload = candidate_encoding(candidate, canonical)
                encoding_seconds += time.perf_counter()-stamp
                if cid in anchors and anchors[cid] != payload:
                    raise ValueError("Conflicting duplicate candidate")
                anchors[cid] = payload
                candidate_objects[cid] = candidate
                anchor_ids.append(cid)
            stamp = time.perf_counter()
            encoded_summary = summary_encoding(result)
            if encoded_summary is None:
                summary = {key: value for key, value in result.items() if key != "anchors"}
                if "anchor_ids" in summary:
                    raise ValueError("Worker result uses reserved anchor_ids field")
                summary["anchor_ids"] = anchor_ids
                encoded_summary = canonical(summary)
            encoding_seconds += time.perf_counter()-stamp
            seed_rows.append((index_key(idx), seed, encoded_summary))
            for cid, payload in anchors.items():
                candidate = candidate_objects[cid]
                candidate_rows.append((cid, index_key(idx), seed, candidate["qualification"], payload))
            for key, value in result.get("counts", {}).items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("Invalid worker counter")
                batch_counts[key] = batch_counts.get(key, 0) + value
        ordered = [by_index[i] for i in sorted(by_index)]
        hash_started = time.perf_counter()
        if self._digest_version == 2:
            hasher = hashlib.sha256(b'realm-range-digest-v2')
            for collection in (sorted(seed_rows), sorted(candidate_rows)):
                hasher.update(len(collection).to_bytes(8, 'big'))
                for fields in collection:
                    framed = bytearray()
                    for field in fields:
                        value = field.encode()
                        framed.extend(len(value).to_bytes(8, 'big')); framed.extend(value)
                    payload_bytes += len(value)
                    hasher.update(framed)
            digest = hasher.hexdigest()
        else:
            digest = hashlib.sha256(canonical(ordered).encode()).hexdigest()
        encoded_receipt=None
        if receipt is not None:
            encoded_receipt=canonical({**receipt,'start':start,'end':end,'retention':self.retention})
            digest=hashlib.sha256(canonical(['realm-retained-range-v1',digest,encoded_receipt]).encode()).hexdigest()
            payload_bytes+=len(encoded_receipt.encode())
            batch_counts.update(scanned_inputs=end-start,retained_inputs=len(results),
                retained_anchors=receipt['retained_anchors'],discarded_inputs=end-start-len(results),
                discovered_anchors=receipt['discovered_anchors'])
        hash_seconds = time.perf_counter()-hash_started
        task_started = time.perf_counter()
        inventory_rows = []
        for cid, idx, seed, qualification, payload in candidate_rows:
            inventory_rows.extend(self._inventory_rows(candidate_objects[cid]))
        discovery_rows = [(r[0], name) for r in seed_rows for name in ('stronghold','fortress')]
        variant_rows = [(r[0], variant) for r in candidate_rows if r[3]!='FAILED' for variant in self.active_variants]
        if self._digest_version != 2:
            payload_bytes = sum(len(r[-1].encode()) for r in seed_rows+candidate_rows)
        timings = {'prepare_seconds':time.perf_counter()-started,'encoding_seconds':encoding_seconds,
                   'hash_seconds':hash_seconds,'task_preparation_seconds':time.perf_counter()-task_started}
        timings['validation_row_seconds'] = timings['prepare_seconds']-encoding_seconds-hash_seconds-timings['task_preparation_seconds']
        return _restore_prepared((start,end,tuple(seed_rows),tuple(candidate_rows),tuple(inventory_rows),
                             tuple(discovery_rows),tuple(variant_rows),tuple(sorted(batch_counts.items())),
                             digest,payload_bytes,self._preparation_policy,tuple(timings.items()),encoded_receipt))

    def complete_range(self, start, end, results, *, capacity_check=None):
        return self.complete_prepared(self.prepare_range(start,end,results),capacity_check=capacity_check)

    def complete_prepared(self, prepared, *, capacity_check=None, lease=None):
        """Atomically save a validated owned batch; connection stays writer-owned."""
        if not isinstance(prepared,PreparedRange) or prepared._token is not _PREPARATION_TOKEN or prepared.policy != self._preparation_policy:
            raise ValueError('Invalid or incompatible prepared range')
        start_key,end_key=index_key(prepared.start),index_key(prepared.end)
        row=self.db.execute('SELECT end,status,digest,worker,attempts FROM ranges WHERE start=?',(start_key,)).fetchone()
        if row is None or row[0]!=end_key:raise ValueError('Unknown or mismatched range')
        if row[1]=='complete':
            if row[2]!=prepared.digest:raise ValueError('Completed range retry differs from committed results')
            return False
        if lease is not None and (row[1]!='in_progress' or (row[3],row[4])!=tuple(lease)):
            raise ValueError('Stale range lease')
        if (prepared.receipt is not None)!=(self.retention['mode']=='survivors'):raise ValueError('Prepared retention mode differs from checkpoint')
        if prepared.receipt is not None and json.loads(prepared.receipt)['retention']!=self.retention:
            raise ValueError('Prepared near-miss allowance differs from checkpoint')
        if capacity_check is not None:capacity_check(3*prepared.payload_bytes)
        timings=dict(prepared.timings);sql_started=time.perf_counter()
        with self.db:
            self.db.executemany('INSERT INTO seeds VALUES (?,?,?)',prepared.seed_rows)
            self.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?)',prepared.candidate_rows)
            self.db.executemany("INSERT OR IGNORE INTO inventory_work(unit_id,candidate_id,kind,identity,status) VALUES (?,?,?,?,'pending')",prepared.inventory_rows)
            self.db.executemany("INSERT INTO discovery_tasks(idx,structure,status) VALUES (?,?,'pending')",prepared.discovery_rows)
            self.db.executemany("INSERT INTO variant_tasks VALUES (?,?,'pending')",prepared.variant_rows)
            if prepared.receipt is not None:
                self.db.execute('INSERT INTO retention_receipts VALUES (?,?,?,?)',(start_key,end_key,prepared.receipt,prepared.digest))
            self.db.execute("UPDATE ranges SET status='complete',worker=NULL,digest=? WHERE start=?",(prepared.digest,start_key))
            self._set('completed_seeds',self.get_state('completed_seeds')+prepared.end-prepared.start)
            counts=self.get_state('counts')
            for key,value in prepared.counts:counts[key]=counts.get(key,0)+value
            self._set('counts',counts)
            timings['sql_seconds']=time.perf_counter()-sql_started
            commit_started=time.perf_counter()
        timings['commit_seconds']=time.perf_counter()-commit_started
        self.last_range_timings=timings
        return True

    def status(self):
        bounds = self.get_state("range")
        completed = self.get_state("completed_seeds")
        ranges = dict(self.db.execute("SELECT status,count(*) FROM ranges GROUP BY status"))
        candidates = dict(self.db.execute("SELECT qualification,count(*) FROM candidates GROUP BY qualification"))
        revision = self.get_state("rescore_revision")
        task_counts = list(self.db.execute("SELECT variant,status,count(*) FROM variant_tasks GROUP BY variant,status"))
        return {"schema": SCHEMA, "retention":self.retention,
                "saved_seed_rows":self.db.execute('SELECT count(*) FROM seeds').fetchone()[0],
                "coverage_scope":('every processed input and discovered anchor retained' if self.retention['mode']=='full' else 'predictor-processing range checkpoints; discarded inputs/anchors have no individual evidence'),
                "range": bounds, "completed_seeds": completed,
                "total_seeds": bounds[1] - bounds[0] if bounds else 0,
                "remaining_seeds": bounds[1] - bounds[0] - completed if bounds else 0,
                "ranges": ranges, "candidate_counts": candidates, "counts": self.get_state("counts"),
                "active_variants": list(self.active_variants),
                "variant_tasks": {f"{variant}:{status}": count for variant, status, count in task_counts if variant in self.active_variants},
                "inactive_variant_tasks": {f"{variant}:{status}": count for variant, status, count in task_counts if variant not in self.active_variants},
                "score_revision": {key: value for key, value in revision.items() if key != "policy"} if revision else None,
                "discovery_tasks": dict(self.db.execute("SELECT status,count(*) FROM discovery_tasks GROUP BY status")),
                "inventory_work": dict(self.db.execute("SELECT status,count(*) FROM inventory_work GROUP BY status")),
                "discovery_coverage": "Unresolved tasks retain unvalidated recall; completed seeds count predictor processing, not authoritative discovery coverage",
                "worker_statistics": self.get_state("worker_statistics"), "memory": self.get_state("memory"),
                "workspace_disk":self.get_state('workspace_disk'),"workspace_disk_failure":self.get_state('workspace_disk_failure')}

    def iter_candidates(self, statuses=None, batch_size=256, *, include_score=False):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        statuses = [statuses] if isinstance(statuses, str) else list(statuses or [])
        last = ""
        while True:
            condition = " AND qualification IN (" + ",".join("?" for _ in statuses) + ")" if statuses else ""
            table='candidate_leaderboard_view' if include_score else 'candidates'
            fields='id,result,smart_score' if include_score else 'id,result'
            rows = self.db.execute(f"SELECT {fields} FROM {table} WHERE id>?" + condition + " ORDER BY id LIMIT ?", (last, *statuses, batch_size)).fetchall()
            if not rows:
                return
            for row in rows:
                candidate=json.loads(row[1])
                if include_score:candidate['smart_score']=row[2]
                yield candidate
            last = rows[-1][0]

    def iter_results(self, batch_size=256):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        last = ""
        while True:
            rows = self.db.execute("SELECT idx,result FROM seeds WHERE idx>? ORDER BY idx LIMIT ?", (last, batch_size)).fetchall()
            if not rows:
                return
            for idx, payload in rows:
                result = json.loads(payload)
                if "anchor_ids" in result:
                    candidates = {cid: json.loads(candidate) for cid, candidate in self.db.execute("SELECT id,result FROM candidates WHERE idx=?", (idx,))}
                    result["anchors"] = [candidates[cid] for cid in result.pop("anchor_ids")]
                yield result
            last = rows[-1][0]

    def get_candidate(self, candidate_id):
        row = self.db.execute("SELECT result FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def backfill_discovery_tasks(self, *, after_index=None, batch_size=256):
        """Explicit bounded legacy migration; missing observations remain unavailable."""
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 4096:
            raise ValueError("Invalid discovery backfill page size")
        after = "" if after_index is None else index_key(after_index)
        rows = self.db.execute("SELECT idx FROM seeds WHERE idx>? ORDER BY idx LIMIT ?", (after, batch_size)).fetchall()
        with self.db:
            before = self.db.total_changes
            self.db.executemany("INSERT OR IGNORE INTO discovery_tasks(idx,structure,status) VALUES (?,?,'pending')",
                                [(row[0], name) for row in rows for name in ('stronghold', 'fortress')])
            inserted = self.db.total_changes - before
        return {"visited_seeds": len(rows), "inserted_tasks": inserted,
                "next_after_index": int(rows[-1][0]) if rows else after_index}

    def get_discovery_task(self, index, structure):
        row = self.db.execute("SELECT t.status,t.worker,t.attempts,t.result,s.seed,s.result FROM discovery_tasks t JOIN seeds s ON s.idx=t.idx WHERE t.idx=? AND t.structure=?",
                              (index_key(index), structure)).fetchone()
        if row is None:
            return None
        seed_result = json.loads(row[5])
        observation = seed_result.get('discovery', {}).get(structure)
        return {"index": index, "seed": row[4], "structure": structure, "status": row[0],
                "worker": row[1], "attempts": row[2], "recovery_evidence": json.loads(row[3]) if row[3] else None,
                "discovery_observation": observation,
                "evidence_status": "SAVED_PREDICTION" if observation is not None else "LEGACY_EVIDENCE_UNAVAILABLE",
                "coverage_status": "RESOLVED" if row[0] == 'complete' else "UNRESOLVED"}

    def iter_discovery_tasks(self, *, status=None, structure=None, batch_size=256):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        last = ("", "")
        while True:
            terms, args = ["(idx,structure)>(?,?)"], list(last)
            for field, value in (("status", status), ("structure", structure)):
                if value is not None:
                    terms.append(f"{field}=?"); args.append(value)
            rows = self.db.execute("SELECT idx,structure FROM discovery_tasks WHERE " + " AND ".join(terms) + " ORDER BY idx,structure LIMIT ?", (*args, batch_size)).fetchall()
            if not rows:
                return
            for idx, name in rows:
                yield self.get_discovery_task(int(idx), name)
            last = rows[-1]

    def claim_discovery_task(self, worker):
        with self.db:
            # Serialize competing recovery consumers before selecting a pending lease.
            self.db.execute("UPDATE discovery_tasks SET worker=worker WHERE 0")
            row = self.db.execute("SELECT idx,structure FROM discovery_tasks WHERE status='pending' ORDER BY idx,structure LIMIT 1").fetchone()
            if row is None:
                return None
            self.db.execute("UPDATE discovery_tasks SET status='in_progress',worker=?,attempts=attempts+1 WHERE idx=? AND structure=?", (str(worker), *row))
        return self.get_discovery_task(int(row[0]), row[1])

    def recover_discovery_assignments(self):
        """Call only once the previous recovery owner is known to have stopped."""
        with self.db:
            cursor = self.db.execute("UPDATE discovery_tasks SET status='pending',worker=NULL WHERE status='in_progress'")
        return cursor.rowcount

    def complete_discovery_task(self, index, structure, evidence):
        """Resolve recall only with explicit complete actual-generation coverage.

        This records supplied evidence, not an independent certification of a provider.
        It never changes scan coverage or silently creates additional candidate anchors.
        Settings cover discovery query bounds, not independently verified world settings.
        """
        if self.db.in_transaction:
            raise ValueError("Finish the caller transaction before completing discovery recovery")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return self._complete_discovery_task_locked(index, structure, evidence)

    def _complete_discovery_task_locked(self, index, structure, evidence):
        task = self.get_discovery_task(index, structure)
        if task is None:
            raise ValueError("Unknown discovery task")
        cfg = (self.identity or {}).get('config', {})
        game, settings = cfg.get('game', {}), cfg.get('discovery', {})
        bounds = settings.get('overworld_bounds' if structure == 'stronghold' else 'nether_bounds')
        source = evidence.get('source', {})
        coordinates = evidence.get('coordinates')
        if (not isinstance(source, dict) or source.get('kind') != 'actual_generation'
                or not isinstance(source.get('provider'), str) or not source['provider'].strip()
                or not isinstance(source.get('version'), str) or not source['version'].strip()
                or source.get('provider') == 'native'
                or not game.get('target_version') or source.get('target_version') != game['target_version']
                or (source.get('provider') == 'bds' and source['version'] != game.get('bds_version'))
                or (source.get('provider') != 'bds' and source['version'] != game['target_version'])
                or evidence.get('seed') != task['seed'] or evidence.get('structure') != structure
                or not settings or evidence.get('settings') != settings or bounds is None or evidence.get('bounds') != bounds
                or evidence.get('complete') is not True or evidence.get('coverage_complete') is not True
                or evidence.get('verification') != 'VERIFIED' or not isinstance(evidence.get('confirmed_absent'), bool)
                or not isinstance(coordinates, list)
                or any(not isinstance(p, list) or len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in p) for p in coordinates)
                or any(not (bounds[0] <= p[0] < bounds[2] and bounds[1] <= p[1] < bounds[3]) for p in coordinates)
                or evidence.get('confirmed_absent') != (not coordinates)):
            raise ValueError("Discovery recovery requires complete actual source/version/settings/bounds coverage evidence")
        payload = canonical(evidence)
        if task['status'] == 'complete':
            if canonical(task['recovery_evidence']) != payload:
                raise ValueError("Completed discovery evidence is immutable")
            return False
        if task['status'] != 'in_progress':
            raise ValueError("Claim discovery task before completing recovery")
        self.db.execute("UPDATE discovery_tasks SET status='complete',worker=NULL,result=? WHERE idx=? AND structure=?", (payload, index_key(index), structure))
        return True

    def _inventory_rows(self, candidate):
        inventory=candidate.get('inventory',{})
        kinds=inventory.get('tasks',[])
        if any(kind not in ('structures','biomes') for kind in kinds):
            raise ValueError('Unknown inventory task kind')
        if not kinds:return []
        identity={'version':inventory['version'],'sampling':inventory['sampling_policy'],
                  'backend_sha256':self._inventory_backend_digest,'bounds':candidate['bounds']}
        encoded=canonical(identity);cid=canonical(candidate['id'])
        return [(hashlib.sha256(('['+cid+','+canonical(kind)+','+encoded+']').encode()).hexdigest(),
                 candidate['id'],kind,encoded) for kind in kinds]

    def _ensure_inventory_locked(self, candidate):
        self.db.executemany("INSERT OR IGNORE INTO inventory_work(unit_id,candidate_id,kind,identity,status) VALUES (?,?,?,?,'pending')",self._inventory_rows(candidate))

    def recover_inventory_work(self):
        with self.db:
            self.db.execute("UPDATE inventory_work SET status='pending',worker=NULL WHERE status IN ('running','failed')")

    def claim_inventory_work(self, worker, candidate_id=None, *, include_pending=False):
        if self.db.in_transaction:
            raise ValueError('Finish caller transaction before inventory dispatch')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            terms = ["w.status='pending'"]
            args = []
            if candidate_id is not None:
                terms.append('w.candidate_id=?'); args.append(candidate_id)
            if not include_pending:
                terms.append("c.qualification IN ('PREDICTED','VERIFIED')")
            row = self.db.execute("SELECT w.unit_id,w.candidate_id,w.kind,w.identity,w.attempts FROM inventory_work w JOIN candidates c ON c.id=w.candidate_id WHERE " + ' AND '.join(terms) + ' ORDER BY w.rowid LIMIT 1', args).fetchone()
            if row is None:
                return None
            uid, cid, kind, identity, attempts = row
            self.db.execute("UPDATE inventory_work SET status='running',worker=?,attempts=attempts+1 WHERE unit_id=?", (worker, uid))
            return {'unit_id': uid, 'candidate_id': cid, 'kind': kind, 'identity': json.loads(identity),
                    'worker': worker, 'attempt': attempts+1}

    def complete_inventory_work(self, unit, patch):
        digest = hashlib.sha256(canonical(patch).encode()).hexdigest()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT status,worker,attempts,digest FROM inventory_work WHERE unit_id=?', (unit['unit_id'],)).fetchone()
            if row is None or row[2] != unit['attempt']:
                raise ValueError('Stale inventory lease')
            if row[0] == 'complete':
                if row[3] != digest:
                    raise ValueError('Completed inventory retry differs')
                return False
            if row[:2] != ('running', unit['worker']):
                raise ValueError('Inventory lease is not owned by this worker')
            candidate = self.get_candidate(unit['candidate_id'])
            updated = {**candidate, **patch}
            remaining = [kind for kind in candidate['inventory']['tasks'] if kind != unit['kind']]
            updated['inventory'] = {**candidate['inventory'], 'tasks': remaining,
                                    'status': 'DEFERRED' if remaining else 'COMPLETE'}
            updated['baseline_score_complete'] = not remaining
            observed = (updated.get('biomes') or {}).get('score', 0) + sum(
                obs.get('bonus', 0) for obs in updated.get('optional_structures', {}).values())
            updated['baseline_score_observed'] = observed
            updated['baseline_score'] = None if remaining else observed
            updated['baseline_score_status'] = 'PARTIAL; inventory deferred' if remaining else 'PREDICTED; observed predictor score'
            policy = self.get_state('score_policy') or self.identity['config']
            from .baseline import baseline_score_uncertainty
            updated['baseline_score_uncertainty'] = baseline_score_uncertainty(updated.get('biomes'), updated.get('optional_structures', {}), policy, updated.get('pending_reasons', []))
            if not remaining:
                updated['processing_status'] = 'baseline_complete' if updated['qualification'] != 'PENDING' else 'baseline_pending'
            self._upsert_candidate_locked(updated)
            self.db.execute("UPDATE inventory_work SET status='complete',worker=NULL,result=?,digest=? WHERE unit_id=?", (canonical(patch), digest, unit['unit_id']))
            return True

    def fail_inventory_work(self, unit, error):
        with self.db:
            changed = self.db.execute("UPDATE inventory_work SET status='failed',worker=NULL,result=? WHERE unit_id=? AND status='running' AND worker=? AND attempts=?",
                                     (canonical({'error': str(error)}), unit['unit_id'], unit['worker'], unit['attempt'])).rowcount
            if not changed:
                raise ValueError('Stale inventory failure lease')

    def upsert_candidate(self, candidate, *, allow_qualification_change=False):
        """Update saved evidence/score; eligibility changes require explicit opt-in.

        Only complete_range creates candidates, so this cannot invent covered anchors.
        Missing fields preserve the saved record and immutable seed/anchor identity.
        """
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before updating candidate evidence")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return self._upsert_candidate_locked(candidate, allow_qualification_change=allow_qualification_change)

    def _upsert_candidate_locked(self, candidate, *, allow_qualification_change=False):
        cid = candidate.get("id")
        previous = self.get_candidate(cid)
        if previous is None:
            raise ValueError("Unknown baseline candidate")
        updated = {**previous, **candidate}
        immutable = ("id", "seed", "stronghold", "index", "game_version", "bds_version", "backend_model", "backend_commit", "bounds")
        if any(updated.get(key) != previous.get(key) for key in immutable if key in previous):
            raise ValueError("Baseline candidate identity is immutable")
        qualification = updated.get("qualification")
        if qualification not in {"PREDICTED", "PENDING", "FAILED", "VERIFIED"}:
            raise ValueError("Unknown candidate qualification")
        if qualification != previous.get("qualification") and not allow_qualification_change:
            raise ValueError("Qualification changes require explicit authorization")
        self.db.execute("UPDATE candidates SET qualification=?,result=? WHERE id=?", (qualification, canonical(updated), cid))
        if qualification != "FAILED":
            self.db.executemany("INSERT OR IGNORE INTO variant_tasks VALUES (?,?,'pending')", [(cid, variant) for variant in self.active_variants])
        return updated

    def ensure_terrain_pool(self, identity, statuses=None, *, revision=None, new_revision=False, progress=None):
        """Freeze explicit membership once; later baseline arrivals require a new revision."""
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before freezing a terrain pool")
        statuses = sorted(set(statuses or ('PREDICTED', 'VERIFIED')))
        encoded_identity, encoded_statuses = canonical(identity), canonical(statuses)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            active = self.get_state('terrain_pool_revision')
            if active is not None and self.get_terrain_pool(active)['identity'] != identity:
                raise ValueError("Terrain provider/algorithm identity changed; use a separate checkpoint")
            selected = revision or (None if new_revision else active)
            if selected is not None:
                pool = self.db.execute("SELECT identity,statuses FROM terrain_pools WHERE revision=?", (selected,)).fetchone()
                if pool is None:
                    raise ValueError("Unknown terrain pool revision")
                if pool != (encoded_identity, encoded_statuses):
                    raise ValueError("Terrain pool provider/algorithm/selection identity changed")
                return selected
            if active is None and self.db.execute("SELECT 1 FROM variants LIMIT 1").fetchone():
                raise ValueError("Historical terrain results lack a fixed pool revision; use a separate checkpoint")
            number = self.db.execute("SELECT count(*) FROM terrain_pools").fetchone()[0] + 1
            selected = f"pool-{number:08d}"
            self.db.execute("INSERT INTO terrain_pools VALUES (?,?,?,0)", (selected, encoded_identity, encoded_statuses))
            marks = ','.join('?' for _ in statuses)
            cursor = self.db.execute("INSERT INTO terrain_pool_members SELECT ?,id FROM candidates WHERE qualification IN (" + marks + ")", (selected, *statuses))
            members = cursor.rowcount
            self.db.execute("UPDATE terrain_pools SET members=? WHERE revision=?", (members, selected))
            self._set('terrain_pool_revision', selected)
        if progress:
            progress({'revision': selected, 'members': members, 'status': 'complete'})
        return selected

    def get_terrain_pool(self, revision):
        row = self.db.execute("SELECT identity,statuses,members FROM terrain_pools WHERE revision=?", (revision,)).fetchone()
        return {'revision': revision, 'identity': json.loads(row[0]), 'statuses': json.loads(row[1]), 'members': row[2]} if row else None

    def iter_terrain_pool_candidates(self, revision, batch_size=256, *, start_after=None, stop_at=None):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        if self.get_terrain_pool(revision) is None:
            raise ValueError("Unknown terrain pool revision")
        last = start_after or ''
        while True:
            upper = ' AND p.candidate_id<=?' if stop_at is not None else ''
            args = (revision, last, stop_at, batch_size) if stop_at is not None else (revision, last, batch_size)
            rows = self.db.execute("SELECT p.candidate_id,c.result FROM terrain_pool_members p JOIN candidates c ON c.id=p.candidate_id WHERE p.revision=? AND p.candidate_id>?" + upper + " ORDER BY p.candidate_id LIMIT ?", args).fetchall()
            if not rows:
                return
            for cid, payload in rows:
                yield json.loads(payload)
            last = rows[-1][0]

    def _terrain_unit_values(self, revision, candidate_id, variant, payload, status):
        if variant not in {'v1', 'v2'} or status not in {'pending', 'deferred'}:
            raise ValueError("Invalid terrain variant or initial work status")
        pool = self.get_terrain_pool(revision)
        candidate = self.get_candidate(candidate_id)
        if pool is None or candidate is None or not self.db.execute("SELECT 1 FROM terrain_pool_members WHERE revision=? AND candidate_id=?", (revision, candidate_id)).fetchone():
            raise ValueError("Terrain work must belong to a frozen pool")
        required = ('stage', 'coarse_center', 'resolution', 'halo_level', 'raster_bounds', 'lattice')
        if any(key not in payload for key in required) or payload['stage'] not in {'nomination', 'height', 'halo'}:
            raise ValueError("Terrain work needs exact stage/center/resolution/halo/bounds/lattice")
        for key in ('resolution', 'halo_level'):
            value = payload[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < (1 if key == 'resolution' else 0):
                raise ValueError("Invalid terrain resolution or halo level")
        center, bounds = payload['coarse_center'], payload['raster_bounds']
        if (not isinstance(center, (list, tuple)) or len(center) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in center)
                or not isinstance(bounds, (list, tuple)) or len(bounds) != 4
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in bounds)
                or bounds[0] >= bounds[2] or bounds[1] >= bounds[3] or not isinstance(payload['lattice'], dict)):
            raise ValueError("Invalid terrain center/bounds/lattice")
        priority = payload.get('priority', payload.get('coarse_score', 0))
        if isinstance(priority, bool) or not isinstance(priority, (int, float)) or not math.isfinite(priority):
            raise ValueError("Invalid terrain priority")
        unit_identity = {'revision': revision, 'candidate_id': candidate_id, 'variant': variant,
                         **{key: payload[key] for key in required}}
        unit_id = hashlib.sha256(canonical(unit_identity).encode()).hexdigest()
        sampling = {'identity': pool['identity'], 'seed': candidate['seed'], 'stage': 'nomination' if payload['stage'] == 'nomination' else 'height',
                    **{key: payload[key] for key in ('resolution', 'raster_bounds', 'lattice')}}
        if 'sampling_scope' in payload:
            if not isinstance(payload['sampling_scope'], str) or not payload['sampling_scope']:
                raise ValueError("Terrain sampling scope must be a nonempty string")
            sampling['scope'] = payload['sampling_scope']
            unit_identity['sampling_scope'] = payload['sampling_scope']
            unit_id = hashlib.sha256(canonical(unit_identity).encode()).hexdigest()
        sampling_key = hashlib.sha256(canonical(sampling).encode()).hexdigest()
        return (unit_id, revision, candidate_id, variant, status, priority, canonical(payload), sampling_key)

    def _insert_terrain_work(self, revision, candidate_id, variant, payload, status='pending'):
        values = self._terrain_unit_values(revision, candidate_id, variant, payload, status)
        prior = self.db.execute("SELECT payload FROM terrain_work WHERE unit_id=?", (values[0],)).fetchone()
        if prior:
            if prior[0] != values[6]:
                raise ValueError("Terrain work identity already has different immutable payload")
        else:
            self.db.execute("INSERT INTO terrain_work(unit_id,revision,candidate_id,variant,status,priority,payload,sampling_key) VALUES (?,?,?,?,?,?,?,?)", values)
        return values[0]

    def ensure_terrain_work(self, revision, candidate_id, variant, payload, status='pending'):
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before enqueuing terrain work")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return self._insert_terrain_work(revision, candidate_id, variant, payload, status)

    def get_terrain_work(self, unit_id):
        row = self.db.execute("SELECT revision,candidate_id,variant,status,priority,payload,sampling_key,worker,attempts,result FROM terrain_work WHERE unit_id=?", (unit_id,)).fetchone()
        if row is None:
            return None
        return dict(zip(('revision','candidate_id','variant','status','priority','payload','sampling_key','worker','attempts','result'),
                        (row[0], row[1], row[2], row[3], row[4], json.loads(row[5]), row[6], row[7], row[8], json.loads(row[9]) if row[9] else None)), unit_id=unit_id)

    def iter_terrain_work(self, revision, candidate_id=None, variant=None, status=None, batch_size=256):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        last = None
        while True:
            terms, args = ['revision=?'], [revision]
            for field, value in (('candidate_id', candidate_id), ('variant', variant), ('status', status)):
                if value is not None:
                    terms.append(f'{field}=?'); args.append(value)
            if last is not None:
                terms.append('(priority<? OR (priority=? AND unit_id>?))'); args.extend((last[0], last[0], last[1]))
            rows = self.db.execute("SELECT priority,unit_id FROM terrain_work WHERE " + ' AND '.join(terms) + " ORDER BY priority DESC,unit_id LIMIT ?", (*args, batch_size)).fetchall()
            if not rows:
                return
            for priority, uid in rows:
                yield self.get_terrain_work(uid)
            last = rows[-1]

    def claim_terrain_work(self, unit_id, worker):
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before claiming terrain work")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            unit = self.get_terrain_work(unit_id)
            if unit is None:
                raise ValueError("Unknown terrain work")
            if unit['status'] not in {'pending', 'deferred'}:
                return None
            self.db.execute("UPDATE terrain_work SET status='leased',worker=?,attempts=attempts+1 WHERE unit_id=?", (str(worker), unit_id))
        return self.get_terrain_work(unit_id)

    def recover_terrain_work(self, revision):
        """Only the scheduler holding the run lock may recover an abandoned owner."""
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before recovering terrain work")
        with self.db:
            cursor = self.db.execute("UPDATE terrain_work SET status='pending',worker=NULL WHERE revision=? AND status='leased'", (revision,))
        return cursor.rowcount

    def claim_priority_terrain(self,revision,variants,worker,epoch,*,continue_manual=False,max_refinements=None):
        """Indexed bounded refill, alternating variants, three ranked/one oldest.

        Queue hints are immutable scheduling evidence, not eligibility or exported
        scores. Dispatch cycle and lease commit in the same transaction. SQLite
        provides the rank/age views directly; no unbounded Python heap is needed.
        """
        if self.db.in_transaction:raise ValueError('Finish caller transaction before priority dispatch')
        variants=sorted(set(variants))
        if not variants or any(v not in ('v1','v2') for v in variants):raise ValueError('Invalid priority variants')
        if max_refinements is not None and (isinstance(max_refinements,bool) or not isinstance(max_refinements,int) or max_refinements<0):raise ValueError('Invalid priority center budget')
        self.db.execute('CREATE TEMP TABLE IF NOT EXISTS priority_centers(epoch TEXT,candidate_id TEXT,variant TEXT,center TEXT,PRIMARY KEY(epoch,candidate_id,variant,center))')
        policy={'version':'terrain-priority-v1','ranked_per_oldest':3,'refill_limit':4096,
                'baseline_range':[0,60],'geometry_range':[0,100],'unknown_hint':50,'weights':[.5,.5]}
        key=f'terrain_priority_cycle:{revision}'
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            saved=self.get_state(key) or {'policy':policy,'next_variant':'v1','positions':{'v1':0,'v2':0},'dispatches':0}
            if saved['policy']!=policy:raise ValueError('Priority queue policy changed')
            rows=self.db.execute("SELECT w.rowid,w.unit_id,w.variant,w.payload,c.result FROM terrain_work w JOIN candidates c ON c.id=w.candidate_id LEFT JOIN terrain_priority_queue q ON q.unit_id=w.unit_id WHERE w.revision=? AND q.unit_id IS NULL ORDER BY w.rowid LIMIT 4096",(revision,)).fetchall()
            for ordinal,uid,variant,payload,candidate in rows:
                p=json.loads(payload);c=json.loads(candidate);baseline=c.get('baseline_score')
                if isinstance(baseline,dict):baseline=baseline.get('normalized',baseline.get('quality'))
                def hint(value,cap):
                    return 50. if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) else min(100.,max(0.,100.*value/cap))
                hints={'baseline':hint(baseline,60),'geometry':hint(p.get('coarse_score'),100)}
                score=.5*hints['baseline']+.5*hints['geometry']
                self.db.execute('INSERT INTO terrain_priority_queue VALUES (?,?,?,?,?,?,NULL)',(uid,revision,variant,ordinal,score,canonical(hints)))
            ordered=sorted(variants,key=lambda v:v!=saved['next_variant'])
            for variant in ordered:
                oldest=saved['positions'][variant]%4==3
                order='q.enqueue_ordinal,q.unit_id' if oldest else 'q.score DESC,q.enqueue_ordinal,q.unit_id'
                # One failed unit is tried once per invocation. Three failures
                # require explicit continuation; stage deferrals are not failures.
                sql=("SELECT w.unit_id FROM terrain_priority_queue q JOIN terrain_work w ON w.unit_id=q.unit_id "
                     "WHERE q.revision=? AND q.variant=? AND w.status IN ('pending','deferred') "
                     "AND (q.last_epoch IS NULL OR q.last_epoch!=?) "
                     "AND (? OR NOT coalesce(json_extract(w.payload,'$.manual_continuation_required'),0)) "
                     "AND (? OR w.attempts<3 OR (json_extract(w.result,'$.result.sampling_failure') IS NULL AND json_extract(w.result,'$.state.capacity_failure') IS NULL)) "
                     "AND (? IS NULL OR json_extract(w.payload,'$.stage')='nomination' OR "
                     "((w.status!='deferred' AND EXISTS(SELECT 1 FROM priority_centers p WHERE p.epoch=? AND p.candidate_id=w.candidate_id AND p.variant=w.variant AND p.center=json_extract(w.payload,'$.coarse_center'))) OR "
                     "((SELECT count(*) FROM priority_centers p WHERE p.epoch=? AND p.candidate_id=w.candidate_id AND p.variant=w.variant)<? AND NOT EXISTS(SELECT 1 FROM priority_centers p WHERE p.epoch=? AND p.candidate_id=w.candidate_id AND p.variant=w.variant AND p.center=json_extract(w.payload,'$.coarse_center'))))) "
                     'ORDER BY '+order+' LIMIT 1')
                row=self.db.execute(sql,(revision,variant,str(epoch),continue_manual,continue_manual,max_refinements,str(epoch),str(epoch),max_refinements,str(epoch))).fetchone()
                if row is None:continue
                uid=row[0]
                unit=self.get_terrain_work(uid)
                if unit['payload']['stage']!='nomination':
                    self.db.execute('INSERT OR IGNORE INTO priority_centers VALUES (?,?,?,?)',(str(epoch),unit['candidate_id'],variant,canonical(unit['payload']['coarse_center'])))
                self.db.execute("UPDATE terrain_work SET status='leased',worker=?,attempts=attempts+1 WHERE unit_id=?",(str(worker),uid))
                self.db.execute('UPDATE terrain_priority_queue SET last_epoch=? WHERE unit_id=?',(str(epoch),uid))
                saved['positions'][variant]+=1;saved['dispatches']+=1;saved['next_variant']='v2' if variant=='v1' else 'v1'
                saved['last']={'unit_id':uid,'variant':variant,'slot':'oldest' if oldest else 'ranked','enqueue_ordinal':self.db.execute('SELECT enqueue_ordinal FROM terrain_priority_queue WHERE unit_id=?',(uid,)).fetchone()[0]}
                self._set(key,saved)
                return self.get_terrain_work(uid)
            self._set(key,saved)
        return None

    def complete_terrain_work(self, unit_id, result=None, successor_units=(), variant_results=(), observation=None, state=None, candidate_update=None):
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before committing terrain work")
        successor_units, variant_results = list(successor_units), list(variant_results)
        if len(successor_units) > 4096 or len(variant_results) > 4096:
            raise ValueError("Terrain completion batch exceeds bounded commit size")
        completed = {'result': result, 'successor_units': successor_units, 'variant_results': variant_results, 'observation': observation, 'state': state}
        if candidate_update is not None:completed['candidate_update']=candidate_update
        digest = hashlib.sha256(canonical(completed).encode()).hexdigest()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            unit = self.get_terrain_work(unit_id)
            if unit is None:
                raise ValueError("Unknown terrain work")
            prior_digest = self.db.execute("SELECT digest FROM terrain_work WHERE unit_id=?", (unit_id,)).fetchone()[0]
            if unit['status'] == 'complete':
                if prior_digest != digest:
                    raise ValueError("Completed terrain retry differs from committed work")
                return False
            if unit['status'] != 'leased':
                raise ValueError("Claim terrain work before completing it")
            if observation is not None:
                if (observation.get('id') != unit['sampling_key'] or observation.get('bounds') != unit['payload']['raster_bounds']
                        or observation.get('resolution') != unit['payload']['resolution'] or observation.get('lattice') != unit['payload']['lattice']
                        or not isinstance(observation.get('channels'), dict) or not observation['channels']):
                    raise ValueError("Terrain observation needs matching sampling key/bounds/lattice and raw channels")
                previous = self.get_observation(unit['sampling_key'])
                if previous is not None and canonical(previous) != canonical(observation):
                    raise ValueError("Shared terrain observation is immutable")
                self._account_terrain_observation(observation)
                self.db.execute("INSERT OR IGNORE INTO observations VALUES (?,NULL,?)", (unit['sampling_key'], canonical(observation)))
            elif self.get_observation(unit['sampling_key']) is None:
                raise ValueError("Terrain completion requires a durable raw sampling observation")
            for successor in successor_units:
                if successor.get('candidate_id', unit['candidate_id']) != unit['candidate_id'] or successor.get('variant', unit['variant']) != unit['variant']:
                    raise ValueError("Successor terrain work must preserve its evaluation chain")
                self._insert_terrain_work(unit['revision'], unit['candidate_id'], unit['variant'], successor['payload'], successor.get('status', 'pending'))
            for variant_result in variant_results:
                if variant_result['candidate_id'] != unit['candidate_id'] or variant_result['variant'] != unit['variant']:
                    raise ValueError("Terrain result must preserve its evaluation chain")
                wrapper = {key: variant_result[key] for key in ('candidate_id','variant','center','result')}
                self.db.execute("INSERT INTO variants VALUES (?,?,?,?) ON CONFLICT(candidate_id,variant,center) DO UPDATE SET result=excluded.result",
                                (unit['candidate_id'], unit['variant'], canonical(wrapper['center']), canonical(wrapper)))
            if candidate_update is not None:
                if candidate_update.get('id')!=unit['candidate_id']:raise ValueError('Marine update must preserve terrain candidate')
                self._upsert_candidate_locked(candidate_update)
            self.db.execute("UPDATE terrain_work SET status='complete',worker=NULL,result=?,digest=? WHERE unit_id=?", (canonical({'result': result, 'state': state}), digest, unit_id))
            self.db.execute("UPDATE variant_tasks SET status='started' WHERE candidate_id=? AND variant=?", (unit['candidate_id'], unit['variant']))
        return True

    def terrain_work_complete(self, revision, candidate_id, variant):
        """An empty or budget-limited queue cannot masquerade as completed evaluation."""
        statuses = dict(self.db.execute("SELECT status,count(*) FROM terrain_work WHERE revision=? AND candidate_id=? AND variant=? GROUP BY status", (revision, candidate_id, variant)))
        return bool(statuses) and set(statuses) == {'complete'}

    def defer_terrain_work(self, unit_id, result=None, observation=None, state=None, variant_results=(), *, expected_attempt=None, worker=None):
        """Atomically retain a failed attempt while leaving its exact work retryable.

        Failed observations never occupy the reusable sampling key. Optional attempt
        and owner tokens reject stale callers even when no raw observation exists.
        """
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before deferring terrain work")
        variant_results = list(variant_results)
        if len(variant_results) > 4096:
            raise ValueError("Terrain deferral batch exceeds bounded commit size")
        contents = {'result': result, 'state': state, 'observation': observation, 'variant_results': variant_results}
        digest = hashlib.sha256(canonical(contents).encode()).hexdigest()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            unit = self.get_terrain_work(unit_id)
            if unit is None:
                raise ValueError("Unknown terrain work")
            if expected_attempt is not None and (isinstance(expected_attempt, bool) or not isinstance(expected_attempt, int) or expected_attempt != unit['attempts']):
                raise ValueError("Terrain attempt ownership changed")
            previous = self.db.execute("SELECT worker,digest FROM terrain_work_attempts WHERE unit_id=? AND attempt=?", (unit_id, unit['attempts'])).fetchone()
            if unit['status'] == 'deferred' and previous is not None:
                if previous[1] != digest or (worker is not None and worker != previous[0]):
                    raise ValueError("Deferred terrain retry differs from committed attempt")
                return False
            if unit['status'] != 'leased' or (worker is not None and worker != unit['worker']):
                raise ValueError("Claim current terrain attempt before deferring it")
            if observation is not None:
                expected_ids = {f"{unit['sampling_key']}:attempt:{unit['attempts']}",
                                f"{unit['sampling_key']}:unit:{unit_id}:attempt:{unit['attempts']}"}
                if (observation.get('id') not in expected_ids or observation.get('sampling_key') != unit['sampling_key']
                        or observation.get('bounds') != unit['payload']['raster_bounds']
                        or observation.get('resolution') != unit['payload']['resolution'] or observation.get('lattice') != unit['payload']['lattice']
                        or not isinstance(observation.get('channels'), dict) or not observation['channels']):
                    raise ValueError("Failed terrain observation must match current attempt sampling key/bounds/lattice/raw channels")
                old = self.get_observation(observation['id'])
                if old is not None and canonical(old) != canonical(observation):
                    raise ValueError("Failed terrain attempt observation is immutable")
                self._account_terrain_observation(observation)
                self.db.execute("INSERT OR IGNORE INTO observations VALUES (?,NULL,?)", (observation['id'], canonical(observation)))
            for variant_result in variant_results:
                if variant_result['candidate_id'] != unit['candidate_id'] or variant_result['variant'] != unit['variant']:
                    raise ValueError("Terrain result must preserve its evaluation chain")
                wrapper = {key: variant_result[key] for key in ('candidate_id', 'variant', 'center', 'result')}
                self.db.execute("INSERT INTO variants VALUES (?,?,?,?) ON CONFLICT(candidate_id,variant,center) DO UPDATE SET result=excluded.result",
                                (unit['candidate_id'], unit['variant'], canonical(wrapper['center']), canonical(wrapper)))
            self.db.execute("INSERT INTO terrain_work_attempts VALUES (?,?,?,?,?)",
                            (unit_id, unit['attempts'], unit['worker'], digest,
                             canonical({key: value for key, value in contents.items() if key != 'observation'} |
                                       {'observation_id': observation['id'] if observation is not None else None})))
            self.db.execute("UPDATE terrain_work SET status='deferred',worker=NULL,result=? WHERE unit_id=?", (canonical({'result': result, 'state': state}), unit_id))
            if isinstance(state, dict) and state.get('capacity_failure'):
                self._set('terrain_disk_last_failure', {'unit_id': unit_id, 'attempt': unit['attempts'], 'reason': state['capacity_failure']})
            self.db.execute("UPDATE variant_tasks SET status='started' WHERE candidate_id=? AND variant=?", (unit['candidate_id'], unit['variant']))
        return True

    def terrain_work_counts(self, revision, candidate_id=None, variant=None):
        terms, args = ['revision=?'], [revision]
        for field, value in (('candidate_id', candidate_id), ('variant', variant)):
            if value is not None:
                terms.append(f'{field}=?'); args.append(value)
        return dict(self.db.execute("SELECT status,count(*) FROM terrain_work WHERE " + ' AND '.join(terms) + " GROUP BY status", args))

    def configure_terrain_disk_policy(self, limit_bytes=8 << 30, free_reserve_bytes=16 << 30):
        """Engineering defaults bound serialized rasters; they are not host measurements.

        Existing observations are counted and retained even when already over budget.
        This cap is logical serialized payload size, not a maximum SQLite file size.
        """
        for name, value in (('limit_bytes', limit_bytes), ('free_reserve_bytes', free_reserve_bytes)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f'{name} must be a nonnegative integer number of bytes')
        if self.db.in_transaction:
            raise ValueError("Finish caller transaction before configuring terrain disk policy")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if not self.get_state('terrain_disk_accounting_initialized'):
                self.db.execute("INSERT OR IGNORE INTO terrain_observation_bytes SELECT id,length(CAST(result AS BLOB)) FROM observations WHERE json_extract(result,'$.kind')='terrain_raster'")
                # Prior attempt journals duplicated raw payloads. Preserve them and
                # count those copies; new journals hold only immutable references.
                self.db.execute("INSERT OR IGNORE INTO terrain_observation_bytes SELECT 'legacy-journal:'||unit_id||':'||attempt,length(CAST(json_extract(result,'$.observation') AS BLOB)) FROM terrain_work_attempts WHERE json_type(result,'$.observation')='object'")
                usage = self.db.execute("SELECT coalesce(sum(bytes),0) FROM terrain_observation_bytes").fetchone()[0]
                self._set('terrain_disk_usage_bytes', usage)
                self._set('terrain_disk_accounting_initialized', True)
            self._set('terrain_disk_policy', {'limit_bytes': limit_bytes, 'free_reserve_bytes': free_reserve_bytes,
                                            'accounting': 'UTF-8 serialized durable raster observations including failed attempts; SQLite/WAL overhead separate'})
        return self.terrain_disk_status()

    def terrain_disk_status(self):
        policy = self.get_state('terrain_disk_policy')
        usage = self.get_state('terrain_disk_usage_bytes') or 0
        result = {'policy': policy, 'accounted_raster_bytes': usage,
                  'last_capacity_failure': self.get_state('terrain_disk_last_failure')}
        try:
            result['free_disk_bytes'] = shutil.disk_usage(self.run).free
            result['disk_monitor_available'] = True
        except OSError as exc:
            result.update(disk_monitor_available=False, disk_monitor_error=str(exc))
        result['sqlite_file_bytes'] = sum(path.stat().st_size for path in (self.run/'realm.sqlite', self.run/'realm.sqlite-wal') if path.exists())
        return result

    def _account_terrain_observation(self, observation):
        """Check/reserve new bytes inside the caller's BEGIN IMMEDIATE transaction."""
        oid = observation['id']
        payload_bytes = len(canonical(observation).encode('utf-8'))
        prior = self.db.execute("SELECT bytes FROM terrain_observation_bytes WHERE id=?", (oid,)).fetchone()
        if prior:
            if prior[0] != payload_bytes:
                raise ValueError("Immutable terrain observation byte accounting changed")
            return
        policy = self.get_state('terrain_disk_policy')
        usage = self.get_state('terrain_disk_usage_bytes') or 0
        if policy is not None:
            try:
                free = shutil.disk_usage(self.run).free
            except OSError as exc:
                raise TerrainCapacityError('Terrain disk monitoring unavailable; raw observation remains uncommitted') from exc
            if usage + payload_bytes > policy['limit_bytes']:
                raise TerrainCapacityError(f"Terrain durable raster cap reached: projected {usage + payload_bytes} bytes exceeds {policy['limit_bytes']}")
            # Conservative engineering allowance for pages and WAL, not a measured
            # bound on filesystem allocation or another process's concurrent writes.
            required_free = policy['free_reserve_bytes'] + 3 * payload_bytes + (64 << 10)
            if free < required_free:
                raise TerrainCapacityError(f"Terrain free disk reserve reached: {free} bytes free, {required_free} required")
        self.db.execute("INSERT INTO terrain_observation_bytes VALUES (?,?)", (oid, payload_bytes))
        self._set('terrain_disk_usage_bytes', usage + payload_bytes)

    def terrain_pool_uninitialized_counts(self, revision):
        pool = self.get_terrain_pool(revision)
        if pool is None:
            raise ValueError("Unknown terrain pool revision")
        return {variant: pool['members'] - self.db.execute(
            "SELECT count(DISTINCT candidate_id) FROM terrain_work WHERE revision=? AND variant=?",
            (revision, variant)).fetchone()[0] for variant in pool['identity'].get('terrain', {}).get('variants', self.active_variants)}

    def upsert_variant(self, candidate_id, variant, center, result):
        if variant not in {"v1", "v2"}:
            raise ValueError("Realm terrain supports v1 and v2")
        if not self.db.execute("SELECT 1 FROM candidates WHERE id=?", (candidate_id,)).fetchone():
            raise ValueError("Unknown baseline candidate")
        payload = {"candidate_id": candidate_id, "variant": variant, "center": center, "result": result}
        with self.db:
            self.db.execute("INSERT INTO variants VALUES (?,?,?,?) ON CONFLICT(candidate_id,variant,center) DO UPDATE SET result=excluded.result", (candidate_id, variant, canonical(center), canonical(payload)))
            self.db.execute("UPDATE variant_tasks SET status='started' WHERE candidate_id=? AND variant=? AND status='pending'", (candidate_id, variant))

    def iter_variant_tasks(self, variant=None, status=None, batch_size=256):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        last = ("", "")
        while True:
            terms, args = ["(candidate_id,variant)>(?,?)"], list(last)
            for field, value in (("variant", variant), ("status", status)):
                if value is not None:
                    terms.append(f"{field}=?")
                    args.append(value)
            rows = self.db.execute("SELECT candidate_id,variant,status FROM variant_tasks WHERE " + " AND ".join(terms) + " ORDER BY candidate_id,variant LIMIT ?", (*args, batch_size)).fetchall()
            if not rows:
                return
            for cid, task_variant, task_status in rows:
                yield {"candidate_id": cid, "variant": task_variant, "status": task_status}
            last = rows[-1][:2]

    def set_variant_task_status(self, candidate_id, variant, status, *, pool_revision=None):
        if status not in {"pending", "started", "complete"}:
            raise ValueError("Invalid variant task status")
        revision = pool_revision or self.get_state('terrain_pool_revision')
        if status == 'complete' and revision is not None and not self.terrain_work_complete(revision, candidate_id, variant):
            raise ValueError("Pending/deferred terrain work prevents aggregate completion")
        with self.db:
            cursor = self.db.execute("UPDATE variant_tasks SET status=? WHERE candidate_id=? AND variant=?", (status, candidate_id, variant))
            if not cursor.rowcount:
                raise ValueError("Unknown variant task")

    def get_variant_task_status(self, candidate_id, variant):
        row = self.db.execute("SELECT status FROM variant_tasks WHERE candidate_id=? AND variant=?", (candidate_id, variant)).fetchone()
        return row[0] if row else None

    def get_variant(self, candidate_id, variant, center):
        row = self.db.execute("SELECT result FROM variants WHERE candidate_id=? AND variant=? AND center=?", (candidate_id, variant, canonical(center))).fetchone()
        return json.loads(row[0]) if row else None

    def iter_variants(self, candidate_id=None, variant=None, batch_size=256):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        last = ("", "", "")
        while True:
            terms, args = ["(candidate_id,variant,center)>(?,?,?)"], list(last)
            if candidate_id is not None:
                terms.append("candidate_id=?")
                args.append(candidate_id)
            if variant is not None:
                terms.append("variant=?")
                args.append(variant)
            rows = self.db.execute("SELECT candidate_id,variant,center,result FROM variants WHERE " + " AND ".join(terms) + " ORDER BY candidate_id,variant,center LIMIT ?", (*args, batch_size)).fetchall()
            if not rows:
                return
            for row in rows:
                yield json.loads(row[3])
            last = rows[-1][:3]

    def upsert_observation(self, candidate_id, observation=None):
        if observation is None:
            observation = candidate_id
            candidate_id = observation.get("candidate_id")
        if candidate_id is not None and not self.db.execute("SELECT 1 FROM candidates WHERE id=?", (candidate_id,)).fetchone():
            raise ValueError("Unknown baseline candidate")
        payload = dict(observation)
        payload.setdefault("candidate_id", candidate_id)
        oid = payload.get("id") or hashlib.sha256(canonical(payload).encode()).hexdigest()
        payload["id"] = oid
        terrain_raw = payload.get('kind') == 'terrain_raster'
        if terrain_raw and self.db.in_transaction:
            raise ValueError("Finish caller transaction before writing terrain observation")
        with self.db:
            if terrain_raw:
                self.db.execute("BEGIN IMMEDIATE")
                prior = self.get_observation(oid)
                if prior is not None and canonical(prior) != canonical(payload):
                    raise ValueError("Durable terrain observation is immutable")
                self._account_terrain_observation(payload)
            self.db.execute("INSERT INTO observations VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET candidate_id=excluded.candidate_id,result=excluded.result", (str(oid), candidate_id, canonical(payload)))
        return oid

    def iter_observations(self, candidate_id=None, batch_size=256):
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("Invalid page size")
        last = ""
        while True:
            extra = " AND candidate_id=?" if candidate_id is not None else ""
            args = (last, candidate_id, batch_size) if candidate_id is not None else (last, batch_size)
            rows = self.db.execute("SELECT id,result FROM observations WHERE id>?" + extra + " ORDER BY id LIMIT ?", args).fetchall()
            if not rows:
                return
            for _, payload in rows:
                yield json.loads(payload)
            last = rows[-1][0]

    def get_observation(self, key):
        row = self.db.execute("SELECT result FROM observations WHERE id=?", (str(key),)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
