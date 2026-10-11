import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from seed_search.backend import Backend,STRUCTURES
from seed_search.cache import CachedBackend
from seed_search.config import load_config,validate_config
from seed_search.geometry import components
from seed_search.landscapes import flat_metrics,ring_metrics,round_robin,deep_dark_hint
from seed_search.structures import at_center,required_types
from seed_search.scoring import structure_scores,weighted_score
from seed_search.review import apply_review,validate_review
from seed_search.report_cache import save_terrain,load_terrain,map_identity,save_maps,reuse_maps
from seed_search.search import run_search
from seed_search.storage import Store


def test_new_required_policy_and_optional_bastion():
    cfg,_=load_config();assert set(required_types(cfg))=={'fortress','stronghold'}
    scans={t:{'raw':[],'viable':[]} for t in STRUCTURES}
    for t,p in [('stronghold',(200,-400)),('fortress',(120,32))]:scans[t]={'raw':[p],'viable':[p]}
    rows,status=at_center(scans,(0,0),cfg)
    assert status=='predicted_required_structures'
    assert rows['stronghold']['required'] and rows['stronghold']['dimension']=='overworld'
    assert not rows['bastion']['required'] and rows['bastion']['dimension']=='nether'
    score,_,_=structure_scores(rows,cfg)
    assert score['nether_proximity']==.8
    scans['bastion']={'raw':[(16,16)],'viable':[(16,16)]}
    more,status2=at_center(scans,(0,0),cfg);s2,_,_=structure_scores(more,cfg)
    assert status2==status and s2['nether_proximity']-score['nether_proximity']==pytest.approx(.2)
    scans['stronghold']={'raw':[],'viable':[]}
    uncertain,status=at_center(scans,(0,0),cfg)
    assert status=='disputed_required_review' and uncertain['stronghold']['completeness']=='unknown'
    scans['fortress']={'raw':[],'viable':[]}
    assert at_center(scans,(0,0),cfg)[1]=='missing_required_local_prediction'


def test_score_survives_sorted_checkpoint_configuration_with_exact_floats():
    cfg,_=load_config()
    restored=json.loads(json.dumps(cfg,sort_keys=True))
    scores=dict(zip(cfg['score_weights'],[.905082332647422,.6428571428571428,.9422222222222221,.26666666666666666,.8544776119402986,.517375818169566,.9538824796143124]))
    assert weighted_score(scores,cfg)==weighted_score(scores,restored)
    scores['wood']=None;scores['overworld_structures']=None
    assert weighted_score(scores,cfg,[.397,.597])==weighted_score(scores,restored,[.397,.597])


@pytest.mark.parametrize('seed',[12853964,-1,4294979641])
def test_exact_cache_seed_stride_negative_coordinate_and_eviction_semantics(seed):
    rng=np.random.default_rng(911);points=rng.integers(-2000,2000,(90,2),dtype=np.int32)
    points=np.r_[points,points[:10],np.array([[-256,-256],[0,0],[256,256]],np.int32)]
    with Backend(seed) as native,CachedBackend(seed,cache_mb=.0625) as cached:
        for stride in (8,1,4,8):
            expected=native.heights(points,stride);actual=cached.heights(points,stride)
            assert all(np.array_equal(a,b) for a,b in zip(actual,expected))
        assert np.array_equal(native.land(points),cached.land(points))
        stats=cached.cache_statistics();assert stats['evictions']>0 and stats['peak_bytes']<=stats['maximum_bytes']
        with pytest.raises(ValueError):cached.heights([[0.5,0]],8)
        with pytest.raises(ValueError):cached.land([[2**30,0]])
    with pytest.raises(RuntimeError,match='closed'):cached.heights(points,8)


def test_cache_hits_reordered_duplicates_and_returned_array_mutation():
    points=np.array([[-256,0],[-252,0],[0,0],[0,0]],np.int32)
    with CachedBackend(12853964) as b:
        h,biomes=b.heights(points,8);saved=h.copy();h[:]=999
        h2,b2=b.heights(points[::-1],8)
        assert np.array_equal(h2,saved[::-1]) and np.array_equal(b2,biomes[::-1])
        s=b.cache_statistics()['operations']['height_stride_8']
        assert s['computed_points']==3 and s['reused_points']==5


