# Common-center lower32 pilot — 11 October 2026

Common-center geometry alone added **zero** whole-lower32-family rejections in
2,048 distinct layouts. Restricting the center to a source-backed superset of
possible predicted Stronghold positions added **16–17** rejections. This is a
modest improvement, not support for the 99.9% rejection aspiration.

The implementation is a shadow diagnostic. Search requirements, production raw
adapter eligibility and ranking remain unchanged. Geometry is 4000×4000
discovery, 1536×1536 Overworld deployment and 896×896 Nether deployment.

## Matched comparison

The manifest contains 2,048 dispersed lower32 values across three sampling keys
(683/683/682 inputs). Each profile uses the same layouts and borders.

- **Envelope:** required raw placements exist somewhere in the union of possible
  deployment borders. Different placements may suit different centers.
- **Common integer center:** at least one integer center inside discovery can
  accommodate all required placements simultaneously. The solver computes the
  exact feasible area over all 16 million integer centers using event slabs;
  this is not a sampled center grid.
- **Possible Stronghold center:** the common placement requirements must hold
  at one of the pinned predictor's possible Stronghold centers, derived from
  lower32. This is still a superset; full64 biome viability determines which
  village positions the predictor actually selects.

| Experimental placement profile | Envelope rejected | Common integer center rejected | Possible Stronghold center rejected |
|---|---:|---:|---:|
| Current raw Village/City/Fortress/Bastion | 77 (3.76%) | 77 (3.76%) | 93 (4.54%) |
| Add Mansion and Outpost | 77 (3.76%) | 77 (3.76%) | 94 (4.59%) |
| Expanded region-MT families | 77 (3.76%) | 77 (3.76%) | 94 (4.59%) |
| Expanded families plus four shared feature slots | 77 (3.76%) | 77 (3.76%) | 94 (4.59%) |

Expanded presence represents 13 Overworld MT families and three Nether MT
families. Desert pyramid, jungle temple, swamp hut and igloo share one raw
placement group, so the solver represents their identical presence once. The
capacity profile instead requires four distinct slots. Stronghold is handled by
the separate center-superset check. Mineshaft and the three LCG families are not
part of this raw region combination; none of these profiles claims full
all-structure/full64 eligibility.

Envelope and unrestricted common-center counts were identical within every
sampling-key cohort, not only in the aggregate. The stronger possible-center
test eliminated another 0.78–0.83 percentage points of the total pool.
It still retained more than 95% of lower32 families in this pilot.

## Why unrestricted common centers reject little

Average feasible discovery-center area was **70.05%** for the current four
families and **66.32%** with Mansion/Outpost. There is less center space, but
almost every envelope-positive layout still has some usable center.

Most additional raw families are dense. Village, City, Monument, Shipwreck,
Ocean Ruin, Portal and Treasure region widths are small compared with the
1536-block square. A square that contains complete placement regions gets their
raw candidates regardless of biome viability. Mansion/Outpost are sparser, but
their placement constraints still left a common center in every envelope-positive
layout in this cohort.

The shared feature grid has 512-block regions. A 1536-block interval contains at
least two complete regions on each axis, so the square contains at least four
complete feature regions and therefore four raw slots in this predictor. This
explains why the four-slot capacity condition added no rejection at this width.
It cannot tell whether the four different required biomes occur at those slots.

## More specific lower32 Stronghold centers

The pinned source emits regional Strongholds and three village-related
Strongholds. Regional generation uses `setSeed(uint32_t)`. Village-related
results always use a raw Village position shifted by (-4,-4); the village's raw
placement also depends on lower32, while viability depends on full64.

The additional pilot retained every shifted raw Village inside discovery plus
every regional Stronghold in the same regional halo used by `ss_scan`. This
produced **52–65 candidate centers per layout**, mean **58.40**, instead of an
unrestricted 16-million-center domain. Some are unreachable by the actual
three-Stronghold iteration; retaining them preserves the superset property.

