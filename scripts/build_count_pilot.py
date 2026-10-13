"""Build isolated count-N kernels with the same pinned generator sources.

Use --output to verify a fresh build without replacing frozen pilot evidence.
Importing this module only exposes source-generation/build helpers.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re

from cffi import FFI

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT=ROOT/'runs/count-bits-2026-10-11/native'
UNITS=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']


def mineshaft_source(filters):
    """Derive a private cap-limited query without depending on first's meaning.

    Production first=0 means complete inventory. The pilot instead retains at
    most cap raw/qualified witnesses. Returning immediately after each emit
    prevents the next successful start from overflowing that retained prefix.
    Assert both compiler branches were transformed; fail rather than silently
    compile a diagnostic with changed semantics after future source edits.
    """
    start=filters.index('static int ss_mineshaft_query(')
    end=filters.index('\nint ss_mineshaft_first(',start)
    body=filters[start:end].replace('ss_mineshaft_query','pc_mineshaft_query')
    body,count=re.subn(r'n\s*=\s*emit\([^;]+;',lambda match:match.group(0)+'if(n>=cap)return n;',body)
    if count!=2:
        raise ValueError(f'Mineshaft extraction expected two emit sites, found {count}')
    return body


def build_source(root=ROOT):
    mineshaft=mineshaft_source((root/'native/filters.inc').read_text())
    qualified=mineshaft.replace('pc_mineshaft_query','pc_mineshaft_qual_query')
    signature='int cap,int first)'
    if qualified.count(signature)!=1:raise ValueError('Mineshaft qualifier signature changed')
    qualified=qualified.replace(signature,'int cap,int first,const int *allow,int y,int *stats)')
    replacements={
        'n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);':
            'if(allow) {stats[2]++;int id=ss_biome(ctx,0,x*16+8,y,zz*16+8);if(id<0 || id>=256 || !allow[id])continue;}\n                n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);',
        'n=emit(p,xz,n,cap);':
            'if(allow) {stats[2]++;int id=ss_biome(ctx,0,p.x,y,p.z);if(id<0 || id>=256 || !allow[id])continue;}\n            n=emit(p,xz,n,cap);',
    }
    for old,new in replacements.items():
        if qualified.count(old)!=1:raise ValueError('Mineshaft qualifier emit site changed')
        qualified=qualified.replace(old,new)
    return '#include "bridge.c"\n'+mineshaft+'\n'+qualified+'\n'+(root/'native/count_pilot.inc').read_text()


def build(output=DEFAULT_OUTPUT):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    ffi=FFI();header=(ROOT/'native/bridge.h').read_text()
    ffi.cdef('\n'.join(s for s in header.splitlines() if not s.startswith('#'))+'''
int pc_bits(int type);
void pc_cache_reset(int enabled);
int pc_count(SeedContext *,int,const int *,int,int,int,const int *,int,int *);
int pc_combo(SeedContext *,const int *,const int *,const int *,int,int,int,const int *,int *);
int pc_biome_count(SeedContext *,int,const int *,int,const int *,int,int *);
''')
    source=build_source()
    ffi.set_source('_count_pilot',source,sources=[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in UNITS],
        include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],
        extra_compile_args=['-O3','-std=c11','-fwrapv'],libraries=['m'])
    previous=os.environ.get('ARCHFLAGS')
    try:
        os.environ['ARCHFLAGS']='-arch '+platform.machine()
        path=ffi.compile(tmpdir=str(output),verbose=False)
    finally:
        if previous is None:os.environ.pop('ARCHFLAGS',None)
        else:os.environ['ARCHFLAGS']=previous
    inputs=[ROOT/'scripts/build_count_pilot.py',ROOT/'native/bridge.c',ROOT/'native/bridge.h',
            ROOT/'native/filters.inc',ROOT/'native/count_pilot.inc']+[ROOT/f'vendor/cubiomes-bedrock/{u}.c' for u in UNITS]
    identity={'extension':path,'extension_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        'flags':['-O3','-std=c11','-fwrapv'],'production_extension_replaced':False}
    (output/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    return identity


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args(argv)
    identity=build(args.output)
    print(json.dumps({'built':identity['extension'],'sha256':identity['extension_sha256']}))


if __name__=='__main__':main()
