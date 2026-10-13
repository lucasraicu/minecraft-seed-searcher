# CPU completion benchmark evidence

This continuation shares the original pre-sweep 1,200-second measured-run hard cap. The new `timing_budget.json` starts with the original 161.714675633-second measured balance and records each new CLI or fixture trial, including failed measured attempts. Build time is separate. All external CLI runs use `config/realm.yaml`, corrected v2 run key `0`, B=2, 34 threads, batch 16,384 and portable O3/chunk 16 unless a comparison explicitly says otherwise.

The tuning interval is `[3000000,3050000)`, capped at 50,000 inputs per arm. The untouched final interval is `[12345670000,12345770000)`; existing run JSON/Markdown and source were searched for these exact bounds before its selection. The old `[9000000000,9000100000)` heldout and documented example at 9.1 billion are excluded.

| Comparison | Inputs per arm | Control wall | Variant wall | Speedup | Status |
|---|---:|---:|---:|---:|---|
| Old O3 control vs compact origin stack anchor | 50,000 | 1.7894s | 1.7847s | 1.0026× | Parity passed; effectively even in one pair. |
| Stack anchor default order vs strict-first order | 50,000 | 1.7894s | 1.5881s | 1.1267× | Parity passed. |
| Stack anchor default order vs strict-first order, reverse order | 50,000 | 1.7567s | 1.5753s | 1.1151× | Repeated improvement. |
| Strict-first Stronghold after two checks vs after one | 50,000 | 1.5671s | 1.6311s | 0.9608× | Earlier query is slower. |
| Strict-first Stronghold after two checks vs after four, three AB/BA/AB pairs | 50,000 | 1.5642–1.5656s | 1.3231–1.3476s | 1.1616–1.1822× | After four consistently faster. |
| Same-source after-four vs after-three | 50,000 | 1.3963s | 1.4454s | 0.9660× | After three slower. |
| Same-source after-four vs after-five | 50,000 | 1.3514s | 1.3504s | 1.0007× | Effectively even. |
| Same-source after-four without vs with stack anchor, AB/BA pairs | 50,000 | 1.3395s / 1.3712s | 1.3870s / 1.3572s | 0.9657× / 1.0103× | No demonstrated stack benefit. |

Both measured builds passed natural native/direct/replay and Python decision checks, complete synthetic fixture qualification (three predicted, one pending), and compact retention of all three predicted fixtures. The 50,000-input strict-first pair retained one natural candidate in each arm with identical semantic record hashes. Their aggregate input-decision receipt hashes differ because the rejected-input processing order changes; no equality claim is made for that diagnostic hash. Both arms completed every checkpoint and retention receipt and passed SQLite integrity.

The stack-anchor experiment was rejected and removed. The strict-first and after-four variants were adopted only after the final frozen-source held-out confirmation. The initial candidate fixture digest failure was traced to integer `1` versus boolean `True` in `baseline_score_complete`; the adapter now serializes a boolean, with regression coverage and passing native/direct/replay gates. Failed and diagnosis measurements remain charged to the timing budget.

Grouped palette measured 0.7533→0.7427 seconds on 96 repeated natural positives (~1.4% native service gain), below the adoption threshold, and was removed. No population throughput estimate is inferred from repeated positives.

Final frozen-source compiler AB/BA screening: native ratios 1.0047/1.0404, LTO 0.9891/1.0126, native+LTO 1.0009/1.0120, PGO 1.0251/1.0523. All passed parity, none demonstrated a stable >=5% external improvement. Portable O3 retained. PGO training used its separate 50,000-input interval plus positive fixtures and matching source/profile manifest.

Queue depth two was slower than three; writer preparation and encoding variants preserved semantic records and did not justify changing defaults. Array/from-buffer packing was slower than list CFFI. Raw pipeline, encoding and packing JSONs retain measurements. The 97-batch memory check kept a known survivor each batch and stabilized after warm-up, with approximately 1.2 MB variation across the last 20 RSS samples.

Five held-out AB/BA/AB/BA/AB pairs on the untouched interval completed with one matching natural candidate per arm, exact 100,000-input receipts and SQLite integrity. External speedup ratios: 1.3575, 1.3649, 1.3744, 1.3579, 1.3838; geometric mean 1.3676557, exact paired-bootstrap 95% interval [1.3591359,1.3766862]. Selected median external wall 2.113025 seconds (~47,326 inputs/s); checkpointed rate separately 68,573 inputs/s. See `final-heldout-summary.json` for identities, resource samples and overlapping service timers.

Total measured shared budget: 366.149397 seconds including inherited 161.714676 seconds, well below the 1,200-second cap. Build and correctness-test time are excluded. The final source and runtime identities are frozen; no unlimited sweep or actual-world certification is implied. Current dispositions and reproducible commands are in the root CPU completion report.

Final correctness gate: 933 tests passed in 263.09 seconds. Frontend source was unchanged in this continuation; earlier production build/lint passed.
