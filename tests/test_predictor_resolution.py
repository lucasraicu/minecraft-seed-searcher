"""Independent regression cases for repeat decoding and corrected biome identity."""
import json
from pathlib import Path
import struct

import pytest

from seed_search.realm.bedrock_biome_storage import decode_data3d, resolve_repeated_sections
from seed_search.realm.biomes import canonical, classify
from seed_search.realm.config import default_config
from scripts.predictor_storage_probe import compare_points

ROOT = Path(__file__).resolve().parents[1]


def test_repeat_copies_whole_asymmetric_array_and_preserves_raw_markers():
    # X/Z/Y-dependent 8-bit indices; independent byte packing, no production encoder.
    indices = bytes((x * 7 + z * 3 + y) % 11 for x in range(16) for z in range(16) for y in range(16))
    raw = bytes(512) + b'\x11' + indices + struct.pack('<I11I', 11, *range(100, 111)) + b'\xff\xff'
    original = decode_data3d(raw)
    resolved = resolve_repeated_sections(original)
    assert original.sample(9, -40, 7) is None
    for x, z, y in [(0, 0, 0), (9, 7, 8), (15, 2, 13), (1, 15, 15)]:
        for floor in [-64, -48, -32]:
            assert resolved.sample(x, floor + y, z) == 100 + (x * 7 + z * 3 + y) % 11
    assert resolved.sample(0, -16, 0) is None  # absent section is never inherited


def test_leading_repeat_is_rejected_and_wrong_input_fails():
    with pytest.raises(ValueError, match='previous contiguous'):
        resolve_repeated_sections(decode_data3d(bytes(512) + b'\xff'))
    with pytest.raises(TypeError):
        resolve_repeated_sections(None)


def test_explicit_repeat_replay_recovers_six_values_without_filling_absent_records():
    total = repeated = missing = 0
    expected = [[12, 30, 30, 185, 5], [35]]
    for world in (0, 1):
        base = ROOT / f'fixtures/bedrock-26.52/storage-regressions/world-{world}'
        export = json.loads((base / 'export.json').read_text())
        old = json.loads((base / 'comparison.json').read_text())
        points = [r['position'] for r in old['rows']]
        strict = compare_points(export, points)
        assert strict == old
        result = compare_points(export, points, resolve_repeats=True)
        assert result['revision'] == 'stored-biome-point-diagnostics-v2'
        inherited = [r['stored_id'] for r in result['rows'] if r['status'] == 'stored_repeated']
        assert inherited == expected[world]
        total += result['stored']
        repeated += len(inherited)
        missing += result['unknown']
    assert (total, repeated, missing) == (33, 6, 21)


def test_spruce_identity_is_correct_on_three_independent_recorded_seeds():
    base = ROOT / 'fixtures/bedrock-26.52/predictor-corrections'
    rows = json.loads((base / 'cohort-biome-scale-comparison.json').read_text())['rows']
    spruce = [r for r in rows if r['id'] == 'minecraft:redwood_taiga_mutated']
    assert len(spruce) == 6
    assert len({r['seed'] for r in spruce}) == 3
    assert all(canonical(r['id']) == r['direct_quart'] == 'old_growth_spruce_taiga' for r in spruce)
    # Raw historical aliases remain unchanged; new behavior is tested separately.
    assert json.loads((base / 'manifest.json').read_text())['aliases']['redwood_taiga_mutated'] == 'taiga'
    assert canonical('minecraft:redwood_taiga_hills_mutated') == 'old_growth_spruce_taiga'
    policy = default_config()['biomes']
    assert classify(['minecraft:redwood_taiga_mutated'], policy) == classify(['old_growth_spruce_taiga'], policy)
    assert canonical('mega_taiga') == 'old_growth_pine_taiga'
    assert canonical('taiga_mutated') == 'taiga'


def test_resolution_fixture_binds_membership_to_game_and_keeps_locate_separate():
    from seed_search.realm.predictor_resolution import resolution_report
    report = resolution_report(ROOT / 'fixtures/bedrock-26.52/predictor-resolution')
    rows = [r for r in report['structure_presence'] if r['seed'] == '-9103892851552028103' and r['position'] == [820, 16, -1708]]
    assert len(rows) == 1
    assert rows[0]['structures'] == ['minecraft:stronghold']
    assert rows[0]['block'] == 'minecraft:air'
    q = next(r for r in report['locate_disagreements'] if r['feature'] == 'structure.stronghold')
    assert q['query'] == [820, -1708] and q['reported'] == [98, -2030]
    # A remote locate does not override physical presence. Empty membership does
    # not create fabricated absent structures or a certified zero count.
    assert all(r['structures'] for r in report['structure_presence'])
    assert not any('absent' in r for r in report['structure_presence'])
    assert [(r['stored'], r['unknown']) for r in report['persistence'] if r['mode'] == 'dirty_restore'] == [(70, 0), (8, 0)]


