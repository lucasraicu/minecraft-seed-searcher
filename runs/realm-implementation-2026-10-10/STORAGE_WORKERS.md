# Realm storage and worker implementation — 10 October 2026

Implemented parent-owned SQLite/WAL/FULL checkpointing and bounded spawn-based multiprocessing. This is prediction infrastructure, not certification of actual 26.52 generation or production-scale readiness.

## Coverage and persistence

The ledger stores unsigned full64 indices and half-open endpoints as zero-padded 20-character TEXT, including endpoint 18446744073709551616. Sequential enumeration maps each unsigned word to its signed decimal seed; permutation enumeration uses the existing bijection and stable run key. Each worker receives one nonoverlapping finite range. Distinct scanned coverage counts only atomically committed indices; dispatched/retried work does not inflate it. At most one outstanding batch per worker bounds job/result accumulation. Baseline results, all anchors (including PENDING/FAILED), counters, completed coverage, and independent V1/V2 pending tasks for nonfailed candidates commit in one transaction. Duplicate completion with identical results is idempotent; conflicting retry results fail. Parent memory holds at most the outstanding batches, and database reads use keyset pages.

An OS-released flock protects the scan invocation before lease recovery, refusing a second concurrent scanner while allowing read-only status access. On resume, outstanding leases become retries, completed ranges remain untouched, and changing workers/max_workers/batch_size is compatible. Semantic config hashing removes exactly those scheduling fields before recomputing config_sha256. Seed sequence, run key, other configuration, and provided code/backend identities remain checked. Callers supply the complete code/backend identity; the runner's fallback identity contains configuration, interval, and evaluator and is intended for isolated tests, not a production provenance seal.

Variant rows are unique by candidate, variant and center. Observations are unique by observation key. Both provide direct lookups and streaming iterators. Task state is pending until work begins, then started; callers explicitly mark complete after the variant's proposed-center work finishes. Incomplete budgets therefore remain visible.

## Workers and resource policy

Run_scan supports workers 1–36 within max_workers, spawned processes, numerical-library environment threads fixed to 1, exact newly committed stop_after limits, progress callbacks, graceful KeyboardInterrupt during dispatch waiting/progress, and failure checkpoints. A worker hard exit stops dispatch; other submitted results are drained where available. Failed/uncommitted leases stay retryable. Resuming never skips their indices. Worker wall/CPU time, actual getrusage worker peak RSS bytes, and evaluator stage seconds are aggregated. Process-tree RSS and CPU are sampled through ps; RSS sums can double-count shared pages. Memory reporting uses bytes with GiB=2^30 bytes. Above the 25 GiB target, dispatch pauses until outstanding work drains; crossing the 30 GiB combined ceiling stops new dispatch and retains the checkpoint. An 8 GiB Docker reserve applies when the BDS provider is configured, or an explicit docker_reserve_gib overrides it. This is conservative budget accounting, not a measurement of VM committed memory. Sampling can miss brief peaks and cannot enforce a hard OS allocation limit.

Counts beyond pilot_limit require explicit allow_prediction_scale and a persisted compatibility.json matching target 26.52/BDS 1.26.52.3/prediction model MC_26_50 with a features map. large_search_ready=false remains valid only for explicitly authorized prediction experiments; it never grants exact large-search certification. No large scan was run for this component.

## Verification and measurements

`.venv/bin/python -m pytest tests/test_realm_store.py tests/test_realm_workers.py -q` passes 11 tests (about 3.8 seconds). Coverage includes an injected SQLite trigger failure proving transaction rollback, multi-anchor persistence/task parity, identical retry idempotence, changed scheduling hash compatibility and changed sequence identity rejection, high unsigned indices/end2^64, retry splitting, keyset reads and upserts, deterministic output across 1/2/3 workers, numerical threads 1, a real spawned worker os._exit crash and successful resume without rescanning committed ranges, graceful callback interrupt, signed sequential endpoint enumeration, explicit scale gate, current process-tree RSS/CPU availability, an injected memory-ceiling event that retains a resumable empty checkpoint, and refusal/release of a concurrent scanner lock.

Earlier synthetic equivalent-table write measurement (2048 identical payloads): legacy per-seed FULL/WAL commits 0.2155 s; batch 32 commits 0.0274 s, a 7.87× transaction-only improvement; serialization 0.0090 s. This is a storage microbenchmark, not native scanner throughput or an end-to-end speedup. No 12–36 worker native scaling conclusion is supported by these tests.

