# Bedrock island seed search

## Stronghold-centered Realm search (schema 5)

Current target: **4000×4000 discovery in each dimension, 1536×1536 Overworld, 896×896 Nether**. The [compact search implementation plan](COMPACT_SEARCH_IMPLEMENTATION_PLAN.md) is implemented; measured results and remaining prediction limits are in [COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md](COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md). Older benchmark results retain their original geometry. Use fresh run directories for changed computation identities.

The default `search`, `doctor`, and `benchmark` commands now use the new Realm contract. Explicit schema 3/4 configurations and existing historical checkpoints retain their legacy interfaces. New results are predictions until actual Bedrock evidence establishes otherwise.

The new universal baseline discovers Strongholds in `[-2000,2000)` on both axes and records each anchor separately. Its mandatory Overworld region and Realm border are 1536×1536, centered on that Stronghold and allowed beyond discovery bounds. Village, Trial Chamber, Ancient City and Mineshaft are mandatory, together with the anchor, a broad initial Nether Fortress and at least two of five wooded families. Missing unvalidated predictions remain pending. Savanna is neutral and caves are manual-only.

V1 finds islands with connected surrounding water; V2 finds mountain basins and accepts jagged or steep interiors. Both independently consume the same saved provisionally qualified baseline pool. The former combined variant is retired. Formation-fit status stays separate; promising outside/uncertain footprints remain recorded. Final Nether bounds are 896×896 around exact Stronghold/8, requiring Fortress and Bastion. Exact generated structure enumeration and complete natural-ground validation remain unsupported/unverified; no fully verified Realm candidate is claimed.

The active terrain preferences now require **250,000 square blocks of one connected main island**, favor about **650,000**, and permit area-equivalent diameters up to **1300 blocks**. Disconnected islets do not add to the main island's area; irregular outlines are allowed and border fit uses the sampled footprint. V2 uses an inclusive **surrounding mountains** policy: substantial elevated terrain on at least **16 of 32 directions**, at least **24 blocks** above the sampled interior, at **150–700 blocks**, with no empty angular gap above **135°**. Separate mountains, open passes, rough interiors and water interiors are allowed; strict connected-arc shape is an optional historical policy. These are nomination preferences, with actual geometry verification separate. See [terrain preference update](TERRAIN_PREFERENCE_UPDATE.md). Existing results retain their old policy and need a fresh matching computation identity for further work.

```sh
.venv/bin/python -m seed_search compatibility --output runs/compatibility.json
.venv/bin/python -m seed_search baseline --count 1000 --output runs/my-realm
.venv/bin/python -m seed_search status --run runs/my-realm
.venv/bin/python -m seed_search inventory --run runs/my-realm --limit 20
.venv/bin/python -m seed_search inventory --run runs/my-realm --candidate='<seed>:<sx>:<sz>' --all-starts
.venv/bin/python -m seed_search resume --run runs/my-realm --workers 24
.venv/bin/python -m seed_search terrain --run runs/my-realm --variant all --limit 1
.venv/bin/python -m seed_search results --run runs/my-realm --variant v2 --export
.venv/bin/python -m seed_search verify-terrain --run runs/my-realm --variant v2 --top 1
.venv/bin/python -m seed_search verify-biomes --run runs/my-realm --candidate='<seed>:<sx>:<sz>' --points points.json
.venv/bin/python -m seed_search verify-realm --run runs/my-realm --candidate='<seed>:<sx>:<sz>'
.venv/bin/python -m seed_search verify-caves --seed 12345 --stronghold-x 0 --stronghold-z 0 --provider predictor --output runs/manual-caves.json
```

Use `--config config/realm.yaml` before the command for the explicit profile. Above 1000 inputs, scans need `--prediction-scale`; the persisted compatibility report records that scale is prediction-only. Benchmarks explicitly exercise this mode. `rescore --run <run> --policy <profile.yaml>` changes recorded bonus/score weights without world-generation queries. An interrupted revision resumes with `rescore --run <run> --resume`, using its persisted policy; status remains available while ranking/generation are guarded. JSONL, CSV and readable summaries export every candidate pair, independent of shortlist limits. Export sets publish atomically through `results/current`; resolve that generation once when reading multiple files.

The default eligibility pass records one viable structure-start witness where presence is enough, and visits biome points in small batches until two wooded families are found. It retains incomplete scores and durable inventory tasks. `inventory` completes family-presence bonuses and the canonical biome sample; it does not imply complete start counts or actual generation. `--all-starts --candidate` saves a separate complete bounded predictor start audit. Terrain and verification nominations complete their candidate's scoring inventory before use. `search.inventory_mode: complete` remains available for complete baseline scans.

