# Readiness audit — checked October 22, 2026

This is a repository/readiness audit, not fresh exhaustive certification of every
line, game world or historical test. Current source/build/state matches the 208-file
profiling baseline. Fresh checks: 638 catalog tests collect, legacy contracts
validate, and 26 focused reserve/native-guard/finalization/cache-integrity tests pass
in 6.37s. One known Python multithreaded-fork warning remains in its explicit test.
The prior full 637-test catalog run and subsequent focused evidence are reused;
they are not relabeled as a new 638-test pass. No source/runtime change or seed/game
campaign occurred. See [check receipts](AUDIT_CHECKS.json) and the
[reviewed proposed plan](../../docs/PRE_GPU_READINESS_PLAN.md).

| Area | Current finding | Evidence | Before-transition disposition |
|---|---|---|---|
| Personal prediction/search | Implemented, corrected 34-thread native engine; about 69k input seeds/sec with bounded active catalog load | [Benchmark](../current-framework-benchmark-2026-10-22/REPORT.md) | Freeze reproducible oracle; measure sustained/full-reserve behavior |
| Personal 2K reserve | New Top-50 runs retain 100; historical run preserved | [Tests](../../tests/test_personal_reserve.py), [release](../biome-expansion-plan-2026-10-22/RELEASE_REPORT.md) | Mechanics pass; natural full-heap/sustained cost remains unmeasured |
| Local catalog | 222 worlds, 109,918 memberships, 7,543 objectives; 93 available metadata options | [Live state](LIVE_STATE.json), [variant release](../variant-controls-and-organization-2026-10-22/RELEASE_REPORT.md) | No repeat feature-expansion project needed |
| Biomes/variants | 56 exact Overworld biomes, five Nether biomes, four groups; basement/treasure controls passed | [Controls](../../fixtures/bedrock-26.52/variant-controls/README.md) | Keep predicted labels and finite-control limits; historical gates unchanged |
| Scoring/coordinates | 845/265/140; Overworld sides 2048/4096/8192, Nether 1024; same-anchor ANY/ALL and unknown semantics | [V3](../../docs/catalog/v3/README.md), [oracles](../biome-expansion-plan-2026-10-22/FINAL_CATALOG_AUDIT.json) | Mandatory CPU/GPU/read-model regression contract |
| Extraction | 32.43s probe; repeated JSON/checkpointing and 5.74s summaries expensive | [Profile](../storage-query-profile-2026-10-22/REPORT.md) | Reduce repeated serialization without weakening durability |
| Serving | Result-cache misses about 2–5s; board page about 3.25s with manifest rebuild | [Queries](../storage-query-profile-2026-10-22/QUERIES.json) | Production guarded read views remain to implement |
| Read-index prototypes | Finite exact-output checks; about 0.48ms board lookup and 0.254s selective blob load/scorer | [Prototypes](../storage-query-profile-2026-10-22/READMODELS.json) | Integrity, cursors, recovery and concurrent-publication integration outstanding |
| Storage | Current reachable CAS 241MB; all automation CAS 1,036MB; SQLite 111.8MB | [Inventory](../storage-query-profile-2026-10-22/STORAGE.json) | Preserve evidence/history; no custom-engine winner established |
| Recovery | Queue/lease, atomic-publication, page-corruption and worker tests exist | [Harvest](../../tests/catalog/test_harvest_process_recovery.py), [paging](../../tests/catalog/test_manifest_paging.py), [workers](../../tests/catalog/test_query_workers.py) | Changed checkpoint/view formats need fault and restore checks |
| Retention quality | Full-sort/mechanics evidence exists; current retained union cannot prove default-cap population recall | [Limits](../catalog-validation-2026-10-20/REPORT.md) | Use oversubscribed mechanics before integration; large real held-out quality later |
| Finalist certification | Operator implemented; every current winner is not game-certified | [Operator](../../src/seed_search/catalog/finalization_operator.py) | Certify advertised finalists before verified launch; no blanket campaign before GPU proof |
| Strongholds/terrain | Stronghold coverage partial; landing, safety and exhaustive absence unsupported | [Investigation](../biome-expansion-plan-2026-10-22/STRONGHOLD_COVERAGE.md) | Preserve limits; predictor changes are a separate project |
| Historical P1 reports | Current code recounts optional features after snapping, uses nb_alloc, dispatches V3 rescoring, respects cutoff policy and waits outside the pause lock | [Fixes](../framework-fixes-2026-10-16/IMPLEMENTATION.md), [refinement](../native-refinement-2026-10-16/IMPLEMENTATION.md) | Preserve reports/regressions; do not label archived findings current without reproduction |
| Legacy GPU architecture | Superseded; shared personal rejection conflicts with independent public admission | [Old proposal](../../docs/specs/DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md), [authority](../../PUBLIC_CATALOG_SYSTEM_SPEC.md) | Replace contract; free harvesting, 64-byte records and 100M/sec are unverified assumptions |
| Hardware | This iMac: AMD Radeon Pro Vega 56, 8GB; future NVIDIA/CUDA target unverified | [Inventory](gpu-inventory.log) | Confirm actual host, device, toolchain and access before kernel coding |
| GPU/database implementation | No CUDA/custom-engine implementation found in inspected src/native/scripts; no DuckDB/Arrow runtime dependency | Source, path and dependency inspection | Conversion remains proposed |
| Repository organization | Eight approved document moves/navigation completed; inherited dirty work preserved | [Organization](../../REPO_ORGANIZATION_PLAN.md), [Git baseline](git-status-before.txt) | Restorable source snapshot next; broad source/test moves unnecessary |
| Documentation | Found stale variant-gate language in active V3 README and outdated scale evidence in status | [Before V3](V3_README_BEFORE.md), [before status](PROJECT_STATUS_BEFORE.md) | Active guides corrected during this audit; historical reports/templates preserved |
| Public launch | Local server/host guards exist; hosting, accounts, payments and production SLA remain separate work | [Server](../../src/seed_search/catalog/http_server.py), [status](../../docs/PROJECT_STATUS.md) | Separate launch track; not an isolated GPU proof prerequisite |

Personal PID91321 remains completed/idle with its historical saved run. Public
PID22035 remains paused at 0/600s with no jobs/campaigns. Vite PID17880 is preserved.
Conservative repository templates are intentional: live availability belongs to
the immutable current snapshot registry. Two independent High critiques and the
Codex dispositions are in [RECONCILIATION.md](RECONCILIATION.md).
