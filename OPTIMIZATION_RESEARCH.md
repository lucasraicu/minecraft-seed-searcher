# Seed-search optimization research — 7 October 2026

Scope: online speed reports and a read-only audit of the verified Bedrock pipeline. No production code/configuration changes or broad sweep. Existing readiness must remain valid.

## Published workloads and rates

These are authors' reports, not benchmarks rerun on this Mac. A rejected seed often takes only its first filter; seeds per second do not measure the cost of fully analyzing a survivor or the time to find a worthy world.

| Source | Specifications | Reported rate / limitations |
|---|---|---|
| [Seeder](https://www.mcseeder.com/) | Modern 1.18+ 3-D biome search within300 blocks; one core | About12 seeds/s. No detailed hardware or reproducible benchmark provided. Current tool supports Java and Bedrock, but the FAQ does not separate edition-specific performance. |
| [MC-SeedFinder](https://github.com/doublegate/MC-SeedFinder#performance) | Java raw structure-only village within100-block radius | Python82,000 seeds/s, Rust extension2.4million, standalone release14.8million. Machine/query/build-dependent; Bedrock worldgen explicitly unsupported. This is not terrain/island-connectivity validation. |
| [SeedLookout](https://seedlookout.com/blog/why-we-started-seedlookout/) | Java26.3, village within256 of actual predicted spawn, one thread | Native Cubiomes-style465–490/s versus prototype4,390–4,860/s. |
| Same SeedLookout study | Mushroom fields + Stronghold + village near spawn,16 threads | Cubiomes-style2,800/s versus prototype31,000/s. Preliminary short runs on Ryzen7 7840H under30–60% background load, not stable production benchmarks. |
| [Cubiomes Viewer maintainer discussion](https://github.com/Cubitect/cubiomes-viewer/issues/91) | Historical Java1.17 test with village500-square / relative spawn20-square | Maintainer about100,000/s. Reference dependencies and batch size change performance; older broken relative semantics could appear faster. |

No found primary report benchmarks our exact combination: Bedrock26.52, search across±5000 candidate-center axes, three landscape types, exact3008/992 borders, thin-coast/connectivity refinement, full density scoring, structure ambiguity handling and report generation. Broad online claims of millions/s therefore do not show that our equivalent workload should achieve that rate.

Our measured20-input pilot:387.62s end to end,19.38s/input effective throughput with parallelism; individual worker mean96.39s. About184 inputs/hour including two report invocations. This is not matched-world throughput. Coast39.20%, landscape34.09%, preliminary24.56%, structures1.21% of summed worker time. Selectively moving filters can improve rejected-seed cost; accepting dense survivors will remain expensive.

## Genuine bit patterns and their limits

Pinned Bedrock [mt.h](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/mt.h) uses a32-bit seed for region Mersenne Twister initialization. [finders.h](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.h) dispatches per structure between this RNG and Java-style48-bit placement. Its inherited generic48-bit documentation must not override the actual per-type code.

Direct native experiment: three lower-bit bases, three changed upper32-bit values per base, five positive/negative regions, eight MT structure types. All360 paired raw placements repeat when only the upper32 bits change. Trial Chamber raw placement differs in45/45 pairs; sampled terrain biome IDs differ in36/36 pairs. Results: `runs/optimization-research/bit-pattern-check.json`. Finite sample only; does not validate every version, viability, village-associated Strongholds or terrain reuse.

Therefore a future staged finder can prefilter/reuse **raw** MT structure layouts by `seed & 0xffffffff`, then evaluate full64-bit terrain and viability. Trial Chambers need their own dependency treatment. Do not truncate the entire seed, collapse terrain worlds, or apply Java quad-hut low20-bit masks to our landscapes. Java Cubiomes' [quad-base shortcut](https://github.com/Cubitect/cubiomes#quad-structure-search) is a specific structure constellation optimization, not a general mountain/island seed signature.

For2000 broadly distributed64-bit seeds, random lower32-bit collisions have only about0.0465% probability; a cache alone would rarely reuse a raw layout. Choosing many high-bit variants of selected raw layouts is a different sampling strategy and requires measured selectivity/recall and deterministic enumeration. All114 scored pilot locations already have a predicted Fortress;19 unresolved locations lack local Stronghold predictions. Their absence cannot safely veto them because known baseline misses establish incomplete Stronghold enumeration. This makes a simple structure-first bit prefilter weak under our broad current borders. Eliminating every structure calculation could save only the measured1.21% worker-time share, unless it enabled earlier rejection of substantial terrain work.

## Filter order audit

Current real path (`landscapes.py`, not the historical fallback in `search.py`): coarse discovery → full structure scans → per-kind nominations prioritized by possible Fortress/Stronghold → bounded preliminary terrain → round-robin refinement → island coast → full3008 density raster → fine flat/ring/ocean tests → scoring → cached reports. Required structures affect nomination priority; this is not a universal hard rejection at that point. Missing Strongholds stay reviewable. The basin branch bypasses island coast.

This is reasonable, but no optimal-order A/B proof exists. More difficult filters should not automatically run first. For equivalent short-circuit boolean tests on the same incoming candidates, compare `cost / rejection_probability`; put the lower cost per rejection earlier, subject to dependencies and uncertainty. Measure conditional pass rates separately per landscape branch.

Highest-value experiments:

1. **Basin rejection before full raster.** Twenty-five refined basin nominations are rejected only after the full3008 raster. Sample the small floor/necessary ring points first, retaining every allowed nearby recenter candidate within256 blocks. A bad initial anchor must not discard an acceptable nearby floor. Dry/gentle point counts can give conservative impossibility bounds without assuming complete connected ground. Relief based on the wrong connected subset is not a safe substitute. Full-raster connectivity remains necessary for accepted survivors.
2. **Coverage upper bounds / early termination.** At75% of180 mountain bearings,135 hits are required. Once46 bearings are proven misses, even every remaining bearing passing cannot meet the criterion. Unseen/uncertain bearings must not count as misses. For85% dryness, stop only when observed failures make the best possible final fraction too small. This saves terrain generation only if point sampling is lazy; an early return after the whole raster is already generated saves little.
3. **Fixed-center eligibility earlier where sound.** Cheap exact-square Fortress checks can precede full scoring when the finalized center is known. Before coast/recentering, use a conservative possible-center envelope. Retain negative control/near-miss reporting. In this sample every scored center has Fortress, so no demonstrated large saving. Do not veto missing local Strongholds.
4. **Avoid duplicated work, then measure.** `scan_envelope` calls raw and viable full scans separately. A combined native scan or validating already enumerated raw starts avoids repeated placement, but structures are a small fraction. Flat metrics also recompute gradients/labels for nearby floor candidates; share immutable raster intermediates while preserving each center's connected component and gradient edge behavior. Raw point cache already preserves stride semantics; report refresh already reuses152 identical PNGs in1.09s.
5. **Worker count / native SIMD.** Benchmark full equivalent workload at other worker counts before claiming18 cores are optimal. Native integer placement already uses release optimization/bit operations. Noise/density SIMD or GPU work needs parity tests and may be a bigger engineering project; it does not follow from structure-only GPU speed. Small Python shift/arithmetic changes target negligible seed-enumeration/scoring cost.

Do not relax isolation, flatness, borders, optional/required policy, sampling budgets, unknown handling or terrain semantics to claim a speedup. Any production change invalidates the existing readiness seal and requires affected correctness tests, exact prediction/resume checks and a measured equivalent workload. Research files are outside the sealed production artifacts.
