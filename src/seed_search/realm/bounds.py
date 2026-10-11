"""Half-open block bounds; only the legacy native adapter uses inclusive maxima."""
import math
from fractions import Fraction


def square(center, side):
    if isinstance(side, bool) or not isinstance(side, int) or side <= 0 or side % 2:
        raise ValueError('Square width must be a positive even integer')
    half = side // 2
    return (center[0]-half, center[1]-half, center[0]+half, center[1]+half)


def contains(point, bounds):
    return bounds[0] <= point[0] < bounds[2] and bounds[1] <= point[1] < bounds[3]


def native_bounds(bounds):
    """Integer membership interval for an inclusive native query (also fractional bounds)."""
    lo = (math.ceil(bounds[0]), math.ceil(bounds[1]))
    hi = (math.ceil(bounds[2])-1, math.ceil(bounds[3])-1)
    if lo[0] > hi[0] or lo[1] > hi[1]:
        raise ValueError('Empty block bounds')
    return (*lo, *hi)


def nether_square(stronghold, side=896):
    return square((Fraction(int(stronghold[0]),8), Fraction(int(stronghold[1]),8)), side)


def json_bounds(bounds):
    return [int(v) if int(v) == v else float(v) for v in bounds]


def border_fit(footprint, stronghold, side=1536, complete=True):
    if footprint is None:
        return {'status':'unknown','border_fit':'unknown','footprint':None,'complete':False,
                'overflow':None,'minimum_side_blocks':None}
    border=square(stronghold,side)
    overflow={'west':max(0,border[0]-footprint[0]),'north':max(0,border[1]-footprint[1]),
              'east':max(0,footprint[2]-border[2]),'south':max(0,footprint[3]-border[3])}
    minimum=2*math.ceil(max(stronghold[0]-footprint[0],footprint[2]-stronghold[0],
                            stronghold[1]-footprint[1],footprint[3]-stronghold[1]))
    status='outside' if any(overflow.values()) else 'within' if complete else 'unknown'
    return {'status':status,'border_fit':status,'footprint':json_bounds(footprint),'complete':bool(complete),
            'overflow':overflow,'minimum_side_blocks':minimum,
            'minimum_addon_side_blocks':math.ceil(minimum/32)*32,
            'minimum_is_lower_bound':not complete,'policy_version':'local-formation-footprint-v1'}
