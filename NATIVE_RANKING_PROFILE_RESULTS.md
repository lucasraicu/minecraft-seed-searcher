# SQLite ranking and native stage profiling results

The later locked 2048/1024 revision and terrain/BDS investigation are recorded in [NATIVE_LOCKED_GEOMETRY_RESULTS.md](NATIVE_LOCKED_GEOMETRY_RESULTS.md). Measurements below retain their original policy and cohort.

Subsequent locked 2048/1024 implementation and measurements are in [NATIVE_LOCKED_GEOMETRY_RESULTS.md](NATIVE_LOCKED_GEOMETRY_RESULTS.md). The measurements below retain the historical 1536/896, two-miss policy.

12 October 2026. Implemented and verified indexed baseline ranking, retained the two-miss compact policy, added bounded diagnostic timing distributions and adopted exact per-input Mansion viability reuse. The original full-evidence and serial routes remain supported.

## Ranking behavior

`candidate_leaderboard_view` exposes `smart_score`, qualification, retention classification and unmet requirements. An expression index supplies the full ordering: verified candidates, complete predicted survivors, near misses with fewer misses, other pending candidates and failed records. Scores descend within each group, with candidate ID as the stable tie-breaker. A row represents one Stronghold anchor.

Scores follow the existing bonus formula. Near misses use the observed partial predictor score; deferred full-evidence inventories retain their provisional interval-midpoint score. Near misses stay `PENDING`. CLI results add `leaderboard_rank`, `smart_score`, `unmet_requirements` and an explicit ranking view. JSONL/CSV exports include the score.

Index entries update atomically with candidate inserts, evidence updates and rescores. Original candidate JSON, range digests, coverage and task records are unchanged. Legacy checkpoints receive an additive, transactional index/view migration. Already-installed readers acquire no migration write lock; rankings read a consistent snapshot during active writes. An incomplete score revision hides the SQL view and blocks CLI ranking/export. Index JSON expressions guard invalid excluded payloads, preserving bounded terrain reads; decoding an invalid selected record still fails.

## Indexed query measurement

An 18,350-anchor database produced identical top-20 IDs/scores for indexed and full-sort queries in ten alternating trials. Median indexed SQL time was **34.14 microseconds**, versus **266.31 milliseconds** for the equivalent unindexed reference (**7,801x**). EXPLAIN confirms index traversal without a temporary sort.

This is a warm SQL top-20 measurement excluding JSON decoding and a dashboard. It is not a seed-scanning speedup. Maintaining the index adds insert/update work; both scanning arms below include that work.

## Profiling design and scope

The separate `--profile` extension records bounded histograms, count/sum/min/max and worst seed/coordinate per entered stage, Y level, generated biome ID and all 13 family predicates. It captures timings before compact rejection frees records. Production builds contain no per-point timing instrumentation. Diagnostic buffers are capped at 64 MiB per call, additionally to the native output/scratch cap.

The active two-miss cohort has 10,000 distinct inputs, repeated three times at 32 threads. A separate 128-input, eight-thread forced-complete cohort measures late stages independently of natural survival. All instrumented/control complete semantic fingerprints match. Forced Fortress/Bastion and Outpost inventory probes are labeled separately; the production Nether pair shares its scan. Per-point biome timing covers direct lattice and Mansion-witness queries; biome work inside structure viability remains included in its structure stage. Family grouping describes queries returning that family, rather than separate generation calls for every predicate.

Active profiling overhead was **4.98%** on this small-batch diagnostic harness. Timed C calls exclude record extraction, SQL and CLI startup. Counts below pool three repetitions, which are not additional distinct seeds. p99 values are power-of-two histogram intervals, not fabricated exact percentiles. The tail flag uses p99 lower bound >=4x entered-call mean with >=100 calls; it is an investigation heuristic.

## Structure and shared-stage timings

All times are microseconds per entered call. Active mean and p99 are conditional costs at 32 threads; forced means use eight threads and full enumeration. They are not additive multicore wall-time contributions.

