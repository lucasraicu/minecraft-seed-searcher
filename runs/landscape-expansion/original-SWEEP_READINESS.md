> Historical verified workload. Superseded by the user's later landscape/structure requirements on 7 October 2026. Current machine readiness is false; the changed search needs new readiness evidence before a large sweep. See LANDSCAPE_EXPANSION.md. All prior pilot and external observations remain preserved.

# Sweep readiness: Bedrock 26.52

The implementation and measured evidence support a finite local sweep. The large sweep is **unstarted**. This is a bounded heuristic predictor search; it does not promise exhaustive island/seed coverage or actual generated block/tree/structure accuracy.

## Reproducible configuration and backend

- Frozen configuration: [config/sweep.yaml](runs/sweep-readiness/config/sweep.yaml), byte SHA256 `2e588a59bc0e9a0962d5eb2555849b7e9c93cadcb8d576bddc0e83c9e317894e`. All numeric defaults, both required Nether types and fixed 3008/992 squares remain unchanged. Equivalent diameter 300–700 and mountain coverage 0.75 remain preferences.
- Target Bedrock 26.52 explicitly maps to `MC_26_50`, matching the actual website selector **Bedrock 26.50–26.52**. No Java-backend substitution or lower-bit optimization.
- Backend [FragrantResult186/cubiomes-bedrock](https://github.com/FragrantResult186/cubiomes-bedrock/tree/294c72ab0392dd818a91d293dbd5774d4874d64b), pinned commit `294c72ab0392dd818a91d293dbd5774d4874d64b`; all 33 vendored source/license hashes match. Installed license matches the vendored license.
- Python 3.13.15; Intel macOS 15.8; Intel Xeon W-2191B has 18 physical/36 logical CPUs and 64 GiB RAM. All 21 locked distribution versions match; `pip check` passes. Imported native binary SHA256 `8b5365179743aedae8a99d68406df75a5d0360aa70444d5a7233a1aa8072b426`. Complete module/native/config/source/test/evidence identities are in [readiness.json](runs/sweep-readiness/readiness.json).
- Supported native rebuild: `.venv/bin/python -m pip install --no-build-isolation --no-deps -e .`. Build log: [optimized-native-build.log](runs/sweep-readiness/optimized-native-build.log). Direct `native/build.py` relative path is repaired; its standalone macOS target can be a `.dylib`, so editable installation is the supported Python-import path.

## Verification and measured accuracy

` .venv/bin/python -m pytest -q `: **80 passed**, including upper-bit Trial Chamber RNG, negative coordinates, exact square corners/endpoints, all eleven adapter partitions, one-block bridges, finite-raster unknowns, raw/rejected targets, website marker/border handling, unknown preference intervals, woodland denominators, deterministic distinct-seed ties and actual scored-island resume comparisons with one versus two processes. [Tests log](runs/sweep-readiness/tests.log), [verification record](runs/sweep-readiness/verification.json).

` .venv/bin/python -m seed_search regression --output runs/sweep-readiness/regression ` repeats the immutable four-seed website baseline: 159 coordinate rows, 880 structure rows, 874 unique typed correspondences, 6 explicitly managed disagreements, 0 reused starts and **no exact local prediction drift**. Biomes match 153/159 overall and 129/135 surface; 135 height samples have MAE 1 and maximum 5 blocks. Type-specific marker conventions never change square membership. Capped positive lists do not measure complete recall or a false-positive rate. [Regression JSON](runs/sweep-readiness/regression/regression.json), [structure diagnosis/handling](runs/sweep-readiness/STRUCTURE_HANDLING.md).

Bastion rotated-piece biome samples, Ancient City quart/Y=-27 samples and static plus first-three village-associated Stronghold enumeration are diagnosed. General game rules for the six discrepancies are not established, so no coordinate exceptions were encoded. Rejected raw starts remain visible; missing Stronghold completeness is unknown. Website review can resolve required-marker eligibility without inventing native viability or game confirmation. The corrected false seed 12345 Fortress(-152,120) remains excluded.

Fresh browser work used the actual matching-version site with Terrain enabled. Four holdout seed/center reviews checked both dimensions and exact borders; one earlier calibration near miss remains separate, and two Overworld-only controls test rejected/recovered geometry. Negative coordinates and large upper-bit seeds are included. Eight newly retained coordinate rows on three seeds match 8/8 biome labels, height MAE 1.00, max 3; this small chosen subset is not a random accuracy sample. [Fresh holdout reviews](fixtures/bedrock-26.52/fresh-holdout-reviews.json), [calibration](fixtures/bedrock-26.52/fresh-calibration-review.json), [geometry controls](fixtures/bedrock-26.52/fresh-geometry.json), [fresh points](runs/sweep-readiness/fresh-coordinate-comparison.json). Repeat retained point comparisons with `.venv/bin/python scripts/compare_fresh_coordinates.py`.

| Holdout seed | Overworld center | Website review outcome |
|---|---|---|
| 2185194620014831856 | (-3464, -4984) | unresolved |
| 3471015484745077182 | (4432, -2056) | near miss |
| 514794171988716146 | (-4424, 3688) | supported candidate |
| 7300246764159736452 | (-1432, -3248) | unresolved |

Supported seed 514794171988716146 is an open, gently sloping Plains island, center(-4424,3688), equivalent diameter 295.2, water enclosure 1.0, median gap 88, external woodland 0.485. Nearby forests and high terrain/scarps support the intended setting; high-terrain directional coverage 0.322 is below the preferred 0.75, so it is a promising example rather than an ideal uniformly enclosed mountain basin. Its diameter is slightly below the soft preference without changing that preference. Website Fortress(-549,491) and Bastion(-270,648) lie inside Nether center(-553,461), bounds X[-1049,-57],Z[-35,957]. A second Bastion(-695,944) is only 13 blocks from an edge and retains footprint/access risk.

Seed 7300246764159736452 has stronger mountains but unresolved isolation: a stone-colored neck looks connected while live Stony Shore samples there are underwater Y39/46 or near-sea Y62/63. Map/biome colors cannot establish dry connectivity. It remains unresolved; actual thin-bridge confirmation is optional follow-up. Explicit negative website outcomes are shown as near misses; unresolved outcomes remain in review. `chunkbase_checked` is always distinct from `actual_minecraft`, which remains null for these fresh candidates.

## Complete pipeline and pilot

Cheap whole-possible-center required Nether screening runs before expensive terrain. Ambiguous raw targets and a representative negative control remain reviewable. Up to 32 preliminary density components and 8 one-block coasts are reviewed per seed. Stride-one shoreline continuation follows new thin connections, with finite edges/budgets left unknown. Water/mountain rays, external-land woodland denominator, island openness, every configured score, structures and deterministic ranking are implemented. Parent-owned SQLite commits each completed index atomically and rejects changed configuration/backend/seed/evidence identity on resume.

Pilot commands (completed; bounded, not the large sweep):

```sh
.venv/bin/python --version
.venv/bin/python -m seed_search --config search.example.yaml search --count 100 --start-index 0 --workers 8 --stop-after 10 --output runs/sweep-readiness/pilot-100
.venv/bin/python -m seed_search resume --run runs/sweep-readiness/pilot-100 --workers 8
```

Initial ten seeds were measured with four processes before optimization; their saved analysis 623.88s plus map 141.59s gives 765.46s total. The optimized ten-seed repeat used eight processes: 249.95s analysis plus 122.63s maps=372.58s. The current-identity first-ten checkpoint took 359.65s total including 117.17s export. It exactly matches all 74 candidate predictions/rejection/count fields of the uninterrupted repeat; only measured timings/RSS/PIDs were excluded. The source test independently compares one versus two workers with scored candidates. [Resume proof](runs/sweep-readiness/resume-proof.json). Supplied-seed `rank` also completed a one-seed small-envelope smoke with actual maps in 30.94s.

The final 100 unique indices 0..99 produced **781 scored centers**, 100 seeds with predicted both required Nether starts, and 287 centers with all three core Overworld starts. Total across checkpoint/resume invocations **2474.18s (41.24min)**, analysis 1890.54s, reports 583.63s; 24.742s/seed including both exports (145.5 seeds/hour). Worker peak 244.1MiB; parent peak 1062.9MiB. These are process peaks, not measured simultaneous aggregate RAM. Each invocation used eight actual worker PIDs. Recommend **8 processes**, one numeric thread each, as the measured full-pipeline setting; global optimal worker count is not claimed. The finite 60-minute pilot budget was recorded before launch and was respected. [Invocation records](runs/sweep-readiness/pilot-100/run.json), [stage/memory/counter measurement](runs/sweep-readiness/pilot-measurements.json).

Summed worker-stage seconds (not wall time):

| Stage | Seconds |
|---|---:|
| discovery | 41.06 |
| structures | 117.30 |
| preliminary | 518.40 |
| coast | 7144.42 |
| landscape | 6111.89 |
| scoring | 15.35 |

All seeds/centers/rejection/deferred reasons are saved in [JSON](runs/sweep-readiness/pilot-100/candidates.json), [CSV](runs/sweep-readiness/pilot-100/candidates.csv) and SQLite. Candidate JSON includes seed, exact centers/borders, metrics/scores, raw/viable/website statuses and outstanding review. Shortlist folders include Overworld/Nether maps and inspection notes, including a separate `chunkbase_supported` group. Previous generated shortlist views are preserved in `report-history` on refresh so stale folder ordinals do not remain in the active rankings. Frozen baseline/user/phone evidence was preserved; this directory is not a Git checkout.

## Finite sweep budget and tested commands

Future workload: 2,000 full signed 64-bit seeds, indices 100..2099 (no overlap with pilot), current fixed ±5000 center axes, identical density/budget/scoring configuration. The readiness gate caps count at 2,000 and hashes source/tests/evidence; `large_search_enabled` remains false. Estimates assume the measured machine/workload: amortized analysis plus both observed export costs gives **10.7 hours**; applying the full pilot seconds/seed to every future seed gives **13.7 hours**. A 1.5× uncertainty envelope is approximately 16.0–20.6 hours. These are scoped extrapolations, not guarantees, and exclude manual website/game checks. The initial finite sweep count is chosen to bound time and memory: measured decoded 100-seed results occupy 114.98 MiB, extrapolating to 2.25 GiB for 2000, with a four-buffer 9 GiB allowance plus roughly 3 GiB report/worker overhead on the 64 GiB host. This is a workload estimate, not a measured future memory peak. See [memory budget](runs/sweep-readiness/memory-budget.json). The future sweep is finite and resumable, with no claimed candidate-yield guarantee from 100 seeds.

The exact finite 2,000-seed start command also passed the evidence gate with `--dry-run` (exit 0); its output says `would_start_sweep: false`. Resume flags passed against the actual partial/current pilot; the future resume path intentionally has no checkpoint before the sweep starts. Argument order matches CLI help. Full command-validation evidence is in [command-validation.json](runs/sweep-readiness/command-validation.json).

Start (unstarted):

```sh
/Users/lucasraicu/Downloads/minecraft-seed-searcher/.venv/bin/python -m seed_search --config /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/sweep-readiness/config/sweep.yaml search --count 2000 --start-index 100 --workers 8 --readiness /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/sweep-readiness/readiness.json --output /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/sweep-2000
```

Resume after an interruption:

```sh
/Users/lucasraicu/Downloads/minecraft-seed-searcher/.venv/bin/python -m seed_search resume --run /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/sweep-2000 --workers 8
```

## Managed limits and evidence preservation

- Raw density omits caves, aquifers, decoration and actual chunk interpolation; stride-eight interior estimates and ±5-block observed shoreline uncertainty can miss subtle features. One-block coast work improves connectivity within that model, not exact liquid/block proof.
- Finite coarse discovery, 32/8 refinement budgets and 1408-block patches may miss or defer islands. Rejection/deferred counts and reasons are explicitly exported; no whole-world coverage claim.
- Forest groups are surface-biome wood proxies, not counted trees/logs. The fresh review supports external woodland appearance; access/harvesting remains optional actual-game evidence.
- Starts and website markers establish square-point membership only; full accessible footprints, entrances, safe portal arrival and spawn/border behavior remain unknown. Capped website lists are positive evidence, not absence/recall proofs.
- Stronghold completeness and six baseline structure disagreements remain explicitly managed through unknown preference intervals/raw review. They are not hidden by widened tolerance, failed-Bastion promotion or bespoke coordinate exceptions.
- Further source/config/backend/evidence changes invalidate the readiness record and incompatible checkpoints. `review` reads persisted configuration; retain this project/.venv and all referenced evidence/config files for resume.

The persistent goal is completed only after final artifact/gate checks and the completion notification. The notification is not a command to start the sweep.
