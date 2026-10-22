"""Pinned offline world-spawn estimator adapter. Never runs from HTTP serving."""
from pathlib import Path
import hashlib
import json
import subprocess
from .accuracy import sha256
from .models import validate_identity
from .anchors import make_anchor
from .registry import digest


class SpawnEstimator:
    def __init__(self, executable, *, binary_sha256, source_sha256):
        self.path=Path(executable).resolve(strict=True)
        self.binary_sha256=sha256(binary_sha256);self.source_sha256=sha256(source_sha256)
        if not self.path.is_file() or self.path.stat().st_size>32<<20:
            raise ValueError('Expected bounded spawn estimator executable')
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.binary_sha256:
            raise ValueError('Spawn estimator binary differs')
        self._cache={}

    def estimate(self,identity):
        validate_identity(identity)
        if identity['world_settings_id']!='default' or identity['source_sha256']!=self.source_sha256 or identity['model_id'] not in ('26.50','MC_26_50'):
            raise ValueError('Spawn estimator source/model differs')
        key=digest(identity)
        if key in self._cache:return json.loads(self._cache[key])
        result=subprocess.run([str(self.path)],input=identity['seed']+'\n',capture_output=True,text=True,timeout=5,check=True)
        if len(result.stdout)>4096 or len(result.stderr)>4096:raise ValueError('Spawn estimator output cap')
        row=json.loads(result.stdout)
        if row.get('seed')!=identity['seed'] or row.get('estimate')!=row.get('repeat_estimate'):
            raise ValueError('Spawn estimate identity/repeat mismatch')
        evidence=digest(dict(estimator_binary_sha256=self.binary_sha256,source_sha256=self.source_sha256,
                             seed=identity['seed'],coordinate=row['estimate']))
        context=dict(identity=identity,dimension='overworld',provider='estimated_world_spawn_v1',
                     observed_build=None,evidence_sha256=evidence)
        anchor=make_anchor(context,row['estimate'])
        if len(self._cache)>=2000:self._cache.clear()
        self._cache[key]=json.dumps(anchor)
        return json.loads(self._cache[key])


def extract_with_accuracy(identity,backend,*,estimator,name_for_id,previous=None,on_progress=None):
    """Public branch adapter: estimate once BEFORE extraction/admission/retention.

    The original v1 inventory remains reusable. A failed estimate raises/defer,
    rather than rejecting a seed or fabricating Origin as world spawn.
    """
    anchor=estimator.estimate(identity)
    from .extract import extract_observation
    from .anchors import derive_anchor_layouts
    obs=extract_observation(identity,backend,name_for_id=name_for_id,previous=previous,on_progress=on_progress)
    return obs,derive_anchor_layouts(obs,anchor)
