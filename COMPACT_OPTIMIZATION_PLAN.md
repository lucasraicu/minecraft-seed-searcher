# Compact throughput optimization plan

Repository audit: 12 October 2026. Base commit: `b3089ddbf9f050d80416d7d1d29a321b53853cef` plus the existing working-tree changes. This document specifies future implementation and experiments; no optimization or new throughput result is claimed from this audit.

## Objective and measurement contract

Maximize **newly processed input seeds covered by completed FULL-durability range transactions per elapsed second**, using the active `locked-2048-1024-outpost-v3` policy and compact retention with `max_misses=1`. Retain every qualifying anchor, complete required inventories, scores, witnesses, uncertainty labels and downstream tasks. Preserve exact retries, recoverable leases, supported serial execution and the full-evidence route.

Report three separate measurements: fresh CLI launch through process exit; pipeline startup through drain/close; C-only evaluation. Also report terrain and BDS separately if measured. A faster all-reject cohort is not evidence of faster complete world qualification. A change to floors, geometry, allowed misses or biome sampling is not an implementation speedup.

“Maximum possible” cannot be established from a finite experiment. The deliverable is the fastest verified configuration among a recorded, bounded set of experiments on this host, with remaining hypotheses and measurement limits disclosed. No target rate is promised. Optimization preserves the current predictor contract; it cannot establish actual Bedrock accuracy independently of that model.

## What the repository establishes

| Finding | Evidence and consequence |
|---|---|
| Compact CLI median 22,525.37/sec; range 22,453.22–22,649.95 | Three 50,000-input v3 trials in [final workflow](runs/outpost-optimization-2026-10-12/final-workflow/results.json). This is the historical control, to be rerun against current sources. |
| Pipeline elapsed 1.5644–1.5788 s versus external CLI 2.2075–2.2269 s | Same three trials: 0.6425–0.6480 s lies outside the pipeline timer. One trial reports 31,701.07/sec inside the pipeline. Attribute this residual before optimizing SQL; it includes work outside the timer, not necessarily imports alone. |
| C-only held-out median 35,385.17/sec | [Order experiments](OUTPOST_OPTIMIZATION_RESULTS.md). This is not an attainable ceiling or a durable rate. |
| No natural retained candidates in these compact trials | Need retained-candidate and late-stage fixtures as separate workload arms. Database size 212,992 bytes is an all-reject result, not a storage estimate for winners. |
| Stronghold: 30,000 entered calls, mean 414.90 µs | [Verified stage profile](runs/outpost-optimization-2026-10-12/verified-stage-profile/results.json). Every input performs discovery; this is the first native kernel to investigate. Parallel stage times cannot be added into CLI elapsed time. |
| No natural Chamber, Mineshaft or palette entries in that profile | Forced full palette averaged 27.71 ms and full Mineshaft enumeration 5.98 ms. Optimize these for late-stage service only after establishing their contribution to the intended workload. |
| Current order already has measured improvements | Nether pair → Portal → Outpost → Pyramid → Temple → Mansion → City → Village → Chamber → Mineshaft. Pyramid/Temple alternatives effectively tied on held-out data. Mansion-first regressed. |
| Chunk 16 beat 64/128 on the previous river policy | [Chunk review](GEMINI_PIPELINE_REVIEW_RESULTS.md). Recheck v3; fewer atomics do not prove higher throughput. |
| Current resource-monitoring edit is a regression | `runner.py` substitutes SELF peak RSS for unavailable tree RSS and reports success. Audit rerun: `pytest tests/test_pipeline_review.py -q`: **4 failed, 1 passed**. Fix before accepting resource gates. |

Source inspection adds concrete optimization candidates, but does not establish their costs:

- `native/blueprint_batch.inc:nb_run` creates/destroys each worker's generator and scratch state every batch.
- `nb_eval` seeds both dimensions before discovery; this initialization sits outside the Stronghold stage timer.
- Rejected seeds still build C observation allocations; compact cleanup occurs after `nb_eval`. Only Python record construction is limited to retained seeds.
- `nb_alloc` updates a shared allocation counter atomically; this is currently cumulative allocation accounting, not live-byte accounting. Changes must preserve a documented bound.
- Stronghold scanning in `native/bridge.c:ss_scan` includes regional placements with a halo **and** three village-associated iterations. Removing either changes discovery.
- `persist_pipeline` uses one native producer, one record preparer and one SQLite writer, with two or three outstanding batches. It creates Python seed lists and commits leases/checkpoints per batch.
- Receipt hashing already consumes a C buffer without per-input Python dictionaries. Do not rebuild it as Python objects.
- `scripts/benchmark_native_chunks.py` hardcodes the older river policy; adapt and verify its config identity before using it for v3.

## P0 — Freeze a valid control and close profiling gaps

1. Preserve the current diff and untracked files. Record source/config/build hashes, compiler flags, pinned libomp identity, Python/dependency versions, CPU topology, available memory and free disk. Keep all historical runs intact. Do not benchmark an old extension against edited source without identifying the mismatch.
2. Resolve the monitoring regression in a separate change: fail closed when tree memory cannot be measured, or supply independently tested equivalent tree accounting. Do not silently overwrite the user's edit. Run monitoring, memory-policy and resource-limit tests before performance work.
3. Reproduce v3 compact at 32 native threads, batch 4096, chunk 16 and the existing bounded pipeline. Use the same exact inputs for control/candidate pairs; freeze one control build for attribution.
4. Add opt-in timing/counters for imports, config/identity/build loading, store initialization/range setup, input enumeration/CFFI conversion, context creation, dimension seed initialization, allocation/zeroing/copy/free, native worker busy/idle time, record preparation, receipt hashing, lease SQL/commit, completion SQL/commit, disk/resource probes and shutdown. Timers must distinguish exclusive elapsed phases from overlapping service time.
5. Measure instrumented versus normal builds and verify semantic equivalence. Use profiling builds for diagnosis and uninstrumented builds for adoption. Do not insert per-biome timers into production.

Exit: reproducible baseline, validated monitoring, explicit workload identity and an attributed time profile. Choose subsequent experiments from measured cost, not presumed savings.

## P1 — Reduce launch overhead and tune scheduling

**First experiment:** profile imports and work outside `persist_pipeline`; move unnecessary command-specific imports or repeated setup only if demonstrated expensive. Preserve CLI validation and identity checks. Compare actual fresh CLI performance, not just the inner timer. A persistent session is a separate interface change and must not hide startup in reported results.

Then use a staged sweep, not a full Cartesian search:

1. Threads 8, 16, 24, 30, 32, 34 at batch 4096/chunk 16.
2. For the two best thread counts, batches 1024, 4096, 8192, 16384, subject to memory gates.
3. At the two best configurations, chunks 16, 64, 128.
4. At the winning configuration, compare two versus three outstanding batches and preparation placement only if queue costs warrant it.

Use three rotated trials per screening configuration, same input cohort. Recheck finalists on untouched inputs. Preserve the two CPU slots reserved for preparation/writing. Measure tail batch latency, worker imbalance, CPU utilization and owned-buffer memory, including late/retained fixtures. Larger batches increase work lost on interruption; retain bounded recovery and report the tradeoff.

Exit: measured best configuration, with defaults changed only after held-out confirmation. No change to scheduling algorithm or OpenMP runtime is justified solely by this sweep.

## P2 — Remove avoidable work on discarded inputs

Proceed if allocation/setup counters show material cost.

