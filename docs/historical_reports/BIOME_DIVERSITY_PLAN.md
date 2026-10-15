# Weighted biome diversity — implemented policy

User request: score biome diversity across the search and award more credit to useful biomes. Implemented in `biomes.py` and all four category scores; comparative verification is complete. Results: [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md).

## Scope and sampling

Apply the same diversity policy to structures-only, enclosed inner island, ocean island and mountain basin candidates. Stronghold/Fortress and the terrain branch's requirements still control eligibility. Biome variety cannot rescue a failed required check.

Default scheduling: sample every **structure-qualified full64 seed**, including seeds that fail all terrain branches and may qualify for structures-only. This interprets 'all seeds' across all four categories. Keep a separate configurable diagnostic option for sampling every evaluated full64 seed, including structure failures; diagnostic inventories never establish candidate eligibility. Raw low32 layouts have no unique biome world until high32 is selected; do not sample or score them as though they did.

- Coarse inventories are fixed-Y/model hints for candidate-center prioritization, with explicit spacing, Y, coverage and evidence status.
- Terrain survivors reuse their existing height-following surface-biome arrays. Counting these arrays adds no native sampling calls.
- The two selected structures-only centers receive a coarse inventory and height-following surface-biome sampling at spacing 16. Surface sampling here is a measurement, not an island/basin qualification requirement.
- Only count samples inside the selected 2304-square Overworld / 928-square Nether borders. Whole discovery-envelope variety is not a playable-world score.
- Surface Overworld, underground and Nether inventories remain separate. Underground sampling needs explicit Y layers and a finite budget; it is not a default multiplier of every surface grid.
- Unseen biomes in a coarse sample are unobserved, not proven absent. Preserve the coarse inventory alongside refined evidence instead of calling the two inventories equivalent.

## Suggested editable usefulness weights

Weights are a survival/building preference, not an objective Minecraft ranking. Start with 3 for broadly useful resource families, 2 for specialized building/resource variety, and 1 for other distinct environments. Freeze the complete biome-ID-to-family map and weights in the new configuration identity before benchmarking.

| Example family | Suggested weight | Reason for preference |
|---|---:|---|
| Jungle / bamboo jungle | 3 | Distinct wood, bamboo and food/crop variety |
| Forest and taiga resource families | 3 | Reliable wood variety; taiga variants share one family credit |
| Mangrove swamp | 3 | Distinct wood and wetland building materials |
| Badlands | 3 | Terracotta and red-sand variety |
| Desert | 2 | Sand/resource variety |
| Warm ocean | 2 | Coral/decorative variety |
| Other distinct wood families, such as savanna or cherry | 2 | Additional building palette |
| Other surface environment families | 1 | Variety without inventing resource guarantees |

Primary resource descriptions: [Jungle](https://www.minecraft.net/nb-no/article/around-block--jungle), [Badlands](https://www.minecraft.net/en-us/article/around-block--badlands), [Mangrove Swamp](https://www.minecraft.net/ja-jp/article/around-block--mangrove-swamp), [Warm Ocean](https://www.minecraft.net/zh-hant/article/around-block--warm-ocean), [Snowy Taiga](https://www.minecraft.net/en-us/article/snowy-taiga). These inform the preference; a sampled biome label is not a verified count of generated trees, coral or harvestable blocks. Do not award extra structure points from biome names.

## Scoring contract

Report raw distinct biome IDs, canonical family count, estimated sampled coverage/patch locations, evidence quality and weighted utility separately. Several taiga variants do not each receive full spruce-resource credit. Keep distinct resource/wood families separate when their utility differs, using a reviewed mapping rather than substring guesses.

For each canonical family g, use a versioned configurable weight w_g and a sampled extent factor q_g in [0,1]. Suggested initial extent rule: q_g = min(1, estimated_in_border_area_g / 4096, unique_supporting_sample_cells_g / 4). These are coarse estimates, not certified patch areas; refine sparse/rare detections in finalists. A single coarse pixel must not receive full credit merely because step² exceeds the extent target. Unknown/incomplete measurements retain an interval and cannot become a known zero or known full score.

Weighted utility = sum(w_g × q_g) / sum(w_g for the configured scoring families). Adding another useful family increases the score; increasing one family's area stops helping after saturation. Record nearest sampled patch distance as a separate metric initially; do not claim walking accessibility from straight-line distance.

Suggested bonus budget: **up to five extra points**, explicitly separate from the existing base score. Terrain categories retain their base out of 100 and expose a combined maximum of 105. Structures-only retains its structure base out of 30 and exposes a combined maximum of 35. Optional Bastion remains capped at two base points; no existing structure/terrain weight is silently rescaled. Combined score intervals include biome uncertainty. Compare results only within the same category and sampling/evidence grade, and preserve the original base score for A/B review.

## Implementation and verification

Files: `config.py`, a dedicated biome-family/scoring helper, `landscapes.py`, `scoring.py`, candidate/report schemas, `reports.py`, checkpoint/readiness identity and tests. Add counters for biome-query points, inventory count time, surface-height work and refinement budgets. Count-only ranking on existing terrain arrays must use zero additional native calls.

Verify: border clipping, variants sharing a family, distinct resource-family credit, duplicate samples, monotonic/saturating rewards, tiny/sliver detections, missing evidence, coarse/refined grade separation, unchanged mandatory eligibility, deterministic worker/resume results and identical base scores. Measure the extra per-seed work before enabling universal diagnostic sampling. Do not infer the detailed surface-inventory cost from the old 0.34-second whole-envelope coarse stage.

Original additional engineering estimate: **2–4 hours**, including focused tests, reporting and timing. The policy is implemented; measured verification and final handoff are recorded in [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md). No production sweep has started.
