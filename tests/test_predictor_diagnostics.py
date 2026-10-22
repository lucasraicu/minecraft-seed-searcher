"""Saved game regressions: zero tolerance and no population accuracy claims."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from seed_search.realm.predictor_diagnostics import (
    comparison_rows, diagnostic_report, load_bundle, structure_rows,
)

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/bedrock-26.52/predictor-corrections'


@pytest.fixture(scope='module')
def bundle():
    return load_bundle(FIXTURES)


def test_exact_api_comparisons_are_reproduced_under_frozen_name_policy():
    report = diagnostic_report(FIXTURES)
    assert report['biome_comparisons']['cohort']['points'] == 330
    assert report['biome_comparisons']['cohort']['matches'] == dict(direct_quart=311, vendor_block=292)
    assert report['biome_comparisons']['pilot']['points'] == 256
    assert report['biome_comparisons']['pilot']['matches'] == dict(direct_quart=253, vendor_block=239)
    assert report['biome_comparisons']['vertical']['points'] == 28
    assert 'No global sampler replacement' in report['verdict']


def test_navigation_projection_replays_saved_game_references_without_reclassifying_raw_failures():
    report = diagnostic_report(FIXTURES)
    projections = report['coordinate_projections']
    assert projections['candidate_directed'] == {
        'mineshaft': dict(tested=12, exact_projected_reference=12),
        'fortress': dict(tested=9, exact_projected_reference=9),
        'outpost': dict(tested=12, exact_projected_reference=11),
    }
    controls = projections['independent_discovery']
    assert len(controls) == 6
    assert sum(r['distinct_located'] for r in controls) == 23
    assert all(r['distinct_located'] == r['exact_projected_membership'] and not r['unmatched'] for r in controls)
    assert report['structure_roles']['candidate_directed']['coordinate_difference'] >= 30
    assert 'stronghold' not in projections['candidate_directed']
    assert projections['projected_differences'] == [dict(
        seed='-3509659830737203357', feature='outpost', candidate=[528, 512],
        projected_reference=[536, 520], reported=[-1000, 408], raw_outcome='coordinate_difference')]


def test_unknown_coordinate_identifiers_do_not_raise_or_guess():
    from seed_search.realm.structure_coordinates import project_navigation_reference
    for feature, dimension in [([], 'overworld'), ('outpost', []), ({}, 'nether'), (None, None)]:
        assert project_navigation_reference(feature, 0, 0, dimension=dimension,
            prediction_revision='cubiomes-bedrock-26.50', bds_build='1.26.52.3') is None


def test_six_spruce_rows_retain_raw_name_without_alias_fitting(bundle):
    manifest, data, reports = bundle
    rows = comparison_rows(manifest, data, reports)['cohort']
    rows = [r for r in rows if r['id'] == 'minecraft:redwood_taiga_mutated']
    assert len(rows) == 6
    assert {r['direct_quart'] for r in rows} == {'old_growth_spruce_taiga'}
    assert manifest['aliases']['redwood_taiga_mutated'] == 'taiga'


def test_cave_and_boundary_disagreements_are_not_hidden(bundle):
    manifest, data, reports = bundle
    rows = comparison_rows(manifest, data, reports)['vertical']
    row = next(r for r in rows if (r['x'], r['y'], r['z']) == (-256, 63, -256))
    assert row['id'] == 'minecraft:ice_plains'
    assert row['vendor_block'] == row['direct_quart'] == 'dripstone_caves'
    boundary = next(r for r in rows if (r['x'], r['y'], r['z']) == (448, 63, -512))
    assert boundary['id'] == 'minecraft:snowy_slopes'
    assert boundary['direct_quart'] == 'snowy_slopes'
    assert boundary['vendor_block'] == 'snowy_plains'


def test_loaded_flag_is_harness_action_not_chunk_absence(bundle):
    manifest, data, reports = bundle
    rows = comparison_rows(manifest, data, reports)['vertical']
    assert any(r['loaded'] is False and r['id'] for r in rows)
    assert 'Not a world-generation' in manifest['loaded_field_semantics']
    observer = data['observer.js'].decode()
    assert "id=dim.getBiome({x,y,z}).id;}catch(first)" in observer
    assert "createTickingArea('audit_'+q.id+'_'+i,opts);loaded=true" in observer


def test_historical_village_and_stronghold_locate_disagreements_remain_in_raw_evidence(bundle):
    rows = structure_rows(bundle[2])
    village = next(r for r in rows if r['kind'] == 'structure.village' and r['query'] == [-296, -312])
    assert village['reported'] == [-888, 136]
    assert village['outcome'] == 'coordinate_difference'
    strongholds = [r for r in rows if r['kind'] == 'structure.stronghold']
    assert len(strongholds) == 9
    assert sum([r['reported'][0]-r['query'][0], r['reported'][1]-r['query'][1]] == [-2, -2] for r in strongholds) == 8
    assert any([r['reported'][0]-r['query'][0], r['reported'][1]-r['query'][1]] == [-722, -322] for r in strongholds)


def test_discovery_probes_not_misreported_as_candidate_misses(bundle):
    rows = structure_rows(bundle[2])
    assert len([r for r in rows if r['kind'].startswith('discovery.')]) == 176
    assert len([r for r in rows if r['kind'].startswith('structure.')]) == 232


def test_derived_rows_must_bind_to_actual_api_responses(bundle):
    manifest, data, reports = bundle
    data = dict(data)
    path = manifest['comparisons']['cohort']
    doc = json.loads(data[path])
    doc['rows'][0]['id'] = 'minecraft:invented_biome'
    data[path] = json.dumps(doc).encode()
    with pytest.raises(ValueError, match='original observation'):
        comparison_rows(manifest, data, reports)


@pytest.fixture
def copied(tmp_path):
    target = tmp_path / 'bundle'
    shutil.copytree(FIXTURES, target)
    return target


def test_fixture_byte_tampering_fails(copied):
    p = copied / 'direct-f9a3dff6c7d1/report.json'
    p.write_bytes(p.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='checksum'):
        load_bundle(copied)


@pytest.mark.parametrize('mutation', ['seed', 'build', 'cleanup'])
def test_semantic_identity_failures_rejected_even_with_updated_file_checksum(copied, mutation):
    path = 'direct-f9a3dff6c7d1/report.json'
    p = copied / path
    doc = json.loads(p.read_bytes())
    if mutation == 'seed':
        doc['world_identity']['seed'] = '1'
    elif mutation == 'build':
        doc['controls']['image_id'] = 'sha256:' + '0' * 64
    else:
        doc['clean_shutdown'] = False
    p.write_text(json.dumps(doc))
    manifest = json.loads((copied / 'manifest.json').read_bytes())
    manifest['files'][path] = dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (copied / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='identity/cleanup'):
        load_bundle(copied)


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'back\\slash'])
def test_manifest_paths_cannot_escape_bundle(copied, name):
    p = copied / 'manifest.json'
    manifest = json.loads(p.read_bytes())
    manifest['files'] = {name: dict(bytes=1, sha256='0' * 64)}
    p.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Invalid fixture path'):
        load_bundle(copied)


def test_fixture_symlink_rejected(copied):
    p = copied / 'observer.js'
    p.unlink()
    p.symlink_to(FIXTURES / 'observer.js')
    with pytest.raises(ValueError, match='symlink'):
        load_bundle(copied)


def test_grouped_temple_and_unknown_location_are_retained(bundle):
    rows = structure_rows(bundle[2])
    temples = [r for r in rows if r['kind'] == 'structure.desert_pyramid' and r['reported']]
    assert temples and all('minecraft:temple' in '\n'.join(r['raw_output']) for r in temples)
    camps = [r for r in rows if r['kind'] == 'structure.abandoned_camp']
    assert len(camps) == 9
    assert all(r['reported'] is None and r['outcome'] == 'no_location' for r in camps)
