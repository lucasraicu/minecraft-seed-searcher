# Final system audit — commit 233fad7

| Item | Scope |
|---|---|
| Audited commit | `233fad76fddc5667e77c27ab7e5cc83d3669a7a2` |
| Remote check | Local `main` matched GitHub `refs/heads/main` when checked. |
| Decision | **Do not mark the v2 rollout fully verified yet. Fix F1–F4 before relying on new campaign rankings.** |
| Changes made by this audit | Evidence, probes, and this report only. No production source, configuration, blueprint, or aggregation edits. |
| Policy authority | Agreed contracts in aggregation Sections 8–9, checked against implementation; the contradictory README/blueprint prose is a finding. |

**Concurrent-change boundary:** during the final artifact check, an external edit changed `vendor/cubiomes-bedrock/generator.c` to use a small stack buffer in `getBiomeAt`, and the optimized extension was replaced. Neither change was made or reverted by this audit. Tests and measurements below apply to the recorded commit/build identities, not that newer working-tree optimization. Its diff is captured in [concurrent-generator-change.patch](concurrent-generator-change.patch). Validate its output parity and buffer initialization assumptions across the supported sampling paths before transferring these results to the new build. No defect in that new optimization is asserted here.

## 1. Findings, ordered by impact

### F1 — P1: Native scenic scoring reads Y=0 instead of Y=63

**Source:** `native/blueprint_dynamic.inc:352` and `:358`; grid population at `:100`; policy assignment in `src/seed_search/realm/native_batch.py:113`.

The grid stores layers in policy order `[63, -48, 0, 160]`. The scenic cache reads layer index **2**, which is Y=0. The agreed scenic/River pairing requires Y=63, index 0. This affects scoring during center selection, not merely a displayed witness.

**Reproduced using the actual native cache functions:**

| Controlled biome evidence | Expected bonus | Native bonus |
|---|---:|---:|
| Qualifying scenic/River pair only at Y=63 | 20 | 0 |
| Qualifying pair only at Y=0 | 0 | 20 |

Evidence: [native_probe.c](native_probe.c), [native-probe.json](native-probe.json).

The record parity check does not independently catch this: `ReplayProvider` carries native scenic flags, and `evaluate_dynamic_seed` uses those flags. The existing independent-selection fixture does not contain a positive River pairing.

**Smallest fix:** select the actual Y=63 layer by a named index or resolved policy position. Add native positive and negative height-layer cases and a multi-center independent-selection fixture where the scenic component changes the winner. No extra biome generation is necessary.

**Existing results:** fixed-window rescoring can correct a stored window only after F5 is fixed. It cannot recover a better center discarded during original selection. Re-evaluate affected seeds when correct winning-center rankings are required.

### F2 — P1: The web launch path still selects v1

**Source:** `src/seed_search/web/server.py:32`, `:130`, `:145`, `:1262`; `web-ui/src/mockData.ts:35`; `web-ui/src/components/FilterSidebar.tsx:687`.

The CLI/default configuration is v2, but the web profile factory still maps `dynamic1664` to `dynamic_blueprint_config`, the **v1** factory. Default web deficit budget remains 2, and the UI offers only 0/1/2. Generated profile metadata already advertises v2 and 3, so metadata checks alone miss the discrepancy.

**Reproduced:** intercepting the resolved configuration before any process launch produced:

```json
{"revision":"dynamic-envelope-1664-v1","budget":2,"terrain_variants":["v1"]}
```

This means a web-launched campaign does not use the agreed v2 score/eligibility contract. It also retains the old terrain configuration; this probe does **not** claim the web launch itself automatically runs a terrain job.

**Smallest fix:** route the active profile to the v2 factory; derive defaults and selectable deficit budgets from the resolved profile. Preserve explicit historical profile/resume behavior. Verify the actual launch configuration and command, including an eligible three-deficit fixture, rather than testing only generated JSON.

### F3 — P1: NumPy inputs bypass the native seed-buffer contract

