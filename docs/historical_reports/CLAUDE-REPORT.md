> Historical external-model review of the earlier working tree. Findings and severity labels are hypotheses, not current certification; the reviewed commit dispositions and checks are recorded in COMMIT_REVIEW.md.

# Comprehensive Codebase Review — Minecraft Seed Searcher

**Date:** 2026-10-13
**Codebase:** `minecraft-seed-searcher` (~40K lines of project code)
**Stack:** Python 3.13 · CFFI/C11+OpenMP native extensions · cubiomes-bedrock vendor · SQLite · React 19 / TypeScript / Vite / Tailwind · FastAPI (abandoned)

---

## 1. Executive Summary

The codebase is an impressive, ambitious Minecraft Bedrock seed search engine with a native C11 pipeline capable of ~20K seeds/sec, a comprehensive React HUD, and deep domain modelling. However, it has evolved through rapid prototyping phases that left behind **critical structural fault lines**:

1. **Two forked search engines** (Legacy Schema 3/4 "island" pipeline + Realm Schema 5 "coastal continent" pipeline) coexist via runtime argument-sniffing dispatchers, with neither cleanly deprecated. The root `search.example.yaml` still targets the legacy engine.
2. **A phantom `./seed_search/` directory at the repo root** (created by CFFI builds) shadows the real `src/seed_search/` package as a PEP 420 namespace package, causing `ModuleNotFoundError` on clean checkouts. Generated `.c` files and a 2 MB `.dylib` binary are committed to Git.
3. **The web layer fabricates geographic coordinates** — ravines and cave clusters are generated using arbitrary arithmetic formulas (`(seed ^ 0xA5A5) % 800 - 400`) rather than cubiomes, displaying fake map features to users. An abandoned FastAPI mock server sits alongside the real `server.py` monolith.
4. **Storage is a scalability bottleneck** — full JSON serialization per seed into SQLite reduces native throughput from 20K to ~1K seeds/sec, and `runs/` has grown to 103 GB with 698 files tracked in Git.
5. **Dominant good patterns:** Disciplined lattice/boundary modelling, transactional SQLite state persistence, comprehensive test coverage (940 tests), and well-structured native CFFI bridge. The Realm subsystem's domain decomposition (biomes, terrain, coastal, marine, verification) is clean when viewed in isolation.

---

## 2. Prioritised Action Items

### P0 — Will cause data loss, security breach, or production crash

---

#### P0-1: Phantom Root `seed_search/` Directory Causes Namespace Shadowing

**Affected files:** `./seed_search/_native.c` (tracked), `./seed_search/_blueprint_batch.c`, `native/build.py:49`, `native/blueprint_build.py:22`, `src/seed_search/_native.c` (tracked), `src/seed_search/_native.dylib` (tracked, 2.1 MB)

**Problem:** `native/build.py` compiles with `ffibuilder.compile(tmpdir=".")`, causing CFFI to output `./seed_search/_native.c` and `.o` at the repo root. Python discovers this as an empty PEP 420 namespace package, shadowing `src/seed_search/`. Running `python -c "import seed_search.cli"` from the project root immediately fails with `ModuleNotFoundError`. Additionally, generated C sources and a compiled `.dylib` binary are committed to Git, bloating the repository and causing dirty working trees on every build.

**Fix prompt:**
> In the `minecraft-seed-searcher` repository:
> 1. Run `git rm -f seed_search/_native.c src/seed_search/_native.c src/seed_search/_native.dylib` and `rm -rf seed_search/`.
> 2. In `native/build.py:49`, change `ffibuilder.compile(tmpdir=".", ...)` to `ffibuilder.compile(tmpdir="build", ...)`.
> 3. In `native/blueprint_build.py:22`, make the same `tmpdir` change.
> 4. Add to `.gitignore`: `seed_search/`, `build/`, `*.dylib`, `*.so`, `*.o`, `*.profraw`.
> 5. Verify that `python -c "from seed_search.cli import main; print('OK')"` works from the project root.

---

#### P0-2: Native C Functions Lack NULL Pointer Checks — Immediate Segfault

**Affected files:** `native/bridge.c` — functions `ss_land` (L421–423), `ss_heights` (L182–185), `ss_grid` (L163–165), `ss_density_points` (L458–460)

**Problem:** All four public bridge functions validate `n` bounds but do NOT check if `ctx`, `xz`, `land`, `heights`, `surface_biomes`, `biomes`, `climate`, `approx_height`, `xyz`, or `out` pointers are NULL. A NULL pointer from a failed allocation or CFFI marshalling error causes an immediate, unrecoverable segfault that crashes the entire Python process.

**Fix prompt:**
> In `native/bridge.c`, add NULL guards at the top of each function:
> - `ss_land()` (L422): `if (!ctx || (n > 0 && (!xz || !land))) return -1;`
> - `ss_heights()` (L184): `if (!ctx || (n > 0 && (!xz || !heights || !surface_biomes))) return -1;`
> - `ss_grid()` (L165): `if (!ctx || !biomes || !climate || !approx_height) return -1;`
> - `ss_density_points()` (L459): `if (!ctx || (n > 0 && (!xyz || !out))) return -1;`

---

#### P0-3: Unhandled Exception in `SweepManager.start_sweep` Permanently Bricks Server State

**Affected file:** `src/seed_search/web/server.py` — `SweepManager.start_sweep` (L114–192)

**Problem:** `self.status = "running"` is set at L129 inside `with self.lock:`. If policy writing (`yaml.safe_dump`) or `subprocess.Popen` raises an exception, the exception escapes unhandled. `self.status` remains `"running"` and `self.process` remains `None`, causing all subsequent `start_sweep` or `resume_sweep` calls to permanently fail with "A sweep is already actively running". The server is deadlocked until process restart.

**Fix prompt:**
> In `src/seed_search/web/server.py`, `SweepManager.start_sweep`: wrap the entire run setup (directory creation, YAML dumping, `subprocess.Popen`) inside `with self.lock:` in a `try...except` block. In the `except` handler, reset `self.status = "error"`, set `self.error_message = str(exc)`, append the error to `self.logs`, clean up any incomplete run directory, and return `{"ok": False, "error": str(exc)}`.

---

#### P0-4: Forked Legacy vs Realm Architecture with CLI/Config Dispatch Sniffing

**Affected files:** `src/seed_search/cli.py`, `src/seed_search/realm/cli.py`, `src/seed_search/config.py`, `src/seed_search/realm/config.py`, `src/seed_search/search.py`, `src/seed_search/realm/runner.py`, `search.example.yaml`

