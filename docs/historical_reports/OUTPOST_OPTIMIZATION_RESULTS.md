# Outpost screening and exact coastal optimization — 12 October 2026

Implemented and adopted `locked-2048-1024-outpost-v3` for the active configuration and default CLI policy. Native execution remains an explicit executor option; the compatible Python route remains available. Compact screening now measures **22,525 checkpointed inputs/sec**. Full-evidence persistence measures **1,180 inputs/sec**, so the original 5,000 full-evidence inputs/sec target remains unmet.

## Changes and adoption

- Added the required **two-Outpost floor** consistently to C screening, Python evaluation, direct/replay records, retention validation, SQLite and exports. There are now 24 baseline requirements: 11 structure counts and 13 biome predicates. The Stronghold anchor remains mandatory. One unmet requirement can be retained as a near miss with complete core inventories.
- Kept the 2048×2048 Overworld and 1024×1024 Nether bounds, Bastion floor three, deferred Shipwreck floor five, river corridor 600 blocks and highway radius 250 blocks. Stage 3 queries only Monuments and Shipwrecks; it preserves the baseline Outpost inventory. Outposts retain +10 points per observed copy.
- Selected the measured sequence: Nether pair, Ruined Portal, Outpost, Desert Pyramid, Jungle Temple, Mansion, Ancient City, Village, Trial Chamber, Mineshaft. Validated alternate orders remain available for measurement. Earlier policy revisions preserve their semantics.
- Kept atomic OpenMP chunk claiming at 16, following the previous measured chunk-size review. No unsupported OpenMP dispatch ABI was introduced.
- Replaced repeated coastal edge-strip `np.unique` calls with vectorized exact label reductions. Empty selections, unknown cells, component identity, length accumulation and decisions retain their previous meaning.
- Preserved the full four-Y biome contract. Absence in the first 32–128 samples cannot prove absence over the lattice; no approximate negative cutoff was adopted.

The native ABI changed to carry the Outpost goal and structure order. Rebuild the batch extension and start a fresh run. Existing runs retain their identities and cannot silently resume under the new policy. See [README.md](README.md) for build, compact/full scan, resume and export commands. The original generator extension and pinned OpenMP runtime are unchanged.

## Actual production-entry-point measurements

Fresh CLI processes, three rotated trials per arm, durable SQLite WAL/FULL operation, bounded cohorts, retained raw results:

| Workflow | Inputs per trial | Median inputs/sec | Trial range |
|---|---:|---:|---:|
| Compact native v3, one miss | 50,000 | **22,525.37** | 22,453.22–22,649.95 |
| Compact previous river-v2, one miss | 50,000 | 11,979.32 | 11,833.28–11,999.66 |
| Full-evidence native v3 | 5,000 | **1,179.67** | 1,173.85–1,180.66 |
| Full-evidence Python v3, 36 workers | 5,000 | 886.78 | 881.98–888.66 |

Compact v3 is **1.88×** the preceding policy's throughput. This includes the selectivity change from requiring Outposts and the ordering improvements; it is not an isolated implementation speedup. Under the same v3 policy, full-evidence native is **1.33×** the fresh Python control. Complete durable record/task fingerprints match between those full-evidence arms.

The compact cohort had **zero natural retained candidates**, under both policies. Positive and near-miss persistence, scores, inventories, terrain transitions, retry and export are covered by fixtures, not inferred from this all-reject cohort. These numbers measure checkpointed screening, not complete world qualification or BDS verification.

Full-evidence trials stored all 5,000 inputs, 9,338 discovered anchors, 10,000 discovery tasks and 9,338 V1 tasks. Native database size was 95,444,992 bytes; Python was 95,924,224 bytes. Compact databases were 212,992 bytes. Maximum sampled process-tree RSS was 119,541,760 bytes for compact v3, 123,871,232 for compact v2, 430,964,736 for full native and 1,649,557,504 for full Python. Disk preflight and bounded counts were used; no unlimited search ran.

Native full-evidence service medians per 5,000 inputs were 0.150 seconds C, 0.824 record preparation, 1.187 encoding, 0.207 hashing, 0.760 SQL and 0.339 commit. Writer wall service was 1.189 seconds. These overlap and are separately aggregated, so they must not be added as a wall-time breakdown. Serialization, preparation and persistence remain the full-evidence bottleneck.

Raw evidence: [final workflow](runs/outpost-optimization-2026-10-12/final-workflow/results.json).

## Isolating filter-order improvements

All orders in these comparisons enforce the same v3 requirements. Each cohort contains 50,000 distinct inputs, with three rotated trials. Native decision fingerprints match across orders.

| Order | First cohort compact median | Disjoint held-out compact median |
|---|---:|---:|
| Portal → Outpost → Mansion | 18,757.61/sec | 18,472.90/sec |
| Portal → Outpost → Pyramid → Temple → Mansion | **22,597.61/sec** | **22,535.67/sec** |
| Portal → Outpost → Temple → Pyramid → Mansion | 22,297.00/sec | 22,541.16/sec |

Moving both scattered structures before Mansion improves persisted compact throughput by about 20–22%. Their relative order is effectively tied on the held-out cohort; Pyramid-first was retained, without claiming a universally optimal order. An earlier same-policy comparison measured Mansion-first at 13,232.45/sec and Portal→Outpost→Mansion at 18,549.24/sec.

The selected order's **C-only** median was 35,510.86/sec on the first cohort and **35,385.17/sec** on the held-out cohort. C-only rates omit record preparation, SQLite and CLI overhead.

