# Final executable pre-sweep plan

Phase 1 audit: 2026-10-13. **Not sweep-ready:** the checkpoint preserves recent work, including known release blockers below. Phase 2 must implement and verify these gates before promoting the new policy. No unlimited sweep is authorized by this plan.

## Contract and reproducibility

The active target is Bedrock 26.52, pinned model MC_26_50 and backend commit 294c72ab0392dd818a91d293dbd5774d4874d64b. Predictor starts, sampled biomes, website markers and actual BDS evidence are distinct. Fixed Overworld square is half-open [-1024,1024)²; Nether is [-512,512)². Origin is the evaluation center, never a fabricated Stronghold location.

The new policy revision is `origin-fixed-2048-two-group-v2`, provided by `two_group_blueprint_config()` and `config/realm.yaml`. Historical `origin-fixed-2048-v1` and its helper remain reproducible. Phase 2 must select the new helper as CLI default, bind its defaults everywhere, and refuse older native ABIs. Both native and Python entry points explicitly refuse v2 until Phase 2 replaces the guards with verified hard-floor enforcement. Config acceptance is not enforcement.

| Category | Ideal | Fatal floor | Budget |
|---|---:|---:|---|
| Stronghold, Jungle Temple, Desert Pyramid, Outpost | 1 each | 1 each | Strict; never spend B |
| Mansion | 1 | 0 | One category if below ideal |
| Trial Chambers | 10 | 8 | One category if below ideal |
| Villages | 7 | 5 | One category if below ideal |
| Ruined Portals | 7 | 5 | One category if below ideal |
| Mineshafts | 20 | 17 | One category if below ideal |
| Ancient Cities | 2 | 1 | One category if below ideal |
| Fortresses | 2 | 1 | One category if below ideal |
| Bastions | 3 | 2 | One category if below ideal |
| Monuments / Shipwrecks | 1 / 3 | Stage 3 | Deferred; never spend B |

B defaults to 2 and counts **deficit categories**, independently of fatal floors. Missing two Chambers is one category; a below-floor category rejects even with unused B. All required biome families remain mandatory: the old native `structure misses + missing biome families` formula must not apply to v2. At most eight flexible categories exist. Custom API ideals must remain >= fixed floors; strict categories and the fixed footprint cannot be relaxed accidentally. Persist the exact resolved config and budget in each run identity.

Bonuses: first and second Mansion +50 each; second Stronghold +50; qualifying ravine within <=200 blocks of documented hub +35; river highway +35; third/fourth City +25 each; third/fourth Fortress +20 each; Bastions >=4 +20 each; second coastal Monument +25; Chambers >10 +10 each; Villages >7 and Portals >7 +5 each; Mineshafts >20 +1 each; Cherry/Badlands/Mushroom families +15 each. Deferred terrain bonuses require evidence, not generated illustrations. Keep any additional historical bonuses versioned rather than silently applying them to v2.

Baseline survivors pass Stages 1 and 2 under this policy, including permitted target deficits. Persist those rows and tasks before Stage 3. Missing ocean/marine evidence gives PENDING/NEAR_MATCH downstream and must not erase or revoke baseline survival. Record deficit categories separately from fatal reasons, biome failure, marine status, and actual-generation verification.

## W0 — Audit, repair and baseline freeze

Completed in Phase 1:

- Inspected dirty tree before editing; preserved recent origin geometry, native, terrain, UI and blueprint work. No reset or generated-output cleanup.
- Fixed `runner.process_tree_resources`: OS inspection errors return `available: False`; SELF peak RSS never substitutes for live process-tree accounting. `tests/test_pipeline_review.py`: 5/5 passed.
- Added versioned config targets, explicit hard floors including strict categories, default B=2, schema validation and historical revision tests.
- Frozen initial status/diff, source hashes, historical config/result/build identity under `runs/pre-sweep-audit-2026-10-13/`. Local bulky evidence stays out of the source commit. Small `identity.json` hashes initial working source, not the eventual final source.
- Detected Intel Xeon W-2191B, 18 physical / 36 logical CPUs; macOS x86_64; Apple Clang 17.0.0. Private native builder already uses `-O3 -std=c11 -fwrapv` and work chunk 16. Read its saved identity for exact OpenMP runtime/hash. Preserve historical extension and runtime.

Historical origin result: 41,854 checkpointed inputs/sec, 21,735/sec including CLI startup; 30,000 distinct inputs repeated three times, no natural retained origin candidate. The claimed 44,972/sec lacks matched raw evidence in this audit. Neither is comparable to v2's stricter counts/floors. The new **same-policy control** must be frozen only after semantic repairs and before optimization. Record source/config/extension/runtime/compiler/linker hashes, exact commands, cohort interval/key, threads, batch/chunk, environment, wall time, counts and memory. Do not compare a v1 control to v2 as a speedup.

### Release-blocking audit findings and owners

