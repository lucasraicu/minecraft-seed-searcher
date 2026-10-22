"""Replay retained independent game bytes; no game, network or native jobs in tests."""
from pathlib import Path
import hashlib,json,tarfile
import pytest
from seed_search.catalog.models import identity
from seed_search.catalog.biome_provider import StoredBiomeProvider
from seed_search.catalog.refinement import make_tile,evaluate_scope

ROOT=Path(__file__).resolve().parents[1]/'fixtures/bedrock-26.52/accuracy-expansion'


@pytest.fixture(scope='module')
def evidence():
    manifest=json.loads((ROOT/'manifest.json').read_text());raw=(ROOT/manifest['archive']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==manifest['archive_sha256']
    with tarfile.open(ROOT/manifest['archive'],'r:gz')as archive:
        members=archive.getmembers();assert {m.name for m in members}==set(manifest['files'])
        data={}
        for member in members:
            assert member.isfile() and not member.name.startswith('/') and '..'not in Path(member.name).parts and member.size<=4<<20
            value=archive.extractfile(member).read();expected=manifest['files'][member.name]
            assert len(value)==expected['bytes'] and hashlib.sha256(value).hexdigest()==expected['sha256'];data[member.name]=value
    return data


def context(case,provider,evidence_hash):
    return dict(identity=identity(case['seed'],model_id='26.50',native_sha256='19a4b81e2ed97ca1d5033db789225a0ad421cc7de2032d9e20be510cde59965e',source_sha256=case['prediction']['source_sha256']),dimension=case['dimension'],provider=provider,observed_build='1.26.52.3',evidence_sha256=evidence_hash)


def test_world_spawn_matches_independent_saved_metadata_and_sentinel_is_not_ground(evidence):
    for i in range(8):
        r=json.loads(evidence[f'fresh/{i:02}/report.json']);e=json.loads(evidence[f'fresh/{i:02}/export.json'])
        assert r['clean_shutdown'] is r['save_confirmed'] is r['owned_container_removed'] is True
        assert e['world_identity']['level_dat_sha256']==hashlib.sha256(evidence[f'fresh/{i:02}/level.dat']).hexdigest()
        api=r['world_identity']['worldSpawn'];saved=e['world_identity']['world_spawn']
        assert [api['x'],api['z']]==[saved['SpawnX'],saved['SpawnZ']]
        assert api['y']==32767 and r['world_identity']['players']==0


def test_saved_height_provider_matches_scoped_game_associations_and_retains_missing_records(evidence):
    frozen=json.loads(evidence['protocol/frozen.json']);analysis=json.loads(evidence['protocol/storage-analysis.json'])
    # These are explicitly calibrated local saved-ID/API-name associations from
    # the pilot, not an assumed universal equivalence with predictor numeric IDs.
    names={(r['dimension'],r['stored_id']):r['api_names'][0]for r in analysis['associations']}
    known=unknown=0
    for i,c in enumerate(frozen['worlds']):
        export=json.loads(evidence[f'fresh/{i:02}/export.json']);report=json.loads(evidence[f'fresh/{i:02}/report.json'])
        ctx=context(c,'bds_saved_runtime_v3',hashlib.sha256(evidence[f'fresh/{i:02}/export.json']).hexdigest())
        records=[dict(chunk_x=r['cx'],chunk_z=r['cz'],payload=bytes.fromhex(r['data']))for r in export['records']if r['dimension']==c['dimension']]
        provider=StoredBiomeProvider(ctx,records)
        for row in report['target_result']['rows']:
            value=provider.sample(row['x'],row['y'],row['z'])
            if value['raw_id']is None:unknown+=1;assert value['status']=='unknown'
            else:known+=1;assert names[(c['dimension'],value['raw_id'])]==row['id']
    assert (known,unknown)==(15462,1034)
    # Controlled persistence repair is a separate copied-world observation.
    c=frozen['worlds'][7];export=json.loads(evidence['persistence/export.json']);report=json.loads(evidence['persistence/report.json'])
    assert report['copied_world']['source_unchanged'] is True
    ctx=context(c,'bds_saved_runtime_v3',hashlib.sha256(evidence['persistence/export.json']).hexdigest())
    p=StoredBiomeProvider(ctx,[dict(chunk_x=r['cx'],chunk_z=r['cz'],payload=bytes.fromhex(r['data']))for r in export['records']if r['dimension']=='nether'])
    assert all(p.sample(row['x'],row['y'],row['z'])['raw_id']==8 for row in report['target_result']['rows'])
    assert all(m['restored'] for m in report['target_result']['mutations'])


def test_dense_game_tile_recovers_a_biome_missing_from_its_coarse_sample(evidence):
    c=json.loads(evidence['protocol/frozen.json'])['worlds'][0];r=json.loads(evidence['fresh/00/report.json'])
    offset=len(c['points']);rows=r['target_result']['rows'][offset:offset+1024]
    coarse=[row for row in rows if row['x']%64==0 and row['z']%64==0]
    assert len(coarse)==1 and all(row['id']!='minecraft:taiga'for row in coarse)
    assert sum(row['id']=='minecraft:taiga'for row in rows)==99
    ctx=context(c,'bds_script_api_v1',hashlib.sha256(evidence['fresh/00/report.json']).hexdigest())
    tile=make_tile(ctx,[0,0,32,32],63,[1 if row['id']=='minecraft:taiga'else 2 for row in rows],biome_names={'1':'taiga','2':'old_growth_spruce_taiga'})
    assert evaluate_scope([tile],ctx,[0,0,32,32],63,[1])['status']=='present'
    assert evaluate_scope([tile],ctx,[0,0,33,32],63,[3])['status']=='unknown'
