"""Preserve historical model counterexamples without requiring future bugs to persist."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import pytest

from seed_search.realm.bedrock_biome_storage import decode_data3d, resolve_repeated_sections
from seed_search.realm.biomes import canonical
from seed_search.realm.predictor_resolution import load_resolution

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'fixtures/bedrock-26.52/predictor-mechanism'
PARENT=ROOT/'fixtures/bedrock-26.52/predictor-resolution'
SEEDS={0:'-3509659830737203357',1:'-9103892851552028103'}


@pytest.fixture(scope='module')
def bundle():
    manifest=json.loads((FIXTURE/'manifest.json').read_text())
    assert manifest['revision']=='predictor-mechanism-regressions-v1'
    assert hashlib.sha256((PARENT/'manifest.json').read_bytes()).hexdigest()==manifest['parent_resolution_manifest_sha256']
    data={}
    for name,entry in manifest['files'].items():
        assert Path(name).name==name
        raw=(FIXTURE/name).read_bytes()
        assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
        data[name]=raw
    assert sum(map(len,data.values()))<4<<20
    domain=json.loads(data['domain.json'])
    keys=[(SEEDS[c['world']],x,y,z) for c in domain['chunks']
          for x in range(c['cx']*4-1,c['cx']*4+6) for y in range(3,23)
          for z in range(c['cz']*4-1,c['cz']*4+6)]
    nodes={}
    for key,line in zip(keys,data['nodes.txt'].decode().splitlines(),strict=True):
        fields=line.split();assert len(fields)==9
        assert key not in nodes
        nodes[key]=dict(native_id=int(fields[0]),name=fields[1],sha=int(fields[2]),climate=list(map(int,fields[3:])))
    _,parent=load_resolution(PARENT)
    return manifest,data,nodes,parent


def test_frozen_dense_domain_has_discovery_and_independent_holdouts(bundle):
    _,data,nodes,_=bundle
    domain=json.loads(data['domain.json']);findings=json.loads(data['findings.json'])
    assert len(nodes)==3920
    assert len(domain['local_x'])*len(domain['local_z'])*len(domain['chunks'])==128
    assert {c['role'] for c in domain['chunks']}=={'discovery','spatial_holdout','seed_holdout'}
    assert findings['observed_points']==8320 and findings['python_java_selection_parity']==614
    assert findings['mapped_points']==8320 and findings['unmapped_points']==0
    assert findings['missing_carrier_count']==30 and len(findings['missing_carrier_witnesses'])==30
    assert sum(g.get('unmapped_stored_id',0) for g in findings['historical_v2_groups'].values())==171
    assert sum(g['mapped_points'] for g in findings['historical_v2_groups'].values())==8149


@pytest.mark.parametrize('index',range(8))
def test_frozen_model_cannot_select_the_saved_label_from_its_27_parents(bundle,index):
    _,data,nodes,parent=bundle
    findings=json.loads(data['findings.json']);w=findings['primary_witnesses'][index]
    world=next(i for i,seed in SEEDS.items() if seed==w['seed'])
    exported=json.loads(parent[f'lifecycle/dirty_restore-{world}/export.json'])
    x,y,z=w['position'];record=next(r for r in exported['records'] if (r['cx'],r['cz'])==(x//16,z//16))
    raw=bytes.fromhex(record['data']);assert hashlib.sha256(raw).hexdigest()==record['sha256']
    decoded=resolve_repeated_sections(decode_data3d(raw))
    assert decoded.sample(x%16,y,z%16)==w['stored_id']
    assert findings['numeric_name_associations'][w['seed']][str(w['stored_id'])]==w['observed']
    labels={nodes[w['seed'],x//4+dx,y//4+dy,z//4+dz]['name']
            for dx,dy,dz in itertools.product((-1,0,1),repeat=3)}
    assert labels==set(w['neighbor_labels'])
    assert w['observed'] not in labels
    # The raw numeric namespaces deliberately differ (e.g. storage188/native174).
    assert all(nodes[w['seed'],x//4+dx,y//4+dy,z//4+dz]['native_id']>=0
               for dx,dy,dz in itertools.product((-1,0,1),repeat=3))


def test_added_name_associations_are_bound_to_existing_game_copy_and_stored_coordinates(bundle):
    _,data,_,parent=bundle
    findings=json.loads(data['findings.json'])
    for assoc in findings['copied_associations']:
        world=next(i for i,s in SEEDS.items() if s==assoc['seed'])
        report=json.loads(parent[assoc['report']]);export=json.loads(parent[f'lifecycle/dirty_restore-{world}/export.json'])
        assert report['copied_world']['source_unchanged'] is True
        assert report['copied_world']['source_hashes']['level.dat']==export['world_identity']['level_dat_sha256']
        row=next(r for r in report['target_result']['rows'] if [r['x'],r['y'],r['z']]==assoc['position'])
        assert canonical(row['id'])==assoc['name']
        x,y,z=assoc['position'];record=next(r for r in export['records'] if [r['cx'],r['cz']]==[x//16,z//16])
        assert resolve_repeated_sections(decode_data3d(bytes.fromhex(record['data']))).sample(x%16,y,z%16)==assoc['stored_id']


def test_failed_alternatives_and_missing_terrain_coverage_remain_explicit(bundle):
    _,data,_,_=bundle
    models=json.loads(data['witness-model-results.json'])
    for model in models.values():
        assert model['points']==17 and model['center_matches']==9
        assert model['all_missing_carriers_fixed'] is False
    fitness=json.loads(data['tree-fitness-results.json'])
    assert fitness['leaves']==7776
    assert all(r['gap']>0 and r['minimum_tied_biomes']==1 for r in fitness['witnesses'])
    terrain=json.loads(data['start-footprint-results.json'])
    assert len(terrain)==4
    assert next(r for r in terrain if r['kind']=='village' and r['negative'])['missing_footprint_samples']>0
    assert next(r for r in terrain if r['kind']=='outpost' and not r['negative'])['covered_delta']==22


def test_node_builder_cannot_overwrite_repository_or_existing_external_output(tmp_path):
    spec=importlib.util.spec_from_file_location('node_probe_builder',ROOT/'scripts/build_biome_sampling_probe.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    outside=tmp_path/'kept';outside.write_text('preserve')
    for output in (ROOT/'native/do-not-build-node-probe',outside):
        with pytest.raises(SystemExit) as stopped:
            builder.main(['--mode','nodes','--output',str(output)])
        assert stopped.value.code==2
    assert outside.read_text()=='preserve'
    assert not (ROOT/'native/do-not-build-node-probe').exists()


def test_direct_stable_bds_confirms_new_witnesses_and_unknown_id_without_reclassifying_nodes(bundle):
    import re
    _,data,_,parent=bundle
    frozen=json.loads(data['direct-frozen.json']);compared=json.loads(data['direct-comparison.json'])
    assert len(compared)==25
    findings=json.loads(data['findings.json'])
    primary={(w['seed'],*w['position']) for w in findings['primary_witnesses']}
    confirmed=set()
    preservation=json.loads(data['direct-source-preservation.json'])
    for world,case in enumerate(frozen):
        report=json.loads(data[f'direct-world-{world}-report.json'])
        assert report['status']=='observed'
        assert report['save_confirmed'] and report['clean_shutdown'] and report['owned_container_removed']
        assert report['world_identity']==dict(seed=case['seed'],api='2.10.0',players=0)
        assert report['controls']['manifest_sha256']==hashlib.sha256(data['direct-frozen.json']).hexdigest()
        assert report['controls']['observer_sha256']==hashlib.sha256(data['direct-observer.js']).hexdigest()
        assert report['controls']['settings_sha256']==hashlib.sha256(data[f'direct-world-{world}-server.properties']).hexdigest()
        log=data[f'direct-world-{world}-console.log'].decode()
        assert re.search(r'\bVersion: 1\.26\.52\.3(?:\s|$)',log)
        emitted=[json.loads(s.split('TARGET_RESULT ',1)[1]) for s in log.splitlines() if 'TARGET_RESULT ' in s]
        assert emitted==[report['target_result']]
        assert [[r['x'],r['y'],r['z']] for r in report['target_result']['rows']]==case['points']
        export=json.loads(parent[f'lifecycle/dirty_restore-{world}/export.json'])
        assert report['copied_world']['source_hashes']['level.dat']==export['world_identity']['level_dat_sha256']
        assert report['copied_world']['source_unchanged'] is True
        state=next(s for s in preservation if s['seed']==case['seed'])
        assert state['unchanged'] and state['before']==state['after']==report['copied_world']['source_hashes']
        for row in report['target_result']['rows']:
            key=(case['seed'],row['x'],row['y'],row['z'])
            comparison=next(c for c in compared if (c['seed'],*c['position'])==key)
            assert comparison['observed']==canonical(row['id'])
            x,y,z=row['x'],row['y'],row['z']
            record=next(r for r in export['records'] if (r['cx'],r['cz'])==(x//16,z//16))
            stored=resolve_repeated_sections(decode_data3d(bytes.fromhex(record['data']))).sample(x%16,y,z%16)
            assert comparison['stored_id']==stored
            assert findings['numeric_name_associations'][case['seed']][str(stored)]==comparison['observed']
            if key in primary:confirmed.add(key)
    assert confirmed==primary
    assert next(c for c in compared if c['stored_id']==1)['observed']=='plains'
    assert sum(json.loads(data[f'direct-world-{i}-report.json'])['target_result']['biomeReads'] for i in (0,1))==25
    assert sum(json.loads(data[f'direct-world-{i}-report.json'])['target_result']['blockReads'] for i in (0,1))==28



def test_original_and_portable_probe_provenance_remain_distinct(bundle):
    _,data,_,_=bundle
    original=json.loads(data['original-build.json'])
    portable=json.loads(data['build.json'])
    findings=json.loads(data['findings.json'])
    assert findings['build_sha256']==original['binary_sha256']
    entry=next(sha for name,sha in original['source_sha256'].items() if name.endswith('/node_probe.c'))
    assert hashlib.sha256(data['original-probe.c']).hexdigest()==entry
    assert 'scripts/biome_node_probe.c' in portable['source_sha256']
    assert 'scripts/biome_sampling_probe.c' in portable['source_sha256']
