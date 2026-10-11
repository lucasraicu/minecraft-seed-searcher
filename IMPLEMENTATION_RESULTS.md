# Approved implementation — 8 October 2026

The approved core implementation and bounded verification are complete under `runs/implementation-2026-10-08`. **Reference search is recommended; both modes are available.** The production sweep is unstarted. Conditional Stronghold/SIMD/island-filter work remains deferred as explained below.

| Change | Result / intended effect |
|---|---|
| Geometry | 2304 Overworld / 928 Nether, one selected eight-block Overworld center; Nether center divided by eight. Full 16-spaced landscape grid is 145² instead of 189². This changes eligibility as well as cost. |
| Four categories | Independent structures-only, enclosed inner island, ocean island and dry mountain basin lists. Structures-only has its own two-center budget and `terrain_status: not_required`. |
| Required structures | Stronghold and Fortress in the same center's exact squares. All other supported structures remain preferences; optional Bastion contributes at most two base points with the default weights. |
| Native correctness | Explicit thread-local MT initialization fixes cold seed -1 Mineshaft results; state save/restore preserves initialization. No coordinate exceptions installed. |
| Terrain correctness | Basin necessary bounds preserve the reference lattice and recenter/gradient halos. Coast reuse keys include the actual request bounds and sampling policy. |
| Quart land reuse | Exact raw-land classification shared by quart X/Z cell, original request order restored. Height and block-biome samples keep their own coordinates/strides. |
| Biome ranking | Editable resource-family weights, sampled extent/support, border clipping and separate surface/Nether inventories. Up to five extra points; base maxima stay 30 / 100. Cave coverage is explicitly unmeasured by default. |
| Staged search | Bijective finite low32 enumeration, eight audited raw MT families, raw Fortress feasibility, 48 top + 16 exploration layouts, four distinct upper32 siblings each. Full64 viability, Stronghold/Trial Chamber/Mineshaft and terrain repeat per sibling. |
| Recovery / resume | Raw selection cursor and exact completed full64 indices checkpointed; small sibling batches preserve raw-cache locality. Changed predictor/configuration identities reject incompatible resumes. |
| Reports | Per-category rankings and interval review lists, eligibility independent of optional score uncertainty, atomic report-generation switch, separate deferred seed lists and decision JSONL. |
| Readiness | New schema validates both raw and full64 budgets, runtime/source/native identity, measured comparison subrecords and artifact hashes. Historical readiness is incompatible. Publication validates a temporary record before atomically replacing the active seal. |

## Conditional proposals

**Early island hard rejection stays disabled.** The implemented shadow bound conservatively covers every center the finite coast patch could return and checks required-structure window compatibility. Coarse diameter and enclosure targets remain scoring preferences; they cannot justify rejecting an island. The shadow record never short-circuits coast work. A useful hard terrain proof has not been established.

**SIMD stays deferred.** The pre-implementation test found density drift with FMA, a slower four-Y kernel after exact reuse and only 2.6% serial gain from strict AVX2 flags. See [SIMD_TEST_RESULTS.md](SIMD_TEST_RESULTS.md). Production keeps the scalar native kernel and original floating-point policy.

**Stronghold root correction remains unresolved.** Private diagnostic traces cover -1, 0, 12345, 4294979641 and held-out 9. They expose RNG draws, angle steps, candidate ordering and village-biome acceptance and match the installed path. They do not supply an independent modern generator trace at the first divergence. The known discrepancies remain visible; fast exclusions are deferred for bounded `review_all` recovery.

## Verification record

Completed:

- Full unit/native suite: 141 tests pass in 102.23 seconds.
- Supported editable native rebuild, installed vendor license, all pinned vendor hashes and all locked dependency versions match.
- Frozen 880 structure / 159 coordinate comparisons match the versioned expectation: 874 unique typed correspondences, six known disagreements, no new drift. Height MAE 1 / maximum error 5 against the recorded external fixture.
- Cold/warm/threaded Mineshaft and native MT state-save/restore controls pass.
- Fresh matching-version browser evidence confirms both required markers for 12853964 and high-bit seed 4294979641 at the new borders. These are structures-only controls; no terrain suitability or actual Minecraft observations are inferred.

The two predeclared keys × two 256-input modes and all three alternating-order 20-control quart comparisons are complete. Quart reuse preserves all prediction payloads exactly; median wall/CPU savings are **26.4% / 25.0%** on that chosen cohort. The 1/8/12 requested-worker comparisons and interruption after five staged completions match exactly. The raw-phase interruption test also passes. The 20-seed full-map pilot (five completions then resume) matches its independent 20-seed repeat exactly; actual pilot worker counts are 5 then 12. It saves 132 centers: 40 structures-only, 52 enclosed islands, 40 ocean islands and no basin. The chosen controls are not a yield estimate. Fresh required-marker reviews support two structures-only candidates; optional-score uncertainty keeps them in interval-review lists. Representative maps for all four categories pass visual geometry/schema inspection; the separately rendered basin is still an unconfirmed terrain prediction.

