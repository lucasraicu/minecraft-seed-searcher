# Preflight status — 7 October 2026

Historical planning/audit evidence is retained below. Current implementation and verification progress is in [PROGRESS.md](PROGRESS.md); the active completion criteria are [SWEEP_READY_HANDOFF.md](SWEEP_READY_HANDOFF.md). The expanded search, measured pilot, fresh selection checks and finite readiness verification are complete; current outcomes and remaining limits are in [SWEEP_READINESS.md](SWEEP_READINESS.md).

The local native prototype builds and passes **44 tests**. A large search has not run and remains disabled. Three phone observations support initial local surface predictions; the proposed Bedrock 26.52 → MC_26_50 mapping still needs broader landscape and structure validation. Resumed Chunkbase checks agree closely with all three Overworld phone anchors. Actual Nether locate outputs are recorded, and a user-confirmed absent Fortress exposed a false positive that has now been corrected.


## Current review policy — user decision

The user chose Chunkbase as the primary external prediction reference to save verifier development time. [Adopted workflow](CHUNKBASE_WORKFLOW.md): use the local model for discovery/ranking, then review a small shortlist with matching-version Chunkbase and Terrain enabled. Building a Minecraft/BDS validator is deferred. Actual phone checks below remain optional follow-up evidence, not prerequisites for the bounded pilot.

Keep `chunkbase_checked` separate from actual-world verification. Chunkbase's own documentation lists structure and coastline limitations and does not substantiate the claimed 99.99% accuracy. The large search remains disabled because landscape/ranking/resume and pilot work are unfinished; it is no longer waiting for a Minecraft validator.

## Broad Chunkbase audit

A bounded audit now compares **159 coordinate samples** and **880 structure predictions** on seeds 12345, 0, -1 and 4294979641, with matching Bedrock 26.50–26.52 selected. Coverage includes 52 surface biome types, four cave biome types, all five Nether biome types and all eleven supported structure adapters.

- Surface biome agreement: **129/135 (95.6%)**. Six exact-coordinate disagreements lie within one or two blocks of local biome boundaries.
- Nether biome samples: **20/20**. Cave names at Y=-51: **4/4**, with differences in three cave vertical ranges.
- Density heights: **1.0-block mean absolute difference**, 125/135 within two blocks, maximum five blocks. Four land/water threshold disagreements remain; the cheaper discovery proxy has six.
- Structure correspondence within 64 blocks: **874/880 (99.3%)**. Two missing strongholds, two rejected ancient cities and the same rejected bastion on two related seeds remain unresolved against Chunkbase. Exact marker/start coordinates match in 477/880 rows; offsets are retained.

[Full audit and coverage limits](runs/accuracy-audit/REPORT.md), [durable external fixture](fixtures/bedrock-26.52/chunkbase-accuracy-audit.json), and [optional in-game disagreement checks](runs/accuracy-audit/PHONE_DISAGREEMENTS.md). This is agreement between predictors, not an in-game accuracy percentage or a measured false-positive rate. End features and structure types outside the eleven-type wrapper are unsupported. Actual landscape, positive structure visits, woodland calibration and the bounded pilot remain pending; the large-search gate stays closed.

## Current Nether findings and correction

- Actual Fortress locate **(64,816)** is near the ordinary local start **(72,824)** and outside the diagnostic square.
- Actual Bastion locate **(-680,-168)** equals the local viable start and is also outside the diagnostic square. Y and actual positive visits are unknown.
- After the initially obstructed teleport, the user reports looking around **(-152,120)** and finding no Fortress. The inspected extent is unspecified. The phone fixture records this prediction as absent.
- The native adapter incorrectly promoted a biome-rejected Bastion attempt to a Fortress. Removed that promotion for this Bedrock prototype and rebuilt the native adapter through the documented editable-install route.
- The regression failed against the old adapter; **all 44 tests now pass**, including the absent prediction and retained ordinary Nether starts. The comparison/probe data are refreshed; the diagnostic square now has **no predicted Fortress**.

[Correction evidence](runs/preflight/fortress-correction.json). The prior clean-build and benchmark records describe the earlier adapter; their measured timings and hashes have not been reused as proof of the corrected build. Further actual structure visits, island/bridge contrast, woodland/mountain calibration and the bounded pilot remain pending. A snowy/forested location reached via `/execute in overworld run tp @s 256 160 -256` was the deliberate Overworld escape route, not another Nether Fortress target.

