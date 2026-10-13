"""Bounded geometry-only profile on three retained natural 4-block rasters."""
import argparse
import importlib.util
import copy
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from seed_search.realm.config import locked_blueprint_config,river_blueprint_config
from seed_search.realm.coastal import evaluate_coastal
from seed_search.realm.raster import Raster


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--python-oracle',type=Path)
    args=p.parse_args()
    if args.output.exists():p.error('Fresh output directory required')
    args.output.mkdir(parents=True);original=json.loads((args.source/'results.json').read_text())
    controls=[o for o in original['observations'] if o['arm']=='existing_six_levels' and o['trial']==0]
    if len(controls)!=3:raise ValueError('Exactly three retained controls required')
    rasters=[]
    for i,c in enumerate(controls):
        _,x,z=c['candidate_id'].rsplit(':',2);x,z=int(x),int(z)
        f=args.source/f'existing_six_levels-0-{i}.npz'
        with np.load(f) as a:rasters.append(Raster((x-1024,z-1024,x+1024,z+1024),4,a['height'],biomes=a['biomes'],known=a['known'],metadata={'source':'prediction'}))
    policies={'locked':locked_blueprint_config(),'river':river_blueprint_config()};observations=[];expected={}
    evaluators={arm:evaluate_coastal for arm in policies}
    if args.python_oracle:
        spec=importlib.util.spec_from_file_location('seed_search.realm.river_python_oracle',args.python_oracle)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        policies['python_river']=river_blueprint_config();evaluators['python_river']=module.evaluate_coastal
    for trial in range(3):
        for arm in (list(policies)[trial%len(policies):]+list(policies)[:trial%len(policies)]):
            for raster,c in zip(rasters,controls):
                before=time.perf_counter();r=evaluators[arm](raster,stronghold=(raster.bounds[0]+1024,raster.bounds[1]+1024),thresholds=policies[arm]['terrain']['v1'],require_monument=False)
                if arm!='locked':
                    semantic=copy.deepcopy(r);semantic['metrics'].pop('stage_seconds')
                    cid=c['candidate_id']
                    if cid in expected:assert semantic==expected[cid],(arm,cid,'complete coastal decision parity')
                    else:expected[cid]=semantic
                observations.append({'trial':trial,'arm':arm,'candidate_id':c['candidate_id'],'seconds':time.perf_counter()-before,'result':r})
    result={'scope':'Geometry-only; three natural near-miss rasters, three counterbalanced repetitions. No density sampling/SQL/BDS included.',
        'observations':observations,'full_river_semantic_differences':0,
        'python_oracle_sha256':hashlib.sha256(args.python_oracle.read_bytes()).hexdigest() if args.python_oracle else None,'median_cohort_seconds':{arm:statistics.median(sum(o['seconds'] for o in observations if o['arm']==arm and o['trial']==trial) for trial in range(3)) for arm in policies},
        'input_rasters_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in args.source.glob('existing_six_levels-0-*.npz')},
        'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),ROOT/'src/seed_search/realm/coastal.py']}}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['median_cohort_seconds']))


if __name__=='__main__':main()
