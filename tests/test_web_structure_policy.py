"""Execute UI alias/display/edit/launch regressions against the TypeScript source."""
from pathlib import Path
import subprocess


def test_web_structure_policy():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['node', '--test', str(root / 'tests/web_structure_policy.cjs')],
                   cwd=root, check=True, capture_output=True, text=True)
