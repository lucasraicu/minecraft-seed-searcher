# Follow-up repository review

## Decision and scope

**The main scoring fixes are verified, but the repository is not fully clear of issues.** The default v2 path is substantially improved. Correct the campaign defaults before launching the generated large campaign, and finish the remaining rescore, result-access, and reporting fixes below.

This review covers the **uncommitted working tree on top of `233fad76fddc5667e77c27ab7e5cc83d3669a7a2`**, including the new campaign script and tests. The HEAD commit alone does not identify these changes. [starting-state.json](starting-state.json) records modified/new source hashes; [working-tree.patch](working-tree.patch) captures the tracked diff. Those source hashes remained unchanged during review. No implementation files were changed by this review.

**Verification:** 1,104 tests passed in 302.32 seconds; web build and lint passed; a fresh private serial native extension built and loaded. The current optimized extension matched its source and binary identity, and matched the fresh serial build on three positive synthetic fixtures.

## Remaining findings

### R1 — P1: Generated campaigns still default to the historical v1 policy

**Location:** `scripts/shard_campaign.py:28`, `:43`, `:398`; `config/realm_1664.yaml:209`.

The new campaign tool defaults to `config/realm_1664.yaml`, which explicitly selects `dynamic-envelope-1664-v1`, and passes `--max-misses 2`. The active agreed policy is v2 with three allowed deficient categories.

**Reproduction:** `partition_campaign()` generates four nine-billion-input shard commands. Each uses the v1 configuration and budget 2. The range partition tests pass because they check index coverage and command strings, not the resolved gameplay policy.

**Impact:** running the generated defaults spends a large campaign searching under the old scoring/eligibility contract. The fixed web default does not fix this separate entry point.

**Fix:** use the active v2 configuration by default and derive the deficit budget from it unless explicitly overridden. Keep historical v1 as an explicit option. Add a generated-command configuration/dry-run test that checks revision, budget, terrain variants, and index boundaries. Validate policy semantics before starting billions of inputs.

Evidence: `shard_defaults` in [probe-results.json](probe-results.json).

### R2 — P2: Rescoring still trusts the scenic flag and can produce contradictory saved components

**Location:** `src/seed_search/realm/reports.py:332`–`:357`.

Bastion variants are now retained and Village spread is recomputed, which fixes part of the earlier evidence gap. However:

- Scenic scoring still uses `candidate.get('scenic_bonus', 0)` instead of deriving the pair from retained Y=63 evidence. The same retained scenic/River pair still scores **344 with flag 0 and 364 with flag 20**.
- Recomputed Village-spread and treasure values update `ranking.components`, but do not update their top-level flags or witnesses. A synthetic stale record rescored to spread/treasure components of zero while retaining `village_spread_bonus=15` and `treasure_bastion=1`. The new UI reads those top-level fields, so its explanation can disagree with the total.
- Missing variant evidence still falls back to the old treasure flag. That does not establish an independently reproducible score for old records.

**Impact:** rerunning rescore does not repair scenic awards produced before the height-layer fix, and the displayed evidence may contradict recalculated scores.

**Fix:** recompute scenic pairing from retained surface samples; update component totals, flags, and witnesses together; distinguish missing evidence from evaluated absence. Do not attempt to repair historical center selection with fixed-window rescoring alone—re-evaluate the seed when recovering the correct selected center matters.

Evidence: `same_evidence_scenic_rescore` in [probe-results.json](probe-results.json), and `rescore_inconsistent_display` in [extra-results.json](extra-results.json).

### R3 — P2: Pagination only slices the first 5,000 candidates

**Location:** `src/seed_search/web/server.py:574`, `:1113`; `web-ui/src/App.tsx:114`.

The query limit increased from 250 to 5,000. The new endpoint applies offset/limit to `MANAGER.candidates`, the already-truncated list. It reports the length of that list as the total. The frontend continues to request `/api/candidates` without page controls.

**Reproduction:** with 5,001 synthetic database candidates, the manager holds 5,000, the reported total is 5,000, and the page starting at offset 5,000 is empty.

