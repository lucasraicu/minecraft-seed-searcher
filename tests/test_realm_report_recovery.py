import copy
import hashlib
import json
import sqlite3

import pytest

from seed_search.realm import reports
from seed_search.realm.config import default_config
from seed_search.realm.store import RealmStore
from seed_search.realm.terrain import apply_score_policy, attach_actual_evaluation


def populated(path,total=3):
    cfg=default_config()
    store=RealmStore(path,{'config':cfg,'count':total,'start_index':0})
    store.configure_range(0,total,3)
    store.claim_range(0)
    anchors=[]
    for index in range(3):
        candidate={'id':f'{index}:1:2','seed':str(index),'stronghold':[1,2],
                   'qualification':'PREDICTED','baseline_score':5,
                   'biomes':{'raw_names':['forest','taiga'],'score':0},
                   'optional_structures':{'monument':{'predicted_viable':[[1,1]],'bonus':5}}}
        anchors.append({'index':index,'seed':str(index),'anchors':[candidate],'counts':{}})
    store.complete_range(0,3,anchors)
    for candidate in store.iter_candidates():
        prediction={'evidence':'PREDICTED','geometry_pass':True,'geometry_score':75,
                    'biome_fit':50,'baseline_quality':10,'border_fit':{'complete':True,'status':'within'},
                    'provider':{'source':'prediction'},'metrics':{'keep':3}}
        apply_score_policy(prediction,cfg['scoring'],component_status={'biome_fit':'PREDICTED','baseline_quality':'PREDICTED'})
        actual={'evidence':'PARTIAL','geometry_pass':False,'geometry_score':60,'biome_fit':0,
                'baseline_quality':10,'border_fit':{'complete':False,'status':'unknown'},
                'provider':{'source':'actual'},'metrics':{'keep_actual':7}}
        apply_score_policy(actual,cfg['scoring'],source='actual',component_status={'biome_fit':'UNKNOWN','baseline_quality':'PREDICTED'})
        attach_actual_evaluation(prediction,actual,cfg['scoring'])
        for variant in ('v1','v2'):
            store.upsert_variant(candidate['id'],variant,[0,0],copy.deepcopy(prediction))
    return store,cfg


def weight_change(cfg):
    changed=copy.deepcopy(cfg)
    changed['structures']['optional_bonuses']['monument']=15
    changed['scoring'].update(geometry_weight=.5,biome_fit_weight=.3,baseline_weight=.2)
    return changed


def public_bytes(root):
    return {name:(root/name).read_bytes() for name in reports.EXPORT_FILES}


@pytest.mark.parametrize('phase',['candidates','variants'])
def test_rescore_interruption_resume_revision_and_nested_views(tmp_path,monkeypatch,phase):
    store,cfg=populated(tmp_path/'run')
    policy=weight_change(cfg)
    original_identity=copy.deepcopy(store.identity)
    def no_generation(*args,**kwargs):
        raise AssertionError('Rescore generated more data')
    from seed_search import backend
    monkeypatch.setattr(backend.Backend,'__init__',no_generation)
    def interrupt(revision):
        if revision['phase']==phase:
            raise RuntimeError('injected rescore interruption')
    try:
        reports.export(store)
        old_public=public_bytes(store.run/'results')
        with pytest.raises(RuntimeError,match='injected'):
            reports.rescore(store,policy,batch_size=1,progress=interrupt)
        revision=store.get_state('rescore_revision')
        revision_id=revision['id']
        assert revision['status']=='running' and revision['phase']==phase
        assert store.status()['score_revision']['status']=='running'
        assert store.get_state('score_policy') is None
        for function in (reports.ranked,reports.export,reports.ensure_score_revision_complete):
            with pytest.raises(ValueError,match='Incomplete score revision'):
                function(store)
        assert public_bytes(store.run/'results')==old_public
        different=copy.deepcopy(policy)
        different['structures']['optional_bonuses']['monument']=16
        with pytest.raises(ValueError,match='resume its saved policy'):
            reports.rescore(store,different)
        store.close()
        store=RealmStore(tmp_path/'run',resume=True)
        result=reports.rescore(store,policy,batch_size=1)
        assert result=={'rescored_candidates':3,'rescored_variants':6,'generation_queries':0,'score_revision':revision_id}
        assert store.get_state('rescore_revision')['status']=='complete'
        assert store.identity==original_identity
        assert store.status()['completed_seeds']==3
        assert all(c['baseline_score']==15 and c['score_revision']==revision_id for c in store.iter_candidates())
        for wrapper in store.iter_variants():
            record=wrapper['result']
            assert record['score_revision']==revision_id
            assert record['metrics']=={'keep':3}
            assert record['actual_evaluation']['metrics']=={'keep_actual':7}
            assert record['score_generation_source']=='prediction'
            assert record['predicted_score'] is not None
            assert record['actual_evaluation']['actual_partial_score'] is not None
            assert record['verified_score'] is None
        assert len(reports.ranked(store))==3
        reports.export(store)
        assert public_bytes(store.run/'results')!=old_public
    finally:
        store.close()


