> Historical preparation notes from the paused window. Subsequent experiments are complete; the authoritative handoff is [REPORT.md](REPORT.md). Statements below about pending work refer to that earlier window.

# Sol source review — prepared while heavy work is paused

Status: **partial audit; no new timings, builds, tests, or profiling runs have been performed.** The user explicitly reserved heavy work for a later release. Source inspection and experiment preparation continue within that restriction. This is not the final Sol report.

Baseline: `54b7d631b8bdb481894980a31be16aaa02901b18`. Production source is unchanged. The production input hashes, extension hash, and OpenMP runtime hash are checked by the preparation script and captured in `manifest.json`.

## S-PERF-01 — Unused legacy surface-noise initialization in modern Mansion checks

Classification: **PROVEN_BOUND for unused object data; HYPOTHESIS for aggregate speed-up and safe adoption.**

At `vendor/cubiomes-bedrock/finders.c:1825`, the modern Mansion branch creates and initializes a `SurfaceNoise` object:

```c
SurfaceNoise sn;
initSurfaceNoise(&sn, DIM_OVERWORLD, g->seed);
```

It passes the object to:

```c
mapApproxHeight(&height, &biome_id, g, &sn, x >> 2, z >> 2, 1, 1);
```

In `vendor/cubiomes-bedrock/generator.c:610`, `mapApproxHeight` returns from its `g->mc >= MC_1_18` branch without reading `sn`. The active version is `MC_26_50`. The enclosing Mansion branch only takes this path for modern versions. The object is not used elsewhere in the Mansion case.

`initSurfaceNoise`, at `biomenoise.c:25`, initializes 60 Perlin octaves across five octave groups and performs an additional `skipNextN(262*10)`. Each `perlinInit` consumes three `nextFloat` draws and 256 `nextInt` draws. The pinned wrappers each consume one `mt_next`, giving exactly `60*(3+256)+2620 = 18,160` MT draws per initialization, in addition to MT reseeding work. This is concrete work with unused object contents in this call path. No cycle fraction or throughput benefit has been measured in this audit.

**Important side effect:** initialization reseeds and advances the thread-local MT state. Removing the object initialization is therefore not generally equivalent to deleting a pure computation. The proposed isolated arm passes `NULL` to the modern height function and removes initialization only in the modern Mansion case. It must be checked against the bounded native pipeline, including interleaved structure calls, multiple seeds per worker, and complete evidence reconstruction.

Source tracing so far: the remaining Mansion height/biome checks do not consume that MT stream; static Stronghold placement and the initial village-Stronghold iterator reseed their streams; subsequent region placement and Outpost/Bastion variant paths also establish their own seeds. This supports an experiment, but does not replace parity verification or establish that the public vendor API promises identical post-call MT state.

Prepared arms: `no-surface-init` against control, and `lazy-no-surface-init` against lazy initialization. They are experimental copies; no production or vendor source was edited.

Required before accepting: sampling/diagnostic cost attribution, source-matched PGO, natural decision parity, positive Mansion component parity, survivor reconstruction parity, and five paired confirmation trials on a quiet machine. Report any post-call MT-state limitation explicitly.

## S-PERF-02 — Necessary Dark Forest witness gate before Mansion viability

Classification: **HYPOTHESIS for performance; source-level necessary-condition argument.**

The current eligibility condition requires enough viable Mansion starts whose Y=63 witness equals Dark Forest. Native evaluation currently computes expensive viability first, then samples those witnesses. A candidate experiment samples Y=63 at raw Mansion starts first and rejects the seed only when fewer than the required number can possibly qualify.

Raw starts are a superset of viable starts. Therefore a shortage of raw starts with the required witness is a necessary failure. For positive gate results, the original complete Mansion inventory path still runs, including non-Dark-Forest viable starts retained as evidence. The proposed gate does not replace complete inventory with only its qualifying subset.

The extra biome/placement work may cost more than it saves, especially if S-PERF-01 succeeds. This candidate must be evaluated conditionally against the strongest relevant control. No speed-up is claimed. The prepared `dark-gate` arm includes the prior delayed-generator change, so compare it to `lazy` to attribute the gate's incremental effect.

## S-PERF-03 — Mansion cache has no reusable queries in the active dynamic path

Classification: **PROVEN_BOUND for zero possible hits in the inspected normal dynamic call graph; unmeasured cost.**

`nb_eval_dynamic` clears `w->mansion_cache_n` before each seed and calls `nb_pair(w,0,...)` once. `nb_pair` copies and sorts/deduplicates raw starts before querying its cache. Final window extraction uses `nb_dynamic_subset`, not another Mansion viability pass. Consequently, positions queried within that one cache lifetime are distinct and cannot hit entries from earlier seeds.