- Prototype compact-only decision state in reusable worker scratch, promoting owned evidence only for qualifying anchors. Compare transfer/copy against exact regeneration for survivors. Preserve discovery totals and one verdict per input, stable input offsets, errors, and all retained evidence. A failed allocation must remain an error, never become a rejection.
- Avoid allocating empty anchor/result data when discovery is empty. Preserve receipt semantics.
- Investigate worker-local bounded reservations to reduce shared allocation-counter contention. Specify both live/peak ownership and the existing cumulative-limit behavior; a faster allocator cannot quietly remove the batch cap.
- Measure amortizing generator/scratch initialization across calls. Persistent state requires explicit lifetime, per-call policy reset, per-seed cache invalidation, simultaneous-caller isolation, cancellation and teardown tests. Retain a simple serial route.
- Defer Nether initialization until actually needed only if no-anchor frequency and setup time justify it; ensure no path observes a stale generator seed.

Exit: zero semantic differences and statistically supported full-workflow gain. Reject added ownership complexity if the gain is not distinguishable from noise.

## P3 — Optimize the native discovery and filtering kernels

Profile `ss_scan(Stronghold)` into placement, village-associated iteration, biome lookup and sorting/deduplication; include generator initialization separately. Investigate redundant exact computations and bounded per-seed caches, preserving the region halo, both discovery sources, full64 seed semantics and negative-coordinate arithmetic.

For other structures, collect conditional rejection and cost statistics under **one-miss** retention. Use those measurements to evaluate alternate orders; ordinary zero-miss greedy formulas do not establish the best near-miss order. Keep the current measured order as control. Do not cap final retained inventories at floors.

If sample overlap is material, test exact per-seed reuse keyed by full coordinates, dimension, Y, sampling convention and relevant generator identity. Reset caches correctly between seeds. Preserve witness selection and record order. Only attempt SIMD/compiler changes when a specific hot kernel supports bit-exact output and portable fallback; exclude unsafe floating-point transformations.

Exit: independent Python/direct/replay parity and held-out compact improvement. Discovery recall cannot be inferred from matching all-reject counts alone.

## P4 — Late-stage and durable candidate service

Treat these as separate measured workloads:

- Exact palette: investigate repeated biome calculations and bounded sample reuse. Preserve all four Y levels and thirteen predicates, existing lattice/bounds and first-witness semantics. Missing a biome in 32–128 samples is **not** grounds for rejection. Safe stopping requires a mathematically sufficient decision under the exact contract.
- Mineshaft and other full inventories: remove duplicate computation without dropping enumeration. Measure complete records, not first-witness speed.
- Retained preparation/SQLite: profile positive/near-miss fixtures, serialization, hashes, indexes, inventory/tasks and fsync. Optimize only demonstrated cost; zero natural survivors do not validate this path's capacity.
- Checkpoint costs: increase amortization within existing bounded batches before redesigning leases. Any batching of claims/completions must preserve atomic durable coverage and exact retries. Keep WAL/FULL, validation, ranking and exports.

Terrain/coastal evaluation and BDS remain separate follow-on workloads. No coarse-grid rejection without proof of equivalence, no finalist truncation that silently removes qualifying compact candidates, and no assumed world-discovery probability.

## PC — Compiler experiments (after P0, before invasive kernel changes)

The audited host is x86_64 Intel Xeon W-2191B. The private builder currently specifies `-O3 -std=c11 -fwrapv`, compiles Cubiomes units separately, and performs an extension-load check. No quoted 3–25% improvement is established for these proposals.

