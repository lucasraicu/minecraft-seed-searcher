from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def render_probe(path,height,biomes,woodland,sparse,points,seed,center):
    extent=[int(points[:,0].min()),int(points[:,0].max()),int(points[:,1].max()),int(points[:,1].min())]
    fig,axes=plt.subplots(1,3,figsize=(16,5.5),constrained_layout=True)
    fig.suptitle(f"Seed {seed} — prediction diagnostics; actual game validation pending",fontsize=13)
    h=axes[0].imshow(height,extent=extent,cmap="terrain",vmin=40,vmax=180)
    axes[0].set_title("Raw density ground estimate (Y)")
    fig.colorbar(h,ax=axes[0],shrink=.75)
    if height.min()<63<height.max():
        x=np.linspace(extent[0],extent[1],height.shape[1]);z=np.linspace(extent[3],extent[2],height.shape[0])
        axes[0].contour(x,z,height,levels=[62.5],colors="navy",linewidths=.5)
    axes[1].imshow((height>=63).astype(int),extent=extent,cmap="Blues_r",vmin=0,vmax=1)
    axes[1].set_title("Land/water proxy at sea level\nNot proof of island separation")
    wood=np.where(height<63,0,np.where(woodland,3,np.where(sparse,2,1)))
    from matplotlib.colors import ListedColormap
    axes[2].imshow(wood,extent=extent,cmap=ListedColormap(["#3c7eaa","#ddd59c","#99b979","#286439"]),vmin=0,vmax=3)
    axes[2].set_title("Woodland potential\nBlue water · tan other · light sparse · dark woodland")
    for ax in axes:
        ax.scatter([center[0]],[center[1]],marker="+",color="red",s=65)
        ax.set_xlabel("X (blocks)");ax.set_ylabel("Z (blocks)")
    fig.savefig(Path(path),dpi=140)
    plt.close(fig)


