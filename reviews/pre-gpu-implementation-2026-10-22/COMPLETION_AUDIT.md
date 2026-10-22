# Requirement-by-requirement completion audit

Scope derives from the approved readiness plan and the user's executing goal:
“do all of those”, then **define the GPU contract only**, then compare database
options. GPU implementation/adoption and live restarts/migration are excluded.
This audit uses actual current files, process/API state, command receipts and outputs.

| Requirement | Authoritative evidence | Disposition |
|---|---|---|
| A: Preserve dirty source/build/dependencies/data identities | REFERENCE_FREEZE.json, RESTORE_NATIVE_SMOKE.json, RESTORE.md, SOURCE_HASHES.json in private root, source-before.tar.gz | 978 files archived/restored byte-exact; native imports passed; current data copied with SQLite backup |
| A: Freeze CPU query/coordinate/seed oracles | Frozen ORACLES/QUERIES files, CPU_REFERENCE_VECTORS.json, GPU_CONTRACT_VERIFICATION.json | Complete query outputs retained; 75 CPU vectors replayed |
| A: Reconcile current versus historical/proposed facts | Updated active plan/status/navigation, POLICY_COMPATIBILITY.md, REPORT.md | Corrected source-policy handling and 93-entry registry breakdown; historical records retained |
| A/E: Determine hardware boundary | Prior actual system_profiler receipt and GPU contract | Current Vega56/8GB verified; future target unassigned. Hardware/device proof is a future gate under the contract-only instruction |
| B: Reduce real serialization/derivation work | DERIVATION_BEFORE/AFTER.json, RECORD_REPLAY.json | Three matched component trials and three counterbalanced full-record pairs show improvement; no native work/height/validation/fsync omitted |
| B: Fixed-work fact/score/witness/coverage parity | FIXED_REPLAY_PARITY.json, SAVED_FACT_REPLAY.json | All frozen pipeline facts match excluding explicit policy ID; 28 stratified full summaries equal scalar source |
| B: Durable boundaries, old readers, source-bound compatibility | test_ingestion_optimization.py, test_versioned_derivation.py, full-regression.log | Same envelope/readers/fsync boundary; replace failure preserves prior bytes; old config unchanged; changed fast-source pin rejected |
| B: Explicit recovery work/time bounds | REPORT.md recovery-quantum paragraph and unchanged extraction/queue code | Existing per-stage quanta and parent/tile/search limits retained; acknowledged facts/budgets not rolled back |
| C: Board ranks, counts, statuses, pagination and reserves | SERVING_AFTER.json, SERVING_PARITY.json | All 36 products / 72 views checked in complete order against full original membership facts |
| C: Conservative flexible-query masks, same-anchor ALL and biome ANY/unknown | SAVED_FACT_REPLAY.json, test_guarded_read_views.py, SERVING_PARITY.json | All222 worlds/54,615 summaries,151,848 mask comparisons; complete five-query outputs equal |
| C: Snapshot/projection bindings, corruption, cursors and immutable cache values | test_guarded_read_views.py, test_verified_query_index.py, full regression | Warm unrelated-page/projection corruption detected; changed bindings rejected; original cursors remain pinned across publication |
| C: Publication/recovery architecture | service.py/read_views.py, existing manifest/worker/publication tests | New views are bounded ephemeral immutable caches; no new durable index or query-triggered disk rebuild. Existing immutable CAS publication/fault paths retained |
| C: Memory, timeout and full API measurements | SERVING_AFTER.json, SUSTAINED.json | Existing64MiB per-worker serialized allowance and10s limit retained; primed guarded service≈146ms, loopbackHTTP≈157ms |
| D: Full100 reserve mechanics, ties, cutoff, dedup, persistence, promotion | test_readiness_reserve_capacity.py and test_personal_reserve.py in687-test run | Full production capacity checked synthetically; independent full-sort/pruned pipeline and historical50 compatibility retained |
| D: All7,543 objective2K mechanics | test_reserve_v3.py and prior full-sort evidence, rerun in current catalog suite | Exact capacities and oversubscription mechanics pass; large real held-out recall remains a separate quality study |
| D: Sustained real coexistence, durable screening, selected candidates and rates | SUSTAINED.json, POSITIVE_COEXISTENCE.json | Five-minute repeated-known-cohort test;1,944HTTP queries;3full records; rare-positive pair matches prior receipts/full record SHA. Zero-survivor long cohort disclosed |
| D: Backpressure/fencing under faster intake | BACKPRESSURE.json, selected queue/recovery tests | Eight descriptors/32saved seeds stay at4pending jobs across32expansions; bounded sampled handoff and owned cancellation verified |
| D: Fault/restore/resource/budget tests | Full selected suite and private recovery receipts | Crash/leases/resume/corruption/limits checked; source restore demonstrated; extraction spending includes failed attempt; final resource ledger/preservation checked separately |
| D: Full current catalog and affected native/personal regression | full-regression.log | 687 tests pass, one known fork-test warning |
| D: Frontend contracts/build | FRONTEND_CHECKS.json and logs | 10 catalog Node suites and build pass; interactive browser waiver retained |
| E: Defined numerical/admission/transport/progress/fallback contract | docs/gpu/GPU_CONTRACT_V1.md and gpu_contract_v1.json | Concrete bounded wire records/IDs, independent admission, exact integer/wide ranking semantics, retained2K, failure/overflow/backpressure/fallback rules defined |
| E: Contract validation without claiming GPU work | GPU_CONTRACT_VERIFICATION.json | 75 CPU vectors, record sizes, seven malformed wire examples checked; no device/kernel/production codec claim |
| F: Compare standard storage options on actual facts | DATABASE_COMPARISON.json and DATABASE_COMPARISON.md | SQLite3.54.1, DuckDB2.0,Parquet,NumPy mmap measured; original full scorer equal;4x replicas labeled,notfleet data |
| F: Recovery/integrity/concurrency and build/storage costs | DATABASE_RECOVERY.json, DATABASE_COMPARISON.json | Both engines preserve committed rows/retry afterSIGKILL,rollbackuncommitted data,explicit concurrency conflicts; hashes detect corruption |
| F: Current documentation and justified decision | docs/catalog/DATABASE_COMPARISON.md | Official SQLite/DuckDB2.0/PostgreSQL sources checked; Quack mode acknowledged; no invented PostgreSQL/Arrow/Quack timings; keep SQLite now,no custom engine selected |
| Dependency finding: SQLite WAL-reset fix | SQLITE_PRIVATE_RUNTIME.json, patched-sqlite logs, DATABASE_RECOVERY.json | Private official3.54.1 adapter validated;678initial passes+9corrected bootstrap reruns cover selected687cases. Live3.50.4 replacement remains a controlled activation task |
| Preserve personal/native/history/live state and quota | FINAL_VERIFICATION.json, RESOURCE_LEDGER.json, worker status receipts | Final independent hashes/APIs/processes/resource reconciliation required before goal completion |

Final preservation/audit status: PASS — all required current-scope evidence verified.

The following are future transition gates, not silently marked complete: confirmed
GPU device/toolchain; an approved bounded kernel implementation and actual device
parity/performance proof; controlled adoption of source and a patched production
interpreter; fleet ingestion/engine migration; large real retention-quality/game
certification studies; exhaustive stronghold/terrain/landing guarantees; hosting,
accounts and billing. No GPU port or engine replacement is required to satisfy this
contract-and-comparison goal.
