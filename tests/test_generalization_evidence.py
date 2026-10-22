"""Portable real-game regressions: retain errors and rejected positive references."""
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

import pytest

from seed_search.realm.bedrock_biome_storage import decode_data3d, sample_bedrock_runtime

from scripts.generalization_audit import validate_manifest
from scripts.generalization_biome_probe import compare_biomes
from scripts.generalization_structure_probe import assess_locates

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/bedrock-26.52/generalization'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope='module')
def bundle():
    descriptor = json.loads((FIXTURE / 'audit-evidence-v1.manifest.json').read_bytes())
    assert descriptor['revision'] == 'generalization-audit-evidence-v1'
    assert descriptor['archive'] == 'audit-evidence-v1.tar.gz'
    raw = (FIXTURE / descriptor['archive']).read_bytes()
    assert len(raw) == descriptor['archive_bytes'] <= 8 << 20
    assert digest(raw) == descriptor['archive_sha256']
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
            assert member.name not in files and len(files) < 256
            assert 0 <= member.size <= 16 << 20
            data = archive.extractfile(member).read(16 * (1 << 20) + 1)
            assert len(data) == member.size
            files[member.name] = data
            assert sum(map(len, files.values())) <= 32 << 20
    assert set(files) == set(descriptor['files'])
    for name, entry in descriptor['files'].items():
        assert len(files[name]) == entry['bytes'] and digest(files[name]) == entry['sha256']
    return descriptor, files


def test_all_default_worlds_have_bound_game_provenance(bundle):
    descriptor, files = bundle
    manifest = json.loads(files['cohort/manifest.json'])
    assert digest(files['cohort/manifest.json']) == descriptor['source_manifest_sha256']
    assert validate_manifest(manifest)['worlds'] == 24
    ledger = json.loads(files['cohort/ledger.json'])
    assert len(ledger) == 24 and {r['index'] for r in ledger} == set(range(24))
    for entry in ledger:
        assert entry['state'] == 'complete' and entry['wall_seconds'] <= 600
        prefix = f'cohort/world-{entry["index"]:02}/'
        report = json.loads(files[prefix + 'report.json'])
        assert digest(files[prefix + 'report.json']) == entry['report_sha256']
        world = manifest['worlds'][entry['index']]
        assert report['seed'] == report['world_identity']['seed'] == world['seed']
        assert report['world_identity']['api'] == '2.10.0' and report['world_identity']['players'] == 0
        assert report['image_id'] == manifest['image_id']
        assert report['manifest_sha256'] == descriptor['source_manifest_sha256']
        assert report['status'] == 'observed'
        assert all(report[k] is True for k in ('clean_shutdown', 'owned_container_removed', 'save_confirmed', 'game_build_observed'))
        assert digest(files[prefix + 'server.properties']) == report['settings_sha256']
        assert ('level-seed=' + world['seed']).encode() in files[prefix + 'server.properties'].splitlines()
        assert digest(files[prefix + 'observer.js']) == report['observer_sha256']
        console = files[prefix + 'console.log'].decode()
        assert re.search(r'\bVersion: 1\.26\.52\.3(?:\s|$)', console)
        cases = {q['case_id']: q for q in world['structures']}
        assert set(cases) == {q['case_id'] for q in report['queries']}
        for query in report['queries']:
            case = cases[query['case_id']]
            assert query['query'] == case['origin'] and query['dimension'] == case['dimension']
            assert query['command_id'] == case['command_id']
            x, z = query['query']
            command = f'AUDIT_INPUT execute in {case["dimension"]} positioned {x} 64 {z} run locate structure minecraft:{case["command_id"]} false'
            assert command in console
            assert all(line in console for line in query['output'])
        batches = [json.loads(line.split('GENERALIZATION_RESULT ', 1)[1]) for line in console.splitlines()
                   if 'GENERALIZATION_RESULT ' in line]
        assert all(batch in batches and batch['chunksAfterUnload'] == 0 for batch in report['biome_batches'])


def test_real_point_and_reference_outcomes_replay_without_masking_failures(bundle):
    _, files = bundle
    manifest = json.loads(files['cohort/manifest.json'])
    result = json.loads(files['cohort/results.json'])
    assert result['prediction_verdict'] == 'counterexamples_observed'
    assert result['all_supported_features_verified'] is False
    assert all(result[k] is None for k in ('generated_count', 'exhaustive_count', 'recall'))
    original_biomes = {(r['seed'], r['dimension'], *r['position']): r for r in result['biome_rows']}
    original_structures = {r['case_id']: r for r in result['structure_rows']}
    rejected_positive = set()
    checked_biomes = checked_structures = 0
    for world in manifest['worlds']:
        report = json.loads(files[f'cohort/world-{world["index"]:02}/report.json'])
        structures = assess_locates(world['structures'], report['queries'],
            prediction_revision=manifest['prediction_revision'], bds_build=manifest['bds_build'])
        for row in structures:
            old = original_structures[row['case_id']]
            assert (row['outcome'], row['reported'], row['disposition']) == (old['outcome'], old['reported'], old['disposition'])
            if row['disposition'] == 'rejected' and row['outcome'] in ('reference_exact', 'navigation_exact'):
                rejected_positive.add(row['case_id'])
                assert 'possible over-rejection' in row['interpretation']
        checked_structures += len(structures)
        for dimension in ('overworld', 'nether', 'the_end'):
            predicted = [{k:v for k,v in p.items() if k != 'dimension'} for p in world['predictions'] if p['dimension'] == dimension]
            observed = [r for batch in report['biome_batches'] if batch['dimension'] == dimension for r in batch['rows']]
            rows = compare_biomes(predicted, observed, aliases=manifest['aliases'], non_comparable=manifest['non_comparable'])
            for row in rows:
                old = original_biomes[world['seed'], dimension, *row['position']]
                assert (row['outcome'], row['observed_name']) == (old['outcome'], old['observed_name'])
            checked_biomes += len(rows)
    assert checked_biomes == len(result['biome_rows'])
    assert checked_structures == len(result['structure_rows'])
    assert rejected_positive == {r['case_id'] for r in result['possible_over_rejections']}
    assert rejected_positive
    coverage = json.loads(files['cohort/coverage.json'])
    assert len(coverage['biomes']) == 61 and len(coverage['structures']) == 21
    assert all(r['matching_seeds'] for r in coverage['biomes'])


