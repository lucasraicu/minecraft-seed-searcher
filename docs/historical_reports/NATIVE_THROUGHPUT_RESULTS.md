# Native persisted throughput results

The later locked 2048/1024 revision and terrain/BDS investigation are recorded in [NATIVE_LOCKED_GEOMETRY_RESULTS.md](NATIVE_LOCKED_GEOMETRY_RESULTS.md). Measurements below retain their original policy and cohort.

Implementation results, 12 October 2026. The original full-evidence
adoption gate passed; native execution is integrated as an explicit option. The
Python route remains the default. Production held-out and terrain receipts are complete. The user additionally authorized compact retention of predicted
survivors and near misses with at most two unmet baseline requirements, while
keeping full-evidence mode. This is an explicit change to the storage contract.

The final actual CLI held-out medians are **3,730.73 persisted inputs/sec** with
full evidence, **12,226.51 checkpointed scanned inputs/sec** allowing two misses,
and **1,174.71 persisted inputs/sec** for the comparable Python control. The
5,000/sec full-evidence target remains unmet. Compact benchmarks retained no
natural candidates; accepted records are covered by positive and near-miss fixtures.

| Milestone | Status | Evidence |
|---|---|---|
| M0: profile and preserve control | Verified | `runs/native-throughput-2026-10-12/control`, initial identity/diff/status and original profile |
| M1: direct records | Verified | Direct/replay/independent evaluator parity, including complete positives and late failures; controlled record-cost medians 0.256 vs 0.412 s / 2,048 inputs |
| M2: validated owned preparation | Verified | Shared dictionary/prepared validation, canonical template encoding, task batching, unchanged v1/v2 retry digests, WAL/FULL retained |
| M3: bounded overlap | Verified | One native producer, one preparer, one connection-owning writer; two/three bounded in-flight batches, byte caps and recoverable leases |
| M4: correctness and performance gates | Verified | Repeated three-cohort and held-out comparisons, full semantic/task parity; final integrated suite: 809 tests passed; 1,184 serial ASan inputs |
| M5: production option | Verified | Actual CLI three-cohort and held-out gates passed; packaged serial, CLI resume, exports and compatibility validated |
| M6: V1 Coastal Continent profile | Verified; additional C work deferred | Native sampling dominates; complete raster/decision and independent cache-accounting comparison passed |

The first bounded pipeline measured 2,659 persisted inputs/sec. Tuning the bounded
SQLite page cache and checkpoint interval brought two-stage runs to about 3,300/sec;
three-stage overlap reached about 3,500/sec. A spawned preparation worker lost at
about 3,100/sec and remains an experiment. Canonical seed-summary templates reached
about 3,800–3,950/sec in tuning. These short tuning runs are not the final adoption
comparison, and none establishes the 5,000/sec target.

The completed three-cohort counterbalanced comparison (three repetitions per arm)
measured **3,061.70 durably persisted inputs/sec** for native, **1,164.12/sec** for
the best fresh current Python profile (36 processes), **1,128.78/sec** for the
current 30-process profile, and **1,177.36/sec** for the preserved original
30-process control. Native/current paired cohort ratios are 2.634, 2.661 and 2.595;
the aggregate ratio is 2.630. Native/original is 2.600. Complete records, counters,
discovery tasks, inventory work, V1 tasks and completed coverage match. Held-out
validation subsequently passed, and production integration is tested below.

Shared-store changes alone did not improve the fresh Python path: current versus
original at 30 processes is approximately 0.959x. The substantial native gain comes
from direct/template preparation and bounded overlap, not a claimed common writer
speedup. Native trial rates range from 2,984.24 to 3,216.73/sec; peak observed native
process-tree RSS is 368,525,312 bytes, versus 1,912,623,104 bytes for current Python
at 36 processes. Native SQLite cost averages 14,317 bytes/input. Short tuning numbers
were higher and are not substituted for these fresh complete-lifecycle measurements.

In full mode every processed input, discovered anchor, pending candidate, discovery task and V1
task remains durable. Schema-fixed JSON fragments are encoded once; variable data
uses canonical numeric/string representations. Complete positives and later failures
use full direct records. The replay adapter and Python evaluator remain oracles.
No parity exclusions were added. Native generation allocation failures and byte-budget
failures stop publication rather than truncate evidence. ASan is serial buffer testing,
not a race or leak certification.

