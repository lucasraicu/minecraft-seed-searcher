> **Current Realm target, 10 October 2026:** 4000×4000 discovery in both dimensions; 1536×1536 Overworld centered on the Stronghold; 896×896 Nether centered on exact Stronghold/8. See [COMPACT_SEARCH_IMPLEMENTATION_PLAN.md](COMPACT_SEARCH_IMPLEMENTATION_PLAN.md) and `config/realm.yaml`. The specifications, commands and measurements below describe earlier contracts; they do not override this target.

# Master implementation plan: speed, accuracy and validation

> **Execution authorized, 10 October 2026:** this roadmap is now an active implementation goal. The concrete target is a reproducible Stronghold-centered prediction/verification pipeline with the existing 2688/1024 borders, all five required Overworld structures, two wooded families, independent V1/V2, and **both Fortress and Bastion checked in every candidate's exact final Nether square**. Missing predictions remain pending; actual verification remains a separate evidence gate. Preserve historical runs and identities.
>
> Delivery order: frozen reference and tests → required-Nether correctness → exact native horizontal/vertical reuse → durable priority/resource/recovery work → bounded lower32 funnel and measured OpenMP/SIMD decisions → final checks → **one benchmark of exactly 1,000,000 distinct full64 inputs**. The benchmark includes baseline discovery, all required prediction checks, worker startup and persistence; terrain/BDS costs are measured separately on bounded saved candidates. Use one selected worker configuration, not repeated million-input worker trials. Do not launch the production sweep in this goal.
>
> Initial ETA: **3–5 working days** for implementation/verification, plus approximately **1.4–2.7 hours** for the benchmark at historical baseline rates. Those rates already used 30 Python processes and exclude the new native changes and stricter final-Nether checks. Forecasts are provisional; record the expected rate/storage before the benchmark and compare measured results afterward. Optional performance experiments receive explicit pass/defer outcomes; unresolved game accuracy remains visible rather than being assumed complete.
>
> Execution evidence: [runs/master-implementation-2026-10-10](runs/master-implementation-2026-10-10). Current decisions and remaining accuracy gates are in [MASTER_IMPLEMENTATION_RESULTS.md](MASTER_IMPLEMENTATION_RESULTS.md) and the [requirement checklist](MASTER_SWEEP_READINESS.md). The million-input benchmark is the final delivery gate for this implementation goal; a production sweep is a separate launch.

Reviewed 10 October 2026 against the live checkout, the Gemini research brief, existing experiments, and the Realm implementation. This revised roadmap is the accepted implementation target. The review does not establish actual game accuracy; execution and measured promotion decisions are recorded separately.

The supplied plan has the right goals: eliminate repeated work, measure native acceleration, and verify finalists in the real game. Its ordering, safety claims, performance promises, and description of the current system need correction. Accuracy work starts before scale-up and continues alongside optimization. Exact work reuse comes before additional parallelism. A raw lower32 layout scan is a selection experiment, not exhaustive world validation.

**Six-discrepancy follow-up, 10 October 2026:** incorporated native horizontal deduplication, a durable priority scheduler, explicit mixed-workload resource trials, terrain-error attribution and an early lower32 feasibility task. Section 2.1 records which claims are supported and which remain hypotheses. Fortress/Bastion contact is an optional diagnostic, not a new eligibility requirement.

## 1. Freeze the current contract

Use [the Realm specification](REALM_BASELINE_IMPLEMENTATION_PLAN.md) and [schema-5 configuration](src/seed_search/realm/config.py) as the requirements. The exported [Gemini brief](exports/gemini-seed-selection-2026-10-08/GEMINI_RESEARCH_BRIEF.md) is a historical research snapshot with older geometry and policies.

- Target pinned Bedrock 26.52 / official BDS **1.26.52.3**. Keep the compiled **MC_26_50** backend explicitly labeled as a predictor. Preserve backend commit `294c72ab0392dd818a91d293dbd5774d4874d64b` and the reviewed MT initialization patch.
- Discover Strongholds in the half-open Overworld square `[-2500,2500) × [-2500,2500)` and initial Fortress predictions in the same-sized Nether square.
- Evaluate each seed/Stronghold pair independently. Its Overworld Realm is **2688 × 2688**, centered on the Stronghold; final Nether is **1024 × 1024**, centered on Stronghold/8. Preserve exact fractional Nether centers and half-open border semantics.
- Require Stronghold, Ancient City, Village, Trial Chamber and Mineshaft in the Overworld evaluation square, and two of the specified five wooded families. Final Nether requires **Fortress AND Bastion**. Do not restore the old optional-Bastion rule.
- Run **V1 island/water** and **V2 mountain valley** independently from the durable baseline pool. The retired island/water/mountains branch stays retired. V2 has no hard flatness/buildability exclusion.
- Keep partial, missing and unsupported evidence recoverable. Predicted negatives cannot establish actual absence. Prediction and actual scores remain separate. Cave inventory remains explicit, manual and score-neutral.
- Preserve the 25 GiB working target / 30 GiB combined memory ceiling, including Docker reservation. Keep existing configurations, checkpoints, fixtures and historical measurements intact.

## 2. Assessment of the supplied proposals