1. **Build support and provenance.** Add explicit opt-in build variants in `scripts/build_blueprint_batch.py`, retaining the unchanged portable control. Record compiler/linker versions, all compile/link flags, target features, source/binary/runtime hashes and PGO profile hash. Apply LTO at both compilation and linking; validate toolchain support by actually building and loading. Preserve the pinned OpenMP ABI and load smoke test.
2. **LTO.** Compare the existing build with supported full LTO and ThinLTO separately. Check generated-code/inlining reports where available. Measure build time and binary size as well as runtime. Do not assume linking succeeded merely because individual objects compiled.
3. **CPU targeting.** Compare `-march=native` alone and combined with the better LTO variant. Do not use `-mcpu=apple-m1` on this Intel host. Host-specific builds must remain explicitly labelled and cannot replace a portable binary for other CPUs. Preserve `-fwrapv`; exclude `-ffast-math`/`-Ofast` and audit floating-point contraction changes against exact biome/density outputs.
4. **PGO.** Build with supported instrumentation, train, merge raw profiles with matching `llvm-profdata`, and rebuild with profile-use flags. Verify profile collection from the CFFI extension and OpenMP threads, matching tool versions, and no stale/mismatched-profile warnings. Evaluate the uninstrumented profile-use binary. Train one profile on representative natural compact screening; optionally compare a second explicitly weighted profile including late/positive fixtures. Never infer natural survivor frequency from that synthetic mixture. Evaluate on disjoint held-out natural inputs and forced late-stage regressions. PGO optimizes generated code using observed execution; it does not guarantee a particular branch-prediction benefit.
5. **Unity build.** Attempt only as a separately measured alternative if LTO leaves a documented opportunity. Generate a private aggregation unit; do not rewrite vendor files. Resolve static-name/macro collisions explicitly, prevent duplicate compilation and verify initialization/visibility behavior. Compare against the best LTO build. Cross-module inlining gains overlap: do not add percentages from unity, LTO and PGO.
6. **Static structure configuration.** Profile lookups both in `ss_structure_count` and downstream placement. The former retrieves config once outside its region loop. If material cost remains after compiler optimization, cache immutable configuration by structure type and model/version, preserving unsupported-type behavior. Avoid racy lazy initialization. Compare with uncached results across all supported policy revisions. Constant folding from LTO may make manual caching unnecessary.

Budget compiler screening separately from P1: at most eight configurations (control, full LTO, ThinLTO, native CPU, selected LTO+native, two PGO profiles, unity alternative), three 50,000-input trials each: at most 1.2 million processed benchmark inputs. Up to two 50,000-input PGO training passes add 100,000 processed inputs; log fixture training separately with a cap of 256 inputs per profile. These are proposed caps, not work already performed. Shared training cohorts do not create additional distinct volume. Apply the same disk/resource preflight and held-out adoption gates as other phases.

Exit: best verified compiler configuration with portable fallback. Recheck the selected thread/batch settings afterward because generated code can change scheduling behavior. A compiler change must pass the full parity gate even when source semantics appear unchanged.

## Complete proposal register and disposition

This register includes earlier adjacent proposals so that exclusion from the compact hot path is explicit. Requirements and already-adopted behavior are controls, not new speedups.

