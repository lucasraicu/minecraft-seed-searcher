# Storage and Web Control Audit Report

**Auditor Agent**: G-STORE (Storage and Web Control Auditor)  
**Audit Target**: `dynamic-envelope-1664-v1` Storage Layer & Web Control Plane  
**Target Specification**: Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes MC_26_50  
**Durability Contract**: SQLite WAL mode, `PRAGMA synchronous = FULL`  
**Report Date**: 2026-10-15  
**Probe Directory**: `reviews/split-audit-2026-10-15/gemini/probes/store/`  

---

## Executive Summary

An exhaustive independent audit of the Minecraft seed searcher storage persistence engine (`src/seed_search/realm/store.py`), the web control plane backend (`src/seed_search/web/server.py`), and the native pipeline transaction caller (`src/seed_search/realm/native_batch.py`) was conducted.

The audit verified critical strengths in the engine, including strict schema validation, deterministic candidate encoding, JSON canonicalization, and crash-resilient WAL configuration. However, **8 distinct vulnerabilities and architectural defects** were uncovered across the storage and web control planes:
- **G-STORE-01 (HIGH)**: Web UI candidate caching in `server.py` relies exclusively on `(count, max(rowid))` dirtiness signatures. In-place `UPDATE` operations on candidates (such as BDS surface verification, inventory task completion, and manual score changes) leave `(count, max(rowid))` invariant, causing the web server to serve stale candidate data indefinitely.
- **G-STORE-02 (HIGH)**: A Time-of-Check to Time-of-Use (TOCTOU) race condition in `RealmStore.complete_prepared` validates range lease ownership outside the transaction prior to file system capacity checks. The subsequent `UPDATE ranges SET status='complete' ...` lacks lease preconditions in its `WHERE` clause, permitting stale or reassigned workers to overwrite active leases and double-count seeds in compact retention mode.
- **G-STORE-03 (MEDIUM)**: `RealmStore.complete_range` bypasses lease validation entirely by invoking `complete_prepared` with `lease=None`, permitting unauthenticated commits across recovered and foreign-claimed ranges.
- **G-STORE-04 (MEDIUM)**: `claim_range` and `complete_prepared` use Python's deferred transaction mode (`with self.db:`) instead of `_immediate_transaction`. Under concurrent range claims, simultaneous read locks followed by lock upgrades cause `sqlite3.IntegrityError: UNIQUE constraint failed: ranges.start` and lock deadlocks.
- **G-STORE-05 (MEDIUM)**: `SweepManager.pause_sweep` and `stop_sweep` block on `subprocess.Popen.wait()` for up to 30 seconds while holding `self.lock`, causing complete HTTP starvation of `GET /api/sweep/status` polling clients.
- **G-STORE-06 (LOW)**: `RealmStore` relies on passive WAL autocheckpoints without explicit checkpoint maintenance, allowing active readers or unexhausted cursors to block frame checkpoints and cause WAL file bloat.
- **G-STORE-07 (LOW / ARCHITECTURAL)**: `native_batch.py` passes the entire `store` instance across a thread boundary to `ThreadPoolExecutor` workers. While current preparation code avoids DB calls, this fragile coupling risks immediate `sqlite3.ProgrammingError` crashes under default `check_same_thread=True`.
- **G-STORE-08 (LOW)**: `SweepManager.list_runs` accesses and mutates `self._runs_cache` without thread synchronization under `ThreadingHTTPServer`.

All findings are grounded with dedicated, automated reproduction probes in `reviews/split-audit-2026-10-15/gemini/probes/store/`.

---

## Findings Matrix

