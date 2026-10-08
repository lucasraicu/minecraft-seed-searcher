"""Deterministic finite full-seed pipeline; only the parent writes checkpoints."""
import os
import time
import resource
import platform
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from multiprocessing import get_context
import numpy as np
from .backend import Backend
from .config import discovery_grid,validate_config
from .geometry import components,band
from .structures import scan_envelope,at_center,square,nether_center
from .terrain import coast_component,preliminary_component,raster,island_mask_on_raster,LIMITS
from .scoring import landscape_scores,structure_scores,weighted_score,distinct_rank
from .seeds import seed_from_index,parse_seed
from .storage import Store,backend_identity,semantic_hash,SCHEMA
from .preflight import save_json,metadata


def analyze_seed(job):
    index,seed,cfg=job[:3]
    if 'landscapes' in cfg:
        from .landscapes import analyze_landscapes
        return analyze_landscapes(job)
    start=time.perf_counter();times={};counts={};near=[];candidates=[]
    grid=discovery_grid(cfg)
    analysis_bounds=(grid[0],grid[1],grid[0]+(grid[2]-1)*grid[4],grid[1]+(grid[3]-1)*grid[4])
    with Backend(seed) as b:
        t=time.perf_counter();coarse=b.grid(*grid)
        _,cs=components(coarse['approx_height']>=63,*grid[:2],grid[4],cfg['search']['center_axis_bounds_blocks'])
        counts['discovery_points']=coarse['biomes'].size;counts['discovery_components']=len(cs)
        times['discovery']=time.perf_counter()-t
        t=time.perf_counter();scans=scan_envelope(b,cfg);times['structures']=time.perf_counter()-t
        bounded=[c for c in cs if not c['touches_raster_boundary']]
        near.extend({'center':c['center'],'reason':'finite_discovery_boundary','isolation':'unknown'} for c in cs if c['touches_raster_boundary'])
        # Cheap required-target screening covers every possible center in the
        # component plus discovery displacement margin, rather than origin only.
        # Keep one representative rejection per seed for filter audits.
        possible=[];missing=[]
        for component in bounded:
            cb=component['bounds']; margin=64
            nb=(int(np.floor((cb[0]-margin)/8))-496,int(np.floor((cb[1]-margin)/8))-496,
                int(np.ceil((cb[2]+margin)/8))+496,int(np.ceil((cb[3]+margin)/8))+496)
            from .structures import inside
            if all(any(inside(p,nb) for p in scans[t]['raw']) for t in ('fortress','bastion') if cfg['nether'][t+'_required']):
                possible.append(component)
            else:missing.append(component)
        preference=lambda c:(-band(c['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),c['center'])
        possible.sort(key=preference);missing.sort(key=preference)
        counts['early_required_target_screened_components']=len(bounded)
        counts['early_missing_required_components']=len(missing)
        near.extend({'center':c['center'],'reason':'no_required_local_raw_in_possible_center_neighborhood','isolation':'unknown'} for c in missing)
        bounded=possible+missing[:1]
        counts['preliminary_density_points']=0
        counts['preliminary_attempts']=min(len(bounded),cfg['search']['maximum_preliminary_components_per_seed'])
        times['preliminary']=0.0; preliminary=[];pre_seen=set()
        for c in bounded[:cfg['search']['maximum_preliminary_components_per_seed']]:
            t=time.perf_counter(); pc,rejection,points=preliminary_component(b,c,cfg,analysis_bounds)
            times['preliminary']+=time.perf_counter()-t;counts['preliminary_density_points']+=points
            if rejection:near.append(rejection)
            elif tuple(pc['center']) not in pre_seen:
                pre_seen.add(tuple(pc['center']));preliminary.append(pc)
        near.extend({'center':c['center'],'reason':'deferred_preliminary_budget','isolation':'unknown'} for c in bounded[cfg['search']['maximum_preliminary_components_per_seed']:])
        counts['preliminary_closed_components']=len(preliminary)
        preliminary.sort(key=preference);bounded=preliminary
        budget=cfg['search']['maximum_refined_centers_per_seed']
        near.extend({'center':c['center'],'reason':'deferred_refinement_budget','isolation':'unknown','discovery_diameter':c['equivalent_diameter']} for c in bounded[budget:])
        counts['refinement_attempts']=min(budget,len(bounded));counts['deferred_components']=max(0,len(bounded)-budget)
        counts['coast_density_points']=counts['landscape_density_points']=0
        times['coast']=times['landscape']=times['scoring']=0.0
        seen=set()
        for c in bounded[:budget]:
            t=time.perf_counter();coast,rejection=coast_component(b,c,cfg,analysis_bounds);times['coast']+=time.perf_counter()-t
            if rejection:
                near.append(rejection);counts['coast_density_points']+=rejection.get('density_points',0);continue
            cc=coast['component'];center=cc['center']
            counts['coast_density_points']+=coast['points']
            if tuple(center) in seen:continue
            seen.add(tuple(center));structure,status=at_center(scans,center,cfg)
            t=time.perf_counter();terr=raster(b,square(center,3008),cfg['search']['refinement_spacing_blocks'])
            times['landscape']+=time.perf_counter()-t;counts['landscape_density_points']+=terr['points']+terr['sea_level_stride1_points']
            mask=island_mask_on_raster(coast,terr)
            if not mask.any():near.append({'center':center,'reason':'island_below_landscape_grid_resolution','isolation':'unknown'});continue
            t=time.perf_counter();scores,metrics=landscape_scores(terr,mask,cc,cfg)
            ss,factors,sinterval=structure_scores(structure,cfg);scores.update(ss)
            score=weighted_score(scores,cfg,sinterval);times['scoring']+=time.perf_counter()-t
            review=['Terrain-enabled shoreline separation','Settlement buildability','Surrounding mountain appearance',
                    'Extensive accessible woodland on external land/slopes','Required Nether markers and border access','Actual structure footprints remain unknown']
            if status!='predicted_both_required':review.append(status)
            if score['unknown_components']:review.append('Unknown scores: '+', '.join(score['unknown_components']))
            candidate={'seed':str(seed),'index':index,'center':center,'nether_center':list(nether_center(center)),
                       'bounds':{'overworld':list(square(center,3008)),'nether':list(square(nether_center(center),992))},
                       'island':cc,'metrics':metrics,'structures':structure,'structure_score_factors':factors,
                       'nether_status':status,'score':score,'chunkbase_checked':False,'actual_minecraft':None,
                       'selection_status':'unreviewed_local_prediction','remaining_review':review,
                       'approximation_limits':LIMITS,'spawn_proposal':{'x':center[0],'z':center[1],'y':None,'safety':'requires inspection'}}
            candidates.append(candidate)
        counts['scored_centers']=len(candidates)
        counts['predicted_both_nether_centers']=sum(c['nether_status']=='predicted_both_required' for c in candidates)
        counts['disputed_required_centers']=sum(c['nether_status']=='disputed_required_review' for c in candidates)
        core=('trial_chamber','stronghold','mineshaft')
        counts['core_structure_centers']={t:sum(bool(c['structures'][t]['viable']) for c in candidates) for t in core}
        counts['all_three_core_centers']=sum(all(c['structures'][t]['viable'] for t in core) for c in candidates)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
    return {'index':index,'seed':str(seed),'candidates':candidates,'near_misses':near,'counts':counts,
            'stage_seconds':times,'total_seconds':time.perf_counter()-start,'worker_pid':os.getpid(),'worker_peak_rss_mb':rss}


def run_search(cfg,config_hash,output,count=10,start_index=0,workers=None,seeds=None,resume=False,readiness=None,dry_run=False,stop_after=None):
    validate_config(cfg)
    workers=cfg['search']['workers'] if workers is None else workers
    if not isinstance(workers,int) or not 1<=workers<=12:raise ValueError('Workers must be in 1–12')
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=2**64 or not 0<=start_index<2**64 or start_index+count>2**64:
        raise ValueError('Finite index interval must not wrap unsigned 64-bit range')
    if seeds is not None:
        seeds=[parse_seed(s) for s in seeds]
        if len(set(seeds))!=len(seeds) or not seeds:raise ValueError('Supplied seeds must be nonempty and unique')
        count=len(seeds)
    # Bounded pilots <=1000 are authorized by the handoff. Anything larger needs
    # the measured evidence gate; a YAML flag alone never enables it.
    if count>1000:
        from .readiness import check_readiness
        check_readiness(readiness,cfg,config_hash,count)
    identity={'schema':SCHEMA,'config':cfg,'config_sha256':config_hash,'semantic_config_sha256':semantic_hash(cfg),
              'backend':backend_identity(),'start_index':start_index,'count':count,
              'sequence':'supplied' if seeds is not None else 'splitmix64_finalizer','seeds':[str(s) for s in seeds] if seeds else None,
              'evidence_policy':'chunkbase_matching_version_terrain','readiness':str(Path(readiness).resolve()) if readiness else None}
    if dry_run:
        if resume:
            store=Store(output,identity,resume=True);done=store.completed();store.close()
        else:done=set()
        return {'dry_run':True,'would_start_sweep':False,'count':count,'start_index':start_index,'workers':workers,'completed':len(done),'identity':identity}
    store=Store(output,identity,resume=resume);done=store.completed();began=time.perf_counter();batch=[]
    save_json(store.run/'configuration.json',{'original_config_sha256':config_hash,'semantic_sha256':semantic_hash(cfg),'config':cfg})
    if stop_after is not None and not 1<=stop_after<=count:raise ValueError('stop-after must be in 1..count')
    indices=(i for i in range(start_index,start_index+count) if i not in done)
    # Keep only a bounded number of futures: a million-seed run must not enqueue
    # a million jobs or materialize its full seed list.
    def job(i):
        value=(i,seeds[i-start_index] if seeds is not None else seed_from_index(i,int(cfg['search']['run_key'])),cfg)
        return (*value,str(store.run.resolve()/'terrain-cache')) if cfg.get('optimization',{}).get('persist_report_terrain') else value
    try:
        with ProcessPoolExecutor(max_workers=workers,mp_context=get_context('spawn')) as pool:
            pending={};finished=0
            def submit():
                if stop_after is not None and finished+len(pending)>=stop_after:return False
                try:i=next(indices)
                except StopIteration:return False
                j=job(i);pending[pool.submit(analyze_seed,j)]=(i,j[1]);return True
            for _ in range(workers*2):
                if not submit():break
            while pending:
                ready,_=wait(pending,return_when=FIRST_COMPLETED)
                for future in ready:
                    i,seed=pending.pop(future);r=future.result();store.save(i,seed,r);batch.append(r);finished+=1
                    print(f'Completed index {i}, seed {seed}: {r["counts"]["scored_centers"]} centers, {r["total_seconds"]:.2f}s',flush=True)
                while len(pending)<workers*2 and submit():pass
        results=store.results();analysis_wall=time.perf_counter()-began
        from .reports import export_search
        summary=export_search(store.run,results,cfg,config_hash,identity)
        wall=time.perf_counter()-began
        parent_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
        invocation={'completed_this_invocation':len(batch),'wall_seconds':wall,'effective_seconds_per_seed':wall/len(batch) if batch else None,
                    'analysis_wall_seconds':analysis_wall,'report_wall_seconds':wall-analysis_wall,'parent_peak_rss_mb':parent_rss,
                    'workers_requested':workers,'actual_worker_pids':sorted({r['worker_pid'] for r in batch}),
                    'worker_peak_rss_mb':max((r['worker_peak_rss_mb'] for r in batch),default=0),
                    'stage_seconds_summed':{k:sum(r['stage_seconds'][k] for r in batch) for k in (batch[0]['stage_seconds'] if batch else [])},
                    'completed_total':len(results),'requested_total':count,'complete':len(results)==count}
        number=len(list(store.run.glob('invocation-*.json')))
        save_json(store.run/f'invocation-{number:03d}.json',invocation)
        save_json(store.run/'run.json',{'metadata':metadata(config_hash),'identity':identity,'summary':summary,'last_invocation':invocation})
        return invocation
    finally:store.close()
