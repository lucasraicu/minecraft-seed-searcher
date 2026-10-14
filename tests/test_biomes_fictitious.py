"""Test that unvalidated biome names are excluded from the supported scoring policy."""
from seed_search.biomes import GROUPS, FAMILIES, MANUAL_CAVE_FAMILIES
from seed_search.wood import WOODLAND_NAMES


def test_no_fictitious_biomes():
    fictitious = {"dappled_forest", "sulfur_caves", "ice_caves"}
    for name in fictitious:
        assert name not in GROUPS
        assert name not in FAMILIES
        assert name not in MANUAL_CAVE_FAMILIES
        assert name not in WOODLAND_NAMES
