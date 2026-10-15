# Native performance decision — 8 October 2026

Status: **test complete; ready to implement the revised plan, not ready to launch a sweep**. This was an isolated pre-implementation experiment. Production source, configuration and installed native binary remain unchanged. Reproduction and raw evidence: [work record](runs/simd-test-2026-10-08/WORK.md).

## Decision

1. Fix the newly reproduced seed -1 Mineshaft initialization defect before optimization or fresh readiness. It affects optional structure records/scores and can depend on worker history; it is separate from the unresolved Stronghold discrepancy.
2. Promote exact quart-cell land reuse through the plan's corrected-baseline parity gates. It reduced the three-seed aggregate analysis time by **28.1%** in this test.
3. Do not ship Gemini's FMA flags or this four-Y SIMD prototype. The former changed raw density; the latter was **1.2% slower after reuse**. Strict AVX2 flags gave only **2.6% additional saving after reuse** here; defer production integration until a new-border multiworker benchmark justifies CPU dispatch/build maintenance. This does not rule out a better future kernel.
4. Keep the approved four categories and bounded lower32/upper32 experiment in the plan. Add early island bounds as a measured shadow-mode experiment, with no automatic conversion of preferences into hard filters.

The current revised implementation reserve is **26–48 engineering hours / roughly 4–6 working days**, including the fourth category, early-island experiment, MT initialization correction and subsequently requested weighted biome diversity. This excludes an unproved Stronghold root fix and substantial new SIMD design. A new-geometry pilot still determines the sweep ETA.

## Scope

Intel Xeon W-2191B, macOS 15.8, Apple Clang 17, Python 3.13.15, pinned vendor revision and unchanged current 3008/992 geometry. Four private native modules: current compiler policy (`scalar`), strict AVX2 flags (`avx2`), Gemini's AVX2/FMA/x86-64-v3 flags (`gemini`), and an explicit four-Y AVX2 kernel (`vector4`). All comparison builds use the same x86_64 host slice. The scalar control is the existing implementation, not an artificially deoptimized build; its compiler may already use ordinary SSE optimizations.

The vector prototype batches four vertical samples. It preserves scalar permutation/gradient lookups and uses packed interpolation/noise accumulation, with FMA disabled. This is a concrete SIMD test, not a claim to cover every possible vector layout, horizontal batching, vertical noise-cell reuse, AVX-512 or ARM/NEON design.

The installed Python defaults to universal2 builds. Gemini's x86-only flags failed on the arm64 compiler slice in the initial attempt. This was corrected only in the isolated harness by setting `ARCHFLAGS=-arch x86_64`; no production build flags or installed native binary were changed. A shipping native optimization still needs CPU/OS capability checks, a scalar fallback and supported architecture builds.

## Micro parity and timing

Six fixed seeds (-1, 0, 9, 12345, 4294979641, -9048740180577658153), each with 384 X/Z probes, heights at strides 1/8/16, associated biomes, land booleans, a 17×17 climate/biome grid, and 1024 raw-density probes. Negative boundaries and vertical endpoints are included. These are sampled checks against the scalar predictor, not a new game-accuracy claim.

- Strict AVX2 and vector4: all compared arrays match exactly, including the vector kernel's 6144 raw-density values.
- Gemini flags: **1162 of 6144 raw-density values differ**, maximum absolute difference **7.510185469072894e-7**. Sampled density signs, heights, land classifications and biome/climate arrays still match. This fails the exact predictor-parity gate; unchanged sampled decisions do not establish safety near every future threshold.
- All 144 micro timing cases produced matching public outputs.

Timing below is the sum of three per-seed median query times; each median uses three rotated-order trials. Negative saving means slower. One-time terrain initialization is excluded equally. Quart grouping and result expansion are included in the quart query time.

| Workload | Scalar seconds | Strict AVX2 saving | Gemini flags saving | Four-Y SIMD saving |
|---|---:|---:|---:|---:|
| Heights, vertical stride 8 | 0.303654 | 1.64% | 3.87% | **−6.71%** |
| Heights, vertical stride 1 | 0.965709 | 3.44% | 5.48% | 5.66% |
| 4096 land columns per seed | 2.497807 | 2.88% | 6.51% | **−7.93%** |
| Same land requests with quart reuse | 0.186993 | 4.09% | 7.02% | **−7.62%** |

These micro timings are not whole-search speedups. In this cohort, scalar quart reuse reduces land-query time by 92.51% including grouping; remaining height work still costs time. The vector prototype can perform extra Y samples before an early exit and still pays scalar lookup costs; those are plausible reasons it loses on some workloads, not separately measured causal attribution.

