"""Build isolated count-N kernels with the same pinned generator sources."""
from pathlib import Path
import hashlib,json,os,platform
from cffi import FFI
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/count-bits-2026-10-11/native'
OUT.mkdir(parents=True,exist_ok=True)
ffi=FFI()
header=(ROOT/'native/bridge.h').read_text()
ffi.cdef('\n'.join(s for s in header.splitlines() if not s.startswith('#'))+'''
int pc_bits(int type);
void pc_cache_reset(int enabled);
int pc_count(SeedContext *,int,const int *,int,int,int,const int *,int,int *);
int pc_combo(SeedContext *,const int *,const int *,const int *,int,int,int,const int *,int *);
int pc_biome_count(SeedContext *,int,const int *,int,const int *,int,int *);
''')
filters=(ROOT/'native/filters.inc').read_text()
start=filters.index('static int ss_mineshaft_query(')
end=filters.index('\nint ss_mineshaft_first(',start)
mineshaft=filters[start:end].replace('ss_mineshaft_query','pc_mineshaft_query').replace('n<0 || first','n<0 || first || n>=cap')
qualified=mineshaft.replace('pc_mineshaft_query','pc_mineshaft_qual_query').replace('int cap,int first)', 'int cap,int first,const int *allow,int y,int *stats)')
qualified=qualified.replace('n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);', 'if(allow) {stats[2]++;int id=ss_biome(ctx,0,x*16+8,y,zz*16+8);if(id<0 || id>=256 || !allow[id])continue;}\n                n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);')
qualified=qualified.replace('n=emit(p,xz,n,cap);', 'if(allow) {stats[2]++;int id=ss_biome(ctx,0,p.x,y,p.z);if(id<0 || id>=256 || !allow[id])continue;}\n            n=emit(p,xz,n,cap);')
source='#include "bridge.c"\n'+mineshaft+'\n'+qualified+'\n'+(ROOT/'native/count_pilot.inc').read_text()
units=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
ffi.set_source('_count_pilot',source,sources=[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in units],
 include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],
 extra_compile_args=['-O3','-std=c11','-fwrapv'],libraries=['m'])
os.environ['ARCHFLAGS']='-arch '+platform.machine()
path=ffi.compile(tmpdir=str(OUT),verbose=False)
identity={'extension':path,'extension_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
 'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
 'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
  [ROOT/'native/bridge.c',ROOT/'native/bridge.h',ROOT/'native/filters.inc',ROOT/'native/count_pilot.inc']+[ROOT/f'vendor/cubiomes-bedrock/{u}.c' for u in units]},
 'flags':['-O3','-std=c11','-fwrapv'],'production_extension_replaced':False}
(OUT/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps({'built':path,'sha256':identity['extension_sha256']}))