| Finding ID | Severity | File & Line Anchor | Title / Summary | Reproduction Probe |
|---|---|---|---|---|
| **G-STORE-01** | **HIGH** | `src/seed_search/web/server.py:516-535` | Stale Candidate Caching via Invariant `(count, max(rowid))` Signature on In-Place `UPDATE` | `probe_candidate_cache_invalidation.py` |
| **G-STORE-02** | **HIGH** | `src/seed_search/realm/store.py:423-444` | TOCTOU Lease Validation & Blind Overwrite in `complete_prepared` | `probe_toctou_lease_overwrite.py` |
| **G-STORE-03** | **MEDIUM** | `src/seed_search/realm/store.py:415-416` | Missing Lease Validation in `complete_range` Bypasses Worker Ownership | `probe_complete_range_no_lease.py` |
| **G-STORE-04** | **MEDIUM** | `src/seed_search/realm/store.py:247-266` | Deferred Transactions in `claim_range` Cause `IntegrityError` Under Concurrency | `probe_deferred_transaction_lock.py` |
| **G-STORE-05** | **MEDIUM** | `src/seed_search/web/server.py:366-384`, `468-489` | Web Server Global Lock Starvation During Sweep Pause/Stop Blocking Waits | `probe_web_server_lock_starvation.py` |
| **G-STORE-06** | **LOW** | `src/seed_search/realm/store.py:134-144` | WAL Checkpoint Blockage and File Bloat Under Concurrent Readers | `probe_wal_checkpoint_growth.py` |
| **G-STORE-07** | **LOW** | `src/seed_search/realm/native_batch.py:485`, `store.py:310` | Fragile Cross-Thread `RealmStore` Sharing Violates Connection Thread Confinement | `probe_connection_thread_confinement.py` |
| **G-STORE-08** | **LOW** | `src/seed_search/web/server.py:315-325` | Unsynchronized `_runs_cache` Mutation Under Concurrent HTTP Requests | Code Inspection / Trace |

---

## Detailed Audit Findings

### G-STORE-01: Stale Candidate Caching via Invariant `(count, max(rowid))` Signature

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L516-L535`
- **Component**: `SweepManager._query_sqlite_candidates`

#### 2. Vulnerability Mechanism
In `src/seed_search/web/server.py`, `SweepManager._query_sqlite_candidates()` maintains an in-memory cache of candidate records (`self.candidates`) to avoid expensive JSON decoding and leaderboard ranking queries on every status poll. The cache invalidation logic computes a dirtiness signature:

```python
# Lines 516-535 in server.py
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
```

`sig` evaluates `(count(*), max(rowid))` on `candidates`, `variants`, and `observations`.
In SQLite:
1. When a candidate record is updated in place via `UPDATE candidates SET qualification=?, result=? WHERE id=?` (such as in `RealmStore.upsert_candidate`, `surface.py:67` BDS surface biome verification, `RealmStore.complete_inventory_work`, or candidate qualification updates):
   - The row count (`count(*)`) is strictly unchanged.
   - The SQLite `rowid` of the updated record is strictly unchanged.
   - Therefore, `cand_sig` is identical before and after the update.
2. If the update does not insert new variant rows or observation rows (e.g., BDS surface point verification stores its results directly in the candidate result JSON, or inventory completion resolves missing structures), `var_sig` and `obs_sig` also remain identical.
3. As a result, `_last_candidates_sig == sig` evaluates to `True`, and `_query_sqlite_candidates()` returns early without re-querying the database.
4. The web server continues serving outdated candidate data (old scores, `PREDICTED` instead of `VERIFIED`, missing surface verification evidence) to `/api/candidates` and `/api/sweep/status`.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_candidate_cache_invalidation.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_candidate_cache_invalidation.py`
- **Output / Evidence**:
  ```
  [Probe] Initial sig: ('.../web-sweep-20261015-120000-abcd1234', (1, 1), (0, None), (0, None))
  [Probe] Initial candidate score: 55.0, qualification: PREDICTED
  [Probe] SQLite DB verified: qualification=VERIFIED, score=99.0
  [Probe] SQLite count, max(rowid) after update: (1, 1)
  [Probe] After query_sqlite_candidates(): sig=('.../web-sweep-20261015-120000-abcd1234', (1, 1), (0, None), (0, None))
  [Probe] Cached candidate score: 55.0, qualification: PREDICTED
  [BUG CONFIRMED] G-STORE-01: Manager served stale candidate data from cache!
    Expected: score=99.0, qualification=VERIFIED
    Actual:   score=55.0, qualification=PREDICTED
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: Any modification to candidate evidence, verification state, qualification, or score updates the web server's candidate cache on the subsequent poll.
- **Actual**: `sig` does not change on `UPDATE` operations, causing the web server to serve stale candidate information indefinitely.

#### 5. Minimal Unapplied Fix
Track database file modification via WAL mtime/size or use SQLite `PRAGMA data_version` across a persistent connection, or incorporate `candidates` data change indicators:
```diff
--- a/src/seed_search/web/server.py
+++ b/src/seed_search/web/server.py
@@ -513,6 +513,11 @@ class SweepManager:
             conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
             cur = conn.cursor()
 
