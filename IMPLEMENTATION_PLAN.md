# Bedrock island seed search — implementation plan

Historical planning/audit evidence is retained below. Current implementation and verification progress is in [PROGRESS.md](PROGRESS.md); the active completion criteria are [SWEEP_READY_HANDOFF.md](SWEEP_READY_HANDOFF.md). The expanded search, measured pilot, fresh selection checks and finite readiness verification are complete; current outcomes and remaining limits are in [SWEEP_READINESS.md](SWEEP_READINESS.md).

Updated 7 October 2026. Status: the bounded native preflight builds and passes 44 tests; stage benchmarks, terrain/structure comparisons and a phone inspection packet are available. Three initial phone observations support surface predictions: water at origin, and one-block ground differences at (256,-256) and (256,256). Matching-version Chunkbase agrees closely with the three Overworld phone anchors; actual inspection found the Fortress fallback at (-152,120) absent; failed-Bastion promotion has been removed and the diagnostic square now has no predicted Fortress. Broader landscape/structure validation remains pending. No large seed search is running. Numerical preferences remain provisional until the pilot. See [the goal](GOAL.md), [all query distances and areas](SEARCH_TARGETS.md), and [preflight progress](PREFLIGHT_STATUS.md).

## 1. Agreed result

Find a Bedrock **26.52** seed with a fully separated, buildable, preferably lightly wooded island inside a water-and-mountain basin, abundant building wood on the surrounding land, useful nearby Overworld structures, and a Nether Fortress and Bastion inside the Nether border. Search on the Intel Mac; review finalists in matching-version Chunkbase, optionally inspect in Minecraft; upload the selected world to a Mojang-hosted Realm from the phone.

| Item | Decision |
|---|---|
| Game | Bedrock 26.52; version recorded in every result |
| Search machine | Intel iMac Pro, 18 physical cores, 64 GB RAM, macOS 15.8 |
| Realm | Hosted by Mojang; the Mac is not the Realm server |
| Achievements | Not a requirement |
| Spawn | Selected island; natural world spawn need not be nearby |
| Island | No land bridge; preferred diameter 300–700 blocks |
| Landscape | Water separation and mountains across roughly 75% of directions |
| Wood | Prefer less wood on the central island; require abundant accessible forest on surrounding land and lower mountain slopes |
| Core structures | Trial Chamber, Stronghold, Mineshaft are strong preferences, initially not hard filters |
| Bonuses | Ancient City first; Village, ruined portal, shipwreck, monument, outpost afterward |
| Nether | Both Fortress and Bastion required inside its square; closer is better |
| Output | Ranked seed/center pairs, maps, metrics, evidence status, deployment instructions |

The central island does not need a wood supply; fewer trees there are preferable for building. Nearby external land and wooded lower slopes should provide the large wood supply. Snowy or bare summits can qualify. A forest biome label alone does not establish actual tree abundance. The island must also have usable settlement space for about ten players; buildability is inspected manually in the first version.

Numeric geometry thresholds, wood fractions, scoring weights, center search extent, and worker counts below are **starting defaults to tune**, rather than additional user commitments.

## 2. Border sizing and centers

The user has confirmed **3008 × 3008 in the Overworld and 992 × 992 in the Nether** to use the stock addon. The 1200 × 1200 core and 2000 × 2000 primary squares are report/map overlays. Continuous distance scoring favors nearby structures; these overlays add no separate score bonuses or hard cutoffs.

