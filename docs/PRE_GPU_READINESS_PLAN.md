# Readiness plan before GPU or storage-engine conversion

**Status: execution approved and completed for A–D, GPU contract only and database
comparison, October 22, 2026.** The original audit proposal is retained below.
See the [execution report](../reviews/pre-gpu-implementation-2026-10-22/REPORT.md),
[GPU contract](gpu/GPU_CONTRACT_V1.md) and [database decision](catalog/DATABASE_COMPARISON.md).
No GPU kernel, live restart/adoption or engine migration was performed. Device
confirmation and a bounded kernel implementation plan remain future gates.

## 1. What is already finished

The personal CPU engine, local four-pillar catalog, expandable biome filters,
per-objective 2K reserves, both predicted structure variants, safe document
organization, current benchmarking and cost profiling are implemented or completed.
There is no need to repeat those feature projects before GPU work.

Current catalog: 222 worlds, 109,918 memberships, 7,543 objectives and capacity for
115,964 primary / 231,928 total membership slots. Membership capacity is not a
unique-world count and does not bound all historical storage. The current snapshot
contains 93 feature entries: 19 structures and 74 biome entries. The latter include
56 exact Overworld biomes, five Nether biomes, four groups and nine legacy
Overworld aliases. Availability does not imply exhaustive coverage or game
certification. Historical snapshots retain their original capabilities.

| Current measurement | Evidence |
|---|---|
| Personal scan with active catalog work | About 69,100 input seeds/sec; paired control about 75,700/sec |
| Full current public record | About 32–35 seconds per existing-world replay |
| Record stages in the latest probe | 22.52s extraction/checkpoints; 5.74s summaries; 0.23s extra heights; 1.44s publication |
| Generic result-cache miss | 2.25–4.59s on 222 worlds; immediate hits 0.07–0.10s |
| Precomputed board page | About 3.25s; a narrow SQLite lookup prototype took about 0.48ms, excluding complete API guards |
| Storage | Current reachable CAS 241MB; all automation CAS 1,036MB; SQLite harvest state 111.8MB |

Sources: [benchmark](../reviews/current-framework-benchmark-2026-10-22/REPORT.md),
[profiling](../reviews/storage-query-profile-2026-10-22/REPORT.md), and the
[readiness audit](../reviews/pre-gpu-readiness-2026-10-22/AUDIT_MATRIX.md).

Fresh audit checks: 638 catalog tests collect; 26 focused reserve, native-guard,
finalization and cache-integrity tests pass; legacy contracts validate; current
source/build/state matches the 208-file profiling baseline. These checks do not
constitute a new full-suite pass. Earlier regression evidence remains available.
The explicit fork regression emits Python's known multithreaded-fork warning.

The remaining work has two tracks:

- **CPU/catalog integration:** A → B and C in parallel → D.
- **GPU exploration:** A → E specification and hardware confirmation → a separately
  approved isolated one-device proof. This need not wait for serving package C.
- **Fleet ingestion:** requires D and the GPU proof together before connecting a
  faster candidate emitter to production intake.
- **Storage-engine decision F:** conditional, before any engine replacement;
  it is not a prerequisite to an isolated GPU proof.

## 2. A — Freeze a reproducible CPU reference

**Priority:** first. **Complexity:** small/medium. **Owner:** Codex.

1. Create a restorable source snapshot containing relevant dirty/untracked source,
   tests, configuration, dependency locks, native build inputs/flags, binary/libomp
   digests and current data/schema/registry/policy/profile IDs. Verify restoration
   and import/smoke checks in a fresh isolated destination. Do not reset, stash,
   clean, commit, push or manufacture a clean working tree.
2. Freeze golden requests, complete ordered results and deterministic CPU fixtures.
   Reuse the 222 saved observations, portable game controls, nonempty positives,
   public-useful/personal-failing worlds and generated boundary cases.
3. Separate fixed-work numerical parity from wall-clock-limited behavior. Profiling
   changed one bounded 8192 search's work count; the fixed-observation derivation
   replay produced exactly the same snapshot. Do not require identical completion
   metadata when different amounts of work were allowed to finish, or silently
   promote partial results to complete.
4. Reconcile active documentation with live state. Conservative checked-in registry
   templates and historical reports remain intact. Preserve old audit findings and
   link their fixes; do not reclassify an old-baseline finding as a current defect
   without reproduction.
