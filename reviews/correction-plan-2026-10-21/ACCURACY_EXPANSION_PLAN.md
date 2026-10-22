# Added accuracy work — proposed execution and acceptance

User explicitly added four fixes to the active goal on2026-10-21: spawn, every
supported structure's verification/reference method, height-dependent biome
behavior, and small patches. The current validated native correction/catalog/UI/
load slice continues independently. This plan requires the project's High critique
and final user approval before significant new implementation. No whole-goal
completion while these requirements remain. Interactive browser QA is waived;
Codex automated checks plus Gemini High review remain required. No GPU/custom
storage engine, payment, account switching, personal restart or large seed sweep.

## Evidence that changes the starting point

Spawn audit reviews/spawn-validation-2026-10-17/README.md has108 predetermined
BDS1.26.52.3 worlds, independent level.dat agreement108/108, three no-pack controls.
estimateSpawn median3.83ms,p9511.31blocks,max11.31 observed displacement, exact0/108.
getSpawn exact50/108,max30.53blocks. These are old-source measurements, not a
universal bound; replay CURRENT native source first. Zero observed first-player
joins; four prior client attempts failed transport/authentication. Do not retry
failed unsigned/login paths or use credentials/accounts automatically. Default
world spawn XZ is available without a player, butY32767 is a sentinel, not terrain.

All21 OW/Nether structure types were attempted in the completed24-world audit.
Stronghold/trial/trail reference gaps, generic temple subtypes and abandoned camp
remain. Current public registry has14 structures; backend-only types are not
silently activated as public filters. Experimental getGeneratedStructures returns
feature names containing one point, not instanceIDs/boundingboxes. It cannot alone
certify an exact count, even after scanning connected positive points; overlapping
same-type instances require an identity source. Keep Beta copied worlds separate.

Stored Data3D v3 decoder already derives per-record ceiling and last-Y15 behavior;
8320stored/330direct controls pass. One later OW mismatch matches saved data using
its localY95 ceiling. Missing/interior unknown sections remain unknown. The missing
stored-record issue has a tested dirty/restore persistence protocol on disposable
worlds. No global95 clamp or reuse of v2 repeat-section semantics is valid.

Public observations v1 support only25600Y63/stride64samples and nine biomefamilies;
coverage complete means the declared lattice was evaluated, not that every biome
patch/absence was resolved. V1 model/codec/anchor grid are fixed. Extend via versioned
records and migration; don't reinterpret old complete bits as exact absence.

Primary references checked2026-10-21:
https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/dimension?view=minecraft-bedrock-experimental
https://github.com/MicrosoftDocs/minecraft-creator/blob/main/creator/ScriptAPI/minecraft/server/World.md
Documentation explains interfaces; actual pinned2.10/2.11-beta capability probes
and frozen game evidence determine supported behavior on this project build.

## Architecture and ordered work

0. Finish current corrected extractor publication, independent48600layout numeric
checks, existing-app UI reviews and500-world operational validation. Preserve
baseline results as the comparison, never overwrite raw game outcomes. This is a
milestone within the expanded goal, not permission to stop the expanded goal.

1. Define shared evidence contracts, then independent implementations. New
catalog verification records bind seed,edition,game build,world settings,native/
source hash,dimension,reference kind,absoluteXYZ orX/Z+nullableY,scope,method and
raw evidence digest. Distinguish unknown/unavailable, predicted, observed at point,
located reference, and enumerated physical instance. Never convert errors or
missing data into zero/absence. Preserve all old immutable snapshots/URLs/favorites.
Files: new catalog verification/anchors/refinement modules, versioned contracts,
models/codec/request/coverage/service/view and existing web-ui/catalog only as
needed. Additive schema/revisions or explicit migration, never silently mutate v1.

