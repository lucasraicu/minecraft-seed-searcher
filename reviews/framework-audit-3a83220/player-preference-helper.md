# Player preference helper — commit `3a83220`

Scope: the active 2,048 × 2,048 Overworld / 1,024 × 1,024 Nether blueprint for 15–20 Bedrock players; latest scoring and centroid rebalance; relationship between predictor rankings and actual player experience. Production code was not edited.

## Verdict

The latest rebalance is coherent, and its diminishing-return schedules are better behaved. It is a reasonable **provisional preference model**, not an empirically established optimum for these players. No numerical defect was found in the changed score schedules. The largest player-facing weakness is that structure richness can compensate for an inconvenient or unsuitable shared hub, while the model does not measure usable land, actual routes, loot capacity, or complete structure containment. Changing weights again without preference data would give another defensible opinion rather than establish an optimum.

Confidence: **high** for code behavior and arithmetic; **medium** for likely player consequences; **low** for any claim that a particular fixed set of point values maximizes this community's enjoyment. The user has not supplied pairwise seed preferences, play-test outcomes, or an agreed tradeoff between building, exploration, and technical farms.

## What the latest push improves

- The stronghold surplus sequence is now `0, 30, 50`: its marginal rewards are `30, 20, 0`. The previous `0, 20, 50` gave the third stronghold a larger reward than the second. This is a definite correction **under the intended diminishing-return design**, not a proof that 30 and 20 are the correct player values. Sources: `native/blueprint_dynamic.inc:321`, `src/seed_search/realm/blueprint.py:602`.
- Mansion surplus falls from a cap of 85 to 70, and trial-chamber surplus rises from 30 to 45. This reduces the previous bias toward repeated mansions. A second mansion still scores 45, equal to five additional trial chambers beyond the eight-chamber floor. That remaining ratio needs explicit player approval/calibration. Sources: `src/seed_search/realm/blueprint.py:599`, `src/seed_search/realm/blueprint.py:611`.
- Lower per-instance village/trial pull makes those numerous categories less dominant. Stronghold weight rises from 1 to 3. The change is directionally consistent with improving End-access proximity, while the actual End portal room is explicitly unverified. Sources: `src/seed_search/realm/config.py:407`, `MASTER_SEED_BLUEPRINT.md:99`.
- Caps remain internally consistent: core 650, optional 200, luxury 265, spatial 135; total 1,250. All 14 core surplus schedules and five optional schedules pass monotonicity and non-increasing-marginal checks above their floors. Equal marginal rewards are allowed by this definition of diminishing returns.

Reproduction: `PYTHONPATH=src .venv/bin/python reviews/framework-audit-3a83220/probe_player_rankings.py`. Results are saved in `player-ranking-probes.json`. These are mathematical scoring probes, not generated-world validations or an estimate of typical seed distributions.

## Prioritized findings

### P1 — The baseline does not guarantee a suitable shared starter hub

**Demonstrable behavior; high confidence. Preference priority depends on the stated shared-hub goal.**

The hard floors require six villages but do not require one within 256 or 512 blocks of the chosen center. A center without a village within 512 earns zero village-hub points and remains eligible. Moving the nearest village from 900 blocks to 100 blocks improves the score by only 15 points, all other components held constant. One optional basement igloo earns 30; a second mansion earns 45. A player who considers a conveniently located settlement essential can therefore receive the opposite ranking to their stated preference.

The centroid is not a guarantee of a flat, safe, dry, connected building site. Scenic scoring checks fixed-Y biome witnesses plus a river within set radii. It does not establish slope, surface elevation, buildable area, navigability, or enough separate plots for 20 people. Dynamic candidates explicitly record terrain analysis as not applicable and full blueprint certification as false. Sources: `src/seed_search/realm/config.py:401`, `src/seed_search/realm/dynamic.py:178`, `src/seed_search/realm/dynamic.py:280`, `src/seed_search/realm/blueprint.py:899`, `src/seed_search/realm/blueprint.py:924`.

Recommendation: decide which hub properties are actual requirements. If a village within 256/512 is essential, make it a feasibility requirement for a future policy revision or finalist deployment gate. Measure buildability, actual surface height, traversability, and usable plots in finalist verification. Do not infer those properties from the biome label. Keep the fast predictor stage inexpensive; these checks belong on the small finalist set unless measurement proves an earlier cheap filter worthwhile.

