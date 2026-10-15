# Implementation plan after the system audit

Status: **P0–P5 implementation and bounded verification complete; reference recommended; sweep unstarted**. Requirements approved on 8 October 2026: **2304/928**, Stronghold + Fortress mandatory, Bastion and other structures optional. The requested lower32/upper32 mode is included below. Evidence and reasoning: [SYSTEM_AUDIT.md](SYSTEM_AUDIT.md).

Latest approved scope: **four independent categories** — structures-only, enclosed inner island with water and surrounding mountains, ocean island, and dry flat mountain basin without an inner island. Structures-only is a qualifying category with terrain marked `not_required`; it is not a failed-terrain diagnostic. The three terrain categories keep their own requirements and evidence. This supersedes the audit's initial off-by-default structure-only diagnostic proposal.

The requested pre-implementation test is complete: [SIMD_TEST_RESULTS.md](SIMD_TEST_RESULTS.md). Decision: fix the demonstrated MT initialization defect, promote exact land reuse, and defer production SIMD integration. The four-Y prototype was slower after reuse; Gemini's FMA flags changed density values; strict AVX2 added only 2.6% in the serial current-geometry cohort.

Biome diversity now applies across all four categories as a separate weighted ranking bonus. Concrete sampling, usefulness weights, score bounds and validation: [BIOME_DIVERSITY_PLAN.md](BIOME_DIVERSITY_PLAN.md). Default scope is every structure-qualified full64 seed; broader failed-seed sampling is an optional diagnostic.

## Delivery order and estimate

Engineering estimates include focused tests and documentation. Machine-running time and availability of external/game observations can extend elapsed delivery. Do not start a sweep while a required gate is pending.

| Step | Work and dependency | Estimated effort | Intended impact | Completion condition |
|---|---|---:|---|---|
| P0 | Freeze four-category contract, add stage telemetry and evidence schema | 2–3 h | Makes decisions, costs, deferred work and output eligibility inspectable | One documented contract and explicit stage counters |
| P1 | Migrate every geometry consumer to 2304/928; P0 | 3–5 h | Correct smaller-world eligibility; 41.14% fewer samples per full 16-spaced landscape raster | Borders/envelopes/maps agree, legacy outputs remain historical |
| P2 | Fix native MT initialization, lattice/eligibility/cache-key risks, add structures-only category and define Stronghold evidence handling; P1 | 6–9 h | Prevents order-dependent structures, unsupported early rejection and inconsistent shortlist routing | Fresh/warm workers agree; four categories route correctly; unresolved evidence cannot enter a confirmed shortlist |
| P2b | Add weighted biome diversity across all four categories; P0–P2 | 2–4 h | Prefer usable resource variety while retaining mandatory eligibility | Versioned weights/coverage, separate base/bonus, deterministic ranking and measured sampling costs |
| P3 | Promote exact quart-cell land reuse; P2 | 2–3 h | Target 25–40% less equivalent-workload analysis time; three-seed measured aggregate 28.1% | Complete predictions and decision records match the corrected reference |
| P3b | Test safe island bounds before coastline; P2–P3 | 3–6 h | Potentially avoid expensive coast calls; benefit unmeasured | Shadow decisions have zero false rejections and save net time; otherwise retain prioritization only |
| P4 | Implement bounded lower32 → upper32 experimental mode; P0–P3 | 4–7 h | Potential better structure quality/yield per CPU-hour; currently unquantified | Deterministic full64 siblings, correct resume/gates, no optional hard requirements |
| P5 | Same-target benchmarks, holdouts, recovery test and refreshed readiness; P1–P4 | 4–7 h | Establishes actual throughput, quality, recall tradeoffs and safe finite launch | Evidence gates below pass; mode/budget chosen from measurements |

**Updated core total: 26–44 hours; reserve 26–48 hours / about 4–6 working days.** This replaces the initial 16–30 hour estimate: the user added a qualifying structures-only branch and an early island-bound experiment, the native test exposed an additional MT initialization defect, and the user added usefulness-weighted biome diversity across all categories. A Stronghold root correction or substantial SIMD/native algorithm rewrite is additional work. Do not delay a supported bounded search indefinitely waiting for an unproved patch; retain the explicit review/recovery policy if the disagreement remains unresolved. The demonstrated MT defect must be fixed before refreshed readiness.