def candidate_maps(out,c,cfg,run=None):
    from .backend import Backend,biome_name
    from .terrain import raster
    from .wood import wood_masks
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    import time
    started=time.perf_counter()
    opt=cfg.get('optimization',{});run=Path(run) if run else None
    cache_key=None
    if run and opt.get('reuse_unchanged_maps'):
        from .report_cache import map_identity,reuse_maps
        cache_key=map_identity(c,cfg)
        if reuse_maps(run/'map-cache',cache_key,out):return time.perf_counter()-started
    with Backend(c['seed']) as b:
        terrain=None
        if run and opt.get('persist_report_terrain'):
            from .report_cache import load_terrain,save_terrain
            terrain=load_terrain(run/'terrain-cache',c['seed'],c['bounds']['overworld'],cfg['search']['refinement_spacing_blocks'],cfg)
        if terrain is None:
            terrain=raster(b,c['bounds']['overworld'],cfg['search']['refinement_spacing_blocks'])
            if run and opt.get('persist_report_terrain'):save_terrain(run/'terrain-cache',c['seed'],c['bounds']['overworld'],terrain,cfg)
        height=terrain['height'];dense,sparse=wood_masks(terrain['biomes'])
        bounds=c['bounds']['overworld'];extent=[bounds[0],bounds[2],bounds[3],bounds[1]]
        fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
        fig.suptitle(f"Seed {c['seed']} · {c.get('landscape_type','enclosed_island')} · center {tuple(c['center'])}\nDensity/biome predictions; Chunkbase checked: {c['chunkbase_checked']}")
        axes[0].imshow(height,extent=extent,cmap='terrain',vmin=40,vmax=max(150,height.max()))
        axes[0].set_title('Ground Y · predicted coast at sea level')
        if height.min()<63<height.max():
            x=np.linspace(bounds[0],bounds[2],height.shape[1]);z=np.linspace(bounds[1],bounds[3],height.shape[0])
            axes[0].contour(x,z,height,levels=[62.5],colors='navy',linewidths=.5)
        wood=np.where(height<63,0,np.where(dense,3,np.where(sparse,2,1)))
        axes[1].imshow(wood,extent=extent,cmap=ListedColormap(['#3c7eaa','#ddd59c','#99b979','#286439']),vmin=0,vmax=3)
        axes[1].set_title('Woodland biome proxy · structures (predicted starts)')
        for typ,r in c['structures'].items():
            if r['dimension']!='overworld':continue
            if r['viable']:
                pts=np.array(r['viable']);axes[1].scatter(pts[:,0],pts[:,1],s=14,label=typ,alpha=.7)
        axes[1].legend(fontsize=6,loc='upper left',ncol=2)
        for ax in axes:
            ax.plot(*c['center'],marker='+',color='red',markersize=10)
            ax.add_patch(Rectangle((bounds[0],bounds[1]),bounds[2]-bounds[0],bounds[3]-bounds[1],fill=False,edgecolor='black',linewidth=2))
            for side,style in ((cfg['overworld']['report_core_side_blocks'],':'),(cfg['overworld']['report_primary_side_blocks'],'--')):
                ax.add_patch(Rectangle((c['center'][0]-side/2,c['center'][1]-side/2),side,side,fill=False,edgecolor='gray',linestyle=style))
            ax.set_xlabel('X (blocks)');ax.set_ylabel('Z (blocks)')
        fig.savefig(out/'overworld.png',dpi=120);plt.close(fig)
        nb=c['bounds']['nether'];step=16
        xx,zz=np.meshgrid(np.arange(nb[0],nb[2]+1,step),np.arange(nb[1],nb[3]+1,step))
        biomes=np.array([b.biome(int(x),33,int(z),-1) for x,z in zip(xx.ravel(),zz.ravel())]).reshape(xx.shape)
        values=sorted(np.unique(biomes));colors=['#85443c','#705951','#27a395','#791429','#6a6565']
        fig,ax=plt.subplots(figsize=(7,7),constrained_layout=True)
        mapped=np.zeros_like(biomes)
        for i,v in enumerate(values):mapped[biomes==v]=i
        ax.imshow(mapped,extent=[nb[0],nb[2],nb[3],nb[1]],cmap=ListedColormap(colors[:len(values)]),vmin=-.5,vmax=len(values)-.5)
        for typ,color in (('fortress','gold'),('bastion','white')):
            r=c['structures'][typ]
            for key,marker in (('viable','o'),('rejected_raw_review','x'),('chunkbase_markers','s')):
                if r[key]:
                    pts=np.array(r[key]);ax.scatter(pts[:,0],pts[:,1],c=color,marker=marker,s=75,label=f'{typ}: {key}')
        ax.plot(*c['nether_center'],marker='+',color='cyan',markersize=15)
        ax.add_patch(Rectangle((nb[0],nb[1]),nb[2]-nb[0],nb[3]-nb[1],fill=False,edgecolor='black',linewidth=2))
        ax.set_title(f"Nether · seed {c['seed']}\ncenter {tuple(c['nether_center'])}; {nb[2]-nb[0]} × {nb[3]-nb[1]} square\nStarts/markers do not establish accessible footprints")
        ax.set_xlabel('X (blocks)');ax.set_ylabel('Z (blocks)');ax.legend(fontsize=8)
        fig.savefig(out/'nether.png',dpi=120);plt.close(fig)
    if cache_key is not None:
        from .report_cache import save_maps
        save_maps(run/'map-cache',cache_key,out)
    return time.perf_counter()-started


def score_lists(candidates,limit):
    """Required-evidence eligibility and numeric-score certainty are separate.

    A website-supported candidate with uncertain optional points remains eligible,
    but its score interval belongs in the review list, not a known-total ranking.
    """
    from .scoring import distinct_rank,ranking_key,candidate_route
    lists=distinct_rank([c for c in candidates if c['score']['total'] is not None or candidate_route(c)!='ranked'],limit)
    uncertain=[c for c in candidates if candidate_route(c)=='review' or
               (candidate_route(c)=='ranked' and c['score']['total'] is None)]
    values=[];seen=set()
    for c in sorted(uncertain,key=ranking_key):
        if c['seed'] not in seen and len(values)<limit:values.append(c);seen.add(c['seed'])
    lists['review']=values
    return lists


