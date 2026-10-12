"""Build independent, bounded, full64 distinct-biome count kernels."""
from pathlib import Path
import hashlib,json,os,platform
from cffi import FFI
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/count-bits-2026-10-11/native-biomes'
OUT.mkdir(parents=True,exist_ok=True)
ffi=FFI();header=(ROOT/'native/bridge.h').read_text()
ffi.cdef('\n'.join(s for s in header.splitlines() if not s.startswith('#'))+'''
int bd_count(SeedContext *,int,const int *,int,const int *,int,int *);
int bd_combo(SeedContext *,int,const int *,int,const int *,const int *,int,int *);
''')
source='#include "bridge.c"\n'+(ROOT/'native/biome_diversity_pilot.inc').read_text()
units=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
ffi.set_source('_biome_diversity_pilot',source,sources=[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in units],
 include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],extra_compile_args=['-O3','-std=c11','-fwrapv'],libraries=['m'])
os.environ['ARCHFLAGS']='-arch '+platform.machine()
path=ffi.compile(tmpdir=str(OUT),verbose=False)
identity={'extension':path,'extension_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
          'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
          'definition':'Distinct active biome IDs within one family; full64 seed; stop after N different allowed IDs; insufficient catalog capacity can reject before sampling.',
          'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'native/bridge.c',ROOT/'native/bridge.h',ROOT/'native/filters.inc',ROOT/'native/biome_diversity_pilot.inc']+[ROOT/f'vendor/cubiomes-bedrock/{u}.c' for u in units]}}
(OUT/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps({'built':path,'sha256':identity['extension_sha256']}))
