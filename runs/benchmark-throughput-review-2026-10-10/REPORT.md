# Saved benchmark throughput review

The million-input run completed in 96.14 minutes at 173.37 input seeds/s, with discovery 5000, Overworld 2688, Nether 1024, and 30 processes × one native thread. It includes structural/biome baseline, worker startup, IPC and persistence; terrain/BDS are excluded.

Forecast point: 82.44 minutes; working range 74.20–123.66. Time was 16.61% above the point estimate, throughput 14.25% below it.

## Discovery compromise

5000-input pilots with Overworld 2688 and Nether 1024, not reoptimized for compact 1280/896; 4000 is a speed/coverage compromise, not a proven terrain optimum.

| Discovery side | Input seeds/s | Predicted qualifying anchors/s | Anchors retained vs 5000 |
|---:|---:|---:|---:|
| 5000 | 193.77 | 234.54 | 100.00% |
| 4000 | 267.90 | 230.23 | 71.00% |
| 3000 | 440.59 | 220.12 | 41.28% |

## Timed filtering calls

Number of reached-stage seed/anchor checks divided by summed timed call duration across workers. Local per-worker average, not separate wall-clock seed throughput or an isolated benchmark. No multiplication by 30 is justified.

Stronghold and initial Fortress discovery each query a seed. Subsequent checks query Stronghold anchors; multiple anchors can belong to one seed. Optional structures are bonus scoring, not an eligibility filter.

| Stage | Reached checks | Timed checks/s per worker | Mean ms/check | Share of timed stage call cost |
|---|---:|---:|---:|---:|
| Stronghold discovery | 1,000,000 | 2,719.84 | 0.3677 | 0.69% |
| Initial Fortress discovery | 1,000,000 | 3,005.29 | 0.3327 | 0.63% |
| Final Fortress | 2,629,026 | 6,310.16 | 0.1585 | 0.79% |
| Final Bastion | 2,629,026 | 11,177.26 | 0.0895 | 0.44% |
| Ancient City | 2,067,891 | 1,342.30 | 0.7450 | 2.91% |
| Village | 1,207,511 | 1,620.35 | 0.6172 | 1.41% |
| Trial Chamber | 1,205,024 | 2,698.06 | 0.3706 | 0.84% |
| Mineshaft | 1,205,024 | 44.99 | 22.2271 | 50.61% |
| Wooded-biome inventory | 1,205,024 | 79.33 | 12.6061 | 28.70% |
| Optional structures (one grouped bonus batch) | 1,202,310 | 175.18 | 5.7084 | 12.97% |

Counts for Ancient City, Village and biome checks are derived from aggregate counters using the formulas in summary.json and the saved baseline algorithm. Timed rates exclude untimed Python orchestration, IPC and parent persistence; they cannot be read as separately measured pipeline capacities.

The new compact pilot at 4000 discovery / 1280 Overworld / 896 Nether measured 430.80 input seeds/s and 107.27 qualifying layouts/s on fresh 1000-input trials. This is not a sustained million-run measurement. Its bounded eight-center-per-variant terrain median was 11.89 seconds per anchor; no strict terrain passes were found.

Lower32 promotion targets were not met: measured coarse rejection 0.73%, with a 63.03-hour full-range native projection before ranking/checkpoint costs, versus proposed 99.9% / 45-minute aspirations.

Actual-generation certification and terrain/BDS end-to-end throughput remain unmeasured. All benchmark identities/checkpoints are preserved.

Evidence: [derived summary and source hashes](summary.json), [completed million benchmark](../master-implementation-2026-10-10/million/benchmark.json), [pre-benchmark forecast](../master-implementation-2026-10-10/million-forecast.json), [discovery comparison](../discovery-size-comparison-2026-10-10/REPORT.md), [compact pilots](../compact-border-funnel-2026-10-10/REPORT.md).
