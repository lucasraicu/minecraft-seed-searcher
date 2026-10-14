# Pre-push change review

Date: 2026-10-14. Base: `c8843c8`. Scope: the pending working tree and review corrections, not a new release or exhaustive CPU-optimality certification.

Every included path below was inspected before commit. The green light applies to the described change and its available verification; pre-existing backlog items remain recorded in the historical reviews. Source/test changes were checked through diffs, execution-path inspection, focused regression tests and the full Python/frontend gates. Small run records were checked as historical provenance, with JSON parsing, size and credential-pattern inspection; they are not certified reproduction inputs for the changed computation identity.

## Blockers corrected before approval

- Absolute native source paths failed wheel packaging; packaging uses relative sources while standalone builds use resolved sources and build scratch directories.
- Packaged Stronghold identity previously copied a Python constant; the C ABI now reports the compiled setting.
- SELF RSS fallbacks cannot account for child processes; partial diagnostics stay unavailable to the memory gate and child RSS stays unknown in the UI.
- Compact disk forecasts ignored their own empirical rate; configured and observed growth now participate while physical limits remain enforced.
- Run selection needed traversal/symlink validation and truthful partial-run state; process/evidence ownership now guards cross-run operations.
- Nether grid requests previously queried Overworld data; grids now use the requested dimension and explicitly carry predictor provenance.
- Duplicate Nether anchors and invented shared count floors could distort verification; distinct anchors and resolved per-category requirements are used.
- Merge imports could fabricate a resumable checkpoint; the tool now declares a read-only aggregate, rejects conflicting records atomically and preserves original sources.
- Tuning recommendations exceeded production limits or misrepresented kernel rates; the bounded grid now varies actual batches and reports its limited measurement scope.
- UI details fabricated perfect metrics and accepted stale command/polling results; unknown data remains unknown and command generations protect state.

## Verification

Final gates: **974 Python tests passed in 287.06 seconds**, frontend lint and production build passed, the standalone native blueprint rebuild passed, and the wheel build passed. Focused regressions and the dimension-aware Nether API smoke check passed; whitespace checks and the selected-file credential-pattern scan passed. Browser smoke on an isolated empty run directory confirmed live empty-state rendering and opening/Escape-closing the evidence dialog without starting a sweep.

## File-by-file green light