| Location | Finding | Required fix / acceptance |
|---|---|---|
| `native/blueprint_batch.h`, `.inc`, `native_batch.py` | Only target-miss bits; strict temples/outpost can spend B; no fatal floors; outpost goal hardcoded 2; missing biomes consume B | Add versioned ABI fields for goals/floors/flexible mask; floor exit in Nether and OW; strict Stronghold retained; all-biome requirement; adapter refuses stale ABI |
| `blueprint.py`, `native_records.py`, adapter replay | Python short-circuits on any miss; retained deficits become PENDING; old score constants diverge | Shared explicit v2 classification; native/direct/replay/Python parity and complete inventories; qualification distinguishes valid baseline from unresolved downstream |
| `blueprint.py`, native score, `marine.py`, `reports.py` | First Mansion/excess bonuses missing; deferred recomputation can drop evidence | Versioned score parity at every boundary; retain terrain/biome provenance; bonus boundary tests |
| `server.py` start + `App.tsx` | Counts not bound; defaults B=1/batch16384/thread32; no resolved config passed; malformed input defaults into a sweep | Validate object/schema/types/ranges, immutable per-run YAML, exact CLI args, reject unsupported fields, return effective config; frontend sends counts/B/threads |
| `server.py` lifecycle | stderr only read after waiting can deadlock; second-resolution run IDs collide; stopped old thread can mutate new run; final count invented on zero | Drain both streams, unique run directories, per-run generation state, measured SQLite counts only, stop/restart/concurrency tests |
| `server.py` HTTP | Wildcard CORS, all-interface binding, unbounded body, weak type validation | Default loopback; restrict allowed local origins; bound JSON and reject invalid requests before filesystem/process effects; preserve explicit remote-use option only if intended |
| `server.py` candidate serialization | Hash-invented spawn, fixed terrain metrics/biomes, fabricated carvers/caves; BDS verified from score>=90; zero score replaced with 65 | Real persisted evidence only. Unknown/null/PENDING otherwise. Never derive verification from score. Keep demo visuals explicit and separate |
| `server.py` telemetry / UI | SELF RSS labeled as memory, fixed threads/CPU/rate, native service time confused with throughput, live/demo mixing | Actual process-tree memory or unavailable; configured threads; detected host; durable count/time denominator labeled; empty live results remain empty |
| `probability.ts` and funnel labels | Marginals/independence and binomial expansion presented as calibrated world odds; not established joint B=2 distribution | Label heuristic assumptions and cohort/policy; correct category B semantics; no implied probability guarantee or discovery ETA certification |
| `surface.py`, verification, recovery, exports | Legacy field `stronghold` doubles as origin center | Use explicit evaluation center and actual structure arrays; audit every fallback so absent Stronghold never exports as (0,0); keep historical replay |
| `marine.py`, store/tasks | Deferred failure must preserve baseline survivor and task evidence | Persistence/restart tests for no ocean, zero marine, partial verification, task failure, resume and re-score |
| `server.py`, reports | Wrong hardcoded `b1.21` Chunkbase URL; unsupported proof | Validate current link/version with live official page; unsupported mapping requires manual version selection, never silent substitution |
| `native/blueprint_profile.inc` hook | Stronghold profiling recorded before delayed query | Account delayed query; record conditional entered/pass/fail and profiler overhead |

Phase 1 is an audited preservation checkpoint, not certification of all preexisting changes. Generated CFFI sources and run artifacts are not evidence of source correctness.

## W1 — Compiler experiments

After correctness-first v2 baseline: extend `scripts/build_blueprint_batch.py` with opt-in CPU/LTO/PGO options and complete identity. Compare portable O3 control, `-march=native`, LTO, native+LTO; do not claim O3 as new optimization since already enabled. Keep floating-point semantics, prohibit fast-math. Test PGO train/use once on separate <=50k training input plus bounded positive fixtures; stale profiles rejected. Unsupported compiler/runtime combinations are recorded failures, not silent fallback.

Every candidate build must load pinned OpenMP and pass exact decisions/inventory/score parity before timing. Report build time separately. Compiler behavior/dependencies should be checked from local tooling and official documentation when needed. Keep portable fallback. Adopt only measured stable improvement; 50,000/sec is aspirational.

## W2 — Hot path and scheduling

1. Implement fatal-floor early exits and v2 native/Python classification first. Tests cover ideal, exact floor, floor-1 for every flexible category; strict category absence at B=0/2/8; exactly 0/1/2/3 deficits; biome absence; marine deferral. Retain complete final counts for bonuses; do not use capped floor witnesses as complete inventories.
2. Repair profiling and measure C screening versus startup/packing/allocation/extraction/receipts/SQLite/monitor/shutdown. Avoid adding overlapping service times. Profile total across both phases <=20 minutes, target 15; record actual seconds and stop at cap. Phase 1 has spent zero profiling budget.
3. Bounded adaptive matrix: threads 16/24/30/32/34 at 4096 batch; best two with 8192/16384; winner with chunks 16/64/128. Deduplicate settings and honor host capacity/reserved CPUs. Each tuning trial <=50,000 input seeds. Use short initial trials where adequate; three repeats only for credible finalists. Do not blindly exhaust a Cartesian product.
4. Inspect worker scratch ownership and measure reusable buffers/zero-reject allocations, generator reuse/cache reset, shared allocation bookkeeping, seed packing, queue pressure. Implement one measured bottleneck at a time. Reject or defer with empirical evidence when cost cannot support useful improvement. Same for filter order, Stronghold placement, Mineshaft/palette and serialization work. Preserve exact supported searches, late witnesses and concurrent-call isolation.
5. Maintain optimization ledger: hypothesis, source patch/build identity, cohort/config, raw measurements, parity, measured adoption/rejection and reason. Each identified optimization requires measured disposition. A blanket claim that all CPU optimizations are exhausted is not defensible beyond this identified bounded matrix.