def ring_terrain(moat=False,steep=False,missing_quadrant=False):
    z,x=np.mgrid[-512:513:8,-512:513:8];r=np.hypot(x,z)
    h=np.full(x.shape,72,dtype=np.int32)
    ring=(r>=200)&(r<=280)
    if missing_quadrant:ring &= ~((x>0)&(z>0))
    h[ring]=160
    if moat:h[(r>=128)&(r<176)]=45
    if steep:h[r<100]=72+(x[r<100]+100)//2
    return {'height':h,'biomes':np.ones_like(h),'step':8,'bounds':[-512,-512,512,512]}


def test_dry_flat_mountain_basin_and_moat_inner_island_are_distinct():
    cfg,_=load_config();settings={**cfg['landscapes'],'ring_radius_blocks':400}
    dry=ring_terrain();flat,mask,connected=flat_metrics(dry,[0,0],settings)
    ring=ring_metrics(dry,[0,0],settings,connected,flat['inner_height_median'])
    assert flat['flat_ground_preference_met'] and ring['dry_mountain_basin_preference_met']
    assert ring['ring_fraction_bounds']==[1,1]
    moat=ring_terrain(moat=True);fm,_,cm=flat_metrics(moat,[0,0],settings)
    rm=ring_metrics(moat,[0,0],settings,cm,fm['inner_height_median'])
    assert fm['flat_ground_preference_met'] and rm['ring_preference_met']
    assert not rm['dry_mountain_basin_preference_met'] and rm['ring_dry_connected_fraction']==0
    steep=ring_terrain(steep=True);fs,_,_=flat_metrics(steep,[0,0],settings)
    assert not fs['flat_ground_preference_met']


def test_finite_ring_raster_does_not_certify_unseen_mountains():
    cfg,_=load_config();terrain=ring_terrain()
    flat,_,connected=flat_metrics(terrain,[400,400],cfg['landscapes'])
    ring=ring_metrics(terrain,[400,400],cfg['landscapes'],connected,flat['inner_height_median'])
    assert ring['ring_unknown_rays']>0


def test_round_robin_budget_retains_each_enabled_landscape_type():
    assert round_robin({'a':[1,2,3],'b':[4,5],'c':[6]},4)==[('a',1),('b',4),('c',6),('a',2)]


def test_review_requires_stronghold_and_does_not_require_bastion_or_mountains_for_ocean():
    cfg,h=load_config();scans={t:{'raw':[],'viable':[]} for t in STRUCTURES};rows,_=at_center(scans,(0,0),cfg)
    candidate={'seed':'12853964','center':[0,0],'landscape_type':'ocean_island','structures':rows,'actual_minecraft':None}
    half=cfg['deployment']['overworld_side_blocks']//2;nh=cfg['deployment']['nether_side_blocks']//2
    r={'source_kind':'fresh_chunkbase_browser_UI','source_url':'https://www.chunkbase.com/apps/seed-map',
       'version':'Bedrock 26.50 - 26.52','recorded_at':'test','browser_evidence':['synthetic-test-only'],
       'seed':'12853964','center':[0,0],'config_sha256':h,'landscape_type':'ocean_island',
       'terrain_enabled':True,'dimensions_checked':['overworld','nether'],
       'island_separated':True,'ocean_setting':True,'nearby_wood_abundant':True,'buildability':True,
       'mountain_setting':False,'structures':{'stronghold':[[half,half]],'fortress':[[nh,nh]],'bastion':[]}}
    supported=apply_review(candidate,[r],cfg,h)
    assert supported['selection_status']=='chunkbase_supported_candidate' and supported['actual_minecraft'] is None
    assert supported['structures']['stronghold']['confirmed_required_eligible']
    assert not supported['structures']['bastion']['confirmed_required_eligible']
    r['structures']['stronghold']=[[half+1,half]]
    assert apply_review(candidate,[r],cfg,h)['selection_status']=='chunkbase_checked_near_miss_or_unresolved'
    del r['structures']['stronghold']
    with pytest.raises(ValueError,match='stronghold'):validate_review(r,cfg)


def test_report_terrain_cache_checks_identity_hash_and_shape(tmp_path):
    cfg,_=load_config();bounds=[-16,-16,16,16]
    terrain={'height':np.arange(9,dtype=np.int32).reshape(3,3)+65,'biomes':np.ones((3,3),np.int32),
             'bounds':bounds,'step':16,'points':9,'sea_level_stride1_points':0}
    path=save_terrain(tmp_path,12853964,bounds,terrain,cfg)
    loaded=load_terrain(tmp_path,12853964,bounds,16,cfg)
    assert np.array_equal(loaded['height'],terrain['height'])
    assert load_terrain(tmp_path,-1,bounds,16,cfg) is None
    assert load_terrain(tmp_path,12853964,bounds,8,cfg) is None
    other=copy.deepcopy(cfg);other['landscapes']['maximum_flat_relief_blocks']=20
    assert load_terrain(tmp_path,12853964,bounds,16,other) is None
    path.write_bytes(b'damaged')
    assert load_terrain(tmp_path,12853964,bounds,16,cfg) is None


