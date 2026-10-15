# All-structure combinations at the selected Stronghold border

Recommendation: retain direct full64 existence checks and the lower32 placement logic already inside them. Do not add a separate lower32 gate to the current search. Requiring more structures made viable worlds rarer, but did not make the separate placement pass faster in these matched pilots.

## Inputs and comparison

Reused the frozen, disjoint tuning (436) and holdout (460) layouts from the selected-Stronghold pilot: 896 distinct full64 inputs. Each center was the first discovered Stronghold in sorted order, fixed before filtering. Discovery was 4000×4000, deployment was 1536×1536 Overworld and 896×896 Nether with the exact fractional center/8 conversion. Production still evaluates its discovered anchors independently; its requirements and selection were not changed.

Four combinations were timed, plus 20 increasing prefixes of the all-structure combination. The 21-family profile requires all 18 supported Overworld families (including the previously discovered Stronghold) and all three Nether families. End cities were additionally queried in the End dimension using a diagnostic 1536-square window at the same selected X/Z center; this is not an adopted End border. All 22 exposed families were therefore covered. Unsupported features such as dungeon/monster-room generation are outside this adapter.

Direct checks stop at the first missing viable witness. The current four-family path retains its combined Fortress/Bastion scan, then City and Village. Other profiles use a greedy cost/rejection order learned only on tuning and frozen for holdout. For the all-structure profile, the first five checks were Outpost, Fortress, Bastion, Swamp Hut, Jungle Temple; subsequent checks were never reached once those eliminated every layout.

The initial comparison used the optimized native four-family raw gate and the existing complete raw scanners for expanded combinations. A second comparison removed unnecessary raw enumeration: the 16-family raw conjunction reduces here to the four-family gate plus minimal first-placement Outpost/Mansion checks; all other audited families have placement guaranteed at these widths. A cached arm reuses only equal lower32 plus exact Overworld/Nether bounds. Its cache starts empty on every replay, so construction, misses and hits are charged. There were 624 distinct keys among the 896 layouts (272 repeat queries). Native identity is fixed per run.

Six counterbalanced trials per arm, eight replays per trial, with equal warmups and precreated native handles. These rates are conditional structure-stage layouts/second on one process, not complete search seeds/second; discovery, context setup, biome inventory, terrain, persistence and actual world generation are excluded.

## Held-out speed

| Required combination | Direct layouts/s | Cached minimal lower32 gate + direct, layouts/s | Added time |
|---|---:|---:|---:|
| Current four | 8,150 | 7,188 | 13.39% slower |
| Current four + Mansion/Outpost | 11,532 | 9,229 | 24.95% slower |
| All 16 audited MT placement families | 21,012 | 14,697 | 42.96% slower |
| All 21 Overworld/Nether families | 20,863 | 14,433 | 44.55% slower |

The uncached minimal gate was 19.61%, 37.58%, 66.49% and 65.45% slower respectively. The native four-family gate alone was 19.60%, 24.24%, 42.08% and 41.78% slower in the first comparison. Expanded complete raw scanners were substantially slower still; their list-allocation cost is not evidence about the speed of a future fused native implementation.

## Rarity and seed bits

| Required combination | Missing necessary raw placements, holdout | Viable combinations, holdout |
|---|---:|---:|
| Current four | 119/460 (25.87%) | 82/460 |
| Current four + Mansion/Outpost | 131/460 (28.48%) | 0/460 |
| All 16 audited MT placement families | 131/460 (28.48%) | 0/460 |
| All 21 Overworld/Nether families | 131/460 (28.48%) | 0/460 |

Combined tuning and holdout, the current four had 169/896 viable positives; the expanded six, 16-family and all-21 profiles each had zero. Zero observed positives does not prove these combinations impossible. Adding the End control also had zero positives; End-city witnesses themselves were positive at all 896 diagnostic windows.

The 99.9% lower32-rejection aspiration was not reached. All 16 audited MT families together removed 32.48% of combined layouts by raw placement, versus 28.79% for the current four. The extra families added only 3.68 percentage points. Most families already have raw candidates guaranteed at this width, and pyramid/temple/hut/igloo share one placement grid. Their distinct biome requirements create full64 rarity without creating independent lower32 constraints.

A direct first-witness detector already performs raw placement and then tests full64 viability only as needed. A separate raw gate repeats placement/wrapper work on positives and cannot reject worlds whose candidate placements fail only because of biomes. Trial Chambers, Trail Ruins and Abandoned Camps need lower48 placement information in this pinned version; Stronghold discovery and biome/terrain checks require the full seed. A failed exact-center query never rejects all upper32 siblings, since their discovered centers and viability can differ.

