import copy
import numpy as np
import pytest

from seed_search.backend import Backend, biome_catalog
from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.blueprint import PALETTE, biome_gate, smart_score
from seed_search.realm.config import blueprint_config, default_config, validate_config

IDS={row['name']:row['id'] for row in biome_catalog()}


class BlueprintBackend:
    missing=None
    calls=[]
    def __init__(self,seed):self.native_work={}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structures(self,name,bounds,viable=True):
        self.calls.append(name)
        if name==self.missing:return []
        n=blueprint_config()['structures']['minimum_counts'].get(name,1)+2
        if name=='stronghold':return [(0,0)]
        return [(i*16,16) for i in range(n)]
    def structure_pair(self,name,bounds):
        values=self.structures(name,bounds)
        return values,values
    def structure_count(self,name,bounds,minimum):return self.structures(name,bounds)[:minimum]
    def biome_points(self,points):
        surface=['plains','desert','forest','taiga','jungle','swamp','snowy_plains','dark_forest','jagged_peaks','stony_shore']
        caves=['lush_caves','dripstone_caves','deep_dark']
        if len(points)<10:return np.full(len(points),IDS['dark_forest']) # Mansion anchor
        return np.array([IDS[(caves if y in (-48,0) else surface)[(int(x)//64+int(z)//64) % (3 if y in (-48,0) else 10)]] for x,y,z in points],dtype=np.int32)


def test_explicit_profile_retains_historical_contract():
    old=default_config();new=blueprint_config()
    validate_config(old);validate_config(new)
    assert 'contract' not in old and old['terrain']['variants']==['v1','v2']
    assert new['terrain']['variants']==['v1'] and 'v2' not in new['terrain']
    assert new['structures']['minimum_counts']['village']==5
    assert set(new['structures']['optional_bonuses'])=={'outpost'}
    for path,value in [(('structures','minimum_counts','village'),4),(('biomes','sample_y_levels'),[63]),(('terrain','variants'),['v1','v2'])]:
        cfg=copy.deepcopy(new);parent=cfg
        for key in path[:-1]:parent=parent[key]
        parent[path[-1]]=value
        with pytest.raises(ValueError):validate_config(cfg)


def test_four_y_roles_separate_surface_from_caves():
    class Swapped(BlueprintBackend):
        def biome_points(self,points):
            return np.array([IDS['dark_forest' if y<1 else 'lush_caves'] for x,y,z in points])
    result=biome_gate(Swapped(0),(-768,-768,768,768),blueprint_config(),complete=True)
    assert 'dark_forest' in result['missing_families'] and 'lush_caves' in result['missing_families']
    assert result['sample_count']==24*24*4
    assert result['sampling']['complete_defined_lattice']
    assert result['qualification']=='PENDING' and not result['surface_generation_verified']


def test_palette_requires_peak_and_shore_and_three_caves():
    assert PALETTE['peaks']=={'jagged_peaks','stony_peaks'}
    assert PALETTE['stony_shore']=={'stony_shore'}
    assert PALETTE['dark_forest']=={'dark_forest'}
    assert not {'pale_garden','sparse_jungle','windswept_forest'} & set.union(*PALETTE.values())


def test_short_circuit_matches_reference_on_passing_fixture():
    cfg=blueprint_config();BlueprintBackend.calls=[]
    fast=evaluate_seed(0,1,cfg,backend_factory=BlueprintBackend)['anchors'][0]
    reference=evaluate_seed(0,1,cfg,backend_factory=BlueprintBackend,combined=False,short_circuit=False)['anchors'][0]
    assert fast['qualification']==reference['qualification']=='PREDICTED'
    assert fast['baseline_score']==reference['baseline_score']
    assert fast['baseline_score_complete'] and fast['inventory']['tasks']==[]
    assert fast['biomes']['observed_families']==reference['biomes']['observed_families']
    assert fast['biomes']['witnesses']==reference['biomes']['witnesses']
    assert fast['biomes']['sample_count']<reference['biomes']['sample_count']
    assert fast['ranking']==reference['ranking']
    for name in cfg['structures']['minimum_counts']:
        assert fast['required_structures'][name]['predicted_viable']==reference['required_structures'][name]['predicted_viable']
    for family,witness in fast['biomes']['witnesses'].items():
        x,y,z=witness['coordinate']
        assert -768<=x<768 and -768<=z<768
        assert x%64==z%64==0 and witness['biome'] in PALETTE[family]
        assert y in ((-48,0) if family.endswith('caves') or family=='deep_dark' else (63,160))
    assert not set(BlueprintBackend.calls)&{'end_city','igloo','swamp_hut','buried_treasure','ocean_ruin'}
    assert fast['ranking']['bonuses']['coastal_monument_footprint']==0


def test_count_floor_failure_stays_pending_and_avoids_later_work():
    class Missing(BlueprintBackend):missing='mansion';calls=[]
    result=evaluate_seed(0,1,blueprint_config(),backend_factory=Missing)
    candidate=result['anchors'][0]
    assert candidate['qualification']=='PENDING'
    assert candidate['pending_reasons']==['count_mansion']
    assert candidate['biomes'] is None
    assert Missing.calls==['stronghold','mansion']
    assert result['counts']['confirmed_rejections']==0


@pytest.mark.parametrize('family',[name for name in blueprint_config()['structures']['minimum_counts'] if name!='stronghold']+['fortress','bastion'])
def test_each_required_floor_cannot_be_satisfied_by_presence_alone(family):
    cfg=blueprint_config()
    class OneBelow(BlueprintBackend):
        def structures(self,name,bounds,viable=True):
            values=super().structures(name,bounds,viable)
            floor=cfg['structures']['minimum_counts'].get(name,1)
            return values[:floor-1] if name==family else values
    fast=evaluate_seed(0,1,cfg,backend_factory=OneBelow)['anchors'][0]
    reference=evaluate_seed(0,1,cfg,backend_factory=OneBelow,combined=False,short_circuit=False)['anchors'][0]
    assert fast['qualification']==reference['qualification']=='PENDING'
    assert 'count_'+family in fast['pending_reasons']
    assert fast['baseline_score'] is None and fast['inventory']['tasks']==[]


def test_smart_ranking_caps_and_unbounded_extras():
    def obs(n):return {'predicted_viable':[(i,0) for i in range(n)]}
    structures={name:obs(n) for name,n in [('village',8),('trial_chamber',8),('ancient_city',4),('desert_pyramid',4),('jungle_temple',3),('monument',3),('ruined_portal',6),('shipwreck',7),('mineshaft',25)]}
    result=smart_score(structures,{'fortress':obs(4),'bastion':obs(3)},{'outpost':obs(2)})
    assert result['score']==290
    assert result['bonuses']['trial_chamber']==20 and result['bonuses']['monument']==25
    assert smart_score(structures,{}, {},coastal_footprint_verified=True)['bonuses']['coastal_monument_footprint']==25


@pytest.mark.parametrize('seed',[0,12345,-1])
def test_native_count_floors_match_full_inventory(seed):
    with Backend(seed) as backend:
        for name,minimum in [('village',5),('trial_chamber',2),('ancient_city',1),('mineshaft',5),('shipwreck',2),('ruined_portal',3),('mansion',1),('outpost',2)]:
            bounds=(-768,-768,767,767)
            full=backend.structures(name,bounds)
            capped=backend.structure_count(name,bounds,minimum)
            assert len(capped)==min(len(full),minimum)
            assert set(capped)<=set(full)
        with pytest.raises(ValueError):backend.structure_count('village',bounds,True)
        with pytest.raises(ValueError):backend.structure_count('stronghold',bounds,1)


def test_active_inventory_and_rescore_preserve_count_contract():
    from seed_search.realm.inventory import detect_structures,execute_inventory
    from seed_search.realm.reports import _candidate_rescore
    cfg=blueprint_config()
    candidate=evaluate_seed(0,1,cfg,backend_factory=BlueprintBackend)['anchors'][0]
    before=copy.deepcopy(candidate)
    backend=BlueprintBackend(1);BlueprintBackend.calls=[]
    inventory=detect_structures(candidate,cfg,backend,exhaustive=True)
    assert set(inventory['structure_inventory'])==set(cfg['structures']['minimum_counts'])|{'fortress','bastion','outpost'}
    biome_inventory=execute_inventory(candidate,cfg,'biomes',backend)
    assert set(biome_inventory)=={'biomes'}
    assert biome_inventory['biomes']['sample_y_levels']==[63,-48,0,160]
    rescored=_candidate_rescore(candidate,cfg,'test-revision')
    assert rescored['baseline_score']==before['baseline_score']
    assert rescored['biomes']==before['biomes']
    assert rescored['pending_reasons']==before['pending_reasons']


def test_capabilities_describe_active_contract_and_hash_new_implementation():
    from seed_search.realm.capabilities import report,identity
    active=report(blueprint_config());legacy=report(default_config())
    assert active['variants']==['v1'] and legacy['variants']==['v1','v2']
    assert 'four-Y' in active['caves'] and active['full_blueprint_certification'] is False
    hashes=identity()['sha256']
    assert 'src/seed_search/realm/blueprint.py' in hashes
    assert 'src/seed_search/realm/coastal.py' in hashes


@pytest.mark.parametrize('seed',[2**32+12345,-2**63,2**63-1])
def test_count_kernel_keeps_full_seed_viability_and_negative_boundaries(seed):
    with Backend(seed) as backend:
        for bounds in [(-1537,-1025,-2,510),(-16,-16,15,15)]:
            for name,floor in [('mineshaft',5),('village',5),('trial_chamber',2),('fortress',1),('bastion',1),('outpost',2)]:
                full=backend.structures(name,bounds)
                witnesses=backend.structure_count(name,bounds,floor)
                assert len(witnesses)==min(len(full),floor)
                assert set(witnesses)<=set(full)


def test_source_distribution_includes_native_kernel_fragments():
    from pathlib import Path
    from setuptools._distutils.filelist import FileList
    root=Path(__file__).resolve().parents[1]
    manifest=FileList()
    manifest.findall(str(root))
    # Distutils normally changes into project root and records relative paths.
    manifest.allfiles=[str(Path(p).relative_to(root)) for p in manifest.allfiles]
    for line in (root/'MANIFEST.in').read_text().splitlines():
        if line.strip() and not line.startswith('#'):manifest.process_template_line(line)
    assert 'native/filters.inc' in manifest.files
    assert 'native/count_pilot.inc' in manifest.files