| Stage | Active calls | Active mean µs | Active p99 bounds µs | Forced mean µs |
|---|---:|---:|---:|---:|
| stronghold | 30,000 | 425.08 | 524.29–1,048.58 | 277.86 |
| structure_mansion | 55,263 | 464.34 | 1,048.58–2,097.15 | 278.23 |
| structure_jungle_temple | 55,263 | 106.11 | 131.07–262.14 | 81.63 |
| structure_desert_pyramid | 55,263 | 99.21 | 131.07–262.14 | 73.86 |
| structure_monument | 12,507 | 388.59 | 1,048.58–2,097.15 | 387.87 |
| structure_ancient_city | 3,708 | 228.74 | 262.14–524.29 | 168.92 |
| structure_village | 894 | 249.66 | 262.14–524.29 | 172.94 |
| structure_trial_chamber | 102 | 32.69 | 65.54–131.07 | 78.88 |
| structure_ruined_portal | 102 | 6.42 | 8.19–16.38 | 9.20 |
| structure_shipwreck | 102 | 1,017.98 | 2,097.15–4,194.30 | 908.28 |
| structure_mineshaft | 54 | 590.93 | 524.29–1,048.58 | 3,656.86 |
| nether_pair | 54 | 17.06 | 16.38–32.77 | 13.41 |
| biome_palette_4y | 33 | 24,061.03 | 16,777.22–33,554.43 | 16,817.88 |
| ranking_inventory_outpost | 0 | not reached | not reached | 15.23 |
| isolated_inventory_fortress | 0 | not reached | not reached | 7.49 |
| isolated_inventory_bastion | 0 | not reached | not reached | 10.47 |

Only 11 natural active anchors reached the palette per trial; Mineshaft and the Nether pair also have limited active samples. No active candidate reached accepted-record ranking inventory. The isolated inventory rows are forced diagnostics, not production survivors.

## Biome query timings

| Family | Active query observations | Active mean µs | Forced mean µs |
|---|---:|---:|---:|
| plains | 1,950 | 10.79 | 7.20 |
| desert | 3,621 | 10.20 | 7.45 |
| forest | 3,285 | 11.12 | 7.45 |
| taiga | 0 | not observed | 7.17 |
| jungle | 2,292 | 11.44 | 7.88 |
| swamp | 117 | 12.10 | 7.82 |
| snowy_ice | 27 | 13.41 | 6.05 |
| dark_forest | 714 | 11.04 | 7.65 |
| peaks | 99 | 14.70 | 10.68 |
| stony_shore | 813 | 9.98 | 7.30 |
| lush_caves | 2,967 | 9.49 | 6.62 |
| dripstone_caves | 1,854 | 8.69 | 5.81 |
| deep_dark | 2,889 | 14.75 | 9.23 |

| Y | Active direct queries | Active mean µs | Forced mean µs |
|---|---:|---:|---:|
| 63 | 19,383 | 10.94 | 7.97 |
| -48 | 19,008 | 11.10 | 7.68 |
| 0 | 19,008 | 10.92 | 7.52 |
| 160 | 19,008 | 7.92 | 5.38 |

No large p99 cold-biome tail appeared under the stated threshold. Taiga had no active family observations; snowy/ice and peaks have sparse active observations. The forced controls cover all 13 families. Generator output determines family membership, so reordering family-name tests does not avoid the underlying biome query.

## Outlier rechecks and optimization decision

Monument is the reproducible forced-stage tail: about 0.39 ms mean with p99 between 2.10 and 4.19 ms. Its worst seed repeated at up to 3.89 ms serially; the expensive anchor contained five viable Monument starts. The pinned predictor performs two neighborhood viability checks. Full enumeration on such a layout is legitimate work, rather than evidence of a bug. Existing count-floor early stopping is retained.

The worst parallel Stronghold and Mansion observations (9.75 and 10.78 ms) fell to 0.51 and 0.43 ms maximum in five serial rechecks. Shipwreck fell from 5.26 to 3.27 ms; the palette from 29.82 to 17.00 ms. These rechecks are consistent with contention/measurement context contributing to spikes; they do not prove a specific OS cause.

**Adopt the bounded exact Mansion cache.** Mansion consumes the largest active baseline service share. Reusing identical start viability across anchors within the same full64 input removed 1,686 of 26,116 repeated raw-start checks per active trial (6.46%). The 64-entry cache resets before every input, is private to its native worker and falls back to direct evaluation when full. Counts, witnesses, inventory, scores and uncertainty remain identical; there is no cross-seed or low-bit reuse. `--disable-mansion-cache` retains a build control. Rebuild the native extension to enable the optimization; existing checkpoints retain their frozen computation identities.

Longer isolated controls confirm a **2.92% C-only gain** at 32 threads on 100,000 inputs, and **2.65%** serial gain on the contained 5,000-input subset, each repeated three times. Parallel medians were 14,652.41 versus 15,080.16 C-only inputs/sec. Short 10,000-input C measurements varied from +5.7% to -4.4%; those noisy samples are retained, and the longer controls support the decision.

