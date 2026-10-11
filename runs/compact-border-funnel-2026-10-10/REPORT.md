# Compact border pilots — 10 October 2026

**Compact recommendation: 1280 × 1280 Overworld / 896 × 896 Nether, with discovery 4000 × 4000 in each dimension.**

This retains 249 predicted layouts from 1,000 inputs versus 174 at 1280/768: **43.10% more layouts per input** and **35.38% more qualifying layouts/s** in these matched short trials. Nether width rises 16.67%, area 36.11%; the preferred 1280 Overworld stays fixed.

Keep **1280/768** if minimum playable size is the overriding objective. **1536/896** is the first roomier Overworld fallback, retaining 337 layouts from the same inputs. These are judgments based on the compactness preference, not a mathematically identified terrain optimum.

The compactness recommendation also has a measured area-efficiency basis: with Nether fixed at 896, **Overworld 1280 gives the most qualifying layouts per unit Overworld area** among the seven widths. With Overworld fixed at 1280, **Nether 896 gives the most qualifying layouts per unit Nether area** among the five widths. These are structural-layout density comparisons, not terrain success probabilities.

The highest measured structural layout throughput in the full tested range was **2048/1024**, at 179.85 layouts/s. This larger pair is a throughput reference, not the compact recommendation.

## Scope

Seven Overworld widths (1024, 1280, 1536, 1792, 2048, 2304, 2380) × five Nether widths (512, 640, 768, 896, 1024), with two reversed-order trials per pair: **70,000 evaluations of the same 1,000 distinct signed full64 inputs**, using 30 baseline processes and one native thread each. Discovery is fixed at half-open [-2000,2000) on each axis independently in each dimension.

Overworld is Stronghold-centered. Nether uses its exact fractional Stronghold/8 center. All five required Overworld structures, Fortress AND Bastion, and two wooded families remain mandatory. The 2380 width uses exact membership despite not being a chunk multiple. No geometry threshold, score, game model, native binary, or production setting was changed.

## Structural survival matrix

Each entry is qualifying Stronghold layouts per 1,000 inputs, not distinct seeds or verified worlds.

| Overworld side | Nether 512 | 640 | 768 | 896 | 1024 |
|---:|---:|---:|---:|---:|---:|
| 1024 | 32 | 70 | 103 | 150 | 181 |
| 1280 | 41 | 110 | 174 | 249 | 303 |
| 1536 | 60 | 143 | 232 | 337 | 411 |
| 1792 | 73 | 172 | 288 | 420 | 516 |
| 2048 | 87 | 207 | 353 | 516 | 638 |
| 2304 | 97 | 236 | 411 | 593 | 730 |
| 2380 | 105 | 257 | 440 | 637 | 777 |

![Border matrix](border-matrix.png)

## Compact options and measured rates

| OW / Nether | Qualifying layouts | Unique qualifying seeds | Inputs/s | Qualifying layouts/s |
|---|---:|---:|---:|---:|
| 1024 / 768 | 103 | 96 | 470.55 | 48.47 |
| 1280 / 512 | 41 | 39 | 501.50 | 20.56 |
| 1280 / 640 | 110 | 99 | 473.56 | 52.09 |
| 1280 / 768 | 174 | 156 | 455.36 | 79.23 |
| 1280 / 896 | 249 | 215 | 430.80 | 107.27 |
| 1280 / 1024 | 303 | 252 | 404.39 | 122.53 |
| 1536 / 768 | 232 | 204 | 421.32 | 97.75 |
| 1536 / 896 | 337 | 281 | 386.27 | 130.17 |
| 1536 / 1024 | 411 | 331 | 367.74 | 151.14 |
| 1792 / 896 | 420 | 331 | 354.21 | 148.77 |
| 2048 / 1024 | 638 | 456 | 281.90 | 179.85 |
| 2380 / 1024 | 777 | 511 | 230.30 | 178.95 |

## Every baseline filter

Counts below are cumulative qualifying Stronghold anchors. Predictor nonpasses remain pending; they do not establish actual-world absence. Both final Nether structures are queried at every anchor, even if one fails; the table shows logical cumulative survival. Optional structures only add bonuses and are not rejection filters.

| Filter | 1280 / 512 | 1280 / 768 | 1280 / 896 | 1536 / 896 | 2380 / 1024 |
|---|---:|---:|---:|---:|---:|
| Strongholds | 1835 | 1835 | 1835 | 1835 | 1835 |
| Initial fortress | 1835 | 1835 | 1835 | 1835 | 1835 |
| Final fortress | 648 | 1134 | 1374 | 1374 | 1523 |
| Final bastion | 198 | 841 | 1203 | 1203 | 1456 |
| Ancient city | 45 | 203 | 288 | 372 | 782 |
| Village | 44 | 193 | 275 | 363 | 778 |
| Trial chamber | 44 | 193 | 275 | 363 | 778 |
| Mineshaft | 44 | 193 | 275 | 363 | 778 |
| Two wooded families | 41 | 174 | 249 | 337 | 777 |

![Filter funnel](filter-funnel.png)

At every Overworld size, Nether 512 retains only 198 of the 1,835 discovered anchors after the Fortress+Bastion pair; 768 retains 841, 896 retains 1,203, and 1024 retains 1,456. At compact Overworld widths, Ancient City is the next dominant requirement. Trial Chamber and Mineshaft add no further losses in this cohort after the preceding filters; that result is cohort-specific.

## Terrain filtering

