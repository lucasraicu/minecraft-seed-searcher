# Master Five-Model Audit — Gemini Implementation Brief

| Item | Contract |
|---|---|
| Status | Workstreams A/B implemented. Current acceptance and remaining-finding remediation are tracked in the [2026-10-15 implementation/verification ledger](remaining-fixes-2026-10-15/IMPLEMENTATION.md), with the subsequent [UI-to-machine parity verification](ui-machine-parity-2026-10-15/IMPLEMENTATION.md). Benchmark claims retain their recorded build/cohort scope. |
| Project | `minecraft-seed-searcher` |
| Historical audit baseline | Commit `54b7d631b8bdb481894980a31be16aaa02901b18`, policy `dynamic-envelope-1664-v1` |
| New policy | `dynamic-envelope-1664-v2` |
| Predictor pin | Cubiomes `MC_26_50`; historical BDS reference `1.26.52.3`. Preserve repository pins; no world-generation dependency upgrade. |

> **Gemini: implement this brief, not another proposal.** Complete Section 7's audit remediation first, then Section 8's player/scoring revision under Section 9's speed and accuracy requirements. Section 0 governs delegation and delivery. Sections 1–6 summarize historical evidence and adoption candidates; they are not a second set of patch instructions. Section 8 is the sole source of new gameplay numbers. Verify the integrated result before declaring completion.

## Contents

