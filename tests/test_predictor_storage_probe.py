"""Offline integrity/decoder regressions; no game or Docker launched by tests."""
import copy
import hashlib
import json
from pathlib import Path
import struct

import pytest

from scripts.predictor_storage_probe import compare_points, load_json, tree_hashes
from seed_search.realm.bedrock_biome_storage import decode_data3d

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/bedrock-26.52/storage-regressions'


def read(name):
    return json.loads((FIXTURES / name).read_bytes())


def test_frozen_game_exports_and_reports_have_exact_hashes():
    manifest = read('manifest.json')
    assert len(manifest['files']) == 12
    for name, identity in manifest['files'].items():
        data = (FIXTURES / name).read_bytes()
        assert len(data) == identity['bytes']
        assert hashlib.sha256(data).hexdigest() == identity['sha256']
    for world in (0, 1):
        report = read(f'world-{world}/report.json')
        export = read(f'world-{world}/export.json')
        assert report['status'] == 'observed'
        assert report['clean_shutdown'] is report['save_confirmed'] is report['owned_container_removed'] is True
        assert export['provenance']['source_unchanged'] is True
        assert report['world_identity']['seed'] == export['world_identity']['seed']


def test_every_stored_block_matches_independent_reference_decoder_hash():
    oracle = read('decoder-oracle.json')
    assert (oracle['packed_sections'], oracle['uniform_sections'], oracle['unknown_sections']) == (29, 52, 87)
    exports = [read(f'world-{world}/export.json') for world in (0, 1)]
    for reference in oracle['records']:
        record = next(r for r in exports[reference['world']]['records'] if [r['cx'], r['cz']] == reference['chunk'])
        assert record['sha256'] == reference['record_sha256']
        decoded = decode_data3d(bytes.fromhex(record['data']))
        assert len(decoded.sections) == len(reference['sections'])
        for section, expected in zip(decoded.sections, reference['sections']):
            assert (section.section_y, section.kind) == (expected['y'], expected['kind'])
            if section.kind == 'unknown':
                continue
            values = (section.palette[0],) * 4096 if section.kind == 'uniform' else tuple(section.palette[n] for n in section.indices)
            assert hashlib.sha256(struct.pack('<4096I', *values)).hexdigest() == expected['ids_u32le_yzx_sha256']


def test_api_storage_comparisons_preserve_unknowns_and_block_coordinates():
    cases = read('cases.json')
    results = []
    for world, case in enumerate(cases):
        report = read(f'world-{world}/report.json')
        points = case['points'] + [[c['x'], c['above']['y'], c['z']] for c in report['target_result']['columns'] if 'above' in c]
        result = compare_points(read(f'world-{world}/export.json'), points)
        assert result == read(f'world-{world}/comparison.json')
        results.extend(result['rows'])
    assert len(results) == 54
    assert sum(r['status'] == 'stored' for r in results) == 27
    boundary = next(r for r in results if r['position'] == [448, 63, -512])
    assert boundary['stored_id'] is None and boundary['status'] == 'missing_data3d_record'
    assert boundary['quart'] == [112, 15, -128]
    cave = next(r for r in results if r['position'] == [-256, 63, -256])
    assert cave['stored_id'] == 12 and cave['chunk'] == [-16, -16] and cave['local'] == [0, 15, 0]
    deep = next(r for r in results if r['position'] == [-448, -48, 320])
    assert deep['stored_id'] == 190


@pytest.mark.parametrize('mutation', [
    lambda e: e['records'][0].update(cx=True),
    lambda e: e['records'][0].update(cx=999),
    lambda e: e['records'][0].update(sha256='0' * 64),
    lambda e: e['records'].append(copy.deepcopy(e['records'][0])),
    lambda e: e['world_identity'].update(seed=str(1 << 63)),
    lambda e: e['world_identity'].update(seed=123),
])
def test_unbound_or_malformed_export_cannot_be_a_success(mutation):
    export = read('world-0/export.json')
    mutation(export)
    with pytest.raises(ValueError):
        compare_points(export, [[0, 63, 0]])


@pytest.mark.parametrize('points', [[], [[True, 63, 0]], [[0, 320, 0]], [[0, 63]], [[6000, 63, 0]]])
def test_query_coordinate_caps(points):
    with pytest.raises(ValueError):
        compare_points(read('world-0/export.json'), points)


def test_source_inventory_is_read_only_and_rejects_symlinks(tmp_path):
    world = tmp_path / 'world'
    (world / 'db').mkdir(parents=True)
    (world / 'level.dat').write_bytes(b'level')
    (world / 'db/data').write_bytes(b'original')
    first = tree_hashes(world)
    assert first == tree_hashes(world)
    (world / 'db/link').symlink_to(world / 'db/data')
    with pytest.raises(ValueError, match='symlink'):
        tree_hashes(world)


@pytest.mark.parametrize('text', ['{"seed":"1","seed":"2"}', '{"value":NaN}'])
def test_invalid_json_is_rejected(tmp_path, text):
    path = tmp_path / 'bad.json'
    path.write_text(text)
    with pytest.raises(ValueError, match='Duplicate|Nonfinite'):
        load_json(path)


def test_allocation_cap_includes_memoryview_bytes_not_just_element_count():
    oversized = memoryview(bytearray((1 << 20) + 8)).cast('Q')
    assert len(oversized) < 1 << 20
    with pytest.raises(ValueError, match='1 MiB'):
        decode_data3d(oversized)
