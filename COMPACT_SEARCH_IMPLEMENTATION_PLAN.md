# Compact search: target and implementation plan

10 October 2026. **The geometry and optimization APIs below are implemented.** Final bounded measurements and acceptance decisions are recorded in [COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md](COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md). This document retains the original implementation and acceptance contract. No new million-input or full32 sweep has been launched.

## 1. Fixed target

| Region | Exact contract |
|---|---|
| Overworld discovery | 4000×4000; X/Z each `[-2000,2000)` |
| Initial Nether discovery | 4000×4000; X/Z each `[-2000,2000)` |
| Final Overworld | 1536×1536; Stronghold `(sx,sz)` ±768; may extend beyond discovery |
| Final Nether | 896×896; exact `(sx/8,sz/8)` ±448; no center rounding |
| Native integer queries | Convert half-open bounds to inclusive integer limits only at the adapter |

Keep Stronghold, Village, Trial Chamber, Ancient City, Mineshaft, two wooded families, initial Fortress, and final-square Fortress **and** Bastion requirements. Preserve V1/V2 independence, terrain thresholds/resolutions, uncertainty rules and manual-only caves. Bedrock 26.52 / BDS 1.26.52.3 and the MC_26_50 predictor remain pinned. Predictions do not establish actual absence or verified generation.

The active YAML, default configuration, bounds helpers, raw geometry, cave bounds and verification geometry now agree. The raw ranking algorithm is unchanged; its new geometry has a new checkpoint identity. Historical artifacts stay intact. Use new run directories: changed config/source identities must reject attempts to resume old computation with new semantics. Explicit historical verification configurations retain their supplied side lengths.

The selected geometry is a constrained search choice, not a proof of optimal discovery size. The previous 1000-input compact pilot measured 337 qualifying **anchors**, 386.27 full64 inputs/sec and 130.17 qualifying anchors/sec at 1536/896. These are baseline predictions with the then-current code, not terrain-qualified or verified worlds. Source: [compact pilot](runs/compact-border-funnel-2026-10-10/report.json).

## 2. Evidence driving the work

The [investigation report](runs/filter-cost-investigation-2026-10-10/REPORT.md) and its linked raw measurements are the basis for this plan.

| Finding | Implementation consequence |
|---|---|
| Mineshaft complete enumeration restarts MT for every chunk; eligibility needs one start. It consumed 50.61% of summed timed filtering work in the old million-input benchmark. | Add a first-witness API; defer the full inventory. Vectorize complete scans only where still useful. |
| Biome calls consumed 28.70% of that timed work. Almost all cost is climate/noise/lookup, not Python crossings or allocation. | Evaluate only enough points for wooded eligibility; do full inventory later. |
| Eligibility-first prototype matched decisions on 96 seeds at both tested geometries; 1280/896 took 0.115 s versus 0.267 s. | Promote the staged contract, then measure again at **1536/896 with persistence**. Do not promise the prototype's 2.33× ratio at the new geometry. |
| A moving border-relative biome lattice loses known wooded witnesses when a border grows. Cached climate-leaf hints changed four biome IDs. | Version a stable lattice; retain in-border witnesses. Keep NULL climate hints. |
| At 1536/896, only 165/4096 dispersed low32 layouts failed raw presence/common-center feasibility. | Treat roughly 4% as observed selectivity, not 99.9%. Improve cost and useful ranking separately. |
| Village and Ancient City raw presence is guaranteed at every allowed center at these widths. Their capped counts add a constant 64 to the current ranking. | Eliminate those scans from the proved presence predicate and constant ranking terms. Full64 viability remains required. |

The old million-input result was 173.37 full64 inputs/sec with persistence at 5000/2688/1024. Native layouts/sec, stage calls/sec, full64 inputs/sec, qualifying anchors/sec and verified worlds/hour are different metrics. No new end-to-end optimized throughput is established yet.

## 3. Phase A — freeze the new reference and measurement contract

**Files:** extend `scripts/diagnose_filter_costs.py`; use `realm/runner.py`, `baseline.py`, `store.py` instrumentation and existing compact-pilot seed manifests.

1. Save source/binary/config identities and an immutable seed manifest at 4000/1536/896. Re-run the existing 1000-input compact cohort with the unchanged inventory algorithm as the reference. Keep a disjoint 1000-input manifest for held-out validation; repeats are timing trials, not new samples.
2. Record per-stage calls, positive/negative/deferred counts, native work, sampled points, first-witness latency, total worker CPU, elapsed time including persistence, peak RSS and output bytes. Report per-call service rates separately from pipeline inputs/sec.
3. Use three counterbalanced trials on identical inputs. Keep 30 processes × one native thread as the reference. No concurrent terrain/BDS for this baseline comparison. Record machine load and separately time later inventory completion.
4. Store complete reference candidate payloads. Subsequent stages must compare either full payload parity or a declared narrower decision contract; never compare only aggregate counts.

