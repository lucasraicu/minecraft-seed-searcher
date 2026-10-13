"""Coastal geometry is a fixed-box model, with honest incomplete actual evidence."""
import numpy as np
import pytest

from seed_search.realm.coastal import COASTAL, evaluate_coastal
from seed_search.realm.raster import Raster
from seed_search.realm.terrain import evaluate_v1, run_terrain

BOUNDS = (-768, -768, 768, 768)
POLICY = {'mode':'coastal_continent', 'coastal_continent':dict(COASTAL)}


def coast(resolution=16, *, bounds=BOUNDS, actual=False):
    xx, zz = np.meshgrid(np.arange(bounds[0], bounds[2], resolution), np.arange(bounds[1], bounds[3], resolution))
    water = xx < -464
    return Raster(bounds, resolution, np.where(water,50.,85.), water=water,
                  biomes=np.where(water,0,1), natural_ground=np.ones(water.shape,bool),
                  metadata={'source':'actual' if actual else 'prediction',
                            'water_evidence':'actual_blocks', 'natural_ground_evidence':'verified_natural'})


def evaluate(raster, **kwargs):
    return evaluate_coastal(raster, monuments=[[-640, 0]], **kwargs)


@pytest.mark.parametrize('resolution', [4, 16, 64, 70, 128])
def test_coastal_fraction_clips_cells_and_uses_one_mainland(resolution):
    raster = coast(resolution)
    result = evaluate(raster)
    assert result['geometry_pass'], result['reasons']
    assert .75 <= result['metrics']['mainland_fraction'] <= .85
    assert result['metrics']['known_fraction'] == 1
    assert result['border_fit']['state'] == 'within'
    assert result['border_fit']['footprint'] == list(BOUNDS)
    assert result['qualification'] == 'PREDICTED'
    assert not result['metrics']['monument_actual_footprint_verified']
    assert result['verified_score'] is None


def test_dispatch_ignores_arbitrary_island_center_and_requires_stronghold_box():
    result = evaluate_v1(coast(), (600,600), BOUNDS, (0,0), thresholds=POLICY, monuments=[[-640,0]])
    assert result['center'] == [0,0]
    assert result['mode'] == 'coastal_continent'
    with pytest.raises(ValueError, match='exact Stronghold'):
        evaluate_coastal(coast(), bounds=(-800,-800,800,800))


def test_fraction_clips_halo_to_border_and_nonzero_stronghold():
    raster = coast(100, bounds=(-1000,-1000,1000,1000))
    result = evaluate(raster)
    # Cells are represented by their sampled state, clipped to the exact box.
    assert result['metrics']['land_fraction'] == pytest.approx((768+400)/1536)
    assert result['metrics']['known_fraction'] == 1
    shifted = coast(); shifted.bounds = (BOUNDS[0]+11, BOUNDS[1]-7, BOUNDS[2]+11, BOUNDS[3]-7)
    result = evaluate_coastal(shifted, stronghold=(11,-7), monuments=[[-629,-7]])
    assert result['center'] == [11,-7]


def test_disconnected_total_land_does_not_substitute_for_single_mainland():
    raster = coast()
    raster.water[47:49,:] = True
    raster.height[47:49,:] = 50
    raster.biomes[47:49,:] = 0
    result = evaluate(raster)
    assert .75 <= result['metrics']['land_fraction'] <= .85
    assert result['metrics']['mainland_fraction'] < .5
    assert not result['geometry_pass']


def test_unknown_cells_never_become_land_or_complete_geometry():
    raster = coast(); raster.known[20,60] = False
    result = evaluate(raster)
    assert result['qualification'] == 'PENDING'
    assert not result['geometry_pass']
    assert result['metrics']['unknown_fraction'] > 0
    assert not result['border_fit']['complete']


def test_river_or_inland_water_cannot_claim_ocean_edge():
    raster = coast(); raster.biomes[raster.water] = 7
    result = evaluate(raster)
    assert not result['geometry_pass']
    assert result['metrics']['ocean_edges'] == []


def test_boundary_sector_passes_without_full_edge_and_tiny_patch_fails():
    raster = coast()
    # Half of the western edge, with a 512-wide connected sea. Land = 83.3%.
    xx, zz = raster.coordinates()
    water = (xx < -256) & (zz < 0)
    raster.water = water; raster.height = np.where(water,50.,85.); raster.biomes = np.where(water,0,1)
    result = evaluate_coastal(raster, monuments=[[-640,-384]])
    assert result['geometry_pass'], result['reasons']
    assert result['metrics']['ocean_sectors'][0]['contiguous_length_blocks'] == 768
    strict = evaluate_coastal(raster, monuments=[[-640,-384]], thresholds={**COASTAL,'ocean_edge_fraction_min':1.})
    assert not strict['geometry_pass']
    # Retain plenty of interior ocean but only a tiny boundary opening.
    raster.water[:,0] = False; raster.water[0,0] = True
    raster.height = np.where(raster.water,50.,85.); raster.biomes=np.where(raster.water,0,1)
    assert not evaluate_coastal(raster, monuments=[[-640,-384]])['geometry_pass']


