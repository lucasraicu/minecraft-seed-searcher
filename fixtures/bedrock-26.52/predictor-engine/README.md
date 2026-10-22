# Bedrock engine correction evidence

This bundle preserves BDS 1.26.52.3 observations used to investigate the native
biome and structure corrections. `manifest.json` binds the raw reports, consoles,
settings, exports and supporting observations. Existing parent fixtures remain
unchanged.

The three disposable runs query the same 33 points on one known seed: fresh
generation, a copy of its clean save, and a copy of a retained earlier world.
All 99 API observations agree. Only the fresh disposable world uses the previously
validated sky marker protocol after observation; the marker is restored to air.
Sources stay unchanged and every owned game container stops cleanly.

`heldout-biome-cohort.json` references 330 earlier direct Overworld observations
across three seeds. Its diagnostic prediction fields are historical evidence;
tests must calculate current predictions and compare with observed names.
Structure controls similarly preserve independently located positive positions,
not an exhaustive physical census.

The native generator uses an 8-block sampling grid. Runtime queries above a
chunk's stored biome ceiling clamp to its last Y=15 plane. These are separate
operations: the storage ceiling must not be invented from a seed or imposed as a
global generator height limit. Historical whole-volume 0xff extrapolation is not
a runtime oracle. Missing records remain unknown.

Run `tests/test_bedrock_engine_corrections.py` for a fresh isolated C build,
application C-bridge checks, 8,320 stored-data boundary samples, 330 direct game
observations, 3,920 unchanged raw nodes, 1,800 coordinate/hash edge cases, range
indexing and structure regressions. Passing these scoped cases does not certify
all seeds, terrain, counts or future game versions.