The retained source snapshot preserves the dirty starting work and original Python
control. Fresh comparisons include the original 30-process path, the changed-store
30-process path, the best tuned Python process count and the native pipeline. The
benchmark preflight uses 65,536 bytes per stored input repetition and a 16 GiB reserve.
Repetitions do not increase distinct search volume. Prediction throughput does not
certify actual Bedrock playability or establish time to a complete world.

## Held-out full-evidence adoption gate

The original pre-integration comparison used the same additional **100,000 distinct
inputs**, repeated three times per arm. Native median: **2,793.36/sec**, versus
**996.41/sec** for the best current Python control and **1,035.99/sec** for the
preserved original 30-process control. Native/current is **2.803x**; native/original
is **2.696x**. Native trial rates were 2,644.52–2,871.12/sec. Every semantic record,
count and task fingerprint matched, with 184,879 retained anchors and zero complete
baseline survivors. Maximum observed native RSS was 573,956,096 bytes. SQLite
used 1,423,724,544 bytes (14,237 bytes/input). The target remains unmet in full mode.

In the last held-out native trial, inclusive service timings were 7.98 s native,
8.95 s record preparation, 9.18 s range preparation (6.71 s hashing), and 30.18 s
writer service (18.27 s SQL, 11.63 s commit), for 34.83 s total wall time. Work overlaps;
these timings must not be added to derive wall time. SQL service can include GIL
contention and commit includes WAL/checkpoint work. This is not a claim of 30 s disk
hardware time. Sorting candidate/task inserts was tested afterward: the approximately
0.4% median gain was within repeat variability, so the experiment was not adopted.

## Integrated production CLI comparison

Fresh child CLI processes included imports/startup, computation, preparation,
FULL SQLite commits, queue drain, process exit and close. All three 10,000-input
cohorts were repeated three times with rotated arm order. Builds/tests were kept
out of timed trials. Diagnostic readback/integrity comparisons were outside every
arm's timer.

| Mode | Aggregate inputs/sec | Observed trial range | Peak process-tree RSS | Mean SQLite bytes per 10,000 inputs |
|---|---:|---:|---:|---:|
| Python, full evidence, 36 workers | 1,158.71 | 1,132.01–1,179.28 | 1,916,682,240 | 143,561,159 |
| Native, full evidence, 16 threads | 2,870.02 | 2,777.48–2,913.95 | 427,405,312 | 143,183,872 |
| Native, strict survivors, 32 threads | 8,380.31 | 7,748.52–8,594.27 | 135,921,664 | 196,608 |
| Native, up to two misses, 32 threads | 7,041.84 | 6,795.84–7,241.08 | 134,475,776 | 196,608 |

Full-mode paired cohort speedups are 2.461, 2.487 and 2.483, with zero semantic or
task differences. Compact rates measure **checkpointed scanned inputs/sec**, not
complete per-input evidence persistence. Compact controls had zero natural retained
candidates; complete positives and one/two/three-miss fixtures verified selection,
full required inventories, missing reasons, witnesses, scores, durability and exports.
Storage grows with accepted near misses/survivors as well as the number of checkpoint
ranges. It is not guaranteed to stay at 196,608 bytes.

## Storage and recovery contracts

Full mode keeps every input, discovered anchor, pending candidate and original task.
Its canonical template path applies only to the audited first-Mansion failure;
other paths use direct equivalent records. Legacy retry digests retain exact original
framing. Private encoded/prepared objects are immutable, own their bytes and reject
public construction. C buffers are freed only after preparation has copied evidence.

Compact mode evaluates at most 25 predictor requirements at each Stronghold anchor:
12 count requirements and 13 biome families. A count shortfall is one miss regardless
of deficit size. The C path stops once the allowance cannot be met, drops unwanted
anchors, and returns compact retained results plus a fixed-width decision buffer.
Python hashes that buffer without constructing individual rejected record dictionaries.
Accepted near misses receive full required predictor inventories and an exact miss list.
They stay `PENDING` with `retention.classification=NEAR_MISS`; complete baseline
survivors stay `PREDICTED`. V1/actual-game requirements are subsequent gates.

SQLite atomically saves retained seed/candidate evidence, their discovery/inventory/V1
tasks, aggregate counters and a range receipt containing a decision digest. Rejected
inputs receive no seed/candidate/task row. The receipt certifies predictor processing,
not actual-world discovery recall. Mode and miss allowance are checkpoint identities;
changes require a fresh run. Stale leases, foreign prepared policies and altered retry
bytes are rejected. Crash tests cover before/during transactions and after a commit
with lost acknowledgement. Smaller resumed batches split recovered native leases.