The first cohort uses key 120267003000 and the held-out cohort key 120270003000. The final CLI comparison reuses the held-out cohort, and its 5,000-input full-evidence cohort is a subset. Repeated trials and these reused inputs are not additional distinct search volume. Index-plus-key enumeration means nearby keys alone would not establish disjoint cohorts.

Evidence: [initial orders](runs/outpost-optimization-2026-10-12/order-benchmarks/results.json), [refined orders](runs/outpost-optimization-2026-10-12/rare-order-benchmarks/results.json), [held-out orders](runs/outpost-optimization-2026-10-12/heldout-order-benchmarks/results.json).

## Structure and biome profiling

The separate instrumented extension records stage timings; production does not add per-point timing calls. Final profiling used 10,000 active inputs and 64 forced diagnostic inputs per trial, three trials. Normal/profile semantic differences were zero; measured active instrumentation overhead was about 13%.

| Active stage | Pooled entered calls | Mean µs | p99 histogram interval µs |
|---|---:|---:|---:|
| Stronghold | 30,000 | 414.90 | 524–1,049 |
| Nether pair | 55,263 | 17.85 | 16–33 |
| Ruined Portal | 45,000 | 9.81 | 8–16 |
| Outpost | 44,997 | 32.74 | 33–66 |
| Desert Pyramid | 15,729 | 172.60 | 131–262 |
| Jungle Temple | 4,038 | 159.21 | 131–262 |
| Mansion | 1,350 | 816.05 | 1,049–2,097 |
| Ancient City | 114 | 422.45 | 524–1,049 |
| Village | 9 | 479.56 | 524–1,049 |

The order change reduced Mansion entries from 15,729 to 1,350 across matching diagnostic trials: **91.4% fewer calls**. Village has too few observations for a useful tail conclusion. No active inputs reached Chambers, Mineshafts or palette evaluation; their absence does not mean zero cost.

Forced late-stage diagnostics measured full Mineshaft enumeration at **5.98 ms per entered anchor** and the complete four-Y palette at **27.71 ms**. Other forced means were Mansion 423 µs, Temple 123, Pyramid 129, City 277, Village 245, Chamber 120, Portal 14, Nether pair 15 and Outpost 25. These forced workloads establish costs, not natural survivor frequency. Full inventories cannot be replaced with first-witness counts. No stage with at least 100 entered calls met the diagnostic large-tail rule (p99 lower bound at least four times its mean); that is not a guarantee against rare outliers.

Use [verified stage profile](runs/outpost-optimization-2026-10-12/verified-stage-profile/results.json) for final findings. The earlier `final-stage-profile` trial overlapped a small CLI smoke run and is preserved but excluded from performance conclusions. Full family/Y histograms remain in the raw profile.

## Coastal geometry

Three retained natural 4-block rasters, three counterbalanced repetitions, identical river policy:

| Coastal evaluation | Median elapsed |
|---|---:|
| Retained previous implementation | 0.242607 seconds |
| Exact vectorized strip reduction | **0.214711 seconds** |

This is **1.13× geometry throughput**, or 11.5% less elapsed time, with zero semantic differences after excluding only stage timings. A separate randomized oracle checks 200 grids in both orientations, including empty selections and unknown labels. Profiling identified 36,960 `np.unique` calls across 18 evaluations before the change.

These are geometry evaluations over existing rasters, not terrain generation or persisted seed throughput. Density sampling remains unchanged; the proposed sub-15-ms complete terrain prediction and sub-eight-second BDS verification are not established. Existing exact nested sample reuse remains in place. Coarse grids cannot safely certify unseen fine features. BDS was not launched.

Evidence: [coastal comparison](runs/outpost-optimization-2026-10-12/coastal-final/results.json).

## Verification and milestones

- **M0:** Preserved dirty/untracked work, source snapshot, build/runtime identities, bounded benchmark budgets and profiles.
- **M1:** Direct native, replay and independent Python records agree for positives, signed/shifted bounds, all synthetic missing requirements and alternate orders. Natural complete enumeration and capped Outpost counts were checked separately.
- **M2:** Updated 24-requirement persistence validation; retained atomic FULL durability, exact retry, task tables, scores and exports. A retained synthetic export contains one predicted survivor and one Outpost near miss; its third, two-miss input is discarded with durable coverage.
- **M3:** Preserved bounded owned buffers, backpressure, recoverable leases and process-tree resource accounting. Serial and simultaneous independent OpenMP calls agree after buffers close.
- **M4:** **868 tests passed in 208.26 seconds**. Six natural capped-count cases were expanded to cover Outposts and rerun successfully. Serial ASan covered **1,248 inputs with zero errors**, including profile buffers and all current policy flags; leak detection is unavailable on this host. This is not a parallel race-detector result.
- **M5:** Actual CLI v3 scan and zero-work resume passed. Adopted v3 support in the explicit native production executor; retained the Python default and historical policies. Fresh paired full-workflow measurements, database integrity checks and protected binary hashes are retained.
- **M6:** Profiled and optimized exact coastal geometry; retained terrain and baseline performance as separate quantities. No additional density approximation or actual-game certification was promoted.

Build identities, test logs, SQLite files, raw trials and [final verification](runs/outpost-optimization-2026-10-12/final-verification.json) are under `runs/outpost-optimization-2026-10-12/`. Original historical runs remain untouched. The final source manifest identifies the reviewed implementation.

Remaining limits: full-evidence persistence is below target; late full palette/inventory work remains expensive; the active 75–85% mainland threshold versus authored 70–80% wording remains an explicit policy discrepancy; the web dashboard is still a mock; actual Bedrock playability and complete-world discovery probability remain unverified. Prediction-scale and large-search readiness gates remain enforced.