def test_rescore_batch_database_failure_rolls_back_cursor_and_records(tmp_path):
    store,cfg=populated(tmp_path/'run')
    try:
        original=list(store.iter_candidates())
        store.db.execute("CREATE TRIGGER rescore_fail BEFORE UPDATE ON candidates WHEN NEW.id='1:1:2' BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(sqlite3.IntegrityError):
            reports.rescore(store,weight_change(cfg),batch_size=2)
        revision=store.get_state('rescore_revision')
        assert revision['candidate_cursor']=='' and revision['rescored_candidates']==0
        assert list(store.iter_candidates())==original
        store.db.execute('DROP TRIGGER rescore_fail')
        assert reports.rescore(store,weight_change(cfg),batch_size=2)['rescored_candidates']==3
    finally:
        store.close()


def test_export_failure_preserves_complete_previous_generation(tmp_path,monkeypatch):
    store,cfg=populated(tmp_path/'run')
    try:
        first=reports.export(store)
        root=store.run/'results'
        pinned=(root/'current').resolve()
        before=public_bytes(root)
        reports.rescore(store,weight_change(cfg))
        original=reports._publish_pointer
        def fail_before_switch(*args):
            raise RuntimeError('injected publication failure')
        monkeypatch.setattr(reports,'_publish_pointer',fail_before_switch)
        with pytest.raises(RuntimeError,match='publication'):
            reports.export(store)
        assert (root/'current').resolve()==pinned
        assert public_bytes(root)==before
        monkeypatch.setattr(reports,'_publish_pointer',original)
        second=reports.export(store)
        assert (root/'current').resolve()!=pinned
        assert public_bytes(root)!=before
        assert (pinned/'baseline.jsonl').read_bytes()==before['baseline.jsonl']
        manifest=json.loads((root/'manifest.json').read_text())
        assert manifest['exported_records']=={'baseline':3,'v1':3,'v2':3}
        for name,entry in manifest['files'].items():
            assert hashlib.sha256((root/'current'/name).read_bytes()).hexdigest()==entry['sha256']
        assert all((root/name).is_symlink() for name in reports.EXPORT_FILES)
    finally:
        store.close()


def test_export_mid_stream_failure_keeps_previous_files(tmp_path,monkeypatch):
    store,cfg=populated(tmp_path/'run')
    try:
        reports.export(store)
        root=store.run/'results'
        before=public_bytes(root)
        original=RealmStore.iter_candidates
        def failed_page(snapshot,*args,**kwargs):
            for candidate in original(snapshot,*args,**kwargs):
                yield candidate
                raise OSError('injected output interruption')
        monkeypatch.setattr(RealmStore,'iter_candidates',failed_page)
        with pytest.raises(OSError,match='interruption'):
            reports.export(store)
        assert public_bytes(root)==before
    finally:
        store.close()


def test_export_snapshot_does_not_commit_caller_and_does_not_mix_late_writes(tmp_path,monkeypatch):
    store,cfg=populated(tmp_path/'run')
    try:
        store.db.execute("UPDATE candidates SET result=json_set(result,'$.uncommitted',1) WHERE id='0:1:2'")
        assert store.db.in_transaction
        reports.export(store)
        assert store.db.in_transaction
        assert 'uncommitted' not in json.loads((store.run/'results/baseline.jsonl').read_text().splitlines()[0])
        store.db.rollback()
        original=reports._export_files
        def late_write(snapshot,*args):
            # Snapshot already pinned by its meta query; another writer can commit in WAL.
            store.upsert_candidate({'id':'0:1:2','late':True})
            return original(snapshot,*args)
        monkeypatch.setattr(reports,'_export_files',late_write)
        reports.export(store)
        saved=[json.loads(line) for line in (store.run/'results/baseline.jsonl').read_text().splitlines()]
        assert all('late' not in candidate for candidate in saved)
        assert 'late' in store.get_candidate('0:1:2')
    finally:
        store.close()


def test_existing_flat_exports_migrate_and_keep_legacy_bytes_on_failed_switch(tmp_path,monkeypatch):
    store,cfg=populated(tmp_path/'run')
    try:
        reports.export(store)
        root=store.run/'results'
        before=public_bytes(root)
        for name,data in before.items():
            (root/name).unlink()
            (root/name).write_bytes(data)
        (root/'current').unlink()
        original=reports._publish_pointer
        switches=[]
        def fail_new_generation(root,generation):
            switches.append(generation.name)
            if generation.name.startswith('export-'):
                raise RuntimeError('injected new switch')
            return original(root,generation)
        monkeypatch.setattr(reports,'_publish_pointer',fail_new_generation)
        with pytest.raises(RuntimeError,match='new switch'):
            reports.export(store)
        for name in reports.EXPORT_FILES:
            assert (root/name).read_bytes()==before[name]
        assert switches[0].startswith('legacy-')
    finally:
        store.close()


def test_same_completed_policy_rescores_new_candidates_and_centers(tmp_path):
    store,cfg=populated(tmp_path/'run',total=4)
    policy=weight_change(cfg)
    try:
        first=reports.rescore(store,policy,batch_size=1)
        candidate=copy.deepcopy(store.get_candidate('0:1:2'))
        candidate.update(id='3:1:2',seed='3',baseline_score=5)
        candidate.pop('score_revision')
        candidate['optional_structures']['monument']['bonus']=5
        lease=store.claim_range(0)
        assert lease==(3,4)
        store.complete_range(*lease,[{'index':3,'seed':'3','anchors':[candidate],'counts':{}}])
        record=store.get_variant('0:1:2','v1',[0,0])['result']
        store.upsert_variant('3:1:2','v1',[4,4],record)
        second=reports.rescore(store,policy,batch_size=1)
        assert second['score_revision']!=first['score_revision']
        assert second['rescored_candidates']==4 and second['rescored_variants']==7
        assert store.get_candidate('3:1:2')['baseline_score']==15
        assert store.get_variant('3:1:2','v1',[4,4])['result']['score_revision']==second['score_revision']
    finally:
        store.close()


def test_cli_blocks_generation_during_incomplete_revision_but_keeps_status(tmp_path,capsys):
    from seed_search.realm.cli import main
    store,cfg=populated(tmp_path/'run')
    def interrupt(_):
        raise RuntimeError('pause rescore')
    with pytest.raises(RuntimeError):
        reports.rescore(store,weight_change(cfg),batch_size=1,progress=interrupt)
    store.close()
    run=str(tmp_path/'run')
    for args in (['resume','--run',run],['terrain','--run',run],
                 ['verify-terrain','--run',run,'--variant','v1'],
                 ['verify-realm','--run',run,'--candidate','0:1:2']):
        with pytest.raises(SystemExit) as rejected:
            main(args)
        assert rejected.value.code==2
        assert 'Incomplete score revision' in capsys.readouterr().err
    assert main(['status','--run',run])['score_revision']['status']=='running'


def test_invalid_policy_and_caller_transaction_do_not_start_revision(tmp_path):
    store,cfg=populated(tmp_path/'run')
    try:
        invalid=copy.deepcopy(cfg)
        invalid['scoring']['geometry_weight']=-1
        with pytest.raises(ValueError):
            reports.rescore(store,invalid)
        assert store.get_state('rescore_revision') is None
        store.db.execute("UPDATE candidates SET result=json_set(result,'$.temporary',1) WHERE id='0:1:2'")
        with pytest.raises(ValueError,match='caller transaction'):
            reports.rescore(store,weight_change(cfg))
        assert store.db.in_transaction
        store.db.rollback()
    finally:
        store.close()
