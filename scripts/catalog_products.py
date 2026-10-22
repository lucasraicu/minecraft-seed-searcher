#!/usr/bin/env python3
"""Derive research previews from existing catalog observations; never extract seeds."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--snapshot', required=True)
    args = parser.parse_args(argv)
    # Separate offline process: bounded CPU, peak RSS checked per observation.
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    from seed_search.catalog.segments import SegmentedCatalog
    from seed_search.catalog.product_views import derive_previews, write_previews
    started = time.monotonic()
    with SegmentedCatalog(args.root) as store:
        payload = derive_previews(store, args.snapshot, deadline=started + 300)
    destination = write_previews(args.root, payload)
    print(json.dumps(dict(path=str(destination), snapshot_id=args.snapshot,
                          population_worlds=payload['population_worlds'],
                          wall_seconds=time.monotonic() - started)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