Biome sampling uses a versioned world-aligned lattice, caches exact full-seed points, and preserves in-border positive witnesses across overlapping borders. A bounded 128-point refinement can resolve additional wooded positives; misses remain pending. Nether and End samples are supplemental; End biome IDs are predictor classes, with actual Bedrock names unverified. All 22 exposed regional/start structure families are available, including buried treasure and the correctly initialized End dimension. Monster rooms and special terrain/decorator features still require separate support.

Docker runs only for explicitly selected verification requests, including optional random low-ranking audits to detect predictor misses. It does not run per baseline seed or automatically check cave diversity. Use `verify-terrain --top N --borderline N --unusual N --random N` to select observations under the persisted budget. The pinned runtime is BDS 1.26.52.3; the native MC_26_50 predictor is separately labeled approximate. The initial verifier limits one server and 16 tiles per request; larger footprints return partial status until their budget is explicitly expanded. Verified-generation ground masking, full-sized formation controls and rare-event recall remain gates, not inferred from the small extraction tests.

Verification skips cached observations by default. `--include-cached` explicitly reviews them without charging new-attempt slots; `--retry-failed` retries failures within the remaining budget. `calibration --run <run>` reports independent V1/V2 formation diagnostics only when complete actual geometry evidence is available. Partial results never become negative truth, and selected-cohort metrics are not population accuracy estimates.

Terrain work uses a fixed saved membership revision for both variants and durable center/resolution/halo queues. Repeated limited invocations advance a rotating pool cursor, retain lower-ranked and failed work, and reuse exact prediction rasters across variants. `--pool-revision pool-00000001` selects a saved membership; `--new-pool-revision` explicitly includes later baseline arrivals. Automatic halo expansion has a resource cap; `--continue-deferred-halos` permits one additional queued expansion per center. Status separates queued pending/deferred units from pool members whose work has not been initialized. Raw terrain storage cost and retention limits still need measurement and policy.

`verify-biomes` explicitly loads up to 16 points in one BDS world. `points.json` is an array such as `[[100,200],[-300,400]]`; every point must be inside the candidate's Stronghold-centered Realm. Stable observed names can establish two wooded families, while absent or unsupported samples stay unknown. Actual surface evidence and bonus intervals are saved separately from prediction scores and exposed in exports. This command never certifies the required structures, exhaustive biome coverage, or whole terrain geometry, and never invokes cave scanning.

Measured performance and exact supported/unverified scope are in [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md), [REALM_IMPLEMENTATION_RESULTS.md](REALM_IMPLEMENTATION_RESULTS.md) and `runs/realm-implementation-2026-10-10/`.

The completed [master implementation](MASTER_IMPLEMENTATION_PLAN.md) adds mandatory final-square Fortress/Bastion prediction checks, exact eight-Y noise reuse and native quart deduplication. `config/realm.yaml` selects 18 OpenMP threads for its single-process terrain scheduler running alone; baseline remains 30 processes with one native/numerical thread each. Concurrent discovery/terrain/BDS needs a separately measured smaller profile. The code defaults retain serial compatibility. `terrain.scheduler: priority` enables the experimental durable 3:1 ranked/oldest dispatcher; rotation remains the measured default. Native thread counts and numerical-library limits are separate.

`native/build.py` builds a portable serial extension by default. On this Intel Mac, its optional host-only OpenMP build is:

```sh
ARCHFLAGS='-arch x86_64' SEED_SEARCH_OPENMP_PREFIX="$PWD/runs/master-implementation-2026-10-10/openmp/install" .venv/bin/python native/build.py
```

Keep that local runtime prefix while using the OpenMP extension. Its library hash is included in computation identity. Rebuild serial before moving to a machine without that runtime; unsupported multi-thread requests fail explicitly. No AVX ISA flag is shipped by default.

The bounded lower32 experiment has its own checkpoint and explicit raw-only ranking policy:

```sh
.venv/bin/python -m seed_search.realm.raw scan --count 4096 --threads 4 --output runs/raw-diagnostic
.venv/bin/python -m seed_search.realm.raw siblings --selection runs/raw-diagnostic/raw-selection.json --limit 128 --output runs/raw-siblings
.venv/bin/python -m seed_search raw-scan --count 4096 --mode presence --threads 18 --output runs/raw-presence
.venv/bin/python -m seed_search raw-scan --count 4096 --mode capped --ranking geometry --output runs/raw-geometry
.venv/bin/python -m seed_search raw-adaptive --selection runs/raw-geometry/geometry-selection.json --budget 4096 --output runs/adaptive-siblings
```

