# Additional pre-sweep optimization and verification

This follow-up addresses the remaining concrete CPU hypotheses and operation checks requested after the bounded CPU completion report. It does not launch the user's production sweep. The earlier 47,326 end-to-end seeds/second and 68,573 checkpointed seeds/second are different measurement scopes; neither is a guarantee for every cohort or concurrent BDS workload.

## CPU and production changes

The delayed-Nether experiment passed natural/synthetic candidate and receipt parity but lost performance in two counterbalanced 50,000-input pairs: 1.0054× and 0.9332×, geometric mean 0.9687×. It was rejected and its source removed; the exact experimental patch, build identity and measurements remain in `runs/pre-sweep-finalization-2026-10-13/`.

The production native adapter previously rejected every range above 100,000, including explicit prediction-scale scans. It now accepts finite full64 ranges above that bound only with explicit `--prediction-scale` and persisted compatibility evidence. Batch size remains <=16,384, pending batches <=3, and existing owned-memory, process memory, disk projection and durable checkpoint gates remain enforced. Experimental helper calls remain capped unless both production and scale gates apply. Latency telemetry is bounded to the last 4,096 batches, with its sample scope exposed in status. Disk projections can still reject a requested range; this is not unlimited-run authorization.

A planned 100,001-input test processes only six inputs across stop/resume and verifies exact coverage, SQLite integrity and lease recovery. No large sweep is executed merely to test this gate. The focused native throughput/retention suite passed 33 tests.

The aligned scheduler/allocation counter experiment also preserved parity but produced paired ratios 0.9608× / 1.0070× (geometric mean 0.9836×). It was rejected and source restored. Existing atomic reservation semantics and buffer caps were not weakened.

Five fresh AB/BA/AB/BA/AB held-out pairs on `[14345670000,14345770000)` revalidated the selected extension with the final Python runtime. Each arm processed 100,000 inputs, retained the same one natural candidate, and passed complete checkpoint/retention coverage and SQLite integrity. Selected median **48,273 external inputs/s**, separately **71,455 checkpointed inputs/s**; paired geometric mean improvement versus the previous control **1.3793×**, exact paired-bootstrap 95% interval `[1.3449,1.4386]`. Cohort variation means this does not imply a new algorithm gain over the earlier 47,326/s result. The selected native extension remains `b7e2420f1092cae903a5f02cc6646dabd039859182649d4686199befe8227b75`. [Frozen runtime](runs/pre-sweep-finalization-2026-10-13/final-runtime-identity.json) and [fresh summary](runs/pre-sweep-finalization-2026-10-13/final-heldout-summary.json) record current identities.

Shared measured budget including prior work, both rejected hypotheses, memory, crash checks and conservatively the BDS preflight: **632.912 seconds / 1,200-second cap**. Build and correctness-test time are separate.

## Crash recovery and memory

A disposable 50,000-input native scan was killed after a durable checkpoint, then resumed. The uninterrupted control and resumed scan both covered the exact interval `[2020000,2070000)` without gaps or duplicate receipts, retained the same two input records, produced identical candidate semantics, and passed SQLite integrity. Evidence: `crash-resume.json` and `check_crash_resume.py` under the finalization directory.

A longer observation completed 97 batches / 49,664 inputs over 185.028 seconds, retaining the known positive in every batch. The last 20 RSS samples ranged from 91,750,400 to 93,310,976 bytes (~1.6 MB variation). The beginning overlapped the bounded BDS preflight; these are memory observations, not concurrent-service throughput claims. This remains an observed finite run, not an indefinite-memory proof. Final complete backend regression: **935 passed in 259.96 seconds** (`PYTHONPATH=. .venv/bin/pytest -q tests`). Frontend source was unchanged; prior production build/lint results remain applicable.

## Fresh actual-server verification

The pinned BDS image generated a disposable 32-block square around origin for signed seed `8521796464527647971` (known-positive predictor index `2028375`). One verification attempt took 26.171 seconds. All 16 sampled columns and exposed-biome observations were stable. All 71 saved block probes reconciled: 26 exact matches and 45 state-only differences independently resolved through the pinned runtime. The snapshot was complete, server exit was clean, no containers remained running, and a cached repeat consumed no second attempt. Exact evidence and tool/runtime identity are in `bds-preflight.json`.

The result correctly remains **PARTIAL**. The user confirmed no Bedrock client is available here, so actual initial-player placement cannot be observed with current tools. No compatible headless client was found in local dependencies. Adding one would require newly validated NetherNet transport, Xbox Live authentication, allow-listed identity and first-join capture; changing to an offline/RakNet runtime would change the tested settings. The stable server API also does not enumerate complete structure inventories. Natural-ground provenance, full terrain connectivity, marine footprints and safe routes are not certified by a 32-square sample. Verifying the eventual winning seed requires generating and inspecting that selected world; a pre-sweep sample cannot certify all future seeds.

## Readiness boundary

CPU experiments are adopted only when correctness agrees and repeatable throughput improves. Unmeasured universal CPU optimality cannot be proved. Actual-world verification remains a separate gate: no predictor candidate is promoted to a verified world by this optimization work. The production sweep remains unstarted.
