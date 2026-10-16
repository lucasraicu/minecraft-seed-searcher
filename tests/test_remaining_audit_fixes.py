"""Behavioral regressions for the final follow-up audit's remaining findings."""
import copy
import http.client
import http.server
import json
import shlex
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from test_dynamic_v2_scoring import native_v2
from scripts.shard_campaign import partition_campaign
from scripts.merge_runs import merge_runs
from seed_search.realm.cli import load
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.realm.reports import _candidate_rescore
from seed_search.realm.store import RealmStore, canonical
from seed_search.web import server

ROOT = Path(__file__).resolve().parents[1]


def test_generated_campaign_resolves_v2_and_historical_budget(tmp_path):
    shard = partition_campaign(total_seeds=17, nodes=1)[0]
    cfg = load(shard.config)
    assert cfg['screening_revision'] == 'dynamic-envelope-1664-v2'
    assert cfg['terrain']['variants'] == []
    assert shard.max_misses == cfg['search']['max_misses'] == 3
    args = shlex.split(shard.cli_command.replace('\\\n', ''))[3:]
    output = args.index('--output') + 1
    args[output] = str(tmp_path / 'dry-run')
    result = subprocess.run([sys.executable, '-m', 'seed_search', *args, '--dry-run'], cwd=ROOT,
                            check=True, capture_output=True, text=True)
    planned = json.loads(result.stdout)
    assert (planned['start_index'], planned['planned_seeds'], planned['max_misses'], planned['executed_seeds']) == (0, 17, 3, 0)
    assert partition_campaign(total_seeds=1, nodes=1, config='config/realm_1664.yaml')[0].max_misses == 2
    assert partition_campaign(total_seeds=1, nodes=1, max_misses=1)[0].max_misses == 1
    with pytest.raises(ValueError):
        partition_campaign(total_seeds=1, nodes=1, max_misses=True)


@pytest.fixture
def positive_anchor(native_v2):
    with native_v2.sweep([456], fixtures=[(0, 0, -1)]) as batch:
        return batch.records()[0]['anchors'][0]


def test_rescore_reconstructs_spatial_and_variant_evidence(positive_anchor):
    row = positive_anchor
    cx, cz = row['evaluation_center']
    sx, sz = 64 * round(cx / 64), 64 * round(cz / 64)
    for sample in row['biomes']['sampling']['samples']:
        if sample['coordinate'][1] == 63:
            sample['biome'] = 'dark_forest'
        if sample['coordinate'] == [sx, 63, sz]:
            sample['biome'] = 'plains'
        if sample['coordinate'] == [sx + 64, 63, sz]:
            sample['biome'] = 'river'
    villages = row['required_structures']['village']['predicted_viable']
    villages[:3] = [[cx-200, cz-200], [cx+200, cz-200], [cx-200, cz+200]]
    row['bastion_variants'][0][2] = 2
    row.update(scenic_bonus=0, village_spread_bonus=0, treasure_bastion=0)
    rescored = _candidate_rescore(copy.deepcopy(row), {}, 'regression')
    comp = rescored['ranking']['components']
    assert rescored['scenic_bonus'] == comp['scenic_bonus'] == 20
    assert rescored['scenic_witness'] == [sx, sz]
    assert rescored['river_witness'] == [sx+64, sz]
    assert rescored['village_spread_bonus'] == comp['village_spread_bonus'] == 15
    assert len(rescored['village_triple']) == 3
    assert rescored['treasure_bastion'] == 1 and comp['treasure_bastion_bonus'] == 15
    row.update(scenic_bonus=20, village_spread_bonus=15, treasure_bastion=1)
    assert _candidate_rescore(row, {}, 'regression')['baseline_score'] == rescored['baseline_score']
    parsed = server.parse_candidate_row(rescored['seed'], rescored['baseline_score'], canonical(rescored))
    assert parsed['scenicBonus'] == parsed['scoreComponents']['scenic_bonus']
    assert parsed['villageSpreadBonus'] == parsed['scoreComponents']['village_spread_bonus']


@pytest.mark.parametrize('missing', ['variants', 'one_variant', 'surface'])
def test_rescore_does_not_convert_missing_evidence_to_zero(positive_anchor, missing):
    if missing == 'variants':
        positive_anchor.pop('bastion_variants')
    elif missing == 'one_variant':
        positive_anchor['bastion_variants'].pop()
    else:
        samples = positive_anchor['biomes']['sampling']['samples']
        samples.remove(next(row for row in samples if row['coordinate'][1] == 63))
    with pytest.raises(ValueError, match='retained.*evidence|retained.*variants'):
        _candidate_rescore(positive_anchor, {}, 'missing')


