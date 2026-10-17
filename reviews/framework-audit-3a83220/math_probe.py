"""Source-level arithmetic parity and deterministic center-policy witnesses.

Run from the repository with .venv/bin/python reviews/framework-audit-3a83220/math_probe.py.
These synthetic structure inventories test geometry, not Minecraft generation likelihood.
"""
from __future__ import annotations
import ctypes
import json
from pathlib import Path
import random
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.realm.blueprint import DYNAMIC_V3_LUXURIES, dynamic_v3_score
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import (DYNAMIC_V3_CENTROID_WEIGHTS, candidate_centers,
    hub_bonus_v3, nether_core_bonus_v3, nether_bounds, overworld_bounds, weighted_radial_v3)
from seed_search.realm.bounds import contains
from seed_search.realm.native_batch import NAMES

source = (ROOT / 'native/blueprint_dynamic.inc').read_text()
def extract(name):
    start = re.search(r'static (?:inline )?(?:int64_t|int) ' + name + r'\(', source).start()
    body = source.index('{', start)
    depth, end = 1, body + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return re.sub(r'^static (?:inline )?', '', source[start:end], count=1)

code = '''#include <stdint.h>
#include <stddef.h>
static int floordiv(int a,int b) {int q=a/b; return q-(a%b<0);}
typedef struct {int n; int *xz;} NBPoints;
'''
code += '\n'.join(extract(n) for n in ('nb_clamp_i32', 'nb_dynamic_v3_core_bonus',
    'nb_dynamic_v3_optional', 'nb_dynamic_v3_biome_bonus', 'nb_dynamic_floor64',
    'nb_dynamic_snap', 'nb_dynamic_count'))
code += '''
int witness_count(int px,int x,int half) {
    int coords[2]={px,0}; NBPoints p={1,coords};
    return nb_dynamic_count(&p,x,0,half,1,NULL,0);
}
'''
probe_c = BASE / 'math_probe.c'
probe_c.write_text(code)
so = BASE / ('math_probe.dylib' if sys.platform == 'darwin' else 'math_probe.so')
subprocess.run(['cc', '-O2', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
    '-fPIC', str(probe_c), '-o', str(so)], check=True)
lib = ctypes.CDLL(str(so))
lib.nb_dynamic_snap.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_int64,ctypes.c_int,
    ctypes.c_int,ctypes.POINTER(ctypes.c_int)]
rng = random.Random(20261016)
opts = ('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')
score_errors = []
for i in range(20000):
    counts = {n:rng.randrange(0,50) for n in (*NAMES,'stronghold')}
    optional = {n:rng.randrange(0,10) for n in opts}
    mask = rng.randrange(1024)
    c_core = lib.nb_dynamic_v3_core_bonus((ctypes.c_int*13)(*[counts[n] for n in NAMES]),counts['stronghold'])
    c_opt = lib.nb_dynamic_v3_optional((ctypes.c_int*5)(*[optional[n] for n in opts]))
    c_lux = lib.nb_dynamic_v3_biome_bonus(mask)
    py_total, comp, _ = dynamic_v3_score(counts,[m[0] for k,(_,m) in enumerate(DYNAMIC_V3_LUXURIES) if mask>>k&1],optional_counts=optional)
    if (c_core,c_opt,c_lux) != (comp['core_surplus'],comp['optional_bonus'],comp['luxury_biomes']):
        score_errors.append(i)

