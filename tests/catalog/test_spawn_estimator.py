from pathlib import Path
import hashlib
import json
import pytest
from seed_search.catalog.spawn_estimator import SpawnEstimator
from seed_search.catalog.models import identity


def test_estimator_identity_repeat_cache_and_wrong_binary(tmp_path,monkeypatch):
    path=tmp_path/'estimator';path.write_bytes(b'explicit fixture bytes')
    h=hashlib.sha256(path.read_bytes()).hexdigest();est=SpawnEstimator(path,binary_sha256=h,source_sha256='b'*64)
    ident=identity('-9223372036854775808',model_id='26.50',native_sha256='a'*64,source_sha256='b'*64)
    calls=[]
    def run(*a,**kw):
        calls.append(kw['input'])
        class Result:
            stdout=json.dumps(dict(seed=ident['seed'],estimate=[-8,8],repeat_estimate=[-8,8]));stderr=''
        return Result()
    monkeypatch.setattr('seed_search.catalog.spawn_estimator.subprocess.run',run)
    anchor=est.estimate(ident);assert anchor['y'] is None and anchor['coordinate']==[-8,8]
    anchor['coordinate'][0]=999;assert est.estimate(ident)['coordinate']==[-8,8]
    assert calls==[ident['seed']+'\n']
    with pytest.raises(ValueError):est.estimate(dict(ident,source_sha256='c'*64))
    with pytest.raises(ValueError):est.estimate(dict(ident,world_settings_id='flat'))
    with pytest.raises(ValueError):SpawnEstimator(path,binary_sha256='f'*64,source_sha256='b'*64)
