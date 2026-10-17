# Framework review of `3a83220` — October 16, 2026

**Verdict: the current source has a strong CPU architecture and coherent new score arithmetic, but it is not established as the fastest, most accurate, or best-ranked implementation possible.** The latest scoring rebalance is reasonable to retain provisionally. The larger issues are native deployment compatibility, search-domain validation, activation of promised features, the limited center objective, and validation against actual generated worlds.

Reviewed `main` / `origin/main` at `3a83220a932d1e7750aa8f93510b1b956ed8c60f`, emphasizing its changes from `84a83ba` and the preceding framework optimizations. The working tree was clean when this review began. This audit adds reports, reproducible probes and isolated evidence under this directory; application source and selected native deployments were not changed.

The four perspectives are [mathematical analyst](mathematical-analyst.md), [player preference helper](player-preference-helper.md), [pessimist](pessimist.md), and [optimist](optimist.md). This report is the fifth role: it checks their conclusions, separates demonstrated defects from design choices, and determines what their evidence actually supports.

## Prioritized actionable findings

### F1 — P1: the web default selects a stale native build

`src/seed_search/web/server.py:41–46,184–191`; `src/seed_search/realm/native_batch.py:75–95`.

The preferred directory `runs/dynamic-baseline-2048/native-mansion-bound-2026-10-16` has **11** native/vendor inputs differing from this checkout. Its binary and runtime match its own old manifest, so `Prototype` accepts it. That check does not establish agreement with the currently requested scoring and center policy.

A positive synthetic fixture, seed `456` with fixture `(0,0,-1)`, then fails with `RuntimeError: Native/direct dynamic record parity failure at anchor 0`. The current private directory `runs/dynamic-baseline-2048/native` has **zero recorded input mismatches** and produces the new **479-point** fixture score, as does the packaged extension. Independent root and pessimist probes agree.

This can remain invisible through many rejected inputs and fail when positive evidence is reconstructed. Select a source-compatible build and reject incompatible policy/build combinations before starting a run. Include a positive-path launch check. Preserve historical builds only with their matching historical policy. Evidence: [positive.json](positive.json), [integration_probe.json](integration_probe.json).

### F2 — P2: direct strided scans accept indices that silently repeat seeds

`src/seed_search/seeds.py:24–40,43–67`; `src/seed_search/realm/native_batch.py:48–53,572–578,732`; `src/seed_search/realm/runner.py:192–194`; `scripts/shard_campaign.py:174–177`.

For a fixed low32, only **2^32 distinct upper-bit siblings** exist. The scalar, list and NumPy generators mask the index to 32 bits, but the direct native scan validates its range against the generic **2^64** limit. In each generator, index `0` and index `2^32` with low32 `12345` both return seed `12345`.

An isolated one-input production native call with `start_index=2**32`, `count=1`, sequence `strided`, low32 `12345` was accepted and durably committed. Larger scans crossing the boundary can therefore count repeated worlds as additional covered indices. The campaign partitioner correctly enforces the narrower domain, so the defect affects bypassing that partitioner through direct entry points, not its validated campaign output.

Enforce `[0,2^32)` at every strided generator and scan boundary, including resume and merge coverage validation. Do not apply that restriction to the normal full64 permutation sequence. Evidence: [strided-wrap.json](strided-wrap.json), [probe_strided.py](probe_strided.py).

### F3 — P2: automatic Top-50 pruning is implemented but off in normal launches

`src/seed_search/realm/config.py:388–413`; `src/seed_search/realm/native_batch.py:555–558,581–583,747–751`; `MASTER_SEED_BLUEPRINT.md:169,245`.

The v3 config supplies no `search.top_k`; `run_native_scan()` resolves the default to zero. The ordinary CLI/web launch does not enable it. A known positive custom-palette run saved a candidate without creating Top-50 artifacts. This contradicts wording that presents the ratchet as an automatic active feature.

Choose and expose the intended default, persist it, and test the actual UI/CLI launch path. The existing tracker/recovery implementation can be retained. This will not improve initial yield or speed before enough eligible candidates exist to establish a cutoff. Evidence: [integration_probe.json](integration_probe.json).

### F4 — P2: the advertised portable x86 build now requires AVX2/FMA

`vendor/cubiomes-bedrock/noise.c:7–12,133,195–219`; `native/build.py:11–16`.

