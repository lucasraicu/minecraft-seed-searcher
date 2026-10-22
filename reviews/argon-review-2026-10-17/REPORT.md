# Review of Argon proposal — 2026-10-17

## Verdict and scope

Useful research ideas, but **not an implementation-ready or verified performance audit**. Several recommendations duplicate existing work; several others would change search semantics or silently discard qualifying seeds. The numerical speed, retention, recall, and query-latency forecasts are not established by the supplied evidence.

Reviewed the supplied 539-line proposal against the current local source and existing benchmark artifacts. The checkout contains uncommitted changes: this review describes the inspected working tree, not only HEAD `02f041e`. No proposed implementation, commit, push, GPU benchmark, or fresh end-to-end benchmark was performed. `checks.json` records small mathematical counterexamples and sizing calculations, not Minecraft-world validation. Its attachment hash identifies the reviewed document.

## Findings requiring correction

### 1. High: the proposed coarse biome rejection has no recall guarantee

Proposal line 82 rejects seeds based on a 5×5 grid at stride 256 before dense sampling. Absence from those samples does not establish absence elsewhere. A rare biome witness at (64,64) can appear on a 64-block lattice and be missed on a 256-block lattice. This is a counterexample to the inference, not an observed failing Minecraft seed. Fixtures alone cannot prove the inference safe.

Use sparse samples to prioritize work or confirm positive evidence. Reject only with a valid upper bound on the final criterion, or explicitly offer an approximate mode with measured missed-hit rates. Also, five positions separated by 256 span 1024 blocks, not a 2048-block side.

### 2. High: local Top-K does not produce the claimed global Top-K

Proposal lines 152/184 retain 4,096 results per worker and merge into global pools of 50,000. If the best 50,000 all occur on one worker, 45,904 can be lost. The exact merge identity requires each worker to retain at least the global K under the same fixed total ordering, or a lossless spill/refill protocol.

Small reproducible example: worker A has [100,99,98,97,96], worker B [5,4,3,2,1]. Local top-2 pools cannot reconstruct global top-5. Population-dependent Pareto ranks also require a separate merge argument; they are not fixed scalar keys.

### 3. High: catalog coverage conflicts with existing hard filters

The current v3 search enforces a conjunction of blueprint requirements. A seed excellent for a specialist query can fail that conjunction before any proposed catalog bucket sees it. Three jungle temples do not rescue a seed already rejected for another mandatory structure.

A broad customer catalog needs its own eligibility contract and union of query-safe gates. Its survival rate and feature-extraction cost must be measured independently. Tightening a GPU filter on the server with fewer CPU cores changes which results survive; balance queues and work allocation instead if identical search semantics are required.

Neither finite archetype heaps nor fixed diversity cells prove >99.5% recall for arbitrary preference combinations. For example, axis objectives prefer (10,0) and (0,10), while equal weights prefer (6,6); retaining only the axis winners loses the balanced winner. A recall percentage requires a defined query distribution and exhaustive reference corpus. “100% specialist recall” is only defensible for precisely defined predicates evaluated completely on every eligible seed and center, with every match retained; it is not a guarantee of Bedrock-world accuracy.

### 4. High: geometry, center storage, and ranking semantics would change

The proposal repeatedly calls 1664/2048 radii; the current blueprint uses window side lengths. Radius-based feature fields would describe different areas. Preserve the 4000×4000 search envelope, playable-window dimensions, half-open capture boundaries, and center-domain contract explicitly.

The proposed int16 chunk coordinates cannot represent current 8-block center refinement exactly. Store block coordinates where range permits, or an explicit 8-block unit with schema/version metadata. One center optimized for the current policy also need not be optimal for a different player's weights: retain alternate centers or regenerate and optimize for the actual query.

Replacing ordinary radial distance with squared distance preserves a single radius test, but not sums or means: distances [0,10] have mean 5 versus 6 for [6,6], while squared sums reverse the order (100 versus 72). The current weighted radial tie-break intentionally uses `hypot` in [native/blueprint_dynamic.inc](../../native/blueprint_dynamic.inc), around line 274. Existing hub threshold predicates already use squared distances.

Likewise, bounding all available structure instances is not equivalent to requiring at least N instances. Correct feasible-center reasoning must account for qualifying subsets, not force every outlying instance into the window. Existing raw preflight and native raster refinement already address substantial parts of the proposed center work (same file, lines 851 and 935).

### 5. Medium: the MT baseline is stale; the optimization remains an experiment

The claim that every relevant call fully initializes 624 words is inaccurate for this checkout. [mt.c](../../vendor/cubiomes-bedrock/mt.c), lines 104–116, already contains lazy/short initialization; [filters.inc](../../native/filters.inc), lines 11–25, already has small-state first-output and four-lane helpers. Regional placement uses the short path through the MT wrapper.

Broader specialization may still reduce memory traffic. It requires a draw-count and fallback audit, exact parity for seed/coordinate boundaries, and measured compiler output. The initialization recurrence still performs roughly 400 dependent steps; “eight registers” is not a measured compiled resource count or an end-to-end speedup. The first four twisted outputs also require the relevant initial successor words, including s4, not merely s0–s3.

### 6. High: lower-bit reuse is overstated

