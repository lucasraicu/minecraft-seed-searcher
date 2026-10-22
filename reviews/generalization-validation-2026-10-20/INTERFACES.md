# Approved audit helper interfaces

User approved PLAN and explicitly requires justified strictness, testing retained
AND rejected candidates, BDS confirmation, useful Gemini parallelism and updates.
No automatic seed/structure deletion, stricter personal criteria, tolerance fitting,
new prediction algorithm, serving restart or catalog publication in helpers.
Helpers are PURE standard-library analysis. No native calls,BDS processes,network,
filesystem writes at import or recursive agents. CLI optional,not required.
Preserve every input case in output; lack of confirmation is not absence proof.

## Biome worker ownership

ONLY scripts/generalization_biome_probe.py and tests/test_generalization_biome_probe.py.
Implement compare_biomes(predictions, observations, *, aliases=None,
non_comparable=()) -> list[dict]. Predictions are list of dicts with exact fields
position=[x,y,z],biome_name=str,sample_group=str. Observations are list of dicts
with x,y,z and either id=str or error=str. Optional extra observed fields (block,
dimension etc) are preserved if useful but not interpreted as biome truth.
Coordinates strict integer (no bool); y may[-64,319]; X/Z signed32 bounded.
Duplicate XYZ in either list raises ValueError; orphan observed XYZ raises ValueError;
missing observation yields unknown,explicit observation error yields error. Invalid
input schema/types raises ValueError. Aliases is explicit string->string mapping;
strip only minecraft: namespace from names and alias keys/values. No inferred alias,
numeric-ID conversion,group collapse or cave masking. Unknown_* labels yield unknown.
Any label in explicit non_comparable collection yields not_comparable. Matching uses
provided aliases deterministically; reject cycles or ambiguous normalized aliases.
Output each row: position, sample_group, predicted_name (raw), observed_name(raw orNone),
canonical_predicted,canonical_observed,outcome(match/mismatch/unknown/error/not_comparable),
reason. Retain source order,never mutate inputs. summarize_biomes(rows)->dict with
by_group {group:{outcome:count}}, by_name {canonical_predicted:{outcome:count}},
total=count. No accuracy percentage or population conclusion. Tests cover malformed,
missing/error rows,duplicates,explicitaliases,namespace,noncomparableEndclasses,
negativecoords,caves and lack of cross-height matching. Do not require BDS or native.

## Structure worker ownership

ONLY scripts/generalization_structure_probe.py and tests/test_generalization_structure_probe.py.
Implement assess_locates(cases, results, *, prediction_revision,bds_build)->list[dict].
Cases: case_id=str,structure_type=str (backend raw name),dimension=str among
(overworld,nether,the_end),predicted=[x,z] OR None,origin=[x,z],disposition oneof
retained/rejected/discovery. Predictions must beNone ONLY fordiscovery. Results:
case_id=str,output=list[str]. Extra result fields from driver permitted. IDsunique;
orphan result/invalidschemas raiseValueError; missingresult ->unknown. Coordinate
strictint/nobool/signed32. Parse exact official BDS line regex:
The nearest minecraft:([a-z_]+) is at block (-?\d+), \(y\?\), (-?\d+)
Expect command IDs from seed_search.realm.predictor_diagnostics.COMMANDS.get(type,type).
Wrong command match,ambiguousmultiplelocate results,syntaxerror,Unknowncommand ->
verifier_unavailable orerror (never absence). No-valid-structure/Couldnotfind ->
no_location,notphysicalabsence. Exact rawposition ->reference_exact;
use existing project_navigation_reference whitelist ONLY for exactversion/dimension
and compare the corresponding predicted navigationposition ->navigation_exact.
Different ->different_reference; discoveryNone ->discovery_location ifreported.
Reject missing/unsupported identity gracefully asunknown (no offset guesses).
Never offset stronghold/trial/trail orsetdistance tolerance; noNether8xconversion.
Output each: case_id,structure_type,dimension,disposition,predicted,origin,reported,
outcome,grouped_command (templetypes),interpretation. No physical count orabsence
claim. Groupedtemple agreement doesnotcertify subtype. Rejectedcase exact/navmatch
must remain visible aspossibleover-rejection, not filtered. summarize_structures(rows)
returns total andby_disposition counters plusby_type counters,notrecall/accuracy.
Tests cover distinctraw/nav/versionguards/negativecoords,unknown/error/missing,
rejectedpositive visibility,ambiguousmatches,groupedtemple and discovery semantics.

## Worker execution limits

Both workers use High, isolated dirty-baseline snapshot,600s wall/240CPU/1536MiB.
Permitted terminal command ONLY python3 -m pytest -q
<owned test path>, with worker snapshot cwd. Dependencies existing only; no installs.
Checks must pass, meaningful assertions independent from implementation. No shell
wrappers,Gitmutation,BDS,seedsearch,notification or edits beyondownership. Use built-
in readers/editors forownedfiles. Finish concise summary and WORKER_COMPLETE marker.
Codex independently reviews patches and reruns checks before integration. An empty
SUCCESS ordenied required action is a failure. No worker is allowed to launch BDS.
