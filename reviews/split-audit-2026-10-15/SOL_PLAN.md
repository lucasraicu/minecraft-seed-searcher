# Sol assignment: remaining performance audit

Use this document as the execution prompt for Sol. Read `CODEX_REVIEW.md` in this directory for the common evidence and final-review requirements.

## Objective and scope

Audit the remaining throughput bottlenecks in `dynamic-envelope-1664-v1`. Identify the dominant remaining costs and evaluate a small number of justified optimization proposals. Deliver evidence and reviewable diffs to Codex for final review.

This is an audit assignment. Experimental builds and probes belong in isolated directories. Do not apply fixes to production, replace its binary, or publish a new performance claim in README. Exclude end-to-end pipeline runs, combined generation-to-SQLite benchmarks, live sweeps, BDS verification, and deployment.

The reference checkout when these assignments were prepared is:

```text
54b7d631b8bdb481894980a31be16aaa02901b18
```

Verify the checkout at execution time. If it has changed, record the new baseline and identify which prior findings still apply. Both teams must audit the same agreed commit and configuration; do not silently compare different revisions.

## Ownership

Sol owns profiling, timed experiments, experiment builds, and performance conclusions. Gemini owns the independent correctness, memory, concurrency, boundary, and storage/control-plane reviews. Codex reviews both completed packages and makes the final disposition.

Only one CPU-intensive experiment may run on the benchmark machine at a time. Arrange an exclusive measurement window with the user or other active team before timing. Gemini can continue light source review during that window; pause builds, heavy tests, scans, and fault-injection workloads. A local lock helps only if every participant actually honors it.

Write results under `reviews/split-audit-2026-10-15/sol/`. Use separate build directories for each arm. Do not modify Gemini's outputs.

## Fixed mathematical contract

- Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes `MC_26_50`.
- Overworld: `[C_X-832,C_X+832)` and the equivalent Z interval.
- Nether: `[C_X/8-416,C_X/8+416)` and the equivalent Z interval. Production centers are snapped to multiples of eight; only there does rational scaling equal `center // 8`.
- Integer entry events: `X_i-831` and `8*X_N,j-3327`; exit events are one past the corresponding inclusive upper center bounds.
- Preserve all 160 raw lattice event contributions per axis and every resulting membership transition. Clipping and deduplication are legitimate; deleting transitions is not.
- Second Ocean Monument milestone: +30 points.
- Preserve mandatory floors, strict goals, flexible-category deficit rules, snapping, evidence completeness, and full64 viability semantics.

No relaxed bounds, reduced lattice, low-bit viability substitutions, or changed floating-point noise expressions are acceptable performance shortcuts. New spatial indexes require measured evidence of a benefit over the contiguous arrays.

## S0 — Freeze workloads and build identities

Create `manifest.json` before timing. Record:

1. Baseline commit and working-tree differences relevant to compilation or policy.
2. Resolved policy and its hash.
3. Source, native binary, OpenMP runtime, and PGO profile identities; compiler and flags.
4. CPU topology, available physical/logical CPUs, memory, and operating system.
5. Explicit seed sequence, run key, index intervals, retention mode, batch size, and thread count for every workload.

Prepare three labeled cohorts:

- Ordinary natural seeds, using permutation indices disjoint from PGO training.
- Archived natural seeds reaching late stages, if available and compatible with the baseline.
- Deterministic synthetic survivors, explicitly labeled as fixtures.

Do not substitute synthetic seeds for evidence about natural survivor frequency. Adjacent run keys are not proof of disjoint cohorts: check the actual seed mapping or explicit input sets.

Read the prior `reviews/codex-audit-2026-10-15/AUDIT.md` and `evidence.json`. Treat the earlier delayed-initialization result as a prior measurement to verify against the frozen baseline, not a new discovery. Do not repeat the entire completed audit.

**Output:** manifest and a short inventory of reusable evidence versus missing evidence.

## S1 — Profile Mansion evaluation first

Trace `nb_pair(...,0,...)` into the pinned Cubiomes viability implementation.

Measure:

- Number of raw starts examined and viability calls per entering seed.
- Conditional rejection rates.
- Time spent in noise/biome queries, viability checks, and Dark Forest witness sampling.
- Repeated work within a seed and actual Mansion-cache hit rate in the dynamic path.
- Cycle, instruction, branch-miss, and cache-miss information where supported.

Start with sampling. Add narrowly scoped diagnostic instrumentation only where attribution remains unclear. Run final timing without that instrumentation. If counters are unavailable, state that limitation and avoid declaring the code cache-bound, bandwidth-bound, or branch-bound from elapsed time alone.

Inspect whether an already calculated result can safely satisfy a later query, whether unnecessary work can be delayed, and whether the current cache earns its overhead. Any reuse must preserve exact seed, position, version, dimension, and predicate semantics.

**Output:** measured hotspot table and at most two justified candidates. Stop pursuing a proposed change when its maximum aggregate benefit is negligible or its correctness assumptions cannot be established.

