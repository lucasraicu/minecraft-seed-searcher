# Locked geometry, native screening and terrain/BDS investigation

Completed 12 October 2026. Evidence is retained in `runs/native-locked-geometry-2026-10-12/`. The active revision is `locked-2048-1024-v1`; historical configurations and measurements remain available. No unlimited search was launched.

## Implementation and adoption

The active CLI/configuration now use a 2048×2048 Overworld square, inclusive `[anchor−1024, anchor+1023]`, and a 1024×1024 Nether square around the **exact fractional Stronghold/8 center**. Integer bounds use ceilings to preserve half-open membership, including negative coordinates. The historical `blueprint_config()` remains 1536/896; `locked_blueprint_config()` supplies the new default. A stale batch extension fails with an explicit rebuild instruction. The original generator binary and pinned OpenMP runtime were preserved.

Core floors are Mansion 1, Village 6, Trial Chamber 5, Ancient City 2, Pyramid 1, Jungle Temple 1, Portal 6, Mineshaft 15, Fortress 2 and Bastion 2. Stronghold is mandatory. Native screening runs Nether pair, Portal, Chamber, cached Mansion, Pyramid, Temple, City, Village and Mineshaft. Count queries stop at their floors; retained candidates receive complete core inventories. The exact 64-entry per-input Mansion cache remains enabled.

Compact mode defaults to **one unmet requirement**. Its 23 criteria are ten structure-count requirements and thirteen biome predicates at the same anchor. Missing several copies of one structure counts as one miss. `--max-misses 2` remains available. Unretained inputs create no per-input evidence objects/SQL rows; atomic FULL-durability range receipts still record coverage and retry decisions. Full-evidence mode keeps every input, discovered anchor and pending task.

Monument, Shipwreck and optional Outpost are absent from both baseline count and baseline full-inventory queries. After the finest configured terrain raster has complete known coverage and passes the coastal footprint model, Stage 3 obtains full unfiltered marine inventories, derives the qualifying coastal subset, and checks Monument ≥1 / Shipwreck ≥4. Candidate, score, marine evidence and terrain completion commit atomically with exact retry validation. Deferred marine requirements are labeled explicitly and do not silently count as passed. `full_blueprint_certification=false` remains explicit. Near misses remain PENDING and require `terrain.include_pending` to enter terrain automatically.

The new 64-block four-Y lattice has **4096 defined points**, rather than the old 2304. All thirteen predicates and their Y roles remain exact. The proposed rejection after 64–128 samples was **not adopted**: failure to witness a rare family in a prefix does not establish absence in the rest of the square. A regression fixture places a required snowy witness after 512 queries and must survive. Existing dispersed traversal and exact early success remain; negative decisions retain the entire required lattice.

The revised native route is adopted as an **explicit executor option** after native/direct/replay/Python semantic parity, ownership, durable workflow and portable-build verification. Python remains available and the default executor. The shortened terrain ladder, approximate biome rejection and changed BDS properties were not adopted. This is not a certificate of actual Bedrock playability or an estimate of world-discovery time.

## Fresh throughput comparison

Three counterbalanced trials per arm; 50,000 distinct inputs, key `120267001000`. Full-evidence trials use a contained 10,000-input subset, not additional distinct search volume. Native-only timing excludes SQL. CLI timing includes startup/import, native or Python work, record preparation, FULL SQLite commits, pipeline drain and process exit. Batch size 4096; compact/C use 32 native threads, full evidence uses 16 native threads plus two pipeline CPU slots, and the Python control uses 36 one-thread workers. Each trial uses a fresh run directory.

| Contract and policy | Median inputs/sec | Three-trial range |
|---|---:|---:|
| Historical two-miss C only | 15,089.92 | 14,794.78–15,103.30 |
| Locked one-miss C only | 12,646.71 | 12,382.69–13,042.32 |
| Locked two-miss C only | 6,672.50 | 6,659.69–6,680.16 |
| Historical two-miss compact CLI | 11,662.36 | 11,660.45–11,880.16 |
| **Locked one-miss checkpointed compact CLI** | **10,192.81** | **10,182.02–10,263.31** |
| Locked two-miss checkpointed compact CLI | 5,783.05 | 5,686.15–5,832.88 |
| **Locked native full-evidence persisted CLI** | **1,281.97** | **1,276.92–1,317.27** |
| Locked Python full-evidence persisted CLI | 961.98 | 948.47–968.11 |