def test_changed_review_invalidates_map_reuse_and_corruption_is_rejected(tmp_path):
    cfg,_=load_config();c={'seed':'12853964','chunkbase_checked':False};out=tmp_path/'original';out.mkdir()
    for name in ('overworld.png','nether.png'):(out/name).write_bytes(b'test-map-data')
    key=map_identity(c,cfg);save_maps(tmp_path/'cache',key,out)
    other=tmp_path/'new';other.mkdir();assert reuse_maps(tmp_path/'cache',key,other)
    assert map_identity({**c,'chunkbase_checked':True},cfg)!=key
    (tmp_path/'cache'/key/'overworld.png').write_bytes(b'corruption')
    assert not reuse_maps(tmp_path/'cache',key,other)


def test_candidate_renderer_reuses_its_own_maps_without_queries_or_redraw(tmp_path,monkeypatch):
    from seed_search.reports import candidate_maps
    import matplotlib.pyplot as plt
    cfg,_=load_config()
    scans={t:{'raw':[],'viable':[]} for t in STRUCTURES}
    scans['fortress']={'raw':[(0,0)],'viable':[(0,0)]}
    scans['stronghold']={'raw':[(0,0)],'viable':[(0,0)]}
    rows,_=at_center(scans,(0,0),cfg)
    c={'seed':'12853964','center':[0,0],'nether_center':[0,0],
       'landscape_type':'ocean_island','chunkbase_checked':False,'structures':rows,
       'bounds':{'overworld':[-16,-16,16,16],'nether':[-16,-16,16,16]}}
    first=tmp_path/'first';second=tmp_path/'second';first.mkdir();second.mkdir()
    candidate_maps(first,c,cfg,tmp_path)
    def forbidden(*args,**kwargs):raise AssertionError('Unnecessary native query or redraw')
    monkeypatch.setattr(Backend,'heights',forbidden)
    monkeypatch.setattr(Backend,'biome',forbidden)
    monkeypatch.setattr(plt,'subplots',forbidden)
    candidate_maps(second,c,cfg,tmp_path)
    for name in ('overworld.png','nether.png'):
        assert (first/name).read_bytes()==(second/name).read_bytes()


@pytest.mark.parametrize('section,key,value',[
    ('landscapes','deep_dark_policy','hard_filter'),('landscapes','ring_radius_blocks',2000),
    ('landscapes','maximum_flat_slope',float('nan')),('optimization','cache_mb_per_worker',1000),
    ('nether','optional_bastion_proximity_weight',.9)])
def test_expansion_rejects_unverified_filters_and_unbounded_settings(section,key,value):
    cfg,_=load_config();cfg[section][key]=value
    with pytest.raises(ValueError):validate_config(cfg)


def test_expanded_real_checkpoint_resume_matches_worker_variation(tmp_path):
    cfg,_=load_config();cfg['search']['center_axis_bounds_blocks']=[-4000,-3000]
    # These negative-axis controls deliberately lack a local Stronghold. Keep
    # this test exercising real terrain/scoring, not just the fast deferral path.
    cfg['optimization']['stronghold_prefilter']='review_all'
    cfg['search']['maximum_refined_centers_per_seed']=1
    cfg['output']['candidate_files']=['candidate.json','inspection.md']
    h=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    run_search(cfg,h,tmp_path/'full',count=2,workers=1)
    run_search(cfg,h,tmp_path/'split',count=2,workers=2,stop_after=1)
    run_search(cfg,h,tmp_path/'split',count=2,workers=2,resume=True)
    def predictions(path):
        s=Store(path,resume=True);rows=s.results();s.close()
        return [{k:v for k,v in row.items() if k not in ('worker_pid','worker_peak_rss_mb','stage_seconds','total_seconds','native_work','worker_cpu_seconds')} for row in rows]
    assert predictions(tmp_path/'full')==predictions(tmp_path/'split')
    assert any(r['candidates'] for r in predictions(tmp_path/'full'))
    changed=copy.deepcopy(cfg);changed['nether']['optional_bastion_proximity_weight']=.1
    with pytest.raises(ValueError,match='Incompatible'):run_search(changed,h,tmp_path/'split',count=2,resume=True,dry_run=True)