- [0. Gemini execution and verification contract](#0-gemini-execution-and-verification-contract)
- [1. What the audit established](#1-what-the-audit-established)
- [2. Findings and dispositions](#2-findings-and-dispositions)
- [3. Architecture to retain](#3-architecture-to-retain)
- [4. Historical performance evidence](#4-historical-performance-evidence)
- [5. Source evidence and patch references](#5-source-evidence-and-patch-references)
- [6. Readiness and acceptance](#6-readiness-and-acceptance)
- [7. Audit remediation](#7-implementation-plan--audit-remediation-first)
- [8. Player improvements and scoring](#8-implementation-plan--agreed-player-improvements-and-scoring-revision)
- [9. Speed and accuracy](#9-player-policy-implementation--speed-and-accuracy-requirements)

---

## 0. Gemini execution and verification contract

### 0.1 Authority, scope, and working rules

1. Read repository `AGENTS.md` instructions, this entire brief, and the relevant source before editing. Work from the current checkout; record its identity and existing dirty changes. The historical audit commit is evidence, not an instruction to reset the repository. Preserve unrelated user work and historical run artifacts.
2. Implement both workstreams, including tests, native build integration, storage, CLI/UI, README, and `MASTER_SEED_BLUEPRINT.md`. Maintain separate audit-remediation and policy-change commits and completion reports. Do not publish, deploy, launch an unbounded search, or perform actual BDS world generation as part of this task.
3. Use the exact Section 8 contract. Existing code establishes integration details and historical behavior; obsolete code, old README examples, and earlier audit proposals do not override the new policy. A repeated table or comment must not become a competing source of truth.
4. Resolve routine implementation choices from inspected code and focused probes. Do not invent missing APIs, file paths, biome IDs, benchmark results, or completed tests. If a fact is unverified, label it and investigate the smallest relevant case. Ask the user only if an unresolved decision would change agreed gameplay or authorized scope; continue independent work meanwhile.
5. Keep C11/OpenMP, bulk CFFI, bounded batches, and SQLite WAL/FULL. Extend existing helpers, tests, and report structures. Do not add a generic plugin framework, new service, rewrite, speculative index/cache hierarchy, or dependency merely to implement these bounded features.
6. No automatic terrain/coastal screening, BDS launches, block generation, or inspection work for v2. Required fixed-Y biome prediction remains. A correctly implemented predictor is still predictive evidence, not certification of a generated world.
7. Use `dynamic-envelope-1664-v2` consistently as the policy/score revision. Preserve v1 interpretation and saved identities. Do not change historical behavior globally to make v2 tests pass.

### 0.2 Gemini subagent assignments

Use one coordinating Gemini agent and multiple focused Gemini subagents. Use the roles below across waves; reuse slots as agents finish. Respect the available concurrency limit. More simultaneous writers do not help when they edit the same files. If subagent tooling is unavailable, report that limitation and execute these assignments sequentially; never claim that independent agent review occurred.

| Role | Assignment | Ownership and handoff |
|---|---|---|
| Coordinator | A0, B1, integration, ownership ledger, final release decision | Own the contract/configuration and integration branch. Assign exact files and tests before each wave; resolve shared-file conflicts. |
| Audit oracle agent | A1 | Own post-snap Python recount and its regression tests; hand back before B2 edits those files. |
| Native reliability agent | A2 | Own native allocation accounting/failure recovery; hand back before native policy work. |
| Pipeline agent | A3–A4 | Own batch ownership, web lock/cache, SQLite lifetime fixes; serialize edits with later storage/UI agents. |
| Python reference agent | B2, Python side of B4 | Own independent v2 scoring/selection and boundary fixtures after the B1 contract is frozen. |
| Native policy agent | B3, native side of B4 | Own native score helper, ABI, caches, variant evidence, and matching adapter changes. Coordinate interface changes with the coordinator before editing. |
| Persistence/workflow agent | B5–B6 | Own ranking, rescore, storage, exports, and removal of active v2 terrain work after the evidence interface is frozen. |
| Player UI/docs agent | B7–B8 documentation | Own report presentation, pagination/comparison UI, README and blueprint. Wait for API/schema handoff; shared report/server files have one owner at a time. |
| Verification agent | Independent acceptance review and integration tests | Read integrated code; independently derive expected outcomes from Section 8, run checks, and challenge missing evidence. Do not rubber-stamp author summaries. Return defects to the owner. |
| Performance agent | A5 evaluation and Section 9.6 measurements | Own isolated benchmark artifacts. Vendor/source edits need explicit file ownership and occur separately from correctness/policy edits. Reuse existing tools. |

Only the coordinator delegates work; subagents must not recursively spawn overlapping assignments.

Each assignment receives: relevant section/package IDs, exact writable files, read-only dependencies, frozen interface, required checks, and excluded scope. Each agent returns: changed paths, implemented behavior, commands and exit statuses, evidence paths, and unresolved items. One concise handoff per assignment is sufficient; do not create overlapping plans or repetitive reports.

**File ownership rule:** never let two agents edit the same file concurrently. Tests also need ownership. Use isolated worktrees when available, or serialize overlapping writes in a shared checkout. Only the coordinator integrates changes and records final commits. Build/test artifacts must use separate fresh directories. Do not run competing performance jobs on the same host.

### 0.3 Dependency waves and integration gates

| Wave | Parallel work permitted | Gate before dependent work |
|---|---|---|
| 1 — establish baseline | Coordinator inspects current state; verifier inspects existing evidence/tests | A0 records source/build/config identity, open findings, file ownership, and bounded validation inputs. No broad re-audit. |
| 2 — repair v1 | Audit oracle, native reliability, pipeline agents on disjoint files | A1–A4 fixes and applicable reproductions pass; independent verifier checks the combined diff. Record the corrected v1 baseline and A6 report. |
| 3 — freeze v2 interface | Coordinator B1; Python/native agents review the contract | Freeze category parameters, revision dispatch, native ABI additions, component/evidence schema, and ranking keys. Put this in existing code/docs; no separate design framework. |
| 4 — implement scorer | Python reference and native agents implement separate paths; storage/UI agents may inspect and prepare against frozen interfaces | B2 arithmetic and independent selection cases pass before claiming native parity. B3–B4 agree on eligibility, centers, components, and witnesses. |
| 5 — connect consumers | Persistence/workflow and UI/docs agents on disjoint files; coordinator serializes shared files | B5–B8 use the same revision and score; historical compatibility and no-terrain scheduling checks pass. |
| 6 — verify integrated result | Verifier checks correctness; performance agent runs bounded measurements after competing jobs stop | Complete Sections 8.7 and 9.5–9.7, final frontend build/lint, applicable Python regressions, and fresh end-to-end validation. |

A5 micro-optimizations are evaluated in a separate branch/commit after the corrected baseline exists. Adopt only supported, parity-preserving changes with measured benefit. Deferral with a reason does not block v2. Update A6's corrected-baseline report with A5 adoption/deferral when evaluation finishes. If adopted, record the new baseline/build and use equivalent optimization settings in the v1/v2 policy comparison. Do not allow optional tuning to delay required correctness work indefinitely.

### 0.4 Evidence, efficient verification, and stopping rules

- For each repaired defect, retain a bounded reproducer or regression test that fails on the affected baseline and passes after repair. For each new behavior, cover the relevant Section 8.7 cases with meaningful assertions, preferably parameterized within existing suites. Source-text searches and matching totals alone are not behavioral proof.
- Independent reference selection must enumerate the specified representative candidates and compute expected outcomes from inventories/samples. It may share the named policy constants, but must not call the native scoring/selection implementation to manufacture expected results. Test constants against the explicit schedules, including the 719-point arithmetic ceiling.
- Verify native tests load the freshly built artifact. Record source/build/config identity and extension path/hash. A passing test against an old extension does not validate the patch. Regenerate source-matched PGO only for a build that uses PGO; portable correctness validation does not require a tuning campaign.
- Preserve historical audit artifacts. Inspect reproduction scripts before executing them: some embed machine-specific paths or overwrite their historical output. Port the bounded cases into existing tests or run adapted probes in a fresh artifact directory. Do not overwrite the audit evidence to produce a new “pass.”
- Run focused checks during implementation. At integration, run the relevant existing regression suites and the frontend checks once against the combined changes; rerun affected checks after a correction. A skipped native test, failed prerequisite, missing positive fixture, or unexecuted command is not a pass. Record unrelated pre-existing failures separately; unresolved failures affecting this contract block completion.
- For every benchmark/end-to-end job, record exact inputs or seed-generation parameters, input count, trial count, runtime limit, settings, output directory, and provenance before execution. Start from a bounded smoke run; use existing positive fixtures when natural survivors are absent. Do not expand the seed search until a natural survivor appears merely to finish verification. Respect existing CLI safety limits and scale gates.
- Benchmark only the comparisons in Section 9.6 and A5 candidates actually considered. Inspect script arguments and internal workload before use; a historical tuning script is not automatically a v2 test. No blanket retuning of thread counts, batch sizes, hardware, or languages.
- Stop when the required deliverables and acceptance checks pass. Do not add extra gameplay, generalized abstractions, redundant test frameworks, or another speculative audit. If a required check cannot be completed, state precisely what remains and do not claim readiness.

**Existing verification entry points** (run from the repository root; inspect prerequisites and adapt only where the implemented interface requires it):

```sh
.venv/bin/python -m seed_search doctor
.venv/bin/python scripts/build_blueprint_batch.py --output <fresh-build-directory>
.venv/bin/python -m pytest -q tests/test_dynamic_baseline.py tests/test_dynamic_integration.py
.venv/bin/python -m pytest -q tests/test_realm_leaderboard.py tests/test_realm_rescore_cli.py tests/test_realm_store.py
.venv/bin/python -m pytest -q tests/test_web_server_hardening.py tests/test_web_server_evidence.py
npm --prefix web-ui run build
npm --prefix web-ui run lint
```

Angle-bracket arguments are placeholders, not literal shell input. These are starting points, not an exhaustive checklist: include native allocation/retention/build tests, historical policy tests, and added regressions affected by the change. Private native builds default to serial; use an inspected, available OpenMP prefix for parallel validation. If packaged native extensions are used, rebuild through the repository's existing build workflow as well. Missing environment prerequisites must be reported, not bypassed with fabricated success.

**Final handoff:** provide two concise workstream reports (audit repair and player/scoring implementation), with commit/source/build/config identities; a package-to-evidence checklist for A0–A6 and B1–B8; commands, exit statuses and artifact paths; bounded end-to-end results; measured kernel/persistence performance; and any deferred optional optimizations. Include the fifteen improvements and old-policy compatibility in acceptance coverage. Update this brief's status only when supported by those results. Starting a production search is a separate action.

---

## 1. What the audit established

The historical review found **no verified P0** and **three reproduced P1 defects**. This is a bounded finding, not proof that the engine is bug-free. The [final review](split-audit-2026-10-15/codex/FINAL_REVIEW.md), [reproductions](split-audit-2026-10-15/codex/reproductions.json), and [claim dispositions](split-audit-2026-10-15/codex/dispositions.json) distinguish evidence from unsupported claims.

Preserve these geometry rules under both the remediation and new policy:

- Half-open Overworld bounds `[Cx-832,Cx+832) × [Cz-832,Cz+832)` and exact Nether bounds centered on `(Cx/8,Cz/8)` with half-width 416.
- Integer center event boundaries for an Overworld start at X: enter at `X-831`, leave at `X+833`. For a Nether start at Xn: enter at `8*Xn-3327`, leave at `8*Xn+3329`. Do not confuse the inclusive last center with the exclusive exit event.
- Existing world-aligned biome lattice events and constrained 16/8-block snapping. Mandatory membership and sampled palette membership are invariant inside the corresponding event cells; optional counts and proximity scores are not automatically invariant.
- Selection chooses among the defined representatives, not every possible world coordinate. Post-snap scoring restores that policy; it does not prove global spatial optimality.

Historical tests and experiments support specific cases and builds. Recheck applicable invariants after the change; do not describe test coverage as universal mathematical certification.

## 2. Findings and dispositions

Line numbers in old reports identify the audited baseline. Locate symbols in the current source before editing.

| Finding | Evidence/disposition | Required work |
|---|---|---|
| P1: Python optional counts before snapping | Boundary fixture selects a different center/score from native; independently reproduced | A1: recount optional structures at each final snapped center, then independently compare selection. |
| P1: dynamic allocations bypass reservation | A 1.4 MB cap admitted at least 1,872,336 live requested bytes in the recorded fixture | A2: route dynamic buffers through accounted ownership; state what the cap covers. This is not proof of a normal-path leak. |
| P1: failed growth publishes invalid capacity | Injected allocation failure causes a null dereference on later worker reuse | A2: allocate into temporaries and publish pointer/capacity only after success; retain safe prior state on failure. |
| P2: stale web candidate cache | `count(*)`/`max(rowid)` does not change when scores/evidence change | A3: invalidate correctly on updates, including unchanged row counts. |
| P2: blocked control requests | Waiting for a child while holding the manager lock delays status requests | A3: wait outside the lock and revalidate process ownership/generation. Do not claim an unmeasured HTTP failure rate. |
| P2: inflight over-reservation | Refill before release can own four batches with `inflight=3` | A3: release/commit before refilling, preserving the single-writer model. |
| SQLite connection lifetime | Connection context management controls transactions, not explicit closing; claimed multi-day `EMFILE` rate was not established | A4: close owned read connections and verify repeated polling/resource lifetime. |
| Independent-selection coverage gap | Replay at a native-selected center does not establish correct center choice | A1/B2–B4: include nonempty optional inventories and spatial boundary fixtures in independent selection checks. |
| Optional score inflation | A gameplay-policy decision, not a fourth reproduced P1 | B1–B4: apply only the capped Section 8 schedules under v2. |

Refuted or unsupported historical claims do not become new implementation tasks. In particular, the final review did not establish production double-counting from the unsupported lease interleaving, a normal-path dynamic-buffer leak, a measured GPU verdict, or unconditional end-to-end readiness. Reopen a claim only with relevant new evidence, not a subagent's assertion.

## 3. Architecture to retain

Keep C11/OpenMP and contiguous native arrays, worker-local generator/scratch state, bulk CFFI calls, Python orchestration, bounded ownership, and a single parent SQLite WAL/FULL writer. Preserve the native linear best-candidate reduction.

No measured benefit justifies a Rust rewrite, GPU port, handwritten SIMD redesign, new service, or durability reduction for this assignment. This is a scope decision, not a claim that alternatives can never be faster. CFFI releases the GIL for the bulk call, but inputs and retained records still involve copying/reconstruction. Measure per-survivor work separately; do not describe the entire pipeline as zero-copy or assume persistence is fully hidden by a background writer.

## 4. Historical performance evidence

These are **native-kernel-only**, source-matched PGO comparisons from the [Sol report](split-audit-2026-10-15/sol/REPORT.md) and [measurements](split-audit-2026-10-15/sol/measurements.json), as reviewed by Codex. They are not v2 or durable-pipeline throughput promises.

| Experiment | Control median, inputs/sec | Candidate median, inputs/sec | Recorded paired improvement |
|---|---:|---:|---:|
| Remove unused modern Mansion surface initialization | 46,208 | 147,568 | +218.82% |
| Combine removal with delayed seeding | 46,208 | 182,471 | +292.80% |
| Add necessary raw Dark Forest witness gate | 182,715 | 215,413 | +18.51% |

Each comparison used five alternating paired trials. The gate confirmation used a different cohort: do not divide across rows to invent a paired total speedup. The 2,000-component parity corpus included 134 viable Mansion seeds and relevant RNG interleavings; this is bounded evidence, not a universal parity guarantee. Retained-record cost and end-to-end throughput require separate current measurements.

## 5. Source evidence and patch references

Earlier inline diffs have been replaced with references to avoid shipping obsolete formulas and incomplete patches as executable instructions. Inspect source compatibility; do not blindly apply historical patches.

| Reference | Permitted use |
|---|---|
| [Codex final review](split-audit-2026-10-15/codex/FINAL_REVIEW.md) and [prior audit](codex-audit-2026-10-15/AUDIT.md) | Reproduced defect details and bounded regression cases for A1–A4. |
| [Claim dispositions](split-audit-2026-10-15/codex/dispositions.json) | Distinguish corroborated, refuted, unresolved, and out-of-scope claims. |
| [Combined initialization proposal](split-audit-2026-10-15/sol/proposals/lazy-no-surface-init.patch) | A5 candidate: unused modern Mansion surface initialization plus delayed seeding; preserve older branches and relevant RNG consumers. |
| [Incremental Dark Forest gate](split-audit-2026-10-15/sol/proposals/dark-gate-incremental.patch) | A5 candidate after the combined initialization change; retain complete inventories after a positive gate. |

**Superseded scoring:** the old “first hut +15, other first +10, then +3 each” proposal is withdrawn. Do not implement it under v1 or v2. Section 8 alone specifies v2 points.

**Empty inventory correction:** a successfully completed prediction with zero starts remains complete predicted evidence. Never infer `PARTIAL` from an empty list alone. Incomplete/error evidence must remain distinct from evaluated absence.

**SQLite correction:** explicit closing does not automatically reproduce transaction context-manager semantics. Preserve commit/rollback behavior where needed and close only connections owned by the call.

## 6. Readiness and acceptance

The audited baseline was **not unconditionally ready**: the three reproduced P1 defects remained. Audit completion and promising optimization results did not mean those repairs had shipped.

This document is ready to use as an implementation brief. The resulting system is ready only after the required Section 7–9 checks pass on the integrated source and matching build. Optional A5 deferrals are allowed; unresolved required correctness, evidence, compatibility, or workflow failures are not. Do not promote predictions to actual-world verification or replace measured results with model consensus.

---

## 7. Implementation Plan — Audit Remediation First

**Workstream A: repair the existing implementation without retuning gameplay.** Sections 7 and 8 require separate commits, validation, and completion reports. Section 8 changes the search policy only after the corrected baseline is established. Section 0 defines Gemini ownership and integration gates.

### 7.1 Evidence and precedence

- Use [Codex's final review](split-audit-2026-10-15/codex/FINAL_REVIEW.md), its [reproductions](split-audit-2026-10-15/codex/reproductions.json), and [claim dispositions](split-audit-2026-10-15/codex/dispositions.json) to establish which aggregated findings are reproduced. Check the implementation checkout before treating an old finding as still open.
- Historical model assertions and kernel timings are not acceptance criteria. A fix needs applicable source changes and passing verification. Use Section 5's references only within their stated scope.
- Scoring changes belong exclusively to Section 8 under v2. Do not apply withdrawn formulas while repairing v1.
- Preserve the distinction between evaluated absence and incomplete evidence: a complete empty predicted inventory is not `PARTIAL` simply because it has zero starts.
- Preserve the existing two-deficit policy, thresholds, bonus formulas, and representative-selection policy while validating audit remediation. The optional recount repair intentionally corrects Python selection where it previously disagreed with the native policy; do not require preservation of that known-wrong Python result.

### 7.2 Ordered audit work packages

| Order | Work package | Primary implementation locations | Required result |
|---|---|---|---|
| A0 | Freeze the implementation baseline and disposition list | Existing audit artifacts; current Git/source/build/config identities | Record commit, dirty changes if any, compiler/runtime, native build identity, and which findings remain reproducible. Use bounded probes, not a new broad audit. |
| A1 | Correct optional recount after snapping | `src/seed_search/realm/dynamic.py`, `blueprint.py`; dynamic tests | Recount optional starts using the final half-open Overworld bounds. Reproduce the documented swamp-hut boundary case and restore independent Python/native center and score agreement. |
| A2 | Repair allocation accounting and failed growth together | `native/blueprint_dynamic.inc`, allocation/cleanup helpers in the native batch implementation | Account for dynamic buffers according to the documented reservation contract. Allocate replacements into temporaries; publish pointers and capacities only after success. Preserve valid old buffers on failure and worker reuse. |
| A3 | Correct pipeline/control ownership defects | `src/seed_search/realm/native_batch.py`, `src/seed_search/web/server.py` | Release/commit an owned batch before refilling its slot; wait for processes outside the manager lock and revalidate process generation; invalidate candidate caches after score/evidence updates. |
| A4 | Reconcile SQLite connection ownership | Actual read-only connection sites in `src/seed_search/web/server.py` | Explicitly close owned read connections while retaining transaction behavior. Verify resource lifetime under repeated polling; do not infer a specific production failure rate from context-manager syntax alone. |
| A5 | Evaluate optional micro-optimizations separately | Pinned `vendor/cubiomes-bedrock` integration and native initialization paths; Section 5 proposals | Evaluate the unused modern Mansion surface initialization, delayed seeding, and necessary raw Dark Forest witness gate. Adopt only source-compatible changes with passing parity and measured benefit; otherwise record deferral. Preserve RNG interleavings and exact eligibility. Rebuild source-matched PGO where used. |
| A6 | Publish remediation result | Audit completion note and benchmark artifacts | List repaired findings, unresolved items, exact build identity, passing checks, and measured timings. Keep correctness and performance conclusions separate. |

**A2 verification:** repeat the existing tight-reservation and allocation-failure cases, including failure followed by another seed on the same worker. Confirm cleanup and error propagation. State which fixed/runtime allocations the memory limit covers; do not silently change the monotonic reservation contract.

**A3–A4 verification:** exercise inflight ownership, a slow-to-exit process while status is requested, score updates without row-count changes, and repeated short-lived SQLite reads. Use temporary databases and deterministic subprocess probes.

**A5 verification:** use the existing positive component corpus and relevant RNG call interleavings, not only all-reject receipts. Measure matched builds with repeated alternating trials. Do not promise the historical 215k/sec figure on another build or workload.

### 7.3 Boundary between the workstreams

Commit and identify the corrected baseline before changing policy. Correctness fixes must pass before the new policy is released. Optional performance experiments may be deferred without blocking the policy work once required correctness fixes pass; do not mix their effects into the player-policy performance comparison.

The engineering reliability item was removed from the **player-improvement list**, not from remediation of the existing audit. It is handled here once. Likewise, the Python/native recount repair below is a dependency already delivered by A1, not a duplicate implementation task.

---

## 8. Implementation Plan — Agreed Player Improvements and Scoring Revision

**Workstream B: implement `dynamic-envelope-1664-v2`.** This section is the authoritative player/eligibility/scoring contract. Retain the historical meaning of `dynamic-envelope-1664-v1` and older saved runs. Do not backport these gameplay changes into historical revisions.

### 8.1 Scope: the fifteen retained improvements

| # | Agreed improvement | Implementation outcome |
|---|---|---|
| 1 | Recommend a spawn candidate near the selected center | Reuse cached biome witnesses within 256 blocks to suggest a location; label it a biome-based candidate. Actual ground height and safety are unverified. No automatic terrain sampling or new rejection gate. |
| 2 | Consistent Python/native scoring | Carry A1's final-center recount into the new policy and independently verify selection and score components. |
| 3 | Flexible deficits | Allow at most three deficient categories; apply category-specific deductions after eligibility. |
| 4 | Remove salvage centroid pull | Set Shipwreck and Ruined Portal weights to zero for both centroid positioning and weighted radial comparison in Python, native code, and configuration. Other weights retain their existing values. |
| 5 | Improve the starter hub | Reserve the single Village-proximity contribution separately from the other nearby-structure contribution. |
| 6 | Cap repeated structures | Implement the exact surplus and optional schedules below. |
| 7 | Describe End access accurately | Show predicted Stronghold evidence and an optional inspection status for actual portal-room access; no automated portal-room certification. |
| 8 | Treasure-Bastion preference | Award +15 once for a predicted viable treasure variant inside the selected Nether window. |
| 9 | Optional portal inspection | Expose arrival/return-link inspection status separately from the score; no automatic portal construction or traversal in the search. |
| 10 | Separate snow/ice evidence | Distinguish biome predictions from block-resource observations; do not infer packed ice, blue ice, or powder snow quantities from a family witness. Unsupported evidence stays unverified. |
| 11 | Capped archaeology reward | First Trail Ruin +15; second +10; no further count points. |
| 12 | Optional biome variety | Apply the one-time category table below, with no Mangrove or dual-swamp reward. |
| 13 | Predictive scenic pairing | +20 once for the exact scenic/River witness pairing below, using existing samples. |
| 14 | Distributed Villages | +15 once for the exact three-quadrant/separation condition below. |
| 15 | Retain and compare qualifying results | Persist the one winning representative for every qualifying seed under either supported retention mode; paginate listings and allow side-by-side comparisons. Do not persist every eligible center. A displayed shortlist does not delete other results. |

**Explicit exclusions:** no automatic coastal or terrain screening; no land-fraction/ocean-strip/Monument-footprint gate; no terrain score; no actual spawn-arrival/bed-respawn test. Earlier removed resource, farm, pre-generation, End-policy, slime-cluster, and structure-edge-warning proposals are not reintroduced. Optional human inspection is outside automated eligibility and scoring.

### 8.2 Eligibility and geometry

Keep the existing half-open geometry and predictor pins:

- Macro-envelopes: Overworld `[-2000,2000) × [-2000,2000)`; Nether `[-562,562) × [-562,562)`. Allowed integer centers satisfy `-1168 <= Cx,Cz <= 1168`.
- Overworld playable bounds: `[Cx-832, Cx+832) × [Cz-832, Cz+832)` within that macro-envelope.
- Nether playable bounds: `[Cx/8-416, Cx/8+416) × [Cz/8-416, Cz/8+416)`, using the existing exact rational/integer containment rules, including negative coordinates.
- Keep the event-cell construction, mandatory membership invariance, and constrained 16-block snapping with the existing 8-block fallback.
- Keep the world-aligned 64-block lattice and existing four-Y roles: surface-family witnesses at Y=63/160 and cave-family witnesses at Y=-48/0. Keep the existing Y=63 Dark Forest Mansion witness rule; changing that rule is outside this plan.

| Structure | Hard minimum | Preferred target | Deficient counts | Deduction per deficient category |
|---|---:|---:|---|---:|
| Stronghold | 1 | 1 | None | — |
| Mansion | 1 | 1 | None | — |
| Village | 8 | 9 | 8 | 10 |
| Trial Chamber | 7 | 8 | 7 | 10 |
| Ancient City | 3 | 4 | 3 | 10 |
| Desert Pyramid | 2 | 3 | 2 | 10 |
| Jungle Temple | 2 | 3 | 2 | 10 |
| Monument | 1 | 1 | None | — |
| Ruined Portal | 5 | 7 | 5–6 | **5** |
| Shipwreck | 4 | 6 | 4–5 | **5** |
| Mineshaft | 12 | 15 | 12–14 | 10 |
| Outpost | 2 | 2 | None | — |
| Nether Fortress | 2 | 2 | None | — |
| Bastion | 2 | 2 | None | — |

A count below any hard minimum rejects that window. A flexible count at or above its minimum but below its target consumes **one category**, regardless of the number of missing structures. At most **three categories** may be deficient. Four categories reject the window even if their deductions would be small. Required biomes never consume this allowance: a missing required family rejects the window.

Keep all thirteen required Overworld families: Plains, Desert, Forest, Taiga, Jungle, Swamp, Snowy/Ice, Dark Forest, Peaks (including the current Frozen Peaks option), Stony Shore, Lush Caves, Dripstone Caves, Deep Dark. Either ordinary Swamp or Mangrove satisfies the existing Swamp family. Keep all five Nether biomes: Nether Wastes, Crimson Forest, Warped Forest, Soul Sand Valley, Basalt Deltas, sampled on the existing world-aligned 64-block lattice at Y=64.

The v2 default deficit budget is three, in both native and Python execution. Update all dispatch/preflight/CLI validation paths that embed the old limit; do not reinterpret older profiles' generic near-miss allowances as permission to omit v2 biome families. A stricter existing user override may reduce the budget, never exceed three or bypass a floor. Complete v2 predictions within the selected budget are eligible, including those with deficits; do not demote them behind lower-scoring zero-deficit results.

**Worked eligibility cases:** five Portals plus four Shipwrecks are two deficient categories and a 10-point total deduction. Add eight Villages: three categories and 20 points deducted, still eligible if everything else passes. Add fourteen Mineshafts as well: four categories, rejected. Four Portals or three Shipwrecks reject immediately because the hard minimum fails.

### 8.3 Complete score contract

For an eligible final snapped window, count only captured predicted viable starts, using the selected dimension's bounds and existing qualifying predicates (including the Y=63 Mansion rule and basement-only igloos). Apply all Section 8 bonuses to that same window, not to its full macro-envelope. The seed's published score is its winning representative's score; never sum scores across centers.

For that window:

```text
deficit_penalty = sum(category deduction for each deficient category)
bonus_total = core_structure_bonus + optional_structure_bonus
            + biome_bonus + treasure_variant_bonus
            + hub_bonus + scenic_pair_bonus + village_spread_bonus
final_score = bonus_total - deficit_penalty
```

Retain signed scores; a negative score is not itself a rejection. Do not normalize or clamp the result to the old terrain scale. Apply deductions once, not separately in native selection and again during record construction.

#### A. Core structure bonuses: start above the preferred target

At exactly the preferred target there is no extra-count bonus. Presence, proximity, and variant bonuses remain independent.

| Structure | Exact reward schedule | Cap |
|---|---|---:|
| Mansion | +50 once at count ≥2 | 50 |
| Stronghold | +35 once at count ≥2 | 35 |
| Monument | +35 once at count ≥2 | 35 |
| Village | +25 at ≥10; another +10 at ≥11; another +5 at ≥12 | 40 |
| Trial Chamber | +10 for each of counts 9, 10, 11 reached | 30 |
| Ancient City | +25 once at count ≥5 | 25 |
| Desert Pyramid | +20 once at count ≥4 | 20 |
| Jungle Temple | +20 once at count ≥4 | 20 |
| Outpost | +20 once at count ≥3 | 20 |
| Fortress | +20 once at count ≥3 | 20 |
| Bastion | +20 once at count ≥3 | 20 |
| Ruined Portal | +5 for each of counts 8, 9 reached | 10 |
| Shipwreck | +5 for each of counts 7, 8 reached | 10 |
| Mineshaft | +1 for each of counts 16 through 20 reached | 5 |

Rewards in a row are cumulative and stop at its cap. For example, Village count contribution including its deficit is −10 at eight, 0 at nine, +25 at ten, +35 at eleven, and +40 at twelve or more. This replaces the old ninth-Village/eighth-Chamber/fourth-City/third-Temple milestones.

#### B. Optional structures and treasure variant

| Feature | Exact reward schedule | Cap |
|---|---|---:|
| Witch hut | First +20; second +10 | 30 |
| Trail Ruins | First +15; second +10 | 25 |
| Ocean Ruins | First two +10 each | 20 |
| Buried Treasure | First four +6 each | 24 |
| Basement igloo | First +10; second +5 | 15 |
| Treasure Bastion | +15 once if at least one predicted viable variant-2 Bastion is captured | 15 |

An ordinary igloo without a predicted basement earns no igloo points. A treasure variant can stack with the Bastion count milestone because they measure different features. Additional treasure variants earn no further variant points.

#### C. Optional biome categories

Use captured Y=63 witnesses for luxury scoring, matching the existing luxury-evidence convention. Required-family Y roles remain separate. Resolve names through `src/seed_search/realm/biomes.py:canonical`; derive native membership IDs from the same catalog. Existing aliases, including `shattered_savanna_plateau` and giant-tree/giant-spruce taiga names, map into the listed categories without extra awards. Do not broaden the accepted canonical category sets.

| Category | Accepted canonical names | One-time points |
|---|---|---:|
| Cherry Grove | `cherry_grove` | 25 |
| Pale Garden | `pale_garden` | 25 |
| Mushroom Fields | `mushroom_fields` | 25 |
| Badlands | `badlands`, `wooded_badlands`, `eroded_badlands` | 20 |
| Warm Ocean | `warm_ocean` | 15 |
| Ice Spikes | `ice_spikes` | 15 |
| Savanna | `savanna`, `savanna_plateau`, `windswept_savanna`; existing `shattered_savanna` alias | 15 combined |
| Old-growth taiga | `old_growth_pine_taiga`, `old_growth_spruce_taiga` | 15 combined |
| Flower Forest | `flower_forest` | 10 |
| Bamboo Jungle | `bamboo_jungle` | 10 |

Repeated patches and multiple members of one category do not multiply points. **Mangrove alone: zero. Ordinary Swamp plus Mangrove: zero.** Preserve the required Swamp-family membership independently of these removed bonuses.

#### D. Protected starter-hub contribution

All distances below are horizontal Euclidean distances from the **selected border center**, using inclusive thresholds and only captured predicted viable structures.

```text
village_hub = 10 if any Village is within 256 blocks
              6 if none is within 256 but one is within 512
              0 otherwise
other_hub = 6 * (nearby Desert Pyramids + Jungle Temples + Outposts)
          + 4 * nearby Ruined Portals
hub_bonus = village_hub + min(30, other_hub)
```

“Nearby” means within 512 blocks. Village proximity is awarded once. Maximum hub score is 40; it is 36 with only a 257–512-block Village, or 30 with no Village within 512. Use squared integer distances; no square roots are needed for threshold checks.

#### E. Scenic pairing and Village distribution

**Scenic pairing: +20 once.** A Y=63 witness in `plains`, `sunflower_plains`, `meadow`, or `cherry_grove` must be within 192 blocks of the selected center. A Y=63 `river` witness must be within 128 blocks of that scenic witness. Both must lie inside the selected Overworld window. Use inclusive squared Euclidean distances. `frozen_river` does not silently substitute for `river`. No separate component points, no multiplication for multiple pairs, and no terrain/navigation guarantee. The independent Cherry presence bonus may stack.

**Village distribution: +15 once.** There must exist three captured Villages in three distinct quadrants about the selected center, with every pair separated by at least 256 blocks. For deterministic boundary handling, assign `x >= Cx` to the positive-X side and `z >= Cz` to the positive-Z side. Store a qualifying triple, chosen in stable coordinate order. Do not accept three occupied quadrants without checking the pairwise separation.

The arithmetic ceiling for all bonuses is **719 points**, before deductions; simultaneous attainability is not assumed. It is a regression check on the schedules, not a normalization denominator or expected score.

### 8.4 Ranking and retained evidence

Apply the same integer final score to native center selection, independent Python selection, saved records, rescoring, CLI exports, and the database/dashboard leaderboard. Among eligible results, use:

```text
final_score descending
deficient_category_count ascending
radial_key ascending
origin_distance_squared ascending
Cx ascending
Cz ascending
stable candidate ID ascending (across saved seed results only; binary lexical order)
```

For v2, `radial_key` is the integer obtained by rounding `weighted_radial_distance * 1_000_000` to nearest, with exact halves away from zero, matching native `llround` for this nonnegative finite value. Python's `round(value, 6)` is not the specified rule. `origin_distance_squared = Cx*Cx + Cz*Cz` is an exact integer. Use the existing durable candidate identifier; do not substitute a worker-completion sequence or a new random ID. Persist the normalized keys so SQL/export use the same comparison rather than re-rounding a floating display value. Human-readable radial/origin distances may remain alongside them.

Preserve native radial distance arithmetic and use its traversal order as the v2 reference: Strongholds first, then the fixed macro-slot order in `realm/native_batch.py:NAMES`, skipping zero-weight categories; preserve each inventory's enumeration order through reconstruction. Python must accumulate the same contributions in that order, with the same weights and denominator. Do not use unordered containers, a different reduction, or a sorted copy only on one path. Test half-step quantization and near ties explicitly. This resolves an existing native/Python/SQL convention mismatch for v2; leave historical revision interpretation isolated.

Do not leave deficit-first or verification-status SQL tiers in front of the v2 score among eligible results. Keep rejected/incomplete records outside the eligible-result comparison; show evidence status separately rather than promoting a prediction to verified. All ranking paths must agree on the complete key. Different policy revisions are not one comparable point scale; filter/label them separately instead of mixing them into a v2 leaderboard.

Save a compact `ranking.components` breakdown with positive bonus components, positive `deficit_penalty`, `bonus_total`, `final_score`, and `score_revision`. Save the deficient category names and observed/target/floor counts. Preserve existing compatibility score fields consistently for the new revision; do not let a stale `combined_score` override the new final score.

Retain the evidence needed to explain and recompute a selected-window score: luxury witnesses; nearest qualifying Village; scenic witness pair; distribution triple; Bastion coordinates/variant IDs and prediction status. Retain enough underlying selected-window evidence to recompute these terms, not only the winning score flags. Select evidence witnesses deterministically: coordinate tuples use ascending X then Z; pick the lexicographically first qualifying scenic/River pair and sorted Village triple, and the nearest hub Village with coordinate ties. Prepare witness iteration order once per seed as needed, without changing the radial inventory order. Reuse existing inventories and sampled arrays rather than duplicating them in every component.

Freeze component names/types and the native/Python evidence interface in B1 before parallel implementation. Evaluated absence is a zero component with no witness; failed/unevaluated scoring is not zero and must not produce a completed eligible score. Inspection statuses default to unverified/unavailable with provenance when evidence is supplied; they do not alter points. Reuse existing evidence schemas where possible; a new inspection workflow or automatic verifier is outside scope.

### 8.5 Efficient implementation sequence

Complete each package and its targeted checks before moving to the dependent package. Keep C11/OpenMP, bulk CFFI calls, the single SQLite writer, and bounded batches.

| Order | Package | Files and concrete work | Acceptance criterion |
|---|---|---|---|
| B1 | Versioned contract and score descriptor | `src/seed_search/realm/config.py`, `config/realm.yaml`, `blueprint.py`; add a small revision-scoped score-policy module if needed. Define named category/threshold tables once on the Python side and encode their fixed-size parameters for native use. Add explicit dispatch for the new revision across policy predicates. | Old revision fixtures retain their old interpretation. New revision accepts three deficits and zero salvage centroid weights; unsupported revisions/builds fail clearly. |
| B2 | Independent Python scoring reference | `dynamic.py`, `blueprint.py`, dynamic tests | Implement all schedules, weighted penalties, final-center spatial terms, and score-first ordering. Arithmetic unit cases and independent synthetic selection cases pass before native parity is claimed. |
| B3 | Native policy, metadata, and scoring | `native/blueprint_batch.h`, `blueprint_batch.inc`, `blueprint_dynamic.inc`, `bridge.c`, matching CFFI declarations/build inputs, `realm/native_batch.py` | Encode revision/score parameters explicitly, update the native `max_misses > 2` guard only for the new revision, retain final-center counts, and use one shared native scoring helper for selection and final anchor reconstruction. Rebuild and detect stale ABI/build identities. |
| B4 | Cached spatial/variant evidence | Native dynamic worker data and Python `PaletteIndex`/inventory handling | Compute River relationships, Village pair separation, and Bastion variants once per relevant seed. Per-center scoring reuses these results and stops on the first qualifying combination. Full native/Python component and center parity passes. |
| B5 | Storage, rescore, and ranking | `native_records.py`, `native_batch.py`, `reports.py`, `leaderboard.py`, `store.py`; inspect `native_encoding.py` where the new record path uses it | Round-trip the score and supporting evidence; SQL and CLI order match the reference. Score changes invalidate the web cache. A fixed-window rescore is not presented as a fresh center search. |
| B6 | Retire terrain from this revision's workflow | `config.py`, `runner.py`, `cli.py`, `store.py`, terrain entry points, web server callers | New runs have no active terrain variants, enqueue no terrain work, and never wait for a terrain pass to qualify. Validate the empty active-variant list for this revision. Historical terrain runs remain readable; computation resumes only with compatible saved source/build/config identities as specified in Section 9.5. |
| B7 | Player reports and dashboard | `src/seed_search/web/server.py`, `web-ui/src/types.ts`, relevant UI components, `scripts/export_web_policy.py` where applicable | Display score breakdowns, deductions, predictive witnesses, and optional inspection statuses. New-revision terrain state is `not_applicable`, not permanently pending/rejected. Paginate results and compare selected entries without dropping others. |
| B8 | Blueprint, README, and measured release | `MASTER_SEED_BLUEPRINT.md`, `README.md`, policy docs/tests and benchmark artifacts | Documentation and executable policy agree; source/build/config identities are recorded; bounded end-to-end and performance checks complete. Start only a fresh bounded v2 validation run with its input range/count and runtime limit recorded beforehand. Do not launch a production campaign. |

**B1/B3 detail:** current code embeds bonus membership and point arrays in several places, and both Python and native validation reject more than two deficits. Audit each policy dispatch rather than globally replacing old constants. The new luxury table still has ten categories: replacing the removed Mangrove bonus slot with old-growth taiga can avoid increasing the 23-channel prefix layout, provided the mapping is revision-specific. Use named counts/slots and assert matching dimensions. Do not change the historical meaning of a saved bonus bit.

**B2/B3 detail:** keep eligibility independent from bonus thresholds. Raising the bonus threshold for an Ancient City to five must not raise its preferred target above four or its floor above three. Deduction uses category identity: a bare deficit count is insufficient when Portals and Shipwrecks cost five but other categories cost ten.

**B4 detail — scenic pairing:** use the existing Y=63 biome grid. For each scenic lattice witness, inspect its small, fixed neighborhood for a River within 128 blocks; cache the resulting qualifying scenic witnesses and a stable River witness. For each snapped center, examine only the neighborhood within 192 blocks. Do not resample biomes or compare every scenic point against every River for every center. Dense sampling, heightmaps, and new event subdivisions are outside this plan.

**B4 detail — Village spread:** precompute pairwise squared separations for the macro Village list once. Per center, filter captured Villages, assign quadrants, and short-circuit when a valid three-quadrant triple is found. Keep this simple until profiling demonstrates a need for a different representation; account for any worker scratch allocation.

**B4 detail — treasure Bastion:** the pinned `getVariant(..., Bastion, MC_26_50, seed, x, z, -1)` exposes `sv.start == 2` for treasure. Query each predicted viable Bastion once and reuse the result for all centers. Prefer the direct variant query over the diagnostic wrapper's additional biome sample. Treat API failure as an explicit error/unsupported observation, not as a non-treasure answer. Propagate coordinates and variants through the native/Python evidence boundary and test subsequent RNG consumers. No chest or block generation is needed.

**Selection scope:** score location-dependent terms after snapping. The existing cells preserve mandatory membership, not every proximity bonus. Continue choosing among the defined representative centers; do not claim exhaustive optimality over all coordinates or expand the event grid to chase every bonus boundary.

**Spawn/report detail:** choose the nearest captured Y=63 witness from `plains`, `sunflower_plains`, `meadow`, or `cherry_grove` within an inclusive 256 blocks of the selected center, breaking equal-distance ties by X then Z. It need not participate in a River pair. This suggestion adds no score and no eligibility requirement. If no candidate exists, report unavailable without rejection. Keep witness sample Y separate from actual spawn height; never emit a claimed safe `/setworldspawn` command from a fixed-Y biome sample. End/portal inspection fields remain unverified unless explicit evidence is supplied. Snow/ice reporting uses only supported evidence, with no new block-generation pass.

### 8.6 System and blueprint updates

Update the active blueprint in B8 as one consistent revision, with the following checklist:

| Blueprint area | Required rewrite |
|---|---|
| Revision header and geometry | Name the new policy and retain exact 1664/832 bounds, lattice, and snapping conventions. |
| Centroid distribution | Zero Shipwreck and Ruined Portal weights; keep other weights explicit. |
| Tolerance matrix and miss-budget section | Three categories maximum; hard floors unchanged; category-specific deductions; include the two-missing-Portals/Shipwrecks examples. |
| Structure and luxury matrices | Replace every old threshold and uncapped formula with Section 8.3, including surplus bonuses beginning above targets and zero swamp bonuses. |
| Hub and player bonuses | Protected Village contribution, exact distance inclusivity, scenic +20 combination, and Village-spread +15 condition. |
| Hierarchical sorting diagram and prose | Score first, then deficit count; identical native/Python/database semantics. |
| Execution pipeline | Remove automatic terrain/coastal scoring, screening, scheduling, and certification prerequisites for the new revision. Keep optional inspection evidence separate. |
| Yield/performance claims | Mark old-policy measurements as historical; remove any implication that old yield forecasts or optimized-kernel timings establish new-policy yield or persisted throughput. |
| Evidence language | Predictions remain predictions. Biome witnesses do not establish safe ground, loot, portal rooms, actual resource quantities, or navigable Rivers. |

Align README commands and the UI's policy labels with the same contract. Do not leave obsolete terrain-required instructions as the default workflow. Preserve historical commands for historical runs.

### 8.7 Targeted verification matrix

Extend the existing dynamic baseline/integration, leaderboard, rescore, and web evidence tests; add narrowly scoped cases where existing fixtures cannot express the new feature. Test outcomes and boundaries rather than source substrings.

| Area | Required cases |
|---|---|
| Floors/targets/deficits | Each category at floor−1, floor, target−1, target, and target+1; strict categories have no deficit allowance; three deficient categories pass, four fail; five Portals/four Shipwrecks deduct ten total. |
| Count bonuses | Every threshold and cap, including Village 9/10/11/12/13, Chambers 8/9/10/11/12, City 4/5/6, Temples 3/4/5, optional counts from zero through one beyond their last rewarded count (hut/ruins/igloo: 0–3; treasure: 0–5), not through the numeric point cap. |
| Complete-score examples | Isolate Village contributions −10/0/25/35/40 at counts 8/9/10/11/12; assert bonus total minus the exact deduction; negative eligible scores remain eligible. |
| Hub | Inclusive 256/512 boundaries and immediately outside; one Village award; other-structure saturation cannot erase the Village contribution; maximum 40. |
| Scenic pairing | Inclusive 192/128 boundaries, diagonal distances, River-only/scenic-only failures, `frozen_river` exclusion, multiple-pair cap, Cherry presence stacking, final-center movement changing eligibility. |
| Village distribution | Three quadrants without separation fails; qualifying triple passes; exactly 256 separation passes; axis assignments and multiple triples are deterministic. |
| Biomes | One bonus per category; Savanna aliases do not double-count; old-growth variants do not double-count; Mangrove and dual-swamp award zero while the required family still passes. |
| Bastions | All four variant IDs; zero/one/multiple treasure variants; treasure outside the selected Nether bounds; negative-coordinate containment; explicit variant-query failure; interleaved structure queries. |
| Selection parity | Independent Python enumeration against native selection with nonempty optional inventories and spatial bonuses; all thresholds evaluated after final snapping; complete ties, half-step radial rounding, weighted deficits, deterministic witnesses, X/Z/ID ties, and a higher-scoring deficient result beating a lower-scoring zero-deficit result. Replay at a C-chosen center is supplementary, not independent selection proof. |
| Spawn/inspection reports | Nearest qualifying Y=63 witness at inclusive 256, equal-distance coordinate ties, no-witness unavailable, and independence from River pairing; sample Y is never reported as verified ground/safety. End/portal/snow-ice inspection fields neither change score nor schedule generation/terrain work. |
| Persistence/UI | Native score equals reconstructed/exported/rescored components; SQL order matches reference; unchanged-row-count rescore refreshes dashboard; all qualifying results remain retrievable through pagination. |
| Policy history | Old-policy fixtures remain valid; new config/ABI identity cannot resume an old run silently; old terrain records remain readable; new runs enqueue no terrain work and show `not_applicable`. |
| End-to-end | A bounded fresh run writes results, survives stop/resume under the same identity, and exports consistent evidence. Use valid positive fixtures if natural survivors are absent; label their provenance. |

### 8.8 Performance check and rollout

Compare the new policy with the **corrected Section 7 baseline**, using the same hardware, input seeds, thread/batch settings, retention mode, and matched build methodology. Policies intentionally select different windows and retain different seeds; cross-policy receipt equality is not an acceptance criterion. Within each policy, native/Python agreement is required.

Measure native inputs/sec separately from durable end-to-end inputs/sec. Record stage times, windows entering palette/scoring work, retained results per input, peak memory, record construction/serialization time, and database write cost. Include a bounded natural cohort and positive survivor fixtures so both rejection and retained-record paths are exercised. Report actual differences without inventing a speed budget or claiming zero cost.

If spatial work is material, inspect the per-seed caches before introducing new data structures. If survivor storage grows, retain bounded inflight ownership and pagination; do not drop qualifying results or weaken WAL/FULL durability to improve a headline rate. Removing terrain saves only work that was actually being run downstream, not automatically native-kernel time.

Use a fresh run directory for bounded new-revision validation, following Section 0.4; production-scale searching is not a completion requirement. Rescoring old selected windows cannot recover newly eligible seeds or centers discarded by the old policy. Reevaluate old seed IDs for center changes when desired; rescan old input ranges to recover formerly rejected inputs. Keep old saved identities intact.

**Completion deliverables:** separate audit-remediation and player-policy commits/reports; updated blueprint/README/configuration; rebuilt native artifact and recorded identity; passing targeted tests and bounded end-to-end evidence; measured performance comparison; all fifteen retained improvements represented accurately in outputs. Finish when these concrete deliverables pass—do not expand into new gameplay features or another speculative optimization audit.

---

## 9. Player-Policy Implementation — Speed and Accuracy Requirements

**Purpose:** implement Section 8 without avoidable repeated work or loss of scoring correctness. This section adds implementation and verification requirements; it does not change any agreed floor, target, deduction, bonus, or selection scope. Apply it within work packages B1–B8 after the Section 7 correctness work.

### 9.1 Where costs can actually increase

The added integer score arithmetic is small. The material risks are more windows reaching late stages, repeated spatial queries inside the center loop, and more retained evidence. Their aggregate impact must be measured; no zero-cost or unchanged-throughput claim is established.

| Change | Potential cost | Required implementation approach |
|---|---|---|
| Three deficits instead of two | More windows may need palette checks and scoring; additional seeds may survive | Keep mandatory floors and cheap necessary preflight checks. Measure stage-entry counts. Do not compensate by silently tightening requirements. |
| Revised counts, caps, and deductions | A bounded number of integer comparisons per eligible representative | Use the shared revision-specific score parameters and native helper. No Python callbacks, dictionaries, serialization, or allocations per native center. |
| Scenic/River pairing | Repeating biome generation or all-pairs witness searches | Reuse the existing Y=63 grid and bounded lattice neighborhoods; cache seed-level relationships once. |
| Village distribution | Repeated pair-distance calculation and triple searches | Precompute pair separation once; use captured Villages and quadrants per center, with exact early exits. |
| Treasure variant | Repeating `getVariant` for the same Bastion at many centers | Reuse an already available variant if the collection API exposes it; otherwise query once per predicted viable Bastion and retain the result. |
| Hub | Repeated full scans for multiple distance bands | Compute both Village bands in one traversal; use squared integer distances and capped sums. |
| More survivors | More reconstruction, JSON, SQLite writes, and UI rows | Keep bounded batches and indexed pagination. Construct full result records only for retained results according to the selected retention mode. |
| Terrain removal | Removes downstream work only when that stage previously ran | Enqueue no new-revision terrain work. Do not attribute a native-kernel speedup to removing a separate downstream stage. |

### 9.2 Work placement and cache lifetime

| Frequency | Work allowed here | Work to keep out |
|---|---|---|
| Once per policy/build initialization | Resolve named score parameters, canonical biome memberships, revision/ABI compatibility | Rebuilding these tables for each seed or center |
| Once per seed, lazily when needed | Existing structure inventories and biome grids; new scenic relationship cache, Village separation cache, Bastion variants | Eager new feature work on seeds already rejected by cheap mandatory checks |
| Per eligible snapped representative in native scoring | Exact containment, category deductions, score arithmetic, bounded local scenic lookup, hub and Village-spread checks | Biome regeneration, repeat variant generation, FFI calls, JSON, database access, heap allocation |
| After choosing the winning representative | Complete component breakdown, retained witnesses/inventories, spawn suggestion, explanatory fields | Building full report objects for every losing center |
| At persistence/UI boundaries | Encode retained records, commit bounded batches, indexed pagination, display evidence | Serializing every candidate on every UI refresh or loading all retained rows into browser memory |

Preserve the existing early filtering sequence unless a separately measured reorder is justified. Start new spatial caches only after a representative can meet the mandatory structure and biome requirements. Existing inventories may retain their current lazy collection points; do not reorder expensive palette and optional-inventory work on assumption alone.

Keep cache storage worker-local. Capacity may be reused across seeds, but valid lengths, flags, witness coordinates, and seed ownership must reset on every seed, including rejection and error paths. Cache values are valid only for the exact seed and policy that produced them. Route new buffers through the repaired reservation/ownership mechanism, check allocation sizes, and retain failure-safe pointer/capacity publication.

### 9.3 Exact low-cost feature calculations

**Scenic pairing:** on the existing 64-block grid, a 128-block-radius River neighborhood around a scenic lattice point contains at most 13 integer lattice offsets, including the origin. Precompute that offset list once. For each relevant scenic witness, cache whether an accepted River witness exists and a deterministic supporting coordinate. Do not search every River in the macro-envelope for each scenic point.

For a snapped center, a 192-block-radius query fits within at most a 7×7 lattice bounding box. Inspect only those positions and apply the exact squared-distance predicate; the box itself is not the eligibility test. Stop after a qualifying pair is found, with stable iteration order for reproducible evidence. Preserve Y=63, ordinary `river`, half-open window containment, and the single +20 award. No additional `nb_point`/biome-noise query is required for this feature.

**Village distribution:** for N predicted macro Villages, compute the N(N−1)/2 pair separation predicates once and store them in checked, accounted worker memory. For each representative, use the captured Village list. If fewer than three quadrants are occupied, return zero immediately. Otherwise examine triples from distinct quadrants using cached pair predicates and stop at the first valid triple in deterministic order. Do not award the bonus solely from quadrant occupancy. Start with this bounded implementation; introduce a more elaborate search representation only if profiling identifies it as material.

**Hub:** traverse captured Villages once, checking 256- and 512-block bands. A Village within 256 establishes the maximum Village reward. Traverse the other relevant lists with squared distances and stop accumulating their score once 30 is reached. These score-only exits must not truncate the complete stored inventories. Preserve `village_hub + min(30, other_hub)` exactly.

**Treasure Bastion:** cache the variant for each predicted viable start, then test captured variant-2 starts using the existing exact Nether containment. Multiple treasure starts still award +15 once. The diagnostic wrapper also samples a biome; do not call that wrapper in the center loop merely to retrieve a variant ID. Verify any new variant call's RNG interaction before treating it as safe to insert into the pipeline.

**Count and biome bonuses:** use existing counts and prefix membership. New caps are arithmetic saturation, not permission to stop collecting inventories needed for centroid selection, hub scoring, spread, or retained evidence. The revised luxury categories still fit ten category channels; removing Mangrove and adding old-growth taiga does not require a larger prefix table. Keep bit mappings explicitly revision-specific.

**Spawn and inspection information:** compute the biome-based spawn suggestion after choosing the winner. End-access, portal-safety, and snow/ice inspection fields add report state only where supported evidence exists. They must not trigger heightmaps, BDS launches, block generation, portal traversal, or new search filters.

### 9.4 Preserve selection correctness while reducing work

- Evaluate all agreed score components at the final snapped representative. Only mandatory membership and the defined lattice membership can be reused under the existing cell-invariance argument; proximity, quadrants, and optional counts need their own correct final-center handling.
- Keep the current linear best-candidate reduction in native selection. Do not introduce a full sort of native candidate cells or an exhaustive search over every coordinate for these additions.
- Do not add speculative score-based pruning or extra event boundaries. Evaluate every eligible representative required by the existing policy and let the complete adjusted score decide; persist only the winning representative per qualifying seed.
- A possible later micro-optimization is to evaluate the weighted radial tie-break only when score and deficit count tie, plus once for the final winner's saved evidence. Adopt it only if profiling justifies it and comparison tests prove identical winners; do not alter the floating-point expression, summation order, or 1e-6 quantization to obtain speed.
- Retain signed scores and exact integer point arithmetic. Five-point Portal/Shipwreck deductions require category identity, not merely the deficit count. Hard floors and the three-category budget remain separate predicates.
- The Python reference must remain an independent selection implementation. Production bulk native execution can retain its existing reconstruction checks; do not run a second exhaustive Python selection for every production seed just to claim parity. Run independent selection comparisons in bounded verification workloads.

### 9.5 Additional accuracy acceptance conditions

These conditions supplement Section 8.7 and resolve the handoff review's remaining implementation details:

1. **Worker reuse:** process seed A, then a different seed B, then A again on the same worker. Require identical A results and independently correct B results for scenic witnesses, Village spread, and Bastion variants. Include early rejection, an injected failure followed by another seed, and multi-worker ordering. Test both validity reset and reusable capacity.
2. **Missing score evidence:** a query or allocation failure is not “feature absent.” Follow the existing explicit error/incomplete-result path. Do not publish a completed eligible score, classify the input as an ordinary rejection, or commit successful range completion with silently missing required scoring work. A successfully evaluated feature that is absent contributes zero; an unevaluated feature does not establish zero.
3. **Historical resume:** old results remain readable. Resuming old computation still requires compatible saved source/build/configuration identities or the preserved compatible execution environment. Never relax identity checks merely because the old policy name is recognized by the new code.
4. **Score/evidence parity:** compare selected center, deficient categories, each bonus component, penalty, final score, and stable witnesses across native selection, independent Python selection, reconstruction, export, and fixed-window rescore. A matching total alone can hide two compensating errors.
5. **Bounds and state:** include exact distance thresholds, negative coordinates, window-edge inclusion/exclusion, axis quadrants, multiple qualifying witnesses, and no-witness cases. Freeze canonical alias handling and test old/new bonus-bit interpretation separately.

### 9.6 Measure overhead without confusing it with policy changes

Use existing profiling/benchmark infrastructure where suitable: `scripts/profile_native_stages.py`, `scripts/benchmark_dynamic_baseline.py`, and `scripts/benchmark_compact_selection_persistence.py`. Extend only the missing measurements for the new revision. Use profiling builds for attribution and uninstrumented matched builds for headline timings.

Measure policy impact in all cases; measure implementation efficiency when comparing an additional optimization. Do not build a deliberately slow duplicate v2 production path solely to obtain a control. Use the correct implementation checkpoint before that optimization.

The two comparison types are:

- **Policy impact:** corrected v1 against the new v2 policy on the same bounded natural input cohort and comparable build conditions. Record changed eligibility and retention. Different winners and receipts are expected here.
- **Implementation efficiency:** the straightforward correct v2 implementation against any optimized v2 implementation on the same workload. Require identical eligibility, selected centers, score components, and retained evidence. This isolates optimization from deliberate policy changes.

Include both natural inputs and positive fixtures. An all-reject natural cohort cannot measure scenic/spread/variant or survivor-persistence costs. Fixtures exercise those paths but do not establish natural survivor frequency. Include a dense valid fixture with many eligible representatives to expose repeated work; use bounded sizes and label synthetic results.

Collect the following measurements in bounded diagnostic runs, not per-center production logs:

| Measurement | What it resolves |
|---|---|
| Inputs/sec, native kernel and durable pipeline separately | Whether time moved into persistence or remained in the kernel |
| Windows reaching floor, deficit, palette, and scoring stages | How much extra work comes from the three-deficit policy |
| Cache build time and per-feature scoring time | Whether new work is once per seed or accidentally repeated per center |
| Additional biome-query and variant-call counts | Scenic feature adds no noise queries; variant queries scale with viable starts, not center count |
| Retained results/input and bytes/result | Whether storage growth is explained by more survivors or larger records |
| Reconstruction, serialization, commit time, outstanding batch count | Whether backpressure and ownership remain bounded |
| Peak process-tree memory and accounted native scratch | Whether caches/buffers fit the stated reservation and lifecycle |
| Repeated-run timing spread and paired medians | Whether an apparent regression is reproducible rather than timing noise |

If a reproducible regression appears, first attribute it to additional eligible work, retained evidence, or redundant implementation work. Remove redundant calls and unbounded materialization before adding new data structures or changing settings. Do not reduce the agreed deficit allowance, remove bonuses, drop qualifying results, or weaken durability to conceal the cost. Do not impose an invented percentage performance promise without measurements.

### 9.7 Release conditions for the player/scoring work

- All Section 8 score/eligibility tests and Section 9 state/evidence checks pass; no acceptance based only on source inspection or all-reject receipts.
- New native per-center scoring code contains no biome generation, repeated Bastion-variant generation, report serialization, database operations, or heap allocation. Lazy seed-cache initialization is a once-per-seed operation, even if triggered by the first eligible center.
- New scratch is bounded/accounted, worker reuse is verified, and production logging does not scale with candidate-center count.
- No terrain tasks are scheduled for the new policy; no terrain status blocks qualification; optional report fields do not start automatic verification work.
- The final-center result can be reconstructed from retained evidence with the exact same component total and ordering.
- Performance is reported with workload/build identities, actual retained counts, and separate kernel/persistence figures. Any material unexplained regression is resolved before production rollout.

**Expected engineering outcome:** the scoring arithmetic remains small, new spatial relationships are computed once and reused, and extra work caused by retaining more qualifying seed results is visible and measured. This controls avoidable cost while preserving the exact agreed player policy; it does not promise zero added compute or a particular seeds/sec figure.