**Source:** `src/seed_search/realm/native_batch.py:160` and `:180`.

Any object with `__array_interface__` bypasses `parse_seed`. Its bytes are exposed as `uint64_t[]`, while C receives `len(seeds)` as the element count. The adapter does not verify an eight-byte integer dtype, native byte order, or one-dimensional shape.

**Reproduced:**

- Real native compact evaluation accepts `np.float64([1.0])` and evaluates the bit pattern as seed `4607182418800017408`, returning without error when no record survives.
- A safely intercepted call with `np.int32([1,2])` exposes **one** uint64 element but requests **two** native inputs. Allowing that call to proceed would permit an out-of-bounds read. The audit deliberately intercepted it before entering C.

The production `seeds_np` generator currently produces suitable int64 arrays. This is a defect in the public adapter boundary, not evidence that ordinary generated batches already read out of bounds.

**Smallest fix:** require a contiguous, one-dimensional, native-endian eight-byte integer buffer; define accepted signed/unsigned seed semantics explicitly; validate buffer length against the count before calling C. Keep the fast path for known-good generated arrays. Test float, int32, multidimensional, wrong-endian, and noncontiguous rejection plus signed-boundary parity.

### F4 — P1: Accepted custom targets make native and Python deficit scoring disagree

**Source:** `src/seed_search/realm/config.py:430`; `native/blueprint_dynamic.inc:851`; `src/seed_search/realm/blueprint.py:528`; `src/seed_search/realm/native_records.py:110`.

Configuration validation permits changing flexible preferred targets while retaining fixed hard floors. Native penalties use the configured goals. Python `dynamic_v2_score` hardcodes the default targets.

**Reproduced with valid configurations and synthetic native survivors:**

| Configured target | Observed count | Native deduction | Record construction |
|---|---:|---:|---|
| Villages 10 | 9 | 10 | Native/direct parity failure |
| Ruined Portals 8 | 7 | 5 | Native/direct parity failure |
| Trial Chambers 9 | 8 | 10 | Native/direct parity failure |

A customized run can process rejected inputs successfully and then fail when it reaches a qualifying record. Independent Python selection also evaluates the wrong configured deficit cost.

**Smallest fix:** pass resolved targets into the reference scorer and rescore path, using the same policy values as native eligibility. Keep the approved bonus schedule explicit; do not silently shift milestone thresholds merely because a user changes a screening target. If customization is intentionally unsupported for v2, reject it at configuration loading instead of accepting it and failing later. Test both raised and lowered flexible targets.

### F5 — P2: Retained evidence and rescoring do not independently establish new spatial/variant bonuses

**Source:** `src/seed_search/realm/blueprint.py:698`, `:712`, `:766`; `src/seed_search/realm/reports.py:332`; `src/seed_search/realm/dynamic.py:239`; `native/blueprint_dynamic.inc:483`.

Three related gaps remain:

1. The native result carries Bastion coordinates/variant IDs, but the final durable anchor retains only the treasure flag, not those per-Bastion variants. The saved candidate cannot independently explain or reconstruct that award.
2. Rescoring reads saved scenic, Village-spread, and treasure flags. It does not recompute the first two from retained samples/coordinates, and absent flags default to zero. Supplying the same retained Y=63 pair with a flag of 0 versus 20 changes the rescore by 20. It therefore preserves F1's wrong award unless explicitly repaired.
3. The treasure helper treats a variant error value of `-1` as ordinary non-treasure absence. The native cache also does not propagate a negative variant result. This is a demonstrated error-handling gap, not a claim that the normal pinned predictor frequently fails.

**Smallest fix:** persist the compact coordinate/variant evidence already obtained; recompute selected-window spatial bonuses from retained data; represent missing/failed evidence as unresolved rather than evaluated absence. Keep predictive status explicit. An independent test should invalidate a stale flag or missing variant evidence, not simply replay it.

**Related presentation issue:** treasure's 15 points are included in `optional_bonus` and also exposed as `treasure_bastion_bonus`. The aggregate is correct, but those entries are not additive siblings. Label treasure as a subcomponent or separate it from the optional subtotal before displaying an additive breakdown.

