import copy
import json
import hashlib
from pathlib import Path
import numpy as np
import pytest
from seed_search.config import load_config,validate_config,discovery_grid
from seed_search.geometry import components,angular_metrics
from seed_search.terrain import coast_component
from seed_search.structures import square,inside,nether_center,at_center
from seed_search.backend import STRUCTURES,Backend,structure_diagnostic
from seed_search.scoring import weighted_score,distinct_rank
from seed_search.regression import regression,correspond
from seed_search.storage import Store
from seed_search.search import run_search
from seed_search.readiness import check_readiness


def test_frozen_external_comparison(tmp_path):
    r=regression(tmp_path)
    assert r['passed']
    assert r['summary']['unique_type_correspondences']==874
    assert r['summary']['known_structure_disagreements']==6
    assert r['summary']['reused_starts']==0
    assert r['summary']['height_max_error']==5
    assert len({(v['seed'],v['type'],tuple(v['marker'])) for v in r['known_disagreements']})==6


def test_type_conventions_reject_swaps_and_multiple_correspondences():
    assert correspond('fortress',(11,11),[(8,8)])['status']=='unique'
    assert correspond('fortress',(11,11),[(11,11)])['status']=='missing'
    assert correspond('outpost',(16,16),[(8,8)])['status']=='unique'
    assert correspond('stronghold',(16,16),[(17,16)])['status']=='missing'
    assert correspond('bastion',(0,0),[(5,5),(10,10)])['status']=='ambiguous'


def test_exact_square_corners_and_negative_conversion():
    assert nether_center((-8,-16))==(-1,-2)
    with pytest.raises(ValueError):nether_center((-1,8))
    bounds=square((-1,-2),992)
    assert inside((495,494),bounds)
    assert not inside((496,494),bounds)
    assert np.hypot(496,496)>496  # corner eligibility is independent of radius


def test_disputed_raw_bastion_kept_without_confirming_required_eligibility():
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml")
    with Backend(12345) as b:
        raw=b.structures('bastion',(1208,408,1208,408),False)
        viable=b.structures('bastion',(1208,408,1208,408))
        diagnostic=structure_diagnostic(b,'bastion',1208,408)
    assert raw==[(1208,408)] and viable==[]
    assert diagnostic['sample_biome']=='basalt_deltas'
    assert diagnostic['start_biome']=='nether_wastes'
    scans={t:{'raw':[],'viable':[]} for t in STRUCTURES}
    scans['bastion']={'raw':raw,'viable':viable}
    scans['fortress']={'raw':[(1300,450)],'viable':[(1300,450)]}
    records,status=at_center(scans,(9664,3264),cfg)
    assert status=='disputed_required_review'
    assert records['bastion']['rejected_raw_review']==[[1208,408]]
    assert not records['bastion']['confirmed_required_eligible']
    assert not records['bastion']['chunkbase_checked']


def test_ancient_city_quart_diagnostic_preserves_disagreement():
    with Backend(-1) as b:d=structure_diagnostic(b,'ancient_city',-3048,3256)
    assert d['quart_sample']==[-762,-7,814]
    assert d['sample_biome']=='birch_forest' and d['start_biome']=='deep_dark'


def test_boundary_component_retained_as_unknown():
    land=np.zeros((20,20),bool);land[3:7,3:7]=True;land[:4,:4]=True
    labels,cs=components(land,0,0,8,[-1000,1000])
    assert len(cs)==1 and cs[0]['isolation']=='unknown'

class FakeTerrain:
    def __init__(self,bridge=False):self.bridge=bridge
    def heights(self,points,vertical_step=8):
        p=np.asarray(points);x,z=p.T
        land=(abs(x)<=24)&(abs(z)<=24)
        # One-block bridge between four-block coarse nodes, diagonal contacts.
        if self.bridge:land|=(z==1)&(x>=20)
        return np.where(land,70,50).astype(np.int32),np.ones(len(p),np.int32)


def test_one_block_coast_bridge_and_separated_component():
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");cfg['search']['center_axis_bounds_blocks']=[-128,128]
    coarse={'bounds':[-24,-24,24,24],'center':[0,0]}
    separated,err=coast_component(FakeTerrain(),coarse,cfg,(-200,-200,200,200))
    connected,err2=coast_component(FakeTerrain(True),coarse,cfg,(-200,-200,200,200))
    assert separated is not None and err is None
    assert separated['component']['center']==[0,0]
    assert separated['component']['isolation_verified'] is False
    assert connected is None and err2['isolation']=='unknown'