5. Confirm the intended GPU host/device, model, count, VRAM, OS, driver/toolchain and
   access. This iMac has an AMD Radeon Pro Vega 56 with 8GB VRAM; a future NVIDIA/CUDA
   target has not been verified. Mathematical contract drafting can proceed now.

**Acceptance:** an isolated restore works; source/build/data identities and golden
oracles are recorded; documentation distinguishes current, historical and proposed
behavior. No new seed search or game launch is needed.

## 3. B — Reduce checkpoint and derivation costs

**Priority:** highest measured ingestion opportunity. **Complexity:** medium.
Can proceed alongside C once A and shared interfaces are frozen.

Primary files: `src/seed_search/catalog/harvest_native.py`, `extract.py`,
`refinement_queue.py`, `refinement_worker.py`, `summaries.py`; shared protocol changes
in `ingestion.py`, `models.py` and `artifacts.py` remain coordinator-owned.

- Reduce repeated whole-observation JSON serialization, hashing, copying and
  validation where the same source-bound facts can be reused. The measured 814MB
  was serialized text, not measured physical disk writes. Record both separately.
- Evaluate smaller versioned progress records or fewer full rewrites. Define a
  concrete recovery quantum in the correct unit: biome-point batch, refinement
  tile, or seed batch. Bound unacknowledged recomputation in both work and time.
- Preserve all acknowledged observations/ranges, consumed budgets, leases,
  heartbeats, incremental durability and atomic commit rules. A corrupt delta must
  not silently roll back acknowledged work. Replay a verified valid prefix only
  when its full committed state can be reconstructed; otherwise fail closed and
  keep the job pending/error with evidence preserved.
- Retain old checkpoint readers or use an explicit versioned compatibility path in
  a new private workspace. Never overwrite active/resumable jobs or reset budgets.
- Preserve partial coverage and deadline behavior. Do not obtain speed by dropping
  heights, structures, refinement, scoring, fsync or validation requirements.

**Acceptance:** fixed-work facts, scores, witnesses and coverage match; targeted
crash/restart tests pass at changed boundaries; paired unprofiled replays show a
reduction beyond variability with no lost completeness or resource regression.
Do not infer a GPU speedup from Python profiler percentages.

## 4. C — Make guarded serving read views production-ready

**Priority:** highest measured serving opportunity. **Complexity:** medium/high.
This is a read-model change, not a database-engine replacement.

Primary files: `catalog/store.py`, `automation_query.py`, `service.py`, and a new
read-view module/tests. Keep the original `query.py` scorer initially. Shared
artifact/schema ownership stays with Codex; frozen V1/V2 JSON contracts stay intact.

1. Start with precomputed boards: snapshot-bound, objective-local ordered members
   or indexed SQLite read views. Keep primary/reserve counts, ranks and page order.
2. Add conservative typed candidate masks for flexible selection. Required rows
   must hold at the same anchor; alternatives within one row mean ANY. Missing
   biome/structure evidence stays pending. Broad queries need a correct fallback.
3. Bind every view to immutable snapshot, policy, registry, observation/profile and
   validator identities. A cursor must continue reading its original snapshot and
   matching view generation during concurrent publication. Preserve compatible old
   cursors; do not add an unnecessary mutable transaction-sequence contract.
4. Preserve existing corruption detection before warm-cache reuse, including bound
   page checks. Prototype timings omit some production checks. A different trust
   model requires explicit review; do not weaken guards to reproduce a microbenchmark.
5. Stage, fsync, checksum and validate views before atomic pointer publication.
   Missing, corrupt or stale views fail closed or use a verified existing fallback.
   Queries never launch extraction or index regeneration. Protect old shares/pins.
6. Keep existing 64MiB serialized cache allowance per worker. Bound SQLite page
   caches, typed buffers, memory mappings and temporary files explicitly; the
   prototype's fully predecoded RAM representation is not permission for an
   unbounded production cache.

**Acceptance:** complete ordered outputs match for all 36 products / 72 views and
an adversarial query matrix, including witnesses, pending results and exact ties.
Wrong-view/expired cursors, stale bindings, corruption of bound pages, concurrent
publication, worker loss, restart and rollback pass. Rebenchmark complete API
requests with all guards and response serialization.

An illustrative goal is a median ≤250ms for primary/reserve first pages on the
222-world snapshot with verified context primed, filesystem cache warm and result
payload uncached. It must be accepted as part of the implementation plan, tested
through the full API, and never advertised as a production p95/SLA. The existing
10s request allowance remains fixed. Generic selective requests should improve;
broad requests must not regress materially under matched conditions.

