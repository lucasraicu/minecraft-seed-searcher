"""Regression checks for blockers found during the pre-push review."""
import json

import pytest
from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.resources import disk_policy, disk_status
from seed_search.realm.store import RealmStore, canonical, index_key
from seed_search.realm.verification import final_nether_evidence
from seed_search.realm.verification_plan import verification_region
from seed_search.web import server
from scripts.merge_runs import merge_runs
from scripts import tune_machine


def test_compact_projection_uses_observed_growth(tmp_path):
    (tmp_path / 'data').write_bytes(b'x' * 100000)
    policy = disk_policy({'run_disk_limit_bytes': 1 << 30, 'free_disk_reserve_bytes': 1}, retention='survivors')
    sample = disk_status(tmp_path, policy, completed_seeds=1000, remaining_seeds=1000)
    assert sample['bytes_per_seed_estimate'] >= 150
    assert sample['projected_run_bytes'] >= 250000
    assert disk_policy({})['retention'] == 'full'
    assert disk_policy({'compact_projected_bytes_per_seed': 90}, retention='survivors')['projected_bytes_per_seed'] == 90


def test_current_verification_region_cannot_be_shrunk_by_candidate():
    cfg = two_group_blueprint_config()
    with pytest.raises(ValueError, match='fixed Stronghold2048'):
        verification_region({'center':[0,0], 'bounds':{'overworld':[-768,-768,768,768]}}, 'v1', cfg, 16)


def test_duplicate_nether_anchors_do_not_satisfy_count_goal():
    anchor = {'x':0,'y':64,'z':0,'actual':True}
    evidence = {'seed':'1','bds_version':'1.26.52.3','dimension':'nether','source':'manual-snapshot',
                'structures':{'fortress':[anchor]*2,'bastion':[anchor]*3}}
    result = final_nether_evidence('1',(0,0),evidence)
    assert result['status'] == 'PARTIAL'
    assert len(result['structures']['bastion']['anchors']) == 1


def test_view_run_rejects_traversal_and_symlinks(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    manager = server.SweepManager()
    for value in (None, '../outside', '/tmp', 'unknown'):
        assert not manager.select_run(value)['ok']
    link = tmp_path / 'web-sweep-20261014-120000-abcdef01'
    link.symlink_to(tmp_path.parent, target_is_directory=True)
    assert not manager.select_run(link.name)['ok']


def source_run(root, payload):
    identity = {'config_sha256':'same-policy','native_build':'same-build'}
    with RealmStore(root,identity=identity) as store:
        store.configure_range(0,10)
        store.db.execute("INSERT INTO ranges VALUES (?,?,'complete','worker',1,'digest')",(index_key(0),index_key(10)))
        data={'id':'candidate','seed':'123','qualification':'PREDICTED','payload':payload}
        store.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?)',('candidate',index_key(0),'123','PREDICTED',canonical(data)))
        store.db.commit()


def test_merge_is_atomic_readonly_and_idempotent(tmp_path):
    first, second, master = (tmp_path / n for n in ('first','second','master'))
    source_run(first,'A'); source_run(second,'B')
    result = merge_runs([first, first],master)
    assert result['total_seeds_scanned'] == 10
    assert result['resumable'] is False
    with pytest.raises(ValueError,match='incompatible records'):
        merge_runs([second],master)
    assert merge_runs([first],master)['total_candidates'] == 1
    with pytest.raises(ValueError,match='Read-only aggregate'):
        RealmStore(master,resume=True)
    with pytest.raises(ValueError,match='original runs'):
        merge_runs([second],first)


def test_merge_conflict_into_new_destination_can_retry(tmp_path):
    first, conflict, master = (tmp_path / n for n in ('first', 'conflict', 'master'))
    source_run(first, 'A')
    source_run(conflict, 'B')
    with pytest.raises(ValueError, match='incompatible records'):
        merge_runs([first, conflict], master)
    assert merge_runs([first], master)['total_candidates'] == 1


def test_tuner_partitions_actual_batches_and_respects_production_threads(monkeypatch,tmp_path,capsys):
    calls=[]
    class Batch:
        def __init__(self,n): self.native_seconds=n * 0.0001
        def __enter__(self): return self
        def __exit__(self,*args): pass
    class Prototype:
        identity={'openmp':True}
        def __init__(self,directory,cfg):
            assert cfg['screening_revision'] == 'dynamic-envelope-1664-v1'
            assert cfg['structures']['hard_floors']['shipwreck'] == 4
        def sweep(self,seeds,threads,**kwargs):
            assert 1 <= threads <= 34
            assert len(seeds) <= 16384
            calls.append((threads,len(seeds)))
            return Batch(len(seeds))
    (tmp_path/'identity.json').write_text(json.dumps({'openmp':True}))
    monkeypatch.setattr(tune_machine,'Prototype',Prototype)
    builds=[]
    monkeypatch.setattr(tune_machine,'build',lambda *args,**kwargs: builds.append(kwargs))
    monkeypatch.setattr(tune_machine.os,'cpu_count',lambda:192)
    winner=tune_machine.tune_machine(tmp_path,None,count=30000)
    assert builds and builds[0]['work_chunk']==64
    assert winner['threads'] <= 34
    assert any(n == 8192 for _,n in calls)
    assert any(n == 16384 for _,n in calls)
    output = capsys.readouterr().out
    assert '192 Logical Cores' in output
    assert '1–34' in output
    assert '--native-build' in output
    with pytest.raises(ValueError,match='50,000'):
        tune_machine.tune_machine(tmp_path,None,count=50001)
