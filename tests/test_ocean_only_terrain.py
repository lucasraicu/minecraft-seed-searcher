"""Current optional terrain screening requires ocean evidence, not rivers."""
import numpy as np

from seed_search.backend import biome_catalog
from seed_search.realm import coastal
from seed_search.realm.config import marine_baseline_blueprint_config, river_blueprint_config, validate_config
from seed_search.realm.raster import Raster
from seed_search.realm.reports import _candidate_rescore


def test_ocean_only_geometry_passes_without_rivers_and_skips_corridor_search(monkeypatch):
    cfg=marine_baseline_blueprint_config()
    validate_config(cfg)
    bounds=(-1024,-1024,1024,1024)
    raster=Raster(bounds,16,np.ones((128,128))*85,metadata={'source':'prediction'})
    xx,_=raster.coordinates()
    water=xx < -512
    ids={row['name']:row['id'] for row in biome_catalog()}
    raster.water=water
    raster.height=np.where(water,50.,85.)
    raster.biomes=np.where(water,ids['deep_ocean'],ids['plains'])
    historical=coastal.evaluate_coastal(raster,(0,0),thresholds=river_blueprint_config()['terrain']['v1'],require_monument=False)
    assert any('river corridor' in reason for reason in historical['reasons'])
    def no_corridor_search(*args,**kwargs):
        raise AssertionError('River pathfinding must not run')
    monkeypatch.setattr(coastal,'_corridor_components',no_corridor_search)
    current=coastal.evaluate_coastal(raster,(0,0),thresholds=cfg['terrain']['v1'],require_monument=False)
    assert current['model_geometry_pass'],current['reasons']
    assert current['metrics']['ocean_edges']
    assert not any(key.startswith('river_') for key in current['metrics'])
    assert not any('river' in item for item in current['pending_work'])
    raster.biomes[:]=ids['plains']
    failed=coastal.evaluate_coastal(raster,(0,0),thresholds=cfg['terrain']['v1'],require_monument=False)
    assert not failed['model_geometry_pass']


def test_rescore_keeps_marine_baseline_bonus_and_ignores_river_evidence():
    def observation(count):
        return {'predicted_viable':[[i,0] for i in range(count)]}
    candidate={
        'contract':'master_seed_blueprint_v1',
        'screening_revision':marine_baseline_blueprint_config()['screening_revision'],
        'required_structures':{'monument':observation(2),'shipwreck':observation(7)},
        'required_nether_structures':{},'optional_structures':{},
        'baseline_score_complete':True,'pending_reasons':[],
        'marine_stage':{'status':'PREDICTED'},
        'terrain_status':{'source':{'kind':'actual_generation'}},
        'terrain_score_metrics':{'river_highway_connected':True},
        'ranking':{'coastal_footprint_bonus_status':'VERIFIED'},
    }
    result=_candidate_rescore(candidate,{},'test')
    assert result['baseline_score']==10  # Seven Shipwrecks: two extra above five.
    assert result['combined_score']==35  # Verified second monument still earns 25.
    assert 'river_highway' not in result['ranking']['bonuses']