**Problem:** Two complete, incompatible search engines coexist: Legacy (Schema 3/4, island, 2304×928, `search.py`/`storage.py`/`scoring.py`) and Realm (Schema 5, coastal continent, 2048×2048, `realm/runner.py`/`realm/store.py`/`realm/leaderboard.py`). They are coupled via runtime argument-sniffing dispatchers: `cli.py` invokes `realm.cli:handles(argv)` to conditionally hijack execution; `config.py` delegates to `realm/config.py` when `schema_version == 5`. The root `search.example.yaml` is Schema 4 (deprecated), misleading users who intend to run the active Master Seed Blueprint.

**Fix prompt:**
> 1. Establish Realm (Schema 5) as the canonical engine. Move legacy Schema 3/4 files (`search.py`, `landscapes.py`, `storage.py`, `scoring.py`, `staged.py`, `regression.py`) into `src/seed_search/legacy/`.
> 2. Replace the argument-sniffing `handles()` dispatch in `cli.py` with standard `argparse` subparsers or separate entry points.
> 3. Rename `search.example.yaml` to `search.legacy.yaml` and create `realm.example.yaml` based on `config/realm.yaml` as the primary example config.
> 4. Add a `seed-realm` entry point to `pyproject.toml` `[project.scripts]`.

---

### P1 — Likely to cause bugs or meaningfully degrade UX / performance

---

#### P1-1: Fatal Process-Tree Monitoring Crash in Sandboxed / Non-Root Environments

**Affected files:** `src/seed_search/realm/resources.py:108–126` (`process_tree_resources`), `src/seed_search/realm/runner.py:247–252, 332`, `src/seed_search/realm/native_batch.py:446–450`

**Problem:** `resources.py` invokes `ps -axo pid=,ppid=,rss=,pcpu=`. In macOS sandboxes, CI runners, or unprivileged containers, `ps` fails with `Operation not permitted`. `runner.py` and `native_batch.py` treat `available == False` as a hard fatal error, raising `RuntimeError` and aborting scans. This causes 19 of 20 test failures and blocks all production scans in restricted environments.

**Fix prompt:**
> 1. In `src/seed_search/realm/resources.py:process_tree_resources`, when `ps -axo` returns non-zero or raises `PermissionError`/`OSError`, implement a graceful fallback using `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` and `resource.RUSAGE_CHILDREN`. Return `{'available': True, 'rss_bytes': total_rss, 'process_count': 1, 'fallback': True}`.
> 2. In `runner.py:336` and `native_batch.py:447`, only raise `RuntimeError` if strict monitoring is explicitly enabled in config; otherwise log a warning and proceed.
> 3. Create `tests/conftest.py` with a session-scoped mock for `process_tree_resources` returning valid dummy metrics.

---

#### P1-2: Cave Cluster Stepper Buttons Completely Non-Functional in FilterSidebar

**Affected file:** `web-ui/src/components/FilterSidebar.tsx` — `handleCountChange` (L98–116), `CAVE_CLUSTERS.map` (L528–557)

**Problem:** `handleCountChange` guards on L100 with `const minVal = V2_FLEXIBLE_FLOORS[id]; if (minVal === undefined) return;`. `V2_FLEXIBLE_FLOORS` only defines 8 structure types. Cave clusters (`lush_caves`, `deep_dark`, `dripstone_caves`) are NOT in `V2_FLEXIBLE_FLOORS`. When the user clicks `+` or `-` on any cave cluster, `minVal === undefined` causes the function to immediately return. The steppers do nothing at all.

**Fix prompt:**
> In `web-ui/src/components/FilterSidebar.tsx`, add cave cluster entries to `V2_FLEXIBLE_FLOORS`:
> ```typescript
> lush_caves: 0, deep_dark: 0, dripstone_caves: 0,
> ```
> Or update `handleCountChange` to fall back: `const minVal = V2_FLEXIBLE_FLOORS[id] ?? (CAVE_CLUSTERS.some(c => c.id === id) ? 0 : undefined);`

---

#### P1-3: "Sync Sweep Volume" Sets Astronomical Seed Counts Exceeding Server Disk Limits

**Affected files:** `web-ui/src/components/FilterSidebar.tsx:286–295`, `src/seed_search/web/server.py:98–102`

**Problem:** `server.py` enforces a disk budget of 128 GiB at 64 KB/seed, capping safe sweeps at ~2M seeds. The "Sync Sweep Volume" button sets `sweepSeedCount: Math.min(Number.MAX_SAFE_INTEGER, ...)` with no real cap. For Rare/Extreme/Astronomical feasibility levels, `expectedSeedsNeeded` reaches 10M–100M+. Clicking this button and launching a sweep immediately crashes with a `ValueError` from the disk budget check. The tooltip claims a 100K cap but the code has none.

**Fix prompt:**
> In `web-ui/src/components/FilterSidebar.tsx` (L286–295), cap the synced sweep volume:
> ```typescript
> const SAFE_MAX_SWEEP_SEEDS = 2_000_000;
> const targetVol = Math.min(SAFE_MAX_SWEEP_SEEDS, Math.max(1, feasibility.expectedSeedsNeeded));
> onChangeConfig({ ...config, sweepSeedCount: targetVol });
> ```
> Display a notice when `expectedSeedsNeeded` exceeds the cap so the user knows multiple sweeps are required.

---

#### P1-4: Status Flattening Collapses `completed` and `error` States to `idle`

**Affected file:** `web-ui/src/App.tsx` — polling `useEffect` (L95–148)

**Problem:** `TelemetryState.status` supports `'idle' | 'running' | 'paused' | 'completed' | 'bds_verifying' | 'error'`. But at L114, polling maps with `status: data.status === 'running' ? 'running' : 'idle'`. This collapses `completed`, `error`, and `bds_verifying` to `idle`. If a sweep crashes, the error state is silently swallowed — no error banner, no indication of failure.

**Fix prompt:**
> In `web-ui/src/App.tsx`, preserve the full status from `/api/sweep/status`:
> 1. Set `status: data.status` (or fallback to `'idle'`).
> 2. Detect transitions from `running` to `error` and show a toast: `Sweep Failed: ${data.error}`.
> 3. In `TelemetryBar.tsx`, display an error pill when `telemetry.status === 'error'`.

---

#### P1-5: `POST /api/sweep/stop` Fails with 400 on Bodyless Requests

**Affected file:** `src/seed_search/web/server.py` — `WebSearchHandler.do_POST` (L831–841)

