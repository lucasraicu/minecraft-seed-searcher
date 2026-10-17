# Mathematical analyst review: `3a83220` against `84a83ba`

## Verdict

The latest score changes are mathematically coherent: the surplus ladders are nondecreasing, have diminishing or equal marginal returns, and preserve all existing pruning caps. In particular, Stronghold `{0,30,50}` fixes the previous increasing marginal return `{0,20,50}`. C and Python implement the changed arithmetic consistently in the checks below. I found no new half-open membership or negative-coordinate snapping defect.

The algorithm is exact for its **specified constrained-centroid representative policy**. It does not find the best legal center for the player's actual scoring function, and the centroid does not minimize its own mean Euclidean-distance tie-breaker. Those are existing design limits; `MASTER_SEED_BLUEPRINT.md:311` already qualifies global optimality. The latest weights change the strength of these effects, rather than introducing them. “Fastest and most accurate possible without GPU” is therefore unsupported.

## Prioritized findings and recommendations

### M1 — Material design limitation: equivalence cells preserve eligibility counts, but not the entire score

**References:** `src/seed_search/realm/dynamic.py:101`, `:118`, `:125`, `:135`; `native/blueprint_dynamic.inc:1068`, `:1125`, `:1150`, `:1168`.

Optional structures are deliberately omitted from event coordinates. Hub, Nether-core, scenic-radius and village-quadrant bonuses also vary inside a cell whose mandatory counts and biome samples remain constant. The code scores only one snapped centroid per cell, so a higher scoring center in the same cell can be missed. This is not a faulty pruning bound or a discrepancy with the defined representative policy.

**Runnable witness:** `reviews/framework-audit-3a83220/math_probe.py`; complete inventory and results in `math-probe.json`. It constructs an integer-coordinate synthetic inventory satisfying every v3 hard floor. Mandatory Overworld points have X=32 except the Stronghold at X=992; eligible Nether starts are central. Two optional Swamp Huts sit at `(-992,0)` and `(1040,0)`. Hold the required biome palette valid at both centers, with no luxury, scenic or treasure bonus. This is an algebraic geometry witness, not a claim that a particular generated Minecraft seed has these coordinates.

The two huts are both captured precisely when `17 <= center_x <= 32`. The mandatory/lattice cell containing this interval is `[1,64]`; its centroid X is approximately 114.286 and its representative snaps/clamps to 64. No representative has X in `[17,32]`.

| Check | Best of 510 policy representatives | Valid chunk-aligned alternative |
|---|---:|---:|
| Center | `(64,0)` | `(32,0)` |
| Core surplus | 0 | 0 |
| Optional bonus | 25 | 40 |
| Hub bonus | 45 | 45 |
| Nether-core bonus | 20 | 20 |
| Total | **90** | **105** |
| Weighted radial distance | 115.605558 | **98.742857** |
| All 14 hard floors | Pass | Pass |

Thus the missed center is better on both total score and walkability. A cutoff between 91 and 105 would reject the seed under this policy even though a higher-scoring legal center exists. Such a rejection remains correct relative to the currently declared representative policy.

**Recommendation:** Decide explicitly whether the product promises the best representative or the best playable center. For the latter, keep the fast rejection funnel and optimize over a finite center grid only on surviving seeds. There are just **15,129** fully chunk-aligned centers (`123 x 123`, multiples of 16 in `[-976,976]`) and **60,025** integer-Nether-center candidates on the full multiples-of-8 grid. A CPU exhaustive oracle on selected seeds is practical to benchmark. Adding optional events alone does not solve circular proximity and quadrant score changes.

### M2 — Material objective mismatch: the centroid minimizes squared distances, while ranking uses ordinary distances

**References:** `src/seed_search/realm/dynamic.py:118`, `:128`, `:137`, `:262`; `native/blueprint_dynamic.inc:253`, `:266`; `MASTER_SEED_BLUEPRINT.md:36`, `:260`.

For a fixed captured set, the weighted centroid minimizes `sum_i w_i ||p_i-c||^2`. The implemented radial tie-breaker is `sum_i w_i ||p_i-c|| / sum_i w_i`, whose unconstrained minimizer is a weighted geometric median. Snapping and clamping the centroid exactly solves the former objective on the selected rectangular grid, not the latter. No theorem makes those objectives interchangeable. M1's witness also demonstrates a strict radial improvement at an unrepresented legal center.

**Recommendation:** If the desired result is lower average travel distance, compare constrained geometric-median candidates or evaluate radial distance on tied best-score grid centers. If the intended utility is protection against exceptionally long walks, measure a maximum or high quantile of essential-site distances explicitly. Changing weights alone does not fix an objective mismatch.

### M3 — Preference/calibration uncertainty: reduced village/chamber influence is real, but “good weights” is not mathematically established

**References:** `src/seed_search/realm/config.py:407`; `src/seed_search/realm/dynamic.py:32`, `:244`; `native/blueprint_dynamic.inc:249`, `:257`, `:269`.

