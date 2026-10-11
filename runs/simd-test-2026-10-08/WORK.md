# Pre-implementation native performance test

User request: test the proposed SIMD/native optimization before implementing the audit plan; return with an evidence-based decision. Production prediction code/configuration/native binary and the sweep are outside this experiment's mutations.

## Isolation and variants

`scripts/simd_probe.py` builds private CFFI modules in this directory from the pinned vendor and a copy of the owned bridge. It switches a process-local backend reference only after closing handles. Nothing is installed into `src/seed_search`.

- `scalar`: current `-O3 -std=c11 -fwrapv` build policy, freshly compiled control.
- `avx2`: adds `-mavx2 -ffp-contract=off`; tests compiler flags without an explicit kernel rewrite.
- `gemini`: adds `-mavx2 -mfma -march=x86-64-v3`; tests the proposed flags.
- `vector4`: strict AVX2 plus `scripts/simd_probe_kernel.c`, four vertical density samples per batch, scalar permutation lookup/gradients and packed interpolation/accumulation. Not a claim to be an optimal SIMD implementation.

Python is universal2. The initial Gemini-flags build failed for its arm64 slice; `universal2-build-attempt.txt` preserves the error. All subsequent experimental builds consistently use host-only `ARCHFLAGS=-arch x86_64`. This is a harness setting, not a production build change. A deployable optimization needs portable builds and safe CPU dispatch.

## Reproduction

Run timing phases serially with no other benchmark jobs. From the project root:

```sh
.venv/bin/python scripts/simd_probe.py build > runs/simd-test-2026-10-08/build.log 2>&1
.venv/bin/python scripts/simd_probe.py micro > runs/simd-test-2026-10-08/micro.log 2>&1
.venv/bin/python scripts/simd_probe.py full --variants scalar avx2 vector4 --repeats 2 > runs/simd-test-2026-10-08/full.log 2>&1
.venv/bin/python scripts/simd_probe.py regression --variants scalar avx2 vector4 > runs/simd-test-2026-10-08/regression.log 2>&1
.venv/bin/python scripts/simd_probe.py seed_order
.venv/bin/python scripts/simd_probe.py summarize
```

The Gemini flag arm is excluded from full-seed performance promotion because micro parity already found raw-density drift. Height, land and grid outputs matched in the sampled micro cases; this is not evidence of universal decision parity.

Micro parity: six fixed seeds, 384 X/Z points per seed (including negative cell boundaries), heights at strides 1/8/16, biomes, land, 17×17 climate/biome grids and 1024 raw-density samples per seed. Vector groups share X/Z and have four Y values including vertical boundaries. Micro timings: three seeds × four workloads × four variants × three rotated-order trials, cold handles with one equal terrain-initialization warm-up; query setup excluded except quart grouping/broadcast included in its workload.

Full comparison: three seeds (-1, 12345, 4294979641) × three variants × land reuse off/on × two reversed-order trials. Each analyzes the entire finite current seed pipeline with cold per-seed caches, original 3008/992 geometry and existing budgets. No process pool, renderer, website or game verification. Compare exact `index`, `seed`, `candidates`, `near_misses`, `counts`, and `filter_policy`; timings and cache-computation counts are intentionally separate. This includes bounded nomination outcomes, not exhaustive world search.

`builds.json` records flags and binary hashes; `environment.json` records host/compiler and production hashes; `assembly-evidence.json` records disassembly instruction counts. `micro-parity.json`, `micro-timing.json`, individual `full-*.json` and `full-summary.json` retain measured evidence. The assembly confirms actual packed operations in the vector kernel and FMA instructions in the Gemini build. Counts alone do not measure runtime or prove speedup.

## Added user requirements during the test

The user approved four independent categories: structures-only; inner island with water/mountains; ocean island; dry flat mountain basin. Stronghold and Fortress remain mandatory in each. Updated workflow/plan documents supersede the earlier diagnostic-only proposal; no production fourth branch was installed.

Gemini's early island-filter suggestion is included as P3b, with shadow-mode measurements and proof requirements. Diameter/enclosure preferences cannot become hard rejections silently; coarse unknown cells, alternate components/centers and finite edges require conservative treatment. Its speedup remains unmeasured.

## Correctness defect discovered by the reversed-order pass

The initial full-seed process uses seed -1 before any other Mineshaft seed. The second trial visits -1 after the other seeds. All three modules then produce different Mineshaft records and dependent scores for -1; the six first-trial comparisons and six second-trial comparisons agree **within their respective trials**. The original `equal: false` flags remain in `full-summary.json`; do not rewrite them as a globally passing repeatability result.

A fresh process using the unchanged installed binary independently reproduces the defect in a ±1024 square: sequence `-1, -1, 0, -1, -1` produces counts `0, 0, 28, 44, 44`. See `mineshaft-installed-seed-order.json`. Source: thread-local `mt_ws` starts at `(uint64_t)-1`, while `mt_a`/`mt_b` are zero. `setCarverSeed` skips initialization when that valid seed is queried first. Related helpers share this cache.

The plan now requires an explicit initialized flag, preserved by `MTRngState` save/restore, new identities and cold/warm worker/resume tests before sweep readiness. No production fix was installed during this experiment. The old frozen regression can pass because its usual seed order initializes the cache before -1. This finding is distinct from Stronghold prediction recall and from Gemini's floating-point drift.

Performance comparisons must use matched initialization history; the final analysis separately reports within-trial variant parity and the failed cross-trial seed-order gate. These timings support prioritization, not production release readiness.

## Completion

All 36 timed analyses completed. `analysis.json` confirms same-trial parity for every arm and retains six cross-trial failures confined to seed -1's Mineshaft records/derived scores and counter. Scalar reuse saves 28.1% across the selected cohort; strict AVX2 adds 2.6% after reuse; four-Y SIMD is 1.2% slower after reuse. All three retained variants pass the frozen 880-structure/159-coordinate regression, including its six known disagreements. The installed seed-order reproduction remains a deliberately recorded failed invariant requiring a future production fix.

Final decision, limitations and updated plan: [SIMD_TEST_RESULTS.md](../../SIMD_TEST_RESULTS.md). No production implementation or sweep was started.