Disassembly confirms packed operations inside the explicit kernel and FMA instructions in the Gemini variant. Strict AVX2 flags also produce some packed operations inside existing Perlin code; flags alone should not be described as implementing a full four-column density kernel. Clang documents that fused operations can change rounding and that `-ffp-contract=off` disables contraction. [Clang floating-point controls](https://clang.llvm.org/docs/UsersManual.html#controlling-floating-point-behavior).

## Complete-seed comparison

Completed three seeds × scalar/strict AVX2/vector4 × reuse off/on × two reversed-order trials: **36 analyses**. Gemini flags were excluded because raw-density parity already failed. Every run used the same finite nomination budgets and current geometry, cold per-seed caches, one process, no profiling instrumentation and no exports. Exact comparison includes full candidates, scores, near misses, counts and filter policy. Cache work and timing counters intentionally differ.

Median seconds per seed (two trials; these medians are the average of the two observations):

| Seed | Scalar | Scalar + reuse | AVX2 | AVX2 + reuse | Four-Y SIMD | Four-Y SIMD + reuse |
|---|---:|---:|---:|---:|---:|---:|
| -1 | 35.489 | 26.145 | 34.443 | 25.481 | 36.586 | 26.357 |
| 12345 | 64.770 | 38.908 | 63.183 | 37.844 | 67.561 | 39.585 |
| 4294979641 | 77.745 | 62.979 | 74.830 | 61.382 | 79.004 | 63.682 |
| Sum | **178.004** | **128.033** | 172.455 | 124.706 | 183.151 | 129.623 |

Scalar reuse savings range from **19.0% to 39.9% per seed**, with **28.1%** for this combined workload. AVX2 adds 2.6% versus the scalar reuse arm; four-Y SIMD costs 1.2% more versus that arm. Without reuse, AVX2 saves 3.1% and four-Y SIMD costs 2.9% more. Do not add these percentages together.

**Parity qualification:** all variant/reuse arms match their same-trial scalar control, yielding the same ten candidate locations across the three seeds. However, six second-trial seed -1 runs differ from the initial cold-process reference because of the Mineshaft defect below. The original six failed equality flags remain in the raw data. Both other seeds repeat exactly; -1's changed paths are confined to Mineshaft records, their score contributions/intervals and the dependent legacy core-center counter. These timing comparisons match initialization history within each trial; they do not establish production repeatability. [Computed comparisons and individual timings](runs/simd-test-2026-10-08/analysis.json).

All three retained variants pass the existing frozen regression: **880 structure rows, 159 coordinate rows, 874 unique correspondences, six known structure disagreements, zero reused starts, 153 biome matches, height MAE 1 / maximum error 5**. That fixture is historical website evidence, not fresh generated-game validation, and it misses the cold -1 condition. [Regression results](runs/simd-test-2026-10-08/regression-summary.json).

Limits: three selected complete seeds, two repeats, one Intel host, current geometry and existing finite nomination budgets. This is prioritization evidence, not a statistically established whole-sweep multiplier or a new-border/four-category throughput test. The future 2304/928 pilot must use the corrected scalar baseline and include process pools, export costs and holdouts.

## Additional required structure fix discovered by this test

The seed-order check failed for **seed -1 Mineshafts**, including the scalar control. A fresh process using the **unchanged installed production binary** reproduces counts `0, 0, 28, 44, 44` when scanning the same ±1024 square for seeds `-1, -1, 0, -1, -1`. This is a real initialization defect, not an observed SIMD discrepancy. [Exact records](runs/simd-test-2026-10-08/mineshaft-installed-seed-order.json).

In `vendor/cubiomes-bedrock/mt.c`, thread-local `mt_ws` starts at `(uint64_t)-1`; `mt_a`/`mt_b` initially contain zero. In `mt.h`, `setCarverSeed()` initializes those coefficients only when `mt_ws != worldSeed`. Therefore a first query with the valid seed -1 skips initialization; a query for another seed first changes that behavior. Related seeding helpers share the cache. The candidate records under the current 3008-block-side border gain Mineshaft starts and optional score points in the repeated full-seed run; terrain and chosen centers remain unchanged in the compared records.

Required P2 fix: an explicit cache-initialized flag, set after computing both coefficients and preserved by `MTRngState` save/restore. Add fresh-process/thread, seed-order, RNG-state, worker and resume coverage. Version the reviewed native patch and re-establish the corrected scalar baseline before optimization parity/readiness. Do not use a warm-up seed or coordinate exception as the production fix.

The existing frozen regression can pass while this defect remains because its usual seed order initializes the cache before -1. Its passing result must not override the failed cold/warm invariant. This does not diagnose or fix the separate Stronghold disagreement. No production fix was applied during this test.

## Four-category contract and early island filtering

The user confirmed these four independent categories, all requiring Stronghold and Fortress:

1. Structures-only: terrain not required; separate shortlist and structure score.
2. Enclosed inner island: separated island with water and surrounding mountains; branch-specific terrain evidence required.
3. Ocean island: separated island in the required ocean setting.
4. Mountain basin: dry flat connected interior with mountain ring, no inner-island requirement.

The existing code still has three terrain branches. The updated [workflow](SEED_SELECTION_WORKFLOW.md) and [implementation plan](AUDIT_IMPLEMENTATION_PLAN.md) specify the fourth branch and distinct evidence/ranking/counting. They do not relabel failed terrain as a terrain pass.

Gemini's early island filter is now P3b. Start in shadow mode and compare proposed rejections with completed reference results. Coarse 16-block samples alone do not certify unsampled bridges, channels, component area or all possible final centers. Treat unknown cells/rays optimistically in a necessary bound. Apply hard rejection only to mandatory criteria; diameter 300–700 and water-enclosure 0.85 are currently preferences, so those alone cannot reject a nomination. Require proof and zero false rejections plus positive net time savings after quart reuse. Otherwise keep the estimates as nomination priorities.

The previous basin 95.47% saving and historical coast share are not island-filter performance measurements. No safe new island bound or island-filter speedup has been established by this native experiment.
