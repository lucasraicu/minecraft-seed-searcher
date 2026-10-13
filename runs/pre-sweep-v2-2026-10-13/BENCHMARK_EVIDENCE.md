# Pre-sweep v2 benchmark evidence

This is the complete benchmark and optimization record, including final untouched-cohort confirmation. Raw trials, resource receipts, build identities, and machine-readable summaries are alongside this file in `tuning/`, `timing_budget.json`, `parity_gate.json`, `pre-heldout-results.json`, and `final-heldout-summary.json`.

## Policy, cohorts, and identity

All trials use `config/realm.yaml`, screening revision `origin-fixed-2048-two-group-v2`, run key `0`, and `B=2`. Compiler, thread, batch, chunk, and PGO tuning used only `[2000000,2050000)`, with no more than 50,000 distinct inputs per run. PGO generation used `[1000000,1050000)` and four positive/pending synthetic fixtures. After the final Python/runtime freeze, the untouched interval `[9000000000,9000100000)` was scanned in exactly five counterbalanced 100,000-input pairs.

The portable O3 control extension is `794b62a893f5fef7e9859bac8175354a9a452ed1a34e280a89e36e2dd677492f`; the pinned OpenMP runtime is `af4f16ce7fb34f8e444d328b105adead0b655768e32aadbf438972d8e79f92f6`. All seven compared builds passed the exact parity gate: six natural seeds matched Python, native direct, and replay semantics; complete synthetic fixtures had the expected three `PREDICTED` and one `PENDING` result; compact survivor retention kept exactly the first three predicted fixtures and replayed the retained records consistently. The final heldout runs additionally validate full checkpoint/retention receipt coverage and semantic equality between paired arms. See `parity_gate.json` and `final-heldout-summary.json` for build identities, record digests, retention results, and receipts.

The frozen backend suite passed 929/929 tests. Its retention/replay coverage includes real multi-anchor compaction over 64 natural seeds with owned evidence checked against full records, compact receipt and crash-atomic coverage, restart/resume and policy-mismatch guards, and direct/replay parity against independent Python decisions. The final all-reject cohort itself retained no candidates, so the separate positive natural run and synthetic survivor fixtures cover candidate serialization and retention behavior. Process-tree RSS was sampled during the final arms (observed maxima 86,552,576 B control and 96,030,720 B selected); sampling is not a continuous or guaranteed peak measurement.

The earliest O3/native/LTO builds have source digests that include the earlier builder-script hash `2cbaed11702766d9c934fcd3362f42a7652667ce1cb28642f8737feb8989d3a3`; later chunk/profile/PGO builds use builder hash `67ca87a3e8e95f43515bb032004f7b6ec7f189abd9569d98d19f1ee6b41da8d3`. Phase2 verified that native, bridge, and vendor inputs match. The hash difference is builder bookkeeping, including the later preservation of OpenMP LTO/PGO link flags and effective compiler identity. LTO build identities show `-flto` in their linker flags.

## Compiler and PGO decisions

The primary rate is external CLI wall time. Checkpointed throughput, native service time, memory, output bytes, completion receipts, and semantic hashes are recorded separately per arm.

| Variant against portable O3 | Inputs | Counterbalanced result | Disposition |
|---|---:|---:|---|
| `-march=native` | 50k | 0.978× control-over-native; 10k smoke was 1.041× | Keep portable O3; native result was slightly slower on the 50k confirmation. |
| LTO | 50k | 0.914× | Reject; slower. |
| `-march=native` + LTO | 50k | 0.993× | Reject; effectively even/slightly slower. |
| PGO use | 2 × 50k | 1.018× and 1.001×; geometric mean 1.0096× | Reject as below timing noise; retain portable O3. |

PGO training covered exactly 50,000 natural inputs and the fixture run exercised three `PREDICTED` plus one `PENDING` result. Apple LLVM 17 merged the two raw profiles into a 103,344-byte profile with the matching source/chunk/compiler manifest. The instrumented training CLI took 38.182 seconds (about 1,310 inputs/s), compared with roughly 20,000–28,000 external inputs/s on ordinary 50k trials; that profile-generation slowdown is recorded and is not mistaken for PGO-use runtime. Build identities and profile SHA are in `pgo-training/pgo-merge.json` and `pre-heldout-results.json`.

## Scheduling and chunk decisions

Repeating the 16-thread/4096 baseline against each thread count yielded geometric-mean external speedups of 1.087× at 24 threads and 1.128× at 30 threads. The 32-thread screen was 1.060×. The 34-thread repeat was 1.118×; its earlier raw pair reported 1.710× because the control arm took 3.595 seconds, an obvious outlier retained in the raw data but excluded from the estimate.

