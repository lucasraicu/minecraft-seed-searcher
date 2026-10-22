# Generalization audit — findings

The bounded audit is finished. The current predictor is not fully verified.
Several real engine references were incorrectly removed by viability checks;
the biome sampler also has reproducible disagreements outside the successful
sampled witnesses. No predictor, seed-admission policy or catalog generation was
changed. The user explicitly requested finishing the audit before changes.

## Scope and recorded results

Reference: BDS1.26.52.3, default ScriptAPI2.10.0, pinned image
`sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8`.
Predictor source `f51d3b3b48375ddd2c1f6a3c1b3b94ac0b2e0c246865962d19d5b8df134c3fef`;
verified isolated native binary `aac26a213aa9a56de51f7d4de21977fa4a171c43947127dc7f8a7ebc163f0209`.
Manifest `bbc14d21fba0455ed8f7cfe66099f34b6734575dfb7d8ffbcb00337eced72f1c`
was frozen before game output:16 deterministic blind seeds and eight deliberately
biased targeted seeds. No failed seed was rerolled.

| Required Overworld/Nether cohort | Point attempts | Matching labels | Mismatches | Loading errors |
|---|---:|---:|---:|---:|
|16 blind worlds|2082|2065|0|17|
|8 targeted worlds|1257|1236|4|17|
|Total|3339|3301|4|34|

All56 active Overworld classes and all five Nether classes have matching BDS
witnesses in both cohorts. Every active member of the nine selectable public
biome families also has a matching witness at registryY63. This is point coverage,
not an all-seed, every-patch, surface-area or absence guarantee. Loading errors
are unknown observations, never failed seeds.

All21 supported Overworld/Nether structure types were attempted in1670 queries.
The frozen secondary End probes add72 biome points and72 structure queries;
therefore full artifacts contain3411 point attempts and1742 queries. End results
do not inflate the required-dimension coverage claims.

See [the complete type/claim matrix](COVERAGE_AND_CLAIMS.md). Generic temple
commands do not establish desert/jungle/hut/igloo subtype. Trial-chamber,
trail-ruins and stronghold reference conventions remain unresolved; a different
located reference is not absence. Abandoned-camp queries returned no location
and do not validate that feature or prove all candidates absent.

## Viability checks really do discard valid references

Fourteen rejected village references across eight seeds match BDS exactly:
one blind-cohort reference and13 targeted references. The targeted group was
selected for recent removals; do not turn its counts into a population rate.

Disassembly of the pinned engine retains exact blockY for preliminary biome
checks, while our helper rounds Y down to a four-block plane. The unchanged
isolated exact-Y prototype restores all14 counterexamples, including11 obtained
after the initial three cases, retains51 earlier positives and two earlier
negative controls. It also preserves98000 old/new integer-quart outputs across
four model versions, five seeds and five sampling-flag combinations. These are
prototype results, not an integrated production fix. Full 3D checks remain;
there is no seed exception, cave mask, fitted tolerance or slope veto.

Independent fixed-origin discovery also found two bastions and one ancient city
that exist as raw candidate positions but are missing from the viable inventory.
They have different causes from the village Y rounding; the exact-Y prototype
does not explain the ancient-city failure.

## Copied-world evidence and its limits

Five stopped source worlds supplied137 targeted point checks under BetaAPI2.11.
Every source remained unchanged. All six selected counterexample neighborhoods
(three villages, two bastions, one ancient city) contain the expected engine
structure-type membership. The88 positive member points are not88 instances.
Beta settings on copies are a separate scope, not default-generation equivalence
or a physical structure census.

At seed219044158440418215, bastion reference(1640,1672) has no membership at the
three sampled heights, but nearby(1616,1640) has bastion membership. Empty points
at a navigation reference would therefore incorrectly reject that structure.
Both bastion cases have a nether-wastes raw center and a basalt-delta variant
center; bastion membership extends into the latter. This contradicts treating
the present variant-center biome rejection as established Bedrock correctness.
It does not justify globally allowing every basalt-delta candidate. Fortress
sharing must be tested with any later Bastion change.

The ancient city has membership at points whose biome is old-growth spruce
taiga, with Deep Dark lower down. Requiring Deep Dark at one unproven fixedY
is not sufficient evidence to discard it. Actual Bedrock placement/biome-check
semantics still need source-backed derivation before a general native fix.

