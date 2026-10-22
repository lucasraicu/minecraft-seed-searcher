"""Reviewed exclusions, immutable audit lineage and precommit readiness."""
import copy

import pytest

from seed_search.catalog.corrections import (derive_observation, rebind_summary,
    rebind_evidence, reviewed_ledger, METHOD)
from seed_search.catalog.codec import pack_summary
from seed_search.catalog.coverage import complete_for
from seed_search.catalog.evidence import build_evidence, write_evidence, read_evidence
from seed_search.catalog.models import identity, empty_observation, world_id, observation_id
from seed_search.catalog.registry import ENVELOPE, digest
from seed_search.catalog.geometry import bounds_for
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.summaries import summarize


def source(seed='123'):
    obs = empty_observation(identity(seed, model_id='26.50', native_sha256='a'*64, source_sha256='b'*64))
    obs['structures']={'structure.village':[[-296,-312],[100,100]],'structure.outpost':[[528,512],[200,200]]}
    for f in obs['structures']:
        obs['coverage'][f]=dict(status='complete',bounds=list(ENVELOPE),method_id='predictor_viable_starts_v1')
    return obs


def ledger_for(obs):
    return dict(source_header={k:v for k,v in obs['identity'].items() if k!='seed'},
                source_snapshot_id='1'*64,removals=[dict(seed=obs['identity']['seed'],
                world_id=world_id(obs['identity']),observation_id=observation_id(obs),
                feature_id='structure.village',position=[-296,-312])])


def audit(obs, sid='1'*64):
    verifier=dict(edition='bedrock',game_build_id='1.26.52.3',image_sha256='c'*64,
                  script_api='2.10.0',settings_sha256='d'*64,report_sha256s=['e'*64])
    return build_evidence(obs,sid,verifier,[dict(feature_id='structure.village',command_id='village',
        predicted=p,reported=p,outcome='located_exact') for p in obs['structures']['structure.village']])


def test_pinned_ledger_and_corruption(tmp_path):
    ledger=reviewed_ledger()
    assert len(ledger['removals'])==2
    from seed_search.catalog.corrections import LEDGER
    changed=tmp_path/'ledger.json';changed.write_bytes(LEDGER.read_bytes()+b' ')
    with pytest.raises(ValueError,match='reviewed ledger'):
        reviewed_ledger(changed)


def test_transform_is_scoped_and_keeps_full_provenance():
    original=source(); baseline=copy.deepcopy(original); ledger=ledger_for(original); e=audit(original)
    new=derive_observation(original,ledger,evidence=e)
    assert original==baseline
    assert new['structures']['structure.village']==[[100,100]]
    assert new['structures']['structure.outpost']==original['structures']['structure.outpost']
    assert new['biomes']==original['biomes']
    p=new['metrics']['transformation_provenance']
    assert p['source_identity']==original['identity']
    assert p['source_observation_id']==observation_id(original)
    assert p['source_evidence_sha256']==digest(e)
    assert p['excluded_structure_checks']==[e['structure_checks'][0]]
    assert new['identity']['native_sha256']==original['identity']['native_sha256']
    assert new['identity']['source_sha256']!=original['identity']['source_sha256']
    assert new['coverage']['structure.village']['method_id']==METHOD
    assert complete_for(new,'structure.village',[0,0],2048)
    assert derive_observation(original,ledger,evidence=e)==new
    rows=summarize(new); old=summarize(original)
    assert len(rows)==len(old)==243
    for a,b in zip(rows,old):
        lo_x,lo_z,hi_x,hi_z=bounds_for(a['anchor'],a['border_side'])
        inside=lo_x<=-296<hi_x and lo_z<=-312<hi_z
        d2=(-296-a['anchor'][0])**2+(-312-a['anchor'][1])**2
        for scope,radius in enumerate((256,512,1024,None)):
            excluded=inside and (radius is None or d2<=radius*radius)
            assert a['counts'][0][scope]==b['counts'][0][scope]-int(excluded)
        assert a['counts'][1:]==b['counts'][1:]
        assert a['complete']==b['complete']
    with pytest.raises(ValueError): derive_observation(new,ledger)


@pytest.mark.parametrize('change', ['settings','source','oid','missing','audit_snapshot'])
def test_fail_closed_source_binding(change):
    obs=source();ledger=ledger_for(obs);e=audit(obs)
    if change=='settings':obs['identity']['world_settings_id']='other'
    if change=='source':obs['identity']['source_sha256']='c'*64
    if change=='oid':obs['metrics']['unreviewed']=True
    if change=='missing':
        obs['structures']['structure.village'].pop(0)
        ledger['removals'][0]['observation_id']=observation_id(obs)
        e=audit(obs)
    if change=='audit_snapshot':e['snapshot_id']='2'*64
    with pytest.raises(ValueError):derive_observation(obs,ledger,evidence=e)


