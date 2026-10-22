# Generalization and player-claim validation — proposed

Status: APPROVED by the user: go ahead with the concrete plan, justify strictness
using seed tests and BDS, preserve potential villages, and use Gemini workers.
Approval covers this bounded audit and its helper implementation; it does not
authorize stricter admission, a new search campaign, serving restart or automatic
catalog rewrite. Original proposal and critique were presented before approval. The last reported-
error correction pass is complete. This proposal addresses broader validation.

Latest user scope clarification: all active generating biome classes and all
supported structure types in Overworld and Nether are required in the coverage
matrix, not just selectable public families. The pinned native inventory lists
56 Overworld and five Nether classes, plus 21 structure types in these dimensions.
All are represented in the frozen cohort; successful observations, errors and
unavailable/subtype verifiers remain separate. Existing frozen End probes are
retained as secondary evidence; no further End expansion is required here.

## Objective and evidence

Establish exactly which version/dimension/feature promises are supported and test
new seeds independently of the prior debugging cohort before Stage D expansion.
Current ENGINE_REPORT documents general MC_26_50 biome/village/outpost fixes,
8320 stored points,330 direct game reads and51 positive/two negative structure
controls. These are scoped observations, not population accuracy or physical recall.
Older all-supported-types report still contains coordinate/subtype/capability gaps
for trial chambers,trail ruins,End cities,temple subtypes,abandoned camp and other
cases. New village/outpost fixes do not automatically resolve unrelated types.
Historical diagnostic documents need clearly labeled supersession notices.

## Ordered work and proposed ownership

1. Codex inventories current feature claims and evidence:14 public structure
   features,nine selectable biome families,22 broader backend types,dimension and
   exact game/model/settings identities. Reconcile existing raw results with new
   engine, WITHOUT rerunning successful campaigns or assuming old verdicts still
   describe current source. Write a matrix of method,observations,unresolved cases,
   support scope and allowed UI wording. Separate observed game facts,computed
   predictions,sampled absence,unavailable verifier and unknowns.
2. Codex freezes a cohort manifest BEFORE observing new game output:16 uniformly
   generated signed64 seed values from a recorded deterministic random procedure,
   plus8 explicitly targeted feature/terrain controls disjoint from prior tuning
   seeds where feasible. Keep targeted and blind results separate. No rerolling
   failed or inconvenient cases; exhausted/missing cases remain reported. Targeted
   controls may be selected using predictor presence and are explicitly biased.
   This is bounded world verification, not a high-throughput seed search.
3. Pilot at most5 worlds (three blind,two targeted) to verify capability,world
   identity,persistence,methods,cleanup and measured costs. Reuse pinned BDS image,
   disposable owned worlds,no published ports,retained sources read-only. A missing
   verifier,semantic ambiguity or resource failure stops dependent checks before
   expansion. Feature-specific unavailable verifiers gate that feature only;
   shared identity/persistence/cleanup failures stop the campaign. After a clean
   pilot expand only if measured per-batch costs fit the remaining declared caps;
   24 worlds is a maximum,not guaranteed completion or feature coverage.
4. Biomes: compare same seed/dimension/exactXYZ against direct BDS queries; freeze
   nomenclature mappings first. Include independently fixed positions and reserved
   holdouts across negative coordinates,heights,cave/surface transitions and biome
   boundaries. Fixed probes supply baseline evidence; predictor-selected boundary
   stress probes are reported separately. Preserve raw names/IDs and storage/API
   lifecycle distinctions; never assume numeric-ID namespaces coincide. Validate
   all selected families/backend classes with available controls; absent controls
   remain unknown. End terrain classes must not be mistaken for BDS biome IDs.
5. Structures: test retained positives,new rejections and discovery independent of
   predicted locations. Distinguish placement reference,navigation point,locate
   output,subtype and generated membership. Preserve exact disagreements; no fitted
   distance tolerance or automatic raw-start offset for an unproven type. In
   particular investigate trial-chamber/trail-ruins reference semantics and temple
   subtype verification rather than hiding all as matches. Sparse negative points
   do not prove absence. Full-volume checks prove only their explicit membership
   bounds; an empty start chunk does not prove absence everywhere.
6. Feasibility gate for recall/count claims: current getGeneratedStructures returns
   type membership at a point, not unique structure-instance IDs. It cannot by
   itself establish a distinct physical structure census. First determine whether
   an independent,version-correct way to enumerate instances exists. Only then
   measure bounded-window recall with frozen deduplication,reference,border and
   guard-band rules. Otherwise publish independent-discovery witnesses/unknowns,
   omit numerical recall/exhaustive-count claims and keep actual totals null.
   Do not schedule full-volume scans as routine cohort work. Their initial pilot
   allowance is ZERO. An optional later batch must name a discriminating case and
   fit a measured remaining budget; it establishes membership only within its
   recorded bounds,never an instance census. /locate alone is never an exhaustive
   oracle. Beta membership evidence stays
   settings/version-bound and cannot silently certify default settings.