## P0 — Contract and telemetry

Files: `search.example.yaml`, `config.py`, `landscapes.py`, `terrain.py`, `search.py`, `storage.py`, `reports.py`, this plan and `SEED_SELECTION_WORKFLOW.md`.

1. Introduce a new configuration/checkpoint version for the target geometry and staged enumeration. Keep old runs readable as historical data, and reject attempts to resume them with changed prediction semantics.
2. Record required structures once: `stronghold`, `fortress`. Optional scores retain their existing budgets; optional Bastion can contribute at most two total points. Do not change flatness, separation, ocean fraction or mountain thresholds to manufacture successes.
3. Add per-stage input/survivor/failed/unresolved/deferred counts, timings, branch, nomination ID, center/recenter, reason and native request/cache-miss counts. Distinguish requested block columns from unique raw-density cells. Save JSONL or normalized diagnostic records in addition to final summaries.
4. Profile setup, Stronghold, raw placement, full viability, preliminary height sampling, native land sampling, morphology, labels, ray metrics, report generation, cache lookups and serialization separately. Capture cold versus warm report costs and RSS.
5. Add an explicit output classification. Suggested values: `predicted_candidate`, `unresolved_review`, `failed_terrain_diagnostic`, `failed_required_structure_diagnostic`, `website_supported_candidate`, `game_observed_candidate`. Preserve the evidence fields and a reason list; do not infer a game observation from a website review.
6. Separate `search_category` from evidence status. Enable all four approved categories. Structures-only uses `terrain_status: not_required`, null terrain metrics, the existing 20-point Overworld plus 10-point Nether components (a separate score out of 30), and its own shortlist/counts. Retain optional Bastion's two-point cap and label the denominator. Add the separate biome bonus of up to five points in P2b: retain base/bonus explicitly and label combined maxima 35 for structures-only / 105 for terrain categories. Do not compare its structure-only total directly with a terrain-weighted total. A seed can qualify in several categories; report unique seeds and category memberships separately.
7. Make a branch-specific requirement/score/review matrix. Enclosed-island final review must establish separation, surrounding water and mountains; ocean-island review establishes separation and ocean setting; basin review establishes a dry flat interior and mountain ring. Structures-only skips terrain qualification. Existing diameter/gap/enclosure preferences remain preferences unless explicitly configured as hard limits; a scored prediction is not proof of the intended appearance.

Validation: stage counts reconcile for each branch, every terminal decision has a reason, one seed may have both a candidate and deferred locations without contradiction, and timing is excluded from deterministic prediction comparisons. Keep metrics collection cheap; do not log every Y-density sample in normal searches.

## P1 — Geometry migration with one source of truth

The user enlarged the planned Nether side from 640 to **928** after the native experiment. Keep the selected Overworld center divided by eight as its anchor. This is the 288-block mapped Overworld footprint plus 320 Nether blocks of padding on each side. Playable Nether area is **2.1025×** the prior 640-square proposal; this can admit more Fortress/Bastion placements but is not a measured yield multiplier. Historical 640-based diagnostics remain labeled with that geometry.

Files: `config.py`, `structures.py`, `landscapes.py`, `search.py` (including the legacy path), `reports.py`, `preflight.py`, `observations.py`, relevant tests and the active documentation/readiness generator.