### P1 — "Zero resource depletion" is an unsupported outcome

**Definite scope gap; high confidence.**

The blueprint targets "zero resource depletion" (`MASTER_SEED_BLUEPRINT.md:7`), but scores structure starts and sampled biome presence. Chest loot, complete portal rooms, and actual generation remain unverified (`MASTER_SEED_BLUEPRINT.md:122`, `MASTER_SEED_BLUEPRINT.md:456`). The model does not measure remaining individual loot opportunities, reserve quantities, or how those quantities compare with 15–20 players' goals. No End-resource inventory is defined by this blueprint.

Trial chambers are especially relevant to multiplayer capacity: official Bedrock 1.21 notes say vaults can serve multiple players but each player can unlock a particular vault once, while spawners have a cooldown. Eight predicted chambers is therefore not a certificate that every player can obtain every desired vault reward indefinitely. The correction is to state a finite-resource policy, not to promise unlimited capacity from a count floor. [Official Bedrock 1.21 release notes](https://feedback.minecraft.net/hc/en-us/articles/27451789924237-Minecraft-Bedrock-Edition-1-21-Tricky-Trials).

Recommendation: classify the community's required resources as renewable supply, shared progression access, or finite personal discoveries; define the intended season duration and replenishment/reset policy where necessary. For a finalist, inspect relevant loot opportunities and generated structures before calling a resource objective satisfied. This is a product specification issue, not a numerical scoring bug.

### P2 — Per-instance weights do not cap a category's total influence

**Demonstrable behavior; high confidence.**

The latest minimum-inventory centroid masses are:

| Category | Required count | Weight each | Total baseline pull |
|---|---:|---:|---:|
| Villages | 6 | 2 | 12 |
| Trial chambers | 8 | 1 | 8 |
| Stronghold | 1 | 3 | 3 |
| Ancient cities | 2 | 2 | 4 |
| Mansion, desert pyramid, jungle temple | 1 each | 2 | 6 combined |
| Monument, outpost | 1 each | 1 | 2 combined |
| **Total** | | | **35** |

Thus villages and trials retain 20/35 = **57.1%** of baseline pull, while the stronghold has 3/35 = **8.6%**. Before this push those respective shares were 34/47 = **72.3%** and 1/47 = **2.1%**. The change is meaningful but does not make the stronghold the dominant anchor. Surplus villages/trials continue adding centroid pull even after their scoring categories hit caps. Sources: `src/seed_search/realm/dynamic.py:118`, `src/seed_search/realm/config.py:401`, `native/blueprint_dynamic.inc:253`.

The current design is defensible if every captured location is meant to represent an independently valuable travel destination. It is less faithful if the goal is nearest-village convenience, nearest verified portal access, or balanced category influence. Repeated one-time destinations should not automatically carry the same travel demand as a frequently used settlement.

Recommendation: retain `village=2, trial=1, stronghold=3` as a documented starting hypothesis. Compare it with category-normalized pull, capped top-k destinations, and nearest-destination travel objectives on actual finalists. Select the rule that best predicts stated player preferences. Category normalization is an alternative objective and must not be described as an unconditional mathematical improvement.

### P2 — Landmark counts and biome presence are imperfect utility proxies

**Definite scoring behavior; medium confidence about its undesirability.**

All locations within a category receive the same surplus reward irrespective of actual accessibility, footprint, visual quality, or usefulness to this group's activities. A single qualifying badlands witness gives 35 luxury points; a substantially larger usable badlands region gives the same 35. Three extra villages give only 30 points. The first two optional basement igloos give 50 points, despite the baseline already containing six villages and a fortress. Igloo basements do provide a villager and zombie villager, per the [official igloo guide](https://www.minecraft.net/da-dk/article/igloo); how much extra value that has for this community is a preference question.

Presence is a good cheap diversity indicator. It should not be relabeled as material reserve, usable surface area, or an objective measurement of scenery. A rare structure's rarity alone is not a reason it should outrank frequent daily convenience. Sources: `src/seed_search/realm/blueprint.py:477`, `src/seed_search/realm/blueprint.py:649`, `src/seed_search/realm/blueprint.py:662`, `src/seed_search/realm/dynamic.py:412`.

Recommendation: for finalists add measured region size, minimum border clearance/complete containment for important structures, route/access quality, and a short player inspection score. Require actual quantities when the stated goal is resource capacity. Avoid spending full terrain-generation cost on every raw seed.

### P2 — "Optimal center" needs to be read as optimal among prescribed representatives

**Definite implementation limitation; high confidence; already qualified in the blueprint.**

The solver proposes one snapped centroid per structure/biome-lattice event rectangle. The rectangle invariants cover required counts and sampled palette membership. Optional structure counts are recalculated only at the representative; hub-radius bonuses, village quadrants, scenic proximity, and radial distances can vary within that same rectangle. It follows that increasing the stronghold coefficient does not solve the broader problem of finding the best shared hub or maximizing every scored amenity across all valid centers. Sources: `src/seed_search/realm/dynamic.py:101`, `src/seed_search/realm/dynamic.py:118`, `src/seed_search/realm/dynamic.py:135`, `src/seed_search/realm/blueprint.py:768`, `native/blueprint_dynamic.inc:1126`.

The disclaimer at `MASTER_SEED_BLUEPRINT.md:311` correctly limits the claim. The opening "sliding optimal cluster center" and "guarantees dense interior clustering" language at lines 4 and 27 should be read alongside that qualification. For important finalists, compare the chosen center with a broader local valid-grid search and report any additional score or player-convenience improvement. That can be done entirely on the CPU. Exhaustiveness and cost of any replacement should be assessed by the mathematical/performance roles.

## Concrete ranking examples

These are controlled deltas over an identical floor-qualified baseline, with all unspecified components equal. They do not claim that all such paired worlds exist or occur equally often.

| Change | New points | Interpretation |
|---|---:|---|
| Second stronghold | 30 | More than the third's 20: consistent diminishing returns. |
| Five extra villages | 50 | Beats a second mansion's 45: less mansion-dominated than the previous policy. |
| Five extra trial chambers | 45 | Ties one extra mansion; explicit tradeoff for players to assess. |
| Four extra trial chambers | 38 | The new cap is reached at 13 total chambers, not 12. |
| Two basement igloos | 50 | Beats a second mansion, five extra trial chambers, and improving nearest-village distance from 900 to 100 blocks. Potentially inappropriate for a settlement-first group. |
| One badlands witness | 35 | Beats three additional villages' 30; does not distinguish a tiny witness from a useful region. |
| Village within 256 + scenic pair + village spread + both Nether-core structures | 85 | Daily convenience is rewarded, but those proxy observations still do not certify a buildable or safe shared hub. |

The point is not that these comparisons are universally wrong. They expose the actual decisions hidden behind the phrase "good scoring." Weight approval should mean accepting comparisons like these.

## Calibration method that would establish a stronger answer

1. Agree on non-negotiable deployment requirements first: verified End access, usable hub, preferred nearest-village radius, important full structure containment, and actual finite-resource policy. A very rare structure should not compensate for violating an essential requirement.
2. Retain a diverse calibration pool, not only today's top 50. Include candidates strong in terrain, exploration, farms, diversity, travel convenience, and current score. Otherwise the existing model selects the examples used to approve itself.
3. Have the 15–20 intended players compare blinded seed/center pairs using the same maps, measurements, and short play-test evidence. Include explicit tradeoffs from the table above; collect building, exploration, and technical-player preferences separately.
4. Fit a simple monotone additive model with non-increasing marginal rewards and nonnegative convenience weights. Use observed pair choices to estimate relative weights. Do not optimize against raw rarity or the old score. Keep the current capped schedules as an interpretable baseline.
5. Hold out seeds and some preference comparisons. Compare pairwise agreement, top-choice stability, and individual-player disagreement with the current model. Vary plausible weights and show which finalists remain strong. If preferences conflict, offer a small Pareto shortlist or clear player profiles instead of asserting one universal winner.
6. Tune centroid alternatives separately from feature points. On finalist seeds, compare nearest-useful-destination travel, hub feasibility, stronghold access, and worst-served district alongside the current all-instance centroid. Re-run predictor and actual-generation verification after selecting a different center.

This approach can preserve the existing high-throughput CPU screening architecture: cheap broad discovery first, measured player utility and more expensive verification on the shortlist. A GPU is not required to establish whether these preferences and centers are better.
