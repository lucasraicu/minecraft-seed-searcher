"""V2 ridge arcs must differ from a ring of substantial isolated hills."""
import numpy as np
import pytest
from seed_search.realm.raster import Raster
from seed_search.realm.terrain import evaluate_v2


def formation(kind, resolution=8):
    bounds=(-1024,-1024,1025,1025)
    xx,zz=np.meshgrid(np.arange(bounds[0],bounds[2],resolution),np.arange(bounds[1],bounds[3],resolution))
    radius=np.hypot(xx,zz)
    angle=np.degrees(np.arctan2(zz,xx))%360
    height=np.full(radius.shape,180.)
    if kind.startswith('hills'):
        count,hill_radius,center_radius={'hills8':(8,180,600),'hills6':(6,240,650),'hills4':(4,350,650)}[kind]
        ridge=np.zeros(radius.shape,bool)
        for bearing in np.arange(count)*2*np.pi/count:
            ridge |= np.hypot(xx-center_radius*np.cos(bearing),zz-center_radius*np.sin(bearing))<=hill_radius
    elif kind=='broad_spikes':
        ridge=np.zeros(radius.shape,bool)
        for bearing in np.arange(8)*2*np.pi/8:
            radial=xx*np.cos(bearing)+zz*np.sin(bearing)-600
            tangent=-xx*np.sin(bearing)+zz*np.cos(bearing)
            ridge |= (radial/240)**2+(tangent/180)**2<=1
    else:
        ridge=(radius>=500)&(radius<=620)
        if kind=='four_arcs':ridge &= (angle%90>=9)&(angle%90<=81)
        if kind=='two_arcs':ridge &= ((angle>=10)&(angle<=150))|((angle>=190)&(angle<=330))
        if kind=='one_pass':ridge &= angle>=90
        if kind=='jagged_arcs':
            ridge &= (angle%90>=9)&(angle%90<=81)
            height += np.where(radius<180,45*np.sin(xx/12)*np.cos(zz/12),0)
    height[ridge]=250
    return Raster(bounds,resolution,height,water=np.zeros(radius.shape,bool),metadata={'source':'prediction'})


@pytest.mark.parametrize('kind',['hills8','hills6','hills4','broad_spikes'])
def test_substantial_independent_hills_do_not_enclose_basin(kind):
    result=evaluate_v2(formation(kind),(0,0))
    assert not result['geometry_pass'],result['metrics']


@pytest.mark.parametrize('kind',['four_arcs','two_arcs','one_pass','jagged_arcs'])
def test_separate_enclosing_arcs_and_passes_remain_allowed(kind):
    result=evaluate_v2(formation(kind),(0,0))
    assert result['geometry_pass'],result['reasons']


def test_rejected_hill_runs_explain_continuity_failure_and_configurable_policy():
    raster=formation('hills4')
    rejected=evaluate_v2(raster,(0,0))
    assert rejected['metrics']['raw_ridge_rays']==20
    assert rejected['metrics']['ridge_rays']==0
    assert len(rejected['metrics']['rejected_support_components'])==4
    assert 'ridge arc continuity/support' in rejected['reasons']
    for run in rejected['metrics']['ridge_arc_runs']:
        assert run['rays']==5 and not run['qualified']
        assert run['radial_thickness']>32
        assert run['arc_aspect']<2
    relaxed=evaluate_v2(raster,(0,0),thresholds={'ridge_min_arc_aspect':1,'ridge_min_arc_rays':2})
    assert relaxed['geometry_pass']


def test_arc_runs_cross_bearing_zero_without_splitting():
    from seed_search.realm.terrain import _circular_component_runs
    assert _circular_component_runs([7,7,0,0,7,7])==[(7,[4,5,0,1])]
    assert _circular_component_runs([3]*32)==[(3,list(range(32)))]
    assert _circular_component_runs([0]*32)==[]


def test_old_v2_config_detector_merges_defaults_without_config_mutation(tmp_path):
    import yaml
    from seed_search.realm.config import default_config
    from seed_search.realm.cli import load
    cfg=default_config()
    for key in ('ridge_min_arc_rays','ridge_min_arc_aspect','enclosure_policy'):cfg['terrain']['v2'].pop(key)
    path=tmp_path/'old.yaml';path.write_text(yaml.safe_dump(cfg))
    loaded=load(path)
    assert loaded==cfg
    result=evaluate_v2(formation('four_arcs'),(0,0),thresholds=loaded['terrain']['v2'])
    assert result['metrics']['ridge_continuity_policy']['minimum_arc_rays']==4
    assert result['metrics']['ridge_continuity_policy']['minimum_arc_aspect']==2
    loaded['terrain']['v2']['unknown_geometry_policy']=1
    path.write_text(yaml.safe_dump(loaded))
    with pytest.raises(ValueError,match='Invalid configurable v2'):load(path)


def test_config_rejects_impossible_or_fractional_arc_ray_requirement():
    from seed_search.realm.config import default_config,validate_config
    for value in (33,3.5):
        cfg=default_config();cfg['terrain']['v2']['ridge_min_arc_rays']=value
        with pytest.raises(ValueError,match='ridge_min_arc_rays'):validate_config(cfg)


@pytest.mark.parametrize('resolution',[4,16,32])
def test_disconnected_broad_hills_and_jagged_arc_controls_across_sampling(resolution):
    assert not evaluate_v2(formation('hills4',resolution),(0,0))['geometry_pass']
    result=evaluate_v2(formation('jagged_arcs',resolution),(0,0))
    assert result['geometry_pass'],result['reasons']
    assert result['metrics']['interior_roughness']>10
    assert 'floor' not in result['metrics']['geometry_weights']


def test_validation_leaves_legacy_config_bytes_and_baseline_resume_identity_unchanged(tmp_path):
    import copy
    from seed_search.realm.config import default_config,validate_config
    from seed_search.realm.store import RealmStore,canonical,semantic_identity
    cfg=default_config()
    for key in ('ridge_min_arc_rays','ridge_min_arc_aspect','enclosure_policy'):cfg['terrain']['v2'].pop(key)
    before=canonical(cfg)
    identity={'config':copy.deepcopy(cfg),'count':1,'start_index':0}
    prior_semantic=semantic_identity(identity)
    with RealmStore(tmp_path,identity=identity):pass
    validate_config(cfg)
    assert canonical(cfg)==before
    assert semantic_identity({'config':cfg,'count':1,'start_index':0})==prior_semantic
    with RealmStore(tmp_path,identity={'config':cfg,'count':1,'start_index':0},resume=True) as resumed:
        assert canonical(resumed.identity['config'])==before
