"""Independent raw-observation oracle: does not use summary predicate helpers."""
from fractions import Fraction
from math import isqrt
import random
import pytest
from seed_search.catalog.registry import STRUCTURES, BIOMES, ENVELOPE
from seed_search.catalog.models import identity, empty_observation
from seed_search.catalog.summaries import summarize
from seed_search.catalog.query import search

AXIS=(-976,-768,-512,-256,0,256,512,768,976)


@pytest.fixture(scope='module')
def corpus():
    rng=random.Random(1901); observations=[]; layouts=[]; facts=[]
    for seed in (-1, 0, 9223372036854775807):
        obs=empty_observation(identity(seed,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
        for f in STRUCTURES:
            pts={(rng.randrange(-3000,3001),rng.randrange(-3000,3001)) for _ in range(30)}
            pts.update({(-1024,0),(1024,0),(512,0),(0,0)})
            obs['structures'][f['id']]=[list(p) for p in sorted(pts)]
            obs['coverage'][f['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_viable_starts_v1'}
        if seed == -1:
            obs['biomes']=[[x,63,z,2 if (x,z)==(0,0) else 3 if (x,z)==(512,0) else 1]
                for z in range(-5120,5120,64) for x in range(-5120,5120,64)]
            obs['biome_names']={'1':'plains','2':'cherry_grove','3':'mushroom_fields'}
            for f in BIOMES:
                obs['coverage'][f['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_world_lattice_y63_stride64_v1'}
        observations.append(obs); layouts.extend(summarize(obs))
        biome_points={f['id']:[(p[0],p[2]) for p in obs['biomes']
            if obs['biome_names'].get(str(p[3])) in f['canonical_members']] for f in BIOMES}
        # Raw-coordinate facts are cached once, independently of production summaries.
        for side in (2048,4096,8192):
            for cx in AXIS:
                for cz in AXIS:
                    row={'seed':str(seed),'anchor':[cx,cz],'side':side,'features':{}}
                    for f in STRUCTURES+BIOMES:
                        points=obs['structures'].get(f['id'],[]) if f in STRUCTURES else biome_points[f['id']]
                        d2=sorted((x-cx)**2+(z-cz)**2 for x,z in points
                            if cx-side//2<=x<cx+side//2 and cz-side//2<=z<cz+side//2)
                        row['features'][f['id']]={'known':f['id'] in obs['coverage'],
                            'counts':[sum(d<=r*r for d in d2) for r in (256,512,1024)]+[len(d2)],
                            'nearest':d2[0] if d2 else None}
                    facts.append(row)
    return observations,layouts,facts


def oracle(facts,request,limit):
    rows=request['rows']; candidates=[]
    for raw in facts:
        if raw['side']!=request['border_side'] or (request['anchor_mode']=='origin' and raw['anchor']!=[0,0]): continue
        total=Fraction(0); weights=0; distance_tie=0; passes=True
        for row in rows:
            radius=row['scope'].get('radius'); scope=(256,512,1024).index(radius) if radius else 3
            selected=[raw['features'][k] for k in ([row['feature']] if row['kind']=='structure_count' else row['any_of'])]
            known=all(f['known'] for f in selected)
            nearest=min((f['nearest'] for f in selected if f['nearest'] is not None),default=None)
            if row['kind']=='structure_count':
                utility=Fraction(min(selected[0]['counts'][scope],row['at_least']),row['at_least']) if known else Fraction(0)
            else:
                utility=Fraction(int(known and nearest is not None and (radius is None or nearest<=radius*radius)))
            if row['rule']=='required' and (not known or utility<1): passes=False; break
            if row['rule']=='preferred':
                total+=row['importance']*utility; weights+=row['importance']
            distance_tie+=min(1000000,isqrt(nearest*10**12)//(radius or raw['side']//2)) if nearest is not None else 1000000
        if passes:
            score=total/weights
            candidates.append(((-score,distance_tie,int(raw['seed'])&((1<<64)-1),*raw['anchor']),raw,score))
    candidates.sort(key=lambda value:value[0]); result=[]; seeds=set()
    for _,raw,score in candidates:
        if raw['seed'] not in seeds:
            seeds.add(raw['seed']); result.append((raw['seed'],raw['anchor'],float(score*100)))
            if len(result)==limit: break
    return result


def test_220_raw_coordinate_query_cases(corpus):
    observations,layouts,facts=corpus; rng=random.Random(77)
    for case in range(220):
        rows=[]
        for index in range(rng.randrange(1,5)):
            row={'rule':'preferred' if index==0 or rng.random()<0.5 else 'required',
                 'scope':{'kind':'inside_border'} if rng.random()<0.25 else {'kind':'near_base','radius':rng.choice((256,512,1024))}}
            if row['rule']=='preferred': row['importance']=rng.choice((1,3,5))
            if rng.random()<0.25:
                row.update(kind='biome_witness',any_of=rng.sample(['biome.plains','biome.cherry_grove','biome.mushroom_fields','biome.badlands'],rng.randrange(1,4)))
            else: row.update(kind='structure_count',feature=rng.choice(STRUCTURES)['id'],at_least=rng.randrange(1,17))
            rows.append(row)
        request={'request_revision':'catalog-query-v1','edition':'bedrock','game_build_id':'research:MC_26_50',
            'catalog_snapshot_id':'oracle','world_settings_id':'default','dimension':'overworld',
            'anchor_mode':rng.choice(('origin','recommended')),'border_side':rng.choice((2048,4096,8192)),
            'evidence_policy':'predicted_observations_v1','fallback_profile':'balanced_survival','rows':rows}
        expected=oracle(facts,request,3)
        actual=search(layouts,request,snapshot_id='oracle',limit=3,observations=observations)
        assert [(r['seed'],r['anchor']) for r in actual]==[(s,a) for s,a,_ in expected],case
        assert [r['score'] for r in actual]==pytest.approx([s for _,_,s in expected]),case
