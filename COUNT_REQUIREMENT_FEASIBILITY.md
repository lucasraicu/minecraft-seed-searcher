# Count requirement feasibility from the retained million-seed benchmark

The million run can establish **observed coexistence and larger observed counts for categories it actually recorded**. It cannot establish absolute achievable maxima, complete counts for unqueried categories, or current filter throughput. This analysis reused its saved coordinates without launching another seed search.

## Geometry and coverage

The historical benchmark ran 1,000,000 distinct full64 inputs with **5000×5000 discovery / 2688×2688 Overworld / 1024×1024 Nether**. Its 2,629,026 candidates are Stronghold anchors, not distinct seeds.

This read-only scan examined **2,629,026 candidate records**, retained **1,846,578 anchors** across 865,137 distinct seeds inside today's 4000×4000 discovery, then cropped each recorded start inventory to **1536×1536 Overworld** at that same Stronghold and **896×896 Nether** at its exact Stronghold/8 center. Scan time was 10.79 minutes. No candidate centers were shifted to improve counts.

All retained anchors are considered; this differs from the smaller count pilot, which froze the first selected anchor per input. Lower and upper border membership use half-open bounds. Counts deduplicate coordinate pairs within each structure type. A profile is matched only when its requirements coexist in the same candidate's border.

## Selective combinations found

Each row requires at least the listed number of distinct starts of each type, plus its chosen Stronghold anchor. Columns show **distinct seeds with retained positive evidence**, not anchor totals, estimated world probabilities, or complete rejection rates. One seed can occur in several rows.

Nether means at least one Fortress and one Bastion together inside 896×896. Biome columns additionally require the listed number of **distinct active biome IDs** within Forest and Taiga, witnessed inside that same 1536×1536 border. These biome counts are conservative lower bounds from stored first witnesses at Y=63; they do not replay the new four-Y world-aligned sampling policy.

| Requirement profile | Villages | Trial Chambers | Ancient Cities | Mineshafts | OW evidence | + Nether | + Forest 2 / Taiga 1 | + Forest 3 / Taiga 2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| core_one_each | 1 | 1 | 1 | 1 | 314,011 | 263,458 | 14,838 | 1,742 |
| two_core | 2 | 2 | 2 | 3 | 146,657 | 121,809 | 6,359 | 730 |
| more_core | 3 | 3 | 2 | 5 | 113,052 | 93,808 | 4,887 | 566 |
| more_core_three_cities | 3 | 3 | 3 | 5 | 57,815 | 47,702 | 2,426 | 283 |
| four_each_core | 4 | 4 | 4 | 4 | 17,297 | 14,285 | 682 | 62 |
| eight_each_core | 8 | 8 | 8 | 8 | 0 | 0 | 0 | 0 |
| previous_individual_core_maxima | 9 | 11 | 7 | 55 | 0 | 0 | 0 | 0 |

These selective requirements have positive examples; the zero-result rows only mean that this retained evidence did not demonstrate them. Old early exits left later checks unqueried, so a zero row is not a proof of impossibility. Terrain and actual-game generation remain unevaluated.

A concrete example for the `more_core` profile is seed **-8246845270002098890**, centered at Stronghold **[-284, -1356]**. Its retained cropped structure counts are `{"ancient_city": 2, "bastion": 2, "fortress": 1, "mineshaft": 37, "monument": 0, "outpost": 1, "ruined_portal": 6, "shipwreck": 0, "trial_chamber": 7, "village": 6}`. Its retained first-witness biome family counts are `{"dark_pale": 2, "forest": 4, "mountains": 2, "rivers_shores": 2, "snowy_ice": 3, "taiga": 3}`. This is one coherent border, rather than separate category maxima combined across seeds.

A fresh inventory of this example on the current world-aligned 64-block lattice at Y=63,-48,0,160 found **5 Forest IDs and 3 Taiga IDs** among 2304 sample points. The native capped Forest-3/Taiga-2 combination passed after 289 queries. This checks one concrete example against the current policy; it is not a four-Y replay of every million-run candidate.

## Largest retained positive counts

These are observations in current-size crops, not absolute maxima or a promise that the entries coexist in one seed. Positive counts were recorded by the historical predictor; later skipped stages cannot lower the evidence but may hide larger counts elsewhere. The ten categories below are the useful historical inventories. Their individual maxima examples were independently replayed with the current full64 native predictor.