**Problem:** L832 parses `content_length = int(self.headers.get('Content-Length', ''))`. When a client issues `POST /api/sweep/stop` without a body (no `Content-Length`), `int('')` raises `ValueError`, which is caught and returns 400 Bad Request. Stopping a sweep should not require a request body.

**Fix prompt:**
> In `src/seed_search/web/server.py` `do_POST`, handle bodyless requests before parsing content length:
> ```python
> content_length_header = self.headers.get('Content-Length')
> if path == '/api/sweep/stop' and not content_length_header:
>     req_data = {}
> else:
>     content_length = int(content_length_header or 0)
>     req_data = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
> ```

---

#### P1-6: Store Overwrites & Corrupts Scores for Blueprint Candidates

**Affected file:** `src/seed_search/realm/store.py:647–654` (`complete_inventory_work`)

**Problem:** `complete_inventory_work` unconditionally recalculates candidate score using legacy baseline formulas (`biomes.get('score', 0) + bonuses`). For blueprint candidates (`revision.startswith('blueprint-')`), candidate score is an integer count of matched requirements, not a floating-point baseline percentage. This overwrites the valid blueprint score with a meaningless number, corrupting the leaderboard ranking.

**Fix prompt:**
> In `src/seed_search/realm/store.py` `complete_inventory_work` (around L645–655):
> ```python
> is_blueprint = str(candidate.get('revision', '')).startswith('blueprint')
> if not is_blueprint:
>     score = biomes.get('score', 0) + bonuses
>     candidate['score'] = score
>     candidate['score_uncertainty'] = baseline_score_uncertainty(score, cfg)
> # else: retain blueprint score as-is
> ```

---

#### P1-7: Unhandled `NoneType` Dereference on Missing Candidates

**Affected files:** `src/seed_search/realm/calibration.py:93,101`, `src/seed_search/realm/cli.py:426`, `src/seed_search/realm/reports.py:68,451–452`

**Problem:** `store.get_candidate(id)` can return `None` if a candidate was pruned. Multiple call sites access `candidate['seed']`, `candidate.get('biomes')`, or `row[0]` without null checks, crashing with `TypeError: 'NoneType' object is not subscriptable` or `AttributeError`.

**Fix prompt:**
> 1. In `calibration.py:93`: `if candidate is None: return {'status': 'FAILED', 'reason': f"Candidate {wrapper['candidate_id']} not found"}`
> 2. In `cli.py:426`: `row = ...; if not row: raise ValueError(f"Candidate not found"); candidate = json.loads(row[0])`
> 3. In `reports.py:68,451`: Guard both lookups with `if not row: continue` and `if candidate is None: continue`.

---

#### P1-8: Chained `NoneType` AttributeError on Nested Optional Dicts

**Affected files:** `src/seed_search/realm/marine.py:80`, `src/seed_search/realm/reports.py:321`, `src/seed_search/realm/coastal.py:249`, `src/seed_search/realm/verification.py:668,677,690,745`

**Problem:** Patterns like `(candidate.get('biomes') or {}).get('sampling', {}).get('samples', ())` crash when `sampling` is explicitly `None` (serialized when sampling is skipped), because `.get('sampling', {})` returns `None`, and `None.get(...)` raises `AttributeError`. Similarly, `row.get('ground', {}).get('y')` crashes when `ground` is `None`.

**Fix prompt:**
> Replace all `x.get(key, {}).get(...)` chains with `(x.get(key) or {}).get(...)` in:
> - `marine.py:80`, `reports.py:321`, `coastal.py:249`
> - `verification.py:668,677,690,745` — also fix `(evidence.get('structures') or {}).get(kind, [])`

---

#### P1-9: Vacuous Truth and TypeError in `geometry.largest_gap` and `angular_metrics`

**Affected file:** `src/seed_search/geometry.py:60–67` (`largest_gap`), L101–102 (`angular_metrics`)

**Problem:** For an empty array, `np.array([]).all()` evaluates as `True` (vacuous truth), making `largest_gap([])` return `360.0` instead of `0.0`. If `a.all()` were `False`, L67 divides by zero. In `angular_metrics`, `~np.array([])` on a `float64` array raises `TypeError: ufunc 'invert' not supported`.

**Fix prompt:**
> In `src/seed_search/geometry.py`:
> 1. At the top of `largest_gap()`: `if not len(a): return 0.0`
> 2. In `angular_metrics()`, add explicit dtype: `~np.array(enclosed, dtype=bool) & ~np.array(unresolved, dtype=bool)`

---

#### P1-10: Stronghold Cross-Product Creates Phantom Center Coordinates

**Affected file:** `src/seed_search/structures.py:77–85` (`structure_centers`)

**Problem:** Stronghold X and Z coordinates are accumulated in separate sets `xs` and `zs`, then combined with `centers.update((x,z) for x in xs for z in zs)`. For two strongholds at (100, 200) and (300, 400), this creates phantom centers (100, 400) and (300, 200) that don't correspond to any actual stronghold, inflating the search space with invalid candidates.

**Fix prompt:**
> In `src/seed_search/structures.py:structure_centers`, add grid centres first via cross-product of boundary coordinates, then add clamped stronghold coordinates as paired tuples:
> ```python
> centers = {(x,z) for x in {x0,x1,((x0+x1)//16)*8} for z in {z0,z1,((z0+z1)//16)*8}}
> for p in scans['stronghold']['viable']:
>     centers.add((min(x1,max(x0,round(p[0]/8)*8)), min(z1,max(z0,round(p[1]/8)*8))))
> ```

---

#### P1-11: SQLite Store Resume Fails if `state` Table Wasn't Initialized

**Affected file:** `src/seed_search/storage.py:40` (`Store.__init__`)

**Problem:** `CREATE TABLE IF NOT EXISTS state` is guarded by `if not resume:`. When resuming a run where `state` was never created (interrupted early or legacy run), `get_state()`/`set_state()` crash with `sqlite3.OperationalError: no such table: state`.

**Fix prompt:**
> In `src/seed_search/storage.py:40`, remove `if not resume:` so the `CREATE TABLE IF NOT EXISTS state` executes unconditionally.

---

#### P1-12: In-Tree Path Assumption Breaks Package Installation

**Affected files:** `src/seed_search/storage.py:9,16` (`backend_identity`), `src/seed_search/report_cache.py:64–65` (`map_identity`)

**Problem:** `ROOT = Path(__file__).resolve().parents[2]` followed by hashing files at `ROOT/'native/bridge.c'`, `ROOT/'vendor/backend.json'`, etc. If the package is installed via pip into site-packages, `src/` and `native/` don't exist at `ROOT`, causing `FileNotFoundError`.