| Proposal | Decision and reason | Revised action |
|---|---|---|
| Phase 1 audit is fully complete; no leaks or off-by-one errors | Too strong. Regression success covers tested behavior, not absence of every memory/logic defect or exact Bedrock parity. The latest implementation has substantial additional evidence but open accuracy gates. | Freeze live source/binary/config identity, rerun the relevant suite, and use focused native ownership/boundary/sanitizer checks for future C changes. |
| Reduce 12 Python workers to 4–6 | Treat as an experiment. Schema 5 already defaults to 30 single-threaded workers, supported by historical baseline-only scaling. Terrain and BDS have different resource demands. | Compare measured process/thread combinations on identical workloads; preserve the existing default until a replacement wins. |
| Insert OpenMP pragmas into `ss_land`, `ss_heights`, `ss_grid` | Conditional. Shared generator ownership, lazy initialization, any mutable caches and per-thread RNG must be audited first. Pragmas also require compiler/runtime/link configuration. Six processes × three threads does not guarantee ideal saturation. | Initialize outside parallel regions, parallelize independent outer columns, retain small-batch serial paths, and test scheduling determinism. |
| Add AVX flags to obtain 8–16 Perlin blocks per core | Unsupported as stated. Flags permit instructions; they do not build a lane-wise noise kernel. For doubles, AVX2/AVX-512 have 4/8 lanes per register, not a guarantee of equivalent block throughput. | Use compiler vectorization reports, disassembly, architecture-specific dispatch and equivalent-workload benchmarks. |
| Stride-8 `ss_land` with refinement cannot miss floating overhangs | Incorrect. Both endpoints can be air while an intermediate Y has positive density; refinement only after a sampled hit never visits that interval. Current `ss_land` deliberately checks every Y from 63 through 319. | Retain exact classification. Prototype reuse of noise within aligned eight-block Y cells while preserving every scalar density decision. |
| Hard classify `approx_height < 30` / `> 85` | No demonstrated error bound supports those thresholds. `NP_DEPTH / 76.0` is a heuristic, not exact surface/liquid height. | Use only for scheduling or explicitly labeled shadow predictions until conservative bounds are established. Retain recovery coverage. |
| Move coast frontier to C to remove massive pickling/IPC | Misidentifies the boundary. Frontier work currently runs inside a worker; CFFI calls are in-process. Pickling applies to worker dispatch/results. Morphology already uses SciPy native code. | Profile native density, SciPy morphology, point-array construction, CFFI copies and process serialization separately; port only a measured bottleneck. |
| Full lower32 sweep in less than 45 minutes | Unmeasured, and depends on regions/families scanned, ranking work and result persistence. There is no production `ss_sweep_raw` yet. | Build a bounded resumable native adapter, prove parity, measure rates, and derive the forecast. |
| Top 1,000–10,000 raw layouts yield the absolute best seeds | False completeness claim. Only eight reviewed MT placement families alias lower32. Stronghold iteration, Trial Chamber, Mineshaft, full64 viability and terrain are outside that guarantee. Selecting layouts/high32 siblings introduces bias. | Compare staged yield per CPU-hour against independent full64 enumeration and retain exploration quotas. Report best among evaluated seeds only. |
| Metal delivers a sub-five-minute sweep | Speculative. This host has an AMD Radeon Pro Vega 56, not an Apple Silicon GPU; its Metal capabilities and workload costs must be measured. MT state/initialization, arithmetic widths and compaction matter. | Defer until the CPU filter is correct, selective and demonstrably limiting. Start with an integer-only parity prototype. |
| Stronghold mismatch is probably C versus C++ rounding | Hypothesis, not a diagnosis. Both-axis truncation fails 12345; X-only truncation fails independent seed 9. | Trace RNG consumption, candidate order and biome viability against exact-build generated evidence before changing arithmetic. |
| Chunkbase top-100 checks are authoritative | Useful independent prediction comparisons, but not generated-world authority or an unbiased accuracy sample. | Keep website and actual-game evidence separate; include positive, negative, borderline and randomly selected controls. |
| Terrain thresholds can perfectly match Bedrock visuals | Raw density omits important generation stages and actual liquids. Matching a few visual examples does not establish precision/recall. | Calibrate complete actual formations, define measurable tolerances and retain uncertainty; do not change requirements to manufacture passes. |