+            wal_path = self.run_dir / "realm.sqlite-wal"
+            db_stat = (db_path.stat().st_mtime_ns, wal_path.stat().st_mtime_ns if wal_path.exists() else 0, wal_path.stat().st_size if wal_path.exists() else 0)
+
             # Dirtiness check before re-parsing
             cur.execute("SELECT count(*), max(rowid) FROM candidates")
             cand_sig = cur.fetchone()
@@ -528,7 +533,7 @@ class SweepManager:
             if has_obs:
                 cur.execute("SELECT count(*), max(rowid) FROM observations")
                 obs_sig = cur.fetchone()
 
-            sig = (str(self.run_dir), cand_sig, var_sig, obs_sig)
+            sig = (str(self.run_dir), cand_sig, var_sig, obs_sig, db_stat)
             if getattr(self, '_last_candidates_sig', None) == sig and self.candidates:
                 return
             self._last_candidates_sig = sig
```

---

### G-STORE-02: TOCTOU Lease Validation & Blind Overwrite in `complete_prepared`

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/store.py#L423-L444`
- **Component**: `RealmStore.complete_prepared`

#### 2. Vulnerability Mechanism
In `RealmStore.complete_prepared`:
```python
# Lines 423-444 in store.py
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
```

1. **Check outside transaction**: The range lease check occurs at line 428 *outside* the transaction. The transaction context manager `with self.db:` is only entered at line 435, after `capacity_check` executes filesystem I/O (`shutil.disk_usage`).
2. **Blind UPDATE WHERE clause**: Inside the transaction at line 443, the update query is:
   `UPDATE ranges SET status='complete',worker=NULL,digest=? WHERE start=?`
   It contains no check on `status='in_progress'`, `worker=?`, or `attempts=?`!
3. **Lease hijacking and double counting**: If a range is recovered (`recover_assignments`) and reassigned to Worker B (attempt 2) while Worker A (attempt 1) is running `capacity_check`:
   - Worker A enters the transaction and blindly updates `ranges` to `status='complete'`, hijacking Worker B's active lease.
   - In compact survivor mode (`retention='survivors'`), when a batch contains 0 survivors, `seed_rows`, `candidate_rows`, `discovery_rows`, and `variant_rows` are all empty tuples, so no primary key integrity constraints fail.
   - Worker A increments `completed_seeds` and updates `counts`.
   - When Worker B later attempts to commit, Worker B finds `ranges.status == 'complete'` and fails with `ValueError: Completed range retry differs from committed results`.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_toctou_lease_overwrite.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_toctou_lease_overwrite.py`
- **Output / Evidence**:
  ```
  [Probe] Inside capacity_check: simulating recovery and reassignment to Worker B...
  [Probe] Range in DB is now: status=in_progress, worker=worker-B, attempts=2
  [Probe] Stale Worker A complete_prepared returned: True
  [Probe] Range in DB after stale Worker A commit: ('complete', None, 2)
  [Probe] completed_seeds after Worker A: 10
  [Probe] Worker B failed to commit with error: ValueError: Completed range retry differs from committed results
  [BUG CONFIRMED] G-STORE-02: Stale Worker A committed and hijacked Worker B's active lease!
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: A worker with lease `('worker-A', 1)` must be rejected if the database record is reassigned to `('worker-B', 2)`.
- **Actual**: Worker A commits successfully because lease verification is not atomic with the update statement.