## First actual observations

| Coordinate (X, Z) | User observation | Model prediction | Result |
|---|---|---|---|
| 0, 0 | Water | Ocean / ground Y=48 | Surface kind agrees |
| 256, −256 | Wooded spruce area; ground Y=147 | Grove; ground Y=146 | One-block ground difference |
| 256, 256 | Ground Y=91; dark-log tree top Y=101 | Dark Forest; ground Y=90 | One-block ground difference; tree top kept separate |

The user requested skipping `(-256,-256)`; that point stays unvisited and will not be requested again. These observations do not validate island connectivity, mountain coverage, tree abundance, or structures. Do not add an arbitrary height offset from two observations. The observations are recorded under the requested seed/version; explicit default-generation confirmation has not been supplied.

Actual observations are saved separately from predictions in [the durable user fixture](fixtures/bedrock-26.52/seed-12345.user-observations.json), with unvisited facts left null. The [comparison](runs/probe-12345/comparison.json) records height errors and retains the closed large-search gate. Derived reports remain under `runs/`.

## First actual structure locate results

The user's phone screenshot records these outputs from commanded Overworld reference `(-3712,320,3328)`. The screenshot reports player position `(-3711.50,320.00,3328.50)`. Y is unknown for each locate output; no visits have been reported.

| Type | Phone locate X, Z | Nearest viable predicted start X, Z | Horizontal offset | Inside diagnostic border? |
|---|---|---|---:|---|
| Trial Chamber | −3689, 3513 | −3672, 3512 | 17.0 blocks | Both inside |
| Stronghold | −5134, 5522 | −5132, 5524 | 2.8 blocks | Both outside |
| Mineshaft | −3680, 3312 | −3672, 3320 | 11.3 blocks | Both inside |

These are nearby starts, not exact-coordinate matches or visit confirmations. The diagnostic Overworld square is X `[-5216,-2208]`, Z `[1824,4832]`. The Stronghold locate point is 690 blocks beyond its upper Z boundary. Finding it nearby in the larger world supports the placement comparison while leaving the original in-border report unchanged.

The playable square is **3008 × 3008**. The planned per-seed center-search window is separately **10,000 × 10,000**, with a **13,008 × 13,008** analysis envelope before raster snapping. Those are current finite starting budgets, not exhaustive whole-world coverage or user-mandated distance limits.

## Finished locally

- Compiled the pinned Bedrock backend with a batched CFFI adapter.
- Tested signed seeds, upper seed-bit dependence, negative coordinates, scalar/batch agreement, special Stronghold/Mineshaft logic, and direct Fortress/Bastion selection. The former fallback test was replaced with a real negative fixture.
- Tested diagonal land connections, centroid-on-land selection, separate island/external wood preferences, bounded benchmark limits, and pending-evidence handling.
- Implemented structure-observation comparisons with explicit dimensions, nearby placement/viable starts, offsets and square-border eligibility. A located coordinate and a visited generation confirmation remain separate; no offset automatically passes a capability.
- Installed and hash-checked the 21-package dependency lock; recorded source hashes and retained the backend license.
- Built an extracted source archive in a fresh virtual environment, installed the resulting wheel, and passed all 43 tests against the installed package. The installed CLI reproduced the three recorded surface comparisons and kept the large-search gate closed. The source archive includes the configuration, tests and user fixture; the wheel includes the exact backend license. See [clean-build evidence](runs/preflight/clean-build.json). This is a functional rebuild check, not a claim of byte-identical package output.
- Documented every target's area, distance and initial score rule in [SEARCH_TARGETS.md](SEARCH_TARGETS.md).
- Generated [the seed 12345 map](runs/probe-12345/terrain.png), [predictions](runs/probe-12345/probe.json), and [phone instructions](runs/probe-12345/PHONE_CHECKS.md). These are diagnostic predictions, not a verified seed recommendation.

## Measured performance

Three fixed seeds (0, 1, 12345), on this Intel iMac Pro. Rounded current measurements:

| Workload | Samples | Median seconds |
|---|---:|---:|
| Full coarse biome/climate map | 41,616 points at 64-block spacing | 0.34 |
| One full-border density refinement | 35,721 columns at 16-block spacing | 3.68 |
| One shoreline patch | 4,225 columns at 4-block spacing | 0.43 |
| All eleven structure adapters | Recorded full analysis envelopes | 0.58 |

The coarse-only parallel workload used at most ten unique seeds and tested 4, 8 and 12 workers. Startup is included. See [BENCHMARK.md](runs/preflight/BENCHMARK.md) and [the exact results/configuration hash](runs/preflight/benchmark.json) for current measurements.

**Complete search time per seed is not measured.** It will depend on how many candidate centers survive and how much terrain each needs. The fixed refinement benchmark estimates computational cost; it does not execute the planned full search.

## Still unknown

1. Whether the 26.50 backend agrees sufficiently with actual Bedrock 26.52 terrain and structure generation.
2. Whether the cheap height proxy reliably shortlists the desired basins and islands. Coarse samples can miss a bridge.
3. Whether raw density estimates are accurate enough for shorelines/mountains. They exclude caves, aquifers, decorations and actual chunk interpolation; stride-eight height scans can miss thin layers.
4. How closely woodland biome coverage corresponds to abundant accessible trees. Sparse woodland weights and initial percentages need actual examples.
5. Candidate yield, useful worker count for the full pipeline, and complete time per seed.

Water/mountain angular metrics, refined island/external woodland zones, final score intervals, ranking, persistence and resume remain later implementation work. The preflight map reports biome potential; it does not claim those full scores are implemented.

## Optional phone checks — no longer pilot prerequisites

1. **Core structure visits:** Trial Chamber, Stronghold and Mineshaft locate outputs have been recorded. Visit the indicated sites in Spectator mode to confirm actual generation. Locate anchors can differ from predicted starts; the comparison reports offsets for review. The Stronghold is outside the diagnostic playable square, but can still supply a compatibility example.
2. **Nether requirements:** Fortress and Bastion. Use Nether reference `(-464,416)`. Record locate outputs and visits; check the 992-square boundary, rather than assuming the nearest structure fits. A predicted start or locate anchor inside the border does not guarantee the whole entrance/structure is accessible.
3. **Landscape examples:** inspect the predicted island around `(-3712,3328)` for water separation, external mountains and extensive accessible forest; record an actual peninsula/land-bridge contrast with coordinates. This is a validation example, not the selected seed. Biome coverage must be compared with actual trees before calibrating woodland thresholds.
4. **Optional structure capabilities:** Ancient City, Village, Ruined Portal, Shipwreck, Monument and Outpost. Their predictions remain unvalidated until their own checks are recorded; incomplete optional capabilities stay unknown.

Use [PHONE_CHECKS.md](runs/probe-12345/PHONE_CHECKS.md) for commands and a table of predicted starts. The initial surface section has already been checked; continue with the structures. The comparison command accepts actual observations without automatically certifying the model or opening the large-search gate.

After these examples, remaining local work is to assess terrain/woodland errors, tune the provisional metrics and measure a bounded pilot. Final Realm checks such as safe spawn, actual portal arrival and border behavior apply to the eventual selected world, after the seed search.

## Completion audit

| Preflight requirement | Current evidence | Status |
|---|---|---|
| Lightly wooded island, abundant external wood | Revised plan/configuration, separate openness/external-wood helpers and tests | Preference revision complete; actual zone metrics/calibration pending |
| Every structure/biome query region and distance | SEARCH_TARGETS.md and configuration | Written; variable shoreline areas will be measured per island |
| Pinned local prototype builds and runs | Source hashes, hash-locked dependencies, fresh archive-to-wheel build, installed CLI, 43 passing tests | Locally verified |
| Stage timings on this Intel Mac | Three serial diagnostic seeds and ten-seed coarse parallel batches in benchmark.json | Measured; complete search time/yield unmeasured |
| Real surface comparison | Three user reports; water agrees, two reported ground heights differ by one block | Initial support; broader accuracy unproven |
| Real structure comparison | Five Overworld/Nether locate outputs, one user-reported absent Fortress; corrected negative regression | Partial support; positive visits pending |
| Island versus land-bridge contrast | Synthetic connectivity tests; no actual contrast recorded | Pending actual landscape examples |
| External forest abundance and mountain ring | Diagnostic map; no inspected forest/height coverage examples recorded | Pending observation/calibration |
| Bounded pilot after applicable validation | No ranking pilot run; large-search flag false | Pending preceding checks |

