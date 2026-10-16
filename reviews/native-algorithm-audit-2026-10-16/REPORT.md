# Native engine and algorithm audit — October 16, 2026

> Follow-up: N1 and N2 were fixed and the Mansion bounds optimization was deployed later on October 16. See [IMPLEMENTATION.md](IMPLEMENTATION.md). The findings below document the audited pre-fix snapshot.

## Verdict

**There is a measured, substantial optimization available: tighten raw feasible-center bounds using every possible Mansion.** An isolated implementation improved median compact kernel throughput from **56,944 to 87,494 seeds/sec (1.54×)** on three matched cohorts. This is a local benchmark result, not a promise of production throughput or a proof of complete predictor recall.

Correctness has improved since the earlier framework audit: the known natural survivor now agrees at **296 points** across native, independent Python, and same-policy rescore. However, this audit reproduced two defects: the disabled-preflight control silently rejects a valid compact survivor, and Top-K recovery can erase the leaderboard while the saved candidate remains in the database.

The most useful next work is: repair those defects, productionize and regression-test the tighter bounds, retain large native batches, and investigate Mineshaft/Mansion inventory costs. Hand-written SIMD and continuously shared cutoff updates are lower priorities.

## Scope and reproducibility

Audited the dirty working tree based on `173765c3723cd56741304b68034adc7f8e3bb20c`, not the older commit named in `AUDIT_CONTEXT.md`. Existing user changes were preserved. All experimental C changes and builds are isolated under this directory; no experimental kernel was deployed. Source hashes are in `source-hashes.json`; each private build records compiler, flags, source hashes, and binary identity.

Coverage: structure preflight, split noise initialization, event geometry, center snapping/selection, score arithmetic and bounds, full/compact retention, threads/batches, native allocations, tracker persistence/recovery, Python integration, and frontend contracts. Tests and bounded experiments cannot certify every possible seed, absence of every memory race, or agreement with actual Bedrock generation. No BDS/world-generation verification was run. Address/undefined-behavior sanitizers covered the extracted geometry helpers, not the entire CFFI/OpenMP/backend stack.

## Reproduced correctness findings

### N1 — High: disabling preflight breaks split noise initialization

`native/blueprint_dynamic.inc:777–919`; `build_disabled.py`, `disabled.json`.

`NB_DYNAMIC_PREFLIGHT=0` returns immediately from `nb_dynamic_raw_preflight()`. Compact evaluation then calls `applySeedPhase2()` without initializing Phase 1 for that seed. Phase 1 normally runs inside preflight. Full mode initializes the whole generator, so the two modes disagree.

For seed `-3336796033057908633`, with the supported empty Overworld palette:

| Build | Full | Compact |
| --- | --- | --- |
| Preflight disabled, current implementation | center (-480, 0), score 296 | rejected |
| Preflight disabled, explicit Phase 1 initialization restored | center (-480, 0), score 296 | center (-480, 0), score 296 |

This is a defect in the optional diagnostic/control build, not a reproduced rejection in the default preflight-enabled build. It invalidates using the existing disable flag as an independent correctness/performance control. Fix initialization ownership and test alternate initialization/filter paths with real survivors and changing seed order. The no-preflight timings below use the corrected control.

### N2 — High: Top-K resume can silently discard an already discovered leader

`src/seed_search/realm/native_batch.py:547–555,638–663`; `recovery.py`, `recovery.json`.

The pipeline loads only `top50.json`, catches every load exception, and continues with an empty tracker. It does not reconstruct the tracker from saved candidates or `top_candidates`. Range commits and tracker snapshots are separate operations; periodic tracker snapshots also depend on a progress callback being supplied.

Reproduction in an isolated two-seed manifest run:

1. Process the natural 296-point survivor and stop after one input: tracker contains one candidate.
2. Replace its tracker JSON with an invalid checkpoint.
3. Resume and process the second input.
4. Completed coverage becomes 2/2; JSON and SQLite `top_candidates` both become empty. The canonical store still reports one saved seed row.

