"""Finite validation workloads; no production sweep or synthetic website evidence.

Modes: experiment (two keys x two 256-input arms), parity (20 chosen controls,
three alternating-order quart comparisons), workers (1/8/12 resume), recovery.
All outputs preserve config/runtime identity and distinguish predictions/reviews.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
import argparse
import copy
import hashlib
import json
import statistics
import time
from pathlib import Path
import numpy as np
import yaml
from seed_search.config import load_config
from seed_search.search import run_search,analyze_seed
from seed_search.seeds import seed_from_index
from seed_search.storage import Store,backend_identity
from seed_search.scoring import candidate_eligible

OUT=Path('runs/implementation-2026-10-08')
IGNORE={'worker_pid','worker_peak_rss_mb','stage_seconds','total_seconds','worker_cpu_seconds','native_work'}

def write(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def config(name,cfg):
    path=OUT/'config'/f'{name}.yaml';path.parent.mkdir(parents=True,exist_ok=True)
    text=yaml.safe_dump(cfg,sort_keys=False);path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()

def read(path):
    store=Store(path,resume=True)
    try:return store.identity,store.results()
    finally:store.close()

def completed(path,count,cfg,h):
    """Reuse finished evidence without adding empty resume invocations."""
    path=Path(path)
    if not (path/'checkpoint.sqlite').exists():return False
    identity,rows=read(path)
    if identity['backend']!=backend_identity() or identity['config']!=cfg or identity['config_sha256']!=h or identity['count']!=count:
        raise ValueError(f'Existing verification run is incompatible: {path}')
    return len(rows)==count and (path/'summary.json').exists() and json.loads((path/'summary.json').read_text())['completed_seeds']==count and any(
        json.loads(p.read_text()).get('complete') is True for p in path.glob('invocation-*.json'))

def predictions(rows,optimization=False):
    return [{k:v for k,v in row.items() if k not in IGNORE and (not optimization or k!='cache')} for row in rows]

def summary(path):
    identity,rows=read(path);candidates=[c for r in rows for c in r['candidates']]
    inv=[json.loads(p.read_text()) for p in sorted(Path(path).glob('invocation-*.json'))]
    raw=json.loads((Path(path)/'staged-selection.json').read_text()) if (Path(path)/'staged-selection.json').exists() else {}
    cpu=sum(r.get('worker_cpu_seconds',0) for r in rows)+raw.get('raw_cpu_seconds',0)
    wall=sum(r['wall_seconds'] for r in inv)
    categories={kind:len({c['seed'] for c in candidates if c['landscape_type']==kind and candidate_eligible(c)}) for kind in identity['config']['landscapes']['enabled']}
    cohorts={}
    if raw:
        for selection in ('top','exploration'):
            subset=[r for r in rows if r.get('staged',{}).get('selection')==selection]
            cs=[c for r in subset for c in r['candidates']]
            cohorts[selection]={'full64_count':len(subset),'worker_cpu_seconds':sum(r.get('worker_cpu_seconds',0) for r in subset),
                'category_unique_seeds':{kind:len({c['seed'] for c in cs if c['landscape_type']==kind and candidate_eligible(c)}) for kind in categories},
                'raw_cost':'Shared raw phase charged to whole arm, not assigned twice to selection cohorts.'}
    shadow=[d for r in rows for d in r.get('decisions',[]) if d.get('stage')=='pre_coast_bound']
    return {'path':str(path),'full64_count':len(rows),'raw_layouts':identity.get('raw_layout_budget',0),'raw_seconds':raw.get('raw_seconds',0),
            'run_key':identity['config']['search']['run_key'],'search_mode':identity['config']['search']['mode'],
            'raw_eligible_layouts':raw.get('eligible_raw'),'selection_cohorts':cohorts,
            'wall_seconds':wall,'cpu_seconds':cpu,'candidate_category_unique_seeds':categories,'unique_predicted_qualifying_seeds':len({c['seed'] for c in candidates if candidate_eligible(c)}),
            'website_supported_seeds':len({c['seed'] for c in candidates if c['selection_status']=='chunkbase_supported_candidate'}),
            'predicted_yield_per_cpu_hour':{k:v/cpu*3600 if cpu else None for k,v in categories.items()},
            'timing_percentiles':dict(zip(('p50','p95','maximum'),np.percentile([r['total_seconds'] for r in rows],[50,95,100]).tolist())),
            'distinct_low32':len({int(r['seed'])&0xffffffff for r in rows}),'distinct_centers':len({tuple(c['center']) for c in candidates}),
            'terrain_biome_signatures':len({tuple(sorted(c.get('biome_diversity',{}).get('surface',{}).get('raw_ids',{}))) for c in candidates}),
            'shadow_bounds':len(shadow),'shadow_would_defer':sum(d.get('would_defer',False) for d in shadow),
            'peak_worker_rss_mb':max((r['worker_peak_rss_mb'] for r in rows),default=0),'peak_cache_mb':max((r.get('cache',{}).get('peak_bytes',0)/1024**2 for r in rows),default=0),
            'limits':'Prediction yield, not verified world suitability or recall. Raw scan included; renderer policy identical. CPU excludes parent export/selection serialization and interpreter startup.',
            'backend_identity':identity['backend']}

def experiment():
    base,_=load_config();base['output']['candidate_files']=['candidate.json','inspection.md']
    base['search']['workers']=12
    arms=[]
    # Second key predeclared here before either arm runs. Rotate mode order.
    for key,modes in (('0',('lower32_staged','full_64_bit_reference')),('11400714819323198485',('full_64_bit_reference','lower32_staged'))):
        for mode in modes:
            cfg=copy.deepcopy(base);cfg['search']['run_key']=key;cfg['search']['mode']=mode;cfg['search']['lower_bit_optimization_enabled']=mode=='lower32_staged'
            name=f'experiment-{key}-{mode}';h=config(name,cfg);path=OUT/name
            resume=(path/'checkpoint.sqlite').exists()
            if not completed(path,256,cfg,h):run_search(cfg,h,path,count=256,workers=12,resume=resume)
            arm=summary(path);arms.append(arm);write(OUT/'mode-comparison-partial.json',arms)
    write(OUT/'mode-comparison.json',{'complete':True,'run_keys':['0','11400714819323198485'],'full64_per_arm':256,'arms':arms,'default_promotion':'unresolved_until_category_specific_external_quality; retain reference default'})

def control_seeds():
    # Frozen chosen controls, never used as a random-yield estimate.
    import sqlite3
    db=sqlite3.connect('runs/filter-optimization/pilot-20/checkpoint.sqlite')
    try:rows=[json.loads(v[0]) for v in db.execute('SELECT result FROM seeds')]
    finally:db.close()
    return [int(r['seed']) for r in sorted(rows,key=lambda r:r['index'])][:20]

def parity():
    base,_=load_config();base['output']['candidate_files']=['candidate.json','inspection.md']
    seeds=control_seeds();assert len(seeds)==20
    rows=[]
    for trial in range(3):
        modes=(False,True) if trial%2==0 else (True,False)
        for reuse in modes:
            cfg=copy.deepcopy(base);cfg['optimization']['quart_land_reuse']=reuse
            name=f'parity-{trial}-{int(reuse)}';h=config(name,cfg);path=OUT/name
            if not completed(path,len(seeds),cfg,h):run_search(cfg,h,path,seeds=seeds,workers=12,resume=(path/'checkpoint.sqlite').exists())
        _,a=read(OUT/f'parity-{trial}-0');_,b=read(OUT/f'parity-{trial}-1')
        equal=predictions(a,True)==predictions(b,True)
        write(OUT/f'parity-{trial}.json',{'equal':equal,'original':summary(OUT/f'parity-{trial}-0'),'quart':summary(OUT/f'parity-{trial}-1')})
        assert equal,'Quart reuse changed prediction payload'
        rows.append(json.loads((OUT/f'parity-{trial}.json').read_text()))
    write(OUT/'quart-parity.json',{'equal':True,'trials':rows,'seeds_per_trial':20,'seed_list':[str(s) for s in seeds],
          'wall_median_original':statistics.median(v['original']['wall_seconds'] for v in rows),'wall_median_quart':statistics.median(v['quart']['wall_seconds'] for v in rows)})

def workers():
    base,_=load_config();base['landscapes']['enabled']=['structures_only'];base['output']['candidate_files']=['candidate.json','inspection.md']
    base['search']['mode']='lower32_staged';base['search']['lower_bit_optimization_enabled']=True
    base['search']['staged'].update(raw_layout_count=32,retained_layouts=8,exploration_layouts=2,siblings_per_layout=2,maximum_full64_evaluations=16)
    h=config('worker-variation',base)
    for worker in (1,8,12):
        path=OUT/f'workers-{worker}'
        if not completed(path,16,base,h):run_search(base,h,path,count=16,workers=worker,resume=(path/'checkpoint.sqlite').exists())
    split=OUT/'workers-split'
    if not (split/'checkpoint.sqlite').exists():run_search(base,h,split,count=16,workers=8,stop_after=5)
    if not completed(split,16,base,h):run_search(base,h,split,count=16,workers=12,resume=True)
    baseline=predictions(read(OUT/'workers-1')[1]);equal=all(baseline==predictions(read(path)[1]) for path in [OUT/'workers-8',OUT/'workers-12',split])
    assert equal
    write(OUT/'worker-resume.json',{'equal':equal,'worker_counts':[1,8,12],'full64_count':16,'interrupted_after':5,'backend_identity':backend_identity()})

def recovery():
    cfg,_=load_config();cfg['optimization']['stronghold_prefilter']='review_all';cfg['output']['candidate_files']=['candidate.json','inspection.md']
    # Four discriminating complete seeds; bounded recall diagnostic, not exhaustive recovery.
    seeds=[-1,0,9,4294979641];h=config('recovery',cfg);path=OUT/'recovery'
    if not completed(path,len(seeds),cfg,h):run_search(cfg,h,path,seeds=seeds,workers=12,resume=(path/'checkpoint.sqlite').exists())
    fast=copy.deepcopy(cfg);fast['optimization']['stronghold_prefilter']='defer_unpredicted'
    fh=config('recovery-fast-controls',fast);fp=OUT/'recovery-fast-controls'
    if not completed(fp,len(seeds),fast,fh):run_search(fast,fh,fp,seeds=seeds,workers=12,resume=(fp/'checkpoint.sqlite').exists())
    keys=lambda row,eligible=False:{(c['landscape_type'],tuple(c['center'])) for c in row['candidates'] if not eligible or candidate_eligible(c)}
    comparisons=[]
    for a,b in zip(read(fp)[1],read(path)[1]):
        assert a['seed']==b['seed']
        comparisons.append({'seed':a['seed'],'fast_counts':a['counts']['scored_by_type'],'recovery_counts':b['counts']['scored_by_type'],
            'new_recovery_centers':sorted(keys(b)-keys(a)),'fast_only_centers':sorted(keys(a)-keys(b)),
            'new_native_eligible_centers':sorted(keys(b,True)-keys(a,True)),
            'fast_only_native_eligible_centers':sorted(keys(a,True)-keys(b,True))})
    write(OUT/'recovery.json',{'complete':True,'declared_seeds':[str(s) for s in seeds],'summary':summary(path),
          'fast_summary':summary(fp),'comparisons':comparisons,
          'limits':'Four matched full seeds. Review-all changes nomination scheduling under the same finite budgets; it is not an exhaustive superset or a generated-world Stronghold recall measurement. New centers require independent marker/terrain evidence.'})

def pilot():
    cfg,h=load_config('config/reference-sweep.yaml');seeds=control_seeds()
    split=OUT/'pilot-20';repeat=OUT/'repeat-20'
    if not (split/'checkpoint.sqlite').exists():run_search(cfg,h,split,seeds=seeds,workers=8,stop_after=5)
    if not completed(split,len(seeds),cfg,h):run_search(cfg,h,split,seeds=seeds,workers=12,resume=True)
    if not completed(repeat,len(seeds),cfg,h):run_search(cfg,h,repeat,seeds=seeds,workers=12,resume=(repeat/'checkpoint.sqlite').exists())
    assert predictions(read(split)[1])==predictions(read(repeat)[1])
    write(OUT/'map-pilot.json',{'equal':True,'pilot':summary(split),'repeat':summary(repeat),'seed_list':[str(s) for s in seeds]})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['experiment','parity','workers','recovery','pilot']);args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    globals()[args.mode]()
