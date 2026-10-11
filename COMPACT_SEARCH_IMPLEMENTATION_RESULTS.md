# Compact search implementation results

10 October 2026. Geometry remains **4000×4000 discovery, 1536×1536 Overworld and 896×896 Nether**, with exact fractional Stronghold/8 centers. The native filters, deferred inventory, stable biome sampling, recovery integration and bounded sibling allocator are implemented. **Independent full64 remains the default.** No new million-input or full32 sweep ran.

## Accuracy contract

A first-start observation uses the same pinned placement and viability rules as a complete scan and stops at the first positive. It establishes bounded **predictor presence**, not a total count, full footprint, a remnant crossing the border from an outside start, or actual Bedrock generation. Misses remain PENDING. The complete native start API and `inventory --all-starts --candidate` remain available. Stronghold discovery is unchanged and retains its known recall limitations; the existing Ancient City/Bastion fixture disagreements remain disclosed.

The 64-seed, four-boundary audit made **1,281,088 comparisons with zero differences**, including 5,376 first-witness tests across 21 families (Stronghold stays fully enumerated). All 22 exposed structure families had positive cases. Every one of the **66 IDs marked generating by the pinned model** was observed. The other 28 named IDs are not marked currently generating; this is a catalog distinction, not an absence claim. End predictions use a correct End generator; old End raw-start coordinates were checked separately from corrected viability.

Frozen-lattice qualification, pending reasons and bounds matched across both 1000-input cohorts (3,807 anchor/completion checks; zero differences). Completing 64 sampled inventories reproduced the reference's canonical biome counts, first coordinates and original bonuses. Newly supported buried treasure deliberately contributes its configured bonus. 95,256 point comparisons matched at 1/4/18 native threads. The final End optimization added 201,870 scalar/batch comparisons against the saved correct pre-optimization End adapter, with zero differences.

Scoring inventory COMPLETE means predictor family presence and a complete **defined canonical biome sample**. Individual first-witness records still say remaining starts are unqueried. Supplemental witnesses and refined points have separate provenance and never inflate canonical frequency counts. No actual-world or exhaustive biome coverage claim is made. Monster rooms, End gateways and terrain/decorator features (ravines, lava lakes, geodes and desert wells) lack a reviewed bounded adapter and remain explicitly unsupported.

## Implemented changes

- Mineshaft first-witness API with exact +8 chunk-center bounds and reference RNG; complete scans use an exact portable four-lane MT kernel with scalar fallback.
- Other regional families use first viable starts when once-per-family presence suffices. Shared Fortress/Bastion placement avoids duplicated complementary draws. Audited regular-region halos are trimmed; Stronghold halos remain.
- Wooded eligibility visits dispersed 16-point batches and stops at two families. Exact full-seed point caching, world-aligned grids, retained in-border witnesses and bounded 128-point refinement prevent the known moving-border witness loss. NULL climate hints preserve biome tie behavior.
- Correct End generator and End biome-name classes; dense End queries share one bounded height map. Supplemental Nether/End inventories stop when all active model classes have witnesses, retaining unresolved misses.
- Transactional inventory tasks have fenced leases, recovery and atomic patches. Partial scores retain uncertainty. Terrain and final verification complete scoring inventories before use; generation-free rescoring and exports preserve partial status.
- Persistence avoids repeated whole-batch JSON decoding/encoding and streams a versioned content digest. Old digest/checkpoint semantics remain guarded.
- Native lower32 presence, capped-score and complete modes have separate contracts. Batched raw selection and a versioned exploration permutation remove per-row Python ranking work. Geometry ranking remains experimental; adaptive siblings use durable 1/4/16 rounds and an exploration reserve. Canonical full64 manifests and actual spawned-worker resume are tested.

## Persisted throughput

Three timing trials per row. Reference and frozen-lattice eligibility trials were counterbalanced on identical manifests. Each cohort has 1000 distinct full64 inputs; timing repeats add evaluations, not new independent seeds. Baseline timing includes process startup and SQLite persistence, and excludes deferred inventory, terrain and BDS.

