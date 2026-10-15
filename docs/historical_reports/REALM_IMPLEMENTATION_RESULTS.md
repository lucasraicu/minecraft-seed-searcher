# Realm seed finder implementation results — 10 October 2026

Implementation and validation remain in progress. The 100,000-input baseline benchmark, fresh resume check and selected BDS integration check have completed. The subsequent audit identified additional correctness fixes; full terrain/structure certification and population prediction accuracy remain unverified. No further large seed benchmark is required for these fixes.

## Architecture and preserved behavior

The new schema-5 Realm profile is additive. Default search, doctor, and benchmark commands use it; explicit historical schema-3/4 configurations retain their existing interface. The pre-change dirty checkout was preserved in a source archive and manifest before editing. Historical October 8 exports are reference artifacts, not the new policy.

The pipeline is discovery → required structure predictions → required wooded families → inexpensive bonuses → persistent baseline pool → independent V1/V2 terrain observations → selected actual BDS observations → final Nether evidence. Automatic cave diversity and V3 are removed from the new scope. The cave checker requires an explicit command.

Discovery uses half-open 5,000-square bounds around the origin independently in the Overworld and Nether. Every discovered Stronghold has its own 2,688-square Overworld Realm and mandatory evaluation region, including areas outside discovery. Final Nether evaluation is a 1,024-square around the exact fractional Stronghold/8 center. Terrain centers are unrestricted within the Realm; sampling halos can extend outside it. Whole-formation border fit is independent of terrain quality, and outside/unknown formations remain saved with expansion information.

All five required Overworld structures and initial Nether Fortress remain eligibility conditions. Two of Forest, Taiga, Jungle, Dark/Pale, and Cherry are required. Additional wooded-family bonuses are 0/5/10/15 for 2/3/4/5 families. Surface and optional structure bonuses are configurable and can be recomputed from saved evidence. Savanna always contributes zero and never rejects a record. Neither Ocean nor Mountains is a baseline requirement.

V1 evaluates sampled island/water components, effective diameter, enclosure, water width and usable area. V2 measures continuous ridges and relative relief around an interior that may be rough, steep, or jagged; there is no flat-floor eligibility threshold or floor score. Both variants use the same saved baseline pool and independent center/refinement budgets. Cheap 2D nomination prioritizes expensive density work but cannot certify absence. Approximate low scores preserve every baseline survivor and closest matches.

## Implementation locations

- [Realm configuration](config/realm.yaml), [validation](src/seed_search/realm/config.py), [capability report](src/seed_search/realm/capabilities.py), and [bounds](src/seed_search/realm/bounds.py).
- [Baseline evaluator](src/seed_search/realm/baseline.py) and [biome classification](src/seed_search/realm/biomes.py).
- [SQLite storage](src/seed_search/realm/store.py) and [parallel range runner](src/seed_search/realm/runner.py).
- [Shared terrain raster](src/seed_search/realm/raster.py), [independent geometry detectors](src/seed_search/realm/terrain.py), [reports and rescoring](src/seed_search/realm/reports.py).
- [Selected BDS adapter](src/seed_search/realm/verification.py), bundled BDS extraction tools, [manual cave checker](src/seed_search/realm/caves.py), and [CLI](src/seed_search/realm/cli.py).
- Legacy CLI/configuration dispatch and automatic cave scoring were adjusted; native and vendor changes already present before this goal were preserved.

## Performance evidence

The equivalent one-worker, 128-input paired baseline comparison improved **6.84 → 15.35 seeds/s (2.25×)**. It compares identical prediction qualification and qualified-record scores. The original full landscape trace is a different workload and is not used for this speedup claim.

The same 1,000-input worker series measured about **9.7×** scaling from one worker to 30. The larger repeated 10,000-input series measured **188.20 seeds/s at 30 workers** and **187.71 at 36**, effectively tied in a single ordered trial. All 36 workers contributed in the 10,000-input case. The original paired baseline benchmark used one worker, not 30.

See [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md) for the frozen reference, five measured bottlenecks, stage costs, allocation limits, and equivalent comparison; [SCALING.md](runs/realm-implementation-2026-10-10/SCALING.md) and [storage/worker evidence](runs/realm-implementation-2026-10-10/STORAGE_WORKERS.md) record scaling, memory, provenance, and actual coverage.

The 100,000-input follow-up completed in **972.144 seconds, 102.865 seeds/s at 30 workers**. It includes process startup, baseline prediction, result serialization and checkpointing, and excludes terrain and BDS. Its growing database exposed repeated progress aggregation overhead. Progress aggregation is now throttled and variant-task counts have a covering index; biome postprocessing was also corrected to avoid redundant work.