The new noise implementation enables AVX2/FMA on every x86-64 GCC/Clang build through target attributes, without runtime CPU dispatch. Leaving the opt-in AVX2 build flag off does not restore scalar behavior on x86. A CPU without those instructions can execute an unsupported instruction when sampling. This is established by the source; this host supports them, so an older-CPU crash was not reproduced.

Provide scalar entry points plus guarded dispatch, or explicitly require and validate the minimum CPU ISA before scanning. Make build metadata describe the actual requirement. This issue originates in `84a83ba`, not the score-only latest commit.

### F5 — P2: the suite has stale score expectations and launch assumptions

`tests/test_native_mansion_bound_and_recovery.py:81`; `tests/test_top_k_integration.py:13,48,94`; `tests/test_web_machine_contract.py:77`.

The missing/corrupt/stale/valid checkpoint recovery cases still expect **296** points. The current natural custom-palette survivor is **311** points. The preceding assertions establish that recovery preserved its committed leader; the remaining failures are obsolete expectations, not renewed evidence of the old recovery-loss bug. Another cutoff test still expects **482** rather than the new **479** fixture score. These five golden-score failures were missed by the latest rebalance.

Two additional Top-K tests request four threads from the packaged **serial** build, without supplying an explicit OpenMP build. The web machine-contract test inherits the now-active v3 profile but still expects a one-miss launch, while v3 correctly resolves it to zero. These three failures are test setup/assumption gaps, not demonstrated faults in those production safeguards. Use an explicit compatible build/profile, or adapt the expectations to the active v3 contract. Retain the positive recovery and entry-point coverage.

### F6 — P2: current parity and benchmark claims exceed their coverage

`tests/test_v3_optimizations_parity.py:96–138,159–167,265–285`; `scripts/benchmark_v3_throughput.py:30–38,133–150,159–173`.

The 5,000-input parity test compares retained candidates and, when none survive, independently checks only **eight rejects**. The determinism test compares survivor counts, which can agree at zero without exercising scoring. Direct-versus-replay fixtures share native evidence and the selected center. These are useful checks, but they cannot prove complete recall or optimal center selection.

The throughput script reports the **best of two** trial times against literal historical baseline rates; it is not a fresh paired old/new experiment. Its stage profile uses **full retention**, whose stronghold-discovery order differs materially from compact screening. Do not use that profile's 62.7% stronghold share as a compact bottleneck measurement. Current private-build metadata has **no PGO profile hash**, so the existence of a PGO rebuild script does not establish that the selected runtime uses PGO.

Use nonempty positive corpora, bounded independent rejection comparisons, exact source/build identities, repeated matched cohorts, median timings and separate durable-pipeline measurements. Existing earlier matched Mansion-bound measurements remain historical evidence for that optimization; this finding does not invalidate them.

## Center selection: correct geometry, limited optimization objective

The new pull weights are consistently `village=2`, `trial_chamber=1`, `stronghold=3` in the reviewed current C/Python paths. The half-open geometry and snapping probes found no defect: **100,000** snapping checks and **315,732** Nether membership/boundary checks passed. The changed score helpers passed **20,000** randomized fresh-source C/Python comparisons.

However, event cells preserve mandatory counts and sampled palette membership, while optional counts and proximity bonuses can change inside them. Evaluating a single snapped centroid does not maximize the complete player score across legal centers. A reproducible synthetic inventory satisfying all 14 floors demonstrates:

| Result | Center | Score | Mean weighted radial distance |
|---|---|---:|---:|
| Best defined representative | `(64,0)` | 90 | 115.606 |
| Better valid chunk-aligned center | `(32,0)` | **105** | **98.743** |

The alternative captures two optional huts instead of one. Exhaustive evaluation of **15,129** chunk-aligned centers confirms the better result. The witness assumes the required palette is valid at those centers; it is a mathematical counterexample, not a discovered natural seed or a frequency estimate. [Runnable probe](math_probe.py), [complete evidence](math-probe.json).

The blueprint already limits its claim at line 311. Treat this as an existing design limitation, not a new incorrect pruning bound. The centroid also minimizes weighted **squared** distance; the radial tie-breaker uses ordinary Euclidean distance, whose minimizer is a geometric median. They are different objectives.

For finalists, compare all 15,129 chunk-aligned centers or the separately labeled 60,025-point grid of multiples of 8. Keep the rapid rejection funnel and benchmark the added work only after hard-floor survival. This can improve selection entirely on the CPU. Full optional events alone would not address changing circular hub/scenic distances.

