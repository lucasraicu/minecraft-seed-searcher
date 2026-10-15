# Filter optimization — complete, 8 October 2026

Implemented and verified the user-requested shortcuts and fast Stronghold screening. Stronghold/Fortress joint-window checks precede expensive terrain; incomplete predictions are deferred with recovery exports. Combined native enumeration, bounded typed raw-MT caching, conservative basin bounds and shared raster intermediates are complete. All 112 tests and the frozen external regression pass. The 20-input pilot has 96 predicted-required locations; all 95 common qualifying prior locations retain identical complete candidate records. Independent 20-input runs match exactly across checkpoint/resume and 8 versus 12 workers. The controlled 12-worker run saves 9.01% analysis wall time. Fresh Chunkbase follow-ups confirm required markers for two ocean controls, preserving original geometry evidence and prediction limits. The exact finite 2000-input command passes dry-run validation from /tmp, and missing/tampered/stale readiness and over-budget requests fail. Current package: `runs/filter-optimization/readiness.json`; prior identities are superseded. The large sweep remains unstarted. Details: `SWEEP_READINESS.md`, `FILTER_OPTIMIZATION.md`, and `runs/filter-optimization/WORK.md`.

# Historical completed landscape expansion goal — 7 October 2026

The expanded search and required verification are complete: 99 tests, frozen external regression, a 20-seed end-to-end checkpoint/resume pilot, an exactly matching independent ten-seed repeat, actual matching-version Chunkbase reviews and the evidence-derived readiness gate. Three landscape branches are implemented; Fortress and Stronghold are required, Bastion optional. The current finite 2000-seed launch and resume equivalent pass dry runs from /tmp, and no large-sweep output directory exists. This sample supports two ocean candidates and contains no accepted dry flat mountain basin; no positive basin yield or game-level accuracy is claimed.

Current measured details, remaining limits and commands: [SWEEP_READINESS.md](SWEEP_READINESS.md), [LANDSCAPE_EXPANSION.md](LANDSCAPE_EXPANSION.md), and `runs/landscape-expansion/readiness.json`. Pilot 387.62s for20 inputs/114 locations, exact-cache A/B saving5.83%, unchanged full report refresh1.09s/152 identical PNGs with no native queries/redraws. Original sources/evidence are preserved; prior readiness is superseded. The large sweep remains unstarted.

The following records describe the prior completed implementation and its history.

# Goal: validate the Bedrock island search before scaling up

Build and validate a local Bedrock **26.52** prediction prototype on the Intel Mac before any large seed search. The intended world has a fully separated, buildable, preferably lightly wooded central island, surrounding water and mountains, very abundant accessible forest on the external land, useful Overworld structures, and both a Fortress and Bastion within the **992 × 992** Nether square. Its Overworld border is **3008 × 3008**. Chunkbase is the primary external prediction reference under the user-approved [review workflow](CHUNKBASE_WORKFLOW.md). Building a Minecraft verifier is deferred; phone checks are optional final confirmation.

## Work in order

1. Update the landscape/scoring requirements and record every structure/biome query area and distance in [SEARCH_TARGETS.md](SEARCH_TARGETS.md).
2. Compile the pinned Bedrock backend and verify seed, coordinate, batched-sampling, and special structure adapters with meaningful tests.
3. Measure discovery sampling, structure checks, and terrain estimation separately on this Mac. Report measured stage cost and distinguish it from still-unmeasured full search time per seed.
4. Review shortlisted seeds/centers against matching-version Chunkbase terrain, biomes and structures. Record external predictions separately from actual phone observations; do not claim that a Chunkbase check is an in-game verification.
5. Calibrate mainland woodland potential and island openness against the external maps; preserve uncertainty about actual tree abundance and thin land bridges.
6. Only after the applicable checks pass, run a small bounded pilot to measure candidate yield and refine the scoring. A large search remains disabled until preflight is complete.

## Completion criteria

- The pinned native backend builds reproducibly and regression tests pass.
- All structure and biome targets have explicit query regions and eligibility/scoring rules.
- Measured stage benchmarks are saved, with hardware/configuration and sample counts.
- Matching-version Chunkbase reviews support candidate selection, including terrain-enabled shoreline checks and both required Nether structures. Actual-world confirmation is optional and remains a separate evidence status.
- Remaining prediction limitations are documented and accounted for in output.
- Scoring reflects less central-island wood and abundant surrounding wood.
- No large seed search has run before these checks.

Report progress at every milestone: what finished, the evidence, what remains unknown, and the next action. Phone observations may require user participation; independent local work continues while they are pending.

## Historical preflight progress