After those fixes, the matched 1,000-input comparison measured **16.876 seeds/s at one worker and 155.375 at 30 workers (9.207× scaling)**, with identical pool hashes and counters. A subsequently completed 10,000-input run measured **204.936 seeds/s at 30 workers**, with 2.593 GiB sampled scanner peak RSS. There is **no post-fix 100,000-input throughput measurement**. The different batch sizes do not establish a same-workload speedup. Further large seed benchmarks were stopped at the user's request; no million- or billion-input achievement is asserted.

The 100,000-input range contains **100,000 distinct full-64-bit inputs**, not the sum of repeated worker trials. It saved 263,075 seed/Stronghold pairs: **153,394 PREDICTED and 109,681 PENDING**. Its counters record 109,047 Ancient City pending pairs, 311 Village pending pairs, 5,074 unresolved Stronghold discoveries, and **zero confirmed actual-generation rejections**. The broad initial Fortress prediction was positive for all 100,000 inputs. These are prediction/unknown counts, not verified survival statistics. The original database occupied 3,346,128,896 bytes (3.116 GiB) and sampled scanner peak RSS was 4.152 GiB, excluding the separately reserved Docker VM allocation.

## Reproducibility and data retention

Deterministic full-64-bit input ranges support sequential or bijective permuted enumeration. Workers have independent, nonoverlapping leases with one numerical thread per process and bounded outstanding batches. Parent-owned batched SQLite transactions commit covered ranges and all Stronghold records together. Interrupted/crashed leases are recoverable, completed ranges are not rescanned, and seed/Stronghold IDs deduplicate results. Worker count can change on resume; incompatible generation or computation identity changes are rejected.

Eight raw-MT structure placement families internally use low 32 seed bits. Viability and biome inputs retain full 64 bits; full seed values and this aliasing limitation are recorded. Repeating the same interval with different worker counts increases evaluations, not distinct coverage.

Predicted-qualified and pending records are both retained. Unsupported features and coarse misses do not establish actual absence. Terrain observations, independent rankings, raw geometry metrics, final Nether evidence, cache identities, and rescoring policy are separate from baseline eligibility.

A fresh native interruption/resume control stopped after 13 inputs, resumed the remaining 51 with a different worker count, and compared against an uninterrupted one-worker run. All **172 anchors (109 PREDICTED, 63 PENDING)** and counters matched, with no duplicate candidate IDs. Export and generation-free rescoring passed. This is a 64-input recovery control, not extra distinct production coverage.

## Actual Bedrock generation evidence and limits

The installed Intel Docker setup pins official **BDS 1.26.52.3** and its exact image, ZIP, extraction tools, seed and world settings. The existing compiled **MC_26_50** backend remains an explicitly labeled predictor. It does not become an exact 26.52 generator through this integration.

No graphical Minecraft or connected player is required for the proven bounded Script API chunk-loading workflow. One selected disposable world uses 4 CPUs and a 6-GiB container budget in an 8-GiB Docker VM. Successful bounded tests preserve negative coordinates and signed high-bit seeds, compare direct API blocks against stopped-world data, verify chunk coverage, and shut down cleanly. Detailed measurements and retained evidence are in [BDS_INTEGRATION.md](runs/realm-implementation-2026-10-10/BDS_INTEGRATION.md).

The integrated sixteen-column off-grid smoke had **64/64 snapshot/API block comparisons** match and **9/9 requested chunks** finalized, with zero changes across settling passes. Its density-predicted height MAE was **2.3125 blocks**, maximum error **7**, and exposed-water proxy agreement **16/16**. These columns are one small ocean sample; they do not measure general prediction accuracy or rare-formation recall.

A later selected V1-center check generated a **128×128 region at spacing 8 in 20.898 seconds**: 81/81 requested chunks finalized, 568/568 stopped-world/API block comparisons matched, and repeated settling samples agreed. The baseline was unchanged and a cached repeat consumed no new verification attempt. Its 256 columns had height MAE **3.805 blocks**, maximum error **39**, and **71/256 land/water disagreements** with the density proxy. Land and water mismatches are complementary descriptions of those same 71 columns, not 142 separate errors. This remains a selected local diagnostic and a **PARTIAL** natural-ground raster, not a verified island or a population accuracy estimate.

Actual block observations are supported. Complete natural-ground provenance, structure exclusion, waterlogging, ice handling, exhaustive structure starts, and whole-formation certification remain **PARTIAL or UNVERIFIED**. Current rasters therefore cannot certify a final Realm. Final Nether imports can prove Fortress/Bastion existence when supplied actual pinned evidence is within the exact region; missing/outside nearest anchors cannot prove absence. Stable Script API does not provide the required exhaustive generated-structure enumerator.

The default adapter limits total selected attempts and regional tiles, caches observations, records ordinary failures separately from seed eligibility, and does not start BDS for every scanned seed. A footprint beyond the tested budget stays partial. Cave scans are manual and have no ranking effect.

## Validation and remaining external gates

