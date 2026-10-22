"""SIGKILL between snapshot publication and acknowledgement must replay once."""
import json
import os
from pathlib import Path
import subprocess
import sys

from seed_search.catalog.harvest import HarvestQueue
from seed_search.catalog.harvest_native import publish_observation
from seed_search.catalog.segments import SegmentedCatalog
from tests.catalog.test_harvest import descriptor
from tests.catalog.test_ingestion import make_complete_observation


def test_owned_publisher_kill_then_idempotent_replay(tmp_path):
    root=tmp_path/'queue';marker=tmp_path/'published.json'
    with HarvestQueue(root) as queue:queue.register(descriptor(root,count=1))
    source='''
import json,os,signal,sys
from seed_search.catalog.harvest import HarvestQueue
from seed_search.catalog.harvest_native import publish_observation
from tests.catalog.test_ingestion import make_complete_observation
with HarvestQueue(sys.argv[1],clock=lambda:100.) as q:
 job=q.claim('owned-crash-fixture',lease_seconds=1)
 obs=make_complete_observation(job['seed'],{k:v for k,v in job['identity'].items() if k!='seed'})
 with q.publication(job):
  sid=publish_observation(sys.argv[1],job,obs)
  with open(sys.argv[2],'w') as f:json.dump({'snapshot':sid},f);f.flush();os.fsync(f.fileno())
  os.kill(os.getpid(),signal.SIGKILL)
'''
    repo=Path(__file__).resolve().parents[2]
    env=dict(os.environ,PYTHONPATH=str(repo/'src')+os.pathsep+str(repo))
    result=subprocess.run([sys.executable,'-c',source,str(root),str(marker)],env=env,cwd=repo,capture_output=True,text=True,timeout=20)
    assert result.returncode==-9,result.stderr
    sid=json.loads(marker.read_text())['snapshot']
    with HarvestQueue(root,clock=lambda:102.) as queue:
        job=queue.claim('replacement')
        assert job['generation']==2
        obs=make_complete_observation(job['seed'],{k:v for k,v in job['identity'].items() if k!='seed'})
        with queue.publication(job):
            assert publish_observation(root,job,obs)==sid
            queue.acknowledge(job,sid)
        assert queue.status()['jobs']=={'complete':1}
    with SegmentedCatalog(root) as store:
        assert len(store.snapshots())==1 and store.audit(sid)['passed']


def test_native_child_complete_checkpoint_reuses_features_and_sets_resources(tmp_path):
    """Real child startup, fake backend: no world/biome/structure query is allowed."""
    import hashlib
    from seed_search import _native
    from seed_search.backend import model_metadata
    from seed_search.realm.native_identity import native_source_fingerprint
    from seed_search.catalog.models import identity
    from seed_search.catalog.harvest_native import save_checkpoint,checkpoint_observation
    ident=identity(0,model_id=model_metadata()['model'],
        native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
        source_sha256=native_source_fingerprint())
    obs=make_complete_observation('0',{k:v for k,v in ident.items() if k!='seed'})
    checkpoint=tmp_path/'private'/'observation.json';save_checkpoint(checkpoint,obs)
    source='''
import io,json,sys
import seed_search.backend as backend
class NoQueries:
 def __init__(self,seed): pass
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def structures(self,*a,**k):raise AssertionError('Unexpected world query')
 def biome_points(self,*a,**k):raise AssertionError('Unexpected biome query')
backend.Backend=NoQueries
from seed_search.catalog.harvest_native import _child
class Input:
 buffer=io.BytesIO(sys.argv[2].encode())
sys.stdin=Input()
raise SystemExit(_child(__import__('pathlib').Path(sys.argv[1])))
'''
    repo=Path(__file__).resolve().parents[2]
    env=dict(os.environ,PYTHONPATH=str(repo/'src'))
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):env[key]='1'
    request=json.dumps(dict(identity=ident,seconds=5,parent_pid=os.getpid()))
    child=subprocess.run([sys.executable,'-c',source,str(checkpoint),request],env=env,cwd=repo,capture_output=True,text=True,timeout=10)
    assert child.returncode==0,child.stderr
    settings=json.loads(checkpoint.with_suffix('.settings.json').read_text())
    assert settings['native_threads']==settings['numeric_threads']==1
    if settings['nice'] is not None:assert settings['nice']>=10
    assert checkpoint_observation(checkpoint)==obs
