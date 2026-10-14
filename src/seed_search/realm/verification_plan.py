"""Plan actual analysis coverage separately from mandatory Realm membership."""
import math

from .terrain import V1, V2


def verification_region(result, variant, cfg, spacing):
    """Use the exact coastal border or the historical formation support halo.

    A limited BDS tile budget may defer this request, but must never shrink it
    to a region that cannot support the requested geometry evaluation.
    """
    if variant not in ('v1', 'v2'):
        raise ValueError('Verification variant must be v1 or v2')
    if variant not in (cfg.get('terrain') or {}).get('variants', ('v1', 'v2')):
        raise ValueError('Requested terrain variant is inactive in this saved configuration')
    if isinstance(spacing, bool) or not isinstance(spacing, int) or spacing < 1:
        raise ValueError('Verification spacing must be a positive integer')
    footprint = (result.get('border_fit') or {}).get('footprint')
    if footprint is None and 'bounds' in result:
        b = result.get('bounds')
        if isinstance(b, dict):
            b = b.get('overworld')
        if b is not None:
            footprint = b
    center = result.get('center')
    if center is None:
        center = result.get('evaluation_center') or result.get('stronghold')
    if footprint is None:
        return None
    if (not isinstance(center, (list, tuple)) or len(center) != 2 or
        any(isinstance(v, bool) or not isinstance(v, int) for v in center)):
        raise ValueError('Verification requires an integer terrain center')
    if (not isinstance(footprint, (list, tuple)) or len(footprint) != 4 or
        any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in footprint) or
        footprint[0] >= footprint[2] or footprint[1] >= footprint[3]):
        raise ValueError('Invalid measured formation footprint')
    from .coastal import coastal_mode
    if variant == 'v1' and coastal_mode(cfg):
        x, z = center
        cand_bounds = result.get('bounds')
        if isinstance(cand_bounds, dict):
            cand_bounds = cand_bounds.get('overworld')
        side = ((cfg.get('terrain') or {}).get('v1') or {}).get('square_side_blocks')
        if side is None:
            side = (cfg.get('deployment') or {}).get('overworld_side_blocks')
        if side is None:
            inferred = footprint[2] - footprint[0]
            side = inferred if inferred in (1536, 2048) else 1536
        if isinstance(side, bool) or side not in (1536, 2048):
            raise ValueError('Unsupported coastal verification square')
        if cand_bounds is not None and tuple(cand_bounds) != tuple(footprint):
            raise ValueError('Candidate bounds differ from measured coastal footprint')
        half = side // 2
        bounds = (x - half, z - half, x + half, z + half)
        if tuple(footprint) != bounds:
            raise ValueError(f'Coastal verification requires a fixed Stronghold{side} footprint')
        return bounds
    policy = {**(V1 if variant == 'v1' else V2), **((cfg.get('terrain') or {}).get(variant) or {})}
    extent = (policy['diameter_max'] + max(policy['ideal_water_width'], policy['water_width'])
              if variant == 'v1' else policy['distance_max'] + 8*policy['ridge_support_width'])
    radius = math.ceil(extent + 2*spacing)
    x, z = center
    return (min(math.floor(footprint[0])-spacing, x-radius),
            min(math.floor(footprint[1])-spacing, z-radius),
            max(math.ceil(footprint[2])+spacing, x+radius+1),
            max(math.ceil(footprint[3])+spacing, z+radius+1))
