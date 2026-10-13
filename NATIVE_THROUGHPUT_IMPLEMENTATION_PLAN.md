# Native baseline throughput implementation plan

Written 2026-10-12. Status: **planned; optimization work in this document has not started**.

The objective is a substantial increase in **durably persisted input seeds per second**, with the same blueprint requirements, complete evidence, and restart behavior. The primary target is **5,000 persisted seeds/sec** on the measured Intel Xeon W-2191B host; **10,000/sec** is a stretch target. These are engineering targets, not measured results or promises.

The next-chat execution prompt is [NATIVE_THROUGHPUT_HANDOFF.md](NATIVE_THROUGHPUT_HANDOFF.md). The measured starting point is [NATIVE_BASELINE_PROTOTYPE_RESULTS.md](NATIVE_BASELINE_PROTOTYPE_RESULTS.md). This plan supersedes only the next throughput work; it does not replace the blueprint or historical implementation reports.

## 1. Starting evidence and limits

| Workflow | Measured input seeds/sec | Meaning |
|---|---:|---|
| Existing production baseline, 30 Python processes | 1,174.968 | Complete persisted workflow |
| Isolated C baseline, 36 OpenMP threads | 19,835.874 | Native calls only, batch 4,096 |
| Isolated C baseline plus current Python adapter | 948.426 | Complete persisted workflow, batch 256 |

The prototype is 19.28% slower end to end and remains experimental. It already implements complete applicable baseline computation in C, with separate generator state per OpenMP thread. Python currently rebuilds evidence by replaying the existing evaluator against C results, then commits it through `RealmStore`.

The measurements used 30,000 distinct inputs / 55,853 anchors, with three repetitions per implementation. Repetitions do not increase distinct search volume. No natural complete baseline survivor was found; downstream fixture coverage must accompany throughput measurements. The prior suite passed 781 tests and the serial ASan exercise covered 576 inputs. Those results establish the starting point, not validation of future changes.

| Prototype service, summed cohort medians for 30,000 inputs | Time | Approximate isolated capacity |
|---|---:|---:|
| Native batches | 3.494 s | 8,588 inputs/sec |
| Python record reconstruction | 9.850 s | 3,046 inputs/sec |
| Range preparation, serialization and persistence | 17.517 s | 1,713 inputs/sec |

These are separately aggregated medians, not an exact additive wall-time decomposition. The persistence timer includes Python preparation and SQL, so it does not establish that disk I/O alone is limiting. Even ideal overlap at these service rates would remain around 1,700 inputs/sec before contention and other overhead. Both record construction and persistence need improvement.

At 5,000 inputs/sec, each independently pipelined stage must service 30,000 inputs in at most six seconds on average; at 10,000/sec, three seconds. Shared CPU and memory contention require additional headroom. The 19,836 native-only rate is one batch/workload measurement, not a universal ceiling or an achievable persisted rate by itself.

## 2. Contract and preservation requirements

Keep the active `master_seed_blueprint_v1` baseline and V1 Coastal Continent contract. Preserve exact Overworld/Nether bounds, full64 seed handling, all required counts, exact Dark Forest Mansion eligibility, all thirteen biome predicates and four Y levels, sample order/first witnesses, scores, inventories, and uncertainty labels. V2 remains outside the active pipeline. Do not change these requirements to improve throughput.

Preserve every processed seed, every discovered anchor, pending candidates, discovery tasks, inventory work, V1 tasks, counters, and public reconstructed records. Keep atomic coverage/results commits, range leases, retry identity, canonical signed seed strings, source/configuration identities and resume compatibility checks. A failed or uncommitted range must never count as completed.

Retain WAL and `synchronous=FULL`. Preserve the current schema initially. A later storage-format or digest change requires explicit versioning, migration/compatibility tests and an equivalent fully persisted benchmark; it is not the first optimization. Retain existing prediction-scale/readiness gates and separate actual Bedrock verification from predictor throughput.

The working tree contains substantial modified and untracked prior work, including the prototype. Inventory and preserve it before editing. Do not reset, clean, delete benchmark baselines, or switch to a clean checkout that omits the current implementation. Protect `native/`, `seed_search/`, `src/seed_search/`, `config/`, `tests/`, `fixtures/`, runtime dependencies and evidence artifacts.