**Impact:** additional results remain in SQLite but cannot be browsed through this endpoint. Loading a much larger pool on every refresh also increases parsing and response work without implementing complete pagination.

**Fix:** query bounded pages directly from the indexed leaderboard, return the database total, validate page bounds, and wire page/cursor navigation into the UI. Preserve the complete v2 ordering and keep list payloads compact. Do not keep increasing the in-memory cutoff.

Evidence: [pagination_probe.py](pagination_probe.py), [pagination-results.json](pagination-results.json).

### R4 — P2: The merge command reports v2 winners in the old deficit-first order

**Location:** `scripts/merge_runs.py:163`.

The merge summary uses the imported historical `ORDER` constant rather than `order_for(dest)`.

**Reproduction:** two synthetic v2 candidates with identical supporting geometry:

| Candidate | Score | Deficient categories | Merge summary position | Correct v2 position |
|---|---:|---:|---:|---:|
| Seed 0 | 100 | 1 | 2 | 1 |
| Seed 1 | 50 | 0 | 1 | 2 |

**Impact:** the campaign merge command names the wrong best candidate in `top_candidates`. The stored scores and leaderboard view are intact; this finding concerns the returned summary ordering. The defect predates the new campaign helper but is directly exposed by its recommended merge workflow.

**Fix:** use the revision-aware order helper for this summary and test it against the normal v2 query. Preserve historical ordering when merging historical runs.

Evidence: `merge_rank` in [probe-results.json](probe-results.json).

### R5 — P2: The new counter cache makes long-lived checkpoint readers stale

**Location:** `src/seed_search/realm/store.py:229`.

`completed_seeds` and `counts` are cached indefinitely per `RealmStore`. External commits do not invalidate them.

**Reproduction:** open a writer and a separate reader on the same temporary run; read zero progress; commit one input through the writer; call reader status again. The reader still reports **0**, while its direct database query reports **1**.

**Impact:** long-lived consumers using `RealmStore.status()` or `get_state()` can report stale progress/counters. This probe does not demonstrate lost coverage in the current single-writer pipeline, and the web path that reads counters directly through SQLite is not affected by this particular cache.

**Fix:** keep this optimization writer-local, or invalidate reader caches when the connection's `PRAGMA data_version` changes. Include a two-connection reader-refresh regression. Preserve cache invalidation on transaction rollback.

Evidence: `cached_reader` in [probe-results.json](probe-results.json).

### R6 — P2: Spawn suggestions and optional inspection reporting remain unconnected

**Location:** `src/seed_search/web/server.py:831`; `src/seed_search/realm/blueprint.py:807`; aggregation Sections 8.1 and 8.5/B7.

The new score detail cards are implemented, including correct labeling of treasure as part of the optional subtotal. However, the generated `suggested_spawn` still does not reach the existing `spawn_stage` presentation path. Explicit End-access, portal inspection, and snow/ice evidence states from the agreed reporting scope remain unfinished.

**Impact:** players cannot see some of the agreed information even though the backend already computes a biome-based spawn suggestion.

**Fix:** expose the suggestion under its own predictive meaning; do not relabel its fixed sample Y as verified safe ground. Add inexpensive unverified/unavailable inspection states and render them in existing detail views. No automatic terrain or world generation is required.

### R7 — P2: Blueprint Section 3 still contradicts the corrected v2 scoring section

**Location:** `MASTER_SEED_BLUEPRINT.md:93`–`:110`, compared with Section 5.1.

Section 5.1 now largely matches the agreed schedules, but the current structure matrix still states:

- Second Stronghold +50 instead of +35; second Monument +30 instead of +35.
- Village bonuses at the ninth and above, and Trial Chamber bonuses at the eighth and above.
- Ancient City and temple milestones at the preferred target rather than above it.
- Uncapped salvage surplus and the old Igloo award.

The matrix is not clearly labeled as historical; it sits under the updated active three-deficit section. Section 5.1 also omits the Ruined Portal's +4 contribution from its hub description and calls the Bastion variant “verified,” although the award is predictive. The aggregation's blanket completion statement remains unchanged.

