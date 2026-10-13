# CPU optimization completion — 2026-10-13

The bounded CPU optimization work is complete. The selected predictor is portable C11/O3 with OpenMP chunk 16, **34 threads and batches of 16,384**, strict structures first and Stronghold checked after the fourth Overworld structure. It is ready for finite predictor sweeps under the corrected B=2 category policy. Actual Bedrock world, spawn, terrain and route verification remain pending; no large production sweep was launched. This certifies the measured workstream and stopping rule, not mathematical optimality across every possible CPU algorithm.

## Measured result

Five counterbalanced AB/BA/AB/BA/AB pairs each processed exactly 100,000 untouched inputs in `[12345670000,12345770000)`. The comparator is the previous validated portable build at the same 34 threads / 16,384 batch setting and identical acceptance/scoring policy; only processing order and persisted Stronghold placement differ.

| Measure | Previous build | Selected build |
|---|---:|---:|
| Median external CLI wall / 100,000 inputs | 2.9011 s | 2.1130 s |
| Median external CLI rate | 34,470 inputs/s | 47,326 inputs/s |
| Median checkpointed rate, separate scope | 44,691 inputs/s | 68,573 inputs/s |

Paired geometric mean external speed-up is **1.3677× (+36.8%)**, with exact paired-bootstrap 95% interval `[1.3591,1.3767]`. Every arm retained the same one natural candidate, covered all inputs with durable receipts, and passed SQLite integrity. A separate known-positive input also produced identical semantic hashes in control and selected arms. The external rate is below the aspirational 50,000/s target and meets the approved plateau-based release rule. Rates depend on cohort and host load; checkpointed rate excludes some CLI costs.

## Optimization decisions

| Hypothesis | Evidence and disposition |
|---|---|
| Strict-first filter order | Two 50,000-input comparisons improved 11.5–12.7%; adopted. |
| Delayed Stronghold query | After four beat after two by 16.2–18.2% across three pairs; after one/three were slower, after five tied; adopted after four. |
| Rejected-seed stack anchor | Winning-order paired results 0.9657× / 1.0103×; rejected. Existing worker scratch reuse retained. The reject path is not claimed allocation-free. |
| Native CPU flags / LTO / native+LTO | Re-screened on frozen winning source, AB/BA pairs; no stable >=5% external gain; rejected. |
| PGO | Separate 50,000-input training plus positive fixtures, matching profile/source manifest and parity; external ratios 1.0251× / 1.0523× (geometric mean about 1.039×); rejected below adoption threshold. |
| Grouped survivor palette | 96 repeated natural positives: native median 0.7533→0.7427 s (~1.4%); rejected. No population-rate claim from repeated positives. |
| Seed packing | 49,152 inputs per variant; list CFFI 0.001609 s versus array/from-buffer 0.001893 s; retained existing packing. |
| Queue depth / writer preparation | Eight bounded pipeline trials with equal candidate records; queue depth two slower, writer preparation effectively tied; retained depth three and preparation thread. |
| Record encoding | Four matched bounded trials; encoded path slightly faster with identical records; retained. |
| Mineshaft alternative algorithms | Earlier stage profile showed only two entries and 3.6% of small diagnostic native time; no demonstrated population bottleneck justifies an additional algorithm redesign within this bounded workstream. |
| OpenMP threads, batch and chunks / hard-floor exits | Previously measured and implemented; retained selected 34/16,384/chunk-16 settings and category-independent fatal-floor exits. |

The shared measured profiling/benchmark ledger totals **366.149 seconds**, including the inherited 161.715 seconds and failed measured attempts, below the original 900-second target / 1,200-second cap. Compilation and correctness tests are separate. Tuning trials were bounded to 50,000 inputs; final adoption used five 100,000-input pairs. A 97-batch, 49,664-input memory check retained a known positive in every batch; the last 20 RSS samples varied by approximately 1.2 MB after warm-up. This short observation does not certify unlimited-duration memory behavior.

## Correctness and reproducibility

Native/full/compact/Python/replay parity passed for final portable and compiler variants, natural positives and synthetic boundary fixtures. Historical v1 and older v2 ordering remain supported through explicit policy/build matching. New builds persist Stronghold placement; mismatched old private extensions fail before executing the new policy. Native record completeness now serializes as a boolean consistently with replay. The live server selects the new private build; it retains explicit environment override support.

Final backend suite: **933 passed in 263.09 seconds** (`PYTHONPATH=. .venv/bin/pytest -q tests`). The first full run found a stale API-test build path; it was corrected, its focused tests passed, and the complete suite then passed. Earlier frontend build/lint passed; this continuation changed no frontend source.

Selected extension SHA-256: `b7e2420f1092cae903a5f02cc6646dabd039859182649d4686199befe8227b75`. Native source digest: `dac8b08da484a206905ee24cc66603e5c2c8f8f544acc74367c707be2a5f3026`. [Runtime identity](runs/cpu-completion-2026-10-13/final-runtime-identity.json), [held-out summary](runs/cpu-completion-2026-10-13/final-heldout-summary.json), [benchmark ledger](runs/cpu-completion-2026-10-13/BENCHMARK_EVIDENCE.md) and [timing budget](runs/cpu-completion-2026-10-13/timing_budget.json) preserve the exact claims. Local binaries and databases are excluded from source commits.

Rebuild the explicit private extension on another host before use; the packaged extension is not the measured artifact:

```sh
PYTHONPATH=. .venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/cpu-completion-2026-10-13/final-portable \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install \
  --work-chunk 16 --stronghold-after 4
```

Example finite prediction command on a fresh range (not executed):

```sh
PYTHONPATH=. .venv/bin/python -m seed_search --config config/realm.yaml scan \
  --start-index 12400000000 --count 100000 \
  --output runs/cpu-completion-finite-12400000000 --executor native \
  --native-build runs/cpu-completion-2026-10-13/final-portable \
  --native-threads 34 --native-batch-size 16384 \
  --retention survivors --max-misses 2 --prediction-scale
```

The saved memory/disk/owned-buffer limits and downstream verification budget remain applicable. Predictor results retain their evidence status and do not become verified worlds merely by completing this CPU gate.