**Exit:** reproducible reference, exact geometry/boundary tests, and named cohorts containing positive and negative Mineshaft/wooded cases. Where natural negatives are rare, add explicit small-boundary/empty-domain native controls and synthetic decision-path tests; label them separately from production prevalence.

## 4. Phase B — Mineshaft existence and durable deferred inventory

**Files:** `native/bridge.c`, `bridge.h`, `native/build.py`, `src/seed_search/backend.py`; `realm/baseline.py`, `store.py`, `reports.py`, `terrain.py`; focused native, baseline and recovery tests.

### Native contract

Add `ss_mineshaft_first` and a Python wrapper returning a status and optional coordinate. Status distinguishes error, found and exhausted predictor domain. Iterate chunks in the reference order, using exact start-center bounds: for inclusive block limits `[lo,hi]`, chunk indices are `ceil((lo-8)/16)` through `floor((hi-8)/16)`. Keep the existing RNG predicates and seed conversion. Stop at the first in-border start. An exhausted domain is a predictor miss, never confirmed actual absence. Leave the complete enumeration API available.

Test coordinate equality against the full scan's first start, presence parity, negative coordinates, chunk edges, tiny/empty domains, signed/unsigned seed boundaries and repeated/interleaved seeds including `-1`. Verify native error/ownership behavior. Port the private four-lane exact MT kernel only as a separate follow-up for complete inventories or measured expensive negatives, with scalar fallback and full-array parity. Preserve the reviewed cold-seed initialization fix; do not replace MT with a different generator.

### Staged record and queue

Separate `eligibility` from `inventory`. Save the Mineshaft witness, query bounds, predictor identity and `inventory_status=DEFERRED`; do not represent one witness as a complete start list. Add durable inventory work keyed by candidate, inventory kind and computation identity, with pending/running/complete/failed states, transactional leases, recovery and idempotent completion. Use bounded queue reads and the existing resource/disk limits.

Use this same queue for full biome and optional-structure inventories in Phase C. Cheap eligibility may admit a candidate to coarse terrain; full inventory completion is required before publishing a complete baseline bonus score or a final ranked nomination. Exports may contain partial candidates, but must expose deferred work and score intervals. Incomplete bonus components are unknown, not zero. Extend report and scheduler consumers that currently read `baseline_score` directly; preserve an oldest/exploration share so incomplete candidates cannot starve. Do not claim an exhaustive global best from a finite shortlist.

**Exit:** exact eligibility/pending-reason parity on the frozen lattice and seed manifests; completed inventories match reference payloads; interruption/restart gives the same results without duplicated samples or scores. Measure both time-to-eligibility and eligibility-plus-all-inventories, so deferred cost stays visible. Performance objective: at least 10× lower median native cost on positive Mineshaft checks; correctness is mandatory even if this objective is missed.

## 5. Phase C — bounded wooded checks, then stable sampling

**Files:** `realm/baseline.py`, `biomes.py`, `store.py`, `reports.py`, `terrain.py`, `surface.py`; native/backend changes only after the sampling reduction is measured.