The comparable full-evidence native/Python speedup is **1.333× (33.26%)**, with zero complete-record/durable-task semantic differences. Repeated fingerprints are stable. The new one-miss compact policy is 12.60% slower than the fresh historical two-miss control; this comparison changes geometry, floors, ordering, deferred stages and allowance together, so it is not an isolated optimization ablation. Earlier 19,835/sec native-only and 3,730/sec full-evidence numbers apply to older policies/cohorts. They are not current locked-border persisted rates.

The **5,000/sec full-evidence target remains unmet**. Compact exceeds 10,000 checkpointed scanned inputs/sec by discarding rejected per-input evidence, a deliberately different contract. Neither number includes terrain or official-server verification.

The 50,000-input cohort retained one input/anchor with one-miss mode and 25 inputs/26 anchors with two-miss mode. All are natural **near misses**, with zero complete core survivors. The one-miss example is seed `4778609107263059373`, anchor `[-1436,740]`, missing Mansion, observed score 158 and marine DEFERRED. Historical mode retained none. These volumes do not establish full-world probability, Gemini's expected winner counts, or independent structure/biome probabilities.

| CLI arm | Peak process-tree RSS | Largest final SQLite DB |
|---|---:|---:|
| Historical compact | 144.32 MiB | 208 KiB |
| Locked one-miss compact | 147.50 MiB | 320 KiB |
| Locked two-miss compact | 198.28 MiB | 4.57 MiB |
| Locked native full, 10,000 inputs | 548.69 MiB | 184.54 MiB |
| Locked Python full, 10,000 inputs | 1914.55 MiB | 184.82 MiB |

Final DB size excludes transient WAL and retained reports; per-trial WAL peaks are in raw receipts. Full native DB cost is approximately 19.35 KB/input on this cohort. Preflight reserved 33.42 GB projected benchmark allocation plus 16 GiB free reserve, against 636.16 GB available. Native and prepared buffers retain their independent 256 MiB ownership caps, bounded outstanding batches, backpressure and recoverable leases.

For the first 10,000-input native full trial, aggregated service times were C 0.517 s, direct records 1.649 s, encoding 2.445 s, all preparation 3.208 s (including hash 0.456 s, validation 0.140 s and task preparation 0.166 s), SQL 3.448 s, commit 0.725 s, writer wall 4.313 s and queue wait 2.377 s. These overlapping/aggregated timings are not additive end-to-end wall time; preparation is not disk time alone. Serialization, SQL and the single writer remain the full-evidence bottleneck.

## Entered-stage latency and outliers

Diagnostic build, 10,000 active inputs and 128 separately forced complete inputs, each repeated three times. Repetitions are not distinct volume. Profiling overhead was **3.85%**, with zero semantic differences against the untimed build. Timing buffers remain capped at 64 MiB. The natural-positive compact fingerprint now uses the same existing semantic normalization as full records; worker PID, timing and resource metadata no longer manufacture a parity difference. No semantic exclusion was broadened.

| Active entered stage | Calls pooled over repetitions | Mean µs | Bounded p99 interval µs |
|---|---:|---:|---:|
| Stronghold discovery | 30,000 | 407.42 | 524–1049 |
| Nether pair | 55,263 | 18.04 | 16–33 |
| Ruined Portal | 52,275 | 9.81 | 8–16 |
| Trial Chamber | 52,275 | 75.12 | 66–131 |
| Mansion | 52,263 | 753.44 | 2097–4194 |
| Desert Pyramid | 18,036 | 173.10 | 131–262 |
| Jungle Temple | 2,958 | 145.89 | 131–262 |
| Ancient City | 1,230 | 393.81 | 524–1049 |
| Village | 210 | 362.77 | 524–1049 |
| Mineshaft | 33 | 1764.91 | 2097–4194 |
| Four-Y palette | 33 | 42,825.21 | 33,554–67,109 |
| Monument / Shipwreck | **0 baseline calls** | — | — |

Mansion dominates frequently entered structure work; palette dominates each late reached anchor. Mineshaft/palette tails have only eleven natural anchors per repetition and cannot establish population p99. The well-sampled stages did not trigger the diagnostic large-tail threshold. Forced palette mean was 29.10 ms, a different conditional cohort from active 42.83 ms. Raw results include all four Y levels, returned biome IDs and thirteen family groups; family timing describes shared generator calls, not independent searches.

Nether-first work stopped roughly **5.4%** of these one-miss anchors before Portal, not the unverified 45% claim. One unmet Nether requirement is intentionally tolerated. The measurement supports cheap ordering, not a new selectivity prediction. Additional Mansion or exact palette improvements require a controlled same-policy ablation; prefix rejection or approximate SIMD cannot replace parity gates.