### F6 — P2: Agreed player presentation and complete result browsing are unfinished

**Source:** `src/seed_search/web/server.py:566`, `:823`, `:995`; `web-ui/src/types.ts:78`; aggregation Sections 8.1 and B7.

The server/types expose several new scoring fields, but the UI does not consume the new score-component/scenic/spread/treasure/deduction properties. The generated `suggested_spawn` is not exposed through the old `spawn_stage` presentation path. The positive saved fixture also lacks explicit End-access, portal-inspection, and snow/ice inspection fields required by the agreed reporting contract.

The server loads `LIMIT 250`; `/api/candidates` exposes that pool without pagination. This does **not** delete additional database candidates, and CLI export remains available. It does mean the promised ability to browse all retained qualifying results through the dashboard is unfinished.

**Smallest fix:** finish the existing candidate/detail views, expose the biome-based spawn suggestion with its uncertainty, add lightweight unverified/unavailable inspection states, and implement indexed pagination with deterministic ordering. Do not introduce automatic terrain, BDS, portal traversal, or block-resource generation. Verify retrieval beyond 250 candidates and component rendering.

### F7 — P2: The README and blueprint describe materially different policies

**Source:** `README.md:7`, `:18`; `MASTER_SEED_BLUEPRINT.md:81`, `:160`; aggregation status header.

These are behavioral contradictions, not wording preferences:

- README calls hard floors fatal but then says flexible floors may be missed and gives deductions of 30/75/135.
- Blueprint Section 3 still rejects three deficits; active v2 permits three deficient categories, with hard floors remaining fatal.
- The newly labeled active v2 section gives Village floor/target 6/8, Trial Chamber 4/6, and Ancient City 1/2. Agreed and implemented defaults are 8/9, 7/8, and 3/4.
- The documents give wrong surplus/optional schedules and hub/scenic/spread definitions. For example, the actual second Stronghold is +35, and scenic requires a Y=63 scenic/River pair, not two attractive biomes.
- The aggregation says both workstreams are completed and verified, although the findings above and current test failures contradict that acceptance statement.

**Smallest fix:** reconcile README and blueprint with aggregation Sections 8–9 and the corrected implementation. Label historical sections explicitly. Use a small shared policy descriptor/generated table for numerical rules where practical; do not maintain multiple independent hand-entered score schedules. Replace the blanket completion claim with a verification ledger linked to actual artifacts.

The correct default score arithmetic already passes its unit checks: core 340 + optional/treasure 129 + luxury 175 + spatial 75 = **719**, before deductions. That ceiling does not prove simultaneous attainability or imply every score should approach 719. Do not change the working arithmetic to match the erroneous prose.

### F8 — P3: The dashboard's final tie-breaker is not the specified binary order

**Source:** `web-ui/src/utils/ranking.ts:15`.

The v2 UI uses `localeCompare`; the contract and SQLite ordering require binary lexical candidate-ID order. With all preceding keys equal, actual production comparator output places `-1:0:0` before `-10:0:0`; binary comparison places them in the opposite order.

Evidence: [ranking_probe.cjs](ranking_probe.cjs), [ranking-probe.json](ranking-probe.json).

**Smallest fix:** compare these ASCII IDs with `<`/`>` and test a shared tied candidate set across Python, SQL, and UI. This is a reproducible comparator mismatch, not evidence that a naturally occurring tied pair has already changed a campaign's displayed winner.

**Additional bounded concern:** Python `weighted_radial_v2` traverses its Village-first dictionary, while native radial accumulation uses Stronghold first then macro-slot order. That differs from the explicit accumulation-order contract. Floating summation near a rounding boundary can be order-sensitive, especially across Python versions. No changed natural winner from this discrepancy was reproduced here. Align traversal/accumulation and add the required half-step tests before claiming exact cross-path ranking parity.

## 2. Performance: what the measurements actually establish