1. **Decision-preserving pass:** use the existing 576-point, 64-block lattice at 1536. Visit a deterministic dispersed order in batches of 16; stop after two distinct allowed wooded families have positive witnesses. If not found, exhaust all 576 points and retain PENDING. Store point coordinates and IDs so later inventory requests sample only the remainder. Completion reconstructs the original coordinate order before postprocessing, preserving first-coordinate and count semantics. Unknown/unsupported results stay unresolved.
2. Defer optional structure scans and full biome family/variant counts until inventory work is claimed. Persist separate sampling completion, predicted eligibility and bonus intervals. Retain existing distinctions between observed predictor bonuses and actual-generation uncertainty. Integrate inventory completion with rescore, report/export and final nomination paths.
3. **Separate sampling revision:** introduce a world-aligned X/Z lattice (`x,z` multiples of 64, clipped by half-open bounds), with a versioned identity containing spacing, Y, phase and ordering. Cache by full64 seed, backend identity and exact `(x,y,z)` with a bounded per-worker/seed lifetime. Reuse existing in-border witness observations across overlapping anchors. Count canonical-grid inventory points separately from supplemental witnesses so retained evidence does not inflate sampling frequencies or pretend to be uniform coverage.
4. Regression-test the saved witness-loss example: seed `7980124511283784280`, anchor `(772,-1996)`, 2304→2380. A larger border must retain an existing in-border positive witness. Compare the new lattice's qualification changes on the holdout; document them as a sampling revision, not an exact optimization. Old records need a new sampling/scoring revision, not in-place reinterpretation.
5. For unresolved wooded coverage, expose a deterministic refinement budget (initial pilot: at most 128 additional points/anchor at 32-block spacing, prioritized near differing biome samples). Exhausting the budget remains PENDING. Record work independently from the canonical 64-block inventory. Do not add an expensive surface-height query to every baseline input. Reuse later surface observations for final inventory with their own provenance.
6. Optional native follow-up: allocation-free reference-equivalent sampling with NULL hints. Keep the beach/forest tie case at `(3041,63,-1183)`, seed `12345`, as a regression. Parallelize independent point batches only after generator/thread ownership review; compare 30×1, 9×4 and 2×18 schedules within the 36-thread budget. Keep the best measured combined schedule; do not multiply 30 processes by 18 threads.

**Exit:** frozen-lattice early-exit decisions equal exhaustive reference decisions; completed scores/inventories match; stable-lattice changes have explicit provenance and pass nested-border witness retention tests. Initial pipeline objective: ≥1.5× persisted eligibility throughput at 1536/896 without decision changes, with queue growth, deferred cost and RAM reported. This is an acceptance target, not a forecast. Allocation removal alone previously saved only 1–3%, so it is lower priority.

## 6. Phase D — make lower32 cheap and semantically precise

**Files:** `realm/raw.py`, native bridge/header/build, `backend.py`, `realm/capabilities.py`, CLI handoff, `tests/test_master_raw.py` and native tests.

The new geometry derivation is already implemented. Exact native-inclusive envelopes are Overworld `[-2768,-2768,2766,2766]`, final Nether `[-698,-698,697,697]`, initial Nether `[-2000,-2000,1999,1999]`. Center rectangles use Overworld ±768 and scaled-Nether ±3584 with exact half-open membership.

Implement three distinct native operations rather than always returning full counts:

| Operation | Work and output |
|---|---|
| Necessary presence | Skip proved universal Village/City raw-presence clauses. Generate shared Fortress/Bastion placements once, preserving the complementary type draw; stop when the requested predicate is established. Return booleans/witnesses, not fabricated counts. |
| Capped legacy rank | Skip constant Village/City contributions; stop each remaining count at 32. Preserve the existing score exactly for an A/B control. Label values as capped lower bounds. |
| Full layout inventory | Enumerate complete counts/coordinates only when required for selected layouts or geometry features; retain an exact reference implementation. |

Trim redundant regional halos only for audited regular placement types; do not alter displaced Stronghold enumeration. The initial-Fortress presence condition is implied by a final Fortress because this final envelope is contained in discovery. This does not eliminate a requested complete initial inventory. For common-center feasibility, enumerate the necessary Nether points and compute the exact union/intersection of their allowed-center rectangles. Presence of both types anywhere is only a cheap necessary test, not proof they share a center. Do not early-stop an exact coverage-area metric after one pair.

Document and test the raw-presence proof: Village universal for square width ≥944; Ancient City for ≥624. At width 1536, both are universal at every allowed center, although full64 viability is not. Gate the shortcut by pinned placement implementation and geometry; otherwise fall back to the generic algorithm. Preserve shadow/ranking-only semantics for actual-world claims.

Version checkpoints with geometry, predicate, count mode, proof/backend identity and ranking policy; include raw implementation changes in computational identity. Reject incompatible resume and handoff identities. Add exhaustive small-domain center oracles, integer region-phase checks, type-split parity, cap/full-score parity and interrupted-selection recovery.

**Exit:** zero decision/score differences for the respective exact contracts on the saved dispersed cases plus fresh held-out low32 blocks. Benchmark at least 262,144 layouts in dispersed blocks, three trials, including Python selection/checkpoint time separately from native compute. The previous existence-only 1280/896 prototype reached 1.23M layouts/sec at 36 threads; it is relevant to the same Nether predicate but is not a measured 1536 production rate. The 45-minute full32 aspiration needs 1.591M layouts/sec end to end. Do not start that sweep merely because a compute-only extrapolation is close.

## 7. Phase E — earn a useful lower32 advantage

