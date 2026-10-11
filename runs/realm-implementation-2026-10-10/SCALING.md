# Scaling measurements — 10 October 2026

Each10,000-seed run uses the same range[0,10000), identical baseline computation and candidate pool. Six repetitions therefore represent10,000 unique full64 inputs, not60,000. Neither terrain nor BDS runs in these timings. Process startup, serialization and SQLite checkpoints are included.

| Workers | Seeds/s | Wall s | Sampled scanner peak GiB | Effective worker CPU cores | Database MiB |
|---:|---:|---:|---:|---:|---:|
| 12 | 140.49 | 71.18 | 1.290 | 10.26 | 322.4 |
| 16 | 161.35 | 61.98 | 1.652 | 12.61 | 322.4 |
| 18 | 173.22 | 57.73 | 1.846 | 13.59 | 322.4 |
| 24 | 182.48 | 54.80 | 2.294 | 15.06 | 322.4 |
| 30 | 188.20 | 53.14 | 2.721 | 15.84 | 322.4 |
| 36 | 187.71 | 53.27 | 3.150 | 16.42 | 322.4 |

30 and36 are effectively tied in this single ordered measurement (0.26%difference). Choose30 as the initial baseline default;24 costs only3.13%throughput and leaves more CPU headroom for BDS. Dedicated concurrent BDS/scanner timing remains to be measured before choosing a combined default.

All requested worker counts through36 actually contributed in10k. The earlier1,000-input pilot had only32batches, so its36-worker case used32processes. Its one-worker rate was14.9seeds/s. Across the identical1,000-input series,30workers ran about9.7×faster than1worker; the larger10k throughput should not be multiplied into that result as a matched speedup.

Each10k run saved15,618predicted-qualified anchors and10,714pending anchors. Unknown Ancient City predictions dominate pending results; no actual generation absences were asserted. Full64 viability/biomes remain independent even though eight raw-MT structure placement families use low32bits.

RSS is a sampled process-tree sum and may double-count shared pages or miss short peaks. Measured worker getrusage peaks are also saved. The8GiBDockerVM allowance is added conservatively, giving a maximum reserved combined budget estimate11.15GiB at36workers. This is not measured active BDS memory.

Code metadata changed during additive terrain/CLI development, but all baseline computational sources stayed identical across the six10k cases. Exact per-run hashes and configuration are saved. This is documented in STORAGE_WORKERS.md; future baseline-only checkpoint identity excludes separate terrain and presentation code.

100k follow-up and forecasts will be appended once its actual measurements finish. A million-input run will require a practical-cost decision; no billion-input claim is made.
