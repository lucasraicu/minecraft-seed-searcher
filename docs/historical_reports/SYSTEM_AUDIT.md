# System audit — 8 October 2026

## Decision

Implement the approved **2304 × 2304 Overworld / 928 × 928 Nether** migration, repair configuration/eligibility edge cases, and adopt exact density-cell reuse before attempting a native SIMD rewrite. Build the requested **lower32 layout → upper32 sibling** mode as a bounded experimental search strategy and compare its yield with the full64 reference. Stronghold and Fortress remain the only mandatory structures. The user subsequently approved four categories: structures-only, enclosed inner island with water/mountains, ocean island, and dry flat mountain basin. Terrain requirements apply to the three terrain categories; structures-only has a separate qualifying list.

This audit produced documentation and an isolated experimental driver. It did **not** change production prediction code, the native binary, default configuration, or launch a sweep. The existing readiness package describes the old 3008/992 requirements and cannot validate the newly requested target.

Read the [specific implementation plan](AUDIT_IMPLEMENTATION_PLAN.md) and [seed-selection workflow](SEED_SELECTION_WORKFLOW.md). Audit evidence is under [runs/system-audit-2026-10-08](runs/system-audit-2026-10-08/WORK.md).

Follow-up requested test: [SIMD_TEST_RESULTS.md](SIMD_TEST_RESULTS.md). Thirty-six analyses support exact reuse (28.1% aggregate saving) and deferring this SIMD prototype; they also expose the cold seed -1 Mineshaft defect documented below. The initial audit's passing tests did not cover that seed-order condition.

## Scope and baseline

Audited revision: `840d28cc6f210fa118a479512dac44254234eb14`. Reviewed all application modules, the owned C/CFFI bridge and build, configuration, tests, checkpoint/report/review/readiness paths, existing measurements, and relevant pinned vendor structure/RNG/density paths. This is an application and algorithm audit, not an exhaustive proof of every vendored function or a new generated-game validation. Historical game/website observations retain their original scope.

The revised [Gemini recommendation](runs/system-audit-2026-10-08/GEMINI_RECOMMENDATION.txt) was evaluated as a proposal, not treated as verified implementation guidance. Initial user clarification approved 2304/640; the later Nether enlargement supersedes that with **2304/928**. The 640-based experiments below retain their original scope. No instruction made every structure mandatory.

| Verification | Result | Scope |
|---|---|---|
| Existing full test suite | **112 passed, 77.91 s** | Run during this audit before any production changes; synthetic and native tests included |
| Frozen external regression rerun | **874 unique correspondences / 880 structure rows; six known disagreements; zero reused starts** | 159 coordinate rows, 153 biome matches, height MAE 1 / max 5; no new drift, no complete-recall claim |
| Doctor and dependency check | Passed | Native callable; `pip check` reports no broken requirements |
| Existing 20-input pilot cache inspection | **Zero evictions across all 20 seeds** | Maximum allocated tile data 61,046,784 bytes, about 58.22 MiB |
| Exact density-cell experiment | Identical land classifications on ten patches × three trials | Seeds -1, 0, 9, 12345, 4294979641; negative/off-cell anchors; water, mixed, land cases |
| One complete serial seed A/B | **65.51 → 39.72 s, 39.36% less time** | Seed 12345 with cProfile; candidates, scores, near misses, counts, policy identical; no export or process-pool throughput claim |
| Raw lower32 diagnostic | **256 / 256 layouts survive** | New 2304/640 dimensions, ±5000 center envelope; both Fortress existence and even joint raw Fortress/Bastion/Village existence survive |

Machine: Intel Xeon W-2191B, AVX2 available, Apple Clang 17. The existing twelve-worker recommendation remains a starting point; no eighteen-worker result was measured here.

## Findings, in priority order

### Post-audit native test — cold seed -1 has order-dependent Mineshafts

The requested reversed-order performance test exposed a correctness defect missed by the initial audit. The unchanged installed binary returns **0 Mineshaft starts** for seed -1 in `[-1024,-1024,1024,1024]` when queried first, then **44** after a seed-0 Mineshaft query. Repeating -1 within either state retains that state's result. Reproduction: [installed seed-order evidence](runs/simd-test-2026-10-08/mineshaft-installed-seed-order.json).

Cause: `mt.c` initializes thread-local `mt_ws` to `(uint64_t)-1`, a valid seed, while `mt_a` and `mt_b` begin at zero. `setCarverSeed()` in `mt.h` checks only whether the seed differs, so the first -1 query skips generating its coefficients. Related seed helpers share the cache. Use an explicit initialized flag and include it in RNG save/restore; no seed-specific warm-up workaround. The repeated full-seed comparisons show Mineshaft records and optional scores changing, while the compared terrain/centers remain stable. This is a required P2 correction before any refreshed sweep readiness, independent of the Stronghold discrepancy. The frozen regression's usual seed order does not exercise cold -1.