def test_disconnected_water_cannot_supply_monument_coastal_footprint():
    raster = coast(); xx,zz = raster.coordinates()
    pond = (np.abs(xx-400) < 100) & (np.abs(zz) < 100)
    raster.water |= pond; raster.biomes[pond] = 0
    result = evaluate_coastal(raster, monuments=[[400,0]])
    assert result['metrics']['ocean_edges'] == ['west']
    assert not result['metrics']['monument_coastal_model_pass']


@pytest.mark.parametrize('position', [[-470,0], [-760,0]])
def test_monument_center_only_is_insufficient(position):
    result = evaluate_coastal(coast(), monuments=[position])
    assert not result['metrics']['monument_coastal_model_pass']
    assert not result['geometry_pass']
    footprint = result['metrics']['monument_footprints'][0]
    assert not footprint['actual_footprint_verified']


def test_missing_biomes_or_monument_stays_unproven():
    raster = coast(); raster.biomes = None
    assert evaluate(raster)['qualification'] == 'PENDING'
    result = evaluate_coastal(coast())
    assert not result['geometry_pass']
    assert not result['metrics']['monument_actual_footprint_verified']


def test_actual_blocks_do_not_verify_predicted_monument_envelope():
    result = evaluate(coast(actual=True))
    assert result['qualification'] == 'PENDING'
    assert not result['score_verified_complete']
    assert not result['metrics']['monument_actual_footprint_verified']


def test_actual_surface_names_are_used_without_numeric_prediction_ids():
    raster = coast(actual=True); raster.biomes = None
    xx, zz = raster.coordinates()
    raster.metadata.update(surface_biome_evidence='actual_api_string_names', stable_sampled_observations=True,
                           surface_biome_observations=[dict(x=int(x),z=int(z),name='minecraft:ocean' if wet else 'minecraft:plains',status='OBSERVED')
                               for x,z,wet in zip(xx.ravel(),zz.ravel(),raster.water.ravel())])
    result = evaluate(raster)
    assert result['model_geometry_pass']
    assert result['qualification'] == 'PENDING'
    assert result['metrics']['ocean_edges'] == ['west']


@pytest.mark.parametrize('scheduler', ['rotation','priority'])
@pytest.mark.parametrize('qualification', ['PREDICTED','PENDING'])
def test_durable_coast_has_one_center_exact_bounds_active_variant_and_resume(tmp_path,monkeypatch,scheduler,qualification):
    from seed_search.realm.store import RealmStore
    def forbidden(*args,**kwargs):
        raise AssertionError('Coastal mode must not enumerate arbitrary terrain centers')
    monkeypatch.setattr('seed_search.realm.terrain.propose_centers', forbidden)
    calls=[]
    class Provider:
        def sample_raster(self, seed, bounds, resolution, stage, dimension, settings):
            calls.append((bounds,resolution,stage))
            return coast(resolution,bounds=bounds)
    cfg={'terrain':{'variants':['v1'],'v1':POLICY,'scheduler':scheduler,'include_pending':qualification=='PENDING',
                    'maximum_refinements_per_anchor':1,'resolutions':[128,64,32]}}
    store=RealmStore(tmp_path/'run',identity={})
    try:
        store.configure_range(0,1);store.claim_range('test')
        candidate=dict(id='42:0:0',seed='42',stronghold=[0,0],bounds={'overworld':list(BOUNDS)},
                       qualification=qualification,baseline_score=60 if qualification=='PREDICTED' else None,baseline_score_observed=30,
                       required_structures={'monument':{'coordinates':[[-640,0]]}})
        store.complete_range(0,1,[dict(index=0,seed='42',anchors=[candidate])])
        result=run_terrain(store,cfg,provider_factory=lambda seed:Provider(),provider_identity={'fixture':'coastal'})
        assert calls and all(tuple(row[0]) == BOUNDS for row in calls)
        assert [row[1] for row in calls] == [128,64,32]
        rows=list(store.iter_variants())
        assert len(rows) == 1 and rows[0]['variant'] == 'v1' and rows[0]['center'] == [0,0]
        assert rows[0]['result']['mode'] == 'coastal_continent'
        if qualification=='PENDING':
            assert rows[0]['result']['score_component_status']['baseline_quality']=='PENDING'
            assert rows[0]['result']['baseline_quality']==50.
            assert not rows[0]['result']['score_verified_complete']
        assert store.get_variant_task_status(candidate['id'],'v1') == 'complete'
        before=len(calls)
        run_terrain(store,cfg,provider_factory=lambda seed:Provider(),provider_identity={'fixture':'coastal'})
        assert len(calls) == before
        with pytest.raises(ValueError,match='inactive'):
            run_terrain(store,cfg,variants=('v2',),provider_factory=lambda seed:Provider(),provider_identity={'fixture':'coastal'})
    finally:
        store.close()


