# Sol remaining performance audit

Baseline `54b7d631b8bdb481894980a31be16aaa02901b18`; production `dynamic-envelope-1664-v1`. Production inputs/binary/runtime match the recorded identity. All builds and proposed edits are isolated under `/tmp/minecraft-sol-audit-20261015`; production remains unchanged. This report covers S0–S4 of [SOL_PLAN.md](../SOL_PLAN.md). No end-to-end scan, generation-to-SQLite benchmark, live sweep, deployment, or BDS verification was run.

**Status: complete; handoff reviewed by Codex.**

## S0: Provenance and reusable evidence

**MEASURED / source identity checked.** The host has 18 physical and 36 logical CPUs, Intel Xeon W-2191B, 64 GiB RAM, macOS x86-64. Experiments use Apple Clang 17, native-CPU optimization, LTO, the pinned libomp runtime, and freshly generated PGO for every arm/chunk. Each identity is retained under `builds/`; `manifest.json` records the resolved policy/hash, production identity, hardware and workload intervals. Source-matched retraining is used for control too, so the code comparison is not a fresh profile versus stale production PGO comparison.

Training: permutation run key `2026101402`, indices `[0,10000)`, four threads, plus one positive fixture. Evaluation uses run key `2026101401`, with disjoint ordinary/profile/component cohorts. Because the permutation is invertible, compare the nonwrapping `index+run_key` intervals to establish training/evaluation separation. Different adjacent keys alone are insufficient. Repeated same-input arms and intentionally repeated scheduling/profile cohorts are recorded, not represented as independent seed samples.

Reusable prior evidence: three P1 coordinate/allocation findings, the delayed-generator proposal, targeted resource/queue/cache observations, and the earlier regression suite. Missing evidence before this run: Mansion subcomponent attribution, source-matched confirmation of unused initialization, conditional witness-gate timing, staged scheduling, survivor-stage and reconstruction costs. These are addressed below. The previous completed end-to-end measurements are historical only and were not rerun.

## S1: Mansion attribution

**MEASURED, instrumented attribution; nested times must not be summed.** The bounded ordinary cohort contains 100,000 natural inputs, permutation indices `[50000000,50100000)`. One separate TLS diagnostic record per input preserves stage data before result compaction. Final performance timing uses different, uninstrumented builds.

| Component | Calls/entries | Summed worker seconds | Fraction of 97.156 seed-evaluation seconds |
| --- | ---: | ---: | ---: |
| Mansion inventory | 39,682 | 83.163 | 85.60% |
| Mansion viability, nested | 234,083 | 82.614 | 85.03% |
| Legacy SurfaceNoise initialization, nested | 234,083 | 73.692 | 75.85% |
| Approximate height, nested | 234,083 | 3.567 | 3.67% |
| Radius biome check, nested | 234,083 | 5.248 | 5.40% |
| Y=63 witnesses for viable starts | 1,397 inventories | 0.0186 | 0.019% |
| Raw Nether placement pair | 100,000 | 1.614 | 1.66% |
| Outpost viability inventory | 943 | 0.0795 | 0.082% |
| Nether viability pair | 481 | 0.0141 | 0.014% |
| Dynamic event/cell stage | 11 | 0.0110 | 0.011% |

There were **234,083 raw Mansion starts, 234,083 cache queries, zero cache hits, and 1,428 viable starts**. Average viability calls per entering inventory were about 5.90. Cache entries are reset each seed, `nb_pair(slot=0)` runs once, and inputs are sorted/deduplicated. **PROVEN_BOUND:** no repeated positions remain within the inspected dynamic cache lifetime. Its search/insertion cost is unmeasured; zero hits alone does not justify a particular throughput claim or a new data structure.

Sampling was attempted before instrumentation. The `/usr/bin/sample` capture includes substantial Python startup/import time; its Perlin frames corroborate the hotspot but its percentages are not whole-kernel percentages. CPU Counters recording succeeded, but the exported trace provided no usable cycle, instruction, branch-miss, or cache-miss event values. **INCONCLUSIVE:** cache/bandwidth/branch saturation and false sharing. No padding or spatial-index proposal follows from elapsed time.

### S-PERF-01: Remove unused modern Mansion initialization

**PROVEN_BOUND:** in `finders.c:1825`, `initSurfaceNoise(&sn, DIM_OVERWORLD, g->seed)` constructs an object whose contents the active Overworld `mapApproxHeight` branch (`generator.c:623`) never reads. Initialization consumes `60*(3+256)+2620 = 18,160` MT draws, plus MT seeding. This is concrete redundant work. The diagnostic initialization time is 89.20% of Mansion viability time.

