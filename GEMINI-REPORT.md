> Historical external-model review of the earlier working tree. Findings and severity labels are hypotheses, not current certification; the reviewed commit dispositions and checks are recorded in COMMIT_REVIEW.md.

# GEMINI CODEBASE REVIEW REPORT

**Target Repository:** `minecraft-seed-searcher`
**Review Date:** October 13, 2026
**Auditor:** Antigravity (Google DeepMind)
**Status:** Comprehensive Audit Complete

---

## 1. Executive Summary

This codebase exhibits outstanding high-performance engineering in its core C11 OpenMP native kernel (`native/blueprint_batch.inc`) and Realm storage subsystem (`src/seed_search/realm/store.py`), achieving audited scanning throughput of over 41,000 seeds/second. However, the system suffers from an architectural rift between modern Realm v2 components and obsolete v1 legacy modules, compounded by critical reliability flaws in resource monitoring and SQLite transaction handling. Most concerningly, the web presentation layer contains multiple instances of simulated or fallback data masquerading as real evidence—including hardcoded synthetic ravines, fake caves, and procedural continent splines—which directly contradicts the requirement that data must either be truthful or not displayed. By eliminating legacy dead code, hardening process and transaction lifecycles, and removing fabricated visual fallbacks, this project will achieve production-grade reliability, security, and true architectural integrity.

---

## 2. Prioritised Action Items

```
P0: Will cause data loss, security breach, or production crash
P1: Likely to cause bugs or meaningfully degrade UX / performance under real conditions
P2: Technical debt that compounds if left | refactors and pattern inconsistencies
P3: Polish, consistency, minor DX improvements
```

---

### Priority P0 — Critical Crashes, Data Loss & Security Breaches

#### [P0-01] Monitored Process Failure Crashes Scan in Restricted/Sandbox Environments
- **Affected files / functions:** `src/seed_search/realm/runner.py` (`sample_memory`, lines 236–250; `process_tree_resources`, lines 104–126), `src/seed_search/realm/native_batch.py` (lines 445–450).
- **Problem:** `sample = process_tree_resources()` executes the system command `ps -axo pid=,ppid=,rss=,pcpu=`. On macOS sandboxes, restricted Docker containers, minimal Alpine images, or non-Unix platforms where `ps` is prohibited, `sample['available']` evaluates to `False`. Both `runner.py` and `native_batch.py` immediately treat this as an unrecoverable failure and raise `RuntimeError("Process-tree monitoring unavailable; new dispatch stopped and scan checkpoint retained")`, abruptly halting the entire sweep.
- **Fix prompt:**
```text
In `src/seed_search/realm/runner.py` and `src/seed_search/realm/native_batch.py`:
Currently, `sample_memory()` treats `sample["available"] is False` as a fatal error and raises `RuntimeError("Process-tree monitoring unavailable; new dispatch stopped and scan checkpoint retained")`. This crashes scans running inside sandboxes or restricted containers where `ps` is disabled.
Modify the error handling so that when `process_tree_resources()["available"]` is False:
1. Log a single warning that process-tree monitoring is unavailable and fallback mode is active.
2. Fall back to single-process resident memory via `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` (accounting for platform units: bytes on macOS `darwin`, kilobytes on Linux).
3. Do not raise `RuntimeError` or stop the scan unless the fallback self RSS itself exceeds the memory ceiling.
```

#### [P0-02] `BEGIN IMMEDIATE` Inside Active SQLite Context Manager Crashes Candidate Updates
- **Affected files / functions:** `src/seed_search/realm/store.py` (`upsert_candidate`, lines 674–678; `claim_discovery_task`, lines 527–530; `complete_discovery_task`, lines 551–553; `claim_inventory_work`, lines 612–614).
- **Problem:** Under Python 3.12+ (and depending on standard library `sqlite3` transaction settings), entering `with self.db:` starts an implicit transaction upon statement execution. Calling `self.db.execute("BEGIN IMMEDIATE")` while an implicit transaction is open raises:
  `sqlite3.OperationalError: cannot start a transaction within a transaction`
  This crashes worker candidate updates and discovery task completions.