def test_copied_beta_followup_stays_separate_and_charged(bundle):
    _, files = bundle
    original = json.loads(files['cohort/ledger.json'])
    extra = json.loads(files['followup/ledger.json'])
    addendum = json.loads(files['followup/frozen.json'])
    assert len(addendum['cases']) == 5
    assert len({r['index'] for r in extra})==5
    bio=json.loads(files['biome-recheck/ledger.json'])
    for index in range(24):
        original_time=next(r['wall_seconds'] for r in original if r['index']==index)
        assert original_time+sum(r['wall_seconds'] for r in extra+bio if r['index']==index)<=600
    assert sum(r['wall_seconds'] for r in original + extra + bio) <= 7200
    for entry in extra:
        previous = next(r['wall_seconds'] for r in original if r['index'] == entry['index'])
        assert previous + entry['wall_seconds'] <= 600
        assert entry['state'] != 'starting'
        if entry['state'] != 'complete':
            continue  # Explicit failed/unattempted cases are not positive evidence.
        prefix = entry['archive_prefix']
        report = json.loads(files[prefix + 'report.json'])
        case = next(c for c in addendum['cases'] if c['index'] == entry['index'])
        assert digest(files[prefix + 'report.json']) == entry['report_sha256']
        assert report['controls']['script_api'] == '2.11.0-beta'
        assert report['world_identity']['dimension'] == case['dimension']
        assert report['world_identity']['seed'] == case['seed']
        assert entry['source_unchanged'] is True
        assert all(report[k] is True for k in ('clean_shutdown', 'owned_container_removed', 'save_confirmed'))
        assert digest(files[prefix + 'server.properties']) == report['controls']['settings_sha256']
        assert digest(files[prefix + 'observer.js']) == report['controls']['observer_sha256']
        assert [[r['x'],r['y'],r['z']] for r in report['target_result']['rows']] == case['points']
        assert all(r['dimension'] == case['dimension'] for r in report['target_result']['rows'])


def test_original_cohort_and_supplementary_source_scopes_are_explicit(bundle):
    _,files=bundle
    replay=json.loads(files['cohort/native-replay.json'])
    assert replay['points']==3411 and replay['mismatches']==[]
    assert replay['binary_sha256']=='aac26a213aa9a56de51f7d4de21977fa4a171c43947127dc7f8a7ebc163f0209'
    manifest=json.loads(files['cohort/manifest.json'])
    corrected=json.loads(files['biome-recheck/correct-runtime.json'])
    beta=json.loads(files['followup/biome-correct-runtime.json'])
    assert corrected['identity']['source_sha256']==manifest['source_sha256']
    assert beta['identity']['source_sha256']==manifest['source_sha256']
    assert len(corrected['rows'])==46 and len(beta['rows'])==137
    assert beta['outcomes']=={'match':137}
    # Obsolete analyses remain historical data, not evidence against this build.
    assert 'biome-recheck/obsolete-runtime.json' in files
    assert 'followup/biome-obsolete-runtime.json' in files
    addendum=json.loads(files['biome-recheck/frozen.json'])
    ledger=json.loads(files['biome-recheck/ledger.json'])
    assert len(ledger)==2 and all(r['state']=='complete' for r in ledger)
    for entry in ledger:
        prefix='biome-recheck/'+entry['dimension']+'/'
        report=json.loads(files[prefix+'report.json'])
        case=next(c for c in addendum['cases'] if c['dimension']==entry['dimension'])
        assert report['controls']['script_api']=='2.10.0'
        assert report['world_identity']['seed']==case['seed']
        assert report['world_identity']['dimension']==case['dimension']
        assert entry['source_unchanged'] is True
        assert digest(files[prefix+'report.json'])==entry['report_sha256']
        assert digest(files[prefix+'observer.js'])==report['controls']['observer_sha256']
        assert digest(files[prefix+'server.properties'])==report['controls']['settings_sha256']
        assert [[r['x'],r['y'],r['z']] for r in report['target_result']['rows']]==case['points']
        assert all(report[k] is True for k in ('clean_shutdown','owned_container_removed','save_confirmed'))


def test_saved_ceiling_witness_matches_exact_local_api_namespace():
    path = FIXTURE / 'stored-ceiling-witness-v1.json'
    raw = path.read_bytes()
    assert digest(raw) == (FIXTURE / 'stored-ceiling-witness-v1.sha256').read_text().strip()
    witness = json.loads(raw)
    record = witness['record']
    stored = bytes.fromhex(record['data'])
    assert digest(stored) == record['sha256']
    decoded = decode_data3d(stored)
    explicit = [s for s in decoded.sections if s.kind != 'unknown']
    assert max(s.section_y for s in explicit) * 16 + 15 == witness['top_explicit_plane'] == 95
    assert witness['export_provenance']['source_unchanged'] is True
    assert len(witness['api_rows']) == 21
    for row in witness['api_rows']:
        value = sample_bedrock_runtime(decoded, row['x'] % 16, row['y'], row['z'] % 16)
        assert witness['local_stored_id_associations'][str(value)] == row['id']