| Workload | Inputs/sec median | Worker CPU sec/1000 | Biome points | Predicted anchors | Distinct qualifying seeds | Disk MiB |
|---|---:|---:|---:|---:|---:|---:|
| final-reference-border-tuning | 407.1 | 7.560 | 209,088 | 337 | 281 | 16.48 |
| final-eligibility-border-tuning | 624.2 | 2.357 | 25,806 | 337 | 281 | 18.48 |
| final-eligibility-world-tuning | 611.8 | 2.681 | 30,167 | 335 | 279 | 18.70 |
| final-reference-border-holdout | 402.1 | 7.693 | 213,120 | 359 | 285 | 16.91 |
| final-eligibility-border-holdout | 614.3 | 2.201 | 17,727 | 359 | 285 | 18.71 |
| final-eligibility-world-holdout | 603.0 | 2.394 | 19,623 | 359 | 285 | 18.77 |
| final-complete-border | 377.7 | 12.279 | 208,900 | 337 | 281 | 29.24 |
| final-schedule-9x4 | 596.5 | 1.930 | 30,167 | 335 | 279 | 18.70 |
| final-schedule-2x18 | 325.9 | 1.793 | 30,167 | 335 | 279 | 18.68 |

The complete profile includes newly supported buried-treasure enumeration and fuller sampling provenance; it measured 378 inputs/sec and did not outperform the old complete reference. First-witness speedups do not make exhaustive inventory free. The active world-grid holdout is approximately 1.50× the reference; the exact frozen-lattice pass is the one that met the ≥1.5× decision-preserving gate.

Exact-contract persisted speedup: **1.53× tuning, 1.53× holdout**. The ≥1.5× gate is met. Active world-grid/refinement changes are separately versioned: 6 tuning and 2 holdout anchors changed qualification; details are in completion-verification.json. The schedule with the best bounded wall throughput remains the selected default; 30×1 avoids multiplying process/native thread counts beyond 36.

The older million-input result, 173.37 inputs/sec, used 5000/2688/1024 geometry and is not the denominator of this compact optimization speedup. These final measurements are bounded pilots, not a new massive benchmark.

### Filtering stages

Rates below are calls divided by summed worker service seconds on the median active holdout trial. They describe serial service work, not additional independent seeds/sec at each gate. Later stages receive only surviving anchors.

| Stage | Calls | Summed worker sec | Calls/service sec |
|---|---:|---:|---:|
| stronghold | 1000 | 0.4215 | 2,372 |
| initial_fortress | 1000 | 0.0376 | 26,604 |
| final_nether_pair | 1908 | 0.0974 | 19,590 |
| ancient_city | 1243 | 0.2468 | 5,036 |
| village | 381 | 0.0387 | 9,839 |
| trial_chamber | 370 | 0.0137 | 27,025 |
| mineshaft | 370 | 0.0556 | 6,660 |
| wooded_biomes | 370 | 0.9923 | 373 |

Expanded scoring inventory (22 supported families plus unsupported monster-room record and supplemental dimensions): sampled median **14.34 ms/anchor**, CPU 14.34 ms/anchor, separately paid after eligibility. It is a sample, not all deferred tasks completed. The durable terrain follow-up completed 48 inventory tasks for 24 sampled anchors. Deferred cost has not vanished; completing every pending anchor would add work. Peak sampled process-tree RSS was 1.54 GiB, plus the configured 8 GiB Docker reserve, below the 25/30 GiB target/ceiling. RSS may double-count shared pages.

## Structure compute audit

Median milliseconds in the 1536-sized control square, 64 seeds including negatives. Reference is a direct old C call; current full/witness values include Python wrapper overhead, so ratios are local scan measurements rather than pipeline speedups. End comparison is raw starts versus corrected viable scans, not an old viable-scan speed ratio.

| Family | Reference full ms | Current full ms | First witness ms |
|---|---:|---:|---:|
| trial_chamber | 0.0849 | 0.1086 | 0.0194 |
| stronghold | 0.2654 | 0.2897 | unchanged full enumeration |
| mineshaft | 6.0112 | 3.3139 | 0.1262 |
| ancient_city | 0.1843 | 0.1816 | 0.1403 |
| village | 0.1198 | 0.1188 | 0.0545 |
| ruined_portal | 0.0245 | 0.0258 | 0.0089 |
| shipwreck | 1.0701 | 1.1516 | 0.3309 |
| monument | 0.1199 | 0.1271 | 0.1010 |
| outpost | 0.0265 | 0.0277 | 0.0149 |
| fortress | 0.0276 | 0.0255 | 0.0090 |
| bastion | 0.0381 | 0.0391 | 0.0095 |
| desert_pyramid | 0.0871 | 0.0845 | 0.0686 |
| jungle_temple | 0.0893 | 0.0864 | 0.0676 |
| swamp_hut | 0.0890 | 0.0850 | 0.0694 |
| igloo | 0.0900 | 0.0865 | 0.0683 |
| ocean_ruin | 0.2409 | 0.2367 | 0.0615 |
| mansion | 0.3264 | 0.3252 | 0.3110 |
| buried_treasure | 3.8895 | 3.9081 | 0.2721 |
| trail_ruins | 0.0668 | 0.0746 | 0.0457 |
| abandoned_camp | 0.0460 | 0.0599 | 0.0249 |
| ruined_portal_nether | 0.0246 | 0.0332 | 0.0059 |
| end_city | 0.0431 | 0.0938 | 0.0301 |

