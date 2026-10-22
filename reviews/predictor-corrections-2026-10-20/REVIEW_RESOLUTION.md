# Independent review resolution

Both tool-free Gemini reviews completed using gemini-3.8-flash-high, explicit
High effort, exit 0, nonempty responses, denied_actions [], changed_files [].
Biome task 0f02df8f3bff used 21,181 tokens; coordinates f855cfef7997 used 20,323.
These are plan critiques, not independently executed code or game tests.

Accepted: distinguish navigation projections, candidate placement and game evidence;
preserve raw coordinates, counts, borders and snapshot identity; test negative
coordinates and dimension units; a higher API match rate alone does not establish
a replacement world-generation algorithm. Saved-world decoding, if available,
must specify exactly which stored representation it observes.

Rejected or left as hypotheses:
- Biome reviewer incorrectly calls sulfur_caves synthetic/nonvanilla. Mojang's
  own behavior-pack definition includes minecraft:sulfur_caves (format 1.26.30):
  https://raw.githubusercontent.com/Mojang/bedrock-samples/main/behavior_pack/biomes/sulfur_caves.biome.json
  No fixture purge or biome removal is justified.
- Cave masking, palette granularity and client smoothing are unproved explanations.
  Multi-Y changes alone do not prove masking. Surface blocks/foliage are not an
  independent exact biome oracle. No existing stopped-world biome decoder was found.
- Stronghold rings, ocean relocation and trial-chamber piece dimensions were
  asserted without source proof; the pinned source uses getStaticStronghold.
  Large disagreements remain unresolved, without an invented causal explanation.
- An arbitrary ten-seed requirement cannot prove universality. Use source-derived
  conventions plus independent controls, label the supported build and retain
  experimental status outside tested cases. No population-accuracy claim.
- Locate finding another position does not establish why the target was absent.

Codex's independent discovery reanalysis (DISCOVERY_CONTROLS.json) found exact
inverse-adapter membership in 8/8 mineshaft, 8/8 fortress and 7/7 outpost distinct
locations across two seeds, plus 5/5 stronghold references. These fixed-position
queries were independent of candidate-directed probes, but are not an exhaustive
recall census or fresh-seed holdout. Stronghold's original remote failure remains.

Alias issue: all six raw-quart spruce/taiga discrepancies return the raw identifier
minecraft:redwood_taiga_mutated. The current project aliases it to ordinary taiga.
Mojang's definition marks it mega/mutated/taiga and supplies podzol/coarse dirt:
https://raw.githubusercontent.com/Mojang/bedrock-samples/main/behavior_pack/biomes/redwood_taiga_mutated.biome.json
This establishes that the current mapping needs review, not by itself the exact
modern canonical name. Pin a source revision and establish an explicit mapping
before changing aliases; retain raw names in fixtures regardless.

Revised implementation boundary: portable regression fixtures and diagnostics;
three deterministic navigation projections only, with raw coordinates retained.
Stronghold is diagnostic-only, not a production adapter. No native sampler switch,
catalog recount, historical evidence rewrite, or verified badge from projection.
No public UI claim changes in this slice; product integration follows the sampler
verdict and requires explicit coordinate/version contracts.