### A1 — The border migration must cover more than Gemini's file list

**Required before the new sweep.** `search.example.yaml` says border sizes are the source of truth, but live constants remain in `structures.py:31`, `landscapes.py:153`, `landscapes.py:321`, `search.py:44`, `config.py:75`, and `reports.py:71`. Gemini omits the legacy search path, nomination priority padding (1568 = 1504 + 64), map rectangles/titles, and several guards and evidence consumers.

Derive dimensions once from configuration and use them for envelopes, exact center windows, landscape rasters, reports, and review borders. Preserve inclusive marker comparisons; a geometric 2304-wide square has 2305 integer endpoints, not a 2305-block geometric side. Current approved halves are 1152/464; center conversion is still exact division by eight. The center search envelope remains ±5000, independent of natural spawn.

The current refinement patch cap is **2048**, not 3008. Gemini's 2304 proposal increases that cap: at 16-block spacing, a full patch grows from 129² to 145² points, **26.35% more samples**. Keep 2048 for the initial comparison; evaluate a 2304 cap separately if it recovers useful deferred components. Do not present that increase as a speed optimization.

### A2 — Early basin bounds are not lattice-safe for every accepted configuration

**Confirmed counterexample; current default 16-block spacing not shown faulty.** `config.py:79` accepts refinement spacing 64. `basin_necessary_bound()` anchors its local raster at `center - half`, with `half` a multiple of twice the spacing; the full 3008 raster starts at `center - 1504`, offset by 32 modulo 64. Those are different sample lattices.

The [synthetic counterexample](runs/system-audit-2026-10-08/basin-lattice-counterexample.json) passes full-raster dry/gentle and mountain-ring checks at 100%, but the early bound rejects it as wet. This disproves the general necessary-bound guarantee for that accepted setting. It does not establish a missed real seed in the default pilot.

Fix by deriving every local patch from the actual reference raster origin and retaining gradient/5×5 halos. Check recenter phase and finite-border clipping too. Until supported combinations are tested, reject incompatible configurations or skip the shortcut for them. The new 1152 half-width happens to align with all currently allowed spacings, but geometry helpers and tests must enforce the invariant explicitly.

### A3 — Exact 4×4 raw-density land reuse is the best demonstrated remaining optimization

`native/bridge.c:208` computes land by scanning Y≥63. Both terrain shape and raw density receive floored quart X/Z coordinates. Therefore the pinned model's **land boolean is constant within each 4×4 cell**. `cache.py:60` currently caches it at individual block coordinates.

The audit driver groups these queries by floor(X/4), floor(Z/4), calculates each missing cell once, and broadcasts the boolean back to every requested block. It preserves the existing one-block output mask and negative-coordinate floor semantics. It must **not** share block-scale biome results or be retained automatically if the density model changes to interpolation/caves.

Results: ten fixed 4096-point patches gave a **92.47% reduction in the sum of per-patch median land-query times**, including grouping/expansion. The complete seed-12345 A/B reduced computed land columns **173,253 → 10,989**, coast stage **42.36 → 16.58 s**, total **65.51 → 39.72 s**. Full candidate and decision records match. The prototype lives only in `scripts/audit_system.py`.

Source derivation: [pinned density implementation](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/cave.c). This improves work reuse within the current predictor; it adds no real-world accuracy. Adopt with additional complete-seed and topology parity checks before the sweep.

### A4 — Gemini's 99.9% lower32 rejection claim fails the first relevant diagnostic

Using 256 distinct SplitMix-derived low32 values, the then-proposed 2304/640 borders, and jointly satisfiable eight-block centers, **all 256** have a raw Fortress placement. Even adding optional raw Village and Bastion existence leaves **all 256**. This is a bounded deterministic sample, not a statistical proof about all 2³² layouts, but supplies no evidence for 99.9% rejection.

The three raw scans take about a millisecond per layout through the current allocating wrapper; this is not a benchmark of Gemini's nonexistent generator-free scanner. A broad ±5000 center envelope naturally gives many placement opportunities. Village existence does not establish Stronghold existence, and neither optional family may become a mandatory filter.

The requested staged mode remains worthwhile as a **measured layout-prioritization experiment**. Rank promising layouts, allocate a finite number of high32 siblings, and run the unchanged full-seed requirements. A layout scoring cutoff is a deliberate sampling bias, not a safe absence proof. Compare unique qualifying/verified seeds per total CPU-hour, including raw enumeration, full viability, terrain, reporting and review effort.

Raw MT reuse remains limited to the eight verified families. Stronghold village viability, Trial Chamber RNG, Mineshaft handling, biomes and terrain retain full-seed evaluation. The existing `possible_required_centers()` expects required Stronghold data and cannot simply be called with Fortress/Bastion/Village records. The new mode also needs enumeration/checkpoint/readiness schemas and sibling scheduling; it is not just a CLI switch.