## Are the new scores and weights good?

**They are a coherent starting model, with no demonstrated arithmetic defect in the latest push. They are not calibrated player preferences.**

All 14 core and five optional surplus schedules are monotone with non-increasing marginal rewards. The stronghold change fixes the previous increasing marginal reward under that design. The mansion/trial and hut/igloo rebalances conserve the algebraic ceiling: **650 core + 200 optional + 265 luxury + 135 spatial = 1,250**. This ceiling is an arithmetic bound, not a demonstrated attainable generated seed.

The weights materially reduce village/chamber dominance, but they cap each instance, not each category. At the minimum inventory, villages contribute 12 pull units, trials 8 and the stronghold 3 out of 35. Thus villages plus trials supply **57.1%**, while the stronghold supplies **8.6%**. Previously those shares were 72.3% and 2.1%. Extra villages/trials continue pulling even after their score saturates.

The most important player tradeoffs are visible in simple score deltas:

| Improvement, all other components held equal | Points |
|---|---:|
| Nearest village moves from 900 blocks to 100 | 15 |
| One basement igloo | 30 |
| Second mansion | 45 |
| Five additional trial chambers beyond the eight-chamber floor | 45 |
| Two basement igloos | 50 |

These are controlled model comparisons, not a claim all paired worlds occur. For settlement-first players, optional duplicates can outweigh a large improvement in everyday convenience. Six villages somewhere in the window do not guarantee one near the hub. Biome witnesses do not guarantee dry, flat, connected building land, a large useful resource region, or complete structure footprints inside the border.

Retain the current numbers provisionally. Agree on actual finalist requirements, collect blinded pairwise preferences from intended players, and compare current rankings with a simple monotone calibrated model on held-out candidates. Compare alternative center objectives separately. Do not change weights repeatedly based only on which rare feature sounds impressive. The player report gives concrete tradeoffs and a calibration protocol.

## Accuracy and important framework aspects

| Area | Reviewer assessment |
|---|---|
| New score arithmetic and caps | Supported by fresh-source checks; no new LUT defect found. |
| Half-open windows, integer snapping | Strong targeted evidence; no new boundary defect found. |
| Center quality | Best prescribed representative; demonstrably not a global player-score optimum. |
| Native/Python agreement | Positive current-source route agrees at 311 points; shares the underlying predictor. |
| Native deployment | Stale preferred web artifact is an actionable blocker. |
| Long-run ownership and persistence | Bounded pipeline and transactional recovery are strengths; prior Top-K recovery and disabled-preflight initialization defects are fixed. |
| Resume and policy changes | Configuration/computation fingerprints guard normal resume; no resumed score-mixing bug established. |
| Strided/distributed coverage | Campaign partitioner bounds correctly; direct strided entry points can wrap and repeat. |
| Web product contracts | Production build and 13 JavaScript checks pass; runtime native selection remains separate. |
| Terrain, structures and actual generation | Predictor starts/witnesses do not certify physical structures, accessible portals, complete containment, loot or buildability. |
| Numerical SIMD rewrite | Tiny raw-double changes observed; no biome/filter decision mismatch in the bounded control. |
| CPU optimality | Good architecture; further measured opportunities remain, with no proof of a maximum. |

`src/seed_search/realm/capabilities.py:19–35` explicitly retains incomplete stronghold recall and Ancient City/Bastion reference disagreements. The old accuracy audit's Chunkbase agreement percentages compare predictors and are **not** in-game false-positive/recall rates. No fresh BDS generation was performed in this review. Version-matched generated-world observations are needed to resolve the remaining discrepancies and verify important finalist structures and hub conditions.

The scalar/SIMD control checked **131,072** biome points and **131,072** dark-forest-filter evaluations with **zero decision mismatches**. Of 98,304 raw climate doubles, 65,778 differed, with maximum absolute delta `4.44e-16`; none differed after conversion to float32. This supports the tested decisions, not universal numerical identity or Bedrock accuracy. [Control evidence](noise_comparison.json).

Changing scores and center weights while retaining the same human-readable v3 label weakens provenance, but current resume fingerprints prevent the straightforward old/new mix. Give the rebalance an explicit scoring/selection subrevision. Reevaluate historical seeds when the center policy changes: rescoring an already saved window cannot recover discarded alternative centers.

