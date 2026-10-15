# Dynamic baseline benchmark results — 2026-10-14

The adopted compact scan measures **33,710 durable input seeds/sec** (median of five counterbalanced 100,000-input trials), versus **6,037/sec** for the initial unoptimized dynamic implementation at its 16-thread control setting. This is **5.58×** for the complete implementation/settings change. It does not compare identical thread counts or isolate a single optimization. Historical ~70k/sec measurements used an older fixed-window policy and must not be applied to the new sliding-window baseline.

## Final adoption protocol

- Policy: `dynamic-envelope-1664-v1`; exact geometry, required biome families and category budget B=2 unchanged between arms.
- Five distinct 100,000-input cohorts: index ranges `[0,100000)` through `[400000,500000)`, run key `2027101403`.
- Seed generation permutes `index + run_key`. This key is distant from tuning key `2026101401` and training key `2026101402`; their pre-permutation intervals are disjoint.
- Counterbalanced arm order: control/selected, selected/control, control/selected, selected/control, control/selected.
- Both use 16,384-input batches so persisted range boundaries match. Control uses 16 native threads; selected uses 34.
- Wall time includes directory/compatibility preparation, source/build checks, seed preparation, native processing, record/receipt preparation, SQLite commits and pipeline shutdown. Independent database/digest inspection follows the timed invocation.
- Every range receipt, input count, all-input decision digest and retained candidate digest matches between arms. Exact contiguous coverage is checked independently for every run.
- **Zero natural survivors in these 500,000 inputs.** This validates negative processing and durability on this cohort, not rare-survivor cost or a joint pass-rate estimate. Native/reference/replay positive fixtures and independent geometry/scoring checks cover positive behavior separately.
- Cumulative build/profiling/benchmark budget: **1025.0s / 17.08 minutes**, below the agreed 20-minute cap. No additional performance trials were run after adoption.

| Pair | Control durable seeds/sec | Selected durable seeds/sec |
| --- | ---: | ---: |
| 1 | 5,941 | 34,155 |
| 2 | 6,064 | 31,507 |
| 3 | 6,037 | 33,356 |
| 4 | 5,972 | 35,663 |
| 5 | 6,302 | 33,710 |

Selected trials range from 31,507 to 35,663/sec (max/min 1.13). This is a repeated short-run measurement on the current workstation, not a promise for sustained multi-day operation or other hardware.

## Compiler and CPU choices

All configuration trials contain 50,000 inputs; PGO training uses at most 50,000 natural inputs per training process plus a synthetic late-path fixture. Native generator scratch stays worker-owned; no Python per-rejected-seed evidence expansion occurs in compact retention. Exact hard-floor exits and conservative raw-placement impossibility checks replace expensive work only where they cannot change eligibility.

| Initial compiler arm, 34 threads / batch 16384 | Median native kernel inputs/sec |
| --- | ---: |
| control | 7,639 |
| portable | 27,383 |
| native | 25,507 |
| lto | 27,802 |
| native-lto | 27,358 |
| chunk64 | 26,592 |
| chunk128 | 25,634 |
| pgo | 34,167 |

These initial arms used the earlier dynamic source snapshot. `control` disables the new raw preflight; `portable` enables it. Native instructions and LTO alone did not deliver a meaningful reliable gain in those trials; the combined PGO build did. Subsequent shared raw-Nether enumeration preserved independent placement-scan parity; moving compact Stronghold discovery behind cheap rejection checks improved the final portable source and preserved full-retention discovery semantics.

| Final source arm, 34 threads / batch 16384 | Median native kernel inputs/sec |
| --- | ---: |
| shared-portable | 28,811 |
| shared-pgo16 | 38,557 |
| shared-pgo64 | 37,471 |
| shared-pgo128 | 34,969 |

The final PGO16 median above includes both repeated arm trials and the two grid visits at these settings. These are tuning kernel measurements, excluding persistence, not held-out durable measurements. Chunks 64/128 lost to chunk16 on the final source. A two-pass counterbalanced grid measured threads 16/24/30/32/34 × batches 4096/8192/16384. The selected measured combination is **34 threads, batch16384, work chunk16, `-march=native`, LTO and source-matched PGO**.

The installed build is `runs/dynamic-baseline-1664/native`. Its identity and source hashes are recorded in `reviews/dynamic_benchmark_summary.json`; binaries and profiles remain local. Reproduction on another CPU requires retraining/rebuilding and retuning. Build flags:

```sh
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/dynamic-baseline-1664/native \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install \
  --work-chunk 16 --cpu-native --lto \
  --pgo-use runs/dynamic-final-2026-10-14/chunk16.profdata
```

## Excluded and interrupted measurements

An initial durable harness invocation failed because it did not create the compatibility report required by the scale gate. An intermediate refinement was stopped before adoption to move costly Stronghold discovery after cheap compact rejection. An earlier completed five-pair run used key `2026101403`; adjacent keys overlap under seed generation, so that validation is excluded from adoption. The frozen builds were revalidated using the distant key above. All of those runs count toward the cumulative budget; the raw local records remain available.

The committed benchmark drivers now use the distant held-out key. `validate_dynamic_holdout.py` compares persisted decisions directly without duplicating kernel runs, using the prior cumulative budget and frozen builds.

## Release scope

The measured compiler, PGO, raw preflight, worker scratch, filter-order, chunk/thread/batch and persistence paths are reviewed within the bounded plan. This is sufficient to adopt these settings for a **predictor sweep**, with the regression results in `LATEST_PUSH_REVIEW.md`. It does not prove that every possible CPU redesign has been exhausted. Prefix structures, exact noise and complete positive inventories deliberately preserve correctness rather than using unproven heuristic biome cutoffs or structure auto-credit.

Actual-world certification remains separate: current tools provide bounded surface observations, not complete generated structures, portal rooms, loot or first-player spawn. Known predictor recall limits remain. The joint rarity and cluster/yield projections have not been calibrated by this benchmark.
