# Center weights: decisions, experiments and change log

**Current decision: retain the production weights `village=2`, `trial_chamber=1`, `stronghold=3`.** They are a reasonable provisional policy, not a demonstrated optimum. The new exhaustive finalist search is a better-supported improvement than another guessed weight change.

Updated October 16, 2026. All work is local; nothing was pushed. This is the ongoing record for weight proposals, the evidence behind them and promotion into the blueprint.

## Production policy

| Structure | Weight per captured start | Minimum count | Minimum total pull |
|---|---:|---:|---:|
| Village | 2 | 6 | 12 |
| Trial chamber | 1 | 8 | 8 |
| Stronghold | 3 | 1 | 3 |
| Ancient city | 2 | 2 | 4 |
| Mansion | 2 | 1 | 2 |
| Desert pyramid | 2 | 1 | 2 |
| Jungle temple | 2 | 1 | 2 |
| Ocean monument | 1 | 1 | 1 |
| Outpost | 1 | 1 | 1 |
| Ruined portal, shipwreck, mineshaft | 0 | Policy floors remain enforced | 0 |

Total minimum pull is **35**. Villages and chambers provide **57.1%**; the stronghold provides **8.6%**. These are per-instance weights, so extra structures keep adding pull even when their score bonus is saturated. Nether structures constrain feasibility and earn points but do not directly enter this Overworld centroid.

Definitions live in `src/seed_search/realm/config.py`, `src/seed_search/realm/dynamic.py` and `native/blueprint_dynamic.inc`. Any future production change must update centroid and radial calculations consistently, preserve historical profiles, rebuild native artifacts and verify the resulting centers—not merely replace a dictionary.

## Change and decision log

| Date / ID | Change or proposal | Evidence / decision |
|---|---|---|
| October 16 / `3a83220` | Village 3→2; chamber 2→1; stronghold 1→3 | Existing approved rebalance. Village/chamber baseline share falls from 72.3% to 57.1%; stronghold share rises from 2.1% to 8.6%. |
| October 16 / W-001 | Keep those production values during framework repairs | No arithmetic or parity defect in them was established. Avoid combining correctness repairs with an uncalibrated preference change. |
| October 16 / W-002 | Add exhaustive 16/8-grid finalist evaluation | Fixes a demonstrated center-coverage limitation. Synthetic example improves 90→105 points; the tested natural case keeps its 311-point center. |
| October 16 / W-003 | Investigate 27 village/chamber/stronghold settings | Completed: three synthetic cases and one natural predictor case, with previous/current controls. No tested setting improves the primary score within any case. Different settings trade travel convenience. |
| Proposed / W-004 | Category-capped or category-normalized pull | Not implemented. Test whether repeated chambers/villages should continue increasing a category's influence after its score saturates. |
| Proposed / W-005 | Nearest-useful-destination travel objective | Not implemented. Compare nearest settlement, predicted/verified End access, important farm destinations and worst essential trip. Requires agreement about intended play. |

## New sensitivity study

Reproduce with a fresh output path:

```sh
.venv/bin/python scripts/investigate_center_weights.py \
  --output reviews/center-weights-2026-10-16/new-results.json
```

The study tests all combinations of village weight **1, 2, 3**, chamber weight **0, 1, 2**, and stronghold weight **1, 2, 3**. All other weights, hard floors and v3 score points stay fixed. The previous and current configurations are also repeated as controls. There are **27 distinct settings per case**, not 29 independent observations; the controls duplicate two of those settings.

It uses the production event-cell/centroid solver, fixed score functions and ordinary-distance radial tie break under each experimental weight set. A common current-weight radial metric and unweighted nearest-destination distances are reported so changing the measuring weights cannot masquerade as an improvement. Synthetic palettes are assumed valid with no luxury/scenic/treasure bonus. The natural case uses actual pinned-predictor macro inventories and the same biome/scoring machinery, with an explicitly **empty Overworld required palette**; all five Nether biomes remain required.

Raw evidence: [results](reviews/center-weights-2026-10-16/results.json), [execution log](reviews/center-weights-2026-10-16/investigation.log), and [verification and source hashes](reviews/center-weights-2026-10-16/verification.json).

| Case | Primary score across all 27 weight settings | Distinct chosen centers | Exhaustive 16-grid, current radial weights |
|---|---:|---:|---|
| Optional-capture synthetic witness | 90 | 2 | **105 at `(32,0)`** |
| Saturated trial-chamber sprawl, synthetic | 105 | 3 | 105 at `(0,0)` |
| Distant stronghold, synthetic | 65 | 2 | 65 at `(-64,0)` |
| Natural seed `-3336796033057908633`, custom palette | 311 | 2 | 311 at `(-480,0)` |

