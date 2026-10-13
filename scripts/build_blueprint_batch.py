"""Build the private complete-baseline prototype without replacing production."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from cffi import FFI

ROOT=Path(__file__).resolve().parents[1]
UNITS=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']


def build(output,openmp_prefix=None,*,profile=False,disable_mansion_cache=False,work_chunk=16):
    if type(work_chunk) is not int or work_chunk not in (16,64,128):
        raise ValueError('Work chunk must be 16, 64 or 128')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    ffi=FFI()
    header=(ROOT/'native/blueprint_batch.h').read_text()
    if profile:header+='\n'+(ROOT/'native/blueprint_profile.h').read_text()
    ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')))
    source='#include "bridge.c"\n#include "'+('blueprint_profile.inc' if profile else 'blueprint_batch.inc')+'"\n'
    flags=['-O3','-std=c11','-fwrapv',f'-DNB_WORK_CHUNK={work_chunk}'];includes=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')]
    if disable_mansion_cache:flags.append('-DNB_DISABLE_MANSION_CACHE=1')
    libraries=['m'];library_dirs=[];links=[];runtime=None
    if openmp_prefix:
        prefix=Path(openmp_prefix).resolve()
        runtime=prefix/'lib'/('libomp.dylib' if platform.system()=='Darwin' else 'libomp.so')
        if not (prefix/'include/omp.h').is_file() or not runtime.is_file():raise ValueError('OpenMP prefix needs its header and runtime')
        flags+=['-Xpreprocessor','-fopenmp'] if platform.system()=='Darwin' else ['-fopenmp']
        flags+=['-DSS_OPENMP_LIBRARY="'+str(runtime)+'"']
        includes+=[str(prefix/'include')];library_dirs=[str(prefix/'lib')];libraries+=['omp']
        links=['-Wl,-rpath,'+str(prefix/'lib')]
    ffi.set_source('_blueprint_batch',source,
        sources=[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in UNITS],
        include_dirs=includes,extra_compile_args=flags,libraries=libraries,
        library_dirs=library_dirs,extra_link_args=links)
    previous=os.environ.get('ARCHFLAGS')
    try:
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
    inputs=[ROOT/'scripts/build_blueprint_batch.py',*ROOT.glob('native/*.c'),*ROOT.glob('native/*.h'),
            ROOT/'native/filters.inc',ROOT/'native/blueprint_batch.inc',*ROOT.glob('vendor/cubiomes-bedrock/*.h'),
            *ROOT.glob('vendor/cubiomes-bedrock/tables/*.h')]+[ROOT/f'vendor/cubiomes-bedrock/{u}.c' for u in UNITS]
    if profile:inputs.append(ROOT/'native/blueprint_profile.inc')
    identity={'extension':extension,'extension_sha256':hashlib.sha256(Path(extension).read_bytes()).hexdigest(),
        'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        'flags':flags,'openmp':bool(openmp_prefix),'runtime':str(runtime) if runtime else None,
        'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest() if runtime else None,
        'production_extension_replaced':False,'profiling':profile,'mansion_cache':not disable_mansion_cache,'work_chunk':work_chunk,'scope':'private complete blueprint baseline prototype'}
    (output/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    return identity


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--openmp-prefix',type=Path)
    p.add_argument('--profile',action='store_true',help='Build separate bounded stage/biome diagnostic instrumentation')
    p.add_argument('--work-chunk',type=int,choices=(16,64,128),default=16,help='Atomic work-claim size; benchmark before tuning')
    p.add_argument('--disable-mansion-cache',action='store_true',help='Retain an uncached control for measured comparisons')
    a=p.parse_args();identity=build(a.output,a.openmp_prefix,profile=a.profile,disable_mansion_cache=a.disable_mansion_cache,work_chunk=a.work_chunk)
    print(json.dumps({'extension':identity['extension'],'openmp':identity['openmp']}))


if __name__=='__main__':main()
