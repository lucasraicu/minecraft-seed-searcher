> Review snapshot from 2026-10-13. Some findings are addressed by subsequent working-tree changes; see [COMMIT_REVIEW.md](COMMIT_REVIEW.md) for the reviewed commit dispositions.

# COXEX-Report

Review date: 2026-10-13. Project: minecraft-seed-searcher. Baseline: `c8843c81990b58764d5abf29d7b5d1742b321bd9`, plus the working-tree changes present during review, including the uncommitted distributed tools and latest leaderboard/sidebar/modal edits.

## 1. Executive Summary

The codebase has substantial strengths: independent Python/native checks, pinned generation identities, durable range accounting, explicit prediction-versus-actual evidence in much of the backend, and a large passing test suite. The biggest risks are gaps between those backend contracts and the website, incomplete actual-world verification, and new distributed utilities that bypass established storage and execution contracts. Frontend state, policy definitions, database projections, and benchmark orchestration contain repeated logic that makes these inconsistencies easier to introduce. No confirmed P0 issue was found, but the P1 findings should be addressed before relying on the website and distributed workflow for a production sweep. Passing tests establish the covered behavior; they do not establish exhaustive CPU optimality or actual first-player spawn correctness.

### Scope and verification

The review covered first-party application code in `src/seed_search/`, native integration in `native/`, `web-ui/src/`, configuration and packaging, the test suite, support/benchmark scripts, standalone picker tooling, and the distributed documentation/tools currently outside git. Source inventory, import/reference searches, schema and execution-path inspection, and focused runtime reproductions were used. Support scripts were reviewed through inventory/static inspection and risk-focused execution paths; historical artifacts were treated as evidence rather than active application code. Vendored code was reviewed at its integration boundaries and relevant RNG/thread/build paths; this is not a new upstream vulnerability audit or proof that every third-party implementation is correct.

Coverage map:

| Area | Reviewed responsibilities |
| --- | --- |
| Root/configuration/packaging | README and distributed runbook, realm policy, build configuration, dependency/runtime assumptions, native manifests and generated-artifact boundaries |
| `src/seed_search/realm/` | Runner, store, range recovery, compact retention, native batch, baseline/blueprint policy, terrain/biomes/raster/marine/caves, verification, spawn/surface, resources, reports, adaptive siblings, calibration and CLI |
| Other `src/seed_search/` modules | Historical search/storage/cache/reporting, staged filters, native bridge/count/biome pilots, scoring/geometry/landscapes, preflight/readiness/regression and observations/review |
| `src/seed_search/web/` and `web-ui/` | Process lifecycle, API validation and projections, run selection, React state/polling, controls, leaderboards, details, map, telemetry, planning probabilities, accessibility and exports |
| Native/vendor/build | C batch/filter/bridge interfaces, identity/defaults, bounds, OpenMP ownership and compiler/build entry points; relevant vendor integration |
| `scripts/`, `outputs/`, tests | Script inventory and side effects, benchmark/verification/report workflows, merge/tuning helpers, standalone picker scope and automated coverage |

Completed checks:

- Python suite: **940 passed**, 265.38 seconds.
- Frontend lint and production build: **passed** at the tested snapshot. Subsequent working-tree UI edits were inspected; these checks must be rerun when those edits are finalized.
- Temporary-fixture reproductions confirmed: rejection of the current 2048-block verification footprint; one Fortress plus one Bastion marked verified despite larger policy requirements; packaged native policy mismatch; acceptance of an unsupported count of 65; website ordering inconsistent with canonical ranking; missing terrain displayed as failure; duplicated merge coverage with missing range/receipt data; and the tuner's default exceeding the native batch limit.
- No production sweep, expensive benchmark campaign, or live Bedrock world was launched for this review. No client is available to verify a real player's first join.

## 2. Prioritised Action Items

Priority definitions: **P0** — confirmed data loss, security breach or production crash; **P1** — likely bugs or material UX/performance degradation under real conditions; **P2** — compounding technical debt, refactors or inconsistent patterns; **P3** — polish, consistency or minor DX improvements.

### P0

None confirmed. The unsafe merge output described below does not establish destruction of original source databases, and non-loopback exposure is an optional configuration rather than the server default.

### P1

#### P1-01 — Distributed merger creates an incompatible, incomplete database

**Affected files/functions:** `scripts/merge_runs.py:merge_runs`, `src/seed_search/realm/store.py:RealmStore`, `DISTRIBUTED_README.md`.

**Problem:** The merger invents a range schema instead of using RealmStore's schema, then silently ignores failures reading the real range table. It omits source identity, authoritative seed/range/retention-receipt data and other evidence needed for recovery. `INSERT OR IGNORE` silently chooses the first conflicting candidate, even across incompatible policies. Coverage is summed from metadata, so importing the same ten-seed source twice reports twenty seeds; incremental imports also use an incorrect maximum. A nonexistent directory destination becomes a database file, and the resulting aggregate cannot be resumed as the advertised Realm run. Broad exception handling can still report a source as merged after incomplete imports.

**Fix prompt:** Repair `scripts/merge_runs.py` against the authoritative schema in `src/seed_search/realm/store.py`. Decide explicitly whether the output is a resumable RealmStore or a separate read-only aggregate, and implement/document that contract. Validate policy, native identity and seed-domain compatibility before imports; preserve provenance and all evidence required by the chosen contract; reject conflicting records explicitly. Track source imports idempotently, compute unique completed coverage from validated intervals, stream records in bounded transactions, and distinguish directory versus database destinations explicitly. Add temporary-database tests for repeated and incremental imports, overlapping ranges, incompatible identities, conflicting evidence and failed source reads. Preserve original source databases.

