"""Optional complete blueprint extension; portable serial unless OpenMP is explicit."""
from pathlib import Path
import os
import sys
from cffi import FFI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from native.build import units, compile_args, include_dirs, libraries, library_dirs, link_args

ffibuilder = FFI()
header = (ROOT / 'native/blueprint_batch.h').read_text()
ffibuilder.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')))
ffibuilder.set_source('seed_search._blueprint_batch',
    '#include "bridge.c"\n#include "blueprint_batch.inc"\n',
    sources=[f'vendor/cubiomes-bedrock/{u}.c' for u in units],
    include_dirs=include_dirs, extra_compile_args=compile_args, libraries=libraries,
    library_dirs=library_dirs, extra_link_args=link_args)

if __name__ == '__main__':
    os.chdir(ROOT)
    ffibuilder.compile(tmpdir='.', target=str(ROOT / 'src/seed_search/_blueprint_batch.abi3.so'), verbose=True)
