#!/usr/bin/env python3
"""Build the diagnostic probe outside the repository, preserving serving binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UNITS = 'noise biomes layers biomenoise cave generator finders util quadbase mt'.split()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('block', 'nodes'), default='block',
                        help='block sampling (default) or raw quart climate nodes')
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.is_relative_to(ROOT) or output.exists():
        parser.error('Use a new output path outside the repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    vendor = ROOT / 'vendor/cubiomes-bedrock'
    entry = 'biome_node_probe.c' if args.mode == 'nodes' else 'biome_sampling_probe.c'
    sources = [ROOT / 'scripts' / entry] + [vendor / (u + '.c') for u in UNITS]
    inputs = sources + ([ROOT / 'scripts/biome_sampling_probe.c'] if args.mode == 'nodes' else []) + sorted(vendor.glob('*.h')) + sorted((vendor / 'tables').glob('*.h'))
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    command = ['cc', '-O2', '-std=c11', '-fwrapv', '-I', str(vendor),
               *map(str, sources), '-lm', '-o', str(output)]
    subprocess.run(command, check=True, timeout=60)
    record = dict(command=command, source_sha256=hashes,
                  binary_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  compiler=subprocess.check_output(['cc', '--version'], text=True, timeout=10).splitlines()[0])
    Path(str(output) + '.build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