Both modes use FULL synchronization and WAL, a bounded 128 MiB page cache and
64 MiB checkpoint interval. The 128 MiB journal retention setting is not a hard WAL
cap. Three outstanding batches have per-call native and prepared byte caps, explicit
backpressure, error propagation and owned cleanup. Native calls are finite and joined
on cancellation rather than unsafely killed. Disk preflight uses conservative 65,536
bytes/input per stored repetition, with a 16 GiB free-space reserve. RSS plus configured
Docker reserve is checked against the memory ceiling. Neither compact mode nor speed
removes the prediction-scale/large-search readiness gates.

## Artifacts and usage

Raw sources, profiles, tuning losses and trial receipts are retained in
`runs/native-throughput-2026-10-12/`. `paired/` and `heldout/` preserve original and
changed-store controls; `production-paired/` and `production-heldout/` exercise the
actual CLI; `native-final/` contains the load-validated OpenMP extension identity;
`asan-verified/` contains final sanitizer sources/logs. Original prototype runs remain
unchanged. The original `_native.abi3.so` hash still matches the initial snapshot.
Portable serial batch execution is built separately and exercised through the CLI.

See [README.md](README.md) for build, full/compact scan, resume and SQL/export commands.
The existing Python route is available with `--executor python` on a fresh output.
Native resume requires its saved source/runtime identity; an incompatible checkpoint
never silently switches evaluators. V2 remains outside the active pipeline. Prediction
rates and zero-survivor samples do not establish probability of complete-world success,
actual Bedrock playability or time to discover a world.

## Final held-out production result and adoption decision

The actual CLI used the same held-out **100,000-input** cohort, repeated three times
per arm in rotated order, with fresh databases and complete integrity/readback gates.

| Mode | Median inputs/sec | Trial range | Speedup against comparable Python CLI | Peak RSS | SQLite bytes |
|---|---:|---:|---:|---:|---:|
| Python full evidence, 36 workers | 1,174.71 | 1,169.99–1,182.28 | 1.00x | 2,575,974,400 | 1,427,324,928 max |
| Native full evidence, 16 threads | **3,730.73** | 3,660.23–3,889.98 | **3.176x** | 663,068,672 | 1,423,736,832 |
| Native strict survivors, 32 threads | **17,252.74** | 16,690.03–17,391.79 | 14.687x, different retention contract | 161,800,192 | 208,896 |
| Native at most two misses, 32 threads | **12,226.51** | 11,993.67–12,341.01 | **10.408x**, different retention contract | 163,532,800 | 208,896 |

All full-mode semantic/task fingerprints match. Compact mode processed every range,
with zero natural retained candidates, and every range receipt validated. Positive
and near-miss fixtures exercise the accepted-record route; relaxed natural controls
also test retaining and dropping different anchors within the same seed. Repetitions
are not additional distinct input volume. The bounded primary cohorts contain
130,000 distinct inputs in total (30,000 tuning/comparison inputs plus 100,000 held-out).

Median CPU seconds per 100,000 inputs were 299.23 (Python), 212.49 (native full),
165.90 (strict compact) and 239.05 (two-miss compact). The extra near-miss criteria
cost generation work even when nothing is saved. Median batch turnaround p50/p95
were 2.935/3.900 s (native full), 0.619/0.651 s (strict) and 0.890/0.937 s (two misses).
These include bounded queue residence. Peak WAL sizes were approximately 68.7 MB
(Python), 132.0 MB (native full), 1.27 MB (strict) and 1.29 MB (two misses). RSS is
process-tree sampling and can double-count shared pages; the CLI figures include
its outer measurement process. Earlier adapter receipts sampled resources inside
the evaluator process; the CLI harness samples from outside and includes CLI
imports and exit. Results from both harnesses remain retained and shown separately.

The last production full-mode trial took 25.71 s wall time. Inclusive service costs
were 6.46 s native, 7.99 s record extraction/preparation, 6.50 s row preparation
(4.91 s hashing), and 21.07 s writer service (10.92 s SQL, 9.93 s commit). These overlap
and are not additive. Full-mode storage remains about 14.24 KB per input; retaining
complete evidence is not made cheap by filtering harder. Native caps cover output
and scratch buffers; fixed generator contexts are separately counted in RSS monitoring.