#### P1-02 — Hardware tuner fails by default and does not vary batch size

**Affected files/functions:** `scripts/tune_machine.py:tune_machine`, `src/seed_search/realm/native_batch.py:Prototype.sweep`, realm CLI production limits.

**Problem:** The default 30,000-seed trial is passed as one native batch, exceeding the 16,384-input limit. The advertised batch-size loop never uses `batch_size` when submitting work, so it cannot measure batch scaling. Its CPU-count-derived thread grid can exceed supported launch limits, and its reported rate measures native time rather than durable end-to-end scanning. A single fixed-order trial cannot support the printed claim of optimal settings. The emitted production command also uses the wrong CLI entry point/options.

**Fix prompt:** Fix `scripts/tune_machine.py` to partition each trial using the actual tested batch size and supported production thread limits from the realm CLI/native executor. Separate kernel throughput from durable scan throughput. Use bounded, repeated/counterbalanced trials with correctness parity, retaining the approved 50,000-input tuning and five 100,000-input held-out adoption budget within 15–20 minutes. Emit a valid `python -m seed_search --config ... scan ...` command with the selected executor, retention, starting index and native settings. Test orchestration with a fake executor, including the default 30,000 inputs and machines with more cores than the production limit.

#### P1-03 — Actual terrain verification rejects the current footprint

**Affected files/functions:** `src/seed_search/realm/verification_plan.py:verification_region`, verification CLI callers and related tests.

**Problem:** Coastal verification requires the legacy fixed 1536-block Stronghold footprint. The current 2048-block policy produces `ValueError: Coastal verification requires a fixed Stronghold1536 footprint` before verification starts. Existing legacy cases do not protect the current policy.

**Fix prompt:** Update `src/seed_search/realm/verification_plan.py:verification_region` and its callers to derive the exact permitted verification bounds from the candidate and resolved realm configuration, including the current 2048-block square. Keep identity and coordinate validation strict; do not silently shrink the region to meet a resource budget. Return an explicit partial/deferred result when the actual verification budget is insufficient. Add tests for current 2048 and legacy 1536 policies, translated centers, malformed bounds and resource-budget handling.

#### P1-04 — Nether verification certifies presence without satisfying count requirements

**Affected files/functions:** `src/seed_search/realm/verification.py:final_nether_evidence`, `VerificationAdapter.verify_final_nether`, `src/seed_search/realm/cli.py` verification flow.

**Problem:** Evidence containing one Fortress and one Bastion can return `VERIFIED` although the current targets are two Fortresses and three Bastions, with Bastion hard floor two. Distinct starts, bounds and evidence provenance need explicit validation. Presence verification and policy qualification are conflated; this can make actual-world claims stronger than the checked facts.

**Fix prompt:** Make Nether verification in `src/seed_search/realm/verification.py` policy-aware. Separate verified presence from overall qualification; count distinct valid structure starts within the fixed Nether region and enforce resolved hard floors and ideal/category-deficit semantics consistently with the full candidate policy. Validate pinned version, generation settings, seed, bounds and actual evidence provenance. Do not spend the shared deficit budget independently in separate stages. Add tests for one-versus-required counts, duplicate anchors, out-of-bounds records and missing/mismatched provenance, and ensure CLI output describes the remaining verification work accurately.

#### P1-05 — Structure goals exceed native count API bounds

**Affected files/functions:** `src/seed_search/realm/config.py` validation, native count bridge/filter interfaces, `web-ui/src/components/FilterSidebar.tsx` count controls.

**Problem:** Configuration validation accepts goals through 100 while the native count API accepts floors only from 1 to 64. A goal of 65 passes validation and then fails in the backend. The website does not consistently prevent this mismatch before launching a run.

**Fix prompt:** Align configuration and website goal validation with the supported native count contract in `src/seed_search/realm/config.py`, the native bridge/filter code and `web-ui/src/components/FilterSidebar.tsx`. Either reject unsupported goals before run creation or implement a correct inventory path for larger counts. Preserve legitimate zero-baseline categories such as Mansions. Return precise validation errors and add boundary tests for zero, 64, 65 and 100 plus an API test proving invalid settings do not create a run.

#### P1-06 — Packaged native identity disagrees with compiled Stronghold policy

**Affected files/functions:** `native/blueprint_build.py`, `src/seed_search/realm/native_batch.py:Prototype`, packaged native C interface.

**Problem:** The packaged build defaults to the newer Stronghold placement setting, while the metadata fallback used by `Prototype(None, cfg)` supplies an older setting. The packaged prototype rejects the current policy with `Native Stronghold placement differs from the resolved policy`. Private build directories carry more complete identity information than the installed extension.

**Fix prompt:** Expose the compiled policy/build identity through the packaged native ABI and consume it in `src/seed_search/realm/native_batch.py`. Update `native/blueprint_build.py` so packaged and private builds use the same explicit contract without inventing metadata defaults. Keep mismatch rejection intact. Add an isolated fresh-build smoke test loading the packaged extension with the current policy and a negative test with a deliberately incompatible policy; do not overwrite an active benchmark extension during testing.

#### P1-07 — Website ranking overrides the canonical qualification order