#### 5. Minimal Unapplied Fix
Move lease validation inside an immediate transaction and enforce lease conditions in the UPDATE statement's `WHERE` clause:
```diff
--- a/src/seed_search/realm/store.py
+++ b/src/seed_search/realm/store.py
@@ -420,18 +420,10 @@ class RealmStore:
         if not isinstance(prepared,PreparedRange) or prepared._token is not _PREPARATION_TOKEN or prepared.policy != self._preparation_policy:
             raise ValueError('Invalid or incompatible prepared range')
         start_key,end_key=index_key(prepared.start),index_key(prepared.end)
-        row=self.db.execute('SELECT end,status,digest,worker,attempts FROM ranges WHERE start=?',(start_key,)).fetchone()
-        if row is None or row[0]!=end_key:raise ValueError('Unknown or mismatched range')
-        if row[1]=='complete':
-            if row[2]!=prepared.digest:raise ValueError('Completed range retry differs from committed results')
-            return False
-        if lease is not None and (row[1]!='in_progress' or (row[3],row[4])!=tuple(lease)):
-            raise ValueError('Stale range lease')
         if (prepared.receipt is not None)!=(self.retention['mode']=='survivors'):raise ValueError('Prepared retention mode differs from checkpoint')
         if prepared.receipt is not None and json.loads(prepared.receipt)['retention']!=self.retention:
             raise ValueError('Prepared near-miss allowance differs from checkpoint')
         if capacity_check is not None:capacity_check(3*prepared.payload_bytes)
         timings=dict(prepared.timings);sql_started=time.perf_counter()
-        with self.db:
+        with self._immediate_transaction():
+            row=self.db.execute('SELECT end,status,digest,worker,attempts FROM ranges WHERE start=?',(start_key,)).fetchone()
+            if row is None or row[0]!=end_key:raise ValueError('Unknown or mismatched range')
+            if row[1]=='complete':
+                if row[2]!=prepared.digest:raise ValueError('Completed range retry differs from committed results')
+                return False
+            if lease is not None and (row[1]!='in_progress' or (row[3],row[4])!=tuple(lease)):
+                raise ValueError('Stale range lease')
             self.db.executemany('INSERT INTO seeds VALUES (?,?,?)',prepared.seed_rows)
             self.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?)',prepared.candidate_rows)
             self.db.executemany("INSERT OR IGNORE INTO inventory_work(unit_id,candidate_id,kind,identity,status) VALUES (?,?,?,?,'pending')",prepared.inventory_rows)
             self.db.executemany("INSERT INTO discovery_tasks(idx,structure,status) VALUES (?,?,'pending')",prepared.discovery_rows)
             self.db.executemany("INSERT INTO variant_tasks VALUES (?,?,'pending')",prepared.variant_rows)
             if prepared.receipt is not None:
                 self.db.execute('INSERT INTO retention_receipts VALUES (?,?,?,?)',(start_key,end_key,prepared.receipt,prepared.digest))
-            self.db.execute("UPDATE ranges SET status='complete',worker=NULL,digest=? WHERE start=?",(prepared.digest,start_key))
+            updated=self.db.execute("UPDATE ranges SET status='complete',worker=NULL,digest=? WHERE start=? AND status='in_progress' AND (? IS NULL OR (worker=? AND attempts=?))",
+                                    (prepared.digest,start_key,lease[0] if lease else None,lease[0] if lease else None,lease[1] if lease else None)).rowcount
+            if not updated:
+                raise ValueError('Range lease state changed before commit')
```

---

### G-STORE-03: Missing Lease Validation in `complete_range`

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/store.py#L415-L416`
- **Component**: `RealmStore.complete_range`

#### 2. Vulnerability Mechanism
`RealmStore.complete_range` is implemented as:
```python
def complete_range(self, start, end, results, *, capacity_check=None):
    return self.complete_prepared(self.prepare_range(start,end,results),capacity_check=capacity_check)
```
Notice that `complete_range` does not accept or forward a `lease` parameter to `complete_prepared`.
In `complete_prepared` (line 428):
```python
if lease is not None and (row[1]!='in_progress' or (row[3],row[4])!=tuple(lease)):
    raise ValueError('Stale range lease')
```
Because `lease` is `None`, line 428 is skipped entirely. This allows any caller of `complete_range` to commit results even when:
- The range was reset to `status='retry'` by `recover_assignments()`.
- The range was claimed by another worker.
In `src/seed_search/realm/runner.py:319`, the multi-process Python runner calls `store.complete_range(first, end, ...)` instead of `complete_prepared`, leaving the Python execution path completely exposed to stale commits across recovery events.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_complete_range_no_lease.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_complete_range_no_lease.py`
- **Output / Evidence**:
  ```
  [Probe] Initially claimed by: ('in_progress', 'worker-1', 1)
  [Probe] After recovery: ('retry', None, 1)
  [Probe] Reclaimed by worker-2: ('in_progress', 'worker-2', 2)
  [Probe] complete_range returned: True
  [Probe] Final range state: ('complete', None, 2)
  [BUG CONFIRMED] G-STORE-03: complete_range bypassed lease ownership and committed!
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: `complete_range` requires lease identification or defaults to rejecting non-in-progress/foreign-owned ranges.
- **Actual**: `complete_range` commits without validating lease ownership.

