"""Isolated native experiments; does not install or modify the production backend.

Commands: build, micro, regression, full, seed_order, summarize.
All artifacts are local to OUT.
Run timing commands serially. Native variants are swapped only after handles close.
"""
import os
# The installed Python is universal2. Host-only experiments must not pass x86
# ISA flags to its arm64 compiler slice.
os.environ['ARCHFLAGS'] = '-arch x86_64'
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/simd-test-2026-10-08'
COMMON = ['-O3', '-std=c11', '-fwrapv']
FLAGS = {
    'scalar': COMMON,
    'avx2': COMMON + ['-mavx2', '-ffp-contract=off'],
    'gemini': COMMON + ['-mavx2', '-mfma', '-march=x86-64-v3'],
    'vector4': COMMON + ['-mavx2', '-ffp-contract=off'],
}
PROBE = r'''
int ss_probe_density(SeedContext *ctx, const int *xyz, int n, double *out) {
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready=1;
    }
    for (int i=0;i<n;i++) {
        int x=xyz[3*i], y=xyz[3*i+1], z=xyz[3*i+2];
        double offset,factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        out[i]=sampleTerrainDensity(&ctx->terrain,offset,factor,x,y,z);
    }
    return 0;
}
'''

def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def build(variants):
    from cffi import FFI
    records = json.loads((OUT/'builds.json').read_text()) if (OUT/'builds.json').exists() else {}
    original = (ROOT/'native/bridge.c').read_text()
    header = (ROOT/'native/bridge.h').read_text()
    for variant in variants:
        folder = OUT / ('build-' + variant)
        folder.mkdir(parents=True, exist_ok=True)
        code = original
        if variant == 'vector4':
            code = code.replace('int ss_heights(', 'int ss_scalar_heights(').replace('int ss_land(', 'int ss_scalar_land(')
            code += (ROOT/'scripts/simd_probe_kernel.c').read_text()
        code += PROBE
        bridge = folder/'bridge.c'
        bridge.write_text(code)
        ffi = FFI()
        ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')) +
                 '\nint ss_probe_density(SeedContext *, const int *, int, double *);' +
                 ('\nint ss_probe_density4(SeedContext *, const int *, int, double *);' if variant == 'vector4' else ''))
        name = '_simd_probe_' + variant
        units = ['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
        ffi.set_source(name, '#include "bridge.h"\nint ss_probe_density(SeedContext *, const int *, int, double *);\n' +
                       ('int ss_probe_density4(SeedContext *, const int *, int, double *);\n' if variant == 'vector4' else ''),
                       sources=[str(bridge)] + [str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in units],
                       include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],
                       extra_compile_args=FLAGS[variant], libraries=['m'])
        started = time.perf_counter()
        path = ffi.compile(tmpdir=str(folder), verbose=True)
        records[variant] = {'module': name, 'path': path, 'flags': FLAGS[variant],
                            'seconds': time.perf_counter()-started,
                            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                            'bridge_sha256': hashlib.sha256(bridge.read_bytes()).hexdigest()}
        save('builds.json', records)
        print('BUILT', variant, flush=True)

def activate(variant):
    import seed_search.backend as backend
    if variant == 'installed':
        from seed_search import _native as module
    else:
        record = json.loads((OUT/'builds.json').read_text())[variant]
        spec = importlib.util.spec_from_file_location(record['module'], record['path'])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    backend._RAW_LAYOUTS.clear()
    backend.ffi, backend.lib = module.ffi, module.lib
    return module

def arrays(variant, seed, points, density_points):
    from seed_search.backend import Backend
    module = activate(variant)
    with Backend(seed) as b:
        result = {}
        for step in (1, 8, 16):
            h, ids = b.heights(points, step)
            result['height'+str(step)] = h
            result['biomes'+str(step)] = ids
        result['land'] = b.land(points)
        grid = b.grid(-1056, -992, 17, 17, 64)
        result.update({'grid_'+k: v for k, v in grid.items()})
        values = np.empty(len(density_points), np.float64)
        rc = module.lib.ss_probe_density(b._handle(), module.ffi.from_buffer('int[]', density_points),
                                        len(density_points), module.ffi.from_buffer('double[]', values))
        if rc != 0:
            raise RuntimeError(f'{variant} scalar density probe failed: {rc}')
        result['density'] = values
        if variant == 'vector4':
            vector = np.empty(len(density_points), np.float64)
            rc = module.lib.ss_probe_density4(b._handle(), module.ffi.from_buffer('int[]', density_points),
                                            len(density_points), module.ffi.from_buffer('double[]', vector))
            if rc != 0:
                raise RuntimeError(f'{variant} vector density probe failed: {rc}')
            result['density4'] = vector
    return result

