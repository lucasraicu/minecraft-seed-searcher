# Accuracy and advanced products — proposed next stage

Status: superseded by the user's2026-10-21 instruction to remove difficult,
terrain-heavy or materially expensive catalog products. This initial proposal and
its two High critiques are historical evidence, not the active implementation
scope. User objective: do item 5 of the remaining-work list,
"Extend accuracy and advanced products where worthwhile." This includes the
remaining spawn, physical-structure, height/small-patch limits and all five deferred
products. None is silently removed from this plan. A failed capability experiment
is an unresolved result, not completion of an implementation promise.

## 1. Reconciled baseline and preservation

The completed local automation milestone is documented in
`reviews/public-automation-scope-2026-10-21/RELEASE_REPORT.md`. Current source
already supplies estimated and observed world-spawn X/Z, per-chunk saved biome
lookup, exact provider-bound tiles, positive structure witnesses and an offline
refinement queue. Do not rebuild these facilities or call them new accuracy fixes.
The 222-world catalog is a prediction-based product, not a generated-world census.

On inspection, the existing personal backend, catalog backend/two query processes
and Vite remain alive; Docker has no running containers. Installed BDS image ID
matches the existing 1.26.52.3 pin. Gemini queue is idle, not quota/auth paused.
The primary tree contains many inherited tracked/untracked changes. No reset,
stash, clean, merge, push, personal restart or binary replacement is authorized.
No new search or BDS world was started for this plan.

Baseline rerun: 19 tests pass in 0.63 s across structure verification, refinement,
spawn adapter and archived game/storage evidence. This checks existing behavior;
it is not new game validation or proof of the missing capabilities.

## 2. Objective and constraints

Improve actual evidence and algorithms where a reproducible method exists, then
make those improvements visible in the existing four-pillar app. Keep personal
scoring and fixed 845/265/140 budgets, three border sides and both independent
branches. Do not generate terrain per screened seed or in HTTP requests.

Use a cheap prediction/candidate stage, followed by explicit bounded offline
evidence work for promising candidates. Candidate selection is not certification.
Retain unknown/pending worlds and existing useful predictions. Do not turn a
different locate, an empty point, failed load or budget stop into absence.

No GPU, custom database engine, public deployment, payments or new personal
sweep. Reuse SQLite queues and compressed CAS evidence; do not add another queue,
storage engine, generic workflow framework or terrain generator. Automated UI
checks plus Codex/Gemini review remain required; interactive browser QA is waived.

## 3. Ordered accuracy work

### A. Spawn and surface evidence

First inspect `estimateSpawn`/`getSpawn` and the retained 108-world discrepancies.
Freeze any proposed causal correction before fresh observations; no fitted
coordinate offset or replacement of raw results. Preserve estimator build/source
identity and rerun source/native parity in an isolated build if native changes
are justified. Check held-out signed extremes, low32-related pairs, negative
coordinates and observed outliers. Improvements must report exact-match rate and
median/tail displacement against actual default-world spawn, including failures.

World-spawn X/Z, generated surface/support height and initial-player landing are
three separate observations. Add observed surface/headroom/fluid/hazard facts
only from loaded, generated blocks at recorded XYZ. Publish the exact tested
conditions, not a general "safe spawn" badge. A Y=32767 sentinel stays null.

Initial-player landing requires a successful legitimate playerSpawn observation,
initialSpawn flag and unmodified default-world settings, before commands/teleports.
The earlier four client attempts yielded zero joins; never retry their failed
unsigned/offline bypass paths. Existing authenticated client availability is a
prerequisite, not an assumed feature. Do not read credentials, change accounts or
automate a user's game client without explicit authorization. Record repeat joins
on separate fresh-player/world copies; a landing is an observed outcome, not proof
that all players have one deterministic XYZ. If unavailable, this requirement
remains open and is reported; an exact world reference cannot substitute for it.

Files: existing `catalog/spawn_estimator.py`, `anchors.py`, `accuracy.py`, existing
game observer/runner and spawn evidence tests; native finders only if a causal rule
and held-out validation justify a separately scoped patch.

### B. Physical structure evidence

Audit all 21 existing structure methods, including OW and Nether. First seek a
stable instance identity and physical piece/footprint data in generated saved
worlds or a supported API. Reuse the stopped-world read-only copy discipline.
Bounded key/schema inventory precedes a decoder; unknown formats stay opaque.
Do not infer an instance from proximity, connected membership or one locate.