| Proposal | Implementation disposition / dependency |
|---|---|
| Lazy CLI imports, eliminate repeated setup | P1, after exclusive startup profiling. Preserve validation. |
| Persistent bounded search session | Conditional P1 extension only if repeated launch cost matters operationally. Preserve per-invocation volume limits, run identity, locking, resume and shutdown. Report fresh-process performance separately. |
| Thread, batch, chunk and queue tuning | P1 staged sweep; retain atomic claiming compatible with libomp. |
| Alternative scheduling/work stealing | Only after worker imbalance measurements; chunk-size reduction/increase is not proof of a better scheduler. Require starvation, ownership and bounded cancellation checks. |
| Move seed permutation/input packing into C or reusable typed buffers | Conditional P2 experiment if Python enumeration/CFFI conversion is material. Preserve exact index-to-full64 mapping, manifest mode, index limits and receipts. |
| Worker-local allocation arenas, fewer copies/zeroing/frees | P2. Promote only retained evidence; preserve owned lifetimes and memory limits. |
| Reuse generators and scratch across batches | P2. Reset state and caches; preserve independent callers and serial operation. |
| Lazy dimension initialization | P2. Measure actual skipped work and prove no stale seed use. |
| Stronghold and other exact caches, overlapping-query reuse | P3. Preserve discovery halo, full anchor set, bounds, viability and cache keys. |
| Filter reordering | P3. Measure conditional cost under one-miss semantics, not zero-miss assumptions. |
| Mansion 64-entry cache | Already present; retain an uncached oracle. Further changes require hit-rate/cost evidence. |
| LTO, CPU flags, PGO, unity build, config caching | PC, isolated comparisons with recorded toolchain and complete parity. |
| SIMD and PRNG kernel optimization | P3/P4 only after profiling. Preserve pinned arithmetic, thresholds, RNG outputs and scalar oracle. |
| Mineshaft early PRNG rejection | P4 investigation: current code already has four-lane PRNG evaluation and goal stopping. There is no deeper cave-viability call to remove. Test any cheaper exact rejection against the pinned kernel; account for SIMD divergence and remaining PRNG cost. |
| Rare-first/dispersed palette scheduling | P4 only if outputs/witness contract is preserved or explicitly reconciled without weakening evidence. Existing dispersed traversal remains the control. |
| Sparse 32–128-point negative biome cutoff | Rejected: sampled absence does not establish full-lattice absence. No approximate rejection in the accurate mode. |
| Direct record preparation; encode durable rows once | Existing full-evidence work is not automatically a compact gain. Profile and apply to retained compact records only where equivalent and useful. Keep replay/Python oracles. |
| Native serialization | Conditional P4 experiment only if retained record encoding remains material after simpler changes; require exact canonical bytes/digests and schema compatibility. |
| Hashing, SQL bulk inserts, inventory/task batching | P4. Preserve validation, all required rows, ranking, transaction boundaries and retry semantics. |
| Claim/commit amortization; monitoring/probe costs | P4 after P1 batching. Never disable FULL durability, disk checks or fail-closed resource limits to gain throughput. |
| Alternate preparation/writer placement or process pools | Conditional P4 experiment if measured bottleneck warrants it. Include IPC, serialization, memory and shutdown cost; never fork initialized OpenMP state. Prior full-evidence results do not settle compact behavior. |
| Winners plus near misses; marine deferral | Existing policy: retain eligible core candidates, max_misses=1, defer marine checks to the specified terrain stage. Do not count stricter retention/floors as optimization. |
| Coastal vectorization and terrain sample reuse | Separate terrain track; retain existing exact implementations and compare full raster/decision parity for further changes. |
| Coarse/medium/fine terrain cascade | Investigate sample reuse or prioritization. Reject on coarse evidence only where a rigorous bound proves the fine-grid decision; coarse percentages/connectivity alone are not sufficient. No assumed 10 s to 15 ms result. |
| Move terrain density computation into C | Separate terrain profiling decision. Compare full rasters, thresholds and coast/river metrics with the retained oracle, including unknown cells. |
| BDS top-10/20 verification queue | Separate optional finalist verification budget, not a cap on stored qualifying candidates. Preserve ranking/provenance; publish only actual completed verification. |
| BDS headless batching, settings and LevelDB inspection | Separate feasibility experiment. Measure boot, chunk generation, required spatial coverage and clean save/stop independently. Lower view distance must not omit required chunks. Direct DB inspection cannot certify chunks never generated. No promised under-eight-second verification. |
| Larger borders, floor changes, river connectivity, bonuses | Blueprint requirements/accuracy topics, not throughput experiments. Hold the active configuration fixed. Diagonal land contact alone does not prove bridging across river water; separated cave samples do not prove distinct massive cave systems. |

No new terrain/BDS execution is included in the compact experiment budget. Scope and budget those tracks separately before running them. Preserve explicit predictor uncertainty and actual-game verification status throughout.

## Accuracy and durability gates for every adopted change