## 3. Implementation map

| Existing code | Work to perform |
|---|---|
| `scripts/blueprint_batch_prototype.py`: `Batch.records`, `ReplayProvider`, `persist_scan` | Instrument separately; replace evaluator replay on the fast path; retain replay as a parity oracle; add bounded overlap |
| `native/blueprint_batch.h`, `native/blueprint_batch.inc` | Extend owned result buffers or native encoding only where measurements justify it; preserve per-thread generators and explicit freeing |
| `src/seed_search/realm/blueprint.py` | Reference semantics for direct record construction; avoid changing eligibility or ranking |
| `src/seed_search/realm/store.py`: `complete_range`, `_ensure_inventory_locked` | Split preparation from transactional writes; serialize once; batch remaining per-candidate work |
| `scripts/benchmark_native_blueprint.py` | Add service timings, variant comparisons, durable table checks and held-out validation |
| `tests/test_blueprint_batch_prototype.py` and existing store/runner tests | Extend parity, ownership, concurrency, failure and resume coverage |
| `src/seed_search/realm/runner.py`, `cli.py`, `capabilities.py`, `native/build.py` | Integrate a tested execution option only after the adoption gate |
| `src/seed_search/realm/coastal.py`, `terrain.py`, `raster.py`, `src/seed_search/cache.py`, `native/bridge.c` | Profile V1 after baseline optimization; move only measured hot work |

## 4. Milestones

### M0 — Establish a precise cost breakdown

1. Record source diff, extension/runtime hashes, policy, compiler, CPU, Python version, durability settings and benchmark identities. Preserve the original oracle and pre-change production control. Record available memory and disk space.
2. Add separate timers/counters for seed preparation, C execution, CFFI extraction, record assembly, canonical JSON, hashing, row/task preparation, SQL execution, transaction commit, queue wait and shutdown. Report wall time and CPU time where useful; nested timers must not be summed as independent costs.
3. Profile bounded runs and use precomputed representative outputs for isolated record/store microbenchmarks. Include common early failures plus explicit positive and late-failure fixtures. Attribute profile overhead separately from unprofiled timings.
4. Measure rows and bytes per input, commit count, WAL/checkpoint behavior, queue occupancy and process-tree RSS. Inspect actual query/serialization call counts before selecting optimizations.

**Gate:** a saved profile identifies the dominant functions and a specific candidate change. Do not label the entire 17.517 seconds as disk latency without evidence.

### M1 — Build records directly from native results

1. Add a direct record builder for `NBResult` / `NBAnchor`. It must construct the existing evidence schema without invoking `evaluate_seed` or building the replay provider's query maps on the fast path.
2. Hoist immutable configuration/catalog mappings out of per-seed and per-anchor loops. Reuse already available bounds, IDs, counts and witnesses without recomputing generation or duplicating object conversions.
3. Preserve distinctions between unevaluated observations, floor witnesses and full inventories. Preserve pending reasons, score caps, ordering, sample counts, overlap/cache semantics and public identity fields.
4. Compare direct output against both the current replay adapter and the independent production evaluator. Keep replay selectable for diagnostics and tests.
5. If direct Python assembly still exceeds its service budget, prototype native emission of owned serialized rows/bytes. Avoid generating JSON in C only to parse it back into dictionaries and serialize it again. Native encoding must preserve UTF-8 escaping, integer precision, signed seeds, numeric conventions, canonicalization/digest rules, allocation errors and buffer lifetime.

**Gate:** complete semantic parity and a measured reduction in record cost. Prefer the simplest implementation meeting the budget; a complete Python rewrite is not a milestone.

### M2 — Prepare records once and shorten the writer's work

`complete_range` already uses `executemany` for seed and candidate inserts and serializes their rows. Merely adding those techniques again will not solve the bottleneck. `_ensure_inventory_locked` still constructs identities and performs individual inventory-work inserts; measure that work along with JSON, digests and transaction overhead.

