# Combined Sol / Gemini audit — Codex review

Baseline: `54b7d631b8bdb481894980a31be16aaa02901b18`, production `dynamic-envelope-1664-v1`, Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes `MC_26_50`. This is an audit of the checked-in predictor and its orchestration. Production source, binary, policy, and settings remain unchanged. Proposed patches exist only as review artifacts and isolated experiment builds.

**Review status: complete.** Raw artifacts, all 21 Gemini claim dispositions, performance methodology, critical reproductions, and proposed-patch applicability were reviewed. Scope exclusions remain explicit.

## Verified Critical Discrepancies (P0/P1)

No P0 verified. Three P1 findings remain, all independently reproduced against the unchanged baseline. These are the earlier findings corroborated by Gemini, not three newly discovered defects. Raw final-review reproductions: [reproductions.json](reproductions.json); fuller original evidence: [prior audit](../../codex-audit-2026-10-15/AUDIT.md).

### P1: Optional structures are scored at the wrong Python candidate center

Files and verbatim anchors:

```python
# src/seed_search/realm/dynamic.py:82
        if name in OPTIONAL_NAMES:continue
# src/seed_search/realm/dynamic.py:115
            rows.append(Candidate(snapped,density,counts,deficits,radial))
# src/seed_search/realm/blueprint.py:526
                score=dynamic_score(item.counts,palette_index.luxuries(center),hub_bonus(structures,center))
```

`counts` was evaluated before snapping, and optional structures do not contribute cell boundaries. Native code correctly recounts optional structures after snapping:

```c
/* native/blueprint_dynamic.inc:454 */
        for(int k=0;k<5;k++)score+=optional_points[k]*nb_dynamic_count(&optional[k].viable,x,z,832,0,NULL,0);
```

**Numerical trigger:** synthetic fixture `(0,0,-1)`, seed label `123`, extra mask `0`, deficit depth `1`, plus one viable swamp hut `(56,-800)`. C selects center `(-752,-816)` with score **434**. The independent Python oracle selects `(-784,-816)` and finishes with score **422**. Its eastern boundary is `48`, excluding the hut, whereas the native winner's eastern boundary is `80`. Recounting optional points at each snapped Python candidate restores `(-752,-816),434`. This is a coordinate fixture, not a claim about natural world seed 123.

**Minimal fix:** immediately after `snapped=tuple(axes)`, recompute only the optional entries in `counts` using `overworld_bounds(snapped)` and exact half-open membership. Preserve mandatory counts, all lattice transitions, and the centroid policy. Gemini's proposed patch does not apply to the actual function; its suggested `+831` half-open bounds must not replace the specified `+832` exclusive bound. The core mismatch is verified without Gemini's unsupported “80-block within-cell” explanation.

The current partition preserves mandatory membership and biome witnesses. It does not establish invariance for optional counts or radial hub bonuses, and the chosen centroid representative is not a proof of global score optimality over every snapped point in a cell. Recounting restores the current native/oracle policy; expanding that policy would be a separate specification decision.

### P1: Dynamic allocations bypass the configured memory reservation

File: `native/blueprint_dynamic.inc:78`, verbatim anchor:

```c
        w->dyn_prefix=malloc(23*side*side*sizeof(int));
```

The same bypass affects event arrays, cells, biome grids, and Nether tables, including line 412:

```c
        w->dyn_cells=malloc(w->dyn_cells_cap*sizeof(NBDynamicCell));
```

**Numerical trigger:** one default survivor fixture, seed label `123`, `(0,0,-1)`, one thread, `max_buffer_bytes=1,400,000`. The batch succeeds while requested simultaneously live native allocations reach **1,872,336 bytes**, at least **33.74% over the cap**. This excludes allocator metadata and SeedContext, so the violation is conservative. Tracked live bytes return to zero after `nb_free`; it is not evidence of a normal-path leak.

**Minimal fix:** route dynamic allocations through `nb_alloc`, preserving worker reuse and the deliberately monotonic reservation contract. Reserve fixed context costs too if the cap is meant to cover every owned native allocation, or explicitly state the exclusion. Combine with failure-safe growth below. Increasing the configured cap does not repair enforcement. This review retains the prior P1 severity because a promised resource ceiling is ineffective; Gemini classified the same reproduced defect P2.

### P1: A failed growth allocation poisons reusable capacity

File: `native/blueprint_dynamic.inc:381` and `:411`, verbatim anchors:

```c
        w->dyn_ex_cap=ex_need;
        w->dyn_cells_cap=maxcells+1024;
```

These capacities are published before successful allocation is established. `nb_run` continues to another seed using the same worker **within the batch**. An equal-or-smaller request then skips growth and dereferences a null pointer.