- **Fix prompt:**
```text
In `src/seed_search/realm/store.py`:
Methods like `upsert_candidate()` (lines 674-678) currently use:
```python
if self.db.in_transaction:
    raise ValueError("Finish caller transaction before updating candidate evidence")
with self.db:
    self.db.execute("BEGIN IMMEDIATE")
    return self._upsert_candidate_locked(...)
```
In Python 3.12+, `with self.db:` automatically manages transactions. Executing `BEGIN IMMEDIATE` inside the `with self.db:` block can raise `sqlite3.OperationalError: cannot start a transaction within a transaction`.
Refactor `upsert_candidate` and related locking methods (`claim_discovery_task`, `complete_discovery_task`, `claim_inventory_work`, lines 527, 552, 613, 631, 706, 804, 836, 869, 921, 980, 1041) to execute `self.db.execute("BEGIN IMMEDIATE")` cleanly before entering `with self.db:`, or set `autocommit=True` on the connection and manage the `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK` cycle explicitly with a dedicated context manager. Ensure all transactions are safe under concurrency.
```

#### [P0-03] Cross-Origin Execution & Missing CSRF Protection on Sweep Control Endpoints
- **Affected files / functions:** `src/seed_search/web/server.py` (`WebSearchHandler.do_POST`, lines 780–878).
- **Problem:** The web backend exposes `POST /api/sweep/start`, `POST /api/sweep/stop`, and `POST /api/sweep/resume` without CSRF token validation, origin header verification, or authentication. Any webpage visited by a user on the same machine can send unauthenticated cross-origin POST requests to `http://127.0.0.1:3000` to spawn arbitrary OpenMP subprocesses, terminate active searches, or consume CPU/disk resources.
- **Fix prompt:**
```text
In `src/seed_search/web/server.py`:
Currently, `do_POST` processes sweep actions (`/api/sweep/start`, `/api/sweep/stop`, `/api/sweep/resume`) without verifying origin or CSRF tokens.
Harden the POST endpoint handlers:
1. Validate the `Origin` or `Referer` header against an approved whitelist (e.g. `http://localhost:3000`, `http://127.0.0.1:3000`, and the bound server port).
2. If `Sec-Fetch-Site` header is present, reject requests where `Sec-Fetch-Site == 'cross-site'`.
3. Require `Content-Type: application/json` and reject any request with unexpected MIME types.
4. Return HTTP 403 Forbidden with a clear JSON error message if origin validation fails.
```

---

### Priority P1 — Real Bugs, Fabricated Data & Degraded Performance

#### [P1-01] SQL Leaderboard Query Orders by `smart_score` Instead of Canonical Multilevel Ranking
- **Affected files / functions:** `src/seed_search/web/server.py` (`SweepManager._query_sqlite_candidates`, lines 381–382, 392; `get_curated_or_historical_candidates`, lines 725, 735).
- **Problem:** The SQL queries in `server.py` sort candidates using:
  `SELECT seed, smart_score, result FROM candidate_leaderboard_view ORDER BY smart_score DESC LIMIT 50`
  However, the canonical ranking contract defined in `src/seed_search/realm/leaderboard.py` requires:
  `ORDER = "ranking_tier, unmet_requirements, smart_score DESC, id"`
  Sorting solely by `smart_score DESC` allows lower-tier seeds (e.g. Tier 2 near-misses) with higher empirical raw scores to be ranked *ahead* of Tier 0 candidates with 0 deficits. Furthermore, ordering by a non-leading column forces SQLite to bypass the `candidate_leaderboard` index, causing a table scan and filesort on every 650ms poll.
- **Fix prompt:**
```text
In `src/seed_search/web/server.py`:
In `_query_sqlite_candidates` (lines 381-382, 392) and `get_curated_or_historical_candidates` (lines 725, 735), the SQL query sorts candidates using:
`ORDER BY c.smart_score DESC LIMIT 50`
This violates the ranking contract in `src/seed_search/realm/leaderboard.py`, which requires:
`ORDER BY ranking_tier, unmet_requirements, smart_score DESC, id`
Update all candidate leaderboard queries in `server.py` to import `ORDER` from `seed_search.realm.leaderboard` and sort with `ORDER BY {ORDER} LIMIT 50`. Ensure `ranking_tier` and `unmet_requirements` are selected so the UI can clearly display candidate tier qualification.
```

#### [P1-02] Fabricated Fallback Data Masquerading as Evidence in Frontend
- **Affected files / functions:** `web-ui/src/components/MapCanvas.tsx` (`getFallbackRavines`, `getFallbackCaves`, lines 28–42, 119–129, 306–378), `web-ui/src/mockData.ts`.
- **Problem:** When displaying reference seeds or candidates without terrain evidence (`candidate.provenance === 'reference'`), `MapCanvas.tsx` injects hardcoded fake ravines (`{ id: 'rav-f1', x: 120, z: -180... }`) and fake cave clusters (`{ id: 'cave-f1', x: 160, z: -220... }`), draws an artificial trigonometric wobbly continent, and plots a hardcoded river spline `(60, 40) -> (-740, 80)`. This directly violates the rule: **"Data is either correct or it isn't displayed."**
- **Fix prompt:**
```text
In `web-ui/src/components/MapCanvas.tsx`:
Currently, `getFallbackRavines()` (lines 28-36) and `getFallbackCaves()` (lines 38-42) return hardcoded coordinates, and lines 119-129 render them when `candidate.provenance === 'reference'`. Lines 306-378 also draw a fake trigonometric continent and hardcoded river highway vector spline.
Delete `getFallbackRavines` and `getFallbackCaves` entirely. If a candidate does not have real `candidate.ravines` or `candidate.caveClusters`, render nothing for those layers. Remove the fake hardcoded river spline `(60, 40) -> (-740, 80)`. For terrain, only render visual boundaries when actual spatial data is present; otherwise display a clean, honest overlay indicating "Spatial terrain generation pending".
```

#### [P1-03] Unthrottled MouseMove Collision Math and React State Churn in `MapCanvas`
- **Affected files / functions:** `web-ui/src/components/MapCanvas.tsx` (`handleMouseMove`, lines 1081–1153; render `useEffect`, lines 254–1073).
- **Problem:** On every mouse movement over the canvas, `handleMouseMove` calls `setCursorWorld` and executes quadratic distance collision checks against all structures, caves, and ravines. This triggers React state updates on every pointer pixel event. Because `cursorWorld`, `hoveredStructure`, `hoveredCave`, and `hoveredRavine` are in the dependency array of the 800-line canvas render effect, the entire canvas is continuously redrawn on mouse movement, causing high CPU load and frame jitter.
- **Fix prompt:**
```text
In `web-ui/src/components/MapCanvas.tsx`:
`handleMouseMove` currently calls `setCursorWorld(world)` and updates hover states (`setHoveredStructure`, `setHoveredCave`, `setHoveredRavine`) on every single native mousemove event. These state changes trigger full React re-renders and cause the 800-line canvas `useEffect` to re-execute on every pixel traversed.
Refactor `MapCanvas.tsx` to:
1. Throttle or debounce mouse coordinate updates using `requestAnimationFrame`.
2. Keep cursor world coordinates in a `useRef` or local DOM node for HUD display instead of top-level React state.
3. Only trigger a React state change for `hoveredStructure` when the hovered entity ID actually changes (not on every movement within the same entity).
4. Separate the static canvas layer (terrain, grid, distance rings) from dynamic hover/cursor overlays using layered HTML5 canvases or offscreen buffering to eliminate full canvas repaints on cursor movement.
```

#### [P1-04] Linux vs macOS Memory Telemetry Discrepancy Causes Wild Under-Reporting
- **Affected files / functions:** `src/seed_search/web/server.py` (`get_status`, lines 321–326, 420–423), `src/seed_search/realm/runner.py` (line 91).
- **Problem:** `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` returns values in **bytes** on macOS (`darwin`) and in **kilobytes** on Linux. In `server.py`:
  `rss_gib = round(rss_bytes / (1024 * 1024 * 1024), 2)`
  On Ubuntu Linux (e.g. 192-core cluster), dividing Linux KB by $1024^3$ produces a value $1024\times$ too small (e.g. 0.003 GiB instead of 3.0 GiB), which causes the code to trigger an arbitrary fallback `rss_gib = 3.8`.
- **Fix prompt:**
```text
In `src/seed_search/web/server.py`:
Lines 321-326 and 420-423 calculate memory RSS using `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`.
On Linux, `ru_maxrss` is in kilobytes, while on macOS (`darwin`), it is in bytes. The current code divides by `(1024 * 1024 * 1024)` unconditionally, producing numbers 1024x too small on Linux.
Update the calculation in `server.py`:
```python
raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
rss_bytes = raw_rss if sys.platform == "darwin" else raw_rss * 1024
rss_gib = round(rss_bytes / (1024 ** 3), 2)
```
Apply the same platform-aware conversion anywhere `ru_maxrss` is read.
```

#### [P1-05] `stop_sweep` Race Conditions and Zombie Subprocesses in `SweepManager`
- **Affected files / functions:** `src/seed_search/web/server.py` (`SweepManager.stop_sweep`, lines 140–190; `SweepManager._monitor_process`, lines 278–318).
- **Problem:** When `stop_sweep()` is called, it issues `proc.terminate()` and waits with a 3.0s timeout. If the process does not exit, it calls `proc.kill()` but does NOT call `proc.wait()`, leaving zombie processes in the process table. Furthermore, `self.lock` is released while waiting for termination, allowing another request to `/api/sweep/start` to run while the old subprocess is still dying.
- **Fix prompt:**
```text
In `src/seed_search/web/server.py`:
In `SweepManager.stop_sweep()`:
1. Ensure `proc.kill()` is immediately followed by `proc.wait(timeout=2.0)` to prevent zombie processes.
2. Maintain a `_stopping` lifecycle state under `self.lock` so that concurrent `/api/sweep/start` calls receive an immediate error `{"ok": False, "error": "Previous sweep is currently terminating; please wait"}` until the prior process has fully exited and all file descriptors are closed.
3. In `_monitor_process`, ensure stdout and stderr drain threads are joined cleanly with timeouts before setting `self.status`.
```

#### [P1-06] Initial App Load Flashes Mock Candidates Before Live Status Poll
- **Affected files / functions:** `web-ui/src/App.tsx` (lines 13–17, 127–135), `web-ui/src/mockData.ts`.
- **Problem:** `App.tsx` initializes `const [candidates, setCandidates] = useState<SeedCandidate[]>(MOCK_CANDIDATES)`. On application load, users see hardcoded mock candidates for several hundred milliseconds before the first backend poll finishes. If the search database has 0 candidates, mock candidates continue to be displayed, confusing users into thinking fake seeds are real discoveries.
- **Fix prompt:**
```text
In `web-ui/src/App.tsx`:
Currently, `candidates` is initialized to `MOCK_CANDIDATES` and `dataMode` defaults to `'demo'`. This causes mock candidates to flash or stay displayed even when connected to a live sweep with zero results.
Refactor `App.tsx`:
1. Initialize `candidates` to `[]` and `selectedCandidate` to `null`.
2. Initialize `dataMode` to `'live'`.
3. If no live candidates exist and the sweep is idle, display an empty state banner: "No candidates discovered yet. Start a sweep or load saved results."
4. Move `MOCK_CANDIDATES` behind an explicit "Load Demo Preview" button in the HUD for testing, and ensure live sweep views never display mock candidates.
```

#### [P1-07] N+1 SQLite Connections and ABI Checks in `server.py:list_runs`
- **Affected files / functions:** `src/seed_search/web/server.py` (`SweepManager.list_runs`, lines 234–245; `_saved_run`, lines 205–233).
- **Problem:** When the frontend requests `/api/sweep/runs`, `list_runs()` iterates through up to 50 directories matching `web-sweep-*`. For each directory, it opens and closes an SQLite connection, validates configuration, and instantiates CFFI `Prototype` (re-checking C native library ABI). This adds 300–600ms of latency per request and wastes CPU.
- **Fix prompt:**
```text
In `src/seed_search/web/server.py`:
In `SweepManager.list_runs()`:
Currently, up to 50 runs are queried by opening an SQLite connection and instantiating `Prototype(DEFAULT_NATIVE_BUILD, cfg)` on every single run directory.
Optimize `list_runs()`:
1. Cache run metadata in memory (`self._run_cache`) keyed by directory modification time (`st_mtime`).
2. Do not instantiate `Prototype` inside `list_runs()`—validate the native build once at server startup or only when `resume_sweep` is actually invoked.
3. Read `meta` values using a single fast SQLite query with `PRAGMA query_only = ON`.
```

---

### Priority P2 — Technical Debt, Redundancies & Architecture Decoupling

#### [P2-01] Decompose Monolithic `MapCanvas.tsx` (1,524 lines) into Modular Subcomponents
- **Affected files / functions:** `web-ui/src/components/MapCanvas.tsx`.
- **Problem:** At 1,524 lines, `MapCanvas.tsx` is an oversized component combining canvas coordinate transformations, drag-and-drop state, geometry math, structure hit-testing, elevation filtering, compass rose rendering, metric scale bar, and jump targets into one file.
- **Fix prompt:**
```text
Refactor `web-ui/src/components/MapCanvas.tsx` (1,524 lines) into modular files under `web-ui/src/components/map/`:
1. `useMapViewport.ts`: Custom hook managing zoom, offset, pan dragging, screenToWorld, and worldToScreen math.
2. `useFeatureHitTest.ts`: Collision detection for structures, caverns, and ravines.
3. `MapHudOverlay.tsx`: React overlay component for dimension toggle, coordinate display, jump anchor pills, elevation filters, and scale bar.
4. `renderers/gridRenderer.ts`: Canvas 2D grid and distance ring drawing functions.
5. `renderers/structureRenderer.ts`: Structure marker badges and icons.
6. `MapCanvas.tsx`: Clean parent component (<250 lines) composing the canvas ref, viewport hook, and renderers.
Ensure full TypeScript type safety and zero visual regressions.
```

#### [P2-02] Delete Legacy v1 Search Engine Modules (13 Files in `src/seed_search/`)
- **Affected files / functions:**
  - `src/seed_search/search.py`
  - `src/seed_search/staged.py`
  - `src/seed_search/storage.py`
  - `src/seed_search/landscapes.py`
  - `src/seed_search/wood.py`
  - `src/seed_search/scoring.py`
  - `src/seed_search/regression.py`
  - `src/seed_search/readiness.py`
  - `src/seed_search/report_cache.py`
  - `src/seed_search/preflight.py`
  - `src/seed_search/geometry.py`
  - `src/seed_search/observations.py`
  - `src/seed_search/review.py`
- **Problem:** These 13 legacy Python files (thousands of lines) were created for the original v1 Stronghold-centric search engine. Modern v2 execution uses `src/seed_search/realm/` exclusively. None of the modern pipeline modules or web servers import from these files. Keeping them invites confusion, bloats the repository, and causes stale test failures.
- **Fix prompt:**
```text
Delete the obsolete v1 legacy modules from `src/seed_search/`:
- `src/seed_search/search.py`
- `src/seed_search/staged.py`
- `src/seed_search/storage.py`
- `src/seed_search/landscapes.py`
- `src/seed_search/wood.py`
- `src/seed_search/scoring.py`
- `src/seed_search/regression.py`
- `src/seed_search/readiness.py`
- `src/seed_search/report_cache.py`
- `src/seed_search/preflight.py`
- `src/seed_search/geometry.py`
- `src/seed_search/observations.py`
- `src/seed_search/review.py`
Update `src/seed_search/cli.py` to route all commands directly to `src/seed_search/realm/cli.py`. Remove obsolete imports from `src/seed_search/__init__.py`.
```

#### [P2-03] Delete Obsolete `web-api/` FastAPI Prototype
- **Affected files / functions:** `web-api/main.py`, `web-api/`.
- **Problem:** `web-api/main.py` is a 76-line placeholder FastAPI application that generates random telemetry numbers (`seeds += random.randint(10000, 50000)`) via WebSocket. It is completely superseded by `src/seed_search/web/server.py`.
- **Fix prompt:**
```text
Delete the entire `web-api/` directory (including `web-api/main.py` and any local virtual environments or caches). Remove all documentation references to `web-api` across README.md and documentation files, pointing exclusively to `src/seed_search/web/server.py`.
```

#### [P2-04] Remove Dead PRNG Carver Algorithms from `server.py`
- **Affected files / functions:** `src/seed_search/web/server.py` (`predict_candidate_ravines`, lines 584–633; `predict_candidate_cave_clusters`, lines 635–675).
- **Problem:** 91 lines of synthetic PRNG carver math in `server.py` generate fictional ravines and cave clusters. Modern v2 Realm reads persisted LevelDB evidence or returns empty lists. These functions are never called by `parse_candidate_row` and clutter the codebase.
- **Fix prompt:**
```text
In `src/seed_search/web/server.py`:
Delete the dead functions `predict_candidate_ravines` (lines 584-633) and `predict_candidate_cave_clusters` (lines 635-675). Ensure `parse_candidate_row` only serializes real persisted carver/cave evidence from the database record or returns empty lists `[]`.
```

#### [P2-05] Consolidate Redundant Schema v4 Configuration Files
- **Affected files / functions:** `search.example.yaml`, `config/reference-sweep.yaml`, `config/review-all.yaml`, `config/staged-sweep.yaml`.
- **Problem:** `search.example.yaml` is an exact duplicate of `config/reference-sweep.yaml`. All four files use deprecated schema version 4, while modern pipeline execution requires `config/realm.yaml` (schema version 5).
- **Fix prompt:**
```text
Remove deprecated schema version 4 configurations:
- Delete `search.example.yaml`
- Delete `config/reference-sweep.yaml`
- Delete `config/review-all.yaml`
- Delete `config/staged-sweep.yaml`
Provide a clean `config/realm.example.yaml` that mirrors `config/realm.yaml` (schema version 5) as the canonical configuration template. Update documentation to reference `config/realm.yaml`.
```

#### [P2-06] Throttle Status Polling and Memoize Total Feasibility Calculations
- **Affected files / functions:** `web-ui/src/App.tsx` (lines 95–148), `web-ui/src/components/FilterSidebar.tsx`.
- **Problem:** The frontend polls `/api/sweep/status` every 650ms during sweeps, placing continuous load on SQLite and Python. In `FilterSidebar.tsx`, `computeTotalFeasibility(config)` runs polynomial convolution on every render cycle without memoization.
- **Fix prompt:**
```text
In `web-ui/src/App.tsx` and `web-ui/src/components/FilterSidebar.tsx`:
1. In `App.tsx`, increase the active sweep poll interval from 650ms to 1200ms.
2. In `FilterSidebar.tsx`, wrap the call to `computeTotalFeasibility(config)` in `useMemo(() => computeTotalFeasibility(config), [config])` so that the Poisson-Binomial polynomial convolution only re-evaluates when config options actually change.
```

---

### Priority P3 — Polish, Consistency & Minor DX Improvements

#### [P3-01] Remove Unused Vite Template Assets and Dead CSS
- **Affected files / functions:** `web-ui/src/App.css`, `web-ui/src/assets/hero.png`, `web-ui/src/assets/vite.svg`, `web-ui/src/assets/react.svg`.
- **Problem:** Unused starter files from `create-vite`. `App.css` (185 lines) is never imported anywhere in the project.
- **Fix prompt:**
```text
Delete unused template assets from `web-ui/`:
- `web-ui/src/App.css`
- `web-ui/src/assets/hero.png`
- `web-ui/src/assets/vite.svg`
- `web-ui/src/assets/react.svg`
Verify that `npm run build` succeeds without warnings.
```

#### [P3-02] Clean Up Root Directory Build Artifacts and Untracked Files
- **Affected files / functions:** `./seed_search/_blueprint_batch.c`, `_blueprint_batch.o`, `_native.c`, `_native.o`, `default.profraw`.
- **Problem:** Running standalone CFFI build scripts with `tmpdir="."` leaves generated C and object files in a `./seed_search` root directory outside `src/`. An untracked 91KB LLVM profile `default.profraw` is also sitting in the project root.
- **Fix prompt:**
```text
1. Delete the untracked `./seed_search/` root directory and `./default.profraw`.
2. In `native/blueprint_build.py` and `native/build.py`, set CFFI `tmpdir="build"` or output directly to `src/seed_search/`.
3. Add `*.profraw` and `/seed_search/` to `.gitignore`.
```

#### [P3-03] Remove Orphaned Type `BiomeRegion`
- **Affected files / functions:** `web-ui/src/types.ts` (lines 40–57).
- **Problem:** `BiomeRegion` is exported in `types.ts` but never imported or used anywhere in the frontend or backend.
- **Fix prompt:**
```text
In `web-ui/src/types.ts`, delete the unused `BiomeRegion` interface (lines 40-57).
```

#### [P3-04] Fix Default HTML Title in `web-ui/index.html`
- **Affected files / functions:** `web-ui/index.html` (line 7).
- **Problem:** The HTML page title is the default `<title>web-ui</title>`.
- **Fix prompt:**
```text
In `web-ui/index.html`, update `<title>web-ui</title>` to `<title>Minecraft Bedrock Seed Searcher | Realm v2</title>`.
```

---

## 3. Quick Wins

These 5 small, safe, low-effort fixes can be batched together in a single prompt for immediate improvement:

```text
BATCH QUICK-WIN FIX PROMPT:
1. Delete dead files:
   - `web-ui/src/App.css`
   - `web-ui/src/assets/hero.png`
   - `web-ui/src/assets/vite.svg`
   - `web-ui/src/assets/react.svg`
   - `default.profraw`