The underlying candidate is recoverable, but the displayed/running Top-K is wrong. A stale valid checkpoint can similarly omit committed candidates. Restore from the canonical committed store, or atomically checkpoint tracker state and range coverage in one database transaction. Never silently turn unreadable state into an authoritative empty leaderboard. Test abrupt termination, stale/missing/corrupt JSON, pending prepared results, and changed capacity.

### N3 — Medium: score-only cutoff assumes a homogeneous ranking tier

`src/seed_search/realm/top_tracker.py:79–148,199–206`; `probes.json`.

Rank ordering compares tier before score. A tracker containing a tier-2 score-900 record reports cutoff 900, yet correctly admits a tier-0 score-100 record. A native score-only cutoff of 900 would reject the latter before its better tier could be compared. This is a demonstrated API invariant mismatch; this audit did not show mixed tiers entering the ordinary fresh native v3 pipeline.

Constrain the tracker/cutoff to homogeneous eligible native predictions, validate restored records, or include the higher-priority rank dimensions in pruning. Equal scores must remain eligible; current native comparisons use strict `<`, correctly preserving equal-score tie-break opportunities.

A smaller reproduced adapter bug: observing numeric seed `0` twice creates two entries because `_extract_seed()` uses truthiness and converts zero into an empty key. Native records normally use decimal strings, so this is an input-normalization gap rather than a demonstrated normal-run duplicate.

### N4 — Documentation is not a reliable executable specification

The audit dossier says ±512 centers; current blueprint, native code, Python, and tests use **±976**. Its scoring table differs from its own pasted C functions, and its mountain/ocean scenic description differs from the active scenic/river code. It also describes React 18 and Clang 19, whereas this checkout uses React 19 and the measured private builds used Apple Clang 17.

The active blueprint still contains older biome-shortcut/performance claims. Native palette construction explicitly samples 63 × 63 × 4 = **15,876** Overworld points when reached; it does not implement all the claimed witness-based early exits. Structure presence cannot automatically replace the configured lattice witness requirement.

Use the versioned config, code, and tests to generate the dossier. Keep design targets and measured implementation behavior visibly separate. No independent evidence here establishes the dossier's “less than one in 2.5 billion” estimate.

## Measured performance experiments

All arms use isolated builds of the same snapshot, Apple Clang 17, `-O3`, AVX2/FMA, native targeting, LTO, OpenMP, and **no PGO**. This avoids comparing differently built historical kernels. The checked `runs/dynamic-baseline-2048/native` identity likewise records no PGO; its binary differs from the packaged extension. `build-identity.json` preserves those facts. Do not assume a PGO build from the dossier's title.

The host also ran suite/build work and normal desktop processes. Arms were interleaved in deterministic randomized order, with matching seed cohorts and warm-up. Results are short local kernel-loop measurements including seed-buffer creation/teardown, not idle-host or durable production measurements. The small differences below should not be interpreted as wins.

### Initial controls: 3 × 65,536 inputs per arm, 34 threads, batches of 16,384

| Arm | Median seeds/sec | Range | Interpretation |
| --- | ---: | ---: | --- |
| Current snapshot | 57,412 | 56,267–57,704 | Control |
| Raw order: Mansion, Ancient City, Trial Chamber, Village, Outpost | 58,024 | 56,716–58,139 | ~1%; inconclusive |
| Atomic work-claim chunk 64 instead of 16 | 55,171 | 53,855–56,146 | No improvement; retain 16 |
| Preflight disabled, initialization repaired | 48,851 | 48,402–49,512 | Current preflight is useful; ~18% faster than this control |

Ordering should account for cost and conditional rejection probability, not just global rarity. The proposed rarity order did not deliver a material gain in this experiment.

### Bounds and memory experiments: 3 × 131,072 different inputs per arm