## Mode decision

Keep **full64 reference** as the recommended default. It produced more qualifying predictions per CPU-hour in every category for both independent keys. Staged search remains implemented and available with a bounded command. Across the two arms per mode, reference used **9.2% less measured CPU** and **22.1% less wall time**. These percentages compare the two implemented modes, not the old search to the new search.

| Run key / mode | Wall minutes | Worker + raw CPU hours | Structures-only | Enclosed island | Ocean island | Basin |
|---|---:|---:|---:|---:|---:|---:|
| 0 / reference | 21.71 | 4.174 | 256 | 247 | 221 | 1 |
| 0 / staged | 28.25 | 4.657 | 256 | 246 | 220 | 0 |
| 11400714819323198485 / reference | 22.19 | 4.294 | 255 | 238 | 211 | 1 |
| 11400714819323198485 / staged | 28.11 | 4.668 | 255 | 245 | 224 | 1 |

Each row evaluates 256 full seeds; category counts are unique qualifying **predictions** within that arm and overlap between categories. The timed renderer policy is identical and excludes PNGs. Staged arms each pay for 10,000 raw layouts (9,996 raw-Fortress-feasible), retain 48 top plus 16 exploration layouts and expand four siblings. Neither arm establishes verified terrain yield or recall. Shared-host activity can affect wall time; measured worker/raw CPU is the primary comparison. Detailed costs, diversity proxies, selection cohorts and limitations are in `mode-comparison.json`.

The shadow island bound would defer 26 of 5,574 nominations (0.47%), based on predicted required-window compatibility. It proves no terrain impossibility and has not earned promotion to a hard filter. Both known-code and unknown-Stronghold cases still run through the full coast path.

The workflow is documented in [SEED_SELECTION_WORKFLOW.md](SEED_SELECTION_WORKFLOW.md); the approved contract and historical forecasts are in [AUDIT_IMPLEMENTATION_PLAN.md](AUDIT_IMPLEMENTATION_PLAN.md).

## Recovery and current costs

The four matched seeds (-1, 0, 9, 4294979641) produce four additional unresolved island centers under `review_all`, with no additional native-eligible centers. Recovery uses 298.25 worker CPU seconds versus 204.42 in fast mode. No fast-only centers occur in this cohort. This is finite scheduling/evidence coverage, not a generated-world recall measurement. New centers need required-marker review.

The chosen pilot's worker-time shares are preliminary terrain 34.1%, landscape 28.9%, coast 20.7% and structures-only 14.0%. Native height calls account for 91.1% inclusively across those stages; do not add that percentage to the outer stages. Additional batched biome-point calls take 0.064 seconds over the pilot, while the structures-only height-following resource inventory is substantial. This separates cheap known-coordinate lookup from finding the surface.

The interrupted/resumed pilot takes 347.03 seconds, including 143.90 seconds for partial plus final exports; the independent repeat takes 301.07 seconds. Report depth is bounded, so multiplying this small pilot's entire cost per seed by 2000 overstates fixed export work. Use the two independent 256-input reference arms for analysis throughput and add export cost separately.

## Finite sweep ETA and handoff

| Command budget | Measured basis | Reserved elapsed time on this machine |
|---|---|---|
| Recommended reference: 2000 full seeds, 12 workers | 21.71–22.19 minutes per 256 inputs, approximately 2.86 hours extrapolated analysis/export-lite work, plus cold map export and variability | **3–5 hours** |
| Experimental staged: 10000 raw layouts → 256 full seeds, 12 workers | 28.11–28.25 minutes per arm including raw scan, plus map export and variability | **35–50 minutes** |

Manual website/game review is additional. This host has 18 physical cores and 64 GiB RAM. Completed reference arms decode to roughly 1.03–1.04 MiB of result objects per seed, or about 2.1 GiB at 2000 inputs; this is an extrapolation, not measured total parent RSS at 2000. Worker peak RSS in the mode arms is below 667 MiB, with a 64 MiB tile-cache limit. Parent decoding/serialization and other applications need additional memory.

Start/resume/recovery commands: [SWEEP_COMMANDS.md](SWEEP_COMMANDS.md). Current evidence gate: [SWEEP_READINESS.md](SWEEP_READINESS.md). Both future sweep output directories remain absent; finite command checks do not start them.