**Fix prompt:**
> In `report_cache.py:65`, replace `ROOT / 'src/seed_search/reports.py'` with `Path(__file__).with_name('reports.py')`. In `storage.py`, reference Python modules via `Path(__file__).parent / f'{name}.py'` and guard repo-root files with `.is_file()` checks.

---

#### P1-13: Missing React Error Boundary & Silently Swallowed Fetch Failures

**Affected files:** `web-ui/src/main.tsx:1–11`, `web-ui/src/App.tsx:58–90`

**Problem:** No `ErrorBoundary` wraps `<App />`. If a candidate payload contains unexpected data, rendering throws an unhandled exception, unmounting the entire React root (blank white page). Initial fetches to `/api/candidates` and `/api/sweep/status` catch errors with `.catch(() => {})`, silently failing with no user notification when the backend is offline.

**Fix prompt:**
> 1. Create `web-ui/src/components/ErrorBoundary.tsx` with a fallback UI (error message + "Reload UI" button). Wrap `<App />` in `main.tsx`.
> 2. In `App.tsx`, track `apiConnected: boolean` state. When backend requests fail, display a banner: "Backend server offline — running in offline demo mode".

---

#### P1-14: Temp Directory Leak in BDS Snapshot Decoders on Parsing Failure

**Affected files:** `src/seed_search/realm/bds_tools/snapshot_reader.py:7,24`, `compare_saved_blocks.py:68,97`

**Problem:** Both scripts copy BDS snapshots into `tempfile.mkdtemp()` then process with LevelDB. Neither wraps the logic in `try...finally`. If parsing raises, `shutil.rmtree(tmp)` is never reached, leaking multi-hundred-MB world copies in `/tmp` on every failure.

**Fix prompt:**
> Replace `tmp = Path(tempfile.mkdtemp())` with `with tempfile.TemporaryDirectory() as tmp_str: tmp = Path(tmp_str)` to guarantee cleanup on exception.

---

#### P1-15: Test Suite Broken Out-of-Box — Missing `pythonpath` in pyproject.toml

**Affected files:** `pyproject.toml:29–31`, 15+ test files importing from `scripts/`

**Problem:** Running vanilla `pytest` fails during test collection with 15+ `ModuleNotFoundError`s because: (a) `pythonpath` is not configured in `[tool.pytest.ini_options]`, (b) 15 test files import directly from `scripts/` which is not a package.

**Fix prompt:**
> 1. Add `pythonpath = [".", "src"]` to `[tool.pytest.ini_options]` in `pyproject.toml`.
> 2. Move `scripts/build_blueprint_batch.py` to `native/build_blueprint_batch.py` and update test imports.

---

### P2 — Technical debt that compounds; refactors and pattern inconsistencies

---

#### P2-1: Web Server Fabricates Geographic Coordinates Using Arbitrary Arithmetic

**Affected file:** `src/seed_search/web/server.py:584–746` — `predict_candidate_ravines`, `predict_candidate_cave_clusters`, `get_curated_or_historical_candidates`

**Problem:** 162 lines of dead functions generate ravine and cave cluster coordinates using formulas like `(s_int ^ 0xA5A5) % 800 - 400` instead of cubiomes. If ever invoked, they'd display fake map features to users. Additionally, `predict_candidate_ravines` calls `hashlib.sha256(...)` but `hashlib` is never imported — this would crash with `NameError` if called. These functions are never invoked; `parse_candidate_row` handles actual data.

**Fix prompt:**
> Delete `predict_candidate_ravines`, `predict_candidate_cave_clusters`, and `get_curated_or_historical_candidates` from `src/seed_search/web/server.py` (L584–746).

---

#### P2-2: Orphaned and Divergent Mock Server in `web-api/main.py`

**Affected file:** `web-api/main.py` (L1–76)

**Problem:** `web-api/` is a completely detached FastAPI prototype with wrong endpoints (`/api/start-sweep` vs `/api/sweep/start`), deprecated Pydantic v1 `req.dict()`, a fake WebSocket endpoint the frontend never connects to, and insecure CORS (`allow_origins=["*"]` + `allow_credentials=True`, invalid per CORS spec). The real server is `src/seed_search/web/server.py`.

**Fix prompt:**
> Delete `web-api/` entirely. Update any documentation to reference `src/seed_search/web/server.py` as the sole backend.

---

#### P2-3: 13 Circular Dependencies Suppressed via Deferred In-Function Imports

**Affected files:** `config.py ↔ landscapes.py`, `runner.py ↔ native_batch.py`, `preflight.py → reports.py → scoring.py → review.py → preflight.py`, `realm/cli.py ↔ realm/raw.py`, `realm/config.py → terrain.py → marine.py → blueprint.py → spawn.py → config.py`, `realm/terrain.py → marine.py → coastal.py → terrain.py`, and 7 more

**Problem:** 13 circular dependency loops are suppressed by deferring `import` statements inside function bodies. `realm/cli.py` alone has 25+ deferred imports. This obscures domain boundaries, hinders static analysis and IDE tooling, and risks runtime errors if call orders change.

**Fix prompt:**
> 1. Extract shared schemas, data types, and constants into leaf modules (`seed_search.types`, `seed_search.realm.types`).
> 2. Separate validation logic from execution logic.
> 3. Refactor CLI handlers to import at module top-level.

---

#### P2-4: Synchronous SQLite on Every 650ms Poll Under Global Lock

**Affected file:** `src/seed_search/web/server.py` — `SweepManager.get_status` (L406–420), `_query_sqlite_candidates` (L357–404)

**Problem:** Every 650ms frontend poll of `GET /api/sweep/status` acquires `self.lock`, opens SQLite, queries the `candidate_leaderboard_view`, parses 50 candidate JSON rows, and returns. Holding the lock during synchronous I/O blocks concurrent `start`/`stop`/`resume` requests.

**Fix prompt:**
> Decouple SQLite polling: in `_monitor_process`, update `self.scanned_count` and `self.candidates` on a background timer every 1.5–2s. In `get_status()`, return cached values under the lock without touching SQLite.

---

#### P2-5: Structure Hard Floor Constants Duplicated Across 4 Frontend Files

**Affected files:** `FilterSidebar.tsx:6–15` (`V2_FLEXIBLE_FLOORS`), `App.tsx:212–221` (`floors`), `probability.ts:261–294` (`HARD_FLOORS`, `IDEAL_TARGETS`), `mockData.ts:3–21` (`DEFAULT_STRUCTURE_FLOORS`)