def test_resolution_fixture_corruption_fails_closed(tmp_path):
    import shutil
    from seed_search.realm.predictor_resolution import resolution_report
    root = tmp_path / 'fixtures'
    shutil.copytree(ROOT / 'fixtures/bedrock-26.52/predictor-resolution', root)
    target = root / 'membership/world-1/report.json'
    data = json.loads(target.read_text())
    data['target_result']['rows'][0]['structures'] = []
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='hash'):
        resolution_report(root)


def test_frozen_lifecycle_protocol_is_bounded_and_does_not_mutate_source():
    from scripts.predictor_lifecycle_bds import freeze_cases
    original = json.loads((ROOT / 'reviews/storage-bds-verification-2026-10-20/CASES.json').read_text())
    before = json.dumps(original, sort_keys=True)
    cases, budget = freeze_cases(original)
    assert json.dumps(original, sort_keys=True) == before
    assert len(cases[0]['points']) == 63
    assert budget['worlds'] == 4
    assert budget['biome_reads'] == 156
    assert budget['block_reads'] == 7148
    assert budget['locate_commands'] == 24
    assert budget['dwell_ticks'] == 200
    assert budget['protocols'] == ['read_only', 'dirty_restore']


def test_empty_membership_points_remain_explicitly_unconfirmed():
    from seed_search.realm.predictor_resolution import resolution_report
    report = resolution_report(ROOT / 'fixtures/bedrock-26.52/predictor-resolution')
    rows = report['structure_membership']
    assert len(rows) == 37
    empty = [r for r in rows if not r['structures']]
    assert empty and all(r['status'] == 'unconfirmed_at_point' for r in empty)
    assert any(r['position'] == [-296, 77, -312] for r in empty)


def test_corrupted_sections_never_become_unknown_repeat_markers():
    # The raw decoder fails on corruption; only intentional 0xff creates unknown.
    with pytest.raises(ValueError, match='truncated uniform'):
        resolve_repeated_sections(decode_data3d(bytes(512) + b'\x01\x01'))
    with pytest.raises(ValueError, match='unsupported'):
        resolve_repeated_sections(decode_data3d(bytes(512) + b'\x0f'))


def test_full_vertical_membership_preserves_positive_controls_without_absence_claims():
    from seed_search.realm.predictor_resolution import resolution_report
    report = resolution_report(ROOT / 'fixtures/bedrock-26.52/predictor-resolution')
    columns = {(r['seed'], r['x'], r['z']): r for r in report['structure_membership_columns']}
    seed = '-3509659830737203357'
    good = columns[(seed, -360, 248)]
    assert any(v['structures'] == ['minecraft:village'] and v['from'] == 75 and v['to'] == 118 for v in good['intervals'])
    for x, z, kind in [(-296, -312, 'minecraft:village'), (536, 520, 'minecraft:pillager_outpost')]:
        row = columns[(seed, x, z)]
        assert not any(kind in v['structures'] for v in row['intervals'])
        assert 'not an exhaustive' in row['interpretation']
        assert any('minecraft:ancient_city' in v['structures'] for v in row['intervals'])
    stronghold = columns[('-9103892851552028103', 820, -1708)]
    assert any('minecraft:stronghold' in v['structures'] for v in stronghold['intervals'])


def test_all_original_storage_points_are_recovered_in_fresh_persisted_worlds():
    base = ROOT / 'fixtures/bedrock-26.52/predictor-resolution'
    recovered = json.loads((base / 'old54-recovered.json').read_text())
    for world in (0, 1):
        old = json.loads((ROOT / f'fixtures/bedrock-26.52/storage-regressions/world-{world}/comparison.json').read_text())
        export = json.loads((base / f'lifecycle/dirty_restore-{world}/export.json').read_text())
        result = compare_points(export, [r['position'] for r in old['rows']], resolve_repeats=True)
        assert result == recovered[world]
        assert result['unknown'] == 0
    assert sum(r['stored'] for r in recovered) == 54


def test_full_candidate_chunks_keep_count_semantics_separate():
    from seed_search.realm.predictor_resolution import resolution_report
    report = resolution_report(ROOT / 'fixtures/bedrock-26.52/predictor-resolution')
    volume = report['structure_membership_volumes']
    chunks = volume['volumes']
    assert len(chunks) == 4 and sum(v['evaluatedPositions'] for v in chunks) == 393216
    assert 'minecraft:village' not in chunks[0]['counts']
    assert chunks[1]['counts']['minecraft:village'] == 11264
    assert 'minecraft:pillager_outpost' not in chunks[2]['counts']
    assert chunks[3]['counts']['minecraft:pillager_outpost'] == 5632
    assert 'not structure counts' in volume['interpretation']
