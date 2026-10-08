"""Explicit biome groups for diagnostics, without invented density weights."""
import numpy as np
from .backend import biome_name

WOODLAND_NAMES=frozenset({
    "forest","flower_forest","birch_forest","old_growth_birch_forest","dark_forest",
    "taiga","old_growth_pine_taiga","old_growth_spruce_taiga","snowy_taiga",
    "jungle","bamboo_jungle","cherry_grove","grove","mangrove_swamp","swamp",
    "pale_garden","dappled_forest",
})
SPARSE_WOOD_NAMES=frozenset({"sparse_jungle","windswept_forest","savanna",
                           "savanna_plateau","windswept_savanna","wooded_badlands"})

def wood_masks(biomes):
    ids=np.unique(biomes)
    dense=[i for i in ids if biome_name(i) in WOODLAND_NAMES]
    sparse=[i for i in ids if biome_name(i) in SPARSE_WOOD_NAMES]
    return np.isin(biomes,dense),np.isin(biomes,sparse)

def surrounding_score(fraction, full_credit=.60):
    return min(1.0,max(0.0,fraction)/full_credit)

def openness_score(fraction):
    return 1-min(1.0,max(0.0,fraction))
