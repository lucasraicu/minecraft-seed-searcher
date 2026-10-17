# Optimist — current-source CPU architecture and improvements

The framework has a strong CPU design, and the latest push improves the consistency of its intended preference model. There is useful engineering here worth preserving. Neither the source nor the available measurements establishes maximum possible speed, globally optimal centers, or complete Bedrock accuracy.

## What the latest push gets right

Commit `3a83220` makes a focused policy change. Stronghold surplus changes from `0,20,50` to `0,30,50`, fixing the increasing marginal reward under the blueprint's diminishing-return objective. The mansion/trial rebalance preserves the 650-point core ceiling; the hut/igloo rebalance preserves the 200-point optional ceiling. The full ceiling remains `650+200+265+135=1250`. Fresh arithmetic checks in the mathematical analyst's report found no C/Python disagreement.

The village/trial/stronghold centroid change is propagated through the C centroid table, C radial table, Python config, Python center selection, and Python radial policy. The latest source agrees on village 2, trial 1, stronghold 3. Historical v1/v2 weights remain separate. This is a coherent change with understandable intent; the player preference report explains its remaining tradeoffs.

## Architecture worth keeping

- Compact mode rejects seeds before allocating retained Python records. Raw placement, mandatory-structure bounds, delayed noise initialization, and rare-first viability checks avoid expensive work on most inputs. `native/blueprint_dynamic.inc:899–1033`.
- Half-open event boundaries preserve required structure membership and lattice membership. Negative coordinates and integer snapping are handled explicitly. Fresh mathematical probes checked 100,000 snapping cases and 315,732 Nether membership/boundary cases without mismatches. This supports these particular helpers, not a proof of every generator and integration path.
- Native workers use OpenMP; preparation and SQLite writing have separate bounded stages. Batch size, native ownership, payload budgets, disk capacity and memory checks make long sweeps more practical. `src/seed_search/realm/native_batch.py:504–720`.
- The Top-K implementation now observes candidates after their SQLite range commit and reconstructs its state from committed candidates on resume. The old corrupt/stale JSON recovery finding is fixed in current code. `src/seed_search/realm/native_batch.py:613–618,649–655`. Default activation remains a separate issue in the pessimist report.
- Stage score upper bounds are conservative for the current score: 600 points after core, 335 after luxury, and 135 after optional. Strict `< cutoff` pruning preserves equal-score alternatives for later tie breaks. `native/blueprint_dynamic.inc:1032–1042,1119–1174`.
- The app distinguishes predicted evidence from actual generation. Version and computation identities, read-only merge snapshots, transactional recovery tests, missing-evidence rescore errors, and the BDS evidence checks provide a useful basis for trustworthy operation.

## Positive behavior verified afresh

`verify_positive.py` evaluated natural seed `-3336796033057908633` with a **custom empty Overworld palette**. This is a structure-floor positive path, not a survivor of the complete default blueprint.

Current-source native full retention, native compact retention, independent Python generation/evaluation, and same-policy rescoring all returned center `(-480,0)`, score **311**, and radial key **851304967**. The detailed score components also agree. Cutoff 311 retains this candidate; cutoff 312 discards it. Results and native build identity are in `positive.json`.

The web production bundle builds, and all 13 JavaScript contract checks pass. The full Python suite outcome is recorded in the reviewer report; the four recovery expectations still hard-code the former 296-point value even though recovery preserves the new 311-point candidate.

## CPU work that could still help

First make the web server select a source-compatible binary. A stale preferred artifact defeats otherwise correct optimizations and can fail only when a positive candidate is finally reconstructed.

Then measure the real compact path using the same build, policy, retention, cohorts, and durability settings. The existing throughput script reports peak timing against literal historical reference rates and profiles full retention. Its full-mode stage percentages do not identify compact-mode bottlenecks, because full retention performs stronghold discovery before rejecting seeds that compact mode can reject earlier. See `scripts/benchmark_v3_throughput.py:30–38,133–150,159–173` and `native/blueprint_dynamic.inc:932–974`.

Current local build metadata has `pgo_profile_sha256=null`. Representative-workload PGO is therefore an experiment worth comparing against the existing build, not a currently certified property or a guaranteed gain. Clang explicitly recommends representative inputs for PGO: [official Clang manual](https://clang.llvm.org/docs/UsersManual.html#profile-guided-optimization). Preserve numerical semantics and compare retained decisions when changing compiler flags.

For the much smaller survivor path, useful experiments include constant-time per-cell count/centroid tables, calculating radial tie breaks only when needed, and a more exhaustive finalist center search. A 16-block center grid within `[-976,976]^2` contains only **15,129** points; the 8-block grid contains **60,025**. Exhaustive finalist evaluation on a CPU can provide a meaningful correctness oracle and improve selected centers without imposing that work on every raw seed. The production rule prefers 16 where possible and uses 8 only as a cell-local fallback, so the two exhaustive comparisons must be labeled separately.

These are proposed experiments. No speculative speedup percentage is assigned to them, and no production code was changed by this audit.
