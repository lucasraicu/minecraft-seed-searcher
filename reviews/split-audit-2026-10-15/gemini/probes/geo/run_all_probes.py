"""Master execution script for all Geometry and Scoring audit probes.
"""
import subprocess
import sys
import os

PROBES = [
    'probe_task1_events.py',
    'probe_nether_equiv.py',
    'probe_task2_invariance.py',
    'probe_task2_nether.py',
    'probe_task3_optional_drift.py',
    'probe_task5_scoring.py',
]

def main():
    probe_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(probe_dir, '../../../../..'))
    env = dict(os.environ, PYTHONPATH=repo_root)
    python_bin = sys.executable

    print("="*70)
    print("RUNNING ALL GEOMETRY AND SCORING AUDIT PROBES")
    print(f"Repo root: {repo_root}")
    print(f"Python:    {python_bin}")
    print("="*70)

    all_passed = True
    for probe in PROBES:
        path = os.path.join(probe_dir, probe)
        print(f"\n---> Running {probe}...")
        res = subprocess.run([python_bin, path], cwd=repo_root, env=env, capture_output=True, text=True)
        print(res.stdout.strip())
        if res.stderr.strip():
            print("STDERR:\n" + res.stderr.strip())
        if res.returncode != 0:
            print(f"FAILED with exit code {res.returncode}")
            all_passed = False
        else:
            print(f"SUCCESS: {probe}")

    print("\n" + "="*70)
    if all_passed:
        print("ALL PROBES COMPLETED SUCCESSFULLY.")
    else:
        print("SOME PROBES FAILED.")
    print("="*70)

if __name__ == '__main__':
    main()