2A. Spawn: replay108 predictions against current source and inspect source changes.
Integrate estimated world-spawn XZ once per public evaluation world, before final
retention; retain observed world-spawn XZ separately when actual BDS evidence is
available. User-facing names must distinguish the estimate from game-observed
world spawn; neither is exact initial-player landing or terrain/safety proof.
Validate on new held-out seeds; include signed extremes,low32pairs and distance
outliers without selecting away failures. StoreY=null for sentinel, never32767
as usableheight. Compute summaries for all three side lengths at the SAME saved
anchor. Reuse one observation inventory. An out-of-envelope spawn schedules bounded
extra coverage or leaves that layout unavailable; it does not delete the seed.
Support arbitrary anchor coordinates with explicit mode/provenance links; do not
round spawn to the81settlement centers or density-optimize it. If coordinate matches
another anchor, reuse geometry safely without losing the mode/evidence distinction.
Initial-player proof requires a successful legitimate client event on pinned
settings. No automatic account/credential acquisition or authentication bypass.

2B. Structures: build an executable21-type verification matrix. For each type,
source-derive raw-start→locate-reference/variant/piece semantics; challenge current
+8/-8 conventions with held-out negative-coordinate and rotation cases. Temple
subtype requires type-specific evidence; different locate is inconclusive absence.
Investigate camp version/settings/feature registration before treating72no-locate
rows as false absence. Add game point-membership/block/piece witnesses where valid.
For multiplicity, require a demonstrable stable instance identity from game/source
and distinguish overlaps/connected footprints; proximity clustering alone is not
a count. A method without such an oracle remains an OPEN required research item,
not fixed by relabeling. Do not fabricate verified totals or erase useful predicted
starts. Preserve failing references as regressions and retain game/raw/refined
coordinates separately. Native changes only after causal mechanism and held-out
controls; allowlist each supported build/method separately.

2C. Heights: use independent stopped-world decoding plus exactAPIreads as the oracle.
Derive procedural→stored runtime behavior per chunk/volume from source; infer no
ceiling from one witness or only highest non-air block. Test section boundaries,
negativeY,cave transitions,above-count lookup,unknown markers,fresh/reload/copies,
Overworld[-64,319] andNether[0,127]. Preserve raw procedural sampling for structure
gates; expose stored-runtime sampling as an explicit mode/provider. Implement a
seed-only runtime model only if actual per-chunk bounds can be derived and survive
controls; otherwise use game-backed saved observations for those queries and keep
the unobserved case unknown. Missing records are loading/persistence unknowns,
not errors to solve with a global biome replacement.

2D. Small patches: add bounded exact-scope refinement, not merely a denser grid
misnamed exact. At supported Y/dimension, an exact absence claim needs full logical
coverage or a proven conservative cell bound. Prototype cached raw-node/tile
sampling with the same block-coordinate selector; compare every block against an
independent direct path on bounded tiles, and dense BDS tiles including patches
missed by64sampling. Adaptive subdivision may prove absence only with a sound
bound; otherwise subdivide to individual block membership. Store compressed tile
facts/proof masks once per world, reuse across anchors and2048/4096/8192 borders.
Don't dump per-block JSON, triple worlds or repeatedly hash/sample full envelopes.

Sparse missing witnesses remain unresolved; they must not become proof of absence
in retention/index pruning. Required queries can enqueue refinement and distinguish
confirmed matches from potential unresolved candidates. Never label unknown as a
match or rejection. Preserve specialist/diversity/reference retention objectives.
A preference may affect ranking only under its declared evidence semantics.

3. Integrate: migrate/refresh the same200-world catalog with applicable verified
anchors/refinements, no arbitrary extra seed population. Check counts, ranks,
filters, all three borders and same-anchor conjunctions. UI shows concrete scope
and evidence, supports unknown/loading/error states, preserves personal Sweep.
Codex build/render/handler/contracts plus independent Gemini High UI review.
Measure bytes/world, latency and retained coverage; tile/index costs precede any
GPU/custom database implementation decision. Re-run only affected regressions.

## Delegation, resource gates and acceptance

Codex owns architecture, version migration, native integration, evidence admission,
resources and final validation. Gemini High critique: one reviewer accuracy/oracle
feasibility, another dataflow/performance/UX; then bounded implementation ownership
for independent spawn/reference/storage/refinement components, at most4workers.
No overlapping writable ownership, no recursive delegation. Workers never operate
BDS concurrently without Codex scheduling; no unrestricted permissions.