**Problem:** Floor minimums (e.g., `trial_chamber: 8`, `village: 5`, `mineshaft: 17`) are defined in 4 files. If the v2 policy updates a threshold, these will drift out of sync.

**Fix prompt:**
> Create `web-ui/src/constants/structures.ts` exporting `STRUCTURE_HARD_FLOORS`, `STRUCTURE_IDEAL_TARGETS`, and `STRUCTURE_METADATA`. Import these across `FilterSidebar.tsx`, `App.tsx`, `probability.ts`, and `mockData.ts`.

---

#### P2-6: `MapCanvas.tsx` Re-renders on Every Mouse Move (1,524-Line Monolith)

**Affected file:** `web-ui/src/components/MapCanvas.tsx` — L105, L1081–1090, L1221–1229

**Problem:** `setCursorWorld` updates state on every mouse move, causing the entire 1,524-line component to re-render at 60–120 FPS. The coordinate overlay should be rendered to canvas directly or isolated in a lightweight subcomponent.

**Fix prompt:**
> Store cursor world coordinates in a `useRef` instead of state. Render the coordinate text directly onto the canvas in the animation frame, or extract a `<CoordinateBadge>` subcomponent that reads from the ref.

---

#### P2-7: Global Keyboard Shortcuts Fire Inside Modals

**Affected files:** `web-ui/src/App.tsx:274–291`, `SeedDetailModal.tsx`, `FunnelModal.tsx`

**Problem:** Space toggles start/stop sweeps globally. While `HTMLInputElement` and `HTMLSelectElement` are guarded, pressing Space when a modal is open starts/stops a sweep. Neither modal responds to Escape.

**Fix prompt:**
> In `App.tsx`, check `if (isFunnelOpen || inspectedCandidate !== null)` before handling Space/d/b/g. Add Escape key listener to close modals.

---

#### P2-8: ~80% Duplicate Evaluation Code in `blueprint.py`

**Affected file:** `src/seed_search/realm/blueprint.py` — `evaluate_seed` (L185–279) vs `evaluate_locked_seed` (L281–410)

**Problem:** Both functions share ~80% identical code for lattice sampling, biome counting, distance calculation, and result formatting. Bug fixes in one are frequently missed in the other.

**Fix prompt:**
> Extract shared logic into `_evaluate_blueprint_core(predictor, points, required_biomes, bounds, ...)`. Have both `evaluate_seed` and `evaluate_locked_seed` delegate to this helper.

---

#### P2-9: Blanket Exception Swallowing Across Server and Caching

**Affected files:** `web/server.py:334,458,742` (`except Exception: pass`), `report_cache.py:60,78`, `reports.py:194`, `realm/native_batch.py:470` (`except BaseException: pass`)

**Problem:** Bare `except Exception: pass` silently hides SQLite read errors, JSON syntax errors, and missing files. `except BaseException` in `native_batch.py` and `verification.py` catches `KeyboardInterrupt` and `SystemExit`, preventing graceful shutdown.

**Fix prompt:**
> 1. Replace `except Exception: pass` with specific exception types and add `logging.warning(...)`.
> 2. Change `except BaseException` to `except Exception` and re-raise in cleanup contexts.

---

#### P2-10: SQLite Nested Transaction Warning in BDS Attempt Reservation

**Affected file:** `src/seed_search/realm/verification.py:199–200` (`_reserve_attempt`)

**Problem:** `with db:` starts transaction management. `db.execute('BEGIN IMMEDIATE')` inside it can trigger `sqlite3.OperationalError: cannot start a transaction within a transaction`.

**Fix prompt:**
> Replace:
> ```python
> with db:
>     db.execute('BEGIN IMMEDIATE')
>     ...
> ```
> With:
> ```python
> db.execute('BEGIN IMMEDIATE')
> try:
>     ...
>     db.commit()
> except Exception:
>     db.rollback()
>     raise
> ```

---

#### P2-11: Dead Deep Dark Heuristic Logic in `landscapes.py`

**Affected file:** `src/seed_search/landscapes.py:62–73` (`deep_dark_hint`), L429, L450–451, L569

**Problem:** `deep_dark_hint()` is defined but `hint = None` is hardcoded at L429. The sorting key references `v[2]['contrast']` which is always `None`. The function and downstream plumbing are entirely inert.

**Fix prompt:**
> Remove `deep_dark_hint` function, simplify the nomination tuple to omit the dummy hint, and remove contrast checks from candidate sorting.

---

#### P2-12: Global Cache Size Collision Between Backend Instances

**Affected file:** `src/seed_search/backend.py:20, 305–312` (`_RAW_LAYOUTS`, `structure_pair`)

**Problem:** `_RAW_LAYOUTS = OrderedDict()` is module-level. When `structure_pair` evicts entries, Backend instance B with `raw_cache_entries=0` will flush instance A's cached layouts.

**Fix prompt:**
> Make `_raw_layouts` an instance attribute on `Backend` instead of a module-level global.

---

#### P2-13: Hardcoded Docker Executable Path in BDS Tools

**Affected file:** `src/seed_search/realm/bds_tools/poc_control.py:5`

**Problem:** `DOCKER = '/Applications/Docker.app/Contents/Resources/bin/docker'` breaks on Linux, WSL, CI, and Homebrew-installed Docker.

**Fix prompt:**
> Replace with: `DOCKER = shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'`

---

#### P2-14: Hardcoded `runs/` Paths in Production Code and Tests

**Affected files:** `src/seed_search/web/server.py:37` (`DEFAULT_NATIVE_BUILD`), 8+ test files

**Problem:** `server.py` hardcodes `DEFAULT_NATIVE_BUILD = 'runs/cpu-completion-2026-10-13/final-portable'`. Tests hardcode paths to untracked timestamped `runs/` folders. If `runs/` is cleaned, both production and tests break.

**Fix prompt:**
> In `server.py`, resolve native build path dynamically via `importlib.resources` or config. In tests, use `search.example.yaml` or fixtures in `fixtures/` instead of `runs/` paths.

---

#### P2-15: Hot-Loop Repeated Imports in `terrain.py`

**Affected files:** `src/seed_search/realm/terrain.py:349,362,381,401,412`, `siblings.py:29`

**Problem:** Functions perform repeated inline `import` statements inside inner per-candidate loops for `raster_variant_fit`, `evaluate_marine_stage`, `biome_name`, `uuid`, `fcntl`. In `siblings.py`, `set(random)` is re-evaluated inside a list comprehension per candidate.

