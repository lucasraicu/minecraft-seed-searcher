# Active baseline sweep workflow

The CLI and website default to `dynamic-envelope-1664-v1`: a sliding 1664×1664 Overworld window inside `[-2000,2000)²`, with an 832×832 Nether window centered at exactly one eighth of the selected center. Centers remain inside ±1168 and use the nearest valid multiple of 16 per axis, falling back to 8 while retaining every captured start in that cell. The selected center is a constrained weighted centroid, not the Stronghold coordinate or an observed player spawn.

Both `config/realm.yaml` and `config/realm_1664.yaml` are generated from the validated dynamic constructor. The website's profile metadata is generated with:

```sh
.venv/bin/python scripts/export_web_policy.py
```

## What a baseline survivor establishes

The engine checks 14 structure categories, 13 Overworld biome families on the defined four-Y lattice, and all five Nether biome families on a world-aligned 13×13 grid at Y=64. Below any hard floor rejects; below an editable ideal consumes one category deficit, regardless of the number of missing starts. Stronghold, Mansion, Monument, Outpost, Fortress and Bastion are strict categories. B is bounded to 0–2.

Monuments and Shipwrecks use the pinned structure placement and biome-viability predictor. Neither a coastline shape nor a navigable ocean corridor is required. **The active sweep has no terrain-height, land-fraction, river, ravine or island-shape filter.** The explicit CLI terrain tools remain available for optional investigation.

Scores include the resolved one-time structure milestones, repeating Village/Trial/Shipwreck/Portal/Mineshaft scalers, sampled luxury biomes, optional structure inventories and the structure-based 512-block hub bonus capped at 40. Igloo points use the pinned basement PRNG prediction. A cave biome ID does not establish an open mega-cave entrance: that optional actual-world bonus remains unawarded without appropriate evidence. The leaderboard orders deficit tier ascending, score descending, weighted radial distance ascending, then distance from origin ascending. Legacy policy formulas and ordering remain versioned separately.

## Build and launch

Build artifacts belong to the local machine and are not included in Git. An explicitly installed OpenMP runtime is required for parallel execution. On this workstation:

```sh
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/dynamic-baseline-1664/native \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python -m seed_search.web.server 3000
```

Use the selected build flags/settings recorded in the final benchmark report when reproducing the measured result. Rebuilding with the portable command above does not automatically reproduce an adopted PGO or host-instruction build.

The website supports finite runs above 100,000 seeds, exact full64 starting indices, saved-run selection, pause and identity-checked resume. Edit live structure targets using the steppers; launch validates every target against the selected policy. Planning calculator controls are labelled separately and do not relax live required biome families or hard floors. The production pipeline reserves two CPU slots for record preparation and persistence and accepts at most 34 native threads per scan process.

A CLI example is:

```sh
.venv/bin/python -m seed_search --config config/realm.yaml scan \
  --executor native --native-build runs/dynamic-baseline-1664/native \
  --native-threads 34 --native-batch-size 16384 \
  --retention survivors --prediction-scale \
  --start-index 0 --count 1000000 --output runs/my-dynamic-shard
```

For another node, build against that node's runtime and measure its settings. Allocate disjoint index intervals with the same explicit policy and run key. The runtime disk gate is conservative: compact retention defaults to 32 projected bytes/input; full retention defaults to 65,536. A 36B campaign must use appropriately sized finite shards and available capacity, rather than bypassing the disk gate.

## Saved versions and checkpoints

Historical `2048 marine` and `2048 two-group` profiles remain selectable. Their YAML snapshots are `config/realm_2048_marine.yaml` and `config/realm_2048_two_group.yaml`. The prior terrain-enabled website is preserved on `saved/terrain-enabled-ui` at `63728a35184be99be54ddde78cbe6aedeceea371`.

A checkpoint retains its original geometry, policy and computation identity. An old checkpoint can be inspected; it cannot silently resume with an incompatible new engine. Keep its original build/source checkout to resume it, or start a new dynamic run. `git worktree add ../minecraft-seed-searcher-terrain saved/terrain-enabled-ui` opens the saved version independently.

## Evidence and verification

Map biomes are an on-demand, cached Y=63 sample overlay. Its geometry follows the candidate's reported bounds and selected center, including exact Nether scaling. It does not generate heights or become a sweep gate.

The 100-block spawn metric is measured from supplied coordinates to the selected hub, before rounding. Unknown spawn stays unknown. The optional feed filter excludes unknown coordinates; it does not certify first-player placement or change native eligibility. No Bedrock client is available for a real first-join observation.

The website's BDS action starts an owned background subprocess using the existing `verify-biomes` CLI, with 1–16 explicit surface witness points. The provider enforces pinned identity, attempt budgets, cache policy and its Docker ownership/cleanup protocol. Pause a sweep before starting verification. Partial point evidence stays partial; failures never mark a Realm verified. The old synthetic `99.8%`/portal-room claims are removed and stub-shaped stored certificates are not trusted by the website.

Actual generated structure counts, complete Stronghold recall, portal rooms, loot and initial player spawn remain outside the current automated surface-point provider's established evidence. A predictor survivor is a search result for further validation, not a certified playable world.

## Performance evidence

`LATEST_PUSH_REVIEW.md` and the dynamic benchmark report record the final checks and measured rates. Historical 2048 rates and the blueprint's cluster/yield projections do not establish a rate or survivor probability for this dynamic policy. Compiler flags, preflight culling, work chunks and OpenMP settings must be measured using the same policy and disjoint tuning/held-out cohorts.
