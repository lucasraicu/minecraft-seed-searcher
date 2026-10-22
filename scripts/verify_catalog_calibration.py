#!/usr/bin/env python3
"""Independent raw-coordinate oracle for the selectively found Realm controls."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.geometry import inside
from seed_search.catalog.ingestion import atomic_json,strict_json_loads
from seed_search.catalog.models import validate_observation_v2
from seed_search.catalog.registry import digest
from seed_search.realm.blueprint import PALETTE,CAVE_FAMILIES,dynamic_v3_score
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import hub_bonus_v3,nether_core_bonus_v3,retained_scenic_pair_v2,village_spread_bonus_v2


def verify(obs,result,calibration,side):
    center=result['center'];x,z=center;half=side//2;ow=[x-half,z-half,x+half,z+half]
    nx,nz=x//8,z//8;nw=[nx-512,nz-512,nx+512,nz+512]
    table=calibration['thresholds']['sizes'][str(side)];inventory=obs['realm']['inventory']
    points={name.removeprefix('structure.'):rows for name,rows in obs['structures'].items()}
    for name in ('ocean_ruin','buried_treasure','igloo_basement'):points[name]=inventory[name]['points']
    selected={name:[p for p in rows if inside(*p,nw if name in ('fortress','bastion') else ow)] for name,rows in points.items()}
    counts={name:len(rows) for name,rows in selected.items()};counts['igloo']=counts['igloo_basement']
    for name,count in result['counts'].items():
        if counts.get(name)!=count:raise ValueError('Saved count differs from raw-coordinate oracle: '+name)
    for name,floor in result['floors'].items():
        if counts[name]<floor:raise ValueError('Positive control fails frozen floor')
    normalized={name:max([max(0,entry['base_levels'][0]-1)]+[base for base,threshold in zip(entry['base_levels'],entry['thresholds']) if counts[name]>=threshold]) for name,entry in table.items()}
    normalized.update(fortress=counts['fortress'],bastion=counts['bastion'])
    names=obs['biome_names'];config=dynamic_v3_blueprint_config();ow_biomes=obs['biomes']['overworld']
    for family in config['biomes']['required_families']:
        levels=(-48,0) if family in CAVE_FAMILIES else (63,160)
        if not any(y in levels and inside(x,z,ow) and names[str(bid)] in PALETTE[family] for x,y,z,bid in ow_biomes):
            raise ValueError('Positive control lacks required height-specific family: '+family)
    nether_names={names[str(bid)] for x,y,z,bid in obs['biomes']['nether'] if y==64 and inside(x,z,nw)}
    if not set(config['biomes']['nether_required'])<=nether_names:raise ValueError('Missing required linked Nether biome')
    for dimension,box,levels,expected in [('overworld',ow,(-48,0,63,160),(side//64)**2),('nether',nw,(64,),256)]:
        for level in levels:
            sampled={(x,z) for x,y,z,bid in obs['biomes'][dimension] if y==level and x%64==0 and z%64==0 and inside(x,z,box) and not names[str(bid)].startswith('unknown')}
            if len(sampled)!=expected:raise ValueError('Score completeness lacks entire declared lattice')
    local=[x-1024,z-1024,x+1024,z+1024]
    hub=hub_bonus_v3({name:[p for p in rows if inside(*p,local)] for name,rows in points.items()},center)
    nether=nether_core_bonus_v3(selected,center)
    surface=[dict(coordinate=[x,y,z],biome=names[str(bid)]) for x,y,z,bid in ow_biomes if y==63 and x%64==0 and z%64==0]
    scenic=bool(retained_scenic_pair_v2(surface,center,overworld_half=1024)[0])
    spread=bool(village_spread_bonus_v2(points['village'],center,overworld_half=half)[0])
    variants={(x,z):v for x,z,v in inventory['bastion_variant']['points']}
    treasure=any(variants.get(tuple(p))==2 for p in selected['bastion'])
    luxury={names[str(bid)] for x,y,z,bid in ow_biomes if y==63 and inside(x,z,ow)}
    score,components,_=dynamic_v3_score(normalized,luxury,hub=hub,nether_core=nether,scenic=scenic,village_spread=spread,treasure_bastion=treasure)
    if score!=result['score']:raise ValueError(f'Score differs from shared scorer: {score}/{result["score"]}')
    nether_score=dynamic_v3_score({name:counts[name] for name in ('fortress','bastion')},nether_core=nether,treasure_bastion=treasure)[0]
    groups=dict(overworld=score-components['luxury_biomes']-nether_score,luxury_biomes=components['luxury_biomes'],nether=nether_score)
    if groups!=result['group_scores']:raise ValueError('Score groups differ')
    return dict(center=center,score=score,groups=groups,raw_count_oracle=True,complete_lattice_oracle=True,
                required_families_oracle=True,shared_score_parity=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--controls',type=Path,required=True)
    parser.add_argument('--original-cohort',type=Path,required=True);parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    state=strict_json_loads((args.controls/'progress.json').read_bytes());calibration=strict_json_loads(args.calibration.read_bytes())
    if not state.get('complete') or state['pin']['calibration_id']!=digest(calibration):raise ValueError('Unfinished or changed validation')
    old=strict_json_loads((args.original_cohort/'progress.json').read_bytes());old_seeds={r['seed'] for r in old['worlds']}
    store=ArtifactStore(args.controls/'selected-control-objects');verified=[]
    for control in state['controls']:
        obs=validate_observation_v2(store.get_json(control['artifact']))
        if digest(obs)!=control['observation_id']:raise ValueError('Changed saved control facts')
        for side,result in control['evaluation']['sizes'].items():
            if result['status']=='match':
                checked=verify(obs,result,calibration,int(side))
                verified.append(dict(seed=control['seed'],side=int(side),independent_of_fit=control['seed'] not in old_seeds,
                    observation_id=control['observation_id'],**checked))
    report=dict(revision='catalog-calibration-control-oracle-v1',calibration_id=digest(calibration),
        input_manifest_id=state['pin']['manifest_id'],processed=len(state['rows']),selected_controls=len(state['controls']),
        independent_positive_counts={str(side):sum(v['side']==side and v['independent_of_fit'] for v in verified) for side in (4096,8192)},
        verified=verified,limitation='Selectively enriched controls validate feasible predictions; no population prevalence or physical BDS certification claim')
    atomic_json(args.output,report);print(json.dumps(report),flush=True)


if __name__=='__main__':main()