**Fix prompt:**
> Hoist all helper/module imports to module level or top of function outside the candidate loop. Extract `random_set = set(random)` once before the loop.

---

#### P2-16: 185 Lines of Boilerplate Vite CSS in `App.css`

**Affected file:** `web-ui/src/App.css` (L1–185)

**Problem:** Default Vite starter CSS (`.counter`, `.hero`, `.framework`, `#center`, `#next-steps`). Never imported by `App.tsx`. Project uses Tailwind CSS exclusively.

**Fix prompt:**
> Delete `web-ui/src/App.css`.

---

#### P2-17: Repository Hygiene — 103 GB `runs/`, 48 Root Markdown Files, Profiler Dumps

**Affected areas:** Repository root, `runs/`, `exports/`, `default.profraw`

**Problem:** 48 Markdown files at root (specs, benchmarks, LLM handoff prompts). 698 run files tracked in Git due to `!runs/**/*.json` in `.gitignore`. 13 MB of committed snapshot bundles in `exports/`. Stale `default.profraw` (91 KB).

**Fix prompt:**
> 1. Organize docs into `docs/` with `specs/`, `architecture/`, `archive/` subfolders.
> 2. Fix `.gitignore` to exclude `runs/` entirely; remove tracked run files from Git.
> 3. Delete `exports/` (host snapshots as release assets if needed).
> 4. Delete `default.profraw`; add `*.profraw` to `.gitignore`.

---

#### P2-18: Missing BDS Dependencies and CLI Entry Point in `pyproject.toml`

**Affected file:** `pyproject.toml:11–17`

**Problem:** `compare_saved_blocks.py` and `snapshot_reader.py` import `amulet_nbt` and `leveldb`, but neither is declared. No `seed-realm` CLI entry point exists.

**Fix prompt:**
> Add to `pyproject.toml`:
> ```toml
> [project.optional-dependencies]
> bds = ["amulet-nbt>=3.0.0", "amulet-leveldb>=1.0.0"]
> [project.scripts]
> seed-realm = "seed_search.realm.cli:main"
> ```

---

### P3 — Polish, consistency, minor DX improvements

---

#### P3-1: Toast Timer Overwrites — Newer Messages Cleared by Earlier Timeout

**Affected file:** `web-ui/src/App.tsx` — `showToast` (L51–54)

**Problem:** `showToast` sets a 3.5s timeout without clearing existing timeouts. A second toast triggered at 2s gets cleared at 3.5s by the first timeout.

**Fix prompt:**
> Store `toastTimerRef = useRef<NodeJS.Timeout | null>(null)`. In `showToast`, call `if (toastTimerRef.current) clearTimeout(toastTimerRef.current)` before scheduling.

---

#### P3-2: Saved Runs Not Auto-Loaded When Opening Hardware Tab

**Affected file:** `web-ui/src/components/FilterSidebar.tsx:38–48, 913–925`

**Problem:** `refreshRuns` is only called on manual button click. The runs dropdown is empty when navigating to the Hardware tab.

**Fix prompt:**
> Call `refreshRuns()` inside a `useEffect` when `activeTab === 'engine'`.

---

#### P3-3: `parse_candidate_row` Omits `spawnDistanceUnits`

**Affected files:** `src/seed_search/web/server.py:554–581`, `web-ui/src/types.ts:93`

**Problem:** Structures include `distanceUnits` but candidates don't include `spawnDistanceUnits`. Frontend falls back to generic `'blocks'`.

**Fix prompt:**
> In `parse_candidate_row`, add `"spawnDistanceUnits": "overworld horizontal blocks"` to the returned dict.

---

#### P3-4: Incomplete `COMMANDS` Set in Realm CLI

**Affected file:** `src/seed_search/realm/cli.py:20`

**Problem:** Omits `'search'`, `'doctor'`, `'benchmark'`, `'resume'` from the `COMMANDS` set, causing valid CLI commands to fail early membership validation.

**Fix prompt:**
> Update: `COMMANDS = {'init', 'run', 'search', 'resume', 'status', 'verify', 'calibrate', 'export', 'inventory', 'benchmark', 'doctor'}`

---

#### P3-5: Identical Redundant Boolean Computation in `verification.py`

**Affected file:** `src/seed_search/realm/verification.py:827–828`

**Problem:** `(~predicted_water[known] != ~actual_water[known])` is mathematically identical to `(predicted_water[known] != actual_water[known])`. The same computation runs twice under two key names.

**Fix prompt:**
> Compute `mismatches = int((predicted_water[known] != actual_water[known]).sum())` once and assign to both keys.

---

#### P3-6: Fragile Float Truthiness Check in `scoring.py`

**Affected file:** `src/seed_search/scoring.py:68`

**Problem:** `if distance else 1 if distance==0 else None` relies on float `0.0` being falsy — confusing and fragile.

**Fix prompt:**
> Rewrite: `1.0 if distance == 0 else min(1.0, full_credit / distance) if distance is not None else None`

---

#### P3-7: Fictitious Biome Names in Taxonomy

**Affected files:** `src/seed_search/biomes.py:39–41`, `src/seed_search/wood.py:9`

**Problem:** `"dappled_forest"`, `"sulfur_caves"`, `"ice_caves"` don't exist in Bedrock or cubiomes. Dead config entries.

**Fix prompt:**
> Remove fictitious biome names from `biomes.py` group definitions and `wood.py` woodland sets.

---

#### P3-8: Production Data Integrity Checks Using `assert`

**Affected file:** `src/seed_search/realm/bds_tools/probe_tools.py:78,81–83`

**Problem:** `assert` validates batch ordering and row counts. Running Python with `-O` silently strips these checks.

**Fix prompt:**
> Replace `assert` with `if ...: raise RuntimeError(...)`.

---

#### P3-9: Repeated Set Allocation in `scoring.distinct_rank`

**Affected file:** `src/seed_search/scoring.py:126`

**Problem:** `{v['seed'] for v in lists[group]}` re-computed on every iteration. O(N × limit) instead of O(1) with a persistent set.

**Fix prompt:**
> Maintain `seen_seeds = {g: set() for g in lists}` and use `if c['seed'] not in seen_seeds[group]`.

---

#### P3-10: Unchecked Type in `review.validate_review` Raises Wrong Exception

**Affected file:** `src/seed_search/review.py:24,34`

**Problem:** `len(r['center'])` without `isinstance` check raises `TypeError` instead of descriptive `ValueError` on malformed JSON.

**Fix prompt:**
> Add: `if not isinstance(r.get('center'), (list, tuple)): raise ValueError("Review requires exact eight-block center")`