**MEASURED:** compare `no-surface-init` with a freshly trained unchanged control, and `lazy-no-surface-init` with `lazy`, using source-matched PGO. See the trial summary below. The minimal vendor diff affects only the modern Mansion branch and passes `NULL` to the branch that does not read SurfaceNoise. It does not change floating-point arithmetic.

**Adoption qualification:** the removed initializer reseeds/advances thread-local MT. Public ambient RNG state is therefore not identical. Source tracing establishes that relevant subsequent pipeline RNG consumers reseed; native component/interleaving tests confirm the bounded uses exercised here. Do not assert this is a universally side-effect-free vendor change for arbitrary external callers.

## S2: Conditional preflight and reuse

The raw Nether pair/bounds ran on 100,000 inputs; 39,898 reached raw Outpost, 39,687 raw Mansion, 39,683 raw Trial/Ancient/Village, and 39,682 Mansion inventory. Thus the initial raw Nether gate rejects about 60.1% before OW inventories, while the subsequent raw Outpost/Mansion gates reject relatively few of their entering seeds. Their measured conditional costs do not justify blindly moving all raw checks or trying every permutation.

The Mansion stage has 39,682 timed entries, followed by 1,097 timed Stronghold-discovery entries, 943 Outpost inventories, 481 Nether viability pairs, 403 Jungle inventories, 91 Desert, 30 Monument, 22 Ancient, and 11 Village/Trial/Portal/Shipwreck/Mineshaft and cell-stage entries. Native stage-field counts are nonzero-time proxies, not independent exact entered-predicate counters; custom raw/Mansion/Outpost/Nether hooks are exact. Preserve that distinction when calculating conditional rates.

### S-PERF-02: Necessary raw Dark Forest witness gate

**PROVEN_BOUND:** every viable Mansion counted toward the mandatory goal is a raw Mansion start whose Y=63 biome equals Dark Forest. If too few raw starts have that exact witness, no viable subset can satisfy the goal. The candidate gate applies that necessary condition before viability. If it passes, the original inventory still runs and retains every viable start, including non-Dark-Forest starts. It adds no spatial index, relaxed boundary, or altered lattice.

**MEASURED:** evaluate this increment against `lazy-no-surface-init`, not against the slower original initialization path. Full/compact records and fixtures match; direct Mansion component positives are checked separately. This is a third experiment arm, while the previous lazy-generator proposal is explicitly prior work. At most two new adoption proposals are retained: redundant initialization removal and this gate.

### S-PERF-03: Prior delayed generator seeding

**MEASURED:** still applicable and still unapplied. Generator initialization is deferred until the first biome/viability consumer; full-evidence discovery ordering is preserved. The independent `lazy` arm measures its effect on the unchanged baseline; the combined arm measures interaction with S-PERF-01. Gemini's verifier checks parity but does not measure speed, so its +10% repeats the prior audit rather than adding new timed evidence.

**MEASURED: five alternating confirmation trials, rates in native inputs/sec.** Each arm processes 1.2M inputs per trial (6M distinct inputs, indices 52M–58M); all trial arms exceed five seconds. Seeds, record walking and receipt hashing are outside the native timer.

| Trial | control | lazy | no-surface-init | lazy-no-surface-init |
| --- | ---: | ---: | ---: | ---: |
| 1 | 45,974 | 49,798 | 144,495 | 178,851 |
| 2 | 46,208 | 50,629 | 146,761 | 179,282 |
| 3 | 46,511 | 50,703 | 150,510 | 182,695 |
| 4 | 46,286 | 50,682 | 147,568 | 182,471 |
| 5 | 46,110 | 50,427 | 149,553 | 182,995 |
| Median | 46,208 | 50,629 | 147,568 | 182,471 |

- `lazy` versus matched control: median paired **+9.36%**, ratio range 1.083–1.096.
- `no-surface-init` versus matched control: median paired **+218.82%**, ratio range 3.143–3.243.
- `lazy-no-surface-init` versus matched control: median paired **+292.80%**, ratio range 3.880–3.969.
- Lazy seeding added after removing surface initialization: **+22.36%** median paired. Effects are not additive.

**MEASURED: the raw witness gate versus the already optimized control**, five alternating trials of 1.5M inputs each (7.5M distinct inputs, indices 100M–107.5M), all arms over five seconds:

| Trial | lazy-no-surface-init | dark-gate |
| --- | ---: | ---: |
| 1 | 187,115 | 224,523 |
| 2 | 187,437 | 220,769 |
| 3 | 178,380 | 211,755 |
| 4 | 182,715 | 215,413 |
| 5 | 179,867 | 213,158 |
| Median | 182,715 | 215,413 |