def _export_search(view,results,cfg,config_hash,identity,run):
    import csv
    import json
    from .scoring import distinct_rank,ranking_key,candidate_route,candidate_eligible
    from .preflight import save_json
    from .review import apply_review,landscape_review_fields
    from .structures import required_types
    run=Path(run)
    view=Path(view)
    reviews=json.loads((run/'reviews.json').read_text()) if (run/'reviews.json').exists() else []
    candidates=[apply_review(c,reviews,cfg,config_hash) for r in results for c in r['candidates']]
    lists=score_lists(candidates,cfg['search']['report_top_distinct_seeds'])
    supported=[];seen=set()
    for c in sorted(candidates,key=ranking_key):
        if c['selection_status']=='chunkbase_supported_candidate' and c['seed'] not in seen and len(supported)<cfg['search']['report_top_distinct_seeds']:
            supported.append(c);seen.add(c['seed'])
    lists['chunkbase_supported']=supported
    if 'landscapes' in cfg:
        for kind in cfg['landscapes']['enabled']:
            category=score_lists([c for c in candidates if c.get('landscape_type')==kind],cfg['search']['report_top_distinct_seeds'])
            lists[kind]=category['ranked']
            lists[kind+'_review']=category['review']
    if 'landscapes' in cfg:lists['ranked']=[]
    summary={'completed_seeds':len(results),'scored_centers':len(candidates),
             'filter_policy':cfg.get('optimization',{}).get('stronghold_prefilter','review_all'),
             'structure_deferred_locations':sum(r['counts'].get('early_structure_deferred',0) for r in results),
             'seeds_with_predicted_both_nether':len({c['seed'] for c in candidates if all(c['structures'][t]['viable'] for t in ('fortress','bastion'))}),
             'scored_with_all_three_core':sum(all(c['structures'][t]['viable'] for t in ('trial_chamber','stronghold','mineshaft')) for c in candidates),
             'required_structure_types':list(required_types(cfg)),
             'scored_with_required_structures':sum(all(c['structures'][t]['viable'] for t in required_types(cfg)) for c in candidates),
             'list_counts':{k:len(v) for k,v in lists.items()},'unique_qualifying_seeds':len({c['seed'] for c in candidates if candidate_eligible(c)}),
             'category_memberships':{kind:len({c['seed'] for c in candidates if c.get('landscape_type')==kind and candidate_eligible(c)}) for kind in cfg.get('landscapes',{}).get('enabled',[])},'map_generation_seconds':0}
    if 'csv' in cfg['output']['summary_formats']:
        with (view/'candidates.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['seed','index','landscape_type','center_x','center_z','nether_x','nether_z','total','score_lower','score_upper','base_total','base_lower','base_upper','biome_bonus','score_maximum','biome_surface_spacing','required_structure_status','chunkbase_checked','actual_minecraft'])
            for c in candidates:
                s=c['score']
                w.writerow([c['seed'],c['index'],c.get('landscape_type','enclosed_island'),*c['center'],*c['nether_center'],s['total'],*s['interval'],s.get('base_total',s['total']),*s.get('base_interval',s['interval']),s.get('biome_bonus',0),s.get('maximum',100),s.get('biome_surface_spacing'),c['nether_status'],c['chunkbase_checked'],c['actual_minecraft']])
    for group,cs in lists.items():
        # Near misses remain fully exported in JSON/CSV; maps focus on the same
        # shortlist depth, including a representative rejected seed for review.
        for i,c in enumerate(cs):
            out=view/'shortlist'/group/f'{i+1:02d}_{c["seed"]}_{c["center"][0]}_{c["center"][1]}'
            out.mkdir(parents=True,exist_ok=True)
            save_json(out/'candidate.json',{'config_sha256':config_hash,'backend_identity':identity['backend'],**c})
            if 'overworld.png' in cfg['output']['candidate_files'] or 'nether.png' in cfg['output']['candidate_files']:
                summary['map_generation_seconds']+=candidate_maps(out,c,cfg,run)
            lines=[f"# Seed {c['seed']}",'',f"Overworld center {c['center']}, bounds {c['bounds']['overworld']}; Nether center {c['nether_center']}, bounds {c['bounds']['nether']}.",'',
                   f"Status: {c['selection_status']}. Chunkbase checked: {c['chunkbase_checked']}; actual Minecraft evidence: {c['actual_minecraft']}.",'',
                   f"Score: {c['score']['total']} / interval {c['score']['interval']}; maximum {c['score'].get('maximum',100)}. Base interval {c['score'].get('base_interval',c['score']['interval'])}; biome bonus {c['score'].get('biome_bonus',0)}. See candidate.json for metrics, sampling evidence and raw/viable/website statuses.",'',
                   'Review in [Chunkbase](https://www.chunkbase.com/apps/seed-map) with Bedrock 26.50–26.52 and Terrain enabled in the Overworld. Required structure markers must lie inside their reported squares. Starts and markers cannot establish whole-structure access.','']
            lines.extend('- [ ] '+v for v in c.get('remaining_review',cfg['verification']['final_required_checks']))
            lines.extend(['','Optional actual-game checks: '+', '.join(cfg['verification'].get('optional_actual_game_checks',[])), '',*c['approximation_limits']])
            (out/'inspection.md').write_text('\n'.join(lines)+'\n')
    save_json(view/'summary.json',summary)
    deferred=[{'seed':r['seed'],'index':r['index'],**v} for r in results for v in r['near_misses'] if v['reason'].startswith('deferred_') and 'required_prediction' in v['reason']]
    save_json(view/'stronghold-deferred.json',{'scope':'Fast prediction exclusions; not proven absent. Recover with review_all and a new run.',
                                              'records':deferred,'seeds':sorted({v['seed'] for v in deferred},key=int)})
    (view/'stronghold-deferred-seeds.txt').write_text(''.join(seed+'\n' for seed in sorted({v['seed'] for v in deferred},key=int)))
    if 'json' in cfg['output']['summary_formats']:
        save_json(view/'candidates.json',{'identity':identity,'summary':summary,'lists':lists,'all_centers':candidates,
                                         'rejections_and_deferred':[{'seed':r['seed'],**v} for r in results for v in r['near_misses']]})
    from .preflight import save_json
    (view/'shortlist').mkdir(exist_ok=True)
    with (view/'decisions.jsonl').open('w') as f:
        for r in results:
            for d in r.get('decisions',[]):f.write(json.dumps({'seed':r['seed'],'index':r['index'],**d},sort_keys=True)+'\n')
    return summary


def export_search(run,results,cfg,config_hash,identity):
    """Render a complete generation before atomically switching the active view."""
    import os,uuid,shutil
    run=Path(run);history=run/'report-history';history.mkdir(exist_ok=True)
    generation=history/('generation-'+uuid.uuid4().hex);generation.mkdir()
    try:
        summary=_export_search(generation,results,cfg,config_hash,identity,run)
    except Exception:
        shutil.rmtree(generation)
        raise
    # All public aliases point through this one atomic generation pointer.
    aliases=('shortlist','summary.json','candidates.json','candidates.csv','stronghold-deferred.json','stronghold-deferred-seeds.txt','decisions.jsonl')
    for name in aliases:
        p=run/name
        if p.exists() and not p.is_symlink():p.rename(history/('legacy-'+uuid.uuid4().hex+'-'+name))
        if not p.is_symlink():p.symlink_to('reports-current/'+name,target_is_directory=name=='shortlist')
    temporary=run/('.reports-'+uuid.uuid4().hex)
    temporary.symlink_to(generation.relative_to(run),target_is_directory=True)
    os.replace(temporary,run/'reports-current')
    return summary