The goal is incomplete. The user-approved Chunkbase workflow replaces mandatory actual-world fixture collection and defers verifier development. Existing phone evidence and unresolved disagreements remain recorded without changing their meaning. Remaining landscape metrics, ranking/resume and bounded pilot measurements still need implementation; the large search remains disabled for that work.

## History: User-requested wait

The user asked to use Chunkbase while away, and to wait if it could not be used. Its public Seed Map page was readable, but opening the interactive map failed: the in-app browser was unavailable and the browser inventory was empty. No Chunkbase coordinates or matching-version selection were obtained, and no new observations were inferred from our own predictions. [Attempt record](runs/preflight/chunkbase-attempt.json). The goal is paused until the user returns.

The user then specified comparing the three existing Overworld locate results with Chunkbase first. A fresh browser-inventory check still returned no browsers. [Overworld comparison attempt](runs/preflight/chunkbase-overworld-attempt.json): the comparison is unperformed, not a pass or failure of Chunkbase's predictions. When map access is available, compare Trial Chamber `(-3689,3513)`, Stronghold `(-5134,5522)` and Mineshaft `(-3680,3312)` in seed 12345 using the matching Bedrock version before proceeding to additional locations.

## History: Resumed Chunkbase checks

On 7 October 2026 the user returned and requested continuing in a new conversation. Interactive browser access now works. Seed 12345 with Bedrock 26.50–26.52 gives Overworld anchor offsets of 0 blocks (Trial Chamber), 2.8 (Stronghold) and 11.3 (Mineshaft) from the actual phone locate outputs. The prior wait is superseded by this resumption.

[Full comparison](runs/preflight/CHUNKBASE_COMPARISON.md): the local in-border Fortress at (-152,120) comes from promoting a biome-rejected Bastion attempt. It is absent from the observed capped Chunkbase search list, which instead shows a Fortress crossing at (75,827), 43 blocks beyond the diagnostic square's eastern edge. This is unresolved third-party disagreement, not proof of actual absence or permission to alter the generator. The test of the fallback only establishes internal behavior. Actual in-game Nether locate results and visits are the next evidence needed; no in-border Fortress is validated. Chunkbase shows three nearby Bastion anchors inside the square, but full structure containment and actual generation remain unknown.

The [Chunkbase fixture](fixtures/bedrock-26.52/seed-12345.chunkbase-predictions.json) is separate from the unchanged phone fixture. The large search remains disabled; island/bridge, mountain and woodland examples still require actual observation.

## History: New actual Nether locate

The user reported Fortress X=64, Z=816 (Y unknown), 11.3 blocks from the ordinary local start (72,824) and 15.6 from Chunkbase crossing (75,827). The actual locate anchor is 32 blocks beyond the diagnostic Nether square's eastern edge X=32. The [phone fixture](fixtures/bedrock-26.52/seed-12345.user-observations.json) now preserves four locate records; visit status remains unknown. The separate in-border fallback (-152,120) remains disputed and awaits inspection; Bastion locate is still pending.

## History: Actual Bastion locate

User report: Bastion **(-680,-168)**, Y and visit unknown; actual locate reference not supplied. This equals the local viable start and is 28.2 blocks from previously observed Chunkbase Treasure-room anchor (-669,-194). It is 88 blocks beyond the diagnostic Nether square's minimum-Z edge Z=-80. Five locate records are now saved. Both Nether locate anchors have been recorded, while actual visits, the disputed Fortress fallback inspection, and landscape calibration remain pending. These out-of-square results do not validate the diagnostic square's required in-border structures.

## History: Disputed Fortress point inspection

The user teleported to **(-152,70,120)**, reported netherrack and no visible structure, and was unable to leave the surrounding block mass after using TNT. Surrounding positions/heights were not inspected. Record this as an **obstructed point inspection** with generation status unknown, not a confirmed whole-Fortress absence. It does not validate the fallback. Spectator mode and `/execute in overworld run tp @s 256 160 -256` were provided to return to the previously observed spruce location. No successful escape has been reported yet.
