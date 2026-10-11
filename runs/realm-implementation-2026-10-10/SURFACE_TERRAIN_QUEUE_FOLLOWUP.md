# Surface evidence and durable terrain work — 10 October 2026

This checkpoint advances the existing migration; it is not a full completion or exact Realm certification claim. No new baseline seed range or large throughput benchmark was run.

## Implemented and tested

- Fixed baseline membership revisions serve both V1 and V2. Later baseline arrivals require an explicit new revision. Work units preserve every nominated center, resolution, halo and unfinished state across invocations. Compressed exact-lattice prediction observations are shared across variants; actual observations use private scope rather than silently adopting another generation snapshot.
- Failed, missing, unsupported and unstable samples persist immutable attempt evidence and closest metrics, remain retryable, and never establish absence. Atomic lease/attempt ownership protects retries and rollback. Rotating indexed pool cursors prevent a failing first anchor from starving later anchors under a one-candidate limit. Counts distinguish uninitialized pool members from queued work.
- Candidate evidence patches read and merge under a SQLite write lock. Concurrent independent patches preserve both fields; invalid identity/qualification changes and caller-owned transactions reject safely.
- Actual surface biome string names carry query Y, canopy policy and sampling uncertainty. Mojang Bedrock aliases map to the agreed families without guessed numeric IDs. Arbitrary unmapped names cannot establish wooded-family absence. The pinned runtime registry lists Dappled Forest and Sulfur Caves; registry availability does not prove their spatial generation accuracy.
- Explicit `verify-biomes --run <run> --candidate <id> --points <JSON-file>` uses up to 16 in-bound points in one BDS world under the shared attempt budget. Positive family evidence and sampled bonus intervals remain separate from prediction scores and overall baseline qualification. Rescoring uses saved detections without generation; JSONL/CSV/human summaries expose the actual evidence channel.

## Controlled actual BDS evidence

Artifacts are under `bds-positive-column-fixtures-0a5b7c`. The disposable world used the previously selected signed seed `-1001562501133105644`, official BDS 1.26.52.3, 4 CPUs and a 6-GiB container allocation. Nine small controlled cases cover primary water, flowing water, waterlogged seagrass, a waterlogged slab, thin/solid/powder snow, ice-covered water, and an elevated lake. They are deliberately rejected from natural-world terrain rankings.

All nine cases matched same-tick reference/native column reads, with no missing columns. One flowing-water column settled; subsequent scans changed zero columns. Positive saved/API comparison had 19 probes: 13 exact palette matches and six full state differences. All six saved palettes resolved in the matching runtime to exactly the originally observed API type/states. All 16 overlay checks matched, including three positive overlay-water probes. Raw exact differences remain retained, not relabeled as byte-for-byte equality. The container peaked at 294,612,992 bytes in this small experiment; Docker VM overhead is excluded.

Runtime testing exposed and corrected two fixture issues: setting `flowing_water` canonicalizes the placed block to `water` with the same fluid state, and a waterlogged block must be cleared before setting original air. All 382 journal cells then restored to their exact original API state. A separate clean restart with read-only `testforblock ... air` commands confirmed all 382 cells again, in 42.66 seconds, with clean shutdown and no mutations. Microsoft's [testforblock documentation](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/testforblock?view=minecraft-bedrock-stable) describes this direct block check.

The generic stopped-world reader still reports the erased all-air subchunks as unknown (382 probes, no decoded mismatches); it does not infer air from a missing subchunk. The fixture snapshot contains four finalized chunks of the nine requested because only fixture-containing chunks were dirtied. This proves positive sampled controls and restoration, not complete requested-region snapshot coverage or natural formation geometry. All raw failures, mutation/rollback journals, palette differences and cleanup artifacts remain saved.

## Current natural-world regression

