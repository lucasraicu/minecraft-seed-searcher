# Remaining fixes and verification work — 10 October 2026

This is a read-only audit backlog, not a completion claim. No additional seed benchmark, native timing, BDS launch, or implementation change was performed during the audit. Findings come from current source, existing test definitions, and retained runtime evidence. Newly identified adverse paths still need focused reproduction tests before a fix is claimed verified.

The user's additional fixes are deferred at their request; the requested deliverable is the list below. The goal remains active and unfinished. No completion notification was sent.

## Priority 1 — correctness and result integrity

1. **Correct V1 whole-formation border handling.** A bounded wide lake can have a fully observed connected component but no opposite shore within the fixed ray search radius. The current code can fall back to a 100-block belt and still mark the footprint complete. Add a wide-lake control and prevent a truncated surrounding-water footprint from being classified within the Realm. Explicitly distinguish the complete relevant lake enclosure from an open-ocean minimum belt and unrelated water arms.
2. **Apply one scoring policy to predicted and actual results.** Actual evaluation currently uses hardcoded 80/10/10 weights, can use predicted biome fit without explicit component provenance, and does not consistently apply saved rescore policy. Ranking and rescoring need to preserve and use independent actual/verified scores rather than overwrite or ignore them.
3. **Reserve BDS attempts atomically.** Persisted budget read/increment occurs before the extraction lock. Concurrent commands can reserve the same counter and exceed the budget. Reserve unique attempt IDs and enforce the cap transactionally; test competing processes.
4. **Complete cache identity and refresh rules.** Include native binary/backend/provider identity in terrain task provenance and verification/raster interpretation in observation provenance. Actual failed/unknown windows must remain retryable even when they omit `metadata.source='actual'`. Preserve exact-coordinate native reuse without reusing a stale actual observation.
5. **Make rescore and export interruption states explicit.** Rescore commits individual records before saving its global policy, allowing mixed revisions after interruption. Persist a target revision, resume or complete it, and prevent ambiguous ranking. Write exports through temporary files and publish complete sets atomically.
6. **Validate memory accounting and worker results.** Reject negative/nonfinite Docker reserve, define monitor-failure behavior, and validate returned seeds against their assigned index/sequence before coverage commits. Extend cancellation handling across sampling, dispatch and commit boundaries. Existing coverage transactions already protect committed results; broad graceful-shutdown claims need stronger evidence.

## Priority 2 — complete the intended workflow

7. **Preserve full discovery evidence and recovery work.** Save seed-level Stronghold/Fortress raw and viable observations even when there are no anchors. Record unresolved coverage/recovery tasks rather than only counters. Known incomplete Stronghold enumeration needs a supported recovery route.
8. **Use actual surface biome observations and quantitative uncertainty.** Fixed Y=63 predictions are provisional. Add surface-aware sampling and refinement, retain observed/possible wooded-family counts, and propagate unknown family/optional-structure coverage into baseline and variant score intervals.
9. **Strengthen mountain enclosure controls.** Add substantial disconnected hill/spike arrangements and verify that the intended ridge continuity and angular-gap measurements distinguish them from a meaningful mountain enclosure. Preserve jagged/steep V2 interiors and avoid a flat-floor gate.
10. **Make verification scheduling advance and retries accessible.** Skip or separately review already cached top records, allow explicit CLI retry of failed attempts, and avoid charging cached picks against remaining new-attempt selection slots. Guarantee container cleanup with bounded timeouts and stop/remove fallback.
11. **Generate the complete required analysis region and reuse BDS data.** V2 needs its ridge-search/support halo, not merely a measured footprint plus one sample cell. Reuse overlapping generated regions across V1/V2, preserve coverage and stability, and cache final Nether evidence by seed/Stronghold/settings/region. Never infer complete geometry from a partial region.
12. **Correct calibration and manual-cave failure/refinement paths.** Calibration must use requested, known, stable lattice cells rather than raw square-tile overscan. Explicit cave checks should retain failure artifacts and refine bounded uncertain/missing regions as well as positives; they must remain manual and score-neutral.