def test_water_rays_ignore_internal_pond_and_detect_mountains():
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");cfg['overworld']['surrounding_range_from_shore_blocks']=100
    z,x=np.mgrid[-200:201:4,-200:201:4];dist=np.hypot(x,z)
    island=(dist>=8)&(dist<=32)
    h=np.where(island,70,np.where(dist>=80,130,40))
    r=angular_metrics(h,island,(16,0),-200,-200,4,cfg)
    assert r['unknown_rays']==0
    assert r['enclosure_fraction_bounds']==[1,1]
    assert r['high_terrain_fraction_bounds']==[1,1]
    assert 35<=r['median_gap']<=60
    unknown=(x>0)&(dist>35)
    r2=angular_metrics(h,island,(16,0),-200,-200,4,cfg,unknown)
    assert r2['unknown_rays']>0


def test_unknown_weighted_scores_are_intervals():
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");scores={k:1.0 for k in cfg['score_weights']};scores['wood']=None
    r=weighted_score(scores,cfg)
    assert r['total'] is None and r['interval']==[80,100] and r['unknown_components']==['wood']


def test_edition_fixed_requirements_and_unsupported_method_rejected():
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml")
    for section,key,value in [('game','edition','java'),('deployment','nether_side_blocks',1000),('nether','bastion_required',False),('water','score_method','placeholder')]:
        c=copy.deepcopy(cfg);c[section][key]=value
        with pytest.raises(ValueError):validate_config(c)


def test_checkpoint_out_of_order_and_identity_rejection(tmp_path):
    identity={'schema':1,'config':{'workers':1}}
    s=Store(tmp_path,identity)
    s.save(4,-1,{'index':4,'seed':'-1'});s.save(2,2,{'index':2,'seed':'2'})
    assert s.completed()=={2,4};s.close()
    s=Store(tmp_path,identity,True);assert [v['index'] for v in s.results()]==[2,4];s.close()
    with pytest.raises(ValueError,match='Incompatible'):Store(tmp_path,{'schema':2},True)


def test_resume_equals_uninterrupted_real_bounded_pipeline(tmp_path):
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");cfg['search']['center_axis_bounds_blocks']=[-4000,-3000]
    cfg['search']['maximum_refined_centers_per_seed']=1
    cfg['output']['candidate_files']=['candidate.json','inspection.md']
    h=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    run_search(cfg,h,tmp_path/'full',count=3,workers=1)
    first=run_search(cfg,h,tmp_path/'split',count=3,workers=2,stop_after=1)
    assert first['completed_total']==1
    resumed=run_search(cfg,h,tmp_path/'split',count=3,workers=2,resume=True)
    assert resumed['completed_total']==3
    def prediction(run):
        store=Store(run,resume=True);rs=store.results();store.close()
        return [{k:v for k,v in r.items() if k not in ('worker_pid','worker_peak_rss_mb','total_seconds','stage_seconds')} for r in rs]
    assert prediction(tmp_path/'full')==prediction(tmp_path/'split')
    assert sum(len(r['candidates']) for r in prediction(tmp_path/'full'))>0
    changed=copy.deepcopy(cfg);changed['search']['run_key']='1'
    with pytest.raises(ValueError,match='Incompatible'):run_search(changed,h,tmp_path/'split',count=3,resume=True,dry_run=True)


def test_large_gate_cannot_be_enabled_by_flag_or_empty_record(tmp_path):
    cfg,h=load_config("runs/sweep-readiness/config/sweep.yaml")
    with pytest.raises(ValueError,match='requires --readiness'):run_search(cfg,h,tmp_path/'none',count=1001,dry_run=True)
    f=tmp_path/'ready.json';f.write_text('{"ready":true}')
    with pytest.raises(ValueError):check_readiness(f,cfg,h,1001)
    assert not (tmp_path/'none').exists()

@pytest.mark.parametrize('name',STRUCTURES)
def test_all_structure_adapters_region_and_exact_border_partition(name):
    # Split negative/positive coordinates directly at a chunk boundary. Exact
    # endpoints and upper seed bits must not disappear under regional scanning.
    with Backend(4294979641) as b:
        bounds=(-513,-481,511,543)
        full=set(b.structures(name,bounds,False))
        pieces=set(b.structures(name,(-513,-481,-1,543),False))|set(b.structures(name,(0,-481,511,543),False))
        assert full==pieces
        for x,z in sorted(full)[:3]:assert (x,z) in b.structures(name,(x,z,x,z),False)