Use `--resume` with the original range/selection to finish interrupted chunks. Chunk/thread sizes may change while the selection identity stays fixed. Raw counts cover conservative envelopes for all permitted Stronghold centers; they cannot establish joint-center feasibility or generated-world absence. Full64 siblings pass the same required-structure baseline before terrain/verification. Scanner and terrain writes check physical workspace growth/free space as well as the existing logical raster cap. BDS checks host evidence and Docker filesystem headroom before generation. No automatic evidence deletion is performed.

Raw `presence`, `capped`, `complete`, and `reference` modes have different explicit contracts. Only capped/reference counts support the legacy density score. Geometry ranking and adaptive 1/4/16 sibling rounds are bounded experiments with an exploration reserve; independent full64 remains the default because the held-out CPU comparison did not meet the adoption gate. A full32 sweep is not justified by native throughput alone.

## Historical schema 3/4 profiles

The following sections document the preserved earlier profiles and their results. Their boundaries, categories, and defaults apply when an explicit historical configuration is supplied.

> **8 October implementation:** 2304 × 2304 Overworld / 928 × 928 Nether; four categories; mandatory Stronghold and Fortress; separate weighted biome bonus; bounded lower32/upper32 mode. Implementation and bounded verification are complete. Reference search is recommended after the two-key comparison; staged search remains available. The older sweep package is historical. No production sweep has started.

Local full signed-64-bit search for **Bedrock 26.52**, explicitly mapped to the pinned Bedrock fork's **MC_26_50** model. Matching-version Chunkbase is the external prediction reference. Actual Minecraft observations remain separate and optional. The Overworld square is 2304 × 2304; the Nether square is 928 × 928 at the Overworld center divided exactly by eight.

The pipeline searches structures-only locations, enclosed inner islands, ocean islands, and dry flat mountain basins. Bastion is optional and contributes at most two of the ten Nether proximity points. The default fast mode screens joint Stronghold/Fortress center windows before expensive terrain work. Missing predictions and incompatible nomination envelopes are saved in `stronghold-deferred.json` and `stronghold-deferred-seeds.txt`; they are not proof of absence. Recover those cases in a new bounded rank run with `config/review-all.yaml`. Known Stronghold misses mean fast mode can overlook worthy worlds. It then refines density coast connectivity, scores terrain and structures, ranks distinct seeds, and checkpoints completed indices in SQLite. This is a bounded heuristic search, not exhaustive coverage. The pinned density model excludes caves, aquifers, decoration and actual chunk interpolation; woodland is a surface-biome proxy.

Large sweeps require a readiness record matching configuration, source/native identity and verified evidence artifacts. Changing `large_search_enabled` cannot open the gate. Work status and finite pilot budgets are in [PROGRESS.md](PROGRESS.md); current results and commands are in [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) and [SWEEP_COMMANDS.md](SWEEP_COMMANDS.md). The production sweep remains unstarted.

## Commands

From this project directory, with the existing `.venv`:

```sh
.venv/bin/python -m seed_search doctor
.venv/bin/python -m seed_search regression --output runs/sweep-readiness/regression
.venv/bin/python -m pytest -q
.venv/bin/python -m seed_search search --count 10 --workers 4 --output runs/new-pilot
.venv/bin/python -m seed_search rank --seeds seeds.txt --output runs/new-ranking
.venv/bin/python -m seed_search resume --run runs/new-pilot
```

Specify `--config path.yaml` **before** the command. Automatic enumeration applies the SplitMix64 finalizer to `(index + run_key) mod 2^64`; indices never wrap in a run. Supplied seeds are one signed decimal integer per line. JSON/CSV/SQLite seeds are decimal text. Worker scheduling does not affect predictions or ranking.

`search --dry-run` validates the finite workload and readiness gate without starting it. `--stop-after N` saves a partial bounded run for resume verification. Resume checks the original configuration, complete backend/source identity and seed sequence; incompatible resumes fail. Each completed seed is committed independently, so interrupted or out-of-order work is rerun without skipping an unfinished index.

Outputs include all center metrics and explicit rejection/deferred reasons, separate numeric rankings and interval review lists, and shortlist folders with `candidate.json`, Overworld/Nether PNGs and `inspection.md`. Required disputed raw starts remain available for Chunkbase review; they cannot be presented as website-confirmed eligible first. Marker/start border membership is separate from accessible structure footprints.

Optimization details and controlled measurements are in [FILTER_OPTIMIZATION.md](FILTER_OPTIMIZATION.md). Raw MT structure layouts alone can share lower32-bit cache keys; full seeds still determine biome/terrain/viability, and the seed sequence is unchanged. The prior readiness records do not validate this changed algorithm; use the current command and record in [SWEEP_READINESS.md](SWEEP_READINESS.md).