Files owned by this component: src/seed_search/realm/store.py, runner.py, tests/test_realm_store.py, tests/test_realm_workers.py, and this report.

## Measured storage growth on saved 128-seed baseline pilot

Measured the full optimized worker results from baseline-ab.json, committing all 128 consecutive indices and all discovered anchors in batches of 32. Seeds now contain summaries with ordered anchor_ids; candidates contain each full anchor once. iter_results reconstructs the public full-result API through the indexed candidate.idx lookup. Range digests still cover the full original incoming worker results, so later rescore/evidence updates do not alter coverage retry identity. get_candidate and upsert_candidate permit saved evidence/score changes while enforcing immutable seed/Stronghold identity; changing qualification requires explicit allow_qualification_change=True.

```json
{
  "summary": {
    "committed_seeds": 128,
    "candidate_counts": {
      "PENDING": 129,
      "PREDICTED": 206
    },
    "seed_result_payload_bytes": 131950,
    "candidate_payload_bytes": 3860583,
    "live_sqlite_wal_shm_bytes": 9371592,
    "closed_sqlite_bytes": 4431872,
    "closed_bytes_per_seed": 34624.0,
    "batch_commit_seconds": 0.27167043497320265
  },
  "duplicated_anchors": {
    "committed_seeds": 128,
    "candidate_counts": {
      "PENDING": 129,
      "PREDICTED": 206
    },
    "seed_result_payload_bytes": 3981533,
    "candidate_payload_bytes": 3860583,
    "live_sqlite_wal_shm_bytes": 9371592,
    "closed_sqlite_bytes": 8343552,
    "closed_bytes_per_seed": 65184.0,
    "batch_commit_seconds": 0.2690479210577905
  }
}
```

The duplicated_anchors comparison uses the same ledger/index/task schema with full anchors also written into seed results, reproducing the prior payload duplication. Both measurements use real pilot observations, not synthetic identical payloads. Closed SQLite size includes allocated pages and indices; live sizes include WAL/SHM and vary with checkpoint timing. The comparison database was not vacuumed, so its extra rewrite allocation is included.

At the measured 34,624 closed bytes per seed, a straight-line payload/page projection is 3.22 GiB for 100,000 seeds, 32.25 GiB for 1 million, and 3224.6 GiB for 100 million, before terrain tiles, variant results, BDS evidence, exports, backups, and transient WAL. Anchor counts and large structure observations vary by seed; 128 seeds are insufficient for a production capacity guarantee. No 100,000-seed production scan was run.

## 10,000-input worker scaling — standalone measured run

Command: `.venv/bin/python -m seed_search --config config/realm.yaml benchmark --count 10000 --workers 12 16 18 24 30 36 --output runs/realm-implementation-2026-10-10/worker-scaling-10000`. Exit status 0. Log: worker-scaling-10000.log. Authoritative measurements/checkpoints: worker-scaling-10000/benchmark.json and its workers-* subdirectories. The prior full suite finished (193 passed in 110.01 seconds), and no pytest process was running when this benchmark began. No source edits were made by the benchmark agent.

All runs used the same indices [0,10000), configuration and native baseline workload, including spawn, prediction and checkpoint transactions; terrain and actual BDS execution are excluded. All requested worker processes contributed, including all 36 in the final run. Each run committed 10,000 distinct inputs; six repeats produced 60,000 evaluations but only 10,000 distinct full64 inputs. Prediction-qualified membership hashes and all stage counters match across all six worker counts. Each checkpoint retains 15,618 PREDICTED and 10,714 PENDING anchors (26,332 total), and both independent terrain tasks for every anchor.

| Workers | Wall seconds | Seeds/s | Peak scanner RSS GiB | RSS + reserved Docker GiB | Worker CPU seconds | Worker CPU / elapsed cores | Closed SQLite MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 71.18 | 140.49 | 1.290 | 9.290 | 730.29 | 10.26 | 322.39 |
| 16 | 61.98 | 161.35 | 1.652 | 9.652 | 781.52 | 12.61 | 322.38 |
| 18 | 57.73 | 173.22 | 1.846 | 9.846 | 784.73 | 13.59 | 322.41 |
| 24 | 54.80 | 182.48 | 2.294 | 10.294 | 825.31 | 15.06 | 322.39 |
| 30 | 53.14 | 188.20 | 2.721 | 10.721 | 841.74 | 15.84 | 322.39 |
| 36 | 53.27 | 187.71 | 3.150 | 11.150 | 874.98 | 16.42 | 322.36 |

