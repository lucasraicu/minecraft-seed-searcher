# Practical accuracy extension — local research catalog

Current2026-10-21: the separate spawn helper now uses the fitness-search position
before chunk centering and matched124distinct BDS1.26.52.3 controls (116retained,
8fresh). The222-world catalog has migrated to those predicted references, reusing
raw facts and preserving old snapshots. See
[release evidence](../../reviews/accuracy-advanced-products-2026-10-21/RELEASE_REPORT.md).
The original200-world extension and centered-estimator errors below are historical
evidence, not measurements of the corrected helper. Player landing/Y/safety and
physical counts remain unsupported; no stronger claim follows from finite controls.

This extends the existing four-pillar app. It does not activate public hosting,
billing, terrain/farm guarantees, exact initial-player landing or physical counts.
The original `catalog-observation-v1`, packed summaries and query-v1 remain valid.

## Player-visible choices

Recommended settlement selects among the 81 saved centers. Origin is (0,0).
World spawn (estimated) uses the saved native estimate without moving it to a
more attractive location. World spawn (game observed) appears only for records
with actual default-world X/Z evidence. Both spawn modes have nullable ground Y;
32767 is a sentinel, never a usable height. Neither claims first-player landing,
dry ground, safety or that a recommended settlement moves the player in game.

The current 200-world cohort has estimated anchors for all worlds and fresh
observed anchors for three overlapping pilot worlds. Three border sides remain
2048,4096,8192. All predicates use one anchor. Absolute observations are reused;
there is no second/third generation pass for larger borders. An uncovered spawn
layout is unavailable rather than invented zero counts or seed rejection.

## Contracts and persistence

`accuracy.py` validates seed/build/settings/source/native identity, dimension,
provider, observed game build and evidence digest. `anchors.py` defines arbitrary
anchor records and a separate `catalog-anchor-summary-v1`; grid-v1 rows are not
relaxed. `accuracy_store.py` writes immutable content-addressed generations under
`accuracy/`, with an atomically replaced latest pointer for a base snapshot.
Requests explicitly pin the generation; older generations remain readable.
Published anchors/tiles cannot be removed from later generations of that same
base snapshot. New snapshots can carry compatible retained-world facts forward.

The versioned request is `catalog-query-accuracy-v1`, with required
`accuracy_generation` and `evidence_policy=predicted_plus_refined_witnesses_v1`.
It supports Origin, Recommended, world_spawn_estimated and world_spawn_observed.
Legacy query-v1 still uses predicted_observations_v1. A known biome witness can
satisfy an OR predicate without establishing absence of other alternatives.
Missing sparse witnesses remain unresolved. Potential candidates are returned
separately and never counted as matches or deleted from retention. No HTTP query
launches a game server or extraction worker. Cache/cursor keys bind the request,
base snapshot and accuracy generation; integrity validation precedes cache reuse.

`refinement.py` stores compressed uint32 tiles (at most4096 blocks/tile), namespaced
by provider/build/settings/seed/Y and absolute half-open bounds. Every logical
block is represented; unknowns are explicit. Exact absence requires full coverage
of the precise requested box/circle intersection. Conflicting overlap is an error,
empty scopes are rejected, and an uncovered block prevents an absence proof.
This bounded reference path uses brute force, not an unproved adaptive bound.
Native-model IDs are build-bound. Game-run ID namespaces remain evidence-bound;
separate observations cannot silently share an inferred numeric namespace.

`StoredBiomeProvider` reads explicit per-chunk Data3D records, preserving unknown
interior/missing records and each record's own ceiling. It never substitutes a
seed-only biome or a global Y95 clamp. Saved-ID/name maps must be explicit; measured
pilot associations are not a universal equivalence with native numeric IDs.
The dimension-aware stopped-world reader recognizes Overworld9-byte and
Nether/End13-byte biome keys. Source worlds mount read-only; LevelDB opens only a
copy. Old Overworld-only export behavior is unchanged by default.