7. Freeze any new failure as a regression,diagnose cause,then propose bounded fixes.
   No seed blacklist,no threshold/tolerance edits just to pass,no weakened tests.
   Harness/accounting fixes stay within an approved audit scope; consequential
   predictor changes require an evidence-backed plan/review before implementation.
   Fresh held-out cases after any tuning; repeat only affected checks. Refresh
   catalog only if justified by actual source/evidence changes,with immutable
   provenance,independent query checks and prior snapshots preserved.
8. Release feature-by-feature with explicit evidence and sampling limits. A clean
   cohort means no observed failure in that cohort,not all-seed certification. Add
   accuracy/coverage wording only when its measurement supports that claim. Small
   biome patches can be missed by the catalogY63/stride64 lattice even when each
   sampled point is correct. Promise positive sampled witnesses,not universal biome
   absence,coverage or every patch. Desired exact small-area biome predicates need
   separate dense verification of shortlisted worlds; do not blanket-densify the
   entire8192 envelope. World-spawn,terrain suitability,loot and farm guarantees
   need their own verifiers. For positive multiplicity requirements, separately
   verified distinct instances can support an 'at least N' claim even without a
   complete census. Multiple member blocks are not multiple instances; establish
   distinct-reference semantics first. Keep exact totals and rare density ranking
   claims separate. Reuse the existing evidence UI; do not build another labeling
   system. Stage D follows this explicit evidence reconciliation.

Use one Gemini High reviewer for this plan,tool-free/read-only. For subsequent
execution at most two useful High workers: one owns ONLY scripts/generalization_biome_probe.py
and tests/test_generalization_biome_probe.py; one owns ONLY
scripts/generalization_structure_probe.py and tests/test_generalization_structure_probe.py.
Codex owns scripts/generalization_audit.py,tests/test_generalization_audit.py,
cohort selection,BDS resources,claim matrix,source review and integration.
Freeze helper interfaces and permitted commands before any
coding submission; isolated dirty-baseline snapshots,never primary binary writes.
No duplicate writable ownership. Active BDS concurrency remains ONE regardless of
Gemini concurrency. Independent Codex review is mandatory; worker claims are not
verification. No merge,push,account switch or broad permissions bypass.

## Files and implementation boundary

Proposed new scripts/generalization_audit.py and tests/test_generalization_audit.py
for manifest/resource/result validation; new bounded helpers and tests with
nonoverlapping ownership; fixtures/bedrock-26.52/generalization/ for compact hashed
observations; reviews/generalization-validation-2026-10-20/ for reports; scoped
updates to diagnostic documentation,shared evidence adapters and UI labels only
where actual evidence requires them. Reuse existing catalog_game_probe and
predictor lifecycle/storage/volume helpers; do not rewrite the catalog architecture.
All code/file boundaries are finalized before delegation,not implicit permission
to touch backend/native/frontend wholesale. Personal-engine activation is a
separate controlled deployment after confirming no active personal job and safe
extension replacement; no current service or historical result is changed here.

## Proposed ceilings and complexity

No execution now. Pilot:5 worlds maximum,1800 cumulative game-wall seconds,one BDS
at a time,2CPU/2GiB per container,600s maximum perworld and ZERO full-volume scans.
Total including pilot:24 worlds,7200 cumulative
BDS wall seconds,8GiB owned output,24576 biome API reads,2000 locate commands,
196608 block reads,8192 point-membership reads,786432 full-volume membership reads
(eight full16x16x384chunks). These are fail-closed ceilings,not promises that every
case will fit. Include generation/save/shutdown in wall accounting; no unbounded
retries. Freeze actual batches and checks before starting; stop if capabilities,
IDs,persistence,cleanup or budgets fail. Report untouched/missing cases explicitly.
Host-side data checks capped15min/2GiB; no expensive performance benchmarks.

Acceptance: immutable build/settings/seed/XYZ provenance,blind/targeted separation,
per-feature and per-seed matched/mismatched/unknown/error counts,independent probe
reports,regressions for new defects,and supported UI claims with no fabricated
census. All required applicable focused checks pass. Sampling correlations and
lack of independent instance enumeration remain explicit. No numerical population
accuracy claim or generic95/99.9% guarantee from a small selected cohort.

Complexity: harness/claim reconciliation moderate; an independent instance oracle
may be high-risk or infeasible with current API. Planning estimate after approval:
2–4hours for initial harness/reconciliation/pilot,up to2hours game runtime within
caps,then variable diagnosis time if new discrepancies arise. This is an estimate,
not an established complete-catalog ETA; revise after measured pilot. No GPU or
new database is required for this validation pass.
