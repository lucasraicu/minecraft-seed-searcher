# Joint Overworld / Nether border comparison — 10 October 2026

**Recommendation for the full V1/V2 target: discovery 4000 × 4000 in both dimensions, final Overworld 2688 × 2688 and Nether 1280 × 1280.** This is a conservative recommendation, not a demonstrated terrain optimum. Overworld remains Stronghold-centered; Nether uses the exact Stronghold/8 center. Fortress and Bastion remain mandatory together.

**Compact alternative: Overworld 2048 × 2048 / Nether 1280 × 1280.** It gives the highest measured structural qualifying-layout rate, reduces Overworld area by 41.95%, and retains 71.82% of the largest pair’s qualifying layouts per input. It has not demonstrated the full terrain target in this pilot.

## Matched structural benchmark

The same first **1,000 distinct signed full64 inputs** as the million pilot were evaluated in all 12 arms, three rotated/reversed trials each: **36,000 accepted diagnostic evaluations**, **30 processes × 1 native thread**. Initial discovery stayed at 4000 in both dimensions; only the final borders changed. All existing structure and biome eligibility thresholds stayed fixed. Short-run timing includes worker startup, IPC and checkpointing.

| Overworld side | Nether side | Median baseline seeds/s (range) | Qualifying layouts / 1,000 inputs | Unique qualifying seeds | Qualifying layouts/s |
|---:|---:|---:|---:|---:|---:|
| 1280 | 768 | 465.43 (463.30–470.50) | 174 | 156 | 80.98 |
| 1280 | 1024 | 421.25 (421.17–429.34) | 303 | 252 | 127.64 |
| 1280 | 1280 | 401.04 (389.81–401.83) | 357 | 294 | 143.17 |
| 1536 | 768 | 429.96 (406.65–452.57) | 232 | 204 | 99.75 |
| 1536 | 1024 | 371.66 (370.24–384.57) | 411 | 331 | 152.75 |
| 1536 | 1280 | 359.89 (354.66–361.33) | 480 | 378 | 172.75 |
| 2048 | 768 | 363.98 (351.54–365.39) | 353 | 279 | 128.48 |
| 2048 | 1024 | 286.52 (279.66–286.83) | 638 | 456 | 182.80 |
| 2048 | 1280 | 264.07 (261.69–264.68) | 752 | 521 | 198.58 |
| 2688 | 768 | 271.09 (269.84–271.11) | 504 | 356 | 136.63 |
| 2688 | 1024 | 196.85 (193.59–198.40) | 897 | 559 | 176.57 |
| 2688 | 1280 | 175.32 (167.86–175.73) | 1047 | 629 | 183.56 |

At Overworld 2688, expanding Nether 1024 → 1280 retained **150 additional layouts (+16.72%)** and raised qualifying-layout throughput by **3.96%**, while baseline input throughput decreased **10.93%**. The Nether area increases 56.25%. Nether 768 retains only **48.14%** of the 2688/1280 pair’s layouts; none of the 768 arms wins qualifying-layout throughput at its Overworld size.

The 2048/1280 alternative processes inputs **50.62% faster** and qualifying layouts **8.18% faster** than 2688/1280, with **28.18% fewer layouts per input**. Overworld 1280 / Nether 1280 retains only **34.10%** of those largest-pair layouts; its raw input rate overstates its opportunity gain.

**These are baseline rates, not terrain/BDS or sustained sweep rates.** The earlier 5,000-input discovery experiment measured 267.90 seeds/s at 2688/1024/4000. Short 1,000-input trials have different startup amortization and load balance, so compare border arms within this matched experiment rather than replacing the completed million-run measurement.

## Predictive terrain comparison

A fixed hash ordering selected **12 anchors from the union of 1,047 qualifying layouts**, plus **four additional controls from the 174 anchors qualifying in every border arm**. Selection was independent of terrain scores. The unit sampled is an anchor, not an independently sampled seed. Common controls are reported separately.

There were **38 anchor/Overworld evaluations**, using the real durable terrain scheduler, complete default nomination grid, independent V1/V2 refinement, **18 native OpenMP threads**, and resolutions **128 → 64 → 32 → 16 → 8 → 4**. To keep this quick, refinement was limited to **two nominated centers per variant**, versus production eight. Low-score refinement and halo work follow the existing deferral rules; queued work remains saved. No nomination shortcut or threshold relaxation was used.

