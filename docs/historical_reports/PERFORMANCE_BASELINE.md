# Measured performance baseline — 10 October 2026

Host: Intel Xeon W-2191B, 18 physical cores / 36 logical threads, 64 GiB RAM. Numerical libraries use one thread per worker. All figures below are measurements, not production forecasts.

## Frozen reference

Pre-change source/configuration snapshot: `runs/realm-implementation-2026-10-10/pre-change-source.tar.gz`, with hashes and the existing dirty git diff retained beside it. Reference suite: 141 tests passed in 99.65 seconds.

## Existing full-search trace

One fixed full64 input, index1, original reference-sweep configuration: **56.362 seconds**. It includes landscape search and scoring; it cannot be compared as equivalent work to the new baseline-only pipeline.
The five largest measured stages at the main search level were landscape18.764s, preliminary14.867s, coast13.137s, biome inventory8.270s and structure scan0.563s. Structures-only8.355s includes nested inventory/refinement work and is excluded from this nonoverlapping ranking. Native height calls totaled51.064s inclusive across their callers: raw density dominates this trace. Inclusive native/API timings must not be added to caller stage times.

## Unconditional diagnostic stage profile

Eight deterministic SplitMix64 full seeds (indexes1–8), one worker, 1764 columns per biome/height workload, exact new discovery/anchor widths. Each seed measures every stage even if its prediction would be pending. Origin is the documented fallback if Stronghold discovery has no predicted viable anchor. Python tracemalloc was enabled; allocations exclude native buffers and are not peak total RAM.

| Stage | Median seconds | Total seconds |
|---|---:|---:|
| raw_density_height_batch | 0.173094 | 1.390492 |
| mineshaft_raw | 0.018795 | 0.151149 |
| mineshaft_viable_repeats_raw | 0.018331 | 0.149051 |
| biome_climate_2d_batch | 0.013660 | 0.112256 |
| surface_biome_batch | 0.009809 | 0.078972 |
| ancient_city_raw | 0.000614 | 0.005031 |
| village_viable_repeats_raw | 0.000501 | 0.004333 |
| ancient_city_viable_repeats_raw | 0.000538 | 0.004276 |
| fortress_viable_repeats_raw | 0.000514 | 0.004272 |
| fortress_raw | 0.000518 | 0.004211 |
| sqlite_single_commit | 0.000548 | 0.004087 |
| trial_chamber_viable_repeats_raw | 0.000468 | 0.003813 |
| stronghold_raw | 0.000433 | 0.003361 |
| serialization | 0.000382 | 0.003107 |
| village_raw | 0.000358 | 0.002883 |
| stronghold_viable_repeats_raw | 0.000349 | 0.002801 |
| trial_chamber_raw | 0.000295 | 0.002452 |
| generator_setup | 0.000125 | 0.000994 |

Python traced peak 1,931,673 bytes; process peak RSS 33,374,208 bytes; wall 1.963s, process CPU 1.961s. Full-search seeds/second is not implied by these unconditional microbenchmarks.

## Equivalent new-baseline reference versus optimization

128 unique full64 inputs (indexes1–128), one worker. Alternate execution order per seed. The reference repeats raw placement in separate raw/viable calls and evaluates remaining required structures/biomes after a provisional negative. The optimized version combines raw+viable scans and defers remaining work for pending anchors. Qualification and observed score of every provisionally qualified record matched exactly; pending records remain saved with explicit deferred checks.

Reference **18.725s (6.84 seeds/s)**; optimized **8.338s (15.35 seeds/s)**. Measured workload speedup **2.25×**, without multiprocessing or terrain/BDS cost.
335 discovered anchor pairs:206 provisionally qualified,129 pending Ancient City viability. Six seeds had no predicted Stronghold; discovery is incomplete, so they remain unresolved rather than certified empty. All128 had a broad predicted Fortress. No confirmed actual-generation rejection occurred.

Ancient City prediction is cheap and deferred129/335 anchors (38.5%) before expensive Mineshaft enumeration and biome batches. On this sample Village/Trial Chamber/Mineshaft had no additional provisional negatives. The measured default order is Ancient City→Village→Trial Chamber→Mineshaft. It is a sampling-based scheduling choice; future measured conditional rates can reorder checks without changing eligibility.

Combined scans reduced Mineshaft work from11.923s to3.689s across paired runs; deferral reduced biome samples from590940 to363384. Optional scoring runs only after required prediction coverage. Contexts are reused per full64 seed and biome calls are batched. No automatic cave inventory is included.

## Persistence and scale limits

The transaction-only synthetic experiment measured2048 identical payloads: legacy per-seed FULL/WAL0.2155s versus batch32 transactions0.0274s (7.87×). This is not an end-to-end search speedup.

Actual compact storage for128 optimized seeds:4,431,872bytes (34,624bytes/seed). Removing duplicated anchors reduced the reproduction from8,343,552bytes by46.9%. Straight-line storage projections are about3.22GiB/100000 seeds and32.25GiB/million, before terrain, BDS or exports; seed-to-seed variation and SQLite growth add uncertainty.

Worker scaling, aggregate sampled RSS, bounded large batches and timing forecasts are recorded separately after their runs. Billion-scale enumeration is implemented as finite resumable ranges; storing billion-scale survivors on one disk is not demonstrated.
