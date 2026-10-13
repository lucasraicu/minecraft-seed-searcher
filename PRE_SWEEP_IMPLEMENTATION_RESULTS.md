# Bounded v2 pre-sweep implementation results

The repository is ready for a **finite predictor sweep** under `origin-fixed-2048-two-group-v2`. Native, Python and replay decisions agree on natural and synthetic cases; a valid Stage 1/2 survivor persists even with two permitted flexible deficit categories. This does **not** certify an actual Bedrock world, initial-player spawn, terrain geometry, monument footprint or safe route. Those claims need separate generated-world evidence. The large production sweep was not started.

## Policy and corrections

`config/realm.yaml` pins Bedrock 26.52, model MC_26_50, run key `0`, fixed half-open Overworld square `[-1024,1024)²`, Nether square `[-512,512)²`, and B=2. Strict Stronghold, Jungle Temple, Desert Pyramid and Outpost floors cannot spend B. Each of eight flexible categories contributes at most one deficit; below-floor counts and missing biome families reject independently. Monument and Shipwreck checks remain deferred. Historical v1 policies and scoring paths remain available. The policy table and exact bonus values are in [the execution plan](PRE_SWEEP_IMPLEMENTATION_PLAN.md).

The native ABI now binds goals, fixed floors and flexible mask and refuses stale v2 extensions. Direct, compact-retention, Python and replay paths enforce the same hard floors, complete score inventories and v2 bonus boundaries. A mismatched CLI B override fails before input publication. Marine `PENDING` preserves baseline survival and its score; later scores remain separate. Spawn evidence has an explicit initial-player/radius/Y/dry/solid/headroom policy and remains `PENDING` without pinned actual-generation evidence. Exports include signed seeds, origin as an evaluation center, independently observed Stronghold starts, every raw or viable predicted structure start, horizontal distance and evidence status; unknown Y is blank. The live API validates and persists the resolved policy, uses exact durable SQLite progress and actual process-tree telemetry, and exposes unknown evidence as null/PENDING rather than inventing spawn, terrain or BDS verification. The UI labels demo and heuristic views separately from live results.

## Verification

- `PYTHONPATH=. .venv/bin/pytest -q tests`: **929 passed** in 262.28s. The first full run exposed four historical river/outpost scoring regressions and one stale default-policy assertion; these were corrected, the five targeted cases passed, and the entire suite passed on the final CLI/native semantics.
- Focused v2/native/API/history gate: **61 passed**. After selecting the live defaults, the API/v2 focused gate passed **43/43**. Frontend production build and lint passed without warnings after the live-mode and stop-request fixes.
- Four compiler arms plus chunk and PGO builds passed exact natural/fixture direct/replay parity. A 100-input v2 CLI smoke and the positive natural service case persisted valid receipts. Existing suite covers compact crash/recovery, concurrent calls, owned buffers, limits, and SQLite integrity. Held-out runs additionally checked every 100,000-input receipt, same-build semantic equality and `PRAGMA integrity_check`.

The positive service case used the already observed tuning index `2,028,375`, outside the held-out interval. It retained **one PREDICTED candidate** from one input and passed SQLite integrity; selected-setting external CLI wall was 0.8599s, internal wall 0.2162s and native service 0.0597s. This checks candidate materialization separately from the all-reject held-out interval. It is not a representative throughput estimate.

## CPU result and decision

The selected configuration is the **same portable O3, OpenMP, chunk-16 extension** at **34 threads and batch 16,384**. The control uses that extension at 16 threads and batch 4,096. `-march=native`, LTO, native+LTO and PGO passed parity but did not show a stable whole-CLI advantage; they were not adopted. Five counterbalanced pairs each ran exactly 100,000 untouched inputs `[9,000,000,000,9,000,100,000)` under the same B=2 policy. No arm retained a natural candidate on this interval.

| External CLI measure | Control | Selected |
|---|---:|---:|
| Median wall per 100,000 inputs | 3.814s | 2.847s |
| Median external rate | 26,218/s | 35,120/s |
| Median checkpointed rate (separate scope) | 31,793/s | 46,019/s |

