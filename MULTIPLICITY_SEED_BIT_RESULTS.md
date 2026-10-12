# Structure multiplicity, biome diversity and seed-bit pilots

Completed 11 October 2026. All measurements are serial on this host; they are pilot results, not a new massive production benchmark.

## Decision

Requiring **two or more distinct viable structure starts** makes a fused lower32 placement gate useful for the expanded combination's conditional count stage. At two of every Overworld/Nether structure, cached lower32 reduces count-stage time by 40.1%; lower48 gives practically the same result. Requiring only one of each makes both gates slower. Stronghold discovery and context preparation erase most of the count-stage gain, so there is no demonstrated large improvement in complete seed-search throughput.

For biomes, the requested multiplicity is **different active biome IDs within a family**. A repeated patch of Forest counts once. Use the full64 seed for every biome query. Native early stopping can be much faster for readily satisfied diversity goals, but a broad rare-family conjunction can be slower than batched inventory because it must inspect essentially the whole grid.

These pilots do not change production structure requirements, adopted borders, search policy or the production native extension. No combination requiring every structure produced a fully viable layout in this sample; this prevents a claim about time to a qualifying all-structure world.

## Geometry, cohorts and comparison

Discovery is 4000×4000. Each full64 seed chooses its first sorted discovered Stronghold before screening. Deployment is 1536×1536 Overworld at that anchor and 896×896 Nether at the exact fractional anchor/8. Coordinates use the existing half-open border contract converted to inclusive native bounds. The End-city control uses a diagnostic 1536-square window in its own dimension; no End border is adopted. Production's evaluation of all eligible anchors remains unchanged.

Structure counts use 436 tuning and 460 held-out selected-center layouts: 896 full64 inputs in 256 disjoint lower32 groups. Another 128 of the original 1024 inputs had no discovered anchor and remain unresolved. A separate discovery-included replay uses the first 128 full64 inputs per cohort, including unresolved inputs. Biome tests use 24 layouts per cohort and are a small correlated-sibling pilot, not 48 independently drawn lower-bit groups.

The five arms are: direct full64 viable-start counting; fused lower32 raw capacity plus fresh full64 viability; fused lower48; and those two fused arms with a bounded raw-prefix cache. Counts stop at the required number. A failed threshold need not return an exact partial inventory. Raw prefixes retain coordinates and the enumeration cursor, so viability continues without redoing placement. Cache reset, construction and misses are charged. Keys include the proved seed bits, structure, exact bounds and threshold; cached biome or viability answers are never shared between full64 seeds.

The direct baseline already uses cheap placement internally. Merely masking a seed does not intrinsically make the RNG faster. Stronghold count queries are a special case: count two or more requires full64 bounded enumeration and deduplication; a one-Stronghold combination can reuse its already selected anchor. Mineshaft uses its specialized count-capped vector kernel. The four shared feature families require at least 4×N distinct raw slots, with separately checked disjoint viable-biome sets.

Orders were learned on tuning and frozen for holdout. Structure combinations use five counterbalanced trials with four passes per trial, each with an empty paid cache. Biome combinations and discovery-included replay use three counterbalanced trials. Individual-family microsecond means are exploratory single passes; interpret them as cost indicators, not robust timing rankings.

## All 21 supported Overworld/Nether structures together

Conditional layouts/second excludes Stronghold discovery, native context creation, terrain and biome inventory. It includes raw gating and full64 viable-count checks reached after rejection. Both bit modes have identical raw rejection in these cohorts.

| N each | Direct64 | Fused32 | Fused48 | Cached32 | Cached48 | Raw rejection | Viable passes /460 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 25,511 | 16,082 | 15,935 | 18,825 | 18,620 | 28.48% | 0 |
| 2 | 71,880 | 91,839 | 90,403 | 119,910 | 118,719 | 95.65% | 0 |
| 3 | 119,489 | 188,113 | 188,456 | 242,751 | 242,101 | 100.00% | 0 |
| 4 | 126,727 | 205,839 | 205,716 | 262,868 | 261,300 | 100.00% | 0 |

At N=1 the cached32 arm takes 35.5% more time; at N=2 it takes 40.1% less (1.67× throughput); at N=3 and N=4 it takes 50.8% and 51.8% less. Uncached fused32 at N=2 takes 21.7% less time. Tuning raw rejection at N=1/2/3/4 is 36.70%/96.79%/100%/100%, supporting the direction of the conditional-stage result. Observed 100% rejection is a finite-sample result, not proof of universal impossibility or a guaranteed 99.9% rejection rate.

