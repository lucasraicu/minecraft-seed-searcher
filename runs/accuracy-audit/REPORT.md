# Bedrock 26.52 accuracy audit — 7 October 2026

Our prototype agrees closely with Chunkbase on the tested samples, but this is a bounded comparison between predictors, not proof of whole-world Minecraft accuracy. Six structure disagreement records and six surface biome disagreements remain. The broader preflight goal remains incomplete.

## Scope and method

- Chunkbase Seed Map was read through its interactive UI with **Bedrock 26.50–26.52** selected. Local model: pinned `MC_26_50` backend. Seeds: `12345`, `0`, `-1`, `4294979641`.
- The upper-bit seed equals `12345 + 2^32`; some structure families repeat, so these are not four statistically independent worlds for every family.
- A deterministic local grid surveyed 65,536 points at each of Y=63 and Y=-51 per seed, from -32,768 to 32,512 at 256-block spacing. It selected surface representatives, four cave representatives, 40 random terrain columns and five Nether biome representatives per seed.
- 159 unique coordinate checks cover **52 surface biome types, four cave types, and all five Nether types**. These are representatives; their complete area, boundaries and vertical extent are not validated.
- Chunkbase labels **Deep Warm Ocean** as **unused**. The backend enum retains it, but it did not occur in the surveyed grids and was not given an invented passing sample.
- Structures: 20 parsable UI coordinate rows per type per seed, 880 total, across all 11 wrapper-supported types. Search lists are capped and their order is not distance order. Portal variant labels can make some rows unparsable; this is a convenience sample, not a random sample.
- Correspondence rule: nearest viable local start within 64 blocks; a ±160-block diagnostic window also checks raw placements. Starts and website entrance/room markers can differ. Unmatched records were rechecked in 6,000-block-wide local windows.
- The radius is a declared matching heuristic, not a correctness tolerance certified by Minecraft. Complete structure footprints, types/variants, entrances and safe access were not checked.
- Local density ground Y is compared directly with Chunkbase marker Y, with no added global offset. Marker Y is a website estimate, not an observed game block. Land/water means the prototype’s Y>=63 threshold; it does not establish actual liquid blocks.
- All external rows are stored as third-party predictions. Existing phone observations remain separate. No large seed search was run.

## Quantitative results

| Measurement | Agreement/error |
|---|---:|
| Surface biome, exact X/Z | 129/135 = 95.6% |
| Nether biome, sampled Y=33 | 20/20 |
| Cave biome, sampled Y=-51 | 4/4 |
| Terrain height, mean / median absolute difference | 1.0 / 1.0 blocks |
| Terrain height, 95th percentile / maximum difference | 3.0 / 5 blocks |
| Terrain heights within 2 blocks / exact | 125/135 / 46/135 |
| Density height land/water threshold agreement | 131/135 |
| Cheap discovery proxy, mean / maximum absolute difference | 2.84 / 19.18 blocks |
| Cheap proxy land/water threshold agreement | 129/135 |
| Default stride-eight versus stride-one heights | 133/135 identical |
| Structure correspondences within 64 blocks | 874/880 = 99.32% |
| Structures with exactly equal marker/start coordinates | 477/880 |

These percentages describe this sample. They are not a false-positive rate, complete recall, or a guarantee that a candidate island fits. Capped positive lists cannot certify missing structures or extra local predictions.

## Structure results

| Type | Corresponding viable starts | Exact coordinates | Maximum offset among matches |
|---|---:|---:|---:|
| trial_chamber | 80/80 | 0 | 24.04 blocks |
| stronghold | 78/80 | 78 | 0.00 blocks |
| mineshaft | 80/80 | 80 | 0.00 blocks |
| ancient_city | 78/80 | 78 | 0.00 blocks |
| village | 80/80 | 80 | 0.00 blocks |
| ruined_portal | 80/80 | 1 | 19.85 blocks |
| shipwreck | 80/80 | 80 | 0.00 blocks |
| monument | 80/80 | 80 | 0.00 blocks |
| outpost | 80/80 | 0 | 11.31 blocks |
| fortress | 80/80 | 0 | 4.24 blocks |
| bastion | 78/80 | 0 | 43.84 blocks |

