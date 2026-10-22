"""Real killed-publisher checks around the additive generation pointer."""
import json,os,subprocess,sys,time
from pathlib import Path
import pytest
from seed_search.catalog.models import identity,empty_observation
from seed_search.catalog.summaries import summarize
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.anchors import make_anchor,derive_anchor_layouts
from seed_search.catalog.accuracy_store import write_bundle,read_bundle,REVISION


@pytest.mark.parametrize('boundary',['before','after'])
def test_sigkill_preserves_ready_generation_and_old_links(tmp_path,boundary):
    root=tmp_path/'catalog';ident=identity(19,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64);obs=empty_observation(ident)
    with SegmentedCatalog(root)as s:sid=s.publish([obs],summarize(obs))
    ctx=dict(identity=ident,dimension='overworld',provider='estimated_world_spawn_v1',observed_build=None,evidence_sha256='c'*64)
    bundle=dict(revision=REVISION,snapshot_id=sid,anchors=[derive_anchor_layouts(obs,make_anchor(ctx,[7,13]))],tiles=[],metadata={'version':0})
    old=write_bundle(root,bundle);bundle['metadata']['version']=1
    payload=tmp_path/'incoming.json';payload.write_text(json.dumps(bundle));marker=tmp_path/'boundary'
    code='''import json,sys,time
from pathlib import Path
from seed_search.catalog import accuracy_store as a
root,payload,marker,boundary=map(str,sys.argv[1:]);original=a.atomic_json
def write(path,value):
 if str(path).endswith('.latest.json'):
  if boundary=='after':original(path,value)
  Path(marker).write_text('ready')
  time.sleep(30)
 original(path,value)
a.atomic_json=write
a.write_bundle(root,json.loads(Path(payload).read_text()))
'''
    child=subprocess.Popen([sys.executable,'-c',code,str(root),str(payload),str(marker),boundary],env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src')))
    try:
        deadline=time.monotonic()+10
        while not marker.exists() and child.poll()is None and time.monotonic()<deadline:time.sleep(.01)
        assert marker.exists(),'Owned child did not reach frozen boundary'
        child.kill();child.wait(timeout=5);assert child.returncode==-9
    finally:
        if child.poll()is None:child.kill();child.wait(timeout=5)
    generation,ready=read_bundle(root,sid)
    assert ready['metadata']['version']==(0 if boundary=='before' else 1)
    assert read_bundle(root,sid,old)[1]['metadata']['version']==0
    with SegmentedCatalog(root)as store:assert store.info(sid)['worlds']==1