#### 5. Minimal Unapplied Fix
Accept an optional `lease` parameter in `complete_range` and require `status='in_progress'` even when `lease is None`:
```diff
--- a/src/seed_search/realm/store.py
+++ b/src/seed_search/realm/store.py
@@ -415,2 +415,2 @@ class RealmStore:
-    def complete_range(self, start, end, results, *, capacity_check=None):
-        return self.complete_prepared(self.prepare_range(start,end,results),capacity_check=capacity_check)
+    def complete_range(self, start, end, results, *, capacity_check=None, lease=None):
+        return self.complete_prepared(self.prepare_range(start,end,results),capacity_check=capacity_check,lease=lease)
@@ -428,2 +428,4 @@ class RealmStore:
-        if lease is not None and (row[1]!='in_progress' or (row[3],row[4])!=tuple(lease)):
-            raise ValueError('Stale range lease')
+        if row[1] != 'in_progress':
+            raise ValueError('Range is not in progress')
+        if lease is not None and (row[3], row[4]) != tuple(lease):
+            raise ValueError('Stale range lease')
```

---

### G-STORE-04: Deferred Transactions in `claim_range` Cause `IntegrityError` Under Concurrency

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/store.py#L247-L266`
- **Component**: `RealmStore.claim_range`

#### 2. Vulnerability Mechanism
In `RealmStore.claim_range`:
```python
# Lines 247-266 in store.py
with self.db:
    row = self.db.execute("SELECT start,end FROM ranges WHERE status='retry' ORDER BY start LIMIT 1").fetchone()
    if row:
        ...
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
```
In Python's `sqlite3`, `with self.db:` starts a deferred transaction upon the first DML statement.
1. When two workers invoke `claim_range` simultaneously, both execute the initial `SELECT` statements (`SELECT ... FROM ranges`, `SELECT ... FROM meta WHERE key='range'`, `SELECT ... FROM meta WHERE key='next_index'`) under shared read locks.
2. Both read the identical `next_index` (e.g. `0`).
3. Both proceed to generate the same primary key `index_key(0)`.
4. Worker 1 executes `INSERT INTO ranges ...` and succeeds.
5. Worker 2 executes `INSERT INTO ranges ...` with the identical start key `index_key(0)` and crashes with:
   `sqlite3.IntegrityError: UNIQUE constraint failed: ranges.start`!
Furthermore, in multi-process deployments, concurrent deferred transactions trying to upgrade shared read locks to reserved write locks cause `SQLITE_BUSY: database is locked`.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_deferred_transaction_lock.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_deferred_transaction_lock.py`
- **Output / Evidence**:
  ```
  [Probe] Claims made: 5, Errors: [(2, 'IntegrityError', 'UNIQUE constraint failed: ranges.start')]
  [Probe] claim_range uses _immediate_transaction: False
  [CODE CONFIRMED] G-STORE-04: claim_range uses 'with self.db:' instead of '_immediate_transaction'!
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: `claim_range` uses `BEGIN IMMEDIATE` with retries to serialize range allocations and prevent duplicate claims.
- **Actual**: `claim_range` uses deferred transactions, producing duplicate primary key collisions under concurrent callers.

#### 5. Minimal Unapplied Fix
Use `with self._immediate_transaction():` in `claim_range`:
```diff
--- a/src/seed_search/realm/store.py
+++ b/src/seed_search/realm/store.py
@@ -247,1 +247,1 @@ class RealmStore:
-        with self.db:
+        with self._immediate_transaction():
```

---

