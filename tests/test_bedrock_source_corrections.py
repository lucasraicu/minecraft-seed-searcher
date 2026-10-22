"""Source-derived Nether selector and structure gates against frozen game evidence."""
import ctypes
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

import pytest
from tests.test_generalization_evidence import bundle

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'fixtures/bedrock-26.52/generalization'
WRAPPER=r'''
#include "generator.h"
#include "finders.h"
#include "util.h"
#include <stdlib.h>
#include <limits.h>
int probe_version(int i){int v[]={MC_1_18,MC_1_20,MC_1_21_60,MC_26_50};return v[i];}
int probe_type(int i){int v[]={Fortress,Bastion,Ancient_City};return v[i];}
int probe_biome(uint64_t seed,int version,int dim,int scale,int x,int y,int z){
 Generator*g=calloc(1,sizeof(*g));setupGenerator(g,version,0);applySeed(g,dim,seed);
 int id=getBiomeAt(g,scale,x,y,z);free(g);return id;
}
const char*probe_name(int id){return biome2str(MC_26_50,id);}
int probe_viable(uint64_t seed,int version,int type,int x,int z){
 Generator*g=calloc(1,sizeof(*g));setupGenerator(g,version,0);
 applySeed(g,type==Ancient_City?DIM_OVERWORLD:DIM_NETHER,seed);
 int ok=isViableStructurePos(type,g,x,z,0);free(g);return ok;
}
int probe_start(uint64_t seed,int type,int rx,int rz,int *out){
 Pos p;int ok=getStructurePos(type,MC_26_50,seed,rx,rz,&p);out[0]=p.x;out[1]=p.z;return ok;
}
int probe_grid(uint64_t seed,int x,int y,int z,int sx,int sy,int sz,int*out){
 Generator*g=calloc(1,sizeof(*g));setupGenerator(g,MC_26_50,0);applySeed(g,DIM_NETHER,seed);
 Range r={1,x,z,sx,sz,y,sy};int ok=genBiomes(g,out,r);free(g);return ok;
}
#ifndef LEGACY_BUILD
int probe_node(uint64_t seed,int x,int z,int*out){return getBedrockNetherQuart(seed,x,z,out);}
#endif
'''

@pytest.fixture(scope='module',params=['-ffp-contract=off','-ffp-contract=fast'])
def source_native(tmp_path_factory,request):
 out=tmp_path_factory.mktemp('source-corrections');wrapper=out/'wrapper.c';wrapper.write_text(WRAPPER)
 vendor=ROOT/'vendor/cubiomes-bedrock';target=out/'source-corrections.dylib'
 units='noise biomes layers biomenoise cave generator finders util quadbase mt'.split()
 result=subprocess.run(['cc','-shared','-fPIC','-O3','-std=c11','-fwrapv',request.param,'-I',str(vendor),str(wrapper),*[str(vendor/(u+'.c'))for u in units],'-lm','-o',str(target)],capture_output=True,text=True,timeout=90)
 assert result.returncode==0,result.stderr
 lib=ctypes.CDLL(str(target));lib.probe_biome.argtypes=[ctypes.c_uint64,*([ctypes.c_int]*6)]
 lib.probe_viable.argtypes=[ctypes.c_uint64,*([ctypes.c_int]*4)]
 lib.probe_start.argtypes=[ctypes.c_uint64,*([ctypes.c_int]*3),ctypes.POINTER(ctypes.c_int)]
 lib.probe_grid.argtypes=[ctypes.c_uint64,*([ctypes.c_int]*6),ctypes.POINTER(ctypes.c_int)]
 lib.probe_node.argtypes=[ctypes.c_uint64,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int)]
 lib.probe_name.argtypes=[ctypes.c_int];lib.probe_name.restype=ctypes.c_char_p
 return lib

@pytest.fixture(scope='module')
def source_bundle():
 descriptor=json.loads((FIXTURE/'source-corrections-v1.manifest.json').read_bytes())
 raw=(FIXTURE/descriptor['archive']).read_bytes()
 assert len(raw)==descriptor['archive_bytes']<4<<20
 assert hashlib.sha256(raw).hexdigest()==descriptor['archive_sha256']
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as archive:
  files={}
  for member in archive:
   assert member.isfile() and not Path(member.name).is_absolute() and '..'not in Path(member.name).parts
   data=archive.extractfile(member).read();assert len(data)==member.size<4<<20
   assert member.name not in files;files[member.name]=data
 assert set(files)==set(descriptor['files'])
 for name,data in files.items():assert hashlib.sha256(data).hexdigest()==descriptor['files'][name]['sha256']
 return files

