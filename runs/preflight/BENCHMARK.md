# Preflight performance measurements

Fixed diagnostic workloads on this Mac; **not a completed search benchmark**.

| Stage | Median seconds | Observed range |
|---|---:|---:|
| generator setup seconds | 0.000 | 0.000–0.000 |
| coarse biome climate seconds | 0.335 | 0.328–0.343 |
| coarse component seconds | 0.004 | 0.003–0.005 |
| one full border density refinement seconds | 3.678 | 3.465–3.720 |
| one 256 block shoreline patch seconds | 0.426 | 0.415–0.452 |
| all structure adapter seconds | 0.580 | 0.576–0.589 |

Coarse-only parallel tests (10 seeds at most; startup included):

| Workers | Batch seconds | Effective seconds/seed |
|---|---:|---:|
| 4 | 1.581 | 0.158 |
| 8 | 1.291 | 0.129 |
| 12 | 1.050 | 0.105 |

Full search time per seed remains unmeasured. More candidate islands mean more refinement work.
These are local prediction timings; phone inspection is separate.

Backend: `294c72ab0392dd818a91d293dbd5774d4874d64b`; proposed 26.50 model for 26.52 remains unverified.