| Arm | Median seeds/sec | Range | Median process peak RSS |
| --- | ---: | ---: | ---: |
| Current snapshot | 56,944 | 53,280–58,282 | 103.2 MB |
| Keep only the best center while scanning | 57,659 | 53,019–58,356 | 96.8 MB |
| Tighten feasible bounds with all possible Mansions | **87,494** | **77,533–88,434** | 102.6 MB |

Matched-cohort speedups for tighter bounds were approximately **1.50×, 1.55×, and 1.46×**. Ratio of medians is 1.54×. All three cohorts improve substantially, despite host noise. These experiments retained no default-palette candidates; positive-path validation was performed separately.

#### Why the Mansion bound helps

Current raw preflight derives a bounding rectangle from Nether-feasible centers and checks whether *any* Mansion overlaps it. It still inventories Overworld structures across the full enclosing rectangle.

`build_tight.py` intersects each Nether-feasible center cell with each possible dark-Mansion capture interval, snaps the intersection inward to valid 8-block centers, unions **all** resulting center regions, and expands the final bounding rectangle by the Overworld half-width. It does not select one arbitrary Mansion or incorrectly intersect mutually alternative Mansion windows.

Across 393,216 inputs, all-structure macro survivors fell from **1,516 to 443**, while both versions found the same **four structure-feasible seeds** and zero palette-qualified seeds. The known natural survivor preserved center and score. Both positive synthetic and natural paths passed; the new bounds also matched exhaustive brute force on 300 random Nether/two-Mansion configurations.

Recommendation: this is the strongest candidate to productionize. Add permanent union/edge tests, a larger positive-survivor corpus, full evidence comparisons, and held-out durable benchmarks before release. The audit's standalone build is a reviewable prototype, not a deployed change.

#### Keep one best center instead of an entire cell array

The current selector appends scored centers, then scans the array for the winner; it already avoids a full sort. `build_stream.py` retains only the best center using the same comparator. This removes `O(number of event cells)` candidate storage while preserving the comparator's first-winner behavior.

Observed RSS decreased modestly; throughput did not materially improve. Favor it as a memory/simplicity improvement. It does not eliminate event-grid traversal or repeated structure counts.

### Batch and thread observations

Single exploratory cohort, 32,768 inputs; do not treat this as a complete tuning study:

| Threads | Batch size | Seeds/sec |
| ---: | ---: | ---: |
| 1 | 16,384 | 3,469 |
| 8 | 16,384 | 23,147 |
| 18 | 16,384 | 42,632 |
| 34 | 1,024 | 14,756 |
| 34 | 4,096 | 35,118 |

The 34-thread, 16,384-batch controls above were around 57k/s on other cohorts. Do not shrink batches just to propagate a cutoff more often. Each call creates/destroys OpenMP worker contexts and their scratch caches; that overhead and smaller scheduling opportunities matter. A 32,768-input batch was correctly rejected by the public 16,384 cap, not measured as throughput.

### Where time goes

An isolated single-thread diagnostic aggregated existing stage timers before compact rejects were cleared: 16,384 inputs, 4.675 seconds of evaluator time (`timing.json`). Approximately:

- Mineshaft stage: **28.1%**.
- Mansion macro work: **22.5%**.
- Combined raw preflight / Nether stage bucket: **17.8%**.
- Shipwreck: **8.1%**.
- Desert Pyramid: **4.6%**; Monument: **4.1%**.
- Stronghold discovery: **3.7%**.
- Event-cell/palette/scoring bucket: **0.5%** on this mostly rejected cohort.

Existing buckets mix preflight and Nether work, and some initialization/early-exit work is outside the individual buckets; they account for about 96% of measured evaluator time. These are diagnostic CPU-time proportions for one cohort, not exclusive production-wide stage profiles or a survivor-cost forecast.

The result supports reducing inventory regions and rejecting impossible co-windows before expensive remaining inventories. It does not support spending the first optimization effort on final bonus arithmetic.

## Algorithm, bounds, and concurrency assessment

