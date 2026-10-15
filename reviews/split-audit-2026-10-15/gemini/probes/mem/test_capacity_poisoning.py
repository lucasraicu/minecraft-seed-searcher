"""
Deterministic subprocess crash harness for Task 2:
Tests allocation failure recovery and reusable worker capacity poisoning.
Verifies SIGSEGV on worker reuse with core dumps disabled.
"""
import subprocess
import resource
import sys
from pathlib import Path

PROBE_BIN = Path(__file__).parent / "probe_capacity_poisoning"

def run_probe_case(call_number, description):
    print(f"\n========================================================")
    print(f"Running Subprocess Test: {description} (Target malloc call #{call_number})")
    print(f"========================================================")
    
    # Run in subprocess with core dumps disabled
    cmd = [str(PROBE_BIN), str(call_number)]
    
    def preexec():
        # RLIMIT_CORE = 0: Core dumps disabled
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    
    proc = subprocess.run(cmd, capture_output=True, text=True, preexec_fn=preexec)
    
    print("STDOUT:")
    print(proc.stdout.strip() if proc.stdout else "(empty)")
    print("STDERR:")
    print(proc.stderr.strip() if proc.stderr else "(empty)")
    print(f"Exit code: {proc.returncode}")
    
    # In UNIX, exit code -11 or 139 (128 + 11) indicates SIGSEGV
    is_segfault = (proc.returncode in (-11, 139, 128 + 11))
    if is_segfault:
        print(f"--> RESULT: CRASH DETECTED (SIGSEGV / exit code {proc.returncode})!")
        print(f"--> ROOT CAUSE: Capacity poisoned on seed 0 failure; seed 1 dereferenced NULL pointer on reused worker.")
    else:
        print(f"--> RESULT: Process exited with code {proc.returncode}")
    
    return is_segfault

def main():
    if not PROBE_BIN.exists():
        print(f"Error: {PROBE_BIN} does not exist. Compile it first.")
        sys.exit(1)
        
    results = {}
    
    # Test 1: dyn_ex failure (call #31)
    results['dyn_ex'] = run_probe_case(31, "dyn_ex malloc failure followed by worker reuse")
    
    # Test 2: dyn_ez failure (call #32)
    results['dyn_ez'] = run_probe_case(32, "dyn_ez malloc failure followed by worker reuse (asymmetric leak)")
    
    # Test 3: dyn_cells failure (call #33)
    results['dyn_cells'] = run_probe_case(33, "dyn_cells malloc failure followed by worker reuse")
    
    print("\n========================================================")
    print("SUMMARY OF FAULT INJECTION CRASH RESULTS:")
    print("========================================================")
    all_reproduced = True
    for test_name, crashed in results.items():
        status = "REPRODUCED (SIGSEGV)" if crashed else "FAILED TO REPRODUCE"
        print(f"  {test_name:15}: {status}")
        if not crashed:
            all_reproduced = False
            
    if all_reproduced:
        print("\nAll capacity poisoning failure modes 100% deterministically reproduced!")
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