Larger batches improved the faster thread settings. At 30 threads, batch 8192 was 1.057× and batch 16384 was 1.142× versus batch 4096. At 34 threads, they were 1.110× and 1.144×. Two direct finalist pairs comparing the same portable O3 extension at 16/4096 and 34/16384 gave 1.344× and 1.295× external speedup, geometric mean 1.319×. Checkpointed rates rose from 30,066 to 42,305 inputs/s in one pair and from 29,240 to 43,583 inputs/s in the other.

Work chunk 64 showed a favorable 1.043× external-wall ratio in one pair, but checkpointed throughput declined from 42,437 to 41,495 inputs/s; it is not selected. Chunk 128 was slower, at 0.965× external-wall speedup with a lower checkpointed rate. Keep chunk 16. The selected heldout arm is portable O3, chunk 16, 34 threads, batch 16384; control is the same extension at 16 threads and batch 4096.

## Native stage and allocation disposition

The diagnostic-only profile covered 510 tuning seeds plus two natural positive survivors. A one-thread profile took 0.24235 seconds of C wall time. Non-overlapping top-level profile stages 0–13 sum to 0.20953 seconds; the 0.03282-second residual (13.54% of wall) is only an upper bound on allocation, seed setup, loop/bookkeeping, profiling/clock overhead, and all other work outside those timed stages. It is not an allocation-only estimate. The profile is diagnostic and does not support throughput claims.

On that sample, Stronghold discovery plus delayed query took 0.07335 seconds, biome palette 0.05699 seconds (two positive inputs), and Trial Chamber floor checks 0.02754 seconds. Mineshaft floor checks were two calls totaling 0.00880 seconds. The profile resets the mansion cache per seed; it observed 30 queries and no hits in this sample. Inventory substage timers are nested inside the full-inventory timer and must not be added to the top-level total. See `w2-profile-1t.json` and `w2-profile.json` for the parallel diagnostic and complete histograms.

Static audit finds eight `nb_alloc` call sites. Discovery-copy storage and the per-seed `NBAnchor` output are allocated before later compact-mode rejection can occur, so rejected inputs are not allocation-free. Scratch and flags are grown and reused per worker; generator/context is reused within a native call; the mansion cache resets per input. Lazy structure, nether, palette, biome, and output buffers allocate when their stages need them. No source instrumentation was added to count exact calls. A zero-allocation reject-path patch is deferred as unmeasured; the 13.54% residual is too broad to establish its benefit.

The measurements below make the remaining W2 hypotheses explicit. Service intervals overlap, so the seconds are reported as separate observations and must not be added together.

| Hypothesis | Measured evidence | Disposition |
|---|---|---|
| Fatal-floor early exits and v2 classification | Corrected v2 parity passed on all seven builds. Timed runs all used the same v2 policy. | Correctness is verified, but no old-policy side-by-side was run; do not attribute semantic savings to same-policy speedup. |
| Scratch, generator reuse, and mansion cache reset | Scratch/flags grow per worker; `ss_create` is once per worker per native call; cache resets per seed. The 512-input profile had 30 mansion queries and zero cache hits. | Reuse already exists; no additional patch supported. |
| Allocation and shared allocation bookkeeping | One-thread top-level residual is 0.03282s (13.54% of 0.24235s C wall), only an upper bound. `nb_alloc` atomically reserves bytes, but dynamic calls were not counted. | Allocation-only benefit remains unmeasured; defer the zero-allocation reject-path idea. |
| Seed packing and preparation | Across two finalist pairs, median seed-preparation was 0.0480s at 16/4096 and 0.0785s at 34/16384; preparation-wall was 0.0299s and 0.0327s. Task preparation was about 0.00004s and 0.00003s. | No packing variant was measured; these components do not support a standalone patch. |
| Queue pressure | Pipeline state showed 13 batches / 4 batches, at most 3 outstanding in both settings, and maximum estimated prepared-owned bytes of 501,004. Cumulative queue-wait was 1.453s / 0.958s, overlapping other work. | No queue-cap variant was tested; pressure is bounded in this run, but a queue optimization is unmeasured. |
| Filter order | The same corrected v2 order was used for every arm; parity remained exact. | No alternate order was run. Preserve current order; do not claim this avenue exhausted. |
| Delayed Stronghold query | Discovery plus delayed query used 0.07335s, 30.3% of one-thread C wall in the diagnostic. The compact path runs the exact query after two cheap structure slots pass. | The diagnostic combines early discovery and delayed query; no placement A/B exists. Keep current placement and defer alternatives. |
| Mineshaft floor | Two calls totaled 0.00880s (3.6% of diagnostic C wall) among 512 inputs. | Rare in this sample; no optimization run. Preserve exact search and defer. |
| Biome palette | Two positive-input calls totaled 0.05699s (23.5% of diagnostic C wall). | Meaningful cost on these two candidates, but too few positives to generalize. No algorithm change; revisit only with candidate-preserving trials. |
| Record extraction and serialization | Finalist medians at 16/4096 vs 34/16384: record 0.0276s / 0.0684s, encoding 0.0126s / 0.0208s, hashing 0.00277s / 0.00287s. Each retained only two positive inputs. | Measured, but no implementation variant; not an identified standalone bottleneck for this workload. |
| Receipts and SQLite | Each arm validated 50,000 receipt inputs and complete checkpoint coverage. SQLite was 708,608 bytes (14.17/input) vs 700,416 bytes (14.01/input); median SQL was 0.0081s / 0.0092s, commit 0.0092s / 0.0096s, writer wall 0.0246s / 0.0312s. | No writer/SQLite change measured or indicated by these timings. Integrity passed. |
| Startup, monitor, and shutdown | Median external-minus-internal wall was 0.759s / 0.689s; this bundles process startup, CLI setup and harness process sampling. RSS samples were 4 / 3 per arm; observed process-tree peaks were 85–87 MiB / 93–96 MiB. Median shutdown was 0.00037s / 0.00068s. | Startup and sampler CPU were not isolated; sampled RSS is not a guaranteed peak. Shutdown is small. No monitor-specific patch is supported. |