Overworld geometry was evaluated once per eligible anchor/Overworld size and reused across Nether sizes only when that pair’s own structural baseline qualified. Nether geometry/accessibility was not measured. Source-arm baseline bonuses affect total score, so only geometry/border fit is reused, not comparative overall scores.

| Overworld side | Random union anchors eligible/evaluated at Nether 1280 | Random anchors with a finest complete footprint within border | Strict V1/V2 matches in random sample | Shared controls evaluated | Shared controls with a finest complete footprint within border | Strict V1/V2 matches in controls | Median terrain seconds/anchor across both groups |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1280 | 2 / 12 | 0 | 0 | 4 / 4 | 0 | 0 | 5.06 |
| 1536 | 3 / 12 | 0 | 0 | 4 / 4 | 0 | 0 | 5.93 |
| 2048 | 5 / 12 | 0 | 0 | 4 / 4 | 0 | 0 | 8.86 |
| 2688 | 12 / 12 | 3 | 0 | 4 / 4 | 0 | 0 | 14.85 |

**Zero strict terrain passes were found.** A pass requires `qualification=PREDICTED`, `geometry_pass=true`, a complete footprint wholly within the border, and height resolution 4. Three union-sample anchors had a complete within-border footprint at 2688, but they still failed other geometry thresholds. High scores, near matches, clipped footprints and partial halos do not count as passes.

This small, reduced-budget pilot **does not establish absence of suitable terrain**, a terrain pass-rate advantage, or optimal borders. Thousands of other centers remain pending, and some fine stages remain deferred. The random eligible subsets differ across Overworld sizes; the four common controls did not find a strict match at any size. A larger border protects more possible placements, but that is a geometric/coverage rationale rather than a measured success-rate claim.

Measured terrain work took **386.66 seconds (6.44 minutes)** in total. These per-anchor timings apply to this two-center pilot; they do not measure production eight-center cost or authoritative verification.

## Decision and next gate

Choose **2688 Overworld / 1280 Nether** when keeping the full mountain-ring and dry-basin target is the priority. Choose **2048 / 1280** only if the smaller playable area and measured structural throughput are more important than retaining all opportunities. I recommend the former for our current full terrain goal; I would not promote 1280 Overworld on this evidence.

Before adopting a smaller Overworld border or beginning the production sweep, obtain a selected finest-resolution complete-within V1/V2 prediction with adequate refinement and validate its required structures, formation, water and natural ground in actual Bedrock. This diagnostic does not close the existing authoritative-validation or sweep-readiness blockers.

Production configuration remains **discovery 5000, Overworld 2688, Nether 1024**. The recommended sizes were saved separately. No production settings changed; no production sweep or BDS verification ran.

## Verification and provenance

Repeated baseline memberships are identical, all arms discover the same anchors, narrower-border eligibility is nested, and the 2688/1024 arm exactly matches the first 1,000 inputs/qualifiers of the earlier discovery experiment. All **191 previously sealed source hashes** and production/native identities remained unchanged. The independent audit checks stored candidate imports, saved variant results, sample selection, pair-specific eligibility and pass-count calculations.

An initial exploratory timing run eagerly imported terrain libraries into spawned baseline workers. It was interrupted, corrected with a lazy terrain import, and preserved in [excluded-startup-probe](excluded-startup-probe/EXCLUDED.md). Those timings are excluded from every summary above. The separate [smoke check](smoke-report.json) is timing-only and is not part of either terrain cohort.

Native density and biome rasters are predictions from MC_26_50, not actual Bedrock 26.52 terrain/liquid/ground evidence. Structural qualification measures predicted starts/viability, not complete structure footprints or playable paths. Nothing here is actual-generation certified.

Evidence: [full report](report.json), [baseline trials and memberships](baseline.json), [sample selection](selection.json), [all terrain measurements](terrain-progress.json), [recommended target](recommended-target.json), [verification](verification.json), [independent audit](independent-audit.json). Diagnostic [script](../../scripts/measure_realm_border_combinations.py); each arm retains its configuration/checkpoint and each terrain arm retains the exact imported source candidate.