The consistent offsets for Outpost and Fortress, and varying offsets for Trial Chamber, Portal and Bastion, are compatible with different marker conventions. They are still recorded, and do not prove in-game generation.

### Structure disagreements

| Seed | Type | Chunkbase X,Z | Local finding |
|---|---|---|---|
| 12345 | bastion | (1185, 376) | Raw start (1208, 408) rejected by viability |
| -1 | stronghold | (6212, -4700) | No raw or viable start within ±160 blocks |
| -1 | stronghold | (3524, -7276) | No raw or viable start within ±160 blocks |
| -1 | ancient_city | (-3048, 3256) | Raw start (-3048, 3256) rejected by viability |
| 4294979641 | ancient_city | (-680, 6216) | Raw start (-680, 6216) rejected by viability |
| 4294979641 | bastion | (1185, 376) | Raw start (1208, 408) rejected by viability |

- The bastion disagreement repeats for the two seeds with identical lower bits. Local start `(1208,408)` is rejected; the nearest viable local bastion is `(1272,600)`, 240 blocks from the website marker. The marker’s local biome at Y=33 is Basalt Deltas, while the raw start’s is Nether Wastes. The structure marker and viability sampling point differ; actual presence has not been established.
- Both missing seed -1 strongholds remain absent in local 6,000-block-wide windows centered on the website markers. This is not a small coordinate offset.
- Both ancient cities have exact raw placement matches. The backend viability check samples the biome at Y=-27, using quart coordinates, and rejects those starts. This is a viability disagreement, not a placement-RNG failure. It needs an actual generation check before changing the rule.
- The previously user-confirmed absent seed-12345 Fortress at `(-152,120)` is now excluded by the corrected adapter and regression test. That is separate in-game negative evidence; none of the new disagreements are silently treated as Minecraft observations.

## Biome disagreements and cave boundaries

| Seed | X,Z | Local surface biome | Chunkbase surface biome |
|---|---|---|---|
| 12345 | (-11776, -768) | beach | forest |
| 12345 | (-13568, -24320) | stony_shore | desert |
| 12345 | (6400, 32000) | dark_forest | birch_forest |
| 12345 | (6912, -21504) | old_growth_birch_forest | windswept_forest |
| 12345 | (23296, -31488) | eroded_badlands | river |
| 4294979641 | (3878, -4013) | beach | birch_forest |

All six disagreements persist at the website’s estimated surface height. The website biome occurs one or two blocks away in our local biome map (see boundary diagnostics). This suggests boundary sampling differences; it does not resolve which predictor is correct at the exact block.

The four cave names agree at Y=-51, but vertical ranges do not all agree. Chunkbase ranges versus local exact-block ranges:

- Dripstone: website -56..51; local -56..49 plus a separate 54..55 interval.
- Lush: website -64..11; local -64..9.
- Deep Dark: both -64..-49.
- Sulfur: website -60..31; local -59..31.

## Terrain implications

The density estimator is close enough in this sample for preliminary terrain screening. It does not establish block-perfect coastline geometry. Four columns disagree on the Y=63 land/water threshold; the cheaper discovery proxy disagrees at six. Such errors can create or remove thin apparent land bridges. The prototype excludes caves, aquifers, decorations and actual chunk interpolation. Nether terrain heights, caves/overhang geometry, tree/log abundance, whole-island connectivity and surrounding mountain coverage remain unverified.

| Seed | X,Z | Local density Y | Website Y |
|---|---|---:|---:|
| 0 | (-1792, -32000) | 60 | 63 |
| 0 | (20992, 29952) | 60 | 63 |
| -1 | (711, -2983) | 61 | 63 |
| 4294979641 | (-3127, -2517) | 62 | 63 |

## Unsupported coverage

End biomes, End terrain, End Cities and End Gateways are not implemented by this wrapper. Other website structures/features outside the 11-type adapter include Woodland Mansion, Dungeon, Jungle Temple, Desert Temple, Witch Hut, Buried Treasure, Igloo, Ocean Ruins, Fossil, Nether Fossil, Nether Ruined Portal, Trail Ruins and Abandoned Camp. Spawn, slime chunks, geodes, ore veins, desert wells and cave features are also outside this audit’s implemented capabilities. These are missing coverage, not passing checks.