### G-STORE-05: Web Server Global Lock Starvation During Sweep Pause/Stop

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L366-L384`, `L468-L489`
- **Component**: `SweepManager.pause_sweep`, `SweepManager.stop_sweep`

#### 2. Vulnerability Mechanism
In `SweepManager`:
```python
# Lines 366-384 in server.py
def pause_sweep(self) -> dict:
    with self.lock:
        proc = self.process
        if proc is None or proc.poll() is not None or self.status not in ("running",):
            return {"ok": False, "error": "No active sweep to pause"}
        self.status = "paused"
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
```
And similarly in `stop_sweep` (line 482):
```python
try:proc.wait(timeout=30)
```
`SweepManager.lock` is held for the entire duration of `proc.wait(timeout=6.0)` or `proc.wait(timeout=30)`.
Because `get_status()` (which serves the high-frequency polling endpoint `GET /api/sweep/status`) also acquires `self.lock` (line 622), every polling request from browser clients is blocked for up to 8–30 seconds. In browsers polling every 500ms or 1s, requests queue up, leading to connection timeouts, UI freezes, and socket backlog exhaustion.

Additionally, neither `pause_sweep` nor `stop_sweep` increments `self.generation`. When the child process finally terminates, the asynchronous `_monitor_process` thread executes:
```python
with self.lock:
    if generation != self.generation or run_dir != self.run_dir: return
    self.end_time = time.time()
    ...
    self._record_throughput(self.seeds_per_sec)
```
Because `self.generation` was not incremented, `generation == self.generation` evaluates to `True`, allowing the monitor thread to overwrite telemetry metrics after the pause state took effect.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_web_server_lock_starvation.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_web_server_lock_starvation.py`
- **Output / Evidence**:
  ```
  [Probe] Calling manager.pause_sweep()...
  [Probe] Client sending GET /api/sweep/status (calling get_status())...
  [Probe] pause_sweep() returned after 2.043s with: {'ok': True, 'status': 'paused', 'scannedCount': 0, 'runId': 'test-run'}
  [Probe] get_status() unblocked after 1.938s! Status: paused
  [Probe] Polling request was blocked for 1.938s while holding manager.lock.
  [BUG CONFIRMED] G-STORE-05: Web server get_status was starved for > 1.5s while pause_sweep blocked on subprocess!
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: `pause_sweep` and `stop_sweep` transition process state and wait asynchronously or in a worker thread without holding `self.lock` across long timeouts.
- **Actual**: `self.lock` is held across synchronous `proc.wait()` calls, freezing all concurrent telemetry requests.

#### 5. Minimal Unapplied Fix
Mark state as `stopping` / `pausing`, release `self.lock`, wait on the process in a background thread or without holding the lock, and increment `self.generation`:
```diff
--- a/src/seed_search/web/server.py
+++ b/src/seed_search/web/server.py
@@ -367,7 +367,9 @@ class SweepManager:
         with self.lock:
             proc = self.process
             if proc is None or proc.poll() is not None or self.status not in ("running",):
                 return {"ok": False, "error": "No active sweep to pause"}
-            self.status = "paused"
+            self.status = "pausing"
+            self.generation += 1
+        # Release lock while waiting for process termination
         self.logs.insert(0, "Pausing sweep: waiting for current seed/batch to complete cleanly...")
         try:
             import signal
@@ -384,10 +386,11 @@ class SweepManager:
         except Exception as exc:
+            with self.lock:
                 self.status = 'error'
                 self.error_message = f'Failed to pause owned process: {exc}'
                 return {'ok': False, 'error': self.error_message}
+        with self.lock:
             if proc.poll() is None:
                 self.status = 'error'
                 return {'ok': False, 'error': 'Owned scan has not exited'}
             self.status = 'paused'
             self.process = None
```

---

### G-STORE-06: WAL Checkpoint Blockage and File Bloat Under Concurrent Readers

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/store.py#L134-L144`
- **Component**: `RealmStore.__init__` PRAGMA configuration