## Terrain multi-resolution investigation

Three retained natural two-miss anchors were evaluated unconditionally as diagnostic controls, **not eligible complete survivors**. Three rotated trials compared the existing `128 → 64 → 32 → 16 → 8 → 4` schedule, proposed `128 → 32 → 4`, and `4` alone, using 18 native terrain threads. Sampling and geometry are timed; retained NPZ artifact writes are outside timing. All 27 final rasters and full final coastal decisions agree exactly. Timing metadata and independently validated reuse counters are normalized, while all semantic metrics/decisions remain compared.

| Existing level | Samples | Median sampling ms | Median geometry ms |
|---|---:|---:|---:|
| 128-block nomination | 256 | 1.34 | 1.14 |
| 64-block density | 1,024 | 7.90 | 1.46 |
| 32-block density | 4,096 | 23.10 | 2.45 |
| 16-block density | 16,384 | 88.69 | 5.62 |
| 8-block density | 65,536 | 351.62 | 12.11 |
| 4-block density | 262,144 | 1376.18 | 33.45 |

The 128 nomination is a cheap 2D approximation, **not equivalent 3D density**. The existing density cascade already reuses every exact nested sample: across density levels it queries only 262,144 unique points, plus 256 nomination points. The final row above therefore samples only 196,608 new points, reusing 65,536. Removing middle levels hardly reduces actual density work.

Median total for the three-control cohort: existing six levels **5.665 s**, three levels **5.567 s**, fine-only **5.640 s**. The proposed ladder gains only **1.76%**, too small on three controls to justify discarding intermediate evidence/scheduling behavior. It was not promoted. A fresh 32-level without prior density reuse takes about 31 ms to sample, already beyond the proposed 15 ms complete-medium target.

All three controls fail the final coastal model. Coarse mainland fraction is not a safe rejection proof: one control changes from 60.55% nomination to 36.52% medium and 24.74% fine. Early coarse work can prioritize or defer candidates, while queues preserve them; it cannot establish fine-resolution connectivity, exact cliff/beach slopes or absence. A 4-block raster is itself sampled model evidence, not exact continuous terrain or actual blocks. Existing bounded refinement and ranking are retained. No 10 s → <15 ms complete-footprint speedup was measured.

## Bounded BDS investigation

The existing production adapter already runs headless after screening, reserves a persistent budget of 20 official-world attempts, caches exact requests, batches tiles **within the same world**, cleanly stops before snapshotting and reads copied LevelDB chunks. `verify-terrain --top 20` is bounded by the remaining budget and eligibility; neither a repeated cached request nor partial evidence becomes a new verified world. Different seeds require distinct generated worlds.