Paired external speedups were **1.337, 1.357, 1.382, 1.301 and 1.340×** in AB/BA/AB/BA/AB order; geometric mean **1.3432×**, exact paired-bootstrap 95% interval **[1.3194, 1.3655]**. This clears the plan's >=5% whole-CLI adoption criterion. The aspiration of 50,000 external inputs/s was not reached. Observed process-tree RSS was approximately 84–96 MB across the held-out arms; this is sampled RSS, not a guaranteed peak or a BDS-concurrent certificate. The complete measured optimization/profiling budget was **161.715s**, below the 900s target and 1,200s hard cap. Build time is tracked separately.

The [optimization ledger](runs/pre-sweep-v2-2026-10-13/BENCHMARK_EVIDENCE.md) records raw comparisons and dispositions for compiler flags, batch/thread/chunk settings, scratch and generator reuse, allocation, seed packing, queue pressure, filter order, delayed Stronghold, Mineshaft, palette, serialization, SQLite and lifecycle overhead. The one-thread diagnostic leaves a 13.54% wall residual that only upper-bounds allocation **plus** setup/bookkeeping/profiler overhead; a zero-allocation reject-path redesign was not measured or adopted. Filter-order, alternative Stronghold placement and candidate-heavy palette work also remain bounded follow-ups. No exhaustive CPU-optimality claim is made.

## Frozen identity and reproducible finite command

The measured extension SHA-256 is `794b62a893f5fef7e9859bac8175354a9a452ed1a34e280a89e36e2dd677492f`; native source digest `999cd4ca5628c1ce21f35c7e2191f4a032cfbbf1745ac9e88ca625b26b3ad8de`; OpenMP runtime SHA-256 `af4f16ce7fb34f8e444d328b105adead0b655768e32aadbf438972d8e79f92f6`; policy SHA-256 `e6f180bb9f69b42458a1c8e769523eb9b951f79cdfacf4b2755959592992fa44`. [The frozen runtime identity](runs/pre-sweep-v2-2026-10-13/final-runtime-identity.json) records per-file Python hashes at benchmark time. The post-benchmark web launch defaults changed to 34/16,384; they do not alter the measured CLI/native path. Run output identities record the exact resolved config and native build. The local private extension must be rebuilt on a different machine before using this command.

For one fresh finite 100,000-input range outside training, tuning and held-out cohorts:

```sh
PYTHONPATH=. .venv/bin/python -m seed_search --config config/realm.yaml scan \
  --start-index 9100000000 --count 100000 \
  --output runs/pre-sweep-v2-finite-9100000000 \
  --executor native \
  --native-build runs/pre-sweep-v2-2026-10-13/control-native \
  --native-threads 34 --native-batch-size 16384 \
  --retention survivors --max-misses 2 --prediction-scale
```

The saved policy caps native owned buffers at 256 MiB per batch, has a 30 GiB process memory ceiling, 16 GiB free-disk reserve and 128 GiB run-disk cap, and budgets at most 20 downstream BDS verifications with 4 CPU/6 GiB Docker allocation. The command runs prediction only; it does not launch BDS or mark spawn/terrain verification complete. No Chunkbase versioned share-link syntax was established for the pinned Bedrock version, so exports/UI leave the link unset for manual review rather than silently using an older mapping.

Raw five-pair receipts, resource samples and SQLite outputs are under `runs/pre-sweep-v2-2026-10-13/final-heldout/`; the checked [held-out summary](runs/pre-sweep-v2-2026-10-13/final-heldout-summary.json), [pre-heldout results](runs/pre-sweep-v2-2026-10-13/pre-heldout-results.json), [timing ledger](runs/pre-sweep-v2-2026-10-13/timing_budget.json) and [parity gate](runs/pre-sweep-v2-2026-10-13/parity_gate.json) preserve the exact claims. These local run artifacts include bulky databases and private binaries and are not required for source review.