#### 2. Vulnerability Mechanism
`RealmStore` configures WAL mode with:
```python
self.db.execute("PRAGMA journal_mode=WAL")
self.db.execute("PRAGMA wal_autocheckpoint=16384")
self.db.execute("PRAGMA journal_size_limit=134217728")
```
1. `PRAGMA wal_autocheckpoint=16384` triggers `wal_checkpoint(PASSIVE)` whenever the WAL reaches 16,384 pages (64 MiB).
2. Under SQLite WAL semantics, passive checkpoints can only transfer frames up to the frame of the oldest active read transaction.
3. If an external client or web server reader opens a read transaction or unexhausted cursor (such as `leaderboard.rows(db, limit)` which yields an active cursor), `wal_checkpoint(PASSIVE)` cannot checkpoint frames past that read transaction.
4. `journal_size_limit=134217728` (128 MiB) is only applied when a checkpoint runs to completion. Because checkpoints cannot complete while readers are open, SQLite cannot truncate the WAL, causing the `-wal` file to grow past the 128 MiB threshold during continuous scanning.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_wal_checkpoint_growth.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_wal_checkpoint_growth.py`
- **Output / Evidence**:
  ```
  [Probe] Configured wal_autocheckpoint: 16384 pages
  [Probe] Configured journal_size_limit: 134217728 bytes (128 MiB)
  [Probe] WAL size while reader active: 1,874,632 bytes
  [Probe] PASSIVE checkpoint result: busy=0, log=455, checkpointed=84
  [Probe] Checkpoint blocked by reader: True (log=455, checkpointed=84)
  [Probe] Checkpoint after reader closed: busy=0, log=455, checkpointed=455
  [BUG/RISK CONFIRMED] G-STORE-06: Reader blocked WAL checkpointing from advancing!
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: WAL checkpoints run periodically to completion to bound WAL file size within configured limits.
- **Actual**: Open read transactions block passive checkpoints, allowing WAL frames to accumulate.

#### 5. Minimal Unapplied Fix
Execute explicit `PRAGMA wal_checkpoint(TRUNCATE)` at run boundaries or batch intervals when readers are idle:
```diff
--- a/src/seed_search/realm/store.py
+++ b/src/seed_search/realm/store.py
@@ -1249,2 +1249,5 @@ class RealmStore:
     def close(self):
+        try:
+            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
+        except Exception:
+            pass
         self.db.close()
```

---

### G-STORE-07: Fragile Cross-Thread `RealmStore` Sharing Violates Connection Thread Confinement

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L485`, `src/seed_search/realm/store.py#L310-L315`
- **Component**: `native_batch.persist_pipeline` and `prepare` task

#### 2. Vulnerability Mechanism
In `src/seed_search/realm/native_batch.py`:
```python
# Lines 485 in native_batch.py
future=None if prepare_on_writer else preparer.submit(prepare,native_future,first,end,store)
```
The entire `store` instance (`RealmStore`) is passed to `preparer` (a `ThreadPoolExecutor(max_workers=1, thread_name_prefix='native-records')`).
`RealmStore` owns `self.db = sqlite3.connect(...)`, which in Python defaults to `check_same_thread=True`.
While `store.prepare_range` and `store.prepare_retained_range` currently avoid touching `self.db`, passing the `RealmStore` instance across thread boundaries creates a fragile architecture: any helper function, accessor (`store.get_state()`), or debugging hook invoked inside `prepare` immediately causes `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`.

#### 3. Concrete Reproduction
- **Script**: `reviews/split-audit-2026-10-15/gemini/probes/store/probe_connection_thread_confinement.py`
- **Execution Command**: `./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_connection_thread_confinement.py`
- **Output / Evidence**:
  ```
  [Probe] Expected ProgrammingError caught when accessing store.db from another thread: SQLite objects created in a thread can only be used in that same thread.
  [Probe] prepare_range executed successfully on thread without touching store.db.
  [Probe] Cross-thread call to store.get_state() resulted in: CRASH: SQLite objects created in a thread can only be used in that same thread.
  [AUDIT CONFIRMED] G-STORE-07: RealmStore.db is strictly thread-confined. Passing store instance to preparer thread creates fragile coupling across thread boundaries.
  ```

#### 4. Expected vs. Actual Behavior
- **Expected**: Worker preparation threads receive only immutable policy tuples (`store._preparation_policy`), eliminating connection leakage.
- **Actual**: The full `store` instance containing thread-confined `self.db` is passed to the preparation thread.

#### 5. Minimal Unapplied Fix
Pass only `policy` to the preparation thread, or use static preparation methods:
```diff
--- a/src/seed_search/realm/native_batch.py
+++ b/src/seed_search/realm/native_batch.py
@@ -485,1 +485,1 @@ def persist_pipeline(...):
-        future=None if prepare_on_writer else preparer.submit(prepare,native_future,first,end,store)
+        future=None if prepare_on_writer else preparer.submit(prepare,native_future,first,end,store._preparation_policy,store.retention)
```

---

### G-STORE-08: Unsynchronized `_runs_cache` Mutation Under Concurrent HTTP Requests