1. Extract a validated prepared-batch representation containing seed rows, candidate rows, inventory rows, discovery/variant task rows, counts and range digest. The existing dictionary API should use the same preparation logic so the two paths cannot drift.
2. Serialize immutable evidence and identity fragments once per necessary scope. Batch inventory work using equivalent conflict behavior and validation. Avoid repeated JSON encode/decode cycles and unnecessary full-record traversals.
3. Keep all affected rows, coverage, counters and range completion in one transaction. Validate ownership, identities, completeness and retry semantics before committing. Prepared/native payloads must not bypass checks simply because they came from C.
4. Tune range/transaction size with FULL durability retained. Test 256, 1,024 and 4,096 inputs first; expand only where the profile supports it. Record throughput, commit latency, retry cost, memory and WAL growth.
5. If record generation happens in a different stage, hand the writer prepared owned data so expensive Python preparation does not remain in its critical path. Keep the SQLite connection owned by one writer.

**Gate:** old and prepared APIs produce equivalent durable state, reject malformed/conflicting retries and survive interruption. Saving only winners, disabling durability, deleting pending work or dropping indexes needed by consumers is not an acceptable speedup.

### M3 — Overlap bounded stages

The target pipeline is:

```text
Leased input ranges → C/OpenMP batches → direct/prepared records → one SQLite writer
                         bounded owned queues and backpressure
```

1. Start with two in-flight batches and a single native producer, overlapping its C call with record preparation/writing. CFFI currently releases the GIL around native calls; validate actual overlap rather than assuming two Python CPU stages run concurrently.
2. Assign explicit ownership to native buffers and prepared batches. Never queue borrowed C pointers after `nb_free`; retain the owning batch until its last consumer finishes. Bound queues by bytes as well as item count, including positive/late-stage outputs.
3. Keep DB claims and writes on the connection-owning thread/process. Track range IDs through each stage. Handle ordered or out-of-order completion without skipping uncommitted ranges, double-counting or accumulating an unbounded reorder buffer.
4. Use a small record-worker process pool or native record encoding only if profiling shows Python assembly still serializes the pipeline. Measure serialization/IPC costs before adopting another process layer. Avoid fork-based sharing of initialized OpenMP state.
5. Tune total compute budget across OpenMP, record workers and writer. Compare native thread counts such as 16, 18, 30 and 36; reserve CPU capacity where it helps persisted throughput. Prevent numerical-library threads from multiplying the budget.
6. Add bounded shutdown, cancellation, error propagation and lease recovery. Benchmark batch-size/context-setup costs; reuse worker contexts across calls only if that remaining overhead is material and lifetime/state-isolation tests pass.

**Gate:** demonstrated overlap, bounded memory, deterministic evidence, reliable resume and improved persisted throughput. Report speedup from each change separately; do not multiply unrelated microbenchmark ratios.

### M4 — Full correctness and performance gate

Correctness coverage must include:

- Real signed-64 extremes, high-bit siblings, repeated seeds, negative bounds and exact fractional Nether bounds.
- Synthetic complete positives, each count/biome failure, wrong-Y witnesses, Pale Garden decoys, multiple anchors, full inventories and bonus caps.
- Serial/parallel and direct/replay/production parity, including records beyond early-exit paths. Synthetic cases establish behavior, not natural-world yield.
- Queue saturation, reordered completion, native errors, invalid payloads, cancellation and buffer ownership. Repeat ASan when native allocation/encoding changes; do not describe serial ASan as a race test.
- Failure before commit, during the transaction, and after commit before acknowledgement. Verify rollback, recovery, exact completed coverage and idempotent retry; reject changed retry payloads.
- Readback/export/scoring compatibility plus semantic contents of discovery, inventory and V1 task tables, not only seed/anchor fingerprints. Range partition and attempt metadata may differ with scheduling; coverage and work semantics must match.

Retain the current explicit exclusions for implementation-specific timing/resource/prototype metadata. Do not widen exclusions to hide evidence differences. Keep same-path retry digests exact; cross-path semantic comparisons and retry-byte identity are different checks.

Benchmark protocol:

