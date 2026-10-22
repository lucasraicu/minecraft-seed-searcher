# Pinned BDS/predictor regressions

These are byte-for-byte copies of five completed local BDS audit reports, their
settings and console logs, plus saved isolated-sampler comparisons. They cover
four full signed-64 seeds. No worlds or database files are included.

`manifest.json` records file sizes and SHA-256 digests, predictor/game identities,
and the frozen name-normalization policy used in the original analysis. Checksums
detect accidental changes; they do not authenticate the original experiment.
The observed BDS console version is 1.26.52.3, Script API 2.10.0. The predictor
uses MC_26_50; these are different identities, not assumed equivalent releases.

The raw reports contain 232 candidate-directed structure queries, 176 independent
fixed-location discovery queries, and 644 biome API observations (including 30
Nether/End observations). The isolated sampler comparisons cover 614 Overworld
observations: 330 cohort, 256 snowy pilot, and 28 vertical/local controls.
Some repeat the same seed/XYZ across runs; these are observations, not 614 unique
world positions. Discovery queries are not an exhaustive recall census.

`discovery-predictor-points.json` records eight bounded predictor enumerations
for two already-tested seeds and the original native binary digest. It supports
exact membership comparison against discovery locate outputs, not physical counts.
`predictor-source/` preserves the relevant bridge/name-projection/backend identity
files. `biome-scale-build.json` preserves the earlier diagnostic helper build.

Important observer detail: `loaded: true` means the harness created a ticking
area after the initial biome query threw. `false` means the API returned without
that intervention. It does not mean the chunk was unloaded. See `observer.js`.

Known village, outpost, stronghold, cave and boundary disagreements are intentional
fixtures. Never edit them into matches, use a distance tolerance to hide them, or
infer a physical structure's completeness from a locate reference. Raw strings
are retained even where the current name projection appears questionable.

Replay instructions and limitations:
[Predictor diagnostics](../../../docs/catalog/PREDICTOR_DIAGNOSTICS.md).
