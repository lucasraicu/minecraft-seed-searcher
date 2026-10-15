"""Probe Task 1: Check all 160 raw lattice events and membership transitions.
"""
import sys

def main():
    OW_HALF = 832
    NETHER_HALF = 416
    MIN_C = -1168
    MAX_C = 1168

    ow_samples = list(range(-1984, 1985, 64))
    nether_samples = list(range(-512, 513, 64))

    print(f"OW sample count: {len(ow_samples)} -> {len(ow_samples)*2} events")
    print(f"Nether sample count: {len(nether_samples)} -> {len(nether_samples)*2} events")
    total_raw = len(ow_samples)*2 + len(nether_samples)*2
    print(f"Total raw events: {total_raw}")

    ow_events = []
    for s in ow_samples:
        ow_events.append((s, 'OW_entry', s - 831))
        ow_events.append((s, 'OW_exit', s + 833))

    nether_events = []
    for n in nether_samples:
        nether_events.append((n, 'Nether_entry', 8*(n - 416) + 1))
        nether_events.append((n, 'Nether_exit', 8*(n + 416) + 1))

    all_events = ow_events + nether_events

    in_domain = [e for e in all_events if MIN_C < e[2] <= MAX_C]
    out_domain = [e for e in all_events if not (MIN_C < e[2] <= MAX_C)]

    print(f"Events strictly in ({MIN_C}, {MAX_C}]: {len(in_domain)}")
    print(f"Events outside ({MIN_C}, {MAX_C}]: {len(out_domain)}")

    # Let's inspect the out_domain events
    print("\nOut of domain events:")
    for src, typ, val in sorted(out_domain, key=lambda x: x[2]):
        print(f"  src={src:5d}, type={typ:12s}, val={val:6d}")

if __name__ == '__main__':
    main()
