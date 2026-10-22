"""Integer geometry; no changes to the native personal-search conventions."""
from .registry import SIDES, RADII, AXIS


def integer(value, lo=-(1 << 31), hi=(1 << 31)-1):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError('Integer outside declared range')
    return value


def bounds_for(anchor, side):
    if side not in SIDES or type(side) is not int or len(anchor) != 2:
        raise ValueError('Unsupported layout')
    x, z = (integer(v) for v in anchor)
    return (x-side//2, z-side//2, x+side//2, z+side//2)


def inside(x, z, bounds):
    return bounds[0] <= x < bounds[2] and bounds[1] <= z < bounds[3]


def distance2(x, z, anchor):
    return (x-anchor[0])**2 + (z-anchor[1])**2


def eligible(x, z, anchor, side, radius=None):
    return inside(x, z, bounds_for(anchor, side)) and (radius is None or distance2(x, z, anchor) <= radius**2)


def contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def tile(x, z):
    return integer(x)//256, integer(z)//256


def anchors():
    return tuple((x, z) for x in AXIS for z in AXIS)