Inspection of the [myGen v4.0.0 addon](https://www.curseforge.com/minecraft-bedrock/addons/bedrock-world-border/files/8896076) revealed that its menu and ScriptEvent inputs use `parseInt`, and its size is a **radius in chunks**. The full side length is `2 × chunks × 16`. These observations come from `scripts/utils.js`, `constants.js`, and `WorldBorderManager.js` inside the published package.

| Requested side | Exact radius input | Nearest stock input | Actual stock side |
|---|---:|---:|---:|
| 3000 blocks | 93.75 chunks | 94 | 3008 blocks |
| 1000 blocks | 31.25 chunks | 31 | 992 blocks |

**Confirmed choice:** keep the stock addon and use 3008 and 992. Store each accepted side length once in the config; derive the menu radius as `side / 32` and the playable half-width as `side / 2`. Validate that each side is divisible by 32. All boundary tests and reported structure eligibility use these sizes. No addon modification is needed.

Use the island's area centroid as its geometric reference. Choose the nearest eight-block-grid point that lies on the island as the border center, breaking distance ties by X then Z. This keeps angular measurements anchored on land even for a crescent-shaped island or a central pond, and makes the Nether center exactly `(overworld_x / 8, overworld_z / 8)` at integer coordinates. Report the centroid, chosen center, and displacement. The safe spawn position can differ from the border center.

For each dimension, square membership is:

`abs(x - center_x) <= side_length / 2 AND abs(z - center_z) <= side_length / 2`.

Use horizontal Euclidean distance for proximity scoring, **not** square membership. Structures near square corners can legitimately be more than 500 Nether blocks away. Check structure access and footprint near edges during finalist inspection; a predicted start inside the border does not guarantee its entire structure is accessible.

An automatically created portal may not appear exactly at the ideal divided coordinates. Its actual placement is part of finalist verification.

## 3. Feasibility and compatibility gates

The project is a staged heuristic search using Chunkbase as the primary external prediction reference, per the user's 7 October 2026 decision. Building an automated Minecraft validator is deferred; in-game finalist confirmation is optional. See [the adopted workflow](CHUNKBASE_WORKFLOW.md). It is not an exhaustive traversal of all 64-bit seeds. Initial measured stage costs are recorded in [PREFLIGHT_STATUS.md](PREFLIGHT_STATUS.md); complete search time per seed remains unmeasured because automated multi-candidate refinement and ranking are not implemented yet.

Use [FragrantResult186/cubiomes-bedrock](https://github.com/FragrantResult186/cubiomes-bedrock), pinned to commit `294c72ab0392dd818a91d293dbd5774d4874d64b`, with its license retained. The [version enum](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/biomes.h) contains `MC_26_50`; `MC_NEWEST` points to a 26.60 preview. It has no explicit `MC_26_52` entry. Explicitly test a proposed `26.52 -> MC_26_50` mapping and record it as unverified until the fixture checks pass. The [26.52 changelog](https://feedback.minecraft.net/hc/en-us/articles/49175370527501-Minecraft-Bedrock-Edition-26-52-Hotfix-Changelog) does not announce world-generation changes; that alone is not proof of compatibility.

The [structure implementation](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.c) uses different random generators for different structures. Trial Chambers use `JAVA_RANDOM`, so treating every structure as dependent on only the lower 32 seed bits would be incorrect. First build a deterministic full-64-bit reference search. Add lower-bit caching/filtering only for individually audited structures, after a benchmark proves that it helps. Trial Chamber checks must retain the relevant upper bits.

Biome/climate data predicts landscape categories. The fork also has reconstructed terrain-density APIs in [cave.h](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/cave.h). Neither replaces Bedrock-generated blocks, trees, water, or actual structure generation. A usable land/water and surface-height estimate is a prerequisite for automated island and mountain scoring. First test whether the cheap biome/climate approximation is adequate; if it is not, evaluate the density API on shortlisted regions. Use vertical sampling rather than assuming density is monotonic with height. If neither approach distinguishes a known island from a known land bridge reasonably, stop at map inspection and improve the terrain estimator before a large search.

Compare enabled capabilities with matching-version Chunkbase examples at positive and negative coordinates. Review candidate shorelines with Terrain enabled, woodland biome potential, mountains and both required Nether structures. Record local placement, viability, Chunkbase markers and actual generation separately. External agreement supports selection; it does not prove all seeds match. Required Nether structures must be checked on the shortlist, while local rejection alone is not proof of absence. Unknown or disputed predictions stay available for review instead of being silently certified or discarded. Mandatory phone fixtures and a BDS validator are no longer prerequisites for a bounded pilot.

## 4. Concrete stack

Use a local CLI and PNG reports first. No Minecraft installation is required to execute the Mac search; the phone can supply the real-world checks. The existing Python 3.13.15, Apple Clang 17, and Git suffice to start. Native builds use setuptools/CFFI, so CMake is not required for this approach.

| Dependency | Proposed pin | Purpose |
|---|---|---|
| Python | 3.13.15 | Orchestration and reports |
| cubiomes-bedrock | commit above | Bedrock biome, climate and structure predictions |
| [CFFI](https://pypi.org/project/cffi/2.1.1/) | 2.1.1 | Small compiled C wrapper with batched calls |
| [NumPy](https://pypi.org/project/numpy/2.5.3/) | 2.5.3 | Raster arrays and vector operations |
| [SciPy](https://pypi.org/project/scipy/1.18.1/) | 1.18.1 | Connected components, distance transforms, morphology |
| [PyYAML](https://pypi.org/project/PyYAML/6.0.3/) | 6.0.3 | Editable search configuration |
| [Matplotlib](https://pypi.org/project/matplotlib/3.11.2/) | 3.11.2 | Diagnostic map PNGs |
| [pytest](https://pypi.org/project/pytest/9.1.1/) | 9.1.1 | Coordinate, topology, seed and regression tests |
| [setuptools](https://pypi.org/project/setuptools/84.0.0/), [wheel](https://pypi.org/project/wheel/0.48.0/) | 84.0.0 / 0.48.0 | Native build tooling |

These pins were successfully installed together on this Intel Mac on 7 October 2026. [requirements.lock](requirements.lock) records all 21 resolved dependency/build/test packages with wheel hashes for Intel macOS/Python 3.13; a hash-checked download verified the lock. [vendor/backend.json](vendor/backend.json) records the pinned backend archive and source hashes. The corrected compiled native adapter and 44 local tests pass. This verifies the local software, not agreement with Bedrock-generated worlds.

Use standard-library `sqlite3`, `argparse`, `json`, `csv`, and `concurrent.futures.ProcessPoolExecutor`. Start with four processes and benchmark 4, 8, and 12. Set numeric library thread counts to one per worker to avoid oversubscription. GPU work is outside the initial implementation.

## 5. Search and measurement definitions

### Search unit and seed traversal

A result is `(full seed, selected island center)`, not just a seed. Analyze multiple islands per seed. Initially search potential centers inside `[-5000, +5000]` on each Overworld axis, configurable and relative to coordinate origin, not natural spawn. Add a finite halo equal to the Overworld half-width, 1504 blocks, so the whole playable square is available for each eligible center. Snap raster bounds outward to the sample grid. A land component touching this outer analysis boundary is unresolved; do not certify it as an island or keep expanding the map indefinitely. Regional reads during refinement stay inside this bounded area.

This extent is a work budget, not a claim that good seeds are concentrated near origin. At 64-block spacing, a full discovery map is roughly 204 × 204, or 42,000 samples per seed before refinement. Benchmark this cost before increasing either the center extent or seed count. Report samples and candidate centers processed as well as seeds processed.

Support a line-separated file of signed decimal seeds and an automatic deterministic sequence. For automatic search, apply the SplitMix64 finalizer to `(candidate_index + run_key) mod 2^64`; perform all arithmetic as unsigned 64-bit. The index starts at zero and never wraps during a run. Worker scheduling must not affect which seeds are tested. Use one canonical signed 64-bit decimal seed for entry into Minecraft; retain its unsigned bit pattern internally. Persist seeds as decimal **text** in SQLite/JSON/CSV to avoid unsigned database overflow or floating-point precision loss. Resume with the same backend and scoring config; a changed config starts a new run or explicitly rescores stored data.

Keep supplied-seed ranking available without automatic search. Chunkbase is the primary external shortlist review source, accessed through its browser UI. No supported bulk/export API or high-volume integration has been verified; local sampling remains the volume-search engine.

### Progressive landscape analysis

1. Generate tiled, batched biome/climate rasters at 64-block spacing for discovery. Use favorable continentalness/erosion/weirdness and biome transitions to prioritize water/basin locations. This is heuristic; record the sampling strategy and do not claim it finds every qualifying island.
2. Refine promising and ambiguous regions at 16-block spacing. Build a water/land/unknown classification using the terrain estimator that passed the small fixture check. A sea-level biome alone cannot conclusively classify land or water.
3. Refine shortlisted shorelines and suspected bridges at 4-block spacing. Narrow connections can be missed even here; final separation is verified in actual Minecraft. Sparse coarse sampling must never be advertised as exact isolation.
4. Use conservative land connectivity, including diagonal contacts, to identify candidate components. Record area, bounding dimensions, equivalent diameter `2 * sqrt(area / pi)`, and maximum span. Preferred diameter refers to equivalent diameter. Report elongation and local height variation for inspection; do not introduce an unspecified shape penalty or claim exact buildable area in version 1.
5. Choose the border center from the component geometry; separately identify a safe spawn/building area. Center choice must be deterministic.

Every terrain result carries `predicted`, `verified`, or `unknown` evidence status. Preserve unknown cells rather than silently treating them as ocean or empty space.

### Water and mountains

Use 180 angular directions at two-degree increments for shortlisted candidates. Along each ray, use the outermost exit from the selected island component as its shoreline, then measure to the next land component. This avoids counting internal ponds as the enclosing water. Search up to 800 blocks beyond that shoreline, clipped to the playable border. A ray with known water throughout that range is open; a ray interrupted by unknown terrain is unknown. Record gap percentiles, coverage, the fraction of directions with a preferred 50–200-block gap, and the largest contiguous opening. At 800 blocks from the ray origin, two-degree rays are about 28 blocks apart: these are visual enclosure estimates, not a shoreline connectivity test.

Starting water enclosure target: surrounding land is found in at least 85% of directions within the search range; 90% earns full enclosure credit. Gap width is a separate preference, with 50–200 blocks ideal. Neither percentage is a hard discovery filter. This distinguishes an isolated open-ocean island from the desired enclosed basin without confusing isolation with enclosure. Exclude unknown observations from numeric claims: report coverage bounds, rather than treating unknown rays as either open or enclosed.

Measure high terrain on external land beyond the water: target 75% directional coverage, within the same 800-block shoreline range. The initial proxy is at least 50 blocks above the measured water surface. This is a permissive high-terrain detector; a broad plateau can satisfy it without looking like a mountain ring. Report local relief, median qualifying height, distance, and largest angular gap, and verify the mountain appearance in game. Keep 50 and 75% tunable until the pilot; increasing them now would be guesswork. Wooded slopes contribute to the wood assessment.

### Wood and building space

Assess these zones separately: island land, and external land within 800 blocks of the island shoreline inside the Overworld border. Normalize wooded fractions over **land area**, excluding water, and report absolute wooded area too. Prefer forest, birch forest, dark forest, taiga and jungle; include other wood-bearing biomes with explicit, version-audited potential weights. Sparse savanna should not automatically receive the same expected density as dense forest. Query predicted surface elevations or calibrated altitude slices, rather than sampling all mountain biomes only at sea level.

The island has no minimum woodland fraction. Its openness preference increases as estimated wooded fraction decreases; do not equate a treeless rocky island with buildable land. Surrounding land retains a provisional 30% wooded-coverage preference and 60% full-credit target. These are soft tuning values; the final requirement is a genuinely abundant, accessible external forest supply. Report absolute wooded area, distance to forest, and distribution around the basin without arbitrary area thresholds. These remain estimates of wood potential, **not tree counts or verified log yields**.

Surrounding wood abundance is mandatory for the selected final world. Bulk proxies prioritize likely candidates; uncertain estimates remain reviewable. Final inspection must confirm extensive harvestable forests on nearby external land and lower slopes, together with open or clearable island ground to build. A bare island is acceptable; a single sparse external grove or a distant forest beyond the border is insufficient. Record coordinates of several surrounding forest patches; determine any numerical tree/log threshold only after calibration.

### Structures and Nether

Build per-structure adapters for placement and viability. Strongholds and Mineshafts need their special APIs/logic; they are not all generic regional features. Return placement candidates separately from viable predictions and actual confirmations. Record horizontal distance and whether a start and estimated footprint are within the playable square. Unknown predictions are explicit.

Use only the nearest viable in-border structure of each type for scoring; list additional structures without extra score. Split the Overworld structure budget as Trial Chamber 25%, Stronghold 25%, Mineshaft 20%, Ancient City 15%, combined secondary structures 15%. Each type's contribution is `exp(-distance / 1000)` when present and zero when known absent; out-of-border structures earn no credit. The secondary contribution is the mean over its five configured types, including known absences as zero. Report all three core targets individually and measure their joint occurrence before considering stricter filters.

For the Nether, retain centers only where both Fortress and Bastion have viable predictions inside the effective square; confirm generation for finalists. Prefer each within 300 blocks, while allowing the full square. Audit shared placement regions while preserving the selected Bedrock structure type. Do not promote a biome-rejected Bastion attempt into a Fortress; actual seed-12345 inspection falsified that previous rule. If prefiltering before island discovery, it must cover the entire possible-center envelope plus the corresponding border half-width; testing only around origin is unsound.

### Initial score, without hidden penalties

Initial category weights: island size 15, island openness 5, water 15, mountains 15, surrounding wood 20, Overworld structures 20, Nether proximity 10. Splitting the former 20 island points into size and openness expresses the revised island preference without adding a hard forest cutoff. These sum to 100 and remain tunable. Buildability, forest accessibility, and the visual mountain setting remain mandatory final inspections.

For positive measurements define `band(v, low, high) = min(1, v / low, high / v)`; use zero when `v = 0`. This gives full credit inside a preferred interval and a gradual decline outside it. Define the components as follows:

| Component | Initial score from 0 to 1 |
|---|---|
| Island size | `band(equivalent_diameter, 300, 700)` |
| Island openness | `1 - island_wooded_fraction`; no minimum island wood requirement |
| Water | `min(enclosure / 0.90, 1) * band(median_gap, 50, 200)`; zero if no surrounding land is found |
| Mountains | `min(high_terrain_directional_fraction / 0.75, 1)` |
| Surrounding wood | `min(surrounding_wooded_fraction / 0.60, 1)` |
| Overworld structures | Weighted sum of the type contributions defined above |
| Nether proximity | Mean of `min(1, 300 / distance)` for Fortress and Bastion; distance zero earns one |

Island openness and surrounding wood are separate contributions. A zero-land surrounding zone has zero wood score. Unknown terrain or unsupported predictions remain unknown, not zero. A candidate with an unknown scoring component receives a score interval: known weighted subtotal to that subtotal plus the unknown weights. It is kept in a separate review list, not assigned a comparable single total.

All fully scored candidates use `sum(weight * component)` with the same config. Final tie-breaks are smaller mountain gap, greater median relative height, then nearer mountains, followed by seed and center for deterministic output. Keep a ranked list of the best center per distinct seed; expose other scored centers for inspection. Show missing preferences alongside every score. The 1200/2000-block overlays describe where structures lie; the 1000-block distance scale controls their continuous proximity preference.

## 6. Files and implementation order

```text
pyproject.toml                 dependency pins and native build
requirements.lock             resolved dependencies with hashes
vendor/cubiomes-bedrock/       pinned source and license
native/bridge.c                batch API, seed conversions, capability wrappers
src/seed_search/
  cli.py                      commands and config validation
  backend.py                  compiled wrapper and version capability checks
  seeds.py                    input parsing, deterministic iteration
  structures.py               versioned structure adapters
  terrain.py                  raster sampling and estimate calibration
  geometry.py                 components, water, high terrain, shape/relief metrics
  wood.py                     separate island/surrounding woodland estimates
  scoring.py                  fixed normalized scoring
  storage.py                  checkpoints and candidate evidence
  reports.py                  JSON/CSV/PNG and inspection checklist
tests/                        synthetic cases and recorded 26.52 fixtures
fixtures/26.52/                provenance, observed samples, expected results
```

1. **Environment and basic backend prototype.** Create `.venv`, resolve and lock dependencies, vendor the pinned C source, and compile a batched CFFI bridge with Apple Clang. Implement seed conversion and explicit version selection. Exit criterion: the native wrapper compiles and repeated biome/structure sample calls are deterministic. This step does not certify features whose adapters have not yet been written.
2. **Single-seed terrain inspection.** Implement input-seed parsing, tiled sampling, multiple-center discovery, and a PNG map. Compare matching-version Chunkbase terrain-enabled island, peninsula/bridge, and mountain/forest examples; establish a usable estimator for candidate screening before automating geometry scores. Add water, high-terrain and wood metrics. Exit criterion: understandable maps and metrics on these examples, with errors and unknowns recorded. Buildability stays a manual check.
3. **Structure scoring and fixtures.** Add the three core Overworld structures and both Nether requirements; then Ancient City and secondary bonuses. Compare each enabled adapter with matching-version Chunkbase predictions and any existing phone observations. Exit criterion: placement/viability disagreements are recorded, negative coordinates and square corners are handled, and required Nether targets can be checked on the shortlist. Actual-world absence must not be inferred from capped website lists. List any unavailable optional capability explicitly.
4. **Supplied-seed ranking.** Read `seeds.txt`, score all discovered centers, store their lightweight metrics and output the best center from each of the top 20 distinct seeds with maps. Keep candidates with unknown scores in a separate review list. Exit criterion: stable rankings, evidence fields, separate island openness and external wood metrics, and a usable inspection report.
5. **Automatic resumable search.** Add deterministic full-seed iteration, four worker processes, parent-owned SQLite writes, and checkpoints. Store completed index ranges or batches so out-of-order worker completion cannot skip unfinished seeds after a restart. Keep lightweight center metrics and aggregate rejection counters; generate full raster/map artifacts only for shortlisted results. Exit criterion: interrupt/resume and different worker counts produce the same tested seed indices and scores under the same config/backend.
6. **Benchmark and tune.** Start with 10 seeds to measure cost, then 100 and 1000 if practical. Follow the pilot measurements below. Tune worker count and sampling gates; audit any lower-bit optimization against the full-seed reference. Choose a time budget from observed throughput before any larger run. A million-seed run is not a prerequisite or an initial commitment.
7. **Review finalists and deploy.** Start with the best five candidates in matching-version Chunkbase with Terrain enabled. Check island/woodland potential, surrounding terrain and required structures against the proposed borders, and record `chunkbase_checked`. Optional phone inspection can confirm actual separation, trees and structure access. Choose the best reviewed match, then set up spawn, portal and borders on the phone before Realm deployment.

Implemented CLI contract (global configuration flag precedes the subcommand):

```sh
python -m seed_search --config search.example.yaml doctor
python -m seed_search --config search.example.yaml probe --seed 12345 --output runs/example
python -m seed_search --config search.example.yaml rank --seeds seeds.txt --output runs/ranking
python -m seed_search --config search.example.yaml search --count 10 --output runs/pilot
python -m seed_search resume --run runs/pilot
```

## 7. Verification and reporting

Meaningful algorithm tests: negative block/chunk conversion; signed seed extremes; seed-bit dependence by structure; diagonal bridges and narrow water gaps; open-ocean islands versus enclosed basins; clipped components; centroid-in-water handling; wooded-fraction denominators; separate wood zones; gradual score changes at preferred interval boundaries; unknown score handling; square-corner eligibility; fixture predictions; out-of-order checkpoints. Test scalar sampling against batched sampling to catch raster scale/coordinate mistakes.

The pilot must retain these measurements, with explicit denominators:

| Measurement | What it tells us |
|---|---|
| Seeds completed, discovery centers, refined centers, and candidates checked for each structure | How much work actually occurred at each stage |
| Centers with each core structure and all three together / centers where all those checks completed | Conditional structure frequency in the sampled candidate set |
| Seeds with at least one candidate satisfying both Nether requirements / completed seeds | Practical yield under this search method and center envelope |
| Median and slow-case stage times, raster samples, peak memory | Likely run cost and where optimization helps |
| Predicted passes and near misses inspected in game; reason for each mismatch | Whether estimates/filter choices need adjustment |

Always distinguish seed counts from center counts: several islands from the same seed are not independent seed trials. These are descriptive results for this search method, not global probabilities over Minecraft seeds. Supplied hand-picked seeds are not a random sample. Zero successes in a small pilot is not evidence that the target is impossible. Inspect some near misses as well as top-ranked candidates; otherwise overly strict filters are hard to notice. Record metric distributions before introducing any new hard threshold.

Test fixtures require recorded game version, seed string, coordinates, observation method, and expected evidence. Synthetic raster tests prove the analysis implementation, not the accuracy of Minecraft predictions.

Each shortlisted candidate folder contains `candidate.json`, `overworld.png`, `nether.png`, and `inspection.md`. Global CSV/JSON summaries include seed, backend commit/model, config hash, border centers/sizes, spawn proposal, island geometry, water/mountain coverage and largest gaps, wood potential by zone, biome inventory, structures/distances/status, total/component scores or score interval, and missing targets. Maps label scale, axes, borders, predicted shoreline, woodland and structures. Do not merge predictions with verified facts. Persist prediction-validation status and observed phone-test results in run metadata, rather than editable search settings.

The primary external selection reference is now [Chunkbase](https://www.chunkbase.com/apps/seed-map), using the matching Bedrock version and Terrain mode for shoreline review. Record website checks as `chunkbase_checked`; only actual phone observations count as in-game verification. The user chose to defer building a Minecraft/BDS validator to save time. Optional finalist phone visits can check thin bridges, tree abundance and actual structures without becoming a prerequisite for the pilot. The claimed 99.99% accuracy is not substantiated by the site's documentation; its published feature and coastline limitations remain in candidate reports.

## 8. What the user needs before the first large algorithm run

User-reported test on 7 October 2026: the addon works on the phone. Import/activation is complete. Its settings, persistence, and enforcement are deployment checks; they do not block algorithm development. Achievements are outside the requirements.

1. Keep Bedrock 26.52 available on the phone and be able to create/inspect test worlds. If the phone or Realm moves to a later version before deployment, rerun compatibility checks for that version.
2. Complete the remaining ranking/refinement pipeline and measure a bounded pilot. Review the shortlist in Chunkbase with matching version/dimension and Terrain enabled. Real-world fixtures and a Minecraft verifier are no longer required before that pilot.

Installing Bedrock on the Mac is optional. The [unofficial macOS launcher](https://github.com/minecraft-linux/macos-builder/releases/tag/v1.8.5) is a separate possible inspection tool and does not establish 26.52 compatibility on this Intel Mac. Its [FAQ](https://mcpelauncher.readthedocs.io/en/latest/faq/index.html) describes the Android/Google Play ownership requirement. Do not make purchasing another edition or installing this launcher a prerequisite for the search.

## 9. Final phone-to-Realm procedure

The simplest path is to **create the chosen seed directly on the phone**, which avoids world conversion or needing a Mac Bedrock client. Set up the final world with the same generation settings used for validation. Alternatively, import a prepared `.mcworld`; that archive must contain world files at its root rather than an enclosing folder. Follow Microsoft's [world-transfer instructions](https://help.minecraft.net/hc/en-us/articles/4409165790605-How-to-Transfer-Your-World-to-Another-Device-in-Minecraft-Bedrock-Edition).

1. Enable cheats for setup. Visit the island and choose a safe ground position.
2. Set the spawn using [`/setworldspawn X Y Z`](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/setworldspawn?view=minecraft-bedrock-stable). This does not teleport existing players; use `/tp @a X Y Z` when everyone is present. Existing beds/respawn anchors can override individual respawn locations.
3. Activate both addon packs. Open `/worldborder:menu`; set the Overworld and Nether independently, with the chosen centers and effective radii. Check the status display. Do not enable another bordered area that allows players to escape the intended region.
4. Verify Fortress and Bastion access, the actual portal, spawn/respawn, the surrounding water and mountains, abundant wood, and border enforcement on all four edges in both dimensions. Confirm that player whitelist settings match the intended restrictions. Record the final spawn and settings in the selected candidate report.
5. Turn Activate Cheats off if desired; recheck addon behavior. The saved spawn remains. Keep a backup of the configured world.
6. Upload/replace the Realm world from the phone. Verify that packs and settings persisted, then teleport arriving players during setup if needed and restore cheats off afterward. Confirm a non-operator is constrained by both borders.

Direct `level.dat` editing is unnecessary for this route. The command workflow avoids reliance on unverified legacy NBT fields.

## 10. Completion definition

Implementation is ready for use when supplied and automatic seed modes are reproducible and resumable, the enabled prediction capabilities agree with recorded version fixtures, diagnostic outputs expose uncertainty, and the real-world finalist checklist distinguishes full matches from near misses. A seed is only labeled **selected and verified** after actual game inspection confirms island separation, a surrounding water-and-mountain setting, buildability, abundant surrounding wood, and both required Nether structures within the playable area. Prefer an open or lightly wooded island. The provisional percentages guide ranking; they do not replace that final landscape check.