**Affected files/functions:** `src/seed_search/web/server.py:_query_sqlite_candidates`, `src/seed_search/realm/leaderboard.py`, `web-ui/src/components/CandidateFeed.tsx` sorting.

**Problem:** The website orders primarily by raw score instead of the canonical tier, unmet requirements, score and stable ID order. A pending high-score candidate can displace a verified lower-score candidate. The query also requires a temporary ordering B-tree in the reproduced plan. Frontend score sorting can independently undo server ranking.

**Fix prompt:** Reuse the canonical ranking contract from `src/seed_search/realm/leaderboard.py` in the website query and return qualification tier, misses and stable rank in a typed candidate DTO. Update `web-ui/src/components/CandidateFeed.tsx` so the default leaderboard preserves canonical ranking and any user-selected alternate sort is clearly labeled. Add mixed-status and near-miss tests and inspect the query plan for the actual supported filtering/order rather than adding speculative indexes.

#### P1-08 — Missing terrain evidence is rendered as failure

**Affected files/functions:** `src/seed_search/web/server.py:parse_candidate_row`, `web-ui/src/types.ts`, `SeedDetailModal.tsx`, `CandidateFeed.tsx`.

**Problem:** Absence of a terrain result becomes `terrainPassed: false`. A baseline seed that has never undergone terrain evaluation is then displayed as a failed terrain candidate. This loses the difference between pending, explicit failure, model prediction and actual verification.

**Fix prompt:** Preserve terrain evidence state in `src/seed_search/web/server.py:parse_candidate_row` and the frontend candidate types. Represent never-run/pending, explicit failure, predicted pass and actual verification separately; absence must not become failure. Update details and leaderboard filters/counts to use those states and show provenance. Add projection and UI tests for all states, including a baseline with no variants.

#### P1-09 — New marine UI claims confirmation from terrain success alone

**Affected files/functions:** Working-tree `web-ui/src/components/SeedDetailModal.tsx` Marine Gating panel, `CandidateFeed.tsx` labels, `FunnelModal.tsx`, `src/seed_search/web/server.py:parse_candidate_row`.

**Problem:** The new modal states that both Monuments and Shipwrecks are confirmed whenever `terrainPassed === true`. That flag alone does not establish actual marine structure evidence, count satisfaction, coastal placement or verification provenance. The panel even shows separately recorded counts without using them to justify its confirmation text. It hardcodes goals that may differ from the configured run. The latest backend edit similarly replaces marine status with `EVALUATED` whenever terrain passes, and the funnel text presents broader verification capabilities without checking which evidence is available.

**Fix prompt:** Replace the marine confirmation logic in `web-ui/src/components/SeedDetailModal.tsx` and related feed/funnel labels with explicit marine-stage evidence supplied by `src/seed_search/web/server.py`. Remove the backend terrain-to-marine status override and derive marine status from its own evidence. Display pending, predicted, failed and actual-verified marine states independently of terrain success, using effective run goals and recorded distinct counts/coastal bounds. Never claim confirmed Monuments or Shipwrecks from a terrain boolean. Test terrain-pass-with-no-marine-evidence, insufficient counts, prediction-only evidence and verified sufficient counts.

#### P1-10 — Newly visible controls still do not affect the live request

**Affected files/functions:** Working-tree `web-ui/src/components/FilterSidebar.tsx`, `web-ui/src/App.tsx:handleToggleSweep`, backend sweep request validation.

**Problem:** Recent sidebar edits remove the enclosing planning-only section and enable more controls. The live request still submits only a subset of the displayed settings. Cave/terrain/Nether and deferred marine controls can therefore appear executable while changing estimates only. Some local explanatory text remains, but the broad visual affordance now conflicts with actual run behavior.

**Fix prompt:** Audit every setting exposed by `web-ui/src/components/FilterSidebar.tsx` against the payload built in `web-ui/src/App.tsx` and supported fields in the website API. For each setting, either implement the full server/config/executor behavior with tests or retain it in an explicitly labeled planning-only section that cannot be mistaken for active filtering. Return the effective resolved configuration and display it after start/resume. Add a contract test that changes each live control and verifies the stored run policy changes as intended.

#### P1-11 — Polling and command state can hide errors or overwrite newer runs

**Affected files/functions:** `web-ui/src/App.tsx` initialization effects, status polling, start/stop/resume handlers.

**Problem:** Terminal states collapse into idle, important backend errors are not consistently surfaced, and stop responses are not fully checked. Polling lacks an in-flight/generation guard, so delayed responses from a previous run can overwrite newer state. Optimistic running state also creates a start/stop race before launch acceptance.

**Fix prompt:** Consolidate sweep lifecycle handling in `web-ui/src/App.tsx` into explicit starting/running/stopping/completed/stopped/error states. Check HTTP status and application success for every command, preserve actionable backend errors, and show pending actions accurately. Abort obsolete requests or guard responses by run/generation identity, and avoid overlapping status polls. Add mocked-network tests for delayed old-run responses, failed start/stop/resume, terminal errors and rapid repeated clicks.

#### P1-12 — Completed runs and full candidate sets are inaccessible from the website

**Affected files/functions:** `src/seed_search/web/server.py` manager/run-list/candidate endpoints, `FilterSidebar.tsx` saved runs, `App.tsx` export handlers.

**Problem:** Saved-run selection is effectively a resume selector, excluding completed runs that cannot be resumed. Server restart does not restore the viewed run. The candidate endpoint exposes a limited set (50), while candidate totals, local filtering and export can describe that subset as all surviving candidates. Large sweeps therefore hide data and make exported coverage misleading.

