import pytest

from seed_search.realm.cli import main
from test_realm_report_recovery import populated


@pytest.mark.parametrize('flags,expected',[
    ([],{'pool_revision':None,'new_pool_revision':False,'continue_deferred_halos':False}),
    (['--pool-revision','pool-00000003'],{'pool_revision':'pool-00000003','new_pool_revision':False,'continue_deferred_halos':False}),
    (['--new-pool-revision','--continue-deferred-halos'],{'pool_revision':None,'new_pool_revision':True,'continue_deferred_halos':True}),
])
def test_cli_explicit_pool_and_manual_expansion_flags_reach_scheduler(tmp_path,monkeypatch,capsys,flags,expected):
    from seed_search.realm import terrain
    store,cfg=populated(tmp_path);store.close()
    calls=[]
    def fake_run(*args,**kwargs):
        calls.append((args,kwargs));return {'test_only':True}
    monkeypatch.setattr(terrain,'run_terrain',fake_run)
    main(['terrain','--run',str(tmp_path),'--variant','all',*flags])
    assert calls[0][0][2]==('v1','v2')
    assert {k:calls[0][1][k] for k in expected}==expected
    capsys.readouterr()


def test_cli_cannot_refresh_and_choose_existing_pool_at_once(tmp_path,capsys):
    with pytest.raises(SystemExit) as exc:
        main(['terrain','--run',str(tmp_path),'--pool-revision','pool-00000003','--new-pool-revision'])
    assert exc.value.code==2
    capsys.readouterr()