def micro(variants):
    from seed_search.backend import Backend
    seeds = [-1, 0, 9, 12345, 4294979641, -9048740180577658153]
    rng = np.random.default_rng(20261008)
    points = rng.integers(-6504, 6505, (384, 2), dtype=np.int32)
    points[:16] = np.array([(x,z) for x in (-5,-4,-1,0) for z in (-5,-4,-1,0)])
    # Every group of four uses one column, with distinct Y values including boundaries.
    density_points = np.repeat(points[:256], 4, axis=0)
    ys = rng.integers(-64,320,len(density_points),dtype=np.int32)
    ys[:16] = [-64,-63,-57,-56,0,1,7,8,62,63,64,65,312,317,318,319]
    xyz = np.ascontiguousarray(np.column_stack((density_points[:,0],ys,density_points[:,1])), dtype=np.int32)
    parity=[]
    for seed in seeds:
        reference = arrays('scalar', seed, points, xyz)
        for variant in variants:
            got = arrays(variant, seed, points, xyz)
            fields={}
            for key, expected in reference.items():
                current=got[key]
                fields[key]={'equal': bool(np.array_equal(expected,current)),
                             'different_values': int(np.count_nonzero(expected!=current)),
                             'max_absolute_difference': float(np.max(np.abs(expected.astype(float)-current.astype(float))))}
            if 'density4' in got:
                fields['density4']={'equal':bool(np.array_equal(reference['density'],got['density4'])),
                                     'different_values':int(np.count_nonzero(reference['density']!=got['density4'])),
                                     'max_absolute_difference':float(np.max(np.abs(reference['density']-got['density4'])))}
            parity.append({'seed':str(seed),'variant':variant,'fields':fields,
                           'density_sign_equal':bool(np.array_equal(reference['density']>0,got.get('density4',got['density'])>0))})
        print('PARITY', seed, flush=True)
        save('micro-parity.json', {'rows':parity,'points_per_seed':len(points),'density_samples_per_seed':len(xyz)})
    # Separate fixed workloads: height raster and mixed land/water coastline columns.
    timings=[]
    for seed in (0,12345,4294979641):
        for operation in ('height8','height1','land','quart_land'):
            if operation in ('land','quart_land'):
                x,z=np.meshgrid(np.arange(-65,-1),np.arange(-33,31))
            else:
                x,z=np.meshgrid(np.arange(-1024,1024,64),np.arange(-1024,1024,64))
            p=np.ascontiguousarray(np.column_stack((x.ravel(),z.ravel())),dtype=np.int32)
            reference=None
            for trial in range(3):
                order=variants[trial%len(variants):]+variants[:trial%len(variants)]
                for variant in order:
                    activate(variant)
                    with Backend(seed) as b:
                        b.land(np.array([[0,0]],np.int32))  # Exclude one-time terrain initialization equally.
                        started=time.perf_counter()
                        if operation.startswith('height'):
                            answer=b.heights(p,int(operation[6:]))
                        elif operation=='land':answer=(b.land(p),)
                        else:
                            cells,inverse=np.unique(p//4,axis=0,return_inverse=True)
                            answer=(b.land(cells*4)[inverse],)
                        elapsed=time.perf_counter()-started
                    if reference is None:reference=answer
                    timings.append({'seed':str(seed),'operation':operation,'trial':trial,'variant':variant,
                                    'seconds':elapsed,'points':len(p),
                                    'outputs_equal':all(np.array_equal(a,b) for a,b in zip(reference,answer))})
            print('TIMING',seed,operation,flush=True)
            save('micro-timing.json', {'rows':timings,'trials':3,'scope':'Repeated rotated-order, fixed points; setup excluded; no search or report timings.'})

def regression(variants):
    from seed_search.regression import regression as check
    rows=[]
    for variant in variants:
        activate(variant)
        try:
            result=check(OUT/('regression-'+variant))
            rows.append({'variant':variant,'passed':True,'summary':result['summary']})
        except ValueError as error:
            rows.append({'variant':variant,'passed':False,'error':str(error)})
        save('regression-summary.json', rows)
        print('REGRESSION',rows[-1],flush=True)

def seed_order():
    """Run in a fresh process: reproduce the installed binary's cold -1 defect."""
    from seed_search.backend import Backend
    activate('installed')
    bounds=(-1024,-1024,1024,1024)
    rows=[]
    for seed in (-1,-1,0,-1,-1):
        with Backend(seed) as b:
            positions=b.structures('mineshaft',bounds,False)
        rows.append({'seed':str(seed),'count':len(positions),'positions':positions})
    save('mineshaft-installed-seed-order.json',
         {'backend':'installed unchanged production binary','bounds':bounds,'rows':rows})
    print('INSTALLED SEED ORDER',[(r['seed'],r['count']) for r in rows],flush=True)

def full(variants, seeds, repeats):
    from seed_search.config import load_config
    from seed_search.cache import CachedBackend
    from seed_search.backend import Backend
    import seed_search.landscapes as landscapes
    class Quart(CachedBackend):
        def land(self, points):
            return self._sample(points,'experiment_land_quart',4,128,1,np.int8,-128,
                                lambda p:Backend.land(self,p))[:,0].astype(bool)
    cfg,config_hash=load_config(ROOT/'search.example.yaml')
    fields=('index','seed','candidates','near_misses','counts','filter_policy')
    rows=[]; references={}
    arms=[(variant,reuse) for variant in variants for reuse in (False,True)]
    for trial in range(repeats):
        for seed in seeds:
            order=arms if trial%2==0 else list(reversed(arms))
            for variant,reuse in order:
                activate(variant)
                landscapes.CachedBackend=Quart if reuse else CachedBackend
                started=time.perf_counter()
                r=landscapes.analyze_landscapes((0,seed,cfg))
                elapsed=time.perf_counter()-started
                core={key:r[key] for key in fields}
                if seed not in references:references[seed]=core
                equal=core==references[seed]
                row={'variant':variant,'quart_reuse':reuse,'trial':trial,'seed':str(seed),
                     'seconds':elapsed,'stage_seconds':r['stage_seconds'],'equal':equal,
                     'candidate_count':len(r['candidates']),'cache':r['cache']}
                rows.append(row)
                save(f'full-{seed}-{variant}-{int(reuse)}-{trial}.json',r)
                save('full-summary.json',{'rows':rows,'config_sha256':config_hash,'compared_fields':fields,
                     'scope':'Sequential complete-seed analysis, no cProfile/pool/export. Geometry remains current 3008/992.'})
                print('FULL',seed,variant,reuse,trial,round(elapsed,3),equal,flush=True)
    landscapes.CachedBackend=CachedBackend
    activate('installed')

def summarize():
    summary=json.loads((OUT/'full-summary.json').read_text())
    rows=summary['rows']; fields=summary['compared_fields']
    if len(rows)!=36:
        raise ValueError('The declared comparison requires all 36 analyses')
    def payload(seed,variant,reuse,trial):
        value=json.loads((OUT/f'full-{seed}-{variant}-{int(reuse)}-{trial}.json').read_text())
        return {k:value[k] for k in fields}
    def differences(a,b,path=''):
        if type(a)!=type(b):return [path]
        if isinstance(a,dict):
            out=[]
            for k in sorted(a.keys()|b.keys()):
                out.extend([path+'/'+k] if k not in a or k not in b else differences(a[k],b[k],path+'/'+k))
            return out
        if isinstance(a,list):
            if len(a)!=len(b):return [path+'/length']
            return [p for i,(x,y) in enumerate(zip(a,b)) for p in differences(x,y,path+f'/{i}')]
        return [] if a==b else [path]
    parity=[]; per_seed=[]; repeat_differences={}
    seeds=sorted({r['seed'] for r in rows},key=int)
    for seed in seeds:
        repeat_differences[seed]=differences(payload(seed,'scalar',False,0),payload(seed,'scalar',False,1))
        for trial in (0,1):
            baseline=payload(seed,'scalar',False,trial)
            for r in rows:
                if r['seed']!=seed or r['trial']!=trial:continue
                paths=differences(baseline,payload(seed,r['variant'],r['quart_reuse'],trial))
                parity.append({'seed':seed,'trial':trial,'variant':r['variant'],
                               'quart_reuse':r['quart_reuse'],'equal':not paths,'different_paths':paths})
        for variant in ('scalar','avx2','vector4'):
            for reuse in (False,True):
                values=[r['seconds'] for r in rows if r['seed']==seed and r['variant']==variant and r['quart_reuse']==reuse]
                if len(values)!=2:raise ValueError('Missing or duplicated trial')
                per_seed.append({'seed':seed,'variant':variant,'quart_reuse':reuse,
                                 'median_seconds':statistics.median(values),'trial_seconds':values})
    totals=[{'variant':v,'quart_reuse':q,
             'sum_per_seed_median_seconds':sum(r['median_seconds'] for r in per_seed if r['variant']==v and r['quart_reuse']==q)}
            for v in ('scalar','avx2','vector4') for q in (False,True)]
    result={'within_trial_parity':parity,'cross_trial_scalar_different_paths':repeat_differences,
            'original_cross_trial_mismatches':sum(not r['equal'] for r in rows),
            'per_seed_timings':per_seed,'aggregate_timings':totals,
            'scope':'Match initialization history within each trial. Cold -1 repeat defect remains a failed production invariant.'}
    save('analysis.json',result)
    print(json.dumps({'within_trial_equal':all(r['equal'] for r in parity),
                      'original_cross_trial_mismatches':result['original_cross_trial_mismatches'],
                      'aggregate_timings':totals},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['build','micro','regression','full','seed_order','summarize'])
    parser.add_argument('--variants',nargs='+',default=['scalar','avx2','gemini','vector4'],choices=FLAGS)
    parser.add_argument('--seeds',nargs='+',type=int,default=[-1,12345,4294979641])
    parser.add_argument('--repeats',type=int,default=2)
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.phase=='build':build(args.variants)
    elif args.phase=='micro':micro(args.variants)
    elif args.phase=='regression':regression(args.variants)
    elif args.phase=='seed_order':seed_order()
    elif args.phase=='summarize':summarize()
    else:full(args.variants,args.seeds,args.repeats)
