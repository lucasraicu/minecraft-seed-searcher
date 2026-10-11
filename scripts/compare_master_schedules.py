"""Private OpenMP schedule comparison on identical mixed column workloads."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time
import numpy as np
from verify_master_native import module

ROOT = Path(__file__).resolve().parents[1]


def private_build(folder, policy):
    from cffi import FFI
    assert platform.machine() == 'x86_64'
    os.environ['ARCHFLAGS'] = '-arch x86_64'
    prefix = ROOT / 'runs/master-implementation-2026-10-10/openmp/install'
    folder.mkdir(parents=True)
    code = (ROOT / 'native/bridge.c').read_text()
    assert code.count('schedule(static)') >= 3
    (folder / 'bridge.c').write_text(code.replace('schedule(static)', 'schedule(' + policy + ',64)'))
    header = (ROOT / 'native/bridge.h').read_text()
    ffi = FFI()
    ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')))
    name = '_master_schedule_' + policy
    units = ('noise', 'biomes', 'layers', 'biomenoise', 'cave', 'generator', 'finders', 'util', 'quadbase', 'mt')
    ffi.set_source(name, '#include "bridge.h"',
                   sources=[str(folder / 'bridge.c')] + [str(ROOT / ('vendor/cubiomes-bedrock/' + u + '.c')) for u in units],
                   include_dirs=[str(ROOT / 'native'), str(ROOT / 'vendor/cubiomes-bedrock'), str(prefix / 'include')],
                   extra_compile_args=['-O3', '-std=c11', '-fwrapv', '-Xpreprocessor', '-fopenmp',
                                       '-DSS_OPENMP_LIBRARY="' + str(prefix / 'lib/libomp.dylib') + '"'],
                   libraries=['m', 'omp'], library_dirs=[str(prefix / 'lib')],
                   extra_link_args=['-Wl,-rpath,' + str(prefix / 'lib')])
    path = ffi.compile(tmpdir=str(folder), verbose=True)
    return module(path, name)


def main(output):
    from seed_search import _native
    from seed_search.backend import Backend, configure_native_threads
    import seed_search.backend as wrapper
    folder = Path(output).resolve()
    if folder.exists():
        raise ValueError('Use a fresh schedule comparison directory')
    folder.mkdir(parents=True)
    installed_hash = hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest()
    profiles = [('static', _native)]
    unavailable = []
    for policy in ('dynamic', 'guided'):
        try:
            profiles.append((policy + '64', private_build(folder / policy, policy)))
        except ImportError as error:
            # Record a failed compiler/runtime gate rather than substitute an
            # unproved ABI shim or time a variant that cannot load.
            unavailable.append({'schedule': policy + '64', 'status': 'UNSUPPORTED',
                                'reason': str(error)})
            print(json.dumps(unavailable[-1]), flush=True)
    profiles = tuple(profiles)
    original = (wrapper.ffi, wrapper.lib)
    points = np.array([[x, z] for z in range(-512, 512, 8) for x in range(-512, 512, 8)], np.int32)
    rows = []
    references = {}
    try:
        for trial in range(3):
            offset = trial % len(profiles)
            ordered = profiles[offset:] + profiles[:offset]
            for name, native in ordered:
                wrapper.ffi, wrapper.lib = native.ffi, native.lib
                configure_native_threads(18)
                for seed in (-1, 9, 12345):
                    begin = time.perf_counter()
                    cpu = time.process_time()
                    stages = {}
                    digest = hashlib.sha256()
                    with Backend(seed) as backend:
                        for stage, query in (('land', lambda: [backend.land(points)]),
                                             ('heights8', lambda: list(backend.heights(points, 8))),
                                             ('grid', lambda: list(backend.grid(-512, -512, 128, 128, 8).values()))):
                            start = time.perf_counter()
                            arrays = query()
                            stages[stage] = time.perf_counter() - start
                            for array in arrays:
                                digest.update(array.tobytes())
                    observed = digest.hexdigest()
                    assert references.setdefault(seed, observed) == observed
                    row = {'schedule': name, 'trial': trial, 'seed': str(seed),
                           'seconds': time.perf_counter() - begin,
                           'cpu_seconds': time.process_time() - cpu,
                           'stage_seconds': stages, 'arrays_sha256': observed}
                    rows.append(row)
                    print(json.dumps(row), flush=True)
    finally:
        wrapper.ffi, wrapper.lib = original
        configure_native_threads(1)
    assert hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest() == installed_hash
    totals = {name: [sum(r['seconds'] for r in rows if r['schedule'] == name and r['trial'] == trial) for trial in range(3)] for name, _ in profiles}
    summary = {name: {'median_seconds': statistics.median(times), 'range_seconds': [min(times), max(times)]} for name, times in totals.items()}
    decision = ('Retain shipped static scheduling. Dynamic/guided alternatives failed the compiler/runtime load gate; no performance comparison or runtime change is claimed.'
                if unavailable else
                'Retain shipped static scheduling. Alternatives are isolated measurements and require an end-to-end caller acceptance trial before promotion.')
    report = {'native_threads': 18, 'columns_per_call': len(points), 'seeds': ['-1', '9', '12345'],
              'arrays_equal': True, 'installed_native_unchanged': True,
              'attempted_schedules': ['static', 'dynamic64', 'guided64'],
              'measured_schedules': [name for name, _ in profiles],
              'unavailable_schedules': unavailable,
              'installed_native_sha256': installed_hash, 'rows': rows, 'summary': summary,
              'scope': 'Cold contexts, three alternating-order trials, land/stride8 heights/grid on identical columns. Native workload only; no concurrent BDS or whole-candidate yield claim.',
              'decision': decision}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'summary': summary, 'arrays_equal': True, 'decision': report['decision']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
