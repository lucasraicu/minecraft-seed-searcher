# Evidence-corrected catalog refresh proposal

Scope already user-authorized: validate fixes, preserve regressions, then refresh
catalog results. No new seed extraction, GPU work, custom DB or paid/public rollout.
Native cave/structure rules remain approximate; do not claim a general engine fix.

Inputs: existing200-world/48600-layout snapshot and its immutable evidence overlays;
frozen default-settings stable BDS lifecycle worlds; beta-API copied-world full
candidate-chunk membership, positive controls; user-confirmed village absent and
static stronghold present. Remove ONLY village[-296,-312] and outpost[528,512] on
seed-3509659830737203357, preserving all other candidate coordinates. Do not remove
strongholds. No global AncientCity/proximity/height/terrain filter.

Implement pure versioned transformation module and tests. Require exact expected
source model/build/settings and reviewed adjudication records, full signedseed,
source world/observation identities, fixture hashes and explicit false-positive
verdict. Neither locate difference nor empty individual point alone is enough.
Full candidate-chunk absence is scoped corroboration with controls, not global
world census. Make manual reviewed decisions explicit and immutable.

New snapshot identity model_id/source_sha fingerprints this transform+reviewed
adjudications; retain original native_sha and strict research identity, never label
it accepted public-game compatibility. Apply new header consistently to all200
observations in generation. Preserve raw original snapshot/artifacts. Each new
observation retains original observation ID and transformation provenance in metrics.
Only correctedworld recomputes243summaries; other summaries preserve packed
counts/nearest/coverage exactly while rebinding world/observation/layout identities.
No biome plane re-extraction or Y63value correction. Old summarycountsemantics stay
predictor candidates with reviewed removals, NOT exhaustive physical counts.

Evidence overlays rebound into new immutable namespace with originalsourceaudit
hashes/provenance. Removedcandidate checks retained in reviewed correction ledger,
not passed as still-present observation coordinates. All remaining raw observations
retained exactly. Do not upgrade any evidence outcome; navigation differences remain.
Existing importer format remains strict; no fake stable report from beta data.
Products rederived from corrected observations. No UI wording silently changed.

Dependencies: pure transform/schema/tests -> isolated copied catalog rehearsal ->
verify200world/48600layout membership, exact unaffectedcountparity, correctedcounts,
query/oracle/evidence/preview integrity and failures -> atomic SegmentedCatalog
publication into serving root using existing durability API -> new overlay/preview
readiness -> surface generation to UI. If current API advertises latest before
required overlays/previews ready, use explicit staging gate/manifest publication,
not a window with missing verification. Existing snapshot remains queryable and
personalSweep selectedseed/process untouched. Never overwrite oldevidence.

Tests: wrongseed/version/settings/sourcehash; malformedadjudication; unsupported
proof; missing/duplicatecoordinate; idempotence; count27villagesfrom28andoutpost
minus1 foraffectedworld; unchangedallothercoordinates/biomes; canonicalnamespace;
byteparityunaffectedsummarypayloadexceptidentity; newlayoutIDbinding; rebindsource
evidencewithrawoutcomestillpreserved; no unsupportedcountpromotion; interrupted
publicationdoesnotselectincompletesnapshot. FocusedcatalogandUIcontractchecks.

Risks to critique: whether fullchunkmembership is sufficient to remove start;
source-identity/provenance drift; derived-summary methods still honestly labeled;
atomic visible generation acrossdata/evidence/previews; preserving cache/cursors;
liveWALandoldqueries; need to avoid treating targetedcorrections as exactpipeline.
Estimate: moderate~45–90min after critique; CPUboundedrebind/index, noexpensivenative
benchmark or broad game campaign. Codex owns integration; oneHigh neutral critique
first, coding worker only if independent useful ownership is available.