RSS is a sampled parent-plus-descendant sum and may double-count shared pages or miss short peaks. The 8 GiB Docker amount is reserved budget, not measured active BDS memory. Worker CPU seconds are measured process CPU time summed over batches; the effective core column excludes the parent writer and setup. None crossed the 25 GiB working target or 30 GiB combined ceiling. CPU time rises with worker count while throughput gains flatten, consistent with shared physical cores and parent serialization/checkpoint overhead; this experiment does not isolate their individual contributions.

30 workers was fastest in this one measurement at 188.20 seeds/s, versus 187.71 at 36 (0.26% difference, too small for a significance claim). The gain from 24 to 30 was 3.13%; 36 consumed approximately 0.43 GiB more peak scanner memory than 30 without a measured throughput gain. Use 30 for the next explicitly authorized 100,000-input feasibility check, keeping 24 as a reasonable lower-concurrency option. This is a baseline-only choice; concurrent BDS/terrain workloads need separate measurements. These are one ordered trial per setting, not randomized repeated confidence estimates or comparison against historical full terrain searches.

Closed databases average approximately 33,805 bytes per seed (about 3.15 GiB projected for 100,000 and 31.5 GiB for one million), excluding terrain, BDS evidence, exports, backups and transient WAL. At the best observed throughput, 100,000 baseline inputs project to approximately 8.9 minutes; storage growth and memory lifetime must be checked on that longer run before a larger workload. No 100,000-input run was launched by this component.

During this benchmark, root/terrain agents changed only realm CLI, terrain and capabilities identity-scoping code. The benchmark parent had imported the previous broad identity function before launch; all six checkpoints therefore have 18 broad hash entries, with metadata differences in terrain.py, cli.py and capabilities.py between early and later settings. The baseline computational files (backend/seeds/native and realm baseline/bounds/biomes/config/runner/store) remained unchanged. Qualified-pool hash and all counters matched. These non-baseline metadata differences are preserved and disclosed; no checkpoint identity was rewritten. Future launches use the narrowed baseline computation identity.

## Post-100,000 scale diagnosis and approved minimal fixes

The original standalone 100,000-input run completed in 972.144 seconds (102.865 seeds/s), retained 153,394 PREDICTED and 109,681 PENDING anchors, used 3,346,128,896 closed SQLite bytes, and peaked at 4.152 GiB sampled scanner RSS. Its later throughput intervals dropped substantially below its initial ~205 seeds/s. This is measured baseline prediction, not actual generation. The authorized next step is a clean equivalent 100,000-input repeat after fixes and other CPU work finish; no end-to-end speedup is claimed here.

Sequencing disclosure: an initial study command printed the still-running parent PID but continued before explicitly verifying process exit. The SQLite ledger already had every range complete and all native workers had finished; the parent was finalizing its qualified-pool hash. The initial status/postprocessing study briefly competed with this finalization. Both studies were rerun after pgrep verified process exit, and all metrics below come from that clean rerun. This overlap adds uncertainty to post-scan finalization observations and is preserved rather than hidden. No source changed until the 100,000-input process exited.

### Progress query cost

The runner previously constructed full status after every committed 32-seed batch; CLI throttling only suppressed printing after those queries were already performed. At the final checkpoint, five read-only timings gave mean query costs:

| Query | Mean seconds | Plan |
|---|---:|---|
| range_counts | 0.000335 | SCAN ranges USING COVERING INDEX ranges_status |
| candidate_counts | 0.023354 | SCAN candidates USING COVERING INDEX candidate_status |
| variant_task_counts | 0.332659 | SCAN variant_tasks; USE TEMP B-TREE FOR GROUP BY |

Progress construction now occurs on the first commit and then at most once per 10 seconds, before invoking status queries. Explicit progress_interval_seconds=0 retains per-batch callbacks. The returned final status remains complete, and first-callback cancellation is preserved. A deterministic local-clock test checks seven commits produce only one progress aggregation plus the final returned status, while interval=0 produces all seven callbacks and identical results.