Reuse108spawn +24generalization +new4paired controls and retained stored worlds
first. New proposed pilot:8worlds (4blind,4targeted), then at most24newworlds only
when pilot fits. Freeze seeds/cases/method hypotheses and expected paths before
game observation, preserve every failed attempt. One BDS at a time,2CPU/2GiB,
300s/world/7200s total inclcopies/setup/cleanup,4GiB ownedoutput; dense reads at most
4096biome/8192block/4096membership per world, up to10loadedchunks at once, release
owned areas safely. World spawn reads don't need player joins; authenticated
player testing is a separate prerequisite. Native exact-tile pilot at most8tiles
32×32 per dimension/height, <=60s/512MiB output; extend only after measurements,
never launch whole8192² block scans blindly. Immutable protocol hashes before run.
No speculative binary rewrite, no same-data tuning disguised as validation.

Acceptance is capability-specific: (a)spawn anchor/provenance/coverage correctly
integrated with honest world-vs-player semantics; (b)every21type has a documented,
executable positive verification route, and any physical count is instance-backed;
(c)per-chunk height lookup agrees with independent saved/game evidence, unresolved
seed-only contexts remain explicit; (d)small-patch positive recovery and exact
absence proof cannot silently fall back to64grid. New held-out controls, old
regressions,legacy models/versions and partial coverage all pass. Each unresolved
oracle/mechanism remains tracked work, not a blanket "100% accurate" claim.

Complexity high. First concrete feasibility/contract stage likelyhours; full
implementation and diverse game validation likelyseveral focused workdays. No
reliable date for all physical-instance/initial-player semantics before checking
oracle/auth availability. Report those blockers accurately without discarding
other useful work or declaring the expanded goal complete.

## Reconciled execution decision after two High critiques

Reviewsa47b85533a04/edcb454d9672 succeeded,exit0,denied[],16802/16985reportedtokens,
no edits/tests. Codex inspected actual responses. Current-source replay now
preserves108/108 earlier estimatedspawn coordinates (new game runs not repeated).

Keep WORLD-aligned observations/tiles independent of arbitrary anchor coordinates;
only summary evaluation and anchor provenance change. No anchor-relative resampling
or persistent Y32767. The architecture review's alleged lattice-fracturing is not
necessary and is expressly prohibited. Stage1 contracts precede later schema work.

Freeze strict result semantics: normal matches require positive proof under the
chosen provider; unresolved candidates can appear separately with explicit badges.
An offline bounded refinement queue may process them; normal web queries never
launch BDS. Neither mode fabricates matches. Removing a candidate from a strict
result page is not deletion of that seed from retention or a claim of absence.
Only a complete negative proof for the EXACT requested scope/provider can mark
that predicate false; an entire global envelope need not be negative to answer a
smaller query. Scope/height/provider are mandatory proof-cache keys.

Do not adopt the suggested analytic noise-interval optimization without proof.
A finite candidate-node bound from the already-defined Voronoi selector may be
cheaper: for each cell enumerate ALL selectable raw nodes, prune only if none can
match, otherwise evaluate every required block in that cell. Validate this bound
independently; it proves procedural-model absence only, not unknown stored-runtime
absence. Brute-force bounded tiles remain the oracle/fallback. Native eight-tile
pilot and game4096read cap are different stages: game pilot at most four32x32tiles
TOTAL per world across all dimensions/heights, reserving reads for boundary cases.
No unbudgeted8×32² game scan or whole-border scan.

Correct unsupported review claims: camp non-registration is an unproved hypothesis
until actual command/source registration is inspected;72no-location rows do not
establish it. Point membership returns strings, not bounding boxes, so connected
components do not certify counts. Counts remain predicted starts or properly
identified game instances; do not rename them arbitrary "cluster density".

Proposed practical implementation covers estimated/observed WORLD spawn, correct
structure references and positive evidence routes, explicit chunk-aware height
providers, and small-patch refinement/proofs. Exact initial-player landing and
full physical-instance census require legitimate client/identity oracles; keep
those guarantees gated unless the user explicitly requires them as completion
criteria. They are not silently "fixed" by labels. Present this distinction for
approval before dispatching significant new implementation. User may keep those
research tracks required; then goal remains active while they are unresolved.
