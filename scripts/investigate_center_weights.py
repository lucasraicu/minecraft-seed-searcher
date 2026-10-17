"""Reproducible weight sensitivity study; never changes production policy.

Compares 27 bounded village/trial/stronghold weight settings using the actual
centroid solver and fixed v3 points. Natural evidence uses an explicitly empty
Overworld palette; synthetic cases assume their palette is valid. Neither is a
player calibration or an actual-generation verification.
"""
import argparse
import itertools
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seed_search.backend import Backend
from seed_search.realm.baseline import structure_observation
from seed_search.realm.blueprint import count_observation, dynamic_v3_score
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import (OVERWORLD_NAMES, NETHER_NAMES, OPTIONAL_NAMES,
    candidate_centers, grid_candidate_centers, DYNAMIC_V3_CENTROID_WEIGHTS,
    overworld_bounds, nether_bounds, hub_bonus_v3, nether_core_bonus_v3,
    village_spread_bonus_v2, treasure_bastion_bonus_v2, PaletteIndex)
from seed_search.realm.sampling import BiomeSampler
from seed_search.realm.bounds import contains


def synthetic_inventory(cfg):
    floors=cfg['structures']['hard_floors']
    return {name:[(0,8*(2*i-(n-1))) for i in range(n)] for name,n in floors.items()}


def synthetic_cases(cfg):
    cases={}
    audit=synthetic_inventory(cfg)
    audit={name:[(32,z) for x,z in points] for name,points in audit.items()}
    audit.update(stronghold=[(992,0)],fortress=[(0,0)],bastion=[(-32,0),(32,0)],
                 swamp_hut=[(-992,0),(1040,0)])
    cases['optional_capture_witness']=audit
    saturated=synthetic_inventory(cfg)
    saturated['village']=[(-500,z) for x,z in saturated['village']]
    saturated['trial_chamber']=[(800,8*(2*i-25)) for i in range(26)]
    saturated['stronghold']=[(-800,0)]
    cases['saturated_trial_sprawl']=saturated
    outlier=synthetic_inventory(cfg)
    for name in ('village','trial_chamber'):
        outlier[name]=[(-300,z) for x,z in outlier[name]]
    outlier['stronghold']=[(950,0)]
    cases['stronghold_outlier']=outlier
    return cases


def natural_inventory(seed,cfg,backend):
    inventory={}
    for name in (*OVERWORLD_NAMES,*NETHER_NAMES,*OPTIONAL_NAMES):
        bounds=tuple(cfg['discovery']['nether_bounds' if name in NETHER_NAMES else 'overworld_bounds'])
        ob=(count_observation(backend,name,bounds,1,capped=False) if name=='mansion'
            else structure_observation(backend,name,bounds))
        points=[tuple(p) for p in ob['predicted_viable']]
        if name=='igloo':points=[p for p in points if backend.igloo_basement(*p)]
        inventory[name]=points
    return inventory