Some raw placement computations can reuse lower-32 results; biome generation, viability, and stronghold discovery cannot all be treated as the same lower-32 function. Some structure families use lower-48 dependencies. The existing [stronghold report](../../docs/historical_reports/LOCKED_STRONGHOLD_LOWER32_RESULTS.md) explicitly limits its conclusions.

Combining lower 32 bits with only upper 16 bits covers 2^48 seeds, or 1/65,536 of the full 64-bit domain. Full sibling coverage requires upper 32 bits; [seeds.py](../../src/seed_search/seeds.py) already implements that distinction. Limited sibling sampling can be intentional, but must not be labeled exhaustive full-64 search. The proposed 10–25× speedup needs evidence including discovery and full-seed validation costs.

### 7. Medium: the compact record fits 64 bytes, but does not support all promised exact queries

Four-bit counts saturate at 15; exact higher-count filters and rankings require overflow information. Quantized nearest distance needs conservative filtering followed by exact checks. A nearest-distance field cannot answer whether the third temple is within a specified distance. One biome mask and a few proximity bits cannot encode all spatial relationships.

Exact verification of an initial top-25 pool does not guarantee the exact top-5: candidates outside that pool can overtake them after reconstruction. Use adaptive fetching and valid score bounds, or label the retrieval approximate. Version and verification fields must distinguish generator identity from actual in-game verification. New feature extraction on retained seeds cannot recover previously discarded seeds.

### 8. Medium: storage redesign is plausible, but the stated bottleneck and durability proof are missing

Current survivor persistence is already sparse: [native_batch.py](../../src/seed_search/realm/native_batch.py), line 626, calls [store.py](../../src/seed_search/realm/store.py)'s `prepare_retained_range`, preserving coverage receipts without a candidate row for every rejected seed. Measure write time before replacing it.

Immutable worker segments and later columnar compaction are reasonable catalog experiments. Rename and SQLite completion are separate operations with a crash window; specify idempotent shard identity, fencing against stale workers, durable manifest/directory handling, restart reconciliation, and compaction deduplication. Buffered writes alone do not prove exactly-once processing or zero duplicates. Compaction also adds I/O beyond initial ingestion.

`read_binary_sseg` in the example is an unimplemented custom reader, not a demonstrated drop-in DuckDB facility. DuckDB's documented [raw-file reader](https://duckdb.org/docs/lts/guides/file_formats/read_file) returns file contents; the custom record decoder still needs implementation and validation.

### 9. Medium: retention and performance numbers are forecasts, not measurements

A 99.96th-percentile trigger retains 0.04% for one continuous metric. The union across metrics is not generally 0.04%. Under illustrative independence, 24 such triggers retain about 0.956%, and 72 about 2.839%. Real correlations and ties must be measured. An unbounded specialist bucket also prevents a hard total-storage guarantee.

The arithmetic 36 billion × 0.1% × 64 bytes = 2.304 GB is correct. The assumed retention, compression ratio, bitmap memory, and latency are not established by that arithmetic.

The existing [native refinement benchmark](../native-refinement-2026-10-16/benchmark.json) records roughly 116,582 seeds/s for its native screening kernel and 104,333 seeds/s for durable processing. These historical runs predominantly rejected seeds and retained none; they are not accepted-world/catalog throughput, nor a fresh measurement of today's dirty checkout. They provide no evidence for 4.5–9 million CPU seeds/s or 345–530 million fleet seeds/s.

At 850,000 late candidates/s and 240 fully available CPU cores, the entire CPU budget is about 282 microseconds per candidate before orchestration overhead. Measure the actual conditional late-stage cost. Model throughput as bounded by GPU raw checks, CPU survivor validation, and storage bandwidth; distinguish raw placement calls, lower-32 families, full-64 seeds screened, and fully validated retained results. Do not multiply speculative stage speedups together.

A 16×24 dense score matrix requires 384 scalar multiply-adds; even eight-lane AVX2 requires at least 48 vector FMAs before reductions and heap updates, not the claimed 16. Reconstruction and map generation in 0.11–0.15 ms and end-to-end queries below 8 ms likewise require representative measurements. GPU register occupancy and speed depend on compiled kernels and workload; the [NVIDIA Volta tuning guide](https://docs.nvidia.com/cuda/archive/11.4.4/volta-tuning-guide/index.html) does not establish the proposal's throughput predictions.

## What to keep and how to proceed

1. Keep CPU-first profiling, exact cheap gates before expensive work, bounded-output RNG specialization experiments, and cache reuse restricted to proven seed dependencies.
2. Keep the distinction between one blueprint leaderboard and a broad preference catalog. Evaluate a separate catalog prototype against exhaustive small-corpus queries before changing production admission.
3. Establish a reproducible current-source benchmark with source/build identity, fixed cohorts including survivors, stage costs, memory, and durable throughput. Add query workloads and p50/p95/p99 timing if catalog serving becomes a requirement.
4. Require zero semantic drift for exact optimizations: compare placements, validity, accepted seeds, centers, scores, and restart results with the existing reference. Any approximate mode needs explicit recall measurements and user-visible semantics.
5. Fix Top-K capacity/merge, coordinate units, count overflow, version identity, and crash recovery before scaling storage or deploying distributed workers.

This proposal does not establish optimal center weights. Weight quality still requires player preference evidence and sensitivity analysis; computational optimization cannot determine that utility function. Preserve the existing weight-research track and separate scoring-policy experiments from performance changes.