## 5. D — Prove integration, recovery and sustained CPU behavior

**Priority:** before connecting GPU output at scale. **Complexity:** medium.
Depends on changed B/C components; does not block an isolated mathematical GPU proof.

- Reuse existing reserve tests and add only gaps exposed by changes. Exercise a
  full 100-candidate capacity, cutoff propagation, ties, deduplication, SQLite
  persistence, reserve promotion, restart and historical 50-capacity compatibility.
  Compare pruned results with independent unpruned full sorting. Clearly distinguish
  synthetic/replay stress from natural full-heap performance.
- Test 7,543-objective 2K mechanics using labeled oversubscribed/lower-cap fixtures.
  Report actual discard fractions. An all-worlds-retained cohort cannot establish
  retention quality. Large real default-cap held-out recall is a later catalog
  quality gate, not a requirement to generate tens of thousands of CPU worlds
  before a GPU prototype.
- Use all compatible saved facts for correctness replay, including stratified
  sparse/dense, boundary, spawn, variant and height cases. The ≤5-world extraction
  performance probe is separate; it is not population-wide correctness coverage.
- Run bounded sustained screening with/without actual public extraction and queries.
  Capture real overlap, CPU/RSS, available thermal diagnostics, durable coverage,
  queue growth, backpressure and failure behavior. Report raw input seeds/sec,
  selected candidates/sec, completed observations/sec and retained useful worlds/hr
  separately. Prove a faster emitter cannot force unbounded intake or stricter
  undocumented filtering on a slower host.
- Exercise slow/failed workers, kills around commits/pointer swaps, disk/output
  exhaustion, malformed/corrupt artifacts, budget exhaustion/resume and restoration
  from a copied source/catalog checkpoint. No acknowledged work or budget may be
  lost. Pins, reserves, historical shares and verification-in-progress remain roots.
- Run focused checks during development. Once integrated, run the full current
  catalog suite, affected personal/native parity suites, Node contracts and frontend
  build. Reuse unchanged evidence; repeat only after changes or unresolved failures.
  Interactive browser QA remains waived under the existing instruction.

**Acceptance:** no introduced correctness failures; restore/recovery demonstrated;
fixed-work parity and resource gates pass; sustained rates and backpressure are
reported with their limits. Personal restart/adoption remains a separate approval.

## 6. E — Define GPU mathematics and run one isolated device proof

**Priority:** specification can start alongside B/C after A. **Complexity:** medium
for the contract; high for an actual port, which is a separate implementation plan.

- Bifurcate personal and public admission before personal floors/cutoff. For every
  seed selected into the declared public evaluated population, a shared GPU stage
  must not remove a possible public winner because it fails personal requirements.
  Keep independent public sampling before that filter, or bypass it for the public
  branch. Optional public pruning requires a conservative proof that no remaining
  targeted objective/anchor/dimension can improve; missing data cannot prove failure.
  This invariant does not claim to evaluate every seed outside the declared sample.
- Freeze signed 64-bit seed identity and modulo arithmetic, PRNG behavior, placement
  and viability, negative coordinates, floor-divide-by-eight, half-open borders,
  near-base circles, provider/height/dimension semantics and same-anchor scoring.
  Factual counts must not be clipped to UI threshold limits.
- Preserve 845/265/140 scoring, Overworld sides 2048/4096/8192, fixed Nether 1024,
  effective 2K capacity throughout pruning, partial stronghold coverage and sparse
  biome unknowns. Preserve exact distances, witnesses, ordering and distinct worlds.
- Define canonical batched input/output and checkpoint progress with versioned
  source/build identities, completeness, errors and witness references. Measure
  compaction, transfer and scheduling rather than assuming PCIe cost is negligible.
- First isolate and time candidate native C/CFFI kernels without whole-Python
  profiling. Choose one small kernel, one confirmed device and a fixed-work oracle.
  Keep CPU fallback. Test exact parity where claimed and end-to-end useful outputs;
  predictor parity is not universal game verification.

**Gate for one-device prototype:** A, confirmed hardware, reviewed numerical/admission
contract, and an approved bounded kernel plan. C/D need not be finished for a device
proof that cannot feed live intake. B/C/D and measured GPU acceptance must pass
before high-volume integration or 2/4/8-device/fleet claims.

The superseded [GPU architecture](specs/DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md)
is historical context. Its shared personal gate, free harvesting, 64-byte record,
100M-seeds/sec and fixed fleet assumptions are not accepted implementation contracts.

## 7. F — Decide whether a different engine is needed

