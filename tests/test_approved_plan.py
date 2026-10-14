import copy
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pytest
from seed_search.backend import Backend,RAW_MT_TYPES,STRUCTURES,raw_layout,biome_name
from seed_search.biomes import inventory,FAMILIES,add_bonus,terrain_inventory
from seed_search.cache import CachedBackend
from seed_search.config import load_config,discovery_grid,validate_config
from seed_search.landscapes import basin_necessary_bound,flat_metrics,build_centers,ring_metrics,raster_intermediates,xy_raster
from seed_search.scoring import candidate_route
from seed_search.staged import permute32,compose_seed,prepare,sibling_job
from seed_search.storage import Store
from seed_search.structures import envelope_bounds,square,at_center,structure_centers
from seed_search.search import run_search
from seed_search.terrain import raster

def test_new_geometry_shared_exact_corners_and_joint_centers():
    cfg,_=load_config();assert cfg['schema_version']==4
    assert discovery_grid(cfg)==(-6208,-6208,195,195,64)
    assert envelope_bounds(cfg)==((-6152,-6152,6152,6152),(-1089,-1089,1089,1089))
    scans={name:{'raw':[],'viable':[]} for name in STRUCTURES}
    for name,p in (('stronghold',(-1160,1176)),('fortress',(-465,467))):scans[name]={'raw':[p],'viable':[p]}
    rows,status=at_center(scans,(-8,24),cfg)
    assert status=='predicted_required_structures'
    assert rows['stronghold']['bounds']==[-1160,-1128,1144,1176]
    assert rows['fortress']['bounds']==[-465,-461,463,467]
    scans['stronghold']['raw']=[(-1161,1176)];scans['stronghold']['viable']=scans['stronghold']['raw']
    assert at_center(scans,(-8,24),cfg)[1]=='disputed_required_review'
    assert structure_centers(scans,cfg)
    for c in structure_centers(scans,cfg):assert at_center(scans,c,cfg)[1]=='predicted_required_structures'

def test_mt_cold_warm_threads_and_signed_high32_are_order_independent():
    code="from seed_search.backend import Backend; import json; a=[]\nfor s in [-1,-1,0,-1,4294967295,-1]:\n with Backend(s) as b:a.append(b.structures('mineshaft',(-1024,-1024,1024,1024)))\nprint(json.dumps(a))"
    rows=json.loads(subprocess.check_output([sys.executable,'-c',code],text=True))
    assert len(rows[0])==44 and rows[0]==rows[1]==rows[3]==rows[5]
    def scan(_):
        with Backend(-1) as b:return b.structures('mineshaft',(-1024,-1024,1024,1024))
    with ThreadPoolExecutor(3) as pool:assert all(r==[tuple(p) for p in rows[0]] for r in pool.map(scan,range(6)))

@pytest.mark.parametrize('low',[0,9,12345,2**32-1])
def test_all_eight_generator_free_raw_families_match_full_seed(low):
    bounds=(-920,-1100,1000,870)
    for name in sorted(RAW_MT_TYPES):
        expected=raw_layout(low,name,bounds)
        for high in (0,1,2**32-1):
            with Backend(compose_seed(low,high)) as b:assert expected==b.structures(name,bounds,False)
    for name in ('stronghold','mineshaft','trial_chamber'):
        with pytest.raises(ValueError):raw_layout(low,name,bounds)

