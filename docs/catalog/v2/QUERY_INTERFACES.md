# Additive v2 summaries and request validation — worker C

Approved implementation of PUBLIC_CATALOG_AUTOMATION_PLAN.md. Gemini High only.
Own summaries.py, request.py, tests/catalog/test_v2_summaries.py and
tests/catalog/test_v2_request.py. No other files. Existing v1 APIs/slots unchanged.
No native dependencies, builds, extraction/process launch, network or BDS.
Do not invoke RunCommand at all; bridge runs automatic supplied checks after your
response. Builtin edit/read only; embedded existing source is authoritative.

## request.py

Append validate_request_v2(payload, *, snapshot_id=None,game_build_id=None,
world_settings_id=None). Same exact11 top-level fields as REQUEST_SCHEMA.required.
request_revision='catalog-query-v2', evidence_policy='predicted_observations_v2';
edition='bedrock', dimension='overworld' denotes root anchor coordinate frame.
Research game_build_id restrictions unchanged. Anchor modes origin,recommended,
world_spawn_estimated,world_spawn_observed. OW border_sides unchanged. Fallback
profile existing PROFILES. At most12 rows, Required/Preferred, weights1/3/5,
structure at_least1..16. FEATURES_V2 is additive31 list. Feature's registry dimension
selects near_radii OW256/512/1024 or Nether64/128/256. inside_border means that
dimension's window (OW chosen border, Nether1024 fixed). Biome any_of1..9OW or
1..5Nether, unique and SAME dimension. Reject unknownkeys/bools/noncanonical
identities/mixedbiomegroups, duplicate IDs, wrongdimensionradii. Return deep copy.
Leave original validate_request untouched.

## summaries.py

V2 observation shape in INTERFACES.md; import validator lazily if worker A not
in your snapshot. Add legacy_observation_v2(obs): validates v2 and projects only
old14 OWstructures and nine-family Y63/stride64 full-envelope lattice into a
valid v1 observation. Filter starts/samples to ENVELOPE. Drop nonlattice/dense/
otherY samples, preserve rawnames, complete flags only if underlying coverage
contains ENVELOPE and full25600 known lattice exists. Other states unknown/partial.
Returned v1 observation has existing identity and v1 revision. Metrics/errors can
be copied only compatible JSON (no runtime jobs). Never modify original obs.

Add summarize_v2(obs): derive summaries for81 grid anchors ×3 OW border sides,
plus each estimated/observed spawn in obs.anchors ×3. Avoidduplicate modes/grid
coordinates but preserve source anchor type. Origin grid supports both origin and
recommended; other grid centers support recommended. Spawn rows support their
own mode only. Project Nether coordinate once using Python floor/8.

Each row EXACT fields:
```
revision='catalog-summary-v2', registry_revision=REGISTRY_REVISION_V2,
source_observation_id=digest(obs), world_id, seed,
anchor:[x,z], nether_anchor:[x//8,z//8],anchor_modes:[...],border_side,
layout_id=digest(['catalog-summary-v2',source_observation_id,anchor,anchor_modes,border_side]),
features:{all31 feature_id: {dimension,counts:[n0,n1,n2,nInside],
 complete:[bool,bool,bool,bool],nearest_d2:int|null,witness:[x,y,z]|null}},
legacy: existing v1 summarize_at projection for this sameanchor/border
```
For structures count distinct starts inside dimension square, then closedradii
intersectsquare; nearestwithinwindow same. OW14+stronghold versus Netherfortress/
bastion correctly separated. Structure complete iff featurecoverage complete and
contains FULL requested box; unknownstronghold can retain positive counts.
Biomes map raw names through v2registry canonical_members, OWY63/NetherY64 only;
count fields are0/1presence in each scope, nearestsavedwitness deterministic.
Biome complete flags FALSE: sparse witnesses do not prove exact absence.
For estimatedspawnoutside surveyedcoverage row must NOT claim completedcounts.
Bounds use half-open squares; radii closed; exactboundary tests incl negativefloor.
For performance group points perfeature once outside anchorloop, reuse existing
summarize_at/summarize for legacy; never re-extract or call native peranchor.

Tests: frozen standalone fixture builders with v2 schema; can monkeypatch a local
lazy validator only if missing in isolatedsnapshot, but actual behavior validation
will independently run after Codex integration with realworkerAvalidator. Oldtests
remain unchanged. No weakening assertion or fake source fields. Query rank/serving
integration owned by Codex later; do not implement those here.