Lower48 does not add raw rejections because all layouts already have at least four raw Trial Chamber, Trail Ruin and Abandoned Camp placements. Those three LCG families require lower48 for correct placement, but their final biome eligibility still uses full64. In 64 dependency controls per LCG family, naively truncating to lower32 changed every raw layout; lower48 matched every one. The safe lower32 arm simply leaves those families on the full-seed path.

The all-16-MT and all-22-with-End profiles are also in the detailed combination CSV. At N=2 cached32 count-stage time falls 37.5% for all-16-MT and about 38.9% for all-22. Neither profile yielded a qualifying held-out layout. Every all-structure profile also had zero fully viable tuning layouts.

## Include discovery before interpreting throughput

| N each | Direct64 input seeds/s | Fused32 | Fused48 | Cached32 | Cached48 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1,693 | 1,641 | 1,671 | 1,594 | 1,601 |
| 2 | 1,733 | 1,727 | 1,753 | 1,815 | 1,728 |
| 3 | 1,855 | 1,821 | 1,852 | 1,889 | 1,882 |
| 4 | 1,866 | 1,881 | 1,876 | 1,847 | 1,892 |

These figures include full64 Stronghold discovery, both diagnostic contexts, bounds/FFI preparation and count filtering. They exclude terrain, biome inventory, persistence, IPC and actual game generation, and therefore are still not final pipeline throughput. Of 128 holdout inputs, 13 have no discovered center and remain unresolved; all discovered layouts fail the all-21 conjunction. The extra diagnostic context is common to every arm.

Cached32 N=2 is 4.5% faster by elapsed time on this replay, but it is 4.2% slower on tuning. Changes at N=3/4 are roughly 0–2% and change sign across modes/cohorts. Consequently the small replay does not establish a robust overall speedup. In the held-out direct N=2 pass, median discovery is about 45.5ms and setup 15.2ms per 128 inputs, while count plus preparation is about 9.2ms. Optimizing just a few microseconds after selecting a full64 anchor cannot remove those preceding costs. Medians of components need not sum to the total median.

## Current Village / Ancient City / Fortress / Bastion requirements

| N each | Direct64 layouts/s | Fused32 | Cached32 | Raw rejection | Viable passes /460 |
| --- | --- | --- | --- | --- | --- |
| 1 | 9,742 | 9,626 | 9,891 | 25.87% | 82 |
| 2 | 36,718 | 35,482 | 39,494 | 81.74% | 4 |
| 3 | 126,535 | 141,824 | 192,593 | 100.00% | 0 |
| 4 | 129,167 | 148,185 | 198,968 | 100.00% | 0 |

Two each still permits four held-out layouts, and cached32 reduces this conditional stage's time by about 7.0%. Uncached fusion at two each is about 3.5% slower. One each remains approximately neutral for fusion/cache. This is why the all-structure multiplicity finding does not justify inserting a universal lower32 gate into the current search.

## Every exposed structure

Each pass count below is out of 460 full64 holdout layouts. The costs are direct native count queries in microseconds, before selecting an order; Stronghold's individual count-one query includes enumeration rather than using the already known anchor. Raw placement count is necessary but often weak compared with biome viability. See the CSV for raw passes and both fused-arm times at all four thresholds.