The first current-tooling two-point check observed forest and taiga names in the matching API, but correctly left the family requirement pending because saved/API default-state differences failed consistency. The natural 32-square check finalized all 9 requested chunks, read 16 stable columns and matched all 57 overlay checks; six of 62 probes differed only in saved/API default states for grass, dirt and sand. These failures reproduced the need for an automated exact-runtime saved-palette interpretation pass. Its integration and final current-source test/runtime results are recorded below when terminal evidence is available.

## Remaining full-goal gates

Authoritative generated required structures and complete Stronghold discovery recovery; complete actual V1/V2 positive and negative formations; natural-ground structure provenance and fractional fluid height; broader predictor calibration and population false-negative estimates; overlapping generated-world/final Nether reuse; meaningful accessibility; raw-raster storage/retention policy and arbitrary-boundary crash controls. Existing throughput measurements are preserved; throughput after these changes is unmeasured.

## Final current-policy runtime evidence

The same selected seed was rerun after integrating exact-runtime palette confirmation. Artifacts: `actual-surface-verification-8601a6`.

- Two explicit in-Realm points, (-460,580) and (-76,580), produced stable actual Taiga at Y65 and Forest at Y70. Both requested chunks finalized. Three saved/API probes had two exact matches plus one runtime-proven full-state equivalent, with zero unknown or unresolved mismatches. The wooded-family presence requirement is VERIFIED, while the point observation and overall baseline remain PARTIAL/predicted as appropriate. This does not prove regional absence, structures, or terrain. Point verification took 25.406 seconds in this selected check.
- The natural 32-square water-region request at 8-block spacing finalized all 9 requested chunks and produced 16 usable surface biome observations (Beach, Cold Ocean and Plains). Of 62 probes, 56 exactly matched and 6 were individually proven equivalent in the matching runtime; 57/57 overlay checks matched. No unresolved or unknown comparisons remained. Natural-ground provenance is still unverified, so the raster correctly remains PARTIAL.
- Each request used one reserved attempt, including its same-container palette-confirmation restart. Initial and confirmation servers all stopped cleanly. Combined elapsed time was 41.021 seconds. This is selected small-region cost, not full formation throughput or a broad speed comparison. Production baseline coverage did not change.

Exact palette differences are retained alongside semantic proof. Confirmation is bounded to 64 unique palettes, 8 per request, under the existing single-server lock and original attempt. Primary block or overlay differences, missing/unsupported states, extra/wrong states, identity mismatch, incomplete cleanup and unknown cells cannot be promoted to consistency. Saved snapshots are copied while stopped before any resolver restart.

Concurrent scoring revisions are also handled: surface evidence publication takes the short scoring lock after generation, checks the revision and applies current weights from saved names without generating again. Prediction scores and eligibility remain unchanged.

Intermediate broad test evidence: 389 Realm tests passed in 33.59 seconds; the pre-semantic full suite passed 530 tests in 122.01 seconds; the semantic source passed 559 tests in 123.99 seconds before the final scoring-publication regression. These are intermediate source states. Final-source output and manifest below are authoritative for this checkpoint.

Remaining full-goal work is unchanged by the small positive checks: authoritative structure evidence and discovery recovery, complete natural V1/V2 reference formations, natural-ground provenance, population calibration, overlapping BDS/final Nether reuse, accessibility, disk retention and broad crash controls. Resource extrapolations from existing measurements are in RESOURCE_FORECAST.md; no new large seed benchmark was run.

## Final-source validation

The final repository suite passed **560 tests in 119.03 seconds**, exit 0, after the surface scoring-publication safeguard. `surface-terrain-queue-final-source-tests.log` is the authoritative terminal output. Both final runtime observation identities match current tooling hashes, all their saved/API differences satisfy the strict pinned-runtime proof validator, and the 16-cell natural raster remains PARTIAL despite all cells being known. Six pinned native/vendor inputs match the original pre-change manifest. Docker reports no running containers and the verifier cleanup guard is absent.

`surface-terrain-queue-manifest.json` records final source/test/configuration hashes and checkpoint evidence. The full goal remains active and unfinished; no completion notification was sent.