@pytest.mark.parametrize('seed',[0,-1,4294979641,-2606959012126976886])
def test_exact_land_classifier_equals_stride_one_height_threshold(seed):
    rng=np.random.default_rng(712)
    points=rng.integers(-6000,6000,size=(300,2),dtype=np.int32)
    with Backend(seed) as b:
        h,_=b.heights(points,1)
        assert np.array_equal(b.land(points),h>=63)


def test_preliminary_bridge_remains_unknown_and_separated_refines():
    from seed_search.terrain import preliminary_component
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");cfg['search']['center_axis_bounds_blocks']=[-128,128]
    c={'bounds':[-24,-24,24,24],'center':[0,0]}
    separated,err,n=preliminary_component(FakeTerrain(),c,cfg,(-200,-200,200,200))
    assert separated is not None and err is None and n>0
    # A sub-grid bridge may pass the cheap stage, but the existing one-block
    # continuation regression proves it is caught by the next stage.


def test_fresh_external_separated_island_recovered_by_preliminary_topology():
    from seed_search.terrain import preliminary_component
    data=json.loads(Path('fixtures/bedrock-26.52/fresh-geometry.json').read_text())
    assert data['source_kind']=='fresh_chunkbase_browser_UI' and data['terrain_enabled']
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");grid=discovery_grid(cfg)
    bounds=(grid[0],grid[1],grid[0]+(grid[2]-1)*grid[4],grid[1]+(grid[3]-1)*grid[4])
    with Backend(data['seed']) as b:
        coarse=b.grid(*grid)
        _,cs=components(coarse['approx_height']>=63,*grid[:2],grid[4],cfg['search']['center_axis_bounds_blocks'])
        source=next(c for c in cs if c['center']==data['cases'][0]['anchor'])
        corrected,err,n=preliminary_component(b,source,cfg,bounds)
        assert corrected is not None and err is None
        assert corrected['bounds'][1]<source['bounds'][1]  # original coast patch missed northern land
        bridge_source=next(c for c in cs if c['center']==data['cases'][1]['anchor'])
        bridge,err,n=preliminary_component(b,bridge_source,cfg,bounds)
        assert bridge is None and err['isolation']=='unknown'
    assert all(Path(p).is_file() for case in data['cases'] for p in case['evidence'])


def review_record(seed='12345',center=None):
    cfg,h=load_config("runs/sweep-readiness/config/sweep.yaml")
    return {'source_kind':'fresh_chunkbase_browser_UI','source_url':'https://www.chunkbase.com/apps/seed-map',
            'version':'Bedrock 26.50 - 26.52','recorded_at':'2026-10-07','browser_evidence':['test-only-evidence'],
            'seed':seed,'center':center or [9664,3264],'terrain_enabled':True,'dimensions_checked':['overworld','nether'],
            'island_separated':True,'mountain_setting':True,'external_wood_abundant':True,'buildability':True,
            'config_sha256':h,'structures':{'fortress':[[1303,453]],'bastion':[[1185,376]]}}


def test_review_can_resolve_disputed_required_marker_without_game_confirmation():
    from seed_search.review import apply_review
    cfg,h=load_config("runs/sweep-readiness/config/sweep.yaml");scans={t:{'raw':[],'viable':[]} for t in STRUCTURES}
    scans['bastion']={'raw':[(1208,408)],'viable':[]}
    scans['fortress']={'raw':[(1300,450)],'viable':[(1300,450)]}
    rows,status=at_center(scans,(9664,3264),cfg)
    c={'seed':'12345','center':[9664,3264],'structures':rows,'actual_minecraft':None}
    result=apply_review(c,[review_record()],cfg,h)
    assert status=='disputed_required_review'
    assert result['selection_status']=='chunkbase_supported_candidate'
    assert result['structures']['bastion']['viable']==[]
    assert result['structures']['bastion']['rejected_raw_review']==[[1208,408]]
    assert result['structures']['bastion']['confirmed_required_eligible']
    assert result['actual_minecraft'] is None
    assert not c.get('chunkbase_checked')  # source prediction is not mutated