Median paired gate improvement: **+18.51%**, range 1.178–1.200. Main control and gate medians are different cohorts; their quotient is not a directly paired total improvement. The corresponding full before/after receipts match on every trial. No natural retained survivor appears in these ordinary benchmark cohorts.

Codex additionally reran two alternating 300k-input trials for the four main arms and two for the gate comparison on new index ranges. Both confirm the direction/large magnitude and identical receipts; short trials vary more and are not substituted for the long confirmation estimates. The machine had normal light desktop load, no competing audit build/test/scan during timings, and no affinity/thermal control. All per-trial rates and build hashes are retained.


**MEASURED remaining attribution:** after both initialization changes, Mansion inventory remains 57.48% of instrumented summed evaluation (height 20.95%, radius 32.53% nested). After the witness gate, Mansion inventory runs on 3,941 inputs / 26,592 starts; the gate consumes 23.88%, remaining Mansion inventory 22.32%, and raw-preflight-plus-final-Nether 24.19%. The biome-point hook overlaps gate/witness time and must not be added again. This profile no longer has a single 75% redundant initializer. The optimized non-gated capture retains an empty slot 12 timing hook; it is not initialization work. The gate capture removes that empty hook and explicitly relabels slot 12. These are non-PGO diagnostic fractions, not throughput comparisons.

## S3: Staged scheduling

**MEASURED:** compare threads 16/18/24/30/34 at chunk 16,batch 16,384; chunks 16/64/128 at the strongest thread count; then batches 4,096/8,192/16,384 at the strongest combination. The screen uses three alternating trials per stage on the same 200,000 natural inputs. It is deliberately not the Cartesian product. Five long paired trials compare the existing operating point with the closest batch contender.

| Screen | Threads/chunk/batch | Median inputs/sec |
| --- | --- | ---: |
| threads | 16/16/16384 | 128,849 |
| threads | 18/16/16384 | 138,530 |
| threads | 24/16/16384 | 153,040 |
| threads | 30/16/16384 | 168,064 |
| threads | 34/16/16384 | 178,099 |
| chunks | 34/16/16384 | 174,764 |
| chunks | 34/64/16384 | 172,532 |
| chunks | 34/128/16384 | 161,684 |
| batches | 34/16/4096 | 131,321 |
| batches | 34/16/8192 | 150,986 |
| batches | 34/16/16384 | 172,134 |

**MEASURED operating point: retain 34 threads, chunk 16, batch 16,384 on this host.** Five long paired trials give batch 16,384 a **+15.23%** median paired gain over 8,192 on the initialization-optimized arm. Chunk 64's small screen difference is within screen variability; chunk 128 is clearly weaker in this sample. No justification to change chunk 16. The long batch confirmation includes median native batch latencies of 91.0 ms (batch 16,384) and 46.1 ms (batch8,192); partial tail batches are present in raw data. CPU utilization includes wrapper/hash work, uses process CPU/wall outside kernel timing, and is recorded per row. Scheduling was measured on the initialization-optimized arm; the gate is confirmed at the retained operating point, not subjected to an additional full scheduling sweep.

The baseline diagnostic at 34 threads/chunk 16 has worker summed-evaluation min/max 2.828/2.915 seconds, coefficient of variation **0.60%**. Per-worker measurements are instrumented snapshots, not PMU counters; configurations were not pinned to specific cores. Atomic claims for 100,000 inputs and 34 workers are 6,284 at chunk 16, 1,597 at 64, and 816 at 128. Fewer claims do not imply higher throughput, since larger chunks coarsen load balancing. Context creation also occurs once per worker per native call, making small batches more expensive per input.

## S4: Survivor path and Python boundary

The natural profile archives the 11 inputs reaching dynamic cell evaluation, but **none is a retained survivor**. They are replayed through diagnostic stages. Fully passing `(0,0,-1)` fixtures are explicitly synthetic; they exercise selection/prefix/evidence/reconstruction but do not execute real vendor viability or nonempty optional inventories. A separate forced-component probe uses natural inputs to measure full mandatory/optional inventories, OW/Nether prefix construction, and final evidence at center zero. Forced invocation does not mean those seeds satisfy the policy.

| Isolated component | Median per input | Input provenance |
| --- | ---: | --- |
| mandatory_inventories | 37.159 ms | 11 forced natural component inputs |
| optional_inventories | 31.146 ms | 11 forced natural component inputs |
| overworld_prefix | 88.593 ms | 11 forced natural component inputs |
| nether_prefix | 0.132 ms | 11 forced natural component inputs |
| final_evidence | 0.084 ms | 11 forced natural component inputs |
| native_seconds_instrumented | 1.041 ms | 32 passing fixtures, five trials |
| reconstruction_seconds | 30.518 ms | 32 passing fixtures, five trials |
| serialization_seconds | 3.094 ms | 32 passing fixtures, five trials |

