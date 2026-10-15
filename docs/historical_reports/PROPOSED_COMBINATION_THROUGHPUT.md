# Proposed combination stage throughput

Fresh matched single-process pilots on the existing cohorts; no production requirements or native binaries were changed. Rates use held-out medians and hourly capacity is rate × 3,600, not a sustained-hour measurement. Tuning results and all trials are preserved in the JSON.

## Requirements and sampling

Core: one chosen Stronghold, at least 3 Villages, 3 Trial Chambers, 2 Ancient Cities and 5 Mineshafts in 1536×1536; at least one Fortress and one Bastion in 896×896 at exact Stronghold/8. Discovery is 4000×4000. Core biomes require 3 distinct active Forest IDs and 2 distinct active Taiga IDs.

Strict expanded target: all of the above plus one Monument, Mansion, Jungle Temple and Desert Pyramid, plus Desert-ID presence and Jungle-family-ID presence. This treats the previously discussed preferred core counts as hard requirements for the diagnostic only; it does not adopt a new production configuration.

Structures use 436 tuning and 460 holdout first-selected-center layouts. Biomes use the same 24 tuning and 24 holdout layouts as the preceding pilot, with 2304 world-aligned points at Y=63,-48,0,160. These cohorts contain correlated lower-word siblings. They are not independent random million-seed samples. Biome stage timing is unconditional on these small cohorts, not timing only the structure-stage survivors.

## Structure filtering at an already selected center

Five counterbalanced trials, four passes per trial, precreated native contexts and prepared bounds. Raw-cache reset, construction, misses and hits are paid. This excludes discovery, context creation, biome inventory, terrain, IPC, persistence and game verification. All modes use full64 biome viability; lower32 checks only safe raw placement dependencies, with Trial Chamber retained on the full-seed path. Direct detection already uses cheap placement internally.

| Structure target | Mode | Layouts/sec | Projected layouts/hour/process |
| --- | --- | ---: | ---: |
| Core counts | Direct capped viable detection | 6,293.8 | 22,657,551 |
| Core counts | Uncached fused lower32 | 6,225.6 | 22,412,327 |
| Core counts | Paid cached lower32 | 6,348.7 | 22,855,326 |
| Core + Monument/Mansion/two temples | Direct capped viable detection | 14,996.6 | 53,987,644 |
| Core + Monument/Mansion/two temples | Uncached fused lower32 | 13,002.1 | 46,807,687 |
| Core + Monument/Mansion/two temples | Paid cached lower32 | 14,043.6 | 50,557,091 |

Core viable structure positives: 26/460. Expanded: 0/460. Necessary lower32 raw rejection is 25.87% for core and 27.39% for expanded. The expanded combination is faster to reject because cheap selective structure checks stop before later expensive work. It is not producing qualifying worlds at that rate.

The extra lower32 gate has no demonstrated useful speedup for these exact targets. Direct expanded detection is 15.3% faster in throughput than uncached fusion. Cached core improves this isolated stage by less than 1%; discovery-included effects change sign across tuning and holdout. In the old million inputs only 118 additional occurrences reused lower32, and cache keys also require identical bounds, so the sibling-pilot cache rate should not be assumed for a random seed stream.

## Biome filtering: full64 only

Three counterbalanced trials; the independent full64 batched inventory is the oracle. A goal counts distinct IDs within each family, not repeated samples or connected patches.

| Diversity target | Mode | Layouts/sec | Projected layouts/hour/process |
| --- | --- | ---: | ---: |
| Forest 3 / Taiga 2 | Full64 batched inventory | 68.39 | 246,206 |
| Forest 3 / Taiga 2 | Full64 native distinct-ID early stop | 87.30 | 314,263 |
| Forest 3 / Taiga 2 / Desert 1 / Jungle 1 | Full64 batched inventory | 69.28 | 249,405 |
| Forest 3 / Taiga 2 / Desert 1 / Jungle 1 | Full64 native distinct-ID early stop | 59.35 | 213,662 |

Core biome samples positive: 8/24; strict expanded: 0/24. Unseen biomes outside the defined lattice remain unknown. For the expanded rare-family goal, native early stopping reaches essentially the full grid and pays per-family bookkeeping. Batched inventory is about 16.7% faster in throughput. Budget approximately 250,000 layout checks/hour/process for the broad biome step, or 270,000–315,000 for the core Forest/Taiga native goal across the two cohorts, until measured on actual surviving layouts.

Lower32 biome generation is inaccurate: the preceding controls changed 95.56% of sampled Overworld point IDs compared with full64. Lower48 is also unsafe for biome generation. Safe lower-word structure filtering always retains the full64 seed for biome queries.

## Discovery plus structure screening

Three counterbalanced trials on 128 inputs per cohort. These rates include full64 Stronghold discovery, both diagnostic contexts, bound/FFI preparation and structure checks. They exclude biomes, terrain, IPC, persistence and game verification. Missing anchors remain unresolved.

| Target | Mode | Input seeds/sec | Projected input seeds/hour/process |
| --- | --- | ---: | ---: |
| Core counts | full64_direct | 1,379.6 | 4,966,443 |
| Core counts | fused_lower32 | 1,221.7 | 4,398,300 |
| Core counts | cached_lower32 | 1,377.6 | 4,959,322 |
| Strict expanded counts | full64_direct | 1,585.0 | 5,705,949 |
| Strict expanded counts | fused_lower32 | 1,571.3 | 5,656,805 |
| Strict expanded counts | cached_lower32 | 1,530.8 | 5,510,944 |

This makes the distinction visible: tens of millions of prepared layout checks per hour do not become tens of millions of complete input-seed evaluations. Production evaluates its discovered anchors independently; this pilot uses the first selected anchor.

## Sustained whole-machine evidence

The completed million benchmark used 30 workers and achieved **173.37 full64 input seeds/sec**, or **624,115/hour**, including baseline evaluation, multiprocessing and persistence. It used historical 5000/2688/1024 geometry and older detectors. It did not include terrain qualification or actual-game verification. This is our sustained measured baseline search rate, not an estimate of the exact new combination.

No sustained parallel benchmark yet establishes the exact current combination's complete-pipeline rate. Isolated stage rates cannot be multiplied blindly by the worker count or added together. Only surviving layouts reach the biome stage, and all-anchor counts differ from input-seed counts. Use the serial capacities to identify bottlenecks, then benchmark the actual parallel chain and useful qualifying yield before giving a machine-wide forecast.

## Verification

All 118,176 comparison events matched the full64 structure inventories or full64 batch biome reference, with zero differences. These are repeated comparison events, not that many independent seeds. Orders were learned only from tuning, frozen for holdout; the N5 Mineshaft order-cost heuristic uses the saved N4 timing as a proxy, while actual count queries cap at five. Native predictor parity does not certify actual-game generation.

Evidence: [fresh trials and source identities](runs/count-bits-2026-10-11/proposed-combination-throughput.json), [pilot script](scripts/pilot_proposed_combo_throughput.py), [earlier full count/bit results](MULTIPLICITY_SEED_BIT_RESULTS.md), [sustained million benchmark](runs/master-implementation-2026-10-10/million/benchmark.json).
