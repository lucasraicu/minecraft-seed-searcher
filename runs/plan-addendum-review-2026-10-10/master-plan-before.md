# Master implementation plan: speed, accuracy and validation

Reviewed 10 October 2026 against the live checkout, the Gemini research brief, existing experiments, and the current Realm implementation. **Recommendation: adopt this revised roadmap; do not implement the supplied plan unchanged.** This document completes the requested planning review. It does not claim that the project is fully verified, authorize new large benchmarks, or start a sweep.

The supplied plan has the right goals: eliminate repeated work, measure native acceleration, and verify finalists in the real game. Its ordering, safety claims, performance promises, and description of the current system need correction. Accuracy work starts before scale-up and continues alongside optimization. Exact work reuse comes before additional parallelism. A raw lower32 layout scan is a selection experiment, not exhaustive world validation.

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

Each task produces code, relevant verification, and a saved evidence report. Promote an optimization only after its gate passes. These are future implementation tasks; this review does not execute them.

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

**A3. Complete natural-ground and formation references.**

1. Extend the existing BDS column policy with natural-ground/structure provenance. Preserve primary/overlay water, cover, settling and unknown-state handling already tested; address fractional fluid height if used by a geometry requirement.
2. Obtain complete natural V1 and V2 positive and negative regions, with evaluator halos. Include narrow bridges/peninsulas, closed wide lakes, open ocean, elevated lakes, connected ridges versus disconnected hills, jagged V2 interiors, negative coordinates and chunk edges. Controlled placed-block fixtures validate interpretation, not natural terrain suitability.
3. Start with at least two complete positive and two complete negative formations per variant as engineering controls. They must be independently labeled from actual evidence and remain separate from a later held-out/random calibration cohort. If suitable complete examples are unavailable, report that gate as open.
4. Use `realm/calibration.py` on stable known requested-lattice cells. Measure height errors, water confusion, coast connectivity, whole-formation border fit, ridge relief/continuity, score ordering and false negatives. Exclude partial/mismatched observations from complete-formation accuracy claims.
5. Define acceptable errors and recall/precision targets before evaluating held-out controls. Report denominators, selection probabilities and uncertainty. Adjust scheduling/score calibration transparently; keep eligibility requirements intact.

**Output/gate:** reproducible actual reference corpus and calibration report. A verified terrain result requires complete actual water and natural-ground evidence at the resolution required by the evaluator, complete relevant footprints/halos and all mandatory evidence. Unknown cells cannot become land, water or absence through interpolation.

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

**B3. Batch only proven coast/transfer overhead.**

1. If B1 shows material overhead in legacy `terrain.coast_component`, measure its masks, repeated dilation/erosion, point generation and CFFI transfer separately from density work. Confirm whether that legacy path is part of the intended run.
2. Prefer compact batched buffers, deduplicated point requests and existing cache hits first. Keep SciPy morphology unless a native alternative wins.
3. If a C frontier implementation is justified, preserve the current neighborhood, step, sampled mask, stop condition, finite patch bounds, anchor selection and deferred states exactly. Bound its allocations and expose cancellation/status.
4. Replay thin bridges, separated islands, newly revealed connections and patch-boundary cases; compare masks/components and complete results, not only scores.

**Output/gate:** measured end-to-end gain with unchanged topology. An optimization used only by historical branches cannot be advertised as a schema-5 improvement.

**B4. Keep approximate prefilters in shadow mode.**

Record the `approx_height` proposals and conditional false negatives on actual controls and random recovery samples. Use them to prioritize work, never to permanently delete baseline survivors. A hard negative requires a proved necessary bound for the declared model/coverage. Sea-level uncertainty can prioritize verification or inform an explicitly versioned score; it cannot establish invalid terrain by itself.

### Phase C — add concurrency and SIMD only where they win

**C1. Evaluate native threading after B2.**

1. Audit all called sampling routines for mutable state. Initialize terrain/shaper before entering the team, preserve spline ownership, give scratch data/outputs distinct per-column storage, and prohibit concurrent close/reseed/use of one handle outside its ownership contract. Existing MT state is thread-local; each new thread must establish its own required seed/state rather than assume inheritance.
2. Add an optional OpenMP build/runtime path with explicit compile/link/load checks and a serial fallback. Do not silently change `numeric_threads_per_worker=1`; introduce an explicit versioned native-thread policy and checkpoint/runtime identity.
3. Parallelize outer columns, not early-exit Y loops. Use a batch-size threshold; begin with static scheduling, then compare alternatives for irregular water/land costs. Turn nested numerical parallelism off and account for BLAS/SciPy/Docker activity.
4. Compare process × native-thread combinations such as `30×1` for baseline, and `18×1`, `12×1`, `6×2`, `6×3`, `4×4` for matched terrain work. Treat these as trial points, not recommended defaults; leave CPU headroom when BDS runs.