def test_reader_observes_external_progress_and_counters(tmp_path):
    cfg = dynamic_v2_blueprint_config()
    with RealmStore(tmp_path, {'config': cfg, 'retention': {'mode': 'survivors', 'max_misses': 3}}) as writer:
        writer.configure_range(0, 1, 1)
        with RealmStore(tmp_path, resume=True) as reader:
            assert reader.status()['completed_seeds'] == 0
            writer.claim_range('writer')
            receipt = {'version': 'native-retention-receipt-v1', 'inputs': 1, 'retained_inputs': 0,
                       'retained_anchors': 0, 'discovered_anchors': 0, 'input_decisions_sha256': 'e'*64}
            writer.complete_prepared(writer.prepare_retained_range(0, 1, [], receipt))
            assert reader.status()['completed_seeds'] == 1
            assert reader.get_state('counts')['scanned_inputs'] == 1


def test_merge_v2_summary_uses_score_before_deficits(tmp_path):
    cfg = dynamic_v2_blueprint_config()
    sources = []
    for i, (score, deficits) in enumerate([(100, ['village']), (50, [])]):
        source = tmp_path / str(i)
        sources.append(source)
        with RealmStore(source, {'config': cfg}) as store:
            store.configure_range(i, i+1, 1)
            row = {'id': f'{i}:0:0', 'seed': str(i), 'screening_revision': cfg['screening_revision'],
                   'baseline_score': score, 'deficit_categories': deficits, 'evaluation_center': [0, 0],
                   'radial_key': 0, 'origin_distance_squared': 0}
            with store.db:
                store.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?)',
                                 (row['id'], str(i), str(i), 'PREDICTED', canonical(row)))
                store.db.execute("UPDATE ranges SET status='complete'")
    merged = merge_runs(sources, tmp_path / 'aggregate')
    assert [row['seed'] for row in merged['top_candidates']] == ['0', '1']


def test_http_pagination_reaches_beyond_old_cap(monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path / 'no-web-runs')
    manager = server.SweepManager()
    manager.run_dir = tmp_path / 'run'
    with RealmStore(manager.run_dir, {'config': dynamic_v2_blueprint_config()}) as store:
        with store.db:
            store.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?)', [
                (f'{i}:0:0', str(i), str(i), 'PREDICTED', canonical({
                    'id': f'{i}:0:0', 'seed': str(i), 'screening_revision': 'dynamic-envelope-1664-v2',
                    'baseline_score': i, 'deficit_categories': [], 'evaluation_center': [0, 0]}))
                for i in range(5101)])
        monkeypatch.setattr(server, 'MANAGER', manager)
        httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), server.WebSearchHandler)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        try:
            def get(query):
                conn = http.client.HTTPConnection(*httpd.server_address, timeout=10)
                try:
                    conn.request('GET', '/api/candidates' + query)
                    response = conn.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    conn.close()
            status, first = get('?limit=100&offset=0')
            assert status == 200 and first['total'] == 5101
            assert len(first['candidates']) == 100 and first['candidates'][0]['seed'] == '5100'
            status, last = get('?limit=100&offset=5100')
            assert status == 200 and last['total'] == 5101
            assert [c['seed'] for c in last['candidates']] == ['0']
            for query in ('?offset=-1', '?limit=0', '?limit=251', '?offset=x'):
                assert get(query)[0] == 400
            assert manager.candidates == []  # Page reads do not materialize the full database into the pool.
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join(timeout=5)


def test_suggestions_are_distinct_from_initial_spawn_and_inspections(positive_anchor):
    parsed = server.parse_candidate_row(positive_anchor['seed'], positive_anchor['baseline_score'], canonical(positive_anchor))
    assert parsed['suggestedSpawn']['status'] == 'PREDICTED_SCENIC_SUGGESTION'
    assert parsed['spawnPoint'] is None
    assert all(row['status'] == 'UNVERIFIED' for row in parsed['playerInspections'].values())
    positive_anchor['player_inspections']['end_access'] = {
        'status': 'OBSERVED', 'reason': 'Portal room reached during manual inspection',
        'source': {'kind': 'manual_inspection', 'provider': 'player', 'version': '26.52'}}
    parsed = server.parse_candidate_row(positive_anchor['seed'], positive_anchor['baseline_score'], canonical(positive_anchor))
    assert parsed['playerInspections']['end_access']['source']['kind'] == 'manual_inspection'


def test_real_native_launch_persists_explicit_budget_and_resume_preserves_it(native_v2, tmp_path, capsys):
    from seed_search.realm.cli import main
    run = tmp_path / 'budget-override'
    main(['--config', 'config/realm.yaml', 'scan', '--executor', 'native',
          '--native-build', str(native_v2.directory), '--native-threads', '1',
          '--native-batch-size', '2', '--retention', 'survivors', '--max-misses', '1',
          '--count', '2', '--output', str(run)])
    with RealmStore(run, resume=True) as store:
        assert store.identity['config']['search']['max_misses'] == 1
        assert store.retention['max_misses'] == 1
        assert store.status()['completed_seeds'] == 2
    main(['resume', '--run', str(run)])
    with RealmStore(run, resume=True) as store:
        assert store.identity['config']['search']['max_misses'] == 1
        assert store.status()['completed_seeds'] == 2
    capsys.readouterr()
