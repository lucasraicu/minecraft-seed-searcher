"""Actual compiled helper versus retained independent Bedrock observations."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile

import pytest

from scripts.build_spawn_estimator import ROOT, build_spawn_estimator


@pytest.fixture(scope='module')
def reference_helper(tmp_path_factory):
    return build_spawn_estimator(tmp_path_factory.mktemp('world-spawn')/'reference')


def retained_controls():
    base=ROOT/'reviews/spawn-validation-2026-10-17'
    observed=json.loads((base/'bds-cohort.json').read_text())
    saved={r['label']:r for r in json.loads((base/'persisted-metadata.json').read_text())}
    expected={}
    for row in observed:
        assert row['status']=='observed' and row['clean_shutdown'] is True
        record=saved[row['label']]
        assert record['seed']==row['seed']
        for phase in ('world_load','world_tick20','world_tick40'):
            point=next(r for r in row['rows'] if r['phase']==phase)
            assert point['defaultSpawn']==record['spawn'] and point['players']==0
        expected[row['seed']]=[record['spawn']['x'],record['spawn']['z']]
    assert len(expected)==108
    evidence=ROOT/'fixtures/bedrock-26.52/accuracy-expansion'
    manifest=json.loads((evidence/'manifest.json').read_text())
    archive=evidence/manifest['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as source:
        def read(name):
            member=source.getmember(name)
            assert member.isfile() and member.size<=4<<20
            data=source.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest()==manifest['files'][name]['sha256']
            return data
        worlds=json.loads(read('protocol/frozen.json'))['worlds']
        assert len(worlds)==8
        for i,world in enumerate(worlds):
            report=json.loads(read(f'fresh/{i:02}/report.json'))
            export=json.loads(read(f'fresh/{i:02}/export.json'))
            assert report['clean_shutdown'] is report['save_confirmed'] is True
            assert report['world_identity']['players']==0
            assert export['world_identity']['level_dat_sha256']==hashlib.sha256(read(f'fresh/{i:02}/level.dat')).hexdigest()
            saved=export['world_identity']['world_spawn']
            actual=report['world_identity']['worldSpawn']
            assert [actual['x'],actual['z']]==[saved['SpawnX'],saved['SpawnZ']]
            assert export['world_identity']['seed']==world['seed']
            assert world['seed'] not in expected
            expected[world['seed']]=[actual['x'],actual['z']]
    assert len(expected)==116
    return expected


def test_real_helper_matches_all_retained_game_world_references(reference_helper):
    expected=retained_controls()
    result=subprocess.run([str(reference_helper)],input=''.join(seed+'\n' for seed in expected),
                          capture_output=True,text=True,check=True,timeout=15)
    rows=[json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows)==116 and [r['seed'] for r in rows]==list(expected)
    for row in rows:
        assert row['estimate']==row['repeat_estimate']==expected[row['seed']],row['seed']
    manifest=json.loads(Path(str(reference_helper)+'.build.json').read_text())
    finders=ROOT/'vendor/cubiomes-bedrock/finders.c'
    assert manifest['input_source_hashes']['vendor/cubiomes-bedrock/finders.c']==hashlib.sha256(finders.read_bytes()).hexdigest()
    assert str(finders) not in manifest['command']  # Included once in the helper TU.


def test_real_helper_matches_frozen_fresh_game_controls(reference_helper):
    base=ROOT/'fixtures/bedrock-26.52/spawn-correction'
    manifest=json.loads((base/'manifest.json').read_text());archive=base/manifest['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as source:
        files={}
        for member in source.getmembers():
            assert member.isfile() and member.size<=4<<20 and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            data=source.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest()==manifest['files'][member.name]['sha256']
            files[member.name]=data
    assert set(files)==set(manifest['files'])
    summary=json.loads(files['summary.json']);rows=json.loads(files['results.json'])
    protocol=json.loads(files['frozen-protocol.json'])
    assert summary['matches']==summary['completed']==len(rows)==8 and summary['error'] is None
    assert summary['owned_containers_removed'] is True
    assert [r['seed'] for r in rows]==protocol['seeds']
    assert not set(protocol['seeds']) & set(retained_controls())
    result=subprocess.run([str(reference_helper)],input=''.join(r['seed']+'\n' for r in rows),
        capture_output=True,text=True,check=True,timeout=10)
    for i,(pred,row) in enumerate(zip(map(json.loads,result.stdout.splitlines()),rows,strict=True)):
        assert row['clean_shutdown'] and row['status']=='match' and row['saved']['seed']==pred['seed']==row['seed']
        assert hashlib.sha256(files[f'level-{i}.dat']).hexdigest()==row['level_dat_sha256']
        assert pred['estimate']==pred['repeat_estimate']==[row['saved']['spawn']['x'],row['saved']['spawn']['z']]
        for observation in row['observations']:
            assert observation['defaultSpawn']==row['saved']['spawn'] and observation['players']==0


@pytest.mark.parametrize('seed',['+1','01','-0','9223372036854775808','-9223372036854775809','1x'])
def test_real_helper_rejects_noncanonical_or_out_of_range_seed(reference_helper,seed):
    result=subprocess.run([str(reference_helper)],input=seed+'\n',capture_output=True,text=True,timeout=5)
    assert result.returncode!=0 and result.stdout==''
