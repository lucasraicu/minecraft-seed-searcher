# Practical resource forecast from retained measurements

No new benchmark was run. These arithmetic extrapolations use historical baseline-only measurements and are not forecasts of current-source throughput or actual terrain/Realm verification.

| Distinct input count | Baseline time at historical rates | Baseline database at historical bytes/input |
|---:|---:|---:|
| 100,000,000 | 5.6–11.3 days | about 3.04 TiB |
| 1,000,000,000 | 56.5–112.5 days | about 30.43 TiB |

The rate range is a scenario bracket between the measured original 100,000-input run and the later reporting/postprocessing-fixed 10,000-input run, both with 30 workers. It is not a statistical confidence interval or proof of a same-workload speedup. Database growth and added discovery/terrain evidence can change both costs. Terrain and BDS generation, unsupported recovery, verification selection and final Nether checks are excluded. Historical measured effective full64 production coverage remains exactly 100,000 distinct inputs.

The filesystem currently reports about 681 GiB free. At historical linear database growth this is insufficient for 100 million inputs. Automatic disk-budget enforcement, compaction/deduplicated evidence, retention and bounded run shards need policy before massive searches. Checkpoint correctness alone does not solve storage scale.

Thirty baseline workers were a practical measured default: the older 10,000-input series had 30 and 36 effectively tied. The later 30-worker 10,000-input scanner peaked at 2.593 GiB sampled aggregateRSS, excluding Docker. The 100,000-input run peaked at 4.152 GiB. These are whole-run observations, not universal per-worker memory constants. Native density terrain work and actual generation have different working sets.

Keep the measured single-verifier allocation of 4 CPUs/6 GiB inside the 8 GiB Docker VM for small checks. The controlled fixture container peaked at 294,612,992 bytes; this tiny world observation cannot bound full formation generation RAM. Preserve the combined 25–30 GiB task limit and monitored headroom before increasing concurrent terrain/server work.

Use already measured data for the current fixes. No new 10,000/100,000/million-input benchmark is necessary to implement correctness changes. Updated throughput and storage expansion remain unmeasured until explicitly authorized later.
