# Bedrock spawn audit — 2026-10-17

**Verdict: retain Estimated spawn as a planned public catalog anchor, using `estimateSpawn`. Keep exact initial-player spawn unsupported.** The world-spawn accuracy question now has positive independent evidence. Full catalog extraction cost, spawn coverage, and runtime activation still need implementation/measurement; this audit enables no application capability.

## Measured results

Pinned vendor `MC_26_50`, unmodified prediction routines, compiled `-O3`; independently generated vanilla BDS **1.26.52.3** worlds. The cohort contains 100 predetermined SplitMix64-derived signed seeds plus eight edge/example seeds, including both signed-64-bit extremes. Predictions were saved before generating the worlds; no tuning or cherry-picking followed the observations.

All distances below are Euclidean **horizontal blocks to BDS's default Overworld spawn**, not player-placement errors.

| Measurement | `estimateSpawn` | `getSpawn` |
|---|---:|---:|
| Worlds compared | 108 | 108 |
| Median displacement | 8.94 | 5.73 |
| p95 displacement, nearest rank | 11.31 | 17.49 |
| Maximum observed displacement | 11.31 | 30.53 |
| Within 16 blocks | 108/108 | 98/108 |
| Within 64 blocks | 108/108 | 108/108 |
| Exact X/Z matches | 0/108 | 50/108 |
| Median `applySeed` + routine elapsed time | 3.83 ms | 4.05 ms |
| p95 elapsed time | 5.01 ms | 5.33 ms |

Use the fast estimate: its observed tail error and latency are better, even though the detailed routine matches some coordinates exactly. This is a useful location estimate, not an exact-coordinate capability. The measured maximum is **not** a certified bound for untested seeds or versions. The earlier 3.04 ms median from a smaller probe and this 3.83 ms median are separate local samples, not contradictory throughput guarantees. Routine timings are serial wall-clock intervals on the local iMac with uncontrolled host activity; no V100 or server throughput was measured.

## Independent checks

- Each world had the requested signed seed, zero players, default spawn radius 10, and identical default spawn at world load, tick 20 and tick 40. All 108 shut down cleanly.
- A separate LevelDB/NBT toolchain read saved `level.dat`; persisted `RandomSeed` and `SpawnX/Y/Z` agreed in all 108 worlds.
- Three fresh no-active-behavior-pack controls matched their corresponding cohort worlds. The observer only reads getters and events; it never sets spawn, teleports, changes gamerules or sends commands.
- The estimator returned identical results when repeated for all 108 seeds.
- Existing spawn evidence and display regressions: **47 passed** (`tests/test_two_group_config.py`, `tests/test_web_spawn_metric.py`). These check existing behavior; they are not additional independent game observations.

`getDefaultSpawnLocation()` returns the world's default spawn reference. The observed Y value of **32767 is a sentinel**, not a usable surface height. Microsoft documents that distinction in the [World API](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/world?view=minecraft-bedrock-stable). Do not save it as predicted player Y, terrain height, dry ground or safety evidence.

## Initial-player placement: not validated

Four isolated offline client attempts for seed 12345 produced **zero player joins**:

1. RakNet attempt: the pinned BDS logged that NetherNet is required; no connection was established.
2. HTTP/NetherNet with the newer transport implementation: the client required a player identity before sending an offer.
3. An unsigned HTTP offer to our offline-only disposable server: server rejected it with code 37.
4. An offer signed with a fresh local offline identity: server again rejected it with code 37.

No account credentials were requested, imported or used. No observed `playerSpawn` event exists. These are connection/authentication failures, **not measured spawn prediction failures**. They neither validate nor disprove initial-player placement. The HTTP transport is described by [Mojang's onboarding guide](https://github.com/Mojang/bedrock-protocol-docs/blob/main/additional_docs/NetherNetOnboardingGuide.md); NetherNet authentication and game login remain distinct from observing the world reference.

The retained client is a diagnostic experiment, not a supported player verifier. Successful authenticated joins on this exact build/settings remain necessary before claiming exact player-placement accuracy. Do not satisfy that gate with `level.dat` or the default-spawn getter.

## Catalog decision

1. Keep **Recommended settlement**, advanced **Origin**, and planned **Estimated spawn**. Spawn's center stays fixed at the predictor's absolute integer X/Z; do not improve it by density. Player-facing wording: “Search around estimated world spawn. Your actual starting position may differ.”
2. Persist separate provenance kinds: `estimated_world_spawn`, `observed_world_spawn`, and `observed_initial_player_spawn`. Save source/predictor identity, exact tested game build/settings, X/Z, nullable Y, and evidence ID. An empirical error summary must not become a per-world certified error bound.
3. All border sizes and filters use that same saved anchor. Support the existing 2048, 4096 and 8192 side lengths. Check complete observation coverage for each spawn-centered layout; schedule bounded extra tiles or mark the layout unavailable. Do not assume that the original envelope covers every spawn.
4. Compute once per world in the chosen public evaluation population, reuse observations and summaries, and cache the result. If spawn quality affects retention, evaluate it before final public admission for that population. Enriching only settlement winners cannot produce an unbiased spawn catalog.
5. Do not insert a ~4 ms call into every raw personal-search rejection path. One million calls at this measured median is approximately 3,835 seconds of serial elapsed work before extraction overhead. Benchmark the public workload on the actual machines. The proposed ≤5% added cost per complete public record remains **unmeasured**, because that extractor does not exist yet.
6. Keep runtime flags off until integration, coverage, version acceptance and complete-record cost checks pass. This audit supports the estimated-anchor design; it does not authorize a “verified spawn,” safe spawn, exact player block, universal error bound or multi-version claim.

## Evidence and reproduction

- `summary.json`: both methods' metrics and per-seed displacement; recompute with `python3 reviews/spawn-validation-2026-10-17/analyze.py`.
- `seeds.json`, `predictions.json`, `bds-cohort.json`, `persisted-metadata.json`, `controls.json`: full retained observations, including all outliers.
- `identity.json`: exact BDS image ID, compiler command and source hashes. `followup-identity.json` records the client versions and follow-up checks.
- `observer.js`, `spawn_predict.c`, `bds_runner.py`, `run_cohort.py`, `run_controls.py`: disposable-world observer, prediction harness and controls. The BDS image must already exist; its image ID must match the identity artifact. Scripts create worlds exclusively and refuse to overwrite existing paths. `run_cohort.py` uses two worlds concurrently and needs Docker, C compiler and the pinned vendor checkout. Run controls only after the cohort completes.
- `join-attempts.json`: every failed connection attempt and client error. Earlier client variants are retained alongside `client/join.js` for diagnosis.
- Client experiment dependencies: Node image in the follow-up identity; `bedrock-protocol@3.60.1`; clone `https://github.com/PrismarineJS/node-nethernet.git` into `client/nethernet-source` and check out commit `6431f0f98a4c82d919e59fdbdb54e576e939b9dd`; run `npm ci --ignore-scripts` from `client`, then apply `client/http-offline.patch` inside the transport checkout. The patch allows testing an unsigned offer against our own offline server; it changes no application dependency. The signed variant creates a temporary local identity in memory. `run_join.py` runs the client inside the disposable server's network namespace. This path is expected to fail authentication as documented above; it is not a completed verifier.

Generated worlds, downloaded dependencies, native test binaries and nested third-party checkouts stay local and are excluded from publication. All audit containers have stopped. Existing application and native changes were preserved.