def test_fresh_default_game_points_and_restored_structure_references(source_native,source_bundle,bundle):
 aliases=json.loads(bundle[1]["cohort/manifest.json"])["aliases"]
 lib=source_native;f=json.loads(source_bundle['b-heldout-frozen.json']);ledger=json.loads(source_bundle['ledger.json'])
 assert len(ledger)==8 and all(r['state']=='complete'for r in ledger)
 manifest_sha=hashlib.sha256(source_bundle['b-heldout-frozen.json']).hexdigest()
 nether=restored=retained=0
 for i,c in enumerate(f['cases']):
  raw=source_bundle[f'pass-{i:02}/report.json'];r=json.loads(raw)
  assert hashlib.sha256(raw).hexdigest()==ledger[i]['report_sha256']
  assert r['controls']['manifest_sha256']==manifest_sha
  assert r['world_identity']['seed']==c['seed'] and r['world_identity']['dimension']==c['dimension']
  assert r['world_identity']['api']=='2.10.0' and r['world_identity']['players']==0
  assert all(r[k]for k in ('save_confirmed','clean_shutdown','owned_container_removed'))
  if c['dimension']=='nether':
   for p,o in zip(c['prediction']['selector'],r['target_result']['rows'],strict=True):
    assert p['point']==[o['x'],o['y'],o['z']]
    assert lib.probe_biome(int(c['seed'])%(1<<64),lib.probe_version(3),-1,1,*p['point'])==p['new_id']
    observed=o['id'].removeprefix('minecraft:')
    assert p['new']==aliases.get(observed,observed);nether+=1
  for q,observed in zip(c['structures'],r['queries'],strict=True):
   if q.get('new')!=1:continue
   typ=lib.probe_type(1 if c['dimension']=='nether' else 2)
   assert lib.probe_viable(int(c['seed'])%(1<<64),lib.probe_version(3),typ,*q['point'])>0
   # Exact references only; differing locates never become negative controls.
   exact=f'at block {q["point"][0]}, (y?), {q["point"][1]} (0 blocks away)'
   assert any(exact in line for line in observed['output'])
   restored+=q['old']==0;retained+=q['old']==1
 assert (nether,restored,retained)==(100,5,8)

def test_original_and_recheck_nether_points_match_game(source_native,bundle):
 _,files=bundle;manifest=json.loads(files['cohort/manifest.json']);aliases=manifest['aliases'];total=0
 def check(seed,rows):
  n=0
  for row in rows:
   if 'error'in row:continue
   bid=source_native.probe_biome(int(seed)%(1<<64),source_native.probe_version(3),-1,1,row['x'],row['y'],row['z'])
   name=source_native.probe_name(bid).decode();name=aliases.get(name,name)
   observed=row['id'].removeprefix('minecraft:')
   assert name==aliases.get(observed,observed);n+=1
  return n
 for world in manifest['worlds']:
  r=json.loads(files[f'cohort/world-{world["index"]:02}/report.json'])
  total+=check(world['seed'],[p for b in r['biome_batches']if b['dimension']=='nether'for p in b['rows']])
 assert total==216
 # The portable existing archive also keeps default/Beta copied-world rechecks.
 rechecks=0
 for name,raw in files.items():
  if name.endswith('/report.json') and name.startswith(('followup/','biome-recheck/')):
   r=json.loads(raw);identity=r.get('world_identity',{})
   if identity.get('dimension')=='nether' and r.get('status')=='observed':
    rechecks+=check(identity['seed'],r['target_result']['rows'])
 assert rechecks>=37

def test_legacy_dimensions_scales_structure_gates_and_raw_selection(source_native,source_bundle):
 data=json.loads(source_bundle['legacy-controls.json']);lib=source_native
 for r in data['biomes']:
  assert lib.probe_biome(int(r['seed'])%(1<<64),lib.probe_version(r['version']),r['dimension'],r['scale'],*r['point'])==r['id'],r
 for r in data['structures']:
  assert lib.probe_viable(int(r['seed'])%(1<<64),lib.probe_version(r['version']),lib.probe_type(r['type']),*r['point'])==r['viable'],r
 for r in data['starts']:
  out=(ctypes.c_int*2)();found=lib.probe_start(int(r['seed'])%(1<<64),lib.probe_type(r['type']),*r['region'],out)
  assert bool(found)==r['found'] and list(out)==r['point']
  if found and r['type']==0:assert lib.probe_viable(int(r['seed'])%(1<<64),lib.probe_version(3),lib.probe_type(0),*r['point'])==1
 assert len(data['biomes'])>1000 and len(data['starts'])==800

def test_nether_scalar_grid_height_boundaries_and_integer_safety(source_native):
 lib=source_native;seed=8467329634092353248;out=(ctypes.c_int*(17*3*17))()
 assert lib.probe_grid(seed,-9,16,-9,17,3,17,out)==0
 for iy in range(3):
  for iz in range(17):
   for ix in range(17):
    assert out[(iy*17+iz)*17+ix]==lib.probe_biome(seed,lib.probe_version(3),-1,1,-9+ix,16+iy,-9+iz)
 node=(ctypes.c_int*2)()
 assert lib.probe_node(seed,0,0,None)==-1
 for x in (-(1<<31),-(1<<31)+1,(1<<31)-1):assert lib.probe_node(seed,x,0,node)==-1
 for x in (-30000000,-3,-2,-1,0,1,2,3,30000000):
  assert lib.probe_node(seed,x,-x,node)==0
  assert all(abs(v)<=7500001 for v in node)


def test_all_frozen_raw_candidate_gates_include_basalt_and_non_deep_dark_rejections(source_native,source_bundle):
    """Test source-gate arithmetic; a rejection is not a proven physical absence."""
    lib=source_native;f=json.loads(source_bundle['b-heldout-frozen.json']);negative=0
    for c in f['cases']:
        typ=lib.probe_type(1 if c['dimension']=='nether' else 2)
        for r in c['prediction']['candidates']:
            actual=lib.probe_viable(int(c['seed'])%(1<<64),lib.probe_version(3),typ,*r['point'])
            assert bool(actual)==bool(r['new']),r
            negative+=not r['new']
    assert negative>100
