# Gemini research brief: current Minecraft Bedrock seed selection

Research better seed selection, filter order and computation reduction for this existing implementation. Examine the supplied current code first, then research primary sources and cite exact links, edition/version, commit and workload. Return concrete proposals ranked by expected benefit, correctness risk and implementation effort. Research only; the large sweep is unstarted.

## Current requirements and architecture

- Target Minecraft Bedrock 26.52, modeled by the pinned MC_26_50 backend. Full signed 64-bit seeds; deterministic SplitMix64 finalizer enumeration. This is Python 3.13 with a compiled C backend exposed through CFFI and an owned opaque Generator handle, not a guessed ctypes layout.
- Backend: https://github.com/FragrantResult186/cubiomes-bedrock at commit 294c72ab0392dd818a91d293dbd5774d4874d64b. Bundled vendor/backend.json contains authoritative source hashes. Native source and its license are in the ZIP.
- Intel x86_64 Mac, 18 physical/36 logical cores, 64 GiB RAM. Current measured recommendation is 12 processes, one numeric thread per process. Eighteen workers have not been benchmarked.
- Select a land center snapped to an eight-block grid. Playable Overworld square is exactly 3008 x 3008; Nether square exactly 992 x 992, centered at the Overworld center divided by eight. Candidate-center axes are +/-5000; discovery extends to +/-6528 to provide context. Do not assume center (0,0) is actual spawn: native actual-spawn prediction is unsupported here.
- Stronghold and Fortress are mandatory; Bastion is optional with lower influence. Trial Chamber, Mineshaft and other structures affect scores. Exact square membership must remain distinct from distance ranking and accessible generated footprints.
- Three landscape branches: separated inner island with water and surrounding mountains; ocean island; dry, mostly flat mountain basin without an inner island. Current configuration is the source of truth for all thresholds, scoring, finite nomination/refinement budgets and ambiguity handling. Deep-dark biome coverage at Y=-32 is rank-only evidence, not a proof of terrain shape.
- Chunkbase Bedrock 26.50-26.52 with Terrain enabled is an independent prediction reference. Website markers, native predictions and actual generated-game evidence are distinct. No automatic game/BDS verifier is implemented.

## What is already implemented

Stronghold then required Fortress placement and joint possible-center intersections precede terrain discovery. Nomination-envelope checks and finalized-island-center checks precede expensive terrain. Fast mode defers unpredicted cases; it exports a recovery list. This can miss worthy seeds because Stronghold prediction is incomplete and island nomination envelopes are heuristic. Review-all mode disables that fast exclusion for a separate bounded recovery run.

Other completed shortcuts: one raw placement scan followed by full-seed native viability; a bounded 128-entry process-local raw-layout cache using lower32 only for eight verified MT families; exact per-seed terrain caching; smaller necessary basin dry/gentle bounds including all allowed recenters and kernel halos; lazy mountain-ray impossibility bounds; shared raster labels/gradients/local ranges; persisted report terrain and unchanged-map reuse. Stronghold village iteration, Mineshaft, Trial Chambers, terrain/biomes/density and viability are excluded from that lower32 cache. Every reused raw layout still gets full64 viability. Random lower32 collisions are rare, so generic cache speedup for arbitrary worlds is not established.

## Measured results and caveats

112 tests pass. Frozen 880 structure/159 coordinate comparisons retain 874 unique typed correspondences, six known disagreements and zero reused starts. This does not establish universal accuracy or complete recall. Raw density omits caves, aquifers, decoration and actual chunk interpolation; woodland is a biome proxy.

Current chosen 20-input pilot: 96 scored locations (49 enclosed, 47 ocean, zero accepted basins), two website-supported ocean controls. 345.58 seconds total including interrupted/resumed startup and two exports; 310.89 analysis, 34.69 reports. Effective 17.28 seconds per input; worker mean 80.79 seconds. These are input costs, not time to find 20 worthy seeds. All 95 common qualifying old/new candidate records match exactly. Nineteen prior unresolved locations are deferred and one new location reached. Coverage changed, so old/new overall time is not a controlled equal-workload A/B.

Summed worker-stage shares: coast 47.54%, landscape 26.95%, preliminary terrain 23.51%, structures 0.87%, discovery 0.51%, proxy 0.36%, scoring 0.26%. Stage cost denominators and conditional survivor counts matter.

Controlled separate stage benchmarks: four failed basin nominations 30.72 to 1.39 seconds (95.47% time saving, 94.18% fewer native columns); all four also fail the original full-raster check. Combined structure scans 0.4255 to 0.2515 seconds (40.88%) with identical typed predictions across four seeds/all supported families. These are bounded stage results, not overall universal speedups. Independent 20-input checkpoint/resume and worker-count runs match predictions, metrics and deterministic counters, excluding only timing/RSS/PIDs. Identical uninterrupted 20-input cohorts: 8 workers 233.65 analysis seconds, 12 workers 212.59 (9.01% saving), one trial per count; maps reused for both. Twelve-worker amortization projects about 5.92 hours for 2000 inputs; conservative interrupted-pilot overhead gives 9.60 hours, before variability/manual review.

## Priority research questions

1. Stronghold correctness: diagnose the village-associated path, RNG consumption/precision, angle stepping, village candidate order, biome viability and negative-coordinate rules. Two seed -1 website disagreements are at (6212,-4700) and (3524,-7276). Changing both axes from floor to truncation recovers those but breaks 12345; truncating only X fits four calibration seeds but fails independent seed 9, replacing website-supported (-908,644) with (2404,20). Snow-biome exclusion also breaks other seeds. Do not propose coordinate exceptions or those falsified patches. Separate confirmed cause from hypothesis; propose independent discriminating tests and generated-world checks when needed. Full diagnostics, variants and website text are bundled.
2. Seed selection: would deterministic enumeration of strong raw lower32 structural layouts followed by selected high32 variants improve worthy-world yield per CPU-hour? Quantify raw selectivity, viability dependence, terrain diversity, sampling bias and lost recall. Treat Trial Chamber and Stronghold RNG dependencies separately; Java 48-bit/quad-hut shortcuts are not automatically applicable to Bedrock. Distinguish existence somewhere in the envelope from jointly satisfiable candidate-center bounds.
3. Filter order: measure conditional cost/rejection probability per branch, respect dependencies and unresolved evidence. Hardest first is not a sufficient ordering rule. Are there cheaper safe necessary ocean/coast/basin bounds, adaptive terrain samples or possible-center envelopes that preserve eligible recenters? Label any heuristic recall tradeoff explicitly rather than presenting it as a guaranteed rejection.
4. Remaining computation: coast dominates. Examine duplicated point generation, biome/noise sampling, native density calls, memory allocations, component labeling, gradient/range operations and C/Python transfers. Assess batching, reuse with exact stride semantics, release compiler settings, SIMD/native vectorization and worker scheduling. Give workload-specific benefit estimates; seed-mixer bit tricks target little measured CPU time.
5. Evidence and experiments: propose a bounded equivalent-workload A/B and reference parity suite, with thin bridges, separated islands, nearby alternate basin floors, exact negative borders, full64 siblings, 12345, -1, 0, 4294979641 and independent seed 9. Include positive and negative controls. Measure cold/warm caches and export costs separately; do not infer speedup or good-seed yield from a chosen sample alone.

## Requested response

Provide an evidence-backed table of proposals: precise code location, mechanism, required edition/version assumptions, expected conditional CPU/yield impact, recall/correctness risk, validation experiment and priority. Identify what already exists so it is not proposed as new work. Give a specific plan to resolve Stronghold disagreements, plus the best remaining coastline/terrain optimization. Cite only primary documentation, source code, papers or authors' reproducible benchmarks. Flag unavailable/uncertain facts. Do not change requirements to manufacture passing worlds.

## Reading order and file status

Start with this brief, search.example.yaml, FILTER_OPTIMIZATION.md, STRONGHOLD_INVESTIGATION.md, current source and current measured JSON. SINGLE_FILE_CONTEXT.md embeds the essential documents/code/evidence for easy upload; the ZIP additionally contains complete vendor source, tests, diagnostic variants, frozen fixtures and two candidate map packets. SNAPSHOT_MANIFEST.json lists exact relative source names and hashes; SNAPSHOT_IDENTITY.json records the current backend/config identity.

OPTIMIZATION_RESEARCH.md is historical pre-implementation research from 7 October. Its 'current filter order' and old pilot numbers are superseded by FILTER_OPTIMIZATION.md and the current code/measurements. LANDSCAPE_EXPANSION.md provides historical geometry context. Current source/configuration take precedence over older explanatory documents. This package is a research snapshot; it excludes installed binaries, the virtual environment and full execution checkpoints. The existing local verified sweep package remains unchanged and the large sweep remains unstarted.

# Embedded current files

These sections are exact current file contents. Native finders.c below is a labeled excerpt; its full source is in the ZIP.

## File: search.example.yaml

SHA-256: 89414ed421ecc1fd363b1f5ba3c2b0ec1c3e5653918629732050f3cf9f8ef71c

````yaml
# Configuration for the bounded preflight and planned later search.
# Search remains gated by an evidence-backed readiness record.
# Fixed requirements: Bedrock 26.52, confirmed border sizes, island separation,
# nearby wood, required Fortress and Stronghold, and optional Bastion.
# Numeric landscape preferences and score weights are tunable pilot defaults.
schema_version: 3

game:
  edition: bedrock
  target_version: "26.52"
  backend_repository: https://github.com/FragrantResult186/cubiomes-bedrock
  backend_commit: "294c72ab0392dd818a91d293dbd5774d4874d64b"
  # Explicit 26.52 -> MC_26_50 mapping; bounded predictor evidence in run metadata.
  backend_model: MC_26_50
  require_validated_capabilities_before_large_search: true

deployment:
  host: mojang_realm
  management_device: phone
  achievements_required: false
  border_addon: mygen_world_border
  border_addon_version: "4.0.0"
  # Single source of truth: derive half-width = side / 2 and menu chunks = side / 32.
  overworld_side_blocks: 3008
  nether_side_blocks: 992

search:
  mode: full_64_bit_reference
  deterministic_mixer: splitmix64_finalizer
  run_key: "0"
  # Center envelope around coordinate origin; derive analysis halo from border half-width.
  center_axis_bounds_blocks: [-5000, 5000]
  workers: 4
  numeric_threads_per_worker: 1
  discovery_spacing_blocks: 64
  refinement_spacing_blocks: 16
  shoreline_spacing_blocks: 4
  # Components touching the finite outer analysis boundary remain unresolved.
  raster_boundary_policy: mark_unknown
  lower_bit_optimization_enabled: false
  report_top_distinct_seeds: 20
  # Finite heuristic refinement budget; report deferred components explicitly.
  maximum_preliminary_components_per_seed: 32
  maximum_refined_centers_per_seed: 8
  maximum_refinement_patch_side_blocks: 2048
  pilot_seed_counts: [10, 100, 1000]
  # Only bounded diagnostics are implemented until validation is complete.
  large_search_enabled: false
  preflight_maximum_seeds: 10

overworld:
  # Reporting/map overlays only; distance_score_scale_blocks controls structure proximity.
  report_core_side_blocks: 1200
  report_primary_side_blocks: 2000
  border_center_snap_blocks: 8
  distance_score_scale_blocks: 1000
  # Shared shoreline range for water, high terrain, and nearby external woodland.
  surrounding_range_from_shore_blocks: 800

island:
  conservative_land_connectivity: 8
  preferred_equivalent_diameter_blocks: [300, 700]
  score_method: preferred_interval_ratio

water:
  angular_samples: 180
  preferred_gap_blocks: [50, 200]
  preferred_enclosure_fraction: 0.85
  full_credit_enclosure_fraction: 0.90
  score_method: enclosure_times_gap_fit

mountains:
  preferred_directional_fraction: 0.75
  # Permissive high-terrain proxy; actual mountain appearance is inspected in game.
  minimum_height_above_water_blocks: 50
  snowy_summits_allowed: true
  score_method: coverage_to_target

wood:
  # Percentages refer to estimated wooded surface land, not verified tree/log counts.
  fraction_denominator: land_area
  island:
    abundance_required: false
    preference: less_wooded_more_open
    openness_score_method: one_minus_wooded_fraction
  surrounding_land:
    preferred_wooded_fraction: 0.30
    full_credit_wooded_fraction: 0.60
  score_method: surrounding_fraction_only

structures:
  required_overworld_types: [stronghold]
  core_policy: strong_preferences_not_hard_requirements
  category_budget_fractions:
    trial_chamber: 0.25
    stronghold: 0.25
    mineshaft: 0.20
    ancient_city: 0.15
    secondary_combined: 0.15
  secondary_types: [village, ruined_portal, shipwreck, monument, outpost]
  per_type_score: nearest_viable_in_border
  secondary_aggregation: mean_including_known_absences

nether:
  # Center is derived from the Overworld border center divided by eight.
  fortress_required: true
  bastion_required: false
  optional_bastion_proximity_weight: 0.20
  full_credit_distance_blocks: 300
  score_method: mean_capped_inverse_distance

score_weights:
  island_size: 15
  island_openness: 5
  water: 15
  mountains: 15
  wood: 20
  overworld_structures: 20
  nether_proximity: 10

verification:
  initial_method: chunkbase_matching_version_terrain
  initial_finalist_count: 5
  final_required_checks:
    - island_fully_separated
    - surrounding_water_and_mountains
    - settlement_buildability
    - abundant_accessible_wood_on_surrounding_land
    - fortress_access_inside_nether_border
    - stronghold_inside_overworld_border
  optional_actual_game_checks: [actual_portal_arrival, spawn_and_border_behavior, structure_footprints]

output:
  candidate_files: [candidate.json, overworld.png, nether.png, inspection.md]
  summary_formats: [json, csv]
  unknown_score_policy: interval_and_separate_review_list

# The original water-enclosed island search remains available alongside these.
landscapes:
  enabled: [enclosed_island, ocean_island, mountain_basin]
  ocean_window_side_blocks: 1400
  minimum_ocean_fraction: 0.50
  flat_radius_blocks: 96
  maximum_flat_relief_blocks: 16
  maximum_flat_slope: 0.30
  minimum_dry_fraction: 0.85
  ring_radius_blocks: 800
  minimum_ring_relative_height_blocks: 50
  minimum_ring_fraction: 0.75
  deep_dark_y: -32
  deep_dark_inner_side_blocks: 64
  deep_dark_outer_side_blocks: 200
  deep_dark_spacing_blocks: 16
  deep_dark_policy: rank_only

optimization:
  exact_per_seed_cache: true
  cache_mb_per_worker: 64
  persist_report_terrain: true
  reuse_unchanged_maps: true
  # Fast heuristic: save absent predictions as deferred review, not proven absence.
  stronghold_prefilter: defer_unpredicted
  early_basin_bounds: true
  reuse_raster_intermediates: true
  combined_structure_scan: true
  lazy_coverage_bounds: true
  raw_mt_cache_entries: 128
````

## File: FILTER_OPTIMIZATION.md

SHA-256: 4623aa8cd166db7f96cf603071dd59f687ac8c8823e59ad4cd2089b47ab92737

````markdown
# Filter optimization — 8 October 2026

The user authorized the discussed shortcuts and fast Stronghold filtering.
The production iterator remains pinned and its known misses remain visible. A
rounding workaround that failed independent seed9 verification was not installed.
The large sweep remains unstarted. Prior sources/readiness are preserved in
`runs/filter-optimization/prior-sources.zip` and `prior-readiness.json`.

## New order

1. Enumerate Stronghold, then other required structure predictions before the
   discovery map. Intersect their allowed eight-block center windows. The Fortress
   window is converted to Overworld units exactly once.
2. Discover/nominates the same three landscape branches. Defer components whose
   nominal center envelope has no joint required prediction. Basin envelopes include
   all256-block recenters; island envelopes retain the64-block displacement margin.
   These nomination envelopes are heuristic, not an exhaustive shoreline guarantee.
3. Run bounded preliminary terrain only on retained nominees. Refine coast only
   for selected islands. Check finalized island-center required windows before the
   full3008-square terrain. Basin centers retain their recenter path before final
   eligibility is decided.
4. Before full basin terrain, check necessary dry/gentle upper bounds in a smaller
   lattice-aligned patch with gradient/5×5 kernel halo, including the exact original
   eight nearby floor proposals. Ignore local connectivity for these upper bounds:
   a connection outside the patch must remain possible. Percentile relief remains
   a full-raster test; it is not approximated using a misleading local subset.
5. Lazy mountain-ray checks count only proven misses. With180 rays and75% required,
  46 misses make success impossible. Unknown/unprocessed rays remain possible.
   Connectivity is ignored and113 is the minimum possible height threshold, so
   this is a necessary upper bound. Stop extra sampling at5000 ray points and let
   full terrain resolve the survivor. Accepted basins still require full-raster
   connectivity, dry/gentle fraction, relief and enclosing dry mountain bearings.
6. Reuse per-raster labels, gradients, coordinate meshes and local ranges across
   alternate build centers. Score survivors, checkpoint, and reuse verified cached
   terrain/maps on export.

Fast-mode missing predictions are **deferred, not proven absent**. Both seed-level
and location-level records are exported in `stronghold-deferred.json`; a distinct
seed list is `stronghold-deferred-seeds.txt`. A seed may also have successfully
analyzed locations and still appear there. Use `config/review-all.yaml` for a new
bounded recovery run, in batches of at most1000 supplied seeds. Do not resume a
fast checkpoint with changed configuration. Stronghold and Fortress remain required
for final matching-version website eligibility. No game evidence is inferred.

## Native shortcuts and bits

`ss_filter_starts` validates raw positions without rerunning placement. Its special
Stronghold/Mineshaft handling exactly matches the original adapters. Typed CFFI
buffers and the owned opaque Generator context are retained. The supported editable
native build recompiles the changed owned bridge; all pinned vendor hashes stay
unchanged. No fictional stronghold/fortress symbols or guessed ctypes layouts.

The bounded per-process128-entry raw layout cache uses `(family, seed & 0xffffffff,
bounds)` only for the eight pinned MT families: Village, Ancient City, Ruined Portal,
Shipwreck, Monument, Outpost, Fortress, Bastion. Every cache hit still reruns
viability with the complete world seed. Stronghold village positions, Mineshaft,
Trial Chamber, terrain, biomes and densities never use that cache. Trials keep their
different RNG dependency. Returned results cannot mutate the stored immutable raw
tuples. Negative coordinates, upper-bit worlds, cache eviction and closed handles
are tested. Full64-bit enumeration is unchanged. Random low32 collisions are rare;
the cache mainly helps workloads containing high-bit siblings and is not claimed
to accelerate ordinary random seeds materially.

No Java quad-hut mask, terrain-only lower-bit signature, SIMD/GPU noise rewrite or
unsafe coordinate-rounding patch was adopted. The first two lack applicable Bedrock
terrain guarantees; the latter changes need separate implementation/parity evidence.
No filter threshold, flatness/isolation condition, square, or secondary-score weight
was relaxed.18 workers were not forced simply because18 physical cores exist.

## Verification and measured results

112 meaningful tests pass, including all supported native-family combined-scan
parity on four seeds; low32 raw cache/full64 viability separation; joint windows
and exact negative borders; fast missing-Stronghold deferral before any terrain;
reference-positive/nearby-floor controls for early basin checks; shared raster
parity; the independent seed9 guard; checkpoint/resume and worker variation.
Frozen880 structure/159 point regression remains874 unique correspondences, six
known disagreements, no reused starts. Root Stronghold recall is not fixed.

Alternating-order isolated A/B on four saved failed basin nominations:
30.7207→1.3903 seconds (**95.47% stage time saving**),189268→11016 native density
columns (**94.18% reduction**). Every early rejection also fails the original
full-raster/recenter check. Combined native scans0.4255→0.2515s across four seeds and
all families (**40.88% stage saving**), with exact typed results. These small tests
do not establish universal speed or candidate yield.

Current interrupted/resumed20-input pilot:96 scored locations,49 enclosed/47 ocean,
zero positive dry basins. All95 prior locations with local required predictions
retain identical complete candidate records, metrics and scores.19 prior missing-
Stronghold locations are deferred, and one new location is reached.2082 nominal
locations are explicitly deferred, mostly before preliminary terrain.38 of40 basin
refinements fail the cheap necessary bound; no positive real basin yield is claimed.

Pilot345.58s total,310.89s analysis,34.69s reports;17.28s/input effective throughput,
worker mean80.79s, range40.88–129.15s. Prior20-input pilot387.62s/19.38s/input and
worker mean96.39s. New coverage differs, so the overall comparison is observational,
not an unchanged-workload causal A/B. A separate uninterrupted worker-count
comparison uses identical20 seeds/config/predictions and reusable report maps.
No performance claim is based on how many worthy worlds were found.

Uninterrupted analysis:8 workers233.65s versus12 workers212.59s, **9.01% less wall
time** with identical prediction hashes. Twelve is the current recommendation,
based on one measured trial per count, not a claim of global optimality. Measured
12-worker analysis projects about5.92h for2000 inputs plus amortized cold reports;
the interrupted8-worker pilot's complete overhead gives a conservative9.60h.
Use1.5× allowance(about8.87–14.40h) and add manual review.18 workers were not tested.

Independent20-input12-worker run exactly matches the interrupted/resumed8-worker
pilot, including predictions, metrics, point-cache counters, deferrals/rejections
and deterministic stage counts. Only timings/RSS/PIDs are excluded. Fresh actual
matching-version browser follow-ups re-confirm four required markers on two retained
ocean controls, including a high-bit seed and negative coordinates. Prior geometry
observations retain their original dates/scopes and are not relabeled as new blind
holdouts.150 unchanged PNGs refresh in1.18s with no native height/biome calls or
redraws, enforced by failing hooks. Website evidence remains distinct from Minecraft.

Exact current commands, worker comparison, finite runtime estimate and readiness
identity are in [SWEEP_READINESS.md](SWEEP_READINESS.md). The archived package does
not authorize the changed sources; only newly assembled verified readiness does.
````

## File: STRONGHOLD_INVESTIGATION.md

SHA-256: 52a3b0d5b28552308e06966cb7652d22dadf9228b7ec54ec6bf5b2bfeb743e43

````markdown
# Stronghold disagreement investigation — 2026-10-07

The production iterator is unchanged. The large sweep remains unstarted.

## What was established

The two frozen seed `-1` disagreements come from the village-associated path,
not the static-region scan, its halo, or an output-capacity limit. Current village
starts are `(4084,-828)`, `(-956,5684)`, `(5492,2852)`; the matching-version
Chunkbase fixture has `(4084,-828)`, `(6212,-4700)`, `(3524,-7276)` instead.
This remains a disagreement between predictions, not proof from a generated game.

The reproducible read-only diagnostic is
`runs/stronghold-investigation/diagnose.py`. It uses the installed native MT RNG,
village region positions and village viability checks. No Generator layout is
guessed and no native library is changed. Its 48 variants vary X/Z rounding and
village eligibility separately across four calibration seeds. Earlier 16
precision/rounding variants are retained in `numeric-variants.json`.

Changing both axes from floor to truncation recovers the two missing seed `-1`
markers but breaks seed `12345`: it changes `(276,2836)` to `(2804,-236)`.
A fresh actual Chunkbase UI search again shows `(276,2836)` and does not show the
alternative as its nearest result from `(2804,-236)`. Evidence is saved in
`chunkbase-12345-fresh.txt` and `chunkbase-12345-second-fresh.txt`.

Truncating only X preserves the four calibration seeds and recovers both `-1`
markers. However, the independent seed `9` check rejects that proposed correction:
the current iterator predicts `(-908,644)`, while the variant predicts
`(2404,20)` as its first village stronghold. Fresh Bedrock 26.50–26.52 Chunkbase
search from `(0,0)` shows `(-908,644)` as its nearest Stronghold (Stairway).
Evidence: `chunkbase-seed-9-first.txt`. That nearest-marker check falsifies the
variant; it does not claim complete recall from the website's bounded list.

Removing snow biomes also recovers `-1` but breaks other calibration seeds. These
experiments are candidate hypotheses, not accepted corrections. The historical
[Bedrockified reconstruction](https://github.com/Earthcomputer/bedrockified/blob/master/src/main/java/net/earthcomputer/bedrockified/BedrockStrongholdStructure.java)
also floors both axes; it is not a verified modern-version replacement.

## Safe operational handling, verified

Production `required_status` treats missing Strongholds as unresolved when the
other required predictions pass. It retains them for review instead of treating
absence from this enumerator as proof of absence. The Stronghold remains required:
only a recorded matching-version website marker inside the exact 3008-block square
establishes website-level required eligibility. An out-of-border marker cannot do
that; a missing review field is rejected. This does not certify game footprints.

The existing tests for required Fortress/Stronghold with optional Bastion, missing
Stronghold preservation, external recovery with empty native predictions, and exact
review borders were rerun: two tests pass. The readiness manifest was checked again
against all current source, config, backend and evidence hashes.

## Root correction criteria

Do not install either rounding variant or coordinate-specific exceptions. A root
correction needs to explain the village-acceptance divergence for `-1`, preserve
the frozen comparisons, and pass independent cases such as `9` and `12345`.
Matching-version generated-world evidence would resolve which predictor is wrong
when they disagree. A backend change then requires rebuilding, regression replay,
a new bounded pilot/resume proof and new readiness identity before a sweep.
The tested review path is the current mitigation; complete enumerator accuracy
has not been established.
````

## File: OPTIMIZATION_RESEARCH.md

SHA-256: 10523745428ba4f6ab5993b6c0d179c16af723963192be094f2ccc3a6e97a549

````markdown
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
````

## File: vendor/backend.json

SHA-256: d95c3155f8a98dc40b49a2d083fbfdb2ce35bc496b19554f267d445d6eb3d838

````json
{
  "repository": "https://github.com/FragrantResult186/cubiomes-bedrock",
  "commit": "294c72ab0392dd818a91d293dbd5774d4874d64b",
  "source_archive_sha256": "289f3407e32a0fa980a296d057f3b54ba3c56b684f72ade2e5efbe487a8d3e99",
  "files": {
    "LICENSE": "894d391566a3bb235b1df6c278960b2083769076b0199a0a367c771b05a74120",
    "biomenoise.c": "b93ab7df07c913c9fdaa3e7ee7a7e8294708caf05003c50b29b094259f235a96",
    "biomenoise.h": "7122e30c86d18b0873e29017b44fb22746143b69cb6baa1b6e0ada07cd26f88e",
    "biomes.c": "61cd1c00a30de610f2f86974db32e6c1a2c688bdacd285aa6228a930942fc92e",
    "biomes.h": "3231c509e8129d2f6782e8dcfa83fc4e039e688fdf5c0c6e24cbdaea17fe45a4",
    "cave.c": "60e7cf3080d6e743b9d8b4b2c83d5806971e0980d801fce8f67bf444f15fb8ce",
    "cave.h": "2b39e7e56ad3e76aca0d6566b94c69d437fd556ca210be2ece6cdcba2fec12b1",
    "finders.c": "8980c6703765398a1c6af2934bd990b247c0c9d0e61db9270b4e5eb7e644dcef",
    "finders.h": "b91dae02e695274c32ac9f65423d40dcee967b99fe2336fbc29f6cf3a0fb1b78",
    "generator.c": "3720b172733b36f2fb3fb707e620a491bac1da6d7c682c520a0a549f853f3ca0",
    "generator.h": "963a919e0baf33af9acc5f944f935bd0c025985a64d31a5e11b2736752353517",
    "layers.c": "60274d97f424b898690297ba7dfad564499a337b708b5ea4961f46a5967a3c9a",
    "layers.h": "22bb14b45657a196e166c0bbebc122d736be81ea109b087dabb9766f1cea06a6",
    "mt.c": "853e8b94e2fb024f2c9489d08144fa81e502d641bbb8f2f35c7b5d3b1a59358b",
    "mt.h": "21e1acc1311d4f6109f26669e600646e214c008d14294f5a1a5a57c8d8ea3f5a",
    "noise.c": "4976bde9b593130bcd7d6433392806c68b70ac1db039d89c7c471ccd024b76d5",
    "noise.h": "abec22393485e92722e1e44dd0bc1cdbe98cc487a8625564467549d303ab1bd0",
    "quadbase.c": "52ba0d1a660cc3d81a3ab09adc9bc2dcb2af2069786bde03b8f2a1c471a094d8",
    "quadbase.h": "a0d252b926baa456d399f50077ea63452e63c4eff16dd912ad8316b37321a57a",
    "rng.h": "1342594d0d26f0a3f7436b386ab46491181f8035778fdd257427d8caed9277ed",
    "tables/btree18.h": "c7bbd595cf096f471f88b3f279941b69e4cbb2f320dfdf531f4a6aeaa0095fad",
    "tables/btree19.h": "a5dc2ad87a80436fc80816dc62060e784d8a4b6a33284e429ae71f46fb11d916",
    "tables/btree192.h": "9447413e158d57348262faf62d91576973e39d682488f188a1aee8abe369416d",
    "tables/btree20.h": "8efd25b3165f457d30f9f7fe41f565cba842aa8513038a7e5ed273e481f2aa3b",
    "tables/btree215.h": "2bcadc16af275c49689f0071e8df277ab3c655eea56aafdb666c2cd792c22d4c",
    "tables/btree21wd.h": "ce8cc83f9be7e2bd6e61589bfb5c401451ac01c49032f51949ad7de0cfb303d9",
    "tables/btree262.h": "64b96107cd62021d2a6beff6621783cb66a76f89f7a04408800f0afc28e9ad5a",
    "tables/btree263.h": "9cdebbd5406caed67152657e5e556b136bf19698efede16bfd839cf49013710c",
    "tables/btree264.h": "272f6d9e9fe73016b796ebb823571c06c707acf8039f01ea29264110da8adba7",
    "tables/btree266.h": "94bb762e4e27d862f8053b0c20e9e77eef8d329eedcf0295a1378fcc9cdb04b6",
    "tests.c": "16d343f46ac0edfb929aa186329cf7a176584604c93ed2446107ca679214ee41",
    "util.c": "473423346c6f5a1071e82ce87489e4a5f63905aa3abfe555bf4824a25bee426a",
    "util.h": "6625e4ed1900723d5a030f4503dc615c2d09bdeea724b276b3b18996f2253943"
  }
}
````

## File: pyproject.toml

SHA-256: c11972fdd99d13a26f5334f5497dc3e86e1935f7b5a4633838edd7b309080e86

````text
[build-system]
requires = ["setuptools==84.0.0", "wheel==0.48.0", "cffi==2.1.1"]
build-backend = "setuptools.build_meta"

[project]
name = "bedrock-island-preflight"
version = "0.1.0"
description = "Bounded Bedrock prediction validation and performance prototype"
license-files = ["vendor/cubiomes-bedrock/LICENSE"]
requires-python = ">=3.13,<3.14"
dependencies = [
  "cffi==2.1.1", "numpy==2.5.3", "scipy==1.18.1", "PyYAML==6.0.3",
  "matplotlib==3.11.2",
]

[project.optional-dependencies]
dev = ["pytest==9.1.1"]

[project.scripts]
seed-preflight = "seed_search.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
````

## File: requirements.lock

SHA-256: 0f04c5dbc449aedeb9a76eef867eba947d9ba6b198d74f24330ddf17a7ad0da9

````text
# Intel macOS / CPython 3.13 dependency lock, including build and test tooling.
# Generated from the successfully installed environment on 2026-10-07.
PyYAML==6.0.3 --hash=sha256:8da9669d359f02c0b91ccc01cac4a67f16afec0dac22c2ad09f46bee0697eba8
Pygments==2.21.0 --hash=sha256:2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9
cffi==2.1.1 --hash=sha256:9d2055050ea716bd38b7f7f1579c275386646b4894c155a3e2f3cd62ed41b7c6
contourpy==1.4.0 --hash=sha256:e21d1d4a9db5b3a793649c7ab0ddb4697f2818929eec871a7b9c45fce7b2a1ea
cycler==0.12.1 --hash=sha256:85cef7cff222d8644161529808465972e51340599459b8ac3ccbac5a854e0d30
fonttools==4.66.1 --hash=sha256:60f5ea17aed4262630afa43f26997ceabd6417fa05dcedf54c665f5a29193e18
iniconfig==2.3.1 --hash=sha256:9121e2c1fdb355232495be3194c8dfe87ccc2d5dee45947b78e68f499790d7a7
kiwisolver==1.5.1 --hash=sha256:1ed0f5e49d0ceff8b72190824d9e59c062fbbc02c231b853112c78474b3f5ec2
matplotlib==3.11.2 --hash=sha256:7d43ff8cebb50840648cb6429b2228621dbd709010f3117b3740abb20abf21c0
numpy==2.5.3 --hash=sha256:ccbc4665079665c3cf3bab4db9f6b095370cd6437d66be549b6c2a1fd19e1958
packaging==26.3 --hash=sha256:d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c
pillow==12.3.0 --hash=sha256:7a743ff716f746fc19a9557f60dab1600d4613255f8a7aeb3cdde4db7eb15a66
pluggy==1.6.0 --hash=sha256:e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746
pycparser==3.0 --hash=sha256:b727414169a36b7d524c1c3e31839a521725078d7b2ff038656844266160a992
pyparsing==3.3.3 --hash=sha256:ece8c00a69cf01b45d0b1dedabb469c90d8caf996d4fda40f147627a122849a4
pytest==9.1.1 --hash=sha256:37a86b45efb9a47a61a36449063e8e18d0cab3161329fc099eb21783169c4f0c
python-dateutil==2.9.0.post0 --hash=sha256:a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427
scipy==1.18.1 --hash=sha256:75b00eb8fb802090aa903f4ea1c7f5a584779f967361e68b7e98e531cc2d7174
setuptools==84.0.0 --hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670
six==1.17.0 --hash=sha256:4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274
wheel==0.48.0 --hash=sha256:3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab
````

## File: src/seed_search/backend.py

SHA-256: 743211d5dc807e425154bd787421cd802c988cc47c9bde94e2b1adc9ce580792

````python
from __future__ import annotations

import threading
from collections import OrderedDict
import numpy as np
from .seeds import parse_seed, MASK64
from ._native import ffi, lib

STRUCTURES = ("trial_chamber", "stronghold", "mineshaft", "ancient_city", "village",
              "ruined_portal", "shipwreck", "monument", "outpost", "fortress", "bastion")
# Serializes wrapper access in a Python process; multiprocessing remains parallel.
_LOCK = threading.RLock()
# These pinned-version families use a uint32_t MT placement seed. Stronghold's
# village path, Mineshaft and Trial Chamber are deliberately excluded.
RAW_MT_TYPES=frozenset(('village','ancient_city','ruined_portal','shipwreck','monument','outpost','fortress','bastion'))
_RAW_LAYOUTS=OrderedDict()

def _int(value: int) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool):
        raise ValueError("Coordinates and sizes must be integers")
    value = int(value)
    if not -(1 << 30) <= value < (1 << 30):
        raise ValueError("Coordinate outside safe prototype range")
    return value

def _buffer(array, ctype):
    return ffi.from_buffer(ctype, array)

def biome_name(biome: int) -> str:
    ptr = lib.ss_biome_name(int(biome))
    return ffi.string(ptr).decode() if ptr != ffi.NULL else f"unknown_{biome}"

def structure_type(name: str) -> int:
    if name not in STRUCTURES:
        raise ValueError(f"Unsupported structure: {name}")
    return int(lib.ss_structure_type(name.encode()))

class Backend:
    def __init__(self, seed: str | int, raw_cache_entries: int = 0):
        self.seed = parse_seed(seed)
        if isinstance(raw_cache_entries,bool) or not isinstance(raw_cache_entries,int) or not 0<=raw_cache_entries<=256:
            raise ValueError('Raw layout cache must contain 0–256 entries')
        self.raw_cache_entries=raw_cache_entries
        with _LOCK:
            ptr = lib.ss_create(self.seed & MASK64)
        if ptr == ffi.NULL:
            raise MemoryError("Could not allocate generator")
        self._ctx = ffi.gc(ptr, lib.ss_destroy)

    def close(self):
        with _LOCK:
            if self._ctx is not None:
                ffi.release(self._ctx)
                self._ctx = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _handle(self):
        if self._ctx is None:
            raise RuntimeError("Backend is closed")
        return self._ctx

    def biome(self, x: int, y: int, z: int, dimension: int = 0) -> int:
        if dimension not in (0, -1):
            raise ValueError("Prototype supports Overworld and Nether only")
        with _LOCK:
            return int(lib.ss_biome(self._handle(), dimension, _int(x), _int(y), _int(z)))

    def grid(self, x0: int, z0: int, nx: int, nz: int, step: int = 64, y: int = 63):
        x0,z0,nx,nz,step,y = map(_int,(x0,z0,nx,nz,step,y))
        if nx < 1 or nz < 1 or step < 1 or nx*nz > 100_000:
            raise ValueError("Grid must contain 1–100,000 points with positive spacing")
        _int(x0+(nx-1)*step); _int(z0+(nz-1)*step)
        biomes=np.empty((nz,nx),dtype=np.int32)
        climate=np.empty((nz,nx,6),dtype=np.float64)
        approx=np.empty((nz,nx),dtype=np.float64)
        with _LOCK:
            code=lib.ss_grid(self._handle(),x0,z0,nx,nz,step,y,
                             _buffer(biomes,"int[]"),_buffer(climate,"double[]"),_buffer(approx,"double[]"))
        if code:
            raise RuntimeError(f"Native grid error {code}")
        return {"biomes":biomes,"climate":climate,"approx_height":approx}

    def heights(self, xz, vertical_step: int = 8):
        points=np.asarray(xz)
        if points.ndim != 2 or points.shape[1] != 2 or len(points)>100_000:
            raise ValueError("Expected up to 100,000 X/Z coordinate pairs")
        if not np.issubdtype(points.dtype,np.integer):
            raise ValueError("Point coordinates must be integers")
        if np.any(points < -(1<<30)) or np.any(points >= (1<<30)):
            raise ValueError("Point outside safe prototype range")
        points=np.ascontiguousarray(points,dtype=np.int32)
        if not isinstance(vertical_step,int) or not 1<=vertical_step<=16:
            raise ValueError("Vertical step must be an integer in 1–16")
        heights=np.empty(len(points),dtype=np.int32)
        biomes=np.empty(len(points),dtype=np.int32)
        with _LOCK:
            code=lib.ss_heights(self._handle(),_buffer(points,"int[]"),len(points),vertical_step,
                               _buffer(heights,"int[]"),_buffer(biomes,"int[]"))
        if code:
            raise RuntimeError(f"Native height error {code}")
        return heights,biomes

    def land(self, xz):
        points=np.asarray(xz)
        if points.ndim!=2 or points.shape[1]!=2 or len(points)>100_000 or not np.issubdtype(points.dtype,np.integer):
            raise ValueError('Expected up to 100,000 integer X/Z pairs')
        if np.any(points<-(1<<30)) or np.any(points>=(1<<30)):raise ValueError('Point outside safe range')
        points=np.ascontiguousarray(points,dtype=np.int32);out=np.empty(len(points),dtype=np.int32)
        with _LOCK:
            code=lib.ss_land(self._handle(),_buffer(points,'int[]'),len(points),_buffer(out,'int[]'))
        if code:raise RuntimeError(f'Native land classification error {code}')
        return out.astype(bool)

    def structures(self, name: str, bounds: tuple[int,int,int,int], viable: bool = True):
        typ=structure_type(name)
        x0,z0,x1,z1=map(_int,bounds)
        if x0>x1 or z0>z1 or x1-x0>14_000 or z1-z0>14_000:
            raise ValueError("Invalid or oversized prototype structure bounds")
        cap=((x1-x0)//16+3)*((z1-z0)//16+3)+20
        out=np.empty((cap,2),dtype=np.int32)
        with _LOCK:
            n=lib.ss_scan(self._handle(),typ,x0,z0,x1,z1,int(viable),_buffer(out,"int[]"),cap)
        if n<0:
            raise RuntimeError(f"Native structure scan error {n} for {name}")
        return sorted({(int(x),int(z)) for x,z in out[:n]})

    def attempt(self,name: str,rx: int,rz: int):
        out=ffi.new("int[2]")
        with _LOCK:
            result=lib.ss_attempt(self._handle(),structure_type(name),_int(rx),_int(rz),out)
        if result<0:
            raise ValueError("This type requires its special scan adapter")
        return (int(out[0]),int(out[1])) if result else None

    def structure_pair(self,name,bounds):
        """One placement scan, then full-seed viability. Cache ONLY raw MT layouts."""
        # Validate before a cache hit, including a closed handle and bounds.
        self._handle();typ=structure_type(name);bounds=tuple(map(_int,bounds))
        x0,z0,x1,z1=bounds
        if x0>x1 or z0>z1 or x1-x0>14000 or z1-z0>14000:
            raise ValueError('Invalid or oversized prototype structure bounds')
        key=(name,self.seed & 0xffffffff,bounds) if name in RAW_MT_TYPES and self.raw_cache_entries else None
        with _LOCK:
            raw=_RAW_LAYOUTS.pop(key,None) if key is not None else None
            if raw is None:
                raw=tuple(self.structures(name,bounds,False))
            if key is not None:
                _RAW_LAYOUTS[key]=raw
                while len(_RAW_LAYOUTS)>self.raw_cache_entries:_RAW_LAYOUTS.popitem(last=False)
            if not raw:return [],[]
            pts=np.ascontiguousarray(raw,dtype=np.int32)
            flags=np.empty(len(raw),dtype=np.int32)
            code=lib.ss_filter_starts(self._handle(),typ,_buffer(pts,'int[]'),len(raw),_buffer(flags,'int[]'))
            if code:raise RuntimeError(f'Native start filter error {code}')
            return list(raw),[p for p,ok in zip(raw,flags) if ok]

def model_metadata():
    return {"model": ffi.string(lib.ss_model_name()).decode(),
            "structure_rng": {name: int(lib.ss_structure_rng(structure_type(name))) for name in STRUCTURES}}

def capabilities():
    return {'edition':'bedrock','target_version':'26.52','model':'MC_26_50',
            'mapping_status':'bounded_matching_version_Chunkbase_comparison',
            'dimensions':['overworld','nether'],'structures':list(STRUCTURES),
            'terrain':'raw density estimate, no caves/aquifers/decoration/chunk interpolation',
            'woodland':'surface biome proxy, no tree counts',
            'unsupported':['end','actual structure footprints','portal arrival','spawn','trees'],
            'lower_bit_optimization':False}

def structure_diagnostic(backend, name, x, z):
    out=ffi.new('int[10]')
    with _LOCK:
        ok=lib.ss_diagnostic(backend._handle(),structure_type(name),_int(x),_int(z),out)
    if not ok: raise ValueError('Diagnostic supports Bastion and Ancient City only')
    return {'quart_sample':[int(out[i]) for i in range(3)],'sample_biome':biome_name(out[3]),
            'rotation':int(out[4]),'variant':int(out[5]),'piece_offset':[int(out[6]),int(out[7])],
            'piece_size':[int(out[8]),int(out[9])],'start_biome':biome_name(backend.biome(x,-27 if name=='ancient_city' else 33,z,0 if name=='ancient_city' else -1))}
````

## File: src/seed_search/cache.py

SHA-256: c8be09927ef8fa77563bb8bae253232aa5692c7960f5c5faec3c705ced266513

````python
"""Bounded per-seed exact caches; no reuse across seeds or height strides."""
from collections import OrderedDict, defaultdict
import numpy as np
from .backend import Backend


class CachedBackend(Backend):
    def __init__(self,seed,cache_mb=64,raw_cache_entries=0):
        super().__init__(seed,raw_cache_entries)
        self.limit=int(cache_mb*1024**2)
        if self.limit<32768:raise ValueError('Cache must hold at least one 32 KiB tile')
        self.tiles=OrderedDict();self.bytes=0;self.peak_bytes=0;self.evictions=0
        self.stats=defaultdict(lambda:{'requested_points':0,'computed_points':0,'reused_points':0})

    def _sample(self,points,kind,scale,side,fields,dtype,missing,compute):
        points=np.asarray(points)
        # Preserve Backend validation even when every requested point is cached.
        if points.ndim!=2 or points.shape[1]!=2 or len(points)>100000 or not np.issubdtype(points.dtype,np.integer):
            raise ValueError('Expected up to 100,000 integer X/Z pairs')
        if np.any(points<-(1<<30)) or np.any(points>=(1<<30)):raise ValueError('Point outside safe range')
        self._handle()
        points=points.astype(np.int32);out=np.empty((len(points),fields),dtype=dtype)
        if not len(points):return out
        xy=points.astype(np.int64)//scale;tile=xy//side
        keys=(tile[:,0]<<32)|(tile[:,1]&0xffffffff)
        unique,inverse=np.unique(keys,return_inverse=True)
        order=np.argsort(inverse,kind='stable');edges=np.r_[0,np.cumsum(np.bincount(inverse))]
        st=self.stats[kind];st['requested_points']+=len(points)
        for i,_ in enumerate(unique):
            rows=order[edges[i]:edges[i+1]];tx,tz=tile[rows[0]]
            key=(kind,scale,int(tx),int(tz))
            data=self.tiles.pop(key,None)
            if data is None:
                data=np.full((side*side,fields),missing,dtype=dtype)
                while self.bytes+data.nbytes>self.limit and self.tiles:
                    _,old=self.tiles.popitem(last=False);self.bytes-=old.nbytes;self.evictions+=1
                self.bytes+=data.nbytes;self.peak_bytes=max(self.peak_bytes,self.bytes)
            self.tiles[key]=data
            local=xy[rows]%side;slots=local[:,1]*side+local[:,0]
            absent=data[slots,0]==missing
            if absent.any():
                slots_missing,first,back=np.unique(slots[absent],return_index=True,return_inverse=True)
                batch=points[rows[absent][first]]
                values=np.asarray(compute(batch),dtype=dtype).reshape(len(batch),fields)
                data[slots_missing]=values;st['computed_points']+=len(batch)
            out[rows]=data[slots]
        st['reused_points']=st['requested_points']-st['computed_points']
        return out

    def heights(self,points,vertical_step=8):
        if isinstance(vertical_step,bool) or not isinstance(vertical_step,int) or not 1<=vertical_step<=16:
            raise ValueError('Vertical step must be an integer in 1–16')
        p=np.asarray(points);scale=4 if np.issubdtype(p.dtype,np.integer) and np.all(p%4==0) else 1
        def compute(p):
            h,b=super(CachedBackend,self).heights(p,vertical_step)
            return np.column_stack((h,b))
        out=self._sample(p,f'height_stride_{vertical_step}',scale,64,2,np.int32,-2147483648,compute)
        return out[:,0].copy(),out[:,1].copy()

    def land(self,points):
        out=self._sample(points,'exact_land',1,128,1,np.int8,-128,
                         lambda p:super(CachedBackend,self).land(p))
        return out[:,0].astype(bool)

    def cache_statistics(self):
        return {'operations':dict(self.stats),'maximum_bytes':self.limit,'peak_bytes':self.peak_bytes,'evictions':self.evictions,
                'scope':'One seed/backend instance; X/Z, operation and vertical stride kept separate.'}

    def close(self):
        self.tiles.clear();self.bytes=0
        super().close()
````

## File: src/seed_search/seeds.py

SHA-256: 7730bc5b7a6fb932212693c68940b9ccb76a9638d6753bc02130561e4caa9bf5

````python
MASK64 = (1 << 64) - 1

def parse_seed(value: str | int) -> int:
    if isinstance(value, bool):
        raise ValueError("Seed must be a signed decimal integer")
    text = str(value).strip()
    if not text or not text.lstrip("-").isdigit() or text.count("-") > 1:
        raise ValueError("Seed must be a signed decimal integer")
    seed = int(text)
    if not -(1 << 63) <= seed < (1 << 63):
        raise ValueError("Seed outside signed 64-bit range")
    return seed

def seed_from_index(index: int, run_key: int = 0) -> int:
    if not 0 <= index <= MASK64:
        raise ValueError("Candidate index outside unsigned 64-bit range")
    z = (index + run_key) & MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    z ^= z >> 31
    return z if z < (1 << 63) else z - (1 << 64)
````

## File: src/seed_search/config.py

SHA-256: fa327ef97e6de4c028122f14fe8fc1f78bcb0fe5c74c980ec874689d65eb20db

````python
"""Validate the implemented Bedrock contract before any expensive work."""
from pathlib import Path
import hashlib
import math
import yaml
from . import BACKEND_COMMIT

METHODS = {
    ('island','score_method'): 'preferred_interval_ratio',
    ('water','score_method'): 'enclosure_times_gap_fit',
    ('mountains','score_method'): 'coverage_to_target',
    ('wood','score_method'): 'surrounding_fraction_only',
    ('nether','score_method'): 'mean_capped_inverse_distance',
    ('structures','per_type_score'): 'nearest_viable_in_border',
    ('structures','secondary_aggregation'): 'mean_including_known_absences',
    ('structures','core_policy'): 'strong_preferences_not_hard_requirements',
    ('output','unknown_score_policy'): 'interval_and_separate_review_list',
}

def positive_int(v, name):
    if isinstance(v,bool) or not isinstance(v,int) or v < 1:
        raise ValueError(f'{name} must be a positive integer')

def validate_config(cfg):
    if not isinstance(cfg,dict) or cfg.get('schema_version') != 3:
        raise ValueError('Expected configuration schema_version 3')
    g=cfg['game']; s=cfg['search']
    if (g['edition'],g['target_version'],g['backend_model']) != ('bedrock','26.52','MC_26_50'):
        raise ValueError('Supported target is Bedrock 26.52 mapped explicitly to MC_26_50')
    if g['backend_commit'] != BACKEND_COMMIT or g['backend_repository'] != 'https://github.com/FragrantResult186/cubiomes-bedrock':
        raise ValueError('Configured backend identity differs from pinned source')
    if not g['require_validated_capabilities_before_large_search']:
        raise ValueError('Capability readiness gate cannot be disabled')
    if s['large_search_enabled']:
        raise ValueError('large_search_enabled cannot bypass the evidence readiness gate; leave false')
    if s['lower_bit_optimization_enabled'] or s['mode'] != 'full_64_bit_reference' or s['deterministic_mixer'] != 'splitmix64_finalizer':
        raise ValueError('Only deterministic full-64-bit reference enumeration is supported')
    if s['raster_boundary_policy'] != 'mark_unknown':
        raise ValueError('Finite raster boundaries must remain unknown')
    if not isinstance(s['run_key'],str) or not s['run_key'].isdigit() or not 0<=int(s['run_key'])<2**64:
        raise ValueError('run_key must be unsigned 64-bit decimal text')
    weights=cfg['score_weights']
    if set(weights) != {'island_size','island_openness','water','mountains','wood','overworld_structures','nether_proximity'}:
        raise ValueError('Require all seven implemented score categories')
    if any(isinstance(w,bool) or not isinstance(w,(int,float)) or not math.isfinite(w) or w<0 for w in weights.values()) or sum(weights.values())!=100:
        raise ValueError('Score weights must total 100 and be finite/nonnegative')
    if (cfg['deployment']['overworld_side_blocks'],cfg['deployment']['nether_side_blocks']) != (3008,992):
        raise ValueError('Fixed playable squares are 3008 Overworld and 992 Nether blocks')
    if cfg['overworld']['border_center_snap_blocks']!=8 or cfg['island']['conservative_land_connectivity']!=8:
        raise ValueError('Require eight-block centers and conservative eight-neighbor connectivity')
    required=cfg['structures'].get('required_overworld_types',[])
    if required not in ([],['stronghold']):raise ValueError('Supported required Overworld type is Stronghold')
    if cfg['nether']['fortress_required'] is not True:
        raise ValueError('Fortress is required')
    if cfg['nether']['bastion_required'] is not True:
        if cfg['nether']['bastion_required'] is not False or required!=['stronghold']:
            raise ValueError('Optional Bastion requires the Fortress and Stronghold policy')
        v=cfg['nether'].get('optional_bastion_proximity_weight')
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<=v<=.25:
            raise ValueError('Optional Bastion proximity weight must be in 0..0.25')
    if cfg['verification']['initial_method'] != 'chunkbase_matching_version_terrain':
        raise ValueError('Initial review requires matching-version Chunkbase with Terrain')
    if cfg['wood']['fraction_denominator']!='land_area' or cfg['wood']['island']['openness_score_method']!='one_minus_wooded_fraction' or cfg['wood']['island']['abundance_required'] or cfg['wood']['island']['preference']!='less_wooded_more_open':
        raise ValueError('Require separate island openness and surrounding land woodland')
    for keys,value in METHODS.items():
        if cfg[keys[0]][keys[1]] != value:
            raise ValueError(f'Unsupported method {keys}: expected {value}')
    fractions=cfg['structures']['category_budget_fractions']
    if set(fractions) != {'trial_chamber','stronghold','mineshaft','ancient_city','secondary_combined'} or any(not 0<=v<=1 for v in fractions.values()) or abs(sum(fractions.values())-1)>1e-9:
        raise ValueError('Structure category fractions must total one')
    secondary=cfg['structures']['secondary_types']
    if set(secondary)!= {'village','ruined_portal','shipwreck','monument','outpost'} or len(secondary)!=5:
        raise ValueError('Require the five supported secondary structure types')
    low,high=s['center_axis_bounds_blocks']
    if any(isinstance(v,bool) or not isinstance(v,int) for v in (low,high)) or low>=high or high-low+3008>14000:
        raise ValueError('Analysis envelope must fit within 14,000 blocks per axis')
    for key in ('workers','numeric_threads_per_worker','report_top_distinct_seeds','preflight_maximum_seeds','maximum_preliminary_components_per_seed','maximum_refined_centers_per_seed','maximum_refinement_patch_side_blocks'):
        positive_int(s[key],key)
    if not 1<=s['workers']<=12 or s['numeric_threads_per_worker']!=1:
        raise ValueError('Support 1–12 process workers with one numeric thread each')
    for k in ('discovery_spacing_blocks','refinement_spacing_blocks','shoreline_spacing_blocks'):
        if s[k] not in (4,8,16,32,64):
            raise ValueError('Sampling spacing must be 4, 8, 16, 32 or 64')
    if not s['discovery_spacing_blocks']>=s['refinement_spacing_blocks']>=s['shoreline_spacing_blocks']:
        raise ValueError('Sampling must become finer at each stage')
    for section,key in (('overworld','distance_score_scale_blocks'),('overworld','surrounding_range_from_shore_blocks'),('nether','full_credit_distance_blocks'),('water','angular_samples'),('mountains','minimum_height_above_water_blocks')):
        positive_int(cfg[section][key],key)
    for section,key in (('water','preferred_gap_blocks'),('island','preferred_equivalent_diameter_blocks')):
        lo,hi=cfg[section][key]
        if not 0<lo<=hi: raise ValueError(f'Invalid interval {key}')
    for section,key in (('water','preferred_enclosure_fraction'),('water','full_credit_enclosure_fraction'),('mountains','preferred_directional_fraction')):
        if not 0<cfg[section][key]<=1: raise ValueError(f'Invalid fraction {key}')
    for key in ('preferred_wooded_fraction','full_credit_wooded_fraction'):
        if not 0<cfg['wood']['surrounding_land'][key]<=1: raise ValueError(f'Invalid fraction {key}')
    if cfg['search']['maximum_refinement_patch_side_blocks']>3008: raise ValueError('Refinement patch must fit the Overworld square')
    if set(cfg['output']['candidate_files'])-{'candidate.json','overworld.png','nether.png','inspection.md'}: raise ValueError('Unsupported candidate artifact')
    if set(cfg['output']['summary_formats'])-{'json','csv'}: raise ValueError('Unsupported summary format')
    if 'optimization' in cfg:
        opt=cfg['optimization']
        original={'exact_per_seed_cache','cache_mb_per_worker','persist_report_terrain','reuse_unchanged_maps'}
        additions={'stronghold_prefilter','early_basin_bounds','reuse_raster_intermediates','combined_structure_scan','lazy_coverage_bounds','raw_mt_cache_entries'}
        if not original<=set(opt) or set(opt)-original-additions:
            raise ValueError('Unsupported optimization settings')
        if any(not isinstance(opt[k],bool) for k in ('exact_per_seed_cache','persist_report_terrain','reuse_unchanged_maps')):
            raise ValueError('Optimization flags must be booleans')
        positive_int(opt['cache_mb_per_worker'],'cache_mb_per_worker')
        if opt['cache_mb_per_worker']>128:raise ValueError('Cache is capped at 128 MiB per worker')
        if opt.get('stronghold_prefilter','review_all') not in ('review_all','defer_unpredicted'):
            raise ValueError('Stronghold prefilter must review_all or defer_unpredicted')
        if opt.get('stronghold_prefilter')=='defer_unpredicted' and required!=['stronghold']:
            raise ValueError('Fast Stronghold filtering requires Stronghold as a required structure')
        for key in ('early_basin_bounds','reuse_raster_intermediates','combined_structure_scan','lazy_coverage_bounds'):
            if key in opt and not isinstance(opt[key],bool):raise ValueError('Optimization flags must be booleans')
        entries=opt.get('raw_mt_cache_entries',0)
        if isinstance(entries,bool) or not isinstance(entries,int) or not 0<=entries<=256:raise ValueError('Raw layout cache must contain 0–256 entries')
    if 'landscapes' in cfg:
        from .landscapes import validate_landscapes
        validate_landscapes(cfg['landscapes'])
    return cfg

def load_config(path='search.example.yaml'):
    raw=Path(path).read_bytes()
    return validate_config(yaml.safe_load(raw)),hashlib.sha256(raw).hexdigest()

def discovery_grid(cfg):
    low,high=cfg['search']['center_axis_bounds_blocks']
    half=cfg['deployment']['overworld_side_blocks']//2
    step=cfg['search']['discovery_spacing_blocks']
    start=((low-half)//step)*step
    end=-((-(high+half))//step)*step
    n=(end-start)//step+1
    if n*n>100_000:
        raise ValueError('Configured discovery map exceeds 100,000 point budget')
    return start,start,n,n,step
````

## File: src/seed_search/structures.py

SHA-256: 15921e9a296787dc6926885bd3d246e0fd6abbbc3643b41655402d38672d4c2b

````python
"""Prediction statuses and square eligibility; rejection is never proof of absence."""
import math
from .backend import STRUCTURES

NETHER=('fortress','bastion')
DISPUTED_FAMILIES={'bastion','ancient_city','stronghold'}

def required_types(cfg):
    return tuple(cfg['structures'].get('required_overworld_types',()))+tuple(
        t for t in NETHER if cfg['nether'][t+'_required'])

def required_status(records,cfg):
    required=required_types(cfg)
    if all(records[t]['viable'] for t in required):
        return 'predicted_both_required' if set(required)==set(NETHER) else 'predicted_required_structures'
    # Missing Strongholds are unresolved because this enumerator is incomplete.
    if all(records[t]['raw'] or t=='stronghold' for t in required):return 'disputed_required_review'
    return 'missing_required_local_prediction'

def square(center, side):
    h=side//2
    return (center[0]-h,center[1]-h,center[0]+h,center[1]+h)

def inside(p, bounds):
    return bounds[0]<=p[0]<=bounds[2] and bounds[1]<=p[1]<=bounds[3]

def nether_center(center):
    if any(v%8 for v in center): raise ValueError('Overworld center must lie on eight-block grid')
    return (center[0]//8,center[1]//8)

def envelope_bounds(cfg):
    lo,hi=cfg['search']['center_axis_bounds_blocks']; h=1504
    ob=(lo-h,lo-h,hi+h,hi+h)
    nb=(math.floor(lo/8)-496,math.floor(lo/8)-496,math.ceil(hi/8)+496,math.ceil(hi/8)+496)
    return ob,nb

def scan_type(backend,cfg,name):
    ob,nb=envelope_bounds(cfg);bounds=nb if name in NETHER else ob
    if cfg.get('optimization',{}).get('combined_structure_scan',False):
        raw,viable=backend.structure_pair(name,bounds)
    else:raw=backend.structures(name,bounds,False);viable=backend.structures(name,bounds)
    return {'raw':raw,'viable':viable,'query_bounds':list(bounds)}

def scan_envelope(backend, cfg, initial=None):
    result=dict(initial or {})
    for name in STRUCTURES:
        if name not in result:result[name]=scan_type(backend,cfg,name)
    return result

def possible_required_centers(scans,cfg,center_box):
    """Intersection of axis-aligned center windows, with exact eight-block snapping.

    False means no *predicted* joint placement, never proof of absent Stronghold.
    Fortress center limits are converted to Overworld units exactly once.
    """
    required=required_types(cfg);boxes=[center_box]
    for typ in required:
        scale,half=(8,496) if typ in NETHER else (1,1504)
        windows=[((p[0]-half)*scale,(p[1]-half)*scale,(p[0]+half)*scale,(p[1]+half)*scale)
                 for p in scans[typ]['raw']]
        next_boxes=[]
        for a in boxes:
            for b in windows:
                x0=max(a[0],b[0]);z0=max(a[1],b[1]);x1=min(a[2],b[2]);z1=min(a[3],b[3])
                if math.ceil(x0/8)*8<=x1 and math.ceil(z0/8)*8<=z1:
                    next_boxes.append((x0,z0,x1,z1))
        boxes=next_boxes
        if not boxes:return False
    return True

def at_center(scans,center,cfg):
    nc=nether_center(center); result={}
    for name in STRUCTURES:
        reference=nc if name in NETHER else center
        bounds=square(reference,992 if name in NETHER else 3008)
        raw=[p for p in scans[name]['raw'] if inside(p,bounds)]
        viable=[p for p in scans[name]['viable'] if inside(p,bounds)]
        rejected=[p for p in raw if p not in viable]
        nearest=min(viable,key=lambda p:(math.dist(reference,p),p)) if viable else None
        required=name in required_types(cfg)
        radius={'bastion':48,'fortress':5,'trial_chamber':25,'ruined_portal':21,'outpost':12}.get(name,0)
        near_border=[list(p) for p in raw if min(p[0]-bounds[0],bounds[2]-p[0],p[1]-bounds[1],bounds[3]-p[1])<=radius+32]
        result[name]={'dimension':'nether' if name in NETHER else 'overworld','bounds':list(bounds),
                      'raw':[list(p) for p in raw],'viable':[list(p) for p in viable],
                      'rejected_raw_review':[list(p) for p in rejected],
                      'nearest_viable':list(nearest) if nearest else None,
                      'distance':math.dist(reference,nearest) if nearest else None,
                      'status':'predicted_viable' if viable else 'disputed_raw' if rejected else 'no_local_start_found',
                      'completeness':'unknown' if name=='stronghold' else 'bounded_local_model_scan',
                      'chunkbase_checked':False,'chunkbase_markers':[], 'actual_minecraft':None,
                      'accessible_footprint':'unknown','starts_near_border':near_border,
                      'review_required':required or bool(rejected) or bool(near_border) or name=='stronghold',
                      'required':required,'confirmed_required_eligible':False}
    return result,required_status(result,cfg)
````

## File: src/seed_search/geometry.py

SHA-256: ab4c5cae47e588703a5ad2d756d1a5a2131bada11a7cdabef790a35688603794

````python
"""Diagnostic connected land components; never certify real isolation."""
from __future__ import annotations
import math
import numpy as np
from scipy import ndimage

def band(value, low, high):
    return min(1.0,value/low,high/value) if value>0 else 0.0

def island_components(land: np.ndarray, x0: int, z0: int, spacing: int, center_bounds):
    labels,count=ndimage.label(land,np.ones((3,3),dtype=int))
    slices=ndimage.find_objects(labels)
    sizes=np.bincount(labels.ravel())
    result=[]
    low,high=center_bounds
    for label,sl in enumerate(slices,1):
        if sl is None:
            continue
        zs,xs=sl
        if zs.start==0 or xs.start==0 or zs.stop==land.shape[0] or xs.stop==land.shape[1]:
            continue
        area=int(sizes[label])*spacing**2
        diameter=2*math.sqrt(area/math.pi)
        rr,cc=np.nonzero(labels[sl]==label)
        xx=x0+(cc+xs.start)*spacing
        zz=z0+(rr+zs.start)*spacing
        cx,cz=float(xx.mean()),float(zz.mean())
        i=int(np.lexsort((zz,xx,(xx-cx)**2+(zz-cz)**2))[0])
        center=(int(xx[i]),int(zz[i]))
        if not(low<=center[0]<=high and low<=center[1]<=high):
            continue
        result.append({"center":list(center),"predicted_area_blocks2":area,
                       "equivalent_diameter":diameter,"evidence":"predicted",
                       "isolation_verified":False,"size_score":band(diameter,300,700)})
    return sorted(result,key=lambda p:(-p["size_score"],p["center"]))


def components(land,x0,z0,spacing,center_bounds):
    """Keep finite-edge uncertainty rather than declaring ocean beyond a raster."""
    labels,count=ndimage.label(land,np.ones((3,3),int))
    sizes=np.bincount(labels.ravel()); result=[]
    for ident,sl in enumerate(ndimage.find_objects(labels),1):
        if sl is None: continue
        zs,xs=sl; rr,cc=np.nonzero(labels[sl]==ident)
        xx=x0+(cc+xs.start)*spacing; zz=z0+(rr+zs.start)*spacing
        centroid=(float(xx.mean()),float(zz.mean()))
        eligible=(xx%8==0)&(zz%8==0)&(xx>=center_bounds[0])&(xx<=center_bounds[1])&(zz>=center_bounds[0])&(zz<=center_bounds[1])
        if not eligible.any(): continue
        xx=xx[eligible];zz=zz[eligible]
        i=np.lexsort((zz,xx,(xx-centroid[0])**2+(zz-centroid[1])**2))[0]
        diameter=2*math.sqrt(sizes[ident]*spacing**2/math.pi)
        touches=zs.start==0 or xs.start==0 or zs.stop==land.shape[0] or xs.stop==land.shape[1]
        result.append({'label':ident,'center':[int(xx[i]),int(zz[i])],'centroid':list(centroid),
                       'area':int(sizes[ident])*spacing**2,'equivalent_diameter':diameter,
                       'bounds':[x0+xs.start*spacing,z0+zs.start*spacing,x0+(xs.stop-1)*spacing,z0+(zs.stop-1)*spacing],
                       'touches_raster_boundary':touches,'isolation':'unknown' if touches else 'predicted_separated',
                       'center_displacement':math.dist((int(xx[i]),int(zz[i])),centroid)})
    return labels,result

def largest_gap(mask):
    a=np.asarray(mask,dtype=bool)
    if a.all(): return 360.0
    if not a.any(): return 0.0
    doubled=np.concatenate((a,a)); best=run=0
    for v in doubled:
        run=run+1 if v else 0;best=max(best,run)
    return min(len(a),best)*360/len(a)

def angular_metrics(height,island,center,x0,z0,step,cfg,unknown=None,high_mask=None):
    """Outermost component exit handles ponds/crescents; gaps measured from shore."""
    if unknown is None: unknown=np.zeros_like(island)
    n=cfg['water']['angular_samples']; reach=cfg['overworld']['surrounding_range_from_shore_blocks']
    gaps=[]; high_heights=[]; high_distances=[]; enclosed=[]; high=[]; unresolved=[]
    max_distance=math.hypot(*height.shape)*step
    for angle in np.arange(n)*2*math.pi/n:
        d=np.arange(0,max_distance+step,step/2)
        xx=np.rint((center[0]+np.cos(angle)*d-x0)/step).astype(int)
        zz=np.rint((center[1]+np.sin(angle)*d-z0)/step).astype(int)
        valid=(xx>=0)&(zz>=0)&(xx<height.shape[1])&(zz<height.shape[0])
        xx,zz,d=xx[valid],zz[valid],d[valid]
        indices=np.flatnonzero(island[zz,xx])
        if not len(indices): enclosed.append(False);high.append(False);unresolved.append(True);continue
        shore=indices[-1]; dist=d-d[shore]
        zone=(np.arange(len(d))>shore)&(dist<=reach)
        if not zone.any(): enclosed.append(False);high.append(False);unresolved.append(True);continue
        ext=zone&(height[zz,xx]>=63)&~island[zz,xx]&~unknown[zz,xx]
        unknown_ray=bool(unknown[zz[zone],xx[zone]].any() or dist[-1]<reach)
        unresolved.append(unknown_ray);enclosed.append(bool(ext.any()))
        if ext.any(): gaps.append(float(dist[np.flatnonzero(ext)[0]]))
        mountains=ext&(height[zz,xx]>=63+cfg['mountains']['minimum_height_above_water_blocks'])
        if high_mask is not None: mountains &= high_mask[zz,xx]
        high.append(bool(mountains.any()))
        if mountains.any():
            at=np.flatnonzero(mountains)[0]; high_heights.append(int(height[zz[at],xx[at]])-63);high_distances.append(float(dist[at]))
    ef=sum(enclosed)/n;hf=sum(high)/n;uf=sum(unresolved)/n
    return {'rays':n,'unknown_rays':sum(unresolved),'enclosure_fraction_bounds':[ef,min(1,ef+uf)],
            'high_terrain_fraction_bounds':[hf,min(1,hf+uf)],
            'median_gap':float(np.median(gaps)) if gaps else None,
            'gap_percentiles':np.percentile(gaps,[10,50,90]).tolist() if gaps else None,
            'preferred_gap_fraction':sum(cfg['water']['preferred_gap_blocks'][0]<=v<=cfg['water']['preferred_gap_blocks'][1] for v in gaps)/n,
            'largest_water_opening_degrees':largest_gap(~np.array(enclosed)&~np.array(unresolved)),
            'largest_mountain_gap_degrees':largest_gap(~np.array(high)&~np.array(unresolved)),
            'median_high_relative_height':float(np.median(high_heights)) if high_heights else None,
            'median_mountain_distance_from_shore':float(np.median(high_distances)) if high_distances else None,
            'enclosure_preference_met':ef>=cfg['water']['preferred_enclosure_fraction']}
````

## File: src/seed_search/terrain.py

SHA-256: 165571d71482913c4f361dd0e209ef259385dea09952175772f9e6b91b0ac261

````python
"""Finite density rasters, adaptive sea-level columns, and coast connectivity."""
import numpy as np
from scipy import ndimage
from .geometry import components

LIMITS=['Raw density omits caves, aquifers, decoration and actual chunk interpolation.',
        'Sea-level uncertainty includes the observed five-block predictor height error.',
        'One-block coast samples remain density predictions, not exact liquid blocks.',
        'Discovery/refinement budgets can miss islands; deferred components are reported.']

def sample_points(backend,points,vertical_step=8):
    points=np.asarray(points,dtype=np.int32)
    hs=[];bs=[]
    for i in range(0,len(points),100_000):
        h,b=backend.heights(points[i:i+100_000],vertical_step);hs.append(h);bs.append(b)
    if not hs:return np.array([],dtype=np.int32),np.array([],dtype=np.int32)
    return np.concatenate(hs),np.concatenate(bs)

def raster(backend,bounds,step,adaptive=True):
    x0,z0,x1,z1=bounds
    xa=np.arange(x0,x1+1,step,dtype=np.int32);za=np.arange(z0,z1+1,step,dtype=np.int32)
    xx,zz=np.meshgrid(xa,za);pts=np.column_stack((xx.ravel(),zz.ravel()))
    h,b=sample_points(backend,pts)
    more=0
    if adaptive:
        near=np.abs(h-63)<=5;more=int(near.sum())
        if more:h[near],b[near]=sample_points(backend,pts[near],1)
    shape=(len(za),len(xa))
    return {'height':h.reshape(shape),'biomes':b.reshape(shape),'bounds':[x0,z0,int(xa[-1]),int(za[-1])],
            'step':step,'points':len(pts),'sea_level_stride1_points':more}

def coast_component(backend,discovered,cfg,analysis_bounds):
    step=cfg['search']['shoreline_spacing_blocks']; pad=64
    a=discovered['bounds'];cap=cfg['search']['maximum_refinement_patch_side_blocks']
    bounds=[max(analysis_bounds[0],(a[0]-pad)//step*step),max(analysis_bounds[1],(a[1]-pad)//step*step),
            min(analysis_bounds[2],-(-(a[2]+pad)//step)*step),min(analysis_bounds[3],-(-(a[3]+pad)//step)*step)]
    if max(bounds[2]-bounds[0],bounds[3]-bounds[1])>cap:
        return None,{'reason':'refinement_patch_budget','center':discovered['center'],'isolation':'unknown'}
    r=raster(backend,bounds,step)
    land=r['height']>=63
    # Sample every integer column in a coast band. Interior replication is an
    # explicit approximation; all transition cells are overwritten by stride-one
    # density columns, so narrow connections at sampled coasts are not skipped.
    transition=ndimage.binary_dilation(land,iterations=2)^ndimage.binary_erosion(land,iterations=2,border_value=0)
    highland=np.repeat(np.repeat(land,step,axis=0),step,axis=1)[:(land.shape[0]-1)*step+1,:(land.shape[1]-1)*step+1]
    band=np.repeat(np.repeat(transition,step,axis=0),step,axis=1)[:highland.shape[0],:highland.shape[1]]
    rr,cc=np.nonzero(band)
    pts=np.column_stack((bounds[0]+cc,bounds[1]+rr))
    h=sample_land(backend,pts)
    highland[rr,cc]=h
    sampled=band.copy(); extra=0
    # Follow newly revealed narrow land connections through initially coarse
    # water cells until the coast closes or reaches the finite patch edge.
    while True:
        frontier=ndimage.binary_dilation(highland,iterations=step)&~ndimage.binary_erosion(highland,iterations=step,border_value=0)&~sampled
        fr,fc=np.nonzero(frontier)
        if not len(fr):break
        fh=sample_land(backend,np.column_stack((bounds[0]+fc,bounds[1]+fr)))
        before=highland[fr,fc].copy();highland[fr,fc]=fh;sampled[fr,fc]=True;extra+=len(fr)
        if np.array_equal(before,highland[fr,fc]):break
    labels,cs=components(highland,bounds[0],bounds[1],1,cfg['search']['center_axis_bounds_blocks'])
    # The discovery anchor may become water. Use nearest overlapping component
    # and keep anchor displacement visible, rather than inventing land at center.
    anchor=discovered['center'];candidates=[]
    for c in cs:
        if c['touches_raster_boundary']:continue
        if c['bounds'][0]<=anchor[0]+64 and c['bounds'][2]>=anchor[0]-64 and c['bounds'][1]<=anchor[1]+64 and c['bounds'][3]>=anchor[1]-64:
            candidates.append(c)
    if not candidates:
        return None,{'reason':'density_connected_or_no_closed_component','center':anchor,'isolation':'unknown',
                     'density_points':r['points']+len(pts)+extra+r['sea_level_stride1_points']}
    c=min(candidates,key=lambda c:(np.linalg.norm(np.array(c['center'])-anchor),-c['area'],c['center']))
    c['coast_one_block_columns']=len(pts)+extra;c['coarse_anchor']=anchor
    selected=labels==c['label']
    c['sea_level_uncertain_coast_samples']=int(np.count_nonzero(np.abs(r['height']-63)<=5))
    c['isolation_verified']=False
    c['evidence']='predicted_density_with_one_block_coast_sampling'
    return {'component':c,'mask':selected,'height':r['height'],'biomes':r['biomes'],
            'bounds':bounds,'step':step,'points':r['points']+len(pts)+extra+r['sea_level_stride1_points']},None


def island_mask_on_raster(coast,terrain):
    x0,z0=terrain['bounds'][:2];step=terrain['step']
    xx,zz=np.meshgrid(np.arange(terrain['height'].shape[1])*step+x0,np.arange(terrain['height'].shape[0])*step+z0)
    cc=xx-coast['bounds'][0];rr=zz-coast['bounds'][1]
    valid=(cc>=0)&(rr>=0)&(cc<coast['mask'].shape[1])&(rr<coast['mask'].shape[0])
    mask=np.zeros_like(valid);mask[valid]=coast['mask'][rr[valid],cc[valid]]
    return mask


def sample_land(backend,points):
    points=np.asarray(points,dtype=np.int32);out=[]
    for i in range(0,len(points),100_000):
        batch=points[i:i+100_000]
        out.append(backend.land(batch) if hasattr(backend,'land') else backend.heights(batch,1)[0]>=63)
    return np.concatenate(out) if out else np.array([],dtype=bool)


def preliminary_component(backend,discovered,cfg,analysis_bounds):
    """Cheap 16-block density topology before one-block coast work."""
    step=cfg['search']['refinement_spacing_blocks'];pad=128
    a=discovered['bounds']
    bounds=[max(analysis_bounds[0],(a[0]-pad)//step*step),max(analysis_bounds[1],(a[1]-pad)//step*step),
            min(analysis_bounds[2],-(-(a[2]+pad)//step)*step),min(analysis_bounds[3],-(-(a[3]+pad)//step)*step)]
    if max(bounds[2]-bounds[0],bounds[3]-bounds[1])>cfg['search']['maximum_refinement_patch_side_blocks']:
        return None,{'reason':'preliminary_patch_budget','center':discovered['center'],'isolation':'unknown'},0
    r=raster(backend,bounds,step)
    _,cs=components(r['height']>=63,*bounds[:2],step,cfg['search']['center_axis_bounds_blocks'])
    # Retain components intersecting the original discovery box; nearby unrelated
    # land is not substituted for the intended island.
    cs=[c for c in cs if not(c['bounds'][2]<a[0] or c['bounds'][0]>a[2] or c['bounds'][3]<a[1] or c['bounds'][1]>a[3])]
    closed=[c for c in cs if not c['touches_raster_boundary']]
    points=r['points']+r['sea_level_stride1_points']
    if not closed:
        return None,{'reason':'preliminary_density_connected_or_no_closed_land','center':discovered['center'],'isolation':'unknown'},points
    c=min(closed,key=lambda c:(np.linalg.norm(np.array(c['center'])-discovered['center']),-c['area'],c['center']))
    c['discovery_anchor']=discovered['center']
    return c,None,points
````

## File: src/seed_search/wood.py

SHA-256: f0dcea3ada050362d7fb7b719d15904d2aafb64c3753004e9ad04fe25f3e1f49

````python
"""Explicit biome groups for diagnostics, without invented density weights."""
import numpy as np
from .backend import biome_name

WOODLAND_NAMES=frozenset({
    "forest","flower_forest","birch_forest","old_growth_birch_forest","dark_forest",
    "taiga","old_growth_pine_taiga","old_growth_spruce_taiga","snowy_taiga",
    "jungle","bamboo_jungle","cherry_grove","grove","mangrove_swamp","swamp",
    "pale_garden","dappled_forest",
})
SPARSE_WOOD_NAMES=frozenset({"sparse_jungle","windswept_forest","savanna",
                           "savanna_plateau","windswept_savanna","wooded_badlands"})

def wood_masks(biomes):
    ids=np.unique(biomes)
    dense=[i for i in ids if biome_name(i) in WOODLAND_NAMES]
    sparse=[i for i in ids if biome_name(i) in SPARSE_WOOD_NAMES]
    return np.isin(biomes,dense),np.isin(biomes,sparse)

def surrounding_score(fraction, full_credit=.60):
    return min(1.0,max(0.0,fraction)/full_credit)

def openness_score(fraction):
    return 1-min(1.0,max(0.0,fraction))
````

## File: src/seed_search/landscapes.py

SHA-256: f9a92568fdbdf099f92e2b73b4e668050a13ac7823cbbc9086c7e0649fe87c62

````python
"""Finite searches for enclosed islands, ocean islands and dry mountain basins.

Ocean/Deep Dark coverage nominates locations; density verifies the terrain.
No biome hint establishes isolation or buildability.
"""
import math
import os
import platform
import resource
import time
import numpy as np
from scipy import ndimage
from .backend import Backend,biome_name
from .cache import CachedBackend
from .config import discovery_grid
from .geometry import components,band,largest_gap
from .terrain import raster,sample_points,preliminary_component,coast_component,island_mask_on_raster,LIMITS
from .structures import scan_envelope,scan_type,possible_required_centers,at_center,square,nether_center,inside,required_types
from .scoring import landscape_scores,structure_scores,weighted_score

KINDS=('enclosed_island','ocean_island','mountain_basin')


def validate_landscapes(settings):
    expected={'enabled','ocean_window_side_blocks','minimum_ocean_fraction','flat_radius_blocks',
              'maximum_flat_relief_blocks','maximum_flat_slope','minimum_dry_fraction',
              'ring_radius_blocks','minimum_ring_relative_height_blocks','minimum_ring_fraction',
              'deep_dark_y','deep_dark_inner_side_blocks','deep_dark_outer_side_blocks',
              'deep_dark_spacing_blocks','deep_dark_policy'}
    if set(settings)!=expected:raise ValueError('Unsupported landscape settings')
    kinds=settings['enabled']
    if not kinds or len(kinds)!=len(set(kinds)) or set(kinds)-set(KINDS):raise ValueError('Invalid landscape types')
    for k in ('ocean_window_side_blocks','flat_radius_blocks','maximum_flat_relief_blocks','ring_radius_blocks',
              'minimum_ring_relative_height_blocks','deep_dark_inner_side_blocks','deep_dark_outer_side_blocks','deep_dark_spacing_blocks'):
        v=settings[k]
        if isinstance(v,bool) or not isinstance(v,int) or v<=0:raise ValueError(f'Invalid landscape integer {k}')
    for k in ('minimum_ocean_fraction','maximum_flat_slope','minimum_dry_fraction','minimum_ring_fraction'):
        v=settings[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=1:
            raise ValueError(f'Invalid landscape fraction {k}')
    if not 32<=settings['flat_radius_blocks']<=256 or not settings['flat_radius_blocks']<settings['ring_radius_blocks']<=1000:
        raise ValueError('Flat/ring radii exceed the finite landscape budget')
    if settings['ocean_window_side_blocks']>3008 or not settings['deep_dark_inner_side_blocks']<=settings['deep_dark_outer_side_blocks']<=512:
        raise ValueError('Coverage windows exceed their finite budgets')
    if settings['deep_dark_spacing_blocks'] not in (8,16,32,64) or settings['deep_dark_y']!=-32 or settings['deep_dark_policy']!='rank_only':
        raise ValueError('Deep Dark at Y=-32 is a ranking hint, never a hard terrain filter')


def ocean_ids(biomes):
    return [int(i) for i in np.unique(biomes) if 'ocean' in biome_name(i)]


def coverage_at(coarse,center,grid,side):
    x0,z0,nx,nz,step=grid;half=side//2
    xa=x0+np.arange(nx)*step;za=z0+np.arange(nz)*step
    xm=(xa>=center[0]-half)&(xa<=center[0]+half);zm=(za>=center[1]-half)&(za<=center[1]+half)
    complete=center[0]-half>=xa[0] and center[0]+half<=xa[-1] and center[1]-half>=za[0] and center[1]+half<=za[-1]
    b=coarse['biomes'][np.ix_(zm,xm)]
    return float(np.isin(b,ocean_ids(b)).mean()) if b.size else 0.0,complete


def deep_dark_hint(backend,center,settings):
    rows={}
    for name in ('inner','outer'):
        half=settings[f'deep_dark_{name}_side_blocks']//2;step=settings['deep_dark_spacing_blocks']
        axis=np.arange(-half,half+1,step)
        ids=[backend.biome(int(center[0]+x),settings['deep_dark_y'],int(center[1]+z)) for z in axis for x in axis]
        rows[name+'_fraction']=sum(biome_name(i)=='deep_dark' for i in ids)/len(ids)
        rows[name+'_points']=len(ids)
    # Outer includes the inner window, matching the screenshot.
    rows['contrast']=rows['outer_fraction']-rows['inner_fraction']
    rows['y']=settings['deep_dark_y'];rows['use']='rank_only_not_terrain_proof'
    return rows


def xy_raster(terrain):
    h=terrain['height'];step=terrain['step'];x0,z0=terrain['bounds'][:2]
    return np.meshgrid(x0+np.arange(h.shape[1])*step,z0+np.arange(h.shape[0])*step)


def raster_intermediates(terrain):
    h=terrain['height'];step=terrain['step'];x,z=xy_raster(terrain)
    dry=h>=68;labels,_=ndimage.label(dry,np.ones((3,3),int))
    gz,gx=np.gradient(h.astype(float),step)
    return {'x':x,'z':z,'dry':dry,'labels':labels,'slope':np.hypot(gx,gz),
            'local_range':ndimage.maximum_filter(h,size=5)-ndimage.minimum_filter(h,size=5)}


def flat_metrics(terrain,center,settings,context=None):
    h=terrain['height'];step=terrain['step'];context=context or raster_intermediates(terrain)
    x,z=context['x'],context['z']
    disk=np.hypot(x-center[0],z-center[1])<=settings['flat_radius_blocks']
    dry,labels=context['dry'],context['labels']
    col=round((center[0]-terrain['bounds'][0])/step);row=round((center[1]-terrain['bounds'][1])/step)
    ident=labels[row,col] if 0<=row<h.shape[0] and 0<=col<h.shape[1] else 0
    connected=(labels==ident)&dry if ident else np.zeros_like(dry)
    values=h[disk&connected]
    fraction=float((disk&connected).sum()/disk.sum()) if disk.any() else 0.0
    relief=float(np.percentile(values,90)-np.percentile(values,10)) if len(values) else None
    slope=context['slope']
    gentle=float((disk&connected&(slope<=settings['maximum_flat_slope'])).sum()/disk.sum()) if disk.any() else 0.0
    flat=disk&connected&(slope<=settings['maximum_flat_slope'])
    passed=fraction>=settings['minimum_dry_fraction'] and relief is not None and relief<=settings['maximum_flat_relief_blocks'] and gentle>=settings['minimum_dry_fraction']
    return {'dry_connected_fraction':fraction,'gentle_ground_fraction':gentle,'inner_height_p90_minus_p10':relief,
            'inner_height_median':float(np.median(values)) if len(values) else None,
            'flat_ground_preference_met':bool(passed),'flat_ground_area_blocks2':int(flat.sum())*step**2,
            'flat_radius_blocks':settings['flat_radius_blocks'],'sea_level_safety_margin_blocks':5,
            'buildability_evidence':'sampled_density_relief_and_slope; actual ground requires review'},flat,connected


def ring_metrics(terrain,center,settings,connected,inner_height):
    h=terrain['height'];step=terrain['step'];x0,z0=terrain['bounds'][:2]
    hits=[];dry_hits=[];heights=[];distances=[];unknown=[]
    n=180;reach=settings['ring_radius_blocks'];minimum=settings['flat_radius_blocks']
    threshold=max(113,(inner_height or 63)+settings['minimum_ring_relative_height_blocks'])
    for angle in np.arange(n)*2*math.pi/n:
        distance=np.arange(minimum,reach+1,step/2)
        x=np.rint((center[0]+np.cos(angle)*distance-x0)/step).astype(int)
        z=np.rint((center[1]+np.sin(angle)*distance-z0)/step).astype(int)
        valid=(x>=0)&(z>=0)&(x<h.shape[1])&(z<h.shape[0])
        unknown.append(not bool(valid.all()));x=x[valid];z=z[valid];distance=distance[valid]
        high=h[z,x]>=threshold;hits.append(bool(high.any()))
        dry_high=high&connected[z,x];dry_hits.append(bool(dry_high.any()))
        if high.any():
            at=np.flatnonzero(high)[0];heights.append(float(h[z[at],x[at]]-63));distances.append(float(distance[at]))
    fraction=sum(hits)/n;dry_fraction=sum(dry_hits)/n;uncertain=sum(unknown)/n
    return {'ring_fraction_bounds':[fraction,min(1,fraction+uncertain)],'ring_dry_connected_fraction':dry_fraction,
            'ring_unknown_rays':sum(unknown),'ring_preference_met':fraction>=settings['minimum_ring_fraction'],
            'dry_mountain_basin_preference_met':dry_fraction>=settings['minimum_ring_fraction'],
            'largest_ring_gap_degrees':largest_gap(~np.array(hits)&~np.array(unknown)),
            'ring_height_threshold':threshold,'ring_median_high_relative_height':float(np.median(heights)) if heights else None,
            'ring_median_distance':float(np.median(distances)) if distances else None}


def build_centers(terrain,allowed,center_bounds,limit=1,context=None):
    """Find dry, low-relief areas, rather than placing an ocean base on a summit."""
    h=terrain['height'];step=terrain['step'];context=context or raster_intermediates(terrain)
    flat=allowed&(h>=68)&(context['slope']<=.3)&(context['local_range']<=24)
    _,cs=components(flat,*terrain['bounds'][:2],step,center_bounds)
    return sorted(cs,key=lambda c:(-c['area'],c['center']))[:limit]


def basin_necessary_bound(backend,center,cfg):
    """Prove failure cheaply; never treat local connectivity as global connectivity.

    Include the original anchor and the same eight allowed +/-256 recenters.
    Halo preserves gradients/5x5 nomination kernels and full-raster lattice parity.
    Dry/gentle counts ignore connectivity, so they are upper bounds, not new tests.
    Ring hits ignore connectivity and use the smallest possible threshold (113).
    """
    s=cfg['landscapes'];step=cfg['search']['refinement_spacing_blocks']
    half=math.ceil((256+s['flat_radius_blocks']+2*step)/(2*step))*2*step
    if half>=1504:return {'impossible':False,'points':0,'reason':'local_bound_not_smaller'}
    terrain=raster(backend,square(center,half*2),step)
    context=raster_intermediates(terrain);x,z=context['x'],context['z']
    allowed=np.hypot(x-center[0],z-center[1])<=256
    sites=build_centers(terrain,allowed,cfg['search']['center_axis_bounds_blocks'],8,context)
    centers=[list(p) for p in dict.fromkeys(tuple(p) for p in [center]+[v['center'] for v in sites])];possible=[]
    for candidate in centers:
        disk=np.hypot(x-candidate[0],z-candidate[1])<=s['flat_radius_blocks']
        n=int(disk.sum());dry=int((disk&context['dry']).sum())
        gentle=int((disk&context['dry']&(context['slope']<=s['maximum_flat_slope'])).sum())
        if n and dry/n>=s['minimum_dry_fraction'] and gentle/n>=s['minimum_dry_fraction']:
            possible.append(candidate)
    count=terrain['points']+terrain['sea_level_stride1_points']
    result={'impossible':not bool(possible),'points':count,'tested_centers':centers,
            'reason':'dry_or_gentle_upper_bound','coverage_points':0}
    if result['impossible'] or not cfg.get('optimization',{}).get('lazy_coverage_bounds',False):return result
    # Bound overhead on survivors; unfinished rays remain possible, never misses.
    budget=5000;needed=math.ceil(180*s['minimum_ring_fraction']);origin=(center[0]-1504,center[1]-1504)
    distance=np.arange(s['flat_radius_blocks'],s['ring_radius_blocks']+1,step/2)
    for candidate in possible:
        hits=misses=0
        for first in range(0,180,8):
            batch=[];sizes=[]
            for bearing in range(first,min(180,first+8)):
                angle=bearing*2*math.pi/180
                xx=np.rint((candidate[0]+np.cos(angle)*distance-origin[0])/step).astype(int)*step+origin[0]
                zz=np.rint((candidate[1]+np.sin(angle)*distance-origin[1])/step).astype(int)*step+origin[1]
                points=np.unique(np.column_stack((xx,zz)),axis=0);batch.append(points);sizes.append(len(points))
            points=np.concatenate(batch)
            if result['coverage_points']+len(points)>budget:
                result.update(impossible=False,reason='coverage_budget_unresolved');return result
            heights,_=sample_points(backend,points)
            # Near-sea adaptive correction cannot create a 113-high mountain,
            # but preserve the exact raster contract rather than relying on it.
            near=np.abs(heights-63)<=5
            if near.any():heights[near],_=sample_points(backend,points[near],1)
            result['coverage_points']+=len(points);result['points']+=len(points)+int(near.sum())
            for ray in np.split(heights,np.cumsum(sizes)[:-1]):
                if (ray>=113).any():hits+=1
                else:misses+=1
            if hits>=needed:result.update(impossible=False,reason='ring_possible');return result
            if misses>180-needed:break
        else:
            result.update(impossible=False,reason='ring_possible');return result
    result.update(impossible=True,reason='ring_coverage_upper_bound');return result


def coarse_basin_sites(coarse,grid,settings,center_bounds,labels,center_heights=None):
    """Vectorized nomination; a wide relief window would erase small valleys.

    Evaluate coarse mountain bearings around land points, group neighboring
    nominations, and choose the lowest center with the strongest ring hint.
    Density/slope/connection checks occur later at 16-block spacing.
    """
    h=coarse['approx_height'];x0,z0,nx,nz,step=grid
    reference=h if center_heights is None else center_heights
    xx,zz=np.meshgrid(x0+np.arange(nx)*step,z0+np.arange(nz)*step)
    possible=(h>=68)&(xx>=center_bounds[0])&(xx<=center_bounds[1])&(zz>=center_bounds[0])&(zz<=center_bounds[1])
    rows,cols=np.nonzero(possible);fraction=np.zeros_like(h,dtype=float)
    angles=np.arange(36)*2*math.pi/36
    distance=np.arange(max(step,settings['flat_radius_blocks']),settings['ring_radius_blocks']+1,step)
    dx=np.rint(np.cos(angles)[:,None]*distance/step).astype(int)
    dz=np.rint(np.sin(angles)[:,None]*distance/step).astype(int)
    for start in range(0,len(rows),512):
        r=rows[start:start+512];c=cols[start:start+512]
        rr=r[:,None,None]+dz;cc=c[:,None,None]+dx
        valid=(rr>=0)&(cc>=0)&(rr<nz)&(cc<nx)
        values=h[np.clip(rr,0,nz-1),np.clip(cc,0,nx-1)]
        high=(values>=np.maximum(113,reference[r,c]+settings['minimum_ring_relative_height_blocks'])[:,None,None])&valid
        fraction[r,c]=high.any(axis=2).mean(axis=1)
    _,regions=components(fraction>=settings['minimum_ring_fraction']*.5,x0,z0,step,center_bounds)
    # Label again to preserve the membership of every actual coarse nomination.
    region_labels,_=ndimage.label(fraction>=settings['minimum_ring_fraction']*.5,np.ones((3,3),int))
    out=[]
    for component in regions:
        r,c=np.nonzero(region_labels==component['label'])
        world_x=x0+c*step;world_z=z0+r*step
        eligible=(world_x>=center_bounds[0])&(world_x<=center_bounds[1])&(world_z>=center_bounds[0])&(world_z<=center_bounds[1])
        r=r[eligible];c=c[eligible]
        at=np.lexsort((c,r,reference[r,c],-fraction[r,c]))[0]
        center=[int(x0+c[at]*step),int(z0+r[at]*step)]
        out.append({**component,'center':center,'coarse_ring_fraction':float(fraction[r[at],c[at]]),
                    'discovered_land_label':int(labels[r[at],c[at]])})
    return out


def ocean_preliminary(backend,source,cfg,analysis_bounds):
    step=cfg['search']['refinement_spacing_blocks'];half=cfg['search']['maximum_refinement_patch_side_blocks']//2
    center=source['center']
    bounds=[max(analysis_bounds[0],(center[0]-half)//step*step),max(analysis_bounds[1],(center[1]-half)//step*step),
            min(analysis_bounds[2],(center[0]+half)//step*step),min(analysis_bounds[3],(center[1]+half)//step*step)]
    t=raster(backend,bounds,step);labels,cs=components(t['height']>=63,*bounds[:2],step,cfg['search']['center_axis_bounds_blocks'])
    a=source['bounds'];matching=[c for c in cs if not c['touches_raster_boundary'] and not(c['bounds'][2]<a[0] or c['bounds'][0]>a[2] or c['bounds'][3]<a[1] or c['bounds'][1]>a[3])]
    count=t['points']+t['sea_level_stride1_points']
    if not matching:return None,None,{'reason':'ocean_density_not_closed_within_finite_patch','center':center,'isolation':'unknown'},count
    c=min(matching,key=lambda c:(math.dist(c['center'],center),-c['area'],c['center']))
    sites=build_centers(t,labels==c['label'],cfg['search']['center_axis_bounds_blocks'])
    # A 64-block discovery lattice can miss the small floor of a mountain ring.
    # For a promising coarse ring, nominate again from the density raster already
    # sampled here. This adds no native terrain queries.
    if source.get('coarse_ring_fraction',0)>0:
        s={**cfg['landscapes'],'flat_radius_blocks':32}
        local_grid=(bounds[0],bounds[1],t['height'].shape[1],t['height'].shape[0],step)
        radius=max(1,32//step);rr,cc=np.mgrid[-radius:radius+1,-radius:radius+1]
        median_ground=ndimage.median_filter(t['height'],footprint=rr**2+cc**2<=radius**2)
        local=coarse_basin_sites({'approx_height':t['height']},local_grid,s,cfg['search']['center_axis_bounds_blocks'],labels,median_ground)
        local=[v for v in local if v['discovered_land_label']==c['label']]
        if local:
            site=min(local,key=lambda v:(-v['coarse_ring_fraction'],v['center']))
            if site['coarse_ring_fraction']>=s['minimum_ring_fraction']:
                c['build_center_method']='density_ring_nomination'
                return c,site['center'],None,count
    return c,sites[0]['center'] if sites else c['center'],None,count


def round_robin(groups,limit):
    out=[]
    for i in range(max((len(v) for v in groups.values()),default=0)):
        for kind,values in groups.items():
            if i<len(values):out.append((kind,values[i]))
            if len(out)>=limit:return out
    return out


def analyze_landscapes(job):
    index,seed,cfg=job[:3];cache_root=job[3] if len(job)>3 else None
    start=time.perf_counter();times={k:0.0 for k in ('discovery','structures','proxy','preliminary','coast','landscape','scoring')}
    counts={};near=[];candidates=[];settings=cfg['landscapes'];grid=discovery_grid(cfg)
    bounds=(grid[0],grid[1],grid[0]+(grid[2]-1)*grid[4],grid[1]+(grid[3]-1)*grid[4])
    opt=cfg.get('optimization',{});fast=opt.get('stronghold_prefilter')=='defer_unpredicted'
    backend=CachedBackend(seed,opt['cache_mb_per_worker'],opt.get('raw_mt_cache_entries',0)) if opt.get('exact_per_seed_cache') else Backend(seed,opt.get('raw_mt_cache_entries',0))
    counts.update(discovery_points=0,discovery_components=0,preliminary_attempts=0,preliminary_density_points=0,
                  refinement_attempts=0,coast_density_points=0,landscape_density_points=0,deferred_components=0,
                  early_structure_deferred=0,early_basin_attempts=0,early_basin_rejections=0,early_basin_points=0,
                  nominated_by_type={k:0 for k in settings['enabled']})
    def finish(b):
        counts['scored_centers']=len(candidates)
        counts['scored_by_type']={k:sum(c['landscape_type']==k for c in candidates) for k in settings['enabled']}
        counts['predicted_required_centers']=sum(c['nether_status'] in ('predicted_required_structures','predicted_both_required') for c in candidates)
        counts['predicted_both_nether_centers']=sum(all(c['structures'][t]['viable'] for t in ('fortress','bastion')) for c in candidates)
        counts['disputed_required_centers']=sum(c['nether_status']=='disputed_required_review' for c in candidates)
        counts['all_three_core_centers']=sum(all(c['structures'][t]['viable'] for t in ('trial_chamber','stronghold','mineshaft')) for c in candidates)
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
        return {'index':index,'seed':str(seed),'candidates':candidates,'near_misses':near,'counts':counts,'stage_seconds':times,
                'total_seconds':time.perf_counter()-start,'worker_pid':os.getpid(),'worker_peak_rss_mb':rss,
                'filter_policy':opt.get('stronghold_prefilter','review_all'),
                'cache':b.cache_statistics() if isinstance(b,CachedBackend) else None}
    with backend as b:
        initial={}
        if fast:
            t=time.perf_counter();initial['stronghold']=scan_type(b,cfg,'stronghold')
            if initial['stronghold']['raw']:
                for typ in required_types(cfg):
                    if typ not in initial:initial[typ]=scan_type(b,cfg,typ)
            times['structures']+=time.perf_counter()-t
            lo,hi=cfg['search']['center_axis_bounds_blocks']
            if not initial['stronghold']['raw'] or not possible_required_centers(initial,cfg,(lo,lo,hi,hi)):
                counts['early_structure_deferred']=1
                near.append({'reason':'deferred_seed_no_joint_required_prediction','isolation':'unknown',
                             'center_bounds':[lo,lo,hi,hi],'stronghold_completeness':'unknown',
                             'review':'Fast heuristic; no native prediction is not proof of absence. Re-run with stronghold_prefilter: review_all.'})
                return finish(b)
        t=time.perf_counter();coarse=b.grid(*grid)
        coarse_labels,cs=components(coarse['approx_height']>=63,*grid[:2],grid[4],cfg['search']['center_axis_bounds_blocks'])
        times['discovery']=time.perf_counter()-t
        counts.update(discovery_points=coarse['biomes'].size,discovery_components=len(cs))
        t=time.perf_counter();scans=scan_envelope(b,cfg,initial);times['structures']+=time.perf_counter()-t
        def fortress_possible(c):
            a=c['bounds'];nb=(math.floor((a[0]-64)/8)-496,math.floor((a[1]-64)/8)-496,
                             math.ceil((a[2]+64)/8)+496,math.ceil((a[3]+64)/8)+496)
            return any(inside(p,nb) for p in scans['fortress']['raw'])
        def priority(c):
            a=c['bounds'];ob=(a[0]-1568,a[1]-1568,a[2]+1568,a[3]+1568)
            return (not fortress_possible(c),not any(inside(p,ob) for p in scans['stronghold']['raw']))
        group_started=time.perf_counter()
        closed=[c for c in cs if not c['touches_raster_boundary']]
        groups={k:[] for k in settings['enabled']}
        basin_sites=coarse_basin_sites(coarse,grid,settings,cfg['search']['center_axis_bounds_blocks'],coarse_labels) if any(k in groups for k in ('ocean_island','mountain_basin')) else []
        ring_by_component={}
        for site in basin_sites:
            label=site['discovered_land_label']
            ring_by_component[label]=max(ring_by_component.get(label,0),site['coarse_ring_fraction'])
        if 'enclosed_island' in groups:
            groups['enclosed_island']=sorted(closed,key=lambda c:(*priority(c),-band(c['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),c['center']))
        if 'ocean_island' in groups:
            for c in closed:
                ocean,complete=coverage_at(coarse,c['center'],grid,settings['ocean_window_side_blocks'])
                if complete and ocean>=settings['minimum_ocean_fraction']:
                    groups['ocean_island'].append({**c,'coarse_ocean_fraction':ocean,'coarse_ring_fraction':ring_by_component.get(c['label'],0)})
            groups['ocean_island'].sort(key=lambda c:(*priority(c),-c['coarse_ring_fraction'],-band(c['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),-c['coarse_ocean_fraction'],c['center']))
        if 'mountain_basin' in groups:
            groups['mountain_basin']=basin_sites
            groups['mountain_basin'].sort(key=lambda c:(*priority(c),-c['coarse_ring_fraction'],-c['area'],c['center']))
        times['proxy']+=time.perf_counter()-group_started
        counts['nominated_by_type']={k:len(v) for k,v in groups.items()}
        if fast:
            lo,hi=cfg['search']['center_axis_bounds_blocks']
            for kind,values in groups.items():
                retained=[]
                for c in values:
                    a=c['bounds'];margin=256 if kind=='mountain_basin' else 64
                    box=(max(lo,a[0]-margin),max(lo,a[1]-margin),min(hi,a[2]+margin),min(hi,a[3]+margin))
                    if possible_required_centers(scans,cfg,box):retained.append(c)
                    else:
                        counts['early_structure_deferred']+=1
                        near.append({'landscape_type':kind,'center':c['center'],'reason':'deferred_component_no_joint_required_prediction',
                                     'isolation':'unknown','stronghold_completeness':'unknown',
                                     'review':'Nomination envelope heuristic; retain for review_all recovery, not proof of absence.'})
                groups[kind]=retained
        # Rank the finite nominations using the screenshot's cheap hint. The
        # hint is not a filter, including when Bedrock cave biomes disagree.
        t=time.perf_counter();limit=cfg['search']['maximum_preliminary_components_per_seed']
        nominations=round_robin(groups,limit);prepared={k:[] for k in groups}
        for kind,c in nominations:
            hint=deep_dark_hint(b,c['center'],settings) if kind=='mountain_basin' else None
            prepared[kind].append((c,hint))
        times['proxy']+=time.perf_counter()-t
        counts['preliminary_attempts']=len(nominations);counts['preliminary_density_points']=0
        viable={k:[] for k in groups};pre_cache={}
        for kind,values in prepared.items():
            for c,hint in values:
                t=time.perf_counter()
                if kind=='mountain_basin':pc=c;build_center=c['center'];err=None;points=0
                else:
                    key=(kind,tuple(c['center']))
                    if key in pre_cache:pc,build_center,err,points=pre_cache[key];points=0
                    elif kind=='ocean_island':pc,build_center,err,points=ocean_preliminary(b,c,cfg,bounds);pre_cache[key]=(pc,build_center,err,points)
                    else:pc,err,points=preliminary_component(b,c,cfg,bounds);build_center=pc['center'] if pc else None;pre_cache[key]=(pc,build_center,err,points)
                times['preliminary']+=time.perf_counter()-t;counts['preliminary_density_points']+=points
                if err:near.append({'landscape_type':kind,**err})
                else:
                    pc['coarse_ring_fraction']=c.get('coarse_ring_fraction',0)
                    if kind=='ocean_island':
                        t=time.perf_counter();hint=deep_dark_hint(b,build_center,settings);times['proxy']+=time.perf_counter()-t
                    viable[kind].append((pc,build_center,hint))
        # Hint breaks geometric priority ties; it never outranks required starts.
        for kind,values in viable.items():
            if kind=='mountain_basin':values.sort(key=lambda v:(*priority(v[0]),-v[0]['coarse_ring_fraction'],-(v[2]['contrast'] if v[2] else 0),v[1]))
            else:values.sort(key=lambda v:(*priority(v[0]),-v[0].get('coarse_ring_fraction',0) if kind=='ocean_island' else 0,-band(v[0]['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),-(v[2]['contrast'] if v[2] else 0),v[1]))
        budget=cfg['search']['maximum_refined_centers_per_seed'];selected=round_robin(viable,budget)
        counts['refinement_attempts']=len(selected);counts['coast_density_points']=counts['landscape_density_points']=0
        counts['deferred_components']=sum(len(v) for v in viable.values())-len(selected)
        near.extend({'landscape_type':kind,'center':c['center'],'reason':'deferred_preliminary_budget','isolation':'unknown'} for kind,values in groups.items() for c in values[len(prepared[kind]):])
        selected_keys={(kind,tuple(v[1])) for kind,v in selected}
        near.extend({'landscape_type':kind,'center':v[1],'reason':'deferred_refinement_budget','isolation':'unknown'} for kind,values in viable.items() for v in values if (kind,tuple(v[1])) not in selected_keys)
        seen=set();coasts={}
        for kind,(c,proposed_center,hint) in selected:
            coast=None;t=time.perf_counter()
            if kind=='mountain_basin' and opt.get('early_basin_bounds',False):
                bound=basin_necessary_bound(b,proposed_center,cfg)
                counts['early_basin_attempts']+=1;counts['early_basin_points']+=bound['points']
                times['landscape']+=time.perf_counter()-t;t=time.perf_counter()
                if bound['impossible']:
                    counts['early_basin_rejections']+=1
                    near.append({'landscape_type':kind,'center':proposed_center,'reason':'basin_necessary_bound_failed','bound':bound})
                    continue
            if kind!='mountain_basin':
                key=tuple(c['center'])
                if key in coasts:coast,err=coasts[key]
                else:
                    coast,err=coast_component(b,c,cfg,bounds);coasts[key]=(coast,err)
                    counts['coast_density_points']+=coast['points'] if coast else err.get('density_points',0)
                if err:near.append({'landscape_type':kind,**err});times['coast']+=time.perf_counter()-t;continue
                c=dict(coast['component']);center=c['center'] if kind=='enclosed_island' else proposed_center
                row=center[1]-coast['bounds'][1];col=center[0]-coast['bounds'][0]
                if not(0<=row<coast['mask'].shape[0] and 0<=col<coast['mask'].shape[1] and coast['mask'][row,col]):center=c['center']
                c['center']=center
            else:center=proposed_center
            times['coast']+=time.perf_counter()-t
            if (kind,tuple(center)) in seen:continue
            if fast and kind!='mountain_basin' and not possible_required_centers(scans,cfg,(*center,*center)):
                counts['early_structure_deferred']+=1
                near.append({'landscape_type':kind,'center':center,'reason':'deferred_exact_center_no_joint_required_prediction',
                             'stronghold_completeness':'unknown','isolation':'unknown'})
                continue
            t=time.perf_counter();terrain=raster(b,square(center,3008),cfg['search']['refinement_spacing_blocks'])
            times['landscape']+=time.perf_counter()-t;counts['landscape_density_points']+=terrain['points']+terrain['sea_level_stride1_points']
            t=time.perf_counter();context=raster_intermediates(terrain) if opt.get('reuse_raster_intermediates',False) else None
            flat,build_mask,connected=flat_metrics(terrain,center,settings,context)
            ring_settings={**settings,'flat_radius_blocks':32} if kind=='ocean_island' else settings
            ring_flat,_,_=flat_metrics(terrain,center,ring_settings,context) if kind=='ocean_island' else (flat,None,None)
            ring=ring_metrics(terrain,center,ring_settings,connected,ring_flat['inner_height_median'])
            ring['ring_inner_radius_blocks']=ring_settings['flat_radius_blocks']
            if kind=='mountain_basin' and not(flat['flat_ground_preference_met'] and ring['dry_mountain_basin_preference_met']):
                # Refine a coarse anchor onto a nearby density-flat floor. Reuse
                # the raster already sampled; reject the whole nomination only
                # after testing the finite nearby floor candidates.
                x,z=xy_raster(terrain);nearby=np.hypot(x-center[0],z-center[1])<=256
                sites=build_centers(terrain,nearby,cfg['search']['center_axis_bounds_blocks'],limit=8,context=context)
                alternatives=[]
                for site in sites:
                    f,m,conn=flat_metrics(terrain,site['center'],settings,context)
                    if not f['flat_ground_preference_met']:continue
                    rr=ring_metrics(terrain,site['center'],settings,conn,f['inner_height_median'])
                    if rr['dry_mountain_basin_preference_met']:alternatives.append((site,f,rr))
                if alternatives:
                    site,_,_=min(alternatives,key=lambda v:(-v[2]['ring_dry_connected_fraction'],v[1]['inner_height_p90_minus_p10'],v[0]['center']))
                    times['scoring']+=time.perf_counter()-t;center=site['center']
                    t=time.perf_counter();terrain=raster(b,square(center,3008),cfg['search']['refinement_spacing_blocks'])
                    times['landscape']+=time.perf_counter()-t;counts['landscape_density_points']+=terrain['points']+terrain['sea_level_stride1_points']
                    t=time.perf_counter();context=raster_intermediates(terrain) if opt.get('reuse_raster_intermediates',False) else None
                    flat,build_mask,connected=flat_metrics(terrain,center,settings,context)
                    ring=ring_metrics(terrain,center,settings,connected,flat['inner_height_median'])
                    ring['ring_inner_radius_blocks']=settings['flat_radius_blocks']
            if (kind,tuple(center)) in seen:
                times['scoring']+=time.perf_counter()-t;continue
            seen.add((kind,tuple(center)));structures,status=at_center(scans,center,cfg)
            if fast and status=='disputed_required_review':
                counts['early_structure_deferred']+=1
                near.append({'landscape_type':kind,'center':center,'reason':'deferred_exact_center_no_joint_required_prediction',
                             'stronghold_completeness':'unknown','isolation':'unknown'})
                times['scoring']+=time.perf_counter()-t;continue
            island=island_mask_on_raster(coast,terrain) if coast else build_mask
            if not island.any():
                near.append({'landscape_type':kind,'center':center,'reason':'no_sampled_build_ground'});times['scoring']+=time.perf_counter()-t;continue
            if kind=='mountain_basin':
                if not flat['flat_ground_preference_met'] or not ring['dry_mountain_basin_preference_met']:
                    near.append({'landscape_type':kind,'center':center,'reason':'density_not_dry_flat_mountain_basin',**flat,**ring});times['scoring']+=time.perf_counter()-t;continue
                c={'center':center,'bounds':[center[0]-settings['flat_radius_blocks'],center[1]-settings['flat_radius_blocks'],center[0]+settings['flat_radius_blocks'],center[1]+settings['flat_radius_blocks']],
                   'area':flat['flat_ground_area_blocks2'],'equivalent_diameter':2*math.sqrt(flat['flat_ground_area_blocks2']/math.pi),
                   'isolation':'not_required_dry_connected_basin','isolation_verified':False,'evidence':'finite_density_raster'}
            scores,metrics=landscape_scores(terrain,island,c,cfg)
            ocean_fraction=None;water_fraction=None
            if kind=='ocean_island':
                x,z=xy_raster(terrain);half=settings['ocean_window_side_blocks']//2
                window=(abs(x-center[0])<=half)&(abs(z-center[1])<=half)
                ocean_fraction=float(np.isin(terrain['biomes'][window],ocean_ids(terrain['biomes'])).mean())
                water_fraction=float((terrain['height'][window]<63).mean())
                if ocean_fraction<settings['minimum_ocean_fraction'] or water_fraction<settings['minimum_ocean_fraction']:
                    near.append({'landscape_type':kind,'center':center,'reason':'density_or_biomes_not_majority_ocean','ocean_fraction':ocean_fraction,'water_fraction':water_fraction});times['scoring']+=time.perf_counter()-t;continue
                # Nearby forests on the same ocean island count as supplies.
                # Build-area openness/size are distinct from whole island size.
                supply_mask=build_mask if build_mask.any() else island
                build_component={**c,'equivalent_diameter':2*math.sqrt(max(1,int(supply_mask.sum())*terrain['step']**2)/math.pi)}
                build_scores,supply=landscape_scores(terrain,supply_mask,build_component,cfg)
                for key in ('island_openness','wood'):scores[key]=build_scores[key]
                metrics['whole_island_equivalent_diameter']=c['equivalent_diameter']
                metrics['build_area_woodland_fraction']=supply['island_woodland_fraction']
                metrics['nearby_supply_woodland_fraction']=supply['surrounding_woodland_fraction']
                metrics['nearby_supply_forest_coordinates']=supply['forest_patch_coordinates']
                scores['water']=min(1,water_fraction/.75)
                scores['mountains']=ring['ring_fraction_bounds'][0] if not ring['ring_unknown_rays'] else None
            elif kind=='mountain_basin':
                scores['water']=min(flat['dry_connected_fraction'],flat['gentle_ground_fraction'])
                scores['mountains']=min(1,ring['ring_dry_connected_fraction']/settings['minimum_ring_fraction'])
                # These labels are explicit in the metrics/report; no water
                # enclosure or island-separation requirement applies to a basin.
                metrics['water_score_meaning']='dry_gentle_ground_fraction'
                metrics['largest_mountain_gap_degrees']=ring['largest_ring_gap_degrees']
            metrics.update(flat);metrics.update(ring);metrics['landscape_type']=kind
            metrics['ocean_biome_fraction']=ocean_fraction;metrics['ocean_water_fraction']=water_fraction
            metrics['deep_dark_hint']=hint
            ss,factors,sinterval=structure_scores(structures,cfg);scores.update(ss);score=weighted_score(scores,cfg,sinterval)
            times['scoring']+=time.perf_counter()-t
            remaining=['Matching-version Terrain shoreline and build-ground review','Required Fortress and Stronghold markers inside exact squares',
                       'Actual structure footprints and terrain remain unknown']
            if kind=='ocean_island':remaining+=['Whole ocean island separation','Wood supply on the island or nearby land']
            elif kind=='mountain_basin':remaining+=['Dry connected flat floor without an inner island or moat','Mountain ring appearance']
            else:remaining+=['Inner island separation','Water and surrounding mountains','External woodland abundance']
            candidate={'seed':str(seed),'index':index,'center':center,'nether_center':list(nether_center(center)),
                       'landscape_type':kind,'bounds':{'overworld':list(square(center,3008)),'nether':list(square(nether_center(center),992))},
                       'island':c,'metrics':metrics,'structures':structures,'structure_score_factors':factors,'score':score,
                       'nether_status':status,'required_structure_types':list(required_types(cfg)),
                       'selection_status':'unreviewed_local_prediction','chunkbase_checked':False,'actual_minecraft':None,
                       'remaining_review':remaining,'approximation_limits':LIMITS+['Deep Dark and ocean biome coverage are hints, not exact terrain proofs.'],
                       'spawn_proposal':{'x':center[0],'z':center[1],'y':None,'safety':'requires inspection'}}
            if cache_root and opt.get('persist_report_terrain'):
                from .report_cache import save_terrain
                save_terrain(cache_root,seed,candidate['bounds']['overworld'],terrain,cfg)
            candidates.append(candidate)
        return finish(b)
````

## File: src/seed_search/scoring.py

SHA-256: e18beff6e5e51c16c651a2f5a085f405d7bc1a7ac0f586351eb11e399797bafa

````python
"""Configured normalized scores and explicit intervals for missing measurements."""
import math
import numpy as np
from scipy import ndimage
from .geometry import band, angular_metrics
from .wood import wood_masks


def landscape_scores(terrain,island,component,cfg):
    h=terrain['height'];b=terrain['biomes'];step=terrain['step']
    dense,sparse=wood_masks(b);land=h>=63
    distance=ndimage.distance_transform_edt(~island,sampling=step)
    outside=land&~island&(distance<=cfg['overworld']['surrounding_range_from_shore_blocks'])
    count=int(outside.sum()); icount=int(island.sum())
    if not icount: raise ValueError('Island disappeared on landscape raster')
    island_wood=float((dense&island).sum()/icount);extwood=float((dense&outside).sum()/count) if count else 0.0
    sparse_fraction=float((sparse&outside).sum()/count) if count else 0.0
    from .backend import biome_name
    high_mask=None
    if not cfg['mountains']['snowy_summits_allowed']:
        snow=[i for i in np.unique(b) if any(v in biome_name(i) for v in ('snowy','frozen','ice_spikes'))]
        high_mask=~np.isin(b,snow)
    rays=angular_metrics(h,island,component['center'],*terrain['bounds'][:2],step,cfg,high_mask=high_mask)
    known_rays=rays['unknown_rays']==0
    gap=rays['median_gap']; enclosure=rays['enclosure_fraction_bounds'][0]
    size=band(component['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks'])
    water=min(1,enclosure/cfg['water']['full_credit_enclosure_fraction'])*band(gap,*cfg['water']['preferred_gap_blocks']) if gap is not None else 0.0
    scores={'island_size':size,'island_openness':1-island_wood,
            'water':water if known_rays else None,
            'mountains':min(1,rays['high_terrain_fraction_bounds'][0]/cfg['mountains']['preferred_directional_fraction']) if known_rays else None,
            'wood':min(1,extwood/cfg['wood']['surrounding_land']['full_credit_wooded_fraction'])}
    patches,patch_count=ndimage.label(outside&dense,np.ones((3,3),int)); forest=[]
    for sl in ndimage.find_objects(patches):
        if sl is None:continue
        zz,xx=sl
        forest.append({'x':terrain['bounds'][0]+(xx.start+xx.stop-1)//2*step,
                       'z':terrain['bounds'][1]+(zz.start+zz.stop-1)//2*step})
    rel=h[island]
    metrics={'island_woodland_fraction':island_wood,'surrounding_woodland_fraction':extwood,
             'surrounding_sparse_wood_fraction':sparse_fraction,'surrounding_land_area_blocks2':count*step**2,
             'surrounding_wooded_area_blocks2':int((dense&outside).sum())*step**2,
             'wood_preference_met':extwood>=cfg['wood']['surrounding_land']['preferred_wooded_fraction'],
             'forest_patch_coordinates':forest,'wood_evidence':'surface_biome_proxy_not_tree_counts',
             'island_height_percentiles':np.percentile(rel,[10,50,90]).tolist(),
             'island_height_range':[int(rel.min()),int(rel.max())],
             'buildability':'manual_Chunkbase_terrain_review_required',
             'island_span_blocks':[component['bounds'][2]-component['bounds'][0],component['bounds'][3]-component['bounds'][1]],
             'biome_inventory':{},**rays}
    from .backend import biome_name
    metrics['biome_inventory']={biome_name(i):int((b==i).sum()) for i in np.unique(b)}
    return scores,metrics


def structure_scores(structures,cfg):
    budget=cfg['structures']['category_budget_fractions']; scale=cfg['overworld']['distance_score_scale_blocks']
    factors={}
    for name,r in structures.items():
        if name in ('fortress','bastion'):continue
        factors[name]=math.exp(-r['distance']/scale) if r['distance'] is not None else None if r['rejected_raw_review'] or name=='stronghold' else 0.0
    known=sum(budget[t]*factors[t] for t in ('trial_chamber','stronghold','mineshaft','ancient_city') if factors[t] is not None)
    unknown=sum(budget[t] for t in ('trial_chamber','stronghold','mineshaft','ancient_city') if factors[t] is None)
    types=cfg['structures']['secondary_types']; secondary=budget['secondary_combined']/len(types)
    known+=sum(secondary*factors[t] for t in types if factors[t] is not None)
    unknown+=sum(secondary for t in types if factors[t] is None)
    ns=[]
    for t in ('fortress','bastion'):
        distance=structures[t]['distance']
        ns.append(min(1,cfg['nether']['full_credit_distance_blocks']/distance) if distance else 1 if distance==0 else None)
    if cfg['nether']['bastion_required']:
        nether=sum(ns)/2 if all(v is not None for v in ns) else None
    else:
        optional_weight=cfg['nether']['optional_bastion_proximity_weight']
        # An optional unresolved/missing Bastion must not create an unknown
        # required category or hide a Fortress/Stronghold candidate.
        nether=(1-optional_weight)*ns[0]+optional_weight*(ns[1] or 0) if ns[0] is not None else None
    return {'overworld_structures':known if unknown==0 else None,'nether_proximity':nether},factors,[known,known+unknown]


def weighted_score(scores,cfg,structure_interval=None):
    lower=upper=0.0;unknown=[]
    # SQLite persists configuration as sorted JSON; YAML insertion order must
    # not change floating-point accumulation or unknown-component ordering.
    for name,weight in sorted(cfg['score_weights'].items()):
        value=scores[name]
        if value is None:
            unknown.append(name)
            if name=='overworld_structures' and structure_interval:
                lower+=weight*structure_interval[0];upper+=weight*structure_interval[1]
            else:upper+=weight
        else:
            if not 0<=value<=1:raise ValueError(f'Invalid normalized score {name}')
            lower+=weight*value;upper+=weight*value
    return {'total':lower if not unknown else None,'interval':[lower,upper],'components':scores,'unknown_components':unknown}


def ranking_key(c):
    m=c['metrics'];s=c['score']
    return (-(s['total'] if s['total'] is not None else s['interval'][0]),
            m['largest_mountain_gap_degrees'],-(m['median_high_relative_height'] or 0),
            m['median_mountain_distance_from_shore'] if m['median_mountain_distance_from_shore'] is not None else float('inf'),
            int(c['seed']),*c['center'])


def distinct_rank(candidates,limit):
    # Never compare an interval as a known total. Each list has its own ranking.
    lists={ 'ranked':[],'review':[],'near_misses':[]}
    for c in sorted(candidates,key=ranking_key):
        group='near_misses' if c['nether_status']=='missing_required_local_prediction' else 'review' if c['score']['total'] is None or c['nether_status']=='disputed_required_review' else 'ranked'
        if len(lists[group])<limit and c['seed'] not in {v['seed'] for v in lists[group]}:lists[group].append(c)
    return lists
````

## File: src/seed_search/search.py

SHA-256: 3a6f771c4d95c1bb032c2cd1e739326247d378d5168612d45511c33f4f1c7bfa

````python
"""Deterministic finite full-seed pipeline; only the parent writes checkpoints."""
import os
import time
import resource
import platform
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from multiprocessing import get_context
import numpy as np
from .backend import Backend
from .config import discovery_grid,validate_config
from .geometry import components,band
from .structures import scan_envelope,at_center,square,nether_center
from .terrain import coast_component,preliminary_component,raster,island_mask_on_raster,LIMITS
from .scoring import landscape_scores,structure_scores,weighted_score,distinct_rank
from .seeds import seed_from_index,parse_seed
from .storage import Store,backend_identity,semantic_hash,SCHEMA
from .preflight import save_json,metadata


def analyze_seed(job):
    index,seed,cfg=job[:3]
    if 'landscapes' in cfg:
        from .landscapes import analyze_landscapes
        return analyze_landscapes(job)
    start=time.perf_counter();times={};counts={};near=[];candidates=[]
    grid=discovery_grid(cfg)
    analysis_bounds=(grid[0],grid[1],grid[0]+(grid[2]-1)*grid[4],grid[1]+(grid[3]-1)*grid[4])
    with Backend(seed) as b:
        t=time.perf_counter();coarse=b.grid(*grid)
        _,cs=components(coarse['approx_height']>=63,*grid[:2],grid[4],cfg['search']['center_axis_bounds_blocks'])
        counts['discovery_points']=coarse['biomes'].size;counts['discovery_components']=len(cs)
        times['discovery']=time.perf_counter()-t
        t=time.perf_counter();scans=scan_envelope(b,cfg);times['structures']=time.perf_counter()-t
        bounded=[c for c in cs if not c['touches_raster_boundary']]
        near.extend({'center':c['center'],'reason':'finite_discovery_boundary','isolation':'unknown'} for c in cs if c['touches_raster_boundary'])
        # Cheap required-target screening covers every possible center in the
        # component plus discovery displacement margin, rather than origin only.
        # Keep one representative rejection per seed for filter audits.
        possible=[];missing=[]
        for component in bounded:
            cb=component['bounds']; margin=64
            nb=(int(np.floor((cb[0]-margin)/8))-496,int(np.floor((cb[1]-margin)/8))-496,
                int(np.ceil((cb[2]+margin)/8))+496,int(np.ceil((cb[3]+margin)/8))+496)
            from .structures import inside
            if all(any(inside(p,nb) for p in scans[t]['raw']) for t in ('fortress','bastion') if cfg['nether'][t+'_required']):
                possible.append(component)
            else:missing.append(component)
        preference=lambda c:(-band(c['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),c['center'])
        possible.sort(key=preference);missing.sort(key=preference)
        counts['early_required_target_screened_components']=len(bounded)
        counts['early_missing_required_components']=len(missing)
        near.extend({'center':c['center'],'reason':'no_required_local_raw_in_possible_center_neighborhood','isolation':'unknown'} for c in missing)
        bounded=possible+missing[:1]
        counts['preliminary_density_points']=0
        counts['preliminary_attempts']=min(len(bounded),cfg['search']['maximum_preliminary_components_per_seed'])
        times['preliminary']=0.0; preliminary=[];pre_seen=set()
        for c in bounded[:cfg['search']['maximum_preliminary_components_per_seed']]:
            t=time.perf_counter(); pc,rejection,points=preliminary_component(b,c,cfg,analysis_bounds)
            times['preliminary']+=time.perf_counter()-t;counts['preliminary_density_points']+=points
            if rejection:near.append(rejection)
            elif tuple(pc['center']) not in pre_seen:
                pre_seen.add(tuple(pc['center']));preliminary.append(pc)
        near.extend({'center':c['center'],'reason':'deferred_preliminary_budget','isolation':'unknown'} for c in bounded[cfg['search']['maximum_preliminary_components_per_seed']:])
        counts['preliminary_closed_components']=len(preliminary)
        preliminary.sort(key=preference);bounded=preliminary
        budget=cfg['search']['maximum_refined_centers_per_seed']
        near.extend({'center':c['center'],'reason':'deferred_refinement_budget','isolation':'unknown','discovery_diameter':c['equivalent_diameter']} for c in bounded[budget:])
        counts['refinement_attempts']=min(budget,len(bounded));counts['deferred_components']=max(0,len(bounded)-budget)
        counts['coast_density_points']=counts['landscape_density_points']=0
        times['coast']=times['landscape']=times['scoring']=0.0
        seen=set()
        for c in bounded[:budget]:
            t=time.perf_counter();coast,rejection=coast_component(b,c,cfg,analysis_bounds);times['coast']+=time.perf_counter()-t
            if rejection:
                near.append(rejection);counts['coast_density_points']+=rejection.get('density_points',0);continue
            cc=coast['component'];center=cc['center']
            counts['coast_density_points']+=coast['points']
            if tuple(center) in seen:continue
            seen.add(tuple(center));structure,status=at_center(scans,center,cfg)
            t=time.perf_counter();terr=raster(b,square(center,3008),cfg['search']['refinement_spacing_blocks'])
            times['landscape']+=time.perf_counter()-t;counts['landscape_density_points']+=terr['points']+terr['sea_level_stride1_points']
            mask=island_mask_on_raster(coast,terr)
            if not mask.any():near.append({'center':center,'reason':'island_below_landscape_grid_resolution','isolation':'unknown'});continue
            t=time.perf_counter();scores,metrics=landscape_scores(terr,mask,cc,cfg)
            ss,factors,sinterval=structure_scores(structure,cfg);scores.update(ss)
            score=weighted_score(scores,cfg,sinterval);times['scoring']+=time.perf_counter()-t
            review=['Terrain-enabled shoreline separation','Settlement buildability','Surrounding mountain appearance',
                    'Extensive accessible woodland on external land/slopes','Required Nether markers and border access','Actual structure footprints remain unknown']
            if status!='predicted_both_required':review.append(status)
            if score['unknown_components']:review.append('Unknown scores: '+', '.join(score['unknown_components']))
            candidate={'seed':str(seed),'index':index,'center':center,'nether_center':list(nether_center(center)),
                       'bounds':{'overworld':list(square(center,3008)),'nether':list(square(nether_center(center),992))},
                       'island':cc,'metrics':metrics,'structures':structure,'structure_score_factors':factors,
                       'nether_status':status,'score':score,'chunkbase_checked':False,'actual_minecraft':None,
                       'selection_status':'unreviewed_local_prediction','remaining_review':review,
                       'approximation_limits':LIMITS,'spawn_proposal':{'x':center[0],'z':center[1],'y':None,'safety':'requires inspection'}}
            candidates.append(candidate)
        counts['scored_centers']=len(candidates)
        counts['predicted_both_nether_centers']=sum(c['nether_status']=='predicted_both_required' for c in candidates)
        counts['disputed_required_centers']=sum(c['nether_status']=='disputed_required_review' for c in candidates)
        core=('trial_chamber','stronghold','mineshaft')
        counts['core_structure_centers']={t:sum(bool(c['structures'][t]['viable']) for c in candidates) for t in core}
        counts['all_three_core_centers']=sum(all(c['structures'][t]['viable'] for t in core) for c in candidates)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
    return {'index':index,'seed':str(seed),'candidates':candidates,'near_misses':near,'counts':counts,
            'stage_seconds':times,'total_seconds':time.perf_counter()-start,'worker_pid':os.getpid(),'worker_peak_rss_mb':rss}


def run_search(cfg,config_hash,output,count=10,start_index=0,workers=None,seeds=None,resume=False,readiness=None,dry_run=False,stop_after=None):
    validate_config(cfg)
    workers=cfg['search']['workers'] if workers is None else workers
    if not isinstance(workers,int) or not 1<=workers<=12:raise ValueError('Workers must be in 1–12')
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=2**64 or not 0<=start_index<2**64 or start_index+count>2**64:
        raise ValueError('Finite index interval must not wrap unsigned 64-bit range')
    if seeds is not None:
        seeds=[parse_seed(s) for s in seeds]
        if len(set(seeds))!=len(seeds) or not seeds:raise ValueError('Supplied seeds must be nonempty and unique')
        count=len(seeds)
    # Bounded pilots <=1000 are authorized by the handoff. Anything larger needs
    # the measured evidence gate; a YAML flag alone never enables it.
    if count>1000:
        from .readiness import check_readiness
        check_readiness(readiness,cfg,config_hash,count)
    identity={'schema':SCHEMA,'config':cfg,'config_sha256':config_hash,'semantic_config_sha256':semantic_hash(cfg),
              'backend':backend_identity(),'start_index':start_index,'count':count,
              'sequence':'supplied' if seeds is not None else 'splitmix64_finalizer','seeds':[str(s) for s in seeds] if seeds else None,
              'evidence_policy':'chunkbase_matching_version_terrain','readiness':str(Path(readiness).resolve()) if readiness else None}
    if dry_run:
        if resume:
            store=Store(output,identity,resume=True);done=store.completed();store.close()
        else:done=set()
        return {'dry_run':True,'would_start_sweep':False,'count':count,'start_index':start_index,'workers':workers,'completed':len(done),'identity':identity}
    store=Store(output,identity,resume=resume);done=store.completed();began=time.perf_counter();batch=[]
    save_json(store.run/'configuration.json',{'original_config_sha256':config_hash,'semantic_sha256':semantic_hash(cfg),'config':cfg})
    if stop_after is not None and not 1<=stop_after<=count:raise ValueError('stop-after must be in 1..count')
    indices=(i for i in range(start_index,start_index+count) if i not in done)
    # Keep only a bounded number of futures: a million-seed run must not enqueue
    # a million jobs or materialize its full seed list.
    def job(i):
        value=(i,seeds[i-start_index] if seeds is not None else seed_from_index(i,int(cfg['search']['run_key'])),cfg)
        return (*value,str(store.run.resolve()/'terrain-cache')) if cfg.get('optimization',{}).get('persist_report_terrain') else value
    try:
        with ProcessPoolExecutor(max_workers=workers,mp_context=get_context('spawn')) as pool:
            pending={};finished=0
            def submit():
                if stop_after is not None and finished+len(pending)>=stop_after:return False
                try:i=next(indices)
                except StopIteration:return False
                j=job(i);pending[pool.submit(analyze_seed,j)]=(i,j[1]);return True
            for _ in range(workers*2):
                if not submit():break
            while pending:
                ready,_=wait(pending,return_when=FIRST_COMPLETED)
                for future in ready:
                    i,seed=pending.pop(future);r=future.result();store.save(i,seed,r);batch.append(r);finished+=1
                    print(f'Completed index {i}, seed {seed}: {r["counts"]["scored_centers"]} centers, {r["total_seconds"]:.2f}s',flush=True)
                while len(pending)<workers*2 and submit():pass
        results=store.results();analysis_wall=time.perf_counter()-began
        from .reports import export_search
        summary=export_search(store.run,results,cfg,config_hash,identity)
        wall=time.perf_counter()-began
        parent_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
        invocation={'completed_this_invocation':len(batch),'wall_seconds':wall,'effective_seconds_per_seed':wall/len(batch) if batch else None,
                    'analysis_wall_seconds':analysis_wall,'report_wall_seconds':wall-analysis_wall,'parent_peak_rss_mb':parent_rss,
                    'workers_requested':workers,'actual_worker_pids':sorted({r['worker_pid'] for r in batch}),
                    'worker_peak_rss_mb':max((r['worker_peak_rss_mb'] for r in batch),default=0),
                    'stage_seconds_summed':{k:sum(r['stage_seconds'][k] for r in batch) for k in (batch[0]['stage_seconds'] if batch else [])},
                    'completed_total':len(results),'requested_total':count,'complete':len(results)==count}
        number=len(list(store.run.glob('invocation-*.json')))
        save_json(store.run/f'invocation-{number:03d}.json',invocation)
        save_json(store.run/'run.json',{'metadata':metadata(config_hash),'identity':identity,'summary':summary,'last_invocation':invocation})
        return invocation
    finally:store.close()
````

## File: src/seed_search/storage.py

SHA-256: c2253524fdb651922d09431429ef0999ce6ec772a0c5b3999f3bb5ae4ca6ff80

````python
"""Parent-owned atomic SQLite checkpoints, independent of worker completion order."""
import hashlib
import json
import sqlite3
from pathlib import Path
from .backend import model_metadata

SCHEMA=1
ROOT=Path(__file__).resolve().parents[2]

def backend_identity():
    # Prediction/checkpoint identity excludes rendering and readiness assembly.
    # Those files are verified separately as hashed readiness artifacts; editing
    # a plot title must not invalidate every completed seed prediction.
    modules=('__init__','backend','cache','landscapes','config','geometry','seeds','wood','terrain','structures','scoring','storage','search','review')
    paths=[ROOT/'native/bridge.c',ROOT/'native/bridge.h',ROOT/'vendor/backend.json',*[ROOT/f'src/seed_search/{name}.py' for name in modules]]
    from . import _native
    paths.append(Path(_native.__file__))
    return {'model':model_metadata(),'sha256':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}

def semantic_hash(cfg):
    # Worker count/output depth do not change prediction semantics, but persisted
    # config is compared in full on resume to reject surprise changes.
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Store:
    def __init__(self,run,identity=None,resume=False):
        self.run=Path(run)
        db=self.run/'checkpoint.sqlite'
        if not resume and db.exists():raise ValueError('Run already exists; use resume or a new output directory')
        if resume and not db.exists():raise ValueError('No checkpoint exists to resume')
        self.run.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(db)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS seeds (idx TEXT PRIMARY KEY,seed TEXT NOT NULL,result TEXT NOT NULL)')
        if not resume:
            with self.db:self.db.execute('INSERT INTO meta VALUES (?,?)',('identity',json.dumps(identity,sort_keys=True)))
        self.identity=json.loads(self.db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0])
        if resume and identity is not None and self.identity!=identity:
            self.close();raise ValueError('Incompatible resume: configuration, backend, seed sequence or evidence differs')
    def completed(self):return {int(v[0]) for v in self.db.execute('SELECT idx FROM seeds')}
    def save(self,index,seed,result):
        if str(result['seed'])!=str(seed) or result['index']!=index:raise ValueError('Worker index/seed mismatch')
        with self.db:self.db.execute('INSERT INTO seeds VALUES (?,?,?)',(str(index),str(seed),json.dumps(result,allow_nan=False)))
    def results(self):
        rows=[json.loads(v[0]) for v in self.db.execute('SELECT result FROM seeds')]
        return sorted(rows,key=lambda r:r['index'])
    def close(self):self.db.close()
````

## File: src/seed_search/review.py

SHA-256: ac0795b98d48e7e1de4530c9f3553e7be7d0603851794e43fea84131a99ac078

````python
"""Recorded actual website review, kept separate from local and game evidence."""
import copy
import json
from pathlib import Path
from .seeds import parse_seed
from .structures import inside,required_types
from .preflight import save_json


def landscape_review_fields(kind):
    if kind=='ocean_island':return ('island_separated','ocean_setting','nearby_wood_abundant','buildability')
    if kind=='mountain_basin':return ('dry_flat_floor','mountain_setting','nearby_wood_abundant','buildability')
    if kind!='enclosed_island':raise ValueError('Unsupported reviewed landscape type')
    return ('island_separated','mountain_setting','external_wood_abundant','buildability')


def validate_review(r,cfg=None):
    if r.get('source_kind')!='fresh_chunkbase_browser_UI' or r.get('version')!='Bedrock 26.50 - 26.52':
        raise ValueError('Fresh reviews require actual matching-version Chunkbase browser UI provenance')
    if r.get('source_url')!='https://www.chunkbase.com/apps/seed-map' or not r.get('recorded_at') or not r.get('browser_evidence'):
        raise ValueError('Review requires date, source link and browser evidence references')
    parse_seed(r['seed'])
    if len(r['center'])!=2 or any(not isinstance(v,int) or isinstance(v,bool) or v%8 for v in r['center']):raise ValueError('Review requires exact eight-block center')
    if r.get('terrain_enabled') is not True or set(r.get('dimensions_checked',[]))!={'overworld','nether'}:
        raise ValueError('Review requires Terrain enabled and both dimensions checked')
    for name in landscape_review_fields(r.get('landscape_type','enclosed_island')):
        if r.get(name) is not None and not isinstance(r.get(name),bool):raise ValueError(f'Invalid review field {name}')
    needed=required_types(cfg) if cfg is not None else ('fortress','bastion') if 'landscape_type' not in r else ('fortress','stronghold')
    for t in needed:
        if t not in r.get('structures',{}):raise ValueError(f'Review must record required {t} markers')
    for t,markers in r.get('structures',{}).items():
        if t not in ('fortress','bastion','stronghold'):raise ValueError('Unsupported reviewed structure')
        for p in markers:
            if len(p)!=2 or any(not isinstance(v,int) or isinstance(v,bool) for v in p):raise ValueError('Website markers require exact integer X/Z')
    return r


def apply_review(c,reviews,cfg,config_hash):
    c=copy.deepcopy(c)
    found=[r for r in reviews if r['seed']==c['seed'] and r['center']==c['center'] and r['config_sha256']==config_hash and r.get('landscape_type','enclosed_island')==c.get('landscape_type','enclosed_island')]
    if not found:return c
    r=validate_review(found[-1],cfg);c['chunkbase_checked']=True;c['chunkbase_review']=r
    for t,markers in r['structures'].items():
        if t not in c['structures']:raise ValueError(f'Unsupported reviewed structure type {t}')
        row=c['structures'][t];row['chunkbase_checked']=True;row['chunkbase_markers']=markers
        row['chunkbase_markers_inside']=[p for p in markers if inside(p,row['bounds'])]
        row['confirmed_required_eligible']=bool(row['chunkbase_markers_inside']) if t in required_types(cfg) else False
        row['confirmation_scope']='website_marker_only; accessible footprint remains unknown'
    requirements=[r.get(k) is True for k in landscape_review_fields(c.get('landscape_type','enclosed_island'))]
    required=all(c['structures'][t]['confirmed_required_eligible'] for t in required_types(cfg))
    c['selection_status']='chunkbase_supported_candidate' if all(requirements) and required else 'chunkbase_checked_near_miss_or_unresolved'
    c['remaining_review']=['Optional Minecraft check of thin bridges, actual trees, structure access/footprints and portal arrival'] if c['selection_status']=='chunkbase_supported_candidate' else ['Fresh Chunkbase review did not establish every selection requirement; see review notes']
    return c


def import_review(run,path,cfg=None):
    data=json.loads(Path(path).read_text()); data=data if isinstance(data,list) else [data]
    for r in data:validate_review(r,cfg)
    dest=Path(run)/'reviews.json';existing=json.loads(dest.read_text()) if dest.exists() else []
    for r in data:
        existing=[v for v in existing if (v['seed'],v['center'],v['config_sha256'],v.get('landscape_type','enclosed_island'))!=(r['seed'],r['center'],r['config_sha256'],r.get('landscape_type','enclosed_island'))]
        existing.append(r)
    save_json(dest,existing)
````

## File: src/seed_search/report_cache.py

SHA-256: d7f75aa5303a1dfbdc56e167856588f01a733b40eb8af543eb95663d153a4d04

````python
"""Content-keyed report inputs and maps, verified before reuse."""
import hashlib
import json
import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path
import numpy as np
from .storage import backend_identity,semantic_hash


@lru_cache(maxsize=1)
def predictor_digest():
    return hashlib.sha256(json.dumps(backend_identity(),sort_keys=True).encode()).hexdigest()


def terrain_identity(seed,bounds,step,cfg):
    return {'format':1,'seed':str(seed),'bounds':list(bounds),'step':step,
            'config':semantic_hash(cfg),'predictor':predictor_digest()}


def terrain_path(root,identity):
    digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    return Path(root)/f'{digest}.npz'


def write_atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        temp=f.name;f.write(data)
    os.replace(temp,path)


def save_terrain(root,seed,bounds,terrain,cfg):
    identity=terrain_identity(seed,bounds,terrain['step'],cfg);path=terrain_path(root,identity)
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        name=f.name
        np.savez_compressed(f,height=terrain['height'],biomes=terrain['biomes'],
                            identity=json.dumps(identity,sort_keys=True),actual_bounds=terrain['bounds'],
                            points=terrain['points'],sea_level_stride1_points=terrain['sea_level_stride1_points'])
    os.replace(name,path)
    write_atomic(str(path)+'.sha256',hashlib.sha256(path.read_bytes()).hexdigest().encode())
    return path


def load_terrain(root,seed,bounds,step,cfg):
    identity=terrain_identity(seed,bounds,step,cfg);path=terrain_path(root,identity)
    try:
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=Path(str(path)+'.sha256').read_text():return None
        with np.load(path,allow_pickle=False) as data:
            if json.loads(str(data['identity']))!=identity:return None
            h=data['height'];b=data['biomes'];shape=((bounds[3]-bounds[1])//step+1,(bounds[2]-bounds[0])//step+1)
            if h.shape!=shape or b.shape!=shape or not np.issubdtype(h.dtype,np.integer) or not np.issubdtype(b.dtype,np.integer):return None
            return {'height':h,'biomes':b,'bounds':data['actual_bounds'].tolist(),'step':step,
                    'points':int(data['points']),'sea_level_stride1_points':int(data['sea_level_stride1_points']),
                    'report_cache_hit':True}
    except (OSError,ValueError,KeyError,EOFError):return None


def map_identity(candidate,cfg):
    from .storage import ROOT
    renderer=hashlib.sha256((ROOT/'src/seed_search/reports.py').read_bytes()).hexdigest()
    payload={'candidate':candidate,'config':cfg,'predictor':predictor_digest(),'renderer':renderer,'format':1}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


def reuse_maps(root,key,out):
    cache=Path(root)/key
    try:
        proof=json.loads((cache/'hashes.json').read_text())
        for name in ('overworld.png','nether.png'):
            if hashlib.sha256((cache/name).read_bytes()).hexdigest()!=proof[name]:return False
        for name in ('overworld.png','nether.png'):shutil.copyfile(cache/name,Path(out)/name)
        return True
    except (OSError,ValueError,KeyError):return False


def save_maps(root,key,out):
    cache=Path(root)/key;cache.mkdir(parents=True,exist_ok=True);hashes={}
    for name in ('overworld.png','nether.png'):
        data=(Path(out)/name).read_bytes();write_atomic(cache/name,data);hashes[name]=hashlib.sha256(data).hexdigest()
    write_atomic(cache/'hashes.json',json.dumps(hashes,sort_keys=True).encode())
````

## File: src/seed_search/reports.py

SHA-256: 20c2406b54c173af8a74a7c2f64eb32eabc85e9991d55a1164f3d559b1c42def

````python
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def render_probe(path,height,biomes,woodland,sparse,points,seed,center):
    extent=[int(points[:,0].min()),int(points[:,0].max()),int(points[:,1].max()),int(points[:,1].min())]
    fig,axes=plt.subplots(1,3,figsize=(16,5.5),constrained_layout=True)
    fig.suptitle(f"Seed {seed} — prediction diagnostics; actual game validation pending",fontsize=13)
    h=axes[0].imshow(height,extent=extent,cmap="terrain",vmin=40,vmax=180)
    axes[0].set_title("Raw density ground estimate (Y)")
    fig.colorbar(h,ax=axes[0],shrink=.75)
    if height.min()<63<height.max():
        x=np.linspace(extent[0],extent[1],height.shape[1]);z=np.linspace(extent[3],extent[2],height.shape[0])
        axes[0].contour(x,z,height,levels=[62.5],colors="navy",linewidths=.5)
    axes[1].imshow((height>=63).astype(int),extent=extent,cmap="Blues_r",vmin=0,vmax=1)
    axes[1].set_title("Land/water proxy at sea level\nNot proof of island separation")
    wood=np.where(height<63,0,np.where(woodland,3,np.where(sparse,2,1)))
    from matplotlib.colors import ListedColormap
    axes[2].imshow(wood,extent=extent,cmap=ListedColormap(["#3c7eaa","#ddd59c","#99b979","#286439"]),vmin=0,vmax=3)
    axes[2].set_title("Woodland potential\nBlue water · tan other · light sparse · dark woodland")
    for ax in axes:
        ax.scatter([center[0]],[center[1]],marker="+",color="red",s=65)
        ax.set_xlabel("X (blocks)");ax.set_ylabel("Z (blocks)")
    fig.savefig(Path(path),dpi=140)
    plt.close(fig)


def candidate_maps(out,c,cfg,run=None):
    from .backend import Backend,biome_name
    from .terrain import raster
    from .wood import wood_masks
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    import time
    started=time.perf_counter()
    opt=cfg.get('optimization',{});run=Path(run) if run else None
    cache_key=None
    if run and opt.get('reuse_unchanged_maps'):
        from .report_cache import map_identity,reuse_maps
        cache_key=map_identity(c,cfg)
        if reuse_maps(run/'map-cache',cache_key,out):return time.perf_counter()-started
    with Backend(c['seed']) as b:
        terrain=None
        if run and opt.get('persist_report_terrain'):
            from .report_cache import load_terrain,save_terrain
            terrain=load_terrain(run/'terrain-cache',c['seed'],c['bounds']['overworld'],cfg['search']['refinement_spacing_blocks'],cfg)
        if terrain is None:
            terrain=raster(b,c['bounds']['overworld'],cfg['search']['refinement_spacing_blocks'])
            if run and opt.get('persist_report_terrain'):save_terrain(run/'terrain-cache',c['seed'],c['bounds']['overworld'],terrain,cfg)
        height=terrain['height'];dense,sparse=wood_masks(terrain['biomes'])
        bounds=c['bounds']['overworld'];extent=[bounds[0],bounds[2],bounds[3],bounds[1]]
        fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
        fig.suptitle(f"Seed {c['seed']} · {c.get('landscape_type','enclosed_island')} · center {tuple(c['center'])}\nDensity/biome predictions; Chunkbase checked: {c['chunkbase_checked']}")
        axes[0].imshow(height,extent=extent,cmap='terrain',vmin=40,vmax=max(150,height.max()))
        axes[0].set_title('Ground Y · predicted coast at sea level')
        if height.min()<63<height.max():
            x=np.linspace(bounds[0],bounds[2],height.shape[1]);z=np.linspace(bounds[1],bounds[3],height.shape[0])
            axes[0].contour(x,z,height,levels=[62.5],colors='navy',linewidths=.5)
        wood=np.where(height<63,0,np.where(dense,3,np.where(sparse,2,1)))
        axes[1].imshow(wood,extent=extent,cmap=ListedColormap(['#3c7eaa','#ddd59c','#99b979','#286439']),vmin=0,vmax=3)
        axes[1].set_title('Woodland biome proxy · structures (predicted starts)')
        for typ,r in c['structures'].items():
            if r['dimension']!='overworld':continue
            if r['viable']:
                pts=np.array(r['viable']);axes[1].scatter(pts[:,0],pts[:,1],s=14,label=typ,alpha=.7)
        axes[1].legend(fontsize=6,loc='upper left',ncol=2)
        for ax in axes:
            ax.plot(*c['center'],marker='+',color='red',markersize=10)
            ax.add_patch(Rectangle((bounds[0],bounds[1]),3008,3008,fill=False,edgecolor='black',linewidth=2))
            for side,style in ((cfg['overworld']['report_core_side_blocks'],':'),(cfg['overworld']['report_primary_side_blocks'],'--')):
                ax.add_patch(Rectangle((c['center'][0]-side/2,c['center'][1]-side/2),side,side,fill=False,edgecolor='gray',linestyle=style))
            ax.set_xlabel('X (blocks)');ax.set_ylabel('Z (blocks)')
        fig.savefig(out/'overworld.png',dpi=120);plt.close(fig)
        nb=c['bounds']['nether'];step=16
        xx,zz=np.meshgrid(np.arange(nb[0],nb[2]+1,step),np.arange(nb[1],nb[3]+1,step))
        biomes=np.array([b.biome(int(x),33,int(z),-1) for x,z in zip(xx.ravel(),zz.ravel())]).reshape(xx.shape)
        values=sorted(np.unique(biomes));colors=['#85443c','#705951','#27a395','#791429','#6a6565']
        fig,ax=plt.subplots(figsize=(7,7),constrained_layout=True)
        mapped=np.zeros_like(biomes)
        for i,v in enumerate(values):mapped[biomes==v]=i
        ax.imshow(mapped,extent=[nb[0],nb[2],nb[3],nb[1]],cmap=ListedColormap(colors[:len(values)]),vmin=-.5,vmax=len(values)-.5)
        for typ,color in (('fortress','gold'),('bastion','white')):
            r=c['structures'][typ]
            for key,marker in (('viable','o'),('rejected_raw_review','x'),('chunkbase_markers','s')):
                if r[key]:
                    pts=np.array(r[key]);ax.scatter(pts[:,0],pts[:,1],c=color,marker=marker,s=75,label=f'{typ}: {key}')
        ax.plot(*c['nether_center'],marker='+',color='cyan',markersize=15)
        ax.add_patch(Rectangle((nb[0],nb[1]),992,992,fill=False,edgecolor='black',linewidth=2))
        ax.set_title(f"Nether · seed {c['seed']}\ncenter {tuple(c['nether_center'])}; 992 × 992 square\nStarts/markers do not establish accessible footprints")
        ax.set_xlabel('X (blocks)');ax.set_ylabel('Z (blocks)');ax.legend(fontsize=8)
        fig.savefig(out/'nether.png',dpi=120);plt.close(fig)
    if cache_key is not None:
        from .report_cache import save_maps
        save_maps(run/'map-cache',cache_key,out)
    return time.perf_counter()-started


def export_search(run,results,cfg,config_hash,identity):
    import csv
    import json
    from .scoring import distinct_rank,ranking_key
    from .preflight import save_json
    from .review import apply_review,landscape_review_fields
    from .structures import required_types
    run=Path(run)
    # A resumed/refreshed ranking can change every folder ordinal. Preserve the
    # prior generated view, but never leave stale folders in the active list.
    if (run/'shortlist').exists():
        history=run/'report-history';history.mkdir(exist_ok=True)
        generation=0
        while (history/f'shortlist-{generation:03d}').exists():generation+=1
        (run/'shortlist').rename(history/f'shortlist-{generation:03d}')
    reviews=json.loads((run/'reviews.json').read_text()) if (run/'reviews.json').exists() else []
    candidates=[apply_review(c,reviews,cfg,config_hash) for r in results for c in r['candidates']]
    rejected=[c for c in candidates if c['chunkbase_checked'] and any(c['chunkbase_review'].get(k) is False for k in landscape_review_fields(c.get('landscape_type','enclosed_island')))]
    rejected_keys={(c['seed'],tuple(c['center']),c.get('landscape_type','enclosed_island')) for c in rejected}
    lists=distinct_rank([c for c in candidates if (c['seed'],tuple(c['center']),c.get('landscape_type','enclosed_island')) not in rejected_keys],cfg['search']['report_top_distinct_seeds'])
    near=[];seen=set()
    for c in sorted(lists['near_misses']+rejected,key=ranking_key):
        if c['seed'] not in seen and len(near)<cfg['search']['report_top_distinct_seeds']:
            near.append(c);seen.add(c['seed'])
    lists['near_misses']=near
    supported=[];seen=set()
    for c in sorted(candidates,key=ranking_key):
        if c['selection_status']=='chunkbase_supported_candidate' and c['seed'] not in seen and len(supported)<cfg['search']['report_top_distinct_seeds']:
            supported.append(c);seen.add(c['seed'])
    lists['chunkbase_supported']=supported
    if 'landscapes' in cfg:
        for kind in cfg['landscapes']['enabled']:
            eligible=[c for c in candidates if c.get('landscape_type')==kind and c['nether_status']!='missing_required_local_prediction' and (c['seed'],tuple(c['center']),kind) not in {(v['seed'],tuple(v['center']),v.get('landscape_type')) for v in rejected}]
            seen=set();values=[]
            for c in sorted(eligible,key=ranking_key):
                if c['seed'] not in seen and len(values)<cfg['search']['report_top_distinct_seeds']:values.append(c);seen.add(c['seed'])
            lists[kind]=values
    summary={'completed_seeds':len(results),'scored_centers':len(candidates),
             'filter_policy':cfg.get('optimization',{}).get('stronghold_prefilter','review_all'),
             'structure_deferred_locations':sum(r['counts'].get('early_structure_deferred',0) for r in results),
             'seeds_with_predicted_both_nether':len({c['seed'] for c in candidates if all(c['structures'][t]['viable'] for t in ('fortress','bastion'))}),
             'scored_with_all_three_core':sum(all(c['structures'][t]['viable'] for t in ('trial_chamber','stronghold','mineshaft')) for c in candidates),
             'required_structure_types':list(required_types(cfg)),
             'scored_with_required_structures':sum(all(c['structures'][t]['viable'] for t in required_types(cfg)) for c in candidates),
             'list_counts':{k:len(v) for k,v in lists.items()},'map_generation_seconds':0}
    if 'csv' in cfg['output']['summary_formats']:
        with (run/'candidates.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['seed','index','landscape_type','center_x','center_z','nether_x','nether_z','total','score_lower','score_upper','required_structure_status','chunkbase_checked','actual_minecraft'])
            for c in candidates:w.writerow([c['seed'],c['index'],c.get('landscape_type','enclosed_island'),*c['center'],*c['nether_center'],c['score']['total'],*c['score']['interval'],c['nether_status'],c['chunkbase_checked'],c['actual_minecraft']])
    for group,cs in lists.items():
        # Near misses remain fully exported in JSON/CSV; maps focus on the same
        # shortlist depth, including a representative rejected seed for review.
        for i,c in enumerate(cs):
            out=run/'shortlist'/group/f'{i+1:02d}_{c["seed"]}_{c["center"][0]}_{c["center"][1]}'
            out.mkdir(parents=True,exist_ok=True)
            save_json(out/'candidate.json',{'config_sha256':config_hash,'backend_identity':identity['backend'],**c})
            if 'overworld.png' in cfg['output']['candidate_files'] or 'nether.png' in cfg['output']['candidate_files']:
                summary['map_generation_seconds']+=candidate_maps(out,c,cfg,run)
            lines=[f"# Seed {c['seed']}",'',f"Overworld center {c['center']}, bounds {c['bounds']['overworld']}; Nether center {c['nether_center']}, bounds {c['bounds']['nether']}.",'',
                   f"Status: {c['selection_status']}. Chunkbase checked: {c['chunkbase_checked']}; actual Minecraft evidence: {c['actual_minecraft']}.",'',
                   f"Score: {c['score']['total']} / interval {c['score']['interval']}. See candidate.json for each metric and raw/viable/website statuses.",'',
                   'Review in [Chunkbase](https://www.chunkbase.com/apps/seed-map) with Bedrock 26.50–26.52 and Terrain enabled in the Overworld. Required structure markers must lie inside their reported squares. Starts and markers cannot establish whole-structure access.','']
            lines.extend('- [ ] '+v for v in c.get('remaining_review',cfg['verification']['final_required_checks']))
            lines.extend(['','Optional actual-game checks: '+', '.join(cfg['verification'].get('optional_actual_game_checks',[])), '',*c['approximation_limits']])
            (out/'inspection.md').write_text('\n'.join(lines)+'\n')
    save_json(run/'summary.json',summary)
    deferred=[{'seed':r['seed'],'index':r['index'],**v} for r in results for v in r['near_misses'] if v['reason'].startswith('deferred_') and 'required_prediction' in v['reason']]
    save_json(run/'stronghold-deferred.json',{'scope':'Fast prediction exclusions; not proven absent. Recover with review_all and a new run.',
                                              'records':deferred,'seeds':sorted({v['seed'] for v in deferred},key=int)})
    (run/'stronghold-deferred-seeds.txt').write_text(''.join(seed+'\n' for seed in sorted({v['seed'] for v in deferred},key=int)))
    if 'json' in cfg['output']['summary_formats']:
        save_json(run/'candidates.json',{'identity':identity,'summary':summary,'lists':lists,'all_centers':candidates,
                                         'rejections_and_deferred':[{'seed':r['seed'],**v} for r in results for v in r['near_misses']]})
    return summary
````

## File: src/seed_search/cli.py

SHA-256: 0b30ed8ea25e725d6d7e85a5e40fc594d589689ba0177f4199679d45dfb967a1

````python
from __future__ import annotations
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
    os.environ[_key]="1"

import argparse
import json
from pathlib import Path
from . import BACKEND_COMMIT
from .backend import Backend
from .config import load_config,discovery_grid
from .preflight import benchmark,probe,metadata,compare_observations,save_json
from .seeds import parse_seed

def main(argv=None):
    parser=argparse.ArgumentParser(description="Bedrock 26.52 finite search with measured evidence readiness gate")
    parser.add_argument("--config",help="Configuration path (default search.example.yaml; resume defaults to persisted configuration)")
    sub=parser.add_subparsers(dest="command",required=True)
    doctor=sub.add_parser("doctor",help="Check native backend and pending validation gates")
    doctor.add_argument("--output")
    bench=sub.add_parser("benchmark",help="Measure up to ten fixed diagnostic seeds")
    bench.add_argument("--count",type=int,default=3)
    bench.add_argument("--workers",type=int,nargs="*",default=[4,8,12])
    bench.add_argument("--output",default="runs/preflight")
    inspect=sub.add_parser("probe",help="Generate one predicted terrain/structure inspection packet")
    inspect.add_argument("--seed",type=parse_seed,default=12345)
    inspect.add_argument("--center",type=int,nargs=2)
    inspect.add_argument("--output",default="runs/phone-check")
    compare=sub.add_parser("compare",help="Compare supplied actual phone observations")
    compare.add_argument("--observations",required=True)
    compare.add_argument("--output",default="runs/phone-check/comparison.json")
    reg=sub.add_parser("regression",help="Repeat the frozen external comparison and detect exact local drift")
    reg.add_argument("--output",default="runs/sweep-readiness/regression")
    for name in ("search","rank"):
        q=sub.add_parser(name,help="Finite deterministic automatic search" if name=="search" else "Rank supplied full signed seeds")
        q.add_argument("--output",required=True)
        q.add_argument("--workers",type=int)
        q.add_argument("--readiness")
        q.add_argument("--dry-run",action="store_true")
        q.add_argument("--stop-after",type=int,help="Checkpoint after this many completions, for bounded resume verification")
        if name=="search":
            q.add_argument("--count",type=int,required=True)
            q.add_argument("--start-index",type=int,default=0)
        else:q.add_argument("--seeds",required=True,help="One signed decimal seed per line")
    res=sub.add_parser("resume",help="Resume the exact persisted finite workload")
    res.add_argument("--run",required=True)
    res.add_argument("--workers",type=int)
    res.add_argument("--dry-run",action="store_true")
    review=sub.add_parser("review",help="Import recorded actual Chunkbase UI review and refresh reports")
    review.add_argument("--run",required=True);review.add_argument("--evidence",required=True)
    args=parser.parse_args(argv)
    try:
        if args.command in ('resume','review') and args.config is None:
            from .storage import Store
            original=Store(args.run,resume=True)
            cfg,hash_=original.identity['config'],original.identity['config_sha256'];original.close()
        else:cfg,hash_=load_config(args.config or 'search.example.yaml')
        if cfg["game"]["backend_commit"]!=BACKEND_COMMIT:
            raise ValueError("Configured commit does not match compiled prototype")
        if args.command=="doctor":
            with Backend(12345) as b:
                b.grid(-16,-16,3,3,16)
            result=metadata(hash_)
            result.update({"native_backend":"built_and_callable","discovery_grid":list(discovery_grid(cfg)),
                           "available_commands":["doctor","benchmark","probe","compare","regression","rank","search","resume","review"],
                           "capabilities":__import__("seed_search.backend",fromlist=["capabilities"]).capabilities(),
                           "large_search_gate":"requires_matching_identity_and_verified_readiness_record"})
            if args.output: save_json(args.output,result)
        elif args.command=="benchmark":
            result=benchmark(cfg,hash_,args.output,args.count,tuple(args.workers))
            result={"output":str(Path(args.output).resolve()),"stage_seconds":result["stage_seconds"],
                    "full_search_seconds_per_seed":None}
        elif args.command=="probe":
            result=probe(cfg,hash_,args.seed,args.output,tuple(args.center) if args.center else None)
            result={"output":str(Path(args.output).resolve()),"seed":result["seed"],"center":result["center"],
                    "validation":"predicted_diagnostic_optional_phone_followup"}
        elif args.command=="regression":
            from .regression import regression
            r=regression(args.output);result={"passed":r['passed'],"summary":r['summary']}
        elif args.command in ("search","rank"):
            from .search import run_search
            seeds=Path(args.seeds).read_text().splitlines() if args.command=="rank" else None
            result=run_search(cfg,hash_,args.output,getattr(args,'count',len(seeds) if seeds else 10),getattr(args,'start_index',0),
                              args.workers,seeds,readiness=args.readiness,dry_run=args.dry_run,stop_after=args.stop_after)
        elif args.command=="resume":
            from .search import run_search
            from .storage import Store
            store=Store(args.run,resume=True);identity=store.identity;store.close()
            if cfg!=identity['config'] or hash_!=identity['config_sha256']:
                raise ValueError('Incompatible resume configuration; supply the original --config')
            result=run_search(cfg,hash_,args.run,identity['count'],identity['start_index'],args.workers,
                              identity['seeds'],resume=True,readiness=identity['readiness'],dry_run=args.dry_run)
        elif args.command=="review":
            from .review import import_review
            from .storage import Store,backend_identity
            from .reports import export_search
            store=Store(args.run,resume=True)
            try:
                if store.identity['config_sha256']!=hash_ or store.identity['backend']!=backend_identity():
                    raise ValueError('Review run identity differs from current config/backend')
                import_review(args.run,args.evidence,cfg)
                result=export_search(args.run,store.results(),cfg,hash_,store.identity)
            finally:store.close()
        else:
            result=compare_observations(args.observations,args.output,cfg,hash_)
        print(json.dumps(result,indent=2,allow_nan=False),flush=True)
    except (ValueError,KeyError,FileNotFoundError) as e:
        parser.error(str(e))

if __name__=="__main__":
    main()
````

## File: src/seed_search/readiness.py

SHA-256: 9dde39559b7e0676afedddf4025b44b2d581ea5ca63597adc92aeaea4e04e2b0

````python
"""Evidence-derived, identity-checked gate for a future finite sweep.

This protects normal launches from stale/incomplete evidence; it is not a
cryptographic attestation against somebody deliberately falsifying the files.
"""
import json
import hashlib
import re
from importlib.metadata import version
from pathlib import Path
from .storage import backend_identity, ROOT
from .review import validate_review, apply_review

CHECKS={'native_build','dependencies','tests','external_regression','deterministic_resume','end_to_end_pilot','fresh_chunkbase','candidate_quality','finite_command_validation'}


def artifact_path(value):
    p=Path(value)
    return p if p.is_absolute() else ROOT/p


def required_sources():
    return sorted([*ROOT.glob('src/seed_search/*.py'),*ROOT.glob('tests/test_*.py'),
                   ROOT/'native/build.py',ROOT/'native/bridge.c',ROOT/'native/bridge.h',
                   ROOT/'vendor/backend.json',ROOT/'pyproject.toml',ROOT/'requirements.lock',ROOT/'scripts/assemble_sweep_readiness.py'])


def derive_checks(evidence,cfg,config_hash):
    """Read measured artifacts instead of accepting a set of readiness booleans."""
    def read(key):return json.loads(artifact_path(evidence[key]).read_text())
    verification=read('verification')
    successful=lambda name: verification.get(name,{}).get('exit_code')==0 and bool(verification[name].get('command'))
    tests=verification.get('tests',{})
    test_log=artifact_path(tests.get('log','')).read_text() if artifact_path(tests.get('log','')).is_file() else ''
    passed=re.search(r'(\d+) passed',test_log)
    vendor=json.loads((ROOT/'vendor/backend.json').read_text())
    vendor_valid=all((ROOT/'vendor/cubiomes-bedrock'/name).is_file() and hashlib.sha256((ROOT/'vendor/cubiomes-bedrock'/name).read_bytes()).hexdigest()==digest for name,digest in vendor['files'].items())
    license_record=json.loads(artifact_path(verification['installed_license_evidence']).read_text())
    installed_license=artifact_path(license_record['installed_license'])
    license_valid=installed_license.is_file() and hashlib.sha256(installed_license.read_bytes()).hexdigest()==vendor['files']['LICENSE']
    versions=json.loads(artifact_path(verification['dependency_versions_evidence']).read_text())
    dependency_valid=versions.get('all_locked_versions_match') is True and bool(versions.get('packages')) and all(version(name)==p['locked']==p['installed'] for name,p in versions['packages'].items())
    regression=read('regression')
    resume=read('resume')
    from .storage import Store
    pilot=artifact_path(evidence['pilot'])
    store=Store(pilot,resume=True)
    try:
        identity=store.identity;results=store.results()
    finally:store.close()
    invocations=[json.loads(p.read_text()) for p in sorted(pilot.glob('invocation-*.json'))]
    current=identity['backend']==backend_identity() and identity['config_sha256']==config_hash and identity['config']==cfg
    complete=len(results)==identity['count'] and len(results)>=10 and len({r['seed'] for r in results})==len(results)
    measurements=bool(invocations) and sum(r['completed_this_invocation'] for r in invocations)==len(results) and all(
        r['wall_seconds']>=r['analysis_wall_seconds']>0 and r['report_wall_seconds']>=0 and r['actual_worker_pids'] and r['parent_peak_rss_mb']>0 and r['worker_peak_rss_mb']>0
        for r in invocations)
    candidates=[c for r in results for c in r['candidates']]
    reviews=read('fresh_reviews')
    for r in reviews:
        validate_review(r,cfg)
        if r.get('config_sha256')!=config_hash:raise ValueError('Fresh review configuration differs')
        if not all(artifact_path(p).is_file() for p in r['browser_evidence']):raise ValueError('Fresh browser evidence missing')
    reviewed=[apply_review(c,reviews,cfg,config_hash) for c in candidates]
    matched=[c for c in reviewed if c['chunkbase_checked']]
    exported=json.loads((pilot/'candidates.json').read_text())
    key=lambda c:(c['seed'],tuple(c['center']),c.get('landscape_type','enclosed_island'))
    exports={key(c):c for c in exported['all_centers']}
    output_current=len(exports)==len(candidates) and exported['summary']['completed_seeds']==len(results) and all(
        exports.get(key(c),{}).get('chunkbase_review')==c['chunkbase_review'] for c in matched)
    output_current=output_current and all(len(v)==len({c['seed'] for c in v}) for v in exported['lists'].values())
    packets=list(pilot.glob('shortlist/**/candidate.json'))
    output_current=output_current and len(packets)==sum(len(v) for v in exported['lists'].values()) and all(
        (p.parent/'overworld.png').is_file() and (p.parent/'nether.png').is_file() for p in packets)
    holdouts=[c for c in matched if c['chunkbase_review'].get('review_role')=='holdout_candidate_quality']
    quality=any(c['selection_status']=='chunkbase_supported_candidate' for c in holdouts)
    controls=read('fresh_geometry')
    fresh=bool(holdouts) and any(int(c['seed'])>>32 for c in matched) and any(min(c['center'])<0 for c in matched) and controls.get('source_kind')=='fresh_chunkbase_browser_UI' and controls.get('terrain_enabled') is True and len(controls.get('cases',[]))>=2 and all(artifact_path(p).is_file() for case in controls['cases'] for p in case['evidence'])
    command=read('command_validation')
    return {
        'native_build':successful('native_build') and verification.get('vendor_source_hashes_verified') is True and vendor_valid and license_valid,
        'dependencies':successful('dependencies') and dependency_valid,
        'tests':successful('tests') and tests.get('passed_count',0)>=74 and tests.get('failed_count')==0 and passed is not None and int(passed.group(1))==tests['passed_count'] and not re.search(r'\d+ failed|ERROR|FAILED',test_log),
        'external_regression':regression.get('passed') is True and regression['summary']['unique_type_correspondences']==874 and regression['summary']['known_structure_disagreements']==6 and regression['summary']['reused_starts']==0,
        'deterministic_resume':resume.get('equal') is True and resume.get('candidate_count',0)>0 and resume.get('seeds_compared',0)>=10 and resume.get('prediction_sha256')==resume.get('uninterrupted_prediction_sha256') and resume.get('current_backend_identity')==backend_identity() and resume.get('config_sha256')==config_hash and resume.get('worker_variation_test_passed') is True,
        'end_to_end_pilot':current and complete and measurements and bool(candidates) and output_current,
        'fresh_chunkbase':fresh,
        'candidate_quality':quality,
        'finite_command_validation':command.get('tiny_equivalent_exit_code')==0 and command.get('large_gate_rejection_exit_code')==2 and command.get('resume_dry_run_exit_code')==0 and command.get('sweep_unstarted') is True and command.get('maximum_count',0)>1000,
    }


def check_readiness(path,cfg,config_hash,count):
    if not path:raise ValueError('Large sweep requires --readiness pointing to verified evidence')
    p=Path(path);r=json.loads(p.read_text())
    if r.get('ready') is not True:raise ValueError('Readiness record is not ready')
    if r.get('config_sha256')!=config_hash or r.get('backend_identity')!=backend_identity():
        raise ValueError('Readiness identity is incompatible with current configuration/backend')
    if set(r.get('checks',{}))!=CHECKS or not all(v is True for v in r['checks'].values()):
        raise ValueError('Readiness checks are incomplete')
    if not 1000<count<=r.get('maximum_sweep_count',0):raise ValueError('Sweep exceeds measured readiness budget')
    artifacts=r.get('artifacts',[])
    if not artifacts:raise ValueError('Readiness requires verification artifacts')
    covered=set()
    for a in artifacts:
        f=artifact_path(a['path']).resolve();covered.add(f)
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=a['sha256']:
            raise ValueError(f'Readiness artifact missing or changed: {f}')
    if not set(required_sources())<=covered:raise ValueError('Readiness source/test manifest is incomplete')
    evidence=r.get('evidence',{})
    needed={'verification','regression','resume','pilot','fresh_reviews','fresh_geometry','command_validation'}
    if set(evidence)!=needed:raise ValueError('Readiness evidence links are incomplete')
    linked={artifact_path(v).resolve() for k,v in evidence.items() if k!='pilot'}
    verification=json.loads(artifact_path(evidence['verification']).read_text())
    linked|={artifact_path(verification[k]['log']).resolve() for k in ('native_build','dependencies','tests')}
    linked|={artifact_path(verification[k]).resolve() for k in ('installed_license_evidence','dependency_versions_evidence')}
    vendor=json.loads((ROOT/'vendor/backend.json').read_text())
    linked|={ROOT/'vendor/cubiomes-bedrock'/name for name in vendor['files']}
    pilot=artifact_path(evidence['pilot']).resolve()
    linked|={pilot/'checkpoint.sqlite',*pilot.glob('invocation-*.json')}
    reviews=json.loads(artifact_path(evidence['fresh_reviews']).read_text())
    linked|={artifact_path(v).resolve() for review in reviews for v in review['browser_evidence']}
    geometry=json.loads(artifact_path(evidence['fresh_geometry']).read_text())
    linked|={artifact_path(v).resolve() for case in geometry['cases'] for v in case['evidence']}
    if not linked<=covered:raise ValueError('Readiness evidence is not fully hashed')
    command=json.loads(artifact_path(evidence['command_validation']).read_text())
    if r['maximum_sweep_count']!=command['maximum_count'] or r.get('sweep_command')!=command['sweep_command'] or r.get('resume_command')!=command['resume_command']:
        raise ValueError('Readiness finite budget/commands differ from verified evidence')
    actual=derive_checks(evidence,cfg,config_hash)
    if actual!=r['checks']:raise ValueError('Readiness assertions do not match measured evidence')
    return r
````

## File: native/bridge.c

SHA-256: 7096e03918506eec9c536794566a592681789961e6f75ce51b7141bea5fc8ff5

````c
#include "bridge.h"
#include "generator.h"
#include "finders.h"
#include "cave.h"
#include "util.h"
#include <stdlib.h>
#include <string.h>

/* The opaque handle owns all generator/spline buffers. Never copy it. */
struct SeedContext {
    uint64_t seed;
    Generator overworld, nether;
    TerrainNoise terrain;
    TerrainShaper shaper;
    int terrain_ready;
};

SeedContext *ss_create(uint64_t seed) {
    SeedContext *ctx = calloc(1, sizeof(*ctx));
    if (!ctx) return NULL;
    ctx->seed = seed;
    setupGenerator(&ctx->overworld, MC_26_50, 0);
    setupGenerator(&ctx->nether, MC_26_50, 0);
    applySeed(&ctx->overworld, DIM_OVERWORLD, seed);
    applySeed(&ctx->nether, DIM_NETHER, seed);
    return ctx;
}
void ss_destroy(SeedContext *ctx) { free(ctx); }
int ss_model(void) { return MC_26_50; }
const char *ss_model_name(void) { return mc2str(MC_26_50); }
const char *ss_biome_name(int id) {
    /* Pinned util.c omits these existing enum entries. */
    switch (id) {
        case grove: return "grove";
        case snowy_slopes: return "snowy_slopes";
        case jagged_peaks: return "jagged_peaks";
        case frozen_peaks: return "frozen_peaks";
        default: return biome2str(MC_26_50,id);
    }
}
int ss_structure_type(const char *name) {
    if (!strcmp(name,"trial_chamber")) return Trial_Chambers;
    if (!strcmp(name,"stronghold")) return Stronghold;
    if (!strcmp(name,"mineshaft")) return Mineshaft;
    if (!strcmp(name,"ancient_city")) return Ancient_City;
    if (!strcmp(name,"village")) return Village;
    if (!strcmp(name,"ruined_portal")) return Ruined_Portal;
    if (!strcmp(name,"shipwreck")) return Shipwreck;
    if (!strcmp(name,"monument")) return Monument;
    if (!strcmp(name,"outpost")) return Outpost;
    if (!strcmp(name,"fortress")) return Fortress;
    if (!strcmp(name,"bastion")) return Bastion;
    return -1;
}
int ss_structure_rng(int type) {
    StructureConfig config;
    return getStructureConfig(type, MC_26_50, &config) ? config.rngType : -1;
}
int ss_biome(SeedContext *ctx, int dimension, int x, int y, int z) {
    Generator *g = dimension == DIM_OVERWORLD ? &ctx->overworld : &ctx->nether;
    return getBiomeAt(g, 1, x, y, z);
}
int ss_grid(SeedContext *ctx, int x0, int z0, int nx, int nz, int step,
            int y, int *biomes, double *climate, double *approx_height) {
    if (nx < 1 || nz < 1 || step < 1) return -1;
    for (int z = 0; z < nz; z++) for (int x = 0; x < nx; x++) {
        int bx = x0 + x*step, bz = z0 + z*step;
        int i = z*nx + x;
        int64_t np[6];
        biomes[i] = getBiomeAt(&ctx->overworld,1,bx,y,bz);
        /* Depth at y=0, matching this fork's mapApproxHeight heuristic. */
        sampleBiomeNoise(&ctx->overworld.bn,np,floordiv(bx,4),0,
                         floordiv(bz,4),NULL,SAMPLE_NO_BIOME);
        for (int k=0;k<6;k++) climate[6*i+k] = np[k] / 10000.0;
        approx_height[i] = np[NP_DEPTH] / 76.0;
    }
    return 0;
}
int ss_heights(SeedContext *ctx, const int *xz, int n, int vertical_step,
               int *heights, int *surface_biomes) {
    if (n < 0 || vertical_step < 1 || vertical_step > 16) return -1;
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready = 1;
    }
    for (int i=0;i<n;i++) {
        int x=xz[2*i], z=xz[2*i+1], top=-65;
        double offset, factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,
                           floordiv(x,4),floordiv(z,4),&offset,&factor);
        /* Raw density estimate: excludes cave, aquifer, decoration and
           actual chunk interpolation. Coarse scans can miss thin overhangs. */
        for (int y=319;;y-=vertical_step) {
            if (y < -64) y=-64;
            if (sampleTerrainDensity(&ctx->terrain,offset,factor,x,y,z)>0) {
                top=y;
                for (int yy=y+vertical_step-1;yy>y;yy--) {
                    if (yy<=319 && sampleTerrainDensity(&ctx->terrain,offset,factor,x,yy,z)>0) {
                        top=yy; break;
                    }
                }
                break;
            }
            if (y==-64) break;
        }
        heights[i]=top;
        int sample_y=top<63 ? 63 : top+1;
        surface_biomes[i]=getBiomeAt(&ctx->overworld,1,x,sample_y,z);
    }
    return 0;
}
static int inside(Pos p,int x0,int z0,int x1,int z1) {
    return p.x>=x0 && p.x<=x1 && p.z>=z0 && p.z<=z1;
}
static int emit(Pos p,int *out,int n,int cap) {
    if (n>=cap) return -2;
    out[2*n]=p.x; out[2*n+1]=p.z;
    return n+1;
}
int ss_scan(SeedContext *ctx,int type,int x0,int z0,int x1,int z1,
            int viable_only,int *xz,int capacity) {
    StructureConfig cfg;
    if (x0>x1 || z0>z1 || capacity<1 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    int n=0;
    if (type==Mineshaft) {
        /* Source uses inclusive END chunks, despite stale header width docs. */
        Pos *p=malloc(sizeof(*p)*capacity);
        if (!p) return -1;
        int count=getMineshafts(MC_26_50,ctx->seed,floordiv(x0,16),floordiv(z0,16),
                               floordiv(x1,16),floordiv(z1,16),p,capacity);
        if (count>capacity) { free(p); return -2; }
        for (int i=0;i<count;i++) if (inside(p[i],x0,z0,x1,z1)) {
            n=emit(p[i],xz,n,capacity);
            if (n<0) break;
        }
        free(p); return n;
    }
    int size=cfg.regionSize*16;
    Generator *g=cfg.dim==DIM_NETHER ? &ctx->nether : &ctx->overworld;
    /* One-region halo includes displaced static Stronghold starts. */
    for (int rx=floordiv(x0,size)-1;rx<=floordiv(x1,size)+1;rx++) {
        for (int rz=floordiv(z0,size)-1;rz<=floordiv(z1,size)+1;rz++) {
            Pos p;
            int found=getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p);
            /* Keep the selected Bedrock structure type. Promoting a rejected
             * Bastion to a Fortress produced the absent seed-12345 start at
             * (-152,120); phone inspection supplied the negative fixture. */
            if (!found || !inside(p,x0,z0,x1,z1)) continue;
            if (viable_only && type!=Stronghold && !isViableStructurePos(type,g,p.x,p.z,0)) continue;
            n=emit(p,xz,n,capacity);
            if (n<0) return n;
        }
    }
    if (type==Stronghold) {
        StrongholdIter it={0};
        for (int i=0;i<3;i++) {
            nextVillageStronghold(&it,&ctx->overworld);
            if (inside(it.pos,x0,z0,x1,z1)) {
                n=emit(it.pos,xz,n,capacity);
                if (n<0) return n;
            }
        }
    }
    return n;
}
int ss_attempt(SeedContext *ctx,int type,int rx,int rz,int *xz) {
    if (type<0 || type==Mineshaft) return -1;
    Pos p;
    int ok=getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p);
    if (ok) { xz[0]=p.x; xz[1]=p.z; }
    return ok;
}
/* Validate enumerated starts without repeating placement or Stronghold iteration.
 * Match ss_scan's special adapters: those two families never veto raw starts. */
int ss_filter_starts(SeedContext *ctx,int type,const int *xz,int n,int *viable) {
    StructureConfig cfg;
    if (n<0 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    Generator *g=cfg.dim==DIM_NETHER ? &ctx->nether : &ctx->overworld;
    for (int i=0;i<n;i++)
        viable[i]=(type==Stronghold || type==Mineshaft) ? 1 :
            !!isViableStructurePos(type,g,xz[2*i],xz[2*i+1],0);
    return 0;
}
/* Expose the actual viability sampling convention for evidence, not a new rule.
 * out: quart x/y/z, sampled biome, rotation, variant, offset x/z, size x/z. */
int ss_diagnostic(SeedContext *ctx, int type, int x, int z, int *out) {
    if (type == Ancient_City) {
        out[0]=x>>2; out[1]=-27>>2; out[2]=z>>2;
        out[3]=getBiomeAt(&ctx->overworld,0,out[0],out[1],out[2]);
        for (int i=4;i<10;i++) out[i]=0;
        return 1;
    }
    if (type != Bastion) return 0;
    StructureVariant sv;
    if (!getVariant(&sv,Bastion,MC_26_50,ctx->seed,x,z,-1)) return 0;
    int cx=x>>4,cz=z>>4;
    out[0]=(cx*32+2*sv.x+sv.sx-1)/2>>2;
    out[1]=33>>2;
    out[2]=(cz*32+2*sv.z+sv.sz-1)/2>>2;
    out[3]=getBiomeAt(&ctx->nether,4,out[0],out[1],out[2]);
    out[4]=sv.rotation;out[5]=sv.start;
    out[6]=sv.x;out[7]=sv.z;out[8]=sv.sx;out[9]=sv.sz;
    return 1;
}
/* Exact sea-level classification relative to the stride-one raw density model.
 * Checking upward permits early success for land while retaining thin overhangs.
 * Unlike a monotonic/binary-search shortcut, every Y>=63 is checked for water. */
int ss_land(SeedContext *ctx, const int *xz, int n, int *land) {
    if (n<0) return -1;
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready=1;
    }
    for (int i=0;i<n;i++) {
        int x=xz[2*i],z=xz[2*i+1];
        double offset,factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        land[i]=0;
        for (int y=63;y<=319;y++) {
            if (sampleTerrainDensity(&ctx->terrain,offset,factor,x,y,z)>0) {
                land[i]=1;break;
            }
        }
    }
    return 0;
}
````

## File: native/bridge.h

SHA-256: ecc06ed0e803ca87caf3701e4f849532e654dd9af8906e1e13843e806881eb1f

````c
#include <stdint.h>
typedef struct SeedContext SeedContext;
SeedContext *ss_create(uint64_t seed);
void ss_destroy(SeedContext *ctx);
int ss_model(void);
const char *ss_model_name(void);
const char *ss_biome_name(int id);
int ss_structure_type(const char *name);
int ss_structure_rng(int type);
int ss_biome(SeedContext *ctx, int dimension, int x, int y, int z);
int ss_grid(SeedContext *ctx, int x0, int z0, int nx, int nz, int step,
            int y, int *biomes, double *climate, double *approx_height);
int ss_heights(SeedContext *ctx, const int *xz, int n, int vertical_step,
               int *heights, int *surface_biomes);
int ss_scan(SeedContext *ctx, int type, int x0, int z0, int x1, int z1,
            int viable_only, int *xz, int capacity);
int ss_attempt(SeedContext *ctx, int type, int rx, int rz, int *xz);
int ss_filter_starts(SeedContext *ctx, int type, const int *xz, int n, int *viable);
int ss_diagnostic(SeedContext *ctx, int type, int x, int z, int *out);
int ss_land(SeedContext *ctx, const int *xz, int n, int *land);
````

## File: native/build.py

SHA-256: ddfa6bb78a8e86d34674e3e3beb351feb1c316de8bdc3c19f7223feea59c5169

````python
from pathlib import Path
from cffi import FFI

ROOT = Path(__file__).resolve().parents[1]
ffibuilder = FFI()
header = (ROOT / "native/bridge.h").read_text()
ffibuilder.cdef("\n".join(line for line in header.splitlines() if not line.startswith("#")))
units = ["noise", "biomes", "layers", "biomenoise", "cave", "generator", "finders", "util", "quadbase", "mt"]
ffibuilder.set_source(
    "seed_search._native", '#include "bridge.h"',
    sources=["native/bridge.c"] + [f"vendor/cubiomes-bedrock/{u}.c" for u in units],
    include_dirs=["native", "vendor/cubiomes-bedrock"],
    extra_compile_args=["-O3", "-std=c11", "-fwrapv"],
    libraries=["m"],
)
if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    ffibuilder.compile(tmpdir=".", target=str(ROOT / "src/seed_search/_native.*"), verbose=True)
````

## File: vendor/cubiomes-bedrock/finders.h

SHA-256: b91dae02e695274c32ac9f65423d40dcee967b99fe2336fbc29f6cf3a0fb1b78

````c
#ifndef FINDERS_H_
#define FINDERS_H_


#include "generator.h"
#include "cave.h"
#include "util.h"


#ifdef __cplusplus
extern "C"
{
#endif

#define MASK48 (((int64_t)1 << 48) - 1)
#define MASK32 (((int64_t)1 << 32) - 1)

enum StructureType
{
    Feature, // for locations of temple generation attempts pre 1.13
    Desert_Pyramid,
    Jungle_Temple, Jungle_Pyramid = Jungle_Temple,
    Swamp_Hut,
    Igloo,
    Village,
    Ocean_Ruin,
    Shipwreck,
    Monument,
    Mansion,
    Outpost,
    Ruined_Portal,
    Ruined_Portal_N,
    Ancient_City,
    Treasure,
    Mineshaft,
    Ravine,
    Lava_Lake,
    Stronghold,
    Desert_Well,
    Geode,
    Dungeon,
    Fortress,
    Bastion,
    End_City,
    End_Gateway,
    End_Island,
    Trail_Ruins,
    Trial_Chambers,
    Abandoned_Camp,
    FEATURE_NUM
};


enum RNGType
{
    BEDROCK_RANDOM   = 0,
    JAVA_RANDOM      = 1,
    XOROSHIRO_RANDOM = 2
};


// use getStructureConfig() for the version specific structure configuration
STRUCT(StructureConfig)
{
    int32_t salt;
    int16_t regionSize;
    int16_t chunkRange;
    uint8_t structType;
    int8_t  dim;
    float   rarity;
    uint8_t rngType;
};




STRUCT(StrongholdIter)
{
    Pos pos;        // accurate location of current stronghold
    int index;      // stronghold index counter
    double angle;   // next angle within ring
    double dist;    // next distance from origin (in chunks)
    int mc;         // minecraft version
};


STRUCT(StructureVariant)
{
    uint8_t abandoned   :1; // is zombie village
    uint8_t giant       :1; // giant portal variant & mega ravine
    uint8_t underground :1; // underground portal
    uint8_t underwater  :1; // underwater ravine
    uint8_t airpocket   :1; // portal with air pocket
    uint8_t basement    :1; // igloo with basement
    uint8_t cracked     :1; // geode with crack
    uint8_t large       :1; // large ocean ruin
    uint8_t cluster     :1; // has cluster of ocean ruin
    uint8_t secret      :1; // camp secret chest
    float_t thick;          // ravine thickness
    float_t yaw;            // ravine yaw
    float_t pitch;          // ravine pitch
    uint8_t size;           // geode size | igloo middel pieces
    uint8_t start;          // starting piece index
    short   biome;          // biome variant
    uint8_t rotation;       // 0:0, 1:cw90, 2:cw180, 3:cw270=ccw90
    uint8_t mirror;
    int16_t x, y, z;
    int16_t sx, sy, sz;
    int32_t seed;           // tunnel seed
};

STRUCT(Piece)
{
    const char *name;   // structure piece name
    Pos3 pos;           // position
    BB bb;              // bounding box limits
    uint8_t rot;        // rotation
    int8_t depth;
    int8_t type;
    Piece *next;
};

STRUCT(EndIsland)
{
    int x, y, z;
    int r;
};

enum
{
    BF_APPROX       = 0x01, // enabled aggresive filtering, trading accuracy
    BF_FORCED_OCEAN = FORCE_OCEAN_VARIANTS,
};
STRUCT(BiomeFilter)
{
    // bitfields for biomes required at their respecive layers
    uint64_t tempsToFind; // Special (1:1024)
    uint64_t otempToFind; // OceanTemp (1:256)
    uint64_t majorToFind; // Biome (1:256)
    uint64_t edgesToFind; // Edge (1:64) [mod64: as special case for bamboo]
    // bitfields for biomes to find at RareBiome(1:64), Shore(1:16) and Mix(1:4)
    // layers for (biomeID < 64) and modified (biomeID >= 128 && biomeID < 192)
    uint64_t raresToFind, raresToFindM;
    uint64_t shoreToFind, shoreToFindM;
    uint64_t riverToFind, riverToFindM;
    uint64_t oceanToFind; // all required ocean types

    int specialCnt; // number of special temperature categories required

    uint32_t flags;

    // the biome exclusion aborts generation when the area contains no biomes
    // that can generate the excluded biomes
    uint64_t tempsToExcl;
    uint64_t majorToExcl;
    uint64_t edgesToExcl;
    uint64_t raresToExcl, raresToExclM;
    uint64_t shoreToExcl, shoreToExclM;
    uint64_t riverToExcl, riverToExclM;

    uint64_t biomeToExcl, biomeToExclM;
    uint64_t biomeToFind, biomeToFindM;
    uint64_t biomeToPick, biomeToPickM;
};


/***************************** Structure Positions *****************************
 *
 *  For most structure positions, Minecraft divides the world into a grid of
 *  regions (usually 32x32 chunks) and performs one generation attempt
 *  somewhere in each region. The position of this attempt is governed by the
 *  structure type, the region coordiates and the lower 48-bits of the world
 *  seed. The remaining top 16 bits do not influence structure positions.
 *  The dependency on the region coordinates is linear for both the X and Z
 *  directions, which means that the positions of most structures in a world
 *  can be translated by applying the following transformation to a seed:
 *
 *  seed2 = seed1 - dregX * 341873128712 - dregZ * 132897987541;
 *
 *  Here seed1 and seed2 have the same structure positioning, but moved by a
 *  region offset of (dregX,dregZ).
 *
 *  Another property of note is that seed1 at region (0,0) is simply the world
 *  seed plus a constant that is specific to the stucture type (its salt). This
 *  means that some structure types share quad-bases which are just offset by
 *  their respective salt differences.
 */

//==============================================================================
// Moving Structures
//==============================================================================

/* Transposes a base seed such that structures are moved by the specified region
 * vector, (regX, regZ).
 */
static inline uint64_t moveStructure(uint64_t baseSeed, int regX, int regZ)
{
    return (baseSeed - regX*341873128712 - regZ*132897987541) & 0xffffffffffff;
}


//==============================================================================
// Finding Structure Positions
//==============================================================================


/* Selects the structure configuration for a given version. Returns zero upon
 * failure (e.g. version does not support structure type).
 */
int getStructureConfig(int structureType, int mc, StructureConfig *sconf);

/* The library can be compiled to use a custom internal getter for structure
 * configurations. For this, the macro STRUCT_CONFIG_OVERRIDE should be defined
 * as true and the function getStructureConfig_override() should be defined
 * with a custom function body. However, note this is experimental and not all
 * structure configs may work. (Ideally only change structure salts.)
 */
#if STRUCT_CONFIG_OVERRIDE
int getStructureConfig_override(int stype, int mc, StructureConfig *sconf);
#endif

/* Finds the block position of the structure generation attempt in a given
 * region. You can use isViableStructurePos() to test if the necessary biome
 * requirements are met for the structure to actually generate at that position.
 * Some structure types may fail to produce a valid position in the given
 * region regardless of biomes, in which case the function returns zero.
 *
 * @structureType   : structure type
 * @mc              : minecraft version
 * @seed            : world seed (only the lower 48-bits are relevant)
 * @regX,regZ       : region coordinates (the region size depends on type)
 * @pos             : output block position
 *
 * Returns zero if the position is invalid, or non-zero otherwise.
 */
int getStructurePos(int structureType, int mc, uint64_t seed, int regX, int regZ, Pos *pos);

/* The inline functions below get the generation attempt position given a
 * structure configuration. Most small structures use the getFeature..
 * variants, which have a uniform distribution, while large structures
 * (monuments and mansions) have a triangular distribution.
 */
static inline ATTR(const)
Pos getFeaturePos(StructureConfig config, uint64_t seed, int regX, int regZ);

static inline ATTR(const)
Pos getFeatureChunkInRegion(StructureConfig config, uint64_t seed, int regX, int regZ);

static inline ATTR(const)
Pos getLargeStructurePos(StructureConfig config, uint64_t seed, int regX, int regZ);

static inline ATTR(const)
Pos getLargeStructureChunkInRegion(StructureConfig config, uint64_t seed, int regX, int regZ);

int getStaticStronghold(StructureConfig sconf, uint64_t seed,
    int regionX, int regionZ, Pos *pos);

/* Checks a chunk area, starting at (chunkX, chunkZ) with size (chunkW, chunkH)
 * for Mineshaft positions. If not NULL, positions are written to the buffer
 * 'out' up to a maximum number of 'nout'. The return value is the number of
 * chunks with Mineshafts in the area.
 */
int getMineshafts(int mc, uint64_t seed, int chunkX, int chunkZ,
        int chunkW, int chunkH, Pos *out, int nout);

int getRavines(int mc, uint64_t seed, int chunkX, int chunkZ,
        int chunkW, int chunkH, Pos *out, int nout);

int getGeodes(int mc, uint64_t seed, int chunkX, int chunkZ,
        int chunkW, int chunkH, Pos *out, int nout);

int getLavaLakes(int mc, uint64_t seed, int chunkX, int chunkZ,
        int chunkW, int chunkH, Pos *out, int nout, int isDesert);

// not exacly a structure
static inline ATTR(const)
int isSlimeChunk(int chunkX, int chunkZ)
{
    seedSlimeChunk(chunkX, chunkZ);
    return nextInt(10) == 0;
}

/* Finds the position and size of the small end islands in a given chunk.
 * Returns the number of end islands found.
 */
int getEndIslands(EndIsland islands[2], int mc, uint64_t seed, int chunkX, int chunkZ);

/* Finds the small end islands in the given area and updates the existing
 * height map, y, accordingly. Note that values in the y-map can only increase
 * using this.
 */
int mapEndIslandHeight(float *y, const EndNoise *en, uint64_t seed,
    int x, int z, int w, int h, int scale);

/* Checks if the given chunk contains no blocks. This included a check for
 * small end islands.
 */
int isEndChunkEmpty(const EndNoise *en, const SurfaceNoise *sn, uint64_t seed,
    int chunkX, int chunkZ);

//==============================================================================
// Finding Strongholds and Spawn
//==============================================================================

int nextVillageStronghold(StrongholdIter *sh, const Generator *g);


/* Finds the approximate spawn point in the world.
 * The random state 'rng' output can be NULL to ignore.
 */
Pos estimateSpawn(const Generator *g, uint64_t *rng);

/* Finds the spawn point in the world.
 * Warning: Slow, and may be inaccurate because the world spawn depends on
 * grass blocks!
 */
Pos getSpawn(const Generator *g);


/* Finds a suitable pseudo-random location in the specified area.
 * This function is used to determine the positions of spawn and strongholds.
 * Warning: accurate, but slow!
 *
 * @g           : generator for Overworld biomes
 * @x,y,z       : origin for the search
 * @radius      : square 'radius' of the search
 * validB       : valid biomes, as a bitset for biomes with 0 <= id < 64
 * validM       : valid biomes, as a bitset for biomes with 192 <= id < 256
 * @rnd         : random obj, initialise using setSeed(rnd, world_seed)
 * @passes      : (output) number of valid biomes passed, NULL to ignore
 */
Pos locateBiome(
        const Generator *g, int x, int y, int z, int radius,
        uint64_t validB, uint64_t validM, uint64_t *rng, int *passes);

/* Get the shadow seed.
 */
static inline uint64_t getShadow(uint64_t seed)
{
    return -7379792620528906219LL - seed;
}



//==============================================================================
// Validating Structure Positions
//==============================================================================

/* Performs a biome check near the specified block coordinates to determine
 * whether a structure of the given type could spawn there. You can get the
 * block positions using getStructurePos().
 * The generator, 'g', should be initialized for the correct MC version,
 * dimension and seed. The generator may be temporarily modified during the
 * function call, but will be restored upon return.
 * The 'flags' argument is optional structure specific information, such as the
 * biome variant for villages.
 */
int isViableStructurePos(int structType, Generator *g, int blockX, int blockZ, uint32_t flags);

/* Checks if the specified structure type could generate in the given biome.
 */
int isViableFeatureBiome(int mc, int structureType, int biomeID);

/* Some structures in 1.18 now only spawn if the surface is sufficiently high
 * at all four bounding box corners. This affects primarily Desert_Pyramids,
 * Jungle_Temples and Mansions.
 * Currently cubiomes does not provide overworld surface height and cannot
 * check it, but we can rule out some unlikely positions based biomes.
 *
 * This function is meant only for the 1.18 Overworld and is subject to change.
 */
int isViableStructureTerrain(int structType, Generator *g, int blockX, int blockZ);

/* End Cities require a sufficiently high surface in addition to a biome check.
 * The world seed should be applied to the EndNoise and SurfaceNoise before
 * calling this function. (Use initSurfaceNoiseEnd() for initialization.)
 */
int isViableEndCityTerrain(const Generator *g, const SurfaceNoise *sn,
        int blockX, int blockZ);


//==============================================================================
// Finding Properties of Structures
//==============================================================================

/* Initialises and returns a random seed used in the (16x16) chunk generation.
 * This random object is used for recursiveGenerate() which is responsible for
 * generating caves, ravines, mineshafts, and virtually all other structures.
 */
inline static
uint64_t chunkGenerateRnd(uint64_t worldSeed, int chunkX, int chunkZ)
{
    uint64_t rnd;
    JsetSeed(&rnd, worldSeed);
    rnd = (JnextLong(&rnd) * chunkX) ^ (JnextLong(&rnd) * chunkZ) ^ worldSeed;
    JsetSeed(&rnd, rnd);
    return rnd;
}

/* Get data, such as rotation and bounding box of a structure instance.
 * (Supports only some structure types.)
 */
int getVariant(StructureVariant *sv, int structType, int mc, uint64_t seed,
        int blockX, int blockZ, int biomeID);

/* Generate the structure pieces of an End City. This pieces buffer should be
 * large enough to hold END_CITY_PIECES_MAX elements.
 * @pieces          : output buffer
 * @seed            : world seed
 * @chunkX, chunkZ  : 16x16 chunk position
 *
 * Returns the number of structure pieces generated.
 */
int getEndCityPieces(Piece *pieces, uint64_t seed, int chunkX, int chunkZ);
enum
{   // End City piece types
    BASE_FLOOR,
    BASE_ROOF,
    BRIDGE_END,
    BRIDGE_GENTLE_STAIRS,
    BRIDGE_PIECE,
    BRIDGE_STEEP_STAIRS,
    FAT_TOWER_BASE,
    FAT_TOWER_MIDDLE,
    FAT_TOWER_TOP,
    SECOND_FLOOR_1,
    SECOND_FLOOR_2,
    SECOND_ROOF,
    END_SHIP,
    THIRD_FLOOR_1,
    THIRD_FLOOR_2,
    THIRD_ROOF,
    TOWER_BASE,
    TOWER_FLOOR, // unused
    TOWER_PIECE,
    TOWER_TOP,
    END_CITY_PIECES_MAX = 421
};

/* Generate the structure pieces of a Stronghold. The maximum number of pieces
 * that are generated is limited to 'n'. A buffer length of around 512 should
 * be sufficient in practice.
 */
int getStrongholdPieces(Piece *list, int n, int mc, uint64_t seed, int chunkX, int chunkZ);
enum
{   // Stronghold piece types
    SH_START,
    SH_CORRIDOR,
    SH_PRISON_HALL,
    SH_LEFT_TURN,
    SH_RIGHT_TURN,
    SH_ROOM_CROSSING,
    SH_STAIRS,
    SH_SPIRAL_STAIRCASE,
    SH_FIVE_WAY_CROSSING,
    SH_CHEST_CORRIDOR,
    SH_LIBRARY,
    SH_PORTAL_ROOM,
    SH_SMALL_CORRIDOR,
    SH_PIECES_MAX = 512,
    SH_WEIGHT_TYPES = 11,
};

STRUCT(StrongholdPortalFrame)
{
    Pos3 pos;
    int frameId;
    uint8_t hasEye;
};

STRUCT(StrongholdLayout)
{
    Piece    pieces[SH_PIECES_MAX];
    uint8_t  data[SH_PIECES_MAX];
    int      count;
    uint64_t seed;
};

int getStrongholdLayout(StrongholdLayout *sh, int mc, uint64_t seed, int chunkX, int chunkZ);

/* Find the portal frame positions and eye states for the first Portal Room in
 * 'sh'. This only performs the RNG calls needed to determine each of the 12
 * eye states; it does not regenerate the stronghold layout.
 * Returns 12 on success, or 0 if no Portal Room was found.
 */
int getStrongholdPortalFrames(StrongholdPortalFrame *frames,
        const StrongholdLayout *sh);

/* Generate the structure pieces of a Nether Fortress. The maximum number of
 * pieces that are generated is limited to 'n'. A buffer length of around 400
 * should be sufficient in practice, but a fortress can in theory contain many
 * more than that. The number of generated pieces is given by the return value.
 */
int getFortressPieces(Piece *list, int n, int mc, uint64_t seed, int chunkX, int chunkZ);
int getFortressSpawnerPos(const Piece *piece, Pos3 *spawner);
enum
{   // Fortress piece types
    FORTRESS_START,
    BRIDGE_STRAIGHT,
    BRIDGE_CROSSING,
    BRIDGE_FORTIFIED_CROSSING,
    BRIDGE_STAIRS,
    BRIDGE_SPAWNER,
    BRIDGE_CORRIDOR_ENTRANCE,
    CORRIDOR_STRAIGHT,
    CORRIDOR_CROSSING,
    CORRIDOR_TURN_RIGHT,
    CORRIDOR_TURN_LEFT,
    CORRIDOR_STAIRS,
    CORRIDOR_T_CROSSING,
    CORRIDOR_NETHER_WART,
    FORTRESS_END,
    PIECE_COUNT,
};

/* Generate the structure pieces of an abandoned mineshaft. The maximum number
 * of pieces that are generated is limited to 'n'. The mineshaft type is biome
 * dependent and should be provided explicitly as MINESHAFT_NORMAL or
 * MINESHAFT_MESA.
 */
int getMineshaftPieces(Piece *list, int n, int mc, uint64_t seed, int chunkX, int chunkZ, int type);
enum
{   // Mineshaft types
    MINESHAFT_NORMAL,
    MINESHAFT_MESA,
};
enum
{   // Mineshaft piece types
    MSHFT_ROOM,
    MSHFT_CORRIDOR,
    MSHFT_CROSSING,
    MSHFT_STAIRS,
    MINESHAFT_PIECES_MAX = 1024,
};

STRUCT(DungeonData)
{
    Pos3 pos;       // spawner
    Pos3 chests[2]; // chests
    int  mobType;   // skeleton, zombie, spider
};
enum
{   // mob types
    DUNGEON_ZOMBIE,
    DUNGEON_SKELETON,
    DUNGEON_SPIDER,
};
enum {
    DUNGEON_MAX_PER_CHUNK = 4+10,               // max number of dungeons per chunk
    DUNGEON_CAP = 1<<DUNGEON_MAX_PER_CHUNK,  // 16384 slots, generous for one chunk
};

int getDungeons(
        const BiomeNoise    *bn,
        const TerrainNoise  *tn,
        const TerrainShaper *ts, 
        const CaveNoise     *cn,
        int mc,
        uint64_t seed,
        int chunkX, int chunkZ,
        DungeonData *out, int nout);

/* Generate the scattered structure pieces of a pillager outpost. The maximum number
 * of pieces that are generated is limited to 'n'.
 */
int getOutpostPieces(Piece *pieces, uint64_t seed, int chunkX, int chunkZ);
enum
{   // Outpost piece types
    OUTPOST_CAGE1, // cage1 is the golem cage in Bedrock
    OUTPOST_CAGE2,
    OUTPOST_CAGE_WITH_ALLAYS,
    OUTPOST_LOGS,
    OUTPOST_TARGETS,
    OUTPOST_TENT1,
    OUTPOST_TENT2,
    OUTPOST_PIECES_MAX = 4,
};

int addTunnel(Piece *list, uint32_t tunnelSeed,
              double x, double y, double z,
              float yaw, float pitch, float thick, float scale);

int getEndGatewayPos(uint64_t seed, EndNoise en, SurfaceNoise sn, int chunkX, int chunkZ, Pos *pos);

/* Find the 20 fixed inner positions where End Gateways generate upon defeating
 * the Dragon. The positions are written to 'src' in generation order.
 */
void getFixedEndGateways(int mc, uint64_t seed, Pos src[20]);

/* Get the outer linked Gateway destination for an inner source Gateway.
 * (mc > MC_1_12)
 */
Pos getLinkedGatewayChunk(const EndNoise *en, const SurfaceNoise *sn,
    uint64_t seed, Pos src, Pos *dst);
Pos3 getLinkedGatewayPos(const EndNoise *en, const SurfaceNoise *sn,
    uint64_t seed, Pos src);


/* Find the number of each type of house that generate in a village
 * (mc < MC_1_14)
 * @housesOut       : output number of houses for each entry in the house type
 *                    enum (i.e this should be an array of length HOUSE_NUM)
 * @seed            : world seed
 * @chunkX, chunkZ  : 16x16 chunk position of the village origin
 *
 * Returns the random object seed after finding these numbers.
 */
enum
{
    HouseSmall, Church, Library, WoodHut, Butcher, FarmLarge, FarmSmall,
    Blacksmith, HouseLarge, HOUSE_NUM
};
uint64_t getHouseList(int *houses, uint64_t seed, int chunkX, int chunkZ);

enum
{
    VP_WELL    = 0,
    VP_PATH    = 1,
    VP_TORCH   = 2,
    VP_HOUSE4G = 3,
    VP_CHURCH  = 4,
    VP_HOUSE1  = 5,
    VP_WOODHUT = 6,
    VP_HALL    = 7,
    VP_FIELD1  = 8,
    VP_FIELD2  = 9,
    VP_HOUSE2  = 10,
    VP_HOUSE3  = 11,
    VP_PIECES_MAX = 512,
};

int getPreVillagePieces(Piece *list, int n, uint64_t seed, int chunkX, int chunkZ);


//==============================================================================
// Seed Filters (generic)
//==============================================================================


/* Add the given biome 'id' to a biome set which is represented by the
 * bitfields mL and mM for ids 0-63 and 128-191, respectively.
 */
static inline void idSetAdd(uint64_t *mL, uint64_t *mM, int id)
{
    switch (id & ~0x3f) {
    case 0:     *mL |= 1ULL << id;       break; // [0, 64)
    case 128:   *mM |= 1ULL << (id-128); break; // [128, 192)
    }
}

static inline int idSetTest(uint64_t mL, uint64_t mM, int id)
{
    switch (id & ~0x3f) {
    case 0:     return !!(mL & (1ULL << id));       // [0, 64)
    case 128:   return !!(mM & (1ULL << (id-128))); // [128, 192)
    }
    return 0;
}

/* Samples biomes within the specified range and checks that at least a given
 * proportion of the biomes in that area evaluate as successes.
 *
 * @g           : biome generator
 * @r           : range to be checked
 * @rng         : random number seed for the sampling positions
 * @coverage    : minimum coverage of successful evaluations, [0,1]
 * @confidence  : confidence level, (0,1), e.g. 0.95 for a 95% confidence
 * @eval        : evaluation function - 0:fail, 1:success, -1:skip, else:abort
 * @data        : data argument for eval()
 *
 * Returns non-zero if a sufficient proportion of the sampled positions
 * evaluted as successes.
 */
int monteCarloBiomes(
        Generator         * g,
        Range               r,
        uint64_t          * rng,
        double              coverage,
        double              confidence,
        int (*eval)(Generator *g, int scale, int x, int y, int z, void *data),
        void              * data
        );


//==============================================================================
// Seed Filters (for versions up to 1.17)
//==============================================================================


/* Creates a biome filter configuration from a given list of required and
 * excluded biomes. Biomes should not appear in both lists. Lists of length
 * zero may be passed as null.
 */
void setupBiomeFilter(
    BiomeFilter *bf,
    int mc, uint32_t flags,
    const int *required, int requiredLen,
    const int *excluded, int excludedLen,
    const int *matchany, int matchanyLen);

/* Starts to generate the specified range and checks if the biomes meet the
 * requirements of the biome filter, returning either:
 * 0 (failed),
 * 1 (okay, area is fully generated), or
 * 2 (okay, incomplete generation).
 *
 * The area will be generated inside the cache (if != NULL) but is only
 * defined if the generation was fully completed (check return value).
 * More aggressive filtering can be enabled with the flags which may yield
 * some false negatives in exchange for speed.
 *
 * The generator should be set up for the correct version, however the
 * dimension and seed will be applied internally. This will modify the
 * generator into a partially initialized state that is not valid to use
 * outside this function without re-applying a seed.
 *
 * @g           : biome generator
 * @cache       : working buffer and output (nullable)
 * @r           : range to be checked
 * @dim         : dimension (0:Overworld, -1:Nether, +1:End)
 * @seed        : world seed
 * @filter      : biome requirements to be met
 * @flags       : enables features (see below)
 * @stop        : occasional check for abort (nullable)
 */
int checkForBiomes(
        Generator         * g,
        int               * cache,
        Range               r,
        int                 dim,
        uint64_t            seed,
        const BiomeFilter * filter,
        volatile char     * stop // should be atomic, but is fine as stop flag
        );

/* Specialization of checkForBiomes() for a LayerStack, i.e. the Overworld up
 * to 1.17.
 *
 * @ls          : layered generator (will be modified!)
 * @entry       : generation entry point (setLayerSeed() may be applied here)
 * @cache       : working buffer, and output (if != NULL)
 * @seed        : world seed
 * @x,z,w,h     : requested area
 * @filter      : biomes to be checked for
 */
int checkForBiomesAtLayer(
        LayerStack        * ls,
        Layer             * entry,
        int               * cache,
        uint64_t            seed,
        int                 x,
        int                 z,
        unsigned int        w,
        unsigned int        h,
        const BiomeFilter * filter
        );

/* Checks that the area (x,z,w,h) at layer Special, scale 1:1024 contains the
 * temperature category requirements defined by 'tc' as:
 * if (tc[TEMP_CAT] >= 0) require at least this many entries of this category
 * if (tc[TEMP_CAT] <  0) avoid, there shall be no entries of this category
 * TEMP_CAT is any of:
 * Oceanic, Warm, Lush, Cold, Freeing, Special+Warm, Special+Lush, Special+Cold
 * For 1.7-1.17 only.
 */
int checkForTemps(LayerStack *g, uint64_t seed, int x, int z, int w, int h, const int tc[9]);

/* Find the center positions for a given biome id.
 * @pos     : output biome center positions
 * @siz     : output size of biomes (nullable)
 * @nmax    : maximum number of output entries
 * @g       : generator, should be initialized for overworld generation
 * @r       : area to examine, requires: scale = 4, sy = 1
 * @match   : biome id to find
 * @minsiz  : minimum size of output biomes
 * @tol     : border tolerance
 * @stop    : stopping flag (nullable)
 * Returns the number of entries written to pos and siz.
 */
int getBiomeCenters(
        Pos           * pos,
        int           * siz,
        int             nmax,
        Generator     * g,
        Range           r,
        int             match,
        int             minsiz,
        int             tol,
        volatile char * stop
        );

/* Checks if a biome may generate given a version and layer ID as entry point.
 * The supported layers are:
 * L_BIOME_256, L_BAMBOO_256, L_BIOME_EDGE_64, L_HILLS_64, L_SUNFLOWER_64,
 * L_SHORE_16, L_RIVER_MIX_4, L_OCEAN_MIX_4, L_VORONOI_1
 * (provided the version matches)
 */
int canBiomeGenerate(int layerId, int mc, uint32_t flags, int biomeID);

/* Given a 'biomeID' at a generation 'layerId', this functions finds which
 * biomes may generate from it. The result is stored in the bitfields:
 * mL : for ids 0-63
 * mM : for ids 128-191
 */
void genPotential(uint64_t *mL, uint64_t *mM, int layerId, int mc, uint32_t flags, int biomeID);

/* Gets the biomes that can generate in the given version and layer ID.
 * In contrast to canBiomeGenerate() and genPotential() it also supports
 * L_OCEAN_TEMP_256 and 1.18+, where the layerId is ignored.
 * mL : for ids 0-63
 * mM : for ids 128-191
 */
void getAvailableBiomes(uint64_t *mL, uint64_t *mM, int layerId, int mc, uint32_t flags);

//==============================================================================
// Biome Noise Finders (for 1.18+)
//==============================================================================

/**
 * Runs a gradient descent towards the minimum of the noise parameter times a
 * given factor. The algorithm is restricted to the area (x,z,w,h) and starts
 * at (i0,j0) relative to (x,z). The iteration is terminated when either
 * 1) a fix point has been reached,
 * 2) maxiter iterations have been completed,
 * 3) or the sampling position has moved more than maxrad away from (i0,j0).
 *
 * Alpha is an optimization argument that is used to determine the length of
 * large steps based on the current gradient.
 *
 * Optionally, the iteration can also call the custom function:
 *  func(data, x, z, factor*para_noise(x,z));
 *
 * The return value is the minimum value reached.
 */
double getParaDescent(const DoublePerlinNoise *para, double factor,
    int x, int z, int w, int h, int i0, int j0, int maxrad,
    int maxiter, double alpha, void *data, int (*func)(void*,int,int,double));

/**
 * Determines the value range of a climate noise parameter over the given area.
 * The sampling has scale 1:4 and sampling shift is not considered, so biomes
 * could potentially *leak* in at the boarders.
 * An optional function:
 *  func(data, x, z, climate_noise(x,z))
 * is called in each gradient descent iteration. If this function returns
 * non-zero the search is aborted, the results are undefined and a non-zero
 * error is returned.
 *
 * The results are written to pmin and pmax (which would be cast to an integer
 * during boime mapping). Nullable, to look for minima and maxima separately.
 */
int getParaRange(const DoublePerlinNoise *para, double *pmin, double *pmax,
    int x, int z, int w, int h, void *data, int (*func)(void*,int,int,double));

/**
 * Gets the min/max parameter values within which a biome change can occur.
 */
const int *getBiomeParaExtremes(int mc);

/**
 * Gets the min/max possible noise parameter values at which the given biome
 * can generate. The values are in min/max pairs in order of:
 * temperature, humidity, continentalness, erosion, depth, weirdness.
 */
const int *getBiomeParaLimits(int mc, int id);

/**
 * Determines which biomes are able to generate given a set of climate
 * parameter limits. Possible biomes are marked non-zero in the 'ids'.
 */
void getPossibleBiomesForLimits(char ids[256], int mc, int limits[6][2]);

/**
 * Find the largest rectangle in ids[sx][sz] which consists only of 'match'.
 * The limit corners are written to p0 and p1. Returned is the rectangle's area.
 */
int getLargestRec(int match, const int *ids, int sx, int sz, Pos *p0, Pos *p1);

//==============================================================================
// Implementaions for Functions that Ideally Should be Inlined
//==============================================================================


static inline ATTR(const)
Pos getFeatureChunkInRegion(StructureConfig config, uint64_t seed, int regX, int regZ)
{
    /*
    // Vanilla like implementation.
    setSeed(&seed, regX*341873128712 + regZ*132897987541 + seed + config.salt);

    Pos pos;
    pos.x = nextInt(&seed, 24);
    pos.z = nextInt(&seed, 24);
    */
    Pos pos;
    if (config.rngType == JAVA_RANDOM)
    {
    const uint64_t K = 0x5deece66dULL;
    const uint64_t M = (1ULL << 48) - 1;
    const uint64_t b = 0xb;

    // set seed
    seed = seed + regX*341873128712ULL + regZ*132897987541ULL + config.salt;
    seed = (seed ^ K);
    seed = (seed * K + b) & M;

    uint64_t r = config.chunkRange;
    if (r & (r-1))
    {
        pos.x = (int)(seed >> 17) % r;
        seed = (seed * K + b) & M;
        pos.z = (int)(seed >> 17) % r;
    }
    else
    {
        // Java RNG treats powers of 2 as a special case.
        pos.x = (int)((r * (seed >> 17)) >> 31);
        seed = (seed * K + b) & M;
        pos.z = (int)((r * (seed >> 17)) >> 31);
    }
    }
    else { // other structures
        setRegionSeed(seed, regX, regZ, config.salt);
        pos.x = nextInt(config.chunkRange);
        pos.z = nextInt(config.chunkRange);
    }

    return pos;
}

static inline ATTR(const)
Pos getFeaturePos(StructureConfig config, uint64_t seed, int regX, int regZ)
{
    Pos pos = getFeatureChunkInRegion(config, seed, regX, regZ);

    pos.x = (int)(((uint64_t)regX*config.regionSize + pos.x) << 4);
    pos.z = (int)(((uint64_t)regZ*config.regionSize + pos.z) << 4);
    if (config.structType != Abandoned_Camp)
    {
        pos.x+=8;
        pos.z+=8;
    }
    return pos;
}

static inline ATTR(const)
Pos getLargeStructureChunkInRegion(StructureConfig config, uint64_t seed, int regX, int regZ)
{
    Pos pos;
    if (config.rngType == JAVA_RANDOM)
    {
    const uint64_t K = 0x5deece66dULL;
    const uint64_t M = (1ULL << 48) - 1;
    const uint64_t b = 0xb;

    //TODO: power of two chunk ranges...

    // set seed
    seed = seed + regX*341873128712ULL + regZ*132897987541ULL + config.salt;
    seed = (seed ^ K);

    seed = (seed * K + b) & M;
    pos.x = (int)(seed >> 17) % config.chunkRange;
    seed = (seed * K + b) & M;
    pos.x += (int)(seed >> 17) % config.chunkRange;

    seed = (seed * K + b) & M;
    pos.z = (int)(seed >> 17) % config.chunkRange;
    seed = (seed * K + b) & M;
    pos.z += (int)(seed >> 17) % config.chunkRange;

    pos.x >>= 1;
    pos.z >>= 1;
    }
    else { // other structures
        setRegionSeed(seed, regX, regZ, config.salt);
        pos.x = (nextInt(config.chunkRange) + nextInt(config.chunkRange)) / 2;
        pos.z = (nextInt(config.chunkRange) + nextInt(config.chunkRange)) / 2;
    }

    return pos;
}

static inline ATTR(const)
Pos getLargeStructurePos(StructureConfig config, uint64_t seed, int regX, int regZ)
{
    Pos pos = getLargeStructureChunkInRegion(config, seed, regX, regZ);
    pos.x = (int)(((uint64_t)regX*config.regionSize + pos.x) << 4);
    pos.z = (int)(((uint64_t)regZ*config.regionSize + pos.z) << 4);
    if (config.structType != Abandoned_Camp && config.structType != Outpost)
    {
        pos.x+=8;
        pos.z+=8;
    }
    return pos;
}

static inline ATTR(const)
Pos chunkToRegion(int chunkX, int chunkZ, int regionSize)
{
    Pos p;
    p.x = chunkX / regionSize - (chunkX < 0 && chunkX % regionSize);
    p.z = chunkZ / regionSize - (chunkZ < 0 && chunkZ % regionSize);
    return p;
}

// village 1.0-1.10
static inline int regionOffset(int coord, int regionSize) {
    return ((coord % regionSize) + regionSize) % regionSize;
}

static inline ATTR(const)
int isVillageChunk(StructureConfig config, uint64_t seed, int chunkX, int chunkZ)
{
    int regionSize = 40;
    int chunkRange = 28;//40 - 12
    int regionX = chunkX < 0 ? chunkX - regionSize + 1 : chunkX;
    int regionZ = chunkZ < 0 ? chunkZ - regionSize + 1 : chunkZ;
    setRegionSeed(seed, regionX, regionZ, config.salt);
    if (nextInt(chunkRange) != regionOffset(chunkX, regionSize)) return 0;
    if (nextInt(chunkRange) != regionOffset(chunkZ, regionSize)) return 0;
    return 1;
}


#ifdef __cplusplus
}
#endif

#endif // FINDERS_H_
````

## File: vendor/cubiomes-bedrock/mt.h

SHA-256: 21e1acc1311d4f6109f26669e600646e214c008d14294f5a1a5a57c8d8ea3f5a

````c
#ifndef mt_H_
#define mt_H_

#define __STDC_LIMIT_MACROS
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C"
{
#endif

uint32_t mt_next();
void mt_seed(uint32_t seed_value);

typedef struct MTRngState
{
    uint32_t MT[624];
    size_t index;
    size_t index_fast;
    uint64_t ws;
    int a;
    int b;
} MTRngState;

void mt_get_state(MTRngState *out);
void mt_set_state(const MTRngState *in);

#ifdef _MSC_VER
extern __declspec(thread) uint64_t mt_ws;
extern __declspec(thread) int mt_a;
extern __declspec(thread) int mt_b;
#else
extern __thread uint64_t mt_ws;
extern __thread int mt_a;
extern __thread int mt_b;
#endif

static inline void setSeed(uint32_t value)
{
    mt_seed(value);
}

static inline int next()
{
    return (int)(mt_next() >> 1);
}

static inline int nextInt(const int n)
{
    return (int)(mt_next() % n);
}

static inline int nextIntRange(const int a, const int b)
{
    return (a < b) ? (a + nextInt(b - a)) : a;
}

static inline int nextBoolean()
{
    return (mt_next() & 0x8000000) != 0;
}

static inline double nextDouble()
{
    return mt_next() * (1.0 / 4294967296.0);
}

static inline float nextFloat()
{
    return (float)nextDouble();
}

static inline void skipNextN(int n)
{
    for (int i = 0; i < n; i++) mt_next();
}

//==============================================================================
// ChunkRandom
//==============================================================================

#define REGION_A 341873128712L
#define REGION_B 132897987541L

static inline int32_t setTerrainSeed(int chunkX, int chunkZ)
{
    uint32_t seed = (chunkX * REGION_A + chunkZ * REGION_B);
    setSeed(seed);
    return seed;
}

static inline uint32_t setPopulationSeed(uint64_t worldSeed, int chunkX, int chunkZ)
{
    if (mt_ws != worldSeed)
    {
        setSeed(worldSeed);
        mt_a = next();
        mt_b = next();
        mt_ws = worldSeed;
    }
    uint32_t seed = (chunkX * (mt_a | 1u) + chunkZ * (mt_b | 1u)) ^ worldSeed;
    setSeed(seed);
    return seed;
}

static inline uint32_t setDecorationSeed(uint64_t worldSeed, int chunkX, int chunkZ, int salt)
{
    if (mt_ws != worldSeed)
    {
        setSeed(worldSeed);
        mt_a = next();
        mt_b = next();
        mt_ws = worldSeed;
    }
    uint32_t seed = (chunkX * (mt_a | 1u) + chunkZ * (mt_b | 1u)) ^ worldSeed;
    seed = ((seed >> 2) + (seed << 6) + salt - 1640531527u) ^ seed;
    setSeed(seed);
    return seed;
}

static inline uint32_t setCarverSeed(uint64_t worldSeed, int chunkX, int chunkZ)
{
    if (mt_ws != worldSeed)
    {
        setSeed(worldSeed);
        mt_a = next();
        mt_b = next();
        mt_ws = worldSeed;
    }
    uint32_t seed = (chunkX * mt_a) ^ (chunkZ * mt_b) ^ worldSeed;
    setSeed(seed);
    return seed;
}

static inline uint32_t setRegionSeed(uint64_t worldSeed, int regX, int regZ, int salt)
{
    uint32_t seed = (regX * REGION_A) + (regZ * REGION_B) + worldSeed + salt;
    setSeed(seed);
    return seed;
}

static inline uint32_t setFortressSeed(uint64_t worldSeed, int chunkX, int chunkZ)
{
    uint32_t seed = ((chunkX >> 4) ^ ((chunkZ >> 4) << 4)) ^ worldSeed;
    setSeed(seed);
    return seed;
}

static inline uint32_t seedSlimeChunk(int chunkX, int chunkZ)
{
    uint32_t seed = (chunkX * 522133279U) ^ chunkZ;
    setSeed(seed);
    return seed;
}

#ifdef __cplusplus
}
#endif

#endif
````

## File: vendor/cubiomes-bedrock/mt.c

SHA-256: 853e8b94e2fb024f2c9489d08144fa81e502d641bbb8f2f35c7b5d3b1a59358b

````c
/*
   A C-program for MT19937, with initialization improved 2002/1/26.
   Coded by Takuji Nishimura and Makoto Matsumoto.
   
   Copyright (C) 1997 - 2002, Makoto Matsumoto and Takuji Nishimura,
   All rights reserved.
   
   http://www.math.sci.hiroshima-u.ac.jp/~m-mat/MT/emt.html
*/

#include <stdio.h>
#include "mt.h"

#define SIZE 624
#define PERIOD 397
#define DIFF (SIZE - PERIOD)

static const uint32_t MAGIC = 0x9908b0df;

struct MTState_
{
  uint32_t MT[SIZE];
  size_t index;
  size_t index_fast; /* lazy init progress */
};

typedef struct MTState_ MTState;

#ifdef _MSC_VER
__declspec(thread) static MTState state;
__declspec(thread) uint64_t mt_ws = (uint64_t)-1;
__declspec(thread) int mt_a;
__declspec(thread) int mt_b;
#else
static __thread MTState state;
__thread uint64_t mt_ws = (uint64_t)-1;
__thread int mt_a;
__thread int mt_b;
#endif

#define M32(x) ((x) & 0x80000000)
#define L31(x) ((x) & 0x7FFFFFFF)
#define MIXBITS(u,v) (M32(u) | L31(v))
#define TWIST(u,v) ((MIXBITS(u,v) >> 1) ^ ((v & 1) ? MAGIC : 0))

static inline uint32_t generate()
{
  size_t idx = state.index;
  if (idx == SIZE) idx = 0;

  if (idx >= DIFF)
  {
    if (idx >= SIZE - 1)
      state.MT[SIZE-1] = state.MT[PERIOD-1] ^ TWIST(state.MT[SIZE-1], state.MT[0]);
    else
      state.MT[idx] = state.MT[idx - DIFF] ^ TWIST(state.MT[idx], state.MT[idx+1]);
  }
  else 
  {
    state.MT[idx] = state.MT[idx + PERIOD] ^ TWIST(state.MT[idx], state.MT[idx+1]);
    /* advance lazy init one slot */
    if (state.index_fast < SIZE)
    {
      state.MT[state.index_fast] = 0x6c078965
        * (state.MT[state.index_fast-1] ^ (state.MT[state.index_fast-1] >> 30))
        + state.index_fast;
      state.index_fast++;
    }
  }

  state.index = idx + 1;
  return state.MT[idx];
}

static inline uint32_t temper(uint32_t y)
{
  y ^= y >> 11;
  y ^= (y << 7) & 0x9d2c5680;
  y ^= (y << 15) & 0xefc60000;
  y ^= y >> 18;
  return y;
}

void mt_seed(uint32_t value)
{
  state.MT[0] = value;
  
  for (uint_fast32_t i = 1; i <= PERIOD; ++i)
    state.MT[i] = 0x6c078965 * (state.MT[i - 1] ^ (state.MT[i - 1] >> 30)) + i;
  
  state.index_fast = PERIOD + 1;
  state.index = SIZE;
}

uint32_t mt_next()
{
  if (state.index > SIZE) {
    /* called without mt_seed(): full init with default seed */
    for (uint_fast32_t i = 1; i < SIZE; ++i)
      state.MT[i] = 0x6c078965 * (state.MT[i - 1] ^ (state.MT[i - 1] >> 30)) + i;
    state.index_fast = SIZE;
    state.index = SIZE;
  }
  
  return temper(generate());
}

void mt_get_state(MTRngState *out)
{
  size_t i;
  for (i = 0; i < SIZE; i++)
    out->MT[i] = state.MT[i];
  out->index = state.index;
  out->index_fast = state.index_fast;
  out->ws = mt_ws;
  out->a = mt_a;
  out->b = mt_b;
}

void mt_set_state(const MTRngState *in)
{
  size_t i;
  for (i = 0; i < SIZE; i++)
    state.MT[i] = in->MT[i];
  state.index = in->index;
  state.index_fast = in->index_fast;
  mt_ws = in->ws;
  mt_a = in->a;
  mt_b = in->b;
}
````

## File: vendor/cubiomes-bedrock/rng.h

SHA-256: 1342594d0d26f0a3f7436b386ab46491181f8035778fdd257427d8caed9277ed

````c
#ifndef RNG_H_
#define RNG_H_

#define __STDC_FORMAT_MACROS 1

#include <stdlib.h>
#include <stddef.h>
#include <inttypes.h>


///=============================================================================
///                      Compiler and Platform Features
///=============================================================================

typedef int8_t      i8;
typedef uint8_t     u8;
typedef int16_t     i16;
typedef uint16_t    u16;
typedef int32_t     i32;
typedef uint32_t    u32;
typedef int64_t     i64;
typedef uint64_t    u64;
typedef float       f32;
typedef double      f64;


#define STRUCT(S) typedef struct S S; struct S

#if __GNUC__

#define IABS(X)                 __builtin_abs(X)
#define PREFETCH(PTR,RW,LOC)    __builtin_prefetch(PTR,RW,LOC)
#define likely(COND)            (__builtin_expect(!!(COND),1))
#define unlikely(COND)          (__builtin_expect((COND),0))
#define ATTR(...)               __attribute__((__VA_ARGS__))
#define BSWAP32(X)              __builtin_bswap32(X)
#define UNREACHABLE()           __builtin_unreachable()

#else

#define IABS(X)                 ((int)abs(X))
#define PREFETCH(PTR,RW,LOC)
#define likely(COND)            (COND)
#define unlikely(COND)          (COND)
#define ATTR(...)
static inline uint32_t BSWAP32(uint32_t x) {
    x = ((x & 0x000000ff) << 24) | ((x & 0x0000ff00) <<  8) |
        ((x & 0x00ff0000) >>  8) | ((x & 0xff000000) >> 24);
    return x;
}
#if _MSC_VER
#define UNREACHABLE()           __assume(0)
#else
#define UNREACHABLE()           exit(1) // [[noreturn]]
#endif

#endif

/// imitate amd64/x64 rotate instructions

static inline ATTR(const, always_inline, artificial)
uint64_t rotl64(uint64_t x, uint8_t b)
{
    return (x << b) | (x >> (64-b));
}

static inline ATTR(const, always_inline, artificial)
uint32_t rotr32(uint32_t a, uint8_t b)
{
    return (a >> b) | (a << (32-b));
}

/// integer floor divide
static inline ATTR(const, always_inline)
int32_t floordiv(int32_t a, int32_t b)
{
    int32_t q = a / b;
    int32_t r = a % b;
    return q - ((a ^ b) < 0 && !!r);
}

///=============================================================================
///                    C implementation of Java Random
///=============================================================================

static inline void JsetSeed(uint64_t *seed, uint64_t value)
{
    *seed = (value ^ 0x5deece66d) & ((1ULL << 48) - 1);
}

static inline int Jnext(uint64_t *seed, const int bits)
{
    *seed = (*seed * 0x5deece66d + 0xb) & ((1ULL << 48) - 1);
    return (int) ((int64_t)*seed >> (48 - bits));
}

static inline int JnextInt(uint64_t *seed, const int n)
{
    int bits, val;
    const int m = n - 1;

    if ((m & n) == 0) {
        uint64_t x = n * (uint64_t)Jnext(seed, 31);
        return (int) ((int64_t) x >> 31);
    }

    do {
        bits = Jnext(seed, 31);
        val = bits % n;
    }
    while ((int32_t)((uint32_t)bits - val + m) < 0);
    return val;
}

static inline uint64_t JnextLong(uint64_t *seed)
{
    return ((uint64_t) Jnext(seed, 32) << 32) + Jnext(seed, 32);
}

static inline float JnextFloat(uint64_t *seed)
{
    return Jnext(seed, 24) / (float) (1 << 24);
}

static inline double JnextDouble(uint64_t *seed)
{
    uint64_t x = (uint64_t)Jnext(seed, 26);
    x <<= 27;
    x += Jnext(seed, 27);
    return (int64_t) x / (double) (1ULL << 53);
}

/* A macro to generate the ideal assembly for X = JnextInt(*S, 24)
 * This is a macro and not an inline function, as many compilers can make use
 * of the additional optimisation passes for the surrounding code.
 */
#define JAVA_NEXT_INT24(S,X)                \
    do {                                    \
        uint64_t a = (1ULL << 48) - 1;      \
        uint64_t c = 0x5deece66dULL * (S);  \
        c += 11; a &= c;                    \
        (S) = a;                            \
        a = (uint64_t) ((int64_t)a >> 17);  \
        c = 0xaaaaaaab * a;                 \
        c = (uint64_t) ((int64_t)c >> 36);  \
        (X) = (int)a - (int)(c << 3) * 3;   \
    } while (0)


/* Jumps forwards in the random number sequence by simulating 'n' calls to next.
 */
static inline void JskipNextN(uint64_t *seed, uint64_t n)
{
    uint64_t m = 1;
    uint64_t a = 0;
    uint64_t im = 0x5deece66dULL;
    uint64_t ia = 0xb;
    uint64_t k;

    for (k = n; k; k >>= 1)
    {
        if (k & 1)
        {
            m *= im;
            a = im * a + ia;
        }
        ia = (im + 1) * ia;
        im *= im;
    }

    *seed = *seed * m + a;
    *seed &= 0xffffffffffffULL;
}


///=============================================================================
///                               Xoroshiro 128
///=============================================================================

STRUCT(Xoroshiro)
{
    uint64_t lo, hi;
};

static inline void xSetSeed(Xoroshiro *xr, uint64_t value)
{
    const uint64_t XL = 0x9e3779b97f4a7c15ULL;
    const uint64_t XH = 0x6a09e667f3bcc909ULL;
    const uint64_t A = 0xbf58476d1ce4e5b9ULL;
    const uint64_t B = 0x94d049bb133111ebULL;
    uint64_t l = value ^ XH;
    uint64_t h = l + XL;
    l = (l ^ (l >> 30)) * A;
    h = (h ^ (h >> 30)) * A;
    l = (l ^ (l >> 27)) * B;
    h = (h ^ (h >> 27)) * B;
    l = l ^ (l >> 31);
    h = h ^ (h >> 31);
    xr->lo = l;
    xr->hi = h;
}

static inline uint64_t xNextLong(Xoroshiro *xr)
{
    uint64_t l = xr->lo;
    uint64_t h = xr->hi;
    uint64_t n = rotl64(l + h, 17) + l;
    h ^= l;
    xr->lo = rotl64(l, 49) ^ h ^ (h << 21);
    xr->hi = rotl64(h, 28);
    return n;
}

static inline int xNextInt(Xoroshiro *xr, uint32_t n)
{
    uint64_t r = (xNextLong(xr) & 0xFFFFFFFF) * n;
    if ((uint32_t)r < n)
    {
        while ((uint32_t)r < (~n + 1) % n)
        {
            r = (xNextLong(xr) & 0xFFFFFFFF) * n;
        }
    }
    return r >> 32;
}

static inline double xNextDouble(Xoroshiro *xr)
{
    return (xNextLong(xr) >> (64-53)) * 1.1102230246251565E-16;
}

static inline float xNextFloat(Xoroshiro *xr)
{
    return (xNextLong(xr) >> (64-24)) * 5.9604645E-8F;
}

static inline void xSkipN(Xoroshiro *xr, int count)
{
    while (count --> 0)
        xNextLong(xr);
}

static inline uint64_t xNextLongJ(Xoroshiro *xr)
{
    int32_t a = xNextLong(xr) >> 32;
    int32_t b = xNextLong(xr) >> 32;
    return ((uint64_t)a << 32) + b;
}

static inline int xNextIntJ(Xoroshiro *xr, uint32_t n)
{
    int bits, val;
    const int m = n - 1;

    if ((m & n) == 0) {
        uint64_t x = n * (xNextLong(xr) >> 33);
        return (int) ((int64_t) x >> 31);
    }

    do {
        bits = (xNextLong(xr) >> 33);
        val = bits % n;
    }
    while ((int32_t)((uint32_t)bits - val + m) < 0);
    return val;
}


//==============================================================================
//                              MC Seed Helpers
//==============================================================================

/**
 * The seed pipeline:
 *
 * getLayerSalt(n)                -> layerSalt (ls)
 * layerSalt (ls), worldSeed (ws) -> startSalt (st), startSeed (ss)
 * startSeed (ss), coords (x,z)   -> chunkSeed (cs)
 *
 * The chunkSeed alone is enough to generate the first PRNG integer with:
 *   mcFirstInt(cs, mod)
 * subsequent PRNG integers are generated by stepping the chunkSeed forwards,
 * salted with startSalt:
 *   cs_next = mcStepSeed(cs, st)
 */

static inline uint64_t mcStepSeed(uint64_t s, uint64_t salt)
{
    return s * (s * 6364136223846793005ULL + 1442695040888963407ULL) + salt;
}

static inline int mcFirstInt(uint64_t s, int mod)
{
    int ret = (int)(((int64_t)s >> 24) % mod);
    if (ret < 0)
        ret += mod;
    return ret;
}

static inline int mcFirstIsZero(uint64_t s, int mod)
{
    return (int)(((int64_t)s >> 24) % mod) == 0;
}

static inline uint64_t getChunkSeed(uint64_t ss, int x, int z)
{
    uint64_t cs = ss + x;
    cs = mcStepSeed(cs, z);
    cs = mcStepSeed(cs, x);
    cs = mcStepSeed(cs, z);
    return cs;
}

static inline uint64_t getLayerSalt(uint64_t salt)
{
    uint64_t ls = mcStepSeed(salt, salt);
    ls = mcStepSeed(ls, salt);
    ls = mcStepSeed(ls, salt);
    return ls;
}

static inline uint64_t getStartSalt(uint64_t ws, uint64_t ls)
{
    uint64_t st = ws;
    st = mcStepSeed(st, ls);
    st = mcStepSeed(st, ls);
    st = mcStepSeed(st, ls);
    return st;
}

static inline uint64_t getStartSeed(uint64_t ws, uint64_t ls)
{
    uint64_t ss = ws;
    ss = getStartSalt(ss, ls);
    ss = mcStepSeed(ss, 0);
    return ss;
}


///============================================================================
///                               Arithmatic
///============================================================================


/* Linear interpolations
 */
static inline double lerp(double part, double from, double to)
{
    return from + part * (to - from);
}

static inline double lerp2(
        double dx, double dy, double v00, double v10, double v01, double v11)
{
    return lerp(dy, lerp(dx, v00, v10), lerp(dx, v01, v11));
}

static inline double lerp3(
        double dx, double dy, double dz,
        double v000, double v100, double v010, double v110,
        double v001, double v101, double v011, double v111)
{
    v000 = lerp2(dx, dy, v000, v100, v010, v110);
    v001 = lerp2(dx, dy, v001, v101, v011, v111);
    return lerp(dz, v000, v001);
}

static inline double clampedLerp(double part, double from, double to)
{
    if (part <= 0) return from;
    if (part >= 1) return to;
    return lerp(part, from, to);
}

/* Find the modular inverse: (1/x) | mod m.
 * Assumes x and m are positive (less than 2^63), co-prime.
 */
static inline ATTR(const)
uint64_t mulInv(uint64_t x, uint64_t m)
{
    uint64_t t, q, a, b, n;
    if ((int64_t)m <= 1)
        return 0; // no solution

    n = m;
    a = 0; b = 1;

    while ((int64_t)x > 1)
    {
        if (m == 0)
            return 0; // x and m are co-prime
        q = x / m;
        t = m; m = x % m;     x = t;
        t = a; a = b - q * a; b = t;
    }

    if ((int64_t)b < 0)
        b += n;
    return b;
}


#endif /* RNG_H_ */
````

## File: vendor/cubiomes-bedrock/biomes.h

SHA-256: 3231c509e8129d2f6782e8dcfa83fc4e039e688fdf5c0c6e24cbdaea17fe45a4

````c
#ifndef BIOMES_H_
#define BIOMES_H_

/* Minecraft versions */
enum MCVersion
{   // MC_1_X refers to the latest patch of the respective 1.X release.
    // NOTE: Development effort focuses on just the newest patch for each major
    // release. Minor releases and major versions <= 1.0 are experimental.
    MC_UNDEF,
    MC_B1_7,
    MC_B1_8,
    MC_1_0_0,  MC_1_0  = MC_1_0_0,
    MC_1_1_0,  MC_1_1  = MC_1_1_0,
    MC_1_2_0,  MC_1_2  = MC_1_2_0,
    MC_1_4_0,  MC_1_4  = MC_1_4_0,
    MC_1_5_0,  MC_1_5  = MC_1_5_0,
    MC_1_6_0,  MC_1_6  = MC_1_6_0,
    MC_1_7_0,  MC_1_7  = MC_1_7_0,
    MC_1_8_0,  MC_1_8  = MC_1_8_0,
    MC_1_9_0,  MC_1_9  = MC_1_9_0,
    MC_1_10_0, MC_1_10 = MC_1_10_0,
    MC_1_11_0, MC_1_11 = MC_1_11_0,
    MC_1_12_0, MC_1_12 = MC_1_12_0,
    MC_1_13_0, MC_1_13 = MC_1_13_0,
    MC_1_14_0, MC_1_14 = MC_1_14_0,
    MC_1_16_0, MC_1_16 = MC_1_16_0,
    MC_1_17_0, MC_1_17 = MC_1_17_0,
    MC_1_17_30,
    MC_1_18_0, MC_1_18 = MC_1_18_0,
    MC_1_19_0, MC_1_19 = MC_1_19_0,
    MC_1_20_0, MC_1_20 = MC_1_20_0,
    MC_1_21_0, MC_1_21 = MC_1_21_0,
    MC_1_21_50,
    MC_1_21_60,
    MC_26_20,
    MC_26_30, // preview 26.30.20
    MC_26_40, // preview 26.40.27
    MC_26_50,
    MC_26_60, // preview 26.60.29
    MC_NEWEST = MC_26_60,
};

enum Dimension
{
    DIM_NETHER      =   -1,
    DIM_OVERWORLD   =    0,
    DIM_END         =   +1,
    DIM_UNDEF       = 1000,
};

enum BiomeID
{
    none = -1,
    // 0
    ocean = 0,
    plains,
    desert,
    mountains,                  extremeHills = mountains,
    forest,
    taiga,
    swamp,                      swampland = swamp,
    river,
    nether_wastes,              hell = nether_wastes,
    the_end,                    sky = the_end,
    // 10
    frozen_ocean,               frozenOcean = frozen_ocean,
    frozen_river,               frozenRiver = frozen_river,
    snowy_tundra,               icePlains = snowy_tundra,
    snowy_mountains,            iceMountains = snowy_mountains,
    mushroom_fields,            mushroomIsland = mushroom_fields,
    mushroom_field_shore,       mushroomIslandShore = mushroom_field_shore,
    beach,
    desert_hills,               desertHills = desert_hills,
    wooded_hills,               forestHills = wooded_hills,
    taiga_hills,                taigaHills = taiga_hills,
    // 20
    mountain_edge,              extremeHillsEdge = mountain_edge,
    jungle,
    jungle_hills,               jungleHills = jungle_hills,
    jungle_edge,                jungleEdge = jungle_edge,
    deep_ocean,                 deepOcean = deep_ocean,
    stone_shore,                stoneBeach = stone_shore,
    snowy_beach,                coldBeach = snowy_beach,
    birch_forest,               birchForest = birch_forest,
    birch_forest_hills,         birchForestHills = birch_forest_hills,
    dark_forest,                roofedForest = dark_forest,
    // 30
    snowy_taiga,                coldTaiga = snowy_taiga,
    snowy_taiga_hills,          coldTaigaHills = snowy_taiga_hills,
    giant_tree_taiga,           megaTaiga = giant_tree_taiga,
    giant_tree_taiga_hills,     megaTaigaHills = giant_tree_taiga_hills,
    wooded_mountains,           extremeHillsPlus = wooded_mountains,
    savanna,
    savanna_plateau,            savannaPlateau = savanna_plateau,
    badlands,                   mesa = badlands,
    wooded_badlands_plateau,    mesaPlateau_F = wooded_badlands_plateau,
    badlands_plateau,           mesaPlateau = badlands_plateau,
    // 40  --  1.13
    small_end_islands,
    end_midlands,
    end_highlands,
    end_barrens,
    warm_ocean,                 warmOcean = warm_ocean,
    lukewarm_ocean,             lukewarmOcean = lukewarm_ocean,
    cold_ocean,                 coldOcean = cold_ocean,
    deep_warm_ocean,            warmDeepOcean = deep_warm_ocean,
    deep_lukewarm_ocean,        lukewarmDeepOcean = deep_lukewarm_ocean,
    deep_cold_ocean,            coldDeepOcean = deep_cold_ocean,
    // 50
    deep_frozen_ocean,          frozenDeepOcean = deep_frozen_ocean,
    // Alpha 1.2 - Beta 1.7
    seasonal_forest,
    rainforest,
    shrubland,


    the_void = 127,

    // mutated variants
    sunflower_plains                = plains+128,
    desert_lakes                    = desert+128,
    gravelly_mountains              = mountains+128,
    flower_forest                   = forest+128,
    taiga_mountains                 = taiga+128,
    swamp_hills                     = swamp+128,
    ice_spikes                      = snowy_tundra+128,
    modified_jungle                 = jungle+128,
    modified_jungle_edge            = jungle_edge+128,
    tall_birch_forest               = birch_forest+128,
    tall_birch_hills                = birch_forest_hills+128,
    dark_forest_hills               = dark_forest+128,
    snowy_taiga_mountains           = snowy_taiga+128,
    giant_spruce_taiga              = giant_tree_taiga+128,
    giant_spruce_taiga_hills        = giant_tree_taiga_hills+128,
    modified_gravelly_mountains     = wooded_mountains+128,
    shattered_savanna               = savanna+128,
    shattered_savanna_plateau       = savanna_plateau+128,
    eroded_badlands                 = badlands+128,
    modified_wooded_badlands_plateau = wooded_badlands_plateau+128,
    modified_badlands_plateau       = badlands_plateau+128,
    // 1.14
    bamboo_jungle                   = 168,
    bamboo_jungle_hills             = 169,
    // 1.16
    soul_sand_valley                = 170,
    crimson_forest                  = 171,
    warped_forest                   = 172,
    basalt_deltas                   = 173,
    // 1.17
    dripstone_caves                 = 174,
    lush_caves                      = 175,
    // 1.18
    meadow                          = 177,
    grove                           = 178,
    snowy_slopes                    = 179,
    jagged_peaks                    = 180,
    frozen_peaks                    = 181,
    stony_peaks                     = 182,
    old_growth_birch_forest         = tall_birch_forest,
    old_growth_pine_taiga           = giant_tree_taiga,
    old_growth_spruce_taiga         = giant_spruce_taiga,
    snowy_plains                    = snowy_tundra,
    sparse_jungle                   = jungle_edge,
    stony_shore                     = stone_shore,
    windswept_hills                 = mountains,
    windswept_forest                = wooded_mountains,
    windswept_gravelly_hills        = gravelly_mountains,
    windswept_savanna               = shattered_savanna,
    wooded_badlands                 = wooded_badlands_plateau,
    // 1.19
    deep_dark                       = 183,
    mangrove_swamp                  = 184,
    // 1.20
    cherry_grove                    = 185,
    // 1.21 Winter Drop
    pale_garden                     = 186,
    // 26.30
    sulfur_caves                    = 187,
    // 26.40.27
    dappled_forest                  = 188,
    // 26.60.29
    ice_caves                       = 189,
};


#ifdef __cplusplus
extern "C"
{
#endif

//==============================================================================
// BiomeID Helper Functions
//==============================================================================

int biomeExists(int mc, int id);
int isOverworld(int mc, int id); // false for biomes that don't generate
int getDimension(int id);
int getMutated(int mc, int id);
int getCategory(int mc, int id);
int areSimilar(int mc, int id1, int id2);
int isMesa(int id);
int isShallowOcean(int id);
int isDeepOcean(int id);
int isOceanic(int id);
int isSnowy(int id);

#ifdef __cplusplus
}
#endif

#endif /* BIOMES_H_ */
````

## File: tests/test_filter_optimization.py

SHA-256: 93e160faf39456ae5a08149bae5538863936267d7a39ff55db6d4f6a34b7e8e2

````python
import copy
import numpy as np
import pytest
from seed_search.backend import Backend, STRUCTURES, RAW_MT_TYPES, _RAW_LAYOUTS
from seed_search.config import load_config
from seed_search.landscapes import (analyze_landscapes, flat_metrics, build_centers,
    ring_metrics, raster_intermediates, basin_necessary_bound, xy_raster)
from seed_search.terrain import raster
from seed_search.structures import possible_required_centers


@pytest.mark.parametrize('seed',[-1,0,12345,4294979641])
def test_combined_scan_preserves_every_supported_family(seed):
    with Backend(seed) as b:
        for name in STRUCTURES:
            bounds=(-6504,-6504,6504,6504) if name=='stronghold' else (-900,-1100,1000,1200)
            assert b.structure_pair(name,bounds)==(b.structures(name,bounds,False),b.structures(name,bounds))


def test_raw_cache_reuses_only_verified_mt_layouts_and_full_seed_viability():
    _RAW_LAYOUTS.clear();bounds=(-1024,-1024,1024,1024)
    for name in RAW_MT_TYPES:
        with Backend(-1,2) as b:raw,_=b.structure_pair(name,bounds)
        with Backend(4294967295,2) as other:
            expected=other.structures(name,bounds)
            # If the second raw enumeration happens, this experiment fails.
            other.structures=lambda *_:pytest.fail('Expected exact raw layout cache hit')
            assert other.structure_pair(name,bounds)==(raw,expected)
    with Backend(12345,2) as b:
        first=b.structure_pair('trial_chamber',bounds)[0]
    with Backend(12345+(1<<32),2) as b:
        assert b.structure_pair('trial_chamber',bounds)[0]!=first
    assert len(_RAW_LAYOUTS)<=2
    with pytest.raises(RuntimeError):b.structure_pair('village',bounds)


def test_joint_required_center_intersection_and_exact_negative_border():
    cfg,_=load_config();scans={'stronghold':{'raw':[(-5000,0)]},'fortress':{'raw':[(800,0)]}}
    assert not possible_required_centers(scans,cfg,(-5000,-5000,5000,5000))
    scans={'stronghold':{'raw':[(-1504,-1504)]},'fortress':{'raw':[(-496,-496)]}}
    assert possible_required_centers(scans,cfg,(0,0,0,0))
    scans['stronghold']['raw']=[(-1505,-1504)]
    assert not possible_required_centers(scans,cfg,(0,0,0,0))
    # Integer ranges can overlap while containing no allowed eight-block center.
    scans['stronghold']['raw']=[(1505,1505)]
    assert not possible_required_centers(scans,cfg,(1,1,7,7))


def test_missing_stronghold_fast_path_defers_before_any_terrain(monkeypatch):
    cfg,_=load_config();cfg['optimization']['exact_per_seed_cache']=False
    class EmptyBackend:
        def __init__(self,*_):pass
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def structure_pair(self,name,bounds):assert name=='stronghold';return [],[]
        def grid(self,*_):pytest.fail('Fast deferred seed must not generate terrain')
    monkeypatch.setattr('seed_search.landscapes.Backend',EmptyBackend)
    r=analyze_landscapes((3,12345,cfg))
    assert r['candidates']==[] and r['counts']['discovery_points']==0
    assert r['near_misses'][0]['reason']=='deferred_seed_no_joint_required_prediction'
    assert r['near_misses'][0]['stronghold_completeness']=='unknown'


class Ground:
    def __init__(self,kind):self.kind=kind
    def heights(self,points,vertical_step=8):
        p=np.asarray(points);x,z=p[:,0],p[:,1];r=np.hypot(x,z)
        h=np.full(len(p),72,dtype=np.int32)
        if self.kind=='water':h[:]=50
        if self.kind=='ring':h[(r>=300)&(r<=400)]=160
        if self.kind=='recenter':
            h=72+(x%64).astype(np.int32)
            h[np.hypot(x-192,z)<=112]=72
            h[(np.hypot(x-192,z)>=300)&(np.hypot(x-192,z)<=400)]=160
            h[r<=64]=50
        return h,np.ones(len(p),np.int32)


@pytest.mark.parametrize('kind',['water','plain','ring','recenter'])
def test_basin_impossibility_bound_never_vetoes_reference_survivor(kind):
    cfg,_=load_config();cfg['landscapes']['ring_radius_blocks']=500
    backend=Ground(kind);center=[0,0];s=cfg['landscapes']
    full=raster(backend,(-1504,-1504,1504,1504),16);context=raster_intermediates(full)
    x,z=xy_raster(full)
    centers=[center]+[site['center'] for site in build_centers(full,np.hypot(x,z)<=256,[-5000,5000],8,context)]
    passes=[]
    for c in centers:
        f,_,connected=flat_metrics(full,c,s,context)
        rr=ring_metrics(full,c,s,connected,f['inner_height_median'])
        passes.append(f['flat_ground_preference_met'] and rr['dry_mountain_basin_preference_met'])
    bound=basin_necessary_bound(backend,center,cfg)
    if kind in ('ring','recenter'):assert any(passes), 'Positive control must actually survive the reference'
    if any(passes):assert not bound['impossible']
    if kind=='water':assert bound['impossible'] and bound['reason']=='dry_or_gentle_upper_bound'
    assert bound['points']<full['points']


def test_shared_raster_intermediates_preserve_negative_off_lattice_recenters():
    cfg,_=load_config();terrain=raster(Ground('recenter'),(-1512,-1480,1496,1528),16)
    context=raster_intermediates(terrain)
    for c in [(-8,24),(184,24),(-256,-200)]:
        fresh=flat_metrics(terrain,c,cfg['landscapes']);shared=flat_metrics(terrain,c,cfg['landscapes'],context)
        assert fresh[0]==shared[0]
        assert all(np.array_equal(a,b) for a,b in zip(fresh[1:],shared[1:]))
    allowed=np.hypot(context['x']+8,context['z']-24)<=256
    assert build_centers(terrain,allowed,[-5000,5000],8)==build_centers(terrain,allowed,[-5000,5000],8,context)


def test_rejected_rounding_patch_is_not_installed():
    with Backend(9) as b:
        assert b.structures('stronghold',(-920,630,-890,660))==[(-908,644)]
````

## File: runs/stronghold-investigation/diagnose.py

SHA-256: 19bcd6ea8a192a065149388b84cc8acd7a74d55564cf57fc49746c1fd71104d8

````python
"""Read-only iterator experiments; these variants are NOT production predictions.

Run from the project root with .venv/bin/python runs/stronghold-investigation/diagnose.py.
Uses the installed backend for MT and village placement/viability. Does not change it.
"""
import ctypes
import itertools
import json
import math
from pathlib import Path

from seed_search import _native
from seed_search.backend import Backend, biome_name

native = ctypes.CDLL(_native.__file__)
native.mt_seed.argtypes = [ctypes.c_uint32]
native.mt_seed.restype = None
native.mt_next.argtypes = []
native.mt_next.restype = ctypes.c_uint32
f32 = lambda x: ctypes.c_float(x).value


def replay(seed, rounding_x, rounding_z, eligibility):
    native.mt_seed(seed & 0xffffffff)
    angle = f32(2 * math.pi * f32(native.mt_next() / 4294967296))
    distance = 40 + native.mt_next() % 16
    accepted, trace = [], []
    rounders = {"floor": math.floor, "truncate": int}
    with Backend(seed) as backend:
        cache = {}
        for step in range(10000):
            cx = rounders[rounding_x](math.cos(angle) * distance)
            cz = rounders[rounding_z](math.sin(angle) * distance)
            candidates = []
            for rx in range((cx - 8) // 34, (cx + 7) // 34 + 1):
                for rz in range((cz - 8) // 34, (cz + 7) // 34 + 1):
                    if (rx, rz) not in cache:
                        p = backend.attempt("village", rx, rz)
                        viable = bool(p and backend.structures("village", (*p, *p)))
                        name = biome_name(backend.biome(p[0], 319, p[1])) if p else None
                        cache[rx, rz] = p, viable, name
                    p, viable, name = cache[rx, rz]
                    if not p or not viable:
                        continue
                    if eligibility == "exclude_snow" and name in {"snowy_plains", "snowy_taiga"}:
                        continue
                    if eligibility == "legacy" and name not in {"plains", "desert", "savanna", "taiga"}:
                        continue
                    if cx - 8 <= p[0] // 16 <= cx + 7 and cz - 8 <= p[1] // 16 <= cz + 7:
                        candidates.append(p)
            if candidates:
                p = min(candidates)
                accepted.append([p[0] - 4, p[1] - 4])
                trace.append({"step": step, "angle": angle, "distance": distance,
                              "center_chunks": [cx, cz], "village": list(p)})
                if len(accepted) == 3:
                    return {"seed": str(seed), "x_rounding": rounding_x, "z_rounding": rounding_z,
                            "eligibility": eligibility, "positions": accepted, "trace": trace}
                angle += f32(0.6) * math.pi
                distance += 8
            else:
                angle += f32(0.25) * math.pi
                distance += 4
    raise RuntimeError("Diagnostic iteration bound reached")


if __name__ == "__main__":
    results = [replay(seed, x, z, eligibility) for seed, x, z, eligibility in itertools.product(
        [-1, 0, 12345, 4294979641], ["floor", "truncate"], ["floor", "truncate"],
        ["native", "exclude_snow", "legacy"])]
    destination = Path(__file__).with_name("axis-and-eligibility-variants.json")
    destination.write_text(json.dumps(results, indent=2) + "\n")
    for row in results:
        print(row["seed"], row["x_rounding"], row["z_rounding"], row["eligibility"], row["positions"])
````

## File: runs/filter-optimization/pilot-measurements.json

SHA-256: b01b85897b0b89bc4d3423ec5d135be423ccbaedc11dd585c0031b0b5c65d859

````json
{
  "seed_count": 20,
  "scored_centers": 96,
  "wall_seconds": 345.57881125295535,
  "analysis_wall_seconds": 310.8860593830468,
  "report_wall_seconds": 34.692751869908534,
  "effective_seconds_per_seed": 17.27894056264777,
  "worker_seed_seconds_mean": 80.79307690319838,
  "worker_seed_seconds_percentiles": [
    40.8774210360134,
    55.667270505742636,
    80.55413801502436,
    99.5087773516658,
    129.1522143089678
  ],
  "stage_seconds_summed": {
    "discovery": 8.244041956262663,
    "structures": 13.970866007148288,
    "proxy": 5.879216859582812,
    "preliminary": 379.4873175441753,
    "coast": 767.4006773250876,
    "landscape": 435.03013844799716,
    "scoring": 4.254648079397157
  },
  "stage_percentages": {
    "discovery": 0.5106988147064763,
    "structures": 0.8654619600587471,
    "proxy": 0.3642035178278526,
    "preliminary": 23.50833781464755,
    "coast": 47.538648929018464,
    "landscape": 26.949083622532196,
    "scoring": 0.2635653412087129
  },
  "scored_by_type": {
    "enclosed_island": 49,
    "ocean_island": 47,
    "mountain_basin": 0
  },
  "nominated_by_type": {
    "enclosed_island": 1096,
    "ocean_island": 656,
    "mountain_basin": 1762
  },
  "rejection_reasons": {
    "deferred_component_no_joint_required_prediction": 2063,
    "preliminary_density_connected_or_no_closed_land": 39,
    "deferred_preliminary_budget": 820,
    "deferred_refinement_budget": 421,
    "basin_necessary_bound_failed": 38,
    "density_or_biomes_not_majority_ocean": 2,
    "deferred_exact_center_no_joint_required_prediction": 19,
    "ocean_density_not_closed_within_finite_patch": 7,
    "density_connected_or_no_closed_component": 2,
    "density_not_dry_flat_mountain_basin": 1
  },
  "peak_parent_rss_mb": 554.9375,
  "peak_worker_rss_mb": 434.265625,
  "decoded_result_mb": 16.316611289978027,
  "actual_worker_counts": [
    5,
    8
  ],
  "future_2000_naive_hours": 9.599411423693205,
  "limits": "Two invocations include startup and partial plus final exports. First invocation has only five available jobs; second has fifteen jobs and eight workers. Twenty chosen seeds are not an unbiased yield estimate. No basin passed this bounded sample."
}
````

## File: runs/filter-optimization/shortcuts-ab.json

SHA-256: e9d41e58b9b44b78e01437369f177833534c44d954e9243a0e611efbecca6416

````json
{
  "basins": [
    {
      "seed": "4294979641",
      "center": [
        -896,
        2240
      ],
      "reference": {
        "seconds": 7.580651129945181,
        "passed": false,
        "points": 47090,
        "computed_points": 47090
      },
      "bound": {
        "seconds": 0.2782701210817322,
        "impossible": true,
        "points": 2555,
        "tested_centers": [
          [
            -896,
            2240
          ],
          [
            -832,
            2320
          ],
          [
            -832,
            2016
          ],
          [
            -816,
            2432
          ],
          [
            -1008,
            2336
          ],
          [
            -992,
            2272
          ],
          [
            -816,
            2144
          ],
          [
            -720,
            2320
          ],
          [
            -1136,
            2288
          ]
        ],
        "reason": "dry_or_gentle_upper_bound",
        "coverage_points": 0,
        "computed_points": 2555
      }
    },
    {
      "seed": "12345",
      "center": [
        -1984,
        -4224
      ],
      "bound": {
        "seconds": 0.3851751199690625,
        "impossible": true,
        "points": 2876,
        "tested_centers": [
          [
            -1984,
            -4224
          ],
          [
            -1920,
            -4000
          ],
          [
            -2096,
            -4032
          ],
          [
            -2192,
            -4096
          ],
          [
            -1904,
            -4176
          ],
          [
            -1984,
            -4304
          ],
          [
            -1984,
            -4448
          ],
          [
            -1936,
            -4336
          ]
        ],
        "reason": "dry_or_gentle_upper_bound",
        "coverage_points": 0,
        "computed_points": 2876
      },
      "reference": {
        "seconds": 8.070281168911606,
        "passed": false,
        "points": 49195,
        "computed_points": 49195
      }
    },
    {
      "seed": "12345",
      "center": [
        -2112,
        -4160
      ],
      "reference": {
        "seconds": 8.095373512012884,
        "passed": false,
        "points": 49098,
        "computed_points": 49098
      },
      "bound": {
        "seconds": 0.38252588792238384,
        "impossible": true,
        "points": 2865,
        "tested_centers": [
          [
            -2112,
            -4160
          ],
          [
            -2192,
            -4048
          ],
          [
            -2096,
            -4016
          ],
          [
            -1936,
            -4000
          ],
          [
            -1904,
            -4176
          ],
          [
            -2240,
            -4096
          ],
          [
            -2160,
            -3968
          ],
          [
            -1984,
            -4304
          ],
          [
            -2320,
            -4304
          ]
        ],
        "reason": "dry_or_gentle_upper_bound",
        "coverage_points": 0,
        "computed_points": 2865
      }
    },
    {
      "seed": "12853964",
      "center": [
        1792,
        -960
      ],
      "bound": {
        "seconds": 0.3443149880040437,
        "impossible": true,
        "points": 2720,
        "tested_centers": [
          [
            1792,
            -960
          ],
          [
            1808,
            -832
          ],
          [
            1600,
            -928
          ],
          [
            1776,
            -1088
          ],
          [
            1888,
            -816
          ],
          [
            1728,
            -720
          ],
          [
            1584,
            -816
          ]
        ],
        "reason": "dry_or_gentle_upper_bound",
        "coverage_points": 0,
        "computed_points": 2720
      },
      "reference": {
        "seconds": 6.974430124973878,
        "passed": false,
        "points": 43885,
        "computed_points": 43885
      }
    }
  ],
  "native_structure_scan_seconds": {
    "duplicate": [
      0.1039629599545151,
      0.09768668003380299,
      0.11236776399891824,
      0.11143365094903857
    ],
    "combined": [
      0.0590132171055302,
      0.05519062001258135,
      0.06881985592190176,
      0.06852073897607625
    ]
  },
  "reference_basin_seconds": 30.72073593584355,
  "bound_basin_seconds": 1.3902861169772223,
  "computed_columns_reference": 189268,
  "computed_columns_bound": 11016,
  "all_bound_rejections_reference_failed": true,
  "limits": "Four saved negative nominations, isolated alternating-order cold per-seed cache A/B. Native structure parity covers all supported types and four full seeds. Not a universal yield/timing guarantee."
}
````

## File: runs/filter-optimization/optimization-parity.json

SHA-256: de433e491a39184df508711cfae2447a3abe8013b95646f379dae3bdae50d8e5

````json
{
  "common_centers": 95,
  "unchanged_common_centers": 95,
  "changes": [],
  "old_centers": 114,
  "new_centers": 96,
  "removed_centers": 19,
  "newly_reached_centers": 1,
  "new_all_predicted_required": true,
  "structure_deferred_nominations": 2082,
  "early_basin_rejections": 38,
  "early_basin_attempts": 40,
  "early_basin_points": 139420,
  "scope": "Retained common centers must have identical full candidate records; coverage changes are authorized fast deferrals/refinement reallocation, not an unchanged-workload speed claim."
}
````

## File: runs/filter-optimization/worker-ab.json

SHA-256: 67a6c9666323c61a43eda4d5089492e189e9f97b6581bb4e3abb3eef7d8f62fc

````json
{
  "same_20_seeds_config_and_exact_results": true,
  "recommended_workers": 12,
  "measurements": {
    "8": {
      "analysis_wall_seconds": 233.65322178404313,
      "report_wall_seconds": 1.0552790759829804,
      "wall_seconds": 234.7085008600261,
      "actual_worker_pids": [
        17524,
        17525,
        17526,
        17527,
        17528,
        17529,
        17530,
        17531
      ],
      "parent_peak_rss_mb": 180.921875,
      "worker_peak_rss_mb": 452.29296875,
      "prediction_sha256": "4b81790b3828e49ed61c6dac67c80a8630d0ff9833263821564291d6e65ae58a"
    },
    "12": {
      "analysis_wall_seconds": 212.59465288300999,
      "report_wall_seconds": 1.1864062419626862,
      "wall_seconds": 213.78105912497267,
      "actual_worker_pids": [
        17314,
        17315,
        17316,
        17317,
        17318,
        17319,
        17320,
        17321,
        17322,
        17323,
        17324,
        17325
      ],
      "parent_peak_rss_mb": 179.609375,
      "worker_peak_rss_mb": 452.6484375,
      "prediction_sha256": "4b81790b3828e49ed61c6dac67c80a8630d0ff9833263821564291d6e65ae58a"
    }
  },
  "analysis_saving_of_12_vs_8_percent": 9.012744930389527,
  "scope": "Uninterrupted full20-input cohorts, run sequentially, maps reused for both. One trial per worker count, not proof of globally optimal scheduling; source/seed/geometry/metrics/counters identical."
}
````

## File: runs/filter-optimization/resume-proof.json

SHA-256: 045ef641c7bc38c437791cc3ebcbac59d44430d901f8cb7d92799e87ced83313

````json
{
  "equal": true,
  "seeds_compared": 20,
  "candidate_count": 96,
  "prediction_sha256": "5dbcb5886e8ef9fca752b351033c2b66e9f2720dbc3c869aa99128ccde8a9aab",
  "uninterrupted_prediction_sha256": "5dbcb5886e8ef9fca752b351033c2b66e9f2720dbc3c869aa99128ccde8a9aab",
  "current_backend_identity": {
    "model": {
      "model": "26.50",
      "structure_rng": {
        "trial_chamber": 1,
        "stronghold": 0,
        "mineshaft": 0,
        "ancient_city": 0,
        "village": 0,
        "ruined_portal": 0,
        "shipwreck": 0,
        "monument": 0,
        "outpost": 0,
        "fortress": 0,
        "bastion": 0
      }
    },
    "sha256": {
      "native/bridge.c": "7096e03918506eec9c536794566a592681789961e6f75ce51b7141bea5fc8ff5",
      "native/bridge.h": "ecc06ed0e803ca87caf3701e4f849532e654dd9af8906e1e13843e806881eb1f",
      "vendor/backend.json": "d95c3155f8a98dc40b49a2d083fbfdb2ce35bc496b19554f267d445d6eb3d838",
      "src/seed_search/__init__.py": "eaa142a1ddca6c98f92e2ec3ea37c7b8312196b345bdc85e5526799799047606",
      "src/seed_search/backend.py": "743211d5dc807e425154bd787421cd802c988cc47c9bde94e2b1adc9ce580792",
      "src/seed_search/cache.py": "c8be09927ef8fa77563bb8bae253232aa5692c7960f5c5faec3c705ced266513",
      "src/seed_search/landscapes.py": "f9a92568fdbdf099f92e2b73b4e668050a13ac7823cbbc9086c7e0649fe87c62",
      "src/seed_search/config.py": "fa327ef97e6de4c028122f14fe8fc1f78bcb0fe5c74c980ec874689d65eb20db",
      "src/seed_search/geometry.py": "ab4c5cae47e588703a5ad2d756d1a5a2131bada11a7cdabef790a35688603794",
      "src/seed_search/seeds.py": "7730bc5b7a6fb932212693c68940b9ccb76a9638d6753bc02130561e4caa9bf5",
      "src/seed_search/wood.py": "f0dcea3ada050362d7fb7b719d15904d2aafb64c3753004e9ad04fe25f3e1f49",
      "src/seed_search/terrain.py": "165571d71482913c4f361dd0e209ef259385dea09952175772f9e6b91b0ac261",
      "src/seed_search/structures.py": "15921e9a296787dc6926885bd3d246e0fd6abbbc3643b41655402d38672d4c2b",
      "src/seed_search/scoring.py": "e18beff6e5e51c16c651a2f5a085f405d7bc1a7ac0f586351eb11e399797bafa",
      "src/seed_search/storage.py": "c2253524fdb651922d09431429ef0999ce6ec772a0c5b3999f3bb5ae4ca6ff80",
      "src/seed_search/search.py": "3a6f771c4d95c1bb032c2cd1e739326247d378d5168612d45511c33f4f1c7bfa",
      "src/seed_search/review.py": "ac0795b98d48e7e1de4530c9f3553e7be7d0603851794e43fea84131a99ac078",
      "src/seed_search/_native.abi3.so": "fc6400e327aeedcb3c8c4c7b276c9e1088520bd825abc542736be576393db0bc"
    }
  },
  "config_sha256": "89414ed421ecc1fd363b1f5ba3c2b0ec1c3e5653918629732050f3cf9f8ef71c",
  "worker_variation_test_passed": true,
  "worker_variation_evidence": "test_expanded_real_checkpoint_resume_matches_worker_variation in tests.log: real scored pipeline with one versus two workers; full-envelope interrupted/resumed pilot versus independently repeated 20 seeds with requested worker counts [8] versus [12].",
  "pilot_workers_requested": [
    8
  ],
  "repeat_workers_requested": [
    12
  ],
  "limits": "Only measured timings/RSS/PIDs excluded; predictions, metrics, cache counts, rejections and stage counts compared exactly."
}
````

## File: runs/filter-optimization/fresh-marker-comparison.json

SHA-256: 96a233a118d4687cd10ba3f0bab0c03384332c6929835668d6ae65eef7250501

````json
{
  "fresh_actual_ui_markers": 4,
  "unique": 4,
  "actual_minecraft": null,
  "rows": [
    {
      "seed": "12853964",
      "center": [
        0,
        960
      ],
      "type": "stronghold",
      "marker": [
        -1292,
        1396
      ],
      "bounds": [
        -1504,
        -544,
        1504,
        2464
      ],
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1292,
          1396
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12853964",
      "center": [
        0,
        960
      ],
      "type": "fortress",
      "marker": [
        155,
        11
      ],
      "bounds": [
        -496,
        -376,
        496,
        616
      ],
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          152,
          8
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "center": [
        -2304,
        -4480
      ],
      "type": "stronghold",
      "marker": [
        -1116,
        -5324
      ],
      "bounds": [
        -3808,
        -5984,
        -800,
        -2976
      ],
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1116,
          -5324
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "center": [
        -2304,
        -4480
      ],
      "type": "fortress",
      "marker": [
        -469,
        -853
      ],
      "bounds": [
        -784,
        -1056,
        208,
        -64
      ],
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -472,
          -856
        ]
      ],
      "status": "unique"
    }
  ]
}
````

## File: runs/filter-optimization/regression/regression.json

SHA-256: cb22dd8c6c6261b8afd55b71257869808997245dae89cb52f741c8f80aeb6287

````json
{
  "source_kind": "frozen_actual_website_UI_predictions_not_in_game",
  "target": "Bedrock 26.50 - 26.52",
  "fixture_sha256": "fb0c3f2650f2966d4fec71a63885bc31c7d8170046d7472d825e84b3c5e4d62d",
  "baseline_sha256": "fade34fd110aee23852bad16c698f741a116086f018382df5040c5263c57c868",
  "passed": true,
  "unexplained_regressions": [],
  "summary": {
    "structure_rows": 880,
    "point_rows": 159,
    "unique_type_correspondences": 874,
    "known_structure_disagreements": 6,
    "reused_starts": 0,
    "biome_matches": 153,
    "height_mae": 1.0,
    "height_max_error": 5
  },
  "known_disagreements": [
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        1185,
        376
      ],
      "raw_nearest": [
        1208,
        408
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        6212,
        -4700
      ],
      "raw_nearest": null,
      "viable_nearest": null,
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        3524,
        -7276
      ],
      "raw_nearest": null,
      "viable_nearest": null,
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -3048,
        3256
      ],
      "raw_nearest": [
        -3048,
        3256
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -680,
        6216
      ],
      "raw_nearest": [
        -680,
        6216
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        1185,
        376
      ],
      "raw_nearest": [
        1208,
        408
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [],
      "status": "missing"
    }
  ],
  "structures": [
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        9,
        233
      ],
      "raw_nearest": [
        8,
        232
      ],
      "viable_nearest": [
        8,
        232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          8,
          232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -233,
        55
      ],
      "raw_nearest": [
        -216,
        72
      ],
      "viable_nearest": [
        -216,
        72
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -216,
          72
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        745,
        55
      ],
      "raw_nearest": [
        744,
        72
      ],
      "viable_nearest": [
        744,
        72
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          744,
          72
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        759,
        681
      ],
      "raw_nearest": [
        776,
        680
      ],
      "viable_nearest": [
        776,
        680
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          776,
          680
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -313,
        585
      ],
      "raw_nearest": [
        -296,
        584
      ],
      "viable_nearest": [
        -296,
        584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -296,
          584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -471,
        -313
      ],
      "raw_nearest": [
        -472,
        -296
      ],
      "viable_nearest": [
        -472,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -472,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        137,
        -519
      ],
      "raw_nearest": [
        136,
        -520
      ],
      "viable_nearest": [
        136,
        -520
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          136,
          -520
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        295,
        871
      ],
      "raw_nearest": [
        312,
        888
      ],
      "viable_nearest": [
        312,
        888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          312,
          888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        215,
        1415
      ],
      "raw_nearest": [
        232,
        1432
      ],
      "viable_nearest": [
        232,
        1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          232,
          1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -313,
        1255
      ],
      "raw_nearest": [
        -296,
        1272
      ],
      "viable_nearest": [
        -296,
        1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -296,
          1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -1081,
        7
      ],
      "raw_nearest": [
        -1064,
        24
      ],
      "viable_nearest": [
        -1064,
        24
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -1064,
          24
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -1017,
        -487
      ],
      "raw_nearest": [
        -1000,
        -488
      ],
      "viable_nearest": [
        -1000,
        -488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -1000,
          -488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -807,
        -761
      ],
      "raw_nearest": [
        -808,
        -744
      ],
      "viable_nearest": [
        -808,
        -744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -808,
          -744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        -439,
        -999
      ],
      "raw_nearest": [
        -440,
        -1000
      ],
      "viable_nearest": [
        -440,
        -1000
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -440,
          -1000
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        327,
        -969
      ],
      "raw_nearest": [
        344,
        -952
      ],
      "viable_nearest": [
        344,
        -952
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          344,
          -952
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        1079,
        -311
      ],
      "raw_nearest": [
        1096,
        -312
      ],
      "viable_nearest": [
        1096,
        -312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1096,
          -312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        1703,
        103
      ],
      "raw_nearest": [
        1720,
        120
      ],
      "viable_nearest": [
        1720,
        120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1720,
          120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        1335,
        263
      ],
      "raw_nearest": [
        1352,
        280
      ],
      "viable_nearest": [
        1352,
        280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1352,
          280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        567,
        1353
      ],
      "raw_nearest": [
        584,
        1352
      ],
      "viable_nearest": [
        584,
        1352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          584,
          1352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "trial_chamber",
      "marker": [
        103,
        1751
      ],
      "raw_nearest": [
        120,
        1768
      ],
      "viable_nearest": [
        120,
        1768
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          120,
          1768
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        1460,
        -828
      ],
      "raw_nearest": [
        1460,
        -828
      ],
      "viable_nearest": [
        1460,
        -828
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1460,
          -828
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        276,
        2836
      ],
      "raw_nearest": [
        276,
        2836
      ],
      "viable_nearest": [
        276,
        2836
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          276,
          2836
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        2420,
        3492
      ],
      "raw_nearest": [
        2420,
        3492
      ],
      "viable_nearest": [
        2420,
        3492
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2420,
          3492
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -1212,
        4372
      ],
      "raw_nearest": [
        -1212,
        4372
      ],
      "viable_nearest": [
        -1212,
        4372
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1212,
          4372
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -1116,
        -5324
      ],
      "raw_nearest": [
        -1116,
        -5324
      ],
      "viable_nearest": [
        -1116,
        -5324
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1116,
          -5324
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        5092,
        -4092
      ],
      "raw_nearest": [
        5092,
        -4092
      ],
      "viable_nearest": [
        5092,
        -4092
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5092,
          -4092
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        7588,
        1572
      ],
      "raw_nearest": [
        7588,
        1572
      ],
      "viable_nearest": [
        7588,
        1572
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          7588,
          1572
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        1940,
        7604
      ],
      "raw_nearest": [
        1940,
        7604
      ],
      "viable_nearest": [
        1940,
        7604
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1940,
          7604
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -5132,
        5524
      ],
      "raw_nearest": [
        -5132,
        5524
      ],
      "viable_nearest": [
        -5132,
        5524
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5132,
          5524
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -7564,
        -1500
      ],
      "raw_nearest": [
        -7564,
        -1500
      ],
      "viable_nearest": [
        -7564,
        -1500
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7564,
          -1500
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -7836,
        1188
      ],
      "raw_nearest": [
        -7836,
        1188
      ],
      "viable_nearest": [
        -7836,
        1188
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7836,
          1188
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -828,
        -7772
      ],
      "raw_nearest": [
        -828,
        -7772
      ],
      "viable_nearest": [
        -828,
        -7772
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -828,
          -7772
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        7572,
        4404
      ],
      "raw_nearest": [
        7572,
        4404
      ],
      "viable_nearest": [
        7572,
        4404
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          7572,
          4404
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        2260,
        -10940
      ],
      "raw_nearest": [
        2260,
        -10940
      ],
      "viable_nearest": [
        2260,
        -10940
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2260,
          -10940
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -11196,
        -4332
      ],
      "raw_nearest": [
        -11196,
        -4332
      ],
      "viable_nearest": [
        -11196,
        -4332
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -11196,
          -4332
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -11612,
        4804
      ],
      "raw_nearest": [
        -11612,
        4804
      ],
      "viable_nearest": [
        -11612,
        4804
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -11612,
          4804
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        11972,
        -4588
      ],
      "raw_nearest": [
        11972,
        -4588
      ],
      "viable_nearest": [
        11972,
        -4588
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          11972,
          -4588
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        4900,
        -11884
      ],
      "raw_nearest": [
        4900,
        -11884
      ],
      "viable_nearest": [
        4900,
        -11884
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4900,
          -11884
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -7404,
        -10540
      ],
      "raw_nearest": [
        -7404,
        -10540
      ],
      "viable_nearest": [
        -7404,
        -10540
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7404,
          -10540
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "stronghold",
      "marker": [
        -11388,
        8372
      ],
      "raw_nearest": [
        -11388,
        8372
      ],
      "viable_nearest": [
        -11388,
        8372
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -11388,
          8372
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        408,
        216
      ],
      "raw_nearest": [
        408,
        216
      ],
      "viable_nearest": [
        408,
        216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        -216,
        184
      ],
      "raw_nearest": [
        -216,
        184
      ],
      "viable_nearest": [
        -216,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -216,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        232,
        -168
      ],
      "raw_nearest": [
        232,
        -168
      ],
      "viable_nearest": [
        232,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        632,
        200
      ],
      "raw_nearest": [
        632,
        200
      ],
      "viable_nearest": [
        632,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          632,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        424,
        296
      ],
      "raw_nearest": [
        424,
        296
      ],
      "viable_nearest": [
        424,
        296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          424,
          296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        504,
        392
      ],
      "raw_nearest": [
        504,
        392
      ],
      "viable_nearest": [
        504,
        392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          504,
          392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        8,
        536
      ],
      "raw_nearest": [
        8,
        536
      ],
      "viable_nearest": [
        8,
        536
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8,
          536
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        408,
        -136
      ],
      "raw_nearest": [
        408,
        -136
      ],
      "viable_nearest": [
        408,
        -136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          -136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        824,
        40
      ],
      "raw_nearest": [
        824,
        40
      ],
      "viable_nearest": [
        824,
        40
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          824,
          40
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        584,
        584
      ],
      "raw_nearest": [
        584,
        584
      ],
      "viable_nearest": [
        584,
        584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          584,
          584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        744,
        632
      ],
      "raw_nearest": [
        744,
        632
      ],
      "viable_nearest": [
        744,
        632
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          744,
          632
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        472,
        648
      ],
      "raw_nearest": [
        472,
        648
      ],
      "viable_nearest": [
        472,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          472,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        -8,
        648
      ],
      "raw_nearest": [
        -8,
        648
      ],
      "viable_nearest": [
        -8,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -8,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        -40,
        664
      ],
      "raw_nearest": [
        -40,
        664
      ],
      "viable_nearest": [
        -40,
        664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -40,
          664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        -488,
        712
      ],
      "raw_nearest": [
        -488,
        712
      ],
      "viable_nearest": [
        -488,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -488,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        -232,
        -296
      ],
      "raw_nearest": [
        -232,
        -296
      ],
      "viable_nearest": [
        -232,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -232,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        24,
        -584
      ],
      "raw_nearest": [
        24,
        -584
      ],
      "viable_nearest": [
        24,
        -584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          24,
          -584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        808,
        440
      ],
      "raw_nearest": [
        808,
        440
      ],
      "viable_nearest": [
        808,
        440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          808,
          440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        984,
        520
      ],
      "raw_nearest": [
        984,
        520
      ],
      "viable_nearest": [
        984,
        520
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          984,
          520
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "mineshaft",
      "marker": [
        984,
        552
      ],
      "raw_nearest": [
        984,
        552
      ],
      "viable_nearest": [
        984,
        552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          984,
          552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        504,
        616
      ],
      "raw_nearest": [
        504,
        616
      ],
      "viable_nearest": [
        504,
        616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          504,
          616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -648,
        136
      ],
      "raw_nearest": [
        -648,
        136
      ],
      "viable_nearest": [
        -648,
        136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -648,
          136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -312,
        -216
      ],
      "raw_nearest": [
        -312,
        -216
      ],
      "viable_nearest": [
        -312,
        -216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -312,
          -216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -584,
        -200
      ],
      "raw_nearest": [
        -584,
        -200
      ],
      "viable_nearest": [
        -584,
        -200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -584,
          -200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        920,
        -200
      ],
      "raw_nearest": [
        920,
        -200
      ],
      "viable_nearest": [
        920,
        -200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          920,
          -200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -1000,
        888
      ],
      "raw_nearest": [
        -1000,
        888
      ],
      "viable_nearest": [
        -1000,
        888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1000,
          888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        152,
        -1432
      ],
      "raw_nearest": [
        152,
        -1432
      ],
      "viable_nearest": [
        152,
        -1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          152,
          -1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        3256,
        856
      ],
      "raw_nearest": [
        3256,
        856
      ],
      "viable_nearest": [
        3256,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3256,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        3208,
        1272
      ],
      "raw_nearest": [
        3208,
        1272
      ],
      "viable_nearest": [
        3208,
        1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3208,
          1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        2824,
        1560
      ],
      "raw_nearest": [
        2824,
        1560
      ],
      "viable_nearest": [
        2824,
        1560
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2824,
          1560
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        3928,
        1320
      ],
      "raw_nearest": [
        3928,
        1320
      ],
      "viable_nearest": [
        3928,
        1320
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3928,
          1320
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -984,
        3992
      ],
      "raw_nearest": [
        -984,
        3992
      ],
      "viable_nearest": [
        -984,
        3992
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -984,
          3992
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -1048,
        4408
      ],
      "raw_nearest": [
        -1048,
        4408
      ],
      "viable_nearest": [
        -1048,
        4408
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1048,
          4408
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -2904,
        -3320
      ],
      "raw_nearest": [
        -2904,
        -3320
      ],
      "viable_nearest": [
        -2904,
        -3320
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2904,
          -3320
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -1752,
        -4056
      ],
      "raw_nearest": [
        -1752,
        -4056
      ],
      "viable_nearest": [
        -1752,
        -4056
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1752,
          -4056
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -2936,
        -3736
      ],
      "raw_nearest": [
        -2936,
        -3736
      ],
      "viable_nearest": [
        -2936,
        -3736
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2936,
          -3736
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        5128,
        1640
      ],
      "raw_nearest": [
        5128,
        1640
      ],
      "viable_nearest": [
        5128,
        1640
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5128,
          1640
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -4136,
        -4504
      ],
      "raw_nearest": [
        -4136,
        -4504
      ],
      "viable_nearest": [
        -4136,
        -4504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4136,
          -4504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -2120,
        -5704
      ],
      "raw_nearest": [
        -2120,
        -5704
      ],
      "viable_nearest": [
        -2120,
        -5704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2120,
          -5704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ancient_city",
      "marker": [
        -2600,
        5928
      ],
      "raw_nearest": [
        -2600,
        5928
      ],
      "viable_nearest": [
        -2600,
        5928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2600,
          5928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -488,
        248
      ],
      "raw_nearest": [
        -488,
        248
      ],
      "viable_nearest": [
        -488,
        248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -488,
          248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -936,
        216
      ],
      "raw_nearest": [
        -936,
        216
      ],
      "viable_nearest": [
        -936,
        216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -936,
          216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        104,
        1448
      ],
      "raw_nearest": [
        104,
        1448
      ],
      "viable_nearest": [
        104,
        1448
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          104,
          1448
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -248,
        -904
      ],
      "raw_nearest": [
        -248,
        -904
      ],
      "viable_nearest": [
        -248,
        -904
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -248,
          -904
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        872,
        -776
      ],
      "raw_nearest": [
        872,
        -776
      ],
      "viable_nearest": [
        872,
        -776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          872,
          -776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        1288,
        264
      ],
      "raw_nearest": [
        1288,
        264
      ],
      "viable_nearest": [
        1288,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1288,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -808,
        -1000
      ],
      "raw_nearest": [
        -808,
        -1000
      ],
      "viable_nearest": [
        -808,
        -1000
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -808,
          -1000
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        1368,
        -184
      ],
      "raw_nearest": [
        1368,
        -184
      ],
      "viable_nearest": [
        1368,
        -184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1368,
          -184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        1464,
        -824
      ],
      "raw_nearest": [
        1464,
        -824
      ],
      "viable_nearest": [
        1464,
        -824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1464,
          -824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        1896,
        856
      ],
      "raw_nearest": [
        1896,
        856
      ],
      "viable_nearest": [
        1896,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1896,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -344,
        1928
      ],
      "raw_nearest": [
        -344,
        1928
      ],
      "viable_nearest": [
        -344,
        1928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -344,
          1928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        2376,
        184
      ],
      "raw_nearest": [
        2376,
        184
      ],
      "viable_nearest": [
        2376,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2376,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        1800,
        1128
      ],
      "raw_nearest": [
        1800,
        1128
      ],
      "viable_nearest": [
        1800,
        1128
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1800,
          1128
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        760,
        2216
      ],
      "raw_nearest": [
        760,
        2216
      ],
      "viable_nearest": [
        760,
        2216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          760,
          2216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -904,
        2280
      ],
      "raw_nearest": [
        -904,
        2280
      ],
      "viable_nearest": [
        -904,
        2280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -904,
          2280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -1448,
        -1480
      ],
      "raw_nearest": [
        -1448,
        -1480
      ],
      "viable_nearest": [
        -1448,
        -1480
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1448,
          -1480
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        -200,
        -1944
      ],
      "raw_nearest": [
        -200,
        -1944
      ],
      "viable_nearest": [
        -200,
        -1944
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -200,
          -1944
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        2344,
        904
      ],
      "raw_nearest": [
        2344,
        904
      ],
      "viable_nearest": [
        2344,
        904
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2344,
          904
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        2536,
        1192
      ],
      "raw_nearest": [
        2536,
        1192
      ],
      "viable_nearest": [
        2536,
        1192
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2536,
          1192
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "village",
      "marker": [
        2888,
        200
      ],
      "raw_nearest": [
        2888,
        200
      ],
      "viable_nearest": [
        2888,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2888,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        108,
        100
      ],
      "raw_nearest": [
        120,
        104
      ],
      "viable_nearest": [
        120,
        104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          120,
          104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -488,
        11
      ],
      "raw_nearest": [
        -488,
        24
      ],
      "viable_nearest": [
        -488,
        24
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -488,
          24
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        964,
        84
      ],
      "raw_nearest": [
        968,
        88
      ],
      "viable_nearest": [
        968,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          968,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -7,
        965
      ],
      "raw_nearest": [
        8,
        968
      ],
      "viable_nearest": [
        8,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          8,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        979,
        1011
      ],
      "raw_nearest": [
        984,
        1016
      ],
      "viable_nearest": [
        984,
        1016
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          984,
          1016
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        235,
        1340
      ],
      "raw_nearest": [
        248,
        1352
      ],
      "viable_nearest": [
        248,
        1352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          248,
          1352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        313,
        -901
      ],
      "raw_nearest": [
        328,
        -888
      ],
      "viable_nearest": [
        328,
        -888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          328,
          -888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        1428,
        956
      ],
      "raw_nearest": [
        1432,
        968
      ],
      "viable_nearest": [
        1432,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1432,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -1114,
        -299
      ],
      "raw_nearest": [
        -1112,
        -296
      ],
      "viable_nearest": [
        -1112,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1112,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -572,
        -1076
      ],
      "raw_nearest": [
        -568,
        -1064
      ],
      "viable_nearest": [
        -568,
        -1064
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -568,
          -1064
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -587,
        1667
      ],
      "raw_nearest": [
        -584,
        1672
      ],
      "viable_nearest": [
        -584,
        1672
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -584,
          1672
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        1412,
        -996
      ],
      "raw_nearest": [
        1416,
        -984
      ],
      "viable_nearest": [
        1416,
        -984
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1416,
          -984
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        908,
        1924
      ],
      "raw_nearest": [
        920,
        1928
      ],
      "viable_nearest": [
        920,
        1928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          920,
          1928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -1732,
        371
      ],
      "raw_nearest": [
        -1720,
        376
      ],
      "viable_nearest": [
        -1720,
        376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1720,
          376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -1256,
        -1147
      ],
      "raw_nearest": [
        -1256,
        -1144
      ],
      "viable_nearest": [
        -1256,
        -1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1256,
          -1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -444,
        2084
      ],
      "raw_nearest": [
        -440,
        2088
      ],
      "viable_nearest": [
        -440,
        2088
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -440,
          2088
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        2019,
        -1230
      ],
      "raw_nearest": [
        2024,
        -1224
      ],
      "viable_nearest": [
        2024,
        -1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          2024,
          -1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        1318,
        2133
      ],
      "raw_nearest": [
        1320,
        2136
      ],
      "viable_nearest": [
        1320,
        2136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1320,
          2136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        156,
        2714
      ],
      "raw_nearest": [
        168,
        2728
      ],
      "viable_nearest": [
        168,
        2728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          168,
          2728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "ruined_portal",
      "marker": [
        -2267,
        876
      ],
      "raw_nearest": [
        -2264,
        888
      ],
      "viable_nearest": [
        -2264,
        888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -2264,
          888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        -216,
        -88
      ],
      "raw_nearest": [
        -216,
        -88
      ],
      "viable_nearest": [
        -216,
        -88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -216,
          -88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        -72,
        520
      ],
      "raw_nearest": [
        -72,
        520
      ],
      "viable_nearest": [
        -72,
        520
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -72,
          520
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        840,
        1256
      ],
      "raw_nearest": [
        840,
        1256
      ],
      "viable_nearest": [
        840,
        1256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          840,
          1256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        568,
        1080
      ],
      "raw_nearest": [
        568,
        1080
      ],
      "viable_nearest": [
        568,
        1080
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          568,
          1080
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        904,
        1576
      ],
      "raw_nearest": [
        904,
        1576
      ],
      "viable_nearest": [
        904,
        1576
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          904,
          1576
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        248,
        2008
      ],
      "raw_nearest": [
        248,
        2008
      ],
      "viable_nearest": [
        248,
        2008
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          248,
          2008
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        408,
        2024
      ],
      "raw_nearest": [
        408,
        2024
      ],
      "viable_nearest": [
        408,
        2024
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          2024
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        664,
        -1752
      ],
      "raw_nearest": [
        664,
        -1752
      ],
      "viable_nearest": [
        664,
        -1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          664,
          -1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        1448,
        1976
      ],
      "raw_nearest": [
        1448,
        1976
      ],
      "viable_nearest": [
        1448,
        1976
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1448,
          1976
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        952,
        -1864
      ],
      "raw_nearest": [
        952,
        -1864
      ],
      "viable_nearest": [
        952,
        -1864
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          952,
          -1864
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        2104,
        -712
      ],
      "raw_nearest": [
        2104,
        -712
      ],
      "viable_nearest": [
        2104,
        -712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2104,
          -712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        -1640,
        1928
      ],
      "raw_nearest": [
        -1640,
        1928
      ],
      "viable_nearest": [
        -1640,
        1928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1640,
          1928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        -1912,
        1592
      ],
      "raw_nearest": [
        -1912,
        1592
      ],
      "viable_nearest": [
        -1912,
        1592
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1912,
          1592
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        -680,
        -2056
      ],
      "raw_nearest": [
        -680,
        -2056
      ],
      "viable_nearest": [
        -680,
        -2056
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -680,
          -2056
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        -168,
        -2280
      ],
      "raw_nearest": [
        -168,
        -2280
      ],
      "viable_nearest": [
        -168,
        -2280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -168,
          -2280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        280,
        -2184
      ],
      "raw_nearest": [
        280,
        -2184
      ],
      "viable_nearest": [
        280,
        -2184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          280,
          -2184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        1032,
        -2120
      ],
      "raw_nearest": [
        1032,
        -2120
      ],
      "viable_nearest": [
        1032,
        -2120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1032,
          -2120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        1464,
        -1880
      ],
      "raw_nearest": [
        1464,
        -1880
      ],
      "viable_nearest": [
        1464,
        -1880
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1464,
          -1880
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        1688,
        -1640
      ],
      "raw_nearest": [
        1688,
        -1640
      ],
      "viable_nearest": [
        1688,
        -1640
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1688,
          -1640
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "shipwreck",
      "marker": [
        2104,
        -1096
      ],
      "raw_nearest": [
        2104,
        -1096
      ],
      "viable_nearest": [
        2104,
        -1096
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2104,
          -1096
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        312,
        1784
      ],
      "raw_nearest": [
        312,
        1784
      ],
      "viable_nearest": [
        312,
        1784
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          312,
          1784
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        2152,
        -344
      ],
      "raw_nearest": [
        2152,
        -344
      ],
      "viable_nearest": [
        2152,
        -344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2152,
          -344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        232,
        -2408
      ],
      "raw_nearest": [
        232,
        -2408
      ],
      "viable_nearest": [
        232,
        -2408
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          -2408
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        1848,
        -1400
      ],
      "raw_nearest": [
        1848,
        -1400
      ],
      "viable_nearest": [
        1848,
        -1400
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1848,
          -1400
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        2184,
        -1336
      ],
      "raw_nearest": [
        2184,
        -1336
      ],
      "viable_nearest": [
        2184,
        -1336
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2184,
          -1336
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        2344,
        -680
      ],
      "raw_nearest": [
        2344,
        -680
      ],
      "viable_nearest": [
        2344,
        -680
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2344,
          -680
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        600,
        -2488
      ],
      "raw_nearest": [
        600,
        -2488
      ],
      "viable_nearest": [
        600,
        -2488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          600,
          -2488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        -1352,
        3112
      ],
      "raw_nearest": [
        -1352,
        3112
      ],
      "viable_nearest": [
        -1352,
        3112
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1352,
          3112
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        2616,
        -2248
      ],
      "raw_nearest": [
        2616,
        -2248
      ],
      "viable_nearest": [
        2616,
        -2248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2616,
          -2248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        3960,
        1752
      ],
      "raw_nearest": [
        3960,
        1752
      ],
      "viable_nearest": [
        3960,
        1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3960,
          1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        3848,
        2056
      ],
      "raw_nearest": [
        3848,
        2056
      ],
      "viable_nearest": [
        3848,
        2056
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3848,
          2056
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        -1880,
        3752
      ],
      "raw_nearest": [
        -1880,
        3752
      ],
      "viable_nearest": [
        -1880,
        3752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1880,
          3752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        -3992,
        -744
      ],
      "raw_nearest": [
        -3992,
        -744
      ],
      "viable_nearest": [
        -3992,
        -744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3992,
          -744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        2280,
        -3400
      ],
      "raw_nearest": [
        2280,
        -3400
      ],
      "viable_nearest": [
        2280,
        -3400
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2280,
          -3400
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        2744,
        -3240
      ],
      "raw_nearest": [
        2744,
        -3240
      ],
      "viable_nearest": [
        2744,
        -3240
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2744,
          -3240
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        4280,
        2136
      ],
      "raw_nearest": [
        4280,
        2136
      ],
      "viable_nearest": [
        4280,
        2136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4280,
          2136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        3400,
        3256
      ],
      "raw_nearest": [
        3400,
        3256
      ],
      "viable_nearest": [
        3400,
        3256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3400,
          3256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        3800,
        -2376
      ],
      "raw_nearest": [
        3800,
        -2376
      ],
      "viable_nearest": [
        3800,
        -2376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3800,
          -2376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        4248,
        -1432
      ],
      "raw_nearest": [
        4248,
        -1432
      ],
      "viable_nearest": [
        4248,
        -1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4248,
          -1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "monument",
      "marker": [
        -4488,
        -264
      ],
      "raw_nearest": [
        -4488,
        -264
      ],
      "viable_nearest": [
        -4488,
        -264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4488,
          -264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        552,
        136
      ],
      "raw_nearest": [
        544,
        128
      ],
      "viable_nearest": [
        544,
        128
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          544,
          128
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        1304,
        -472
      ],
      "raw_nearest": [
        1296,
        -480
      ],
      "viable_nearest": [
        1296,
        -480
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1296,
          -480
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        1784,
        632
      ],
      "raw_nearest": [
        1776,
        624
      ],
      "viable_nearest": [
        1776,
        624
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1776,
          624
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -1992,
        408
      ],
      "raw_nearest": [
        -2000,
        400
      ],
      "viable_nearest": [
        -2000,
        400
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -2000,
          400
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        1960,
        2088
      ],
      "raw_nearest": [
        1952,
        2080
      ],
      "viable_nearest": [
        1952,
        2080
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1952,
          2080
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        3000,
        424
      ],
      "raw_nearest": [
        2992,
        416
      ],
      "viable_nearest": [
        2992,
        416
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2992,
          416
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        1736,
        2744
      ],
      "raw_nearest": [
        1728,
        2736
      ],
      "viable_nearest": [
        1728,
        2736
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1728,
          2736
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        2776,
        1944
      ],
      "raw_nearest": [
        2768,
        1936
      ],
      "viable_nearest": [
        2768,
        1936
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2768,
          1936
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        3368,
        -728
      ],
      "raw_nearest": [
        3360,
        -736
      ],
      "viable_nearest": [
        3360,
        -736
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3360,
          -736
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        2936,
        2760
      ],
      "raw_nearest": [
        2928,
        2752
      ],
      "viable_nearest": [
        2928,
        2752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2928,
          2752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -3544,
        264
      ],
      "raw_nearest": [
        -3552,
        256
      ],
      "viable_nearest": [
        -3552,
        256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3552,
          256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -808,
        -3368
      ],
      "raw_nearest": [
        -816,
        -3376
      ],
      "viable_nearest": [
        -816,
        -3376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -816,
          -3376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -1160,
        -4424
      ],
      "raw_nearest": [
        -1168,
        -4432
      ],
      "viable_nearest": [
        -1168,
        -4432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -1168,
          -4432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        3112,
        3976
      ],
      "raw_nearest": [
        3104,
        3968
      ],
      "viable_nearest": [
        3104,
        3968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3104,
          3968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        1432,
        5512
      ],
      "raw_nearest": [
        1424,
        5504
      ],
      "viable_nearest": [
        1424,
        5504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1424,
          5504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -5624,
        360
      ],
      "raw_nearest": [
        -5632,
        352
      ],
      "viable_nearest": [
        -5632,
        352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -5632,
          352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -4568,
        -3832
      ],
      "raw_nearest": [
        -4576,
        -3840
      ],
      "viable_nearest": [
        -4576,
        -3840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4576,
          -3840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        5416,
        3192
      ],
      "raw_nearest": [
        5408,
        3184
      ],
      "viable_nearest": [
        5408,
        3184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5408,
          3184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        -3400,
        -4872
      ],
      "raw_nearest": [
        -3408,
        -4880
      ],
      "viable_nearest": [
        -3408,
        -4880
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3408,
          -4880
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "outpost",
      "marker": [
        6968,
        232
      ],
      "raw_nearest": [
        6960,
        224
      ],
      "viable_nearest": [
        6960,
        224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          6960,
          224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        299,
        -229
      ],
      "raw_nearest": [
        296,
        -232
      ],
      "viable_nearest": [
        296,
        -232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          296,
          -232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        587,
        363
      ],
      "raw_nearest": [
        584,
        360
      ],
      "viable_nearest": [
        584,
        360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          584,
          360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        651,
        507
      ],
      "raw_nearest": [
        648,
        504
      ],
      "viable_nearest": [
        648,
        504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          648,
          504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        75,
        827
      ],
      "raw_nearest": [
        72,
        824
      ],
      "viable_nearest": [
        72,
        824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          72,
          824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        491,
        -597
      ],
      "raw_nearest": [
        488,
        -600
      ],
      "viable_nearest": [
        488,
        -600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          488,
          -600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        -277,
        1259
      ],
      "raw_nearest": [
        -280,
        1256
      ],
      "viable_nearest": [
        -280,
        1256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -280,
          1256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        -469,
        -853
      ],
      "raw_nearest": [
        -472,
        -856
      ],
      "viable_nearest": [
        -472,
        -856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -472,
          -856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        1195,
        -725
      ],
      "raw_nearest": [
        1192,
        -728
      ],
      "viable_nearest": [
        1192,
        -728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1192,
          -728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        1275,
        -469
      ],
      "raw_nearest": [
        1272,
        -472
      ],
      "viable_nearest": [
        1272,
        -472
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1272,
          -472
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        -565,
        1467
      ],
      "raw_nearest": [
        -568,
        1464
      ],
      "viable_nearest": [
        -568,
        1464
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -568,
          1464
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        1723,
        731
      ],
      "raw_nearest": [
        1720,
        728
      ],
      "viable_nearest": [
        1720,
        728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1720,
          728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        -261,
        1707
      ],
      "raw_nearest": [
        -264,
        1704
      ],
      "viable_nearest": [
        -264,
        1704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -264,
          1704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        619,
        -1429
      ],
      "raw_nearest": [
        616,
        -1432
      ],
      "viable_nearest": [
        616,
        -1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          616,
          -1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        1595,
        1051
      ],
      "raw_nearest": [
        1592,
        1048
      ],
      "viable_nearest": [
        1592,
        1048
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1592,
          1048
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        -149,
        1979
      ],
      "raw_nearest": [
        -152,
        1976
      ],
      "viable_nearest": [
        -152,
        1976
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -152,
          1976
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        811,
        -1701
      ],
      "raw_nearest": [
        808,
        -1704
      ],
      "viable_nearest": [
        808,
        -1704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          808,
          -1704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        1563,
        -1093
      ],
      "raw_nearest": [
        1560,
        -1096
      ],
      "viable_nearest": [
        1560,
        -1096
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1560,
          -1096
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        2107,
        491
      ],
      "raw_nearest": [
        2104,
        488
      ],
      "viable_nearest": [
        2104,
        488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          2104,
          488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        1547,
        1755
      ],
      "raw_nearest": [
        1544,
        1752
      ],
      "viable_nearest": [
        1544,
        1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1544,
          1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "fortress",
      "marker": [
        -1701,
        1307
      ],
      "raw_nearest": [
        -1704,
        1304
      ],
      "viable_nearest": [
        -1704,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1704,
          1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -418,
        765
      ],
      "raw_nearest": [
        -392,
        792
      ],
      "viable_nearest": [
        -392,
        792
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -392,
          792
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -338,
        -450
      ],
      "raw_nearest": [
        -312,
        -424
      ],
      "viable_nearest": [
        -312,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -312,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        98,
        -738
      ],
      "raw_nearest": [
        88,
        -712
      ],
      "viable_nearest": [
        88,
        -712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          88,
          -712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        369,
        936
      ],
      "raw_nearest": [
        392,
        968
      ],
      "viable_nearest": [
        392,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          392,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -537,
        -6
      ],
      "raw_nearest": [
        -552,
        24
      ],
      "viable_nearest": [
        -552,
        24
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -552,
          24
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -669,
        -194
      ],
      "raw_nearest": [
        -680,
        -168
      ],
      "viable_nearest": [
        -680,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -680,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        1185,
        376
      ],
      "raw_nearest": [
        1208,
        408
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        1248,
        599
      ],
      "raw_nearest": [
        1272,
        600
      ],
      "viable_nearest": [
        1272,
        600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1272,
          600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -642,
        829
      ],
      "raw_nearest": [
        -616,
        856
      ],
      "viable_nearest": [
        -616,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -616,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        184,
        -1215
      ],
      "raw_nearest": [
        200,
        -1192
      ],
      "viable_nearest": [
        200,
        -1192
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          200,
          -1192
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        1241,
        1238
      ],
      "raw_nearest": [
        1272,
        1224
      ],
      "viable_nearest": [
        1272,
        1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1272,
          1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -914,
        1197
      ],
      "raw_nearest": [
        -888,
        1224
      ],
      "viable_nearest": [
        -888,
        1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -888,
          1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -1374,
        8
      ],
      "raw_nearest": [
        -1352,
        40
      ],
      "viable_nearest": [
        -1352,
        40
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1352,
          40
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -360,
        -1088
      ],
      "raw_nearest": [
        -360,
        -1096
      ],
      "viable_nearest": [
        -360,
        -1096
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -360,
          -1096
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        825,
        1577
      ],
      "raw_nearest": [
        856,
        1608
      ],
      "viable_nearest": [
        856,
        1608
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          856,
          1608
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        418,
        1538
      ],
      "raw_nearest": [
        408,
        1528
      ],
      "viable_nearest": [
        408,
        1528
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          408,
          1528
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        1709,
        -610
      ],
      "raw_nearest": [
        1736,
        -584
      ],
      "viable_nearest": [
        1736,
        -584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1736,
          -584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        2130,
        93
      ],
      "raw_nearest": [
        2120,
        120
      ],
      "viable_nearest": [
        2120,
        120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          2120,
          120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        1040,
        1591
      ],
      "raw_nearest": [
        1064,
        1592
      ],
      "viable_nearest": [
        1064,
        1592
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1064,
          1592
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "12345",
      "type": "bastion",
      "marker": [
        -1110,
        1318
      ],
      "raw_nearest": [
        -1080,
        1304
      ],
      "viable_nearest": [
        -1080,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1080,
          1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        215,
        71
      ],
      "raw_nearest": [
        232,
        88
      ],
      "viable_nearest": [
        232,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          232,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        761,
        311
      ],
      "raw_nearest": [
        760,
        328
      ],
      "viable_nearest": [
        760,
        328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          760,
          328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        743,
        759
      ],
      "raw_nearest": [
        760,
        776
      ],
      "viable_nearest": [
        760,
        776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          760,
          776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -345,
        681
      ],
      "raw_nearest": [
        -328,
        680
      ],
      "viable_nearest": [
        -328,
        680
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -328,
          680
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -519,
        57
      ],
      "raw_nearest": [
        -520,
        56
      ],
      "viable_nearest": [
        -520,
        56
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -520,
          56
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -343,
        -311
      ],
      "raw_nearest": [
        -344,
        -312
      ],
      "viable_nearest": [
        -344,
        -312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -344,
          -312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        329,
        -297
      ],
      "raw_nearest": [
        328,
        -280
      ],
      "viable_nearest": [
        328,
        -280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          328,
          -280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        759,
        -505
      ],
      "raw_nearest": [
        776,
        -488
      ],
      "viable_nearest": [
        776,
        -488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          776,
          -488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        279,
        791
      ],
      "raw_nearest": [
        296,
        808
      ],
      "viable_nearest": [
        296,
        808
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          296,
          808
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        39,
        -823
      ],
      "raw_nearest": [
        56,
        -824
      ],
      "viable_nearest": [
        56,
        -824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          56,
          -824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        1351,
        185
      ],
      "raw_nearest": [
        1368,
        184
      ],
      "viable_nearest": [
        1368,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1368,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -329,
        1127
      ],
      "raw_nearest": [
        -312,
        1144
      ],
      "viable_nearest": [
        -312,
        1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -312,
          1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -873,
        569
      ],
      "raw_nearest": [
        -856,
        568
      ],
      "viable_nearest": [
        -856,
        568
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -856,
          568
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -999,
        -9
      ],
      "raw_nearest": [
        -1000,
        8
      ],
      "viable_nearest": [
        -1000,
        8
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -1000,
          8
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -1015,
        -441
      ],
      "raw_nearest": [
        -1016,
        -424
      ],
      "viable_nearest": [
        -1016,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -1016,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        -505,
        -823
      ],
      "raw_nearest": [
        -488,
        -824
      ],
      "viable_nearest": [
        -488,
        -824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -488,
          -824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        841,
        -1017
      ],
      "raw_nearest": [
        840,
        -1000
      ],
      "viable_nearest": [
        840,
        -1000
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          840,
          -1000
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        1177,
        -743
      ],
      "raw_nearest": [
        1176,
        -744
      ],
      "viable_nearest": [
        1176,
        -744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1176,
          -744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        1097,
        -297
      ],
      "raw_nearest": [
        1096,
        -280
      ],
      "viable_nearest": [
        1096,
        -280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1096,
          -280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "trial_chamber",
      "marker": [
        1433,
        729
      ],
      "raw_nearest": [
        1432,
        728
      ],
      "viable_nearest": [
        1432,
        728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1432,
          728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -3532,
        1892
      ],
      "raw_nearest": [
        -3532,
        1892
      ],
      "viable_nearest": [
        -3532,
        1892
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3532,
          1892
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -2204,
        4100
      ],
      "raw_nearest": [
        -2204,
        4100
      ],
      "viable_nearest": [
        -2204,
        4100
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2204,
          4100
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        5140,
        1492
      ],
      "raw_nearest": [
        5140,
        1492
      ],
      "viable_nearest": [
        5140,
        1492
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5140,
          1492
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        5636,
        -988
      ],
      "raw_nearest": [
        5636,
        -988
      ],
      "viable_nearest": [
        5636,
        -988
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5636,
          -988
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        7412,
        1156
      ],
      "raw_nearest": [
        7412,
        1156
      ],
      "viable_nearest": [
        7412,
        1156
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          7412,
          1156
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -4060,
        -5724
      ],
      "raw_nearest": [
        -4060,
        -5724
      ],
      "viable_nearest": [
        -4060,
        -5724
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4060,
          -5724
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        8340,
        -1660
      ],
      "raw_nearest": [
        8340,
        -1660
      ],
      "viable_nearest": [
        8340,
        -1660
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8340,
          -1660
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        4084,
        -7884
      ],
      "raw_nearest": [
        4084,
        -7884
      ],
      "viable_nearest": [
        4084,
        -7884
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4084,
          -7884
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -988,
        10516
      ],
      "raw_nearest": [
        -988,
        10516
      ],
      "viable_nearest": [
        -988,
        10516
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -988,
          10516
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        11108,
        1156
      ],
      "raw_nearest": [
        11108,
        1156
      ],
      "viable_nearest": [
        11108,
        1156
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          11108,
          1156
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -2156,
        -10812
      ],
      "raw_nearest": [
        -2156,
        -10812
      ],
      "viable_nearest": [
        -2156,
        -10812
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2156,
          -10812
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -7836,
        8228
      ],
      "raw_nearest": [
        -7836,
        8228
      ],
      "viable_nearest": [
        -7836,
        8228
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7836,
          8228
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        4836,
        10836
      ],
      "raw_nearest": [
        4836,
        10836
      ],
      "viable_nearest": [
        4836,
        10836
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4836,
          10836
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        11412,
        4196
      ],
      "raw_nearest": [
        11412,
        4196
      ],
      "viable_nearest": [
        11412,
        4196
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          11412,
          4196
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -5404,
        11684
      ],
      "raw_nearest": [
        -5404,
        11684
      ],
      "viable_nearest": [
        -5404,
        11684
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5404,
          11684
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -13756,
        -4844
      ],
      "raw_nearest": [
        -13756,
        -4844
      ],
      "viable_nearest": [
        -13756,
        -4844
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -13756,
          -4844
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        -1548,
        -14508
      ],
      "raw_nearest": [
        -1548,
        -14508
      ],
      "viable_nearest": [
        -1548,
        -14508
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1548,
          -14508
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        14500,
        4116
      ],
      "raw_nearest": [
        14500,
        4116
      ],
      "viable_nearest": [
        14500,
        4116
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          14500,
          4116
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        2084,
        -15052
      ],
      "raw_nearest": [
        2084,
        -15052
      ],
      "viable_nearest": [
        2084,
        -15052
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2084,
          -15052
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "stronghold",
      "marker": [
        11604,
        -10716
      ],
      "raw_nearest": [
        11604,
        -10716
      ],
      "viable_nearest": [
        11604,
        -10716
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          11604,
          -10716
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        728,
        184
      ],
      "raw_nearest": [
        728,
        184
      ],
      "viable_nearest": [
        728,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          728,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -280,
        168
      ],
      "raw_nearest": [
        -280,
        168
      ],
      "viable_nearest": [
        -280,
        168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -280,
          168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -408,
        88
      ],
      "raw_nearest": [
        -408,
        88
      ],
      "viable_nearest": [
        -408,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -408,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        8,
        -376
      ],
      "raw_nearest": [
        8,
        -376
      ],
      "viable_nearest": [
        8,
        -376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8,
          -376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        136,
        -392
      ],
      "raw_nearest": [
        136,
        -392
      ],
      "viable_nearest": [
        136,
        -392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          136,
          -392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        24,
        952
      ],
      "raw_nearest": [
        24,
        952
      ],
      "viable_nearest": [
        24,
        952
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          24,
          952
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        24,
        984
      ],
      "raw_nearest": [
        24,
        984
      ],
      "viable_nearest": [
        24,
        984
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          24,
          984
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -456,
        -360
      ],
      "raw_nearest": [
        -456,
        -360
      ],
      "viable_nearest": [
        -456,
        -360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -456,
          -360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        728,
        -344
      ],
      "raw_nearest": [
        728,
        -344
      ],
      "viable_nearest": [
        728,
        -344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          728,
          -344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        1048,
        248
      ],
      "raw_nearest": [
        1048,
        248
      ],
      "viable_nearest": [
        1048,
        248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1048,
          248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        920,
        616
      ],
      "raw_nearest": [
        920,
        616
      ],
      "viable_nearest": [
        920,
        616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          920,
          616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        648,
        808
      ],
      "raw_nearest": [
        648,
        808
      ],
      "viable_nearest": [
        648,
        808
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          648,
          808
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        408,
        936
      ],
      "raw_nearest": [
        408,
        936
      ],
      "viable_nearest": [
        408,
        936
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          936
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -424,
        888
      ],
      "raw_nearest": [
        -424,
        888
      ],
      "viable_nearest": [
        -424,
        888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -424,
          888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -712,
        360
      ],
      "raw_nearest": [
        -712,
        360
      ],
      "viable_nearest": [
        -712,
        360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -712,
          360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -1016,
        152
      ],
      "raw_nearest": [
        -1016,
        152
      ],
      "viable_nearest": [
        -1016,
        152
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1016,
          152
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        -200,
        -680
      ],
      "raw_nearest": [
        -200,
        -680
      ],
      "viable_nearest": [
        -200,
        -680
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -200,
          -680
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        632,
        -568
      ],
      "raw_nearest": [
        632,
        -568
      ],
      "viable_nearest": [
        632,
        -568
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          632,
          -568
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        776,
        -168
      ],
      "raw_nearest": [
        776,
        -168
      ],
      "viable_nearest": [
        776,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          776,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "mineshaft",
      "marker": [
        1096,
        280
      ],
      "raw_nearest": [
        1096,
        280
      ],
      "viable_nearest": [
        1096,
        280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1096,
          280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -360,
        1752
      ],
      "raw_nearest": [
        -360,
        1752
      ],
      "viable_nearest": [
        -360,
        1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -360,
          1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -584,
        1752
      ],
      "raw_nearest": [
        -584,
        1752
      ],
      "viable_nearest": [
        -584,
        1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -584,
          1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -1000,
        1592
      ],
      "raw_nearest": [
        -1000,
        1592
      ],
      "viable_nearest": [
        -1000,
        1592
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1000,
          1592
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        1320,
        2456
      ],
      "raw_nearest": [
        1320,
        2456
      ],
      "viable_nearest": [
        1320,
        2456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1320,
          2456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        936,
        2776
      ],
      "raw_nearest": [
        936,
        2776
      ],
      "viable_nearest": [
        936,
        2776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          936,
          2776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        2792,
        -984
      ],
      "raw_nearest": [
        2792,
        -984
      ],
      "viable_nearest": [
        2792,
        -984
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2792,
          -984
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        984,
        3192
      ],
      "raw_nearest": [
        984,
        3192
      ],
      "viable_nearest": [
        984,
        3192
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          984,
          3192
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        1608,
        3592
      ],
      "raw_nearest": [
        1608,
        3592
      ],
      "viable_nearest": [
        1608,
        3592
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1608,
          3592
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        2744,
        -2984
      ],
      "raw_nearest": [
        2744,
        -2984
      ],
      "viable_nearest": [
        2744,
        -2984
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2744,
          -2984
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        2776,
        -3304
      ],
      "raw_nearest": [
        2776,
        -3304
      ],
      "viable_nearest": [
        2776,
        -3304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2776,
          -3304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        4728,
        2872
      ],
      "raw_nearest": [
        4728,
        2872
      ],
      "viable_nearest": [
        4728,
        2872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4728,
          2872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        3288,
        4728
      ],
      "raw_nearest": [
        3288,
        4728
      ],
      "viable_nearest": [
        3288,
        4728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3288,
          4728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        4712,
        -2664
      ],
      "raw_nearest": [
        4712,
        -2664
      ],
      "viable_nearest": [
        4712,
        -2664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4712,
          -2664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        3208,
        5208
      ],
      "raw_nearest": [
        3208,
        5208
      ],
      "viable_nearest": [
        3208,
        5208
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3208,
          5208
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -3000,
        -5672
      ],
      "raw_nearest": [
        -3000,
        -5672
      ],
      "viable_nearest": [
        -3000,
        -5672
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3000,
          -5672
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -5640,
        3576
      ],
      "raw_nearest": [
        -5640,
        3576
      ],
      "viable_nearest": [
        -5640,
        3576
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5640,
          3576
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -5192,
        4664
      ],
      "raw_nearest": [
        -5192,
        4664
      ],
      "viable_nearest": [
        -5192,
        4664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5192,
          4664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -4968,
        5512
      ],
      "raw_nearest": [
        -4968,
        5512
      ],
      "viable_nearest": [
        -4968,
        5512
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4968,
          5512
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        2408,
        -6728
      ],
      "raw_nearest": [
        2408,
        -6728
      ],
      "viable_nearest": [
        2408,
        -6728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2408,
          -6728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ancient_city",
      "marker": [
        -5624,
        5048
      ],
      "raw_nearest": [
        -5624,
        5048
      ],
      "viable_nearest": [
        -5624,
        5048
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5624,
          5048
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        232,
        696
      ],
      "raw_nearest": [
        232,
        696
      ],
      "viable_nearest": [
        232,
        696
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          696
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        760,
        264
      ],
      "raw_nearest": [
        760,
        264
      ],
      "viable_nearest": [
        760,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          760,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -824,
        120
      ],
      "raw_nearest": [
        -824,
        120
      ],
      "viable_nearest": [
        -824,
        120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -824,
          120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -824,
        616
      ],
      "raw_nearest": [
        -824,
        616
      ],
      "viable_nearest": [
        -824,
        616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -824,
          616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        1432,
        840
      ],
      "raw_nearest": [
        1432,
        840
      ],
      "viable_nearest": [
        1432,
        840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1432,
          840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        792,
        -1032
      ],
      "raw_nearest": [
        792,
        -1032
      ],
      "viable_nearest": [
        792,
        -1032
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          792,
          -1032
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -856,
        1352
      ],
      "raw_nearest": [
        -856,
        1352
      ],
      "viable_nearest": [
        -856,
        1352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -856,
          1352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -1560,
        328
      ],
      "raw_nearest": [
        -1560,
        328
      ],
      "viable_nearest": [
        -1560,
        328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1560,
          328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -1928,
        744
      ],
      "raw_nearest": [
        -1928,
        744
      ],
      "viable_nearest": [
        -1928,
        744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1928,
          744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -1928,
        296
      ],
      "raw_nearest": [
        -1928,
        296
      ],
      "viable_nearest": [
        -1928,
        296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1928,
          296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -808,
        -1560
      ],
      "raw_nearest": [
        -808,
        -1560
      ],
      "viable_nearest": [
        -808,
        -1560
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -808,
          -1560
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -2088,
        -248
      ],
      "raw_nearest": [
        -2088,
        -248
      ],
      "viable_nearest": [
        -2088,
        -248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2088,
          -248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        2344,
        -216
      ],
      "raw_nearest": [
        2344,
        -216
      ],
      "viable_nearest": [
        2344,
        -216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2344,
          -216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -2376,
        -456
      ],
      "raw_nearest": [
        -2376,
        -456
      ],
      "viable_nearest": [
        -2376,
        -456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2376,
          -456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        2008,
        -1944
      ],
      "raw_nearest": [
        2008,
        -1944
      ],
      "viable_nearest": [
        2008,
        -1944
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2008,
          -1944
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        2456,
        -1496
      ],
      "raw_nearest": [
        2456,
        -1496
      ],
      "viable_nearest": [
        2456,
        -1496
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2456,
          -1496
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        3064,
        1272
      ],
      "raw_nearest": [
        3064,
        1272
      ],
      "viable_nearest": [
        3064,
        1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3064,
          1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        -1288,
        -2424
      ],
      "raw_nearest": [
        -1288,
        -2424
      ],
      "viable_nearest": [
        -1288,
        -2424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1288,
          -2424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        2920,
        -728
      ],
      "raw_nearest": [
        2920,
        -728
      ],
      "viable_nearest": [
        2920,
        -728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2920,
          -728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "village",
      "marker": [
        3320,
        1288
      ],
      "raw_nearest": [
        3320,
        1288
      ],
      "viable_nearest": [
        3320,
        1288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3320,
          1288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        286,
        371
      ],
      "raw_nearest": [
        296,
        376
      ],
      "viable_nearest": [
        296,
        376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          296,
          376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        222,
        -493
      ],
      "raw_nearest": [
        232,
        -488
      ],
      "viable_nearest": [
        232,
        -488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          232,
          -488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        692,
        269
      ],
      "raw_nearest": [
        696,
        280
      ],
      "viable_nearest": [
        696,
        280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          696,
          280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        85,
        828
      ],
      "raw_nearest": [
        88,
        840
      ],
      "viable_nearest": [
        88,
        840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          88,
          840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -499,
        812
      ],
      "raw_nearest": [
        -488,
        824
      ],
      "viable_nearest": [
        -488,
        824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -488,
          824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -540,
        -435
      ],
      "raw_nearest": [
        -536,
        -424
      ],
      "viable_nearest": [
        -536,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -536,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        972,
        -429
      ],
      "raw_nearest": [
        984,
        -424
      ],
      "viable_nearest": [
        984,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          984,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        119,
        -1124
      ],
      "raw_nearest": [
        120,
        -1112
      ],
      "viable_nearest": [
        120,
        -1112
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          120,
          -1112
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -276,
        1380
      ],
      "raw_nearest": [
        -264,
        1384
      ],
      "viable_nearest": [
        -264,
        1384
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -264,
          1384
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -1101,
        850
      ],
      "raw_nearest": [
        -1096,
        856
      ],
      "viable_nearest": [
        -1096,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1096,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        724,
        -1043
      ],
      "raw_nearest": [
        728,
        -1032
      ],
      "viable_nearest": [
        728,
        -1032
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          728,
          -1032
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        1532,
        -454
      ],
      "raw_nearest": [
        1544,
        -440
      ],
      "viable_nearest": [
        1544,
        -440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1544,
          -440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -941,
        1299
      ],
      "raw_nearest": [
        -936,
        1304
      ],
      "viable_nearest": [
        -936,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -936,
          1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        2197,
        60
      ],
      "raw_nearest": [
        2200,
        72
      ],
      "viable_nearest": [
        2200,
        72
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          2200,
          72
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        1636,
        1420
      ],
      "raw_nearest": [
        1640,
        1432
      ],
      "viable_nearest": [
        1640,
        1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1640,
          1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        989,
        1970
      ],
      "raw_nearest": [
        1000,
        1976
      ],
      "viable_nearest": [
        1000,
        1976
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1000,
          1976
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        380,
        1980
      ],
      "raw_nearest": [
        392,
        1992
      ],
      "viable_nearest": [
        392,
        1992
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          392,
          1992
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        1636,
        -908
      ],
      "raw_nearest": [
        1640,
        -904
      ],
      "viable_nearest": [
        1640,
        -904
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1640,
          -904
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -1164,
        1980
      ],
      "raw_nearest": [
        -1160,
        1992
      ],
      "viable_nearest": [
        -1160,
        1992
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1160,
          1992
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "ruined_portal",
      "marker": [
        -258,
        -1853
      ],
      "raw_nearest": [
        -248,
        -1848
      ],
      "viable_nearest": [
        -248,
        -1848
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -248,
          -1848
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -184,
        -504
      ],
      "raw_nearest": [
        -184,
        -504
      ],
      "viable_nearest": [
        -184,
        -504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -184,
          -504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        232,
        -664
      ],
      "raw_nearest": [
        232,
        -664
      ],
      "viable_nearest": [
        232,
        -664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          -664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -856,
        -696
      ],
      "raw_nearest": [
        -856,
        -696
      ],
      "viable_nearest": [
        -856,
        -696
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -856,
          -696
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -648,
        -568
      ],
      "raw_nearest": [
        -648,
        -568
      ],
      "viable_nearest": [
        -648,
        -568
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -648,
          -568
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        920,
        -520
      ],
      "raw_nearest": [
        920,
        -520
      ],
      "viable_nearest": [
        920,
        -520
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          920,
          -520
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -1080,
        968
      ],
      "raw_nearest": [
        -1080,
        968
      ],
      "viable_nearest": [
        -1080,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1080,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -232,
        -1224
      ],
      "raw_nearest": [
        -232,
        -1224
      ],
      "viable_nearest": [
        -232,
        -1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -232,
          -1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1224,
        -920
      ],
      "raw_nearest": [
        1224,
        -920
      ],
      "viable_nearest": [
        1224,
        -920
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1224,
          -920
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1368,
        -552
      ],
      "raw_nearest": [
        1368,
        -552
      ],
      "viable_nearest": [
        1368,
        -552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1368,
          -552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1688,
        296
      ],
      "raw_nearest": [
        1688,
        296
      ],
      "viable_nearest": [
        1688,
        296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1688,
          296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        904,
        1640
      ],
      "raw_nearest": [
        904,
        1640
      ],
      "viable_nearest": [
        904,
        1640
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          904,
          1640
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -1384,
        -328
      ],
      "raw_nearest": [
        -1384,
        -328
      ],
      "viable_nearest": [
        -1384,
        -328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1384,
          -328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -1512,
        -664
      ],
      "raw_nearest": [
        -1512,
        -664
      ],
      "viable_nearest": [
        -1512,
        -664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1512,
          -664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -872,
        -1256
      ],
      "raw_nearest": [
        -872,
        -1256
      ],
      "viable_nearest": [
        -872,
        -1256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -872,
          -1256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        -584,
        -1512
      ],
      "raw_nearest": [
        -584,
        -1512
      ],
      "viable_nearest": [
        -584,
        -1512
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -584,
          -1512
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        968,
        -1528
      ],
      "raw_nearest": [
        968,
        -1528
      ],
      "viable_nearest": [
        968,
        -1528
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          968,
          -1528
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1256,
        -1272
      ],
      "raw_nearest": [
        1256,
        -1272
      ],
      "viable_nearest": [
        1256,
        -1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1256,
          -1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1784,
        -728
      ],
      "raw_nearest": [
        1784,
        -728
      ],
      "viable_nearest": [
        1784,
        -728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1784,
          -728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1960,
        648
      ],
      "raw_nearest": [
        1960,
        648
      ],
      "viable_nearest": [
        1960,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1960,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "shipwreck",
      "marker": [
        1752,
        1176
      ],
      "raw_nearest": [
        1752,
        1176
      ],
      "viable_nearest": [
        1752,
        1176
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1752,
          1176
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -872,
        -840
      ],
      "raw_nearest": [
        -872,
        -840
      ],
      "viable_nearest": [
        -872,
        -840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -872,
          -840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        168,
        -1288
      ],
      "raw_nearest": [
        168,
        -1288
      ],
      "viable_nearest": [
        168,
        -1288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          168,
          -1288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        1304,
        -408
      ],
      "raw_nearest": [
        1304,
        -408
      ],
      "viable_nearest": [
        1304,
        -408
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1304,
          -408
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -376,
        -1336
      ],
      "raw_nearest": [
        -376,
        -1336
      ],
      "viable_nearest": [
        -376,
        -1336
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -376,
          -1336
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        1864,
        600
      ],
      "raw_nearest": [
        1864,
        600
      ],
      "viable_nearest": [
        1864,
        600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1864,
          600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        1144,
        -1528
      ],
      "raw_nearest": [
        1144,
        -1528
      ],
      "viable_nearest": [
        1144,
        -1528
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1144,
          -1528
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        1608,
        -1272
      ],
      "raw_nearest": [
        1608,
        -1272
      ],
      "viable_nearest": [
        1608,
        -1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1608,
          -1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        1736,
        -1688
      ],
      "raw_nearest": [
        1736,
        -1688
      ],
      "viable_nearest": [
        1736,
        -1688
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1736,
          -1688
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -328,
        2824
      ],
      "raw_nearest": [
        -328,
        2824
      ],
      "viable_nearest": [
        -328,
        2824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -328,
          2824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -2392,
        1704
      ],
      "raw_nearest": [
        -2392,
        1704
      ],
      "viable_nearest": [
        -2392,
        1704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2392,
          1704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -1912,
        2760
      ],
      "raw_nearest": [
        -1912,
        2760
      ],
      "viable_nearest": [
        -1912,
        2760
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1912,
          2760
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -3320,
        232
      ],
      "raw_nearest": [
        -3320,
        232
      ],
      "viable_nearest": [
        -3320,
        232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3320,
          232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -1752,
        3224
      ],
      "raw_nearest": [
        -1752,
        3224
      ],
      "viable_nearest": [
        -1752,
        3224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1752,
          3224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -2200,
        2744
      ],
      "raw_nearest": [
        -2200,
        2744
      ],
      "viable_nearest": [
        -2200,
        2744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2200,
          2744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -3304,
        1672
      ],
      "raw_nearest": [
        -3304,
        1672
      ],
      "viable_nearest": [
        -3304,
        1672
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3304,
          1672
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        2824,
        3288
      ],
      "raw_nearest": [
        2824,
        3288
      ],
      "viable_nearest": [
        2824,
        3288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2824,
          3288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -3864,
        360
      ],
      "raw_nearest": [
        -3864,
        360
      ],
      "viable_nearest": [
        -3864,
        360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3864,
          360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        -1816,
        -3832
      ],
      "raw_nearest": [
        -1816,
        -3832
      ],
      "viable_nearest": [
        -1816,
        -3832
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1816,
          -3832
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        3800,
        -1848
      ],
      "raw_nearest": [
        3800,
        -1848
      ],
      "viable_nearest": [
        3800,
        -1848
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3800,
          -1848
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "monument",
      "marker": [
        3448,
        3256
      ],
      "raw_nearest": [
        3448,
        3256
      ],
      "viable_nearest": [
        3448,
        3256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3448,
          3256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        3128,
        280
      ],
      "raw_nearest": [
        3120,
        272
      ],
      "viable_nearest": [
        3120,
        272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3120,
          272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        1432,
        3208
      ],
      "raw_nearest": [
        1424,
        3200
      ],
      "viable_nearest": [
        1424,
        3200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1424,
          3200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        3112,
        -2152
      ],
      "raw_nearest": [
        3104,
        -2160
      ],
      "viable_nearest": [
        3104,
        -2160
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3104,
          -2160
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        -760,
        4120
      ],
      "raw_nearest": [
        -768,
        4112
      ],
      "viable_nearest": [
        -768,
        4112
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -768,
          4112
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        1624,
        -3752
      ],
      "raw_nearest": [
        1616,
        -3760
      ],
      "viable_nearest": [
        1616,
        -3760
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1616,
          -3760
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        4120,
        -840
      ],
      "raw_nearest": [
        4112,
        -848
      ],
      "viable_nearest": [
        4112,
        -848
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4112,
          -848
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        4360,
        488
      ],
      "raw_nearest": [
        4352,
        480
      ],
      "viable_nearest": [
        4352,
        480
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4352,
          480
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        4376,
        1464
      ],
      "raw_nearest": [
        4368,
        1456
      ],
      "viable_nearest": [
        4368,
        1456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4368,
          1456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        3000,
        -3304
      ],
      "raw_nearest": [
        2992,
        -3312
      ],
      "viable_nearest": [
        2992,
        -3312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2992,
          -3312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        -3512,
        3096
      ],
      "raw_nearest": [
        -3520,
        3088
      ],
      "viable_nearest": [
        -3520,
        3088
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3520,
          3088
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        -4536,
        1528
      ],
      "raw_nearest": [
        -4544,
        1520
      ],
      "viable_nearest": [
        -4544,
        1520
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4544,
          1520
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        -4488,
        824
      ],
      "raw_nearest": [
        -4496,
        816
      ],
      "viable_nearest": [
        -4496,
        816
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4496,
          816
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        328,
        -4760
      ],
      "raw_nearest": [
        320,
        -4768
      ],
      "viable_nearest": [
        320,
        -4768
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          320,
          -4768
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        4392,
        3112
      ],
      "raw_nearest": [
        4384,
        3104
      ],
      "viable_nearest": [
        4384,
        3104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4384,
          3104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        -3160,
        4296
      ],
      "raw_nearest": [
        -3168,
        4288
      ],
      "viable_nearest": [
        -3168,
        4288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3168,
          4288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        5544,
        504
      ],
      "raw_nearest": [
        5536,
        496
      ],
      "viable_nearest": [
        5536,
        496
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5536,
          496
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        -4520,
        2984
      ],
      "raw_nearest": [
        -4528,
        2976
      ],
      "viable_nearest": [
        -4528,
        2976
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4528,
          2976
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        5368,
        -1752
      ],
      "raw_nearest": [
        5360,
        -1760
      ],
      "viable_nearest": [
        5360,
        -1760
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5360,
          -1760
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        1656,
        5704
      ],
      "raw_nearest": [
        1648,
        5696
      ],
      "viable_nearest": [
        1648,
        5696
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1648,
          5696
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "outpost",
      "marker": [
        5256,
        -3160
      ],
      "raw_nearest": [
        5248,
        -3168
      ],
      "viable_nearest": [
        5248,
        -3168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5248,
          -3168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -133,
        107
      ],
      "raw_nearest": [
        -136,
        104
      ],
      "viable_nearest": [
        -136,
        104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -136,
          104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        651,
        331
      ],
      "raw_nearest": [
        648,
        328
      ],
      "viable_nearest": [
        648,
        328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          648,
          328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -405,
        491
      ],
      "raw_nearest": [
        -408,
        488
      ],
      "viable_nearest": [
        -408,
        488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -408,
          488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        667,
        -293
      ],
      "raw_nearest": [
        664,
        -296
      ],
      "viable_nearest": [
        664,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          664,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        555,
        1131
      ],
      "raw_nearest": [
        552,
        1128
      ],
      "viable_nearest": [
        552,
        1128
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          552,
          1128
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        363,
        1275
      ],
      "raw_nearest": [
        360,
        1272
      ],
      "viable_nearest": [
        360,
        1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          360,
          1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        1355,
        267
      ],
      "raw_nearest": [
        1352,
        264
      ],
      "viable_nearest": [
        1352,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1352,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -293,
        -1157
      ],
      "raw_nearest": [
        -296,
        -1160
      ],
      "viable_nearest": [
        -296,
        -1160
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -296,
          -1160
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        1755,
        891
      ],
      "raw_nearest": [
        1752,
        888
      ],
      "viable_nearest": [
        1752,
        888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1752,
          888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        123,
        1819
      ],
      "raw_nearest": [
        120,
        1816
      ],
      "viable_nearest": [
        120,
        1816
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          120,
          1816
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -1525,
        779
      ],
      "raw_nearest": [
        -1528,
        776
      ],
      "viable_nearest": [
        -1528,
        776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1528,
          776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -1317,
        267
      ],
      "raw_nearest": [
        -1320,
        264
      ],
      "viable_nearest": [
        -1320,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1320,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        1323,
        1659
      ],
      "raw_nearest": [
        1320,
        1656
      ],
      "viable_nearest": [
        1320,
        1656
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1320,
          1656
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -1253,
        1627
      ],
      "raw_nearest": [
        -1256,
        1624
      ],
      "viable_nearest": [
        -1256,
        1624
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1256,
          1624
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -1589,
        363
      ],
      "raw_nearest": [
        -1592,
        360
      ],
      "viable_nearest": [
        -1592,
        360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1592,
          360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -1669,
        -597
      ],
      "raw_nearest": [
        -1672,
        -600
      ],
      "viable_nearest": [
        -1672,
        -600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1672,
          -600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        171,
        -2037
      ],
      "raw_nearest": [
        168,
        -2040
      ],
      "viable_nearest": [
        168,
        -2040
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          168,
          -2040
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        1147,
        2107
      ],
      "raw_nearest": [
        1144,
        2104
      ],
      "viable_nearest": [
        1144,
        2104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1144,
          2104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        -1685,
        -1173
      ],
      "raw_nearest": [
        -1688,
        -1176
      ],
      "viable_nearest": [
        -1688,
        -1176
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1688,
          -1176
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "fortress",
      "marker": [
        1707,
        -1301
      ],
      "raw_nearest": [
        1704,
        -1304
      ],
      "viable_nearest": [
        1704,
        -1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1704,
          -1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        46,
        311
      ],
      "raw_nearest": [
        40,
        296
      ],
      "viable_nearest": [
        40,
        296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          40,
          296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        65,
        -375
      ],
      "raw_nearest": [
        88,
        -344
      ],
      "viable_nearest": [
        88,
        -344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          88,
          -344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        729,
        598
      ],
      "raw_nearest": [
        760,
        584
      ],
      "viable_nearest": [
        760,
        584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          760,
          584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -670,
        56
      ],
      "raw_nearest": [
        -648,
        88
      ],
      "viable_nearest": [
        -648,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -648,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        143,
        -679
      ],
      "raw_nearest": [
        136,
        -664
      ],
      "viable_nearest": [
        136,
        -664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          136,
          -664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -2,
        882
      ],
      "raw_nearest": [
        24,
        872
      ],
      "viable_nearest": [
        24,
        872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          24,
          872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -173,
        -642
      ],
      "raw_nearest": [
        -184,
        -616
      ],
      "viable_nearest": [
        -184,
        -616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -184,
          -616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        1014,
        1158
      ],
      "raw_nearest": [
        1000,
        1144
      ],
      "viable_nearest": [
        1000,
        1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1000,
          1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -177,
        1191
      ],
      "raw_nearest": [
        -184,
        1176
      ],
      "viable_nearest": [
        -184,
        1176
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -184,
          1176
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -791,
        944
      ],
      "raw_nearest": [
        -776,
        968
      ],
      "viable_nearest": [
        -776,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -776,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -816,
        -119
      ],
      "raw_nearest": [
        -824,
        -104
      ],
      "viable_nearest": [
        -824,
        -104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -824,
          -104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -727,
        -591
      ],
      "raw_nearest": [
        -712,
        -568
      ],
      "viable_nearest": [
        -712,
        -568
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -712,
          -568
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        130,
        -1197
      ],
      "raw_nearest": [
        120,
        -1208
      ],
      "viable_nearest": [
        120,
        -1208
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          120,
          -1208
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        1065,
        -326
      ],
      "raw_nearest": [
        1096,
        -296
      ],
      "viable_nearest": [
        1096,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1096,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        1336,
        592
      ],
      "raw_nearest": [
        1352,
        616
      ],
      "viable_nearest": [
        1352,
        616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1352,
          616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -1106,
        -434
      ],
      "raw_nearest": [
        -1080,
        -408
      ],
      "viable_nearest": [
        -1080,
        -408
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1080,
          -408
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -1150,
        -647
      ],
      "raw_nearest": [
        -1128,
        -616
      ],
      "viable_nearest": [
        -1128,
        -616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1128,
          -616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        -573,
        -1058
      ],
      "raw_nearest": [
        -584,
        -1032
      ],
      "viable_nearest": [
        -584,
        -1032
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -584,
          -1032
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        505,
        -1129
      ],
      "raw_nearest": [
        536,
        -1144
      ],
      "viable_nearest": [
        536,
        -1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          536,
          -1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "0",
      "type": "bastion",
      "marker": [
        1256,
        -881
      ],
      "raw_nearest": [
        1288,
        -888
      ],
      "viable_nearest": [
        1288,
        -888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1288,
          -888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        345,
        71
      ],
      "raw_nearest": [
        344,
        88
      ],
      "viable_nearest": [
        344,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          344,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        7,
        -215
      ],
      "raw_nearest": [
        24,
        -216
      ],
      "viable_nearest": [
        24,
        -216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          24,
          -216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        105,
        713
      ],
      "raw_nearest": [
        104,
        712
      ],
      "viable_nearest": [
        104,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          104,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -441,
        57
      ],
      "raw_nearest": [
        -424,
        56
      ],
      "viable_nearest": [
        -424,
        56
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -424,
          56
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        551,
        631
      ],
      "raw_nearest": [
        568,
        648
      ],
      "viable_nearest": [
        568,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          568,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -313,
        -265
      ],
      "raw_nearest": [
        -296,
        -248
      ],
      "viable_nearest": [
        -296,
        -248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -296,
          -248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        1095,
        135
      ],
      "raw_nearest": [
        1112,
        152
      ],
      "viable_nearest": [
        1112,
        152
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1112,
          152
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -521,
        535
      ],
      "raw_nearest": [
        -504,
        552
      ],
      "viable_nearest": [
        -504,
        552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -504,
          552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        135,
        -841
      ],
      "raw_nearest": [
        152,
        -824
      ],
      "viable_nearest": [
        152,
        -824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          152,
          -824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        809,
        -423
      ],
      "raw_nearest": [
        808,
        -424
      ],
      "viable_nearest": [
        808,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          808,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        1241,
        633
      ],
      "raw_nearest": [
        1240,
        632
      ],
      "viable_nearest": [
        1240,
        632
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1240,
          632
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        41,
        1305
      ],
      "raw_nearest": [
        40,
        1304
      ],
      "viable_nearest": [
        40,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          40,
          1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -199,
        1127
      ],
      "raw_nearest": [
        -200,
        1144
      ],
      "viable_nearest": [
        -200,
        1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -200,
          1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -887,
        -9
      ],
      "raw_nearest": [
        -888,
        8
      ],
      "viable_nearest": [
        -888,
        8
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -888,
          8
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -983,
        -359
      ],
      "raw_nearest": [
        -984,
        -360
      ],
      "viable_nearest": [
        -984,
        -360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -984,
          -360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        -391,
        -873
      ],
      "raw_nearest": [
        -392,
        -856
      ],
      "viable_nearest": [
        -392,
        -856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -392,
          -856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        1271,
        -761
      ],
      "raw_nearest": [
        1288,
        -744
      ],
      "viable_nearest": [
        1288,
        -744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1288,
          -744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        1129,
        -233
      ],
      "raw_nearest": [
        1128,
        -216
      ],
      "viable_nearest": [
        1128,
        -216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1128,
          -216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        1671,
        215
      ],
      "raw_nearest": [
        1688,
        232
      ],
      "viable_nearest": [
        1688,
        232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1688,
          232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "trial_chamber",
      "marker": [
        695,
        1287
      ],
      "raw_nearest": [
        712,
        1304
      ],
      "viable_nearest": [
        712,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          712,
          1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        4084,
        -828
      ],
      "raw_nearest": [
        4084,
        -828
      ],
      "viable_nearest": [
        4084,
        -828
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4084,
          -828
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -1004,
        4436
      ],
      "raw_nearest": [
        -1004,
        4436
      ],
      "viable_nearest": [
        -1004,
        4436
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1004,
          4436
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -4204,
        884
      ],
      "raw_nearest": [
        -4204,
        884
      ],
      "viable_nearest": [
        -4204,
        884
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4204,
          884
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        7396,
        -1356
      ],
      "raw_nearest": [
        7396,
        -1356
      ],
      "viable_nearest": [
        7396,
        -1356
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          7396,
          -1356
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        6212,
        -4700
      ],
      "raw_nearest": null,
      "viable_nearest": null,
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        3524,
        -7276
      ],
      "raw_nearest": null,
      "viable_nearest": null,
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        8308,
        852
      ],
      "raw_nearest": [
        8308,
        852
      ],
      "viable_nearest": [
        8308,
        852
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8308,
          852
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -8748,
        -1436
      ],
      "raw_nearest": [
        -8748,
        -1436
      ],
      "viable_nearest": [
        -8748,
        -1436
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -8748,
          -1436
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        8484,
        4996
      ],
      "raw_nearest": [
        8484,
        4996
      ],
      "viable_nearest": [
        8484,
        4996
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8484,
          4996
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -5484,
        8020
      ],
      "raw_nearest": [
        -5484,
        8020
      ],
      "viable_nearest": [
        -5484,
        8020
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5484,
          8020
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        10660,
        2036
      ],
      "raw_nearest": [
        10660,
        2036
      ],
      "viable_nearest": [
        10660,
        2036
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          10660,
          2036
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        4292,
        -10444
      ],
      "raw_nearest": [
        4292,
        -10444
      ],
      "viable_nearest": [
        4292,
        -10444
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4292,
          -10444
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -5532,
        11588
      ],
      "raw_nearest": [
        -5532,
        11588
      ],
      "viable_nearest": [
        -5532,
        11588
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5532,
          11588
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        8276,
        11540
      ],
      "raw_nearest": [
        8276,
        11540
      ],
      "viable_nearest": [
        8276,
        11540
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8276,
          11540
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -10412,
        10708
      ],
      "raw_nearest": [
        -10412,
        10708
      ],
      "viable_nearest": [
        -10412,
        10708
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -10412,
          10708
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        -1228,
        -14796
      ],
      "raw_nearest": [
        -1228,
        -14796
      ],
      "viable_nearest": [
        -1228,
        -14796
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1228,
          -14796
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        14388,
        -4476
      ],
      "raw_nearest": [
        14388,
        -4476
      ],
      "viable_nearest": [
        14388,
        -4476
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          14388,
          -4476
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        10564,
        -11148
      ],
      "raw_nearest": [
        10564,
        -11148
      ],
      "viable_nearest": [
        10564,
        -11148
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          10564,
          -11148
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        13972,
        7572
      ],
      "raw_nearest": [
        13972,
        7572
      ],
      "viable_nearest": [
        13972,
        7572
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          13972,
          7572
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "stronghold",
      "marker": [
        10932,
        11700
      ],
      "raw_nearest": [
        10932,
        11700
      ],
      "viable_nearest": [
        10932,
        11700
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          10932,
          11700
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        8,
        584
      ],
      "raw_nearest": [
        8,
        584
      ],
      "viable_nearest": [
        8,
        584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8,
          584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        40,
        744
      ],
      "raw_nearest": [
        40,
        744
      ],
      "viable_nearest": [
        40,
        744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          40,
          744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -8,
        360
      ],
      "raw_nearest": [
        -8,
        360
      ],
      "viable_nearest": [
        -8,
        360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -8,
          360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -424,
        136
      ],
      "raw_nearest": [
        -424,
        136
      ],
      "viable_nearest": [
        -424,
        136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -424,
          136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        232,
        -424
      ],
      "raw_nearest": [
        232,
        -424
      ],
      "viable_nearest": [
        232,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        584,
        728
      ],
      "raw_nearest": [
        584,
        728
      ],
      "viable_nearest": [
        584,
        728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          584,
          728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -360,
        552
      ],
      "raw_nearest": [
        -360,
        552
      ],
      "viable_nearest": [
        -360,
        552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -360,
          552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -744,
        184
      ],
      "raw_nearest": [
        -744,
        184
      ],
      "viable_nearest": [
        -744,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -744,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        536,
        -152
      ],
      "raw_nearest": [
        536,
        -152
      ],
      "viable_nearest": [
        536,
        -152
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          536,
          -152
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        760,
        -168
      ],
      "raw_nearest": [
        760,
        -168
      ],
      "viable_nearest": [
        760,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          760,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        1032,
        104
      ],
      "raw_nearest": [
        1032,
        104
      ],
      "viable_nearest": [
        1032,
        104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1032,
          104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        1272,
        56
      ],
      "raw_nearest": [
        1272,
        56
      ],
      "viable_nearest": [
        1272,
        56
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1272,
          56
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        888,
        312
      ],
      "raw_nearest": [
        888,
        312
      ],
      "viable_nearest": [
        888,
        312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          888,
          312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        936,
        312
      ],
      "raw_nearest": [
        936,
        312
      ],
      "viable_nearest": [
        936,
        312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          936,
          312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        632,
        840
      ],
      "raw_nearest": [
        632,
        840
      ],
      "viable_nearest": [
        632,
        840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          632,
          840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -664,
        616
      ],
      "raw_nearest": [
        -664,
        616
      ],
      "viable_nearest": [
        -664,
        616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -664,
          616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -872,
        120
      ],
      "raw_nearest": [
        -872,
        120
      ],
      "viable_nearest": [
        -872,
        120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -872,
          120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -904,
        88
      ],
      "raw_nearest": [
        -904,
        88
      ],
      "viable_nearest": [
        -904,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -904,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -648,
        -56
      ],
      "raw_nearest": [
        -648,
        -56
      ],
      "viable_nearest": [
        -648,
        -56
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -648,
          -56
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "mineshaft",
      "marker": [
        -600,
        -424
      ],
      "raw_nearest": [
        -600,
        -424
      ],
      "viable_nearest": [
        -600,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -600,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -1848,
        1608
      ],
      "raw_nearest": [
        -1848,
        1608
      ],
      "viable_nearest": [
        -1848,
        1608
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1848,
          1608
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -2216,
        2072
      ],
      "raw_nearest": [
        -2216,
        2072
      ],
      "viable_nearest": [
        -2216,
        2072
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2216,
          2072
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -264,
        -3288
      ],
      "raw_nearest": [
        -264,
        -3288
      ],
      "viable_nearest": [
        -264,
        -3288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -264,
          -3288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -2984,
        2440
      ],
      "raw_nearest": [
        -2984,
        2440
      ],
      "viable_nearest": [
        -2984,
        2440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2984,
          2440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -2200,
        -2968
      ],
      "raw_nearest": [
        -2200,
        -2968
      ],
      "viable_nearest": [
        -2200,
        -2968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2200,
          -2968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        824,
        3960
      ],
      "raw_nearest": [
        824,
        3960
      ],
      "viable_nearest": [
        824,
        3960
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          824,
          3960
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -4024,
        104
      ],
      "raw_nearest": [
        -4024,
        104
      ],
      "viable_nearest": [
        -4024,
        104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4024,
          104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -3800,
        -328
      ],
      "raw_nearest": [
        -3800,
        -328
      ],
      "viable_nearest": [
        -3800,
        -328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3800,
          -328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -2184,
        -3320
      ],
      "raw_nearest": [
        -2184,
        -3320
      ],
      "viable_nearest": [
        -2184,
        -3320
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2184,
          -3320
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -3048,
        3256
      ],
      "raw_nearest": [
        -3048,
        3256
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -4088,
        -600
      ],
      "raw_nearest": [
        -4088,
        -600
      ],
      "viable_nearest": [
        -4088,
        -600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4088,
          -600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -2920,
        -2616
      ],
      "raw_nearest": [
        -2920,
        -2616
      ],
      "viable_nearest": [
        -2920,
        -2616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2920,
          -2616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -4184,
        -296
      ],
      "raw_nearest": [
        -4184,
        -296
      ],
      "viable_nearest": [
        -4184,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4184,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -1816,
        -4104
      ],
      "raw_nearest": [
        -1816,
        -4104
      ],
      "viable_nearest": [
        -1816,
        -4104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1816,
          -4104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        4728,
        -200
      ],
      "raw_nearest": [
        4728,
        -200
      ],
      "viable_nearest": [
        4728,
        -200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4728,
          -200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -2104,
        -4136
      ],
      "raw_nearest": [
        -2104,
        -4136
      ],
      "viable_nearest": [
        -2104,
        -4136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2104,
          -4136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        5064,
        -1032
      ],
      "raw_nearest": [
        5064,
        -1032
      ],
      "viable_nearest": [
        5064,
        -1032
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5064,
          -1032
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        5032,
        -248
      ],
      "raw_nearest": [
        5032,
        -248
      ],
      "viable_nearest": [
        5032,
        -248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5032,
          -248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        -1800,
        -4888
      ],
      "raw_nearest": [
        -1800,
        -4888
      ],
      "viable_nearest": [
        -1800,
        -4888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1800,
          -4888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ancient_city",
      "marker": [
        5528,
        -1464
      ],
      "raw_nearest": [
        5528,
        -1464
      ],
      "viable_nearest": [
        5528,
        -1464
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5528,
          -1464
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        712,
        664
      ],
      "raw_nearest": [
        712,
        664
      ],
      "viable_nearest": [
        712,
        664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          712,
          664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1224,
        56
      ],
      "raw_nearest": [
        1224,
        56
      ],
      "viable_nearest": [
        1224,
        56
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1224,
          56
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1144,
        -440
      ],
      "raw_nearest": [
        1144,
        -440
      ],
      "viable_nearest": [
        1144,
        -440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1144,
          -440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1352,
        648
      ],
      "raw_nearest": [
        1352,
        648
      ],
      "viable_nearest": [
        1352,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1352,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1176,
        1160
      ],
      "raw_nearest": [
        1176,
        1160
      ],
      "viable_nearest": [
        1176,
        1160
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1176,
          1160
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1352,
        -936
      ],
      "raw_nearest": [
        1352,
        -936
      ],
      "viable_nearest": [
        1352,
        -936
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1352,
          -936
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1880,
        264
      ],
      "raw_nearest": [
        1880,
        264
      ],
      "viable_nearest": [
        1880,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1880,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1992,
        712
      ],
      "raw_nearest": [
        1992,
        712
      ],
      "viable_nearest": [
        1992,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1992,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        -2040,
        152
      ],
      "raw_nearest": [
        -2040,
        152
      ],
      "viable_nearest": [
        -2040,
        152
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2040,
          152
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        -1352,
        -920
      ],
      "raw_nearest": [
        -1352,
        -920
      ],
      "viable_nearest": [
        -1352,
        -920
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1352,
          -920
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1896,
        -760
      ],
      "raw_nearest": [
        1896,
        -760
      ],
      "viable_nearest": [
        1896,
        -760
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1896,
          -760
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1864,
        -392
      ],
      "raw_nearest": [
        1864,
        -392
      ],
      "viable_nearest": [
        1864,
        -392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1864,
          -392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        2408,
        248
      ],
      "raw_nearest": [
        2408,
        248
      ],
      "viable_nearest": [
        2408,
        248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2408,
          248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1384,
        1992
      ],
      "raw_nearest": [
        1384,
        1992
      ],
      "viable_nearest": [
        1384,
        1992
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1384,
          1992
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        -2040,
        584
      ],
      "raw_nearest": [
        -2040,
        584
      ],
      "viable_nearest": [
        -2040,
        584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2040,
          584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        -1832,
        -312
      ],
      "raw_nearest": [
        -1832,
        -312
      ],
      "viable_nearest": [
        -1832,
        -312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1832,
          -312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        -1800,
        -1000
      ],
      "raw_nearest": [
        -1800,
        -1000
      ],
      "viable_nearest": [
        -1800,
        -1000
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1800,
          -1000
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        -1384,
        -1400
      ],
      "raw_nearest": [
        -1384,
        -1400
      ],
      "viable_nearest": [
        -1384,
        -1400
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1384,
          -1400
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        2312,
        840
      ],
      "raw_nearest": [
        2312,
        840
      ],
      "viable_nearest": [
        2312,
        840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2312,
          840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "village",
      "marker": [
        1800,
        1688
      ],
      "raw_nearest": [
        1800,
        1688
      ],
      "viable_nearest": [
        1800,
        1688
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1800,
          1688
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -260,
        340
      ],
      "raw_nearest": [
        -248,
        344
      ],
      "viable_nearest": [
        -248,
        344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -248,
          344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -604,
        -348
      ],
      "raw_nearest": [
        -600,
        -344
      ],
      "viable_nearest": [
        -600,
        -344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -600,
          -344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        19,
        1378
      ],
      "raw_nearest": [
        24,
        1384
      ],
      "viable_nearest": [
        24,
        1384
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          24,
          1384
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        1669,
        189
      ],
      "raw_nearest": [
        1672,
        200
      ],
      "viable_nearest": [
        1672,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1672,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        1285,
        852
      ],
      "raw_nearest": [
        1288,
        856
      ],
      "viable_nearest": [
        1288,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1288,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        712,
        1432
      ],
      "raw_nearest": [
        712,
        1432
      ],
      "viable_nearest": [
        712,
        1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          712,
          1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        324,
        -1220
      ],
      "raw_nearest": [
        328,
        -1208
      ],
      "viable_nearest": [
        328,
        -1208
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          328,
          -1208
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        659,
        -1277
      ],
      "raw_nearest": [
        664,
        -1272
      ],
      "viable_nearest": [
        664,
        -1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          664,
          -1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        2149,
        36
      ],
      "raw_nearest": [
        2152,
        40
      ],
      "viable_nearest": [
        2152,
        40
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          2152,
          40
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        1348,
        1476
      ],
      "raw_nearest": [
        1352,
        1480
      ],
      "viable_nearest": [
        1352,
        1480
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1352,
          1480
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -1060,
        1604
      ],
      "raw_nearest": [
        -1048,
        1608
      ],
      "viable_nearest": [
        -1048,
        1608
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1048,
          1608
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -1572,
        772
      ],
      "raw_nearest": [
        -1560,
        776
      ],
      "viable_nearest": [
        -1560,
        776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1560,
          776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -1700,
        -403
      ],
      "raw_nearest": [
        -1688,
        -392
      ],
      "viable_nearest": [
        -1688,
        -392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1688,
          -392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -542,
        -1629
      ],
      "raw_nearest": [
        -536,
        -1624
      ],
      "viable_nearest": [
        -536,
        -1624
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -536,
          -1624
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        13,
        -1836
      ],
      "raw_nearest": [
        24,
        -1832
      ],
      "viable_nearest": [
        24,
        -1832
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          24,
          -1832
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -537,
        2052
      ],
      "raw_nearest": [
        -536,
        2056
      ],
      "viable_nearest": [
        -536,
        2056
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -536,
          2056
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -1653,
        1429
      ],
      "raw_nearest": [
        -1640,
        1432
      ],
      "viable_nearest": [
        -1640,
        1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1640,
          1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        2556,
        868
      ],
      "raw_nearest": [
        2568,
        872
      ],
      "viable_nearest": [
        2568,
        872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          2568,
          872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        1925,
        1558
      ],
      "raw_nearest": [
        1928,
        1560
      ],
      "viable_nearest": [
        1928,
        1560
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1928,
          1560
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "ruined_portal",
      "marker": [
        -420,
        2644
      ],
      "raw_nearest": [
        -408,
        2648
      ],
      "viable_nearest": [
        -408,
        2648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -408,
          2648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        232,
        88
      ],
      "raw_nearest": [
        232,
        88
      ],
      "viable_nearest": [
        232,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        216,
        -184
      ],
      "raw_nearest": [
        216,
        -184
      ],
      "viable_nearest": [
        216,
        -184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          216,
          -184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -376,
        -168
      ],
      "raw_nearest": [
        -376,
        -168
      ],
      "viable_nearest": [
        -376,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -376,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        56,
        -552
      ],
      "raw_nearest": [
        56,
        -552
      ],
      "viable_nearest": [
        56,
        -552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          56,
          -552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -552,
        472
      ],
      "raw_nearest": [
        -552,
        472
      ],
      "viable_nearest": [
        -552,
        472
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -552,
          472
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -712,
        264
      ],
      "raw_nearest": [
        -712,
        264
      ],
      "viable_nearest": [
        -712,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -712,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -600,
        -232
      ],
      "raw_nearest": [
        -600,
        -232
      ],
      "viable_nearest": [
        -600,
        -232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -600,
          -232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -264,
        -568
      ],
      "raw_nearest": [
        -264,
        -568
      ],
      "viable_nearest": [
        -264,
        -568
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -264,
          -568
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        408,
        1208
      ],
      "raw_nearest": [
        408,
        1208
      ],
      "viable_nearest": [
        408,
        1208
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          1208
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -360,
        1064
      ],
      "raw_nearest": [
        -360,
        1064
      ],
      "viable_nearest": [
        -360,
        1064
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -360,
          1064
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -168,
        1336
      ],
      "raw_nearest": [
        -168,
        1336
      ],
      "viable_nearest": [
        -168,
        1336
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -168,
          1336
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -680,
        1560
      ],
      "raw_nearest": [
        -680,
        1560
      ],
      "viable_nearest": [
        -680,
        1560
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -680,
          1560
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        920,
        -1432
      ],
      "raw_nearest": [
        920,
        -1432
      ],
      "viable_nearest": [
        920,
        -1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          920,
          -1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        200,
        2088
      ],
      "raw_nearest": [
        200,
        2088
      ],
      "viable_nearest": [
        200,
        2088
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          200,
          2088
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        88,
        -2008
      ],
      "raw_nearest": [
        88,
        -2008
      ],
      "viable_nearest": [
        88,
        -2008
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          88,
          -2008
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        904,
        -1784
      ],
      "raw_nearest": [
        904,
        -1784
      ],
      "viable_nearest": [
        904,
        -1784
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          904,
          -1784
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        1080,
        1816
      ],
      "raw_nearest": [
        1080,
        1816
      ],
      "viable_nearest": [
        1080,
        1816
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1080,
          1816
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        56,
        2392
      ],
      "raw_nearest": [
        56,
        2392
      ],
      "viable_nearest": [
        56,
        2392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          56,
          2392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        -568,
        2120
      ],
      "raw_nearest": [
        -568,
        2120
      ],
      "viable_nearest": [
        -568,
        2120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -568,
          2120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "shipwreck",
      "marker": [
        1416,
        -1656
      ],
      "raw_nearest": [
        1416,
        -1656
      ],
      "viable_nearest": [
        1416,
        -1656
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1416,
          -1656
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        104,
        -312
      ],
      "raw_nearest": [
        104,
        -312
      ],
      "viable_nearest": [
        104,
        -312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          104,
          -312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        152,
        -712
      ],
      "raw_nearest": [
        152,
        -712
      ],
      "viable_nearest": [
        152,
        -712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          152,
          -712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        600,
        -1416
      ],
      "raw_nearest": [
        600,
        -1416
      ],
      "viable_nearest": [
        600,
        -1416
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          600,
          -1416
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -1320,
        2856
      ],
      "raw_nearest": [
        -1320,
        2856
      ],
      "viable_nearest": [
        -1320,
        2856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1320,
          2856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -2824,
        -1864
      ],
      "raw_nearest": [
        -2824,
        -1864
      ],
      "viable_nearest": [
        -2824,
        -1864
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2824,
          -1864
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        2728,
        3288
      ],
      "raw_nearest": [
        2728,
        3288
      ],
      "viable_nearest": [
        2728,
        3288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2728,
          3288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        4232,
        1208
      ],
      "raw_nearest": [
        4232,
        1208
      ],
      "viable_nearest": [
        4232,
        1208
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4232,
          1208
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        2232,
        3768
      ],
      "raw_nearest": [
        2232,
        3768
      ],
      "viable_nearest": [
        2232,
        3768
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2232,
          3768
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -4296,
        1336
      ],
      "raw_nearest": [
        -4296,
        1336
      ],
      "viable_nearest": [
        -4296,
        1336
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4296,
          1336
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        1720,
        -4440
      ],
      "raw_nearest": [
        1720,
        -4440
      ],
      "viable_nearest": [
        1720,
        -4440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1720,
          -4440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        4712,
        1848
      ],
      "raw_nearest": [
        4712,
        1848
      ],
      "viable_nearest": [
        4712,
        1848
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4712,
          1848
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        3736,
        3336
      ],
      "raw_nearest": [
        3736,
        3336
      ],
      "viable_nearest": [
        3736,
        3336
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3736,
          3336
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        3864,
        3704
      ],
      "raw_nearest": [
        3864,
        3704
      ],
      "viable_nearest": [
        3864,
        3704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3864,
          3704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -1800,
        4872
      ],
      "raw_nearest": [
        -1800,
        4872
      ],
      "viable_nearest": [
        -1800,
        4872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1800,
          4872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -3176,
        4328
      ],
      "raw_nearest": [
        -3176,
        4328
      ],
      "viable_nearest": [
        -3176,
        4328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3176,
          4328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -3336,
        3848
      ],
      "raw_nearest": [
        -3336,
        3848
      ],
      "viable_nearest": [
        -3336,
        3848
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3336,
          3848
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        2424,
        -4440
      ],
      "raw_nearest": [
        2424,
        -4440
      ],
      "viable_nearest": [
        2424,
        -4440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2424,
          -4440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -2280,
        5320
      ],
      "raw_nearest": [
        -2280,
        5320
      ],
      "viable_nearest": [
        -2280,
        5320
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2280,
          5320
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -3800,
        4344
      ],
      "raw_nearest": [
        -3800,
        4344
      ],
      "viable_nearest": [
        -3800,
        4344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3800,
          4344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "monument",
      "marker": [
        -5368,
        600
      ],
      "raw_nearest": [
        -5368,
        600
      ],
      "viable_nearest": [
        -5368,
        600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5368,
          600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        440,
        744
      ],
      "raw_nearest": [
        432,
        736
      ],
      "viable_nearest": [
        432,
        736
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          432,
          736
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        1704,
        472
      ],
      "raw_nearest": [
        1696,
        464
      ],
      "viable_nearest": [
        1696,
        464
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1696,
          464
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        1656,
        1752
      ],
      "raw_nearest": [
        1648,
        1744
      ],
      "viable_nearest": [
        1648,
        1744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1648,
          1744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        2008,
        -856
      ],
      "raw_nearest": [
        2000,
        -864
      ],
      "viable_nearest": [
        2000,
        -864
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2000,
          -864
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        840,
        3032
      ],
      "raw_nearest": [
        832,
        3024
      ],
      "viable_nearest": [
        832,
        3024
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          832,
          3024
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        2968,
        -792
      ],
      "raw_nearest": [
        2960,
        -800
      ],
      "viable_nearest": [
        2960,
        -800
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2960,
          -800
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        3032,
        1608
      ],
      "raw_nearest": [
        3024,
        1600
      ],
      "viable_nearest": [
        3024,
        1600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3024,
          1600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        792,
        -3224
      ],
      "raw_nearest": [
        784,
        -3232
      ],
      "viable_nearest": [
        784,
        -3232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          784,
          -3232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        -2200,
        3032
      ],
      "raw_nearest": [
        -2208,
        3024
      ],
      "viable_nearest": [
        -2208,
        3024
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -2208,
          3024
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        -3464,
        -712
      ],
      "raw_nearest": [
        -3472,
        -720
      ],
      "viable_nearest": [
        -3472,
        -720
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3472,
          -720
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        -504,
        -3432
      ],
      "raw_nearest": [
        -512,
        -3440
      ],
      "viable_nearest": [
        -512,
        -3440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -512,
          -3440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        3144,
        3048
      ],
      "raw_nearest": [
        3136,
        3040
      ],
      "viable_nearest": [
        3136,
        3040
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3136,
          3040
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        4296,
        2808
      ],
      "raw_nearest": [
        4288,
        2800
      ],
      "viable_nearest": [
        4288,
        2800
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4288,
          2800
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        -4408,
        -872
      ],
      "raw_nearest": [
        -4416,
        -880
      ],
      "viable_nearest": [
        -4416,
        -880
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4416,
          -880
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        2984,
        -3592
      ],
      "raw_nearest": [
        2976,
        -3600
      ],
      "viable_nearest": [
        2976,
        -3600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2976,
          -3600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        -4744,
        424
      ],
      "raw_nearest": [
        -4752,
        416
      ],
      "viable_nearest": [
        -4752,
        416
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4752,
          416
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        -3288,
        -3496
      ],
      "raw_nearest": [
        -3296,
        -3504
      ],
      "viable_nearest": [
        -3296,
        -3504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3296,
          -3504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        2568,
        4632
      ],
      "raw_nearest": [
        2560,
        4624
      ],
      "viable_nearest": [
        2560,
        4624
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2560,
          4624
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        5320,
        -2232
      ],
      "raw_nearest": [
        5312,
        -2240
      ],
      "viable_nearest": [
        5312,
        -2240
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5312,
          -2240
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "outpost",
      "marker": [
        5464,
        1880
      ],
      "raw_nearest": [
        5456,
        1872
      ],
      "viable_nearest": [
        5456,
        1872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5456,
          1872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        379,
        171
      ],
      "raw_nearest": [
        376,
        168
      ],
      "viable_nearest": [
        376,
        168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          376,
          168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        395,
        -245
      ],
      "raw_nearest": [
        392,
        -248
      ],
      "viable_nearest": [
        392,
        -248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          392,
          -248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        667,
        283
      ],
      "raw_nearest": [
        664,
        280
      ],
      "viable_nearest": [
        664,
        280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          664,
          280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        219,
        971
      ],
      "raw_nearest": [
        216,
        968
      ],
      "viable_nearest": [
        216,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          216,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -277,
        -293
      ],
      "raw_nearest": [
        -280,
        -296
      ],
      "viable_nearest": [
        -280,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -280,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        651,
        875
      ],
      "raw_nearest": [
        648,
        872
      ],
      "viable_nearest": [
        648,
        872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          648,
          872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -661,
        283
      ],
      "raw_nearest": [
        -664,
        280
      ],
      "viable_nearest": [
        -664,
        280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -664,
          280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        747,
        -661
      ],
      "raw_nearest": [
        744,
        -664
      ],
      "viable_nearest": [
        744,
        -664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          744,
          -664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        795,
        -405
      ],
      "raw_nearest": [
        792,
        -408
      ],
      "viable_nearest": [
        792,
        -408
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          792,
          -408
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        795,
        1531
      ],
      "raw_nearest": [
        792,
        1528
      ],
      "viable_nearest": [
        792,
        1528
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          792,
          1528
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -1093,
        -325
      ],
      "raw_nearest": [
        -1096,
        -328
      ],
      "viable_nearest": [
        -1096,
        -328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1096,
          -328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -293,
        -1269
      ],
      "raw_nearest": [
        -296,
        -1272
      ],
      "viable_nearest": [
        -296,
        -1272
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -296,
          -1272
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        1963,
        123
      ],
      "raw_nearest": [
        1960,
        120
      ],
      "viable_nearest": [
        1960,
        120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1960,
          120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        1595,
        267
      ],
      "raw_nearest": [
        1592,
        264
      ],
      "viable_nearest": [
        1592,
        264
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1592,
          264
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        1643,
        747
      ],
      "raw_nearest": [
        1640,
        744
      ],
      "viable_nearest": [
        1640,
        744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1640,
          744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -1269,
        1243
      ],
      "raw_nearest": [
        -1272,
        1240
      ],
      "viable_nearest": [
        -1272,
        1240
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1272,
          1240
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -1589,
        187
      ],
      "raw_nearest": [
        -1592,
        184
      ],
      "viable_nearest": [
        -1592,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1592,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        -1077,
        -805
      ],
      "raw_nearest": [
        -1080,
        -808
      ],
      "viable_nearest": [
        -1080,
        -808
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1080,
          -808
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        1515,
        -789
      ],
      "raw_nearest": [
        1512,
        -792
      ],
      "viable_nearest": [
        1512,
        -792
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1512,
          -792
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "fortress",
      "marker": [
        1627,
        1371
      ],
      "raw_nearest": [
        1624,
        1368
      ],
      "viable_nearest": [
        1624,
        1368
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1624,
          1368
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -425,
        185
      ],
      "raw_nearest": [
        -440,
        216
      ],
      "viable_nearest": [
        -440,
        216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -440,
          216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        989,
        82
      ],
      "raw_nearest": [
        1016,
        72
      ],
      "viable_nearest": [
        1016,
        72
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1016,
          72
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -423,
        688
      ],
      "raw_nearest": [
        -408,
        712
      ],
      "viable_nearest": [
        -408,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -408,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        134,
        -646
      ],
      "raw_nearest": [
        120,
        -616
      ],
      "viable_nearest": [
        120,
        -616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          120,
          -616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -14,
        792
      ],
      "raw_nearest": [
        8,
        824
      ],
      "viable_nearest": [
        8,
        824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          8,
          824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -637,
        -205
      ],
      "raw_nearest": [
        -648,
        -216
      ],
      "viable_nearest": [
        -648,
        -216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -648,
          -216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -294,
        -662
      ],
      "raw_nearest": [
        -264,
        -632
      ],
      "viable_nearest": [
        -264,
        -632
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -264,
          -632
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        941,
        -114
      ],
      "raw_nearest": [
        968,
        -88
      ],
      "viable_nearest": [
        968,
        -88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          968,
          -88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        1119,
        648
      ],
      "raw_nearest": [
        1112,
        664
      ],
      "viable_nearest": [
        1112,
        664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1112,
          664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        960,
        1159
      ],
      "raw_nearest": [
        984,
        1160
      ],
      "viable_nearest": [
        984,
        1160
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          984,
          1160
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        97,
        1464
      ],
      "raw_nearest": [
        120,
        1496
      ],
      "viable_nearest": [
        120,
        1496
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          120,
          1496
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -886,
        518
      ],
      "raw_nearest": [
        -856,
        504
      ],
      "viable_nearest": [
        -856,
        504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -856,
          504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -1181,
        173
      ],
      "raw_nearest": [
        -1192,
        200
      ],
      "viable_nearest": [
        -1192,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1192,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -825,
        -678
      ],
      "raw_nearest": [
        -840,
        -648
      ],
      "viable_nearest": [
        -840,
        -648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -840,
          -648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        734,
        1303
      ],
      "raw_nearest": [
        728,
        1288
      ],
      "viable_nearest": [
        728,
        1288
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          728,
          1288
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -765,
        -1213
      ],
      "raw_nearest": [
        -776,
        -1224
      ],
      "viable_nearest": [
        -776,
        -1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -776,
          -1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        239,
        -1447
      ],
      "raw_nearest": [
        232,
        -1432
      ],
      "viable_nearest": [
        232,
        -1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          232,
          -1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        226,
        -1501
      ],
      "raw_nearest": [
        216,
        -1512
      ],
      "viable_nearest": [
        216,
        -1512
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          216,
          -1512
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        1246,
        -808
      ],
      "raw_nearest": [
        1240,
        -824
      ],
      "viable_nearest": [
        1240,
        -824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1240,
          -824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "-1",
      "type": "bastion",
      "marker": [
        -130,
        1661
      ],
      "raw_nearest": [
        -104,
        1688
      ],
      "viable_nearest": [
        -104,
        1688
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -104,
          1688
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        311,
        87
      ],
      "raw_nearest": [
        328,
        104
      ],
      "viable_nearest": [
        328,
        104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          328,
          104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -247,
        279
      ],
      "raw_nearest": [
        -248,
        296
      ],
      "viable_nearest": [
        -248,
        296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -248,
          296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        777,
        73
      ],
      "raw_nearest": [
        776,
        72
      ],
      "viable_nearest": [
        776,
        72
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          776,
          72
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        745,
        553
      ],
      "raw_nearest": [
        744,
        552
      ],
      "viable_nearest": [
        744,
        552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          744,
          552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -263,
        535
      ],
      "raw_nearest": [
        -264,
        552
      ],
      "viable_nearest": [
        -264,
        552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -264,
          552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -761,
        249
      ],
      "raw_nearest": [
        -744,
        248
      ],
      "viable_nearest": [
        -744,
        248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -744,
          248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -375,
        -313
      ],
      "raw_nearest": [
        -376,
        -296
      ],
      "viable_nearest": [
        -376,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -376,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        265,
        -505
      ],
      "raw_nearest": [
        264,
        -488
      ],
      "viable_nearest": [
        264,
        -488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          264,
          -488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        743,
        -473
      ],
      "raw_nearest": [
        760,
        -456
      ],
      "viable_nearest": [
        760,
        -456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          760,
          -456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        263,
        793
      ],
      "raw_nearest": [
        280,
        792
      ],
      "viable_nearest": [
        280,
        792
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          280,
          792
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        1367,
        231
      ],
      "raw_nearest": [
        1384,
        248
      ],
      "viable_nearest": [
        1384,
        248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1384,
          248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        311,
        1113
      ],
      "raw_nearest": [
        328,
        1112
      ],
      "viable_nearest": [
        328,
        1112
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          328,
          1112
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -345,
        1127
      ],
      "raw_nearest": [
        -328,
        1144
      ],
      "viable_nearest": [
        -328,
        1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -328,
          1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -921,
        -455
      ],
      "raw_nearest": [
        -904,
        -456
      ],
      "viable_nearest": [
        -904,
        -456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -904,
          -456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -471,
        -793
      ],
      "raw_nearest": [
        -472,
        -776
      ],
      "viable_nearest": [
        -472,
        -776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -472,
          -776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        793,
        -999
      ],
      "raw_nearest": [
        792,
        -1000
      ],
      "viable_nearest": [
        792,
        -1000
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          792,
          -1000
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        1321,
        615
      ],
      "raw_nearest": [
        1320,
        632
      ],
      "viable_nearest": [
        1320,
        632
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          1320,
          632
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        681,
        1385
      ],
      "raw_nearest": [
        680,
        1384
      ],
      "viable_nearest": [
        680,
        1384
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          680,
          1384
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        89,
        1641
      ],
      "raw_nearest": [
        88,
        1640
      ],
      "viable_nearest": [
        88,
        1640
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          88,
          1640
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "trial_chamber",
      "marker": [
        -1033,
        759
      ],
      "raw_nearest": [
        -1016,
        776
      ],
      "viable_nearest": [
        -1016,
        776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_room_marker",
      "diagnostic_radius": 25,
      "possible_starts": [
        [
          -1016,
          776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        740,
        308
      ],
      "raw_nearest": [
        740,
        308
      ],
      "viable_nearest": [
        740,
        308
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          740,
          308
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -1980,
        1252
      ],
      "raw_nearest": [
        -1980,
        1252
      ],
      "viable_nearest": [
        -1980,
        1252
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1980,
          1252
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        2308,
        -316
      ],
      "raw_nearest": [
        2308,
        -316
      ],
      "viable_nearest": [
        2308,
        -316
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2308,
          -316
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -1212,
        4372
      ],
      "raw_nearest": [
        -1212,
        4372
      ],
      "viable_nearest": [
        -1212,
        4372
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1212,
          4372
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -1116,
        -5324
      ],
      "raw_nearest": [
        -1116,
        -5324
      ],
      "viable_nearest": [
        -1116,
        -5324
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1116,
          -5324
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        5092,
        -4092
      ],
      "raw_nearest": [
        5092,
        -4092
      ],
      "viable_nearest": [
        5092,
        -4092
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5092,
          -4092
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        7588,
        1572
      ],
      "raw_nearest": [
        7588,
        1572
      ],
      "viable_nearest": [
        7588,
        1572
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          7588,
          1572
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        1940,
        7604
      ],
      "raw_nearest": [
        1940,
        7604
      ],
      "viable_nearest": [
        1940,
        7604
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1940,
          7604
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -5132,
        5524
      ],
      "raw_nearest": [
        -5132,
        5524
      ],
      "viable_nearest": [
        -5132,
        5524
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -5132,
          5524
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -7564,
        -1500
      ],
      "raw_nearest": [
        -7564,
        -1500
      ],
      "viable_nearest": [
        -7564,
        -1500
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7564,
          -1500
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -7836,
        1188
      ],
      "raw_nearest": [
        -7836,
        1188
      ],
      "viable_nearest": [
        -7836,
        1188
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7836,
          1188
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -828,
        -7772
      ],
      "raw_nearest": [
        -828,
        -7772
      ],
      "viable_nearest": [
        -828,
        -7772
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -828,
          -7772
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        7572,
        4404
      ],
      "raw_nearest": [
        7572,
        4404
      ],
      "viable_nearest": [
        7572,
        4404
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          7572,
          4404
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        2260,
        -10940
      ],
      "raw_nearest": [
        2260,
        -10940
      ],
      "viable_nearest": [
        2260,
        -10940
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2260,
          -10940
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -11196,
        -4332
      ],
      "raw_nearest": [
        -11196,
        -4332
      ],
      "viable_nearest": [
        -11196,
        -4332
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -11196,
          -4332
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -11612,
        4804
      ],
      "raw_nearest": [
        -11612,
        4804
      ],
      "viable_nearest": [
        -11612,
        4804
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -11612,
          4804
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        11972,
        -4588
      ],
      "raw_nearest": [
        11972,
        -4588
      ],
      "viable_nearest": [
        11972,
        -4588
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          11972,
          -4588
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        4900,
        -11884
      ],
      "raw_nearest": [
        4900,
        -11884
      ],
      "viable_nearest": [
        4900,
        -11884
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4900,
          -11884
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -7404,
        -10540
      ],
      "raw_nearest": [
        -7404,
        -10540
      ],
      "viable_nearest": [
        -7404,
        -10540
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -7404,
          -10540
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "stronghold",
      "marker": [
        -11388,
        8372
      ],
      "raw_nearest": [
        -11388,
        8372
      ],
      "viable_nearest": [
        -11388,
        8372
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -11388,
          8372
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        408,
        216
      ],
      "raw_nearest": [
        408,
        216
      ],
      "viable_nearest": [
        408,
        216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        -216,
        184
      ],
      "raw_nearest": [
        -216,
        184
      ],
      "viable_nearest": [
        -216,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -216,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        232,
        -168
      ],
      "raw_nearest": [
        232,
        -168
      ],
      "viable_nearest": [
        232,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          232,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        632,
        200
      ],
      "raw_nearest": [
        632,
        200
      ],
      "viable_nearest": [
        632,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          632,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        424,
        296
      ],
      "raw_nearest": [
        424,
        296
      ],
      "viable_nearest": [
        424,
        296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          424,
          296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        504,
        392
      ],
      "raw_nearest": [
        504,
        392
      ],
      "viable_nearest": [
        504,
        392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          504,
          392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        8,
        536
      ],
      "raw_nearest": [
        8,
        536
      ],
      "viable_nearest": [
        8,
        536
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8,
          536
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        408,
        -136
      ],
      "raw_nearest": [
        408,
        -136
      ],
      "viable_nearest": [
        408,
        -136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          408,
          -136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        824,
        40
      ],
      "raw_nearest": [
        824,
        40
      ],
      "viable_nearest": [
        824,
        40
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          824,
          40
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        584,
        584
      ],
      "raw_nearest": [
        584,
        584
      ],
      "viable_nearest": [
        584,
        584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          584,
          584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        744,
        632
      ],
      "raw_nearest": [
        744,
        632
      ],
      "viable_nearest": [
        744,
        632
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          744,
          632
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        472,
        648
      ],
      "raw_nearest": [
        472,
        648
      ],
      "viable_nearest": [
        472,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          472,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        -8,
        648
      ],
      "raw_nearest": [
        -8,
        648
      ],
      "viable_nearest": [
        -8,
        648
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -8,
          648
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        -40,
        664
      ],
      "raw_nearest": [
        -40,
        664
      ],
      "viable_nearest": [
        -40,
        664
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -40,
          664
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        -488,
        712
      ],
      "raw_nearest": [
        -488,
        712
      ],
      "viable_nearest": [
        -488,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -488,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        -232,
        -296
      ],
      "raw_nearest": [
        -232,
        -296
      ],
      "viable_nearest": [
        -232,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -232,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        24,
        -584
      ],
      "raw_nearest": [
        24,
        -584
      ],
      "viable_nearest": [
        24,
        -584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          24,
          -584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        808,
        440
      ],
      "raw_nearest": [
        808,
        440
      ],
      "viable_nearest": [
        808,
        440
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          808,
          440
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        984,
        520
      ],
      "raw_nearest": [
        984,
        520
      ],
      "viable_nearest": [
        984,
        520
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          984,
          520
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "mineshaft",
      "marker": [
        984,
        552
      ],
      "raw_nearest": [
        984,
        552
      ],
      "viable_nearest": [
        984,
        552
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          984,
          552
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -1096,
        1992
      ],
      "raw_nearest": [
        -1096,
        1992
      ],
      "viable_nearest": [
        -1096,
        1992
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1096,
          1992
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -2552,
        200
      ],
      "raw_nearest": [
        -2552,
        200
      ],
      "viable_nearest": [
        -2552,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2552,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        840,
        -2152
      ],
      "raw_nearest": [
        840,
        -2152
      ],
      "viable_nearest": [
        840,
        -2152
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          840,
          -2152
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        1224,
        2808
      ],
      "raw_nearest": [
        1224,
        2808
      ],
      "viable_nearest": [
        1224,
        2808
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1224,
          2808
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        72,
        2856
      ],
      "raw_nearest": [
        72,
        2856
      ],
      "viable_nearest": [
        72,
        2856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          72,
          2856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -2968,
        -616
      ],
      "raw_nearest": [
        -2968,
        -616
      ],
      "viable_nearest": [
        -2968,
        -616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2968,
          -616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        1576,
        3256
      ],
      "raw_nearest": [
        1576,
        3256
      ],
      "viable_nearest": [
        1576,
        3256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1576,
          3256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        968,
        3608
      ],
      "raw_nearest": [
        968,
        3608
      ],
      "viable_nearest": [
        968,
        3608
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          968,
          3608
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -3336,
        536
      ],
      "raw_nearest": [
        -3336,
        536
      ],
      "viable_nearest": [
        -3336,
        536
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3336,
          536
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        120,
        -3672
      ],
      "raw_nearest": [
        120,
        -3672
      ],
      "viable_nearest": [
        120,
        -3672
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          120,
          -3672
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -696,
        -3656
      ],
      "raw_nearest": [
        -696,
        -3656
      ],
      "viable_nearest": [
        -696,
        -3656
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -696,
          -3656
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -984,
        4808
      ],
      "raw_nearest": [
        -984,
        4808
      ],
      "viable_nearest": [
        -984,
        4808
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -984,
          4808
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        4296,
        2872
      ],
      "raw_nearest": [
        4296,
        2872
      ],
      "viable_nearest": [
        4296,
        2872
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4296,
          2872
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -1048,
        5176
      ],
      "raw_nearest": [
        -1048,
        5176
      ],
      "viable_nearest": [
        -1048,
        5176
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1048,
          5176
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -1000,
        -4968
      ],
      "raw_nearest": [
        -1000,
        -4968
      ],
      "viable_nearest": [
        -1000,
        -4968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1000,
          -4968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        5496,
        2840
      ],
      "raw_nearest": [
        5496,
        2840
      ],
      "viable_nearest": [
        5496,
        2840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5496,
          2840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        88,
        6216
      ],
      "raw_nearest": [
        88,
        6216
      ],
      "viable_nearest": [
        88,
        6216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          88,
          6216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        2824,
        -5320
      ],
      "raw_nearest": [
        2824,
        -5320
      ],
      "viable_nearest": [
        2824,
        -5320
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2824,
          -5320
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        3608,
        5160
      ],
      "raw_nearest": [
        3608,
        5160
      ],
      "viable_nearest": [
        3608,
        5160
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3608,
          5160
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ancient_city",
      "marker": [
        -680,
        6216
      ],
      "raw_nearest": [
        -680,
        6216
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        168,
        88
      ],
      "raw_nearest": [
        168,
        88
      ],
      "viable_nearest": [
        168,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          168,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        744,
        312
      ],
      "raw_nearest": [
        744,
        312
      ],
      "viable_nearest": [
        744,
        312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          744,
          312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -392,
        1224
      ],
      "raw_nearest": [
        -392,
        1224
      ],
      "viable_nearest": [
        -392,
        1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -392,
          1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        1448,
        712
      ],
      "raw_nearest": [
        1448,
        712
      ],
      "viable_nearest": [
        1448,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1448,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -1288,
        -408
      ],
      "raw_nearest": [
        -1288,
        -408
      ],
      "viable_nearest": [
        -1288,
        -408
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1288,
          -408
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        1896,
        856
      ],
      "raw_nearest": [
        1896,
        856
      ],
      "viable_nearest": [
        1896,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1896,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        712,
        1992
      ],
      "raw_nearest": [
        712,
        1992
      ],
      "viable_nearest": [
        712,
        1992
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          712,
          1992
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -936,
        1688
      ],
      "raw_nearest": [
        -936,
        1688
      ],
      "viable_nearest": [
        -936,
        1688
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -936,
          1688
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -1416,
        1240
      ],
      "raw_nearest": [
        -1416,
        1240
      ],
      "viable_nearest": [
        -1416,
        1240
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1416,
          1240
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        1160,
        -1528
      ],
      "raw_nearest": [
        1160,
        -1528
      ],
      "viable_nearest": [
        1160,
        -1528
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1160,
          -1528
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        2376,
        184
      ],
      "raw_nearest": [
        2376,
        184
      ],
      "viable_nearest": [
        2376,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2376,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        760,
        2216
      ],
      "raw_nearest": [
        760,
        2216
      ],
      "viable_nearest": [
        760,
        2216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          760,
          2216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -1976,
        1256
      ],
      "raw_nearest": [
        -1976,
        1256
      ],
      "viable_nearest": [
        -1976,
        1256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1976,
          1256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -1912,
        712
      ],
      "raw_nearest": [
        -1912,
        712
      ],
      "viable_nearest": [
        -1912,
        712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1912,
          712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        1944,
        1928
      ],
      "raw_nearest": [
        1944,
        1928
      ],
      "viable_nearest": [
        1944,
        1928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1944,
          1928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        -2392,
        168
      ],
      "raw_nearest": [
        -2392,
        168
      ],
      "viable_nearest": [
        -2392,
        168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2392,
          168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        1320,
        -1928
      ],
      "raw_nearest": [
        1320,
        -1928
      ],
      "viable_nearest": [
        1320,
        -1928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1320,
          -1928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        2312,
        -312
      ],
      "raw_nearest": [
        2312,
        -312
      ],
      "viable_nearest": [
        2312,
        -312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2312,
          -312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        2888,
        200
      ],
      "raw_nearest": [
        2888,
        200
      ],
      "viable_nearest": [
        2888,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2888,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "village",
      "marker": [
        2296,
        1880
      ],
      "raw_nearest": [
        2296,
        1880
      ],
      "viable_nearest": [
        2296,
        1880
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2296,
          1880
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        108,
        100
      ],
      "raw_nearest": [
        120,
        104
      ],
      "viable_nearest": [
        120,
        104
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          120,
          104
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -488,
        11
      ],
      "raw_nearest": [
        -488,
        24
      ],
      "viable_nearest": [
        -488,
        24
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -488,
          24
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        964,
        84
      ],
      "raw_nearest": [
        968,
        88
      ],
      "viable_nearest": [
        968,
        88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          968,
          88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -7,
        965
      ],
      "raw_nearest": [
        8,
        968
      ],
      "viable_nearest": [
        8,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          8,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        979,
        1011
      ],
      "raw_nearest": [
        984,
        1016
      ],
      "viable_nearest": [
        984,
        1016
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          984,
          1016
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        235,
        1340
      ],
      "raw_nearest": [
        248,
        1352
      ],
      "viable_nearest": [
        248,
        1352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          248,
          1352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        313,
        -901
      ],
      "raw_nearest": [
        328,
        -888
      ],
      "viable_nearest": [
        328,
        -888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          328,
          -888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        1428,
        956
      ],
      "raw_nearest": [
        1432,
        968
      ],
      "viable_nearest": [
        1432,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1432,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -1114,
        -299
      ],
      "raw_nearest": [
        -1112,
        -296
      ],
      "viable_nearest": [
        -1112,
        -296
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1112,
          -296
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -572,
        -1076
      ],
      "raw_nearest": [
        -568,
        -1064
      ],
      "viable_nearest": [
        -568,
        -1064
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -568,
          -1064
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        1412,
        -996
      ],
      "raw_nearest": [
        1416,
        -984
      ],
      "viable_nearest": [
        1416,
        -984
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1416,
          -984
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        908,
        1924
      ],
      "raw_nearest": [
        920,
        1928
      ],
      "viable_nearest": [
        920,
        1928
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          920,
          1928
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -1732,
        371
      ],
      "raw_nearest": [
        -1720,
        376
      ],
      "viable_nearest": [
        -1720,
        376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1720,
          376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -1256,
        -1147
      ],
      "raw_nearest": [
        -1256,
        -1144
      ],
      "viable_nearest": [
        -1256,
        -1144
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -1256,
          -1144
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -444,
        2084
      ],
      "raw_nearest": [
        -440,
        2088
      ],
      "viable_nearest": [
        -440,
        2088
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -440,
          2088
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        2019,
        -1230
      ],
      "raw_nearest": [
        2024,
        -1224
      ],
      "viable_nearest": [
        2024,
        -1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          2024,
          -1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        1318,
        2133
      ],
      "raw_nearest": [
        1320,
        2136
      ],
      "viable_nearest": [
        1320,
        2136
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          1320,
          2136
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        156,
        2714
      ],
      "raw_nearest": [
        168,
        2728
      ],
      "viable_nearest": [
        168,
        2728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          168,
          2728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        -2267,
        876
      ],
      "raw_nearest": [
        -2264,
        888
      ],
      "viable_nearest": [
        -2264,
        888
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          -2264,
          888
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "ruined_portal",
      "marker": [
        164,
        -2363
      ],
      "raw_nearest": [
        168,
        -2360
      ],
      "viable_nearest": [
        168,
        -2360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_portal_marker",
      "diagnostic_radius": 21,
      "possible_starts": [
        [
          168,
          -2360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        680,
        184
      ],
      "raw_nearest": [
        680,
        184
      ],
      "viable_nearest": [
        680,
        184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          680,
          184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        312,
        -88
      ],
      "raw_nearest": [
        312,
        -88
      ],
      "viable_nearest": [
        312,
        -88
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          312,
          -88
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        952,
        200
      ],
      "raw_nearest": [
        952,
        200
      ],
      "viable_nearest": [
        952,
        200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          952,
          200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        696,
        -376
      ],
      "raw_nearest": [
        696,
        -376
      ],
      "viable_nearest": [
        696,
        -376
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          696,
          -376
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1464,
        216
      ],
      "raw_nearest": [
        1464,
        216
      ],
      "viable_nearest": [
        1464,
        216
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1464,
          216
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        792,
        792
      ],
      "raw_nearest": [
        792,
        792
      ],
      "viable_nearest": [
        792,
        792
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          792,
          792
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        984,
        -984
      ],
      "raw_nearest": [
        984,
        -984
      ],
      "viable_nearest": [
        984,
        -984
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          984,
          -984
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1000,
        -712
      ],
      "raw_nearest": [
        1000,
        -712
      ],
      "viable_nearest": [
        1000,
        -712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1000,
          -712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1048,
        -312
      ],
      "raw_nearest": [
        1048,
        -312
      ],
      "viable_nearest": [
        1048,
        -312
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1048,
          -312
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1176,
        -328
      ],
      "raw_nearest": [
        1176,
        -328
      ],
      "viable_nearest": [
        1176,
        -328
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1176,
          -328
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1768,
        168
      ],
      "raw_nearest": [
        1768,
        168
      ],
      "viable_nearest": [
        1768,
        168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1768,
          168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1336,
        424
      ],
      "raw_nearest": [
        1336,
        424
      ],
      "viable_nearest": [
        1336,
        424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1336,
          424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        520,
        1368
      ],
      "raw_nearest": [
        520,
        1368
      ],
      "viable_nearest": [
        520,
        1368
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          520,
          1368
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        8,
        1576
      ],
      "raw_nearest": [
        8,
        1576
      ],
      "viable_nearest": [
        8,
        1576
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          8,
          1576
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        -968,
        1160
      ],
      "raw_nearest": [
        -968,
        1160
      ],
      "viable_nearest": [
        -968,
        1160
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -968,
          1160
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1592,
        616
      ],
      "raw_nearest": [
        1592,
        616
      ],
      "viable_nearest": [
        1592,
        616
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1592,
          616
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        -1528,
        600
      ],
      "raw_nearest": [
        -1528,
        600
      ],
      "viable_nearest": [
        -1528,
        600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1528,
          600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        -1448,
        -248
      ],
      "raw_nearest": [
        -1448,
        -248
      ],
      "viable_nearest": [
        -1448,
        -248
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1448,
          -248
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        -88,
        -1368
      ],
      "raw_nearest": [
        -88,
        -1368
      ],
      "viable_nearest": [
        -88,
        -1368
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -88,
          -1368
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "shipwreck",
      "marker": [
        1192,
        -1240
      ],
      "raw_nearest": [
        1192,
        -1240
      ],
      "viable_nearest": [
        1192,
        -1240
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1192,
          -1240
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        824,
        -360
      ],
      "raw_nearest": [
        824,
        -360
      ],
      "viable_nearest": [
        824,
        -360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          824,
          -360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        1304,
        -280
      ],
      "raw_nearest": [
        1304,
        -280
      ],
      "viable_nearest": [
        1304,
        -280
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          1304,
          -280
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -1160,
        -1352
      ],
      "raw_nearest": [
        -1160,
        -1352
      ],
      "viable_nearest": [
        -1160,
        -1352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1160,
          -1352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -1928,
        -344
      ],
      "raw_nearest": [
        -1928,
        -344
      ],
      "viable_nearest": [
        -1928,
        -344
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1928,
          -344
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -1672,
        -1368
      ],
      "raw_nearest": [
        -1672,
        -1368
      ],
      "viable_nearest": [
        -1672,
        -1368
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1672,
          -1368
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -1880,
        -1784
      ],
      "raw_nearest": [
        -1880,
        -1784
      ],
      "viable_nearest": [
        -1880,
        -1784
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -1880,
          -1784
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -2344,
        -1656
      ],
      "raw_nearest": [
        -2344,
        -1656
      ],
      "viable_nearest": [
        -2344,
        -1656
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2344,
          -1656
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -2472,
        2712
      ],
      "raw_nearest": [
        -2472,
        2712
      ],
      "viable_nearest": [
        -2472,
        2712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2472,
          2712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -904,
        -4200
      ],
      "raw_nearest": [
        -904,
        -4200
      ],
      "viable_nearest": [
        -904,
        -4200
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -904,
          -4200
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        3256,
        3880
      ],
      "raw_nearest": [
        3256,
        3880
      ],
      "viable_nearest": [
        3256,
        3880
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3256,
          3880
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        2824,
        4232
      ],
      "raw_nearest": [
        2824,
        4232
      ],
      "viable_nearest": [
        2824,
        4232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          2824,
          4232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -3912,
        3224
      ],
      "raw_nearest": [
        -3912,
        3224
      ],
      "viable_nearest": [
        -3912,
        3224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3912,
          3224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -3768,
        -2840
      ],
      "raw_nearest": [
        -3768,
        -2840
      ],
      "viable_nearest": [
        -3768,
        -2840
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -3768,
          -2840
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        3160,
        4392
      ],
      "raw_nearest": [
        3160,
        4392
      ],
      "viable_nearest": [
        3160,
        4392
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          3160,
          4392
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        4904,
        -1752
      ],
      "raw_nearest": [
        4904,
        -1752
      ],
      "viable_nearest": [
        4904,
        -1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4904,
          -1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        5304,
        -1352
      ],
      "raw_nearest": [
        5304,
        -1352
      ],
      "viable_nearest": [
        5304,
        -1352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          5304,
          -1352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        4200,
        3800
      ],
      "raw_nearest": [
        4200,
        3800
      ],
      "viable_nearest": [
        4200,
        3800
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          4200,
          3800
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -4408,
        3240
      ],
      "raw_nearest": [
        -4408,
        3240
      ],
      "viable_nearest": [
        -4408,
        3240
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4408,
          3240
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -4456,
        2856
      ],
      "raw_nearest": [
        -4456,
        2856
      ],
      "viable_nearest": [
        -4456,
        2856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -4456,
          2856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "monument",
      "marker": [
        -2280,
        -4904
      ],
      "raw_nearest": [
        -2280,
        -4904
      ],
      "viable_nearest": [
        -2280,
        -4904
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "exact",
      "diagnostic_radius": 0,
      "possible_starts": [
        [
          -2280,
          -4904
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        1784,
        632
      ],
      "raw_nearest": [
        1776,
        624
      ],
      "viable_nearest": [
        1776,
        624
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1776,
          624
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -904,
        1464
      ],
      "raw_nearest": [
        -912,
        1456
      ],
      "viable_nearest": [
        -912,
        1456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -912,
          1456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -1992,
        408
      ],
      "raw_nearest": [
        -2000,
        400
      ],
      "viable_nearest": [
        -2000,
        400
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -2000,
          400
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -2008,
        1784
      ],
      "raw_nearest": [
        -2016,
        1776
      ],
      "viable_nearest": [
        -2016,
        1776
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -2016,
          1776
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        3000,
        424
      ],
      "raw_nearest": [
        2992,
        416
      ],
      "viable_nearest": [
        2992,
        416
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          2992,
          416
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        1736,
        2744
      ],
      "raw_nearest": [
        1728,
        2736
      ],
      "viable_nearest": [
        1728,
        2736
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          1728,
          2736
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -3272,
        1912
      ],
      "raw_nearest": [
        -3280,
        1904
      ],
      "viable_nearest": [
        -3280,
        1904
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3280,
          1904
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -3544,
        264
      ],
      "raw_nearest": [
        -3552,
        256
      ],
      "viable_nearest": [
        -3552,
        256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3552,
          256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        3928,
        728
      ],
      "raw_nearest": [
        3920,
        720
      ],
      "viable_nearest": [
        3920,
        720
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          3920,
          720
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        616,
        -3688
      ],
      "raw_nearest": [
        608,
        -3696
      ],
      "viable_nearest": [
        608,
        -3696
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          608,
          -3696
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        4680,
        1752
      ],
      "raw_nearest": [
        4672,
        1744
      ],
      "viable_nearest": [
        4672,
        1744
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4672,
          1744
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        4296,
        3032
      ],
      "raw_nearest": [
        4288,
        3024
      ],
      "viable_nearest": [
        4288,
        3024
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          4288,
          3024
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -3176,
        -3448
      ],
      "raw_nearest": [
        -3184,
        -3456
      ],
      "viable_nearest": [
        -3184,
        -3456
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3184,
          -3456
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        424,
        -4728
      ],
      "raw_nearest": [
        416,
        -4736
      ],
      "viable_nearest": [
        416,
        -4736
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          416,
          -4736
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -1016,
        5368
      ],
      "raw_nearest": [
        -1024,
        5360
      ],
      "viable_nearest": [
        -1024,
        5360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -1024,
          5360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -3288,
        4472
      ],
      "raw_nearest": [
        -3296,
        4464
      ],
      "viable_nearest": [
        -3296,
        4464
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -3296,
          4464
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        5656,
        360
      ],
      "raw_nearest": [
        5648,
        352
      ],
      "viable_nearest": [
        5648,
        352
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5648,
          352
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        5608,
        1976
      ],
      "raw_nearest": [
        5600,
        1968
      ],
      "viable_nearest": [
        5600,
        1968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5600,
          1968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        5416,
        3192
      ],
      "raw_nearest": [
        5408,
        3184
      ],
      "viable_nearest": [
        5408,
        3184
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          5408,
          3184
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "outpost",
      "marker": [
        -4792,
        4008
      ],
      "raw_nearest": [
        -4800,
        4000
      ],
      "viable_nearest": [
        -4800,
        4000
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 12,
      "possible_starts": [
        [
          -4800,
          4000
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        299,
        -229
      ],
      "raw_nearest": [
        296,
        -232
      ],
      "viable_nearest": [
        296,
        -232
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          296,
          -232
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        587,
        363
      ],
      "raw_nearest": [
        584,
        360
      ],
      "viable_nearest": [
        584,
        360
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          584,
          360
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        651,
        507
      ],
      "raw_nearest": [
        648,
        504
      ],
      "viable_nearest": [
        648,
        504
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          648,
          504
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        75,
        827
      ],
      "raw_nearest": [
        72,
        824
      ],
      "viable_nearest": [
        72,
        824
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          72,
          824
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        491,
        -597
      ],
      "raw_nearest": [
        488,
        -600
      ],
      "viable_nearest": [
        488,
        -600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          488,
          -600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        -277,
        1259
      ],
      "raw_nearest": [
        -280,
        1256
      ],
      "viable_nearest": [
        -280,
        1256
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -280,
          1256
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        -469,
        -853
      ],
      "raw_nearest": [
        -472,
        -856
      ],
      "viable_nearest": [
        -472,
        -856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -472,
          -856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        1195,
        -725
      ],
      "raw_nearest": [
        1192,
        -728
      ],
      "viable_nearest": [
        1192,
        -728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1192,
          -728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        1275,
        -469
      ],
      "raw_nearest": [
        1272,
        -472
      ],
      "viable_nearest": [
        1272,
        -472
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1272,
          -472
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        -565,
        1467
      ],
      "raw_nearest": [
        -568,
        1464
      ],
      "viable_nearest": [
        -568,
        1464
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -568,
          1464
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        1723,
        731
      ],
      "raw_nearest": [
        1720,
        728
      ],
      "viable_nearest": [
        1720,
        728
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1720,
          728
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        -261,
        1707
      ],
      "raw_nearest": [
        -264,
        1704
      ],
      "viable_nearest": [
        -264,
        1704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -264,
          1704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        619,
        -1429
      ],
      "raw_nearest": [
        616,
        -1432
      ],
      "viable_nearest": [
        616,
        -1432
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          616,
          -1432
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        1595,
        1051
      ],
      "raw_nearest": [
        1592,
        1048
      ],
      "viable_nearest": [
        1592,
        1048
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1592,
          1048
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        -149,
        1979
      ],
      "raw_nearest": [
        -152,
        1976
      ],
      "viable_nearest": [
        -152,
        1976
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -152,
          1976
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        811,
        -1701
      ],
      "raw_nearest": [
        808,
        -1704
      ],
      "viable_nearest": [
        808,
        -1704
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          808,
          -1704
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        1563,
        -1093
      ],
      "raw_nearest": [
        1560,
        -1096
      ],
      "viable_nearest": [
        1560,
        -1096
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1560,
          -1096
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        2107,
        491
      ],
      "raw_nearest": [
        2104,
        488
      ],
      "viable_nearest": [
        2104,
        488
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          2104,
          488
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        1547,
        1755
      ],
      "raw_nearest": [
        1544,
        1752
      ],
      "viable_nearest": [
        1544,
        1752
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          1544,
          1752
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "fortress",
      "marker": [
        -1701,
        1307
      ],
      "raw_nearest": [
        -1704,
        1304
      ],
      "viable_nearest": [
        -1704,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "chunk_center_vs_marker",
      "diagnostic_radius": 5,
      "possible_starts": [
        [
          -1704,
          1304
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -418,
        765
      ],
      "raw_nearest": [
        -392,
        792
      ],
      "viable_nearest": [
        -392,
        792
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -392,
          792
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -338,
        -450
      ],
      "raw_nearest": [
        -312,
        -424
      ],
      "viable_nearest": [
        -312,
        -424
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -312,
          -424
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        98,
        -738
      ],
      "raw_nearest": [
        88,
        -712
      ],
      "viable_nearest": [
        88,
        -712
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          88,
          -712
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        369,
        936
      ],
      "raw_nearest": [
        392,
        968
      ],
      "viable_nearest": [
        392,
        968
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          392,
          968
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -537,
        -6
      ],
      "raw_nearest": [
        -552,
        24
      ],
      "viable_nearest": [
        -552,
        24
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -552,
          24
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -669,
        -194
      ],
      "raw_nearest": [
        -680,
        -168
      ],
      "viable_nearest": [
        -680,
        -168
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -680,
          -168
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        1185,
        376
      ],
      "raw_nearest": [
        1208,
        408
      ],
      "viable_nearest": null,
      "raw_rejected": true,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [],
      "status": "missing"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        1248,
        599
      ],
      "raw_nearest": [
        1272,
        600
      ],
      "viable_nearest": [
        1272,
        600
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1272,
          600
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -642,
        829
      ],
      "raw_nearest": [
        -616,
        856
      ],
      "viable_nearest": [
        -616,
        856
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -616,
          856
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        184,
        -1215
      ],
      "raw_nearest": [
        200,
        -1192
      ],
      "viable_nearest": [
        200,
        -1192
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          200,
          -1192
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        1241,
        1238
      ],
      "raw_nearest": [
        1272,
        1224
      ],
      "viable_nearest": [
        1272,
        1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1272,
          1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -914,
        1197
      ],
      "raw_nearest": [
        -888,
        1224
      ],
      "viable_nearest": [
        -888,
        1224
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -888,
          1224
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -1374,
        8
      ],
      "raw_nearest": [
        -1352,
        40
      ],
      "viable_nearest": [
        -1352,
        40
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1352,
          40
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -360,
        -1088
      ],
      "raw_nearest": [
        -360,
        -1096
      ],
      "viable_nearest": [
        -360,
        -1096
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -360,
          -1096
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        825,
        1577
      ],
      "raw_nearest": [
        856,
        1608
      ],
      "viable_nearest": [
        856,
        1608
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          856,
          1608
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        418,
        1538
      ],
      "raw_nearest": [
        408,
        1528
      ],
      "viable_nearest": [
        408,
        1528
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          408,
          1528
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        1709,
        -610
      ],
      "raw_nearest": [
        1736,
        -584
      ],
      "viable_nearest": [
        1736,
        -584
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1736,
          -584
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        2130,
        93
      ],
      "raw_nearest": [
        2120,
        120
      ],
      "viable_nearest": [
        2120,
        120
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          2120,
          120
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        1040,
        1591
      ],
      "raw_nearest": [
        1064,
        1592
      ],
      "viable_nearest": [
        1064,
        1592
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          1064,
          1592
        ]
      ],
      "status": "unique"
    },
    {
      "seed": "4294979641",
      "type": "bastion",
      "marker": [
        -1110,
        1318
      ],
      "raw_nearest": [
        -1080,
        1304
      ],
      "viable_nearest": [
        -1080,
        1304
      ],
      "raw_rejected": false,
      "external_status": "chunkbase_checked",
      "actual_minecraft": null,
      "changed_from_baseline": false,
      "convention": "variable_rotated_piece_marker",
      "diagnostic_radius": 48,
      "possible_starts": [
        [
          -1080,
          1304
        ]
      ],
      "status": "unique"
    }
  ],
  "points": [
    {
      "id": 0,
      "seed": "12345",
      "dimension": 0,
      "x": -11264,
      "z": 9984,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "ocean",
      "chunkbase_comparison_biome": "ocean",
      "chunkbase_cave_range": null,
      "local_biome": "ocean",
      "local_height": 47,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 1,
      "seed": "12345",
      "dimension": 0,
      "x": 1280,
      "z": -8192,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 87,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 86,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 2,
      "seed": "12345",
      "dimension": 0,
      "x": -3584,
      "z": 18176,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 62,
      "chunkbase_marker_biome": "desert",
      "chunkbase_comparison_biome": "desert",
      "chunkbase_cave_range": null,
      "local_biome": "desert",
      "local_height": 60,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 3,
      "seed": "12345",
      "dimension": 0,
      "x": -4608,
      "z": 8192,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 72,
      "chunkbase_marker_biome": "windswept_hills",
      "chunkbase_comparison_biome": "windswept_hills",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_hills",
      "local_height": 72,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 4,
      "seed": "12345",
      "dimension": 0,
      "x": -29440,
      "z": 19200,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 69,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 68,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 5,
      "seed": "12345",
      "dimension": 0,
      "x": 0,
      "z": -23552,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 66,
      "chunkbase_marker_biome": "taiga",
      "chunkbase_comparison_biome": "taiga",
      "chunkbase_cave_range": null,
      "local_biome": "taiga",
      "local_height": 64,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 6,
      "seed": "12345",
      "dimension": 0,
      "x": -31488,
      "z": 27904,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 62,
      "chunkbase_marker_biome": "swamp",
      "chunkbase_comparison_biome": "swamp",
      "chunkbase_cave_range": null,
      "local_biome": "swamp",
      "local_height": 61,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 7,
      "seed": "12345",
      "dimension": 0,
      "x": 15872,
      "z": -13824,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 49,
      "chunkbase_marker_biome": "river",
      "chunkbase_comparison_biome": "river",
      "chunkbase_cave_range": null,
      "local_biome": "river",
      "local_height": 48,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 8,
      "seed": "12345",
      "dimension": 0,
      "x": -7168,
      "z": -20224,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 53,
      "chunkbase_marker_biome": "frozen_ocean",
      "chunkbase_comparison_biome": "frozen_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "frozen_ocean",
      "local_height": 52,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 9,
      "seed": "12345",
      "dimension": 0,
      "x": -6400,
      "z": -7680,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 55,
      "chunkbase_marker_biome": "frozen_river",
      "chunkbase_comparison_biome": "frozen_river",
      "chunkbase_cave_range": null,
      "local_biome": "frozen_river",
      "local_height": 53,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 10,
      "seed": "12345",
      "dimension": 0,
      "x": 11008,
      "z": 31232,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 68,
      "chunkbase_marker_biome": "snowy_plains",
      "chunkbase_comparison_biome": "snowy_plains",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_plains",
      "local_height": 67,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 11,
      "seed": "12345",
      "dimension": 0,
      "x": -6912,
      "z": -27904,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 76,
      "chunkbase_marker_biome": "mushroom_fields",
      "chunkbase_comparison_biome": "mushroom_fields",
      "chunkbase_cave_range": null,
      "local_biome": "mushroom_fields",
      "local_height": 75,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 12,
      "seed": "12345",
      "dimension": 0,
      "x": -11776,
      "z": -768,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "beach",
      "local_height": 63,
      "biome_matches": false,
      "height_delta": 0
    },
    {
      "id": 13,
      "seed": "12345",
      "dimension": 0,
      "x": -6912,
      "z": 11008,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 91,
      "chunkbase_marker_biome": "jungle",
      "chunkbase_comparison_biome": "jungle",
      "chunkbase_cave_range": null,
      "local_biome": "jungle",
      "local_height": 92,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 14,
      "seed": "12345",
      "dimension": 0,
      "x": 19712,
      "z": -9728,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "sparse_jungle",
      "chunkbase_comparison_biome": "sparse_jungle",
      "chunkbase_cave_range": null,
      "local_biome": "sparse_jungle",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 15,
      "seed": "12345",
      "dimension": 0,
      "x": 17408,
      "z": -10240,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 39,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "deep_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_ocean",
      "local_height": 38,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 16,
      "seed": "12345",
      "dimension": 0,
      "x": -13568,
      "z": -24320,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 67,
      "chunkbase_marker_biome": "desert",
      "chunkbase_comparison_biome": "desert",
      "chunkbase_cave_range": null,
      "local_biome": "stony_shore",
      "local_height": 66,
      "biome_matches": false,
      "height_delta": -1
    },
    {
      "id": 17,
      "seed": "12345",
      "dimension": 0,
      "x": -26624,
      "z": -6144,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 56,
      "chunkbase_marker_biome": "snowy_beach",
      "chunkbase_comparison_biome": "snowy_beach",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_beach",
      "local_height": 56,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 18,
      "seed": "12345",
      "dimension": 0,
      "x": -30720,
      "z": 18944,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 73,
      "chunkbase_marker_biome": "birch_forest",
      "chunkbase_comparison_biome": "birch_forest",
      "chunkbase_cave_range": null,
      "local_biome": "birch_forest",
      "local_height": 73,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 19,
      "seed": "12345",
      "dimension": 0,
      "x": 6400,
      "z": 32000,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 75,
      "chunkbase_marker_biome": "birch_forest",
      "chunkbase_comparison_biome": "birch_forest",
      "chunkbase_cave_range": null,
      "local_biome": "dark_forest",
      "local_height": 73,
      "biome_matches": false,
      "height_delta": -2
    },
    {
      "id": 20,
      "seed": "12345",
      "dimension": 0,
      "x": 17920,
      "z": 20736,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 66,
      "chunkbase_marker_biome": "snowy_taiga",
      "chunkbase_comparison_biome": "snowy_taiga",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_taiga",
      "local_height": 66,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 21,
      "seed": "12345",
      "dimension": 0,
      "x": 10240,
      "z": 28416,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "old_growth_pine_taiga",
      "chunkbase_comparison_biome": "old_growth_pine_taiga",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_pine_taiga",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 22,
      "seed": "12345",
      "dimension": 0,
      "x": 20736,
      "z": -16128,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 100,
      "chunkbase_marker_biome": "windswept_forest",
      "chunkbase_comparison_biome": "windswept_forest",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_forest",
      "local_height": 103,
      "biome_matches": true,
      "height_delta": 3
    },
    {
      "id": 23,
      "seed": "12345",
      "dimension": 0,
      "x": -25344,
      "z": -3328,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 64,
      "chunkbase_marker_biome": "savanna",
      "chunkbase_comparison_biome": "savanna",
      "chunkbase_cave_range": null,
      "local_biome": "savanna",
      "local_height": 65,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 24,
      "seed": "12345",
      "dimension": 0,
      "x": 8192,
      "z": 18432,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 108,
      "chunkbase_marker_biome": "savanna_plateau",
      "chunkbase_comparison_biome": "savanna_plateau",
      "chunkbase_cave_range": null,
      "local_biome": "savanna_plateau",
      "local_height": 106,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 25,
      "seed": "12345",
      "dimension": 0,
      "x": -2816,
      "z": 24320,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 135,
      "chunkbase_marker_biome": "badlands",
      "chunkbase_comparison_biome": "badlands",
      "chunkbase_cave_range": null,
      "local_biome": "badlands",
      "local_height": 132,
      "biome_matches": true,
      "height_delta": -3
    },
    {
      "id": 26,
      "seed": "12345",
      "dimension": 0,
      "x": -27392,
      "z": -25856,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 70,
      "chunkbase_marker_biome": "wooded_badlands",
      "chunkbase_comparison_biome": "wooded_badlands",
      "chunkbase_cave_range": null,
      "local_biome": "wooded_badlands",
      "local_height": 69,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 27,
      "seed": "12345",
      "dimension": 0,
      "x": -3840,
      "z": -11520,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "warm_ocean",
      "chunkbase_comparison_biome": "warm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "warm_ocean",
      "local_height": 47,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 28,
      "seed": "12345",
      "dimension": 0,
      "x": -11520,
      "z": -30208,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 46,
      "chunkbase_marker_biome": "lukewarm_ocean",
      "chunkbase_comparison_biome": "lukewarm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "lukewarm_ocean",
      "local_height": 46,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 29,
      "seed": "12345",
      "dimension": 0,
      "x": 6912,
      "z": -26112,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 46,
      "chunkbase_marker_biome": "cold_ocean",
      "chunkbase_comparison_biome": "cold_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "cold_ocean",
      "local_height": 46,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 30,
      "seed": "12345",
      "dimension": 0,
      "x": 8704,
      "z": -14848,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 43,
      "chunkbase_marker_biome": "deep_lukewarm_ocean",
      "chunkbase_comparison_biome": "deep_lukewarm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_lukewarm_ocean",
      "local_height": 42,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 31,
      "seed": "12345",
      "dimension": 0,
      "x": 14336,
      "z": -32000,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 39,
      "chunkbase_marker_biome": "deep_cold_ocean",
      "chunkbase_comparison_biome": "deep_cold_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_cold_ocean",
      "local_height": 37,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 32,
      "seed": "12345",
      "dimension": 0,
      "x": 3328,
      "z": -22272,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 50,
      "chunkbase_marker_biome": "deep_frozen_ocean",
      "chunkbase_comparison_biome": "deep_frozen_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_frozen_ocean",
      "local_height": 49,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 33,
      "seed": "12345",
      "dimension": 0,
      "x": -27904,
      "z": -5376,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 68,
      "chunkbase_marker_biome": "sunflower_plains",
      "chunkbase_comparison_biome": "sunflower_plains",
      "chunkbase_cave_range": null,
      "local_biome": "sunflower_plains",
      "local_height": 68,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 34,
      "seed": "12345",
      "dimension": 0,
      "x": -19712,
      "z": 12032,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 78,
      "chunkbase_marker_biome": "windswept_gravelly_hills",
      "chunkbase_comparison_biome": "windswept_gravelly_hills",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_gravelly_hills",
      "local_height": 77,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 35,
      "seed": "12345",
      "dimension": 0,
      "x": -7168,
      "z": 2816,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 61,
      "chunkbase_marker_biome": "flower_forest",
      "chunkbase_comparison_biome": "flower_forest",
      "chunkbase_cave_range": null,
      "local_biome": "flower_forest",
      "local_height": 59,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 36,
      "seed": "12345",
      "dimension": 0,
      "x": 31232,
      "z": -19456,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 88,
      "chunkbase_marker_biome": "ice_spikes",
      "chunkbase_comparison_biome": "ice_spikes",
      "chunkbase_cave_range": null,
      "local_biome": "ice_spikes",
      "local_height": 88,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 37,
      "seed": "12345",
      "dimension": 0,
      "x": 6912,
      "z": -21504,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 82,
      "chunkbase_marker_biome": "windswept_forest",
      "chunkbase_comparison_biome": "windswept_forest",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_birch_forest",
      "local_height": 82,
      "biome_matches": false,
      "height_delta": 0
    },
    {
      "id": 38,
      "seed": "12345",
      "dimension": 0,
      "x": -19200,
      "z": 30464,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 68,
      "chunkbase_marker_biome": "old_growth_spruce_taiga",
      "chunkbase_comparison_biome": "old_growth_spruce_taiga",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_spruce_taiga",
      "local_height": 67,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 39,
      "seed": "12345",
      "dimension": 0,
      "x": -26112,
      "z": -12800,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 67,
      "chunkbase_marker_biome": "windswept_savanna",
      "chunkbase_comparison_biome": "windswept_savanna",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_savanna",
      "local_height": 69,
      "biome_matches": true,
      "height_delta": 2
    },
    {
      "id": 40,
      "seed": "12345",
      "dimension": 0,
      "x": 23296,
      "z": -31488,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 51,
      "chunkbase_marker_biome": "river",
      "chunkbase_comparison_biome": "river",
      "chunkbase_cave_range": null,
      "local_biome": "eroded_badlands",
      "local_height": 51,
      "biome_matches": false,
      "height_delta": 0
    },
    {
      "id": 41,
      "seed": "12345",
      "dimension": 0,
      "x": 1536,
      "z": 19712,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 64,
      "chunkbase_marker_biome": "bamboo_jungle",
      "chunkbase_comparison_biome": "bamboo_jungle",
      "chunkbase_cave_range": null,
      "local_biome": "bamboo_jungle",
      "local_height": 64,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 42,
      "seed": "12345",
      "dimension": 0,
      "x": 12032,
      "z": -18176,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 110,
      "chunkbase_marker_biome": "meadow",
      "chunkbase_comparison_biome": "meadow",
      "chunkbase_cave_range": null,
      "local_biome": "meadow",
      "local_height": 109,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 43,
      "seed": "12345",
      "dimension": 0,
      "x": -22272,
      "z": 19200,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 124,
      "chunkbase_marker_biome": "grove",
      "chunkbase_comparison_biome": "grove",
      "chunkbase_cave_range": null,
      "local_biome": "grove",
      "local_height": 125,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 44,
      "seed": "12345",
      "dimension": 0,
      "x": 21248,
      "z": 9728,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 77,
      "chunkbase_marker_biome": "snowy_slopes",
      "chunkbase_comparison_biome": "snowy_slopes",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_slopes",
      "local_height": 75,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 45,
      "seed": "12345",
      "dimension": 0,
      "x": 18176,
      "z": 1536,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 127,
      "chunkbase_marker_biome": "jagged_peaks",
      "chunkbase_comparison_biome": "jagged_peaks",
      "chunkbase_cave_range": null,
      "local_biome": "jagged_peaks",
      "local_height": 131,
      "biome_matches": true,
      "height_delta": 4
    },
    {
      "id": 46,
      "seed": "12345",
      "dimension": 0,
      "x": 5888,
      "z": 19200,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 178,
      "chunkbase_marker_biome": "frozen_peaks",
      "chunkbase_comparison_biome": "frozen_peaks",
      "chunkbase_cave_range": null,
      "local_biome": "frozen_peaks",
      "local_height": 174,
      "biome_matches": true,
      "height_delta": -4
    },
    {
      "id": 47,
      "seed": "12345",
      "dimension": 0,
      "x": 7424,
      "z": 16896,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 118,
      "chunkbase_marker_biome": "stony_peaks",
      "chunkbase_comparison_biome": "stony_peaks",
      "chunkbase_cave_range": null,
      "local_biome": "stony_peaks",
      "local_height": 117,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 48,
      "seed": "12345",
      "dimension": 0,
      "x": 29952,
      "z": 28672,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 60,
      "chunkbase_marker_biome": "mangrove_swamp",
      "chunkbase_comparison_biome": "mangrove_swamp",
      "chunkbase_cave_range": null,
      "local_biome": "mangrove_swamp",
      "local_height": 59,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 49,
      "seed": "12345",
      "dimension": 0,
      "x": 23040,
      "z": -26368,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 125,
      "chunkbase_marker_biome": "cherry_grove",
      "chunkbase_comparison_biome": "cherry_grove",
      "chunkbase_cave_range": null,
      "local_biome": "cherry_grove",
      "local_height": 124,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 50,
      "seed": "12345",
      "dimension": 0,
      "x": -9216,
      "z": 14080,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 119,
      "chunkbase_marker_biome": "pale_garden",
      "chunkbase_comparison_biome": "pale_garden",
      "chunkbase_cave_range": null,
      "local_biome": "pale_garden",
      "local_height": 119,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 51,
      "seed": "12345",
      "dimension": 0,
      "x": 20480,
      "z": 20224,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 71,
      "chunkbase_marker_biome": "dappled_forest",
      "chunkbase_comparison_biome": "dappled_forest",
      "chunkbase_cave_range": null,
      "local_biome": "dappled_forest",
      "local_height": 69,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 52,
      "seed": "12345",
      "dimension": 0,
      "x": 25344,
      "z": -19712,
      "mode": "bottom",
      "sample_y": -51,
      "chunkbase_marker_y": 66,
      "chunkbase_marker_biome": "dark_forest",
      "chunkbase_comparison_biome": "dripstone_caves",
      "chunkbase_cave_range": [
        -56,
        51
      ],
      "local_biome": "dripstone_caves",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 53,
      "seed": "12345",
      "dimension": 0,
      "x": 8448,
      "z": 24576,
      "mode": "bottom",
      "sample_y": -51,
      "chunkbase_marker_y": 32,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "lush_caves",
      "chunkbase_cave_range": [
        -64,
        11
      ],
      "local_biome": "lush_caves",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 54,
      "seed": "12345",
      "dimension": 0,
      "x": 11264,
      "z": -11520,
      "mode": "bottom",
      "sample_y": -51,
      "chunkbase_marker_y": 87,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "deep_dark",
      "chunkbase_cave_range": [
        -64,
        -49
      ],
      "local_biome": "deep_dark",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 55,
      "seed": "12345",
      "dimension": 0,
      "x": 25600,
      "z": 26112,
      "mode": "bottom",
      "sample_y": -51,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "warm_ocean",
      "chunkbase_comparison_biome": "sulfur_caves",
      "chunkbase_cave_range": [
        -60,
        31
      ],
      "local_biome": "sulfur_caves",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 56,
      "seed": "12345",
      "dimension": 0,
      "x": 2487,
      "z": 3844,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 69,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 68,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 57,
      "seed": "12345",
      "dimension": 0,
      "x": 2033,
      "z": 447,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 45,
      "chunkbase_marker_biome": "frozen_ocean",
      "chunkbase_comparison_biome": "frozen_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "frozen_ocean",
      "local_height": 45,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 58,
      "seed": "12345",
      "dimension": 0,
      "x": 2400,
      "z": -3176,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 36,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "deep_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_ocean",
      "local_height": 34,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 59,
      "seed": "12345",
      "dimension": 0,
      "x": 4873,
      "z": 547,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 111,
      "chunkbase_marker_biome": "meadow",
      "chunkbase_comparison_biome": "meadow",
      "chunkbase_cave_range": null,
      "local_biome": "meadow",
      "local_height": 111,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 60,
      "seed": "12345",
      "dimension": 0,
      "x": 1608,
      "z": -3151,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 65,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 64,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 61,
      "seed": "12345",
      "dimension": 0,
      "x": -4256,
      "z": -3923,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "warm_ocean",
      "chunkbase_comparison_biome": "warm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "warm_ocean",
      "local_height": 47,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 62,
      "seed": "12345",
      "dimension": 0,
      "x": 3994,
      "z": -1402,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 32,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "deep_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_ocean",
      "local_height": 32,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 63,
      "seed": "12345",
      "dimension": 0,
      "x": -2923,
      "z": -2490,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 48,
      "chunkbase_marker_biome": "beach",
      "chunkbase_comparison_biome": "beach",
      "chunkbase_cave_range": null,
      "local_biome": "beach",
      "local_height": 48,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 64,
      "seed": "12345",
      "dimension": 0,
      "x": 3751,
      "z": -3516,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "river",
      "chunkbase_comparison_biome": "river",
      "chunkbase_cave_range": null,
      "local_biome": "river",
      "local_height": 47,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 65,
      "seed": "12345",
      "dimension": 0,
      "x": -1355,
      "z": 2217,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 69,
      "chunkbase_marker_biome": "birch_forest",
      "chunkbase_comparison_biome": "birch_forest",
      "chunkbase_cave_range": null,
      "local_biome": "birch_forest",
      "local_height": 67,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 66,
      "seed": "12345",
      "dimension": -1,
      "x": -2048,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "nether_wastes",
      "chunkbase_comparison_biome": "nether_wastes",
      "chunkbase_cave_range": null,
      "local_biome": "nether_wastes",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 67,
      "seed": "12345",
      "dimension": -1,
      "x": -768,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "soul_sand_valley",
      "chunkbase_comparison_biome": "soul_sand_valley",
      "chunkbase_cave_range": null,
      "local_biome": "soul_sand_valley",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 68,
      "seed": "12345",
      "dimension": -1,
      "x": -1280,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "crimson_forest",
      "chunkbase_comparison_biome": "crimson_forest",
      "chunkbase_cave_range": null,
      "local_biome": "crimson_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 69,
      "seed": "12345",
      "dimension": -1,
      "x": -1792,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "warped_forest",
      "chunkbase_comparison_biome": "warped_forest",
      "chunkbase_cave_range": null,
      "local_biome": "warped_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 70,
      "seed": "12345",
      "dimension": -1,
      "x": -1536,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "basalt_deltas",
      "chunkbase_comparison_biome": "basalt_deltas",
      "chunkbase_cave_range": null,
      "local_biome": "basalt_deltas",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 71,
      "seed": "0",
      "dimension": 0,
      "x": 19456,
      "z": -8960,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 49,
      "chunkbase_marker_biome": "ocean",
      "chunkbase_comparison_biome": "ocean",
      "chunkbase_cave_range": null,
      "local_biome": "ocean",
      "local_height": 49,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 72,
      "seed": "0",
      "dimension": 0,
      "x": 0,
      "z": -2304,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 64,
      "chunkbase_marker_biome": "desert",
      "chunkbase_comparison_biome": "desert",
      "chunkbase_cave_range": null,
      "local_biome": "desert",
      "local_height": 64,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 73,
      "seed": "0",
      "dimension": 0,
      "x": -14080,
      "z": -12800,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 82,
      "chunkbase_marker_biome": "windswept_hills",
      "chunkbase_comparison_biome": "windswept_hills",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_hills",
      "local_height": 85,
      "biome_matches": true,
      "height_delta": 3
    },
    {
      "id": 74,
      "seed": "0",
      "dimension": 0,
      "x": 25344,
      "z": -9984,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 79,
      "chunkbase_marker_biome": "taiga",
      "chunkbase_comparison_biome": "taiga",
      "chunkbase_cave_range": null,
      "local_biome": "taiga",
      "local_height": 79,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 75,
      "seed": "0",
      "dimension": 0,
      "x": -25856,
      "z": 10496,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 69,
      "chunkbase_marker_biome": "swamp",
      "chunkbase_comparison_biome": "swamp",
      "chunkbase_cave_range": null,
      "local_biome": "swamp",
      "local_height": 68,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 76,
      "seed": "0",
      "dimension": 0,
      "x": -1024,
      "z": -32256,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 57,
      "chunkbase_marker_biome": "frozen_river",
      "chunkbase_comparison_biome": "frozen_river",
      "chunkbase_cave_range": null,
      "local_biome": "frozen_river",
      "local_height": 56,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 77,
      "seed": "0",
      "dimension": 0,
      "x": -9472,
      "z": 12544,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 74,
      "chunkbase_marker_biome": "snowy_plains",
      "chunkbase_comparison_biome": "snowy_plains",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_plains",
      "local_height": 74,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 78,
      "seed": "0",
      "dimension": 0,
      "x": -14848,
      "z": -25600,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 68,
      "chunkbase_marker_biome": "mushroom_fields",
      "chunkbase_comparison_biome": "mushroom_fields",
      "chunkbase_cave_range": null,
      "local_biome": "mushroom_fields",
      "local_height": 67,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 79,
      "seed": "0",
      "dimension": 0,
      "x": -19456,
      "z": -29440,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 111,
      "chunkbase_marker_biome": "jungle",
      "chunkbase_comparison_biome": "jungle",
      "chunkbase_cave_range": null,
      "local_biome": "jungle",
      "local_height": 109,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 80,
      "seed": "0",
      "dimension": 0,
      "x": 2816,
      "z": -18944,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 64,
      "chunkbase_marker_biome": "sparse_jungle",
      "chunkbase_comparison_biome": "sparse_jungle",
      "chunkbase_cave_range": null,
      "local_biome": "sparse_jungle",
      "local_height": 64,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 81,
      "seed": "0",
      "dimension": 0,
      "x": -5376,
      "z": 30464,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 54,
      "chunkbase_marker_biome": "stony_shore",
      "chunkbase_comparison_biome": "stony_shore",
      "chunkbase_cave_range": null,
      "local_biome": "stony_shore",
      "local_height": 53,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 82,
      "seed": "0",
      "dimension": 0,
      "x": -1792,
      "z": -32000,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "snowy_beach",
      "chunkbase_comparison_biome": "snowy_beach",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_beach",
      "local_height": 60,
      "biome_matches": true,
      "height_delta": -3
    },
    {
      "id": 83,
      "seed": "0",
      "dimension": 0,
      "x": -512,
      "z": -13824,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 93,
      "chunkbase_marker_biome": "dark_forest",
      "chunkbase_comparison_biome": "dark_forest",
      "chunkbase_cave_range": null,
      "local_biome": "dark_forest",
      "local_height": 92,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 84,
      "seed": "0",
      "dimension": 0,
      "x": 25344,
      "z": 19712,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 70,
      "chunkbase_marker_biome": "snowy_taiga",
      "chunkbase_comparison_biome": "snowy_taiga",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_taiga",
      "local_height": 69,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 85,
      "seed": "0",
      "dimension": 0,
      "x": -19712,
      "z": 9472,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 89,
      "chunkbase_marker_biome": "old_growth_pine_taiga",
      "chunkbase_comparison_biome": "old_growth_pine_taiga",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_pine_taiga",
      "local_height": 88,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 86,
      "seed": "0",
      "dimension": 0,
      "x": 6656,
      "z": 512,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 97,
      "chunkbase_marker_biome": "windswept_forest",
      "chunkbase_comparison_biome": "windswept_forest",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_forest",
      "local_height": 96,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 87,
      "seed": "0",
      "dimension": 0,
      "x": 6400,
      "z": 10240,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 70,
      "chunkbase_marker_biome": "savanna",
      "chunkbase_comparison_biome": "savanna",
      "chunkbase_cave_range": null,
      "local_biome": "savanna",
      "local_height": 71,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 88,
      "seed": "0",
      "dimension": 0,
      "x": 8192,
      "z": 31488,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 94,
      "chunkbase_marker_biome": "savanna_plateau",
      "chunkbase_comparison_biome": "savanna_plateau",
      "chunkbase_cave_range": null,
      "local_biome": "savanna_plateau",
      "local_height": 92,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 89,
      "seed": "0",
      "dimension": 0,
      "x": 20992,
      "z": 29952,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "badlands",
      "chunkbase_comparison_biome": "badlands",
      "chunkbase_cave_range": null,
      "local_biome": "badlands",
      "local_height": 60,
      "biome_matches": true,
      "height_delta": -3
    },
    {
      "id": 90,
      "seed": "0",
      "dimension": 0,
      "x": 18432,
      "z": 18432,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 87,
      "chunkbase_marker_biome": "wooded_badlands",
      "chunkbase_comparison_biome": "wooded_badlands",
      "chunkbase_cave_range": null,
      "local_biome": "wooded_badlands",
      "local_height": 87,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 91,
      "seed": "0",
      "dimension": 0,
      "x": -30208,
      "z": -19712,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 51,
      "chunkbase_marker_biome": "lukewarm_ocean",
      "chunkbase_comparison_biome": "lukewarm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "lukewarm_ocean",
      "local_height": 53,
      "biome_matches": true,
      "height_delta": 2
    },
    {
      "id": 92,
      "seed": "0",
      "dimension": 0,
      "x": 28416,
      "z": 14080,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 49,
      "chunkbase_marker_biome": "cold_ocean",
      "chunkbase_comparison_biome": "cold_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "cold_ocean",
      "local_height": 49,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 93,
      "seed": "0",
      "dimension": 0,
      "x": 9472,
      "z": -1792,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 42,
      "chunkbase_marker_biome": "deep_lukewarm_ocean",
      "chunkbase_comparison_biome": "deep_lukewarm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_lukewarm_ocean",
      "local_height": 42,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 94,
      "seed": "0",
      "dimension": 0,
      "x": 29440,
      "z": -16384,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 37,
      "chunkbase_marker_biome": "deep_cold_ocean",
      "chunkbase_comparison_biome": "deep_cold_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_cold_ocean",
      "local_height": 36,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 95,
      "seed": "0",
      "dimension": 0,
      "x": 6912,
      "z": -26624,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 38,
      "chunkbase_marker_biome": "deep_frozen_ocean",
      "chunkbase_comparison_biome": "deep_frozen_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_frozen_ocean",
      "local_height": 38,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 96,
      "seed": "0",
      "dimension": 0,
      "x": -512,
      "z": -19712,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "sunflower_plains",
      "chunkbase_comparison_biome": "sunflower_plains",
      "chunkbase_cave_range": null,
      "local_biome": "sunflower_plains",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 97,
      "seed": "0",
      "dimension": 0,
      "x": -4352,
      "z": 1792,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 77,
      "chunkbase_marker_biome": "windswept_gravelly_hills",
      "chunkbase_comparison_biome": "windswept_gravelly_hills",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_gravelly_hills",
      "local_height": 79,
      "biome_matches": true,
      "height_delta": 2
    },
    {
      "id": 98,
      "seed": "0",
      "dimension": 0,
      "x": -11776,
      "z": -28416,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 99,
      "chunkbase_marker_biome": "flower_forest",
      "chunkbase_comparison_biome": "flower_forest",
      "chunkbase_cave_range": null,
      "local_biome": "flower_forest",
      "local_height": 99,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 99,
      "seed": "0",
      "dimension": 0,
      "x": 768,
      "z": 30976,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 61,
      "chunkbase_marker_biome": "ice_spikes",
      "chunkbase_comparison_biome": "ice_spikes",
      "chunkbase_cave_range": null,
      "local_biome": "ice_spikes",
      "local_height": 60,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 100,
      "seed": "0",
      "dimension": 0,
      "x": -18688,
      "z": -512,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 62,
      "chunkbase_marker_biome": "old_growth_birch_forest",
      "chunkbase_comparison_biome": "old_growth_birch_forest",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_birch_forest",
      "local_height": 62,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 101,
      "seed": "0",
      "dimension": 0,
      "x": 3072,
      "z": 18944,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 103,
      "chunkbase_marker_biome": "old_growth_spruce_taiga",
      "chunkbase_comparison_biome": "old_growth_spruce_taiga",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_spruce_taiga",
      "local_height": 101,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 102,
      "seed": "0",
      "dimension": 0,
      "x": -22016,
      "z": -23040,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 59,
      "chunkbase_marker_biome": "windswept_savanna",
      "chunkbase_comparison_biome": "windswept_savanna",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_savanna",
      "local_height": 59,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 103,
      "seed": "0",
      "dimension": 0,
      "x": -26880,
      "z": -5120,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 79,
      "chunkbase_marker_biome": "eroded_badlands",
      "chunkbase_comparison_biome": "eroded_badlands",
      "chunkbase_cave_range": null,
      "local_biome": "eroded_badlands",
      "local_height": 78,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 104,
      "seed": "0",
      "dimension": 0,
      "x": -21248,
      "z": 30976,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "bamboo_jungle",
      "chunkbase_comparison_biome": "bamboo_jungle",
      "chunkbase_cave_range": null,
      "local_biome": "bamboo_jungle",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 105,
      "seed": "0",
      "dimension": 0,
      "x": 24320,
      "z": -1792,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 156,
      "chunkbase_marker_biome": "grove",
      "chunkbase_comparison_biome": "grove",
      "chunkbase_cave_range": null,
      "local_biome": "grove",
      "local_height": 151,
      "biome_matches": true,
      "height_delta": -5
    },
    {
      "id": 106,
      "seed": "0",
      "dimension": 0,
      "x": -13056,
      "z": -13824,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 78,
      "chunkbase_marker_biome": "snowy_slopes",
      "chunkbase_comparison_biome": "snowy_slopes",
      "chunkbase_cave_range": null,
      "local_biome": "snowy_slopes",
      "local_height": 77,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 107,
      "seed": "0",
      "dimension": 0,
      "x": 17408,
      "z": -28416,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 148,
      "chunkbase_marker_biome": "jagged_peaks",
      "chunkbase_comparison_biome": "jagged_peaks",
      "chunkbase_cave_range": null,
      "local_biome": "jagged_peaks",
      "local_height": 151,
      "biome_matches": true,
      "height_delta": 3
    },
    {
      "id": 108,
      "seed": "0",
      "dimension": 0,
      "x": -7936,
      "z": -5120,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 159,
      "chunkbase_marker_biome": "frozen_peaks",
      "chunkbase_comparison_biome": "frozen_peaks",
      "chunkbase_cave_range": null,
      "local_biome": "frozen_peaks",
      "local_height": 158,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 109,
      "seed": "0",
      "dimension": 0,
      "x": 6656,
      "z": 15616,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 143,
      "chunkbase_marker_biome": "stony_peaks",
      "chunkbase_comparison_biome": "stony_peaks",
      "chunkbase_cave_range": null,
      "local_biome": "stony_peaks",
      "local_height": 143,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 110,
      "seed": "0",
      "dimension": 0,
      "x": 18944,
      "z": 11776,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 60,
      "chunkbase_marker_biome": "mangrove_swamp",
      "chunkbase_comparison_biome": "mangrove_swamp",
      "chunkbase_cave_range": null,
      "local_biome": "mangrove_swamp",
      "local_height": 59,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 111,
      "seed": "0",
      "dimension": 0,
      "x": -12032,
      "z": -26624,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 113,
      "chunkbase_marker_biome": "cherry_grove",
      "chunkbase_comparison_biome": "cherry_grove",
      "chunkbase_cave_range": null,
      "local_biome": "cherry_grove",
      "local_height": 112,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 112,
      "seed": "0",
      "dimension": 0,
      "x": -18944,
      "z": 30976,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 104,
      "chunkbase_marker_biome": "pale_garden",
      "chunkbase_comparison_biome": "pale_garden",
      "chunkbase_cave_range": null,
      "local_biome": "pale_garden",
      "local_height": 103,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 113,
      "seed": "0",
      "dimension": 0,
      "x": -31232,
      "z": -21760,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 68,
      "chunkbase_marker_biome": "dappled_forest",
      "chunkbase_comparison_biome": "dappled_forest",
      "chunkbase_cave_range": null,
      "local_biome": "dappled_forest",
      "local_height": 66,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 114,
      "seed": "0",
      "dimension": 0,
      "x": 925,
      "z": -3679,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "warm_ocean",
      "chunkbase_comparison_biome": "warm_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "warm_ocean",
      "local_height": 46,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 115,
      "seed": "0",
      "dimension": 0,
      "x": -798,
      "z": 945,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 66,
      "chunkbase_marker_biome": "savanna",
      "chunkbase_comparison_biome": "savanna",
      "chunkbase_cave_range": null,
      "local_biome": "savanna",
      "local_height": 67,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 116,
      "seed": "0",
      "dimension": 0,
      "x": -1516,
      "z": -3915,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 86,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 84,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 117,
      "seed": "0",
      "dimension": 0,
      "x": -3379,
      "z": -4504,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 46,
      "chunkbase_marker_biome": "ocean",
      "chunkbase_comparison_biome": "ocean",
      "chunkbase_cave_range": null,
      "local_biome": "ocean",
      "local_height": 47,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 118,
      "seed": "0",
      "dimension": 0,
      "x": -1083,
      "z": 1172,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 73,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 72,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 119,
      "seed": "0",
      "dimension": 0,
      "x": -1426,
      "z": -691,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 47,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "deep_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_ocean",
      "local_height": 48,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 120,
      "seed": "0",
      "dimension": 0,
      "x": -4199,
      "z": 2099,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 83,
      "chunkbase_marker_biome": "windswept_gravelly_hills",
      "chunkbase_comparison_biome": "windswept_gravelly_hills",
      "chunkbase_cave_range": null,
      "local_biome": "windswept_gravelly_hills",
      "local_height": 82,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 121,
      "seed": "0",
      "dimension": 0,
      "x": 717,
      "z": -1040,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 77,
      "chunkbase_marker_biome": "savanna",
      "chunkbase_comparison_biome": "savanna",
      "chunkbase_cave_range": null,
      "local_biome": "savanna",
      "local_height": 76,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 122,
      "seed": "0",
      "dimension": 0,
      "x": -498,
      "z": 4594,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 68,
      "chunkbase_marker_biome": "taiga",
      "chunkbase_comparison_biome": "taiga",
      "chunkbase_cave_range": null,
      "local_biome": "taiga",
      "local_height": 69,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 123,
      "seed": "0",
      "dimension": 0,
      "x": 363,
      "z": -1917,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "wooded_badlands",
      "chunkbase_comparison_biome": "wooded_badlands",
      "chunkbase_cave_range": null,
      "local_biome": "wooded_badlands",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 124,
      "seed": "0",
      "dimension": -1,
      "x": -2048,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "nether_wastes",
      "chunkbase_comparison_biome": "nether_wastes",
      "chunkbase_cave_range": null,
      "local_biome": "nether_wastes",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 125,
      "seed": "0",
      "dimension": -1,
      "x": -1664,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "soul_sand_valley",
      "chunkbase_comparison_biome": "soul_sand_valley",
      "chunkbase_cave_range": null,
      "local_biome": "soul_sand_valley",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 126,
      "seed": "0",
      "dimension": -1,
      "x": -768,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "crimson_forest",
      "chunkbase_comparison_biome": "crimson_forest",
      "chunkbase_cave_range": null,
      "local_biome": "crimson_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 127,
      "seed": "0",
      "dimension": -1,
      "x": 640,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "warped_forest",
      "chunkbase_comparison_biome": "warped_forest",
      "chunkbase_cave_range": null,
      "local_biome": "warped_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 128,
      "seed": "0",
      "dimension": -1,
      "x": -1792,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "basalt_deltas",
      "chunkbase_comparison_biome": "basalt_deltas",
      "chunkbase_cave_range": null,
      "local_biome": "basalt_deltas",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 129,
      "seed": "-1",
      "dimension": 0,
      "x": -3734,
      "z": -2415,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 82,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 83,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 130,
      "seed": "-1",
      "dimension": 0,
      "x": 1039,
      "z": -948,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 131,
      "seed": "-1",
      "dimension": 0,
      "x": 711,
      "z": -2983,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "swamp",
      "chunkbase_comparison_biome": "swamp",
      "chunkbase_cave_range": null,
      "local_biome": "swamp",
      "local_height": 61,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 132,
      "seed": "-1",
      "dimension": 0,
      "x": 219,
      "z": 3612,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 65,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 64,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 133,
      "seed": "-1",
      "dimension": 0,
      "x": -1551,
      "z": -4748,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 133,
      "chunkbase_marker_biome": "badlands",
      "chunkbase_comparison_biome": "badlands",
      "chunkbase_cave_range": null,
      "local_biome": "badlands",
      "local_height": 132,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 134,
      "seed": "-1",
      "dimension": 0,
      "x": 164,
      "z": -200,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 34,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "deep_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_ocean",
      "local_height": 33,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 135,
      "seed": "-1",
      "dimension": 0,
      "x": 1039,
      "z": -773,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 70,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 71,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 136,
      "seed": "-1",
      "dimension": 0,
      "x": 772,
      "z": 3123,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 109,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 108,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 137,
      "seed": "-1",
      "dimension": 0,
      "x": -4225,
      "z": 1470,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 38,
      "chunkbase_marker_biome": "deep_ocean",
      "chunkbase_comparison_biome": "deep_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_ocean",
      "local_height": 36,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 138,
      "seed": "-1",
      "dimension": 0,
      "x": 4660,
      "z": -2456,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 103,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 103,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 139,
      "seed": "-1",
      "dimension": -1,
      "x": -1920,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "nether_wastes",
      "chunkbase_comparison_biome": "nether_wastes",
      "chunkbase_cave_range": null,
      "local_biome": "nether_wastes",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 140,
      "seed": "-1",
      "dimension": -1,
      "x": -1792,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "soul_sand_valley",
      "chunkbase_comparison_biome": "soul_sand_valley",
      "chunkbase_cave_range": null,
      "local_biome": "soul_sand_valley",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 141,
      "seed": "-1",
      "dimension": -1,
      "x": -2048,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "crimson_forest",
      "chunkbase_comparison_biome": "crimson_forest",
      "chunkbase_cave_range": null,
      "local_biome": "crimson_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 142,
      "seed": "-1",
      "dimension": -1,
      "x": 1280,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "warped_forest",
      "chunkbase_comparison_biome": "warped_forest",
      "chunkbase_cave_range": null,
      "local_biome": "warped_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 143,
      "seed": "-1",
      "dimension": -1,
      "x": 1536,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "basalt_deltas",
      "chunkbase_comparison_biome": "basalt_deltas",
      "chunkbase_cave_range": null,
      "local_biome": "basalt_deltas",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 144,
      "seed": "4294979641",
      "dimension": 0,
      "x": -2845,
      "z": -3581,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 71,
      "chunkbase_marker_biome": "plains",
      "chunkbase_comparison_biome": "plains",
      "chunkbase_cave_range": null,
      "local_biome": "plains",
      "local_height": 69,
      "biome_matches": true,
      "height_delta": -2
    },
    {
      "id": 145,
      "seed": "4294979641",
      "dimension": 0,
      "x": -3422,
      "z": 3556,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 67,
      "chunkbase_marker_biome": "old_growth_birch_forest",
      "chunkbase_comparison_biome": "old_growth_birch_forest",
      "chunkbase_cave_range": null,
      "local_biome": "old_growth_birch_forest",
      "local_height": 66,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 146,
      "seed": "4294979641",
      "dimension": 0,
      "x": -101,
      "z": -4991,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "beach",
      "chunkbase_comparison_biome": "beach",
      "chunkbase_cave_range": null,
      "local_biome": "beach",
      "local_height": 63,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 147,
      "seed": "4294979641",
      "dimension": 0,
      "x": -3250,
      "z": 2253,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 38,
      "chunkbase_marker_biome": "deep_frozen_ocean",
      "chunkbase_comparison_biome": "deep_frozen_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "deep_frozen_ocean",
      "local_height": 35,
      "biome_matches": true,
      "height_delta": -3
    },
    {
      "id": 148,
      "seed": "4294979641",
      "dimension": 0,
      "x": 3878,
      "z": -4013,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "birch_forest",
      "chunkbase_comparison_biome": "birch_forest",
      "chunkbase_cave_range": null,
      "local_biome": "beach",
      "local_height": 63,
      "biome_matches": false,
      "height_delta": 0
    },
    {
      "id": 149,
      "seed": "4294979641",
      "dimension": 0,
      "x": -1805,
      "z": -4373,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 49,
      "chunkbase_marker_biome": "cold_ocean",
      "chunkbase_comparison_biome": "cold_ocean",
      "chunkbase_cave_range": null,
      "local_biome": "cold_ocean",
      "local_height": 49,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 150,
      "seed": "4294979641",
      "dimension": 0,
      "x": -767,
      "z": 4162,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 106,
      "chunkbase_marker_biome": "badlands",
      "chunkbase_comparison_biome": "badlands",
      "chunkbase_cave_range": null,
      "local_biome": "badlands",
      "local_height": 107,
      "biome_matches": true,
      "height_delta": 1
    },
    {
      "id": 151,
      "seed": "4294979641",
      "dimension": 0,
      "x": -1332,
      "z": 4648,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 70,
      "chunkbase_marker_biome": "desert",
      "chunkbase_comparison_biome": "desert",
      "chunkbase_cave_range": null,
      "local_biome": "desert",
      "local_height": 70,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 152,
      "seed": "4294979641",
      "dimension": 0,
      "x": -3127,
      "z": -2517,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 63,
      "chunkbase_marker_biome": "swamp",
      "chunkbase_comparison_biome": "swamp",
      "chunkbase_cave_range": null,
      "local_biome": "swamp",
      "local_height": 62,
      "biome_matches": true,
      "height_delta": -1
    },
    {
      "id": 153,
      "seed": "4294979641",
      "dimension": 0,
      "x": 491,
      "z": -3074,
      "mode": "surface",
      "sample_y": null,
      "chunkbase_marker_y": 84,
      "chunkbase_marker_biome": "forest",
      "chunkbase_comparison_biome": "forest",
      "chunkbase_cave_range": null,
      "local_biome": "forest",
      "local_height": 84,
      "biome_matches": true,
      "height_delta": 0
    },
    {
      "id": 154,
      "seed": "4294979641",
      "dimension": -1,
      "x": -2048,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "nether_wastes",
      "chunkbase_comparison_biome": "nether_wastes",
      "chunkbase_cave_range": null,
      "local_biome": "nether_wastes",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 155,
      "seed": "4294979641",
      "dimension": -1,
      "x": -768,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "soul_sand_valley",
      "chunkbase_comparison_biome": "soul_sand_valley",
      "chunkbase_cave_range": null,
      "local_biome": "soul_sand_valley",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 156,
      "seed": "4294979641",
      "dimension": -1,
      "x": -1280,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "crimson_forest",
      "chunkbase_comparison_biome": "crimson_forest",
      "chunkbase_cave_range": null,
      "local_biome": "crimson_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 157,
      "seed": "4294979641",
      "dimension": -1,
      "x": -1792,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "warped_forest",
      "chunkbase_comparison_biome": "warped_forest",
      "chunkbase_cave_range": null,
      "local_biome": "warped_forest",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    },
    {
      "id": 158,
      "seed": "4294979641",
      "dimension": -1,
      "x": -1536,
      "z": -2048,
      "mode": "nether",
      "sample_y": 33,
      "chunkbase_marker_y": null,
      "chunkbase_marker_biome": "basalt_deltas",
      "chunkbase_comparison_biome": "basalt_deltas",
      "chunkbase_cave_range": null,
      "local_biome": "basalt_deltas",
      "local_height": null,
      "biome_matches": true,
      "height_delta": null
    }
  ],
  "limits": [
    "Capped positive lists do not measure complete recall or false positives.",
    "Empirical type offsets cannot certify structure footprints or change square-border eligibility.",
    "Exact local baseline comparisons detect drift even inside diagnostic marker bounds."
  ]
}
````

## Excerpt: vendor/cubiomes-bedrock/finders.c, lines 851–996

Village-associated iterator and static Stronghold placement. Full file is in snapshot/.

````c
int nextVillageStronghold(StrongholdIter *sh, const Generator *g)
{
    Pos p;
    StructureConfig sc;
    Generator *gm = (Generator *) g;
    getStructureConfig(Village, g->mc, &sc);

    if (sh->index == 0)
    {
        setSeed(g->seed);
        float angle = 2.0 * PI * nextFloat();
        int dist = 40 + nextInt(16);

        sh->pos.x = 0;
        sh->pos.z = 0;
        sh->angle = angle;
        sh->dist = dist;
        sh->mc = g->mc;
    }

    int placed = 0;
    while (!placed)
    {
        int cx = (int)floor(cos(sh->angle) * sh->dist);
        int cz = (int)floor(sin(sh->angle) * sh->dist);

        if (g->mc >= MC_1_11)
        {
            int minChunkX = cx - 8;
            int maxChunkX = cx + 7;
            int minChunkZ = cz - 8;
            int maxChunkZ = cz + 7;
            Pos r0 = chunkToRegion(minChunkX, minChunkZ, sc.regionSize);
            Pos r1 = chunkToRegion(maxChunkX, maxChunkZ, sc.regionSize);
            Pos candPos[4];
            int candChunkX[4], candChunkZ[4];
            int candCount = 0;

            /* Each 1.11+ village region has at most one candidate chunk, so
             * scanning unique regions avoids recomputing the same position for
             * every chunk in the 16x16 search window.
             */
            for (int rx = r0.x; rx <= r1.x; rx++)
            {
                for (int rz = r0.z; rz <= r1.z; rz++)
                {
                    p = getLargeStructurePos(sc, g->seed, rx, rz);
                    int x = p.x >> 4;
                    int z = p.z >> 4;

                    if (x < minChunkX || x > maxChunkX ||
                        z < minChunkZ || z > maxChunkZ)
                        continue;
                    candPos[candCount] = p;
                    candChunkX[candCount] = x;
                    candChunkZ[candCount] = z;
                    candCount++;
                }
            }

            for (int i = 0; i < candCount; i++)
            {
                int best = i;
                for (int j = i + 1; j < candCount; j++)
                {
                    if (candChunkX[j] < candChunkX[best] ||
                        (candChunkX[j] == candChunkX[best] && candChunkZ[j] < candChunkZ[best]))
                    {
                        best = j;
                    }
                }
                if (best != i)
                {
                    int tmpx = candChunkX[i], tmpz = candChunkZ[i];
                    Pos tmpp = candPos[i];
                    candChunkX[i] = candChunkX[best];
                    candChunkZ[i] = candChunkZ[best];
                    candPos[i] = candPos[best];
                    candChunkX[best] = tmpx;
                    candChunkZ[best] = tmpz;
                    candPos[best] = tmpp;
                }
            }

            for (int i = 0; i < candCount; i++)
            {
                p = candPos[i];
                if (!isViableStructurePos(Village, gm, p.x, p.z, 0))
                    continue;
                sh->pos.x = p.x - 4;
                sh->pos.z = p.z - 4;
                sh->index++;
                placed = 1;
                break;
            }
        }
        else
        {
            for (int x = cx - 8; x < cx + 8 && !placed; x++)
            {
                for (int z = cz - 8; z < cz + 8 && !placed; z++)
                {
                    if (!isVillageChunk(sc, g->seed, x, z))
                        continue;
                    p.x = x*16 + 8;
                    p.z = z*16 + 8;
                    if (!isViableStructurePos(Village, gm, p.x, p.z, 0))
                        continue;
                    sh->pos.x = p.x - 4;
                    sh->pos.z = p.z - 4;
                    sh->index++;
                    placed = 1;
                }
            }
        }
        if (placed)
        {
            sh->angle += 0.6f * PI;
            sh->dist += 8;
        }
        else
        {
            sh->angle += 0.25f * PI;
            sh->dist += 4;
        }
    }

    return 3 - (sh->index-1);
}

int getStaticStronghold(StructureConfig sconf, uint64_t seed,
    int regionX, int regionZ, Pos *pos)
{
    int a = sconf.regionSize * regionX + 100;
    int b = sconf.regionSize * regionZ + 100;
    setSeed(784295783249ULL * a + 827828252345ULL * b + seed + sconf.salt);
    int x = nextIntRange(-50, 50) + a;
    int z = nextIntRange(-50, 50) + b;
    if (nextFloat() >= sconf.rarity)
       return 0;
    pos->x = x*16+4;
    pos->z = z*16+4;
    return 1;
}


````
