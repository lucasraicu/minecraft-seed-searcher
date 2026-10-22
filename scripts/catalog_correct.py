#!/usr/bin/env python3
"""Dry-run by default; publish only the pinned reviewed candidate corrections."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from seed_search.catalog.corrections import reviewed_ledger, refresh_catalog
from seed_search.catalog.segments import SegmentedCatalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    ledger = reviewed_ledger()
    if not (args.root / 'pilot.sqlite').is_file():
        parser.error('An existing dedicated catalog root is required')
    with SegmentedCatalog(args.root) as store:
        info = store.info(ledger['source_snapshot_id'])
        if info['header'] != ledger['source_header'] or (info['worlds'], info['layouts']) != (200,48600):
            raise ValueError('Unreviewed source population')
        result = (refresh_catalog(store) if args.execute else
                  dict(dry_run=True, source=info, exclusions=ledger['removals'],
                       scope='New immutable research generation; no native extraction or game run'))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
