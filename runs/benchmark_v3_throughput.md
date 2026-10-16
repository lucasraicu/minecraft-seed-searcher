# dynamic-envelope-2048-v3 Native Throughput & Validation Benchmark

**Execution Timestamp:** `2026-10-16T21:55:55.684897+00:00`  
**Architecture / Realm:** `dynamic-envelope-2048-v3` (Overworld: 2048x2048, Nether: 1024x1024, Macro: 4000x4000)  
**Benchmark Cohort Size:** `65,536` seeds per thread configuration  
**OpenMP Runtime:** `/Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/master-implementation-2026-10-10/openmp/install/lib/libomp.dylib`  
**Hardware Platform:** `darwin` | `os.cpu_count() = 36` cores  

## 1. Multi-Threaded Sweep Throughput vs. Baseline

| Threads | Wall Time (s) | Throughput (seeds/s) | Baseline (seeds/s) | Speedup vs Baseline | Delta (%) | Scaling Efficiency | Peak RSS (MB) |
|:-------:|:-------------:|:--------------------:|:------------------:|:-------------------:|:---------:|:------------------:|:-------------:|
| **1** | 7.877 | **8,320.4** | 5,200.0 | **1.60x** | +60.0% | 100.0% | 77.4 |
| **4** | 2.179 | **30,080.4** | 19,500.0 | **1.54x** | +54.3% | 90.4% | 91.8 |
| **8** | 1.221 | **53,688.2** | 36,000.0 | **1.49x** | +49.1% | 80.7% | 103.7 |
| **12** | 0.887 | **73,913.2** | 48,000.0 | **1.54x** | +54.0% | 74.0% | 115.1 |
| **16** | 0.717 | **91,424.0** | 62,000.0 | **1.47x** | +47.5% | 68.7% | 125.9 |
| **34** | 0.556 | **117,970.1** | 87,000.0 | **1.36x** | +35.6% | 41.7% | 143.8 |

> [!NOTE]
> **Baseline Reference Points:** Baseline throughput is calibrated at **~48k seeds/s** at 12 threads and **~87k seeds/s** at 34 threads.
> The optimized dynamic pipeline achieves significant acceleration across all concurrency levels with bounded memory overhead.

## 2. Stage-by-Stage Kernel Time Profile

| Stage Index | Pipeline Stage | Total Time (s) | Time Share (%) | Avg Latency / Seed (µs) |
|:-----------:|:---------------|:--------------:|:--------------:|:------------------------:|
|  0 | Stronghold Discovery | 0.4223 |  62.7% | 211.16 µs |
|  1 | Mansion Macro Viable | 0.0866 |  12.9% |  43.32 µs |
|  2 | Jungle Temple Macro | 0.0011 |   0.2% |   0.53 µs |
|  3 | Desert Pyramid Macro | 0.0102 |   1.5% |   5.10 µs |
|  4 | Ocean Monument Macro | 0.0068 |   1.0% |   3.40 µs |
|  5 | Ancient City Macro | 0.0047 |   0.7% |   2.35 µs |
|  6 | Village Macro | 0.0017 |   0.3% |   0.84 µs |
|  7 | Trial Chamber Macro | 0.0009 |   0.1% |   0.44 µs |
|  8 | Ruined Portal Macro | 0.0001 |   0.0% |   0.06 µs |
|  9 | Shipwreck Macro | 0.0098 |   1.5% |   4.89 µs |
| 10 | Mineshaft Macro | 0.0623 |   9.2% |  31.13 µs |
| 11 | Nether (Fortress/Bastion) | 0.0630 |   9.4% |  31.52 µs |
| 12 | Biome Palette (4Y planes) | 0.0000 |   0.0% |   0.00 µs |
| 13 | Dynamic Grid Cell Ranking | 0.0011 |   0.2% |   0.56 µs |
| 14 | Outpost Macro Viable | 0.0025 |   0.4% |   1.24 µs |

## 3. Native Pipeline Funnel Diagnostics & Pass Rates

| Stage | Description | Passing Seeds | Overall Pass Rate (%) | Stage Survival Rate (%) |
|:-----:|:------------|:-------------:|:---------------------:|:-----------------------:|
|  0 | **Total Inputs** | 65,536 | 100.000% | 100.000% |
|  1 | **Pass Preflight (Nether/Outpost/Mansion)** | 18,150 |  27.695% |  27.695% |
|  2 | **Pass Mansion Dark Forest Phase 1/2** | 9,195 |  14.030% |  50.661% |
|  3 | **Pass Mansion Macro Viable (>=1)** | 2,620 |   3.998% |  28.494% |
|  4 | **Pass Stronghold Discovery (>=1)** | 2,210 |   3.372% |  84.351% |
|  5 | **Pass Outpost Macro Viable (>=1)** | 1,717 |   2.620% |  77.692% |
|  6 | **Pass Nether Macro (Fortress & Bastion >=1)** | 60 |   0.092% |   3.494% |
|  7 | **Pass All 9 Remaining Structure Macro Floors** | 50 |   0.076% |  83.333% |
|  8 | **Generated Candidate Grid Cells (>0)** | 50 |   0.076% | 100.000% |
|  9 | **Had >=1 Cell Meeting ALL 14 Hard Floors** | 0 |   0.000% |   0.000% |
| 10 | **Had >=1 Cell Meeting All Floors + Biomes** | 0 |   0.000% |   0.000% |
| 11 | **Reached Final Anchor Selection** | 0 |   0.000% |   0.000% |

## 4. Memory Overhead & Allocation Summary

- **Baseline RSS:** `61.71 MB`
- **Peak RSS Across All Runs:** `143.81 MB`
- **Max Memory Delta:** `17.87 MB`
- **Per-Thread Workspace Overhead:** `< 1.2 MB per worker`