This is **one natural world and three deliberately constructed mathematical cases**. It is not a representative seed sample, a probability estimate, a player survey or BDS verification. The natural world is not certified against the complete default blueprint. Its exhaustive 16-grid search has only **four eligible centers**, illustrating how hard constraints can dominate weight changes.

### What the results establish

**Weight tuning does not repair missing center coverage.** In the optional-capture witness, current weights choose `(64,0)` and previous weights choose `(48,0)`, both scoring 90. Every one of the 27 settings misses the 105-point center `(32,0)`. Exhaustive refinement finds it. This is stronger evidence for expanding finalist center evaluation than for choosing a different set of pull coefficients.

**A setting can improve one kind of travel while worsening another.** In the saturated-chamber case:

| Setting | Center | Score | Nearest village | Nearest stronghold | Nearest chamber |
|---|---|---:|---:|---:|---:|
| Current `(2,1,3)` | `(0,0)` | 105 | 500.1 m | 800.0 m | 800.0 m |
| Experimental `(2,0,3)` | `(-208,0)` | 105 | **292.1 m** | **592.0 m** | 1,008.0 m |

Zeroing chamber pull improves settlement/stronghold access by approximately 208 m here, but moves chambers approximately 208 m farther away. Its current-weight mean radial distance worsens from 556.1 to 645.0 m. Neither result is universally preferable. This case alone does not justify deploying chamber weight zero.

**The stronger End anchor is still a modest aggregate influence.** In the outlier case, current weights leave the predicted stronghold 1,014 m away. Experimental `(1,1,3)` moves the center 16 m toward it, retaining the score while moving the village about 16 m farther away. That is a tradeoff, not proof of a better policy.

**The natural case provides little evidence for retuning.** Previous and current settings both choose `(-480,0)` at 311 points. Across the grid, centers are either `(-480,0)` or the fallback-8 position `(-480,8)`, always at 311 points. A small nearest-village improvement accompanies a slightly longer stronghold trip in the latter. It also changes chunk alignment. The evidence does not identify a meaningfully superior weight setting.

Distances are straight-line distances to predicted starts; they do not measure terrain routes, entrances, actual portals or travel time.

## What would be best

**For the current framework:** keep `(2,1,3)` for fast centroid proposals, then use exhaustive finalist refinement with the existing score. On a fixed legal grid, the maximum primary score is independent of centroid weights because every center is evaluated; the travel weights still determine tie breaks. Step 16 enforces full chunk alignment. Step 8 has a wider alignment scope and must be labeled separately.

**For a settlement-first realm:** first decide whether a nearby village and a usable shared building site are requirements. If they are essential, give them explicit finalist acceptance criteria. A basement igloo or another mansion should not compensate for violating an essential hub requirement. Do not infer buildability from the centroid or a biome witness.

**For future travel ranking:** compare current all-instance pull with a capped/category-normalized objective and nearest-useful-destination distances. A frequently used village may matter more than the tenth captured dungeon, while a once-used stronghold may matter less than its rarity suggests. Those visit frequencies are player preferences and must be supplied or measured.

The centroid minimizes weighted **squared** distances, while the existing radial metric uses ordinary distances. No choice of coefficients makes those objectives equivalent in general. The full-grid finalist evaluator avoids relying on that equivalence.

## Criteria before promoting another production weight change

1. Collect a diverse, nonempty corpus of independently evaluated finalists; record palette policy and complete macro evidence. Keep candidates that expose tradeoffs rather than selecting only the current top scores.
2. Agree on hub requirements and preferred trip types. Collect blinded player choices between the same seed/center maps, including settlement-versus-dungeon and End-access tradeoffs.
3. Compare candidate weights with fixed score points and identical alignment rules. Report nearest village/stronghold/farm trips, mean travel, worst essential trip, hub feasibility, center movement and score. Do not compare two differently weighted means as though they were the same yardstick.
4. Hold out seeds and preference comparisons. Check ranking stability across plausible weight choices and disagreement between player groups. A useful Pareto shortlist is preferable to claiming a universal optimum when preferences conflict.
5. Version the accepted scoring/selection change, record C/Python parity, rebuild the source-matching native binary, and reevaluate old seeds when their best center might change. Rescoring one old saved window cannot recover discarded alternatives.

For each new experiment append: date, source revision/hashes, objective, exact weights, corpus and palette policy, alignment rule, resulting centers/scores/distances, player evidence, limitations and the keep/reject decision. No production weight change was made by this investigation.