**Output/gate:** identical arrays/candidates/counters across thread counts, cold seed histories and interrupt/resume; no sanitizer/race findings in supported checks; sustained throughput gain within the combined memory limit. Choose separate baseline, terrain and verifier allocations from measurements.

**C2. Revisit SIMD only after a successful scalar kernel exists.**

1. Capture `-Rpass=loop-vectorize`, `-Rpass-missed=loop-vectorize`, `-Rpass-analysis=loop-vectorize` and disassembly. Identify actual packed work and remaining gather/branch costs.
2. Prototype strict AVX2 and AVX-512 variants in isolated architecture-specific translation units. The current Xeon exposes both feature sets, but shipping dispatch must also verify OS vector-state support and retain a portable baseline. Preserve universal2 build compatibility or explicitly document an x86_64-only build.
3. Keep scalar operation/rounding policy and reject unproved fast-math/FMA changes. If any numerical change is intentional, treat it as a new predictor requiring independent accuracy calibration, not a transparent optimization.
4. Measure full workloads after reuse, including early exits, compiler overhead, sustained clock behavior and mixed land/water batches.

**Output/gate:** exact public/raw-density parity for a transparent optimization and a reproducible end-to-end gain larger than timing variability. Do not require SIMD completion to proceed if it fails this gate.

### Phase D — prove a native lower32 selection strategy

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

Do not convert historical rates into an unqualified current ETA. No new 10,000/100,000/million-input benchmark or full sweep is needed to finish this planning review.

## 6. Action queue and dependency order

| Priority | Task | Main code/evidence location | Required result | Depends on |
|---|---|---|---|---|
| P0 | A1: live baseline/identity | native, vendor, tests, capability reports | Frozen evidence and regression log | Current checkout |
| P0 | A2: structure authority/recovery | tracer, Realm verification/runner/store | Supported actual evidence and recoverable anchors | A1 |
| P0 | A3: natural V1/V2 reference corpus | BDS column policy, calibration, surface/terrain | Complete positive/negative actual formations | A1; supported actual provider |
| P1 | B1/B2: profile and exact Y-noise reuse | bridge, pinned density source, raster/cache | Exact parity and useful measured speedup | A1 |
| P1 | Actual overlap/Nether reuse | verification, durable store | Reuse under exact seed/build/settings/channel/coverage identity; valid retry/settling | A2/A3 evidence rules |
| P1 | E2/E3: extend disk/backlog/crash controls | runner/store/raster/verification/reports | Whole-run bounded retention and recovery evidence beyond existing raster caps | A1 |
| P2 | B3/B4: coast overhead/heuristic research | legacy terrain; shadow reports | Profile-justified gain or measured scheduling benefit | B1; A3 for game-error claims |
| P2 | C1/C2: native threading/SIMD | bridge/build/runtime policy | Optional acceleration passing parity/resource gates | B2 |
| P2 | D1/D2/D3: lower32/high32 selection | native adapter; new Realm staged integration | Resumable correct selector and measured useful yield | A1; A2/A3 for actual yield |
| P3 | D4: Metal prototype | Separate experimental GPU adapter | Integer parity and full-workload gain | Successful D3 |
| Launch | E1/E4/E5/E6 | New schema-5 readiness/launch report | Explicit finite run with supported evidence and honest limits | Relevant P0/P1 gates; winning optimizations only |

Immediate next implementation work is **A1–A3 plus B1/B2**, followed by resource/recovery gates. OpenMP, SIMD, a full lower32 sweep and Metal are optional measured branches. Their absence does not prevent a useful calibrated CPU search; their presence does not certify accuracy.

## 7. Verification of this planning review

The review reads the live source and retained evidence, checks primary technical documentation, reruns the existing regression suite, checks document links and preserves implementation/configuration/native hashes. Terminal results and the final review manifest are saved under [runs/plan-review-2026-10-10](runs/plan-review-2026-10-10). No production source/native optimization, BDS generation or large seed benchmark is part of this review. Full-project accuracy work above remains open until its explicit gates pass.

Fresh terminal result: **567 tests passed in 117.64 seconds, exit 0**, in [tests.log](runs/plan-review-2026-10-10/tests.log). The fresh [compatibility report](runs/plan-review-2026-10-10/compatibility.json) still reports `large_search_ready=False`. This validates the current covered behavior and the review's readiness assessment; it does not close actual structure/formation accuracy gates.
