"""Reporting must reject changed evidence even under Python optimization."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.generalization_report import analyze


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def campaign(tmp_path):
    manifest = dict(worlds=[dict(index=0, seed='1', group='blind', predictions=[], structures=[], inventory={})],
                    aliases={}, non_comparable=[], image_id='pinned', script_api='2.10.0',
                    prediction_revision='cubiomes-bedrock-26.50', bds_build='1.26.52.3')
    raw = json.dumps(manifest).encode()
    (tmp_path / 'manifest.json').write_bytes(raw)
    (tmp_path / 'manifest.sha256').write_text(digest(raw))
    directory = tmp_path / 'game/world-00'
    directory.mkdir(parents=True)
    work = directory / 'worlds/world'
    work.mkdir(parents=True)
    (work / 'server.properties').write_bytes(b'level-seed=1\n')
    (directory / 'observer.js').write_bytes(b'// frozen observer\n')
    (directory / 'console.log').write_text('Version: 1.26.52.3\n')
    report = dict(status='observed', seed='1', manifest_sha256=digest(raw), image_id='pinned',
                  world_identity=dict(seed='1', api='2.10.0', players=0),
                  settings_sha256=digest((work / 'server.properties').read_bytes()),
                  observer_sha256=digest((directory / 'observer.js').read_bytes()),
                  clean_shutdown=True, owned_container_removed=True, save_confirmed=True,
                  game_build_observed=True, queries=[], biome_batches=[], wall_seconds=1.5)
    (directory / 'report.json').write_text(json.dumps(report))
    ledger = [dict(index=0, state='complete', report_sha256=digest((directory / 'report.json').read_bytes()))]
    (tmp_path / 'game/ledger.json').write_text(json.dumps(ledger))
    return tmp_path


def test_complete_report_binds_frozen_artifacts(campaign):
    result = analyze(campaign)
    assert result['completed'] == 1 and result['game_wall_seconds'] == 1.5
    report = json.loads((campaign / 'results.json').read_text())
    assert report['exhaustive_count'] is None
    assert report['all_supported_features_verified'] is False
    assert report['prediction_verdict'] == 'no_counterexample_observed_in_this_sample'


@pytest.mark.parametrize('filename,message', [('manifest.json', 'Manifest checksum'),
    ('game/world-00/report.json', 'Report checksum'),
    ('game/world-00/observer.js', 'Observer checksum'),
    ('game/world-00/worlds/world/server.properties', 'Settings checksum')])
def test_changed_evidence_is_rejected(campaign, filename, message):
    path = campaign / filename
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match=message):
        analyze(campaign)


def test_inflight_world_is_not_counted_complete(campaign):
    ledger = json.loads((campaign / 'game/ledger.json').read_text())
    ledger[0]['state'] = 'starting'
    (campaign / 'game/ledger.json').write_text(json.dumps(ledger))
    assert analyze(campaign, partial=True)['completed'] == 0
    with pytest.raises(ValueError, match='ledger not complete'):
        analyze(campaign)


def test_checks_remain_enabled_with_python_optimization(campaign):
    (campaign / 'manifest.sha256').write_text('not the manifest digest')
    root = Path(__file__).resolve().parents[1]
    process = subprocess.run([sys.executable, '-O', str(root / 'scripts/generalization_report.py'),
                              '--campaign', str(campaign)], capture_output=True, text=True, timeout=15)
    assert process.returncode != 0
    assert 'Manifest checksum differs' in process.stderr
    assert not (campaign / 'results.json').exists()
