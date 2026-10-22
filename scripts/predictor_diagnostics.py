#!/usr/bin/env python3
"""Replay portable BDS/predictor evidence without launching Minecraft or search."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.realm.predictor_diagnostics import diagnostic_report, replay_probe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=ROOT / 'fixtures/bedrock-26.52/predictor-corrections')
    parser.add_argument('--probe', type=Path, help='Optional isolated sampler executable; no BDS launch')
    parser.add_argument('--resolution-fixtures', type=Path, help='Optional persistence/membership supplement; preserves original outcomes')
    args = parser.parse_args(argv)
    report = diagnostic_report(args.fixtures)
    if args.resolution_fixtures:
        from seed_search.realm.predictor_resolution import resolution_report
        report['resolution_supplement'] = resolution_report(args.resolution_fixtures)
    if args.probe:
        report['probe_replay'] = replay_probe(args.fixtures, args.probe)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report.get('probe_replay', {}).get('identical_to_saved', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
