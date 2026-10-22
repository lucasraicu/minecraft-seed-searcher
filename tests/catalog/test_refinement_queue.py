import pytest
from seed_search.catalog.refinement_queue import RefinementQueue
from seed_search.catalog.refinement import make_tile
from seed_search.catalog.models import identity


def ctx():return dict(identity=identity(9,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64),dimension='overworld',provider='procedural_model_v1',observed_build=None,evidence_sha256='c'*64)


def test_restart_recovers_expired_claim_and_fences_old_writer(tmp_path):
    now=[100];q=RefinementQueue(tmp_path,clock=lambda:now[0]);key=q.submit(ctx(),[0,0,2,2],63)
    assert q.submit(ctx(),[0,0,2,2],63)==key
    old=q.claim(lease_seconds=10);assert q.claim() is None
    now[0]=111;q=RefinementQueue(tmp_path,clock=lambda:now[0]);new=q.claim();tile=make_tile(ctx(),[0,0,2,2],63,[1]*4)
    with pytest.raises(ValueError):q.complete(old,tile)
    q.complete(new,tile);assert q.result(key)['tile']==tile and q.claim() is None


def test_cancel_scope_and_resource_caps(tmp_path):
    q=RefinementQueue(tmp_path);key=q.submit(ctx(),[-2,-2,0,0],-64);claim=q.claim()
    with pytest.raises(ValueError):q.complete(claim,make_tile(ctx(),[0,0,2,2],-64,[1]*4))
    q.cancel(key)
    with pytest.raises(ValueError):q.complete(claim,make_tile(ctx(),[-2,-2,0,0],-64,[1]*4))
    assert q.result(key)['status']=='cancelled'
    with pytest.raises(ValueError):q.submit(ctx(),[0,0,8192,8192],63)


def test_worker_executes_one_bounded_tile_and_survives_restart(tmp_path):
    from seed_search.catalog.refinement_worker import execute_one
    from seed_search.catalog.refinement import decode_tile
    q=RefinementQueue(tmp_path);key=q.submit(ctx(),[0,0,2,2],63)
    class Provider:
        def __init__(self,context):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def sample(self,x,y,z):return 7 if x==z else None
        def name(self,raw):return 'plains'
    assert execute_one(q,Provider)['status']=='complete'
    tile=RefinementQueue(tmp_path).result(key)['tile']
    assert decode_tile(tile)==(7,None,None,7) and tile['biome_names']=={'7':'plains'}