1. Set the new default sides to 2304 and 928. Add helpers returning side, half-width, dimension scale, exact square bounds, center envelopes and sampling origins. Remove live 3008/992/1504/496/1568 literals from prediction/report code.
2. Keep Overworld centers on the eight-block grid and inside ±5000. Convert the selected center to the Nether exactly once. Bounds are center ±1152 Overworld and divided-center ±464 Nether.
3. New structure envelopes: Overworld ±6152 and Nether ±1089. At discovery step 64, snap Overworld outward to ±6208: 195×195 samples. Required-placement windows intersect on a common eight-block center; separate existence in two envelopes is insufficient.
4. Use the derived sides for every initial and recentered full raster, candidate JSON, review-border test, map rectangle/title and native envelope size guard. Nomination priority padding becomes `overworld_half + 64`, not another literal.
5. Retain the **2048 refinement patch budget** initially. A separate experiment may raise it to 2304; record recovered nominations and additional work. Terrain context used to establish finite shoreline uncertainty must not be confused with playable structure eligibility.
6. Keep 800-block shoreline/ring reach and existing landscape preferences. Where the smaller square clips a ray, retain unknown bounds; do not award outside-border resources or reduce the denominator to hide missing directions. Basin radius 800 with allowed 256 recenters fits within half-width 1152, but sampling halo and recentered raster still require explicit tests.
7. Update `SEARCH_TARGETS.md`, `README.md`, progress/status, inspection instructions and the active readiness report generator. Preserve old snapshots and measurements under their original identities.

Validation: negative centers, all four exact corners, markers one block outside, center-to-Nether conversion, non-eight-aligned forbidden centers, common-center intersections, full-raster endpoints, map extent, and finite-edge unknowns. Run configuration-derived tests at 4/8/16/32/64 spacings, rejecting unsupported combinations up front. Keep explicit tests for historical geometry using frozen configurations rather than silently changing old fixtures.

Impact calculation: full 16-spaced landscape raster 189² → 145² (35,721 → 21,025, **41.14% fewer points**). Discovery 205² → 195² (**9.52% fewer points**). Nether report raster at step 16: 63² → 59² (**12.30% fewer points**). These are sample counts, not whole-run speedups; smaller borders also exclude some previously eligible candidates.

## P2 — Correctness and selection routing

Files: `landscapes.py`, `terrain.py`, `config.py`, `review.py`, `scoring.py`, `reports.py`, `storage.py`, `readiness.py`, tests.

**Required native prerequisite:** replace the valid-seed sentinel in `vendor/cubiomes-bedrock/mt.c` / `mt.h` with an explicit thread-local initialization flag. `mt_ws` starts at `UINT64_MAX` (signed seed -1), with zero `mt_a`/`mt_b`; the first `setCarverSeed(-1,...)` skips initialization. The installed binary reproduces 0 → 44 Mineshaft starts in the same ±1024 square after an intervening seed-0 query. Use `!initialized || mt_ws != worldSeed` in all shared seed-cache initializers, set the flag only after both coefficients are ready, and include it in `MTRngState` save/restore. Do not patch individual seed coordinates or rely on a warm-up seed. Update the reviewed vendor-patch manifest, native/backend identity and frozen evidence with explained changes. Test fresh processes/threads, repeated -1, -1→0→-1, 0→-1, high32 siblings, state save/restore and worker-count/resume invariance. This defect affects optional structure scores and is distinct from the unresolved Stronghold predictor discrepancy.

1. Construct the early-basin patch by slicing/indexing the reference lattice, with a two-cell kernel halo. Preserve all eight allowed nearby floor proposals and center phases. If required alignment/coverage is not established, return unresolved and run the full check. Add the audit's 64-spacing counterexample plus positive basin, alternative floor, negative/off-grid center and finite-edge cases.
2. Strengthen `coasts` reuse keys: current key is only the center. Include discovered bounds, analysis bounds and sampling/policy identity (or a normalized component request). Different requests sharing a center must not accidentally reuse a result. This is a source-level risk; no failing real pilot was established in the audit.
3. Make one eligibility/routing function used by global rankings, per-landscape lists, review lists and diagnostic exports. A review that fails to establish required markers must route to unresolved/failed review even when the old native score is fully known. Confirmed terrain failures leave all qualifying lists. Keep unreviewed predictions available for inspection and visibly distinct from supported candidates.
4. Add a first-class `structures_only` branch before terrain nomination. Derive a bounded set of deterministic eight-block centers from jointly feasible required-structure windows, rank with full-seed viable structure results, and recheck exact borders. Give this branch its own center/output budgets so it cannot consume terrain nomination slots. Save its qualifying predictions even when the same seed fails all terrain branches. Export separate maps/review packets and counts; optional terrain maps must not become a qualification cost. Required-marker review still applies. Keep failed terrain records as failures for their original categories; do not relabel them as terrain passes or infer structures-only eligibility without checking its exact center.
5. Make report publication atomic by generating a new report generation before switching the active view. A failed render should leave the last complete view available. Preserve checkpoint commits independently of report success. Aggregate invocation counters without holding a second complete result list unnecessarily.
6. Add dependency/runtime fingerprint fields to new checkpoint identities. Change readiness regression expectations to an explicit versioned baseline with known disagreements and separately reviewed fixes, rather than permanently requiring six failures. Do not let unknown/new disagreement counts silently pass.