**Impact:** a future implementer could reintroduce the old behavior while following the purported current blueprint.

**Fix:** reconcile the active matrix and hub description with the actual v2 scorer; explicitly isolate any historical table. Keep predictor evidence distinct from actual-world verification. Use acceptance status that links to current verification artifacts.

## Previous findings: what is now verified

| Previous issue | Follow-up disposition |
|---|---|
| Scenic Y=0/Y=63 mix-up | **Fixed.** Actual native cache probe gives +20 for a Y=63 pair and 0 for a Y=0-only pair. |
| Web still launching v1 | **Fixed for the active web profile.** Resolved config is v2, budget 3, terrain variants empty. New campaign entry point has separate R1. |
| Unsafe ordinary NumPy dtypes | **Fixed for tested ndarray inputs.** Float64/int32 rejected; new suite covers shape, contiguity, endian, and signed/unsigned inputs. |
| Configured target parity | **Fixed in tested cases.** Raised Village, Portal, and Trial Chamber targets construct records successfully and save the resolved targets. |
| Bastion evidence/error handling | **Improved.** Variants now persist; negative prediction codes propagate. Rescore evidence handling remains R2. |
| Player score cards | **Implemented.** Remaining browsing and presentation work is R3/R6. |
| Incorrect documentation | **Partly fixed.** Remaining contradictions are R7. |
| UI binary tie ordering | **Fixed.** Previous tied-ID reproduction now agrees with binary comparison. |
| Radial accumulation order | Python now uses the intended Stronghold-first traversal and explicit accumulation; three serial/optimized positive fixtures agree. |
| Two prior suite failures | **Resolved.** Full suite now passes. |

## New native optimizations: bounded validation

The review checked the two-phase climate initialization, stack-backed single-point biome cache, new Dark Forest precheck, and Mansion/Nether co-window preflight.

- **32,000 sampled Overworld points:** two-phase initialization matched the original initialization loop; stack-cache output matched the heap-cache path. Four Y levels were included. See [climate_equivalence.c](climate_equivalence.c), [climate-equivalence.json](climate-equivalence.json).
- **103,574 raw Mansion positions over seeds 0–9,999:** 1,792 positions predicted Dark Forest at Y=63. The new necessary-condition gate rejected none of those. See [climate_probe.c](climate_probe.c), [climate-results.json](climate-results.json).
- **Optimized artifact:** source hashes and binary digest match its manifest. See [optimized-identity-check.json](optimized-identity-check.json).
- **Three positive synthetic fixtures:** the current PGO/OpenMP build with 34 threads matched the fresh serial native build's semantic records. See [extra-results.json](extra-results.json).
- **Scenic correction:** the direct native height-layer probe passes. See [scenic-results.json](scenic-results.json); its probe source is the prior audit's `native_probe.c` compiled against the current working tree.

No new native correctness failure was reproduced by these checks. Sampled equivalence is not proof of exhaustive recall across every seed, climate boundary, build, or game version. Positive fixtures bypass parts of natural discovery and cannot alone validate the new reject gate. Keep a documented derivation of the necessary climate bounds and retained differential regressions; throughput gains are not a substitute for them.

No new throughput claim is made in this review, and no BDS world was generated.

## Verification artifacts and recommended order

1. Fix **R1 before launching generated campaigns**. An explicit v2 config plus budget 3 avoids that default-selection defect meanwhile.
2. Fix **R2 and R4** so rescoring and campaign winner summaries are trustworthy.
3. Finish **R3/R5/R6** without increasing query caps or adding expensive generation work.
4. Reconcile **R7**, add focused regressions for the reproduced cases, and rerun affected checks.

Evidence scripts: [probes.py](probes.py), [pagination_probe.py](pagination_probe.py), [ranking_probe.cjs](ranking_probe.cjs). Logs: [pytest.log](pytest.log), [web-build.log](web-build.log), [web-lint.log](web-lint.log), [native-build.log](native-build.log).

The green suite establishes that existing tests pass; the reproducible findings above identify behaviors those tests currently miss.
