"""Master Verification Runner for Adversarial Audit Agent G-VERIFY.

Executes all verification probes and aggregates dispositions across all findings.
"""

import sys
import subprocess
from pathlib import Path

VERIFY_DIR = Path(__file__).parent
ROOT = VERIFY_DIR.parents[4]

PROBES = [
    ("verify_geo_optional_drift.py", "G-GEO-01 / Prior P1-1: Optional Structure Boundary Drift & Fixture Parity"),
    ("verify_secondary_findings.py", "Secondary Findings: G-GEO-03, G-MEM-04/05, G-FFI-03/04/05, G-STORE-03/04/05/06/07/08"),
    ("verify_lazy_generator.py", "Performance Proposal: lazy-generator.patch Parity & Full64 Verification"),
]

def run_probe(filename, description):
    print(f"\n{'='*75}")
    print(f"RUNNING: {description}")
    print(f"SCRIPT:  {filename}")
    print(f"{'='*75}")
    cmd = [str(ROOT / '.venv/bin/python'), str(VERIFY_DIR / filename)]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print("STDERR:\n" + res.stderr.strip())
    print(f"EXIT CODE: {res.returncode}")
    assert res.returncode == 0, f"Probe {filename} failed with exit code {res.returncode}"
    print(f"--> STATUS: PASSED / VERIFIED")

def main():
    print("===========================================================================")
    print("G-VERIFY MASTER ADVERSARIAL VERIFICATION SUITE")
    print("===========================================================================")
    for filename, desc in PROBES:
        run_probe(filename, desc)
    print("\n===========================================================================")
    print("ALL VERIFICATION PROBES EXECUTED AND PASSED SUCCESSFULLY!")
    print("===========================================================================")

if __name__ == '__main__':
    main()
