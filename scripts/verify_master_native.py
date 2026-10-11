"""Isolated frozen-reference parity and equivalent native workload measurements."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import tarfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/master-implementation-2026-10-10'
PROBE = r'''
int ss_density_points(SeedContext *ctx,const int *xyz,int n,double *out) {
    if(n<0)return -1;
    if(!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);ctx->terrain_ready=1;
    }
    for(int i=0;i<n;i++) {
        int x=xyz[3*i],y=xyz[3*i+1],z=xyz[3*i+2];double offset,factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        out[i]=sampleTerrainDensity(&ctx->terrain,offset,factor,x,y,z);
    }
    return 0;
}
'''


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def build_reference():
    from cffi import FFI
    folder = OUT / 'reference-probe'
    folder.mkdir(exist_ok=True)
    with tarfile.open(OUT / 'pre-change-source.tar.gz') as archive:
        bridge = archive.extractfile('native/bridge.c').read().decode()
        header = archive.extractfile('native/bridge.h').read().decode()
    (folder / 'bridge.c').write_text(bridge + PROBE)
    (folder / 'bridge.h').write_text(header)
    ffi = FFI()
    ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')) +
             '\nint ss_density_points(SeedContext *, const int *, int, double *);')
    name = '_master_reference'
    units = ['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
    ffi.set_source(name, '#include "bridge.h"\nint ss_density_points(SeedContext *,const int *,int,double *);',
                   sources=[str(folder/'bridge.c')] + [str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in units],
                   include_dirs=[str(folder),str(ROOT/'vendor/cubiomes-bedrock')],
                   extra_compile_args=['-O3','-std=c11','-fwrapv'],libraries=['m'])
    path = ffi.compile(tmpdir=str(folder), verbose=True)
    record = {'path':path,'module':name,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    (OUT/'reference-probe.json').write_text(json.dumps(record,indent=2)+'\n')


def compare(threads=1):
    record = json.loads((OUT/'reference-probe.json').read_text())
    reference = module(record['path'],record['module'])
    from seed_search import _native as optimized
    rng = np.random.default_rng(1964)
    points = rng.integers(-6209,6210,(256,2),dtype=np.int32)
    patch = np.array([[x,z] for x in range(-17,19) for z in range(-9,11)],np.int32)
    points = np.ascontiguousarray(np.concatenate([points,patch,patch[::-1],patch[:16]]))
    density = rng.integers(-6209,6210,(1024,3),dtype=np.int32)
    density[:,1] = rng.integers(-64,320,len(density),dtype=np.int32)
    density = np.ascontiguousarray(density)
    grids = (-17,-9,9,7,3,63)
    seeds = [-1,0,9,12345,4294979641,-9048740180577658153,-2**63,2**63-1]
    rows=[]
    for seed in seeds:
        outputs=[]
        for m in (reference,optimized):
            ffi,lib=m.ffi,m.lib
            ctx=lib.ss_create(seed & ((1<<64)-1));assert ctx!=ffi.NULL
            if m is optimized:assert lib.ss_set_threads(ctx,threads)==0
            try:
                result={}
                land=np.empty(len(points),np.int32)
                assert lib.ss_land(ctx,ffi.from_buffer('int[]',points),len(points),ffi.from_buffer('int[]',land))==0
                result['land']=land
                for step in (1,8,16):
                    h=np.empty(len(points),np.int32);b=np.empty(len(points),np.int32)
                    assert lib.ss_heights(ctx,ffi.from_buffer('int[]',points),len(points),step,ffi.from_buffer('int[]',h),ffi.from_buffer('int[]',b))==0
                    result[f'heights{step}']=h;result[f'biomes{step}']=b
                d=np.empty(len(density),np.float64)
                assert lib.ss_density_points(ctx,ffi.from_buffer('int[]',density),len(density),ffi.from_buffer('double[]',d))==0
                result['density']=d
                b=np.empty(grids[2]*grids[3],np.int32);c=np.empty((len(b),6),np.float64);a=np.empty(len(b),np.float64)
                assert lib.ss_grid(ctx,*grids,ffi.from_buffer('int[]',b),ffi.from_buffer('double[]',c),ffi.from_buffer('double[]',a))==0
                result.update(grid=b,climate=c,approx=a)
                outputs.append(result)
            finally:lib.ss_destroy(ctx)
        for key in outputs[0]:
            assert np.array_equal(outputs[0][key].view(np.uint8),outputs[1][key].view(np.uint8)),(seed,key)
        rows.append({'seed':str(seed),'arrays_bitwise_equal':list(outputs[0]),'land_columns':len(points),'density_points':len(density)})
    (OUT/f'native-parity-threads{threads}.json').write_text(json.dumps({'status':'PASS','threads':threads,'rows':rows},indent=2)+'\n')
    print(f'Exact native parity passed for {len(seeds)} seeds, all strides, land, raw density and biome/climate grids.')


def benchmark():
    record=json.loads((OUT/'reference-probe.json').read_text());reference=module(record['path'],record['module'])
    from seed_search import _native as optimized
    from seed_search.cache import CachedBackend
    import seed_search.backend as wrapper
    original=(wrapper.ffi,wrapper.lib)
    patch=np.array([[x,z] for z in range(-32,32) for x in range(-32,32)],np.int32)
    grouped=np.ascontiguousarray(np.unique(patch//4,axis=0)*4)
    measurements={};seeds=(-1,12345,4294979641)
    try:
        for trial in range(3):
            for name,m in ((('reference',reference),('optimized',optimized)) if trial%2==0 else (('optimized',optimized),('reference',reference))):
                wrapper.ffi,wrapper.lib=m.ffi,m.lib
                for seed in seeds:
                    for kind in ('land_dense','land_unique','land_python_cache','height8','height1'):
                        points=grouped if kind=='land_unique' else patch
                        with CachedBackend(seed) as backend:
                            backend.heights(points[:1])
                            start=time.perf_counter()
                            if kind=='land_python_cache':values=backend.land(points)
                            elif kind.startswith('land'):values=super(CachedBackend,backend).land(points)
                            else:values=super(CachedBackend,backend).heights(points,1 if kind=='height1' else 8)
                            elapsed=time.perf_counter()-start
                        measurements.setdefault((name,str(seed),kind),[]).append(elapsed)
    finally:wrapper.ffi,wrapper.lib=original
    rows=[{'variant':n,'seed':s,'workload':k,'seconds':v,'median_seconds':statistics.median(v)} for (n,s,k),v in sorted(measurements.items())]
    summary={}
    for kind in ('land_dense','land_unique','land_python_cache','height8','height1'):
        totals={n:sum(r['median_seconds'] for r in rows if r['variant']==n and r['workload']==kind) for n in ('reference','optimized')}
        summary[kind]={**totals,'speedup':totals['reference']/totals['optimized']}
    (OUT/'native-timing.json').write_text(json.dumps({'rows':rows,'summary':summary,'scope':'Three seeds, three alternating trials; no whole-search speedup implied'},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','parity','benchmark'])
    parser.add_argument('--threads',type=int,default=1)
    args=parser.parse_args()
    if args.command=='parity':compare(args.threads)
    else:{'build':build_reference,'benchmark':benchmark}[args.command]()
