# Predictor correctness diagnostics

**Historical diagnostic record.** The later
[native correction report](../../reviews/predictor-resolution-2026-10-20/ENGINE_REPORT.md)
supersedes the earlier unresolved biome-selection findings below. The current
[generalization audit](../../reviews/generalization-validation-2026-10-20/PLAN.md)
is still running and has found village over-rejections and other structure
omissions on new seeds. Earlier successful controls do not establish all-seed
accuracy. The proposed exact-Y correction is awaiting approval; no such native
change has been applied by this audit.

The diagnostic tools preserve reproducible failures without changing personal
search admission or silently promoting predictions to verified counts.
They require no BDS launch, GPU or custom database. The public catalog continues
to expose the evidence already imported by the prior stage.

From the repository root, replay the portable saved evidence:

```sh
python3 scripts/predictor_diagnostics.py
```

This uses the standard library only. Exit zero means the fixture replay completed,
not that all predictions passed. The JSON retains exact differences and unknown
locations, splits candidate-directed probes from independent discovery, and shows
sampler agreement under the frozen comparison name policy.

To independently recompute the two Overworld sampling paths, build a diagnostic
executable at a **new path outside this repository**:

```sh
python3 scripts/build_biome_sampling_probe.py --output /tmp/seed-biome-probe
python3 scripts/predictor_diagnostics.py --probe /tmp/seed-biome-probe
```

The builder refuses an existing executable or output inside the project. It needs
a C compiler, records compiler/source/binary hashes in an adjacent `.build.json`,
and leaves serving libraries untouched. Vendor compilation currently emits two
existing C23 label/declaration warnings. The helper accepts at most 4096 input
rows, exact signed-64 seeds and bounded integer XYZ. Replay has a 30-second limit
and returns nonzero on a changed sampler result, failed process or malformed output.
The first implementation reproduced all 614 saved Overworld comparisons exactly.

## Coordinate projections

`seed_search.realm.structure_coordinates.project_navigation_reference` provides a
separate immutable predicted navigation reference for exactly these conventions:

| Structure | Dimension | Change from raw predictor reference |
|---|---|---|
| Outpost | Overworld | +8 X, +8 Z |
| Mineshaft | Overworld | −8 X, −8 Z |
| Fortress | Nether | −8 X, −8 Z |

Callers must supply `prediction_revision='cubiomes-bedrock-26.50'`,
`bds_build='1.26.52.3'` and the correct dimension. Missing/unsupported identities,
types or coordinates return `None`; no namespace or dimension guessing occurs.
Nether coordinates remain Nether blocks, with no 8× conversion. Candidate and
navigation coordinates are retained separately; projections cannot be used to
silently recount border/radius summaries or reinterpret old evidence.

The module is diagnostic-only and is not wired into public counts or UI fields.
A projected coordinate is not an observation that a structure exists. The combined
saved candidate probes agree after projection for mineshafts 12/12, fortresses
9/9, and outposts 11/12. The remaining outpost query is a remote disagreement,
preserved alongside the village disagreement. The stronghold locate disagreement
was subsequently shown to be a verifier limitation: saved blocks, BDS membership
and an independent player observation confirm that static stronghold exists. Fixed-position
discovery controls yield exact projected membership in 23/23 distinct references
across two seeds; this is sampled evidence, not universal accuracy or full recall.

## Biome verdict

| Saved Overworld group | Observations | Current block lookup matches | Raw-quart matches |
|---|---:|---:|---:|
| Three-seed cohort | 330 | 292 | 311 |
| Snowy pilot | 256 | 239 | 253 |
| Vertical/local controls | 28 | 21 | 25 |

These historical comparisons use their frozen alias policy, not an authoritative
Bedrock numeric-ID conversion. Six cohort disagreements involve the raw identifier
`minecraft:redwood_taiga_mutated`, then mapped to ordinary taiga, against
predicted old-growth spruce taiga. Source-backed resolution now maps mutated
redwood taiga and hills to `old_growth_spruce_taiga`; the original raw names and
historical fixture policy remain unchanged. This explains six name disagreements
across three seeds, not the cave-boundary failures.

Twelve other cohort raw-quart disagreements involve cave/noncave names and one
involves savanna/plains. The cause is unresolved. API representation, model/build
differences, cave selection and interpolation require discrimination; better API
agreement alone does not establish the physical world-generation algorithm.
No global switch of `ss_biome` or cave fallback is justified by this slice.

The next correctness work is an independent, specified biome representation oracle
and targeted diagnosis of the preserved village/outpost/stronghold failures. Any
later extractor correction needs a new identity and regenerated summaries/indexes;
historical observations and immutable evidence must retain their original meaning.


## Follow-up replay and verdict

```sh
python3 -S scripts/predictor_diagnostics.py --resolution-fixtures fixtures/bedrock-26.52/predictor-resolution
```

All original 54 storage target coordinates are readable in newly persisted worlds.
The repeat resolver is explicit and keeps the historical strict decoder unchanged.
The static stronghold at (820,-1708) on seed -9103892851552028103 exists; preserve
its enumeration even though `/locate` reports another stronghold.

On seed -3509659830737203357, complete start-chunk membership checks found no
village at (-296,-312) and no outpost at raw start (528,512). Positive control
chunks contain the expected structures. The user also reported no village at the
first location. These support reviewed per-start corrections, not a world census
or a general Ancient City exclusion rule.

Native cave interpolation and a general village/outpost rejection rule remain
unresolved. Quart offsets, continuous coordinates, Java-style Voronoi variants,
climate interpolation and lower-height viability filters all fail some controls.
Do not replace the production algorithm merely because a hypothesis improves an
aggregate score. Counts stay predictions or scoped BDS matches until the relevant
game evidence supports stronger claims.

The versioned refresh path and publication recovery contract are documented in
[Reviewed catalog corrections](REVIEWED_CORRECTIONS.md).


## Dense follow-up and direct checks

[The continuation report](../../reviews/predictor-resolution-2026-10-20/CONTINUATION_REPORT.md)
records a fixed four-chunk dataset with 8,320 stored points and 3,920 quart climate
nodes. Thirty saved-data labels are absent from the bounded 27-parent native set;
25 direct stable BDS reads corroborate nine counterexamples and their controls.
All eight initially selected witnesses were directly confirmed. This rules out
only that nearby-node selection class, not every possible grid or interpolation.

The separate [mechanism fixture](../../fixtures/bedrock-26.52/predictor-mechanism/README.md)
retains the old native outputs, game identities, exact coordinates and raw logs.
Rebuild the optional raw-node diagnostic outside the repository with
`python3 scripts/build_biome_sampling_probe.py --mode nodes --output /tmp/new-biome-nodes`.
Its input uses quart coordinates; BDS observer requests use exact block coordinates.
Default block-probe behavior is unchanged. No serving algorithm was changed by
this follow-up; model/game compatibility and cave/structure causes remain unresolved.