Synthetic JSON output averages 192,805 bytes per retained input. Fixture per-input medians: event construction 7.344 µs, OW prefix 740.469 µs, Nether prefix 1.594 µs, argmin 0.281 µs, final evidence 98.563 µs; the encompassing cell stage 873.250 µs includes prefixes/optional work. The residual cell scanning/snapping/scoring work is about 124 µs by subtraction; nested timings are not independent. These fixtures bypass real viability and optional inventories, explaining why forced natural prefix/inventory costs are much larger. All 11 late-stage natural inputs reject before optional/prefix work; no eligible natural prefix entry frequency can be extrapolated from the forced calls.

Allocation traffic on one worker for 1/2/32 passing fixtures is 72/132/1,932 allocation calls; requested-live peaks are 1,872,336/1,921,244/3,388,484 bytes. All tracked memory is released after `nb_free`. This confirms scratch reuse while retained output grows with fixture count.

Seed-array marshaling (16,384 precomputed seeds, 20 trials) takes 1.711 ms median; hashing its fixed-width verdict buffer takes 0.547 ms. No native generator work is included in these two timings. This measures marshaling/hash work, not isolated CFFI dispatch latency.

The allocation-fault/live-byte instrument independently reconfirms a one-worker fixture peak of **1,872,336 requested live bytes**, excluding SeedContext and allocator metadata; cleanup returns to zero. This is sufficient to establish the memory-contract defect and a fixture working-set lower bound, not a universal peak for dense natural seeds. No persistent leak on the managed normal path is inferred. Exact allocator traffic for all survivor categories and hardware allocator overhead remain unmeasured.

**PROVEN_BOUND for this observed cohort only:** all event/cell work consumed 0.011% of the original instrumented evaluation sum. Even eliminating that observed stage entirely cannot yield a large original aggregate speedup on this cohort. This does not bound a different population with more survivors, nor the forced-palette workload. Per-survivor reconstruction/serialization costs are reported separately; their natural aggregate impact remains unknown without a representative retained-survivor frequency. No isolated writer benchmark is justified by a measured writer hypothesis, so none was added.

## Parity, architecture, and limitations

Four main PGO arms match natural full/compact semantic records on 256 inputs, 40 fixture variants in each retention mode, and 2,000 native component seeds. **134** component seeds have viable Mansions. Component scans retain raw/viable lists and Y=63 witnesses, followed by Stronghold, Outpost, Fortress, and Bastion operations. The gate comparison adds 256 component seeds with **19** positive Mansion seeds. Before/after equality is not an independent proof that the baseline policy is correct; the optional-count oracle mismatch is separately reproduced.

Additional natural optional-component parity passes on 262 inputs, including 134 known viable-Mansion seeds, followed in the same context by all five optional inventories and igloo-basement decisions. Nonempty viable totals are {'swamp_hut': 114, 'igloo': 879, 'trail_ruins': 1716, 'ocean_ruin': 11375, 'buried_treasure': 32765}; basement positives 441. This checks relevant RNG interleavings and nonempty optional generation, not full natural survivor eligibility.

The fixed half-open envelopes, negative-coordinate rational Nether bounds, 160 raw lattice event contributions per axis (126 OW + 34 Nether), full64 seed identity, strict/flexible floors, and the +30 second-Monument milestone were not changed. Clipping/deduplication of lattice events is preserved. Existing targeted geometry/scoring tests supplement these comparisons.

Keep C11/OpenMP. Wrapping these C calls in Rust has no measured speed benefit. GPU execution has not been benchmarked; divergent rejection/viability paths prevent a defensible speed prediction. SIMD is not justified by a measured substantial exact-arithmetic vectorizable stage. No instruction/cache evidence supports replacing contiguous arrays with trees or hash grids. CFFI batches work and releases the GIL; input seed-array creation copies data, verdict-buffer hashing is a view, and Python survivor reconstruction creates objects. Do not call the entire boundary zero-copy.

The audited memory-budget bypass and capacity-after-OOM crash remain production blockers. The Python independent oracle also has the reproduced optional-score mismatch. All proposed performance patches are provisional artifacts; no deployment or production edit occurred. The final combined disposition belongs to [Codex's review](../codex/FINAL_REVIEW.md), which reconciles Gemini's claims and patch applicability. This audit does not establish that all possible bottlenecks or speedups have been exhausted.
