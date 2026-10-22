"""Manifest, dry-run, and immutable replay guards without starting any worlds."""
import copy
import json
from pathlib import Path
import pytest
from scripts import generalization_audit as audit


def manifest():
    worlds = [dict(index=i, seed=str(i), group='blind' if i < 16 else 'targeted',
                   predictions=[dict(position=[-1, 63, -1], dimension='overworld', biome_name='plains', sample_group='fixed')],
                   structures=[dict(case_id=f'{i}-0', structure_type='village', command_id='village',
                     dimension='overworld', origin=[0, 0], predicted=[0, 0], disposition='retained')]) for i in range(24)]
    return dict(revision='generalization-cohort-v1', image_id=audit.IMAGE, bds_build='1.26.52.3',
        prediction_revision='cubiomes-bedrock-26.50', script_api='2.10.0', worlds=worlds,
        pilot_indices=[0, 16, 1, 17, 2])


def test_dry_run_never_creates_output_or_calls_docker(tmp_path, monkeypatch):
    p = tmp_path/'manifest.json'; p.write_text(json.dumps(manifest()))
    monkeypatch.setattr(audit.subprocess, 'Popen', lambda *a, **kw: pytest.fail('Game launch'))
    monkeypatch.setattr(audit.subprocess, 'check_output', lambda *a, **kw: pytest.fail('Docker lookup'))
    out = tmp_path/'not-created'
    result = audit.run(p, out, phase='pilot')
    assert result['dry_run'] and result['budget'] == dict(worlds=24, biome_reads=24, locates=24)
    assert not out.exists()


@pytest.mark.parametrize('change', [
    lambda m: m['worlds'][0].update(seed='01'),
    lambda m: m['worlds'][0].update(seed=str(2**63)),
    lambda m: m['worlds'][0].update(group='targeted'),
    lambda m: m['worlds'][0]['predictions'][0]['position'].__setitem__(0, True),
    lambda m: m['worlds'][0]['predictions'][0]['position'].__setitem__(1, 320),
    lambda m: m['worlds'][0]['predictions'].append(copy.deepcopy(m['worlds'][0]['predictions'][0])),
    lambda m: m['worlds'][0]['structures'][0].update(command_id='village; stop'),
    lambda m: m['worlds'][0]['structures'][0].update(dimension='nether'),
    lambda m: m['worlds'][0]['structures'][0].update(disposition='discovery'),
    lambda m: m['worlds'][0]['structures'][0].update(predicted=None),
    lambda m: m['worlds'][0]['structures'][0]['origin'].__setitem__(0, 5121),
    lambda m: m.update(image_id='unpinned'),
    lambda m: m.update(pilot_indices=[0, 1, 2, 3, 4]),
])
def test_invalid_cases_fail_before_dispatch(change):
    m = manifest(); change(m)
    with pytest.raises(ValueError): audit.validate_manifest(m)


def test_all_bounds_and_supported_dimensions():
    m = manifest()
    q = m['worlds'][0]['structures'][0]
    q.update(structure_type='fortress', command_id='fortress', dimension='nether')
    p = m['worlds'][0]['predictions'][0]
    p.update(dimension='nether', position=[-5120, 127, 5120])
    assert audit.validate_manifest(m)['worlds'] == 24
    p['position'][1] = 128
    with pytest.raises(ValueError): audit.validate_manifest(m)


def test_symlink_external_output_is_rejected(tmp_path):
    p = tmp_path/'manifest.json'; p.write_text(json.dumps(manifest()))
    target = tmp_path/'real'; target.mkdir()
    link = tmp_path/'alias'; link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='Symlink'):
        audit.run(p, link/'child', phase='pilot', execute=True)


def test_failed_ledger_never_dispatches(tmp_path, monkeypatch):
    p = tmp_path/'manifest.json'; p.write_text(json.dumps(manifest()))
    out = tmp_path/'out'; out.mkdir()
    (out/'ledger.json').write_text(json.dumps([dict(index=0, state='failed', wall_seconds=12)]))
    monkeypatch.setattr(audit, 'run_world', lambda *a, **k: pytest.fail('Unexpected retry'))
    with pytest.raises(ValueError, match='Reconcile'):
        audit.run(p, out, phase='pilot', execute=True)


def test_ledger_report_corruption_rejected_before_docker(tmp_path, monkeypatch):
    p = tmp_path/'manifest.json'; p.write_text(json.dumps(manifest()))
    out = tmp_path/'out'; out.mkdir()
    (out/'ledger.json').write_text(json.dumps([dict(index=0, state='complete', wall_seconds=12, report_sha256='a'*64)]))
    monkeypatch.setattr(audit.subprocess, 'check_output', lambda *a, **k: pytest.fail('Docker called'))
    with pytest.raises(ValueError, match='report changed or is missing'):
        audit.run(p, out, phase='pilot', execute=True)


def test_explicit_resume_reuses_world_and_charges_previous_time(tmp_path, monkeypatch):
    p=tmp_path/'manifest.json';raw=json.dumps(manifest()).encode();p.write_bytes(raw)
    out=tmp_path/'out';old=out/'world-00';old.mkdir(parents=True)
    report=dict(status='failed',seed='0',manifest_sha256=audit.digest(raw),wall_seconds=120.,
        clean_shutdown=True,owned_container_removed=True)
    prior=old/'report.json';audit.atomic_json(prior,report);before=prior.read_bytes()
    audit.atomic_json(out/'ledger.json',[dict(index=0,state='failed',wall_seconds=120.,seed='0',report_sha256=audit.digest(before))])
    monkeypatch.setattr(audit.shutil,'which',lambda _: 'docker')
    monkeypatch.setattr(audit.subprocess,'check_output',lambda *a,**k:(audit.IMAGE+'\n').encode().decode())
    class Captured(Exception):pass
    def capture(world,directory,**kwargs):
        assert directory==out/'world-00-resume-1' and kwargs['resume_from']==old
        assert kwargs['seconds']==480 and world['seed']=='0'
        raise Captured
    monkeypatch.setattr(audit,'run_world',capture)
    with pytest.raises(Captured):audit.run(p,out,phase='pilot',execute=True,resume_index=0)
    assert prior.read_bytes()==before


def test_second_resume_is_not_automatic_or_unbounded(tmp_path,monkeypatch):
    p=tmp_path/'manifest.json';raw=json.dumps(manifest()).encode();p.write_bytes(raw)
    out=tmp_path/'out';old=out/'world-00';old.mkdir(parents=True)
    report=dict(status='failed',seed='0',manifest_sha256=audit.digest(raw),wall_seconds=120.,
        clean_shutdown=True,owned_container_removed=True,resumed_from={'previous_wall_seconds':20})
    prior=old/'report.json';audit.atomic_json(prior,report)
    audit.atomic_json(out/'ledger.json',[dict(index=0,state='failed',wall_seconds=120.,seed='0',report_sha256=audit.digest(prior.read_bytes()))])
    monkeypatch.setattr(audit.subprocess,'check_output',lambda *a,**k:pytest.fail('No dispatch before review'))
    with pytest.raises(ValueError,match='cannot safely resume'):
        audit.run(p,out,phase='pilot',execute=True,resume_index=0)