## Per-family timing

Unconditional first-witness queries were collected for every family, including families that an early rejection would normally skip. The most expensive mean holdout calls were:

| Family | Mean microseconds/query | Positive holdout layouts |
|---|---:|---:|
| buried_treasure | 712.4 | 445/460 |
| shipwreck | 316.2 | 345/460 |
| monument | 305.6 | 133/460 |
| mansion | 271.9 | 3/460 |
| ancient_city | 135.2 | 129/460 |
| end_city | 135.2 | 460/460 |
| mineshaft | 108.5 | 460/460 |

These are measured first-witness queries in the current predictor, not claims of verified in-game coverage. Complete inventory remains inappropriate for a pure existence requirement. No production detector or required structure mix was changed for this experiment.

## Verification and next work

18 focused tests passed. The main pilot recorded 15,008 comparisons with zero differences: raw-presence agreement with the prior frozen layouts, viable-witness membership in raw layouts, and first-witness versus complete viable detection for 32 sampled layouts across all 21 queried families. The minimal gate added 2,688 raw-presence comparisons with zero differences. Every timed replay returned the same final decisions as direct checks; timing repetitions do not add independent seeds.

These checks establish parity against the pinned predictor, not independent Bedrock-world accuracy. The 128 parent inputs without discovered Strongholds remain unresolved and are outside this conditional stage.

Next candidates: fuse selective placement rejection into the native viable-witness scan; reuse raw candidates only for genuinely equal lower32/center/version keys; test a lower48 tier for LCG families with full64 viability. Adopt only after held-out equal-budget useful-yield improvement. Do not require unwanted structures solely to manufacture rarity.

Evidence: [main report](runs/all-structure-combinations-2026-10-11/report.json), [minimal/cached gate timings](runs/all-structure-combinations-2026-10-11/minimal-gate-timing.json), [identity](runs/all-structure-combinations-2026-10-11/identity.json), [main script](scripts/pilot_all_structure_combinations.py), [minimal gate script](scripts/pilot_minimal_raw_gate.py).

## Multiplicity follow-up and diagnostic boundary correction

Reanalysis of the saved raw layouts shows stronger necessary rejection when multiple copies are required for each audited MT family. Holdout raw-capacity rejection was 28.48% for one each, 95.65% for two each (20/460 survive), and 100% observed for three or four each (0/460 survive). Tuning survivors were 276/436, 14/436, 0/436 and 0/436 respectively. Four shared feature types require 4×the per-type copy count in distinct slots; a candidate is never counted four times as a viable structure. These results do not include lower48 placement counts, multiple Strongholds or an adopted End border, and are not a count-detector speed benchmark. Zero survivors in this small cohort does not establish global impossibility or a 100% rejection rate.

Source inspection also identified that Outpost raw coordinates have a +0 block offset while Mansion coordinates add +8. The diagnostic full-offset-rectangle shortcut now distinguishes them. Production placement code already used the correct rules. All 2,688 frozen-layout presence comparisons still pass with zero differences; 19 focused tests now include both offsets and a boundary case that would expose the earlier assumption. Earlier timing results remain historical measurements of the [preserved timed source](runs/all-structure-combinations-2026-10-11/minimal-gate-timed-source.py), whose hash matches the timing artifact. No new timing claim is made for the correction. See [multiplicity and boundary audit](runs/all-structure-combinations-2026-10-11/multiplicity-and-boundary-audit.json).

## Completed native count and biome-diversity pilots

The [multiplicity and seed-bit follow-up](MULTIPLICITY_SEED_BIT_RESULTS.md) now
implements the requested direct stopping after N viable starts versus fused raw
capacity, with retained candidates/cursors and a paid bounded cache. At two of
every Overworld/Nether structure, holdout conditional throughput rises from
71,880 layouts/s direct to 91,839 fused32 and 119,910 cached32, with identical
reference decisions. At one each the gate remains slower. Lower48 adds no raw
rejection through N=4. Discovery-included input throughput is only about
1,700–1,900 seeds/s and the small gains change sign across cohorts, so this is
not evidence of a major complete-search acceleration. All combinations requiring
every structure still yield zero viable worlds in the sample.

The follow-up also covers all active biome IDs and counts distinct variants
within each canonical family, using the full64 seed. This newer fused count
benchmark does not replace the historical separate-gate measurements above;
the method, requested counts and measured stage differ. Production requirements
and the production native extension were not changed by these pilots.