def analyze(name,inventory,cfg,palette=None,get_variant=None):
    base=dict(DYNAMIC_V3_CENTROID_WEIGHTS)
    score_cache={}
    def evidence(center):
        if center in score_cache:return score_cache[center]
        ow,nw=overworld_bounds(center,1024),nether_bounds(center,512)
        captured={kind:[p for p in points if contains(p,nw if kind in NETHER_NAMES else ow)]
                  for kind,points in inventory.items()}
        counts={kind:len(points) for kind,points in captured.items()}
        if palette is not None:
            if not palette.valid(center):score_cache[center]=None;return None
            luxury=palette.luxuries(center)
            scenic=palette.scenic_pair(center)[0]
        else:luxury=[];scenic=0
        spread=village_spread_bonus_v2(captured.get('village',[]),center,1024)[0]
        treasure=(treasure_bastion_bonus_v2(captured.get('bastion',[]),center,get_variant,512)[0]
                  if get_variant is not None else 0)
        score,components,_=dynamic_v3_score(counts,luxury,hub=hub_bonus_v3(captured,center),
            scenic=scenic,village_spread=spread,treasure_bastion=treasure,
            nether_core=nether_core_bonus_v3(captured,center))
        result={'score':score,'components':components,'counts':counts,'captured':captured}
        score_cache[center]=result
        return result

    def measurements(row,weights):
        e=evidence(row.center)
        if e is None:return None
        destinations=[(p,weights.get(kind,0)) for kind,points in e['captured'].items()
                      if kind not in NETHER_NAMES for p in points if weights.get(kind,0)>0]
        distance=lambda p:math.hypot(p[0]-row.center[0],p[1]-row.center[1])
        mass=sum(w for p,w in destinations)
        radial=sum(w*distance(p) for p,w in destinations)/mass if mass else 0.
        nearest={kind:min((distance(p) for p in e['captured'].get(kind,[])),default=None)
                 for kind in ('village','stronghold','trial_chamber')}
        # A common yardstick, independent of the experimental scoring weights.
        common_mass=sum(base.get(kind,0)*len(points) for kind,points in e['captured'].items() if kind not in NETHER_NAMES)
        common_radial=sum(base.get(kind,0)*distance(p) for kind,points in e['captured'].items()
                          if kind not in NETHER_NAMES for p in points)/common_mass if common_mass else 0.
        return {'center':list(row.center),'score':e['score'],'weighted_radial':radial,
                'current_weight_radial':common_radial,'nearest':nearest,
                'origin_distance_squared':sum(v*v for v in row.center)}

    def rank(row):
        return (-row['score'],math.floor(row['weighted_radial']*1e6+.5),
                row['origin_distance_squared'],*row['center'])

    variants=[]
    schemes=[('current',base),('previous',dict(base,village=3,trial_chamber=2,stronghold=1))]
    schemes += [(f'v{v}-t{t}-s{s}',dict(base,village=v,trial_chamber=t,stronghold=s))
                for v,t,s in itertools.product((1,2,3),(0,1,2),(1,2,3))]
    for label,weights in schemes:
        start=time.perf_counter()
        candidates=candidate_centers(inventory,cfg['structures']['hard_floors'],{},
                                    cfg['search']['density_weights'],0,weights,1024,512)
        rows=[item for row in candidates if (item:=measurements(row,weights)) is not None]
        best=min(rows,key=rank) if rows else None
        variants.append({'label':label,'weights':weights,'best':best,
                         'representatives':len(candidates),'seconds':time.perf_counter()-start})
    grid=grid_candidate_centers(inventory,cfg['structures']['hard_floors'],{},cfg['search']['density_weights'])
    rows=[item for row in grid if (item:=measurements(row,base)) is not None]
    best_grid=min(rows,key=rank) if rows else None
    return {'name':name,'evidence_kind':'natural custom empty OW palette predictor' if palette else 'synthetic; assumed valid palette, no luxuries/scenic/treasure',
            'inventory':inventory,'variants':variants,'exhaustive_16_current_weights':best_grid,
            'grid_eligible_count':len(rows)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seed',type=int,default=-3336796033057908633)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh output file')
    cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[]
    results=[]
    for name,inventory in synthetic_cases(cfg).items():
        results.append(analyze(name,inventory,cfg))
        print(name,results[-1]['variants'][0]['best'],flush=True)
    with Backend(args.seed) as backend:
        inventory=natural_inventory(args.seed,cfg,backend)
        palette=PaletteIndex(BiomeSampler(backend),cfg['biomes'],v2=True,overworld_half=1024,nether_half=512)
        variants={p:backend.bastion_variant(*p) for p in inventory['bastion']}
        results.append(analyze(f'natural_{args.seed}',inventory,cfg,palette,lambda x,z:variants[(x,z)]))
        print(results[-1]['name'],results[-1]['variants'][0]['best'],flush=True)
    result={'scope':'Sensitivity experiment, not a representative corpus, preference calibration, or BDS verification',
            'config':cfg,'settings_per_case':27,'controls_per_case':2,'cases':results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