**42 anchor/Overworld pilots across 12 distinct seeds, 9.68 minutes of terrain work**, using the real durable scheduler and 18 native threads. Each Overworld size evaluates six different seeds: two shared controls and four separately hash-selected seeds from that size’s 1024-Nether qualifying pool. Some selected seeds repeat across border sizes, so the 42 evaluations are not 42 independent worlds. Selection ignores terrain scores; common controls and random eligible samples are kept separate.

Nomination covers the full default center grid. The budget is the normal **eight nominated centers per variant**, with independent V1/V2 and resolutions **128 → 64 → 32 → 16 → 8 → 4**. Low-score fine stages, halo limits, and retries retain the production scheduling rules and save unresolved work. This does not exhaust all possible centers.

| Overworld | Samples | V1 strict passes | V2 strict passes | Finest complete footprint within border | Median terrain seconds/anchor |
|---:|---:|---:|---:|---:|---:|
| 1024 | 6 | 0 | 0 | 0 | 10.33 |
| 1280 | 6 | 0 | 0 | 0 | 11.89 |
| 1536 | 6 | 0 | 0 | 0 | 11.53 |
| 1792 | 6 | 0 | 0 | 1 | 13.39 |
| 2048 | 6 | 0 | 0 | 1 | 15.89 |
| 2304 | 6 | 0 | 0 | 2 | 17.93 |
| 2380 | 6 | 0 | 0 | 1 | 17.63 |

**0 strict passing anchor/Overworld evaluations were found.** Strict means predicted qualification, geometry pass, a complete formation footprint wholly inside the exact border, and last height resolution 4. Geometric near matches, partial coverage, and border-clipped formations do not count.

The sample is too small to identify a terrain success-rate optimum. Nether changes baseline eligibility; geometry is reused only when each pair independently qualified the sampled anchor. The four random eligible seeds differ across Overworld sizes; their terrain counts are not a controlled population comparison. The two common controls provide a matched comparison but remain a tiny sample.

| Overworld | V1 evaluations at 128 / 64 / 32 / 16 / 8 / 4 | V2 evaluations at 128 / 64 / 32 / 16 / 8 / 4 |
|---:|---|---|
| 1024 | 1536 / 409 / 48 / 29 / 24 / 24 | 1593 / 408 / 48 / 40 / 35 / 35 |
| 1280 | 2401 / 402 / 48 / 21 / 19 / 19 | 2501 / 414 / 48 / 28 / 25 / 23 |
| 1536 | 3456 / 402 / 48 / 17 / 13 / 13 | 3604 / 420 / 48 / 30 / 27 / 27 |
| 1792 | 4705 / 411 / 48 / 20 / 17 / 17 | 4927 / 429 / 48 / 32 / 30 / 30 |
| 2048 | 6146 / 429 / 48 / 24 / 20 / 20 | 6432 / 432 / 48 / 33 / 33 / 33 |
| 2304 | 7777 / 414 / 48 / 26 / 22 / 22 | 8156 / 432 / 48 / 39 / 38 / 38 |
| 2380 | 8667 / 393 / 48 / 15 / 11 / 11 | 9070 / 414 / 48 / 33 / 30 / 29 |

These are evaluated center observations, including nearby-center tests, adaptive refinement, and halos; they are not unique anchors and are not successive rejection-rate denominators. Full geometry/border counts and reason counts are saved in the JSON/CSV and individual databases.

## Verification and limits

The independent read-only audit passed all **70 baseline databases**, **128,450 candidate-bound/filter checks**, **42 terrain databases**, exact signed-full64 input coverage, repeated memberships, nested required-structure memberships, recomputed stage counts, and **15 public-evaluator seed replays**. Existing computational source/config/native identities remain unchanged (191 sealed files). Overlapping arms also reproduce the previous pilot exactly.

**One biome-sampling exception:** seed 7980124511283784280, Stronghold (772,-1996), qualifies at 2304/1024 but remains pending for wooded-family coverage at 2380/1024. The 2380 border shifts the 64-block biome lattice by 38 blocks relative to 2304; all required structures still qualify. The [coordinate replay](biome-lattice-replay.json) reproduced both forest and jungle at saved points inside the larger border. This is sampling sensitivity, not actual loss of biome coverage or a border-membership error. The exception is preserved in baseline.json and the independent audit rather than hidden to force nested final results.

Native structure/density/biome output is prediction from MC_26_50, not actual Bedrock 26.52 evidence. No BDS or actual structure/terrain/access verification ran, so the final actual-generation filter is **unmeasured**. Production configuration is unchanged and no production sweep started. Small-database rates include startup/IPC/persistence and cannot be substituted for sustained million-input throughput.

Stage seconds in report.json sum measured call durations across workers; they are neither end-to-end wall seconds nor complete CPU attribution. Border area ratios are not used to forecast speed.

Evidence: [report.json](report.json), [independent audit](independent-audit.json), [recommendation](recommended-target.json), [structural matrix CSV](border-matrix.csv), [every filter CSV](filter-funnels.csv), [terrain stages CSV](terrain-stages.csv), [selection](selection.json), [baseline trials](baseline.json), [terrain results](terrain.json).

Reproduce: `.venv/bin/python scripts/measure_compact_border_funnel.py --output <fresh-directory>`; then `.venv/bin/python scripts/audit_compact_border_funnel.py <directory>` and `.venv/bin/python scripts/report_compact_border_funnel.py <directory>`.
