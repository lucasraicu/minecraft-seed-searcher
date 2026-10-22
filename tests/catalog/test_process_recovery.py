"""Actual owned-writer SIGKILL tests, separate from exception-only fault injection."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from seed_search.catalog.models import identity,empty_observation,world_id,observation_id,SUMMARY_REVISION
from seed_search.catalog.codec import layout_id,MISSING
from seed_search.catalog.store import CatalogStore


def records(seed):
    obs=empty_observation(identity(seed,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    oid=observation_id(obs)
    row=dict(revision=SUMMARY_REVISION,observation_id=oid,world_id=world_id(obs['identity']),
        layout_id=layout_id(oid,[0,0],2048),seed=str(seed),anchor=[0,0],border_side=2048,
        counts=[[0]*4 for _ in range(14)],structure_nearest_d2=[MISSING]*14,
        biome_nearest_d2=[MISSING]*9,biome_witness_refs=[MISSING]*9,complete=[[False]*4 for _ in range(23)])
    return obs,row


@pytest.mark.parametrize('boundary',['before_commit','after_commit'])
def test_owned_writer_death_and_replay(tmp_path,boundary):
    root=tmp_path/'catalog';obs0,row0=records(0);obs,row=records(1)
    with CatalogStore(root) as store:old_id=store.publish_snapshot([obs0],[row0])
    fixture=tmp_path/'input.json';fixture.write_text(json.dumps([obs,row]))
    marker=tmp_path/'ready';script=tmp_path/'writer.py'
    script.write_text('''import json,os,sys,time
from pathlib import Path
from seed_search.catalog.store import CatalogStore
root,fixture,marker,boundary=sys.argv[1:]
obs,row=json.loads(Path(fixture).read_text())
def gate():
 with open(marker,'w') as out:out.write('ready');out.flush();os.fsync(out.fileno())
 while True:time.sleep(0.05)
with CatalogStore(root) as store:
 if boundary=='before_commit':
  store.conn.create_function('crash_gate',0,gate)
  store.conn.execute('CREATE TEMP TRIGGER crash_boundary BEFORE INSERT ON catalog_snapshot BEGIN SELECT crash_gate(); END;')
 sid=store.publish_snapshot([obs],[row])
 if boundary=='after_commit':gate()
''')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
    process=subprocess.Popen([sys.executable,str(script),str(root),str(fixture),str(marker),boundary],env=env)
    try:
        deadline=time.monotonic()+10
        while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(0.02)
        assert marker.exists(),'Owned writer never reached declared kill boundary'
        with CatalogStore(root) as reader:
            assert reader.snapshot(old_id)['observations']==[obs0]
            expected=1 if boundary=='before_commit' else 2
            assert reader.conn.execute('SELECT COUNT(*) FROM catalog_snapshot').fetchone()[0]==expected
        process.kill();process.wait(timeout=5)
        assert process.returncode<0
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=5)
    with CatalogStore(root) as recovered:
        assert recovered.snapshot(old_id)['layouts']==[row0]
        sid=recovered.publish_snapshot([obs],[row])
        assert recovered.snapshot(sid)['layouts']==[row]
        assert recovered.conn.execute('SELECT COUNT(*) FROM catalog_snapshot').fetchone()[0]==2
        recovered.backup(tmp_path/'restored')
    with CatalogStore(tmp_path/'restored') as restored:
        assert restored.snapshot(sid)['observations']==[obs]
