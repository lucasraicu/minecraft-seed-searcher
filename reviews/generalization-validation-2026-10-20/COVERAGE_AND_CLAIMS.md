# Generalization coverage and player claims

Frozen cohort complete: 24/24 seed worlds. Blind and targeted controls stay separate. This matrix is derived from validated raw reports; matching references are not generated instance totals.

Build: BDS1.26.52.3; modelMC_26_50. Manifest `bbc14d21fba0455ed8f7cfe66099f34b6734575dfb7d8ffbcb00337eced72f1c`.

## Structure types

| Dimension | Type | Public registry | Retained exact/nav | Rejected exact/nav | Other reference | No location | Current limitation |
|---|---|---|---:|---:|---:|---:|---|
| overworld | abandoned_camp | backend only | 0 | 0 | 0 | 72 | missing matching reference |
| overworld | ancient_city | yes | 23 | 0 | 1 | 0 | discovery requires followup; independent discovery needs follow-up |
| overworld | buried_treasure | backend only | 24 | 0 | 0 | 0 | matching reference observed |
| overworld | desert_pyramid | yes | 19 | 0 | 2 | 0 | grouped subtype unresolved |
| overworld | igloo | yes | 24 | 0 | 0 | 0 | grouped subtype unresolved |
| overworld | jungle_temple | yes | 20 | 0 | 3 | 0 | grouped subtype unresolved |
| overworld | mansion | yes | 7 | 0 | 0 | 0 | matching reference observed |
| overworld | mineshaft | yes | 24 | 0 | 0 | 0 | matching reference observed |
| overworld | monument | yes | 22 | 0 | 2 | 0 | matching reference observed |
| overworld | ocean_ruin | backend only | 24 | 0 | 0 | 0 | matching reference observed |
| overworld | outpost | yes | 48 | 0 | 47 | 0 | matching reference observed |
| overworld | ruined_portal | yes | 24 | 0 | 0 | 0 | matching reference observed |
| overworld | shipwreck | yes | 23 | 0 | 1 | 0 | matching reference observed |
| overworld | stronghold | backend only | 0 | 0 | 24 | 0 | missing matching reference |
| overworld | swamp_hut | yes | 22 | 0 | 0 | 0 | grouped subtype unresolved |
| overworld | trail_ruins | yes | 0 | 0 | 24 | 0 | missing matching reference |
| overworld | trial_chamber | yes | 0 | 0 | 24 | 0 | missing matching reference |
| overworld | village | yes | 72 | 14 | 48 | 0 | over rejection observed |
| nether | bastion | backend only | 24 | 0 | 0 | 0 | discovery requires followup; independent discovery needs follow-up |
| nether | fortress | backend only | 24 | 0 | 0 | 0 | matching reference observed |
| nether | ruined_portal_nether | backend only | 24 | 0 | 0 | 0 | matching reference observed |

Matching temple coordinates identify generic temple locations, not subtype. A different locate reference or no returned location is not absence. Rejected exact references require investigation rather than extra exclusion. Discovery queries are independently fixed origins and are compared against the full frozen inventory, not just selected retained probes. Machine-readable report preserves cohort × disposition and seed identities.

## Biome classes