- Same seeds/config: compare retention decisions and discovered/retained anchor totals for every input; compare complete retained semantic records, scores, witnesses, classification, inventories and durable task tables. Exclude only already-defined nondeterministic timing/runtime metadata, never widen exclusions to pass.
- For batch-size changes, hash the ordered concatenated fixed-width verdict stream or compare decoded per-input verdicts. Hashes of lists of per-batch receipts differ when partitioning changes and are not a valid cross-partition oracle. Verdict counts alone do not establish anchor identity; also compare discovery/retained coordinates against independent enumeration on diagnostic cohorts.
- Explicit positives, each single missing requirement, two missing requirements, late biome witnesses, multi-anchor seeds, threshold boundaries, signed seeds, high bits, negative and shifted bounds, duplicate placements and deferred marine stages. A miss allowance of one must not become zero or two.
- Differential direct/native/replay/Python checks; fixtures that reach all stages; real generator checks beyond synthetic providers. Historical policy compatibility remains covered.
- Serial/OpenMP and simultaneous independent calls; ownership after buffer closure; allocation failure; max-buffer enforcement; no stale cache/policy/seed state. ASan plus available concurrency checks; disclose sanitizer limitations.
- Kill/crash before and after commit, exact retry, resume without gaps or duplicate publication, exhausted disk, unavailable resource monitor, exports and leaderboard equality. Run SQLite integrity checks.
- Run the complete regression suite before promotion; retain logs and all failures. Earlier 880-test success does not certify the currently dirty tree.

## Bounded experiment and adoption protocol

Use one explicit experiment ledger: policy/build identity, seed index interval and key, count per trial, repetitions, distinct inputs, elapsed time, resource/disk estimate and output path. Disjointness depends on the index-plus-key domain before permutation; nearby keys alone do not ensure independent cohorts. Never overwrite original runs or launch unlimited scans.

- Screening: 50,000 inputs per trial, three trials, one training cohort. The P1 grid above has at most 24 configuration trial sets (3.6 million processed inputs including repetitions, only 50,000 distinct training inputs). Deduplicate repeated configurations. Pause after screening to reassess cost before expanding.
- Adoption: control and selected candidate, five counterbalanced pairs on a separate 100,000-input held-out cohort: 1 million processed inputs, 100,000 additional distinct inputs. Each invocation stays within the existing 100,000 cap. Later adaptive work needs a new held-out cohort and explicit budget extension.
- Retained/late diagnostics: finite fixture manifests, separately labelled synthetic, with 0%, 1%, 10% and 100% retained-load stress arms sized to fit measured memory/disk. These are engineering loads, not predicted natural frequencies.
- Calculate disk needs before each phase from measured database/WAL growth plus worst-case configured payload/queue budgets, retained fixture size and free-space reserve. Stop on insufficient space. All-reject database size is not a safe dense-survivor estimate.
- Use an idle host, identical toolchain/storage, alternate execution order and record raw rates, median/range, paired ratios, peak tree RSS, native/prepared buffer peaks, CPU time, WAL/database bytes and latency. Report short-run CLI and sustained behavior separately without hiding startup or exceeding invocation limits.
- Default adoption gate: all accuracy/resource/durability checks pass, at least 5% median CLI improvement, and a paired 95% bootstrap interval for speedup above 1.0. Five pairs can be inconclusive; retain the control rather than assert significance. Smaller changes may be retained for proven resource/correctness benefits but must not be advertised as established throughput wins.
- Stop this optimization round when each measured high-cost component has been tested or explicitly ruled out, finalists pass gates, and remaining experiments fail the gain criterion or lack evidence of sufficient cost. Publish rejected variants as well as winners. This is a bounded engineering stopping rule, not proof of a global optimum.

## Deliverables and order

1. Valid control, resource fix and attributed profile (P0).
2. Compiler experiments (PC) and CLI/setup and scheduling result (P1), each independently attributable; retune finalists if compiler changes alter scheduling.
3. Individually attributable allocation/state/kernel experiments selected from that profile (P2–P3).
4. Retained/late service results and complete correctness/durability validation (P4).
5. Raw measurements, exact reproduction commands, updated usage/defaults if adopted, and a compact results report stating measured improvement and unresolved limits.

Give implementation estimates after P0 identifies the actual costs; evidence currently does not support an honest fixed completion time or a promised final seeds/sec. This audit produced the plan and reproduced the monitoring failures; it did not modify production code, run a new throughput benchmark or certify a new release.