**Numerical trigger:** two fixtures `[123,123]`, both `(0,0,-1)`, one thread, 256 MiB cap. One-shot failure at allocation **34 or 35**, each **11,696 bytes**, or allocation **36**, **77,928 bytes**, produces subprocess exit **-11 / SIGSEGV** on the next seed. These failures were rerun for this final review. The injection changes allocation success, not geometry.

**Minimal fix:** allocate replacement event buffers/cells into temporaries; if allocation fails, free temporaries and retain valid old pointer/capacity pairs; publish replacements and capacities together only after success. Keep batch failure propagation. A successful event allocation paired with a failed second allocation is still owned and freed at worker teardown: Gemini's separate asymmetric-leak finding is refuted by the one-seed failure reproduction, which returns `-3` and leaves **zero** tracked live bytes after cleanup.

## Pragmatic Architecture Verdict

**Keep C11/OpenMP and the contiguous arrays.** Each worker owns its generator/context and scratch; the output indices are disjoint. The claim counter and reservation counter are intentionally atomic. No measured false-sharing, cache-bandwidth, or memory-bandwidth bottleneck justifies padding or spatial indexes. The existing argmin avoids sorting all candidate cells. This audit does not prove every current loop is optimal.

Rust wrapping the same C/Cubiomes calls supplies no demonstrated speedup. A rewrite could improve ownership ergonomics, but that is a separate cost/benefit decision. GPU suitability has **not** been benchmarked: the conditional rejection sequence and divergent biome/viability paths make a simple throughput projection unreliable. It would be unjustified to promise a GPU gain or assert it is certainly slower. SIMD is also unproven: preserve exact floating-point noise expressions, and do not relax lattice events or bounds. The largest measured opportunity is removing redundant work before changing languages or hardware.

CFFI executes one bulk native call per batch and releases the GIL. Seeds are copied into a C array; this is **not an entirely zero-copy pipeline**. Native verdict hashing uses a direct CFFI buffer view; retained evidence is reconstructed into Python objects. These operations are separately accounted for. No evidence makes per-call FFI dispatch the principal cost at batches of 16,384. Python dictionary construction and serialization can matter per survivor, but sparse natural retention must be considered before extrapolating those costs.

SQLite WAL/FULL durability and the single parent writer remain appropriate. This assignment deliberately excludes combined generation-to-persistence and end-to-end throughput, so there is no new SQLite throughput claim. Accepted operational findings are:

- **P2 stale web cache:** `server.py` uses `SELECT count(*), max(rowid) FROM candidates`; a score/qualification update preserves that signature. Use a persistent revision or bounded refresh. WAL-file timestamps alone are not a robust invalidation proof.
- **P2 inflight over-reservation:** `native_batch.py:501–503` pops a still-owned batch then refills `pending` before completion. Configured `inflight=3` can own four ranges. Remove the early refill; retain the refill after commit/resource release. This concerns concurrent owned batches, not multiple simultaneous OpenMP calls—the native executor has one worker.
- **P2 blocked control requests:** `pause_sweep` holds `manager.lock` during `proc.wait(timeout=6.0)` and escalation. A two-second SIGINT-ignoring child delayed status **1.921 s**. Wait outside the lock and revalidate process ownership/generation before updating state.
- **Validation gap:** replay verifies evidence at C's selected center. It is not independent candidate selection. Existing mandatory fixtures do independently exercise selection, but nonempty optional boundary fixtures are needed. Empty fixture optional inventories are a coverage limitation, not production truncation.

Gemini's reported lease TOCTOU is reproducible only with its supplied unsupported interleaving: a capacity callback recovers/reassigns a range between validation and commit. The actual runners use one parent writer and an OS scan lock; the second scanner is independently rejected. The probe shows one 10-seed commit and rejection of the conflicting retry, **not double-counting**. Atomic lease validation is reasonable defensive hardening if broader ownership is intended; a production P1 has not been demonstrated. Similarly, intentionally calling the trusted `complete_range` API without a lease, simultaneous independent `claim_range` writers, or injecting SQL into the DB-free preparer does not prove a failure of the production ownership model.

All **21** Gemini entries have individual dispositions in [dispositions.json](dispositions.json). Several secondary “verified” checks only assert source substrings; they do not demonstrate the claimed failure. In particular, monotonic reservations are intentional, absent redundant Nether mask fields do not lose the 169 retained witness points, and an externally held SQLite read transaction blocking WAL reclamation is expected SQLite behavior. An unlocked runs-cache hypothesis remains unresolved without an observable bad interleaving. Dropping an unmanaged `Batch` does leak its native allocation; that is accepted as a P3 API footgun, while inspected production paths use explicit cleanup.

**Four of Gemini's five proposed patches fail `git apply --check`.** The stale-cache patch applies but still needs its invalidation strategy reviewed. None were applied. Its manifest also lists generic library paths rather than a complete binary/profile/hash identity; final performance attribution therefore uses Sol's independently frozen builds. Gemini's lazy-generator verifier tests parity but does not measure speed; its “+10% confirmed” figure repeats earlier evidence.