def test_complete_block_water_still_cannot_promote_unknown_structure_extent(monkeypatch):
    raster=coast(actual=True)
    monkeypatch.setattr(raster,'quality',lambda:'VERIFIED')
    result=evaluate(raster)
    assert result['qualification']=='PENDING'
    assert result['evidence']=='PARTIAL'
    assert not result['full_blueprint_certification']
    assert result['unverified_terrain_requirements']


def test_nominal_ocean_strip_cannot_be_fabricated_from_missing_box_coverage():
    raster=coast(bounds=(-700,-768,768,768))
    result=evaluate(raster)
    assert result['qualification']=='PENDING'
    assert not result['model_geometry_pass']
    assert 'west' not in result['metrics']['ocean_edges']


def test_cli_default_and_all_use_blueprint_active_variants(tmp_path,monkeypatch,capsys):
    from seed_search.realm.cli import load,main
    from seed_search.realm.store import RealmStore
    cfg=load()
    assert cfg['terrain']['variants']==['v1']
    assert cfg['terrain']['v1']['mode']=='coastal_continent'
    store=RealmStore(tmp_path,{'config':cfg});store.close()
    calls=[]
    monkeypatch.setattr('seed_search.realm.terrain.run_terrain',lambda *args,**kwargs:calls.append(args) or {})
    main(['terrain','--run',str(tmp_path),'--variant','all'])
    assert calls[0][2]==('v1',)
    capsys.readouterr()


def test_cli_actual_verification_requests_exact_border_without_island_halo(tmp_path):
    from seed_search.realm.cli import select_verification
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.store import RealmStore
    cfg=blueprint_config();store=RealmStore(tmp_path,{'config':cfg})
    class Adapter:
        def get_cached(self,*args):return None
    try:
        candidate=dict(id='42:0:0',seed='42',stronghold=[0,0],bounds={'overworld':list(BOUNDS)},qualification='PREDICTED')
        store.configure_range(0,1);store.claim_range('test')
        store.complete_range(0,1,[dict(index=0,seed='42',anchors=[candidate])])
        store.upsert_variant(candidate['id'],'v1',[0,0],evaluate(coast()))
        selected,_=select_verification(store,'v1',cfg,adapter=Adapter(),spacing=16)
        assert selected[0][0]['verification_bounds']==list(BOUNDS)
        with pytest.raises(ValueError,match='inactive'):
            select_verification(store,'v2',cfg,adapter=Adapter())
    finally:
        store.close()


def test_store_creates_only_active_tasks_and_preserves_historical_rows(tmp_path):
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.store import RealmStore
    store=RealmStore(tmp_path,{'config':blueprint_config()})
    try:
        candidate=dict(id='42:0:0',seed='42',stronghold=[0,0],bounds={'overworld':list(BOUNDS)},qualification='PREDICTED')
        store.configure_range(0,1);store.claim_range('test')
        store.complete_range(0,1,[dict(index=0,seed='42',anchors=[candidate])])
        assert [row['variant'] for row in store.iter_variant_tasks()]==['v1']
        store.upsert_candidate(candidate)
        assert list(store.iter_variant_tasks(variant='v2'))==[]
        with store.db:
            store.db.execute("INSERT INTO variant_tasks VALUES (?,'v2','complete')",(candidate['id'],))
        status=store.status()
        assert status['variant_tasks']=={'v1:pending':1}
        assert status['inactive_variant_tasks']=={'v2:complete':1}
        assert len(list(store.iter_variant_tasks()))==2
    finally:
        store.close()


@pytest.mark.parametrize('spacing',[1,4,16,64])
def test_standalone_verification_region_uses_fixed_box_without_legacy_thresholds(spacing):
    from seed_search.realm.verification_plan import verification_region
    cfg={'terrain':{'variants':['v1'],'v1':{'mode':'coastal_continent'}}}
    prediction={'center':[11,-7], 'border_fit':{'footprint':[-757,-775,779,761]}}
    assert verification_region(prediction,'v1',cfg,spacing)==(-757,-775,779,761)
    with pytest.raises(ValueError,match='inactive'):
        verification_region(prediction,'v2',cfg,spacing)
    prediction['border_fit']['footprint']=[-100,-100,100,100]
    with pytest.raises(ValueError,match='fixed Stronghold1536'):
        verification_region(prediction,'v1',cfg,spacing)


def test_actual_adapter_defers_full_coast_honestly_and_rejects_shrunken_box():
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.verification import VerificationAdapter
    candidate={'seed':'42','stronghold':[0,0],'bounds':{'overworld':list(BOUNDS)}}
    adapter=VerificationAdapter(blueprint_config(),runtime=lambda *args:pytest.fail('Insufficient tile budget must not generate'))
    result=adapter.verify_candidate(candidate,spacing=16)
    assert result['bounds']==list(BOUNDS)
    assert result['status']=='PARTIAL'
    assert result['requested_tiles'] > 16
    assert adapter.used==0
    with pytest.raises(ValueError,match='configured center square'):
        adapter.verify_candidate(candidate,bounds=(-100,-100,100,100),spacing=16)
