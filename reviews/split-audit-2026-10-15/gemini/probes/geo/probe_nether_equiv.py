"""Probe: Check if C's nether condition matches Python's nether_bounds for all x, px.
"""
from src.seed_search.realm.dynamic import nether_bounds
from src.seed_search.realm.bounds import contains

def main():
    half = 416
    mismatches = []
    
    # Check all x in [-1168, 1168] and a range of px around the boundary
    for x in range(-1168, 1169):
        nb = nether_bounds((x, 0))
        # check px
        # C condition: 8*(px - half) < x <= 8*(px + half)
        # Python condition: contains((px, 0), nb)
        # The relevant px range is roughly [x/8 - half - 2, x/8 + half + 2]
        min_px = int(x / 8 - half - 2)
        max_px = int(x / 8 + half + 2)
        for px in range(min_px, max_px + 1):
            c_cond = (8 * (px - half) < x <= 8 * (px + half))
            py_cond = contains((px, 0), nb)
            if c_cond != py_cond:
                mismatches.append((x, px, c_cond, py_cond))
                if len(mismatches) <= 10:
                    print(f"Mismatch at x={x}, px={px}: C={c_cond}, Py={py_cond}")

    print(f"Total mismatches: {len(mismatches)}")

if __name__ == '__main__':
    main()
