"""Build the private complete-baseline prototype without replacing production."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import sysconfig
import time
from pathlib import Path

from cffi import FFI

ROOT=Path(__file__).resolve().parents[1]
UNITS=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']


def build(output,openmp_prefix=None,*,profile=False,disable_mansion_cache=False,work_chunk=16,
          cpu_native=False,lto=False,pgo_generate=False,pgo_use=None,
          experiment_order=0,stronghold_after=4):
    if type(work_chunk) is not int or work_chunk not in (16,64,128):
        raise ValueError('Work chunk must be 16, 64 or 128')
    if experiment_order not in (0,1,2) or stronghold_after not in range(1,6):
        raise ValueError('Invalid experimental filter order or Stronghold placement')
    if pgo_generate and pgo_use:raise ValueError('PGO generate and use are separate builds')
    started=time.perf_counter()
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    ffi=FFI()
    header=(ROOT/'native/blueprint_batch.h').read_text()
    if profile:header+='\n'+(ROOT/'native/blueprint_profile.h').read_text()
    ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')))
    source='#include "bridge.c"\n#include "'+('blueprint_profile.inc' if profile else 'blueprint_batch.inc')+'"\n'
    flags=['-O3','-std=c11','-fwrapv',f'-DNB_WORK_CHUNK={work_chunk}',
           f'-DNB_EXPERIMENT_ORDER={experiment_order}',f'-DNB_STRONGHOLD_AFTER={stronghold_after}'];includes=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')]
    if cpu_native:flags.append('-march=native')
    if lto:flags.append('-flto')
    if pgo_generate:flags.append('-fprofile-instr-generate')
    if disable_mansion_cache:flags.append('-DNB_DISABLE_MANSION_CACHE=1')
    libraries=['m'];library_dirs=[];links=[];runtime=None
    if lto:links.append('-flto')
    if pgo_generate:links.append('-fprofile-instr-generate')
    if openmp_prefix:
        prefix=Path(openmp_prefix).resolve()
        runtime=prefix/'lib'/('libomp.dylib' if platform.system()=='Darwin' else 'libomp.so')
        if not (prefix/'include/omp.h').is_file() or not runtime.is_file():raise ValueError('OpenMP prefix needs its header and runtime')
        flags+=['-Xpreprocessor','-fopenmp'] if platform.system()=='Darwin' else ['-fopenmp']
        flags+=['-DSS_OPENMP_LIBRARY="'+str(runtime)+'"']
        includes+=[str(prefix/'include')];library_dirs=[str(prefix/'lib')];libraries+=['omp']
        links+=['-Wl,-rpath,'+str(prefix/'lib')]
    inputs=[ROOT/'scripts/build_blueprint_batch.py',*ROOT.glob('native/*.c'),*ROOT.glob('native/*.h'),
            ROOT/'native/filters.inc',ROOT/'native/blueprint_batch.inc',*ROOT.glob('vendor/cubiomes-bedrock/*.h'),
            *ROOT.glob('vendor/cubiomes-bedrock/tables/*.h')]+[ROOT/f'vendor/cubiomes-bedrock/{u}.c' for u in UNITS]
    if profile:inputs.append(ROOT/'native/blueprint_profile.inc')
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    source_digest=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()
    profile_digest=None
    if pgo_use:
        pgo_use=Path(pgo_use).resolve();manifest=pgo_use.with_suffix('.json')
        if not pgo_use.is_file() or not manifest.is_file():raise ValueError('PGO use requires a profile and its source manifest')
        meta=json.loads(manifest.read_text())
        if (meta.get('source_digest')!=source_digest or meta.get('work_chunk')!=work_chunk or
            meta.get('cpu_native')!=cpu_native or meta.get('lto')!=lto or
            meta.get('experiment_order',0)!=experiment_order or meta.get('stronghold_after',2)!=stronghold_after):
            raise ValueError('Stale or incompatible PGO profile')
        profile_digest=hashlib.sha256(pgo_use.read_bytes()).hexdigest()
        if meta.get('profile_sha256')!=profile_digest:raise ValueError('PGO profile digest mismatch')
        flags.append(f'-fprofile-instr-use={pgo_use}')
        links.append(f'-fprofile-instr-use={pgo_use}')
    ffi.set_source('_blueprint_batch',source,
        sources=[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in UNITS],
        include_dirs=includes,extra_compile_args=flags,libraries=libraries,
        library_dirs=library_dirs,extra_link_args=links)
    previous=os.environ.get('ARCHFLAGS')
    try:
        if platform.system()=='Darwin':
            os.environ['ARCHFLAGS']='-arch '+platform.machine()
        extension=ffi.compile(tmpdir=str(output),verbose=False)
    finally:
        if previous is None:os.environ.pop('ARCHFLAGS',None)
        else:os.environ['ARCHFLAGS']=previous
    # Compile success is insufficient: compiler/runtime ABI mismatches can
    # leave unresolved OpenMP symbols until the extension is actually loaded.
    subprocess.run([sys.executable,'-c',
        "import importlib.util,sys; s=importlib.util.spec_from_file_location('_blueprint_batch',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)",
        extension],check=True,capture_output=True,text=True)
    configured_cc=sysconfig.get_config_var('CC') or 'clang'
    compiler_command=os.environ.get('CC') or configured_cc.split()[0]
    compiler=subprocess.run([compiler_command,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    ld_proc=subprocess.run(['ld','-v'],capture_output=True,text=True)
    linker=(ld_proc.stderr or ld_proc.stdout).strip()
    identity={'extension':extension,'extension_sha256':hashlib.sha256(Path(extension).read_bytes()).hexdigest(),
        'inputs':source_hashes,'source_digest':source_digest,'build_seconds':time.perf_counter()-started,
        'flags':flags,'openmp':bool(openmp_prefix),'runtime':str(runtime) if runtime else None,
        'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest() if runtime else None,
        'links':links,'compiler':compiler,'configured_cc':sysconfig.get_config_var('CC'),
        'configured_ldshared':sysconfig.get_config_var('LDSHARED'),'environment_flags':{k:os.environ.get(k) for k in ('CC','CFLAGS','LDFLAGS','ARCHFLAGS','MACOSX_DEPLOYMENT_TARGET')},
        'linker':linker,'python':sys.version,'arch':platform.machine(),
        'cpu_native':cpu_native,'lto':lto,'pgo_generate':pgo_generate,'pgo_profile_sha256':profile_digest,
        'production_extension_replaced':False,'profiling':profile,'mansion_cache':not disable_mansion_cache,'work_chunk':work_chunk,
        'experiment_order':experiment_order,'stronghold_after':stronghold_after,
        'scope':'private complete blueprint baseline prototype'}
    (output/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    return identity


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--openmp-prefix',type=Path)
    p.add_argument('--profile',action='store_true',help='Build separate bounded stage/biome diagnostic instrumentation')
    p.add_argument('--work-chunk',type=int,choices=(16,64,128),default=16,help='Atomic work-claim size; benchmark before tuning')
    p.add_argument('--disable-mansion-cache',action='store_true',help='Retain an uncached control for measured comparisons')
    p.add_argument('--cpu-native',action='store_true',help='Opt-in host CPU instructions')
    p.add_argument('--lto',action='store_true',help='Opt-in link time optimization')
    p.add_argument('--pgo-generate',action='store_true',help='Instrument a training build')
    p.add_argument('--pgo-use',type=Path,help='Use profdata with matching source manifest')
    p.add_argument('--experiment-order',type=int,choices=(0,1,2),default=0)
    p.add_argument('--stronghold-after',type=int,choices=(1,2,3,4,5),default=4)
    a=p.parse_args();identity=build(a.output,a.openmp_prefix,profile=a.profile,disable_mansion_cache=a.disable_mansion_cache,work_chunk=a.work_chunk,
                                    cpu_native=a.cpu_native,lto=a.lto,pgo_generate=a.pgo_generate,pgo_use=a.pgo_use,
                                    experiment_order=a.experiment_order,stronghold_after=a.stronghold_after)
    print(json.dumps({'extension':identity['extension'],'openmp':identity['openmp']}))


if __name__=='__main__':main()