The read-only `/api/catalog/biome-scope` endpoint requires a pinned generation,
world, provider ID, height, exact bounds and raw-ID alternatives. Responses are
present/absent/unknown within that exact scope. These proofs do not certify another
height/provider or the whole border. Detail responses list saved tile scopes.

## Structures

`structure_verification.py` exposes an executable21-type matrix. Observed type
membership at a point, game-located reference, predicted raw start and navigation
projection remain different facts. Physical totals stay null. Strongholds have a
reliable game-reference route; point membership was not observed in this pilot.
The other20 types have positive sampled Beta-copy membership witnesses, explicitly
separate from default-settings certification. No empty point or different locate
is a proof that a predicted instance is absent. Only the prior audited outpost,
mineshaft and fortress navigation offsets are projected automatically. Variable
piece references are saved directly rather than guessed from a universal offset.

The pinned vanilla pack declares `abandoned_camp` as a structure SET with18
biome-specific structure identifiers. The generic set command returned no location;
exact taiga/forest identifiers returned references on two independent seeds,
including negative X/Z. Exact taiga membership was observed. This corrects the
verifier; it does not discard the earlier72 failures or invent a camp count.
Temple subtypes require their exact type-membership witness; generic `/locate
structure temple` cannot establish a subtype.

## Offline work and two-branch integration

`accuracy_harvest.py` optionally wraps the existing public drain. It estimates
world spawn BEFORE public evaluation, checkpoints its provenance, reuses it on
resume and carries compatible anchors into the published snapshot. It never
consults personal qualification or changes personal checkpoints. Supply all three
pinned estimator options to `scripts/catalog_harvest.py ... drain`:
`--spawn-estimator`, `--spawn-estimator-sha256`, `--spawn-source-sha256`.
Use the validated isolated runtime/script when the primary binary is deliberately
older than current native sources. Missing estimator capability defers work; it
cannot turn into Origin or reject a useful seed. Existing v1 drains remain valid.
No new seed campaign was launched while testing this adapter.

`RefinementQueue` is an offline100-job spool with leases, generation fencing,
cancellation, three-attempt ceiling and atomic results. `python -m
seed_search.catalog.refinement_worker --spool PATH --descriptor FILE
--execute-one` explicitly runs at most one native tile. Descriptor keys are
context,bounds,y. Native source/binary identity must match. Other providers require
an explicit offline oracle; the worker does not automatically launch BDS. Normal
web requests remain read-only.

## Evidence and operating limits

Portable101-file evidence archive (`accuracy-evidence-v2.tar.gz`):
fixtures/bedrock-26.52/accuracy-expansion/. The earlier84-file archive is retained;
v2 adds reproduction sources without replacing historical raw evidence.
Eight fresh default worlds (four blind/four targeted) yielded16496 exact API reads;
16446 procedural matches,50 targeted height-representation differences. The
saved-record path has consistent scoped ID/name associations for15462 readable
points;1034 initially missing Nether points remain recorded as unknown. A separate
owned-copy dirty/restore repair persisted the missing two chunks, preserving the
original and resolving the full repaired point set. Sampled ceilings include
63,79,95,111,127. No global height rule was inferred.

All eight world-spawn API values match independent level.dat X/Z. Estimates are
not exact on these eight; maximum observed displacement is11.314 blocks, not a
universal bound. The previous108-world evidence remains historical, not fresh tests.
One dense game tile recovers99 taiga points absent from that tile's single coarse
sample; it does not establish the total size of the surrounding biome component.

The 500-world/121500-layout synthetic ingestion/retention/reference checks and
200-world full-layout killed-publisher recovery passed. The default10-second
HTTP capacity gate at500 worlds FAILED under eight simultaneous distinct cold
queries: two admitted requests timed out and six returned busy. Pagination over500
worlds matched the oracle. This is a measured performance limit, not a passed
production SLA or evidence for changing storage engines without profiling.

Interactive browser QA was explicitly waived. Automated frontend build, real-source
hook/render/contract checks, Codex review and Gemini High critiques are used.
