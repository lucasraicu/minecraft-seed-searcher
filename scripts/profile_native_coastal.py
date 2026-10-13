"""Labeled standalone V1 service profile; no complete baseline survivor is implied."""
import cProfile
import argparse
import hashlib
import json
import os
from pathlib import Path
import pstats
import sys
import time
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from seed_search.backend import Backend,biome_catalog
from seed_search.realm.config import blueprint_config
from seed_search.realm.bounds import square,nether_square,json_bounds,native_bounds
from seed_search.realm.raster import Raster,RasterCache
from seed_search.realm.coastal import evaluate_coastal
from seed_search.realm.terrain import run_terrain
from seed_search.realm.store import RealmStore,canonical


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'runs/native-throughput-2026-10-12/coastal');args=parser.parse_args()
    output=args.output;output.mkdir(parents=True,exist_ok=True)
    cfg=blueprint_config();cfg['terrain']['include_pending']=True;cfg['terrain']['native_threads']=18
    rows=[r for r in json.loads((ROOT/'runs/locked-stronghold-2026-10-11/holdout/centers.json').read_text()) if r['first_center']]
    selected=rows[::max(1,len(rows)//3)][:3]
    records=[]
    for i,r in enumerate(selected):
        x,z=r['center'];seed=str(r['seed']);bounds=square((x,z),1536)
        with Backend(seed) as backend:monuments=backend.structures('monument',native_bounds(bounds),True)
        candidate={'id':f'{seed}:{x}:{z}','index':i,'seed':seed,'stronghold':[x,z],'qualification':'PENDING',
            'baseline_score':None,'baseline_score_observed':0,'bounds':{'overworld':list(bounds),'final_nether':json_bounds(nether_square((x,z)))},
            'required_structures':{'monument':{'predicted_viable':monuments,'coordinates':monuments}},
            'profiling_control':{'baseline_eligibility_demonstrated':False,'scope':'unconditional retained natural-terrain center'}}
        records.append({'index':i,'seed':seed,'anchors':[candidate],'counts':{'standalone_terrain_controls':1}})
    measured=[]
    for profiled in (False,True):
        run=output/('profiled-durable' if profiled else 'unprofiled-durable')
        with RealmStore(run,{'config':cfg,'scope':'standalone terrain profile; baseline eligibility unproven'}) as store:
            store.configure_range(0,3,3);store.claim_range('control');store.complete_range(0,3,records)
            profile=cProfile.Profile();start=time.perf_counter()
            if profiled:profile.enable()
            result=run_terrain(store,cfg,variants=['v1'],limit=3)
            invocations=[result];resume_seconds=[]
            # The native refinement ladder deliberately leaves low-ranked finer
            # work deferred. Resume may do new successor work, but completed
            # units and their exact durable results must never be recomputed.
            for attempt in range(len(cfg['terrain']['resolutions'])+2):
                before=list(store.db.execute("SELECT unit_id,attempts,digest,result FROM terrain_work WHERE status='complete' ORDER BY unit_id"))
                restart=time.perf_counter();resumed=run_terrain(store,cfg,variants=['v1'],limit=3,resume=True)
                resume_seconds.append(time.perf_counter()-restart);invocations.append(resumed)
                after={row[0]:row for row in store.db.execute("SELECT unit_id,attempts,digest,result FROM terrain_work WHERE status='complete'")}
                assert all(after[row[0]]==row for row in before), 'Completed terrain evidence changed on resume'
                if resumed['work_completed']==0:break
            else:raise AssertionError('Bounded fixed-border refinement failed to drain')
            if profiled:profile.disable()
            seconds=time.perf_counter()-start
            receipt={'profiled':profiled,'wall_seconds':seconds,'control_candidates_per_second':3/seconds,
                'invocations':invocations,'resume_seconds':resume_seconds,
                'table_rows':{n:store.db.execute(f'SELECT count(*) FROM {n}').fetchone()[0] for n in ('terrain_work','observations','variants','terrain_work_attempts')}}
            measured.append(receipt)
            assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            if profiled:
                profile.dump_stats(str(output/'durable.pstats'))
                with (output/'durable-profile.txt').open('w') as stream:pstats.Stats(profile,stream=stream).sort_stats('cumtime').print_stats(70)
    ids={r['name']:r['id'] for r in biome_catalog()};fixtures=[]
    for land_fraction in (.75,.80,.85):
        size=384;cut=int(round(size*(1-land_fraction)));water=np.zeros((size,size),bool);water[:,:cut]=True
        heights=np.where(water,40.,70.);biomes=np.where(water,ids['ocean'],ids['plains'])
        raster=Raster((-768,-768,768,768),4,heights,biomes,water=water,metadata={'source':'prediction','fixture':True})
        start=time.perf_counter();decision=evaluate_coastal(raster,stronghold=(0,0),bounds=raster.bounds,thresholds=cfg['terrain']['v1'],monuments=[(-650,0)])
        fixtures.append({'requested_land_fraction':land_fraction,'seconds':time.perf_counter()-start,'decision':decision,
            'full_raster_sha256':hashlib.sha256(heights.tobytes()+biomes.tobytes()+water.tobytes()).hexdigest()})
    receipt={'scope':'Unconditional labeled natural controls and synthetic coastal/borderline fixtures; no complete baseline survivors or actual-game certification',
        'native_threads':18,'durable_trials':measured,'fixtures':fixtures,'terrain_native_adoption':'No terrain rewrite; profile determines whether new native work is justified',
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'src/seed_search/realm/coastal.py',ROOT/'src/seed_search/realm/raster.py',ROOT/'src/seed_search/realm/terrain.py']}}
    (output/'profile.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(measured,indent=2))

if __name__=='__main__':main()
