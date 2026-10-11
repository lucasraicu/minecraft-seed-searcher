from pathlib import Path
from cffi import FFI

ROOT = Path(__file__).resolve().parents[1]
ffibuilder = FFI()
header = (ROOT / "native/bridge.h").read_text()
ffibuilder.cdef("\n".join(line for line in header.splitlines() if not line.startswith("#")))
units = ["noise", "biomes", "layers", "biomenoise", "cave", "generator", "finders", "util", "quadbase", "mt"]
ffibuilder.set_source(
    "seed_search._native", '#include "bridge.h"',
    sources=["native/bridge.c"] + [f"vendor/cubiomes-bedrock/{u}.c" for u in units],
    include_dirs=["native", "vendor/cubiomes-bedrock"],
    extra_compile_args=["-O3", "-std=c11", "-fwrapv"],
    libraries=["m"],
)
if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    ffibuilder.compile(tmpdir=".", target=str(ROOT / "src/seed_search/_native.*"), verbose=True)