| Category | Largest retained count | OW placement slot ceiling | Example seed | Stronghold center |
| --- | ---: | --- | --- | --- |
| village | 10 | 16 | -1618363647766229637 | [-1468, 900] |
| trial_chamber | 14 | 16 | -1100640056012108111 | [-1708, -1148] |
| ancient_city | 14 | 25 | -1499396919552886818 | [-1516, -972] |
| mineshaft | 68 | 9216 | 837966781688634707 | [1364, -1980] |
| fortress | 7 | Nether; OW ceiling not applicable | 1373100615429081896 | [-1804, 1236] |
| bastion | 8 | Nether; OW ceiling not applicable | -2852701481357597650 | [1268, -1612] |
| monument | 9 | 16 | 836719616355803649 | [1524, 1972] |
| outpost | 4 | 4 | 8648718363399461168 | [884, 1300] |
| shipwreck | 17 | 25 | 4257782967066140495 | [-1532, -1036] |
| ruined_portal | 9 | 9 | 253978793194525224 | [292, 804] |

Mineshaft's 9,216 ceiling counts possible starting-chunk slots and is not a realistic count target. Stronghold is excluded from this maximum table: each candidate explicitly stores its one chosen anchor, not a complete cropped Stronghold inventory.

The old run did not query Desert Pyramid, Jungle Temple, Swamp Hut, Igloo, Mansion, Ocean Ruin, Trail Ruins or Abandoned Camp. Buried Treasure and Monster Room were marked unsupported. It also did not inventory Nether portals or End Cities. Therefore the million run cannot replace the existing all-category pilot or settle maxima for those categories.

## Why maximum-everywhere is not a usable requirement

Independent maxima can conflict. Desert Pyramid, Jungle Temple, Swamp Hut and Igloo share placements and disjoint eligible biome sets in the pinned predictor. Their combined viable-start demand is at most **16** in this border. The earlier individually observed counts require **8 + 4 + 3 + 8 = 23** across those four types. Asking for all four observed maxima together is therefore impossible under these placement rules, even before adding other structures or terrain requirements.

Biome family maxima count distinct IDs, not repeated patches. The catalog ceiling is 56 active Overworld IDs across 19 families. A catalog lists possible IDs; it does not demonstrate all 56 occurring within one border. First-coordinate summaries cannot reconstruct every ID inside a smaller crop, and Y=63 records cannot inventory underground diversity across all requested Y levels. See [the placement and catalog ceilings](OVERWORLD_COUNT_LIMITS.md).

The interactive comparison uses the separate 896-layout structure / 48-layout biome pilot. Its preset match counts and observed maxima deliberately retain that sample's scope rather than mixing its arrays with the million-run replay.

## What the old run says about lower32 and lower48

The million inputs contain **999,882 distinct lower32 values**, with only **118 repeated input occurrences**, and **1,000,000 distinct lower48 values**, with **0 repeats**. Placement cache reuse additionally needs identical query bounds. This cohort offers almost no cross-seed lower-word reuse and does not represent deliberately repeated upper-bit siblings.

That does not rule out a useful uncached raw-count prefilter. Such a gate still needs an explicit matched benchmark using the final center and count requirements. Low full64 acceptance does not imply strong lower32 rejection: a raw placement may be common while its biome viability is rare. Historical full-inventory timings are not timings for today's capped native filters, and no new bit-strategy speed claims are inferred here.

## Verification and remaining work

- The complete scan checked every stored candidate's historical Overworld and exact fractional Nether geometry, reconciled all 2,629,026 rows and both original qualification totals, and verified crop histogram totals.
- 96 fresh full64 structure queries across 21 extrema/profile example borders reproduced the recorded positive counts, with zero discrepancies.
- 132 fresh biome-ID queries at those examples' retained in-border witness points reproduced their IDs, with zero discrepancies. Earlier independent checks additionally matched 80 capped structure queries and 176 biome witness points.
- One concrete selective-combination example also passed the current four-Y world-aligned native biome diversity detector.
- The current and historical pinned vendor metadata identities match; this is still native prediction, not actual-game certification.

To complete the missing-category assessment, reuse these same saved full64 seeds and frozen centers, explicitly query every supported structure with counts capped at the proposed requirement, and run full64 biome diversity over the current four-Y lattice with retained witness refinement as needed. Compare direct full64, fused lower32 and fused lower48 on the same cases; deliberately grouped upper-bit siblings are needed to measure cache amortization. Terrain qualification and actual-game verification then determine whether a count-qualified candidate meets the Realm's full requirements.

Evidence: [million replay](runs/count-bits-2026-10-11/million-count-feasibility.json), [fresh example verification](runs/count-bits-2026-10-11/million-count-replay-verification.json), [current biome policy example](runs/count-bits-2026-10-11/million-example-current-biome-grid.json), [lower-word distribution](runs/count-bits-2026-10-11/million-bit-reuse-distribution.json), [original million benchmark](runs/master-implementation-2026-10-10/million/benchmark.json), [original million coverage audit](runs/master-implementation-2026-10-10/million-audit.json).