def test_unchanged_world_summary_bytes_and_audit_rebinding():
    obs=source(); ledger=ledger_for(obs);ledger['removals']=[];e=audit(obs)
    new=derive_observation(obs,ledger,evidence=e)
    old=summarize(obs)[0]; row=rebind_summary(old,obs,new)
    assert pack_summary(row)==pack_summary(old)
    assert row['layout_id']!=old['layout_id']
    assert row['world_id']!=old['world_id']
    rebound=rebind_evidence(e,obs,new,'2'*64)
    assert rebound['verifier']==e['verifier']
    assert rebound['structure_checks']==e['structure_checks']
    bad=copy.deepcopy(new);bad['structures']['structure.village']=[]
    with pytest.raises(ValueError):rebind_summary(old,obs,bad)


def test_excluded_audit_rows_preserved_in_source_and_ledger():
    obs=source();ledger=ledger_for(obs);e=audit(obs);baseline=copy.deepcopy(e)
    new=derive_observation(obs,ledger,evidence=e)
    rebound=rebind_evidence(e,obs,new,'2'*64)
    assert e==baseline
    assert rebound['structure_checks']==[e['structure_checks'][1]]
    assert new['metrics']['transformation_provenance']['excluded_structure_checks']==[e['structure_checks'][0]]
    assert rebound['verifier']==e['verifier']
    new['metrics']['transformation_provenance']['source_evidence_sha256']='a'*64
    with pytest.raises(ValueError):rebind_evidence(e,obs,new,'2'*64)


def test_precommit_readiness_isolation_and_rollback(tmp_path):
    root=tmp_path/'cat'
    with SegmentedCatalog(root) as s:
        obs=source();sid=s.publish([obs],summarize(obs))
        other=source('456');e=audit(other); prepared=[]
        # Second connection must observe only the previous committed generation.
        with SegmentedCatalog(root) as reader:
            def fail(current,new_sid):
                assert current.info()['snapshot_id']==new_sid
                assert reader.info()['snapshot_id']==sid
                prepared.append(new_sid)
                write_evidence(root,build_evidence(other,new_sid,e['verifier'],e['structure_checks']))
                raise RuntimeError('Preview interrupted')
            with pytest.raises(RuntimeError,match='interrupted'):
                s.publish([other],summarize(other),parent=sid,prepare_publication=fail)
            assert s.info()['snapshot_id']==reader.info()['snapshot_id']==sid
            assert len(s.snapshots())==1
            def ready(current,new_sid):
                assert reader.info()['snapshot_id']==sid
                with SegmentedCatalog(root) as fresh_reader:
                    assert fresh_reader.info()['snapshot_id']==sid
                assert new_sid==prepared[0]
                payload=build_evidence(other,new_sid,e['verifier'],e['structure_checks'])
                write_evidence(root,payload) # idempotent orphan from failed attempt
                assert read_evidence(root,new_sid,world_id(other['identity']),observation_id(other))==payload
            new_sid=s.publish([other],summarize(other),parent=sid,prepare_publication=ready)
            assert reader.info()['snapshot_id']==new_sid
            assert s.observation(sid,world_id(obs['identity']))==obs
            assert s.conn.execute('PRAGMA integrity_check').fetchone()==('ok',)


def test_process_exit_during_readiness_never_selects_snapshot(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root=tmp_path/'cat'
    with SegmentedCatalog(root) as s:
        obs=source();sid=s.publish([obs],summarize(obs))
    child='''
import json,os,sys
from pathlib import Path
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.summaries import summarize
obs=json.load(sys.stdin)
with SegmentedCatalog(sys.argv[1]) as s:
    def interrupted(current,sid):
        (Path(sys.argv[1])/'unreachable-dependent-file').write_text(sid)
        os._exit(17)
    s.publish([obs],summarize(obs),parent=s.info()['snapshot_id'],prepare_publication=interrupted)
'''
    import json
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
    child_result=subprocess.run([sys.executable,'-c',child,str(root)],input=json.dumps(source('456')),text=True,capture_output=True,env=env,timeout=15)
    assert child_result.returncode==17,child_result.stderr
    assert (root/'unreachable-dependent-file').is_file()
    with SegmentedCatalog(root) as s:
        assert s.info()['snapshot_id']==sid
        assert len(s.snapshots())==1
        assert s.conn.execute('PRAGMA integrity_check').fetchone()==('ok',)