## Accuracy gates — required evidence, not speed optimizations

13. **Validate actual ground and water semantics.** Implement/verify natural ground excluding structures, waterlogging/overlay handling, ice/snow policy, water elevation and depth. Existing actual rasters correctly remain PARTIAL. Add matching-runtime forest, river, mountain, elevated-lake, negative-coordinate and chunk-edge controls.
14. **Integrate authoritative required-structure and Nether evidence.** Validate the five required Overworld structures, required surface families, Fortress and Bastion under pinned Bedrock generation. Final Nether is currently trusted-import validation rather than an automatic BDS structure scanner. Unsupported APIs and missing predictions cannot establish absence.
15. **Calibrate complete V1/V2 formations.** Obtain whole-region positive and negative actual controls, including narrow bridges and real mountain enclosures. Compare island closure, ridge relief, rankings, precision/recall and false negatives on a supported sampling design. The selected 256-column check's 71 land/water disagreements are local evidence, not population recall.
16. **Finish final validation and reporting after fixes.** Run focused regressions for these cases and the final relevant suite; update phase status, exact capability limits and consolidated results. Use existing performance evidence. No new 10,000/100,000/million-input benchmark is required to implement these correctness fixes; post-fix 100,000-input throughput must remain labeled unmeasured unless later requested.

## Existing evidence retained

- Full pre-overlap-cache suite: 232 passed. Focused cache/terrain suite: 40 passed, including nine new cache tests. These do not cover all new findings above.
- Fresh 64-input native interruption/resume preserved all 172 anchors identically across worker counts.
- Post-fix baseline: 16.876 seeds/s at one worker and 155.375 at 30 on the same 1,000 inputs; 204.936 at 30 workers on 10,000 inputs. The earlier 100,000-input run predates the reporting/postprocessing fixes.
- BDS selected 128-square check: 81/81 chunks finalized, 568/568 saved-block comparisons matched, stable samples, baseline unchanged. Natural-ground provenance remains PARTIAL; full Realm certification is not established.

Detailed source/test/runtime evidence is in `AUDIT_BASELINE_STORAGE.md`, `AUDIT_TERRAIN.md`, and `AUDIT_BDS_VERIFICATION.md` beside this file. Historical artifacts and native/vendor inputs present before this goal remain preserved.

## Follow-up status — active goal continuation

This list above records the audit findings. Subsequent implementation has resumed under the goal continuation; the full goal remains unfinished.

- **#1 reproduced and corrected in sampled geometry:** no complete border claim for a closed lake whose enclosing rays do not reach opposite shores. Relevant lower-bound overflow is retained, and uncertainty remains explicit. Whole actual-formation calibration remains #15.
- **#2 implemented and tested:** shared scoring policy, saved CLI weights, independent nested score channels, provenance-aware ranking and generation-free rescore preservation. The real synthetic actual-biome propagation regression and both present/missing biome CLI paths pass.
- **#3 implemented and tested:** atomic persisted budget reservations and unique per-call attempt IDs, including concurrent connections and consumed interrupted reservations. In-flight same-observation dedup remains a performance improvement.
- **#4 partly implemented:** unknown/failed provider windows retry rather than becoming stale RasterCache hits, and verification/raster interpretation hashes invalidate stale BDS observations. Native/custom provider identity in terrain-task resume remains open.
- **#6 partly implemented:** finite/nonnegative memory validation, stop/drain on monitor loss and worker-seed/assigned-sequence validation. Arbitrary-boundary cancellation remains open.
- **#12 implemented at function level:** stable known requested-lattice calibration and bounded manual cave uncertainty refinement/failure reports. Actual cave fixture diversity and broader generation validation remain open.
- No new native seed benchmark or BDS launch ran in this batch. The combined Realm suite passed **145 tests in 7.74 seconds** before the final scoring-edge review. Earlier benchmark/BDS artifacts are preserved.

