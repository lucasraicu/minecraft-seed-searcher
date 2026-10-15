# Gemini native-pipeline review

12 October 2026. Compared the working sources with the retained, verified 238-file snapshot in `runs/river-highway-2026-10-12/final-source/`. Preserved the dirty tree and original runs. The supplied working-tree changes comprise **two source changes**: atomic work claims increased from 16 to 64, and a process-resource fallback added to `runner.py`. No new filter-order, sparse-biome or mandatory two-Outpost implementation was present. This report reviews those changes; it does not certify completion of the earlier, broader blueprint-update request.

## Corrections

**Restore 16-input work claims.** The 64-input proposal reduces claim frequency, but throughput fell on this workload. Default C/package/private builds now use 16. Private builds expose `--work-chunk {16,64,128}` and record the choice in flags and build identity, allowing future measured experiments without changing policy or ABI. Atomic claiming remains compatible with the pinned OpenMP runtime; no dispatch-deinit dependency was introduced. Independent per-thread generator state and owned buffers remain intact.

**Remove the misleading memory fallback.** `getrusage(RUSAGE_SELF).ru_maxrss` is the current process's historical peak, not live RSS of an arbitrary requested parent and its descendants. Labeling it as a successful tree sample, with CPU zero, bypassed the existing memory-monitoring failure gate. Failed `ps` sampling again reports unavailable, stops new dispatch, and preserves the checkpoint. A requested root absent from the snapshot now also reports unavailable rather than a successful zero-byte tree. Tests cover subprocess errors/timeouts, missing roots and multi-generation descendants.

**Fix compact river-candidate persistence.** The native adapter correctly labels active river-v2 candidates with 23 core requirements, but SQLite preparation accepted 23 only for locked-v1 and incorrectly demanded 25 for river-v2. Natural compact benchmarks with no retained rows had not exercised that branch. Preparation now uses the shared locked-policy predicate, preserving historical 25-requirement behavior. A new positive/near-miss regression saves two retained fixtures from three inputs, checks FULL synchronization, rejects an incorrect requirement total, tests exact retry and resumes with no remaining work. No counts or evidence constraints were relaxed.

## Fresh same-policy measurements

Three rotated trials per variant; **50,000 distinct inputs**, key `120267002000`. Repetitions are not additional distinct volume. Full evidence uses a contained 5,000-input subset. Native-only and compact CLI use 32 threads; full CLI uses 16. Batches contain at most 4096 inputs. All variants use `locked-2048-1024-river-v2`, Bastion ≥3, the existing structure order, exact four-Y/13-family biome evaluation, and the same SQLite implementation. CLI wall time includes startup, draining, FULL transactions and process exit. Terrain and BDS are excluded.

| Scope | Chunk 16 median (range), inputs/sec | Chunk 64 median (range) | Chunk 128 median (range) |
|---|---:|---:|---:|
| Native C only | 14,928.98 (14,920.60–15,003.92) | 13,278.63 (13,214.84–13,383.07) | 13,090.09 (13,031.18–13,145.31) |
| Compact checkpointed CLI, one miss | **11,899.48 (11,886.16–11,926.76)** | 10,691.77 (10,663.97–10,714.96) | 10,575.65 (10,547.42–10,589.69) |
| Complete full-evidence persisted CLI | **1,223.50 (1,207.76–1,224.63)** | 1,213.47 (1,198.06–1,214.76) | 1,224.75 (1,221.09–1,226.86) |

Restoring 16 improves compact throughput **11.30% against Gemini's 64** and C-only throughput **12.43%**. Full persistence changes little: 128's median gain over 16 is 0.10%, within the observed variability. Larger chunks leave less flexibility to balance uneven work; these measurements establish a regression, not a contention diagnosis or proof of its precise cause. Keep 16 as the shared default rather than adopting an unproven universal chunk increase.

Zero natural retained candidates were found; compact accepted-row cost is covered by positive/near-miss fixtures, not inferred from an empty leaderboard. The full cohort retained all 5,000 inputs, 9,290 anchor candidates, 10,000 discovery tasks and 9,290 V1 tasks. Record and durable-task fingerprints match across chunks and repetitions. Native decision receipts match across chunk variants. Separate complete parallel fixture sweeps compare 192 inputs per variant, including positives, signed/shifted bounds and late biome failures, with zero semantic differences.

The 16-chunk compact database is 212,992 bytes, versus 95,195,136 bytes for full evidence. Maximum sampled process-tree RSS was 147,828,736 bytes compact and 450,060,288 bytes full; RSS sums can double-count shared pages. Full evidence remains limited by record preparation/encoding and persistence, rather than this atomic claim size. One 5,000-input full trial records 0.211 seconds C service, 0.796 record construction, 1.162 encoding, 0.719 SQL and 0.335 commit service; these service times overlap and are not additive wall-time phases. The **5,000/sec full-evidence target remains unmet**.

## Scope still outstanding from the earlier request

- Outpost remains optional and deferred to the coastal marine stage; **Outpost ≥2 has not been adopted**. Adding it requires a versioned policy, native slot-12 goal handling, an additional miss criterion, matching Python/record/retention validation, full retained inventories, and removal of the redundant deferred Outpost query.
- The proposed Mansion/Outpost-first order is absent. Mansion's claimed 1.2 µs cost and resulting 99.8% global skip rate are not established by the retained measurements. Compare orders under the same policy before promoting one.
- Rejecting a seed because four families are absent from the first 32 points can discard later valid witnesses. That negative shortcut remains excluded; exact biome evidence and late-witness regressions are preserved.
- The river/8-way mainland model, ocean/freshwater separation, 600-block corridor, 250-block hub and bonuses were already implemented and verified before Gemini's two changes. Existing terrain tests remain part of verification; this scheduling review does not establish new terrain or BDS speedups.

## Reproduction and retained evidence

```sh
.venv/bin/python scripts/benchmark_native_chunks.py \
  --output runs/new-chunk-review \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/new-reviewed-native --work-chunk 16 \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
```

Use a fresh native build/checkpoint: existing binaries do not change when their source changes. The benchmark's verified 16-chunk build is `runs/gemini-pipeline-review-2026-10-12/benchmarks/native-16`. Portable serial builds omit the OpenMP prefix. The original generator extension and pinned runtime hashes remain unchanged.

Evidence lives in `runs/gemini-pipeline-review-2026-10-12/`: initial status and before-source snapshot; three independent build identities; per-trial commands, CLI logs, receipts and databases; `benchmarks/results.json`; SQL integrity checks; targeted/full-suite logs; and serial ASan diagnostic-buffer results. All 18 benchmark databases passed integrity checks, and transaction receipts report WAL/FULL. ASan exercised 1,248 inputs with zero errors; this is a serial memory-safety check, not a parallel race certificate. Final regression verification is recorded below.

**Final verification: 857 tests passed in 185.62 seconds.** This includes historical/river-policy oracle parity, portable serial builds, parallel ownership, late witnesses, crash/retry/resume, resource failures, terrain/river regressions and durable ranking. An additional actual CLI smoke processed a contained 256-input subset with the reviewed 16-chunk build; resume reported `newly_committed=0` and no remaining work. No natural full-world survivor or new BDS verification is claimed. The earlier requested Outpost/order policy work listed above remains outstanding.