| Dimension | Class | Planned points | Attempted | Match | Mismatch | Error | Matching seeds |
|---|---|---:|---:|---:|---:|---:|---:|
| overworld | badlands | 12 | 12 | 11 | 0 | 1 | 10 |
| overworld | bamboo_jungle | 14 | 14 | 13 | 0 | 1 | 13 |
| overworld | beach | 40 | 40 | 40 | 0 | 0 | 24 |
| overworld | birch_forest | 77 | 77 | 77 | 0 | 0 | 23 |
| overworld | cherry_grove | 11 | 11 | 10 | 0 | 1 | 10 |
| overworld | cold_ocean | 117 | 117 | 117 | 0 | 0 | 24 |
| overworld | dappled_forest | 23 | 23 | 21 | 0 | 2 | 17 |
| overworld | dark_forest | 28 | 28 | 28 | 0 | 0 | 24 |
| overworld | deep_cold_ocean | 88 | 88 | 88 | 0 | 0 | 23 |
| overworld | deep_dark | 9 | 9 | 6 | 0 | 3 | 4 |
| overworld | deep_frozen_ocean | 20 | 20 | 20 | 0 | 0 | 18 |
| overworld | deep_lukewarm_ocean | 27 | 27 | 26 | 0 | 1 | 18 |
| overworld | deep_ocean | 102 | 102 | 102 | 0 | 0 | 23 |
| overworld | desert | 62 | 62 | 61 | 0 | 1 | 13 |
| overworld | dripstone_caves | 153 | 153 | 147 | 0 | 6 | 23 |
| overworld | eroded_badlands | 8 | 8 | 8 | 0 | 0 | 8 |
| overworld | flower_forest | 23 | 23 | 23 | 0 | 0 | 19 |
| overworld | forest | 221 | 221 | 221 | 0 | 0 | 24 |
| overworld | frozen_ocean | 76 | 76 | 76 | 0 | 0 | 20 |
| overworld | frozen_peaks | 15 | 15 | 11 | 0 | 4 | 11 |
| overworld | frozen_river | 47 | 47 | 46 | 0 | 1 | 21 |
| overworld | grove | 33 | 33 | 33 | 0 | 0 | 19 |
| overworld | ice_spikes | 22 | 22 | 22 | 0 | 0 | 15 |
| overworld | jagged_peaks | 13 | 13 | 10 | 0 | 3 | 10 |
| overworld | jungle | 66 | 66 | 66 | 0 | 0 | 20 |
| overworld | lukewarm_ocean | 51 | 51 | 51 | 0 | 0 | 20 |
| overworld | lush_caves | 56 | 56 | 55 | 0 | 1 | 23 |
| overworld | mangrove_swamp | 12 | 12 | 12 | 0 | 0 | 11 |
| overworld | meadow | 60 | 60 | 60 | 0 | 0 | 17 |
| overworld | mushroom_fields | 11 | 11 | 11 | 0 | 0 | 11 |
| overworld | ocean | 129 | 129 | 129 | 0 | 0 | 24 |
| overworld | old_growth_birch_forest | 37 | 37 | 37 | 0 | 0 | 24 |
| overworld | old_growth_pine_taiga | 19 | 19 | 19 | 0 | 0 | 18 |
| overworld | old_growth_spruce_taiga | 32 | 32 | 32 | 0 | 0 | 20 |
| overworld | pale_garden | 10 | 10 | 10 | 0 | 0 | 10 |
| overworld | plains | 473 | 473 | 470 | 0 | 3 | 24 |
| overworld | river | 70 | 70 | 69 | 0 | 1 | 23 |
| overworld | savanna | 77 | 77 | 77 | 0 | 0 | 20 |
| overworld | savanna_plateau | 14 | 14 | 12 | 0 | 2 | 12 |
| overworld | snowy_beach | 17 | 17 | 17 | 0 | 0 | 17 |
| overworld | snowy_plains | 118 | 118 | 118 | 0 | 0 | 22 |
| overworld | snowy_slopes | 15 | 15 | 14 | 0 | 1 | 14 |
| overworld | snowy_taiga | 90 | 90 | 89 | 1 | 0 | 21 |
| overworld | sparse_jungle | 52 | 52 | 51 | 0 | 1 | 19 |
| overworld | stony_peaks | 17 | 17 | 16 | 0 | 1 | 13 |
| overworld | stony_shore | 36 | 36 | 36 | 0 | 0 | 24 |
| overworld | sulfur_caves | 25 | 25 | 25 | 0 | 0 | 13 |
| overworld | sunflower_plains | 43 | 43 | 43 | 0 | 0 | 16 |
| overworld | swamp | 66 | 66 | 66 | 0 | 0 | 20 |
| overworld | taiga | 159 | 159 | 159 | 0 | 0 | 24 |
| overworld | warm_ocean | 52 | 52 | 52 | 0 | 0 | 12 |
| overworld | windswept_forest | 17 | 17 | 17 | 0 | 0 | 13 |
| overworld | windswept_gravelly_hills | 17 | 17 | 17 | 0 | 0 | 14 |
| overworld | windswept_hills | 20 | 20 | 20 | 0 | 0 | 16 |
| overworld | windswept_savanna | 11 | 11 | 11 | 0 | 0 | 11 |
| overworld | wooded_badlands | 10 | 10 | 10 | 0 | 0 | 10 |
| nether | basalt_deltas | 48 | 48 | 48 | 0 | 0 | 14 |
| nether | crimson_forest | 57 | 57 | 57 | 0 | 0 | 13 |
| nether | nether_wastes | 51 | 51 | 51 | 0 | 0 | 14 |
| nether | soul_sand_valley | 48 | 48 | 45 | 3 | 0 | 13 |
| nether | warped_forest | 12 | 12 | 12 | 0 | 0 | 4 |