## W3 — Downstream spawn and marine evidence

Keep spawn out of baseline C screen. Inspect pinned BDS provider for world-spawn metadata versus actual initial-player placement. `getSpawn` predicts x/z and has unvalidated recall; never call it actual Bedrock spawn or reject authoritatively on it. Persist evidence kind/version/coordinates and measured elevation Y>=63, non-ocean biome, dry solid support and headroom as separate predicates. Unknown remains PENDING. Proposed radius <=100 around origin requires explicit policy identity and squared distance boundary tests; do not introduce stricter unseen gates merely to claim readiness.

River/ravine hub must be explicit and carry provenance. Moving hub to supported spawn never recenters the fixed squares. Ravine <=200 and river radius <=250 checks need supported feature geometry; frontend procedural graphics cannot establish these bonuses. Bounded BDS budget only; no mass per-survivor verifier launch. Persist baseline before marine evaluation, and keep it after downstream near-match or unknown results. Exercise resume and transactional score/task updates. If actual evidence is unavailable, expose that limitation and certify only predictor sweep readiness, not a fully spawn-verified world.

## W4 — Candidate delivery and live UI

Exports retain signed seed strings and every observed structure start, dimension and evidence status. Include clean x/z, measured y only when known, horizontal distance with units and explicit hub/provenance. Nether block distances stay distinct; no claim of measured travel route. Export baseline/marine/spawn/actual-generation statuses independently and exact policy identity. Chunkbase is a review link only; live-verify share syntax/version before adopting it.

Keep new canyon/cave rendering and UI controls as visualization features, but real candidates use measured evidence or no feature. Demo mode must be visibly labeled and may not leak into live counters/leaderboard. Remove unsupported BDS proof, terrain numbers, hash-spawn, fixed throughput and estimated probability claims. Add API request/CLI-binding tests and response evidence tests, including score 0, high-bit/negative seeds, absent spawn/Stronghold, no candidates, process errors and restart races. Build and lint frontend; Node is available at `/Users/lucasraicu/.nvm/versions/node/v20.20.2/bin`; prefix PATH for frontend checks. Phase 1 production build passed; lint exits 0 with five existing hook/purity/state warnings in App, FilterSidebar and MapCanvas, to resolve during Phase 2 live UI cleanup.

## W5 — Certification battery

- Use `PYTHONPATH=. .venv/bin/python` and `PYTHONPATH=. .venv/bin/pytest`. Run focused checks during changes, complete `tests/` once final semantics stabilize. Test portable/OpenMP, ownership/cancellation, concurrent calls, allocation limits and available sanitizer checks. Run frontend production build and appropriate API/UI checks.
- Compare Python/native/direct/replay outcomes, counts, complete inventories, scores and ordered verdicts on independent natural inputs plus dense synthetic positives. Include every floor/bonus boundary, deficit-budget separation, high-bit seeds, late witnesses and historical policies. Different batch partitions use ordered input verdicts, not differently partitioned receipt hashes.
- Exercise crash around commit, retry/recovery, resume without duplicate coverage, immutable identity mismatch, unavailable monitor, disk limits, dense retention, database/WAL footprint and `PRAGMA integrity_check`. Memory ceiling includes children and BDS reserve.
- Final performance: **five counterbalanced control/selected pairs**, each invocation **100,000 inputs**, untouched held-out index interval, same v2 policy and cohort for both arms. Do not tune on this cohort. Record raw external CLI and checkpointed rates, medians/ranges, paired ratios/uncertainty, stage timings, tree RSS/buffer peaks and bytes. Positive fixture service separately; all-reject speed cannot certify candidate handling.
- Adopt only correct, stable measured improvements; target >=5% median complete-CLI improvement with paired 95% bootstrap interval >1 where supported. Inconclusive results retain control. Report any new hard-floor semantic savings separately from same-policy optimization. Do not expand tuning or profiling caps to chase 50k/sec.

## Delivery and acceptance

Deliver tested source, rebuilt private extension identity, updated policy/docs, optimization ledger/raw results, final test totals, five-pair report, reproducible finite sweep command, and candid spawn/provider limitation. The command must specify source/config/build identities, finite range/key, B=2, compact survivor retention, resource limits and downstream budget; leave the large sweep unstarted. State which readiness level was actually verified. If any mandatory correctness gate fails, continue fixes; do not mark complete based solely on throughput or UI appearance.
