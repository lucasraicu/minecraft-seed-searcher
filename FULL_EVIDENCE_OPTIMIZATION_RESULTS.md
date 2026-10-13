# Full-evidence persistence optimization — 12 October 2026

The production native full-evidence path improved from **1,413.39 to 2,466.15 durably persisted inputs/sec**, a **1.745× / 74.5% gain** in a fresh, same-policy, three-trial CLI comparison. The **5,000/sec target remains unmet**. Every processed input, discovered anchor, task and coverage record is still saved. This is not survivor-only throughput.

## Root cause and adopted changes

The retained 2,000-input profile attributed 0.544 seconds to record construction, 0.489 to encoding, 0.118 to hashing, 0.165 to SQL and 0.083 to commit. Profiling overhead is included in these diagnostic figures. The previous template encoder explicitly bypassed **all locked screening revisions**, so the active policy rebuilt and reserialized repetitive pending evidence.

`native_encoding.py` now uses bounded, configuration-local templates for common early locked failures. A template key includes missing requirements, score, evaluated/full observation state and observed counts. IDs, signed seeds, indices, exact bounds and every coordinate remain variable. Deferred observations and all uncertainty/evidence fields remain in the canonical JSON. There are at most 256 cached templates per encoder. Unsupported topologies, Mansion biome witnesses, palette evaluation, complete enumeration and cache overflow use the existing direct builder. Compact retention continues through its existing independent path.

Candidate JSON is byte-for-byte equivalent to the direct builder. Strings own their data before native buffers close. Summary counters, synthetic provenance and native stage timings are retained. As in the historical template path, templated per-seed timing reports native evaluator time; actual Python preparation cost is measured at batch level rather than fabricated per seed.

`store.py` reuses an immutable canonical `JSONEncoder` configuration instead of constructing an encoder for every call. It retains the same sorted keys, separators, ASCII escaping, float formatting, circular-reference checks and non-finite-number rejection. No schema, digest version, row validation, ranking formula, SQL index or durability setting changed.

The benchmark harness now explicitly selects the retained source through `PYTHONPATH` for CLI subprocesses and checks module origins. Otherwise an editable installation can silently load the live workspace despite a different working directory. Preliminary `initial-comparison` results encountered this problem and are **excluded from speedup claims**; they are retained with an exclusion note. The final comparison checks distinct source origins before timing.

## Full workflow measurements

Each result below includes a fresh CLI process, imports/startup, native evaluation, record preparation, encoding, hashing, all SQLite rows/tasks, FULL commits, queue drain and database close. Trials alternate control order. Both native arms use 16 native threads and batches of 4,096 under the unchanged Outpost-v3 policy.

| Arm | Inputs per trial | Median persisted inputs/sec | Trial range |
|---|---:|---:|---:|
| Preserved pre-change native source | 30,000 | **1,413.39** | 1,369.09–1,415.76 |
| Optimized native source | 30,000 | **2,466.15** | 2,404.59–2,475.02 |
| Optimized native, smaller comparison | 5,000 | **1,855.75** | 1,827.65–1,869.39 |
| Current Python control, 36 workers | 5,000 | **906.33** | 891.85–908.67 |

Native is **2.048×** the matching current Python control on the smaller cohort. Startup and drain affect smaller runs more, so the two cohort sizes must not be mixed into a speedup ratio. The previous report's 1,179.67/sec figure used a different cohort/run size; the fresh preserved-source result above is the valid before/after control.

The final cohort uses key **120290003000**, disjoint from the 10,000-input tuning cohort at **120280003000**. The 5,000-input Python comparison is a subset of the final cohort. Repetitions, scheduler probes and reused subsets do not add distinct search volume. No unbounded search ran.

Every 30,000-input trial saved **30,000 seed rows, 55,372 candidates, 60,000 discovery tasks and 55,372 V1 tasks**. No natural baseline survivor occurred; inventory-work rows are correctly zero for this workload. Positive/late-stage and inventory-task behavior therefore remains covered by fixtures and independent oracle tests, not inferred from the reject-heavy benchmark.

All six large-trial record fingerprints match:

`90ebd07af5b6d3d9b749b8a2f57b8cf62dc3c38f668ecd846276183516160aed`

Discovery, inventory and V1 task fingerprints, aggregate counters and contiguous complete coverage also match. The smaller native/Python comparison separately matches all records and task fingerprints. Existing exclusions remain limited to runtime/provenance measurement fields; no semantic exclusion was added. Template tests additionally compare entire candidate JSON bytes, provenance labels and stage timing maps.

Raw data: [final CLI comparison](runs/full-evidence-optimization-2026-10-12/final-comparison/results.json).

## Where time went

Service medians per 30,000 inputs, aggregated from the pipeline:

| Service | Before | After |
|---|---:|---:|
| Native batch evaluation | 0.855 s | 0.849 s |
| Record preparation | 5.496 s | 3.921 s |
| Encoding during range preparation | 6.914 s | 0.057 s |
| Hashing | 1.266 s | 1.248 s |
| Total range preparation | 8.786 s | 1.658 s |
| SQL service | 14.434 s | 6.762 s |
| Commit | 2.542 s | 2.512 s |
| Writer wall service | 17.065 s | 9.377 s |