| Path | Disposition | Reviewed change |
| --- | --- | --- |
| `.gitignore` | Green light | Exclude generated native binaries, profiler data and root CFFI output; keep source/evidence ownership clear. |
| `CLAUDE-REPORT.md` | Green light | Preserve the external historical review as hypotheses; do not treat its severity/deletion advice as certification. |
| `COXEX-Report.md` | Green light | Preserve the Oct 13 review snapshot with explicit reference to current commit dispositions. |
| `DISTRIBUTED_README.md` | Green light | Validate setup/CLI bounds and shared seed-domain partitioning; document backups and aggregate restrictions accurately. |
| `GEMINI-REPORT.md` | Green light | Preserve the external historical review as hypotheses; reject unsafe monitor fallbacks suggested by that report. |
| `README.md` | Green light | Describe the real dashboard and supported distributed limits; remove unsupported speed/certification claims. |
| `config/reference-sweep.yaml` | Green light | Remove unvalidated scoring family names consistently from example/historical profiles. |
| `config/review-all.yaml` | Green light | Remove unvalidated scoring family names consistently from example/historical profiles. |
| `config/staged-sweep.yaml` | Green light | Remove unvalidated scoring family names consistently from example/historical profiles. |
| `native/blueprint_batch.h` | Green light | Expose the compiled Stronghold-placement setting through the ABI. |
| `native/blueprint_batch.inc` | Green light | Return the actual compiled Stronghold setting; screening logic is unchanged. |
| `native/blueprint_build.py` | Green light | Generate CFFI scratch under build/; support relative packaging sources and absolute standalone sources. |
| `native/bridge.c` | Green light | Reject NULL context/output buffers before native grid/height/land/density access. |
| `native/build.py` | Green light | Move build scratch out of the root package; preserve portable build flags and valid setuptools paths. |
| `outputs/picker-debug.png` | Green light | Remove a debug screenshot; no runtime dependency. |
| `pyproject.toml` | Green light | Resolve src-layout imports consistently in pytest. |
| `runs/full-evidence-optimization-2026-10-12/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/full-evidence-optimization-2026-10-12/policy.yaml` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/gemini-pipeline-review-2026-10-12/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-build-v2/identity.json` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-build-v3/identity.json` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-build-v4/identity.json` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-locked-geometry-2026-10-12/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-throughput-2026-10-12/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-throughput-2026-10-12/original-profile.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/native-throughputput-cli-smoke/compatibility.json` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/origin-fixed-pilot-2026-10-13/control.yaml` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/origin-fixed-pilot-2026-10-13/origin.yaml` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/origin-fixed-pilot-2026-10-13/results.json` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/outpost-optimization-2026-10-12/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/pre-sweep-audit-2026-10-13/control.yaml` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/pre-sweep-audit-2026-10-13/head.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/pre-sweep-audit-2026-10-13/initial-realm.yaml` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/pre-sweep-audit-2026-10-13/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/pre-sweep-audit-2026-10-13/origin.yaml` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/pre-sweep-audit-2026-10-13/results.json` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `runs/river-highway-2026-10-12/initial-status.txt` | Green light | Small historical audit/configuration/build record only; preserve recorded identity/timing context, not current certification. |
| `scripts/merge_runs.py` | Green light | Stream compatible snapshots into an explicit non-resumable aggregate; atomic conflict rejection, interval-union coverage and source/record provenance. |
| `scripts/tune_machine.py` | Green light | Partition the tested batches, cap production threads, counterbalance repeated kernel-only measurements and emit a valid explicit-build command. |
| `search.example.yaml` | Green light | Remove unvalidated scoring family names consistently from example/historical profiles. |
| `seed_search/_native.c` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `src/seed_search/_native.c` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `src/seed_search/_native.dylib` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `src/seed_search/biomes.py` | Green light | Exclude unvalidated taxonomy families from supported scoring policy; vendor catalog is preserved. |
| `src/seed_search/geometry.py` | Green light | Handle empty angular masks and force boolean inversion semantics. |
| `src/seed_search/realm/bds_tools/compare_saved_blocks.py` | Green light | Close LevelDB and remove copied world directories on success and failure. |
| `src/seed_search/realm/bds_tools/probe_tools.py` | Green light | Use explicit evidence-integrity exceptions, which remain active under python -O. |
| `src/seed_search/realm/bds_tools/snapshot_reader.py` | Green light | Use scoped temporary-world ownership and unconditional database cleanup. |
| `src/seed_search/realm/caves.py` | Green light | Check exact sample-grid cardinality before allocating points. |
| `src/seed_search/realm/cli.py` | Green light | Default new native scans to compact survivors; retain saved retention on resume and full Python behavior. |
| `src/seed_search/realm/coastal.py` | Green light | Handle absent optional nested coastal evidence without inventing observations. |
| `src/seed_search/realm/config.py` | Green light | Validate supported structure goals at the native count boundary (64). |
| `src/seed_search/realm/marine.py` | Green light | Handle absent optional nested stage evidence; preserve separate marine provenance. |
| `src/seed_search/realm/native_batch.py` | Green light | Read packaged compiled policy identity; use retention-aware disk limits and fail closed when tree monitoring is unavailable. |
| `src/seed_search/realm/reports.py` | Green light | Handle optional nested evidence being null while retaining reporting and score contracts. |
| `src/seed_search/realm/resources.py` | Green light | Separate compact/full disk estimates, respect configured rates and measured growth, retain physical cap/reserve checks. |
| `src/seed_search/realm/runner.py` | Green light | Keep unavailable tree monitoring explicit; SELF high-water RSS is labeled diagnostic and cannot bypass the memory gate. |
| `src/seed_search/realm/siblings.py` | Green light | Persist and resume partial adaptive rounds; verify complete result cardinality before advancing. |
| `src/seed_search/realm/store.py` | Green light | Centralize immediate write transactions, preserve sibling dictionary fields/count-score contracts, and reject aggregate databases as checkpoints. |
| `src/seed_search/realm/verification.py` | Green light | Resolve distinct Nether count requirements, deduplicate anchors and improve null handling without certifying global eligibility. |
| `src/seed_search/realm/verification_plan.py` | Green light | Support exact 1536/2048 bounds, prefer configured policy and reject shrunken/mismatched squares. |
| `src/seed_search/structures.py` | Green light | Preserve paired Stronghold proposal coordinates rather than constructing cross-products. |
| `src/seed_search/web/server.py` | Green light | Review run/path and process ownership; restore/view saved data, expose truthful bounded terrain/marine states and correct dimension-aware model grids. |
| `src/seed_search/wood.py` | Green light | Remove an unvalidated woodland scoring name. |
| `tests/test_adaptive_siblings.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_approved_plan.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_biomes_fictitious.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_commit_review.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_geometry.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_merge_runs.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_native_build_hardening.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_realm_store.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_realm_verification.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_realm_verification_plan.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_structures_phantom.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `tests/test_web_server_hardening.py` | Green light | Regression coverage for the associated behavior/contract; test fixtures inspected and included in verification. |
| `web-api/main.py` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `web-ui/index.html` | Green light | Use the project title. |
| `web-ui/src/App.css` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `web-ui/src/App.tsx` | Green light | Validate command success, serialize commands, discard obsolete polling responses, reflect effective goals and protect interactive keyboard contexts. |
| `web-ui/src/assets/hero.png` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `web-ui/src/assets/react.svg` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `web-ui/src/assets/vite.svg` | Green light | Remove obsolete mock API/template asset or stale generated native artifact; authoritative source/build paths remain. |
| `web-ui/src/components/CandidateFeed.tsx` | Green light | Provide explicit stage tabs/alternate sorts, default canonical ranking without hidden minimum score, and truthful copy/evidence feedback. |
| `web-ui/src/components/ErrorBoundary.tsx` | Green light | Render a truthful crash state with reset/reload controls. |
| `web-ui/src/components/FilterSidebar.tsx` | Green light | Bound supported counts and clearly separate planning-only controls from live sweep settings. |
| `web-ui/src/components/FunnelModal.tsx` | Green light | Add keyboard/dialog handling and describe predictor/BDS stages without unsupported certification claims. |
| `web-ui/src/components/MapCanvas.tsx` | Green light | Remove fabricated fallback features, display model biome grids with seed/dimension guards and bounded cache, and throttle hover work. |
| `web-ui/src/components/SeedDetailModal.tsx` | Green light | Expand evidence inspection and dimension distances; remove invented metrics/coordinates and show score points. |
| `web-ui/src/components/TelemetryBar.tsx` | Green light | Expose pause/continue/terrain controls with honest unknown RSS/ETA and completed/error labels. |
| `web-ui/src/constants/structures.ts` | Green light | Centralize existing frontend category/goal metadata without changing the backend oracle. |
| `web-ui/src/main.tsx` | Green light | Install the React error boundary. |
| `web-ui/src/mockData.ts` | Green light | Reuse shared defaults and retain explicit illustrative demo provenance. |
| `web-ui/src/types.ts` | Green light | Describe new ranking, evidence, distance and nullable terrain telemetry fields. |
| `web-ui/src/utils/probability.ts` | Green light | Return probability one for zero goals; reuse shared constants and remove duplicate Nether presence factor. |
| `web-ui/vite.config.ts` | Green light | Proxy local development API requests to the loopback backend. |

## Local artifacts excluded from the commit

- `runs/web-sweep-*/`: mutable website-run policies/checkpoints stay local.
- `runs/test-debug/` and `runs/tune-t36/`: scratch/debug experiments stay local.
- Ignored native binaries, generated build scratch, profiler files, SQLite/WAL databases and frontend dist output stay local. No local run evidence was deleted.

## Remaining limits

Original runs remain authoritative for resume, terrain work and verification; changing computational identities can make older checkpoints unsuitable for resume, and the guard is preserved. Website candidates/JSON export are a bounded displayed pool rather than the full database. Planning probabilities remain uncalibrated, some controls remain planning-only, cross-platform adoption still needs parity/held-out performance evidence, and actual first-player spawn remains pending without a client. This commit does not close every item in the historical reports or replace the production certification process.
