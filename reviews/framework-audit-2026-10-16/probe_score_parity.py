import ctypes,json,random,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.blueprint import dynamic_v3_score,DYNAMIC_V3_LUXURIES
from seed_search.realm.native_batch import NAMES
source=(ROOT/'native/blueprint_dynamic.inc').read_text()
def extract(name):
 start=source.index('static int '+name+'(');body=source.index('{',start);depth=1;end=body+1
 while depth:
  if source[end]=='{':depth+=1
  elif source[end]=='}':depth-=1
  end+=1
 return source[start:end].replace('static int '+name,'int '+name,1)
code='int nb_clamp_i32(int x,int lo,int hi) { return x<lo?lo:x>hi?hi:x; }\n'+'\n'.join(extract(n) for n in ('nb_dynamic_v3_core_bonus','nb_dynamic_v3_optional','nb_dynamic_v3_biome_bonus'))
p=BASE/'score_probe.c';p.write_text(code)
so=BASE/'score_probe.dylib';subprocess.run(['cc','-O2','-dynamiclib',str(p),'-o',str(so)],check=True)
lib=ctypes.CDLL(str(so));rng=random.Random(42);errors=[];rows=[]
opts=('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')
for i in range(10000):
 c={n:rng.randrange(0,40) for n in (*NAMES,'stronghold')};o={n:rng.randrange(0,8) for n in opts};mask=rng.randrange(1024)
 native=lib.nb_dynamic_v3_core_bonus((ctypes.c_int*13)(*[c[n] for n in NAMES]),c['stronghold'])+lib.nb_dynamic_v3_optional((ctypes.c_int*5)(*[o[n] for n in opts]))+lib.nb_dynamic_v3_biome_bonus(mask)
 score,_,_=dynamic_v3_score(c,[members[0] for k,(_,members) in enumerate(DYNAMIC_V3_LUXURIES) if mask>>k&1],optional_counts=o)
 if native!=score:errors.append({'case':i,'native':native,'python':score})
print(json.dumps({'random_cases':10000,'mismatches':errors,'scope':'extracted native score functions vs Python; arithmetic only, not geometry or feature detection'},indent=2))
