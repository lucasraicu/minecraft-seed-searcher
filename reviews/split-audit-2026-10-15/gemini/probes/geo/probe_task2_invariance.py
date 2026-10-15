"""Probe Task 2: Check membership invariance of mandatory structures and biome prefix across equivalence cells.
"""
import math

def floordiv(a, b):
    return a // b

def palette_indices(x):
    x0 = -floordiv(-((x - 832) + 1984), 64)
    x1 = -floordiv(-((x + 832) + 1984), 64)
    return x0, x1

def main():
    # Check all transitions of x0 and x1 as x ranges from -1168 to 1168
    x0_transitions = []
    x1_transitions = []
    prev_x0, prev_x1 = palette_indices(-1169)
    for x in range(-1168, 1169):
        x0, x1 = palette_indices(x)
        if x0 != prev_x0:
            x0_transitions.append((x, prev_x0, x0))
            prev_x0 = x0
        if x1 != prev_x1:
            x1_transitions.append((x, prev_x1, x1))
            prev_x1 = x1
            
    print(f"Number of x0 transitions: {len(x0_transitions)}")
    print(f"Number of x1 transitions: {len(x1_transitions)}")
    
    # What are the raw events generated for lattice?
    # for v in range(-1984, 1985, 64):
    #   entry: v - 831
    #   exit: v + 833
    entry_events = set(v - 831 for v in range(-1984, 1985, 64))
    exit_events = set(v + 833 for v in range(-1984, 1985, 64))
    
    x1_trans_set = set(t[0] for t in x1_transitions)
    x0_trans_set = set(t[0] for t in x0_transitions)
    
    print("\nCheck x1 transitions vs entry_events (in domain -1168..1168):")
    entry_in_domain = set(e for e in entry_events if -1168 <= e <= 1168)
    diff_entry = entry_in_domain ^ x1_trans_set
    print(f"  entry_in_domain count: {len(entry_in_domain)}, x1_trans count: {len(x1_trans_set)}, symmetric diff: {diff_entry}")
    
    print("\nCheck x0 transitions vs exit_events (in domain -1168..1168):")
    exit_in_domain = set(e for e in exit_events if -1168 <= e <= 1168)
    diff_exit = exit_in_domain ^ x0_trans_set
    print(f"  exit_in_domain count: {len(exit_in_domain)}, x0_trans count: {len(x0_trans_set)}, symmetric diff: {diff_exit}")

if __name__ == '__main__':
    main()