| Structure | Placement bits | Viable N1 | N2 | N3 | N4 | Direct N1 µs | Direct N4 µs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trial_chamber | 48 | 460 | 460 | 460 | 460 | 17.5 | 31.5 |
| stronghold | 64 | 460 | 65 | 1 | 0 | 230.1 | 220.1 |
| mineshaft | 32 | 460 | 460 | 460 | 460 | 103.8 | 382.7 |
| ancient_city | 32 | 129 | 61 | 23 | 14 | 133.9 | 129.6 |
| village | 32 | 418 | 357 | 279 | 162 | 57.8 | 119.9 |
| ruined_portal | 32 | 460 | 460 | 460 | 460 | 7.5 | 8.5 |
| shipwreck | 32 | 345 | 257 | 188 | 134 | 307.2 | 742.4 |
| monument | 32 | 133 | 55 | 22 | 9 | 292.4 | 429.8 |
| outpost | 32 | 210 | 31 | 4 | 0 | 17.9 | 13.6 |
| fortress | 32 | 368 | 140 | 26 | 2 | 8.9 | 9.5 |
| bastion | 32 | 405 | 266 | 125 | 33 | 10.6 | 11.3 |
| desert_pyramid | 32 | 59 | 38 | 28 | 14 | 69.9 | 59.6 |
| jungle_temple | 32 | 50 | 7 | 4 | 0 | 60.5 | 59.7 |
| swamp_hut | 32 | 28 | 4 | 2 | 0 | 62.0 | 59.5 |
| igloo | 32 | 105 | 81 | 50 | 37 | 55.5 | 58.4 |
| ocean_ruin | 32 | 395 | 341 | 306 | 263 | 98.0 | 188.1 |
| mansion | 32 | 3 | 0 | 0 | 0 | 260.5 | 249.9 |
| buried_treasure | 32 | 445 | 436 | 431 | 412 | 675.1 | 1324.3 |
| trail_ruins | 48 | 237 | 130 | 63 | 25 | 43.3 | 45.9 |
| abandoned_camp | 48 | 415 | 329 | 218 | 112 | 24.4 | 38.2 |
| ruined_portal_nether | 32 | 460 | 460 | 460 | 449 | 7.3 | 8.3 |
| end_city | 32 | 460 | 459 | 452 | 443 | 129.7 | 256.1 |

Mansion, Outpost and Fortress raw scarcity drives the count-two gate. Mansion raw passes fall from 451 at N1 to 197 at N2, 42 at N3 and zero at N4; Outpost from 449 to 184/40/7; Fortress from 368 to 140/26/2. In contrast, Ancient City has at least four raw positions in every layout, but only 14 have four viable starts. Its rarity is full64 biome viability, so lower32 cannot recognize that rarity.

Buried Treasure (675µs at N1; 1324µs at N4), Shipwreck (307/742µs) and Monument (292/430µs) are the largest remaining regional count costs. Their raw capacity passes every layout through N4, so adding a raw gate does not remove their biome work. Count-capping avoids complete inventories on successful requirements, while negative cases still need all relevant candidates. Mineshaft scales from 104 to 383µs for N1→N4 and already uses its specialized lower32 kernel; adding another raw pass provides no selectivity. Defer expensive families behind cheap selective checks, retain cursors/prefixes and batch/reuse exact full64 biome samples where profiling shows overlap. These latter production improvements are proposed, not measured implementations in this pilot.

## Different biome variants within each family

All 66 active pinned-predictor biome IDs were observed somewhere across the 48 layouts. The existing canonical grouping partitions them into 29 families, including singleton cave, Nether and End groups. No sampled layout contains all 66 IDs or every family's maximum diversity. A Nether/End group with one active ID cannot have two distinct variants under this grouping; a broader user-defined grouping would be a separate requirement.

The reference grid is world-aligned at 64-block spacing. Overworld samples Y=63,-48,0,160 (2304 points/layout), Nether Y=33 (196), and End Y=63 (576). Early stopping sees the identical point set in dispersed order. Unseen biomes outside this defined sampling lattice remain unknown; sample absence is not an exhaustive actual-world rejection.

| Family | Active variants | N1 /24 | N2 /24 | N3 /24 | N4 /24 | All variants /24 |
| --- | --- | --- | --- | --- | --- | --- |
| ocean | 9 | 24 | 23 | 18 | 13 | 0 |
| plains_meadow | 3 | 24 | 18 | 6 | impossible | 6 |
| desert | 1 | 4 | impossible | impossible | impossible | 4 |
| mountains | 6 | 13 | 8 | 4 | 1 | 0 |
| forest | 6 | 24 | 21 | 20 | 13 | 0 |
| taiga | 4 | 11 | 9 | 6 | 2 | 2 |
| swamp | 2 | 2 | 2 | impossible | impossible | 2 |
| rivers_shores | 5 | 24 | 24 | 17 | 5 | 2 |
| nether_wastes | 1 | 24 | impossible | impossible | impossible | 24 |
| the_end | 1 | 9 | impossible | impossible | impossible | 9 |
| snowy_ice | 3 | 9 | 4 | 0 | impossible | 0 |
| mushroom | 1 | 1 | impossible | impossible | impossible | 1 |
| jungle | 3 | 13 | 10 | 7 | impossible | 7 |
| dark_pale | 2 | 11 | 4 | impossible | impossible | 4 |
| savanna | 3 | 15 | 8 | 0 | impossible | 0 |
| badlands | 3 | 4 | 2 | 1 | impossible | 1 |
| small_end_islands | 1 | 24 | impossible | impossible | impossible | 24 |
| end_midlands | 1 | 24 | impossible | impossible | impossible | 24 |
| end_highlands | 1 | 24 | impossible | impossible | impossible | 24 |
| end_barrens | 1 | 24 | impossible | impossible | impossible | 24 |
| soul_sand_valley | 1 | 24 | impossible | impossible | impossible | 24 |
| crimson_forest | 1 | 24 | impossible | impossible | impossible | 24 |
| warped_forest | 1 | 24 | impossible | impossible | impossible | 24 |
| basalt_deltas | 1 | 24 | impossible | impossible | impossible | 24 |
| dripstone_caves | 1 | 23 | impossible | impossible | impossible | 23 |
| lush_caves | 1 | 23 | impossible | impossible | impossible | 23 |
| deep_dark | 1 | 15 | impossible | impossible | impossible | 15 |
| cherry | 1 | 6 | impossible | impossible | impossible | 6 |
| sulfur_caves | 1 | 21 | impossible | impossible | impossible | 21 |