The threading and vectorization decisions follow [OpenMP's memory model](https://www.openmp.org/spec-html/5.0/openmpsu9.html), [Clang's OpenMP/runtime documentation](https://clang.llvm.org/docs/OpenMPSupport.html), [LLVM vectorization diagnostics](https://llvm.org/docs/Vectorizers.html), and [Clang floating-point controls](https://clang.llvm.org/docs/UsersManual.html#controlling-floating-point-behavior). These document constraints, not workload speedups. GPU capability checks must use the actual device and [Apple's Metal feature tables](https://developer.apple.com/metal/Metal-Feature-Set-Tables.pdf).

### 2.1. Review of the six additional discrepancies

| Discrepancy | Assessment | Addition to this roadmap |
|---|---|---|
| Lower32 should be the front-door filter, rejecting 99.9% in seconds | A front-door stage is worth testing earlier, but neither rejection nor timing claim is established. [The existing audit](SYSTEM_AUDIT.md) found zero rejections among 256 layouts under its historical broad-envelope test; the new contract needs its own measurement. Unknown Stronghold centers and full64 viability prevent a fixed-box raw filter from being treated as complete world eligibility. | D0 moves bounded filter design/selectivity work to P1 after A1. Promote to Tier 0 only after joint-center correctness and useful-yield gates pass. |
| Move horizontal 4×4 reuse into `ss_land` | Useful concrete experiment. Production `cache.py` already groups/cache-reuses quart cells. Direct native callers can still repeat cells; moving grouping into C may reduce NumPy sorting/temporary work. The claimed thousands of pointer conversions per seed are not established: `Backend.land` currently makes one C call and two buffer adapters per batch, not per column. | B2a adds bounded native quart deduplication with original-order expansion and a separate cache/no-cache A/B. |
| 14 workers × 2 OpenMP threads is the optimal topology; 30 workers approach OOM | Unsupported as a measured conclusion. Historical scanner RSS was 2.593–4.152 GiB; adding the conservative 8 GiB Docker reservation gives 10.593–12.152 GiB for those scanner observations, not approximately 30 GiB. Concurrent terrain memory remains unmeasured. The contract is 25/30 GiB, not a new 32 GB ceiling. | C1a supplies concrete staged resource profiles and trials, including 14×2; defaults change only after mixed-load measurements. |
| Define a priority heap to surface results quickly | Useful, but part of it exists: durable work has numeric priorities/coarse scores and candidate rotation already prevents starvation. An in-memory heap alone loses scheduling state on restart and does not guarantee results within five minutes. | B4a extends existing storage with a bounded cross-candidate/variant scheduler, stable ties, durable dispatch and an exploration quota. |
| Aquifers, caves and decoration explain all 71 errors | These are generation mechanisms to investigate, not demonstrated causes of this sample. All 71 labels were predicted water versus no actual exposed water. Fresh replay found identical stride-1/8 heights; a sea-level inequality change leaves 64 mismatches. Surface material replacement also does not establish a universal 1–5-block height shift. | A3a adds per-column causal diagnostics for interpolation, vertical stride, sea-level conventions, liquids, cave density and surface interpretation. |
| Require Fortress and Bastion to touch/intersect | That requirement is absent from the agreed contract. Both structures must exist in the exact Nether square; physical contact is not necessary. Start coordinates or overlapping coarse envelopes cannot establish actual contact/access. | A2a adds optional actual-footprint distance/contact diagnostics without rejecting separated qualifying structures. A future hard contact rule would be an explicit requirement change. |

The review's [original supplied text and evidence manifest](runs/plan-addendum-review-2026-10-10) are retained separately. The historical 97% native-terrain observation is one workload's inclusive profile, not a current universal cost share; B1 remains necessary.

## 3. What already exists and what the evidence means

Do not propose these as new implementation: fixed signed-full64 enumeration; bounded multiprocessing; raw placement/full64 viability separation; MT cold-seed initialization repair; exact quart-cell land caching; exact-lattice prediction raster reuse across V1/V2; durable terrain work/retries; transactional candidate patches; atomic export generations; rescore recovery; selected pinned BDS extraction; actual surface-family observations; controlled waterlogging/snow/ice fixtures; interpretation/provider identity checks; durable terrain-raster byte caps and free-disk reserve checks.

The live terrain disk policy defaults to an **8 GiB logical serialized-raster cap / 16 GiB free-space reserve**, enforced transactionally, with recoverable capacity-blocked work. Those are engineering defaults, not measured capacity limits. Accounting excludes SQLite/WAL overhead and is not a complete cap on baseline databases, BDS worlds, snapshots or exports. Extend this existing protection when scaling; do not reimplement it as new work.

Source anchors: [native bridge](native/bridge.c), [exact cache](src/seed_search/cache.py), [Realm raster](src/seed_search/realm/raster.py), [Realm terrain](src/seed_search/realm/terrain.py), [baseline](src/seed_search/realm/baseline.py), [runner](src/seed_search/realm/runner.py), [store](src/seed_search/realm/store.py), [verification](src/seed_search/realm/verification.py), and [surface observations](src/seed_search/realm/surface.py).

| Retained evidence | Interpretation |
|---|---|
| [SIMD experiment](SIMD_TEST_RESULTS.md): exact quart reuse saved 28.1% aggregate analysis time on three historical seeds; strict AVX2 added 2.6%; four-Y SIMD was 1.2% slower after reuse | Workload-specific historical findings. Prefer reuse first; no universal speed multiplier is established. |
| Same experiment: relaxed Gemini flags changed 1,162/6,144 raw density values | A numerical change can preserve sampled signs yet fail exact predictor parity. Do not ship those flags as an accuracy-preserving optimization. |
| [Baseline benchmark](PERFORMANCE_BASELINE.md): paired 128-input one-worker comparison 6.84 → 15.35 seeds/s | Equivalent prediction qualification/qualified scores; terrain and BDS are excluded. |
| [Implementation results](REALM_IMPLEMENTATION_RESULTS.md): later 10,000-input baseline run 204.936 seeds/s at 30 workers; earlier 100,000-input run 102.865 seeds/s | Different sizes and source states; neither is current-source sustained throughput. No post-fix 100,000-input measurement exists. |
| Selected actual 256-column check: 71 land/water disagreements, height MAE 3.805 blocks, maximum error 39 | Clear reason to prioritize calibration. This local check is not a population error estimate. |
| [Latest checkpoint](runs/realm-implementation-2026-10-10/SURFACE_TERRAIN_QUEUE_FOLLOWUP.md): 560 passing tests, sampled actual Forest/Taiga presence, positive controlled column fixtures | Valuable covered behavior; whole natural formations, natural-ground provenance and required structures remain unverified. |

The current [capability report implementation](src/seed_search/realm/capabilities.py) still reports `large_search_ready=False`. Historical schema-3/4 sweep seals do not certify schema 5. The old [backlog](runs/realm-implementation-2026-10-10/FIX_BACKLOG.md) includes later status sections: many earlier items are already implemented. Use its latest status and the checkpoint report rather than treating its opening list as all-new work.

## 4. Ordered implementation work

Each task produces code, relevant verification, and a saved evidence report. Promote an optimization only after its gate passes. Use the execution results for completed, deferred and open-gate status.

### Phase A — establish trustworthy reference evidence

**A1. Freeze the live baseline and evidence identities.**

1. Save hashes for source, native binary, vendor patches, numerical dependencies, compiler settings, schema-5 configuration, BDS image/build and extraction policies. Record dirty-checkout state without resetting it.
2. Run the existing suite. Explicitly retain cold-process seed `-1`, seed-order independence, signed extremes, negative borders, full64 siblings, interrupted leases, terrain retry and export/rescore controls.
3. For later C changes, run targeted ownership, invalid input, capacity and supported ASan/UBSan checks. Preserve intentional arithmetic semantics; a passing Python suite alone is not a leak audit.

**Output/gate:** immutable reference manifest, test log and a capability matrix distinguishing implemented, tested prediction, actual sampled evidence and still-unverified features. No stale readiness record is reused.

**A2. Resolve structure/discovery authority before relying on structural rejection.**

1. Extend [the Stronghold tracer](scripts/trace_strongholds.py) and [investigation](STRONGHOLD_INVESTIGATION.md) to record MT state/draw positions, float/double angles, region/chunk conversions, sorted village candidates, sampled viability and the first divergence. Use `-1`, `0`, `9`, `12345`, `4294979641` and signed/high32 controls.
2. Compare disputed starts with pinned actual Bedrock worlds. Preserve the existing website markers separately. Record whether the evidence proves a start, accessible generated footprint, nearest result, or complete region coverage.
3. Extend existing trusted evidence imports with actual required-structure acquisition and a discovery-recovery executor in `realm/verification.py`, `realm/runner.py` and `realm/store.py`. Start with supported positive evidence; do not imply that a nearest-only locator or failed query proves exhaustive absence. The published stable [Dimension API](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/dimension?view=minecraft-bedrock-stable) does not supply the required exhaustive structure enumerator; recheck the pinned runtime before choosing a provider.
4. Integrate recovered in-discovery Stronghold anchors transactionally. Preserve seed/anchor identity, pool revisions and unresolved work. Apply all five Overworld requirements and the exact final Fortress/Bastion square.
5. Change vendor arithmetic only when a causal explanation survives independent controls. Update reviewed patch hashes, rebuild identity, replay fixtures, and distinguish explained corrections from new regressions. No seed-coordinate exceptions or already-falsified truncation fixes.

**Output/gate:** generated positive/negative structure controls where the provider supports them, recovery/resume tests, coordinate/footprint conventions and an honest completeness statement. Unsupported negative evidence stays pending. Full recall is not claimed from a top-100 website comparison.

**A2a. Optional Fortress/Bastion geometry and access diagnostics.**

Extend actual Nether evidence, when supported, with generated piece bounds or structure-associated block sets, their Y extents, evidence coverage and exact-build identity. Report nearest separation, overlapping piece boxes, observed block contact and traversable access as distinct measurements. Bounding-box overlap is a broad geometric test and may include empty space; it does not prove touching structure blocks or a usable route. Clip/report relation to the exact 1024-square without changing required-anchor conventions. Missing footprint evidence stays unknown. Add controls for separated boxes, touching faces, overlapping empty envelopes, vertical separation and interrupted/partial observations. These metrics are optional and do not alter eligibility or ranking weights by default.

**A3. Complete natural-ground and formation references.**

1. Extend the existing BDS column policy with natural-ground/structure provenance. Preserve primary/overlay water, cover, settling and unknown-state handling already tested; address fractional fluid height if used by a geometry requirement.
2. Obtain complete natural V1 and V2 positive and negative regions, with evaluator halos. Include narrow bridges/peninsulas, closed wide lakes, open ocean, elevated lakes, connected ridges versus disconnected hills, jagged V2 interiors, negative coordinates and chunk edges. Controlled placed-block fixtures validate interpretation, not natural terrain suitability.
3. Start with at least two complete positive and two complete negative formations per variant as engineering controls. They must be independently labeled from actual evidence and remain separate from a later held-out/random calibration cohort. If suitable complete examples are unavailable, report that gate as open.
4. Use `realm/calibration.py` on stable known requested-lattice cells. Measure height errors, water confusion, coast connectivity, whole-formation border fit, ridge relief/continuity, score ordering and false negatives. Exclude partial/mismatched observations from complete-formation accuracy claims.
5. Define acceptable errors and recall/precision targets before evaluating held-out controls. Report denominators, selection probabilities and uncertainty. Adjust scheduling/score calibration transparently; keep eligibility requirements intact.

**Output/gate:** reproducible actual reference corpus and calibration report. A verified terrain result requires complete actual water and natural-ground evidence at the resolution required by the evaluator, complete relevant footprints/halos and all mandatory evidence. Unknown cells cannot become land, water or absence through interpolation.

**A3a. Attribute terrain disagreement before selecting a model correction.**

The retained [selected BDS check](runs/realm-implementation-2026-10-10/final-bds-selected-check.json) has this binary confusion matrix:

| Prediction label | Actual exposed water | Actual no exposed water |
|---|---:|---:|
| Sea-level water proxy | 28 | 71 |
| No sea-level water proxy | 0 | 157 |

This is a comparison of two different water-label mechanisms, not proof that the 71 cells are natural dry ground. [The BDS integration report](runs/realm-implementation-2026-10-10/BDS_INTEGRATION.md) records the same direction. Mojang documents [Bedrock noise caves and aquifers](https://www.minecraft.net/en-us/article/caves---cliffs--part-ii-out-today-bedrock), and its [world-generation overview](https://learn.microsoft.com/en-us/minecraft/creator/documents/world-generation?view=minecraft-bedrock-stable) separates terrain/surface/features. Those sources establish relevant mechanisms, not causality or exact 26.52 equivalence for this predictor.

**Fresh bounded replay during this addendum review:** [the diagnostic](runs/plan-addendum-review-2026-10-10/replay_selected_columns.py) queried only the saved 256 X/Z points with the existing native predictor; [results](runs/plan-addendum-review-2026-10-10/selected-column-replay.json) reproduce the original height MAE, maximum error and 71 water mismatches. Stride-1 and stride-8 heights match at all 256 points, so coarse Y sampling explains none of this sample's height differences. Eight original water disagreements have predicted height 63. Using `<63` instead of `<=63` removes those eight but introduces one opposite disagreement, leaving 64; the exact raw-land complement also yields 64. This isolates a label-convention contribution but does not validate an inequality change or explain the remaining differences. No new Bedrock world was generated and no production policy changed.

1. Preserve the original observation, extraction policy and labels. Join each requested X/Z to predicted height, observed support Y/type, primary/overlay fluid, water top/depth/known flags, cover and stability. Do not reinterpret old missing fields as current-policy known values.
2. Replay identical points at native height strides 8 and 1 to isolate coarse vertical misses; compare the exact `ss_land` predicate separately. Check the convention boundary explicitly: native land accepts positive density at Y≥63, while calibration's water proxy uses height≤63. Audit off-by-one, coordinate lattice, inclusive/half-open conversions and saved/API interpretation before blaming game physics.
3. Compare raw density with interpolation/cave/fluid-aware diagnostic variants where supported, changing one factor at a time. Keep each variant labeled as an unvalidated predictor. Such terrain-physics probes do not enable automatic cave-biome inventory or cave scoring. Noninterpolated 4×4 land reuse must never be transferred to a new interpolated/cave/fluid model without a new proof.
4. Compare surface/support interpretation with actual type/state observations. Replacing a surface material need not change height; foliage is already filtered from current ground observations. Investigate snow/ice, waterlogged blocks, structure provenance and exposed-versus-underground fluid semantics independently. The maximum observed 39-block error needs direct explanation rather than a presumed decoration offset.
5. Produce a per-column attribution table: reproduced cause, discriminating test, error change and remaining uncertainty. If required raw fields are absent, request a separately budgeted pinned-runtime observation in future implementation; never mutate historical evidence to manufacture an explanation.

**Output/gate:** reproducible attribution evidence and a proposed model/interpretation correction only for demonstrated causes. Calibrate corrections on independent regions; do not simply tune thresholds to erase the 71 disagreements.

### Phase B — reduce exact terrain work

**B1. Profile the current V1/V2 path and protect existing reuse.**

1. Instrument exclusive stage time, inclusive native call time, requested/unique columns, cache hits, allocations, SQLite/serialization, exports and peak aggregate RSS. Use saved pool members; baseline scans need not be repeated to profile terrain.
2. Compare cold and warm caches separately. Verify that exact-lattice cross-variant reuse preserves coordinates, vertical stride, surface-biome channels, provider identity and unknown/retry semantics.
3. Keep raw-density quart-cell sharing confined to its proven X/Z-invariant land predicate. Never extend it to actual interpolated terrain, block-specific biomes or actual liquid observations without a separate proof.

**Output/gate:** current-source equal-workload profile and unchanged candidates/geometry/evidence. Historical coast percentages cannot select the new pipeline's bottleneck by themselves.

**B2. Prototype exact eight-block Y-cell noise reuse before Y striding.**

1. From [the pinned density source](vendor/cubiomes-bedrock/cave.c), split the expensive `sampleSurfaceNoise` calculation from the remaining scalar density formula. For fixed X/Z it depends on `(floor(x/4), floor(y/8), floor(z/4))`; the remaining formula still depends on exact Y.
2. Cache that noise value for the current aligned Y cell. Continue testing every requested Y and preserve evaluation order, arithmetic, clamping, early land success, endpoint handling and public height-stride behavior. Do not interpolate density or assume monotonicity across cell boundaries.
3. Apply first to `ss_land`; extend to `ss_heights` only where its current scan/refinement repeats a Y-cell noise evaluation. Keep surface-biome sampling at its original exact coordinate/Y.
4. Compare raw density values, signs, land booleans, heights at strides 1/8/16, biomes, full candidate results and thin-overhang/negative-boundary controls against the frozen native reference.

**Expected benefit:** a full water-column `ss_land` scan covers 257 Y values but only 33 aligned Y noise cells. That is an opportunity to reduce expensive repeated noise evaluations, **not** a measured 7.8× whole-query or whole-search speedup. Land columns that already exit immediately may gain little. This is a new source-derived experiment, not completed work.

**Output/gate:** isolated scalar prototype, exact parity evidence and repeated terrain timings. Ship only if complete useful workload improves; preserve fallback and record the new computation identity.

**B2a. Prototype horizontal quart deduplication inside native land batches.**

1. Add an isolated native batch path that groups `floor(x/4), floor(z/4)`, computes shape and exact stride-one land once per unique cell, and broadcasts booleans to the original request order. Use correct negative-floor semantics and safe unsigned key construction; do not left-shift signed negative coordinates.
2. Bound hash/sort/index workspace by batch size, account for allocations and free on every return. Cover empty batches, duplicates, arbitrary point order, negative cell edges, allocation failure and unchanged output/error contracts. Initialize owned terrain data once before any parallel computation.
3. Keep per-call deduplication separate from cross-call caching. The existing Python tile LRU avoids recomputation across calls; native per-call grouping alone cannot replace it. If a native per-context cache is later justified, define its seed/model identity, byte cap, eviction and destruction first.
4. Compare four arms: original native calls, existing Python quart cache, native grouping alone, and native grouping with the existing cache. Measure grouping, copying, buffer adapters, density work and cold/warm total times separately. Avoid counting already-deduplicated calls as a new density reduction.
5. Compose with B2's Y-cell reuse only after each isolated variant passes exact parity. Share raw land only; retain block-specific surface biomes and height-stride semantics. Reuse immutable dedup mappings if C1 parallelizes unique cells.

**Output/gate:** identical land masks and complete candidate/topology results with a measured gain for real callers. Current buffers use [CFFI's zero-copy `ffi.from_buffer`](https://cffi.readthedocs.io/en/latest/ref.html#ffi-buffer-ffi-from-buffer); contiguous-array preparation and boolean output conversion may still copy. Record actual call/allocation counts instead of assuming per-column pointer costs.

**B3. Batch only proven coast/transfer overhead.**

1. If B1 shows material overhead in legacy `terrain.coast_component`, measure its masks, repeated dilation/erosion, point generation and CFFI transfer separately from density work. Confirm whether that legacy path is part of the intended run.
2. Prefer compact batched buffers, deduplicated point requests and existing cache hits first. Keep SciPy morphology unless a native alternative wins.
3. If a C frontier implementation is justified, preserve the current neighborhood, step, sampled mask, stop condition, finite patch bounds, anchor selection and deferred states exactly. Bound its allocations and expose cancellation/status.
4. Replay thin bridges, separated islands, newly revealed connections and patch-boundary cases; compare masks/components and complete results, not only scores.

**Output/gate:** measured end-to-end gain with unchanged topology. An optimization used only by historical branches cannot be advertised as a schema-5 improvement.

**B4. Keep approximate prefilters in shadow mode.**

Record the `approx_height` proposals and conditional false negatives on actual controls and random recovery samples. Use them to prioritize work, never to permanently delete baseline survivors. A hard negative requires a proved necessary bound for the declared model/coverage. Sea-level uncertainty can prioritize verification or inform an explicitly versioned score; it cannot establish invalid terrain by itself.

**B4a. Extend the durable queue with bounded priority scheduling.**

The existing `realm/store.py` work records already carry priorities, and `realm/terrain.py` uses coarse geometry scores plus a rotating pool cursor. Extend this machinery for cross-candidate scheduling rather than introducing a separate volatile seed list.

1. Keep deterministic seed enumeration and committed input coverage unchanged. Schedule persisted expensive terrain/verification work from known seed/Stronghold pairs; an `approx_height` feature requires a full64 generator and is not a free lower32-stage metric. Reuse existing nomination rasters instead of adding speculative grid scans to every input.
2. Use a versioned bounded queue policy. As an initial experiment, rank by `0.5 × normalized baseline-quality hint + 0.5 × variant-specific coarse geometry hint`, using declared finite normalization ranges. Structure proximity belongs to the baseline hint; branch-aware `approx_height` features may inform nomination. Missing hints are unknown, not negative eligibility. This priority is not the exported suitability score.
3. Maintain separate V1/V2 queues. Dispatch three ranked ready units followed by one oldest ready unit in each four-slot cycle, alternating variants with available work. SQLite rank/age indexes select by stable priority, enqueue ordinal and unit ID directly. This avoids a second volatile heap while preserving durable order. The 3:1 ratio and equal hint weights are trial defaults, not established optima.
4. Bound registration refills to 4096 units and candidate nomination windows to 128; retain all unscheduled members in the durable pool. A transaction saves the dispatch lease, queue/pool revision, policy identity and cycle position before work. Failed/unknown tasks retain explicit bounded retry readiness. Preserve the per-anchor center budget across the stages of a selected center.
5. Preserve existing stage dependencies, budgets, retry fairness, immutable evidence, pool membership and result channels. Stable tie breaks must survive restart; timing-dependent parallel completion may change arrival order without changing eventual outputs. Resume from indexed durable state and avoid duplicating completed units.
6. Compare with current rotation on the same fixed pool and budget. Report time to first prediction, first actually verified candidate, useful results at 5/15/60 minutes, total CPU cost, queue ages and starvation/recovery. Five-minute measurements are an objective, not a promised discovery time. Sample exploration work for bias diagnostics.

**Output/gate:** improved early useful yield without lost coverage, weaker evidence or starvation, plus interrupted/resumed deterministic scheduling controls. Keep current fair rotation if priority sampling costs more than it saves.

### Phase C — add concurrency and SIMD only where they win

**C1. Evaluate native threading after B2.**

1. Audit all called sampling routines for mutable state. Initialize terrain/shaper before entering the team, preserve spline ownership, give scratch data/outputs distinct per-column storage, and prohibit concurrent close/reseed/use of one handle outside its ownership contract. Existing MT state is thread-local; each new thread must establish its own required seed/state rather than assume inheritance.
2. Add an optional OpenMP build/runtime path with explicit compile/link/load checks and a serial fallback. Do not silently change `numeric_threads_per_worker=1`; introduce an explicit versioned native-thread policy and checkpoint/runtime identity.
3. Parallelize outer columns, not early-exit Y loops. Use a batch-size threshold; begin with static scheduling, then compare alternatives for irregular water/land costs. Turn nested numerical parallelism off and account for BLAS/SciPy/Docker activity.
4. Compare process × native-thread combinations such as `30×1` for baseline, and `18×1`, `12×1`, `6×2`, `6×3`, `4×4` for matched terrain work. Treat these as trial points, not recommended defaults; leave CPU headroom when BDS runs.

**Output/gate:** identical arrays/candidates/counters across thread counts, cold seed histories and interrupt/resume; no sanitizer/race findings in supported checks; sustained throughput gain within the combined memory limit. Choose separate baseline, terrain and verifier allocations from measurements.

**C1a. Concrete resource profiles for this Xeon host.**

| Workload | Initial configuration or trial | Status |
|---|---|---|
| Baseline only; no simultaneous verifier | Current 30 processes × 1 numerical thread | Existing baseline default; historical measurements, not current mixed-load certification |
| Baseline plus one BDS verifier | Trial 12 processes × 1 thread, with 4 BDS vCPUs / 6 GiB container / 8 GiB VM reservation; compare 16×1 and 24×1 | Conservative first mixed-load measurement; not a configuration change in this planning task |
| Native terrain plus one BDS verifier, after C1 support exists | Start trial at 6 processes × 2 native threads; compare 8×2, 12×2, 14×2 and 16×2 | Experimental process/thread grid; retain one BLAS/numerical-library thread per process |

The suggested 14×2 configuration creates 28 native threads, plus verifier and orchestration work. There are 18 physical cores / 36 logical threads; SMT threads are not independent physical cores, and arithmetic thread counts do not reserve CPU capacity or guarantee memory headroom. Dedicated cores would require separately supported affinity/isolation; macOS VM scheduling must be measured.

Measure scanner/terrain process-tree RSS, parent buffers, per-thread native scratch and verifier/VM accounting together. Add the 8 GiB VM reservation once; do not count both its full reservation and its included 6 GiB container as separate allocations. Pause dispatch above the 25 GiB target and stop new dispatch at the 30 GiB ceiling. These are task budgets, not OS OOM thresholds. Existing monitor stop/drain behavior remains mandatory. Choose a combined default from sustained useful throughput, BDS latency and memory peaks; no 14×2 optimum or 30-worker OOM claim is established by the retained data.

**C2. Revisit SIMD only after a successful scalar kernel exists.**

1. Capture `-Rpass=loop-vectorize`, `-Rpass-missed=loop-vectorize`, `-Rpass-analysis=loop-vectorize` and disassembly. Identify actual packed work and remaining gather/branch costs.
2. Prototype strict ISA variants in isolated architecture-specific translation units only after hardware and OS vector-state checks. The measured host supports AVX2; XCR0=7 does not enable AVX-512 state, so do not execute an AVX-512 variant here. Retain a portable baseline. Preserve universal2 build compatibility or explicitly document an x86_64-only build.
3. Keep scalar operation/rounding policy and reject unproved fast-math/FMA changes. If any numerical change is intentional, treat it as a new predictor requiring independent accuracy calibration, not a transparent optimization.
4. Measure full workloads after reuse, including early exits, compiler overhead, sustained clock behavior and mixed land/water batches.

**Output/gate:** exact public/raw-density parity for a transparent optimization and a reproducible end-to-end gain larger than timing variability. Do not require SIMD completion to proceed if it fails this gate.

### Phase D — prove a native lower32 selection strategy

**D0. Bring bounded Tier-0 feasibility forward after A1.**

1. Specify a coarse raw-layout funnel for the current contract and an equivalent control before scanning billions. Test necessary raw Village/Ancient City availability, broad initial Fortress availability, and final Fortress/Bastion compatibility across the **entire possible Stronghold-center domain**. Overworld and Nether regions use their respective units; a fixed box at origin cannot substitute for the unknown final anchor.
2. Form candidate-center sets using exact border helpers, union the possible centers for each relevant raw start, and intersect required-family possibilities. Preserve half-open boundaries and fractional Nether-center conventions. Independent structure existence in broad envelopes does not establish a jointly satisfiable center; Village placement alone does not supply a Stronghold.
3. Retain the distinction between necessary bounds relative to the pinned placement predictor and actual-generation absence. Initially run the filter in shadow/ranking mode. Only a proved safe condition for the declared supported model may become a predictor filter; unresolved game compatibility stays visible/recoverable.
4. Use a finite diagnostic cohort (for example 4096 distinct raw layouts) with measured raw cost/selectivity, independent full64 siblings and boundary/adversarial controls. Include Ancient City, which the historical 256-layout three-family diagnostic did not test. Do not extrapolate that historical result to the new contract, or accept 99.9% rejection without new evidence.
5. Measure a minimal batching prototype before the full native scanner/ranking architecture. If selectivity and parity pass, D1–D3 may become the front door of a staged run. If broad bounds reject little, use layouts to prioritize full64 siblings and keep independent full64 exploration.

**Output/gate:** exact coarse-filter specification, bounded selectivity/parity report and an explicit Tier-0 adopt/defer decision. D0 is P1 after A1 and can precede large concurrency/native-sweep work; full-range launch still requires D2/D3 and relevant readiness gates. This moves useful feasibility work earlier without accepting an unmeasured full-sweep promise.

**D1. Specify the search objective and seed dependencies.**

Use `backend.RAW_MT_TYPES` as the allowlist: Village, Ancient City, Ruined Portal, Shipwreck, Monument, Outpost, Fortress and Bastion raw placement. Keep Stronghold iteration, Trial Chamber, Mineshaft, viability, biomes and terrain outside lower32-only equivalence. Inspect each family's configuration/mixing before native specialization; Java seed-search shortcuts are not automatically valid here.

The existing [staged selector](src/seed_search/staged.py) targets historical movable-center geometry and is not a drop-in schema-5 implementation. A new selector must support Stronghold-anchored full64 evaluation. Raw lower32 anchors are not known actual Stronghold centers. Any center-envelope rejection must prove impossibility for **all** permitted anchors; otherwise use the metric only to rank.

**D2. Build `ss_sweep_raw` as a bounded, resumable adapter.**

1. Define a versioned API with a uint64 start/count/end representation for `[0,2**32)`, explicit families/regions/bounds and finite output capacity. Avoid overflow at the final lower32 value. Separate scan coverage from retained output count.
2. Reuse pinned MT/placement semantics, including seed mixing, modulo behavior, negative region conversion, typed Fortress/Bastion selection, ordering and tie breaks. Optimize proven shared calculations without replacing the RNG algorithm.
3. Use per-thread bounded heaps or chunked outputs and deterministic merging. Include top-ranked and independently sampled exploration layouts; document quota/tie rules. Account for explored rejected layouts without storing one large Python/SQLite row per raw seed.
4. Persist completed range leases and output batches transactionally. Resume must neither skip incomplete chunks nor double-count coverage. Change worker/thread counts without changing selected results.
5. For retained layouts, enumerate a declared finite set of distinct high32 siblings and pass each through the existing full64 baseline, V1/V2 and actual verification funnel. Persist submitted versus completed sibling progress separately.

**Output/gate:** parity with `ss_raw_layout` across every allowlisted family, negative/border regions, edge seeds and high32 siblings; deterministic selected layouts and recovery after interruption; bounded memory/storage. Small-range correctness does not prove the full runtime target.

**D3. Measure utility before a full-range launch.**

1. Start with a finite prototype range. Compare staged and independent full64 search under equal CPU/time budgets, identical eligibility and comparable verification selection. Include exploration siblings and an independent reference run key.
2. Record raw layout selectivity, full64 qualification, unresolved Strongholds, terrain diversity, actual verified yield per CPU-hour, verification backlog, bytes retained and unique coverage at every stage. Do not count repeated worker trials or siblings sharing a raw layout as new lower32 coverage.
3. Do not infer zero false-negative selection from retained top layouts. Estimate missed opportunity with held-out/exploration controls and retain explicit bias/recall limits. If it does not improve useful yield, keep full64 enumeration as the primary strategy.

**D4. Treat Metal as optional follow-up.**

Only proceed if D3 identifies raw CPU enumeration as the remaining limiter. Validate the Vega 56 device's integer/atomic capabilities, MT state cost, register pressure and exact arithmetic. Compare raw positions/masks with CPU before performance measurements, then include transfers, output compaction and checkpoints. No terrain GPU port or sub-five-minute promise follows from a successful MT microbenchmark.

### Phase E — scale with explicit launch and stop gates

1. Publish a schema-5 readiness report tied to current source/native/config/runtime evidence. Keep prediction-only exploration and verified Realm eligibility visibly separate. A `--prediction-scale` option is an explicit prediction mode, not evidence that accuracy gates passed.
2. Extend existing terrain-raster disk enforcement to baseline growth, SQLite/WAL overhead, BDS worlds/snapshots and exports. Add projected growth/backlog checks, bounded shards, lossless compact storage and reviewed retention of recoverable pending records. Preserve exact input/lease coverage and evidence pointers through sharding/compaction; never silently discard uncertain seeds to fit the disk.
3. Fault-test worker death, parent interruption around commit, full disk, corrupt/incompatible cache, interrupted export/rescore, failed BDS cleanup and retry exhaustion. Confirm no missing completed ranges, duplicated anchors, stale eligibility or leaked verification attempts.
4. Use a bounded ladder after the relevant tests/reference gates pass: smoke → matched small pilot → sustained finite shard. Advance only with measured throughput, memory, disk/backlog headroom, stable verified yield and recoverable incomplete work. Larger timing experiments and actual generation remain separately budgeted future work.
5. Review generated finalists for real structure access, natural build areas, whole-formation border fit and exact Nether requirements. Phone/PC visual review supplements recorded exact-build evidence; it does not substitute for missing region coverage.
6. Seal the actual finite launch command, configuration, input range, output shard, resource limits, stop rules, recovery commands and remaining accuracy/recall limitations. Report the best evaluated finalists, never the best of the entire 64-bit seed space.

**Output/gate:** reproducible finite launch package and a status report showing which accuracy gates passed. Stop dispatch on insufficient disk/memory, unbounded verifier backlog, identity mismatch or unrecoverable evidence failure while preserving completed work and pending tasks.

## 5. Measurement and forecast rules

For each optimization use the same seeds, pool revision, query points, terrain resolutions, budgets and evidence policy. Alternate run order; use at least three trials for timing-sensitive decisions and report spread. Separate cold/warm caches, initialization, analysis, checkpointing, exports and actual verification. Compare complete semantic outputs, allowing only declared timing/PID/cache-work differences. Do not add inclusive native timings to their caller timings or multiply unrelated stage speedups.

Maintain two correctness tracks:

1. **Predictor parity:** unchanged outputs relative to the corrected frozen backend. This protects reproducibility and detects optimization regressions.
2. **Game accuracy:** comparison with pinned actual Bedrock evidence on supported complete regions. This detects errors already present in the predictor. Passing track 1 does not imply passing track 2.

For a raw sweep, `seconds = raw_layout_count / measured_raw_layouts_per_second`. Scanning all `2**32 = 4,294,967,296` lower32 values in 45 minutes requires approximately **1.591 million complete raw-layout evaluations/s**; five minutes requires approximately **14.317 million/s**. Those are aggregate targets for the fully specified filter/ranking workload, not current measurements or predictions.

For selected full64 processing, budget separate baseline, terrain and verification queues. With overlap, wall time depends on the bottleneck queue; without overlap, sum stage costs. Include startup, persistence, retries and review. The [retained resource forecast](runs/realm-implementation-2026-10-10/RESOURCE_FORECAST.md) projects about 30.43 TiB for a billion inputs under historical storage behavior, excluding terrain/BDS. It is an arithmetic warning about that retention model, not a measurement of future compact native output or current-source throughput.

Do not convert historical rates into an unqualified current ETA. The completed planning review did not require a new benchmark. The execution request recorded at the top authorizes matched small pilots and exactly one million-input benchmark; a production sweep remains a separate launch.

## 6. Action queue and dependency order

| Priority | Task | Main code/evidence location | Required result | Depends on |
|---|---|---|---|---|
| P0 | A1: live baseline/identity | native, vendor, tests, capability reports | Frozen evidence and regression log | Current checkout |
| P0 | A2: structure authority/recovery | tracer, Realm verification/runner/store | Supported actual evidence and recoverable anchors | A1 |
| P0 | A3/A3a: natural references and terrain-error attribution | BDS column policy, calibration, surface/terrain | Complete actual controls and demonstrated causes, not assumed aquifer offsets | A1; supported actual provider |
| P1 | B1/B2/B2a: profile, exact Y-noise reuse and native quart deduplication | bridge, pinned density source, raster/cache | Exact parity, preserved warm-cache behavior and useful measured speedup | A1 |
| P1 | D0: early Tier-0 feasibility | raw-layout adapter, bounds, staged experiments | Current-contract joint-center/selectivity report and adopt/defer decision | A1; D2/D3 before full launch |
| P1 | B4a: durable priority scheduler | terrain/store/verification selection | Faster useful discovery, bounded heap and preserved fairness/recovery | B1; A1 identity |
| P1 | Actual overlap/Nether reuse | verification, durable store | Reuse under exact seed/build/settings/channel/coverage identity; valid retry/settling | A2/A3 evidence rules |
| P1 | E2/E3: extend disk/backlog/crash controls | runner/store/raster/verification/reports | Whole-run bounded retention and recovery evidence beyond existing raster caps | A1 |
| P2 | B3/B4: coast overhead/heuristic research | legacy terrain; shadow reports | Profile-justified gain or measured scheduling benefit | B1; A3 for game-error claims |
| P2 | C1/C1a/C2: threading, explicit mixed-load profiles and SIMD | bridge/build/runtime policy | Optional acceleration passing parity/resource gates | B2/B2a |
| P2 | D1/D2/D3: lower32/high32 selection | native adapter; new Realm staged integration | Resumable correct selector and measured useful yield | A1; A2/A3 for actual yield |
| Optional | A2a: Fortress/Bastion distance/contact/access | actual Nether structure evidence | Separate measured geometry/access diagnostics without an added rejection rule | A2; supported generated footprints |
| P3 | D4: Metal prototype | Separate experimental GPU adapter | Integer parity and full-workload gain | Successful D3 |
| Launch | E1/E4/E5/E6 | New schema-5 readiness/launch report | Explicit finite run with supported evidence and honest limits | Relevant P0/P1 gates; winning optimizations only |

Immediate next implementation work is **A1–A3/A3a plus B1/B2/B2a**, with **D0's early feasibility check and B4a's scheduler** included before scale-up. Resource/recovery gates follow. OpenMP, SIMD, a full lower32 sweep and Metal are optional measured branches. Their absence does not prevent a useful calibrated CPU search; their presence does not certify accuracy.

## 7. Historical verification of the planning review

The review reads the live source and retained evidence, checks primary technical documentation, reruns the existing regression suite, checks document links and preserves implementation/configuration/native hashes. Terminal results and the final review manifest are saved under [runs/plan-review-2026-10-10](runs/plan-review-2026-10-10). No production source/native optimization, BDS generation or large seed benchmark is part of this review. Full-project accuracy work above remains open until its explicit gates pass.

Fresh terminal result: **567 tests passed in 117.64 seconds, exit 0**, in [tests.log](runs/plan-review-2026-10-10/tests.log). The fresh [compatibility report](runs/plan-review-2026-10-10/compatibility.json) still reports `large_search_ready=False`. This validates the current covered behavior and the review's readiness assessment; it does not close actual structure/formation accuracy gates.

Six-discrepancy follow-up verification is saved under [runs/plan-addendum-review-2026-10-10](runs/plan-addendum-review-2026-10-10): original supplied text, pre-edit roadmap, retained calibration confusion matrix, bounded 256-point native replay, source-preservation hashes and the addendum manifest. This follow-up changes the roadmap and isolated review artifacts only. The 567-test result above belongs to the earlier review; it is not a newly run suite for this documentation edit. No native timing benchmark, BDS request, production implementation or world-border configuration was changed or started.