These nested/overlapping timers must not be summed into elapsed time. Encoding work now includes template substitutions in record preparation; the 99% reduction in the separate encoding timer is not a 99% reduction in total serialization work. SQL service can include waiting for Python's GIL while the preparer runs; the SQL statements themselves did not change. The profile and scheduling probes distinguish this from pure disk time.

Native batch service alone corresponds to roughly **35,300 inputs/sec**, excluding persistence and startup. It is not the achieved workflow rate. Remaining costs include template/coordinate preparation, SHA-256 over full records, SQLite row/index maintenance, thread contention and durable I/O. The single writer still exceeds the six-second service budget for 30,000 inputs at the target rate.

## Resource cost and rejected alternatives

Maximum sampled process-tree RSS for the large comparison fell from **710,639,616 to 602,767,360 bytes**. Optimized SQLite files were **564,494,336–564,506,624 bytes per 30,000 inputs**; controls were 566,022,144–566,038,528 bytes. Small physical size differences include runtime metric text and page packing, not removed evidence. Peak sampled WAL was approximately 86 MB. Queues remain bounded at three outstanding batches, with a 256 MiB prepared-owned-byte budget and existing native allocation caps. Disk reserves and memory monitoring remain enabled.

The smaller native/Python comparison peaked at 317,698,048 versus 1,736,654,848 bytes of sampled process-tree RSS. Sampling is not an exact allocator peak and can include shared pages more than once.

- **Writer-thread preparation:** three-trial 10,000-input pipeline medians were 2,498.45/sec with existing threaded preparation versus 2,445.41/sec with preparation on the writer at batch 4,096. At batch 1,024 they were 2,396.86 versus 2,189.04/sec. The diagnostic option is retained internally; the production default is unchanged.
- **Spawned preparation:** bounded exploratory trials with one, two and three preparer processes measured 2,461.88, 2,188.50 and 2,297.32/sec respectively. Startup, owned-record IPC and scheduling costs did not justify adoption on this workload. These are probes, not broad claims about every workload size; the process experiment remains outside production.
- **Larger WAL checkpoints:** identical precomputed 10,000-input rows, three rotated trials, including database close, measured median writer time 1.791 seconds at 64 MiB versus 1.753 seconds at 256 MiB. The small 2.2% wall-time gain increased WAL from about 79 MB to 195 MB. A much larger apparent commit-only gain mostly moved work to close. The existing 64 MiB threshold was retained.

Evidence: [scheduler trials](runs/full-evidence-optimization-2026-10-12/scheduling/results.json), [process probes](runs/full-evidence-optimization-2026-10-12/process-probe.json), [checkpoint probes](runs/full-evidence-optimization-2026-10-12/checkpoint-probe.json). The initial writer-thread diagnostic's queue-wait timer included preparation; use its total wall, SQL and commit timings. That diagnostic accounting was corrected afterward.

## Accuracy, durability and adoption

**880 tests passed in 226.87 seconds.** Coverage includes exact locked/river/Outpost template bytes; negative and fractional Nether bounds; signed/full64 inputs; positive, early and late failures; all synthetic missing requirements; direct/replay/independent Python parity; capped versus full inventories; scores; full four-Y witnesses; coastal and river decisions; canonical Unicode/numeric/error behavior across threads; closed-buffer ownership; bounded-cache fallback; atomic rollback; stale leases; crash/retry/resume; inventory/discovery/V1 tables; ranking and exports.

Fresh serial **ASan covered 1,248 inputs with zero errors**, including profiling buffers and active policy flags. Leak detection is unavailable in this host's ASan runtime; this is not a race-detector result. C computation sources, the original generator binary and pinned OpenMP runtime were not changed by this pass.

The actual 30,000-input CLI run resumed with **zero new commits**. A retained synthetic export includes one predicted survivor and five pending/late-failure candidates, with complete record parity, exact idempotent retry and explicit synthetic labels. This is not evidence of a naturally discovered complete world.

**Adoption decision:** enable the exact locked template encoder in the existing explicit native full-evidence production executor. Keep the original builder/replay route, Python executor, compact mode, serial build, default threaded schedule, WAL/FULL durability and current checkpoint threshold. Native build/ABI did not change, so the previously verified Outpost-v3 batch extension remains usable. The Python source identity changed: start a fresh scan rather than resuming an incompatible older source identity.

This pass completed profiling, direct-encoding/persistence changes, scheduling comparisons, regression gates and actual-entry-point verification (M0–M5). Terrain/M6 computation was unchanged; this report makes no new terrain or BDS speed claim. Predictor parity is preserved, but does not establish actual Bedrock generation equivalence, full discovery recall or a time to find a complete playable world. Prediction-scale and large-search readiness gates remain enforced.

All profiles, retained controls, trials, exports and [final verification](runs/full-evidence-optimization-2026-10-12/final-verification.json) are under `runs/full-evidence-optimization-2026-10-12/`.
