"""Strict isolated ISA trials; never replaces the portable installed extension."""
import os
os.environ['ARCHFLAGS']='-arch x86_64'
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
import numpy as np
from verify_master_native import module

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/master-implementation-2026-10-10'
CPU=r'''
#include <cpuid.h>
#include <stdint.h>
#include <stdio.h>
int main(void) {
 unsigned a,b,c,d;uint64_t x=0;unsigned lo,hi;int avx=0;
 if(__get_cpuid(1,&a,&b,&c,&d) && (c&(1u<<27)) && (c&(1u<<28))) {
  __asm__ volatile("xgetbv" : "=a"(lo),"=d"(hi) : "c"(0));x=((uint64_t)hi<<32)|lo;avx=(x&6)==6;
 }
 __cpuid_count(7,0,a,b,c,d);
 printf("{\"xcr0\":%llu,\"avx2\":%s,\"avx512f\":%s}\n",(unsigned long long)x,
        avx && (b&(1u<<5))?"true":"false",avx && (x&230)==230 && (b&(1u<<16))?"true":"false");
}
'''


def build():
    from cffi import FFI
    folder=OUT/'isa';folder.mkdir(exist_ok=True)
    (folder/'cpu.c').write_text(CPU)
    subprocess.run(['clang','-O2',str(folder/'cpu.c'),'-o',str(folder/'cpu')],check=True)
    cpu=json.loads(subprocess.check_output([str(folder/'cpu')],text=True))
    (folder/'cpu.json').write_text(json.dumps(cpu,indent=2)+'\n')
    header=(ROOT/'native/bridge.h').read_text();records={}
    for name,flag in (('portable',None),('avx2','-mavx2'),('avx512','-mavx512f')):
        if name=='avx2' and not cpu['avx2'] or name=='avx512' and not cpu['avx512f']:continue
        dest=folder/name;dest.mkdir(exist_ok=True)
        ffi=FFI();ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')))
        flags=['-O3','-std=c11','-fwrapv','-ffp-contract=off','-Rpass=loop-vectorize','-Rpass-missed=loop-vectorize','-Rpass-analysis=loop-vectorize']
        if flag:flags.append(flag)
        module_name='_master_isa_'+name
        ffi.set_source(module_name,'#include "bridge.h"',sources=[str(ROOT/'native/bridge.c')]+[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in ('noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt')],
                       include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],extra_compile_args=flags,libraries=['m'])
        path=ffi.compile(tmpdir=str(dest),verbose=True)
        records[name]={'path':path,'module':module_name,'flags':flags,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
        with (dest/'disassembly.txt').open('w') as stream:
            subprocess.run(['otool','-tvV',path],stdout=stream,check=True)
        (folder/'builds.json').write_text(json.dumps(records,indent=2)+'\n')


def trials():
    import seed_search.backend as wrapper
    from measure_master_acceleration import query
    records=json.loads((OUT/'isa/builds.json').read_text())
    modules={n:module(r['path'],r['module']) for n,r in records.items()}
    original=(wrapper.ffi,wrapper.lib);rows=[];golden=None
    try:
        for trial in range(3):
            for name in modules if trial%2==0 else reversed(modules):
                m=modules[name];wrapper.ffi,wrapper.lib=m.ffi,m.lib
                begin=time.perf_counter();queries=[query((index,1)) for index in range(9)];elapsed=time.perf_counter()-begin
                digests=[r['sha256'] for r in queries]
                if golden is None:golden=digests
                assert digests==golden,'Strict ISA public output differs'
                # Probe values independently, not only terrain classification.
                rng=np.random.default_rng(17);xyz=rng.integers(-2048,2048,(4096,3),dtype=np.int32);xyz[:,1]%=384;xyz[:,1]-=64
                ctx=m.lib.ss_create(12345);raw=np.empty(len(xyz),np.float64)
                try:assert m.lib.ss_density_points(ctx,m.ffi.from_buffer('int[]',xyz),len(xyz),m.ffi.from_buffer('double[]',raw))==0
                finally:m.lib.ss_destroy(ctx)
                if name=='portable':reference_raw=raw
                elif trial==0:assert np.array_equal(reference_raw.view(np.uint8),raw.view(np.uint8))
                rows.append({'variant':name,'trial':trial,'seconds':elapsed})
    finally:wrapper.ffi,wrapper.lib=original;wrapper.configure_native_threads(1)
    summary={name:{'median_seconds':statistics.median(r['seconds'] for r in rows if r['variant']==name),'samples':[r['seconds'] for r in rows if r['variant']==name]} for name in records}
    (OUT/'isa/trials.json').write_text(json.dumps({'rows':rows,'summary':summary,'public_and_raw_arrays_equal':True,
        'scope':'Matched current native column workload after exact reuse; three alternating trials; flags do not prove lane-wise Perlin vectorization'},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('build','trials'));args=p.parse_args()
    {'build':build,'trials':trials}[args.command]()