1. Use the same three disjoint 10,000-input cohorts and keys `120260001000`, `120261001000`, `120262001000`. Run three sequential repetitions per arm, alternating arm order, with fresh databases and identical eligibility/evidence/durability. Keep builds, tests and competing CPU jobs out of timed trials.
2. Preserve a pre-change production control if shared store changes also improve production. Compare the new native pipeline against both the original control and the best current Python path; attribute common writer gains separately.
3. Report native-only, records-only, writer-only and full persisted throughput. The adoption metric includes process/queue startup, preparation, commits, final drain and close. Post-run diagnostic comparisons can be outside the timer for both arms.
4. Show aggregate and per-cohort paired ratios, repeat variability, p50/p95 batch latency, CPU use, peak RSS, rows/bytes, WAL/checkpoint costs and exact identities. Select settings on tuning cohorts; confirm on one additional held-out 100,000-input cohort per arm, repeated three times. Extend the harness explicitly for that cohort; current `--count` applies to each of its three cohorts.
5. Budget storage before long validation. The prior output was roughly 430–450 MB per 30,000 inputs, excluding longer-run growth effects. Enforce bounded runs and existing disk reserves, preserve original evidence, and report any smaller validation scope honestly. No automatic million-seed run is required.

**Adoption gate:** zero unexplained semantic mismatches; all relevant regression/failure tests pass; at least **1.20×** full persisted throughput versus a fresh best production control, with every cohort faster and a gain larger than repeat noise; held-out validation also passes; memory/disk stay within configured budgets. A 20% win may justify adoption, but **5,000/sec remains the substantial-improvement target**. If the target is missed, quantify the remaining bottleneck instead of reporting the target as achieved.

### M5 — Integrate the winning path

After M4 passes, package the extension through supported builds and add an explicit native execution option with a tested legacy/serial path. Validate CLI dispatch, capabilities/computation identity, configuration, fresh runs, exports and checkpoint compatibility. Do not silently resume an incompatible checkpoint or switch implementations after a native failure.

Run the final integrated suite and a production-entry-point persisted benchmark. A promotion decision uses this measurement, not only the experimental script. Keep a documented rollback route; select the native default only for validated compatible configurations/hosts. Preserve large-search readiness gates and report unsupported profiles explicitly.

### M6 — Profile V1 Coastal Continent after baseline work

1. Measure V1 service costs across representative coastal candidates, borderline cases and controlled fixtures. If no naturally passing baseline seed is available, use labeled standalone controls and state that limitation.
2. Separate native density/biome calls, exact cache/raster reuse, Python array/object work, connected-component/coast geometry, serialization and terrain persistence. Existing exact caches and the refinement ladder already exist; assess them before proposing duplication.
3. Move only measured dominant work into C. Potential candidates include classification/connectivity or batched native-to-raster transfer; their priority depends on the profile.
4. Preserve every raw observation, raster alignment, coastal threshold, decision, unresolved status and model limitation. Compare full raster/decision outputs and complete persisted terrain work before adoption.
5. Report terrain candidates/sec and latency independently of baseline input seeds/sec. A mixed-workload estimate requires measured arrival/selectivity and shared-resource scheduling. The current zero-survivor cohort cannot establish a time to a qualifying playable world.

## 5. Reporting, milestones and completion

Keep the following outputs:

- `NATIVE_THROUGHPUT_RESULTS.md`: implemented changes, per-change effects, parity, persisted rates, resource use, adoption decision and remaining limits.
- A fresh `runs/native-throughput-<date>/` directory: identities, profile receipts, raw trial JSON, correctness/crash-test logs and benchmark manifests. Do not overwrite the original prototype evidence.
- README instructions for the resulting execution option and measured scope, once implementation is complete.

Track M0 through M6 as pending/in progress/verified/deferred. Give an initial engineering ETA after M0 identifies the work; update it after each milestone using elapsed work and remaining gates. Send concise progress updates during execution, with findings and the next check. Separate implementation ETA, finite benchmark ETA and unknown world-discovery ETA.

The next chat should proceed through implementation and verification, rather than stop after another plan. If an experiment loses, retain its evidence and pursue the next measured bottleneck. If the adoption gate remains unmet after the planned experiments, preserve production, publish the measured limit and state that the throughput target was not achieved. Terrain profiling can still proceed, but terrain integration must not disguise a failed baseline comparison.

This document-writing task does not implement or benchmark these proposed changes. At completion of the future implementation task, follow the user's completion-notification instruction only after all required verification finishes.