Forest has six active variants: Forest, Birch Forest, Windswept Forest, Flower Forest, Old Growth Birch Forest and Dappled Forest. Taiga has four, Jungle three, Dark/Pale two and Cherry one. Requests above a family's active capacity fail before querying terrain. That is exact catalog impossibility, not a lower32/lower48 achievement. Counts should be configured independently per family, rather than requiring four everywhere.

| Full64 diversity goal | Passes /24 | Full inventory layouts/s | Native stop layouts/s | Elapsed time change |
| --- | --- | --- | --- | --- |
| forest_variants N=1 | 24 | 74.6 | 18,477.1 | -99.6% |
| forest_variants N=2 | 21 | 73.7 | 458.4 | -83.9% |
| forest_variants N=3 | 20 | 74.5 | 322.0 | -76.9% |
| forest_variants N=4 | 13 | 74.5 | 126.7 | -41.2% |
| forest_and_taiga N=1 | 11 | 73.8 | 117.0 | -36.9% |
| forest_and_taiga N=2 | 8 | 74.4 | 96.4 | -22.8% |
| forest_and_taiga N=3 | 5 | 74.7 | 80.0 | -6.7% |
| forest_and_taiga N=4 | 0 | 73.2 | 62.1 | +17.7% |
| forest_taiga_jungle N=1 | 3 | 73.5 | 70.4 | +4.5% |
| forest_taiga_jungle N=2 | 0 | 74.4 | 63.9 | +16.5% |
| forest_taiga_jungle N=3 | 0 | 74.5 | 64.3 | +16.0% |
| five_wooded_families N=1 | 0 | 74.9 | 64.0 | +17.1% |

Increasing diversity makes full64 queries more selective but typically requires more samples: the forest-only native means rise from 6.5 queried points at N1 to 315.9/470.9/1169.9 at N2/3/4. Two forest variants stop early and save 83.9% of inventory time; four save 41.2%. Four each of Forest+Taiga scans all 2304 points on every held-out layout and costs 17.7% more than inventory. Three-family N2 likewise scans the whole grid and costs 16.5% more. The current native combination loops over family masks per point, adding overhead when no early success occurs. A future disjoint-ID→family lookup with one shared seen-ID bitset and batched full64 sampling can reduce that overhead; it must be measured before adoption.

## Accuracy: safe bits versus truncating biome seeds

Safe lower32/lower48 modes never truncate biome generation, Stronghold selection or terrain seeds. All count predicates and tested raw layouts match the defined full64 reference. The intentionally unsafe truncation controls change biome IDs and eligibility:

| Dimension | Lower32 point-ID disagreement | Lower48 disagreement | Full64 inventory points/s |
| --- | --- | --- | --- |
| Overworld | 95.56% | 67.59% | 171,072 |
| Nether | 1.28% | 0.83% | 1,733,551 |
| End | 20.93% | 14.47% | 227,457 |

For two forest variants, full64 accepts 21/24 layouts. Truncated lower32 wrongly rejects 9 of those and wrongly accepts 2 others; truncated lower48 wrongly rejects 2 and wrongly accepts 1. With four forest variants, full64 accepts 13/24, but lower32 wrongly rejects 10 and accepts 1 invalid layout, while lower48 wrongly rejects 4 and accepts 4 invalid layouts. More rarity does not make a wrong truncated biome generator safe.