---

#### P3-11: Temporary Files Abandoned on Exception in `report_cache.py`

**Affected file:** `src/seed_search/report_cache.py:28–33,38–44` (`write_atomic`, `save_terrain`)

**Problem:** `NamedTemporaryFile(delete=False)` creates temp files. If serialization or `os.replace` fails, orphaned files remain.

**Fix prompt:**
> Wrap in `try...finally` that unlinks the temp file if `os.replace()` was not reached.

---

## 3. Quick Wins

The following can be batched into a single cleanup commit:

**Batch prompt:**
> Perform the following cleanup across the `minecraft-seed-searcher` repository:
>
> **Unused imports to remove:**
> - `src/seed_search/regression.py:6` — `from collections import Counter`
> - `src/seed_search/reports.py:31` — `biome_name` from `.backend`
> - `src/seed_search/reports.py:122` — `landscape_review_fields` from `.review`
> - `src/seed_search/search.py:6` — `import json`
> - `src/seed_search/search.py:16` — `distinct_rank` from `.scoring`
> - `src/seed_search/realm/baseline.py:6` — `import numpy as np`
> - `src/seed_search/realm/baseline.py:10` — `postprocess_ids` from `.native_batch`
> - `src/seed_search/realm/baseline.py:11` — `report` from `.bounds`
> - `src/seed_search/realm/blueprint.py:15` — `from .config import WOOD`
> - `src/seed_search/realm/cli.py:13` — `origin_blueprint_config`, `outpost_blueprint_config`, `river_blueprint_config`, `locked_blueprint_config`, `default_config`, `blueprint_config` (6 unused symbols)
> - `src/seed_search/realm/raw.py:243` — `from .baseline import evaluate_seed`
> - `src/seed_search/realm/bds_tools/probe_tools.py:3` — `sys`, `hashlib`, `statistics`
>
> **Duplicate inline imports to deduplicate:**
> - `src/seed_search/landscapes.py:18,49` — `biome_name` re-imported inside functions (already imported at L13)
> - `src/seed_search/reports.py:179` — `from .preflight import save_json` (already imported at L121)
>
> **Dead code to remove:**
> - `src/seed_search/realm/blueprint.py:315` — `if True:` block indentation artifact
> - `src/seed_search/realm/blueprint.py:368` — dead `pass` statement
> - `src/seed_search/realm/bds_tools/Dockerfile:2–3` — consolidate consecutive `RUN apt-get update` into one layer
>
> **Naming fix:**
> - `src/seed_search/cli.py:70` — replace `__import__("seed_search.backend", fromlist=["capabilities"]).capabilities()` with `from .backend import capabilities; capabilities()`
>
> Preserve all existing comments and docstrings. Do not change any logic.

---

## 4. Redundancy Removal Log

### Files to delete outright

| File / Directory | Rationale |
|---|---|
| `web-api/` (entire directory) | Abandoned FastAPI mock server with wrong endpoints, fake data, and insecure CORS. Real server is `src/seed_search/web/server.py`. |
| `web-ui/src/App.css` | 185 lines of default Vite starter CSS. Never imported. Project uses Tailwind. |
| `seed_search/` (root directory) | CFFI build artifacts creating namespace package shadow. Not source code. |
| `src/seed_search/_native.c` | Stale CFFI-generated file from Oct 7 (43 KB). Current version is in root `seed_search/_native.c` (85 KB). |
| `src/seed_search/_native.dylib` | 2.1 MB compiled binary tracked in Git. Should be built locally. |
| `default.profraw` | 91 KB stale profiler dump. |
| `exports/` (entire directory) | 13 MB of committed historical code snapshots. Host as release assets if needed. |

### Dead functions to delete

| Function | File | Rationale |
|---|---|---|
| `predict_candidate_ravines` | `web/server.py:584–633` | Never called. Fabricates coordinates with unimported `hashlib`. |
| `predict_candidate_cave_clusters` | `web/server.py:635–698` | Never called. Fabricates coordinates with arbitrary arithmetic. |
| `get_curated_or_historical_candidates` | `web/server.py:700–746` | Never called. References hardcoded paths. |
| `deep_dark_hint` | `landscapes.py:62–73` | Defined but `hint = None` hardcoded at callsite. Entirely inert. |

### Scripts to delete (95 of 98)

All scripts in `./scripts/` except these 3 are one-off experiments, dated benchmark trials, or historical report generators for completed milestones (Oct 7–13):

**Retain and relocate:**
- `build_blueprint_batch.py` → move to `native/`
- `merge_runs.py` → move to `src/seed_search/realm/merge.py`
- `tune_machine.py` → keep as developer utility

**Delete all others (95 scripts + 2 C probes):**