### Current optimized durable pipeline

Five trials used the source-matched existing PGO+LTO build, each with 100,000 identical natural inputs, run key `2026101401`, starting index `50000000`, 34 threads, batch size 16,384, compact retention, deficit budget 3, and a separate temporary database.

| Metric | Median per 100,000 inputs |
|---|---:|
| Durable wall time | 525.22 ms |
| Native call service time | 505.67 ms |
| Native service/wall ratio | 96.23% |
| Seed preparation | 3.03 ms |
| SQLite commit time | 3.40 ms |
| SQL execution time | 1.19 ms |
| Record construction | 0.14 ms |
| Durable throughput | 190,398 inputs/s |

All trials retained zero candidates. These short measurements support Gemini's approximate **96% native** observation for this workload. They do not establish that Python/SQLite overhead is solved for every workload, nor do they invalidate a different cohort's faster throughput. Service timings can overlap in the pipeline and must not be treated as a mutually exclusive wall-time pie chart.

### Stage entry counts differ substantially from Gemini's table

An isolated source copy added nonoverlapping timers around the current native stages. It used the same 100,000 inputs and retention policy, CPU-native/LTO/OpenMP but **no PGO**. Retained-result outcomes matched the optimized control on this all-reject cohort.

| Instrumented stage | Inputs reaching stage | Share of summed worker elapsed evaluation time |
|---|---:|---:|
| Raw preflight | 100,000 / 100% | 23.38% |
| Overworld generator initialization | 39,682 / 39.682% | 18.24% |
| Raw Dark Forest witness gate | 39,682 / 39.682% | 23.65% |
| Full Mansion inventory | 3,941 / 3.941% | 22.49% |
| Stronghold discovery | 1,097 / 1.097% | 3.93% |
| Outpost inventory | 943 / 0.943% | 0.64% |
| Nether initialization/inventory | 481 / 0.481% | 0.28% |
| Remaining Overworld inventories | 403 / 0.403% | 6.26% |
| Center-search stage entered | 11 / 0.011% | 0.08% |
| Winning evidence reconstruction | 0 | 0% |
| Unattributed evaluation time | — | 1.05% |

Raw preflight rejected **60.318%**, not 91%, on this cohort. Initialization plus the two Mansion stages account for about **64.38%** of the measured worker elapsed time. Mansion-related work is still the largest group, but the supplied stage percentages and entry rates should not be used as verified facts for this revision.

Timers perturb execution, and summed worker elapsed time includes descheduling. These are **not production wall-time fractions or hardware CPU-cycle measurements**. The stage counts are stronger evidence than the timing percentages. The 50 ns/input preflight claim is not supported by this measurement; the instrumented elapsed average was about 30.8 microseconds/input, which should not itself be substituted as a portable CPU-cost claim.

### Positive-path cost is different

A labeled synthetic fixture exercised actual native evaluation, record preparation, SQLite persistence, and stop/resume:

- Stop after 3, resume the remaining 5: **8 total committed; 8 saved candidates; 0 terrain tasks**.
- Across eight candidates: native calls 18.13 ms; record construction 281.15 ms; preparation 46.41 ms; commits 14.64 ms.
- Record construction was about **35.1 ms per retained candidate** in this small fixture experiment. This is not a natural survivor-frequency estimate.

`native_records.build_record` currently routes dynamic records through `ReplayProvider` and `evaluate_dynamic_seed`. Therefore the claim that Python work is effectively eliminated is too broad. At rare survivor rates this cost may be insignificant overall; measure it separately before adding complexity.

### Efficient next steps