Mineshaft fell from 6.01 ms to 0.126 ms (~48×) in this control; complete vector scans took 3.31 ms (~1.81×). Buried treasure was another major outlier (3.91→0.272 ms, ~14×): dense candidate regions and repeated biome checks caused the cost. Shipwrecks (1.15→0.331 ms, ~3.5×) and ocean ruins (0.237→0.061 ms, ~3.9×) also benefited. Shipwreck/monument viability retains its necessary nearby-biome/structure tests. Rare negative mansions gained little; accuracy checks were not removed.

OW biome classes share climate/noise work rather than having a separate expensive algorithm per biome. Most scalar OW calls were about 8 μs. End scalar calls were a separate outlier, about 17–35 μs, because of repeated height maps; the final dense 3969-point End batch was **6.7× faster**. Minimal supplemental witnesses further reduce the query count. The pinned End planar Voronoi helper is preserved exactly; the Overworld 3D nearest-cell rule must not replace it.

## Lower32 / upper32 result

The exact mode benchmark checked 4,718,592 layout-mode comparisons over 262,144 distinct dispersed layouts, at 18 and 36 threads, three counterbalanced trials. Complete counts equal reference; capped values equal min(count,32); presence equals count>0. **3.895%** failed the necessary predicate. The original expectation of 99.9% lossless rejection is not supported by this geometry.

| Mode / implementation | Layouts/sec | Full32 forecast min |
|---|---:|---:|
| Native reference, 36 threads | 49,966 | 1432.6 |
| Native complete, 36 threads | 73,364 | 975.7 |
| Native capped, 36 threads | 348,692 | 205.3 |
| Native presence, 36 threads | 3,006,603 | 23.8 |
| Old persisted presence selection | 143,794 | 497.8 |
| Old persisted capped selection | 104,165 | 687.2 |
| Final persisted presence selection | 1,442,378 | 49.6 |
| Final persisted capped selection | 299,081 | 239.3 |

Forecasts extrapolate bounded measurements and exclude full64 siblings, inventory, terrain and BDS. The 45-minute target needs 1.591 million layouts/sec end to end. Native presence passed that compute rate; the final persisted presence median forecast of 49.6 minutes still **misses the 45-minute target**. Capped ranking remains far slower. Batched selection improved persisted presence about 10× and capped ranking about 2.9×. These forecasts do not justify a full32 ranking sweep.

Village raw presence is guaranteed at every permitted center at widths ≥944; Ancient City at ≥624. Both are universal at 1536, so their old capped ranking contributes a constant 64. Fortress/Bastion placements are complementary and common in the envelope; mere presence does not prove co-location at an actual Stronghold. Counts cannot resolve full64 biome viability, wooded families, Trial placement, Stronghold recall or terrain. Upper32 siblings change those unresolved properties, so a promising low32 is a family of possibilities rather than a known good world. Mineshaft starts are common as well; adding an expensive raw Mineshaft veto offers little selectivity.

The four-arm experiment used two disjoint 4096-layout pools, three allocation keys and at most 256 selected layouts / 4096 full64 inputs per arm. It performed 34,110 evaluations of 30,231 distinct full64 seeds. Adaptive rounds used about 1400 inputs/arm and did not force expenditure of the maximum. Entire raw/feature CPU was charged to each ranked arm/key without amortization. CPU prefixes apportion parent work per input; they are analytical budget truncations of completed bounded runs, not live CPU stops.

| Held-out allocation key | Uniform / independent anchors | Legacy / independent anchors | Geometry / independent anchors |
|---|---:|---:|---:|
| allocation-0 | 0.895× | 0.844× | 0.000× |
| allocation-1 | 0.887× | 0.678× | 0.000× |
| allocation-2 | 0.867× | 0.717× | 0.000× |