**Adopt the native path as an explicit production option for the audited blueprint
profile and this validated host/toolchain.** Full-evidence performance, semantic,
durability and resource gates pass on every cohort and the held-out set. Keep Python
as the default compatible route and portable serial native as a tested option. Compact
retention is separately adopted under the user's explicit two-miss authorization.

**The 5,000/sec full-evidence target and 10,000/sec full-evidence stretch target remain
unmet.** Compact checkpointed scanning exceeds 10,000/sec on the held-out cohort,
with a different evidence contract. Remaining full-mode costs are hashing/record
preparation, SQL index/row insertion and FULL WAL/commit service. Faster compact
scanning neither certifies playability nor estimates time to find a complete world.

## Native-only and V1 measurements

Fresh C-only aggregate rates (same three 10,000-input cohorts, three repetitions,
batch 4,096) were 1,267.83/sec at one thread, 14,912.45/sec at 16, 18,529.50/sec at
32 and **19,205.02/sec at 36**. These include C context/setup/generation/result-buffer
work and exclude record preparation, SQLite and CLI startup. The 36-thread profile
is a C-only diagnostic; the production pipeline reserves CPU slots for preparation
and writing. Native-only rates must not be substituted for durable throughput.

V1 controls are **three labeled natural centers with no demonstrated baseline
eligibility**, plus synthetic 75%, 80% and 85% mainland boundary cases. The complete
six-resolution durable workflow (128, 64, 32, 16, 8, 4) took 4.233 s unprofiled:
**0.709 control candidates/sec**, about 1.411 s/candidate. It saved 18 raster observations,
18 work units and three variant records. Fine work below the scheduling threshold
remains deferred until explicit resume; the profile follows those finite successors
and verifies every completed unit's attempts/digest/result remain unchanged. A final
resume does no new work. This is a small standalone terrain service sample, not a
world-survivor throughput estimate.

The instrumented durable workflow took 4.246 s. Native `ss_heights` used 3.649 s
(86% of profiled wall time); compression used about 0.215 s and coastal evaluation
0.183 s (4.3%). Connectivity already uses compiled SciPy operations. Moving more
Python geometry into C has a small measured ceiling and is not justified here;
additional terrain C implementation is deferred.

The counterbalanced unconditional six-resolution raster comparison took median
4.595 s fresh versus 3.529 s with exact point reuse for three layouts: **1.302x**,
about 23.2% less wall time. Fresh queries were 589,680 versus 442,368 with reuse per
trial. All 108 raster/decision observations matched: height, biome, water and known
arrays and complete decisions, with timing fields omitted. Per-arm query/reuse
counters intentionally differ; their values were independently checked against
coordinate sets before expressing them as total samples in the decision hash. Raw
counter values and complete decisions remain in the receipts. No classification,
threshold, uncertainty or provider evidence was excluded to hide differences.

Profiling exposed and fixed pending-candidate terrain scoring: a null complete
baseline score now uses the observed partial score, while preserving `PENDING`
component status and preventing verified-score promotion. Both rotation and priority
schedulers have regression coverage. Baseline timing/selection is unaffected.
Failed preliminary profile/diagnostic attempts are retained; final evidence is
`coastal-clean/profile.json`, `coastal-clean/durable-profile.txt` and
`coastal-clean/cache-comparison-verified.json`.

Final verification is retained in `runs/native-throughput-2026-10-12/final-verification.json`:
809 integrated tests passed, 1,184 serial ASan inputs reported no errors, all 108
terrain comparisons matched, and the primary cohorts contain 130,000 distinct
inputs. The original generator extension remains unchanged and compiled native
source/runtime hashes match. `final-source/` retains the final source snapshot and
its hashes; the held-out directory also retains the exact measured adapter source.
Its only subsequent change adds synthetic-fixture provenance, outside production
evaluation. `git diff --check` passed.

## Subsequent ranking and profiling work

The later SQLite leaderboard, entered-stage/biome histograms, outlier rechecks and
bounded exact Mansion reuse are documented in
[NATIVE_RANKING_PROFILE_RESULTS.md](NATIVE_RANKING_PROFILE_RESULTS.md). That work
preserves the full and two-miss contracts and has its own fresh paired comparisons
and 820-test final suite. The rates and source identities above remain historical
evidence; the later store/index and native sources have changed. Their different
cohorts and diagnostic scopes are reported separately.
