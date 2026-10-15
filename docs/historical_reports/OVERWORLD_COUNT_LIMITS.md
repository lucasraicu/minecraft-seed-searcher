# Overworld structure and biome count ceilings

Our border is 1536×1536 blocks, or 2,359,296 square blocks. These are geometric placement or predictor-catalog ceilings, not proved achievable viable maxima. Independent ceilings cannot be summed into a promised world.

For a regular structure with region size S chunks and R allowed chunk offsets per axis, one axis has at most ceil((96 + R - 1)/S) intersecting placement supports. Squaring gives the placement ceiling. All chunk-offset phases were enumerated to verify this arithmetic. This counts start origins inside the border; whole structures may extend outside.

| Structure | Region width (blocks) | Placement/model ceiling | Largest raw in 896 layouts | Largest viable in 896 layouts |
| --- | --- | --- | --- | --- |
| trial_chamber | 544 | 16 | 11 | 11 |
| stronghold | 3200 | 4 | 3 | 3 |
| mineshaft | 16 | 9,216 | 55 | 55 |
| ancient_city | 384 | 25 | 21 | 7 |
| village | 544 | 16 | 11 | 9 |
| ruined_portal | 640 | 9 | 9 | 9 |
| shipwreck | 384 | 25 | 21 | 15 |
| monument | 512 | 16 | 12 | 6 |
| outpost | 1280 | 4 | 4 | 4 |
| desert_pyramid | 512 | 16 | 12 | 8 |
| jungle_temple | 512 | 16 | 12 | 4 |
| swamp_hut | 512 | 16 | 12 | 3 |
| igloo | 512 | 16 | 12 | 8 |
| ocean_ruin | 320 | 36 | 27 | 24 |
| mansion | 1280 | 4 | 3 | 1 |
| buried_treasure | 64 | 625 | 586 | 59 |
| trail_ruins | 544 | 16 | 11 | 8 |
| abandoned_camp | 592 | 16 | 10 | 9 |

Mineshaft’s 9,216 is only the number of possible starting-chunk slots. Its rarity prevents treating that as a realistic seed count. Stronghold’s four is the current predictor’s enumeration ceiling (at most one static-regional start plus three village-associated entries), not a certified actual-game bound; existing recall gaps remain.

Desert Pyramid, Jungle Temple, Swamp Hut and Igloo share placements and disjoint viable-biome sets. Their viable counts sum to at most 16, not 64. Thus an equal count N across all four must satisfy 4N ≤ 16. The sample’s largest shared raw count is 12; that is an observation, not a global bound.

| Overworld biome family | Active-ID ceiling | Largest distinct IDs sampled in 48 layouts |
| --- | --- | --- |
| ocean | 9 | 8 |
| plains_meadow | 3 | 3 |
| desert | 1 | 1 |
| mountains | 6 | 4 |
| forest | 6 | 5 |
| taiga | 4 | 4 |
| swamp | 2 | 2 |
| rivers_shores | 5 | 5 |
| snowy_ice | 3 | 2 |
| mushroom | 1 | 1 |
| jungle | 3 | 3 |
| dark_pale | 2 | 2 |
| savanna | 3 | 3 |
| badlands | 3 | 3 |
| dripstone_caves | 1 | 1 |
| lush_caves | 1 | 1 |
| deep_dark | 1 | 1 |
| cherry | 1 | 1 |
| sulfur_caves | 1 | 1 |

The 19 Overworld families partition 56 active biome IDs. A specific biome ID contributes at most one to ID diversity, regardless of repeated patches. The largest sampled total in one border was 34 distinct Overworld IDs across Y=63,-48,0,160, at 64-block spacing. This is sampled presence, not a maximum for the whole border. All 56 IDs together is the catalog ceiling, not proof that such a seed exists. Multiple connected patches are a different quantity and need a dimensional/connectivity definition.

Evidence: [calculated bounds and source identities](runs/count-bits-2026-10-11/overworld-count-limits.json), [count pilots](MULTIPLICITY_SEED_BIT_RESULTS.md).