Stronghold investigation deliverable: a trace of initialization RNG draws, angle/distance, candidate region/chunk order, village placement, sampled biome/viability and accepted start. Compare at the **first divergence**, not only final output. Calibrate on -1/0/12345/4294979641; reserve 9 and new positive/negative-quadrant seeds for independent checks. Preserve floor semantics and snowy village eligibility unless evidence falsifies them. If unresolved, retain `defer_unpredicted` plus a bounded `review_all` recovery cohort; measure lost candidate coverage, not just time saved. A root patch is accepted only with a causal explanation, held-out parity and appropriate external/generated-world evidence.

## P2b — Weighted biome diversity

Implement [BIOME_DIVERSITY_PLAN.md](BIOME_DIVERSITY_PLAN.md). Run cheap inventories after the required-structure gate across all four categories, reuse existing surface arrays for terrain survivors, and refine structures-only finalists without adding terrain-shape requirements. Preserve raw IDs, canonical families, usefulness weights, estimated extent and sampling quality separately. Add at most five bonus points outside the unchanged base budgets; persist base score, bonus and combined interval. Coarse fixed-Y hints must not outrank refined results as if their evidence were equivalent. Optional failed-seed diagnostics are separately budgeted and cannot enter qualifying lists. Freeze policy and sampling identities, measure overhead, and test eligibility/base-score preservation and deterministic resume before promotion.

## P3 — Exact density reuse before SIMD

Files: `cache.py`, `backend.py` only if an explicit capability is needed, native bridge identity metadata, tests. Reference prototype: `scripts/audit_system.py:QuartLandBackend`.

1. Add a versioned capability stating that the pinned **raw land classification** is constant on quart X/Z cells. Share a missing land result by `(seed, operation, floor(x/4), floor(z/4), predictor identity)`. The backend instance already separates seeds; retain its bounded memory policy.
2. Preserve the coordinate validation and closed-handle checks. Broadcast to original point order, including duplicates; return independent arrays. Do not change the high-resolution output mask, morphology, coast stopping rule, or vertical search.
3. Keep surface biomes keyed at original coordinates. Do not alias `(height, biome)` results across a quart cell: block-scale biome selection is a separate operation. Height strides stay separate. An interpolated/new model must disable this capability until equivalence is re-established.
4. Retain the old implementation as a benchmark oracle or test adapter. Compare masks, component choice, centers, metrics, structure records, final scores, rejection reasons, candidate ordering and deterministic decision counts. Computed-cell/cache counters are expected to differ and must be reported separately.

Validation cohort: the ten land patches already measured; arbitrary shuffled/duplicated points and all negative cell boundaries; empty inputs, mutation, eviction and closed handles; thin bridge, diagonal contact, enclosed pond, crescent and finite-edge fixtures; complete seeds -1, 0, 9, 12345, 4294979641 plus independent enumeration indices. No tolerances on boolean masks or eligibility; exact current outputs for this optimization.

Expected impact: target **25–40% less analysis time** on equivalent new-border workloads. The old-geometry seed-12345 measurement is 39.36%; it is encouraging evidence, not acceptance of a universal multiplier. Keep 64 MiB until eviction data justifies a larger cache. Do not spend the core budget on Morton reordering or persistent CFFI buffers without new profile evidence.