## Public selectable biome families

| Family | Active model members | Matched witnesses at registry Y | Untested active members at registry Y |
|---|---|---:|---|
| biome.cherry_grove | cherry_grove | 10 | none |
| biome.mushroom_fields | mushroom_fields | 11 | none |
| biome.bamboo_jungle | bamboo_jungle | 13 | none |
| biome.desert | desert | 28 | none |
| biome.badlands | badlands, eroded_badlands, wooded_badlands | 29 | none |
| biome.snowy | ice_spikes, snowy_plains, snowy_slopes, snowy_taiga | 117 | none |
| biome.mangrove_swamp | mangrove_swamp | 12 | none |
| biome.forest | birch_forest, flower_forest, forest, old_growth_birch_forest | 163 | none |
| biome.plains | meadow, plains, sunflower_plains | 200 | none |

Legacy family aliases that do not generate in MC_26_50 are excluded from the active-member requirement. These rows check exact sampled witness labels at the registryY, not surface extent, suitability, absence or every patch.

## Supported wording and method gates

- Biomes: a directly checked coordinate may be described as a BDS-observed biome witness for the recorded seed/build/dimension/XYZ. A sampled catalog witness is a prediction unless that exact point has game evidence. SparseY63/stride64 catalog samples do not prove absence, complete area, every small patch, or universal biome accuracy.
- Structures: show predicted starts and separately scoped game-located references. Candidate coordinates and tested navigation projections remain distinct. No physical/exhaustive total or numerical recall is established by these probes. Membership returns type-at-point, not unique instance IDs.
- Multiplicity and density: distinct located references need explicit instance semantics before supporting at-least-N physical claims. Ranking predicted starts is a prediction ranking, not verified rarity in the full seed population.
- Public catalog capability flags/build allowlist remain disabled/research-only. Nether, stronghold and other backend-only checks here do not silently add public filters. Spawn, terrain suitability, loot and farm guarantees need separate verifiers.
- Every criterion for a selected world size still applies to the same anchor. Validation does not change the three public border sizes, anchor policy, retention or personal-search rejection rules.
- Failed loading observations remain errors/unknowns. No new seed blacklist, rejection threshold or catalog publication has occurred in this audit.

## Machine-readable evidence

Campaign directory: `/Users/lucasraicu/.local/share/antigravity-worker-mcp/generalization-validation-20261020`. Validated `results.json`, `coverage.json`, frozen manifest and per-world ledger/report/console/settings are preserved there. Source prediction fingerprint: `f51d3b3b48375ddd2c1f6a3c1b3b94ac0b2e0c246865962d19d5b8df134c3fef`. Original facts are retained; no population accuracy percentage is inferred.
