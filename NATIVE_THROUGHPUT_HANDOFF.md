# New-chat task: substantially improve persisted seed-search throughput

Copy the task below into a new chat opened in this repository.

---

Implement [NATIVE_THROUGHPUT_IMPLEMENTATION_PLAN.md](NATIVE_THROUGHPUT_IMPLEMENTATION_PLAN.md) in `/Users/lucasraicu/Downloads/minecraft-seed-searcher`. I want a substantial improvement in **complete, durably persisted input seeds per second**. Proceed with implementation, tests and measured comparisons; do not stop at another plan.

Aim for **5,000 persisted seeds/sec**, with **10,000/sec** as a stretch target on the current host. These are targets, not promised results. Preserve the complete blueprint and evidence contract. Adopt the native production path only after the plan's parity, durability, resource and full-workflow performance gates pass.

## Read first

1. Applicable `AGENTS.md` instructions and `NATIVE_THROUGHPUT_IMPLEMENTATION_PLAN.md`.
2. `NATIVE_BASELINE_PROTOTYPE_RESULTS.md`, `BLUEPRINT_BENCHMARK_RESULTS.md`, `ENGINE_AUDIT_RESULTS.md` and `BLUEPRINT_FEASIBILITY_ANALYSIS.md`.
3. `MASTER_SEED_BLUEPRINT.md`, active blueprint configuration and tests. Use the feasibility report to distinguish desired requirements from unverified probability/geometry claims in the authored blueprint.
4. `scripts/blueprint_batch_prototype.py`, `native/blueprint_batch.h`, `native/blueprint_batch.inc`, `scripts/benchmark_native_blueprint.py`, `src/seed_search/realm/blueprint.py`, `src/seed_search/realm/store.py` and `tests/test_blueprint_batch_prototype.py`.

## Current state

- The complete applicable baseline computation already runs in an isolated C/OpenMP prototype, with independent generator state per thread. Reuse it.
- Native-only rate: **19,835.874 inputs/sec**, 36 threads, batch 4,096.
- Existing complete persisted rate: **1,174.968/sec**, 30 Python workers.
- Prototype complete persisted rate: **948.426/sec**, batch 256. It is **19.28% slower**, so production still uses the existing evaluator.
- Per 30,000 inputs, prototype service medians total approximately 3.494 seconds native work, 9.850 seconds Python record reconstruction and 17.517 seconds range preparation/serialization/persistence. They are separately aggregated timings; the last number is not disk time alone.
- `Batch.records()` currently invokes the Python evaluator against a `ReplayProvider` containing C results. It performs no new generation, but repeats Python control flow and builds many objects.
- `RealmStore.complete_range()` already has transactional bulk seed/candidate inserts, canonical serialization and retry digests. Profile remaining preparation, inventory/task inserts, hashing and commits before changing it.
- Original evidence: `runs/native-blueprint-prototype-2026-10-12/`. The previous suite passed **781 tests**; ASan covered **576 serial inputs**. Rerun appropriate verification after changes.
- Benchmark evidence contains **30,000 distinct inputs**, repeated three times per implementation, and **zero natural complete baseline survivors**. Positive and late-stage fixtures remain essential.
- The roughly 48× historical Mineshaft figure was first-witness early stopping versus full enumeration. It is not a whole-search speedup.

## Execute in this order

1. Inventory the dirty working tree and preserve all existing modified/untracked work. Record current source/runtime identities. Establish a profile splitting C work, extraction, direct record preparation, encoding, hashing, SQL, commit and queue costs.
2. Replace replay-based record construction on the fast path with direct equivalent records from native results. Keep replay and the existing Python evaluator as oracles. Use native serialization only if it is needed to meet the measured record budget.
3. Prepare/serialize each durable row once, batch remaining inventory/task work, and shorten the single SQLite writer's critical path while preserving validation, atomic coverage, FULL durability and exact retry semantics.
4. Overlap native computation, record preparation and saving with bounded owned buffers/queues, backpressure, explicit CPU budgets, failure propagation and recoverable leases. Tune batch size and native threads for persisted throughput. Overlap alone leaves the current writer around 1,700 inputs/sec; reduce its service cost too.
5. Validate complete semantic records and durable task tables, boundaries/positives/late failures, concurrency/ownership, crash/retry/resume, exports and portable builds. Run fresh counterbalanced persisted benchmarks against the best current Python path and preserve the original control for attributing shared-store gains.
6. Promote only after the plan's adoption gate, then validate the actual production entry point. If the target remains unmet, report the remaining bottleneck and continue measured improvements; never declare a native-only number to be persisted throughput.
7. Profile V1 Coastal Continent afterward. Move additional terrain work into C only when its measured cost and full raster/decision parity justify it. Report terrain and baseline rates separately.

## Constraints

- Preserve all blueprint counts, exact bounds, full64 viability, four-Y/thirteen-predicate biome evaluation, scores, witnesses, full inventories and uncertainty labels. Keep V2 outside the active pipeline.
- Keep every processed input, discovered anchor, pending candidate, discovery/inventory/V1 task and coverage record. Do not save only winners, weaken tests, disable durability or broaden parity exclusions to manufacture a gain.
- Keep original benchmark baselines, runtime dependencies, core framework, fixtures and active configs. Do not reset/clean the workspace or overwrite retained runs. This prototype and related work are currently uncommitted/untracked in places; a clean checkout alone will omit them.
- Keep supported builds and a compatible existing/serial route. The pinned macOS OpenMP runtime previously lacked `__kmpc_dispatch_deinit`; the prototype uses atomic chunk claiming. Do not reintroduce that ABI failure without a validated toolchain change.
- Use bounded benchmark volumes and calculate disk needs first. Existing `persist_scan` allows up to 100,000 inputs per call and native batches up to 16,384. Current benchmark `--count` is per cohort, across three cohorts. Do not accidentally call repeated inputs distinct search volume or launch an unlimited search.
- Preserve prediction-scale and large-search readiness gates. Faster prediction does not certify actual Bedrock playability or establish the time to find a complete world.

## Completion and communication

Track milestones M0–M6 from the plan. After profiling, give an engineering ETA and update it as each milestone completes. Provide frequent concise progress updates with measured findings and the next verification. Distinguish implementation ETA from benchmark duration and unknown world-discovery time.

Deliver working code, appropriate tests, retained raw measurements, `NATIVE_THROUGHPUT_RESULTS.md`, updated usage documentation, and an explicit adoption decision. Show native-only and full persisted rates, speedup against a fresh comparable control, variability, memory/disk cost and remaining limits. A modest adoption win does not mean the 5,000/sec target was achieved.

When the task and all required verification are fully complete, run this as the final shell command, substituting an accurate summary:

```sh
python3 /Users/lucasraicu/codex_done.py "CODEX TASK COMPLETE
minecraft-seed-searcher
<one-sentence summary of the completed work and measured outcome>"
```

Do not send the completion notification while work or required verification remains unfinished.