## Evidence and reproduction

- [Durable external observations](../../fixtures/bedrock-26.52/chunkbase-accuracy-audit.json)
- [Biome/terrain rows](biome-terrain-comparison.json), [structure rows](structure-comparison.json), [metrics and source hashes](metrics.json)
- [Exported terrain figure](terrain-comparison.png)
- [Biome boundary diagnostics](biome-boundary-diagnostics.json), [cave range diagnostics](cave-range-diagnostics.json), [structure failure diagnostics](structure-disagreement-diagnostics.json)
- [Existing phone observations](../../fixtures/bedrock-26.52/seed-12345.user-observations.json) remain separate.
- Recompute local structure comparisons: `.venv/bin/python scripts/compare_accuracy_audit.py`.
- Recompute biome/terrain metrics and this report: `.venv/bin/python scripts/report_accuracy_audit.py`.
- The deterministic survey can be regenerated with `scripts/prepare_accuracy_audit.py`; external UI observations are a frozen snapshot and must not be regenerated from our predictor.
- Full local suite: 44 tests pass after the Fortress correction. Audit integrity checks enforce all 159 unique point rows, all 880 unique seed/type/coordinate rows and 20 samples per supported type per seed.

## Per-biome coverage

| Biome | Exact matches / samples | Mode |
|---|---:|---|
| badlands | 4/4 | surface |
| bamboo_jungle | 2/2 | surface |
| basalt_deltas | 4/4 | nether |
| beach | 2/4 | surface |
| birch_forest | 2/2 | surface |
| cherry_grove | 2/2 | surface |
| cold_ocean | 3/3 | surface |
| crimson_forest | 4/4 | nether |
| dappled_forest | 2/2 | surface |
| dark_forest | 1/2 | surface |
| deep_cold_ocean | 2/2 | surface |
| deep_dark | 1/1 | bottom |
| deep_frozen_ocean | 3/3 | surface |
| deep_lukewarm_ocean | 2/2 | surface |
| deep_ocean | 6/6 | surface |
| desert | 3/3 | surface |
| dripstone_caves | 1/1 | bottom |
| eroded_badlands | 1/2 | surface |
| flower_forest | 2/2 | surface |
| forest | 7/7 | surface |
| frozen_ocean | 2/2 | surface |
| frozen_peaks | 2/2 | surface |
| frozen_river | 2/2 | surface |
| grove | 2/2 | surface |
| ice_spikes | 2/2 | surface |
| jagged_peaks | 2/2 | surface |
| jungle | 2/2 | surface |
| lukewarm_ocean | 2/2 | surface |
| lush_caves | 1/1 | bottom |
| mangrove_swamp | 2/2 | surface |
| meadow | 2/2 | surface |
| mushroom_fields | 2/2 | surface |
| nether_wastes | 4/4 | nether |
| ocean | 3/3 | surface |
| old_growth_birch_forest | 2/3 | surface |
| old_growth_pine_taiga | 2/2 | surface |
| old_growth_spruce_taiga | 2/2 | surface |
| pale_garden | 2/2 | surface |
| plains | 7/7 | surface |
| river | 2/2 | surface |
| savanna | 4/4 | surface |
| savanna_plateau | 2/2 | surface |
| snowy_beach | 2/2 | surface |
| snowy_plains | 2/2 | surface |
| snowy_slopes | 2/2 | surface |
| snowy_taiga | 2/2 | surface |
| soul_sand_valley | 4/4 | nether |
| sparse_jungle | 2/2 | surface |
| stony_peaks | 2/2 | surface |
| stony_shore | 1/2 | surface |
| sulfur_caves | 1/1 | bottom |
| sunflower_plains | 2/2 | surface |
| swamp | 4/4 | surface |
| taiga | 3/3 | surface |
| warm_ocean | 3/3 | surface |
| warped_forest | 4/4 | nether |
| windswept_forest | 2/2 | surface |
| windswept_gravelly_hills | 3/3 | surface |
| windswept_hills | 2/2 | surface |
| windswept_savanna | 2/2 | surface |
| wooded_badlands | 3/3 | surface |