**Fix prompt:** Add a read-only open/view-run API distinct from resume in `src/seed_search/web/server.py` and expose completed runs in `web-ui/src/components/FilterSidebar.tsx`. Persist or explicitly restore the selected run after server restart without relaunching it. Implement bounded pagination/server-side filters with authoritative total versus displayed counts. Use a streaming backend export for the full selected result set, reusing realm export logic where possible. Test completed-run viewing, restart, more than 50 candidates, pagination and export completeness.

#### P1-13 — Website shutdown can leave an unmanaged sweep process

**Affected files/functions:** `src/seed_search/web/server.py:run_server`, sweep manager child-process lifecycle.

**Problem:** Cleanup handles the interactive interruption path, but ordinary SIGTERM/process restart can leave the launched scan running without manager ownership. A replacement website process may report idle and start another CPU-heavy sweep. Existing database leases help protect a single run but do not prevent different runs from oversubscribing the machine.

**Fix prompt:** Give `src/seed_search/web/server.py` an explicit shutdown and recovery lifecycle for its owned child process. Handle SIGTERM and normal server teardown, request graceful checkpointed termination, and record enough process/run identity to recover or report an existing live owned scan after restart. Verify identity before signaling any process. Add subprocess lifecycle tests for termination, restart and stale ownership records; preserve RealmStore lease/recovery behavior.

#### P1-14 — Global Space shortcut can accidentally start or stop a sweep

**Affected files/functions:** `web-ui/src/App.tsx` global keydown handler.

**Problem:** The shortcut excludes only some input elements. Space on a focused button, textarea, contenteditable area or modal can also toggle the sweep; key repeat can issue repeated actions. This conflicts with normal keyboard activation and makes destructive workflow transitions surprising.

**Fix prompt:** Fix the global keyboard handler in `web-ui/src/App.tsx` to ignore interactive/editable targets, active dialogs, modifier combinations and repeated keydown events. Only prevent default when the shortcut intentionally owns the action. Preserve standard Space activation on buttons. Add keyboard tests covering focused buttons, textarea/contenteditable, modal state, repeat and an eligible page-level shortcut.

#### P1-15 — Distributed runbook recommends invalid commands and unsafe coverage assumptions

**Affected files/functions:** `DISTRIBUTED_README.md`, working-tree `README.md`, `src/seed_search/seeds.py:seed_from_index`, realm CLI.

**Problem:** Examples use `python -m seed_search.realm.cli`, which has no executable module entry point, wrong start/config options, unsupported thread/batch settings, and a Python version inconsistent with packaging. Website and verification commands also imply unsupported run selection/options. The suggested different run keys do not guarantee disjoint seed sets: the mapping mixes index plus key, so offset combinations collide. Raw copying of an active WAL database can omit committed data. Throughput and verification claims exceed the measured or implemented scope.

**Fix prompt:** Rewrite `DISTRIBUTED_README.md` and its README links using the actual `python -m seed_search --config ...` CLI and supported executor/thread/batch/verification options. Document partitioning by nonoverlapping index intervals under the same validated run key, including interval bounds. Use SQLite backup or a stopped/checkpointed/closed database plus a manifest for transfers; do not copy only a live WAL database file. Remove unsupported throughput and actual-world claims. Add lightweight parser/example validation and a seed-domain collision example explaining why different keys are not a disjointness guarantee.

#### P1-16 — Interrupted adaptive rounds can be counted and skipped as complete

**Affected files/functions:** `src/seed_search/realm/siblings.py:run_adaptive`, child scan status and adaptive checkpoint metadata.

**Problem:** Round accounting advances by the planned row count after a child scan, even when the scan was interrupted and committed only part of the work. Iterating available results can silently produce fewer rows while the next round is still selected. Summary budget and resumed coverage can diverge from actual committed work.

**Fix prompt:** Update `src/seed_search/realm/siblings.py:run_adaptive` to advance a round only after validated complete child coverage. Persist partial-round identity and resume the unfinished child, accounting only committed inputs in allocator statistics and budget summaries. Detect mismatched result counts rather than truncating through zip. Add inexpensive fake-runner tests for interruption before any results, mid-round interruption, repeated resume and complete coverage without duplicates.

#### P1-17 — Essential actual-evidence validation uses removable assertions

**Affected files/functions:** `src/seed_search/realm/bds_tools/probe_tools.py:Probe.rows`.

**Problem:** Batch sequence, sample count, unique coordinates and per-row errors are enforced with `assert`. Running Python with optimization disables these checks, allowing incomplete or malformed probe output to cross an actual-evidence boundary.

**Fix prompt:** Replace integrity assertions in `src/seed_search/realm/bds_tools/probe_tools.py:Probe.rows` with explicit validation exceptions carrying batch/sample context. Keep development-only assertions separate from evidence acceptance. Add fake probe tests for missing batches, duplicate coordinates, incorrect sample counts and error rows, and run the invalid-payload check under `python -O` without launching a Bedrock server.

### P2

#### P2-01 — Policy and API definitions are duplicated across the frontend

**Affected files/functions:** `web-ui/src/App.tsx`, `FilterSidebar.tsx`, `mockData.ts`, `utils/probability.ts`, `types.ts`, realm configuration and website DTOs.

