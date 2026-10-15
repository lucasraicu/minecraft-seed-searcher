# Goal handoff: make the Bedrock search ready for a large sweep

## User authorization and objective

The user authorizes implementation, fixes, research, meaningful tests, native rebuilds, bounded pilots and Chunkbase browser review in this project. Create a persistent Goal, with no invented token budget:

> Implement and verify the Bedrock 26.52 island seed-search system until it is ready to run a large local sweep. Complete the ordered compatibility plan, the actual ranking/search/resume pipeline, repeatable regression comparisons, a measured end-to-end pilot and matching-version Chunkbase review. Report success only when the completion criteria in SWEEP_READY_HANDOFF.md are satisfied. Deliver the tested terminal command for starting the sweep, but leave the large sweep unstarted.

Do the work, rather than returning another implementation proposal. Continue autonomously across turns and compactions. Keep a durable progress log; provide brief required progress updates, but do not ask the user to approve routine implementation choices or return a partial completion report. A genuine external blocker, user interruption or usage limit must be reported honestly and must not be called success. Use native Goal lifecycle tools when available, and follow their completion/blocking rules.

This handoff is preparation for a separate implementation run. Its existence does not mean the algorithm is ready.

## Workspace and fixed requirements

- Project: `/Users/lucasraicu/Downloads/minecraft-seed-searcher`; Intel Mac, macOS, Python virtual environment `.venv`. Check current machine/runtime rather than assuming historical measurements still apply.
- Target: **Minecraft Bedrock 26.52**, full signed 64-bit numeric seeds. Current native model is `MC_26_50`; preserve and explicitly validate/document that mapping. Do not silently switch to the latest preview or standard Java Cubiomes.
- Overworld playable square: **3008 × 3008**. Nether playable square: **992 × 992**, centered at the chosen Overworld center divided by eight. Choose the Overworld center on the eight-block grid and on land. Square membership and proximity distance are different measurements.
- Desired island: fully separated, buildable, preferably open/lightly wooded, preferred equivalent diameter **300–700 blocks**; enclosing water and surrounding mountains; abundant woodland on external land and slopes.
- Trial Chamber, Stronghold and Mineshaft are strong Overworld preferences. Ancient City is a bonus, followed by Village, Overworld Ruined Portal, Shipwreck, Monument and Outpost.
- Both **Fortress and Bastion** are required inside the Nether square. Distinguish predicted starts, website markers and actual accessible structure footprints.
- Existing numeric preferences/weights are pilot defaults. Use the configuration as the source of truth, and explain measured calibration changes. Do not relax fixed requirements merely to manufacture passing candidates.
- Chunkbase is the primary external prediction reference. Select **Bedrock 26.50–26.52** and enable Terrain for shoreline review. Phone observations are optional final evidence. An automated Minecraft/BDS verifier remains deferred.

## Read first and resolve stale statements

Read `BEDROCK_COMPATIBILITY_AUDIT.md`, `CHUNKBASE_WORKFLOW.md`, `search.example.yaml`, `SEARCH_TARGETS.md`, `IMPLEMENTATION_PLAN.md`, `PREFLIGHT_STATUS.md`, `GOAL.md`, and `runs/accuracy-audit/REPORT.md`, then inspect implementation and tests.

The latest user decisions in this handoff and `CHUNKBASE_WORKFLOW.md` supersede historical instructions requiring phone/game validation. In particular, older target tables still describe failed-Bastion promotion as a Fortress fallback: that behavior was wrong and has already been removed. Correct those stale statements while implementing. Reconcile README, config, CLI, metadata and goal documents around the same current workflow.

Preserve user files and the frozen external/phone evidence. Inspect repository state before using Git; historically this directory was not a Git checkout. Do not fabricate Git history or overwrite existing work.

## Starting evidence and known problems

Current backend: FragrantResult186/cubiomes-bedrock, pinned commit `294c72ab0392dd818a91d293dbd5774d4874d64b`; `vendor/backend.json` records the source hashes. It contains substantive Bedrock placement logic. Keep it unless a measured, tested alternative solves a specific problem.