Microsoft documents **view-distance minimum 5**, so proposed 4 is unsupported. Tick-distance already uses its minimum 4. View distance is relative to players; the zero-player script uses managed ticking areas. See [official server properties](https://learn.microsoft.com/en-us/minecraft/creator/documents/bedrockserver/server-properties?view=minecraft-bedrock-stable) and [simulation/render-distance guide](https://learn.microsoft.com/en-us/minecraft/creator/documents/simulationrenderdistanceguide?view=minecraft-bedrock-stable).

Four fresh diagnostic worlds, two counterbalanced trials each, compared current view-distance 8 against 5 at tick-distance 4. Each requested a tiny **32×32 region, sixteen columns and one tile**, using the pinned image, native/reference column checks, stability, save, clean shutdown, snapshot and LevelDB coverage. Docker VM had four CPUs and 7.75 GiB memory; per-server caps remained four CPUs/6 GiB. Production files and verification evidence identities remained unchanged.

| Setting | Median complete adapter latency | Trial range |
|---|---:|---:|
| View distance 8 | 10.987 s | 10.858–11.116 s |
| View distance 5 | 10.958 s | 10.886–11.030 s |

The **0.27%** difference is noise at this sample size. Neither setting met eight seconds. Exact request-cache repeats returned in 0.124–0.226 ms; those are cache lookups, not new-world verification. Peak server memory was at most 307.77 MiB for these tiny probes.

All four controller reports have raw PASS (their stability and reference checks), but raster evidence is **PARTIAL**. Only two of nine expected chunks were present/finalized in each copied LevelDB snapshot. Thirteen sampled-column differences across repeats/settings, including seagrass/coral state changes, are retained verbatim. They are not ignored to produce parity and do not isolate view distance as their cause. These observations are explicitly non-promotable finalist evidence. No production BDS setting was changed. All newly created diagnostic containers and volumes were removed after clean stop and retained snapshots; original containers/evidence were preserved. Two preliminary diagnostic boots and their failed parity run are retained separately.

A 2048 border needs **64 tiles** at the adapter's 256-block tile size, exceeding the current measured 16-tile request cap. The adapter correctly returns PARTIAL rather than silently claiming full coverage. Sequential stability checks have at least two one-second waits per tile, so a complete-border request requires a separately validated batching/coverage policy. Twenty full-world verifications in 2.5 minutes is **not established**. Direct LevelDB reading does not remove generation/load/stability costs or repair missing chunks/natural-ground semantics. The remaining BDS work is completeness and supported chunk coverage, before adopting latency shortcuts.

## Verification, identities and retained artifacts

Final regression suite: **834 passed** (see `final-suite-834.log`). Serial ASan completed **1248 historical + 1248 locked inputs**, including timing buffers, with zero errors. This is serial memory-safety evidence, not a parallel race certificate. Native serial/OpenMP parity, signed64 boundaries, negative fractional Nether centers, every floor, positive and late-stage failures, concurrent owned calls, FULL compact/full task coverage, retry/rollback, export and resume remain covered. The production terrain entrypoint fixture executes all six stages, queries marine only after the finest complete coastal result, updates scoring atomically and resumes without work. The actual CLI 256-input default-one-miss smoke and zero-work resume passed; benchmark SQL integrity/durability checks passed.

The independent Python evaluator, ReplayProvider and native direct records agree. Tests validate deferred marine metadata rather than deleting it from parity. Historical behavior is still tested. Existing authored probability/geometry claims remain distinguished from supported predictor evidence. No new large-search readiness or actual-playability certificate was issued; V2 stays outside active scheduling.

The original dirty/untracked source was saved in `before/`, `before-manifest.json` and `initial-status.txt`; final sources and verification metadata are retained separately. The original `_native.abi3.so` SHA-256 remains `512df6a76cc24c90cd0a78eddd45e60fd06d0f1e945cb3a9521ab42fe75e385d`; runtime SHA-256 remains `af4f16ce7fb34f8e444d328b105adead0b655768e32aadbf438972d8e79f92f6`. New production batch extension SHA-256 is `07c89d1495924ff6b581b5ac0f3ffc2dc03a792ecc2d185de62a5ea579fd9450`; isolated profile extension is `eeb54cb86927afb4ebe5135a65ed5952ae5914ffd55c67613ce3d0422ba5dd54`. Build-input manifests are checked against the final sources.

The earlier M0–M6 throughput milestones remain recorded in [NATIVE_THROUGHPUT_RESULTS.md](NATIVE_THROUGHPUT_RESULTS.md). This revision repeats the applicable inventory/identity, direct-record parity, atomic writer, bounded pipeline, workflow/benchmark, explicit adoption and terrain-profile gates. Passing implementation gates does not mean the throughput target or real-world verification gate passed.

Raw measurements:

- [Native/Python and historical-policy comparisons](runs/native-locked-geometry-2026-10-12/benchmarks/results.json), per-trial receipts, SQLite databases and logs.
- [Entered-stage profile](runs/native-locked-geometry-2026-10-12/stage-profile-final/results.json); the failed metadata-fingerprint diagnostic is also retained.
- [Terrain schedules and exact final parity](runs/native-locked-geometry-2026-10-12/terrain-cascade/results.json), with 27 retained NPZ rasters.
- [BDS latency, exact column differences and coverage](runs/native-locked-geometry-2026-10-12/bds-latency-final/results.json), controller reports, stopped-world snapshots and cleanup receipts.
- `asan-legacy/result.json`, `asan-locked/result.json`, final regression log, CLI smoke/resume and `final-verification.json`.

Reproduce with fresh output directories:

```sh
.venv/bin/python scripts/build_blueprint_batch.py --output runs/new-locked-native \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python scripts/benchmark_locked_blueprint.py --native runs/new-locked-native \
  --output runs/new-locked-comparison --count 50000 --trials 3
.venv/bin/python scripts/investigate_terrain_cascade.py \
  --run runs/native-locked-geometry-2026-10-12/benchmarks/compact_cli-locked_two_miss-0 \
  --output runs/new-terrain-comparison --trials 3
.venv/bin/python scripts/investigate_bds_latency.py --output runs/new-bds-comparison
.venv/bin/python -m pytest -q
```

The benchmark reserves disk before starting and limits inputs to 100,000. BDS diagnostics use temporary property overrides and preserve snapshots; they do not modify production settings or certify finalists. Prediction-scale and larger-search readiness remain separate gates.