Follow-up evidence: the completed three-seed/two-trial comparison measured **28.1% aggregate scalar analysis-time reduction**, with per-seed medians saving 19.0–39.9%. Variants/reuse match within the same initialization history; the separate cold -1 Mineshaft failure must be corrected in P2 before establishing a release baseline. This is current 3008/992 serial analysis, not new-border multiworker throughput.

## P3b — Safe island rejection before coastline

Files: `terrain.py:preliminary_component`, `landscapes.py`, branch telemetry, synthetic topology fixtures and an isolated comparison driver. Gemini correctly identifies expensive coast calls as a target, but the historical 47.54% coast share is not an expected saving, and the 95.47% basin result does not transfer automatically.

1. Record each island nomination's preliminary cost, coast cost, final component choice, branch outcome and rejection reason. Evaluate bounds in **shadow mode** first: continue the existing full computation even when the bound predicts failure. Use the same reference after quart reuse, since reuse changes the economics of this shortcut.
2. Classify cells as proved land, proved water, or unknown using the actual pinned raw-land model. A 16-block height grid is not a certified area/topology raster: height stride and unsampled cells can hide bridges, channels or another eligible overlapping component. Unknown cells remain available to the optimistic completion; finite edges and nearby component substitution must be covered. Any proof must describe its domain and preserve the reference lattice and kernel halos.
3. Apply upper bounds only to **hard** branch requirements. Diameter 300–700 and water enclosure 0.85 are currently scoring preferences, so missing those targets cannot reject a qualifying nomination. If future hard minimum area is configured, reject only when every eligible component's maximum possible area is below it; for a hard maximum area, a lower bound is required. Ocean-majority failure may be proved only over every permitted final 1400-square window, with unknown points counted as possible ocean/water. If the eventual center/window is not fixed, evaluate the union of allowed centers or defer.
4. For a hard directional threshold, count every unresolved ray as a potential hit and reject only when that optimistic total falls short. Ordinary coarse samples do not prove a continuous water gap or connectivity. Keep score-only diameter/enclosure estimates as scheduling priorities; record budget-skipped nominations as deferred. Score-bound pruning is a separate top-K optimization and must not erase qualifying counts or category outputs.
5. Compare full candidates, centers, component identities, eligibility, scores and reasons with the unfiltered reference on closed islands, thin bridges/channels, diagonal contacts, multiple overlapping components, off-grid/negative anchors and finite edges, plus held-out real nominations. Require zero false rejections, a source-level justification of each necessary bound, and positive net time saved after its sampling cost. If proofs require nearly complete coastline sampling, defer the hard filter and retain cheap prioritization.

Also test a cheap **required-structure window check after preliminary refinement and before coast**. The native-test baseline records 4, 4 and 1 exact-center structure deferrals across seeds -1, 12345 and 4294979641, respectively; these do not prove the work could all be skipped. Bound every final center the coast stage could select, including component fallback and eight-block snapping, then intersect that domain with the joint required-structure windows. Only skip when the full possible-center domain is incompatible under the same prediction policy. Checking only the preliminary center would be unsafe. Preserve missing-Stronghold/incomplete-prediction outcomes as deferred recovery records, not proof of structure absence. Measure avoided coast work rather than assuming a saving from the deferral count.

Impact: unquantified until the shadow benchmark; report avoided coast calls and total analysis time, not only time inside the new bound. All four categories retain independent routing; structures-only bypasses this stage entirely.

## P4 — Bounded lower32 layout / upper32 sibling mode

Files: `seeds.py`, `cli.py`, `config.py`, `search.py`, `structures.py`, `backend.py`, `native/bridge.h`, `native/bridge.c`, `storage.py`, `readiness.py`, `reports.py`, new staged-mode tests. This mode is implemented in `staged.py` and `search.py`; validation is recorded separately from the audit driver.

### A. Enumerate and rank raw layouts