At the last audit, 44 tests passed and `doctor` called the installed model successfully. Only `doctor`, `benchmark`, `probe` and `compare` were implemented. Complete landscape scoring, ranked multi-center search and checkpoint/resume remain unfinished. Source/build/test status must be rechecked in the implementation run.

The saved comparison contains four seeds (`12345`, `0`, `-1`, `4294979641`), 159 coordinate rows and 880 structure rows. Structure correspondences were 874/880 within a diagnostic 64-block radius; exact coordinates matched for 477. Surface biomes matched 129/135. Mean terrain-height difference was one block, maximum five. These are bounded comparisons with another predictor, not whole-world Minecraft accuracy or complete recall.

Unresolved structure records:

| Seed | Type | Chunkbase X,Z | Local finding |
|---|---|---|---|
| 12345 | Bastion | 1185,376 | Raw 1208,408 rejected by viability |
| 4294979641 | Bastion | 1185,376 | Same repeated lower-bit case |
| -1 | Stronghold | 6212,-4700 | Missing local placement |
| -1 | Stronghold | 3524,-7276 | Missing local placement |
| -1 | Ancient City | -3048,3256 | Exact raw placement, viability rejection |
| 4294979641 | Ancient City | -680,6216 | Exact raw placement, viability rejection |

Inspect Bastion rotated-piece biome sampling, Ancient City quart coordinates/Y=-27, and static plus village-associated Stronghold enumeration. Root causes are not yet proven; do not encode six coordinate exceptions as an algorithm fix.

The false seed-12345 Fortress at Nether `(-152,120)` was an adapter error, corrected after user-confirmed absence. Keep its regression test. Actual phone locate anchors were Fortress `(64,816)` and Bastion `(-680,-168)`; these are separate from Chunkbase markers. Positive locate evidence is not a visited/generated-footprint confirmation. The user explicitly skipped Overworld `(-256,-256)`; do not request it again.

Raw density terrain omits caves, aquifers, decoration and actual chunk interpolation. Stride-eight sampling can miss thin overhangs. Woodland masks are biome proxies for wood supply. Keep these limits visible rather than claiming exact blocks/trees.

## Work in order

1. Align Bedrock/version validation, capabilities, configuration, CLI and evidence reporting with the current Chunkbase policy. Preserve full seeds and per-structure RNG exceptions; the existing Trial Chamber test shows upper-bit dependencies. Keep lower-bit optimization disabled until individually justified and tested.
2. Automate the saved external comparisons with explicit known discrepancies and per-type coordinate conventions. Add meaningful coverage for negatives, upper bits, region/border edges, missed placements and the corrected false Fortress. The broad 64-block heuristic must not conceal type swaps, multiple-start mismatches or wrong border eligibility. Never generate the external side of a comparison from our own model.
3. Diagnose and correct the failing structure families where evidence supports a general rule. For remaining predictor ambiguity, implement a tested review path that preserves promising raw starts and does not silently treat local rejection as known absence. A disputed required Nether target cannot be presented as a confirmed eligible finalist before Chunkbase review.
4. Implement refined island connectivity, shoreline/water metrics, mountain directional coverage, external woodland and island openness, with explicit unknown handling. Use accurate-enough sampling near candidate coasts and sea level; do not certify isolation from a forest/ocean biome label. Test a connected island/bridge case and a separated case using external evidence where available, plus meaningful geometry tests.
5. Implement deterministic seed enumeration, multi-center refinement, scoring, distinct-seed ranking, bounded search, checkpoint/resume, maps and JSON/CSV reports. Preserve finite-raster uncertainty, exact center conversion and border rules. Persist configuration/backend identity, seed indices and evidence status; reject incompatible resume inputs. Prove resumed and uninterrupted runs yield the same results.
6. Run the complete pipeline on an initial ten-seed pilot. Measure total runtime, per-stage cost, memory, survivor counts and actual worker behavior. Stage microbenchmarks alone cannot complete this step. Expand bounded pilots to 100/1000 seeds if necessary to expose useful candidates or search behavior; choose further increases from measured cost and document the finite budget before launching. Do not start a broad sweep during this goal.
7. Obtain fresh Chunkbase checks beyond the saved four-seed baseline. Review available pilot finalists (up to five), both dimensions, actual centers/borders, Terrain-enabled shorelines and required Nether targets. Also inspect representative rejections/near misses for overly aggressive filtering. Include negative coordinates and an upper-bit seed case. Keep new review data separate from calibration data where practical and report both outcomes. A pilot with no finalists can validate execution but cannot be called successful candidate-quality verification without additional evidence.
8. Fix failures, rerun only the affected checks plus required regression checks, and produce the sweep-readiness package below. Optimize demonstrated bottlenecks without sacrificing verified seed/placement semantics. Do not claim mathematically maximal accuracy or a universal percentage; report the best measured accuracy achieved and remaining managed limits.

