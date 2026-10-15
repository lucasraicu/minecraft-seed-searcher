# Review of the dynamic baseline integration

Reviewed 2026-10-14 against pending changes after `63728a3`. The active CLI and website now implement the approved sliding 1664/832 predictor policy. Historical 2048 profiles and terrain-enabled source remain accessible. This is an implementation and measurement review; generated structures, portal rooms, loot and first-player spawn are not certified by sparse predictor witnesses.

## Approved behavior

- Overworld macro bounds `[-2000,2000)`, playable window 1664; center in ±1168. Nether window 832 centered at exact C/8.
- Mandatory Mansion, Stronghold, Monument, Outpost, Fortress and Bastion categories; flexible deficits consume one unit per category, B≤2.
- Exact event cells, weighted captured-start centroid, constrained 16/8 snapping, 13 Overworld and five Nether sampled families.
- Resolved one-time third/fourth milestones, repeating scalers, optional inventories, hub cap and stable four-level ranking.
- Baseline-only website with marine viability, larger ranges, starting indices, identity-checked resume and evidence-scoped spawn metrics. No active terrain-height or river filter.
- Real owned bounded surface verification replaces fabricated BDS accuracy/portal certificates. Failure never promotes a candidate; partial point evidence remains partial.

## File-by-file green lights

All rows below are approved within the stated scope after the final validation results recorded below. Local databases, generated binaries, raw profiles and the large clipboard bundle are excluded from the source push.