**Priority:** conditional; before engine replacement, not before GPU exploration.
**Complexity:** medium comparative benchmark if a remaining target requires it.

Keep SQLite for queues, leases, receipts and metadata unless measured coordination
or writer constraints establish a different need. Use C's guarded read model for
boards. A custom serving schema does not require a custom database engine.

If decode/scanning still dominates flexible queries, compare standard typed,
immutable serving blocks, such as Arrow IPC/mmap, and an analytical engine such as
DuckDB over suitable columnar data. No such engine was benchmarked or selected.
A small layout experiment may test semantics and decode cost; it cannot select a
fleet engine. Writer contention is not the only possible trigger: broad CPU scans,
RAM pressure, startup, publication cost and history growth also matter.

Before a large engine comparison, declare actual target worlds, memberships,
history policy, useful ingestion rate, reader/writer concurrency, latency target,
hardware and storage budget. Use increasing labeled synthetic replicas and real
cohorts, distinguishing them, and report warm-cache versus genuinely out-of-memory
or cold-storage behavior. There is no universal “10,000 worlds exceeds RAM” threshold.

Compare identical facts, queries, exact ranking/unknown semantics, full API costs,
index build/update, integrity, crash recovery, staged/WAL disk peaks and rollback.
A hand-written `.seedcat` engine or key-value migration is justified only if simpler
standard options fail a concrete target and the maintenance cost is worthwhile.
“No new engine needed” is an acceptable outcome.

## 8. Ownership, resources and approval boundary

Suggested coding decomposition, after approval:

| Owner | Work | Ownership |
|---|---|---|
| Codex | Baseline, contracts, integration, acceptance and activation proposal | Shared schema/artifact interfaces, handoff and reports; review every patch |
| Gemini High worker 1 | B and its focused tests | Assigned harvest/refinement/summary files |
| Gemini High worker 2 | C and its focused tests | Assigned store/service/query-adapter files |
| Independent Gemini High review | Source and acceptance critique | Read-only |

Use only useful concurrency in isolated snapshots; shared files have one owner.
B/C agree on interfaces before parallel coding. Codex independently validates
changes and resolves source/worker disagreements.

Proposed acceptance envelope, to review before execution: ≤5 complete existing-world
extractions per paired cost comparison, ≤120s/world and ≤600s cumulative extraction;
use saved observations for broader correctness coverage. Bound screening/load trials
at 5–10 minutes in private roots. Maximum aggregate owned RSS 4GiB; maximum **3GiB
new logical disk including input copy, staging, indexes, WAL, temporary files and
reports**. Keep query/cache/IPC limits. Larger scale experiments need their own
resource plan. Do not recycle previous spent allocations or silently expand caps.

Final checks are budgeted from the prior approximately five-minute catalog suite
plus affected tests/build. Worker tasks have explicit ≤15-minute limits and bounded
retries. No new BDS, large seed campaign, personal restart, live migration, engine
installation, deletion, automatic commit/merge/push or permission bypass is included.
This document is a proposal, not implementation approval.

## 9. Separate work and transition checklist

Public hosting, accounts/payments, launch security/ownership/limits, certified final
seeds, real-world retention quality and deployment operations are separate tracks.
They are required for their advertised launch claims, not for an isolated GPU parity
experiment. Stronghold recall, terrain/landing/safety and exhaustive absence remain
explicitly limited; changing the predictor needs a separate proposal. Safe repository
organization is complete; further physical source/test moves are not prerequisites.

**Before isolated GPU work:**

- [ ] A: restorable reference, source/build identities and fixed-work oracle.
- [ ] E: confirmed device/host and approved independent-admission/numerical contract.
- [ ] A bounded one-device plan with measured transfer/output and parity acceptance.

**Before connecting GPU output at scale:**

- [ ] B: checkpoint/derivation improvement with durable recovery and preserved facts.
- [ ] C: guarded read views with complete API/cursor/integrity/rollback parity.
- [ ] D: capacity, retention mechanics, sustained load and backpressure checks.
- [ ] One-device GPU correctness and useful-record throughput gates passed.

**Before replacing an engine:**

- [ ] F: target workload and comparative read/write/recovery decision documented.

The original checklist above records transition requirements; see the execution
report for completed A–D evidence. GPU device/prototype/adoption boxes remain open
because the execution instruction explicitly requested the contract only. Two independent
High critiques and their reconciliations are recorded in the
[review evidence](../reviews/pre-gpu-readiness-2026-10-22/RECONCILIATION.md).