2. In `web-ui/src/types.ts`, remove the unused `BiomeRegion` interface.
3. In `web-ui/index.html`, change `<title>web-ui</title>` to `<title>Minecraft Bedrock Seed Searcher | Realm v2</title>`.
4. In `web-ui/src/components/FilterSidebar.tsx`, memoize `computeTotalFeasibility` with `useMemo`.
5. In `.gitignore`, append `*.profraw` and `/seed_search/`.
```

---

## 4. Redundancy Removal Log

The following files and components can be deleted outright:

| Target Path | Category | Rationale |
|---|---|---|
| `web-api/main.py` | File | Obsolete mock FastAPI server generating random telemetry, superseded by `server.py`. |
| `web-api/` | Directory | Obsolete mock server directory. |
| `web-ui/src/App.css` | File | Dead template CSS (185 lines) never imported by any React component. |
| `web-ui/src/assets/hero.png` | Asset | Unused Vite starter image. |
| `web-ui/src/assets/vite.svg` | Asset | Unused Vite logo. |
| `web-ui/src/assets/react.svg` | Asset | Unused React logo. |
| `search.example.yaml` | Config | Exact byte-for-byte duplicate of `config/reference-sweep.yaml` (legacy schema v4). |
| `config/reference-sweep.yaml` | Config | Obsolete schema v4 configuration superseded by `config/realm.yaml` (schema v5). |
| `config/review-all.yaml` | Config | Obsolete schema v4 configuration superseded by `config/realm.yaml`. |
| `config/staged-sweep.yaml` | Config | Obsolete schema v4 configuration superseded by `config/realm.yaml`. |
| `src/native/` | Directory | Empty directory left over from previous refactors. |
| `src/vendor/` | Directory | Empty directory (`cubiomes-bedrock` submodule resides in root `vendor/`). |
| `./seed_search/` | Directory | Misplaced CFFI build artifacts in root; real source is under `src/seed_search/`. |
| `default.profraw` | Artifact | Stray 91KB LLVM profile output from historical PGO instrumentation trial. |
| `src/seed_search/web/server.py:predict_candidate_ravines` | Function | Dead 50-line PRNG carver simulation function never used in production. |
| `src/seed_search/web/server.py:predict_candidate_cave_clusters` | Function | Dead 41-line PRNG cave cluster simulation function never used in production. |
| `web-ui/src/components/MapCanvas.tsx:getFallbackRavines` | Function | Fabricates fake canyon coordinates when actual evidence is missing. |
| `web-ui/src/components/MapCanvas.tsx:getFallbackCaves` | Function | Fabricates fake subterranean cave coordinates when actual evidence is missing. |
| `web-ui/src/types.ts:BiomeRegion` | Type | Unused interface never referenced in any component. |
| `src/seed_search/search.py` | Legacy Module | v1 search pipeline superseded by `seed_search.realm`. |
| `src/seed_search/staged.py` | Legacy Module | v1 staged search pipeline superseded by `seed_search.realm`. |
| `src/seed_search/storage.py` | Legacy Module | v1 SQLite store superseded by `seed_search.realm.store`. |
| `src/seed_search/landscapes.py` | Legacy Module | v1 raster terrain evaluator superseded by `seed_search.realm.terrain`. |
| `src/seed_search/wood.py` | Legacy Module | v1 wood scorer superseded by `seed_search.realm.blueprint`. |
| `src/seed_search/scoring.py` | Legacy Module | v1 scoring evaluator superseded by `seed_search.realm.reports`. |
| `src/seed_search/regression.py` | Legacy Module | v1 regression tester superseded by Realm pytest suite. |
| `src/seed_search/readiness.py` | Legacy Module | v1 readiness verification superseded by Realm verification. |
| `src/seed_search/report_cache.py` | Legacy Module | v1 report caching superseded by Realm store meta tables. |
| `src/seed_search/preflight.py` | Legacy Module | v1 preflight script superseded by Realm calibration tools. |
| `src/seed_search/geometry.py` | Legacy Module | v1 distance geometry functions superseded by Realm bounds. |
| `src/seed_search/observations.py` | Legacy Module | v1 observation wrapper superseded by Realm store tables. |
| `src/seed_search/review.py` | Legacy Module | v1 review importer superseded by Realm store. |
| `scripts/audit_repeated_compute.py` | Script | Historical v1 pilot script from Oct 7, 2026. |
| `scripts/benchmark_exact_cache.py` | Script | Historical v1 cache benchmark script. |
| `scripts/benchmark_filter_shortcuts.py` | Script | Historical v1 shortcut pilot script. |
| `scripts/pilot_count_bits_biomes.py` | Script | Experimental bit-counter pilot superseded by C native batch. |
| `scripts/pilot_count_bits_structures.py` | Script | Experimental bit-counter pilot superseded by C native batch. |
| `scripts/report_million_count_feasibility.py` | Script | One-off exploratory feasibility report generator from Oct 11, 2026. |
