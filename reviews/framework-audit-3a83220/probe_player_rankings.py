"""Small scoring-policy probes; no generated-world or player-preference claims."""
import json
from pathlib import Path

from seed_search.realm.blueprint import DYNAMIC_V3_LUXURIES, dynamic_v3_score
from seed_search.realm.config import dynamic_v3_blueprint_config


def main():
    cfg = dynamic_v3_blueprint_config()
    baseline = dict(cfg["structures"]["hard_floors"])
    scenarios = {}

    def add(name, counts=None, optional=None, biomes=(), **spatial):
        score, components, _ = dynamic_v3_score(
            baseline | (counts or {}), biomes,
            optional_counts=optional or {}, **spatial,
        )
        scenarios[name] = {
            "score": score, "components": components,
            "count_changes": counts or {}, "optional": optional or {},
            "biomes": list(biomes), "spatial_inputs": spatial,
        }

    add("baseline")
    add("second_mansion", {"mansion": 2})
    add("five_extra_villages", {"village": 11})
    add("four_extra_trial_chambers", {"trial_chamber": 12})
    add("five_extra_trial_chambers", {"trial_chamber": 13})
    add("second_stronghold", {"stronghold": 2})
    add("third_stronghold", {"stronghold": 3})
    add("two_basement_igloos", optional={"igloo": 2})
    add("first_swamp_hut", optional={"swamp_hut": 1})
    add("single_badlands_witness", biomes=("badlands",))
    add("three_extra_villages", {"village": 9})
    add("improve_nearest_village_900_to_100_blocks", hub=15)
    add("maximum_all_spatial", hub=45, scenic=1, village_spread=1,
        treasure_bastion=1, nether_core=20)
    add("village_scenic_spread_nether_amenities", hub=15, scenic=1,
        village_spread=1, nether_core=20)

    concavity = {}
    for name, floor in baseline.items():
        values = [dynamic_v3_score(baseline | {name: n})[0]
                  for n in range(floor, floor + 24)]
        increments = [b - a for a, b in zip(values, values[1:])]
        assert all(x >= 0 for x in increments), name
        assert all(a >= b for a, b in zip(increments, increments[1:])), name
        concavity[name] = increments
    for name in ("swamp_hut", "igloo", "trail_ruins", "ocean_ruin", "buried_treasure"):
        values = [dynamic_v3_score(baseline, optional_counts={name: n})[0]
                  for n in range(24)]
        increments = [b - a for a, b in zip(values, values[1:])]
        assert all(x >= 0 for x in increments), name
        assert all(a >= b for a, b in zip(increments, increments[1:])), name
        concavity[name] = increments
    maximum = dynamic_v3_score(
        {name: 100 for name in baseline},
        [members[0] for _, members in DYNAMIC_V3_LUXURIES],
        hub=45, scenic=1, village_spread=1, treasure_bastion=1, nether_core=20,
        optional_counts={name: 100 for name in
                         ("swamp_hut", "igloo", "trail_ruins", "ocean_ruin", "buried_treasure")},
    )
    assert maximum[0] == 1250
    masses = {name: floor * cfg["search"]["centroid_weights"].get(name, 0)
              for name, floor in baseline.items()}
    result = {
        "scenarios": scenarios, "all_19_surplus_schedules_monotone_concave": True,
        "marginal_increments_from_floor": concavity,
        "maximum_score": maximum[0], "maximum_components": maximum[1],
        "baseline_centroid_masses": masses,
        "baseline_total_centroid_mass": sum(masses.values()),
    }
    output = Path(__file__).with_name("player-ranking-probes.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "scenario_scores": {name: item["score"] for name, item in scenarios.items()},
        "monotone_concave_schedules": len(concavity), "maximum": maximum[0],
        "baseline_centroid_mass": sum(masses.values()),
    }, indent=2))


if __name__ == "__main__":
    main()