Provide `full_64_bit_reference` and `lower32_staged` modes. The latter takes explicit finite limits: low32 layouts examined, layouts retained, siblings per retained layout, maximum full64 evaluations and run key. Start the experiment with **10,000 raw layouts, 64 retained layouts, four siblings each, maximum 256 full64 evaluations**. These are experimental budgets, not the production sweep recommendation.

Use a documented bijective 32-bit permutation for layout enumeration, with no wrap/repeats in a finite interval. Add a generator-free native raw-placement adapter based on pinned `getStructurePos` semantics, accepting only the eight verified MT families. Compare it directly against `Backend.structures(..., viable=False)` for every supported family, negative regions and high32 siblings. Trial Chambers, Mineshafts and full Stronghold generation remain outside that adapter.

Filter only on proven necessary conditions for required raw structures. Fortress raw absence from all possible center windows may exclude a layout under the current model; optional Village/Bastion absence may not. The 256-layout audit predicts this broad filter will have little selectivity. Rank retained layouts by an explicitly versioned raw proximity/cluster objective, normalized across families, with deterministic tie-breaking. Raw scores schedule work; full64 scoring remains authoritative.

Reserve a small fixed exploration share (suggest **16 of the 64 layouts**) from a deterministic sample of the remaining layouts to reduce over-concentration; do not describe this as eliminating bias. Keep top-layout-only results separately measurable. No raw Village is substituted for a required Stronghold.

### B. Expand full64 siblings

Generate unique high32 values with a documented deterministic permutation/run-key schedule. Compose unsigned bits `(high32 << 32) | low32`, then convert to signed64 decimal at the interface. Execute full-seed Stronghold iteration, Trial Chamber/Mineshaft logic, all biome viability, terrain and final requirements. Preserve optional structures as preferences.

Schedule small sibling batches on a worker to exploit shared raw layouts, but commit **each full seed** independently. Do not share terrain/biomes/viability across siblings. Limit batch size to avoid a slow layout starving other workers. All timings include raw scan/ranking, setup and full siblings.

### C. Checkpoint and readiness

Persist mode/version, run key, geometry/backend identity, raw cursor, retained-layout selection/version, high32 cursor and exact completed full seeds. Use stable identifiers including layout and sibling indices. An interrupted sibling batch must rerun only unfinished work. Define completion by completed full evaluations, not submitted futures or retained layouts alone.

Extend readiness to enforce **both raw and full64 budgets**, including resume; the current `count > 1000` gate alone is insufficient for a billions-layout scan. Expose all budgets and expected runtime in dry-run output. Do not enumerate 2³² layouts by default: even an unproved 0.1 ms/layout implies **119.3 single-core hours**, before upper-bit work, selection and I/O.

### D. Demonstrate whether it is useful

Compare the 256-sibling arm against **256 independent full64 inputs** under identical new geometry, criteria, worker count and renderer policy. Record CPU-hours as well as wall time, distinct terrain/center diversity, raw layout concentration, known/unknown structure eligibility, passed branch checks and website-supported yield. A second run with a different predeclared run key is required before recommending staged mode as the default.

Break out all four category yields and review outcomes. Structures-only passes must not inflate terrain yield or hide a loss of island/basin candidates. Report overlapping category membership separately from unique seeds. If staged mode helps structures-only but harms a terrain category, retain that tradeoff explicitly rather than promoting it from a pooled success count.

A 20-seed pilot is a smoke/parity check, not enough to validate this biased search strategy. Promotion criterion: reproducible improvement in useful unique candidates per **total** compute cost, no weakened requirements, and manageable diversity/recall tradeoffs. If neither arm produces verified suitable worlds, report yield as unresolved and use proxy counts explicitly; do not manufacture a success rate. Both modes remain available even if staged mode fails to outperform.

## P5 — Verification sequence and sweep gate

