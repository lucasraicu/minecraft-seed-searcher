# Proposed Stage D — evidence first, estimated spawn second

Status: proposed; application implementation not started. User authorized the
completed direct village audit, not an unbounded verification campaign.

## Objective and ordering

1. Resolve or explicitly retain the observed village disagreement. Reuse the saved
   world and pinned build for a bounded generated-chunk investigation; inspect
   engine structure metadata if supported, otherwise suitable generated-block or
   saved-world evidence. Do not equate a missing locate response with proven absence.
   Compare native viability/version rules at the offending location. Freeze it as
   a regression case; do not weaken the predictor based solely on one locate result.
2. Add a shared versioned evidence overlay for all four pillars, retaining existing
   immutable predictor observations. Bind source observation hash/world ID, exact
   edition/build/settings, dimension, feature, coordinate, method, verifier version,
   outcomes and artifact checksum. Validate imports and reject mismatched provenance.
   Distinguish untested, engine-located, generated evidence, disagreement and errors;
   failures/timeouts never become absent or zero. Record exhaustive scope separately.
3. Query/API/UI expose evidence by feature and selected anchor/scope. For this seed,
   show27 engine-located positions and1 unresolved prediction, with the explicit
   radius/Origin scope. Confirmed-location counts are lower bounds unless recall
   and completeness are established. Separate research-density ranking from any
   verified ranking; partial certification must not silently alter ranking semantics.
   Plain structure names and concise badges can replace jargon only when the
   supporting count and evidence remain visible. Do not activate gated presets.
4. Integrate estimated world spawn separately after evidence contracts stabilize.
   Current v1 summary codec permits81 grid anchors, so use an explicit new artifact
   and query version for arbitrary spawn coordinates. Retain v1 compatibility.
   Estimated world spawn is not exact player placement, safety or terrain height.
   Preserve nullableY, estimator/build/settings provenance and measured audit scope.
   Validate geometric coverage for each2048/4096/8192 square border; incomplete
   coverage is unavailable, never zero. No16384 option. All requirements use one
   selected anchor, and radius-circle queries remain distinct from square borders.
   Run estimator once per retained public world, not on every personal reject.

## Architecture and affected areas

Proposed evidence artifact schema/validators and reader in `src/seed_search/catalog/`;
product views/registry, query/service/API routes and
`web-ui/src/catalog/` consume shared evidence. New focused tests under
`tests/catalog/` and UI contracts. Estimated-spawn support affects geometry,
versioned codec/query validation and extractor only in a later dependent step.
SQLite metadata plus existing checksummed artifacts stay in place. Retain
predicted observations without silently rewriting old snapshots or v1 identities.
No GPU, custom database engine, billing, deployment or personal-search changes.

## Assignments and resource needs

Codex owns integration, native diagnosis, pinned-game verification and review.
One Gemini High worker critiques this plan and evidence inference (read-only).
After approval, at most two isolated High coding workers: evidence schema/API and
UI rendering/contracts, with nonoverlapping files and frozen interfaces. Spawn
codec/extractor follows evidence integration, not concurrent incompatible edits.
Small unit/integration checks first. Any larger game cohort requires an explicit
seed/query/CPU/memory/wall/output budget; no full catalog generation during review.
Complexity: evidence schema/query moderate; village root cause uncertain; arbitrary
spawn codec migration moderate-to-high. Completion dates depend on the diagnostic
result and verification tooling; bounded checkpoints are more reliable than an
unqualified launch ETA.

## Acceptance and tests

- Saved direct-audit mismatch preserved; inference distinguishes locate and physical generation.
- Evidence cannot cross seeds, builds, dimensions, features or source hashes.
- Duplicate positions, malformed overlays, corruption and stale evidence rejected.
- Same-anchor aggregation; exact radius and border edges tested, including negatives.
- Partially tested worlds never appear as fully verified or exhaustive record winners.
- Unknown/error remains unknown; no phantom count, fallback zero or global badge.
- All five live research lists and future preset predicates use shared evidence.
- v1 artifacts/queries still work; spawn outside any supported coverage fails explicitly.
- Estimated-spawn precision and measured108-world limits visible; no exact player spawn claim.
- Relevant Python, native parity if C changes, TypeScript/build and UI contract checks pass.
- Original Sweep PID60144, native binaries and unrelated dirty work remain preserved.
- Browser visual/keyboard QA stays pending per user until explicitly resumed.

## Principal risks

Locate semantics may explain some disagreement; physical generation tooling is not
currently established on pinned Script API2.10.0 (`getGeneratedStructures` was
undefined in the retained probe). Do not assume latest web API is installed.
27/28 from one selected seed is not a population accuracy estimate;80/80 third-party
controls are not a game accuracy estimate. Finite catalogs do not imply global
Minecraft records. Estimated spawn errors have no universal maximum established.

## Independent Gemini High critique and reconciliation

Task `0c29cff8e16a`, model `gemini-3.8-flash-high`, explicit effort high:
exit0/SUCCESS, denied_actions=[], changed_files=[], substantive response,
15,629 reported tokens,42.01s. This was a tool-free critique of the evidence and
proposal supplied in the prompt, not an independent execution of BDS or source audit.
Worker supported evidence-first sequencing, provenance binding, partial-ranking gates
and shifted-anchor coverage tests. Codex accepts these recommendations.

Codex does not adopt the worker's unsourced descriptions of village meeting-point
coordinates, exact internal locate search behavior or player-spawn displacement.
The worker also loosely described all grid points as inside the radius; the actual
8x8 grid spans a square and its returned coordinates were independently circle-filtered.
The proposed tolerance-based matching is not accepted: preserve exact matching here;
27 exact controls make an arbitrary tolerance inappropriate, and the discrepant
returned point is742 blocks away. Future feature-specific matching must document
and validate semantics rather than choose a tolerance to pass tests. Only the
observed command output is established; internal rejection cause remains unknown.
A worker's word “approved” is a recommendation, not user implementation approval.

Next approval scope: implement steps1–3 (shared evidence and bounded single-world
diagnosis); step4 estimated-spawn work follows separately after those checks pass.
No larger cohort is included in that proposed scope.