This proof applies to the inspected production dynamic path, not the legacy evaluators, which may query overlapping anchor inventories. The linear cache search and insertion are redundant in this path, but no significant throughput benefit is inferred. Measure actual diagnostic hit counts and bound the cost before considering a dynamic-only bypass.

## S-METHOD-01 — Existing profile histograms omit dynamic stage timings

Classification: **SOURCE_VERIFIED measurement gap; not a production eligibility defect.**

The dynamic evaluator writes `NBResult.stage_seconds`, but does not call `NB_PROFILE_STAGE`. The stage calls in `blueprint_batch.inc` are after `if(w->p->dynamic)return nb_eval_dynamic(w,seed,r);` and therefore belong to legacy evaluation. As a result, `NBProfileSample.stages[*].count` cannot establish dynamic-stage entry counts. The profile's cache/point hooks remain active; the gap concerns stage histograms.

The concrete configuration trigger is `p->dynamic=1,p->complete=0` through `nb_profile_sweep`: every sample's stage histogram counts remain zero under this call graph even while `NBResult.stage_seconds` accumulates work. Forced-complete diagnostic mode can populate separate extra probe slots; those are not timings of the active dynamic stage sequence. This is established by source inspection; no test has been run during the pause.

Prepared diagnostic sources copy stage timings into separate per-input records before result compaction and add distinct counters around the raw checks, Mansion subcomponents, Outpost, and Nether viability. Their labels explicitly distinguish exact call counts from a nonzero-timing-field proxy. The legacy stage-label map must not be reused: dynamic field 14 is Outpost, and field 11 combines raw preflight and final Nether work.

The diagnostic source preparation is not native compilation or a validated profiler. Its build, correctness checks, and overhead assessment remain pending release. Final performance timing must still use an uninstrumented arm.

## S-PERF-04 — Scheduling and setup work can be bounded before timing

Classification: **PROVEN_BOUND for operation counts; no throughput conclusion.**

With `N` inputs, chunk size `K`, and an actual team of `T` workers, the inspected claim loop performs `ceil(N/K)` successful claims plus one failed terminal claim per worker. For 100,000 inputs and 34 workers, this gives 6,284 atomic claims at chunk 16, 1,597 at chunk 64, and 816 at chunk 128. Larger chunks also reduce balancing granularity, so fewer atomics do not establish a winning chunk size.

Every native batch creates and destroys one SeedContext per actual worker, including workers that claim no input. At 34 workers, 100,000 inputs require 238 context creations with batches of 16,384 (7 calls), versus 850 with batches of 4,096 (25 calls). The context constructor initializes both generators before any seed-level preflight. These are source-derived setup counts, not estimates of elapsed time; larger batches also affect retention memory and latency.

No cache-line padding, custom allocator, affinity changes, or SIMD rewrite is justified by these operation counts alone. They identify what the staged scheduling measurements need to distinguish.

## Prepared parity evidence and corpus separation

The benchmark harness now hashes one continuous native verdict-byte stream, so fingerprints do not change merely because identical inputs are partitioned into different batch sizes. Survivor record fingerprints are separately framed and hashed outside native timing. The same ABI and policy must be used for native-byte comparisons.

`probes/parity.py` is prepared to compare natural full/compact records, explicit survivor fixtures, and native Mansion components followed by Stronghold, Outpost, Fortress, and Bastion calls. It reports positive natural Mansion coverage and refuses to treat an empty positive set as evidence that positive calls were exercised. Fixtures bypass the native vendor viability branch, so fixture equality alone cannot validate the unused-noise proposal. The script has not been executed.

The seed permutation is a composition of invertible XOR shifts and multiplication by odd constants modulo `2^64`. Therefore the underlying `(index + run_key) mod 2^64` intervals, rather than index ranges or run keys considered independently, determine disjointness. The prepared nonwrapping training interval at run key 2026101402 and the 50M–61M evaluation ranges at run key 2026101401 are disjoint by this mapping. Repeated same-input paired trials are intentional; screening/profile/confirmation/component cohorts are otherwise separated as recorded in the manifest and commands.

## Remaining work after the user releases the machine

1. Collect Mansion sampling and conditional stage/call-count diagnostics.
2. Build matched PGO controls and only the strongest justified candidate arms.
3. Screen/confirm performance with decision and survivor parity checks.
4. Perform the staged thread/chunk/batch comparison.
5. Measure native survivor stages, reconstruction/serialization, and allocation traffic independently.
6. Save raw results and a final Sol report for Codex review alongside Gemini's package.

None of these pending measurements should be inferred from the historical audit's timing numbers. End-to-end validation remains excluded.
