# Mineshaft, biome inventory and lower32 investigation — 10 October 2026

The dominant cost is complete inventory work executed at the baseline gate. A phased gate can preserve the current eligibility decisions while doing much less work; a native enumeration prototype also accelerates the current complete payload. The 99.9% lower32 rejection aspiration is unsupported by the filter's logic, even with compact borders.

## Evidence and scope

The million-input benchmark used 5000-square discovery, 2688 Overworld and 1024 Nether. It measured 22.23 ms per Mineshaft check and 12.61 ms per 1764-point biome inventory. Mineshaft and biome calls consumed 50.61% and 28.70% of summed timed filtering calls. There were 1,205,024 checks of each, zero recorded Mineshaft prediction misses, and 2,125,662,336 biome points. These are summed worker call durations, not pipeline wall-clock shares. The run's end-to-end rate remained 173.37 full64 inputs/sec, including persistence.

New experiments used eight boundary/control seeds for native microbenchmarks, 96 distinct full64 seeds shared across two border contracts, 4096 distinct low32 values shared across four contracts in eight dispersed blocks, and 262,144 low32 values shared across three contracts for longer existence timing. All timings are local diagnostic workloads; repetitions do not increase unique coverage.

The 96-input complete-payload comparisons used three counterbalanced trials of installed, private-reference and exact-prototype arms. The gate comparison used three counterbalanced trials of full baseline and eligibility first. Production source/config/native binary and prior evidence retain their original hashes. Private builds and logs are under this directory.

## 1. Why Mineshaft takes so long

`native/bridge.c:ss_scan` dispatches to `finders.c:getMineshafts`, which visits every candidate chunk. Each chunk calls `setCarverSeed`, restarting MT19937, skips the first random value and tests the second. `mt_seed` initializes 397 state terms even though a usual chunk needs only two outputs. A 2688 square covers roughly 28,000 chunks: approximately 11 million dependent initialization recurrences per check. This work predicts start positions; `getMineshaftPieces` is not on this path.

The combined wrapper already scans placement once and applies a trivial Mineshaft viability mask. A duplicate raw/viable scan and buffer overflow/retry are not the current cause. The remaining waste is enumerating every start when baseline eligibility needs one. Original chunk rounding can also visit an outside edge row, but tightening the start-center bounds saved little by itself.

Isolated median times in milliseconds, three trials per seed/border case:

| Overworld side | Installed complete scan | Vector4 complete scan | First-start existence |
|---|---:|---:|---:|
| 1280 | 4.994 | 2.656 | 0.152 |
| 2380 | 14.068 | 7.772 | 0.181 |
| 2688 | 17.490 | 9.433 | 0.051 |

The four-lane prototype evaluates exact MT outputs for four chunk seeds together. Complete-scan arms matched every start coordinate; all 672 comparisons passed their full-array or first-witness contracts, including control repetitions. The first three MT outputs also match on 4100 seeds, including unsigned boundaries. The existence arm stops at the first in-border start and matches the full scan's presence and first coordinate; a negative scans the complete relevant domain.

Concrete change: add a native Mineshaft existence API with exact half-open/start-center bounds, return one witness and label the full start inventory deferred. Complete enumeration can run when a candidate is nominated. If the complete baseline payload must be retained immediately, use the reviewed vector kernel with scalar fallback and versioned native identity; it reduces this stage by about half without dropping starts.

The pinned carver code truncates the world seed to uint32 for MT initialization and chunk mixing. All 64 tests of 16 low32 layouts × four high32 siblings matched their start arrays. This supports reviewing Mineshaft raw placement for a version-bound cache, but does not change the existing allowlist or certify real-world generation. Independent full64 enumeration has little useful sibling reuse; prioritize existence first.

## 2. Why biome inventory takes so long, and logic problems

`baseline.py` builds a 64-block grid anchored at each border's lower corner: 1764 points at 2688, 400 at 1280. It samples all points even after two wooded families are known because the same result supplies the entire biome inventory and bonus score. The CFFI call is batched once; it is not one Python/native crossing per point. Each native point calls `getBiomeAt`, which allocates and frees a small cache, then evaluates Voronoi access, climate noise, splines and the biome tree. Seeds are initialized once per context, not per point.

| Side | Points | Original native batch ms | Exact direct sampler ms |
|---|---:|---:|---:|
| 1280 | 400 | 2.002 | 1.949 |
| 2380 | 1444 | 7.479 | 7.361 |
| 2688 | 1764 | 9.324 | 9.161 |

Removing the allocation while preserving Voronoi coordinates, flags, rounding and a NULL climate hint saved only about 1–3%. The primary cost is noise and lookup at every point. Exact point reuse across overlapping anchors was only 0.39% at the old borders and zero at compact borders in the 96-seed cohort, so merely enabling a point cache would not solve it.

The existing `ss_biome_points` loop also has no OpenMP loop even when the handle's native thread count is increased. A private direct loop produced identical IDs at 1/4/18 threads; at 2688 its medians were about 11.13/3.03/0.96 ms. That is useful for an isolated inventory or differently partitioned process/thread budget. The baseline already runs 30 processes × one native thread; adding 18 threads to each would exceed the measured CPU budget. A new combined schedule needs its own benchmark.