The documented getGeneratedStructures API returns feature-type strings at a
point, not instance IDs or bounding boxes. Existing Beta-copy membership evidence
therefore does not certify distinct instance totals or default-world behavior.
If an instance source is found, require independent observed positive controls,
same-instance dedup across chunks, overlapping same-type instances, negative
coordinates, dimensions, rotations and partial-generation tests. Link predictions
to instances using demonstrated source identifiers/geometry, not guessed offsets.

If no identity oracle exists on the pinned build, do not publish exact physical
totals, implement a speculative decoder or claim this track finished. Keep the
21-type research matrix and original predictions; list the concrete missing
oracle. Positive block/type observations can still improve confidence at a point.

Files: `catalog/structure_verification.py`, existing `realm/structure_accuracy.py`,
structure-coordinate helpers and existing stopped-world reader/observer; add at
most one focused instance-evidence module if supported by real retained records.

### C. Height and tiny-patch integration

Existing refinement already proves presence/absence for bounded exact scopes.
Inspect its actual public automation integration before adding behavior. Extend
the existing queue only where it fails to carry applicable witnesses through
evaluation, membership updates and immutable publication. Preserve model, height,
dimension, source/settings and observation-specific game-ID namespaces.

Test OW -64..319 and Nether 0..127 at section boundaries/cave transitions and
record ceilings; compare independently decoded saved records with game reads at
the same XYZ. No global height clamp or seed-only substitute for unknown saved
records. A failure case must survive as a regression before any predictor change.

Prioritize exact tiles around requested missing features or promising candidate
boundaries. Missing coarse samples cannot prune candidates. Do not scan an entire
8192-square world block-by-block. Exact negative results require full requested
scope coverage for that provider/Y; bounds or resource exhaustion remain unknown.

Files: existing `refinement.py`, `refinement_queue.py`, `refinement_worker.py`,
`refined_witnesses.py`, `accuracy_store.py`, automation extraction/evaluation code,
and the existing chunk biome decoder. Measure added bytes, time and recovered
matches against the same frozen candidate set before increasing work caps.

## 4. Five advanced products — stronger definitions need explicit approval

Original promises are in `catalog/products.py`; the five IDs remain deferred in
`docs/catalog/v2/products.json`. These are proposed executable definitions, not
assumptions already accepted by the user. Preserve original IDs/links and make
revision changes explicit. Candidate previews must not enter verified rankings.

All metrics refer to the declared surveyed envelope, game build/settings and
evidence provider. A component reaching an unfinished survey boundary has an
incomplete total. A demonstrated positive size/path lower bound may pass its
threshold without claiming a complete component area or global record. Rank
certified lower bounds separately from completed exact measurements.

| Product | Proposed real acceptance rule | Required evidence / unsolved dependency |
|---|---|---|
| Mega Cherry Grove | One 4-neighbor-connected surface cherry-grove component with two witnessed columns more than 1,200 horizontal blocks apart. Every column along the connecting path has surface cherry evidence. Rank completed measured area descending, then measured diameter descending, then world ID. | Surface-height biome membership and exact path/component coverage. Fixed-Y63 coarse cells cannot prove surface contiguity. An accepted ground/surface rule must be frozen before implementation. |
| Badlands Continental Spine | One surface-connected badlands-family path at least 2,000 horizontal blocks between witnessed endpoints; exposed terracotta on that component and a generated badlands mineshaft with observed gold-ore evidence linked spatially to it. | Proposed meaning of "multiple kilometers" is 2,000 blocks; exact family/ground/terracotta and mineshaft/ore association rules must be approved. No coarse-grid or start-only substitution for continent/terrain claims. |
| Direct-Drop Nether Portal | A specifically recorded standard portal built at OW X/Z=(0,0), with recorded ground Y, orientation and frame; an actual first traversal in a pristine Nether arrives inside an observed fortress corridor or bastion treasure room. | Legitimate player traversal plus generated destination/piece evidence. Projecting floor(X/8),floor(Z/8) is only candidate screening, never a portal simulation. Freeze placement/frame/entry protocol before results. |
| Intersecting Triple Mineshaft | Three distinct generated mineshaft instances form one connected physical piece-intersection graph, with at least one observed cave-spider spawner in the intersecting layout. | Instance identity, piece geometry and spawner block/entity evidence. Three nearby starts or merged membership points do not pass. No working-farm claim; any farm promise requires separate Bedrock simulation/loading rules. |
| Endless Deep Dark Void | A connected player-sized cave route in deep-dark biome joins physical footprints of at least two distinct generated ancient cities; store route XYZ and supporting biome/block witnesses. | Proposed precise replacement for vague "trench/endless": at least two cities connected by a verified route. Exact collision/headroom/fluid rules need approval; this is substantially more expensive than biome presence. No danger-free/working-farm claim. |