Chunkbase reviews must come from the actual matching-version website through available browser tools. Saved rows are useful regression evidence but cannot substitute for a new review falsely labeled fresh. Check browser/tool availability early. If access fails, continue independent implementation and verification, record the missing evidence, and do not mark the goal sweep-ready until required review is possible. No public bulk Chunkbase API is assumed.

## Completion criteria: all required

- Native backend builds through the supported install path; dependencies, license/provenance and meaningful tests pass. The direct `native/build.py` entry point previously had a relative-path issue; fix it if retained as a supported command or document the working build path accurately.
- Enabled Bedrock capabilities and the target/model mapping are explicit. All baseline discrepancies are corrected or have tested, visible review handling; no new unexplained regression is hidden by wider coordinate tolerance or weaker assertions.
- The complete configured landscape, structures, ranking, search and resume paths work with deterministic results and correct border eligibility. Required features are not placeholders or unused YAML declarations.
- Repeatable external comparison, independent fresh Chunkbase evidence and an end-to-end pilot support both prediction handling and candidate selection. Report sample sizes, mismatches, exclusions and remaining uncertainty; do not imply complete recall from capped positive lists.
- Candidate outputs contain the seed, center, bounds, metric breakdown, maps, raw/viable/Chunkbase statuses and remaining review items. `chunkbase_checked` stays distinct from actual Minecraft evidence.
- A deliberate readiness gate permits the future sweep only after these checks; readiness is not achieved simply by toggling `large_search_enabled`. Fresh runs and incompatible resumes fail appropriately when requirements are unmet.
- Save `SWEEP_READINESS.md` and a machine-readable readiness record with exact commands, configuration/backend identity, test/comparison/pilot artifacts, worker recommendation, measured throughput and sweep-runtime estimate. Scope estimates to the measured workload.
- Provide a runnable terminal command for a finite large sweep and its resume command, matching implemented CLI help. Validate argument parsing with a dry run or tiny bounded equivalent. Leave that large sweep unstarted.

Keep `GOAL.md` and a progress file current so work survives context loss. Save the evidence, remaining prediction limits and resume instructions in `SWEEP_READINESS.md`. At successful completion, the final user-facing response should contain only the tested terminal command for starting the large sweep, in a shell code block. Do not provide a terminal command to start another Codex session. Only mark the native Goal complete when all criteria are met. If completion is prevented by a genuine blocker or usage limit, report that honestly instead of issuing a sweep command.

## Completion notification

At true implementation completion, after all required verification, run this as the final shell command:

```sh
python3 /Users/lucasraicu/codex_done.py "CODEX TASK COMPLETE
Minecraft seed searcher
Implemented and verified the Bedrock search, Chunkbase comparisons, and pilot; the algorithm is ready for a large sweep."
```

Do not send that implementation-complete notification after intermediate steps or merely because the handoff has been read.

## Use this handoff in a new Codex chat

Open a new Codex chat in the `minecraft-seed-searcher` project and send:

> Read `/Users/lucasraicu/Downloads/minecraft-seed-searcher/SWEEP_READY_HANDOFF.md` in full. Create a persistent Goal to complete its implementation and all sweep-readiness criteria. Continue until implementation, regression verification, fresh Chunkbase comparisons and the end-to-end pilot are complete. Keep evidence and progress in project files. When fully ready, return only the tested terminal command for starting the large sweep. Leave the large sweep unstarted. If genuinely blocked, explain the blocker without claiming readiness.

The implementation runs in the new chat. The terminal is used afterward to start the verified sweep. Goal lifecycle behavior is documented in [OpenAI's Goals guide](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex).
