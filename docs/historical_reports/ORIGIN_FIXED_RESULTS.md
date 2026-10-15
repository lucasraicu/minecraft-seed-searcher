# Fixed-origin screening pilot — 13 October 2026

The active `origin-fixed-2048-v1` policy evaluates one center at **world origin `(0, 0)`**. This is not a calculation of the player's actual spawn. It uses the half-open Overworld square `[-1024,-1024,1024,1024)` and Nether square `[-512,-512,512,512)`. At least one *actual predicted Stronghold start* inside the Overworld square is mandatory, independent of the one-miss allowance. Every distinct predicted start is retained for the second-Stronghold score. Historical Stronghold-centered policies remain available.

The native compact path checks the Nether pair, Ruined Portals and Trial Chambers before querying Strongholds; it avoids the historical discovery search on many early failures. Full-evidence mode still records the Stronghold query for every input. The remaining structure floors and complete four-Y biome requirements are unchanged. Compact retention still saves near misses of at most one secondary requirement, while a missing Stronghold cannot qualify. No 32-point negative biome shortcut was introduced because it could discard valid late witnesses.

## Bounded production-entry-point pilot

The fresh pilot used 30,000 **distinct input indices per trial**, the same indices for each policy, three repeated trials per policy, rotated order `control, origin, origin, control, control, origin`. All trials ran the production `seed_search baseline` CLI with `--executor native --retention survivors --max-misses 1 --native-threads 32 --native-batch-size 4096`, a new SQLite run for each trial, and the same sequence key. The control is `locked-2048-1024-outpost-v3`; its frozen native build SHA-256 begins `2f771315`. The final origin build SHA-256 begins `8d862689`. The host reported x86_64 Intel Xeon W-2191B and 64 GiB RAM. The OpenMP build used the repository's pinned runtime. This is repeated measurement of the same 30,000 inputs, **not** 180,000 distinct searched seeds.

| Rate, inputs/sec | Historical control, 3 trials | Fixed origin, 3 trials | Median change |
|---|---:|---:|---:|
| Checkpointed scan pipeline | 30,038–30,581; median **30,500** | 41,444–41,924; median **41,854** | **+37.2%** |
| Complete CLI wall time including startup | 18,080–18,470; median **18,412** | 21,530–22,096; median **21,735** | **+18.0%** |

All six databases passed `PRAGMA integrity_check` and recorded completed range coverage for 30,000 inputs. The control retained one near miss; the origin policy retained zero on this cohort. Median database size was 266,240 bytes for control and 204,800 bytes for origin; this difference partly reflects the unequal retained-candidate counts. The pipeline rate includes durable range checkpoints and SQLite commits, but is **compact-mode checkpointed input throughput**, not full-evidence persisted-seed throughput. Native-only rate, peak RSS, actual Bedrock-world validity and complete-world discovery probability were not measured in this pilot. The original 150,000/sec proposal is not met. The two policies have different eligibility and geometry; the measured increase is an end-to-end policy comparison, not a causal estimate of one filter's speedup.

In compact origin mode, `discovered_anchors` counts predicted Strongholds only for seeds that reached the delayed query. It is not an exhaustive Stronghold count across all 30,000 inputs; full-evidence mode preserves that per-input discovery evidence.

Raw rates, source/build identities, stdout/stderr, configurations and six databases are retained under [`runs/origin-fixed-pilot-2026-10-13/final/`](runs/origin-fixed-pilot-2026-10-13/final/), with the final native build under [`final-native/`](runs/origin-fixed-pilot-2026-10-13/final-native/). An earlier pilot build remains in the parent directory and is not substituted for the final source measurement.

## Accuracy and remaining limits

Synthetic fixtures verify the perfect case, one and two missed secondary requirements, a missing mandatory Stronghold, two distinct Stronghold starts, score bonuses, durable tasks, retry/resume and CSV export. Natural high-bit seed fixtures compare direct native records, native replay, and the independent Python evaluator for both short-circuit and complete paths. A 16-input production CLI full-evidence smoke run persisted all 16 input rows and its discovery/terrain tasks; SQLite passed integrity checking. The portable serial native build loaded and completed a compact CLI smoke run. The complete regression suite passed **886 tests**; the log is `runs/origin-fixed-pilot-2026-10-13/full-suite-pass.log`.

The Stronghold predictor remains a model, not authoritative absence or proof of a generated End Portal. The origin center also does not establish the player's actual spawn. Terrain, marine counts, navigable river, loot and actual-game verification remain downstream. No complete natural baseline survivor appeared in the 30,000-input cohort, so the pilot cannot estimate winner frequency or time to a playable world.
