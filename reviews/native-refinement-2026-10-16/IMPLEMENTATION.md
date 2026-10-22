# Pillar 3 — integrated native finalist center refinement

Implements Pillar 3 of `IMPLEMENTATION_PLAN.md` against base commit `02f041e`.
Production scoring tables, hard floors and centroid weights are unchanged.
Pillars 1 and 2 are outside this change.

## Behavior

The native v3 production pipeline now automatically enables
`native-grid-16-local-8-v1` before candidate admission. It first obtains the
best original event-cell representative, keeping complete macro inventories
and biome/spatial caches alive. It then evaluates all **15,129** 16-aligned
centers on **[-976,976]²**. If multiple eligible coarse centers lie within two
score points of the coarse maximum, it searches the union of their local
8-block windows. Each window uses eight offsets per axis, **-24 through +32**
blocks, clipped to the legal domain. Coarse points are reused and fine points
are deduplicated. The complete score and its existing radial/origin/X/Z tie
break determine the winner, including the original representative. Refinement
cannot downgrade the original ranking.

This guarantees the optimum over the complete 16-block grid plus the declared
local windows and original center. **It does not guarantee the global 8-block
grid optimum.** That stronger comparison remains available through the native
API's explicit `grid_step=8` mode and the independent Python finalist script.
A coarse plateau may cause local windows to cover most of the fine grid;
there is no early timeout that would compromise the declared comparison.

The automatic phase runs only after an original representative satisfies all
structure and palette requirements. This preserves the existing fast rejection
funnel; it is not a correction for incomplete structure enumeration or any
predictor false negative. Before refinement, centroid-only score cutoffs are
disabled: a low-scoring proposal must retain the chance to improve. The final
cutoff is applied after comparison. Top-K observes records only after the
existing transactional checkpoint commit.

## Native implementation and ownership

`nb_dynamic_v3_refine_center()` consumes complete macro observations and immutable
palette, scenic-river, village-separation and bastion-variant caches. The plan's
illustrative signature lacked the biome, optional-structure and policy evidence
needed to compute the full score; `NBRefinementInput` explicitly supplies it.
No world generation, Python callback or mutable generator context is used in
the grid loop. A companion diagnostic API scores arbitrary 8-aligned centers
for independent parity tests.

A 245-by-245 count raster uses exact 2D rectangle differences and prefix sums
for all 19 structure categories (13 native slots, strongholds, five optional
slots). This replaces the proposed occupancy bitmask, which would lose counts
when multiple structures share a cell. Half-open Overworld and scaled Nether
membership are retained exactly. Per-point containment counts are O(1) after
precomputation; distance and spread calculations still inspect relevant
inventories.

OpenMP parallelizes independent category rasters and grid points. A stable
serial reduction chooses the result, so scheduling cannot change tie breaks.
Inside the sweep's existing parallel seed workers the refiner runs serially,
avoiding nested OpenMP teams and CPU oversubscription. The public API supports
parallel standalone finalist work. Workspaces are freed before return and
charged to the existing sweep allocation budget (under 8 MiB per invocation,
excluding the already-owned macro caches). Allocation errors fail the batch
rather than publishing partial evidence.

## Storage, identity, and deployment

Existing SQLite candidate JSON now contains:

- `evaluation_center` and `refined_center`: chosen center.
- `centroid_unrefined` and `sweep_centroid`: original center and score.
- `refinement_gain`: chosen score minus original score (nonnegative).
- `grid_step`: chosen center's alignment, 16 or 8.
- `center_selection`: algorithm revision, coarse/fine point counts and precise
  search scope; `global_8_grid_optimum=false`.

The candidate JSON is already persisted in the existing schema and served to
consumers; no redundant SQL columns or destructive migration are needed. Timing
is excluded from candidate provenance so repeatable semantic records do not
acquire nondeterministic timestamps. Native timings remain diagnostic evidence.
Pipeline computation identity records the refinement revision, preserving
fail-closed resume behavior. The low-level `Prototype.sweep()` keeps refinement
explicitly disabled by default for centroid controls and historical comparisons;
`persist_pipeline()` / `run_native_scan()` enable it automatically for v3.
The Python production executor remains the independent reference route.

Both packaged native extensions and the private OpenMP engine were rebuilt.
The web selector prefers the source-compatible
`runs/dynamic-baseline-2048/native-refinement-2026-10-16` build. An already-running
web server must be restarted to load this source and binary; old checkpoints
are not silently migrated. No server was restarted as part of this task.

## Verification and performance

`tests/test_native_refinement_parity.py` covers exact score and rounded radial
key agreement at **1,000** independently calculated centers (including rejects),
the complete 16-grid optimum on the synthetic optional-capture witness,
coarse/hierarchical/full-8 ranking bounds, filtered mansions, custom targets,
floor/palette rejection, malformed arguments, production JSON persistence,
Top-K and resume, and a real native synthetic sweep at the final score cutoff.
The witness recovers **(32,0), 105 points**, instead of the earlier centroid's
90 points. A separate sweep fixture shows automatic 8-block movement at equal
score with improved tie ranking. The natural persistence case has an explicitly
empty required Overworld palette; it is not a full-blueprint survivor or a BDS
verification.

The focused regression run passed **27 tests** (`regressions.log`), including
all **12** new cases plus framework and Top-K regressions. The initial dedicated
10-case run also passed (`parity.log`). The full invocation completed with
**1,218 passed and one skipped in 426.01 seconds** (`pytest.log`). Its sole
skip was the existing v3 OpenMP determinism control: its build picker did not
include the newly rebuilt directory, so it fell back to the serial package.
The picker now includes the current OpenMP build and the control is included
in the final focused recheck. Two additional cases added after full-suite
collection are also included in that recheck. The current suite collects
**1,221 cases** (`collected.log`).

`benchmark_refinement.py` records complete current build identity and repeated
bounded timings in `benchmark.json`. On the available host, **8-thread median
coarse and hierarchical refinement times were 4.14–4.87 ms** across two synthetic
inventories; complete 8-grid searches took 7.54–8.33 ms. These include workspace
allocation and exclude generating the macro inventories. The <5 ms target is
met by these fixture medians, not a worst-case latency guarantee. Single-thread
sweep refinement is deliberately slower to preserve the outer thread budget.
Actual 1-thread/8-thread OpenMP results had identical centers, scores and radial
keys in each measured arm.

Three matched 65,536-input compact screening cohorts measured medians of
**116,582 seeds/sec with refinement enabled**, versus **113,563 disabled**,
using the same build and 34 threads. This supports preserving rejection
throughput; the small apparent gain is timing noise, not an optimization claim.
The checkpointed pipeline measured **104,333 inputs/sec**. All these cohorts
had zero retained candidates, so they do not measure accepted-record throughput
or discovery probability. Tests were concurrent with some timings. No GPU or
new game-world certification is involved.

The known natural positive returned identical semantic records, centers, scores
and radial keys at **1, 4 and 34 outer sweep threads** with automatic refinement
enabled (`positive-determinism.json`). This comparison deliberately excludes
per-run top-level timing metrics and includes all persisted center provenance.

The final **32-test** recheck passed with **no skips** in **22.90 seconds**
(`final-regressions.log`), including the formerly skipped OpenMP control and
all 12 new refinement cases. All **1,221 currently collected cases** are covered
across the full invocation and final rechecks, with no remaining known failure
or unverified skip. The full invocation itself remains recorded accurately as
1,218 passed / one skipped; it is not relabeled as a 1,221-pass invocation.

All changes remain local and uncommitted. No push was performed.