Do not silently activate any of these as a weaker biome sampler, cluster of
predicted starts, approximate portal point or unlabeled research result. Where
the stronger predicate remains infeasible, keep the product gated with its actual
dependency and continue independent tracks. If the user wants the original
"endless" or unspecified farm promises literally, additional finite metrics and
farm criteria are required before implementation, not invented after results.

## 5. Implementation order and independent ownership

0. Codex: inspect source, retained evidence, dirty tree/processes; write this plan;
   obtain two neutral Gemini High critiques and reconcile. Approval gate follows.
1. Approved feasibility stage: independent (a) spawn/surface oracle and (b)
   instance/piece oracle investigations. Codex owns BDS execution and evidence
   acceptance. Stop speculative branches at missing oracle, not the other work.
2. Spawn/surface implementation and height/tile integration can proceed in
   parallel in isolated snapshots with nonoverlapping file ownership. Codex
   integrates shared accuracy contracts first; workers cannot both edit them.
3. Component/path evaluators for cherry/badlands depend on accepted surface data;
   mineshaft/city routes depend on instance/piece data; portal product depends on
   a legitimate player client. Implement evaluators only after their oracle gates.
4. Codex integrates supported evidence into memberships/publication and API;
   an independent Gemini High UI worker reviews the existing app changes. Refresh
   only affected catalog worlds in a new immutable generation. Preserve history.
5. Final evidence audit lists each requested capability/product as implemented
   and verified, blocked by a demonstrated dependency, or still pending. Do not
   mark the overall implementation goal complete with pending required work.

Use two Gemini High workers initially: accuracy-method plan critique and advanced
product plan critique. After approval, at most four independent workers, including
one UI/contract reviewer when relevant. Exact writable files, bounded context,
commands, checks and deadlines are set per task. No recursive delegation or
automatic integration. Shared account/quota handling stays unchanged.

## 6. Resource and validation gates

Plan review does not start game runs. Proposed first approved game allowance:
up to 8 new/disposable worlds, one BDS at a time, 2 CPU/2 GiB, 300 seconds/world,
3,600 seconds total including setup/copies, 4 GiB owned output. Validate limits in
the actual chosen runner; do not reuse a helper that hardcodes 4 CPU/6 GiB without
an explicit scoped change. One loaded target region at a time, at most 10 chunks
and 4,096 biome/8,192 block/4,096 membership reads per world. New containers/volumes
must be uniquely owned and cleanup checked. Original worlds mount read-only;
LevelDB opens only a disposable stopped copy. No automatic expansion of allowance.

These caps are feasibility gates, not enough to certify multi-kilometer terrain.
After pilot bytes/time measurements, present a separate bounded expansion for
large components or paths before running it. Native refinement pilot <=8 tiles
of32x32,60 seconds total; no world-envelope brute force. Player/client work requires
the successful authorized-client prerequisite and a frozen protocol.

Checks: existing regressions; independent exact tile/connected-component/path
oracles on bounded synthetic fixtures; saved game positives and near misses;
held-out worlds/coordinates/heights; mismatch and unknown propagation; resume,
budget expiry and crash tests only on changed paths; source identity/digest,
same-anchor scope and dimension invariants; full affected Python suites, existing
Node handler/contract/render suites and frontend build; Codex/Gemini High reviews.

Completion proof must include actual observed positives and adversarial negatives
for each activated game-backed product, not just a mocked provider or green unit
tests. No new physical total without a census/identity proof. No exact absence
without complete scoped coverage. Preserve all raw failures and honest unavailable
states. Personal results/checkpoints/native binaries remain untouched.

Complexity: spawn evidence/tile integration medium; instance discovery high and
uncertain; surface component surveys high; portal/player and piece/farm products
research-dependent. Plan/feasibility findings can be reported before forecasting
full implementation; no honest full ETA exists before oracle and client gates.

## Official reference boundaries checked during planning

Microsoft's Dimension API documents point feature names, not physical instance
identities: https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/dimension?view=minecraft-bedrock-experimental

World API distinguishes default world reference and sentinel height:
https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/world?view=minecraft-bedrock-stable

Current online docs do not establish availability/semantics on pinned BDS1.26.52.3;
existing evidence and new controlled capability probes remain authoritative.
