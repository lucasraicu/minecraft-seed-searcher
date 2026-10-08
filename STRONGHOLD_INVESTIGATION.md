# Stronghold disagreement investigation — 2026-10-07

The production iterator is unchanged. The large sweep remains unstarted.

## What was established

The two frozen seed `-1` disagreements come from the village-associated path,
not the static-region scan, its halo, or an output-capacity limit. Current village
starts are `(4084,-828)`, `(-956,5684)`, `(5492,2852)`; the matching-version
Chunkbase fixture has `(4084,-828)`, `(6212,-4700)`, `(3524,-7276)` instead.
This remains a disagreement between predictions, not proof from a generated game.

The reproducible read-only diagnostic is
`runs/stronghold-investigation/diagnose.py`. It uses the installed native MT RNG,
village region positions and village viability checks. No Generator layout is
guessed and no native library is changed. Its 48 variants vary X/Z rounding and
village eligibility separately across four calibration seeds. Earlier 16
precision/rounding variants are retained in `numeric-variants.json`.

Changing both axes from floor to truncation recovers the two missing seed `-1`
markers but breaks seed `12345`: it changes `(276,2836)` to `(2804,-236)`.
A fresh actual Chunkbase UI search again shows `(276,2836)` and does not show the
alternative as its nearest result from `(2804,-236)`. Evidence is saved in
`chunkbase-12345-fresh.txt` and `chunkbase-12345-second-fresh.txt`.

Truncating only X preserves the four calibration seeds and recovers both `-1`
markers. However, the independent seed `9` check rejects that proposed correction:
the current iterator predicts `(-908,644)`, while the variant predicts
`(2404,20)` as its first village stronghold. Fresh Bedrock 26.50–26.52 Chunkbase
search from `(0,0)` shows `(-908,644)` as its nearest Stronghold (Stairway).
Evidence: `chunkbase-seed-9-first.txt`. That nearest-marker check falsifies the
variant; it does not claim complete recall from the website's bounded list.

Removing snow biomes also recovers `-1` but breaks other calibration seeds. These
experiments are candidate hypotheses, not accepted corrections. The historical
[Bedrockified reconstruction](https://github.com/Earthcomputer/bedrockified/blob/master/src/main/java/net/earthcomputer/bedrockified/BedrockStrongholdStructure.java)
also floors both axes; it is not a verified modern-version replacement.

## Safe operational handling, verified

Production `required_status` treats missing Strongholds as unresolved when the
other required predictions pass. It retains them for review instead of treating
absence from this enumerator as proof of absence. The Stronghold remains required:
only a recorded matching-version website marker inside the exact 3008-block square
establishes website-level required eligibility. An out-of-border marker cannot do
that; a missing review field is rejected. This does not certify game footprints.

The existing tests for required Fortress/Stronghold with optional Bastion, missing
Stronghold preservation, external recovery with empty native predictions, and exact
review borders were rerun: two tests pass. The readiness manifest was checked again
against all current source, config, backend and evidence hashes.

## Root correction criteria

Do not install either rounding variant or coordinate-specific exceptions. A root
correction needs to explain the village-acceptance divergence for `-1`, preserve
the frozen comparisons, and pass independent cases such as `9` and `12345`.
Matching-version generated-world evidence would resolve which predictor is wrong
when they disagree. A backend change then requires rebuilding, regression replay,
a new bounded pilot/resume proof and new readiness identity before a sweep.
The tested review path is the current mitigation; complete enumerator accuracy
has not been established.