Two membership attempts failed before completion: a five-second loading bound
and a duplicated observation/shutdown reserve. Both failed reports, clean
shutdowns and source hashes remain. Explicit bounded loading and timing repairs
completed the original137 points; neither failed attempt became absence evidence.

## Biome discrepancies and diagnosis

All four original mismatches occur on targeted seed7370389603366252746:
Overworld(248,319,-312), and Nether(512,Y,512) atY16,64,112. A separately frozen
46-point default-API copied-world recheck reproduces them and finds26 mismatching
points in the selected neighborhood/height set. That selected set is diagnostic,
not an independent accuracy cohort.

Overworld: the saved chunk's last explicit biome section ends atY95. The existing
storage-v3 ceiling interpretation matches all21 exact API reads, including the
snowy-beach column aboveY95. The raw procedural block sampler instead keeps
sampling with the requested Y and sometimes selects snowy taiga. This explains
the representation difference for this saved chunk. It does not establish a
universal95-block cutoff or justify applying a cache clamp to raw structure checks.

Nether: the disagreement is near a biome boundary; neighboring points differ.
Neither naive seed truncation nor copying the Overworld8-grid selector resolves
it. The native winner margin at rawquart128,128 is about0.0324, not a one-ULP tie.
The exact Bedrock Nether selection/source discrepancy remains unresolved.
Read-only storage export lacks the exact target chunk's Data3D record; that is
missing persisted evidence, not evidence that the successful API reads were absent.

## A supplementary analysis error was corrected

The storage helper prepends primarysrc to Python's import path. Supplementary
prediction preparation then imported the intentionally stale personal binary
without calling native_runtime(). Those original supplementary prediction values
and mistaken comparisons remain archived and explicitly marked obsolete.

The original24-world freezer imported the isolated backend FIRST and explicitly
validated its source identity. Independent replay of all3411 frozen predictions
under the correct isolated binary produces zero differences. It is unaffected.
Corrected supplementary comparisons are labeled post-observation reanalysis:
all137 Beta-copy biome points match; the46 default-copy points have20 matches
and26 mismatches. Game observations and selected coordinates were never replaced.
Explicit runtime preflight rejects stale binaries; direct Backend construction
currently does not invoke it. This is a real reliability issue for the next plan.

## Resources, regressions and next decision

Total charged game wall time:5163.770seconds, including failed/resumed attempts
and copied-world preparation/cleanup. Maximum per-seed charged time459.454seconds;
limits remain7200total/600perseed. One BDS at a time,2CPU/2GiB, no published ports,
zero full-volume scans. The campaign completes well below8GiB output and declared
read ceilings. There is no numerical recall or exhaustive/generated total.

The portable1.20MB archive retains163 checksummed raw files, frozen manifest,
failed attempts, source-corrected/obsolete comparisons and report/settings/observer
bindings. The separate ceiling witness preserves its exact record and local
numeric-ID association. [Regression tests](../../tests/test_generalization_evidence.py)
replay the real point/reference evidence and prevent rejected positives or loading
errors from being relabeled away. Current audit checks:87passed.

The primary personal server and loaded binaries, existing catalog generation and
unrelated dirty work are preserved. No GPU/custom-database work, new sweep,
commit, push, merge or account change occurred. Browser QA remains user-deferred.

The recommended [next fix plan](NEXT_FIX_PLAN.md) preserves candidate information
and applies only justified corrections. This audit does not authorize publication
or a broader rejection policy, and does not certify the current predictor.

Final independent Gemini High critique completed successfully (task
`c24d96ebc15c`, exit0, no denied actions or edits). Codex's
[reconciliation](FINAL_RECONCILIATION.md) distinguishes confirmed facts from the
reviewer's unproven cause statements. The [completed prototype witness](../../fixtures/bedrock-26.52/generalization/exact-y-completed-audit-prototype-v1.json)
adds all14 cases without rewriting the historical three-case prototype milestone.

Final preservation check: all497 baseline source/binary files unchanged; original
personal process60144 still has its Oct16 start time; no Docker container remains
running. Read-only catalog check still finds snapshot
`b48a7932a54a4e69b1ba28dc56f9ec5f973f9706399a2c483f7ecb6e9e8e66ae`,
200 worlds and48,600 layouts. Owned campaign output is69,128,322bytes at that
checkpoint. Audit completion is distinct from resolving every predictor defect.