**Problem:** Goals, floors, labels and category treatment are independently encoded in several places. `structureFloorCounts` is used for values that function as ideal targets, and effective backend configuration is not consistently used to update the UI after start/resume. Drift is already visible in planning/live and marine behavior.

**Fix prompt:** Introduce a versioned resolved-policy DTO from the website backend and shared typed frontend policy helpers. Make `App.tsx`, `FilterSidebar.tsx` and planning calculations consume the same effective goals/floors/categories; rename misleading floor-versus-ideal fields. Keep independent Python/C correctness oracles independent, with explicit parity tests, rather than sharing away their independence. Test round-trip start/resume configuration display and category-deficit semantics.

#### P2-02 — Planning probability math mishandles zero goals and changed ideals

**Affected files/functions:** `web-ui/src/utils/probability.ts:calculateStructureProb`, `computeStructureFeasibility`, sidebar estimates.

**Problem:** A Mansion goal of zero returns a tiny probability rather than the required probability of one, corrupting deficit calculations. Other tails are not consistently defined at zero. Feasibility can replace selected counts with hardcoded larger ideal targets, ignoring a lowered setting. Additional Nether multipliers can count the same requirement again. Historical/independence labels are useful, but do not correct these internal inconsistencies.

**Fix prompt:** Correct `web-ui/src/utils/probability.ts` so every count-tail satisfies P(count >= 0) = 1, is monotone, and uses the selected effective goal literally. Compute the category-deficit model from consistent ideal/floor probabilities. Remove duplicate event factors unless supported by explicitly conditional measured data. Keep unavailable estimates unavailable instead of inventing fallback probabilities. Add mathematical tests for zero goals, monotonicity, lowered ideals and B=2 category deficits, and clearly separate planning scenarios from the live gate.

#### P2-03 — Compact-run resource planning uses full-evidence byte assumptions

**Affected files/functions:** `src/seed_search/realm/resources.py`, runner preflight/storage estimates, website large-run planning.

**Problem:** The default 65,536-byte-per-input estimate reflects full evidence more than compact survivor retention. With the default 128 GiB workspace budget it can conservatively reject runs beyond roughly two million inputs even when compact storage is much smaller. This undermines the new large-range controls; runtime estimates also use a substantial fixed minimum.

**Fix prompt:** Make realm resource preflight and runtime estimates retention-aware in `src/seed_search/realm/resources.py` and callers. Estimate compact receipts and bounded survivor/evidence costs using measured schema/storage behavior, clearly reporting uncertainty. Preserve physical free-space reserve and hard workspace limits. Test large compact versus full-evidence plans and worst-case survivor growth without running large scans.

#### P2-04 — Status polling repeats expensive work and blocks manager actions

**Affected files/functions:** `src/seed_search/web/server.py:get_status` and run listing, `web-ui/src/App.tsx` polling, `MapCanvas.tsx` drawing effects.

**Problem:** Frequent polling repeats process inspection and SQLite candidate projection under manager ownership, returns largely unchanged logs/candidates, and manufactures changing discovery timestamps. Run listing repeatedly resolves/hashes identity. Fresh candidate objects and mouse movement trigger broad canvas redraws. Multiple clients amplify the cost; this is more significant than isolated missing memoization.

**Fix prompt:** Split lightweight telemetry from versioned candidate/log payloads in `src/seed_search/web/server.py`. Sample process statistics outside the command lock, cache immutable identity work by validated file/build state, and return durable timestamps and revision tokens. Fetch candidates only when their revision changes. Profile `MapCanvas.tsx` and use requestAnimationFrame/stable drawing layers for proven redraw costs. Add concurrency tests that status reads do not block stop commands and measure payload/query counts before adopting caching.

#### P2-05 — Export and selection paths perform repeated per-row database lookups

**Affected files/functions:** `src/seed_search/realm/reports.py:_export_files`, `_variant_rescore`, verification selection in `realm/cli.py`, `store.py:iter_discovery_tasks`, calibration helpers.

**Problem:** Several loops repeatedly load the parent candidate for each variant/task or re-read pools across selection passes. Report rows also duplicate nested evidence across variants. These patterns increase queries, JSON decoding and export bytes as results grow. Current evidence does not justify a generic missing-index claim beyond the observed website sort.

**Fix prompt:** Refactor the named realm report/selection/task paths to use bounded joined queries or page-local parent maps and reuse each selected pool once. Preserve streaming, snapshot consistency and existing output schemas; introduce a compact export representation only with an explicit schema/version choice. Add query-count tests for multi-variant candidates and large fake task pages plus output-parity tests.

#### P2-06 — Evidence publication and rescore do not share one concurrency contract

**Affected files/functions:** `realm/reports.py` rescore locking, inventory/terrain schedulers in `realm/store.py`, direct result updates in `realm/cli.py`, `realm/surface.py:save_surface_verification`.

**Problem:** Scan/rescore, inventory and terrain use different ownership locks. Some verification paths read a candidate, perform slow work, then replace its full JSON result, allowing concurrent publication/rescore fields to be overwritten. Surface verification provides a better pattern by reloading current policy/state and coordinating publication.

**Fix prompt:** Establish one short publication transaction or revision-checked patch API in `src/seed_search/realm/store.py` for candidate evidence and derived scores. Update inventory, terrain, rescore and CLI verification writes to use it, following the current-state/ownership discipline in `realm/surface.py`. Keep slow generation outside database locks. Add interleaving tests proving concurrent terrain, inventory and verification fields survive and stale policy-derived scores cannot be published.