snap_errors = []
for i in range(100000):
    lo = rng.randrange(-2000,2001)
    hi = lo+rng.randrange(0,130)
    weight = rng.randrange(1,200)
    total = rng.randrange(-2000*weight,2000*weight+1)
    step = rng.choice((8,16))
    lower,upper = -(-lo//step)*step,hi//step*step
    value = ctypes.c_int()
    found = lib.nb_dynamic_snap(lo,hi,total,weight,step,ctypes.byref(value))
    want_found = lower<=upper
    expected = max(lower,min(upper,((total+(step//2)*weight)//(step*weight))*step)) if want_found else None
    if bool(found)!=want_found or (found and value.value!=expected):
        snap_errors.append(i)

# All possible snapped v3 center coordinates, every possible macro Nether X.
nether_errors = []
nether_tests = 0
for x in range(-976,977,8):
    bounds = nether_bounds((x,0),512)
    for px in range(-634,634):
        actual = lib.witness_count(px,x,512)
        expected = bounds[0]<=px<bounds[2]
        nether_tests += 1
        if bool(actual)!=expected:
            nether_errors.append([x,px])
# Include fractional/rational center and exact +/-1 entry/exit neighbors.
for px in range(-634,634):
    for x in (8*(px-512),8*(px-512)+1,8*(px+512),8*(px+512)+1):
        bounds=nether_bounds((x,0),512)
        actual=lib.witness_count(px,x,512)
        expected=bounds[0]<=px<bounds[2]
        nether_tests+=1
        if bool(actual)!=expected:nether_errors.append([x,px])

cfg = dynamic_v3_blueprint_config()
floors = cfg['structures']['hard_floors']
inventory = {name:[(32,8*(2*i-(n-1))) for i in range(n)] for name,n in floors.items()
    if name not in ('stronghold','fortress','bastion')}
inventory.update(stronghold=[(992,0)],fortress=[(0,0)],bastion=[(-32,0),(32,0)],
    swamp_hut=[(-992,0),(1040,0)])
rows = candidate_centers(inventory,floors,{},cfg['search']['density_weights'],0,
    centroid_weights=DYNAMIC_V3_CENTROID_WEIGHTS,overworld_half=1024,nether_half=512)

def evaluate(center):
    ow,nw=overworld_bounds(center,1024),nether_bounds(center,512)
    points={name:[p for p in pts if contains(p,nw if name in ('fortress','bastion') else ow)]
        for name,pts in inventory.items()}
    counts={name:len(pts) for name,pts in points.items()}
    hub=hub_bonus_v3(points,center)
    nether_core=nether_core_bonus_v3(points,center)
    score,comp,_=dynamic_v3_score(counts,hub=hub,nether_core=nether_core)
    radial=weighted_radial_v3(points,center,overworld_half=1024)
    return {'center':list(center),'score':score,'radial':radial,
        'components':comp,'counts':counts,
        'all_hard_floors_satisfied':all(counts.get(n,0)>=v for n,v in floors.items())}

best=min((evaluate(r.center) for r in rows),key=lambda r:(-r['score'],r['radial'],sum(v*v for v in r['center']),r['center']))
alternative=evaluate((32,0))
# The finite global 16-block grid needs only 123**2 evaluations.
full_grid_best=min((evaluate((x,z)) for x in range(-976,977,16) for z in range(-976,977,16)),
    key=lambda r:(not r['all_hard_floors_satisfied'],-r['score'],r['radial'],sum(v*v for v in r['center']),r['center']))
assert alternative['all_hard_floors_satisfied'] and best['all_hard_floors_satisfied']
assert alternative['score']==best['score']+15
assert alternative['radial']<best['radial']
assert not any(17<=r.center[0]<=32 for r in rows)

max_counts={name:100 for name in (*NAMES,'stronghold',*opts)}
max_score,max_comp,_=dynamic_v3_score(max_counts,[m[0] for _,m in DYNAMIC_V3_LUXURIES],
    hub=45,nether_core=20,scenic=1,village_spread=1,treasure_bastion=1)

result={
    'score_arithmetic':{'cases':20000,'mismatches':score_errors,'scope':'Freshly extracted C core/optional/luxury helpers vs Python score components'},
    'snapping':{'cases':100000,'mismatches':snap_errors},
    'nether_half_open':{'cases':nether_tests,'mismatches':nether_errors,'scope':'Every snapped v3 center and macro Nether X plus rational entry/exit neighbors'},
    'caps':{'total':max_score,'components':max_comp,'non_core_max':max_score-max_comp['core_surplus'],
        'after_luxury_max':max_score-max_comp['core_surplus']-max_comp['luxury_biomes'],
        'after_optional_max':max_score-max_comp['core_surplus']-max_comp['luxury_biomes']-max_comp['optional_bonus']},
    'center_policy_witness':{'inventory':inventory,'representatives':len(rows),
        'best_defined_representative':best,'unrepresented_valid_center':alternative,
        'best_of_all_15129_chunk_aligned_centers':full_grid_best,
        'palette_assumption':'Hold all required biome families present at both centers, luxuries absent; scenic and treasure bonuses absent. This witness tests geometry and scoring, not generated-seed frequency.'}}
assert not (score_errors or snap_errors or nether_errors)
(BASE/'math-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='center_policy_witness'},indent=2))
print(json.dumps({'center_witness':{'representatives':len(rows),'best':best,'alternative':alternative}},indent=2))