This is an explicit bounded disposition, not a claim that every possible CPU optimization is exhausted. The queue, filter-order, and alternative Stronghold-placement ideas remain unmeasured; palette work is a potential candidate-side follow-up, while allocation and Mineshaft savings are unsupported by this sample.

## Final heldout confirmation

The final runtime freeze identity is in `final-runtime-identity.json`: Python/config digest `9ab26d1119537658e9e6116efbf79721df0c906e80d06ae440dc6a0e84e2d6b6`, native extension `794b62a893f5fef7e9859bac8175354a9a452ed1a34e280a89e36e2dd677492f`, native source digest `999cd4ca5628c1ce21f35c7e2191f4a032cfbbf1745ac9e88ca625b26b3ad8de`, and pinned OpenMP runtime `af4f16ce7fb34f8e444d328b105adead0b655768e32aadbf438972d8e79f92f6`.

| Pair | Order | Control external wall | Selected external wall | Control / selected speedup |
|---:|---|---:|---:|---:|
| 0 | AB | 3.8138s | 2.8518s | 1.3373× |
| 1 | BA | 3.8317s | 2.8232s | 1.3572× |
| 2 | AB | 3.8922s | 2.8162s | 1.3821× |
| 3 | BA | 3.7544s | 2.8855s | 1.3011× |
| 4 | AB | 3.8142s | 2.8473s | 1.3396× |

All ten invocations scanned exactly `[9000000000,9000100000)` under the frozen v2 B=2 policy, with completed checkpoint and retention receipts, SQLite integrity `ok`, identical O3 extensions inside each pair, and matching retained-record semantics. Each arm retained zero candidates on this all-reject cohort; the empty records therefore do not establish positive candidate service. The external CLI median fell from 3.8142s to 2.8473s, a median paired speedup of 1.3396× and geometric-mean speedup of 1.3432× (range 1.3011×–1.3821×). Exact paired bootstrap, resampling the five pair ratios 3,125 times, gives a 95% percentile interval of [1.3194×, 1.3655×]. This clears the plan's 5% improvement threshold and interval-above-1 criterion.

Checkpointed throughput is a separate service measure: median 31,793 inputs/s for control and 46,019/s for selected, with a median selected/control ratio of 1.448×. Process-tree RSS samples peaked at 86,552,576 bytes for control and 96,030,720 bytes for selected; SQLite files were 221,184 and 208,896 bytes respectively, while observed WAL peaks were 1,256,632 and 589,192 bytes. All per-arm overlapping service timers, batch limits, sample counts, and byte measurements are in `final-heldout-summary.json`; they are not summed as a wall-time decomposition.

Because the heldout range had no survivors, a separate one-input positive natural service run used already observed tuning seed index `2028375`, outside the heldout interval. At 34 threads and batch 16384 it retained one `PREDICTED` candidate and one anchor, completed its receipt and SQLite integrity check, and exercised record serialization (`external wall 0.8599s`, internal scan wall `0.2162s`, native service `0.0597s`). This one-input duration is not a throughput estimate and is excluded from the five heldout pair ratios. The exact synthetic direct/replay and compact-retention fixtures remain recorded in `parity_gate.json`.

## Budget accounting

`timing_budget.json` records 161.715 seconds total measured CLI/profile execution against the 900-second target and 1,200-second hard cap (160.486s CLI, 1.228s diagnostic/PGO profile work). This includes the bounded tuning/PGO matrix, five heldout pairs, and separate positive natural service run. Compiler build times are recorded separately in each build `identity.json`.