#### 1. File Anchor
- **File**: `file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L315-L325`
- **Component**: `SweepManager.list_runs`

#### 2. Vulnerability Mechanism
`SweepManager.list_runs()` is invoked by `GET /api/sweep/runs`. The web server runs on `ThreadingHTTPServer`, spawning a separate OS thread for each HTTP connection.
Inside `list_runs()`:
```python
cached = self._runs_cache.get(directory.name)
if cached is not None and cached[0] == cache_key:
    ...
else:
    ...
    self._runs_cache[directory.name] = (cache_key, identity, completed, pipeline)
...
except ...:
    self._runs_cache.pop(directory.name, None)
```
Unlike `_biome_grid_cache` (which is guarded by `self._grid_lock`), `_runs_cache` is accessed and mutated without any lock. Concurrent HTTP requests to `/api/sweep/runs` mutate and pop from `self._runs_cache` simultaneously, risking race conditions and dict mutation inconsistencies.

#### 3. Expected vs. Actual Behavior
- **Expected**: All shared caches in `SweepManager` are synchronized across HTTP worker threads.
- **Actual**: `_runs_cache` has no lock synchronization.

#### 4. Minimal Unapplied Fix
Protect `_runs_cache` access with a dedicated lock or `self.lock`:
```diff
--- a/src/seed_search/web/server.py
+++ b/src/seed_search/web/server.py
@@ -315,3 +315,4 @@ class SweepManager:
-                cached = self._runs_cache.get(directory.name)
+                with self.lock:
+                    cached = self._runs_cache.get(directory.name)
@@ -320,1 +321,2 @@ class SweepManager:
-                    self._runs_cache[directory.name] = (cache_key, identity, completed, pipeline)
+                    with self.lock:
+                        self._runs_cache[directory.name] = (cache_key, identity, completed, pipeline)
```

---

## Probes and Verification Log

All test probes were implemented in `reviews/split-audit-2026-10-15/gemini/probes/store/` and executed cleanly using `./.venv/bin/python`:

| Probe Script | Target Finding | Verification Result |
|---|---|---|
| `probe_candidate_cache_invalidation.py` | G-STORE-01 | **PASSED** (Stale candidate cache reproduced: score 55.0 served instead of 99.0 after UPDATE) |
| `probe_toctou_lease_overwrite.py` | G-STORE-02 | **PASSED** (TOCTOU race reproduced: stale Worker A overwrote Worker B lease and double-counted) |
| `probe_complete_range_no_lease.py` | G-STORE-03 | **PASSED** (Bypass reproduced: `complete_range` committed with `lease=None` across recovered range) |
| `probe_deferred_transaction_lock.py` | G-STORE-04 | **PASSED** (Collision reproduced: `IntegrityError: UNIQUE constraint failed: ranges.start` on concurrent claims) |
| `probe_web_server_lock_starvation.py` | G-STORE-05 | **PASSED** (Starvation reproduced: `get_status` blocked for 1.94s while `pause_sweep` held lock) |
| `probe_wal_checkpoint_growth.py` | G-STORE-06 | **PASSED** (Checkpoint blockage reproduced: 371 frames blocked from checkpoint by open reader) |
| `probe_connection_thread_confinement.py` | G-STORE-07 | **PASSED** (Thread confinement verified: cross-thread connection calls throw `ProgrammingError`) |

---

## Recommendations & Action Items

1. **Immediate Patch (G-STORE-01)**: Incorporate database and WAL file mtime/size into `sig` in `server.py` so that any database write invalidates `self.candidates`.
2. **Immediate Patch (G-STORE-02 & G-STORE-03)**: Move range validation inside `_immediate_transaction` in `complete_prepared` and require `status='in_progress'` in the UPDATE `WHERE` clause. Require `lease` in `complete_range`.
3. **Concurrency Hardening (G-STORE-04)**: Migrate `claim_range` from `with self.db:` to `with self._immediate_transaction():` to prevent duplicate start key generation.
4. **Web UI Responsiveness (G-STORE-05)**: Decouple subprocess process waiting in `pause_sweep` and `stop_sweep` from `self.lock` to prevent UI freezing during graceful pauses.
5. **WAL Hygiene (G-STORE-06)**: Add `PRAGMA wal_checkpoint(TRUNCATE)` on `store.close()` to ensure WAL files are truncated upon scan completion.