def test_website_markers_use_exact_border_and_unresolved_quality_stays_unresolved():
    from seed_search.review import apply_review,validate_review
    cfg,h=load_config("runs/sweep-readiness/config/sweep.yaml");scans={t:{'raw':[],'viable':[]} for t in STRUCTURES}
    rows,_=at_center(scans,(-8,-16),cfg)
    c={'seed':'12345','center':[-8,-16],'structures':rows,'actual_minecraft':None}
    r=review_record(center=[-8,-16]);r['structures']={'fortress':[[495,494]],'bastion':[[496,494]]}
    result=apply_review(c,[r],cfg,h)
    assert result['structures']['fortress']['confirmed_required_eligible']
    assert not result['structures']['bastion']['confirmed_required_eligible']
    assert result['selection_status']=='chunkbase_checked_near_miss_or_unresolved'
    r['structures']['bastion']=[[495,494]];r['buildability']=None
    assert apply_review(c,[r],cfg,h)['selection_status']=='chunkbase_checked_near_miss_or_unresolved'
    for key,value in [('version','Java 26.50'),('terrain_enabled',False),('dimensions_checked',['overworld'])]:
        invalid=copy.deepcopy(r);invalid[key]=value
        with pytest.raises(ValueError):validate_review(invalid)


def test_landscape_wood_denominator_excludes_water_and_island_supply():
    from seed_search.scoring import landscape_scores
    from seed_search.backend import biome_name
    # Obtain the actual biome IDs without substituting a bespoke woodland mask.
    from seed_search.wood import WOODLAND_NAMES
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");island=np.zeros((25,25),bool);island[11:14,11:14]=True
    outside=np.zeros_like(island);outside[2:6,2:6]=True;outside[18:22,18:22]=True
    h=np.where(island|outside,70,40);b=np.zeros(h.shape,dtype=int)
    forest=next(i for i in range(256) if biome_name(i)=="forest");b[island]=forest;b[2:6,2:6]=forest
    terrain={'height':h,'biomes':b,'step':16,'bounds':[-192,-192,192,192]}
    component={'center':[0,0],'bounds':[-16,-16,16,16],'equivalent_diameter':300}
    scores,m=landscape_scores(terrain,island,component,cfg)
    assert m['island_woodland_fraction']==1
    assert m['surrounding_woodland_fraction']==.5
    assert m['surrounding_land_area_blocks2']==32*256
    assert scores['island_openness']==0


def test_ranking_distinct_seeds_and_mountain_ties():
    def c(seed,center,gap):return {'seed':str(seed),'center':center,'nether_status':'predicted_both_required',
        'metrics':{'largest_mountain_gap_degrees':gap,'median_high_relative_height':100,'median_mountain_distance_from_shore':100},
        'score':{'total':80,'interval':[80,80]}}
    result=distinct_rank([c(2,[8,8],30),c(1,[0,0],40),c(2,[16,16],20),c(3,[0,0],40)],3)['ranked']
    assert [(v['seed'],v['center']) for v in result]==[('2',[16,16]),('1',[0,0]),('3',[0,0])]


def test_large_gate_rejects_forged_boolean_record_with_incomplete_artifact_manifest(tmp_path):
    from seed_search.readiness import CHECKS
    from seed_search.storage import backend_identity
    cfg,h=load_config("runs/sweep-readiness/config/sweep.yaml");artifact=tmp_path/'placeholder.log';artifact.write_text('not measured evidence')
    r={'ready':True,'config_sha256':h,'backend_identity':backend_identity(),
       'maximum_sweep_count':10000,'checks':{k:True for k in CHECKS},
       'artifacts':[{'path':str(artifact),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
    p=tmp_path/'forged.json';p.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='manifest is incomplete'):check_readiness(p,cfg,h,10000)
    artifact.write_text('changed after verification')
    with pytest.raises(ValueError,match='missing or changed'):check_readiness(p,cfg,h,10000)
    with pytest.raises(ValueError,match='budget'):check_readiness(p,cfg,h,10001)


def test_missing_stronghold_and_rejected_ancient_city_remain_preference_intervals():
    from seed_search.scoring import structure_scores
    cfg,_=load_config("runs/sweep-readiness/config/sweep.yaml");scans={t:{'raw':[],'viable':[]} for t in STRUCTURES}
    scans['ancient_city']={'raw':[(64,64)],'viable':[]}
    scans['fortress']={'raw':[(8,8)],'viable':[(8,8)]}
    scans['bastion']={'raw':[(72,72)],'viable':[(72,72)]}
    rows,status=at_center(scans,(0,0),cfg)
    scores,factors,interval=structure_scores(rows,cfg)
    assert status=='predicted_both_required'
    assert factors['stronghold'] is None and factors['ancient_city'] is None
    assert scores['overworld_structures'] is None and interval==[0,.4]
    assert rows['stronghold']['completeness']=='unknown'