Full exact Bedrock Realm certification, complete V1/V2 actual fixtures and the remaining backlog are not complete.

Final-source full regression for this follow-up: **290 passed in 106.68 seconds**, exit 0. This confirms the covered correctness cases, not full actual Realm certification. Source/test hashes match correctness-followup-manifest.json.

## Accuracy/recovery continuation status

- **#4 implemented at checkpoint/cache level:** terrain provider binary/wrapper/build identity is pinned before skipping completed tasks. Custom factories require declared static JSON identity; changed or historically unpinned tasks are not silently adopted.
- **#5 implemented:** bounded durable score revisions resume under the saved policy; ranking/generation reject incomplete revisions. Atomic export generations publish one complete set; consumers reading multiple files must pin a generation. `rescore --resume` needs no external policy file.
- **#7 partly implemented:** complete raw/viable seed-level discovery observations persist even without anchors; separate atomic recovery tasks and bounded explicit legacy backfill retain unresolved recall. Completion validates trusted supplied evidence under a serialized write lock, not an implemented authoritative enumerator. Recovered anchors are not silently inserted; executor/integration and exhaustive recall remain open.
- **#8 partly implemented:** observed/possible wooded-family and bonus intervals explicitly distinguish prediction from actual evidence, including unknown biome mappings. Rescore refreshes intervals. Actual surface-aware sampling/refinement remains open.
- **#9 implemented for deterministic controls:** broad disconnected hills/spikes reproduced false acceptance; configurable same-component arc-run/aspect checks reject them while accepting separated arcs, passes and jagged interiors. Actual-world calibration remains open.
- **#10 implemented at scheduler/cleanup level:** selection advances past cached observations, explicit cached review/failed retry separate new-attempt budgets, and conditional random probabilities are stratified. Bounded cleanup fallback and unresolved-container guard have fault controls; successful clean shutdown is also proven in two current-policy runtime smokes. Real daemon-failure controls remain unrun.
- **#11 partly implemented:** actual analysis requests include complete evaluator halos and never clip to a misleading small footprint; oversized requests remain deferred. Cross-request/variant overlapping-world reuse and final Nether caching remain open.
- **#13 partly implemented:** current column policy observes waterlogging, contiguous primary/overlay block-cell depth, snow/ice cover and support classes. Two pinned 32-square runtime smokes validate getter availability and selected primary-water/saved-overlay comparisons; positive waterlogged/ice/snow runtime fixtures, fractional fluid heights and structure/natural-ground provenance remain open.
- **#15 tooling implemented, actual dataset missing:** formation-level calibration computes independent V1/V2 confusion/rank diagnostics only from complete verified actual evidence. Partial/mismatched/unproven observations are excluded; no population accuracy is claimed. Whole actual positive/negative fixtures remain required.

See ACCURACY_FOLLOWUP.md and its test/runtime evidence. The full goal remains unfinished; no large seed benchmark was rerun.

## Surface/terrain queue continuation status

The latest batch implements fixed shared pool membership, durable center/refinement/halo work, atomic failed-attempt retry evidence, rotating pool fairness, uninitialized-work reporting and concurrent candidate patch safety. Actual surface names and explicit bounded point verification now establish sampled wooded presence independently of predictions; unknown names never prove absence. Nine controlled BDS cases validate sampled waterlogging/snow/ice interpretation and exact restoration, with retained snapshot-reader limitations. Pinned-runtime palette resolution now proves supported saved/API default-state equivalence without hiding raw differences or promoting unknowns.

Final-source tests: 560 passed in 119.03 seconds. The selected real two-point check verified Forest+Taiga presence; the selected natural 32-square check produced 16 usable surface observations and 62 consistent saved/API comparisons (56 exact + 6 individually runtime-proven). These are not whole-formation or generated-structure certification. See SURFACE_TERRAIN_QUEUE_FOLLOWUP.md. Remaining authoritative structure/discovery, full actual formation/calibration, natural ground, overlap/Nether reuse, accessibility, disk retention and broad crash gates remain open. No large seed benchmark ran.