All **892 predicted Stronghold anchors from 512 full64 inputs** were inside
their corresponding candidate supersets. Source reasoning and finite parity
support a pinned-predictor feasibility check; they do not fix existing actual
Bedrock Stronghold recall discrepancies or certify real-world absence.

## Checks at predicted full64 Stronghold anchors

The separate anchor diagnostic used 128 of the lower32 layouts with four upper32
choices each. It produced 892 predicted anchors from 512 full64 inputs. Of the
inputs, 76 had no predicted anchor and remain unresolved.

| Profile | Raw-positive anchors | Anchors failing raw placement |
|---|---:|---:|
| Current four families | 615 / 892 | 277 (31.05%) |
| Mansion/Outpost or expanded profiles | 570 / 892 | 322 (36.10%) |

Expanded placement ruled out another 45 anchors, **7.32% of the 615 current
raw-positive anchors**. Inputs with at least one raw-positive predicted anchor
fell from 346 to 329. These are anchor-level/full64-placement outcomes, not
whole-lower32 rejection percentages and not biome/terrain-qualified worlds.

## Compute cost and recommendation

The main diagnostic took **185.86 s**, including full layout enumeration,
four-profile exact area calculations, membership assertions, anchor checks and
artifact writes. The exact area solver itself took **87.00 s**, about **42.5 ms
per layout for all four profiles**. The additional possible-Stronghold-center
pilot took **67.33 s**, including another layout enumeration and the 512-input
Stronghold superset replay. Neither is an optimized presence-only search kernel
or a production throughput benchmark.

Do not add the full-area Python solver to the production lower32 sweep: its
cost bought no extra unrestricted-center rejection in this sample. A cheap,
generator-free possible-Stronghold-center predicate is the stronger next
prototype, but the small 16–17-layout gain still needs an equal-CPU comparison
against the already fast independent full64 path before promotion.

For upper32 siblings, reusing raw positions or cheap center membership may avoid
work at impossible anchors. Actual gains depend on reuse frequency, cache and
selection cost and the existing cheap native checks. The 31–36% anchor rejection
numbers are not claimed speedups. A tighter source-proved set of reachable
village-related Stronghold centers is a further investigation; full64 viability
and game-recall limitations must remain explicit.

## Verification and reproduction

- 26 focused tests passed, including 100 randomized exhaustive small-domain
  area/capacity cases, incompatible families, inclusive edges, clipped duplicate
  slots and the shifted-village/regional candidate construction.
- Unrestricted solver existence matched the previous four-family solver on 64
  layouts. Exact current-family area matched the independent existing Nether
  pair area routine on 128 layouts.
- Witnesses and all sampled Stronghold centers matched the public Fraction-based
  border membership helpers. Profile areas/rejections satisfied containment and
  monotonicity assertions.
- Manifest uniqueness, stored summaries, native/source/script identities and
  artifact hashes passed the audit. No production computational source changed
  during the pilot.

Reproduce into fresh output directories:

```sh
.venv/bin/python scripts/pilot_common_centers.py --count 2048 --anchor-low-count 128 --output runs/common-center-replay/main
.venv/bin/python -m scripts.pilot_possible_stronghold_centers --input runs/common-center-replay/main --count 2048 --output runs/common-center-replay/possible
.venv/bin/python -m pytest -q tests/test_common_center_pilot.py tests/test_master_raw.py tests/test_realm_compact_contract.py
```

Evidence: [main report](runs/common-center-2026-10-11/main/report.json),
[possible-center report](runs/common-center-2026-10-11/possible-stronghold-centers/report.json),
[integrity audit](runs/common-center-2026-10-11/audit.json),
[prior assessment](GEMINI_FRAMEWORK_ASSESSMENT.md),
[investigation backlog](FRAMEWORK_IMPROVEMENT_BACKLOG.md).