| Script | Rationale |
|---|---|
| `assemble_compact_results.py` | One-off markdown assembler for Oct 10 milestone |
| `assemble_master_readiness.py` | Historical assembler for Oct 10 readiness doc |
| `assemble_sweep_readiness.py` | Superseded by current readiness tooling |
| `attribute_master_terrain.py` | One-off Oct 10 terrain attribution |
| `audit_compact_border_funnel.py` | Ephemeral compact border funnel audit |
| `audit_compact_detection.py` | Structure detection rate diagnostic |
| `audit_master_benchmark.py` | Historical 100k/1M benchmark audit |
| `audit_repeated_compute.py` | Obsolete cache evaluation diagnostic |
| `audit_system.py` | Duplicates `readiness.py` and `preflight.py` |
| `benchmark_blueprint.py` | Superseded by native batch benchmarks |
| `benchmark_blueprint_coast.py` | One-off coastal detection benchmark |
| `benchmark_compact_final.py` | Oct 10 compact filter timing benchmark |
| `benchmark_compact_implementation.py` | Python vs C filter runtime comparison |
| `benchmark_compact_raw.py` | Raw structure iteration timing |
| `benchmark_compact_selection_persistence.py` | SQLite persistence latency benchmark |
| `benchmark_exact_cache.py` | Historical caching comparison (Oct 8) |
| `benchmark_filter_shortcuts.py` | Short-circuit bounds benchmark (Oct 8) |
| `benchmark_full_evidence_pipeline.py` | Superseded by `test_native_throughput.py` |
| `benchmark_full_evidence_revision.py` | Candidate row overhead benchmark |
| `benchmark_locked_blueprint.py` | Locked stronghold geometry benchmark |
| `benchmark_native_blueprint.py` | Early CFFI vs native comparison |
| `benchmark_native_chunks.py` | Chunk size micro-benchmark |
| `benchmark_native_entrypoint.py` | CLI entrypoint speed comparison |
| `benchmark_native_ranking.py` | In-memory vs SQLite ranking comparison |
| `benchmark_native_throughput.py` | Thread allocation benchmark |
| `benchmark_outpost_orders.py` | Outpost filter order benchmark |
| `benchmark_outpost_workflow.py` | Outpost filter short-circuit diagnostic |
| `benchmark_realm_stages.py` | Individual Realm stage benchmark |
| `benchmark_river_blueprint.py` | River highway heuristic benchmark |
| `biome_diversity_pilot_api.py` | Experimental biome kernel wrapper; crashes on import |
| `blueprint_batch_prototype.py` | 5-line shim re-exporting `native_batch` symbols |
| `build_biome_diversity_pilot.py` | Standalone CFFI compiler for experimental kernel |
| `build_count_pilot.py` | Standalone CFFI compiler for count-N kernels |
| `compare_accuracy_audit.py` | UI vs engine prediction comparison |
| `compare_compact_selection.py` | Lower32 selection heuristic comparison |
| `compare_fresh_coordinates.py` | Website vs engine coordinate verification |
| `compare_master_schedules.py` | OpenMP scheduling experiment |
| `count_pilot_api.py` | Ephemeral CFFI wrapper; crashes on import |
| `diagnose_filter_costs.py` | 945-line one-off profiling diagnostic |
| `finish_implementation_verification.py` | Oct 8 milestone handoff verification |
| `forecast_master_benchmark.py` | Runtime extrapolation for 1M sweep |
| `investigate_bds_latency.py` | BDS startup latency diagnostic |
| `investigate_terrain_cascade.py` | Terrain cascade edge case investigation |
| `join_master_terrain_evidence.py` | Database join script for terrain evidence |
| `measure_compact_border_funnel.py` | Compact border rejection rate measurement |
| `measure_master_acceleration.py` | OpenMP thread scaling trial |
| `measure_master_borders.py` | Border dimension measurement |
| `measure_master_discovery.py` | Discovery grid spacing evaluation |
| `measure_master_funnel.py` | Candidate survival feasibility pilot |
| `measure_realm_border_combinations.py` | Border dimension variation trial |
| `native_process_experiment.py` | Rejected multi-process IPC experiment |
| `native_throughput_arm.py` | Isolated thread allocation benchmark |
| `pilot_additional_raw_structures.py` | Raw structure type exploration |
| `pilot_all_structure_combinations.py` | Combinatorial structure pilot |
| `pilot_biome_variant_counts.py` | Biome variant counting pilot |
| `pilot_common_centers.py` | Envelope overlap center solver |
| `pilot_count_bits_biomes.py` | Bit-level biome predictability research |
| `pilot_count_bits_discovery.py` | Stronghold discovery amortization pilot |
| `pilot_count_bits_structures.py` | Lower32 vs lower48 bit constraints |
| `pilot_locked_stronghold.py` | Locked stronghold survival pilot |
| `pilot_lower48_siblings.py` | High-16 sibling yield trial |
| `pilot_minimal_raw_gate.py` | Minimal structure filtering pilot |
| `pilot_possible_stronghold_centers.py` | Theoretical stronghold bounds calculation |
| `pilot_proposed_combo_throughput.py` | Filter combination timing trial |
| `plot_accuracy_audit.py` | Matplotlib audit figure generator |
| `prepare_accuracy_audit.py` | Test coordinate sampling script |
| `profile_native_coastal.py` | Coastal contour profiling |
| `profile_native_stages.py` | Per-structure filter profiling |
| `profile_river_coastal.py` | River path extraction profiling |
| `reanalyze_million_count_feasibility.py` | Post-hoc 1M run analysis |
| `report_accuracy_audit.py` | Accuracy audit markdown generator |
| `report_compact_border_funnel.py` | Funnel pass rate report generator |
| `report_count_bits.py` | Bit multiplicity report generator |
| `report_million_count_feasibility.py` | COUNT_REQUIREMENT_FEASIBILITY.md generator |
| `sanitize_blueprint_batch.py` | One-off AddressSanitizer harness |
| `simd_probe.py` | SIMD availability probe; never adopted |
| `trace_master_strongholds.py` | RNG state tracing via monkey-patch |
| `trace_strongholds.py` | Earlier RNG tracing iteration |
| `tune_native_order.py` | SQLite batch insertion order trial |
| `tune_native_process.py` | Multiprocessing vs multithreading benchmark |
| `verify_approved_implementation.py` | Oct 8 sign-off verification |
| `verify_compact_completion.py` | Compact search completion verification |
| `verify_compact_end.py` | End dimension island verification |
| `verify_compact_inventory_terrain.py` | Terrain inventory accuracy verification |
| `verify_compact_native_safety.py` | ASan/UBSan memory safety check |
| `verify_expanded_pilot.py` | Expanded landscape pilot verification |
| `verify_master_isa.py` | Host ISA compatibility verification |
| `verify_master_native.py` | C/Python engine parity check |
| `verify_master_safety.py` | Master implementation memory safety |
| `verify_master_thread_counts.py` | Thread count parity verification |
| `verify_million_count_replay.py` | 1M positive candidate replay |
| `verify_report_reuse.py` | Report cache regression verification |
| `write_expanded_readiness_report.py` | LANDSCAPE_EXPANSION.md generator |
| `write_filter_readiness.py` | FILTER_OPTIMIZATION.md generator |
| `write_sweep_readiness_report.py` | SWEEP_READINESS.md generator |
| `filter_cost_probe.c` | Obsolete C filter cost probe |
| `simd_probe_kernel.c` | Obsolete SIMD instruction probe |

### Test files to delete (9 pilot test files)

| Test File | Rationale |
|---|---|
| `tests/test_all_structure_combinations_pilot.py` | Tests deleted pilot script |
| `tests/test_biome_diversity_count_pilot.py` | Tests deleted pilot; crashes if `runs/` missing |
| `tests/test_blueprint_batch_prototype.py` | Tests deleted prototype shim |
| `tests/test_common_center_pilot.py` | Tests deleted pilot script |
| `tests/test_count_pilot_build.py` | Tests deleted build script |
| `tests/test_locked_stronghold_pilot.py` | Tests deleted pilot script |
| `tests/test_native_count_pilot.py` | Tests deleted pilot API |
| `tests/test_native_stage_profile.py` | Tests deleted profiling script |
| `tests/test_pipeline_review.py:36–42` | Lines testing deleted `build_blueprint_batch` args |
