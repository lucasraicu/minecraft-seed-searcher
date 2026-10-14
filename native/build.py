from pathlib import Path
import os
import platform
from cffi import FFI

ROOT = Path(__file__).resolve().parents[1]
ffibuilder = FFI()
header = (ROOT / "native/bridge.h").read_text()
ffibuilder.cdef("\n".join(line for line in header.splitlines() if not line.startswith("#")))
units = ["noise", "biomes", "layers", "biomenoise", "cave", "generator", "finders", "util", "quadbase", "mt"]
compile_args = ["-O3", "-std=c11", "-fwrapv"]
include_dirs = [str(ROOT / "native"), str(ROOT / "vendor/cubiomes-bedrock")]
libraries = ["m"]
library_dirs, link_args = [], []
# Portable serial is the default. The opt-in runtime must be explicitly supplied;
# no machine-specific ISA is enabled by this build path.
prefix = os.environ.get("SEED_SEARCH_OPENMP_PREFIX")
if prefix:
    prefix = Path(prefix).resolve()
    if not (prefix / "include/omp.h").is_file():
        raise ValueError("OpenMP prefix needs include/omp.h")
    if platform.system() == "Darwin":
        # The local runtime is host-architecture only; do not silently link it to
        # Python's other universal2 slice. Serial builds retain universal2.
        required = "-arch " + platform.machine()
        if os.environ.get("ARCHFLAGS") != required:
            raise ValueError(f"OpenMP host build requires explicit ARCHFLAGS='{required}'")
        compile_args += ["-Xpreprocessor", "-fopenmp"]
    else:
        compile_args += ["-fopenmp"]
    include_dirs += [str(prefix / "include")]
    runtime=prefix/'lib'/('libomp.dylib' if platform.system()=='Darwin' else 'libomp.so')
    if not runtime.is_file():raise ValueError('OpenMP prefix needs its shared runtime library')
    compile_args += ['-DSS_OPENMP_LIBRARY="'+str(runtime)+'"']
    library_dirs += [str(prefix / "lib")]
    libraries += ["omp"]
    link_args += ["-Wl,-rpath," + str(prefix / "lib")]
ffibuilder.set_source(
    "seed_search._native", '#include "bridge.h"',
    sources=[str(ROOT / p) if __name__ == "__main__" else p for p in ["native/bridge.c"] + [f"vendor/cubiomes-bedrock/{u}.c" for u in units]],
    include_dirs=include_dirs,
    extra_compile_args=compile_args,
    libraries=libraries, library_dirs=library_dirs, extra_link_args=link_args,
)
if __name__ == "__main__":
    os.chdir(ROOT)
    (ROOT / "build").mkdir(exist_ok=True)
    # Match Python's extension loader; a macOS .dylib can otherwise leave an
    # older .abi3.so silently active after a successful standalone build.
    ffibuilder.compile(tmpdir="build", target=str(ROOT / "src/seed_search/_native.abi3.so"), verbose=True)