## Top 1–2 High-Impact, Low-Bloat Micro-Optimizations

Uninstrumented matched-PGO results (native kernel only):

| Experiment | Control median | Candidate median | Median paired improvement |
| --- | ---: | ---: | ---: |
| Remove unused surface initialization | 46,208/sec | 147,568/sec | +218.82% |
| Combine with delayed seeding | 46,208/sec | 182,471/sec | +292.80% |
| Add necessary raw Dark Forest gate | 182,715/sec | 215,413/sec | +18.51% |

Each comparison has five alternating paired trials with at least five seconds per arm; raw individual trials are in [Sol's report](../sol/REPORT.md) and [measurements](../sol/measurements.json). Gate confirmation uses a different cohort from the four-arm main comparison; do not divide those medians as though they were a directly paired total gain. Codex's additional alternating checks confirm the direction and receipt parity. The quoted production 47.8k/sec is historical; this machine's fresh control is 46.2k/sec. No checkpointed/end-to-end speed claim follows.

Retain 34 threads / chunk 16 / batch 16,384 on this host. Chunk 64 is not a demonstrated improvement; chunk 128 and smaller batches screen worse. Five long batch trials support 16,384 over 8,192. No operating-setting change was made.

Post-gate attribution is spread across the raw witness gate 23.88%, remaining Mansion inventory 22.32%, and raw preflight plus Nether 24.19% (overlapping biome subqueries must not be double-counted). Natural forced OW prefix work costs 88.593 ms median per forced input, but none of the 100k profile inputs reaches that palette, so it is not an observed aggregate bottleneck. Passing fixtures take 30.518 ms to reconstruct and 3.094 ms to serialize per retained input; their natural aggregate impact is unknown. Seed-array marshaling and verdict hashing take 1.711 ms and 0.547 ms per 16,384 precomputed inputs, outside native timing.

Only two **new** proposals are retained for adoption review:

1. [Remove unused modern Mansion SurfaceNoise initialization](../sol/proposals/no-surface-init.patch). `finders.c` builds a `SurfaceNoise` object, while the active Overworld `mapApproxHeight` branch in `generator.c:623` returns without reading it. Each initialization consumes **18,160 MT draws** plus reseeding. Remove it only in this modern branch and pass `NULL`; preserve all noise arithmetic and older paths. The previously proposed [delayed generator seeding](../sol/proposals/lazy.patch) is independently reconfirmed (+9.36% against unchanged control) and complements this change; the combined arm measures their interaction.
2. [Add the necessary raw Dark Forest witness gate](../sol/proposals/dark-gate-incremental.patch), applied after the combined initialization patch. A viable qualifying Mansion is a raw start with the exact required Y=63 witness. If too few raw starts have it, the viable subset cannot meet the goal. Positive gates retain the original complete inventory, including non-Dark-Forest viable starts. This small loop adds no index, relaxed bounds, or mathematical shortcut. Its +18.51% median paired gain is measured against the already optimized control.

The [combined initialization diff](../sol/proposals/lazy-no-surface-init.patch) contains the first change plus the prior delayed-seeding proposal. Both use newly trained source-matched PGO. Natural full/compact records, 40 explicit fixtures per retention mode, and 2,000 native component seeds—including **134 seeds with a viable Mansion**—match across all four main arms. Mansion calls are followed by Stronghold, Outpost, Fortress, and Bastion calls to test relevant RNG interleavings. Receipt comparisons supplement those positive checks; all-reject receipts alone are insufficient.

**Adoption limit:** removing `initSurfaceNoise` changes ambient thread-local MT state. The bounded pipeline reseeds subsequent relevant RNG consumers and passed the recorded interleaving checks. This is not a promise of identical post-call RNG state for arbitrary external Cubiomes callers. Review the pinned vendor change as a local integration patch, regenerate production PGO/build identity, and preserve the independently recorded parity regressions before adoption. Additional nonempty optional-component/interleaving parity passes on 262 natural inputs, including 441 positive igloo basements. No mathematical tolerance, half-open interval, raw lattice event, score milestone, or retained inventory was altered in these experiments.

## Production Readiness Sign-Off

**FAIL for unconditional readiness in the audited scope.** The three reproduced P1 discrepancies remain present. The audit identifies small, promising performance changes, but speed does not repair the oracle, reservation, or allocation-failure issues. This sign-off covers the checked-in predictor/orchestration and isolated validation only; it does not certify excluded end-to-end persistence behavior, live sweep stability, or actual BDS world generation.

Audit completion does not mean implementation completion. No production change is being made by this handoff, and no claim is made that all possible bottlenecks, bugs, or speedups have been exhausted.