The high16-sibling control tested 32 lower48 groups and four high16 choices per group, discovering each full64 anchor independently. It obtained 114 centers (52 tuning/62 holdout), with 18/17 repeated exact-border queries. All 342 LCG raw-layout comparisons matched lower48. Even with that real reuse, lower48 cache time changes for the three-LCG combination on holdout were +0.06%/+0.11%/−0.16%/−0.33% at N1/2/3/4, with zero raw rejections through N4. Correct lower48 grouping exists, but it has no demonstrated useful acceleration here.

Ancillary structure-in-biome-family counts also cover all structures and all canonical groups. Family-qualified native queries were audited at N=1,2,4 on 24 layouts/cohort, including observed families and an absent-family control. They use the biome at the logged start column and declared Y: generally OW63, City−48, Mineshaft/Trial Chamber0, Nether33, End63. They do not certify a structure's actual generated pieces or surface biome. Additional family-qualified rarity still needs full64 biome queries; it cannot be assumed to improve raw lower-bit rejection.

## Verification and practical next changes

There are 371,240 passing safe comparison events across the structure, biome, sibling and discovery replays, with zero differences from their full64 predictor references. These are repeated check events, not that many independent seeds. The separate unsafe controls contain 295,296 point comparisons. Production native hashes, both private binaries, source inputs, frozen parent cohorts, script identities and the 66-ID partition passed the completion audit. Focused native/count/geometry tests passed: 34 tests.

Predictor parity does not certify the actual game. Existing Stronghold recall and Ancient City/Bastion game-validation gaps remain, including the pinned MC_26_50 model versus the configured 26.52 target. The pilot never replaces unresolved discovery or unsampled biome evidence with a claimed actual-world absence.

1. Add per-structure required counts and per-family required distinct biome IDs as separate configuration concepts. Validate requested diversity against each active catalog capacity and preserve evidence coordinates/IDs.
2. Promote native count-capped detection with retained prefixes/cursors; enable a fused raw gate only for combinations/thresholds whose paid timing repays it. A raw pass remains necessary evidence, followed by full64 viability.
3. Keep the raw cache bounded and keyed by version, proved bits, family, exact border and cap. Reuse only placement. Avoid exhaustive enumeration of upper32/high16 siblings without an equal-CPU useful-yield experiment.
4. Use full64 distinct-ID early stopping for frequently satisfied diversity goals; keep shared batched inventory for broad rare goals until an optimized disjoint-family native path beats it on holdout. Retain unknown states outside sampled evidence.
5. Profile and reduce paid full64 discovery/context/border-preparation costs before claiming a major complete-search gain. Re-run on more independent groups and actual positive worlds with the production all-anchor policy and terrain/verification stages included.

## Detailed artifacts

- [Every structure at every count and bit mode](runs/count-bits-2026-10-11/structure-counts.csv)
- [All combination/cohort/mode timings](runs/count-bits-2026-10-11/structure-combinations.csv)
- [All 29 families, capacities, N1–4 diversity, query costs and truncation errors](runs/count-bits-2026-10-11/biome-variant-counts.csv)
- [All 66 individual biome IDs, presence and costs](runs/count-bits-2026-10-11/biome-ids.csv)
- [Every structure × biome-family count](runs/count-bits-2026-10-11/structure-family-counts.csv)
- [Family-qualified native query timings](runs/count-bits-2026-10-11/structure-family-query-times.csv)
- [Discovery-included repeated trials](runs/count-bits-2026-10-11/discovery-included-report.json)
- [Completion audit and frozen report hashes](runs/count-bits-2026-10-11/completion-audit.json)

Reproduce native builds with `.venv/bin/python scripts/build_count_pilot.py` and `.venv/bin/python scripts/build_biome_diversity_pilot.py`; run the pilots with `.venv/bin/python -m scripts.pilot_count_bits_structures`, then `scripts.pilot_count_bits_biomes`, `scripts.pilot_biome_variant_counts`, `scripts.pilot_lower48_siblings` and `scripts.pilot_count_bits_discovery` using the same `-m` invocation. The frozen predecessor center files are required. Generate these tables with `.venv/bin/python -m scripts.report_count_bits`. Pilot modules intentionally depend on their private build identities.