### Top-K cannot solve initial zero yield by itself

The pipeline still requires all floors and selected palettes. It compares qualified survivors only. Before K candidates exist, there is no learned cutoff. In v3 the early macro/cell bound is `core + 600`; a score cutoff at or below 600 cannot prune those stages at all. Later bounds become tighter after palette/optional work.

A live global atomic cutoff would at most reduce batch propagation delay once sufficiently good survivors already exist. It would not reduce the work of finding the first qualifying seeds. The current call-local copied policy is simpler and avoids mutating policy during a CFFI call. Keep batch-boundary propagation until survivor yield and cutoff effectiveness demonstrate a need for something more complex.

If closest failures are desired, they need an explicit separate ranking and bounded diagnostic sampling strategy. Removing hard thresholds wholesale would force expensive biome/inventory work on vastly more seeds. Keep safe impossibility filters; record useful shortfalls only for an explicitly chosen bounded population.

### Event geometry is sound in tested cases; global bonus optimality is not proved

The extracted native helpers passed:

- 200,000 randomized interval/snapping cases, with positive and negative centers and 8/16 steps.
- 300 exhaustive 245 × 245 center-grid checks of Nether counts and feasible bounding rectangles.
- Another 300 exhaustive grids including the proposed union of two Mansion capture regions.
- AddressSanitizer and UndefinedBehaviorSanitizer on those helper executables.

The allowed 8-block grid is [-976, 976]². No tested snap left its interval. Nether count predicates agree with direct half-open bounds on that grid; this does not claim equivalence for arbitrary unsnapped coordinates.

The production solver chooses constrained centroid representatives within event cells. Structure membership and sampled biome masks are constant within those cells, but hub distances, scenic radius tests, optional structures, and village spread can vary inside them. Thus it does not inherently maximize all bonus points over every allowed center.

An isolated build adding every 8-block center boundary returned the same winner for the known natural survivor and one positive fixture. That is useful spot coverage, not proof of global optimality. Expanding the center search would change the blueprint's representative-selection objective; treat it as a deliberate product/algorithm choice, not an automatic correctness fix.

### Allocation and threading

Workers are automatic locals inside the OpenMP parallel region, with distinct generator and scratch ownership. The proposed blanket alignment of an array of adjacent `NBWorker` objects addresses a layout that this implementation does not have. Aligning a pointer variable also does not align the pointed-to allocation.

The inspected event-buffer growth allocates replacements before releasing old buffers and cleans up partial failures. Cell capacity has an explicit limit; the monotonic allocation budget fails the batch instead of silently returning partial successful coverage. That budget measures cumulative reserved allocations, not exact live RSS, so dense/large batches can fail conservatively. Repeated allocation/free costs and per-call worker lifetime remain plausible improvements; measure a persistent-worker design before accepting its added concurrency complexity.

Diagnostic counters are global and increment atomically, but `nb_diag_reset()` and `nb_diag_get()` use ordinary accesses. They are safe as used here after calls have completed; concurrently resetting/reading them during active sweeps lacks synchronization and can mix calls. They must not be used as per-run authoritative live counters without redesign. No ThreadSanitizer run was performed.

### SIMD and PGO

AVX2/FMA flags do not prove that octave sampling is efficiently vectorized. Independent octave evaluations can be batched, but permutation lookups, differing octave state, and floating-point accumulation order complicate the implementation. An arithmetic rearrangement near a biome decision boundary can change acceptance. No handcrafted SIMD speedup was measured here.

Train PGO on the corrected current policy with a mixture of ordinary rejected seeds and real survivor paths, then benchmark held-out cohorts against a same-source non-PGO build. Do not promote a historical profile or imply a fixed speedup without measurement.

## Validation results and limits

