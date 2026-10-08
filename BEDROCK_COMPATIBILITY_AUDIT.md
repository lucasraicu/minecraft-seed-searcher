# Bedrock compatibility audit and implementation plan

Historical planning/audit evidence is retained below. Current implementation and verification progress is in [PROGRESS.md](PROGRESS.md); the active completion criteria are [SWEEP_READY_HANDOFF.md](SWEEP_READY_HANDOFF.md). The expanded search, measured pilot, fresh selection checks and finite readiness verification are complete; current outcomes and remaining limits are in [SWEEP_READINESS.md](SWEEP_READINESS.md).

Audited 7 October 2026. Target: Bedrock 26.52, local search on the Intel Mac, Chunkbase review of finalists. This audit changes no algorithm or configuration.

**Recommendation: retain the current Bedrock fork, resolve the known discrepancies, and finish the search workflow. A wholesale engine replacement is not justified by the evidence reviewed.** This delivers a practical Bedrock seed finder with declared prediction limits; it does not establish complete block-for-block game emulation.

## What is implemented

| Area | Finding |
|---|---|
| Native backend | `vendor/backend.json` pins FragrantResult186/cubiomes-bedrock at `294c72ab0392dd818a91d293dbd5774d4874d64b`. This is not unmodified Java Cubiomes. |
| Bedrock placement | `vendor/cubiomes-bedrock/finders.c:24` contains Bedrock structure configurations. `finders.h:896` dispatches between Java-style and Bedrock RNG. The wrapper's trial chambers use the Java-style exception; its other ten type configurations select Bedrock RNG. |
| Seeds and concurrency | `seeds.py` preserves signed 64-bit numeric seeds. `backend.py` serializes native access within a process; process workers provide parallelism. Retain these safeguards. |
| Version | `native/bridge.c:22` hardcodes `MC_26_50`. Configuration accepts the specific 26.52/26.50 mapping, but does not validate `game.edition`. Chunkbase's matching version group supports the chosen comparison; it does not prove every generation rule is identical. |
| Coverage | Overworld/Nether biome queries and eleven structure types are exposed. End queries are explicitly rejected. Other structures, exact tree abundance, structure footprints and actual portal arrival are not implemented. |
| Terrain | `ss_heights` estimates raw density. It omits caves, aquifers, decoration and actual chunk interpolation. The cheaper discovery proxy has larger errors. |
| Search | Only `doctor`, `benchmark`, `probe`, and `compare` exist. Connected-component diagnostics and woodland biome masks exist; complete landscape scoring, ranking and resumable search do not. |
| Review policy | `CHUNKBASE_WORKFLOW.md` adopts Chunkbase review, but configuration, CLI gate text and run metadata still reference mandatory phone/game validation. `require_validated_capabilities_before_large_search` is declared but not consumed by the implementation. |

Current checks: **44 tests passed in 0.80 seconds**, including all 33 recorded vendor source hashes. `python -m seed_search doctor` successfully called the installed native backend and reported model 26.50. These checks establish software consistency, not full Minecraft accuracy.

## Existing external evidence

The saved [four-seed audit](runs/accuracy-audit/REPORT.md) contains 159 coordinate checks and 880 structure rows. Its results were reviewed here; the website collection was not repeated.

- Surface biomes: 129/135 exact matches; all six disagreements lie within one or two blocks of a local biome boundary.
- Sampled Nether biomes: 20/20; cave biomes: 4/4 at the sampled height, with three differing vertical ranges.
- Density terrain: mean difference one block, maximum five; four disagreements on the land/water height threshold.
- Structures: 874/880 have a local viable start within 64 blocks, but only 477 coordinates match exactly. The 64-block correspondence rule is a diagnostic heuristic, not a certified correctness tolerance.
- Unresolved structure records: two missing strongholds, two rejected ancient cities, and two rejected bastions. The bastion case repeats for seeds sharing their lower 32 bits.
- The previously false Fortress at seed 12345, Nether `(-152,120)`, came from our adapter's promotion of a rejected Bastion. That fix and its negative regression test are already present.

These are bounded predictor comparisons. The samples do not establish complete recall, false-positive rate, or whole-island separation.

## Library research

