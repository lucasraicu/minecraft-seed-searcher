# Lower32 at the selected Stronghold border — 11 October 2026

Yes: given an explicit Stronghold center, lower32 supplies the same raw MT
placements inside that center's deployment borders as full64. This is a useful
per-layout necessary condition. It does not establish biome viability, select
the correct full64 Stronghold or imply that every sibling of that lower32 fails.
Adding a separate raw gate to the current already cheap viability checks was
slower in the matched stage replay.

The [12-item investigation/improvement list](FRAMEWORK_IMPROVEMENT_BACKLOG.md)
was generated and remains available. This report implements its requested
selected-center investigation as a shadow pilot, without changing production
structure requirements, center selection or compiler flags.

## Exact center and borders

Current `baseline.evaluate_seed` enumerates the full64-discovered Strongholds and
evaluates each independently. It sets the Overworld border to `square(anchor,
1536)` and the Nether border to `nether_square(anchor,896)` with an exact
fractional anchor/8 center. It has no single preselected Stronghold before those
checks. Final selection therefore happens among individually evaluated layouts.

To test one locked Stronghold per seed without selecting only successful cases,
the diagnostic fixes the **first discovered center in the pipeline's sorted
order before testing any raw placements**. This is an explicit pilot selection
policy; it is not a new production choice. We also test every discovered center
independently to match the existing pipeline.

All raw queries use only the selected center's exact deployment bounds. There
is no envelope scan, possible-center superset or common-center search. The
optimized native presence adapter expects five entries, so its fifth Fortress
entry repeats the same exact Nether deployment bound; it does not query broad
discovery.

## Results

Two disjoint cohorts each contain 128 dispersed lower32 values and four upper32
choices per value: **1,024 full64 inputs across 256 lower32 groups**. Upper
choices are fixed controls, not a claim of uniform sampling of every full64
world. 128 inputs had no discovered Stronghold and remain unresolved.

For the remaining inputs, one locked center per seed gives **896 layouts**:

| Necessary raw placement profile | Tuning: 436 locked centers | Holdout: 460 locked centers | Combined missing raw placement |
|---|---:|---:|---:|
| Current Village/City/Fortress/Bastion | 139 missing (31.88%) | 119 missing (25.87%) | 258 / 896 (28.79%) |
| Expanded MT profile including Mansion/Outpost | 160 missing (36.70%) | 131 missing (28.48%) | 291 / 896 (32.48%) |

The expanded full MT-presence and four-feature-slot profiles gave the same
decisions as adding Mansion/Outpost here. "Expanded" covers the 16 tested
region-MT families across their correct dimensions; it does not include every
structure, Mineshaft or the three LCG-based placement families.

Across **all 1,888 discovered centers**, evaluated independently at their own
borders, the corresponding missing-raw-placement rates were 29.29% and 33.21%.
These rates are about individual center/layout evaluations, unlike the earlier
3.76–4.59% whole-lower32-family rejection results.

## Does lower32 agree with full64 at that border?

**30,208 raw-layout comparisons, zero differences.** Sixteen MT families were
compared directly inside each of the 1,888 exact deployment borders. The eight
reviewed families used the generator-free public raw adapter; other families
used a lower32-only diagnostic context and were not promoted into that adapter.
Shared pyramid/temple/hut/igloo lists also matched exactly within these bounds.

The optimized exact-center raw predicate agreed with direct full64 raw
enumeration. Negative raw results skipped the four-family viability stage;
positive raw results still underwent full64 biome viability. The stage's final
decisions matched for every repeated comparison.

These are exact comparisons against the pinned predictor, not independent
actual-world certification. Missing predicted Strongholds and known Bedrock
recall/viability uncertainties are not converted into actual-world absence.

## Why the center must be part of the lower32 query

In **253 of 256 lower32 groups**, changing upper32 changed the discovered center
set. Raw MT placement at a fixed coordinate is unchanged, but a different center
selects a different square and therefore different placements.

For example, lower32 `23588479`:

| Full64 seed | First discovered center | Raw Fortress in its exact 896 Nether border | Current raw combination |
|---|---|---:|---|
| `4318555775` | `(1924,1540)` | 0 | Missing required placement |
| `-8526495043091435905` | `(1156,-156)` | 1 | Raw positive |

The appropriate query/cache key is **lower32 + exact center/bounds + family +
backend version**, not lower32 alone. Full64 biome viability is recomputed for
each sibling. A negative at one center cannot reject another center or sibling.

The ordinary center-conditioned order is therefore:

1. Discover/select the Stronghold using the full64 seed, or validate a supplied
   explicit center with the appropriate evidence.
2. Derive its exact Overworld and fractional Nether borders.
3. Use lower32 for necessary MT placement checks in those borders.
4. Use the required seed bits/full64 for LCG placement, biome viability and
   terrain/actual-world verification.

If full64 center discovery is needed first, this is not a replacement for that
discovery stage or an upfront rejection of all upper32 siblings.

## Speed: a separate gate did not help the current four-family stage

We compared current native final Nether pair → City → Village viability with
the same sequence preceded by the existing generator-free raw presence call.
All calls were inside exact deployment borders and returned identical decisions.

For the one-center-per-seed replay, native handles and bounds were prepared
before timing. Three counterbalanced trials per cohort each replayed the locked
centers eight times; repetitions measure timing stability, not more distinct
seeds. Both paths were warmed equally.

| Cohort | Current stage median | With separate lower32 gate | Time change |
|---|---:|---:|---:|
| Tuning: 436 centers × 8 | 0.4211 s | 0.5023 s | 19.28% slower |
| Holdout: 460 centers × 8 | 0.4836 s | 0.5740 s | 18.69% slower |

The larger all-center replay, which included context setup/bound conversion,
was also slower: 13.51% tuning and 14.78% holdout. Neither benchmark includes
discovery, initial broad Fortress, Trial Chamber, Mineshaft, wooded biome gating,
IPC/persistence, terrain or actual acquisition. These are stage measurements,
not whole-pipeline seeds/second changes.

Village and City raw placement are already guaranteed at this square width.
Most current raw negatives are the missing final Nether pair, which the current
combined native query identifies cheaply. A separate gate adds another wrapper
call, buffer setup and raw work on every positive, outweighing the work saved.

Recommendation: retain exact Stronghold-centered filtering. Do not insert this
separate lower32 gate into production. Investigate a fused native eligibility
path that detects missing raw types before unnecessary biome work, and reuse
placement results only for truly repeated lower32/center queries. Benchmark
those changes including cache costs before adoption. Expanded rare structure
requirements are a separate user preference, not an optimization to introduce
silently.

## Verification and evidence

17 focused tests passed, including fractional/negative border edges, raw-negative
skip behavior, raw-positive/full64-negative behavior and the prior exact-center
geometry controls. All raw and final-stage decision comparisons passed. Tuning
and holdout lower32/full64 manifests are disjoint. Native/script and parent-data
identities are preserved in the artifacts; production source was not changed by
this pilot.

Evidence: [tuning report](runs/locked-stronghold-2026-10-11/tuning/report.json),
[holdout report](runs/locked-stronghold-2026-10-11/holdout/report.json),
[locked-center tuning timings](runs/locked-stronghold-2026-10-11/tuning/locked-stage-timing.json),
[locked-center holdout timings](runs/locked-stronghold-2026-10-11/holdout/locked-stage-timing.json),
[reproduction script](scripts/pilot_locked_stronghold.py).

## All-structure follow-up

The requested all-family combination pilot is complete: [all-structure results](ALL_STRUCTURE_COMBINATION_RESULTS.md). Increasing the mix to every supported Overworld/Nether structure did not improve lower32 timing; a minimal placement gate with charged exact-center caching was 44.55% slower on holdout. The full raw combination rejected 28.48% of holdout layouts; full64 viability rejected all sampled all-structure combinations.