- [x] Revise island openness and external woodland requirements; write all query distances and areas.
- [x] Compile the pinned native adapter, retain source/license hashes, and create a hash-checked dependency lock.
- [x] Rebuild from an extracted source archive in a fresh environment; verify the installed wheel, bundled backend license, CLI and all 43 tests.
- [x] Pass 44 local adapter, geometry, seed, configuration, and preflight checks after correcting the false Fortress fallback.
- [x] Measure bounded stage workloads and 4/8/12-worker coarse sampling.
- [x] Generate a diagnostic terrain map and exact phone-check packet for seed 12345.
- [x] Record three user observations: origin water; Grove/spruce ground at (256,-256); dark-log tree and ground at (256,256). Both ground estimates differ by one block; the other requested point is skipped at the user's request.
- [x] Implement structure comparisons that preserve placement, viability, locate coordinates and visit confirmations as separate evidence.
- [x] Record and compare the three Overworld locate outputs from the user's phone screenshot; retain unknown Y/visit status and the out-of-border Stronghold.
- [x] Compare the three Overworld phone locate anchors with matching-version Chunkbase predictions: offsets 0, 2.8 and 11.3 blocks.
- [x] Record actual Nether Fortress locate (64,816), near the ordinary local/Chunkbase prediction and outside the square.
- [x] Record actual Bastion locate (-680,-168), equal to the local start and outside the diagnostic square.
- [x] Resolve the false Fortress fallback at (-152,120): user reports surrounding-area absence; remove failed-Bastion promotion, rebuild and pass the negative/positive regressions. The diagnostic square now has no predicted Fortress.
- [x] Audit all eleven supported structure types and 61 generated biome types against Chunkbase representatives on four seeds: 159 coordinate samples and 880 structure rows. Record six structure disagreement records, boundary/terrain limitations and unsupported coverage in [the audit](runs/accuracy-audit/REPORT.md).
- [x] Adopt Chunkbase as the primary shortlist reference at the user's request; defer the Minecraft verifier and remove mandatory phone-observation prerequisites.
- [ ] Review the ranked shortlist against Chunkbase terrain and required structures; retain optional in-game checks separately.
- [ ] Calibrate terrain/woodland estimates and implement the remaining landscape/ranking stages.
- [ ] Run the bounded pilot after the applicable validation gates pass.

Evidence and remaining unknowns are in [PREFLIGHT_STATUS.md](PREFLIGHT_STATUS.md). Work resumed in the new conversation at the user's request. Browser access now works and the [Chunkbase comparison](runs/preflight/CHUNKBASE_COMPARISON.md) is recorded separately from phone observations. Overworld anchors agree closely; the absent Nether Fortress fallback has been corrected and all 44 tests pass. The user subsequently chose Chunkbase-based review to save time. Actual visits and landscape examples remain unperformed but are no longer prerequisites for the bounded pilot. At that historical checkpoint, ranking, landscape metrics and pilot measurements were unfinished. The active implementation status is recorded below and in PROGRESS.md. See [the adopted workflow](CHUNKBASE_WORKFLOW.md).

## Active sweep-readiness implementation goal

A persistent native Goal was created in the implementation conversation on 7 October 2026 with the exact objective in SWEEP_READY_HANDOFF.md. That handoff supersedes the older completion checklist above. Durable implementation/verification progress and finite pilot budgets are in [PROGRESS.md](PROGRESS.md). No large sweep has started. All handoff criteria, including fresh candidate-quality review and the evidence readiness gate, must pass before completion.

## Historical implementation checkpoint (7 October 2026)

Configuration/capabilities, immutable baseline regression, explicit discrepancy handling, multi-center density refinement, landscape/structure scoring, distinct-seed ranking, exports and strict SQLite resume are implemented. Initial/optimized ten-seed pilots completed. Current-identity ten-seed predictions exactly match the uninterrupted repeat across74 centers; the100-seed bounded pilot is resuming the remaining90 indices under a recorded finite budget. Meaningful tests include one-block bridges and disputed/border website markers.

Fresh actual matching-version browser evidence is saved separately from the frozen audit. One calibration near miss has weak mountains; a new holdout island is steep and remains unresolved for buildability. Candidate-quality evidence, complete expanded-pilot measurement and final readiness packaging are still pending. The evidence-derived gate is implemented; no ready record or large sweep has been launched, and the persistent goal remains active.

## Sweep readiness achieved (7 October 2026)

All SWEEP_READY_HANDOFF.md implementation and verification criteria are satisfied. The supported native build, dependency/license/provenance checks,80 meaningful tests, frozen159/880-row regression, deterministic scored-island resume proof,100-seed end-to-end pilot, fresh matching-version Chunkbase reviews and artifact/identity readiness gate pass. The pilot produced 781 centers in 41.24minutes including exports; one holdout supports candidate quality, two remain unresolved and one is a near miss. All remaining predictor/game limits remain explicit.

[SWEEP_READINESS.md](SWEEP_READINESS.md) and [readiness.json](runs/sweep-readiness/readiness.json) contain identities, evidence, worker/memory/throughput estimates and tested start/resume commands. The finite initial sweep is 2000 seeds, indices 100..2099, eight processes; approximately 11–14hours under the measured workload, with uncertainty documented. Its exact command passed with --dry-run even from outside the project. No large sweep has started. Persistent goal completion and the requested notification follow the final seal verification.
