from pathlib import Path
from seed_search.catalog.accuracy_harvest import extract_with_spawn,publish_with_spawn
from seed_search.catalog.anchors import make_anchor
from seed_search.catalog.models import identity,empty_observation
from seed_search.catalog.registry import digest
from seed_search.catalog.harvest_native import publish_observation
from seed_search.catalog.accuracy_store import read_bundle


def test_spawn_precedes_public_evaluation_survives_resume_and_carries_into_next_snapshot(tmp_path):
    events=[]
    class Estimator:
        binary_sha256='c'*64;source_sha256='b'*64
        def estimate(self,ident):
            events.append(('estimate',ident['seed']))
            point=[7,13];proof=digest(dict(estimator_binary_sha256=self.binary_sha256,source_sha256=self.source_sha256,seed=ident['seed'],coordinate=point))
            return make_anchor(dict(identity=ident,dimension='overworld',provider='estimated_world_spawn_v1',observed_build=None,evidence_sha256=proof),point)
    from seed_search.catalog.registry import STRUCTURES,BIOMES,ENVELOPE
    from seed_search.catalog.coverage import STRUCTURE_METHOD,BIOME_METHOD
    def obs(ident):
        o=empty_observation(ident);o['structures']={f['id']:[]for f in STRUCTURES};o['biomes']=[[x,63,z,1]for z in range(-5120,5120,64)for x in range(-5120,5120,64)];o['biome_names']={'1':'plains'}
        o['coverage']={f['id']:dict(status='complete',bounds=list(ENVELOPE),method_id=STRUCTURE_METHOD)for f in STRUCTURES}
        o['coverage'].update({f['id']:dict(status='complete',bounds=list(ENVELOPE),method_id=BIOME_METHOD)for f in BIOMES});return o
    def extract(job,seconds):events.append(('extract',job['identity']['seed']));assert 0<seconds<60;return obs(job['identity'])
    est=Estimator();snapshots=[]
    for seed in (1,2):
        ident=identity(seed,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64)
        job=dict(root=tmp_path,checkpoint=tmp_path/'staging'/f'{seed}.json',identity=ident,caps={'output_bytes':2<<30})
        o=extract_with_spawn(job,60,estimator=est,extract=extract)
        sid=publish_with_spawn(tmp_path,job,o,publish=publish_observation);snapshots.append(sid)
        extract_with_spawn(dict(job,previous_checkpoint=job['checkpoint'],checkpoint=tmp_path/'staging'/f'{seed}-generation2.json'),60,estimator=est,extract=extract)
        assert events.count(('estimate',str(seed)))==1
    assert events[:2]==[('estimate','1'),('extract','1')]
    assert len(read_bundle(tmp_path,snapshots[0])[1]['anchors'])==1
    assert len(read_bundle(tmp_path,snapshots[1])[1]['anchors'])==2


def test_unavailable_spawn_defers_instead_of_evaluating_or_fabricating_origin(tmp_path):
    import pytest
    class Unavailable:
        binary_sha256='c'*64;source_sha256='b'*64
        def estimate(self,identity):raise ValueError('Unavailable model')
    job=dict(root=tmp_path,checkpoint=tmp_path/'staging/job.json',identity=identity(7,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64))
    calls=[]
    with pytest.raises(OSError,match='defer'):extract_with_spawn(job,60,estimator=Unavailable(),extract=lambda *a:calls.append(a))
    assert calls==[] and not (tmp_path/'staging/job.anchor.json').exists()
