# Bedrock island seed search

Local full signed-64-bit search for **Bedrock 26.52**, explicitly mapped to the pinned Bedrock fork's **MC_26_50** model. Matching-version Chunkbase is the external prediction reference. Actual Minecraft observations remain separate and optional. The Overworld square is 3008 × 3008; the Nether square is 992 × 992 at the Overworld center divided exactly by eight.

The pipeline searches enclosed inner islands, ocean islands, and dry flat mountain basins. Bastion is optional and contributes at most two of the ten Nether proximity points. The default fast mode screens joint Stronghold/Fortress center windows before expensive terrain work. Missing predictions and incompatible nomination envelopes are saved in `stronghold-deferred.json` and `stronghold-deferred-seeds.txt`; they are not proof of absence. Recover those cases in a new bounded rank run with `runs/filter-optimization/config/review-all.yaml`. Known Stronghold misses mean fast mode can overlook worthy worlds. It then refines density coast connectivity, scores terrain and structures, ranks distinct seeds, and checkpoints completed indices in SQLite. This is a bounded heuristic search, not exhaustive coverage. The pinned density model excludes caves, aquifers, decoration and actual chunk interpolation; woodland is a surface-biome proxy.

Large sweeps require a readiness record matching configuration, source/native identity and verified evidence artifacts. Changing `large_search_enabled` cannot open the gate. Work status and finite pilot budgets are in [PROGRESS.md](PROGRESS.md); all completion criteria are in [SWEEP_READY_HANDOFF.md](SWEEP_READY_HANDOFF.md). The large sweep remains unstarted during this goal.

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

The dependency lock targets Intel macOS/Python 3.13. The vendored Bedrock backend commit is `294c72ab0392dd818a91d293dbd5774d4874d64b`. [vendor/backend.json](vendor/backend.json) records 33 source/license hashes. Compile flags are `-O3 -std=c11 -fwrapv`, without fast-math. The direct `native/build.py` compilation entry point now changes to the repository root before compiling; on macOS its standalone CFFI target may be a `.dylib`. Use the supported editable-install path for the Python-importable extension.

Current optimization verification artifacts are under `runs/filter-optimization`; earlier sweep/expansion/preflight/phone/audit evidence remains preserved. [SEARCH_TARGETS.md](SEARCH_TARGETS.md) defines distances and eligibility; [CHUNKBASE_WORKFLOW.md](CHUNKBASE_WORKFLOW.md) defines external review; [GOAL.md](GOAL.md) records the implementation goal and history.

## Verified finite sweep

[Sweep readiness](SWEEP_READINESS.md) records the optimized implementation,112 tests, frozen external regression, website follow-ups and measured20-seed checkpoint/resume pilot with an independent20-seed repeat. Fortress and Stronghold are required and Bastion is optional. The current finite package is `runs/filter-optimization/readiness.json`, with a frozen configuration and2000-seed start/resume commands. The large sweep remains unstarted. See [FILTER_OPTIMIZATION.md](FILTER_OPTIMIZATION.md) for savings, fast-filter recall tradeoffs and candidate-quality limits. Earlier packages are retained as historical evidence.

## Current landscape and structure policy

`search.example.yaml` enables three landscape types sharing one finite eight-refinement budget. `enclosed_island` preserves separation, surrounding water/mountains and external woodland; `ocean_island` requires predicted separation plus majority ocean biomes and density water over a 1400-square window and counts woodland on the island; `mountain_basin` checks a 192-block-wide dry/gentle core and a mountain ring within 800 blocks that is connected to the floor without an inner island/moat. Defaults are tunable preferences, with finite raster/sampling uncertainty exposed. Each type has a separate distinct-seed shortlist.

Fortress and Stronghold markers must be eligible inside their respective exact squares. Missing local Strongholds remain unresolved because the enumerator is incomplete. A missing Bastion cannot veto a candidate. Website review must include Stronghold and Fortress; required checks depend on landscape type. Nothing promotes website evidence to actual Minecraft evidence.

A bounded 64 MiB exact per-seed cache separates seeds, operations and height strides. Analysis persists the sampled candidate terrain under `terrain-cache`; report generation verifies its identity and content hash before reuse. Completed-map cache reuse is invalidated by prediction/configuration/renderer/review changes. The original baseline configuration is retained at `runs/sweep-readiness/config/sweep.yaml` for regression.
