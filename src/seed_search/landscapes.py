"""Finite searches for enclosed islands, ocean islands and dry mountain basins.

Ocean/Deep Dark coverage nominates locations; density verifies the terrain.
No biome hint establishes isolation or buildability.
"""
import math
import os
import platform
import resource
import time
import numpy as np
from scipy import ndimage
from .backend import Backend,biome_name
from .cache import CachedBackend
from .config import discovery_grid
from .geometry import components,band,largest_gap
from .terrain import raster,sample_points,preliminary_component,coast_component,island_mask_on_raster,LIMITS
from .structures import scan_envelope,scan_type,possible_required_centers,at_center,square,nether_center,inside,required_types
from .scoring import landscape_scores,structure_scores,weighted_score

KINDS=('structures_only','enclosed_island','ocean_island','mountain_basin')


def validate_landscapes(settings):
    expected={'enabled','ocean_window_side_blocks','minimum_ocean_fraction','flat_radius_blocks',
              'maximum_flat_relief_blocks','maximum_flat_slope','minimum_dry_fraction',
              'ring_radius_blocks','minimum_ring_relative_height_blocks','minimum_ring_fraction',
              'deep_dark_y','deep_dark_inner_side_blocks','deep_dark_outer_side_blocks',
              'deep_dark_spacing_blocks','deep_dark_policy'}
    if set(settings)!=expected:raise ValueError('Unsupported landscape settings')
    kinds=settings['enabled']
    if not kinds or len(kinds)!=len(set(kinds)) or set(kinds)-set(KINDS):raise ValueError('Invalid landscape types')
    for k in ('ocean_window_side_blocks','flat_radius_blocks','maximum_flat_relief_blocks','ring_radius_blocks',
              'minimum_ring_relative_height_blocks','deep_dark_inner_side_blocks','deep_dark_outer_side_blocks','deep_dark_spacing_blocks'):
        v=settings[k]
        if isinstance(v,bool) or not isinstance(v,int) or v<=0:raise ValueError(f'Invalid landscape integer {k}')
    for k in ('minimum_ocean_fraction','maximum_flat_slope','minimum_dry_fraction','minimum_ring_fraction'):
        v=settings[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=1:
            raise ValueError(f'Invalid landscape fraction {k}')
    if not 32<=settings['flat_radius_blocks']<=256 or not settings['flat_radius_blocks']<settings['ring_radius_blocks']<=1000:
        raise ValueError('Flat/ring radii exceed the finite landscape budget')
    if settings['ocean_window_side_blocks']>3008 or not settings['deep_dark_inner_side_blocks']<=settings['deep_dark_outer_side_blocks']<=512:
        raise ValueError('Coverage windows exceed their finite budgets')
    if settings['deep_dark_spacing_blocks'] not in (8,16,32,64) or settings['deep_dark_y']!=-32 or settings['deep_dark_policy']!='rank_only':
        raise ValueError('Deep Dark at Y=-32 is a ranking hint, never a hard terrain filter')


def ocean_ids(biomes):
    return [int(i) for i in np.unique(biomes) if 'ocean' in biome_name(i)]


def coverage_at(coarse,center,grid,side):
    x0,z0,nx,nz,step=grid;half=side//2
    xa=x0+np.arange(nx)*step;za=z0+np.arange(nz)*step
    xm=(xa>=center[0]-half)&(xa<=center[0]+half);zm=(za>=center[1]-half)&(za<=center[1]+half)
    complete=center[0]-half>=xa[0] and center[0]+half<=xa[-1] and center[1]-half>=za[0] and center[1]+half<=za[-1]
    b=coarse['biomes'][np.ix_(zm,xm)]
    return float(np.isin(b,ocean_ids(b)).mean()) if b.size else 0.0,complete


def deep_dark_hint(backend,center,settings):
    rows={}
    for name in ('inner','outer'):
        half=settings[f'deep_dark_{name}_side_blocks']//2;step=settings['deep_dark_spacing_blocks']
        axis=np.arange(-half,half+1,step)
        ids=[backend.biome(int(center[0]+x),settings['deep_dark_y'],int(center[1]+z)) for z in axis for x in axis]
        rows[name+'_fraction']=sum(biome_name(i)=='deep_dark' for i in ids)/len(ids)
        rows[name+'_points']=len(ids)
    # Outer includes the inner window, matching the screenshot.
    rows['contrast']=rows['outer_fraction']-rows['inner_fraction']
    rows['y']=settings['deep_dark_y'];rows['use']='rank_only_not_terrain_proof'
    return rows


def xy_raster(terrain):
    h=terrain['height'];step=terrain['step'];x0,z0=terrain['bounds'][:2]
    return np.meshgrid(x0+np.arange(h.shape[1])*step,z0+np.arange(h.shape[0])*step)


def raster_intermediates(terrain):
    h=terrain['height'];step=terrain['step'];x,z=xy_raster(terrain)
    dry=h>=68;labels,_=ndimage.label(dry,np.ones((3,3),int))
    gz,gx=np.gradient(h.astype(float),step)
    return {'x':x,'z':z,'dry':dry,'labels':labels,'slope':np.hypot(gx,gz),
            'local_range':ndimage.maximum_filter(h,size=5)-ndimage.minimum_filter(h,size=5)}


def flat_metrics(terrain,center,settings,context=None):
    h=terrain['height'];step=terrain['step'];context=context or raster_intermediates(terrain)
    x,z=context['x'],context['z']
    disk=np.hypot(x-center[0],z-center[1])<=settings['flat_radius_blocks']
    dry,labels=context['dry'],context['labels']
    col=round((center[0]-terrain['bounds'][0])/step);row=round((center[1]-terrain['bounds'][1])/step)
    ident=labels[row,col] if 0<=row<h.shape[0] and 0<=col<h.shape[1] else 0
    connected=(labels==ident)&dry if ident else np.zeros_like(dry)
    values=h[disk&connected]
    fraction=float((disk&connected).sum()/disk.sum()) if disk.any() else 0.0
    relief=float(np.percentile(values,90)-np.percentile(values,10)) if len(values) else None
    slope=context['slope']
    gentle=float((disk&connected&(slope<=settings['maximum_flat_slope'])).sum()/disk.sum()) if disk.any() else 0.0
    flat=disk&connected&(slope<=settings['maximum_flat_slope'])
    passed=fraction>=settings['minimum_dry_fraction'] and relief is not None and relief<=settings['maximum_flat_relief_blocks'] and gentle>=settings['minimum_dry_fraction']
    return {'dry_connected_fraction':fraction,'gentle_ground_fraction':gentle,'inner_height_p90_minus_p10':relief,
            'inner_height_median':float(np.median(values)) if len(values) else None,
            'flat_ground_preference_met':bool(passed),'flat_ground_area_blocks2':int(flat.sum())*step**2,
            'flat_radius_blocks':settings['flat_radius_blocks'],'sea_level_safety_margin_blocks':5,
            'buildability_evidence':'sampled_density_relief_and_slope; actual ground requires review'},flat,connected


def ring_metrics(terrain,center,settings,connected,inner_height):
    h=terrain['height'];step=terrain['step'];x0,z0=terrain['bounds'][:2]
    hits=[];dry_hits=[];heights=[];distances=[];unknown=[]
    n=180;reach=settings['ring_radius_blocks'];minimum=settings['flat_radius_blocks']
    threshold=max(113,(inner_height or 63)+settings['minimum_ring_relative_height_blocks'])
    for angle in np.arange(n)*2*math.pi/n:
        distance=np.arange(minimum,reach+1,step/2)
        x=np.rint((center[0]+np.cos(angle)*distance-x0)/step).astype(int)
        z=np.rint((center[1]+np.sin(angle)*distance-z0)/step).astype(int)
        valid=(x>=0)&(z>=0)&(x<h.shape[1])&(z<h.shape[0])
        unknown.append(not bool(valid.all()));x=x[valid];z=z[valid];distance=distance[valid]
        high=h[z,x]>=threshold;hits.append(bool(high.any()))
        dry_high=high&connected[z,x];dry_hits.append(bool(dry_high.any()))
        if high.any():
            at=np.flatnonzero(high)[0];heights.append(float(h[z[at],x[at]]-63));distances.append(float(distance[at]))
    fraction=sum(hits)/n;dry_fraction=sum(dry_hits)/n;uncertain=sum(unknown)/n
    return {'ring_fraction_bounds':[fraction,min(1,fraction+uncertain)],'ring_dry_connected_fraction':dry_fraction,
            'ring_unknown_rays':sum(unknown),'ring_preference_met':fraction>=settings['minimum_ring_fraction'],
            'dry_mountain_basin_preference_met':dry_fraction>=settings['minimum_ring_fraction'],
            'largest_ring_gap_degrees':largest_gap(~np.array(hits)&~np.array(unknown)),
            'ring_height_threshold':threshold,'ring_median_high_relative_height':float(np.median(heights)) if heights else None,
            'ring_median_distance':float(np.median(distances)) if distances else None}


def build_centers(terrain,allowed,center_bounds,limit=1,context=None):
    """Find dry, low-relief areas, rather than placing an ocean base on a summit."""
    h=terrain['height'];step=terrain['step'];context=context or raster_intermediates(terrain)
    flat=allowed&(h>=68)&(context['slope']<=.3)&(context['local_range']<=24)
    _,cs=components(flat,*terrain['bounds'][:2],step,center_bounds)
    return sorted(cs,key=lambda c:(-c['area'],c['center']))[:limit]


def basin_necessary_bound(backend,center,cfg):
    """Prove failure cheaply; never treat local connectivity as global connectivity.

    Include the original anchor and the same eight allowed +/-256 recenters.
    Halo preserves gradients/5x5 nomination kernels and full-raster lattice parity.
    Dry/gentle counts ignore connectivity, so they are upper bounds, not new tests.
    Ring hits ignore connectivity and use the smallest possible threshold (113).
    """
    s=cfg['landscapes'];step=cfg['search']['refinement_spacing_blocks']
    # Slice the exact reference lattice, including its phase at spacing 64.
    full=square(center,cfg['deployment']['overworld_side_blocks'])
    reach=256+s['flat_radius_blocks']+2*step
    bounds=[full[0]+math.floor((center[0]-reach-full[0])/step)*step,
            full[1]+math.floor((center[1]-reach-full[1])/step)*step,
            full[0]+math.ceil((center[0]+reach-full[0])/step)*step,
            full[1]+math.ceil((center[1]+reach-full[1])/step)*step]
    if bounds[0]<=full[0] or bounds[1]<=full[1] or bounds[2]>=full[2] or bounds[3]>=full[3]:
        return {'impossible':False,'points':0,'reason':'local_bound_not_smaller_or_clipped'}
    terrain=raster(backend,bounds,step)
    context=raster_intermediates(terrain);x,z=context['x'],context['z']
    allowed=np.hypot(x-center[0],z-center[1])<=256
    sites=build_centers(terrain,allowed,cfg['search']['center_axis_bounds_blocks'],8,context)
    centers=[list(p) for p in dict.fromkeys(tuple(p) for p in [center]+[v['center'] for v in sites])];possible=[]
    for candidate in centers:
        disk=np.hypot(x-candidate[0],z-candidate[1])<=s['flat_radius_blocks']
        n=int(disk.sum());dry=int((disk&context['dry']).sum())
        gentle=int((disk&context['dry']&(context['slope']<=s['maximum_flat_slope'])).sum())
        if n and dry/n>=s['minimum_dry_fraction'] and gentle/n>=s['minimum_dry_fraction']:
            possible.append(candidate)
    count=terrain['points']+terrain['sea_level_stride1_points']
    result={'impossible':not bool(possible),'points':count,'tested_centers':centers,
            'reason':'dry_or_gentle_upper_bound','coverage_points':0}
    if result['impossible'] or not cfg.get('optimization',{}).get('lazy_coverage_bounds',False):return result
    # Bound overhead on survivors; unfinished rays remain possible, never misses.
    budget=5000;needed=math.ceil(180*s['minimum_ring_fraction']);origin=(center[0]-cfg['deployment']['overworld_side_blocks']//2,center[1]-cfg['deployment']['overworld_side_blocks']//2)
    distance=np.arange(s['flat_radius_blocks'],s['ring_radius_blocks']+1,step/2)
    for candidate in possible:
        hits=misses=0
        for first in range(0,180,8):
            batch=[];sizes=[]
            for bearing in range(first,min(180,first+8)):
                angle=bearing*2*math.pi/180
                xx=np.rint((candidate[0]+np.cos(angle)*distance-origin[0])/step).astype(int)*step+origin[0]
                zz=np.rint((candidate[1]+np.sin(angle)*distance-origin[1])/step).astype(int)*step+origin[1]
                points=np.unique(np.column_stack((xx,zz)),axis=0);batch.append(points);sizes.append(len(points))
            points=np.concatenate(batch)
            if result['coverage_points']+len(points)>budget:
                result.update(impossible=False,reason='coverage_budget_unresolved');return result
            heights,_=sample_points(backend,points)
            # Near-sea adaptive correction cannot create a 113-high mountain,
            # but preserve the exact raster contract rather than relying on it.
            near=np.abs(heights-63)<=5
            if near.any():heights[near],_=sample_points(backend,points[near],1)
            result['coverage_points']+=len(points);result['points']+=len(points)+int(near.sum())
            for ray in np.split(heights,np.cumsum(sizes)[:-1]):
                if (ray>=113).any():hits+=1
                else:misses+=1
            if hits>=needed:result.update(impossible=False,reason='ring_possible');return result
            if misses>180-needed:break
        else:
            result.update(impossible=False,reason='ring_possible');return result
    result.update(impossible=True,reason='ring_coverage_upper_bound');return result


def coarse_basin_sites(coarse,grid,settings,center_bounds,labels,center_heights=None):
    """Vectorized nomination; a wide relief window would erase small valleys.

    Evaluate coarse mountain bearings around land points, group neighboring
    nominations, and choose the lowest center with the strongest ring hint.
    Density/slope/connection checks occur later at 16-block spacing.
    """
    h=coarse['approx_height'];x0,z0,nx,nz,step=grid
    reference=h if center_heights is None else center_heights
    xx,zz=np.meshgrid(x0+np.arange(nx)*step,z0+np.arange(nz)*step)
    possible=(h>=68)&(xx>=center_bounds[0])&(xx<=center_bounds[1])&(zz>=center_bounds[0])&(zz<=center_bounds[1])
    rows,cols=np.nonzero(possible);fraction=np.zeros_like(h,dtype=float)
    angles=np.arange(36)*2*math.pi/36
    distance=np.arange(max(step,settings['flat_radius_blocks']),settings['ring_radius_blocks']+1,step)
    dx=np.rint(np.cos(angles)[:,None]*distance/step).astype(int)
    dz=np.rint(np.sin(angles)[:,None]*distance/step).astype(int)
    for start in range(0,len(rows),512):
        r=rows[start:start+512];c=cols[start:start+512]
        rr=r[:,None,None]+dz;cc=c[:,None,None]+dx
        valid=(rr>=0)&(cc>=0)&(rr<nz)&(cc<nx)
        values=h[np.clip(rr,0,nz-1),np.clip(cc,0,nx-1)]
        high=(values>=np.maximum(113,reference[r,c]+settings['minimum_ring_relative_height_blocks'])[:,None,None])&valid
        fraction[r,c]=high.any(axis=2).mean(axis=1)
    _,regions=components(fraction>=settings['minimum_ring_fraction']*.5,x0,z0,step,center_bounds)
    # Label again to preserve the membership of every actual coarse nomination.
    region_labels,_=ndimage.label(fraction>=settings['minimum_ring_fraction']*.5,np.ones((3,3),int))
    out=[]
    for component in regions:
        r,c=np.nonzero(region_labels==component['label'])
        world_x=x0+c*step;world_z=z0+r*step
        eligible=(world_x>=center_bounds[0])&(world_x<=center_bounds[1])&(world_z>=center_bounds[0])&(world_z<=center_bounds[1])
        r=r[eligible];c=c[eligible]
        at=np.lexsort((c,r,reference[r,c],-fraction[r,c]))[0]
        center=[int(x0+c[at]*step),int(z0+r[at]*step)]
        out.append({**component,'center':center,'coarse_ring_fraction':float(fraction[r[at],c[at]]),
                    'discovered_land_label':int(labels[r[at],c[at]])})
    return out


def ocean_preliminary(backend,source,cfg,analysis_bounds):
    step=cfg['search']['refinement_spacing_blocks'];half=cfg['search']['maximum_refinement_patch_side_blocks']//2
    center=source['center']
    bounds=[max(analysis_bounds[0],(center[0]-half)//step*step),max(analysis_bounds[1],(center[1]-half)//step*step),
            min(analysis_bounds[2],(center[0]+half)//step*step),min(analysis_bounds[3],(center[1]+half)//step*step)]
    t=raster(backend,bounds,step);labels,cs=components(t['height']>=63,*bounds[:2],step,cfg['search']['center_axis_bounds_blocks'])
    a=source['bounds'];matching=[c for c in cs if not c['touches_raster_boundary'] and not(c['bounds'][2]<a[0] or c['bounds'][0]>a[2] or c['bounds'][3]<a[1] or c['bounds'][1]>a[3])]
    count=t['points']+t['sea_level_stride1_points']
    if not matching:return None,None,{'reason':'ocean_density_not_closed_within_finite_patch','center':center,'isolation':'unknown'},count
    c=min(matching,key=lambda c:(math.dist(c['center'],center),-c['area'],c['center']))
    sites=build_centers(t,labels==c['label'],cfg['search']['center_axis_bounds_blocks'])
    # A 64-block discovery lattice can miss the small floor of a mountain ring.
    # For a promising coarse ring, nominate again from the density raster already
    # sampled here. This adds no native terrain queries.
    if source.get('coarse_ring_fraction',0)>0:
        s={**cfg['landscapes'],'flat_radius_blocks':32}
        local_grid=(bounds[0],bounds[1],t['height'].shape[1],t['height'].shape[0],step)
        radius=max(1,32//step);rr,cc=np.mgrid[-radius:radius+1,-radius:radius+1]
        median_ground=ndimage.median_filter(t['height'],footprint=rr**2+cc**2<=radius**2)
        local=coarse_basin_sites({'approx_height':t['height']},local_grid,s,cfg['search']['center_axis_bounds_blocks'],labels,median_ground)
        local=[v for v in local if v['discovered_land_label']==c['label']]
        if local:
            site=min(local,key=lambda v:(-v['coarse_ring_fraction'],v['center']))
            if site['coarse_ring_fraction']>=s['minimum_ring_fraction']:
                c['build_center_method']='density_ring_nomination'
                return c,site['center'],None,count
    return c,sites[0]['center'] if sites else c['center'],None,count


def round_robin(groups,limit):
    out=[]
    for i in range(max((len(v) for v in groups.values()),default=0)):
        for kind,values in groups.items():
            if i<len(values):out.append((kind,values[i]))
            if len(out)>=limit:return out
    return out


def analyze_landscapes(job):
    index,seed,cfg=job[:3];cache_root=job[3] if len(job)>3 else None
    start=time.perf_counter();cpu_start=time.process_time();times={k:0.0 for k in ('discovery','structures','proxy','preliminary','coast','landscape','scoring')}
    counts={};near=[];candidates=[];settings=cfg['landscapes'];grid=discovery_grid(cfg)
    times.update(biome_inventory=0.,structures_only=0.)
    decisions=[]
    diversity_enabled='biome_diversity' in cfg
    bounds=(grid[0],grid[1],grid[0]+(grid[2]-1)*grid[4],grid[1]+(grid[3]-1)*grid[4])
    opt=cfg.get('optimization',{});fast=opt.get('stronghold_prefilter')=='defer_unpredicted'
    backend=CachedBackend(seed,opt['cache_mb_per_worker'],opt.get('raw_mt_cache_entries',0),opt.get('quart_land_reuse',False)) if opt.get('exact_per_seed_cache') else Backend(seed,opt.get('raw_mt_cache_entries',0))
    times['setup']=time.perf_counter()-start
    counts.update(discovery_points=0,discovery_components=0,preliminary_attempts=0,preliminary_density_points=0,
                  refinement_attempts=0,coast_density_points=0,landscape_density_points=0,deferred_components=0,
                  early_structure_deferred=0,early_basin_attempts=0,early_basin_rejections=0,early_basin_points=0,
                  nominated_by_type={k:0 for k in settings['enabled']})
    def finish(b):
        if diversity_enabled and cfg['biome_diversity']['scope']=='all_evaluated' and not candidates:
            from .biomes import inventory,grid_points
            lo,hi=cfg['search']['center_axis_bounds_blocks'];anchor=min(math.floor(hi/8)*8,max(math.ceil(lo/8)*8,0))
            box=square((anchor,anchor),cfg['deployment']['overworld_side_blocks']);points=grid_points(box,64)
            t=time.perf_counter();ids=b.biome_points(np.column_stack((points[:,0],np.full(len(points),63),points[:,1])))
            counts['failed_seed_biome_diagnostic']=inventory(ids,points,64,box,cfg['biome_diversity'],'diagnostic_fixed_y',63)
            counts['biome_query_points']=counts.get('biome_query_points',0)+len(points);times['biome_inventory']+=time.perf_counter()-t
        counts['scored_centers']=len(candidates)
        for c in candidates:
            c['search_category']=c['landscape_type']
            c['terrain_status']='not_required' if c['landscape_type']=='structures_only' else 'predicted_branch_checks_passed'
            c['output_classification']='predicted_candidate' if c['nether_status'] in ('predicted_required_structures','predicted_both_required') else 'unresolved_review'
            decisions.append({'branch':c['landscape_type'],'center':c['center'],'outcome':c['output_classification'],'reason':'final_exact_border_checks','index':index})
        for n,v in enumerate(near):
            decisions.append({'branch':v.get('landscape_type','all'),'nomination_id':n,'center':v.get('center'),'reason':v['reason'],'outcome':'deferred' if 'deferred' in v['reason'] or 'budget' in v['reason'] else 'unresolved' if v.get('isolation')=='unknown' else 'failed'})
        counts['terminal_decisions']={outcome:sum(d['outcome']==outcome for d in decisions) for outcome in ('predicted_candidate','unresolved_review','failed','unresolved','deferred')}
        counts['scored_by_type']={k:sum(c['landscape_type']==k for c in candidates) for k in settings['enabled']}
        counts['predicted_required_centers']=sum(c['nether_status'] in ('predicted_required_structures','predicted_both_required') for c in candidates)
        counts['predicted_both_nether_centers']=sum(all(c['structures'][t]['viable'] for t in ('fortress','bastion')) for c in candidates)
        counts['disputed_required_centers']=sum(c['nether_status']=='disputed_required_review' for c in candidates)
        counts['all_three_core_centers']=sum(all(c['structures'][t]['viable'] for t in ('trial_chamber','stronghold','mineshaft')) for c in candidates)
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
        work=getattr(b,'native_work',{})
        for name,row in work.items():times['native_inclusive_'+name]=row['seconds']
        return {'index':index,'seed':str(seed),'candidates':candidates,'near_misses':near,'counts':counts,'stage_seconds':times,
                'total_seconds':time.perf_counter()-start,'worker_cpu_seconds':time.process_time()-cpu_start,'worker_pid':os.getpid(),'worker_peak_rss_mb':rss,
                'decisions':decisions,'filter_policy':opt.get('stronghold_prefilter','review_all'),
                'native_work':{k:{name:v for name,v in row.items() if name!='seconds'} for k,row in work.items()},
                'cache':b.cache_statistics() if isinstance(b,CachedBackend) else None}
    with backend as b:
        initial={}
        if fast:
            t=time.perf_counter();initial['stronghold']=scan_type(b,cfg,'stronghold')
            if initial['stronghold']['raw']:
                for typ in required_types(cfg):
                    if typ not in initial:initial[typ]=scan_type(b,cfg,typ)
            times['structures']+=time.perf_counter()-t
            lo,hi=cfg['search']['center_axis_bounds_blocks']
            if not initial['stronghold']['raw'] or not possible_required_centers(initial,cfg,(lo,lo,hi,hi)):
                counts['early_structure_deferred']=1
                near.append({'reason':'deferred_seed_no_joint_required_prediction','isolation':'unknown',
                             'center_bounds':[lo,lo,hi,hi],'stronghold_completeness':'unknown',
                             'review':'Fast heuristic; no native prediction is not proof of absence. Re-run with stronghold_prefilter: review_all.'})
                return finish(b)
        t=time.perf_counter();coarse=b.grid(*grid)
        coarse_labels,cs=components(coarse['approx_height']>=63,*grid[:2],grid[4],cfg['search']['center_axis_bounds_blocks'])
        times['discovery']=time.perf_counter()-t
        counts.update(discovery_points=coarse['biomes'].size,discovery_components=len(cs))
        t=time.perf_counter();scans=scan_envelope(b,cfg,initial);times['structures']+=time.perf_counter()-t
        if 'structures_only' in settings['enabled']:
            t=time.perf_counter()
            from .structures import structure_centers
            proposed=[]
            for center in structure_centers(scans,cfg):
                rows,status=at_center(scans,center,cfg)
                if status!='predicted_required_structures':continue
                ss,factors,interval=structure_scores(rows,cfg)
                structure_cfg={**cfg,'score_weights':{k:cfg['score_weights'][k] for k in ('overworld_structures','nether_proximity')}}
                base=weighted_score(ss,structure_cfg,interval)
                proposed.append((base['interval'][0],center,rows,status,factors,base))
            limit=cfg['search'].get('maximum_structure_centers_per_seed',2)
            counts['structures_only_center_proposals']=len(proposed)
            counts['structures_only_deferred_centers']=max(0,len(proposed)-limit)
            if len(proposed)>limit:decisions.append({'branch':'structures_only','stage':'center_selection','outcome':'deferred','reason':'structures_only_output_budget','count':len(proposed)-limit})
            for _,center,rows,status,factors,base in sorted(proposed,key=lambda v:(-v[0],v[1]))[:limit]:
                candidate={'seed':str(seed),'index':index,'center':list(center),'nether_center':list(nether_center(center)),
                           'landscape_type':'structures_only','island':None,'metrics':{'terrain':None,'landscape_type':'structures_only'},
                           'bounds':{'overworld':list(square(center,cfg['deployment']['overworld_side_blocks'])),'nether':list(square(nether_center(center),cfg['deployment']['nether_side_blocks']))},
                           'structures':rows,'structure_score_factors':factors,'score':base,'nether_status':status,
                           'required_structure_types':list(required_types(cfg)),'selection_status':'unreviewed_local_prediction','chunkbase_checked':False,'actual_minecraft':None,
                           'remaining_review':['Required Fortress and Stronghold markers inside exact squares','Actual structure access and footprints'],
                           'approximation_limits':LIMITS,'spawn_proposal':{'x':center[0],'z':center[1],'y':None,'safety':'requires inspection'}}
                if diversity_enabled:
                    from .biomes import candidate_diversity,add_bonus
                    tb=time.perf_counter();surface=raster(b,candidate['bounds']['overworld'],cfg['biome_diversity']['structures_surface_spacing'])
                    counts['biome_surface_height_points']=counts.get('biome_surface_height_points',0)+surface['points']+surface['sea_level_stride1_points']
                    div=candidate_diversity(b,surface,center,cfg,coarse,grid)
                    candidate['biome_diversity']=div;candidate['score']=add_bonus(base,div,30)
                    counts['biome_query_points']=counts.get('biome_query_points',0)+div['additional_biome_query_points']
                    times['biome_inventory']+=time.perf_counter()-tb
                candidates.append(candidate)
            times['structures_only']+=time.perf_counter()-t
        if not any(k!='structures_only' for k in settings['enabled']):return finish(b)
        def fortress_possible(c):
            a=c['bounds'];nb=(math.floor((a[0]-64)/8)-cfg['deployment']['nether_side_blocks']//2,math.floor((a[1]-64)/8)-cfg['deployment']['nether_side_blocks']//2,
                             math.ceil((a[2]+64)/8)+cfg['deployment']['nether_side_blocks']//2,math.ceil((a[3]+64)/8)+cfg['deployment']['nether_side_blocks']//2)
            return any(inside(p,nb) for p in scans['fortress']['raw'])
        def priority(c):
            a=c['bounds'];ob=(a[0]-(cfg['deployment']['overworld_side_blocks']//2+64),a[1]-(cfg['deployment']['overworld_side_blocks']//2+64),a[2]+(cfg['deployment']['overworld_side_blocks']//2+64),a[3]+(cfg['deployment']['overworld_side_blocks']//2+64))
            return (not fortress_possible(c),not any(inside(p,ob) for p in scans['stronghold']['raw']))
        group_started=time.perf_counter()
        closed=[c for c in cs if not c['touches_raster_boundary']]
        groups={k:[] for k in settings['enabled'] if k!='structures_only'}
        basin_sites=coarse_basin_sites(coarse,grid,settings,cfg['search']['center_axis_bounds_blocks'],coarse_labels) if any(k in groups for k in ('ocean_island','mountain_basin')) else []
        ring_by_component={}
        for site in basin_sites:
            label=site['discovered_land_label']
            ring_by_component[label]=max(ring_by_component.get(label,0),site['coarse_ring_fraction'])
        if 'enclosed_island' in groups:
            groups['enclosed_island']=sorted(closed,key=lambda c:(*priority(c),-band(c['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),c['center']))
        if 'ocean_island' in groups:
            for c in closed:
                ocean,complete=coverage_at(coarse,c['center'],grid,settings['ocean_window_side_blocks'])
                if complete and ocean>=settings['minimum_ocean_fraction']:
                    groups['ocean_island'].append({**c,'coarse_ocean_fraction':ocean,'coarse_ring_fraction':ring_by_component.get(c['label'],0)})
            groups['ocean_island'].sort(key=lambda c:(*priority(c),-c['coarse_ring_fraction'],-band(c['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),-c['coarse_ocean_fraction'],c['center']))
        if 'mountain_basin' in groups:
            groups['mountain_basin']=basin_sites
            groups['mountain_basin'].sort(key=lambda c:(*priority(c),-c['coarse_ring_fraction'],-c['area'],c['center']))
        times['proxy']+=time.perf_counter()-group_started
        counts['nominated_by_type']={k:len(v) for k,v in groups.items()}
        if fast:
            lo,hi=cfg['search']['center_axis_bounds_blocks']
            for kind,values in groups.items():
                retained=[]
                for c in values:
                    a=c['bounds'];margin=256 if kind=='mountain_basin' else 64
                    box=(max(lo,a[0]-margin),max(lo,a[1]-margin),min(hi,a[2]+margin),min(hi,a[3]+margin))
                    if possible_required_centers(scans,cfg,box):retained.append(c)
                    else:
                        counts['early_structure_deferred']+=1
                        near.append({'landscape_type':kind,'center':c['center'],'reason':'deferred_component_no_joint_required_prediction',
                                     'isolation':'unknown','stronghold_completeness':'unknown',
                                     'review':'Nomination envelope heuristic; retain for review_all recovery, not proof of absence.'})
                groups[kind]=retained
        # Cave inventory is manual-only, including historical profile execution.
        t=time.perf_counter();limit=cfg['search']['maximum_preliminary_components_per_seed']
        nominations=round_robin(groups,limit);prepared={k:[] for k in groups}
        for kind,c in nominations:
            hint=None
            prepared[kind].append((c,hint))
        times['proxy']+=time.perf_counter()-t
        counts['preliminary_attempts']=len(nominations);counts['preliminary_density_points']=0
        viable={k:[] for k in groups};pre_cache={}
        for kind,values in prepared.items():
            for c,hint in values:
                t=time.perf_counter()
                if kind=='mountain_basin':pc=c;build_center=c['center'];err=None;points=0
                else:
                    key=(kind,tuple(c['center']))
                    if key in pre_cache:pc,build_center,err,points=pre_cache[key];points=0
                    elif kind=='ocean_island':pc,build_center,err,points=ocean_preliminary(b,c,cfg,bounds);pre_cache[key]=(pc,build_center,err,points)
                    else:pc,err,points=preliminary_component(b,c,cfg,bounds);build_center=pc['center'] if pc else None;pre_cache[key]=(pc,build_center,err,points)
                times['preliminary']+=time.perf_counter()-t;counts['preliminary_density_points']+=points
                if err:near.append({'landscape_type':kind,**err})
                else:
                    pc['coarse_ring_fraction']=c.get('coarse_ring_fraction',0)
                    viable[kind].append((pc,build_center,hint))
        # Hint breaks geometric priority ties; it never outranks required starts.
        for kind,values in viable.items():
            if kind=='mountain_basin':values.sort(key=lambda v:(*priority(v[0]),-v[0]['coarse_ring_fraction'],-(v[2]['contrast'] if v[2] else 0),v[1]))
            else:values.sort(key=lambda v:(*priority(v[0]),-v[0].get('coarse_ring_fraction',0) if kind=='ocean_island' else 0,-band(v[0]['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks']),-(v[2]['contrast'] if v[2] else 0),v[1]))
        budget=cfg['search']['maximum_refined_centers_per_seed'];selected=round_robin(viable,budget)
        counts['refinement_attempts']=len(selected);counts['coast_density_points']=counts['landscape_density_points']=0
        counts['deferred_components']=sum(len(v) for v in viable.values())-len(selected)
        near.extend({'landscape_type':kind,'center':c['center'],'reason':'deferred_preliminary_budget','isolation':'unknown'} for kind,values in groups.items() for c in values[len(prepared[kind]):])
        selected_keys={(kind,tuple(v[1])) for kind,v in selected}
        near.extend({'landscape_type':kind,'center':v[1],'reason':'deferred_refinement_budget','isolation':'unknown'} for kind,values in viable.items() for v in values if (kind,tuple(v[1])) not in selected_keys)
        seen=set();coasts={}
        for kind,(c,proposed_center,hint) in selected:
            coast=None;t=time.perf_counter()
            if kind=='mountain_basin' and opt.get('early_basin_bounds',False):
                bound=basin_necessary_bound(b,proposed_center,cfg)
                counts['early_basin_attempts']+=1;counts['early_basin_points']+=bound['points']
                times['landscape']+=time.perf_counter()-t;t=time.perf_counter()
                if bound['impossible']:
                    counts['early_basin_rejections']+=1
                    near.append({'landscape_type':kind,'center':proposed_center,'reason':'basin_necessary_bound_failed','bound':bound})
                    continue
            if kind!='mountain_basin':
                if opt.get('island_bound_policy')=='shadow':
                    from .terrain import island_necessary_bound
                    shadow=island_necessary_bound(c,cfg,bounds,scans)
                    decisions.append({'branch':kind,'center':proposed_center,'stage':'pre_coast_bound','outcome':'unresolved',
                                      'reason':shadow['reason'],'would_defer':shadow['predicted_required_window_impossible'],'bound':shadow})
                key=(tuple(c['center']),tuple(c['bounds']),tuple(bounds),cfg['search']['shoreline_spacing_blocks'],cfg['search']['maximum_refinement_patch_side_blocks'])
                if key in coasts:coast,err=coasts[key]
                else:
                    coast,err=coast_component(b,c,cfg,bounds);coasts[key]=(coast,err)
                    counts['coast_density_points']+=coast['points'] if coast else err.get('density_points',0)
                if err:near.append({'landscape_type':kind,**err});times['coast']+=time.perf_counter()-t;continue
                c=dict(coast['component']);center=c['center'] if kind=='enclosed_island' else proposed_center
                row=center[1]-coast['bounds'][1];col=center[0]-coast['bounds'][0]
                if not(0<=row<coast['mask'].shape[0] and 0<=col<coast['mask'].shape[1] and coast['mask'][row,col]):center=c['center']
                c['center']=center
            else:center=proposed_center
            times['coast']+=time.perf_counter()-t
            if (kind,tuple(center)) in seen:continue
            if fast and kind!='mountain_basin' and not possible_required_centers(scans,cfg,(*center,*center)):
                counts['early_structure_deferred']+=1
                near.append({'landscape_type':kind,'center':center,'reason':'deferred_exact_center_no_joint_required_prediction',
                             'stronghold_completeness':'unknown','isolation':'unknown'})
                continue
            t=time.perf_counter();terrain=raster(b,square(center,cfg['deployment']['overworld_side_blocks']),cfg['search']['refinement_spacing_blocks'])
            times['landscape']+=time.perf_counter()-t;counts['landscape_density_points']+=terrain['points']+terrain['sea_level_stride1_points']
            t=time.perf_counter();context=raster_intermediates(terrain) if opt.get('reuse_raster_intermediates',False) else None
            flat,build_mask,connected=flat_metrics(terrain,center,settings,context)
            ring_settings={**settings,'flat_radius_blocks':32} if kind=='ocean_island' else settings
            ring_flat,_,_=flat_metrics(terrain,center,ring_settings,context) if kind=='ocean_island' else (flat,None,None)
            ring=ring_metrics(terrain,center,ring_settings,connected,ring_flat['inner_height_median'])
            ring['ring_inner_radius_blocks']=ring_settings['flat_radius_blocks']
            if kind=='mountain_basin' and not(flat['flat_ground_preference_met'] and ring['dry_mountain_basin_preference_met']):
                # Refine a coarse anchor onto a nearby density-flat floor. Reuse
                # the raster already sampled; reject the whole nomination only
                # after testing the finite nearby floor candidates.
                x,z=xy_raster(terrain);nearby=np.hypot(x-center[0],z-center[1])<=256
                sites=build_centers(terrain,nearby,cfg['search']['center_axis_bounds_blocks'],limit=8,context=context)
                alternatives=[]
                for site in sites:
                    f,m,conn=flat_metrics(terrain,site['center'],settings,context)
                    if not f['flat_ground_preference_met']:continue
                    rr=ring_metrics(terrain,site['center'],settings,conn,f['inner_height_median'])
                    if rr['dry_mountain_basin_preference_met']:alternatives.append((site,f,rr))
                if alternatives:
                    site,_,_=min(alternatives,key=lambda v:(-v[2]['ring_dry_connected_fraction'],v[1]['inner_height_p90_minus_p10'],v[0]['center']))
                    times['scoring']+=time.perf_counter()-t;center=site['center']
                    t=time.perf_counter();terrain=raster(b,square(center,cfg['deployment']['overworld_side_blocks']),cfg['search']['refinement_spacing_blocks'])
                    times['landscape']+=time.perf_counter()-t;counts['landscape_density_points']+=terrain['points']+terrain['sea_level_stride1_points']
                    t=time.perf_counter();context=raster_intermediates(terrain) if opt.get('reuse_raster_intermediates',False) else None
                    flat,build_mask,connected=flat_metrics(terrain,center,settings,context)
                    ring=ring_metrics(terrain,center,settings,connected,flat['inner_height_median'])
                    ring['ring_inner_radius_blocks']=settings['flat_radius_blocks']
            if (kind,tuple(center)) in seen:
                times['scoring']+=time.perf_counter()-t;continue
            seen.add((kind,tuple(center)));structures,status=at_center(scans,center,cfg)
            if fast and status=='disputed_required_review':
                counts['early_structure_deferred']+=1
                near.append({'landscape_type':kind,'center':center,'reason':'deferred_exact_center_no_joint_required_prediction',
                             'stronghold_completeness':'unknown','isolation':'unknown'})
                times['scoring']+=time.perf_counter()-t;continue
            island=island_mask_on_raster(coast,terrain) if coast else build_mask
            if not island.any():
                near.append({'landscape_type':kind,'center':center,'reason':'no_sampled_build_ground'});times['scoring']+=time.perf_counter()-t;continue
            if kind=='mountain_basin':
                if not flat['flat_ground_preference_met'] or not ring['dry_mountain_basin_preference_met']:
                    near.append({'landscape_type':kind,'center':center,'reason':'density_not_dry_flat_mountain_basin',**flat,**ring});times['scoring']+=time.perf_counter()-t;continue
                c={'center':center,'bounds':[center[0]-settings['flat_radius_blocks'],center[1]-settings['flat_radius_blocks'],center[0]+settings['flat_radius_blocks'],center[1]+settings['flat_radius_blocks']],
                   'area':flat['flat_ground_area_blocks2'],'equivalent_diameter':2*math.sqrt(flat['flat_ground_area_blocks2']/math.pi),
                   'isolation':'not_required_dry_connected_basin','isolation_verified':False,'evidence':'finite_density_raster'}
            scores,metrics=landscape_scores(terrain,island,c,cfg)
            ocean_fraction=None;water_fraction=None
            if kind=='ocean_island':
                x,z=xy_raster(terrain);half=settings['ocean_window_side_blocks']//2
                window=(abs(x-center[0])<=half)&(abs(z-center[1])<=half)
                ocean_fraction=float(np.isin(terrain['biomes'][window],ocean_ids(terrain['biomes'])).mean())
                water_fraction=float((terrain['height'][window]<63).mean())
                if ocean_fraction<settings['minimum_ocean_fraction'] or water_fraction<settings['minimum_ocean_fraction']:
                    near.append({'landscape_type':kind,'center':center,'reason':'density_or_biomes_not_majority_ocean','ocean_fraction':ocean_fraction,'water_fraction':water_fraction});times['scoring']+=time.perf_counter()-t;continue
                # Nearby forests on the same ocean island count as supplies.
                # Build-area openness/size are distinct from whole island size.
                supply_mask=build_mask if build_mask.any() else island
                build_component={**c,'equivalent_diameter':2*math.sqrt(max(1,int(supply_mask.sum())*terrain['step']**2)/math.pi)}
                build_scores,supply=landscape_scores(terrain,supply_mask,build_component,cfg)
                for key in ('island_openness','wood'):scores[key]=build_scores[key]
                metrics['whole_island_equivalent_diameter']=c['equivalent_diameter']
                metrics['build_area_woodland_fraction']=supply['island_woodland_fraction']
                metrics['nearby_supply_woodland_fraction']=supply['surrounding_woodland_fraction']
                metrics['nearby_supply_forest_coordinates']=supply['forest_patch_coordinates']
                scores['water']=min(1,water_fraction/.75)
                scores['mountains']=ring['ring_fraction_bounds'][0] if not ring['ring_unknown_rays'] else None
            elif kind=='mountain_basin':
                scores['water']=min(flat['dry_connected_fraction'],flat['gentle_ground_fraction'])
                scores['mountains']=min(1,ring['ring_dry_connected_fraction']/settings['minimum_ring_fraction'])
                # These labels are explicit in the metrics/report; no water
                # enclosure or island-separation requirement applies to a basin.
                metrics['water_score_meaning']='dry_gentle_ground_fraction'
                metrics['largest_mountain_gap_degrees']=ring['largest_ring_gap_degrees']
            metrics.update(flat);metrics.update(ring);metrics['landscape_type']=kind
            metrics['ocean_biome_fraction']=ocean_fraction;metrics['ocean_water_fraction']=water_fraction
            metrics['deep_dark_hint']=hint
            ss,factors,sinterval=structure_scores(structures,cfg);scores.update(ss);score=weighted_score(scores,cfg,sinterval)
            times['scoring']+=time.perf_counter()-t
            remaining=['Matching-version Terrain shoreline and build-ground review','Required Fortress and Stronghold markers inside exact squares',
                       'Actual structure footprints and terrain remain unknown']
            if kind=='ocean_island':remaining+=['Whole ocean island separation','Wood supply on the island or nearby land']
            elif kind=='mountain_basin':remaining+=['Dry connected flat floor without an inner island or moat','Mountain ring appearance']
            else:remaining+=['Inner island separation','Water and surrounding mountains','External woodland abundance']
            candidate={'seed':str(seed),'index':index,'center':center,'nether_center':list(nether_center(center)),
                       'landscape_type':kind,'bounds':{'overworld':list(square(center,cfg['deployment']['overworld_side_blocks'])),'nether':list(square(nether_center(center),cfg['deployment']['nether_side_blocks']))},
                       'island':c,'metrics':metrics,'structures':structures,'structure_score_factors':factors,'score':score,
                       'nether_status':status,'required_structure_types':list(required_types(cfg)),
                       'selection_status':'unreviewed_local_prediction','chunkbase_checked':False,'actual_minecraft':None,
                       'remaining_review':remaining,'approximation_limits':LIMITS+['Deep Dark and ocean biome coverage are hints, not exact terrain proofs.'],
                       'spawn_proposal':{'x':center[0],'z':center[1],'y':None,'safety':'requires inspection'}}
            if diversity_enabled:
                from .biomes import candidate_diversity,add_bonus
                tb=time.perf_counter();div=candidate_diversity(b,terrain,center,cfg,coarse,grid)
                candidate['biome_diversity']=div;candidate['score']=add_bonus(score,div)
                counts['biome_query_points']=counts.get('biome_query_points',0)+div['additional_biome_query_points']
                times['biome_inventory']+=time.perf_counter()-tb
            if cache_root and opt.get('persist_report_terrain'):
                from .report_cache import save_terrain
                save_terrain(cache_root,seed,candidate['bounds']['overworld'],terrain,cfg)
            candidates.append(candidate)
        return finish(b)