A covering index variant_task_status(variant,status) removes the temporary GROUP BY B-tree. On the same completed 526,150-row task ledger its mean query time was 0.052711 seconds, versus 0.332659 before indexing (6.31x query-only improvement). Index creation/open took 0.357 seconds and added 10,002,432 SQLite bytes. Completed coverage and both task counts remained unchanged. The original database size in benchmark.json is preserved as historical measurement; the existing checkpoint now includes this additive index. Full query/index evidence is in checkpoint-status-study.json and checkpoint-status-index-study.json.

### Biome postprocessing cost and parity

The clean study regenerated exactly two saved 1,764-point observations with the unchanged native provider and compared complete classifier/raw_detections output to both original processing and the saved pilot. Each comparison passed, including raw_names, canonical aliases, scores, counts, and first sample coordinate per raw ID.

| Unique IDs | Old biome_name calls | New calls | Old microseconds/anchor | Proposed microseconds/anchor | Postprocess-only gain | Old traced peak bytes | New traced peak bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 31 | 1764 | 31 | 5913.0 | 164.5 | 35.94x | 124178 | 33040 |
| 36 | 1764 | 36 | 6692.1 | 178.2 | 37.56x | 120681 | 33160 |

The implementation reuses each native ID array, concatenating only when multiple bounded query batches exist. np.unique(return_index=True,return_counts=True) supplies sorted raw IDs, exact counts, and first observation positions in one operation; it replaces 62/72 repeated array reconstructions in the measured samples. classify_ids resolves only unique IDs before canonical classification. The microbenchmark gain is not a native scanner or end-to-end claim. Focused tests compare all exposed IDs and repeats in reversed order, unknown IDs, aliases, first coordinates, empty observations, length validation, and unique name-lookup calls. Study script and detailed metrics: biome_postprocess_study.py and biome-postprocess-study.json.

Changed computational sources: realm/runner.py, store.py, baseline.py, biomes.py. Added/focused tests: test_realm_workers.py, test_realm_store.py, test_realm_biome_postprocessing.py. Historical run identities remain historical; new runs use the updated code identity. Finite measured 100,000-input shards remain the practical guidance until fresh scaling demonstrates otherwise; million/billion-input throughput remains unproven.

## Memory and worker-output safeguards follow-up

Focused authorized changes affect realm/config.py, realm/runner.py and new tests/test_realm_memory_policy.py. Shared validation now rejects nonfinite/bool/nonnumeric target, ceiling or Docker reserve; target must be positive, at most ceiling, and ceiling at most 30 GiB; reserve must be nonnegative and below ceiling. Runner validation occurs before creating or mutating a checkpoint. Zero reserve remains allowed when explicitly configured.

Unavailable process-tree monitoring now stops new dispatch. Already submitted batches are drained and valid results committed, the monitor error is persisted in worker statistics/memory, and the invocation raises a clear error after final checkpointing. It does not silently resume dispatch if a later sample recovers; a deliberate resume with working monitoring continues unassigned/retryable work. The actual memory limit remains sampled budget accounting rather than an OS allocation cap.

Parent validation now compares every returned worker seed with _seed(index, search) before complete_range. A mismatched seed fails the batch without committing seed/candidate/coverage data and leaves its range retryable; direct RealmStore synthetic fixtures are unchanged.

Verification: `.venv/bin/python -m pytest tests/test_realm_memory_policy.py tests/test_realm_workers.py tests/test_realm_baseline.py -q` passes 33 tests (about 6 seconds). New tests use deterministic completed futures and mocked monitors, without generation or benchmarks. They cover invalid settings through both configuration and direct runner paths, failure before dispatch, monitoring loss while batches remain in flight, draining those batches without refill, persistent diagnostic/resume, valid zero reserve, and wrong-seed rejection/retry. Existing spawned synthetic worker/crash/cancellation tests continue to pass.

Broader safeguards still outstanding: KeyboardInterrupt at arbitrary sampling/lease/SQLite/statistics instructions is not covered by the existing graceful handler, and parent process death at every transaction/acknowledgment boundary has not been injected. No scoring, storage schema, export, terrain/raster or verification source changed in this follow-up. No seed or BDS benchmark was run.
