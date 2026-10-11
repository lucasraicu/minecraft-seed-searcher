"""Plan actual analysis coverage separately from mandatory Realm membership."""
import math

from .terrain import V1, V2


def verification_region(result, variant, cfg, spacing):
    """Include the measured formation and the evaluator's complete support halo.

    A limited BDS tile budget may defer this request, but must never shrink it
    to a region that cannot support the requested geometry evaluation.
    """
    if variant not in ('v1', 'v2'):
        raise ValueError('Verification variant must be v1 or v2')
    if isinstance(spacing, bool) or not isinstance(spacing, int) or spacing < 1:
        raise ValueError('Verification spacing must be a positive integer')
    footprint = result.get('border_fit', {}).get('footprint')
    center = result.get('center')
    if footprint is None:
        return None
    if (not isinstance(center, (list, tuple)) or len(center) != 2 or
        any(isinstance(v, bool) or not isinstance(v, int) for v in center)):
        raise ValueError('Verification requires an integer terrain center')
    if (not isinstance(footprint, (list, tuple)) or len(footprint) != 4 or
        any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in footprint) or
        footprint[0] >= footprint[2] or footprint[1] >= footprint[3]):
        raise ValueError('Invalid measured formation footprint')
    policy = {**(V1 if variant == 'v1' else V2), **cfg.get('terrain', {}).get(variant, {})}
    extent = (policy['diameter_max'] + max(policy['ideal_water_width'], policy['water_width'])
              if variant == 'v1' else policy['distance_max'] + 8*policy['ridge_support_width'])
    radius = math.ceil(extent + 2*spacing)
    x, z = center
    return (min(math.floor(footprint[0])-spacing, x-radius),
            min(math.floor(footprint[1])-spacing, z-radius),
            max(math.ceil(footprint[2])+spacing, x+radius+1),
            max(math.ceil(footprint[3])+spacing, z+radius+1))
