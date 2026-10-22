import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest
from seed_search.catalog.models import empty_observation_v2,identity
from seed_search.catalog.registry import digest

spec=importlib.util.spec_from_file_location('expanded_calibration',Path(__file__).parents[2]/'scripts/expand_catalog_calibration.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_grid_positive_control_triage_preserves_separate_nether_scope():
    observation=empty_observation_v2(identity('1',model_id='26.50',native_sha256='a'*64,source_sha256='b'*64))
    names=('mansion','village','desert_pyramid','ancient_city','trial_chamber','ruined_portal','shipwreck','monument','outpost','stronghold','mineshaft')
    calibration={'thresholds':{'sizes':{str(side):{name:{'thresholds':[1]} for name in names} for side in (4096,8192)}}}
    class Backend:
        calls=[]
        def structures(self,name,bounds,viable):
            self.calls.append((name,bounds))
            if name=='mansion':return [(4000,0)]
            return [(0,0),(1,1)] if name=='bastion' else [(0,0)]
    backend=Backend()
    assert module.triage(observation,backend,calibration)==[8192]
    assert ('fortress',(-640,-640,639,639)) in backend.calls
    assert observation['coverage']['structure.stronghold']['status']=='partial'


def test_completed_input_validation_rejects_reconstructed_or_unbound_seeds(tmp_path):
    path=tmp_path/'historical.sqlite'
    original={'config':{'search':{'sequence':'sequential'}}}
    with sqlite3.connect(path) as conn:
        conn.executescript('CREATE TABLE meta(key TEXT,value TEXT); CREATE TABLE ranges(start TEXT PRIMARY KEY,end TEXT,status TEXT,digest TEXT);')
        conn.execute('INSERT INTO meta VALUES(?,?)',('identity',json.dumps(original)))
        conn.execute('INSERT INTO ranges VALUES(?,?,?,?)',('0'.zfill(20),'4'.zfill(20),'complete','a'*64))
    row=dict(index='1',seed='1',range_start='0'.zfill(20),range_end='4'.zfill(20),range_digest='a'*64)
    manifest=dict(revision='catalog-expanded-calibration-inputs-v1',source=str(path),source_identity_id=digest(original),rows=[row])
    manifest['manifest_id']=digest(manifest)
    before=path.read_bytes();module.validate_inputs(manifest);assert path.read_bytes()==before
    row['seed']='2';manifest['manifest_id']=digest({k:v for k,v in manifest.items() if k!='manifest_id'})
    with pytest.raises(ValueError,match='Unverified completed input'):module.validate_inputs(manifest)
