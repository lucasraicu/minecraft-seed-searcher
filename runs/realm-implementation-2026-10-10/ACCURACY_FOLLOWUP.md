# Accuracy and recovery follow-up — 10 October 2026

The full migration goal remains active and unfinished. This batch changes authoritative code, deterministic controls and bounded actual-generation evidence; it does not establish full Bedrock Realm certification or a new seed throughput figure.

## Implemented changes

- Terrain checkpoints now include native binary/wrapper/build or explicitly declared custom-provider identity before skipping completed tasks. Historical unpinned or changed terrain tasks cannot be silently adopted. Source/data interpretation changes invalidate BDS observation identity while preserving history.
- Scoring uses durable, bounded revisions with transactional cursors. Interrupted revisions resume under the persisted policy, and ranking/generation reject mixed revisions. CLI `rescore --run <run> --resume` requires no original policy file. Completed same-policy rescoring includes newly added rows. Atomic export generations preserve previous complete outputs; multi-file consumers must pin `results/current` once.
- Selected verification advances past cached records, offers explicit cached review and failed retries, and separates random new-attempt/cached-review inclusion probabilities. Actual analysis requests include complete V1/V2 evaluator halos; tile limits defer oversized requests rather than silently truncate geometry.
- BDS cleanup has bounded graceful/stop/remove paths, preserves original errors and refuses subsequent launches while previous container state is unresolved. Snapshots require confirmed clean shutdown. Runtime success is proven below; daemon-failure fallback tests remain mocked.
- Seed-level raw and viable Stronghold/Fortress observations persist even without anchors. Discovery tasks commit with seed coverage, support bounded legacy backfill and explicit lease recovery, and stay unresolved despite positive predictions. Completing recovery serializes before reading evidence/state; conflicting immutable evidence cannot race to overwrite. Completion validates supplied/trusted evidence, not an implemented exhaustive actual provider, and does not automatically insert recovered anchors.
- Biome/bonus uncertainty records observed and possible wooded families and score intervals. Predictive-model observations do not lower-bound actual generated scores. Unknown biome IDs prevent confirmed wooded absence, even under otherwise exhaustive observations. Rescore refreshes uncertainty. Surface-aware actual sampling/refinement remains outstanding.
- Four substantial disconnected hill/spike arrangements reproduced V2 false enclosure. Configurable engineering defaults require same-component arc runs of at least four bearings and tangential/radial aspect at least two. Separate arcs, a 90-degree pass and jagged interiors still qualify; agreed relative relief, ridge distances and ray thresholds remain unchanged. Old configs are accepted without mutation, and old terrain identities are not adopted. Natural-world calibration of the new defaults remains outstanding.
- Current actual-column-v2 measures contiguous primary/overlay water block cells, treats waterlogged solids as obstructions, records snow/ice cover and hidden substrate, and retains missing/throwing getter uncertainty. Natural ground remains unverified. Ambiguous and legacy overlay-uninspected columns are not known geometry. Continuous fractional water heights are not asserted.
- Formation calibration (`calibration --run <run>`) independently reports V1/V2 confusion matrices, geometry-score error and tied-rank correlation only for complete verified actual geometry. Missing, partial and mismatched evidence never becomes negative truth. Saved actual raster provenance is checked; selected-cohort results are explicitly not population estimates. No actual complete formation dataset is yet available.

## Runtime evidence for current column policy

Both tests reuse seed `-1001562501133105644`, official BDS `1.26.52.3`, pinned image/settings, four container CPUs/six GiB, no connected players and one disposable world per bounded request. They do not modify baseline records or add production seed coverage. Snapshot markers are restored before shutdown and reads use stopped-world copies.

| Request | Wall time | Sample columns | Open-water columns | Saved/API block checks | Overlay flag checks | Unknown/mismatch | Requested chunks |
|---|---:|---:|---:|---:|---:|---:|---:|
| [1508,1540) × [948,980), spacing 8 | 17.222 s | 16 | 0 | 20/20 | 20/20 | 0 | 9/9 |
| [1612,1644) × [1004,1036), spacing 8 | 11.278 s | 16 | 5 | 62/62 | 57/57 | 0 | 9/9 |

Both same-tick native/reference scans matched, subsequent settling comparisons changed zero columns, every sampled waterlogging getter was readable, and shutdown was graceful with exit 0 and confirmed stopped container state. Both rasters correctly remain PARTIAL because natural-ground/structure provenance and unsampled connectivity are unresolved. There were zero positive overlay-water probes; this proves getter/readback behavior at the selected primary-water/land cells, not positive waterlogged vegetation or solids. Positive waterlogging, snow/ice and elevated-lake runtime fixtures remain required. These small elapsed times are not whole-formation generation cost estimates.

Artifacts: `actual-column-policy-smoke/observation.json`, `actual-column-policy-smoke/summary.json`, `actual-column-water-smoke/observation.json`, `actual-column-water-smoke/summary.json`, their logs and stopped-world snapshots.

## Test evidence

- Combined Realm suite before the final recovery-concurrency/mapping controls: 261 passed in 17.99 seconds.
- Full repository suite at that intermediate source: 407 passed in 120.46 seconds.
- Final-source full repository regression: **410 passed in 116.53 seconds**, exit 0. Authoritative output: `accuracy-followup-final-tests.log`. This includes the recovery race and unknown-biome controls.
- Focused deterministic controls use synthetic terrain, JavaScriptCore execution of the actual pure column policy, SQLite fault/recovery cases and mocked Docker failures. They are not rare-terrain actual-world reference fixtures. Full repository tests retain existing native/backend regressions; no new large seed benchmark ran.

## Remaining work

Actual surface biome generation/refinement; full Stronghold discovery recall and a supported recovery executor; authoritative required Overworld/Nether structure evidence; positive liquid/cover runtime fixtures and natural-ground structure masks; complete actual V1/V2 positive/negative formations and population false-negative calibration; resumable remaining terrain centers/refinement/halo units; overlapping generated-world reuse/final Nether cache; meaningful accessibility and width-uncertainty metrics; arbitrary crash/cancellation boundaries; final capability/performance report consolidation.

The installed Docker/BDS runtime works for the bounded checks above. Complete terrain/structure verification remains the accuracy gate. Existing native MC_26_50 remains an explicitly unvalidated predictor for target Bedrock 26.52; no large-scale speed or exactness claim is added by this batch.

Structure automation investigation: official `/locate` reports the nearest structure rather than exhaustive regional presence, and the documented Script API CommandResult exposes successCount rather than coordinates. A successful locate or a missing/outside nearest result does not certify generated structures or regional absence. See Microsoft's [locate documentation](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/commandsreference/examples/commands/locate?view=minecraft-bedrock-stable) and [CommandResult reference](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/commandresult?view=minecraft-bedrock-stable). An independent supported generated-structure evidence route still needs proof.
