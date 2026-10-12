# Larger islands and inclusive surrounding mountains

11 October 2026. Discovery remains 4000×4000, Overworld 1536×1536 and Nether 896×896. Required structures and wooded families retain their existing eligibility contract.

## Main-island area

Area is the sampled land area of the **single connected component containing the terrain center**. Other disconnected islands are excluded. Connected lobes count together; diagonal contacts are conservatively treated as possible land bridges. Neither area nor the equivalent diameter assumes a circular outline. Equivalent diameter is only `2*sqrt(area/pi)`; border fit uses the actual sampled formation footprint.

The former minimum equivalent diameter of 250 already implied approximately 49,087 square blocks, making the old 12,000-area floor redundant. The former 750 maximum limited island area to approximately 441,786 square blocks.

The active profile now uses:

| Preference | Value |
|---|---:|
| Minimum connected main-island land area | 250,000 square blocks |
| Favored land area in ranking | 650,000 square blocks |
| Equivalent diameter range | 500–1300 blocks; the area minimum effectively raises the lower end to about 564 |
| Favored equivalent diameter | 800–1100 blocks |
| Surrounding water | Existing 24/32 connected-water directions and 48-block threshold |

The maximum equivalent diameter permits approximately 1.33 million square blocks. Irregular islands still must fit their sampled footprint and water belt into the Stronghold-centered Realm. The 250,000 minimum is a working preference chosen after explaining the area semantics; it can be raised independently of circularity.

## Surrounding mountains

The active `enclosure_policy: surrounding_mountains` accepts substantial elevated terrain around an interior without demanding one continuous ridge, a particular arc aspect ratio, a perfect ring, a dry floor, or a flat floor.

At least 16 of 32 directions need support 24 blocks above the sampled interior, at distances 150–700 blocks. No unrepresented angular gap may exceed 12 directions (135°). Support still needs at least 32 blocks of sampled ray width and 4096 square blocks of raised component area to exclude tiny spikes. Higher relief and more surrounding directions improve ranking. Separate mountains, passes, water interiors and jagged interiors can qualify.

The existing `continuous_arcs` policy stays selectable, and saved configurations without `enclosure_policy` use that historical policy. Arc metrics remain recorded under both policies; their shape thresholds do not reject candidates in the inclusive policy. The low-level historical fallback constants are retained for explicit historical controls; `default_config()` and `config/realm.yaml` select the new active preferences.

Partial coverage, unknown ridge extents and outside-border formations retain their evidence status. Broader acceptance is a search preference change, not newly established actual-world accuracy. Current-source/config identity guards prevent silently resuming old computations with the new policy.

## Additional structures and lower32

A deterministic pilot sampled **2048 distinct dispersed lower32 layouts**. It added raw Monument, Outpost, Shipwreck and Ruined Portal presence to the existing Village/Ancient City/Fortress/Bastion/initial-Fortress requirements. This is diagnostic only; additional structures are not newly mandatory.

| Raw candidate presence domain | Base passing layouts | Passing with all four extras | Additional exclusions |
|---|---:|---:|---:|
| Conservative envelope covering all permitted centers | 1965 | 1965 | 0 |
| Arbitrary fixed origin center with final 1536/896 squares | 1522 | 1484 | 38 |

All four extra families had raw candidates in every conservative envelope. At the fixed origin center, only Outpost added exclusions: 38 of 2048 total layouts (1.86 percentage points), or 2.50% of base survivors. Raw candidate presence is much less selective than actual biome-valid structures. The fixed origin is not an observed Stronghold; its failures cannot reject an entire lower32 family with other possible centers.

More mandatory structures can improve selectivity when their placements genuinely exclude layouts or constrain a common center. Optional bonuses alone do not create necessary rejection conditions. This pilot did not test joint feasible-center intersections for all extras, upper32 biome viability, actual Stronghold positions, sibling allocation advantage or verified-world yield. A useful next selection experiment would measure added **joint-center/proximity** constraints against independent full64 useful yield, rather than assume more raw names deliver 99.9% rejection.

Reproduction: `.venv/bin/python scripts/pilot_additional_raw_structures.py --count 2048 --output <fresh-output.json>`.

Verification: **680 tests passed in 101.43 seconds**. The focused geometry suite passed 77 tests; verification selection/planning and the new preference controls passed 35 tests. Explicit CLI configuration and default active preferences agree, and whitespace checks pass. The verification tests now exercise the larger island coverage request and new borderline thresholds. Historical arc and small-island controls retain explicit historical preferences.

Evidence: [additional raw-family pilot](runs/terrain-preferences-2026-10-11/additional-raw-structures.json), [acceptance controls](runs/terrain-preferences-2026-10-11/acceptance-controls.json), [verification summary](runs/terrain-preferences-2026-10-11/verification.json), [full test output](runs/terrain-preferences-2026-10-11/full-tests.txt). Synthetic controls cover large irregular islands, disconnected archipelagos, bridges, separate mountains, rough interiors, open passes, one-sided mountains, tiny spikes and unknown coverage; they do not establish natural-world acceptance rates. Larger island analysis/verification halos add downstream work; no new sustained terrain/BDS throughput measurement is claimed.