The configured v3 center weights agree with the C array, Stronghold special case, and Python radial order. At exactly the hard floors, the total positive centroid weight is **35**: Villages contribute 12, Trial Chambers 8, Stronghold 3, and the remaining types 12. Villages plus chambers retain **57.1%** of total influence; Stronghold is **8.6%**. Before the latest push, those shares were 34/47=72.3% and 1/47=2.1%, respectively. This is a meaningful shift toward the End portal and away from dense structure classes.

The pull remains per individual structure, uncapped by type. Surplus villages/chambers keep increasing total centroid influence even once their score has saturated. In contrast, Ruined Portals and Shipwrecks can earn surplus and hub utility while exerting zero direct pull. This can be a valid preference, but it is not a calibrated travel model.

**Recommendation:** Keep the present numbers as a documented provisional preference. Compare old/new settings on the same nonempty survivor inventory, reporting score, nearest village/Stronghold/temple distance, worst essential-site distance and center movement. If needed, cap or normalize total influence per category, or use expected visit frequencies and nearest useful site. Do not present hand-selected ratios as an empirically optimal policy.

### M4 — Test-evidence limitation: the parity suite overstates false-negative coverage

**References:** `tests/test_v3_optimizations_parity.py:102`, `:117`, `:135`, `:159`.

The “5,000 seeds” test compares Python only for retained native candidates. If none survive, it samples eight rejects; if at least one survives, it does not independently check the other native rejects. The fixture parity test compares direct native serialization with replay at the already selected native center; replay does not independently search alternative centers. These are useful arithmetic/serialization checks, but they do not establish zero false negatives across 5,000 seeds or independent center optimality.

**Recommendation:** Correct the test claims. Add a bounded independent rejection comparison and require a known nonempty generated survivor corpus. Retain a separate exhaustive-grid oracle for the precise center optimization promise being made.

### M5 — CPU optimization opportunities remain; measure them where they matter

**References:** `native/blueprint_dynamic.inc:1099`, `:1108`, `:1126`, `:1190`, `:1217`.

Cell evaluation repeatedly scans all points for counts, weighted sums and radial distance. A 2D difference-table construction can add each structure's center-space capture rectangle to count and weighted-coordinate tables, yielding counts and centroid sums per cell without rescanning every structure. Score is the first v3 ordering key, so radial computation for a cell whose score is below the best already seen is unnecessary; keeping the best cell also avoids storing every qualifying cell. Checking whether each axis contains any multiple of 8 can precede expensive count work.

These are opportunities, not measured whole-run speedup claims: survivor geometry can be a small fraction of total scan time. Profile representative survivor-heavy runs before trading simple code for more tables. Preserve the current event and snapping policy if validating an optimization for exact semantic parity.

## Checks and proofs supporting the last push

1. **Fresh source arithmetic parity:** extracted and compiled the actual C core, optional and luxury score helpers from `native/blueprint_dynamic.inc`; compared against Python on **20,000** deterministic randomized cases. **Zero mismatches.** This bypasses potentially stale installed extensions for the arithmetic check.
2. **Exact snapping arithmetic:** **100,000** deterministic cases including negative coordinates and constrained 8/16 grids. C output agreed with the integer Python formula in every case. Integer accumulation and flooring avoid float rounding in center selection.
3. **Nether half-open membership:** **315,732** checks covered every multiples-of-8 v3 center coordinate against every macro Nether X, plus the rational entry/exit neighbors. **Zero mismatches.** Solving `C/8-h <= p < C/8+h` gives `8(p-h)+1 <= C <= 8(p+h)` for integer C; both `nether_bounds` and native predicates implement it correctly.
4. **Pruning-cap proof:** the new maximum is still `650 core + 200 optional + 265 luxury + 135 spatial = 1250`. Therefore the three remainder bounds remain exactly **600**, **335**, and **135**, as used at `native/blueprint_dynamic.inc:1037`, `:1121`, `:1143`, `:1154`. Each surplus ladder is nondecreasing, so macro counts upper-bound any window's core score. Non-Dark-Forest mansions in a macro bound can only loosen it. Strict `< cutoff` correctly retains equality. The mansion -15 / chamber +15 and hut -10 / igloo +10 changes conserve aggregate caps.
5. **Focused repository tests:** `.venv/bin/python -m pytest tests/test_dynamic_v3_2048.py tests/test_v3_optimizations_parity.py -k 'scoring_pure_additive or scoring_component_ladders or cutoff_score_pruning or candidate_match_100_percent' -q` → **5 passed, 17 deselected**. Full-suite results belong to the parent review.

## Limits of this role review

The synthetic witness proves a possible failure of global optimization under the implemented mathematical model; it does not estimate its frequency in real seed inventories. Arithmetic parity is not a proof of Minecraft generation accuracy, complete structure footprints, portal behavior or biome area. No fresh comparative throughput benchmark was run in this role. Production source was not edited.