Two correctness findings affect proposed optimizations:

* The current sample lattice moves when the border size changes. The saved pilot already shows seed `7980124511283784280`, Stronghold `(772,-1996)`, detecting forest+jungle at 2304 but only jungle at 2380. Replaying the old witness coordinates within the larger border restores both. Use a world-aligned lattice and retain existing in-border witnesses; version the sampling contract and re-score candidates. Refine unresolved sparse negatives instead of treating them as absence. Changing the lattice does not preserve the old inventory payload automatically.
* Reusing the previous climate-tree leaf is unsafe for exact sampling. The source tree uses strict distance comparisons, so a cached leaf can win a tie differently. The experimental hint arm changed four IDs, including seed `12345` at `(3041,63,-1183)` from beach to forest. Exclude this shortcut. Preserve NULL hints unless a canonical, reference-equivalent tie rule is proved.

The inventory samples fixed Y=63, so it predicts biomes at that height rather than actual generated surface coverage. Keep that status explicit. For final inventory, reuse surface observations/terrain raster work already available in later stages instead of adding a surface-height scan to every baseline input.

Concrete change: sample a dispersed ordering of the same lattice in small batches, stopping once two wooded families have positive witnesses. If two are not found, finish that lattice and retain PENDING. Defer full family/variant counts and optional bonus inventories, with explicit score intervals and deferred status, then complete them for the shortlist. Future prioritization must account for those unknown scores and retain fair exploration; incomplete scores cannot silently become zero or prove a candidate is worse.

## 3. Complete-payload improvement versus a phased gate

The exact vector Mineshaft scan plus direct biome sampler preserves every compared candidate payload, including all start coordinates, detections, counts, bonuses, statuses and uncertainties. These timings include the same Python cache instrumentation in each arm and exclude persistence/terrain/BDS.

| OW/Nether | Installed seconds / 96 inputs | Exact prototype seconds | Time reduction |
|---|---:|---:|---:|
| 2688/1024 | 4.786 | 3.762 | 21.4% |
| 1280/896 | 0.318 | 0.275 | 13.3% |

A second prototype checks Mineshaft existence and wooded witnesses, deferring full Mineshaft inventory, full biome inventory/bonuses and all optional structure inventories/bonuses. All qualification and pending-reason maps match the full baseline across the same 96 seeds and both geometries. This arm produces a different, incomplete payload and requires a staged contract before adoption.

| OW/Nether | Full baseline seconds | Eligibility-first seconds | Ratio | Biome points visited/full |
|---|---:|---:|---:|---:|
| 2688/1024 | 4.357 | 0.374 | 11.65× | 3,136/218,736 |
| 1280/896 | 0.267 | 0.115 | 2.33× | 976/8,800 |

The old-border cohort had no wooded negative; the compact cohort had one, exercising the full-grid negative fallback. These decision results certify the current sampled predictor only. Deferred work must be paid later if it is needed. These ratios do not establish a new persisted pipeline rate or a verified-world rate.

## 4. Why the lower32 99.9% aspiration fails

`realm/raw.py:FAMILIES` and `center_rectangle` hardcode 5000 discovery / 2688 OW / 1024 Nether. The raw scan searches an envelope containing every possible Stronghold-centered border. A common-center witness can lie anywhere in that domain; it does not need to be an actual Stronghold. Raw Village and Ancient City attempts exist at very high density, while their full64 biome viability, Stronghold discovery, wooded families, Trial Chamber and terrain are outside this filter.

This is a logical selectivity limit. For the old envelopes, there are at least 196 raw Village and 400 raw Ancient City attempts for every low32 value. At the 1280 compact envelopes the guaranteed counts are still 81 and 169. Those families cannot reject a layout via zero raw counts. The genuine raw absence test is almost entirely the small-envelope Fortress/Bastion placement split. The broad initial Fortress condition adds no eligibility rejection when a required final Fortress exists inside its contained envelope.

The stronger result applies inside every individual anchor square: Village raw attempts are guaranteed when the side is at least 944, and Ancient City raw attempts when it is at least 624. Their offsets lie in bounded intervals inside each region, and any square this wide contains a complete allowed-offset region box. Therefore both raw-presence clauses hold at every possible center for all requested OW sizes (1024–2380). Exhaustive integer phase checks verify this, and a two-family Nether-only joint solver matches all 16,384 saved four-family feasibility results. Village/City raw layouts need not be enumerated even for the joint-placement predicate. Full64 biome viability remains essential.

The saved 1280/896 compact baseline already produced qualifying prediction anchors for 215 of 1000 distinct full64 inputs. A necessary prefilter discarding 99.9% before these same structure/wooded checks would discard known positive predictions under the same contract. Final terrain formations may be rare; their rarity cannot be inferred from these common raw placements.

The original saved contiguous test rejected 30/4096 (0.73%). New dispersed results:

| Discovery side | OW/Nether | A family has zero starts | No common allowed center |
|---|---|---:|---:|
| 5000 | 2688/1024 | 31/4096 | 31/4096 (0.76%) |
| 4000 | 1280/768 | 316/4096 | 317/4096 (7.74%) |
| 4000 | 1280/896 | 165/4096 | 165/4096 (4.03%) |
| 4000 | 1536/896 | 165/4096 | 165/4096 (4.03%) |

The joint test added only one rejection, at 1280/768. A much larger necessary-existence cohort confirms the low rejection rates:

| OW/Nether | Necessary rejection % / 262,144 | 18-thread layouts/sec | 36-thread layouts/sec | Full32 forecast at 36 threads |
|---|---:|---:|---:|---:|
| 2688/1024 | 0.72% | 1,001,121 | 1,466,977 | 48.8 min |
| 1280/768 | 7.36% | 817,296 | 1,204,355 | 59.4 min |
| 1280/896 | 3.84% | 887,914 | 1,228,645 | 58.3 min |

The last column is an existence-only compute forecast. It excludes complete counts, ranking, joint-center witnesses, checkpoints, full64 evaluation and all world verification. Even this much lighter prototype remains above the 45-minute aspiration on the measured host. Rejecting 99.9% by keeping only a fixed top quota would be a sampling decision, not a proof that the discarded layouts cannot qualify.

## 5. Lower32 implementation waste and concrete fixes

The current native adapter enumerates all regional attempts to get exact counts and scans a one-region halo. That halo is useful for displaced Stronghold starts but unnecessary for the reviewed regional raw start families here. Fortress and Bastion share candidate coordinates and a complementary type draw; scanning both separately repeats placement work. The broad Fortress scan also overlaps the final envelope.

The current ranking is `sum(min(count,32))`. Village and Ancient City therefore contribute the same 64 points to every layout, universally under these envelopes. Their full counts cost most of the raw sweep and do not distinguish the ranking. Adding Fortress and Bastion counts also mostly rewards total regional attempts, rather than a feasible, viable Stronghold combination. The saved staged comparison yielded 209 predicted anchors versus 199 independent anchors, but cost 7.60+4.73 CPU seconds versus 7.25, and measured no verified yield advantage.

Exact-count prototypes trimmed the halo and reused the shared Nether scan. A separate threshold prototype proves guaranteed counts from fully covered regions, skips constant terms, and stops once 32 hits are found. It preserves capped ranking scores and every zero/nonzero decision; its output counts are capped and must be labeled as such.

18-thread compute-only forecasts, based on the 4096-layout trials:

| OW/Nether | Original full counts | Trim/shared full counts | Exact capped-ranking counts |
|---|---:|---:|---:|
| 2688/1024 | 66.71 h | 50.83 h | 9.01 h |
| 1280/768 | 35.74 h | 23.01 h | 7.82 h |
| 1280/896 | 35.30 h | 23.10 h | 7.63 h |
| 1536/896 | 42.51 h | 29.22 h | 7.86 h |

Concrete changes, in implementation order:

1. Derive and version raw envelopes and center rectangles from the active discovery/OW/Nether contract, preserving fractional Stronghold/8 Nether centers and half-open bounds.
2. Split native APIs for existence, capped ranking metrics and complete layout inventory. Prove region-presence constants and avoid scans for saturated terms. Trim only reviewed region types; retain the displaced-Stronghold adapter.
3. Reduce joint raw feasibility to Fortress/Bastion for the proved OW-size range, and reuse their placement and contained-envelope work. Preserve their complementary type selection and full64 viability.
4. Replace flat raw-density hints with measured geometry metrics, such as feasible-center coverage and Fortress/Bastion coexistence; validate actual Stronghold/biome viability on a bounded high32 cohort. These are ranking experiments until useful yield and recall are established.
5. Keep independent full64 search primary. Measure total CPU time, persistence and verified yield for any sibling strategy; the current evidence does not support a universal 99.9% front-door rejection target.

## Recommended next work

Implement the Mineshaft existence API and a separate baseline eligibility/deferred-inventory contract first. Use dispersed positive-only wooded sampling with explicit pending negatives. Keep the exact vector complete scan as the option when full payloads are needed immediately. Correct the moving lattice under a new sampling identity. Then make the raw adapter contract-aware and remove constant/capped count work. Do not spend a full32 sweep budget before the ranking strategy demonstrates useful yield.

Verification: 63 targeted regression tests passed ([test record](regression-tests.json)). [audit.json](audit.json), [summary.json](summary.json), [micro.json](micro.json), [baseline.json](baseline.json), [gate.json](gate.json), [raw.json](raw.json), [raw-thresholds.json](raw-thresholds.json), [raw-presence-scale.json](raw-presence-scale.json) retain detailed evidence. Run `scripts/diagnose_filter_costs.py` commands with the local `.venv/bin/python`; the script and `scripts/filter_cost_probe.c` reproduce the isolated prototypes. The original 46 sealed source/evidence files and both private binary hashes were checked. Independent verification covers 360 small-domain exhaustive center-intersection cases, 7424 integer region-phase cases, and 16,384 reduced joint-predicate cases. Real-game accuracy and a new persisted end-to-end throughput remain unmeasured by these experiments.