The forced palette had 594,432 logical samples versus 550,396 unique coordinates within each input (7.41% potential exact reuse). No additional palette cache or SIMD rewrite was adopted: the palette is infrequently reached in the active cohort, and a separate measured parity/resource gate would be needed. Mineshaft full enumeration already uses the four-lane kernel.

## Fresh persisted comparison

Three alternating trials compare cached/uncached native builds using the same current indexed store and key `120266001000`. Compact mode scans 50,000 inputs; the full-evidence 10,000-input subcohort is contained in those inputs. Actual CLI timing includes imports/startup, generation, record preparation, FULL SQLite commit, drain and exit. Full semantic/task fingerprints and compact receipts match.

| Scope | Uncached median inputs/sec | Cached median inputs/sec | Ratio |
|---|---:|---:|---:|
| Two-miss checkpointed scans, 50,000 inputs | 11,111.98 | **11,328.21** | 1.0195x |
| Complete persisted inputs, 10,000 inputs | 2,534.55 | **2,554.68** | 1.0079x |

The compact gain is modest (1.95%); full-mode difference is only 0.79% and is not a substantial writer speedup. Cached compact trials ranged 11,195.00–11,568.61/sec, with peak sampled process-tree RSS 149,491,712 bytes and a 212,992-byte SQLite file. Cached full trials ranged 2,553.95–2,557.31/sec, with peak RSS 423,669,760 bytes and 142,503,936 SQLite bytes. RSS sampling may double-count shared pages.

Compact production trials retained zero natural candidates. Positive/near-miss fixtures test accepted persistence, classification and ranking. These fresh 50k/10k figures use a different cohort and include the new index; historical 100k rates remain separate and cannot serve as a comparable control for this change. The 5,000/sec full-evidence target remains unmet. SQL index traversal improves leaderboard reads, while full persistence still pays record preparation, hashing, rows/indexes and FULL commits. No world-discovery time is established.

The new measurement keys cover 110,128 distinct predicted inputs including the extended C-only cohort. Only 50,000 distinct inputs have the new persisted-workflow comparisons; the larger C-only diagnostic has no durable per-input coverage. Repeated trials and contained subcohorts are not additional distinct volume. Disk preflight projected about 23.6 GB plus a 16 GiB reserve for each paired suite; actual fresh databases were much smaller. Original runs and the pre-existing dirty workspace remain preserved.

## Verification and retained evidence

- Final integrated suite: **820 tests passed in 158.32 seconds**.
- Serial AddressSanitizer: **1,248 inputs, zero errors**, including timing-buffer ownership. Leak detection is unsupported on this macOS ASan runtime; this is not a race certificate.
- Ranking tests cover indexed query plans, complete/near-miss ordering, live score updates, exact retry digests, additive migration, concurrent snapshot readers, guarded excluded payloads, exports and incomplete rescore revisions.
- Native tests cover full64 extremes/siblings, serial/parallel/independent evaluator parity, positive and late-failure fixtures, bounded timing allocation and error cleanup.
- The first full run found the malformed-excluded-payload issue (819 passed, one failed); after the fix, 32 targeted checks and the complete 820-test suite passed. Failed preliminary logs remain retained.

Artifacts are under `runs/native-ranking-profile-2026-10-12/`:

- `stage-profile/results.json`: uncached entered-stage/family/Y distributions and controls; its `compiled-source/` snapshot matches all 39 recorded compiler inputs.
- `cached-stage-profile/results.json`: current cache timing distributions, counts and parity.
- `outlier-rechecks.json`: five serial repetitions and complete forced inventories for each selected slow seed.
- `extended-compute.json`: longer parallel and serial C-only controls.
- `paired-final/results.json`: final guarded-index CLI comparisons and ten indexed/full-sort query trials.
- `paired-ranking-cache/results.json`: earlier comparison retained separately.
- `final-suite.log`, `json-guard-regression.log`, `full-suite.log`: final, targeted and preliminary regression evidence.
- `asan-profile/result.json`: sanitizer scope, compile command and measured input count.

Usage and SQL are documented in [README.md](README.md). Earlier complete baseline/terrain evidence remains in [NATIVE_THROUGHPUT_RESULTS.md](NATIVE_THROUGHPUT_RESULTS.md).