#### P2-07 — Installed package assumes repository-only identity resources

**Affected files/functions:** `pyproject.toml`, realm capability/identity helpers, native/vendor manifest lookup paths.

**Problem:** Several identity/resource paths are derived from checkout-relative native/vendor locations. These are not all packaged at the same locations in a wheel. Editable-checkout testing can therefore hide failures in a clean installed environment. This is a static packaging finding; a clean-wheel execution was not performed during this review.

**Fix prompt:** Audit resource lookup in realm capabilities/identity/native setup against `pyproject.toml`. Package required immutable manifests/resources and load them through package-resource APIs, or explicitly declare unsupported checkout-only commands. Add a clean-wheel smoke check in a temporary environment outside the repository for the advertised entry points and current policy identity, avoiding expensive benchmarks.

#### P2-08 — Non-loopback website configuration has no authentication boundary

**Affected files/functions:** `src/seed_search/web/server.py` host configuration, request origin/host validation and mutation handlers.

**Problem:** Loopback is the safe default. If `SEED_SEARCH_WEB_HOST` binds externally, unauthenticated requests without an Origin header can access the sweep controls; Origin checks alone are not authentication. Host validation is also absent as a local-browser hardening boundary. This finding is conditional on exposure, not a claim of default public access or a confirmed breach.

**Fix prompt:** Make `src/seed_search/web/server.py` fail closed for non-loopback binding unless an explicit authenticated deployment mode is configured. Validate allowed hosts/origins, authenticate mutation and private read routes in that mode, and retain loopback convenience. Add tests for default loopback, external binding without credentials, missing/wrong Origin and unexpected Host. Document the supported access model without claiming CORS provides authentication.

#### P2-09 — Snapshot readers leak temporary world copies after errors

**Affected files/functions:** `realm/bds_tools/snapshot_reader.py`, `compare_saved_blocks.py`.

**Problem:** Database close and temporary-directory removal occur on the successful path rather than reliably in finally/context-managed cleanup. Decode/read failures can leave copied worlds in temporary storage, accumulating outside the run's normal workspace accounting.

**Fix prompt:** Use context-managed temporary directories and explicit finally-based database cleanup in `src/seed_search/realm/bds_tools/snapshot_reader.py` and `compare_saved_blocks.py`. Preserve immutable source worlds and existing diagnostic output. Add injected open/decode failures proving copies and handles are released; retain a failed copy only through an explicit, documented diagnostic option.

#### P2-10 — Cave budget checks happen after allocating the full sampling grid

**Affected files/functions:** `src/seed_search/realm/caves.py` sample-grid construction and budget check.

**Problem:** The point list is materialized before its size is compared with the sampling budget. A small spacing over a large footprint can allocate millions of tuples just to return an over-budget result. The nominal budget therefore does not bound preparatory memory use.

**Fix prompt:** In `src/seed_search/realm/caves.py`, compute exact grid cardinality before allocation and reject/defer oversized work immediately. Generate acceptable grids lazily or in bounded batches while preserving deterministic order and evidence semantics. Test extreme spacing/footprint combinations using a sampler that proves no points are allocated/submitted after budget rejection.

#### P2-11 — Demo fallback and unchecked DTOs obscure the actual application state

**Affected files/functions:** `web-ui/src/App.tsx`, `mockData.ts`, `types.ts`, `web-ui/tsconfig*.json`.

**Problem:** The frontend initially renders illustrative mock data and can retain it after failed backend calls. Existing demo labels help, but initial data differs from eventual live data and competes with truthful empty/loading/error states. JSON responses are accepted without a strong shared contract and TypeScript strictness is limited, making stale/malformed response behavior harder to catch.

**Fix prompt:** Initialize the production website with empty/loading/error states in `web-ui/src/App.tsx`; expose demonstration data only through an explicit demo mode. Define typed API DTOs and validate unknown responses at the boundary before updating state. Enable stricter TypeScript checks incrementally for touched modules. Add tests for unavailable backend, malformed payloads, demo entry/exit and successful live loading, with no invented live candidates.

#### P2-12 — Large modules mix unrelated ownership responsibilities

**Affected files/functions:** `web-ui/src/components/MapCanvas.tsx`, `FilterSidebar.tsx`, `App.tsx`, `src/seed_search/web/server.py`, `realm/store.py`.

**Problem:** Rendering, event handling, policy, transport and lifecycle logic are concentrated in large files; server/store modules similarly combine projection, scheduling and persistence. This makes contract fixes require edits across broad surfaces and encourages local duplicated solutions.

**Fix prompt:** After correcting the identified behavior bugs, extract cohesive modules from the named files: sweep API/state hook, resolved policy controls, candidate projection/query service, process manager, bounded evidence-publication API and map drawing/interaction layers. Keep public behavior and compatibility stable, avoid generic frameworks, and move existing tests with the ownership boundary. Use measured redraw/query evidence to guide performance changes rather than blanket memoization.

#### P2-13 — Backend-heavy tests leave critical website behavior uncovered

**Affected files/functions:** `web-ui/package.json`, frontend components/API integration, repository CI configuration.

**Problem:** Frontend lint/build check syntax and packaging, but there is no comparable automated behavior suite for lifecycle races, keyboard actions, evidence labels or export scope. The standalone picker check targets a different UI. No repository CI workflow was found to consistently exercise these boundaries or clean packaging.