Zero survivors in a bounded cohort does not establish impossibility, mutually exclusive climate requirements, or a precise one-in-billions success rate. Score-weight changes do not relax the hard floors. Measure unique-input yield and finalist quality separately from raw seed throughput.

## Verification and measured CPU throughput

The full suite completed with **1,189 passed and 8 failed in 398.97 seconds**. The eight failures are classified in F5: five stale score expectations, two serial/OpenMP test setup failures, and one stale web-profile expectation. This checkout does not have a green test suite. [Full log](pytest.log).

The web production build succeeded; all **13** JavaScript contract checks passed. [Build log](web-build.log), [contract log](web-contract.log). Fresh score/boundary probes and the independent positive survivor check passed. The latter uses the explicitly custom empty Overworld palette and must not be counted as a full-default-blueprint survivor.

Fresh timing used the source-matching current private build, 16,384-input batches, three disjoint 65,536-input cohorts and rotated thread-arm order. Each cohort was reused across arms; there are **196,608 distinct measured inputs**, not a new population for every arm. The full Python suite had ended before timing began. A pre-existing background file scan consuming approximately one CPU core remained active; these are local indicative timings, not an otherwise idle-host certification or a paired historical speedup measurement.

| Current v3 compact path | Median inputs/sec |
|---|---:|
| 1 thread, kernel sweep wrapper | 7,370 |
| 12 threads, kernel sweep wrapper | 67,206 |
| 18 threads, kernel sweep wrapper | 84,878 |
| 24 threads, kernel sweep wrapper | 99,106 |
| 34 threads, kernel sweep wrapper | **113,169** |
| 34 threads, checkpointed compact pipeline | **101,945** |

The host exposes 36 logical CPUs. The 34-thread kernel arm ranged from **110,048 to 117,790 inputs/sec**. Only one distinct measured seed reached a structure-feasible cell; **zero** survived the full default palette. These rates primarily measure rejection throughput. They do not establish accepted-record throughput, game-generation accuracy, a precise discovery rate, or a completed world's delivery time.

The durable arm explicitly enabled Top-K=50 for this experiment; with no survivors, its cutoff remained unset. Its timing therefore demonstrates the checkpointed pipeline with an empty tracker, not acceleration from an active ratchet. Its current build identity records AVX2/FMA and LTO with **no PGO profile**. [Reproduction](benchmark_cpu.py), [raw timings and build identity](cpu-benchmark.json), [execution log](cpu-benchmark.log).

At these conditions the CPU implementation is already useful and fast. There is no evidence that it has exhausted CPU optimization opportunities, and the last scoring push itself is not shown to improve raw throughput. The priority is improving trustworthy results and center quality before claiming another percentage speedup.

## Review of the four perspectives and recommended order

The mathematical analyst's global-optimum counterexample is valid, and is classified as a design limit because the detailed blueprint already acknowledges the representative rule. Its exact score-cap and boundary checks support keeping the latest arithmetic.

The preference helper's ranking examples correctly expose implied tradeoffs. Its suggested priority for hub usability is a recommendation for a shared-survival realm, not a universal numerical correction or authorization to relax floors.

The pessimist's stale-build, Top-K-default, portability and test-baseline findings are supported. Tiny floating-point differences alone are not treated as an observed Minecraft accuracy regression. The old checkpoint-loss bug is not carried forward after the current recovery checks pass.

The optimist is right to preserve the early native rejection funnel, bounded pipeline, conservative bounds and recovery design. Those strengths and internal parity do not establish complete world-generation accuracy or maximum possible throughput.

Recommended order:

1. Make the web default and native/policy compatibility check correct; update stale golden values and make the suite's build/profile assumptions explicit.
2. Bound direct strided scans to their actual 32-bit sibling domain and make CPU ISA requirements explicit.
3. Make Top-50 activation match the product contract. Measure cutoff value and pruning frequency before attributing speed to it.
4. Add an exhaustive CPU finalist-center oracle and a held-out nonempty differential corpus.
5. Measure current compact bottlenecks and representative-workload PGO against a matched control; consider count/centroid tables and deferred radial work only where measured cost justifies them.
6. Verify shortlisted worlds with the pinned game version and calibrate scoring against the players' actual preferences.

No GPU is needed for these corrections or validation steps. No production fixes, deployments or long campaigns were performed as part of this review.