1. Fix correctness and launch-policy issues first; changing to cheaper incorrect predicates is not an optimization.
2. Keep existing C/OpenMP, bulk NumPy dispatch, bounded ownership, WAL/FULL, and late spatial scoring. The observed data does not justify a rewrite, GPU port, new service, or reduced durability.
3. Profile the corrected production build on several deterministic cohorts, with separately reported candidate density. Keep source/build/policy hashes and distinguish worker time from durable wall time.
4. Investigate repeated Mansion-related sampling and preflight region work only where a measured redundant calculation exists. Preserve full64 biome seeding and the exact mandatory Dark Forest witness rule. Any low32 reuse must be limited to proven low32 placement computations.
5. If retained-record work becomes material, encode the already computed native evidence directly using existing record helpers; keep independent reference recomputation in focused verification. Do not add a second elaborate caching layer to hide repeated reconstruction.
6. Check optimization candidates with independent positive selections, boundary cases, and reject receipts. All-reject outcome equality alone cannot prove survivor scoring equivalence.

Artifacts: [measurements.json](measurements.json), [profile-results.json](profile-results.json), [measure.py](measure.py), [profile.py](profile.py), [build_diagnostic.py](build_diagnostic.py).

## 3. Verification and scope

| Check | Result |
|---|---|
| Full Python suite | **1,083 passed, 2 failed**, 289.49 seconds |
| Web build | Passed |
| Web lint | Passed |
| Fresh isolated serial native build | Built and loaded successfully |
| Existing optimized native artifact | Extension/runtime identity checked; recorded native source inputs matched current files |
| Vectorized seed sequence | 16 parity cases passed, including indices near 2^53, 2^63, and 2^64 and varied run keys |
| Default positive fixture | Native record path completed; evidence captured |
| Positive stop/resume | 3 + 5 inputs committed exactly once; 8 candidates; no terrain tasks |
| Targeted correctness probes | F1–F5 and F8 evidence captured; UI/docs gaps traced to current source |

The two suite failures need accurate disposition:

1. `test_cli_default_and_all_use_blueprint_active_variants` still expects the old `['v1']` terrain default. The current v2 `[]` default is intended. Update the test; do not restore terrain screening to make it pass.
2. `test_candidate_canonical_ranking_and_tristate_terrain` builds a minimal database without `meta`. `leaderboard.order_for` now queries `meta`, and the web query catches the resulting database error and returns no candidates. Decide whether such a schema is supported; either use a valid store fixture or add the explicit supported-schema fallback. This is not evidence that normal RealmStore databases lack `meta`.

Logs: [pytest.log](pytest.log), [web-build.log](web-build.log), [web-lint.log](web-lint.log), [native-build.log](native-build.log). Other evidence: [probe-results.json](probe-results.json), [probe.py](probe.py), [positive-fixture.json](positive-fixture.json).

This is a repository/system audit, not generated-world certification. No BDS world was launched, actual portal safety/loot/resource quantities were not verified, and no natural survivor was found in the measured cohort. Existing tests cover substantially more cases than the new probes, but passing them is not proof of complete Bedrock predictor recall, exhaustive global center optimality, or absence of further defects. No new P0 was demonstrated.

## 4. Repair and acceptance order

1. **Fix F1–F4:** scenic layer, web v2 launch/defaults, NumPy boundary validation, configured-target consistency. Rebuild native artifacts after native changes.
2. **Fix F5 and canonical ranking:** persist evidence, independent selected-window rescore, fail-closed variant errors, additive component labeling, exact tie ordering and radial accumulation convention.
3. **Finish F6 and F7:** existing player views, bounded pagination, honest inspection states, accurate README/blueprint, and evidence-linked completion status.
4. **Close the two test failures for the correct reasons.** Add focused regressions that fail before the corresponding fix; repeat the affected native/Python/UI paths, then the complete suite for release.
5. **Run a small positive end-to-end acceptance case** through launch/configuration, native selection, persistence, resume, rescore, export, and UI retrieval. Include scenic +20, three deficits, a custom target, variant evidence, and more than 250 retained rows across suitable fixtures. Do not claim that one synthetic seed proves every combination.
6. **Re-measure corrected production performance.** Publish exact cohorts/build identities and candidate counts. Mark prior v2 result rankings as affected where F1 could have changed the selected center; do not silently resume under a changed computation identity.

No speculative redesign is needed to complete these repairs.