**Fix prompt:** Add a small frontend behavior/integration suite for `App.tsx`, `FilterSidebar.tsx`, `CandidateFeed.tsx` and `SeedDetailModal.tsx` using deterministic mocked API responses. Cover lifecycle/errors, keyboard handling, evidence provenance, effective settings and full export scope. Add a CI workflow for the existing Python suite, frontend checks and clean-package smoke checks with explicit optional-native/platform handling. Keep production benchmarks and live BDS generation outside ordinary CI.

#### P2-14 — Benchmark and verification scripts have inconsistent execution contracts

**Affected files/functions:** `scripts/benchmark_native_entrypoint.py`, `tune_native_order.py`, `report_accuracy_audit.py` and other historical benchmark/report entry points; build/benchmark helpers.

**Problem:** Some scripts execute argument parsing, writes or expensive work at import, and many assume dated run directories or fixed output paths. This complicates safe reuse and provenance. Historical experiments remain valuable controls; deleting them as duplicates would lose evidence.

**Fix prompt:** Audit executable scripts under `scripts/` for import-time actions and implicit output paths. Put work behind `main()` guards, require explicit input/output identities, and protect existing evidence from accidental overwrite. Extract only common trial recording, timing/parity and bounded-budget helpers; retain independent historical algorithms and original artifact schemas. Add import smoke checks and fake-executor tests rather than rerunning expensive historical campaigns.

#### P2-15 — Rebuilt BDS reader environments are not dependency-reproducible

**Affected files/functions:** `src/seed_search/realm/bds_tools/Dockerfile`, reader dependencies and image identity manifest.

**Problem:** The existing pinned image identity is a strength, but Docker rebuilds install unpinned reader libraries and distribution packages. A new image can change decoding behavior despite identical project source. This is a reproducibility issue, not an asserted known vulnerability.

**Fix prompt:** Record and pin the BDS reader dependency environment in `src/seed_search/realm/bds_tools/Dockerfile` and a reviewed build manifest/lock. Keep generated image identity changes explicit and require the existing reader/fixture verification before accepting a rebuilt image. Document platform/base-image assumptions and avoid presenting an unverified rebuild as equivalent to the pinned production image.

### P3

#### P3-01 — Score presentation implies an unsupported 100-point ceiling

**Affected files/functions:** `web-ui/src/components/SeedDetailModal.tsx`, score thresholds in `CandidateFeed.tsx`.

**Problem:** Details show `Score: ... / 100`, although smart-score bonuses can exceed 100 and the raw score is not a percentage. Feed thresholds similarly suggest a normalized scale without that contract.

**Fix prompt:** Update `SeedDetailModal.tsx` and feed score labels to display raw points and explain the active scoring recipe. If a normalized metric is required, define it as a separate explicit backend field rather than clamping raw smart_score. Test candidates above 100 and unrated candidates.

#### P3-02 — Clipboard controls claim success before copying succeeds

**Affected files/functions:** `web-ui/src/components/CandidateFeed.tsx` copy handlers and analogous modal controls.

**Problem:** Clipboard writes are not consistently awaited or handled, so permission/unavailable-API failures can still produce copied feedback.

**Fix prompt:** Share a small asynchronous clipboard helper across `CandidateFeed.tsx` and `SeedDetailModal.tsx`. Report success only after the write resolves, provide useful failure feedback and preserve accurate coordinate/evidence text. Test rejected promises and unavailable clipboard APIs without introducing a fabricated fallback success.

#### P3-03 — Dialog, layout and canvas sizing need accessibility polish

**Affected files/functions:** `SeedDetailModal.tsx`, `FunnelModal.tsx`, `App.tsx` layout, `MapCanvas.tsx` sizing.

**Problem:** Dialog semantics/focus management and small-screen layout are incomplete. Fixed-width panels can crowd the map, while canvas sizing does not consistently account for resize events and device pixel ratio. These affect usability even when the underlying data is correct.

**Fix prompt:** Add dialog roles, focus trapping/restoration and Escape handling to both modal components; make the dashboard panels usable at narrow widths. Use ResizeObserver and explicit device-pixel-ratio handling for MapCanvas without changing world-coordinate interaction. Verify keyboard navigation, resize and high-DPI rendering in an isolated browser test.

#### P3-04 — Local clear actions and zero-result limits are inconsistent

**Affected files/functions:** `web-ui/src/App.tsx` clear handlers, realm results CLI validation, `realm/leaderboard.py:rows`.

**Problem:** Clearing candidates/logs locally is undone by the next poll, and selection can refer to a now-hidden candidate. The results CLI accepts limit zero while the leaderboard helper rejects it; related variant paths allow an empty result. These small inconsistencies make controls harder to predict.

**Fix prompt:** Define local clear behavior in `App.tsx` explicitly as a persistent view dismissal or remove/rename the action; keep selected candidate state consistent without deleting run evidence. Align the realm results CLI and leaderboard zero-limit contract, either returning an empty set everywhere or rejecting zero at parsing everywhere. Add small behavior tests for a poll after clear and both result paths with limit zero.

## 3. Quick Wins

Safe low-effort work can be batched separately from the P1 changes:

- Remove reference-verified dead demo generators and historical fallback reader from the live website server.
- Remove unused template CSS/assets and the unused imports listed below.
- Replace the misleading `/ 100` score label with points.
- Await clipboard operations and surface failure.
- Align zero-limit validation at the CLI boundary.
- Remove unused tuning/merge bookkeeping variables.