Deterministic tests cover boundaries, overflow, families, Savanna, signed seeds, multiple anchors, transactional recovery, worker reproducibility, independent variants, islands versus peninsulas, missing cells, ridge continuity/relative relief, rough V2 interiors, formation footprints, version/source identities, rescoring, selected verification budgets, and explicit caves. Synthetic maps provide known geometry; they do not certify the native predictor against actual rare landscapes.

The full suite before the overlap-cache patch passed **232 tests in 108.59 seconds**. Subsequent targeted cache/terrain checks passed 40 tests; correctness follow-ups add further controls. A new final relevant suite is still required after the remaining fixes. The interrupted native terrain pilot logged at least 217.922 seconds and 2,215,211 columns, completing eight V1 and two V2 centers before interruption; it does not establish full default terrain cost or a cache speedup. No whole post-cache native terrain benchmark has completed.

The audit follow-up reproduced and corrected the wide-lake false border claim and stale missing-raster cache behavior. Selected BDS attempts now reserve budget atomically, calibration uses only stable known requested-lattice cells, and interpretation hashes invalidate stale observations. Memory validation rejects nonfinite/negative reserve settings; loss of monitoring stops dispatch while draining submitted work. Parent coverage commits validate returned seeds against their assigned sequence. Manual cave failures retain reports and earlier detections, with bounded uncertain-neighborhood refinement. A shared score policy preserves independent predicted/actual channels and requires verified weighted components for verified ranking. These source fixes passed the **full 290-test suite in 106.68 seconds**, without new large seed benchmarks or BDS generation. Source/test hashes were rechecked against the batch manifest after the test process exited. See [the follow-up evidence](runs/realm-implementation-2026-10-10/CORRECTNESS_FOLLOWUP.md).

Interruption-safe rescoring/export publication and native/custom terrain-provider identities are implemented. Discovery observations and recoverable evidence tasks now persist; bonus uncertainty explicitly separates model predictions from actual evidence. Stronger V2 disconnected-hill controls and complete analysis-request halos are implemented. Actual surface-biome sampling, an authoritative discovery recovery executor, full-region actual generation/reuse, generated structure verification and whole actual V1/V2 calibration remain open. See [the maintained backlog](runs/realm-implementation-2026-10-10/FIX_BACKLOG.md).

Version-matched exhaustive required-structure validation, full Stronghold recall, true surface-biome coverage, and actual natural-ground/liquid geometry validation remain external gates. Rare-event precision, recall, and false-negative rates require complete actual V1/V2 positive and negative regions; the current small samples cannot supply those numbers. No unvalidated approximation permanently deletes a baseline survivor or certifies that a desired formation is absent.

## Latest accuracy/recovery checkpoint

The latest final-source full suite passed **410 tests in 116.53 seconds**, terminal exit 0, including score/export recovery, provider identities, cached/retry scheduling, discovery completion races, biome uncertainty, V2 broad disconnected hills and actual column interpretation. Two bounded current-policy BDS 32-square checks reused the selected seed: all 16 sampled columns per request had readable waterlogging flags; snapshot/API checks matched 20/20 and 62/62 with stable samples and clean shutdown. The latter contained five open-water columns. No positive overlay-water probe was present, so positive waterlogging/snow/ice fixtures remain needed. Both observations remain PARTIAL and do not certify any whole formation or Realm. No new large seed benchmark ran; throughput after these new evidence/geometry changes is unmeasured. Detailed current evidence and remaining gates: [ACCURACY_FOLLOWUP.md](runs/realm-implementation-2026-10-10/ACCURACY_FOLLOWUP.md).

## Latest durable-terrain/surface checkpoint

The final-source suite passed **560 tests in 119.03 seconds**, exit 0. Terrain pool membership and all remaining center/refinement/halo work are durable; failed samples remain retryable with immutable attempt evidence, fair rotation and correct incomplete-work counts. Actual surface-biome verification/export/rescore is implemented independently of prediction scores. Positive controlled water/cover fixtures and restoration have actual BDS evidence; strict pinned-runtime palette confirmation preserves exact differences and never promotes missing/unsupported cells.

A selected two-point BDS check verified actual Forest and Taiga presence, while overall eligibility stayed provisional. A selected natural 32-square at 8-block spacing had 16 usable surface observations, 9/9 finalized chunks, 56 exact saved/API probe matches plus 6 individually runtime-proven equivalents and 57/57 overlay checks. These are sampled controls, not whole-formation or structure certification. No new baseline seeds or large benchmark were added. Current-source throughput remains unmeasured. See [the checkpoint report](runs/realm-implementation-2026-10-10/SURFACE_TERRAIN_QUEUE_FOLLOWUP.md) and [resource forecast](runs/realm-implementation-2026-10-10/RESOURCE_FORECAST.md) for evidence and remaining gates.