These are matched measured CPU-prefix yield ratios. Geometry feature construction alone exhausted the smallest holdout CPU budgets, hence zero evaluated siblings at those prefixes; it did find richer layouts when more CPU was spent. The layout-cluster bootstrap intervals and complete yield curves are in selection/experiment.json. No arm met the ≥20% heldout advantage with an interval excluding no advantage. More reuse could amortize feature cost, but that benefit has not been demonstrated. Independent full64 is retained.

All four arms received the same two-anchor/eight-refinement V1/V2 budget for each of three heldout keys (24 anchors total). Counts below are distinct anchors with any predicted geometry pass, not verified formations; many durable refinement tasks remain pending.

| Arm | Sampled anchors | Anchors with V1 geometry pass | Anchors with V2 geometry pass |
|---|---:|---:|---:|
| independent | 6 | 1 | 3 |
| geometry | 6 | 1 | 3 |
| uniform | 6 | 1 | 1 |
| legacy | 6 | 0 | 0 |

This sample cannot demonstrate terrain noninferiority or verified-world advantage. No new BDS worlds were generated: the CPU adoption gate failed and no fully verified nomination was established. Generated-world advantage remains unmeasured. The deliberately interrupted serial follow-up is retained separately and excluded from the matched sample.

## Biomes observed

Names below are pinned-predictor IDs observed in the dense surface/cave-layer/dimension audit. End classes are internal model names rather than certified Bedrock biome strings.

**Overworld (56):** badlands, bamboo_jungle, beach, birch_forest, cherry_grove, cold_ocean, dappled_forest, dark_forest, deep_cold_ocean, deep_dark, deep_frozen_ocean, deep_lukewarm_ocean, deep_ocean, desert, dripstone_caves, eroded_badlands, flower_forest, forest, frozen_ocean, frozen_peaks, frozen_river, grove, ice_spikes, jagged_peaks, jungle, lukewarm_ocean, lush_caves, mangrove_swamp, meadow, mushroom_fields, ocean, old_growth_birch_forest, old_growth_pine_taiga, old_growth_spruce_taiga, pale_garden, plains, river, savanna, savanna_plateau, snowy_beach, snowy_plains, snowy_slopes, snowy_taiga, sparse_jungle, stony_peaks, stony_shore, sulfur_caves, sunflower_plains, swamp, taiga, warm_ocean, windswept_forest, windswept_gravelly_hills, windswept_hills, windswept_savanna, wooded_badlands.

**Nether (5):** basalt_deltas, crimson_forest, nether_wastes, soul_sand_valley, warped_forest.

**End (5):** end_barrens, end_highlands, end_midlands, small_end_islands, the_end.

## Verification and evidence

Final verification: **658 tests passed in 98.87 seconds**, native ASan/UBSan PASS, exact decision/completion and End/thread comparisons PASS, doctor and CLI baseline/inventory/full-start/rescore/export/raw/sibling/adaptive smoke checks PASS, and git diff --check PASS. Frozen source/native/config integrity checked 113 unchanged files; 11 linker intermediate .o files were intentionally not archived. Timing manifests retain their measured identities. The later explicit Stronghold full-start audit fix was exercised by the final tests and fresh CLI run; the cheap eligibility path is unchanged. Sanitizer checks use the serial path; Apple leak detection is disabled and the run is not an exhaustive race/leak proof. New computational identities reject incompatible resumes. Historical runs and the frozen reference are preserved.

- [Detailed audit](runs/compact-implementation-2026-10-10/detection-audit.json)
- [Completion and sampling changes](runs/compact-implementation-2026-10-10/completion-verification.json)
- [Raw-mode benchmark](runs/compact-implementation-2026-10-10/raw-benchmark.json)
- [Final persisted selection](runs/compact-implementation-2026-10-10/raw-selection-final.json)
- [Four-arm selection experiment](runs/compact-implementation-2026-10-10/selection/experiment.json)
- [Inventory / terrain follow-up](runs/compact-implementation-2026-10-10/inventory-terrain-followup.json)
- [Native safety](runs/compact-implementation-2026-10-10/safety/report.json)
- [End parity](runs/compact-implementation-2026-10-10/end-parity.json)
- [Final tests](runs/compact-implementation-2026-10-10/full-tests-final.log)

- [CLI checks](runs/compact-implementation-2026-10-10/cli-final.json)
- [Reference integrity](runs/compact-implementation-2026-10-10/reference-integrity.json)
