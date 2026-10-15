"""Probe Task 5: Verify scoring formulas for Bastion, Shipwreck, and other categories in Python and C.
"""
from src.seed_search.realm.blueprint import dynamic_score

def main():
    # Test Bastion scoring
    print("Testing Bastion scoring:")
    for b in range(1, 6):
        score = dynamic_score({'bastion': b}, [])
        print(f"  Bastion count = {b}: score = {score}")
    
    # Test Shipwreck scoring
    print("\nTesting Shipwreck scoring:")
    for s in range(4, 9):
        score = dynamic_score({'shipwreck': s}, [])
        print(f"  Shipwreck count = {s}: score = {score}")

    # Test Ocean Monument scoring
    print("\nTesting Ocean Monument scoring:")
    for m in range(0, 4):
        score = dynamic_score({'monument': m}, [])
        print(f"  Monument count = {m}: score = {score}")

if __name__ == '__main__':
    main()