**Batch fix prompt:** In minecraft-seed-searcher, perform a narrowly scoped cleanup: remove the unreferenced functions `predict_candidate_ravines`, `predict_candidate_cave_clusters` and `get_curated_or_historical_candidates` from `src/seed_search/web/server.py`; remove unused `web-ui/src/App.css` and template assets `react.svg`, `vite.svg`, `hero.png` after a final reference search; remove the reference-verified unused imports and local variables listed in the Redundancy Removal Log. Change the details score label from `/ 100` to points, await clipboard writes with truthful feedback, and align zero-limit validation between the realm results CLI and leaderboard helper. Preserve historical experiments, fixtures, generated-source ownership and compatibility reexports. Do not alter policy, evidence semantics or benchmark output in this batch. Run Python checks appropriate to changed modules and frontend lint/build; add only meaningful tests for the clipboard and zero-limit behavior.

## 4. Redundancy Removal Log

These entries are source-cleanup candidates, not instructions to erase historical evidence or uncommitted work. Recheck references immediately before deletion because the working tree is being edited. Unused imports have no identified runtime/reexport consumers; intentionally reexported compatibility symbols are excluded.

- `src/seed_search/web/server.py:predict_candidate_ravines` — no live callers; invents geological coordinates instead of projecting evidence, and its unused fallback references an unimported hashing module.
- `src/seed_search/web/server.py:predict_candidate_cave_clusters` — no live callers; synthetic cave-coordinate generation is unnecessary in the evidence-backed server.
- `src/seed_search/web/server.py:get_curated_or_historical_candidates` — unreferenced dated-database fallback duplicates candidate retrieval.
- `web-ui/src/App.css` — unused starter stylesheet; the app imports the actual shared stylesheet.
- `web-ui/src/assets/react.svg` — unused starter asset with no current source references.
- `web-ui/src/assets/vite.svg` — unused starter asset with no current source references.
- `web-ui/src/assets/hero.png` — unused starter asset with no current source references.
- `src/seed_search/_native.dylib` — tracked stale generated binary; the active loader/build selects the ABI extension `.so`. Remove after a final clean-build/import-path check, not by modifying generated C manually.
- `src/seed_search/realm/baseline.py` imports `np`, `postprocess_ids`, `report` — unused in the module.
- `src/seed_search/realm/bds_tools/poc_control.py` import `re` — unused.
- `src/seed_search/realm/bds_tools/probe_tools.py` imports `sys`, `hashlib`, `statistics` — unused.
- `src/seed_search/realm/blueprint.py` import `WOOD` — unused.
- `src/seed_search/realm/cli.py` imports `origin_blueprint_config`, `outpost_blueprint_config`, `river_blueprint_config`, `locked_blueprint_config`, `default_config`, `blueprint_config` — unused configuration constructors, with no identified reexport consumers.
- `src/seed_search/realm/runner.py` import `canonical` — unused.
- `src/seed_search/realm/raw.py:evaluate_siblings` local import `evaluate_seed` — unused.
- `src/seed_search/regression.py` import `Counter` — unused.
- `src/seed_search/search.py` imports `json`, `distinct_rank` — unused.
- `scripts/audit_compact_detection.py` import `configure_native_threads` — unused.
- `scripts/benchmark_blueprint_coast.py` import `np` — unused.
- `scripts/benchmark_compact_raw.py` import `statistics` — unused.
- `scripts/benchmark_exact_cache.py` import `json` — unused.
- `scripts/benchmark_filter_shortcuts.py` import `math` — unused.
- `scripts/finish_implementation_verification.py` import `Path` — unused.
- `scripts/pilot_biome_variant_counts.py` imports `defaultdict`, `np` — unused.
- `scripts/pilot_count_bits_biomes.py` import `defaultdict` — unused.
- `scripts/pilot_locked_stronghold.py` imports `contains`, `BASE` — unused.
- `scripts/profile_native_coastal.py` imports `RasterCache`, `canonical` — unused.
- `scripts/simd_probe.py` import `subprocess` — unused.
- `scripts/tune_native_order.py` import `time` — unused.
- `scripts/verify_approved_implementation.py` imports `time`, `analyze_seed`, `seed_from_index` — unused.
- `scripts/verify_master_native.py` import `os` — unused.
- `scripts/tune_machine.py:tune_machine` local `start` timestamp — never read; its `time` import can also be removed if no wall-clock measurement is added by the tuner repair.
- `scripts/merge_runs.py:merge_runs` local `total_candidates_added` accumulator — never reported/read and counts fetched rather than inserted records; remove or replace with truthful accounting during the merge repair.

### Explicit retention decisions

Do not delete historical result reports, benchmark controls, fixture datasets, schema compatibility paths, `scripts/blueprint_batch_prototype.py` compatibility reexports, independent Python/native oracle implementations or generated C sources required by the build merely because they look duplicated. Do not remove physical disk checks, pinned identity rejection or explicit partial-evidence states as simplification. Untracked profiling data and run directories may belong to active work; artifact retention/ignore rules should be handled separately with provenance preserved.

### Release interpretation

This report is a review deliverable, not production certification. Correctness gates, measured CPU-optimization acceptance/rejection, stable held-out benchmarks and actual-world evidence are distinct requirements. The approved bounded optimization definition is achievable; proving that no conceivable CPU redesign could be faster is not established by the current evidence. First-player spawn remains an external verification dependency without a client, and must remain labeled pending rather than inferred from generated blocks.
