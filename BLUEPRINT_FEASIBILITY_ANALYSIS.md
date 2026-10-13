# Blueprint feasibility and playability audit

Research audit, 12 October 2026. This document evaluates `MASTER_SEED_BLUEPRINT.md`; it does not adopt or change production requirements. All local count evidence below is **pinned-predictor evidence**, not certification of generated Bedrock worlds.

The proposed floors are individually compatible with the retained placement bounds, and several substantial subsets have concrete positive examples. **The complete structure + exact biome + terrain conjunction has not been demonstrated. Its probability, expected search volume and verified-world runtime are not statistically identifiable from the historical evidence.** The blueprint's 1-in-1.2–1.8-million rarity and 35–50-minute leaderboard promise are assumptions, not measured results. Some literal interpretations of its coastline specification are geometrically impossible.

## Geometry and version corrections

* The Overworld contains 2,359,296 horizontal block columns. A 75–85% land share is **1,769,472–2,005,401.6 area units**, not 1.9–2.0 million throughout. For discrete columns the upper count must be rounded down. At ten players that is roughly 177,000–200,500 land columns each before common infrastructure, inaccessible terrain and protected areas. Area alone does not establish suitability for ten players.
* A full-length ocean strip of width `w` occupies `1536*w` area; even with every remaining column land, land share is at most `1-w/1536`. At 250 blocks it is 83.72%; at 400 blocks it is **73.96%, contradicting the 75% minimum**. Width must be at most 384 to permit 75% land and at most 230.4 to permit 85% land. The 250–384 subset remains compatible with some of the 75–85% interval. A partial coastal quadrant avoids the full-edge calculation, but needs a specified length/area. Additional inland water reduces these maxima further.
* Total land fraction and the area of the largest connected mainland are different predicates. Islands can increase the former without helping the latter. Define water, natural ground, connectivity (including diagonal adjacency), minimum neck width and the permitted disconnected fraction. No-enclosed-mountain-ring, rolling terrain and sheer ocean cliffs also require terrain/topology predicates, not biome names alone.
* A 1536-square is 96 chunk widths and three 512-block widths, but centering it on a Stronghold does **not** align its boundaries with chunks or512-block regions. An unaligned half-open interval can intersect 97 chunk columns and four 512-block regions per axis, even though its length is 96 chunks. Preserve exact half-open membership and actual structure starts; length arithmetic is not boundary alignment.
* `(0,0)` is the coordinate origin; actual world spawn must be measured. A discovery square around the origin must not be described as centered on observed spawn unless verified. Center-to-edge distance 768 is the perpendicular distance; center-to-corner distance is about 1086.1. Covering 768 blocks in 75 seconds requires 10.24 blocks/second before terrain detours. The blueprint supplies no movement-mode measurement supporting its sprint claim.
* Bedrock Strongholds do not obey the blueprint's guaranteed Java-style first ring. Mojang distinguishes Java rings from Bedrock's random distribution. The pinned implementation searches village-associated starts outward when local searches fail (`nextVillageStronghold`, `finders.c:851` onward), plus static regional starts. Its radius can therefore exceed the initially proposed range. The historical 1024-input pilot found 128 without a discovered anchor; these remain unresolved because recall is incomplete, not proved Stronghold-free worlds. A 4000-square cannot be advertised as a certified three-Stronghold guarantee. [Mojang Stronghold description](https://www.minecraft.net/en-us/article/stronghold).
* A 896-square can intersect 4–9 Nether 480-block grid cells, depending on phase. Partial cells need not contribute starts inside it; placement/type/biome checks also matter. Intersecting cells does **not** guarantee multiple Fortresses and Bastions. The two types share the pinned placement family and compete for slots. Their counts must be tested together.
* Exact Nether center is `SH/8`, retaining fractions and negative-coordinate semantics. An896-square Nether maps to a 7168-square Overworld footprint, much larger than 1536. Portals placed near its outer parts can link outside the intended Overworld play area. Border enforcement and portal policy need an explicit Realm design; geometric search bounds alone do not enforce gameplay boundaries. The stable Bedrock command catalog does not list Java's `/worldborder`. [Microsoft command catalog](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/commandsreference/examples/commandlist?view=minecraft-bedrock-stable).
* “Bedrock1.21+” is not a reproducible generation target. Local configuration is target26.52 / BDS1.26.52.3, while `native/bridge.c` calls the pinned `MC_26_50` model. Vendor commit is `294c72ab0392dd818a91d293dbd5774d4874d64b` (`vendor/backend.json`). Existing actual-game Stronghold recall and Ancient City/Bastion disagreements remain open. Pin an exact game build and generation settings for any delivered candidate; updates need their own compatibility evidence.

## Every structure floor and higher counts

The holdout column below comes from 460 first-selected Stronghold layouts in the earlier correlated-sibling pilot. It is a marginal count, **not a joint probability or an independent 460-seed population estimate**. Historical maxima came from the896-layout pilot or current-size crops of the million run as specified in the linked reports. Start origin inside a border does not guarantee all generated pieces, loot rooms or access routes fit inside it.

| Requirement | Retained evidence | Feasibility and higher-count interpretation |
|---|---|---|
| Stronghold1 at center |460/460 selected layouts necessarily have the selected predicted anchor;128/1024 inputs lacked a discovered anchor |Conditional tautology, not discovery success guarantee. Verify actual start, portal room and usable route in the target build. More Strongholds are unnecessary for this anchor definition. |
| Mansion1 |3/460 have≥1;0/460 have≥2; pilot viable maximum 1; placement ceiling 4 |Individually demonstrated, highly selective in this sample. No two-mansion example retained. This is a major likely bottleneck but its conditional rarity after other checks is unmeasured. Mansion viability can accept pale-garden surroundings in the pinned newer model; separately enforce the requested Dark Forest. |
| Villages5 |92/460≥5 in the exact-floor reanalysis;162/460≥4; cropped observed maximum 10, ceiling 16 |Floor5 and jackpot6–8 have individual positive evidence, but all-blueprint coexistence is unproved. Village abundance needs eligible terrain;75–85% land does not guarantee it. Five villages do not certify population, professions or loot quality. |
| Trial Chambers2 |460/460≥4; cropped maximum 14, ceiling 16 |Floor2 and jackpot3–4 are well supported individually in this predictor. Raw placement uses48 bits; viability still uses64. The pinned viable-biome predicate excludes Deep Dark at the chamber's sampled location, which does not prevent a City elsewhere in the same border. |
| Ancient City1 |129/460≥1,61≥2,23≥3; cropped maximum 14, ceiling25 |Floor1 and jackpot2–3 have positive examples. Deep Dark presence alone does not ensure a City, and actual-game disagreements remain. Cities and chambers can coexist in distinct local underground volumes. |
| Desert Pyramid1 |59/460≥1;38≥2; pilot maximum 8; shared feature ceiling 16 |One and two are individually demonstrated. Desert/temple checks correlate strongly. Combined pyramid+temple demand must fit shared feature slots. |
| Jungle Temple1 |50/460≥1;7≥2; pilot maximum 4; same shared ceiling 16 |One and two individually demonstrated; second temple appreciably scarcer in this pilot. The pinned temple biome check admits jungle/jungle_hills, not every member of the broad Jungle family. Bamboo-only family presence does not establish a temple. |
| Coastal Monument1 |133/460≥1;55≥2; cropped maximum 9, ceiling 16 |One/two **viable starts** individually demonstrated; no corresponding proof of whole-footprint coastal containment. Ocean-neighborhood predictor tests at 63 are not exact water/terrain/footprint certification. Predominantly land plus a coastal sea makes this more conditional than the marginal count suggests. |
| Ruined Portals3 |460/460≥4; cropped maximum 9, ceiling9 |Floor3 and jackpot5–6 individually demonstrated. The pinned viability check largely accepts placement after version gating; actual portal pieces/resources still need generation. Three ruined portals do not guarantee three functional complete portals or any chosen loot. |
| Shipwrecks2 |257/460≥2;134≥4; cropped maximum 17, ceiling25 |Floor2 and jackpot5–7 individually demonstrated. Ocean/beach availability couples this to coastline/monument predicates. Starts do not certify intact ships or all chests. |
| Mineshafts5 |460/460≥5 in the exact-floor reanalysis; concrete cropped core witness has 37; cropped maximum 68 |Floor5 and jackpot15–25 have individual positive evidence. The9216 starting-chunk ceiling is not a realistic count prediction. Five starts do not promise a connected exploration complex, spawner type or five disjoint usable mines. |
| Fortress1 |368/460≥1;140≥2;26≥3; cropped maximum 7 |One and jackpot2–3 individually demonstrated. Pair with Bastion explicitly; grids alone provide no guarantee. Verify generated blaze access and safe travel, not only origin. |
| Bastion1 |405/460≥1;266≥2;125≥3; cropped maximum 8 |One and jackpot2–3 individually demonstrated. Distinct Bastion layouts/loot objectives are additional predicates; actual-generation evidence remains incomplete. |
| Optional Outpost |210/460≥1;31≥2; cropped maximum 4, ceiling 4 |One/two bonus counts are reasonable exploratory ranks; not necessary for floor feasibility. |

The currently requested pyramid1+temple1 consumes only two shared feature slots and has no slot-count contradiction. Even pyramid3+temple3 would be below the ceiling 16. By contrast, simultaneously demanding the earlier individual maxima for Pyramid8+Temple4+Hut3+Igloo8 totals 23 and is impossible in the pinned model. That example explains why individual maxima must never be assembled into an asserted achievable world. Fortress and Bastion counts also cannot be combined from separate extrema; both use the same region family.

The million-record crop proves substantial **subsets** coexist. Seed `-8246845270002098890`, Stronghold `[-284,-1356]`, has 6 Villages,7 Trial Chambers,2 Cities,37 Mineshafts,6 Portals,1 Fortress and2 Bastions in current-size borders. It has 0 recorded Monuments and0 Shipwrecks and lacks inventories for Mansion/temples, so it is **not** a blueprint solution. The million scan found 93,808 distinct seeds with Village≥3/Trial≥3/City≥2/Shaft≥5 plus the Nether pair; it did not query Mansion or either temple. Its selected positive rows and early exits cannot identify the complete blueprint rate. Sources: [count feasibility](COUNT_REQUIREMENT_FEASIBILITY.md), [multiplicity pilot](MULTIPLICITY_SEED_BIT_RESULTS.md), [placement ceilings](OVERWORLD_COUNT_LIMITS.md).

## All surface families and caves

The existing family classifier is broader than the blueprint in several places. Use explicit allowed IDs plus actual resource/terrain checks where needed. The small holdout has 24 layouts sampled at 2304 points each, four world-aligned Y planes (63,-48,0,160) and 64-block spacing. Its marginal presences below establish sampled model witnesses only; multiply none of these rates together.

| Blueprint requirement | Existing sampled family presence /24 | Required interpretation and limitation |
|---|---:|---|
| Plains/Sunflower Plains/Meadow |24 |Correct allowed-ID family, but a tiny sample patch or high-altitude meadow is not a large flat shared hub. Set a usable-area/slope criterion. |
| Desert |4 |Explicit Desert plus enough accessible sand/cactus; a temple's biome predicate is correlated evidence, not an independent extra rarity factor. |
| Forest/Birch Forest |24 broad forest |Broad family also includes flower forest, windswept forest and dappled forest. If literal forest/birch IDs are mandatory, narrow the predicate; if ordinary wood is the aim, verify actual tree resources instead. |
| Taiga/Old Growth Taiga |11 broad taiga |Broad family also includes snowy taiga. Presence does not guarantee a berry bush or particular wolf spawn at a sample point. |
| Jungle/Bamboo Jungle |13 broad jungle |Broad family includes sparse jungle; a family witness is not simultaneous bamboo+cocoa+wood evidence. Temple viability uses a narrower set. |
| Swamp/Mangrove Swamp |2 |Ordinary Swamp is allowed by the stated OR, but does not supply the specifically promised mangrove trees. Decide whether mangrove wood is mandatory. Mojang documents mangrove trees and mud in Mangrove Swamp; the OR does not guarantee both resource packages. [Mojang biome guide](https://help.minecraft.net/hc/en-us/articles/360046470431-Minecraft-Types-of-Biomes). |
| Snowy/Ice |9 current snowy_ice |Current family covers snowy plains/ice spikes/slopes, not all frozen-ocean and frozen-peak IDs. Snow alone does not certify packed/blue-ice inventory. Ice Spikes has documented packed ice; require suitable resource blocks/amounts or a supported production plan rather than any snowy ID. [Mojang Ice Spikes](https://www.minecraft.net/en-us/article/around-block--ice-spikes). |
| Dark Forest |11 broad dark_pale |`dark_pale` accepts Pale Garden. That is not literal Dark Forest or a dark-oak resource guarantee. Check dark_forest explicitly. Mansion origin is not a complete resource inventory. |
| Jagged/Stony Peaks **and** Stony Shore sea cliffs |13 broad mountains;24 broad rivers_shores |Two separate requirements. Existing mountains includes groves/windswept hills/frozen peaks; rivers_shores includes ordinary rivers/beaches. Neither family pair proves the requested IDs, a high summit, sheer cliffs or cliff-to-open-ocean adjacency. |
| Lush Caves |23 |Require lush_caves at underground points, then actual accessible caves/resources. A biome field label inside solid rock does not certify an open cavern or axolotl habitat. |
| Dripstone Caves |23 |Require dripstone_caves; actual pointed dripstone/lava-farm ingredients are separate resource checks. |
| Deep Dark |15 |Require deep_dark separately from City count if whole palette is literal. A predicted City uses a Deep Dark check at a different location/Y from the lattice; a grid can miss that witness. |

“Nine families plus caves” therefore contains more than nine machine predicates: peaks and shore are a conjunction; all three caves are required. A four-Y lattice can miss a small valid patch, and can label a non-surface voxel as a surface resource family. Absence on it is not absence throughout the border; presence does not establish actual exposed terrain or quantity. Keep structure-specific biome witnesses and refine promising near-misses. Surface sampling at verified ground elevation and denser local cave/terrain checks are required for final certification.

No hard climate incompatibility has been proved for all these families in 1536×1536. Nor has this audit found a retained exact all-family witness under the narrow definitions. Hot desert/jungle/mangrove and cold snow/taiga constraints share spatial climate fields; peaks/deep dark share terrain influences; coast/monument/shipwreck share ocean space. These correlations can either help or hurt the joint target, and prevent multiplication of marginal rates.

## Playability and ranking

“Zero resource depletion” is not achievable as a blanket guarantee from finite structure counts. Distinguish renewable farms/trading/propagation from finite exploration loot and fixed natural blocks. More starts provide reserves, not unlimited loot. Trial spawners support repeated challenges, but a player cannot personally reopen a given Vault after unlocking it; a Vault can reward multiple different players. Two chambers are multiplayer-friendly content, not endless per-player vault loot. [Bedrock1.21 official release notes](https://feedback.minecraft.net/hc/en-us/articles/27451789924237-Minecraft-Bedrock-Edition-1-21-Tricky-Trials).

For an 8–10-player Realm, an actual generated candidate should be judged on buildable district area, travel/access, renewable-resource setup, portal links and finite-loot sharing. A central Stronghold should have its desired portal-room functionality verified; a monument should fit its required footprint and water surroundings, not just have its origin inside the border. Mountains and cliff aesthetics can coexist with rolling mainland if “no ring” is spatially defined. Elytra towers are a construction goal; elytra access itself depends on the explicitly unconstrained End.

Keep the stated floors distinct from bonus counts. Increasing any floor cannot increase acceptance. It can **increase rejected-seed throughput** by causing earlier rejection, so seeds/second alone is a misleading optimization objective; compare certified useful yield per wall hour. The score's +25 for a fully coastal Monument duplicates a mandatory condition if Stage3 already requires exactly that condition. Pyramid/temple third-copy rewards exceed the stated jackpot count2; document deliberate caps and whether bonuses are per type or per copy. High Mineshaft/Portal/Shipwreck counts can dominate other preferences unless all counts use explicit caps. Full inventories needed for rank should run after minimum eligibility.

## Measured costs and unsupported probability claims

Historical timing scopes must stay separate:

| Measurement | Measured rate | Time per corresponding input | Scope |
|---|---:|---:|---|
| Expanded prior combination, direct capped count |14,996.6 layouts/s |66.68µs/layout |Prepared contexts, selected anchor; no discovery/setup/biomes/terrain. Prior target differs from exact blueprint. |
| Same prior target with uncached lower32 gate |13,002.1 layouts/s |76.91µs/layout |Gate slower despite raw rejection27.39%; existing direct path already uses cheap placement. |
| Same prior target, discovery included |1,585.0 inputs/s |630.9µs/input |Small serial first-anchor replay; no persistence, terrain or actual game. |
| Broad prior biome batch inventory |69.28 layouts/s |14.43ms/layout |2304 points; unconditional 24-layout cohort, not conditioned structure survivors. |
| Broad prior biome native goal |59.35 layouts/s |16.85ms/layout |Nearly full-grid negative cases; early stopping is not always faster. |
| Sustained million baseline,30 workers |173.37 inputs/s |5.768ms wall/input |Historical5000/2688/1024 geometry, baseline+IPC+persistence; excludes terrain/game. |

Sources: [combination throughput](PROPOSED_COMBINATION_THROUGHPUT.md), [master benchmark](MASTER_IMPLEMENTATION_RESULTS.md). Neither630.9µs nor5.768ms is the established cost of the full exact blueprint. The former is not a multicore machine-wide throughput promise; the latter is a different older pipeline. Do not multiply single-process rates by worker count without a matched measurement.

The parent's fresh reanalysis of the **exact blueprint structure floors** on retained cohorts found **0/436 tuning and0/460 holdout** complete viable layouts. Necessary lower32 raw-family capacity passed286/436 (65.596%) and334/460 (72.609%): this gate rejected34.404% and27.391%, not99.8%. It excludes Stronghold discovery, Trial Chamber lower48 placement, Mineshaft and all biome/coastal viability, so it is not a complete Stage1 pass rate. Mansion-first viable filtering left2 tuning and3 holdout layouts; adding Jungle Temple left0 and1; adding Pyramid left0 and0. Every subsequent conditional denominator is zero, so downstream pass rates are **undefined**, not measured0%. The exact-floor individual results additionally show Village≥5 in95/436 and92/460, and Mineshaft≥5 in every retained layout. This demonstrates individual support for those floors but no complete conjunction. [Exact-floor retained-cohort funnel](runs/blueprint-audit-2026-10-12/historical-blueprint-funnel.json).

Earlier strict expanded structure checks yielded 0/460 holdout layouts; the all 21 structure conjunction also yielded 0/460. These are not the exact blueprint and are not iid inputs. The biome expanded goal yielded 0/24, also not the exact palette. They establish no positive lower bound on full-blueprint acceptance. They do not justify either “impossible” or “one in 1.5 million.”

For a future **iid representative** seed sample with zero complete positives in `n`, the one-sided 95% binomial upper bound is `p_U=1-0.05**(1/n)` (approximately3/n), with lower bound0. For reference, zero in460 gives 0.649%, and zero in 1 million gives about 3×10^-6. These numerical examples are **not valid confidence intervals for the correlated historical layouts**. For grouped siblings, use independent group-level seed-success events or a cluster-aware design; unresolved inputs cannot silently count as certified failures. Even a valid upper bound on `p` supplies no finite upper bound on time to success because `p=0` remains allowed.

If `a_s`, `a_sb`, `a_sbt` are expected numbers per original input of anchors surviving structures, structures+biomes, and structures+biomes+terrain, respectively, a serial expected-cost accounting identity is

`E[C/input] = C(discovery+all-anchor structure work) + a_s E[C_b | S] + a_sb E[C_t | S,B] + a_sbt E[C_game | S,B,T] + C(persistence/IPC/ranking)`.

Use conditional costs on actual survivors. The survival factors here are expected **anchor counts per seed**, not automatically probabilities, because a seed may have several anchors. Seed-level success `p` is the probability at least one anchor passes the complete target; correlated anchors cannot be counted as independent trials. In a parallel pipeline, measure resource contention/queue throughput rather than summing isolated wall timings or applying an unmeasured worker multiplier. Conditional probability chain rules are valid; independence products of marginal rates are not.

For a known seed-level rate `p` and sustained complete input throughput `r`, independent-input scenarios give mean inputs to first success `1/p`, median `ln(.5)/ln(1-p)`,95% probability-of-at-least-one volume `ln(.05)/ln(1-p)`, and time equal to volume/r. A leaderboard of `k` candidates has expected volume `k/p`; its high-confidence volume requires the binomial tail `Pr[Binomial(N,p)>=k]`, not the first-success formula.

Illustrative assumptions only (exclude additional unmeasured stages):

| Assumed full rate | Mean first-success time at 1500/s |95% first-success time at 1500/s |Mean at historical 173.37/s |
|---|---:|---:|---:|
|1 in 1.2million |13.3min |39.9min |115.4min |
|1 in 1.8million |20.0min |59.9min |173.0min |
|1 in 10 million |1.85h |5.55h |16.0h |
|1 in 100 million |18.5h |55.5h |160.2h |

Thus even accepting the blueprint's unmeasured 1-in 1.2–1.8million and 1500–2000/s claims, mean time to **one** candidate is 10–20min and95% first-success time is about 30–60min. A 35–50min run scans 3.15–6million inputs at those assumed rates and has roughly 1.75–5 expected candidates, with no assurance of a substantial leaderboard. If Stage1 passes 0.2% and full acceptance were 1/1.5million, the subsequent combined conditional acceptance would need to be 1/3000; neither component nor that conditional value is established. “Stage2 passes1in 1.5 million” must say whether its denominator is original seeds or Stage1 survivors.

## Recommended evidence sequence

1. Resolve exact coast geometry, allowed biome IDs, footprint containment, resource quantities, spawn versus origin, exact game version and finite-loot expectations. Retain the 1536/896 preference unless the user chooses otherwise; feasibility uncertainty alone does not authorize silently relaxing it.
2. Measure the exact floors on representative independent full64 inputs, testing all eligible anchors with explicit unresolved statuses. Record both seed and anchor denominators, per-stage survivors, paid timings and completed coverage. Reuse raw placement only where dependency proofs and paid benchmarks support it; every biome and terrain query retains full64.
3. Run the narrow palette and terrain predicates on those actual survivors. Include Monument in the count-floor predicate even if its expensive coastal certification stays later. Retain sampled witnesses and report lattice-only rejection as a search-policy decision rather than exhaustive geographic absence.
4. Generate exact-build worlds for complete predicted candidates and verify starts, requested pieces/footprints/resources, mainland connectivity and travel/portal constraints. Only these establish a playable solution. Until complete positives exist, present volume/runtime as scenarios and report the achieved budget rather than promising a completion date.

Verification of this audit consists of reading the pinned source, checking historical denominators/scopes, recomputing geometric and timing arithmetic, and consulting the primary links above. No significant CPU benchmark, production search, config change or actual-world generation was run by this research task. The dated addendum below incorporates the parent-owned fresh exact-target measurements.

## Fresh exact-contract evidence, 12 October 2026

The new all-anchor production baseline was evaluated on **30,000 distinct full64 inputs**, three disjoint 10,000-input cohorts. Repeated trials and different worker counts reuse these inputs and do not increase the statistical sample. The earlier 12,288-input run is contained in these cohorts and must not be added again. The input stream is a deterministic randomized permutation; interpreting it as representative random sampling is a statistical modeling assumption, not actual-game certification. Source: [30,000-input cohort data](runs/blueprint-audit-2026-10-12/scaling/scan-18.json).

Counting the first trial of each cohort once gives this exact anchor funnel:

| Check | Entered anchors | Passed anchors | Conditional observed pass fraction |
|---|---:|---:|---:|
| Mansion with Dark Forest at start Y=63 |55,853 |266 |0.4763% |
| Jungle Temple≥1 |266 |38 |14.2857% |
| Desert Pyramid≥1 |38 |1 |2.6316% |
| Monument≥1 |1 |0 |0/1 |
| Remaining structure floors, Nether pair, palette |0 |0 |Undefined; not reached |

All 30,000 inputs have zero complete predicted baseline positives; **3,946 inputs have no discovered anchor** and remain unresolved. All inputs retain unresolved Stronghold recall, and no actual-world negatives are established. There are 55,853 anchor evaluations, not that many independent seeds. The one Mansion+Temple+Pyramid survivor demonstrates a useful partial conjunction, but failed the Monument floor. The sparse lattice and coastal checks received no complete structure survivors, so their conditional acceptance and useful-world throughput remain unmeasured. The new Mansion screen additionally requires Dark Forest at fixed Y=63; a true surface Mansion with a different biome at that depth can remain pending. This is a conservative predictor policy, not proof of actual absence.

Under an explicitly assumed iid representative model of **implemented predicted seed success**, zero successes among 30,000 gives a nominal one-sided 95% upper bound of **0.000099853** (about one in 10,015), with lower bound0. This cannot bound actual-world acceptance because discovery and the model can miss qualifying worlds. It does not establish rarity near one in 1.5 million: at that hypothetical rate, the probability of zero in 30,000 is **98.02%**. The result is consistent with a much rarer target, the proposed rate, or no possible complete solution. No finite expected or 95% full-world completion time has been inferred from zero positives.

The separate diagnostic retained 48 selected, correlated layouts, with three timing trials per arm. All 48 failed the exact palette; both arms queried the entire 2304-point lattice. Median cost was **34.251ms/layout** for complete inventory and **33.864ms/layout** for the capped gate (approximately 29.20 and29.53 layouts/s). These are unconditional diagnostic costs including the current Python evidence construction, not costs measured on real structure survivors and not directly comparable to the earlier native-only 14.43ms figure. The required biome conjunction has no measured conditional pass rate. Raw Overworld capacity passed 47/48 diagnostic layouts; that partial gate excludes Stronghold, Mineshaft, Nether and biome viability. [Diagnostics](runs/blueprint-audit-2026-10-12/diagnostics.json).

The matched 32-input serial experiment used three counterbalanced trials of exhaustive-reference and cheap-first evaluation under the same contract. Median totals were 2.1171s and 0.04612s, a 45.90× throughput ratio (97.82% less elapsed time), with zero qualification differences across 192 repeated input-arm comparisons. All 47 anchors failed Mansion, so the reference's later inventories and four-Y checks were unnecessary for these inputs. This demonstrates effective early rejection against an exhaustive oracle, **not** a 45.9× gain over the old production pipeline, an improvement on accepted candidates, or a 45.9× full-world-search multiplier. There are 32 distinct input identities, not 192. [Serial comparison](runs/blueprint-audit-2026-10-12/serial.json).

Implementation review confirms all discovered anchors are considered, explicit `dark_forest` excludes Pale Garden, peaks and Stony Shore are separate predicates, and surface-role/cave-role Y samples are separated. Fixed-Y biome labels still do not certify exposed resource quantities. The new terrain evaluation is expressly a **coastal geometry subset**: it does not certify the blueprint's qualitative rolling terrain, peak/cliff relief or no-enclosed-mountain-ring language. Those unresolved semantics must not be inferred from a coastal model pass. The final uncontended worker-scaling results below measure baseline rejection throughput, not complete world-generation verification.


### Final uncontended performance review

The final post-integration recheck ran each worker profile serially, with one trial per disjoint 10,000-input cohort, excluding earlier overlapping/scaffolding timings from headline comparison. Both profiles evaluated the **same 30,000 distinct inputs and 55,853 anchors**, reproducing the funnel above. Each worker used one native thread. The scope includes discovery, all-anchor short-circuit evaluation, startup, IPC, SQLite checkpoints and monitoring. It excludes coast and actual game generation; no input reached the palette. [Final benchmark summary](runs/blueprint-audit-2026-10-12/benchmark-summary.json).

| Workers | Total wall time for 30,000 | Inputs/second | Wall milliseconds/input | Cohort rate range |
|---|---:|---:|---:|---:|
|18 |26.322s |1,139.746 |0.87739 |1,126.05–1,148.44 |
|30 |24.228s |1,238.229 |0.80760 |1,229.14–1,242.87 |

Thirty workers delivered **8.64% higher throughput** on these short runs. This is a measured whole-process baseline rate, not 1500–2000 complete qualified worlds/s, and not a sustained million-input measurement. At the same rate one million baseline inputs would take 13.46 minutes; that is a linear capacity projection without long-run storage/thermal/contention effects or downstream work. The 30-worker files used about 14.35 kB/input and 1.46 GB peak summed process-tree RSS; RSS can double-count shared pages and no concurrent BDS load was measured. Full-world qualification may be slower by an unknown amount.

Summed worker discovery time was 396.21µs/input; Mansion checking was 405.19µs per entered **anchor**, followed by 134.18µs/Jungle check and 128.13µs/Pyramid check on their much smaller conditional samples. These are worker elapsed costs, not additive contributions to multicore wall time per seed. The sole Monument check cannot establish a stable conditional timing distribution. Its failure leaves every later stage without a production survivor denominator.

The separate full coastal refinement ladder took a median **1.19229s/layout** with reuse, or 0.83872 layouts/s, and exact sampling reuse saved **21.905% elapsed time** versus its matched no-reuse reference (1.28049× throughput). All 108 parity checks matched. This is bounded diagnostic terrain evidence, not the conditional average among complete structure-and-biome survivors. It neither multiplies baseline throughput nor establishes a full-blueprint coastal pass rate. Separate count diagnostics produced 3,456 parity checks and per-type gains ranging from approximately 0.989× for Village to 6.40× for Mineshaft; Mansion was 1.001×. Since Mansion rejects almost every current anchor, the large Mineshaft gain has little effect on this observed baseline funnel. The 32-input 45.90× exhaustive-reference comparison retains the limitations above.

Conditional planning scenarios using the **measured 1238.229 inputs/s baseline capacity** are below. Each row assumes an otherwise unmeasured final seed-level success probability and assumes this baseline rate persists; times exclude the unknown added conditional palette/coast/BDS/verification costs. They are not forecasts or guarantees.

| Assumed one success in | Mean inputs to first | Inputs for 95% chance of first | Mean hours to first | Hours for 95% chance of first | Mean hours to five |
|---|---:|---:|---:|---:|---:|
|1,200,000 |1,200,000 |3,594,878 |0.269 |0.806 |1.346 |
|1,500,000 |1,500,000 |4,493,597 |0.337 |1.008 |1.683 |
|1,800,000 |1,800,000 |5,392,317 |0.404 |1.210 |2.019 |
|10,000,000 |10,000,000 |29,957,322 |2.243 |6.720 |11.217 |
|100,000,000 |100,000,000 |299,573,226 |22.433 |67.205 |112.167 |

Even assuming the blueprint's 1-in-1.2–1.8million rate, these measurements imply 16.2–24.2minutes mean time to one candidate and 48.4–72.6minutes for 95% probability of one, before unmeasured downstream costs. Five candidates average 1.35–2.02hours under those assumptions. With no positive lower bound on actual complete-blueprint acceptance, **there is still no defensible finite upper bound on required input volume or verified-world completion time**. The 30,000-input observation demonstrates functioning rejection and measured processing capacity, not existence of the full requested world.
