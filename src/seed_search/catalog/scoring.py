"""Shared deterministic retention profile math, cross-checked against query.py."""
from decimal import Decimal, localcontext
from .registry import PROFILES
from .codec import MISSING

LCM = 720720
GROUPS = ((0,), (1,), (2,), (4,12), tuple(range(14)), tuple(range(14,23)), (0,), (7,8,9,10))


def profile_units(layout, profile):
    coefficients = PROFILES[profile]
    counts = [row[2] for row in layout['counts']]
    known = [all(layout['complete'][slot][2] for slot in group) for group in GROUPS]
    n_biomes = sum(d != MISSING and d <= 1024**2 for d in layout['biome_nearest_d2'])
    units = [min(counts[0],6)*(LCM//6), min(counts[1],4)*(LCM//4),
             min(counts[2],2)*(LCM//2), min(counts[4]+counts[12],6)*(LCM//6),
             sum(n>0 for n in counts)*(LCM//14), min(n_biomes,8)*(LCM//8), 0,
             min(sum(counts[i] for i in (7,8,9,10)),4)*(LCM//4)]
    with localcontext() as context:
        context.prec = 50
        if counts[0] and layout['structure_nearest_d2'][0] != MISSING:
            units[6] = max(Decimal(0),1-Decimal(layout['structure_nearest_d2'][0]).sqrt()/1024)*LCM
        total = sum(c*u for c,u,k in zip(coefficients,units,known) if k)
    return total, sum(coefficients)*LCM, all(k for c,k in zip(coefficients,known) if c)


def canonical_tail(layout):
    return (int(layout['seed']) & ((1<<64)-1), *layout['anchor'], layout['layout_id'])