The missing 99.9% is principally a predicate problem, not a missed SIMD optimization. Raw regional structures are common. Stronghold anchor discovery, Village/City viability, wooded families, Trial Chambers and terrain depend on information not resolved by this raw32 filter. Keeping the top 0.1% is a heuristic sampling quota, not a lossless rejection rate.

Implement a bounded selection experiment after the faster full64 gate exists:

1. Replace flat density ranking in an experimental policy with exact feasible-center area/fraction, Fortress/Bastion co-location coverage and border margins. Compute these only for a bounded eligible pool; measure feature overhead. Any static Stronghold hint is ranking-only unless a conservative superset also covers the village-associated path with proved offsets/halos. An incomplete Stronghold predictor must not become a hard raw veto.
2. Compare four arms: optimized independent full64; uniformly selected low32 with dispersed upper32 siblings; legacy capped-count ranking; new geometry ranking. Use identical total CPU budgets, disjoint tuning/holdout low32 blocks and at least three deterministic allocation seeds. Charge raw enumeration, features, rejected siblings, persistence and deferred inventory to each arm.
3. Initial bounded experiment: 4096 dispersed low32 layouts, maximum 256 admitted layouts and 4096 total full64 evaluations per arm. Allocate siblings in rounds of 1, 4 and 16 cumulative evaluations/layout, keeping 20% of selection budget for uniform exploration. Use a deterministic upper32 permutation rather than only 0 and 1. Store selection probabilities/rounds and all evaluated outcomes. Compare yield curves at common CPU checkpoints; later allocation beyond these budgets requires evidence, not a full32 commitment.
4. Rank promotion by observed qualifying-anchor yield per CPU second with uncertainty; carry promising anchors through identical bounded V1/V2 terrain budgets. Report distinct qualifying seeds and anchors separately. Evaluate final nominations under the same bounded BDS budget. If there are no verified successes, report verified advantage as unmeasured; do not substitute raw or provisional yield.
5. Consider a version-bound Mineshaft raw cache only for this sibling arm after a source-level low32-dependency audit and differential sibling tests. Reuse raw placements/existence with exact bounds; never share full64 biome or terrain results. Independent full64 search has little low32 reuse, so this is not a prerequisite for Phase B.

**Adoption gate:** new ranking must improve held-out predicted qualifying-anchor yield per total CPU by at least 20%, with a layout-cluster bootstrap confidence interval excluding no improvement, and show no measured loss in terrain-success yield at matched budgets. Treat a small/inconclusive cohort as inconclusive; retain independent full64 as default. Verified-world improvement needs verified outcomes and its own uncertainty report. If no arm wins, retain the cheaper raw APIs for diagnostics and stop funding a full32 ranking sweep.

## 8. Delivery order and final acceptance

1. New-geometry reference and metrics (A).
2. Mineshaft first-witness API plus durable eligibility/inventory separation (B).
3. Frozen-lattice wooded early exit and deferred bonuses; then stable-lattice revision (C).
4. Native existence/capped/full lower32 modes and shared Nether geometry (D).
5. Budgeted sibling/ranking experiment against the now-faster independent full64 baseline (E).
6. Only then consider complete-scan vectorization, native biome threading, larger throughput trials and a larger search.

Each delivery includes decision/payload comparisons appropriate to its contract, crash/resume coverage, boundary controls and a machine-readable timing/CPU/memory/disk report. Maintain the 25 GiB target / 30 GiB ceiling including the Docker reserve. Run all Realm/master regression suites after integration; run native sanitizer/ownership checks when C changes are introduced. Keep fair queue scheduling and distinguish DEFERRED from complete inventory throughout CLI, reports, rescoring and terrain nomination.

The later implementation request expands the outcome to the native optimizations, deferred-inventory schema, sampling revision, all-family detection audit and bounded lower32 selection experiment. Structure detection uses minimal positive witnesses where presence suffices, following the user's subsequent instruction. Complete start counts remain a separate explicit audit; scoring-inventory completion means family presence and the canonical biome sample, not complete generated-world coverage.

## Historical geometry-change verification (before optimization)

`tests/test_realm*.py`, `tests/test_master*.py` and `tests/test_approved_plan.py`: **517 passed in 56.60 seconds**. Coverage includes explicit/default profile agreement, fractional negative Nether boundaries, raw envelope membership, recovery and verification. `seed_search --config config/realm.yaml doctor` completed successfully; its existing predictor/actual-generation limitations remain reported. Evidence links resolve and `git diff --check` passed. No optimization benchmark or full sweep was started for this planning task.