- Full Python suite: **1,168 passed, 1 failed in 371.93 seconds**. `tests/test_web_disk_preview.py:62` hardcodes `max_misses=3` after resolving the default v3 config; the CLI correctly rejects it because v3 permits only zero. This stale test must be updated to exercise the intended v3 checkpoint/resume path. It is distinct from the defects N1/N2. See `pytest.log`. An isolated copy changing only the miss budget to zero passed in 1.92 seconds (`test_corrected_cli.py`, `corrected-cli.log`), checkpointing and resuming four inputs within a declared five-billion-input range; no billion-input campaign was run.
- Frontend contract tests: **13 passed**; lint and production build completed successfully.
- **10,000** randomized extracted-C/Python score comparisons: zero mismatches.
- **177** native cutoff fixture cases: zero mismatches against unpruned acceptance filtered by the requested score; includes ties and scores above the maximum.
- Two natural seeds × default/empty Overworld palettes, full/compact, 1/4 threads, four build variants: acceptance/centers/scores agreed. One empty-palette seed exercises an actual positive survivor; neither is asserted to satisfy the default palette.
- The natural survivor agreed at **296** points and center **(-480, 0)** in native, independent Python, and same-policy rescore, including component breakdown.
- Streaming, tightened-bounds, and exhaustive-center experiments preserved the tested natural winner and positive fixture.
- Sanitized helper geometry tests described above passed.
- Public oversized-batch guard behaved correctly; the invalid measurement arm is retained in the log rather than reported as a performance result.

The two benchmark sets contain **589,824 distinct inputs**, reused across arms. Baseline found five structure-feasible seeds and zero full-palette survivors. Repeated arms are not independent observations. This does not establish a precise success probability or justify relaxing any particular floor. The previous report's findings are historical; fixes must be judged against the current source, and this report does not claim every old finding remains open.

## Recommended order of work

1. **Fix disabled-preflight initialization and Top-K recovery**, with the provided positive-survivor regressions and stale/corrupt checkpoint cases.
2. **Productionize Mansion/Nether union bounds** with permanent geometry tests and held-out end-to-end measurements. This is the only tested large throughput gain in this audit.
3. **Keep 16,384-input batches and chunk 16 as the current baseline.** Further thread/batch tuning needs repeated matched cohorts and latency/memory measurements.
4. **Stream the winning center**, mainly to reduce memory and simplify ownership; do not advertise a large speed gain.
5. **Profile and reduce inventory work**, particularly Mineshaft and Mansion. Consider an optimistic partial-structure co-window gate before costly remaining inventories, and preserve all feasible alternatives.
6. **Make tracker eligibility/rank assumptions explicit**, normalize seed identities, and measure how often actual cutoff values prune each stage.
7. **Train current-policy PGO and broaden positive-path differential coverage.** Evaluate SIMD only after profiling identifies the target cost and numerical-parity checks exist.
8. **Generate the audit/spec documentation from the active policy** and clearly separate theoretical upper bounds, observed yield, and unverified world-generation facts.

## Artifact map

`build*.py` and each build's `identity.json` reproduce isolated variants. `measure.py`, `extra.py`, `measurements.jsonl`, `extra.jsonl`, and `summary.json` retain timing/funnel/RSS observations. `geometry*.py`/`.c`/`.log` reproduce sanitizer-backed brute-force checks. `probe.py`, `probes.json`, `survivors.py`, `survivors.json`, `independent.jsonl`, `rescore.json`, and `score-parity.json` retain differential results. `recovery.py`/`recovery.json` and `disabled.json` document the two main defects. `timing.json` records diagnostic stage totals. `pytest.log` and `web-*.log` retain suite/build output.

Use the repository `.venv/bin/python`. Recovery experiments create a run directory; choose a fresh directory when repeating them. Timing instrumentation is intentionally single-thread-only. Builds share an isolated source staging directory and must be run sequentially. Application source was not modified by this audit.

Final source-hash comparison found no changes to audited application sources during the audit. Repository `git diff --check` reports pre-existing extra blank lines at EOF in the two user-modified bundle scripts; these were left untouched.