| File | Review disposition |
| --- | --- |
| `MASTER_SEED_BLUEPRINT.md` | Resolved half-open geometry, centroid/grid rules, one-time milestones and distinction between predictor design and actual generated evidence. |
| `config/realm.yaml` | Validated active dynamic configuration or explicit historical snapshot; no silent migration of old checkpoints. |
| `native/blueprint_batch.h` | Dynamic policy ABI and dispatch with validation and historical engine compatibility. |
| `native/blueprint_batch.inc` | Dynamic policy ABI and dispatch with validation and historical engine compatibility. |
| `native/bridge.c` | Expose pinned Igloo basement PRNG prediction without claiming generated basement evidence. |
| `native/bridge.h` | Expose pinned Igloo basement PRNG prediction without claiming generated basement evidence. |
| `native/filters.inc` | Shared raw Fortress/Bastion placement helper; biome-viability semantics retained. |
| `scripts/build_blueprint_batch.py` | Versioned dynamic source identity, conservative raw-preflight build switch, native-target/LTO/PGO validation and source-specific profile manifest. |
| `scripts/merge_runs.py` | Remove duplicate transaction writes while preserving initialized aggregate identity and corrected conflict/retry behavior. |
| `scripts/tune_machine.py` | Use current dynamic policy; distinguish detected CPUs from supported native-thread cap and enable reachable high-core settings. |
| `src/seed_search/backend.py` | Expose pinned Igloo basement PRNG prediction without claiming generated basement evidence. |
| `src/seed_search/realm/blueprint.py` | Independent dynamic qualification/scoring, optional inventories and exact named milestones; preserve historical formulas. |
| `src/seed_search/realm/capabilities.py` | Include dynamic source units in computation identity and retain explicit predictor limitations. |
| `src/seed_search/realm/cli.py` | Validated dynamic default, mandatory/flexible counts, fixed floors and versioned historical policies. |
| `src/seed_search/realm/coastal.py` | Preserve optional historical terrain behavior while removing river requirements from the active baseline; scope spawn evidence honestly. |
| `src/seed_search/realm/config.py` | Validated dynamic default, mandatory/flexible counts, fixed floors and versioned historical policies. |
| `src/seed_search/realm/leaderboard.py` | Four-level dynamic ranking with historical policy order retained. |
| `src/seed_search/realm/marine.py` | Preserve optional historical terrain behavior while removing river requirements from the active baseline; scope spawn evidence honestly. |
| `src/seed_search/realm/native_batch.py` | Dynamic ABI, owned replay evidence and policy-specific record encoding; semantic parity excludes operational cache counters. |
| `src/seed_search/realm/native_encoding.py` | Dynamic ABI, owned replay evidence and policy-specific record encoding; semantic parity excludes operational cache counters. |
| `src/seed_search/realm/native_records.py` | Dynamic ABI, owned replay evidence and policy-specific record encoding; semantic parity excludes operational cache counters. |
| `src/seed_search/realm/reports.py` | Policy-aware rescoring without losing dynamic inventories, geometry or ranking. |
| `src/seed_search/realm/spawn.py` | Preserve optional historical terrain behavior while removing river requirements from the active baseline; scope spawn evidence honestly. |
| `src/seed_search/web/server.py` | Current policy/build, large ranges and exact starting indices, saved-run ownership/resume, biome-only shifted maps, exact spawn distances and real bounded surface-verification subprocess. Removed synthetic BDS certificates. |
| `tests/test_commit_review.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `tests/test_realm_compact_contract.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `tests/test_realm_inclusive_terrain.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `tests/test_river_highway.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `tests/test_two_group_config.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `tests/test_web_server_evidence.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `tests/test_web_server_hardening.py` | Regression expectations and boundaries for the explicit current policy, with historical-policy coverage retained. |
| `web-ui/src/App.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/components/CandidateFeed.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/components/FilterSidebar.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/components/FunnelModal.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/components/MapCanvas.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/components/SeedDetailModal.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/components/TelemetryBar.tsx` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/constants/structures.ts` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/mockData.ts` | Remove fabricated initial candidates; initial configuration derives from generated current policy. |
| `web-ui/src/types.ts` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/utils/probability.ts` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `native/blueprint_dynamic.inc` | Native event-cell selector, hard floors/category deficits, exact sampled palettes, shared conservative raw culling and complete survivor inventories. |
| `src/seed_search/realm/dynamic.py` | Independent complete-inventory center enumeration, rational Nether bounds, constrained snapping, palette prefixes, hub and radial metrics. |
| `config/realm_1664.yaml` | Validated active dynamic configuration or explicit historical snapshot; no silent migration of old checkpoints. |
| `config/realm_2048_marine.yaml` | Validated active dynamic configuration or explicit historical snapshot; no silent migration of old checkpoints. |
| `config/realm_2048_two_group.yaml` | Validated active dynamic configuration or explicit historical snapshot; no silent migration of old checkpoints. |
| `scripts/export_web_policy.py` | Preserve optional historical terrain behavior while removing river requirements from the active baseline; scope spawn evidence honestly. |
| `scripts/benchmark_dynamic_baseline.py` | Bounded compiler/OpenMP trials and counterbalanced validation; held-out seed inputs are disjoint from training and tuning. |
| `scripts/finish_dynamic_validation.py` | Bounded compiler/OpenMP trials and counterbalanced validation; held-out seed inputs are disjoint from training and tuning. |
| `scripts/validate_dynamic_holdout.py` | Bounded compiler/OpenMP trials and counterbalanced validation; held-out seed inputs are disjoint from training and tuning. |
| `web-ui/src/constants/baselinePolicy.ts` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/constants/searchProfiles.json` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/utils/geometry.ts` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |
| `web-ui/src/utils/ranking.ts` | Match deficit, score, radial and origin ordering in the displayed feed. |
| `web-ui/src/utils/spawn.ts` | Current policy metadata, baseline-only controls, geometry, evidence labels and live candidate flow; retained historical profiles. |

The added dynamic, marine, ocean-only and spawn-metric tests cover native/reference/replay agreement, bounds, floors and scoring, malformed policy rejection, UI metadata/ranking and honest verification ownership. External Gemini deliverables are preserved as review snapshots under `reviews/gemini`; corrections and accepted/rejected claims are recorded in `reviews/CODEX_INTEGRATION_REVIEW.md`. They are not treated as independent runtime certificates.

## Validation and measurement

- Full Python regression suite: **1023 passed in 293.59 seconds**.
- Frontend lint and production TypeScript/Vite build: passed, including the final responsive header fix. Live browser inspection confirmed sweep buttons fit the current viewport, dynamic profile defaults are visible, historical candidates remain labelled and telemetry resolves from the real backend.
- Packaged serial blueprint and installed private OpenMP/PGO builds: rebuilt successfully. Adopted private build source/profile identity validation passed.
- Final independent held-out adoption: five counterbalanced 100,000-input pairs, **500,000 distinct seeds**, matching persisted all-input decision receipts/candidate digests. Optimized durable median **33,710 seeds/sec** versus control **6,037/sec**, at their respective reviewed thread settings. Cumulative benchmark budget **1025.0 seconds / 17.08 minutes**.
- Installed-build checkpoint/resume smoke: exactly eight inputs committed, then resumed to sixteen with two receipts and no duplicate saved ranges.
- Live website/static/API/default-build, shifted 1664 biome map and invalid-map-center rejection: passed. Height remains absent; no production sweep was launched. The prior server's completed 460,010,030-input run was preserved before restarting the server with current code.
- Gemini independent geometry checks: exhaustive internal checks plus **38/38** fixtures. Independent scoring checker: **104/104**; production formula/policy matches **96** explicit qualification and **78** passing numeric score fixtures. Allocator: **92 tests passed** and generated YAML/CLI dry-run succeeded with zero inputs computed.
- Staged whitespace validation passed. Local generated databases, binaries, profiles and clipboard bundle are excluded from this source push.

Final throughput evidence, build hashes, compiler choices and scope are recorded in `DYNAMIC_BASELINE_BENCHMARK_RESULTS.md` and `reviews/dynamic_benchmark_summary.json`. An early validation cohort was excluded because adjacent run keys overlap under the index permutation; adoption uses a distant disjoint key and compares persisted decisions for every input. The build/source/config/UI metadata and positive native/reference/replay fixtures pass; this green light is for the defined predictor sweep and does not certify actual generated worlds.

## Limits retained explicitly

The bounded optimization comparison does not prove universal CPU optimality. Natural held-out cohorts contain no positive survivors, so synthetic positive fixtures and independent geometry/scoring checks remain essential. Known model/Stronghold recall limitations and lack of a Bedrock client remain; the surface provider does not certify complete structure generation, portal rooms, loot or actual initial-player spawn. Joint survivor probability and cluster throughput projections remain uncalibrated.

The saved terrain-enabled source is `saved/terrain-enabled-ui` at `63728a35184be99be54ddde78cbe6aedeceea371`. Old checkpoints retain original policy/build identity and cannot silently resume under the new default.