Independent author research also explicitly warns that a low32 Stronghold candidate may not survive in full64 siblings. Its reported BDS validation is **1.26.51.1**, not proof of our 26.52 mapping. [Ma Ehy's base-seed scan](https://minecraft-fsg.com/news/shscan.html).

### A5 — The claimed Stronghold root cause is unproved; the proposed floor fix already exists

`finders.h:999` implements floor division for negative chunk-to-region coordinates. The production village Stronghold path calls it at `finders.c:883`. Replacing it with `floordiv` is an equivalent expression for positive region size, not a demonstrated correction. Rejected truncation and snow-exclusion patches are already absent.

The initialized angle is rounded to float, while `StrongholdIter.angle` is a double. Gemini's snippet neither proves Bedrock uses its proposed arithmetic nor ensures a float accumulator merely by casting the increments. Historical float/double diagnostic variants retained the same Stronghold positions on the four calibration seeds. Changing arithmetic to fit seed -1 is unsafe without discriminating evidence; seed 9 and 12345 already falsified previous attractive patches.

Retain the current predictor and explicit incomplete-recall handling while tracing the first village-acceptance divergence. A modern matching-version generated-world check is needed to settle predictor disagreements. The official [Bedrock locate command](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/locate?view=minecraft-bedrock-stable) supports a bounded observation procedure; returned markers still need visits if structure generation/access is being claimed. No game verifier was run in this audit.

Primary code: [pinned finder](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.c), [coordinate helper and iterator type](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.h). The [older Bedrockified reconstruction](https://github.com/Earthcomputer/bedrockified/blob/master/src/main/java/net/earthcomputer/bedrockified/BedrockStrongholdStructure.java) is useful for hypotheses, not a verified modern replacement.

### A6 — Native flood-fill/DDA proposals change semantics and target little measured overhead

The one-seed profile attributes **63.74 of 65.51 seconds** to `ss_heights` plus `ss_land`. Python/SciPy morphology wrappers occupy roughly **0.044 s**; `angular_metrics` about **0.049 s**. These are one-workload observations, but do not support an expensive morphology-first rewrite.

Current coast morphology uses SciPy's default cross-shaped connectivity, while component labeling uses eight neighbors. Gemini proposes eight-neighbor morphology too, which changes the sampled frontier. A replacement must preserve structuring elements, edge behavior, coordinate expansion, stopping rules, caches and unknown states. SciPy already tracks changed pixels by default and accepts output buffers. [SciPy binary dilation documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_dilation.html).

Current rays use NumPy round-to-even sampling, outermost island exits, unknown rays, medians, gap percentiles and largest circular gaps. Fixed-point DDA is not automatically equivalent. Its proposed signature omits unknown/high-mask inputs and a complete result contract. Stopping when 46 rays miss applies to a **hard 75% threshold**; island mountain coverage is also a score, so dropping its remaining rays can corrupt rankings. Existing basin lazy bounds already use this rejection rule safely. [NumPy rounding semantics](https://numpy.org/doc/stable/reference/generated/numpy.rint.html).

### A7 — Larger caches, Morton sorting and blanket CFFI buffers are not justified first

There were **zero tile evictions in the existing 20-input pilot**. Raising 64 MiB to 128 MiB cannot recover eviction misses in that sample. Keep the memory ceiling configurable; revisit after target-border profiling. `_sample` already groups/sorts tiles. Morton order does not prevent eviction between separate candidate calls by itself.

The wrapper already passes contiguous NumPy arrays through `ffi.from_buffer`, which does not copy their data. Scratch arrays can reduce allocations, but require lifetime/aliasing tests, separate output capacity for climate/biome/height arrays, and profiling evidence. [CFFI reference](https://cffi.readthedocs.io/en/latest/ref.html#ffi-buffer-ffi-from-buffer). Do not replace safe owned arrays with reusable views whose contents change on the next call.

### A8 — Floating-point and native changes need a stricter acceptance contract

The build already uses `-O3 -std=c11 -fwrapv`. AVX2 availability was confirmed on this host, but compiler flags alone do not supply the proposed vector kernel. `sampleTerrainDensity` is in **cave.c**, not the two files named by Gemini. FMA changes rounding; results near zero density, biome boundaries and scoring thresholds need comparison. [Clang floating-point controls](https://clang.llvm.org/docs/UsersManual.html#floating-point-models).

Prefer reusing `sampleSurfaceNoise` for repeated vertical noise cells while preserving each Y-dependent density calculation, then profile again. Do not assume vertical density is globally monotone. Keep a scalar reference and safe CPU fallback; record compiler/CPU/flags/native hash in evidence. A kernel or vendor patch requires a new backend identity, full regression and new readiness.

### A9 — Selection status needs to control every shortlist consistently

Saved rejection/deferred records are useful diagnostics; they do not establish suitability for the failed category. Today early terrain failures generally lack complete candidate packets, while `reports.py` also maps some scored near misses. The initial audit proposed off-by-default diagnostic structure-only maps. **Superseded by the user's later four-category approval:** implement structures-only as an independent qualifying branch with mandatory Stronghold/Fortress, exact common-center checks, terrain `not_required`, separate scoring/counts and required-marker review. Failed island/basin records remain failures for those categories; they cannot be relabeled as terrain passes.

`apply_review()` changes `selection_status` when required website markers are unconfirmed, but does not change native `nether_status`. `distinct_rank()` uses the latter and the numeric score. The [synthetic in-memory review reproduction](runs/system-audit-2026-10-08/review-ranking-counterexample.json) shows a previously numerically ranked candidate remains in `ranked` after a review supplies no eligible required markers. The candidate still correctly says unsupported/unresolved, and the separate `chunkbase_supported` list does not certify it. This is inconsistent routing, not fabricated confirmation. Route every list through a common eligibility function.

Terrain semantics also differ by branch: basins have hard dry/flat/connected-ring checks; ocean islands have hard sampled ocean/water-majority checks; enclosed-island appearance/wood/buildability include scoring and review. The plan makes these distinctions visible and reserves final suitability for completed required evidence. It does not silently convert all preferences into new mandatory thresholds.

### A10 — Checkpoints and evidence are sound foundations, with extension work needed

Positive findings: parent-only transactional SQLite writes, exact full-seed text, bounded job submission, source/native identity checks, deterministic score ordering, full-seed viability after raw-cache reuse, map integrity hashes, and a separate website/game evidence model.

For staged enumeration, persist layout and sibling cursors and each completed full seed; never mark a layout complete merely because siblings were submitted. For safe re-exports, build reports in a temporary generation and publish only after success; current export renames the old shortlist before completing its replacement. Release the parent `batch` result payload after aggregating statistics, and eventually stream report ranking; the existing finite-2000 memory estimate remains relevant, not proof of unbounded scalability.

Readiness currently hardcodes 874 matches/six disagreements. A genuine Stronghold correction would fail that expectation unless the evidence schema distinguishes explained fixes from new drift. Resume identity also lacks installed numerical dependency/compiler details beyond the binary and source hashes; the large gate checks dependencies separately. Include a runtime fingerprint in future checkpoints. Tests validating 74-or-more passes are historical minimums, not proof that every new stage is covered.

## What the online documentation changes in the plan

It supports exact cell reuse from the pinned density equations, preserves existing floor semantics, confirms zero-copy buffer access and SciPy morphology behavior, and warns that FMA/DDA substitutions need parity work. It does **not** establish the 99.9% layout rejection claim, a modern Stronghold arithmetic fix, or a universal SIMD speedup.

The [MyGen author's border page](https://www.mygen.co.uk/project/bedrock-world-border) documents per-dimension/custom-border features. Exact 4.0.0 installation/menu/boundary behavior was not newly inspected in-game. Divisibility is arithmetic: 2304/32 = 72, 928/32 = 29; the deployment check still needs the installed add-on to confirm the menu's size convention and exact boundary behavior. Do not infer that from divisibility alone.

## Expected impact and timing

The initial audit estimate was 45–75 minutes. The initial core implementation estimate was 16–30 engineering hours. The later four-category requirement, safe early-island-bound experiment, demonstrated MT initialization fix and weighted biome diversity expand the current reserve to **26–48 engineering hours (roughly 4–6 working days)**; see the updated implementation plan. Substantial SIMD/native-coast work is optional additional work, approximately **2–5 days**; a proven Stronghold correction has an external-evidence dependency and no defensible fixed completion date.

The demonstrated exact-land optimization suggests a **25–40% analysis-time reduction target** for equivalent target-border workloads, subject to the multi-seed A/B. Border migration reduces a full 16-spaced raster from 35,721 to 21,025 samples (**41.14%**), but does not reduce every stage or preserve candidate coverage. These savings must not be added together as independent guarantees. No staged-search yield multiplier has been established.

The old 2000-input estimate was 5.92–9.60 hours, with 8.87–14.40 hours including planning allowance, plus review. A provisional optimized scenario is roughly **3.6–7.2 compute hours**, with **5–10 hours reserved**, if the new pilot reproduces a 25–40% reduction on comparable work. This is not an ETA to find a specified number of good worlds. If the staged mode adds significant sibling work or the pilot fails to improve throughput, recalculate from its actual finite budget before launch. Full assumptions and launch gates are in the [implementation plan](AUDIT_IMPLEMENTATION_PLAN.md).