def test_quart_land_parity_with_unaligned_negative_points_and_mutation():
    points=np.array([[x,z] for x in range(-9,10) for z in range(-5,6)],np.int32)
    points=np.r_[points,points[::-1],points[:5]]
    with Backend(9) as reference,CachedBackend(9) as cached:
        expected=reference.land(points);actual=cached.land(points)
        assert np.array_equal(expected,actual)
        actual[:]=False
        assert np.array_equal(cached.land(points[::-1]),expected[::-1])
        stats=cached.cache_statistics()['operations']['exact_land']
        assert stats['computed_points']==len(np.unique(points//4,axis=0))
        assert stats['requested_points']==2*len(points)
        assert all(np.array_equal(a,b) for a,b in zip(reference.heights(points),cached.heights(points)))
    with pytest.raises(RuntimeError):cached.land(points)

def test_every_supported_biome_maps_except_end_and_void():
    known={biome_name(i) for i in range(256) if not biome_name(i).startswith('unknown')}
    assert known-set(FAMILIES)=={'the_end','the_void','small_end_islands','end_midlands','end_highlands','end_barrens','dappled_forest','sulfur_caves','ice_caves'}

@pytest.mark.parametrize('seed',[-1,0,12345,4294979641])
def test_batched_biomes_match_scalar_at_surface_cave_and_nether_layers(seed):
    rng=np.random.default_rng(128);points=rng.integers(-1024,1025,(48,3),dtype=np.int32)
    points[:,1]=np.resize(np.array([-51,-32,0,33,63,96,160,319],np.int32),len(points))
    points=np.r_[points,points[:4],points[::-1]]
    with Backend(seed) as b:
        for dimension in (0,-1):
            expected=np.array([b.biome(int(x),int(y),int(z),dimension) for x,y,z in points])
            assert np.array_equal(b.biome_points(points,dimension),expected)
        assert b.biome_points(np.empty((0,3),np.int32)).size==0
    with pytest.raises(RuntimeError):b.biome_points(points)

def test_diversity_border_clip_variant_dedup_saturation_and_preserved_base():
    cfg,_=load_config();p=cfg['biome_diversity'];bounds=(-128,-128,128,128)
    # Both spruce variants share one family. Duplicate and outside sample ignored.
    ids=[5,30,5,30,5,21,21];pts=[[-64,0],[0,0],[64,0],[0,64],[0,64],[999,0],[-64,-64]]
    a=inventory(ids,pts,64,bounds,p,'surface_sampled')
    assert a['unique_samples']==5 and a['family_count']==2
    assert a['families']['spruce']['extent_factor']==1
    assert a['families']['jungle']['extent_factor']==.25
    b=inventory([5]*4,pts[:4],64,bounds,p,'surface_sampled')
    assert a['weighted_utility']>b['weighted_utility']
    base={'total':20.,'interval':[20.,20.],'components':{},'unknown_components':[]}
    s=add_bonus(base,{'bonus':2.,'grade':'surface_sampled'},30)
    assert base['total']==20 and s['total']==22 and s['maximum']==35 and s['base_interval']==[20,20]
    t={'height':np.ones((2,2)),'biomes':np.array([[5,30],[5,30]]),'bounds':[-64,-64,0,0],'step':64}
    assert terrain_inventory(t,bounds,p)['family_count']==1

def test_review_routing_cannot_be_rescued_by_score_or_optional_structures():
    c={'score':{'total':105},'nether_status':'predicted_required_structures','landscape_type':'structures_only',
       'chunkbase_checked':True,'selection_status':'chunkbase_checked_near_miss_or_unresolved','chunkbase_review':{}}
    assert candidate_route(c)=='review'
    c.update(landscape_type='ocean_island',chunkbase_review={'ocean_setting':False})
    assert candidate_route(c)=='near_misses'

def test_supported_unknown_optional_score_keeps_eligibility_and_interval_list():
    from seed_search.reports import score_lists
    from seed_search.scoring import candidate_eligible
    def candidate(seed,total,interval):
        return {'seed':str(seed),'center':[0,0],'landscape_type':'structures_only','metrics':{},
                'score':{'total':total,'interval':interval},'nether_status':'predicted_required_structures',
                'chunkbase_checked':True,'selection_status':'chunkbase_supported_candidate'}
    uncertain=candidate(1,None,[29,35]);known=candidate(2,28,[28,28])
    groups=score_lists([uncertain,known],1)
    assert candidate_eligible(uncertain) and groups['ranked']==[known] and groups['review']==[uncertain]

def test_bijective_32bit_schedule_sign_and_budgets(tmp_path):
    assert len({permute32(i,2**32-1) for i in range(10000)})==10000
    assert compose_seed(2**32-1,2**32-1)==-1
    cfg,h=load_config();cfg['search']['mode']='lower32_staged';cfg['search']['lower_bit_optimization_enabled']=True
    cfg['search']['staged'].update(raw_layout_count=8,retained_layouts=4,exploration_layouts=1,siblings_per_layout=3,maximum_full64_evaluations=12)
    validate_config(cfg);s=Store(tmp_path/'state',{'test':True})
    state=prepare(s,cfg,0,12)
    assert state['cursor']==8 and len(state['selected'])==4
    seeds=[sibling_job(i,0,cfg,state)[0] for i in range(12)]
    assert len(set(seeds))==12
    assert len({v & 0xffffffff for v in seeds})==4
    assert prepare(s,cfg,0,12)==json.loads(json.dumps(state))
    s.close()
    with pytest.raises(ValueError,match='budget'):run_search(cfg,h,tmp_path/'bad',count=13,dry_run=True)
    cfg['search']['staged']['raw_layout_count']=10001
    with pytest.raises(ValueError,match='readiness'):run_search(cfg,h,tmp_path/'bad',count=1,dry_run=True)
    assert not (tmp_path/'bad').exists()

@pytest.mark.parametrize('step',[4,8,16,32,64])
def test_basin_local_bound_uses_reference_lattice_even_for_historical_phase(step):
    from test_filter_optimization import Ground
    cfg,_=load_config();cfg['deployment']['overworld_side_blocks']=3008;cfg['search']['refinement_spacing_blocks']=step
    cfg['landscapes']['ring_radius_blocks']=500
    center=(-8,24);backend=Ground('recenter');full=raster(backend,square(center,3008),step);ctx=raster_intermediates(full)
    x,z=xy_raster(full);centers=[center]+[v['center'] for v in build_centers(full,np.hypot(x-center[0],z-center[1])<=256,[-5000,5000],8,ctx)]
    passes=[]
    for c in centers:
        f,_,conn=flat_metrics(full,c,cfg['landscapes'],ctx);r=ring_metrics(full,c,cfg['landscapes'],conn,f['inner_height_median'])
        passes.append(f['flat_ground_preference_met'] and r['dry_mountain_basin_preference_met'])
    if any(passes):assert not basin_necessary_bound(backend,center,cfg)['impossible']

def test_staged_real_resume_and_worker_variation(tmp_path):
    cfg,_=load_config();cfg['search']['mode']='lower32_staged';cfg['search']['lower_bit_optimization_enabled']=True
    cfg['search']['staged'].update(raw_layout_count=4,retained_layouts=2,exploration_layouts=1,siblings_per_layout=2,maximum_full64_evaluations=4)
    cfg['landscapes']['enabled']=['structures_only'];cfg['search']['maximum_structure_centers_per_seed']=1
    cfg['output']['candidate_files']=['candidate.json','inspection.md'];h=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    run_search(cfg,h,tmp_path/'full',count=4,workers=1)
    run_search(cfg,h,tmp_path/'split',count=4,workers=2,stop_after=1)
    run_search(cfg,h,tmp_path/'split',count=4,workers=2,resume=True)
    def payload(path):
        s=Store(path,resume=True);rows=s.results();s.close()
        return [{k:v for k,v in r.items() if k not in ('worker_pid','worker_peak_rss_mb','stage_seconds','total_seconds','native_work','worker_cpu_seconds')} for r in rows]
    assert payload(tmp_path/'full')==payload(tmp_path/'split')
    candidates=[c for r in payload(tmp_path/'full') for c in r['candidates']]
    assert candidates and all(c['terrain_status']=='not_required' and c['island'] is None and c['score']['maximum']==35 for c in candidates)

def test_atomic_reports_preserve_last_generation_after_render_failure(tmp_path,monkeypatch):
    from seed_search.reports import export_search
    cfg,h=load_config();run=tmp_path/'run';run.mkdir()
    export_search(run,[],cfg,h,{'backend':{}});before=(run/'reports-current').readlink();raw=(run/'summary.json').read_bytes()
    def fail(*args,**kwargs):raise RuntimeError('render failure')
    monkeypatch.setattr('seed_search.reports._export_search',fail)
    with pytest.raises(RuntimeError):export_search(run,[],cfg,h,{'backend':{}})
    assert (run/'reports-current').readlink()==before and (run/'summary.json').read_bytes()==raw

def test_actual_audit_basin_lattice_counterexample_is_fixed():
    class Ground:
        def heights(self,points,vertical_step=8):
            x,z=np.asarray(points).T;r=np.hypot(x,z)
            h=np.where(x%64==32,72,50).astype(np.int32)
            h[(x%64==32)&(r>=300)&(r<=500)]=160
            return h,np.ones(len(points),np.int32)
    cfg,_=load_config();cfg['search']['refinement_spacing_blocks']=64
    cfg['deployment']['overworld_side_blocks']=3008
    t=raster(Ground(),(-1504,-1504,1504,1504),64)
    f,_,conn=flat_metrics(t,[0,0],cfg['landscapes']);r=ring_metrics(t,[0,0],cfg['landscapes'],conn,f['inner_height_median'])
    assert f['flat_ground_preference_met'] and r['dry_mountain_basin_preference_met']
    assert not basin_necessary_bound(Ground(),[0,0],cfg)['impossible']

def test_raw_phase_interruption_resumes_same_selection(tmp_path,monkeypatch):
    import seed_search.staged as module
    cfg,_=load_config();cfg['search']['staged'].update(raw_layout_count=110,retained_layouts=4,exploration_layouts=1,siblings_per_layout=3,maximum_full64_evaluations=12)
    def fake(low,cfg):return {'low32':low,'raw_score':low/2**32,'raw_counts':{}}
    monkeypatch.setattr(module,'evaluate_layout',fake)
    full=Store(tmp_path/'full',{'test':True});expected=prepare(full,cfg,0,12);full.close()
    calls=0
    def interrupted(low,cfg):
        nonlocal calls
        calls+=1
        if calls==104:raise RuntimeError('interrupted')
        return fake(low,cfg)
    partial=Store(tmp_path/'split',{'test':True});monkeypatch.setattr(module,'evaluate_layout',interrupted)
    with pytest.raises(RuntimeError):prepare(partial,cfg,0,12)
    assert partial.get_state('staged')['cursor']==100;partial.close()
    partial=Store(tmp_path/'split',{'test':True},resume=True);monkeypatch.setattr(module,'evaluate_layout',fake)
    actual=prepare(partial,cfg,0,12);partial.close()
    assert actual['selected']==expected['selected'] and actual['eligible_raw']==expected['eligible_raw']

def test_shadow_island_domain_includes_fallback_centers():
    from seed_search.terrain import island_necessary_bound
    cfg,_=load_config();scans={'stronghold':{'raw':[(1200,0)]},'fortress':{'raw':[(0,0)]}}
    component={'center':[0,0],'bounds':[-200,-200,200,200]}
    bound=island_necessary_bound(component,cfg,(-6208,-6208,6208,6208),scans)
    assert not bound['terrain_impossible'] and not bound['predicted_required_window_impossible']
    scans['stronghold']['raw']=[]
    assert island_necessary_bound(component,cfg,(-6208,-6208,6208,6208),scans)['predicted_required_window_impossible']
    assert cfg['optimization']['island_bound_policy']=='shadow'

def test_unknown_biome_evidence_preserves_interval_and_eligibility():
    from seed_search.scoring import candidate_eligible
    base={'total':20,'interval':[20,20],'components':{},'unknown_components':[]}
    s=add_bonus(base,{'bonus':1,'grade':'coarse_fixed_y','bonus_maximum':5},30)
    assert s['total'] is None and s['interval']==[21,25]
    c={'nether_status':'predicted_required_structures','score':s}
    assert candidate_eligible(c) and candidate_route(c)=='review'

def test_schema4_readiness_requires_measured_comparison_records(tmp_path,monkeypatch):
    import seed_search.readiness as module
    identity={'measured':'current'};monkeypatch.setattr(module,'backend_identity',lambda:identity)
    arm=lambda key,mode:{'run_key':key,'search_mode':mode,'full64_count':256,'backend_identity':identity}
    data={
        'quart_parity':{'equal':True,'seeds_per_trial':20,'trials':[{'equal':True,'original':{'backend_identity':identity},'quart':{'backend_identity':identity}} for _ in range(3)]},
        'worker_resume':{'equal':True,'worker_counts':[1,8,12],'full64_count':16,'backend_identity':identity},
        'raw_resume':{'exit_code':0,'command':'pytest raw interruption control','backend_identity':identity},
        'recovery':{'complete':True,'declared_seeds':['-1','0','9','4294979641'],'summary':{'backend_identity':identity}},
        'mode_comparison':{'complete':True,'run_keys':['0','1'],'arms':[arm(k,m) for k in ('0','1') for m in ('full_64_bit_reference','lower32_staged')]},
    }
    def write():
        for k,v in data.items():(tmp_path/f'{k}.json').write_text(json.dumps(v))
    write();record={'passed':True,'backend_identity':identity,'evidence':{k:str(tmp_path/f'{k}.json') for k in data}}
    assert module.implementation_checks(record)
    data['mode_comparison']['arms'][0]['full64_count']=255;write()
    assert not module.implementation_checks(record)
    data['mode_comparison']['arms'][0]['full64_count']=256
    data['mode_comparison']['arms'][0]['run_key']='1';write()
    assert not module.implementation_checks(record)
    data['mode_comparison']['arms'][0]['run_key']='0'
    data['quart_parity']['trials'][2]['equal']=False;write()
    assert not module.implementation_checks(record)

def test_readiness_publication_preserves_prior_record_on_validation_failure(tmp_path,monkeypatch):
    import importlib.util
    from seed_search.storage import ROOT
    spec=importlib.util.spec_from_file_location('readiness_assembler',ROOT/'scripts/assemble_sweep_readiness.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def save(name,value):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return str(p)
    log=save('log.txt',{})
    license_file=save('current-license.json',{});dependencies=save('current-dependencies.json',{})
    verification=save('verification.json',{'native_build':{'log':log},'dependencies':{'log':log},'tests':{'log':log},
        'installed_license_evidence':license_file,'dependency_versions_evidence':dependencies})
    reviews=save('reviews.json',[]);geometry=save('geometry.json',{'cases':[]})
    command=save('command.json',{'maximum_count':2,'sweep_command':'bounded search','resume_command':'resume',
        'tiny_equivalent_evidence':log,'large_gate_rejection_evidence':log,'resume_evidence':log})
    evidence=save('evidence.json',{'verification':verification,'fresh_reviews':reviews,'fresh_geometry':geometry,
        'command_validation':command,'pilot':str(tmp_path/'pilot')})
    save('vendor/backend.json',{'files':{}});config=save('config.yaml',{})
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'load_config',lambda _:({'search':{'mode':'full_64_bit_reference'}},'hash'))
    monkeypatch.setattr(module,'derive_checks',lambda *args:{'native_build':True})
    monkeypatch.setattr(module,'required_sources',lambda:[])
    monkeypatch.setattr(module,'backend_identity',lambda:{})
    destination=tmp_path/'readiness.json';destination.write_text('prior validated record')
    def fail(*args):raise ValueError('injected validation failure')
    monkeypatch.setattr(module,'check_readiness',fail)
    with pytest.raises(ValueError,match='injected validation failure'):
        module.assemble(config,evidence,destination,2)
    assert destination.read_text()=='prior validated record'
    monkeypatch.setattr(module,'check_readiness',lambda *args:{})
    record=module.assemble(config,evidence,destination,2)
    assert json.loads(destination.read_text())==record
    paths={a['path'] for a in record['artifacts']}
    assert license_file in paths and dependencies in paths