| Candidate | Assessment |
|---|---|
| [Cubitect/cubiomes](https://github.com/Cubitect/cubiomes) | Upstream explicitly targets Java. Replacing our fork with it would not supply the required Bedrock structure rules. |
| [Current Bedrock fork](https://github.com/FragrantResult186/cubiomes-bedrock) | Best starting point for this project: already integrated, built on this Mac, and externally sampled. The [pinned source](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.c) demonstrates substantive Bedrock logic. Keep the exact revision until a tested change is warranted. |
| [SeedFinder](https://github.com/zebedelu/SeedFinder) | C engine with Bedrock-specific placement and a separate [biome viability layer](https://github.com/zebedelu/SeedFinder/blob/main/core/viability.c). Useful comparison source when diagnosing our disagreements. Its advertised support does not establish a better 26.52 replacement; no comparative build or benchmark was performed here. |
| [Seedforge](https://github.com/fwsoapy/seedforge/blob/main/vendor/patches/README.md) | Documents its own Bedrock placement implementation and limitations. Its listed Bedrock omissions include strongholds, mineshafts and trial chambers, all relevant to us. Not a complete replacement. |
| [Chunkbiomes](https://github.com/Nel-S/Chunkbiomes) | Limited port of Chunkbase filters. Its README explicitly says Fortress/Bastion differentiation is missing. It is not equivalent to the current website or a complete backend. |

Repository descriptions disagree on important details, including seed width. Our pinned source and tests take precedence over those descriptions. In particular, preserve the full seed: our trial-chamber test already demonstrates an upper-32-bit placement dependency.

Chunkbase remains the chosen external review reference. Its [documentation](https://www.chunkbase.com/apps/seed-map#troubleshooting) explains terrain mode, possible missing structures and marker offsets. This audit found no demonstrated drop-in library that removes all our remaining limitations.

## Ordered implementation plan

1. **Make the Bedrock target and review policy explicit.** Validate edition as well as version; expose supported dimensions/features and the model mapping. Update config, CLI and metadata to use Chunkbase review for the bounded pilot, with actual game observations kept separate. Keep large search disabled until the search pipeline and pilot are ready. Done when configuration rejects unsupported targets and all outputs report the same review policy.

2. **Automate the comparisons we already have.** Turn the saved Chunkbase fixtures into a repeatable regression command covering all eleven exposed structures and the biome/terrain rows. Preserve six structure and six surface-biome disagreements as explicit known cases, not passing results. Replace blanket distance matching with per-type marker/start conventions where established; retain raw offsets where unknown. Keep the known absent Fortress test. Done when one command reproduces the baseline and detects new regressions.

3. **Investigate the three failing structure families.** Start with Bastion viability because it is a required search target: inspect its rotated-piece biome sampling (`finders.c:1588`). Check Ancient City quart-coordinate/Y=-27 sampling (`finders.c:1852`). Compare both static and village-associated stronghold paths (`finders.c:851`, `:981`) for the two missing positions. Their precise root causes are not established. Use candidate-level Chunkbase results for selection; make a general rule change only when evidence supports it. If unresolved, retain promising raw starts in the review queue instead of treating local rejection as certain absence. Done when each discrepancy has a tested correction or an explicit, tested review fallback.

4. **Handle coastline and biome uncertainty during filtering.** Refine near sea level and near biome transitions, use stride-one density sampling where a potential land bridge matters, and retain unresolved boundaries for Chunkbase Terrain review. Keep woodland coverage labeled as a biome proxy. This improves screening but cannot certify exact liquid blocks or tree counts. Done when uncertain geography is visible and cannot silently become a confirmed isolated island.

5. **Finish the seed-search features.** Implement the configured water/mountain/wood metrics, per-center structure checks, ranking, distinct-seed shortlist, checkpoint/resume and candidate exports. Apply the confirmed 3008-block Overworld and 992-block Nether squares at the actual candidate centers. Preserve uncertain required structures for review and flag markers near borders because marker inclusion does not prove whole-structure access. Done when a bounded run produces reproducible candidates and resumes without losing or duplicating work.

6. **Run a small end-to-end pilot, then scale.** Start with ten seeds, measure the complete pipeline, and review up to five candidates in Chunkbase using the matching Bedrock version and Terrain mode. Check both dimensions and the configured borders. Record `chunkbase_checked` evidence separately from phone observations. If ten seeds produce no viable shortlist, increase the bounded sample based on measured runtime and survivor counts; do not force five results. Scale only after the pilot exposes no unresolved pipeline failures. Building a BDS verifier remains deferred.

Steps 1–4 address compatibility and prediction handling. Steps 5–6 finish and exercise the requested search product. End support and additional structure families can be separate extensions if they become requirements.