Fresh actual website reviews can be recorded in the schema implemented by `review.py`, then imported:

```sh
.venv/bin/python -m seed_search review --run runs/new-pilot --evidence path/to/fresh-review.json
```

`chunkbase_checked` never becomes an actual-game observation. [Frozen external regression](fixtures/bedrock-26.52/chunkbase-accuracy-audit.json) contains 159 coordinate and 880 structure rows. Six structure discrepancies remain explicitly reviewable. Exact local baseline comparisons detect new drift even within per-type empirical marker conventions. Capped positive lists do not establish complete recall or a false-positive rate.

Diagnostic `benchmark`, `probe` and actual-phone `compare` commands remain available. Their historical artifacts are preserved; stage microbenchmarks alone do not establish end-to-end throughput. The user-skipped Overworld point is not requested again.

## Native build and provenance

The supported install/rebuild path is:

```sh
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m seed_search doctor
```

The dependency lock targets Intel macOS/Python 3.13. The vendored Bedrock backend commit is `294c72ab0392dd818a91d293dbd5774d4874d64b`. [vendor/backend.json](vendor/backend.json) records 33 source/license hashes. Compile flags are `-O3 -std=c11 -fwrapv`, without fast-math. The direct `native/build.py` compilation entry point now changes to the repository root before compiling; its standalone CFFI target is `_native.abi3.so`, matching the Python loader. Prefer the supported editable-install path.

Current implementation verification artifacts are under `runs/implementation-2026-10-08`; `runs/filter-optimization` contains historical measurements; earlier sweep/expansion/preflight/phone/audit evidence remains preserved. [SEARCH_TARGETS.md](SEARCH_TARGETS.md) defines distances and eligibility; [CHUNKBASE_WORKFLOW.md](CHUNKBASE_WORKFLOW.md) defines external review; [GOAL.md](GOAL.md) records the implementation goal and history.

## Sweep verification

The prior `runs/filter-optimization/readiness.json` is incompatible with the new geometry and prediction identity. Final tests, two run keys with 256 inputs per search mode, three 20-seed quart comparisons, worker/resume tests and new-border external reviews are being sealed under `runs/implementation-2026-10-08`. Do not reuse the historical 2000-seed command. [SWEEP_READINESS.md](SWEEP_READINESS.md) tracks the gate.

## Enumeration and biome ranking

`full_64_bit_reference` is the default. `lower32_staged` examines 10,000 distinct raw low32 layouts, keeps 48 by raw cluster proximity plus 16 deterministic exploration selections, and evaluates four unique high32 siblings per layout. Raw placement is shared only for eight audited families. Strongholds, Trial Chambers, Mineshafts, terrain, biomes and final viability are evaluated for each complete seed. The strategy is biased; per-category useful yield must justify any default promotion.

All four categories keep the same mandatory structures. Structures-only retains a base score out of 30; terrain categories retain a base out of 100. A separate sampled resource-family bonus adds at most five points. Surface, Nether and unmeasured cave coverage are labeled separately; biome variety never repairs failed eligibility. Weights and sampling are documented in [BIOME_DIVERSITY_PLAN.md](BIOME_DIVERSITY_PLAN.md). Exact quart reuse shares raw-land booleans only; height and biome sample coordinates remain independent.

## Current landscape and structure policy

`search.example.yaml` enables four categories. The three terrain types share a finite eight-refinement budget; structures-only has its own two-center budget and skips terrain qualification. `enclosed_island` preserves separation, surrounding water/mountains and external woodland; `ocean_island` requires predicted separation plus majority ocean biomes and density water over a 1400-square window and counts woodland on the island; `mountain_basin` checks a 192-block-wide dry/gentle core and a mountain ring within 800 blocks that is connected to the floor without an inner island/moat. Defaults are tunable preferences, with finite raster/sampling uncertainty exposed. Each type has a separate distinct-seed shortlist.

Fortress and Stronghold markers must be eligible inside their respective exact squares. Missing local Strongholds remain unresolved because the enumerator is incomplete. A missing Bastion cannot veto a candidate. Website review must include Stronghold and Fortress; required checks depend on landscape type. Nothing promotes website evidence to actual Minecraft evidence.

A bounded 64 MiB exact per-seed cache separates seeds, operations and height strides. Analysis persists the sampled candidate terrain under `terrain-cache`; report generation verifies its identity and content hash before reuse. Completed-map cache reuse is invalidated by prediction/configuration/renderer/review changes. The original baseline configuration is retained at `runs/sweep-readiness/config/sweep.yaml` for regression.
