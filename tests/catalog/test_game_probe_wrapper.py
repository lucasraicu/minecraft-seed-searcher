"""Exercise actual wrapper command construction without starting Docker or worlds."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('collision',[False,True])
def test_probe_labels_lifetime_guard_and_existing_resource_refusal(tmp_path,monkeypatch,collision):
    path=Path(__file__).resolve().parents[2]/'scripts/catalog_game_probe.py'
    spec=importlib.util.spec_from_file_location('catalog_game_probe_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from seed_search.realm import verification as v
    from seed_search.realm.bds_tools import poc_control as c,probe_tools as p
    from seed_search import backend
    monkeypatch.setattr(v,'CLEANUP_GUARD',tmp_path/'absent-global-guard')
    monkeypatch.setattr(c,'DOCKER',c.DOCKER)
    commands=[];resources={};labels={}
    def docker(argv,**kwargs):
        args=list(argv)[1:];commands.append(args)
        if args[:2]==['image','inspect']:return SimpleNamespace(returncode=0,stdout=json.dumps([{'Id':v.IMAGE_ID}]))
        if args[:2]==['volume','inspect'] or args[:1]==['inspect']:
            name=args[-1]
            if name in resources:return SimpleNamespace(returncode=0,stdout=json.dumps([{'Labels':labels,'Config':{'Labels':labels}}]))
            return SimpleNamespace(returncode=0 if collision else 1,stdout='[]')
        if args[:2]==['volume','create'] or args[:1]==['create']:
            label=args[args.index('--label')+1];labels.update([label.split('=',1)])
            name=args[-1] if args[0]=='volume' else args[args.index('--name')+1]
            resources[name]=True
        if args[:1]==['ps']:return SimpleNamespace(returncode=0,stdout='')
        return SimpleNamespace(returncode=0,stdout='')
    monkeypatch.setattr(module.subprocess,'run',docker)
    monkeypatch.setattr(c,'docker',lambda *args,**kw:docker([module.DOCKER,*args],**kw))
    class Adapter:
        def __init__(self,cfg):pass
        def verify_surface_points(self,*args,**kwargs):
            p.docker('volume','create','realm-bds-test-data',capture_output=True,text=True)
            p.docker('create','--name','realm-bds-test','--cpus','4','--memory','6g','--log-driver','local',v.IMAGE,capture_output=True,text=True)
            return {'status':'PARTIAL','surface_biome_observations':[]}
    monkeypatch.setattr(v,'VerificationAdapter',Adapter)
    class Backend:
        def __init__(self,*a):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
    monkeypatch.setattr(backend,'Backend',Backend)
    old_alias=p.docker
    try:status=module.run(tmp_path/'output','17')
    finally:p.docker=old_alias
    report=json.loads((tmp_path/'output/report.json').read_text())
    if collision:
        assert status==2 and report['status']=='FAILED'
        assert not any(args[0] in ('create','rm') or args[:2] in (['volume','create'],['volume','rm']) for args in commands)
    else:
        assert status==0
        created=next(args for args in commands if args[0]=='create')
        assert created[created.index('--entrypoint')+1]=='/usr/bin/timeout'
        assert '--kill-after=15' in created and '--read-only' in created
        assert created[created.index('--network')+1]=='bridge'
        assert '-p' not in created and '--publish' not in created
        assert len(report['cleanup'])==2 and all(row['removed'] for row in report['cleanup'])