## S2 — Audit preflight ordering and duplicated work

Measure each predicate's cost and rejection rate conditional on the predicates before it:

- Raw Nether co-window feasibility.
- Raw Overworld structure-floor checks.
- Mansion viability.
- Outpost viability.
- Nether viability.
- Generator initialization and placement calculations repeated across stages.

Use those observations to choose at most two plausible ordering/reuse experiments. Do not permute every check or choose an order from standalone rejection rates. Moving a check earlier changes how often it executes.

Verify that raw preflight remains a conservative superset of viable outcomes. Preserve complete retained inventories and compare complete decision receipts. Use Gemini's reviewed survivor fixtures when available; record their exact identities.

Regenerate source-matched PGO for changed sources. Never compare a fresh experimental PGO arm against a stale or incompatible profile and attribute the entire difference to the code change.

**Output:** keep/reject/inconclusive result for each candidate, with a proposed patch only for candidates supported by the evidence.

## S3 — Audit scheduling with a staged sweep

Use one fixed natural cohort and uninstrumented kernel timings. Verify the host topology before interpreting SMT effects.

| Variable | Initial values |
| --- | --- |
| OpenMP threads | 16, 18, 24, 30, 34, restricted to supported host capacity |
| Work-claim chunk | 16, 64, 128 |
| Native batch size | 4,096; 8,192; 16,384 |

Avoid the full Cartesian product:

1. Compare thread counts with current batch and chunk settings.
2. Compare chunks at the strongest thread setting; include a nearby thread setting only if results are effectively tied.
3. Compare batch sizes at the strongest combination.

Record kernel throughput, batch latency, CPU utilization, worker imbalance, and variability. Investigate affinity or false-sharing padding only if profiling produces a specific hypothesis. Confirm performance finalists using the common measurement standard below.

**Output:** one justified operating point, or a documented tie, with limits on how broadly it applies.

## S4 — Measure the survivor path in isolation

Time these native stages separately using compatible natural late-stage seeds and explicit survivor fixtures:

- Mandatory and optional inventories.
- Overworld/Nether palette construction.
- Events, cells, centroid snapping, ranking, and final evidence extraction.
- Allocation traffic and peak live bytes per worker.

Measure CFFI record reconstruction and serialization separately from generation. If an isolated writer measurement is justified by a specific hypothesis, use a temporary database and prebuilt records; do not connect it to generation or present it as end-to-end throughput.

Calculate the aggregate impact using an observed entry frequency where one is available. Otherwise give per-survivor cost and label aggregate impact unknown. A large synthetic survivor cost alone does not establish a production bottleneck.

**Output:** survivor-stage cost table and any newly justified performance proposal. Send potential correctness or ownership failures to Gemini with the exact trigger; retain them in Sol's report as pending until independently checked.

## Measurement standard and stopping rules

- Screen candidates with three alternating paired trials on identical inputs.
- Confirm finalists with at least five alternating paired trials. Target at least five seconds of native work per arm per trial by expanding the cohort when necessary.
- Keep seed construction, instrumentation, record walking, and serialization outside kernel timing; report them separately when relevant.
- Compare receipt fingerprints and independently reconstructed survivor content. A matching all-reject receipt alone does not validate rare survivor behavior.
- Report each trial, median paired improvement, variability, and baseline/candidate build identities. Distinguish a median of paired ratios from a ratio of medians.
- If the observed gain is comparable to measurement noise, mark it inconclusive. Extend the measurement once if the plausible benefit warrants it; do not benchmark indefinitely.
- Pursue SIMD only after identifying a significant vectorizable stage and establishing exact arithmetic requirements. Do not implement Rust/GPU prototypes without a measured cost model that justifies the experiment.
- If a proposed optimization changes eligibility, score, selected center, or retained evidence, stop performance evaluation and report the discrepancy. Do not silently repair the policy or normalize away the difference.

## Required handoff to Codex

Provide:

```text
sol/
  REPORT.md
  manifest.json
  measurements.json
  commands.md
  proposals/              # minimal unapplied patches, if justified
  probes/                 # only scripts needed to reproduce results
```

`REPORT.md` must include the dominant measured bottlenecks, accepted/rejected experiments, prior findings rechecked, no more than two strongest optimization proposals, correctness evidence, and remaining limitations. Label each conclusion `MEASURED`, `PROVEN_BOUND`, `HYPOTHESIS`, or `INCONCLUSIVE`.

Use identifiers `S-PERF-01`, `S-PERF-02`, and so on. Every claimed improvement needs raw trials and a reproducible command. Every newly reported defect needs an exact file/anchor, numerical trigger, observed/expected behavior, and minimal fix.

Sol's handoff is provisional. Codex will review methodology, reproduce important claims, reconcile Gemini's findings, and issue the final audit verdict. Do not claim all possible optimizations have been exhausted.