1. Rebuild only if native code changed, using the supported install path. Preserve pinned vendor files or record a reviewed patch/version identity. Run locked-dependency checks and the full suite, including new modes and migration cases.
2. Rerun all 880 structure / 159 coordinate comparisons. Geometry changes alone should not alter the underlying point/placement predictions. Exact reuse must add zero drift. Any approved Stronghold correction needs separate expected-change evidence, not a relaxed tolerance.
   Add cold-versus-warm seed-order regression outside the frozen fixture's normal seed order. That existing order can hide the seed -1 MT initialization defect; a passing aggregate fixture is insufficient. Preserve the pre-fix failing reproduction and explain corrected Mineshaft outputs separately.
3. Freeze a **2304/928 scalar reference** after P1/P2/P2b. Compare P3 to that baseline on identical seeds and work. Use three alternating-order trials on the same 20-input cohort, cold per-seed caches, exports measured separately. A changed border or sampling strategy is never compared directly with 345.58 seconds as a causal optimization result.
4. Verify checkpoint/resume against uninterrupted execution, including interruption after raw selection and midway through siblings, out-of-order completion, failure before checkpoint commit, empty/no-candidate results, and worker counts 1/8/12. Compare full prediction payloads; omit only documented timing/process/cache-work measurements.
5. Run the two-mode 256-input experiment described above, then an independent run key. Monitor p50/p95/max input time, cost per survivor, RSS and tile eviction. Increase workload only within a declared finite budget if evidence is inconclusive.
6. Re-evaluate saved controls under new borders and obtain fresh required-marker/terrain reviews for the retained candidates. Preserve real basin-positive evidence as missing if none exists. Synthetic basin controls validate code behavior but are not a claim of real-world basin yield. Run a predeclared small `review_all` recovery sample to quantify fast-mode omissions.
7. Generate a new readiness record sealing configuration, source/native/runtime identity, unit/regression results, resumability, all finite mode budgets, pilot measurements, review evidence and actual dry-run commands. Old readiness is historical. Verify missing/stale/tampered evidence and excess budgets are rejected.
8. Produce the final chosen-mode start/resume commands and refined ETA. Only then is the finite sweep technically ready. This audit does not launch it.

## Conditional follow-up work

| Work | When justified | Approach | Additional estimate |
|---|---|---|---:|
| Reuse vertical noise-cell samples | Height sampling remains dominant after P3 | Cache repeated `sampleSurfaceNoise` at fixed quart X/Z and floor(Y/8); preserve exact Y arithmetic and scan order | 4–8 h plus parity tests |
| Native coast frontier | Morphology/point construction becomes material after density reuse | Preserve current morphology connectivity, output masks, finite limits and cache reuse; owned buffers/capacities | 1–2 days |
| Ray coordinate reuse/native rays | Ray work becomes material or much denser workloads are required | Cache identical coordinate sequences; native implementation only with round-to-even/unknown/full-metric parity | 0.5–1.5 days |
| SIMD density | A better kernel or new-border multiworker result earns a material gain after reuse | Tested four-Y prototype is 1.2% slower after reuse; strict AVX2 flags save 2.6% serially; Gemini FMA fails density parity. Retain scalar fallback, safe dispatch and explicit FP policy for any later design | 2–5 days for substantial new design |
| Stronghold root correction | Trace + independent reference establishes the cause | Versioned patch, held-out tests, rebuilt baseline, generated evidence when predictors disagree | 2–4 h diagnostic tranche; resolution not time-guaranteed |

Do not add speculative speedups from these rows to the core forecast. Every accepted optimization must earn its own measured benefit without weakening requirements.

## Sweep ETA model

For a selected mode, estimate `raw_scan_wall + full_input_count × measured_analysis_seconds_per_input + measured_export_cost + recovery_cost`, then apply an observed variability allowance. Parallel CPU time and wall time must not be mixed. Include sibling concentration and long-tail inputs in the staged estimate.

Old data projects 5.92–9.60 hours for 2000 inputs. A provisional 25–40% reduction gives approximately **3.6–7.2 compute hours**; reserve roughly **5–10 hours plus human review** until the new pilot replaces this extrapolation. Border-related sample reductions are not stacked on top of that forecast. Staged enumeration may change the required input count and yield in either direction. The final finite launch budget and ETA remain a P5 deliverable, not an unverified promise of a certain number of worthy seeds.
