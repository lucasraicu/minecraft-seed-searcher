"""Probe Task 2 Nether: Check nether prefix transitions match nether lattice events.
"""
def floordiv(a, b):
    return a // b

def nether_indices(x):
    x0 = -floordiv(-(x - 3328 + 4096), 512)
    x1 = -floordiv(-(x + 3328 + 4096), 512)
    return x0, x1

def main():
    x0_trans = []
    x1_trans = []
    prev_x0, prev_x1 = nether_indices(-1169)
    for x in range(-1168, 1169):
        x0, x1 = nether_indices(x)
        if x0 != prev_x0:
            x0_trans.append(x)
            prev_x0 = x0
        if x1 != prev_x1:
            x1_trans.append(x)
            prev_x1 = x1
            
    print(f"Nether x0 transitions: {len(x0_trans)}")
    print(f"Nether x1 transitions: {len(x1_trans)}")
    
    # Events generated in code:
    # 8*(v - 416) + 1  and  8*(v + 416) + 1
    # where v in range(-512, 513, 64)
    # Notice 512 is 8 * 64!
    # Let's check:
    entry_events = set(8*(v - 416) + 1 for v in range(-512, 513, 64))
    exit_events = set(8*(v + 416) + 1 for v in range(-512, 513, 64))
    
    entry_in_domain = set(e for e in entry_events if -1168 <= e <= 1168)
    exit_in_domain = set(e for e in exit_events if -1168 <= e <= 1168)
    
    print("Check x1 transitions vs entry events:")
    diff_entry = entry_in_domain ^ set(x1_trans)
    print(f"  entry in domain: {len(entry_in_domain)}, x1_trans: {len(x1_trans)}, diff: {diff_entry}")
    
    print("Check x0 transitions vs exit events:")
    diff_exit = exit_in_domain ^ set(x0_trans)
    print(f"  exit in domain: {len(exit_in_domain)}, x0_trans: {len(x0_trans)}, diff: {diff_exit}")

if __name__ == '__main__':
    main()
