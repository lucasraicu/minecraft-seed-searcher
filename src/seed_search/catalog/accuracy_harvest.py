"""Optional v2 public drain adapter: spawn before evaluation, independent of personal admission."""
from pathlib import Path
import time
from subprocess import SubprocessError
from .anchors import validate_anchor,derive_anchor_layouts
from .registry import digest
from .ingestion import atomic_json,strict_json_loads,verify_no_symlinks
from .accuracy_store import read_bundle,write_bundle,REVISION
from .models import world_id


def _anchor_path(job):
    checkpoint=verify_no_symlinks(job['checkpoint']);root=verify_no_symlinks(job['root'])
    if not checkpoint.is_relative_to(root/'staging'):raise ValueError('Spawn checkpoint escapes staging')
    return verify_no_symlinks(checkpoint.with_suffix('.anchor.json'))


def extract_with_spawn(job,seconds,*,estimator,extract):
    """An unavailable estimate defers work; it cannot reject or erase the seed."""
    start=time.monotonic();path=_anchor_path(job);path.parent.mkdir(parents=True,exist_ok=True)
    anchor=None
    previous_path=None
    if not path.exists() and job.get('previous_checkpoint'):
        previous_path=_anchor_path(dict(job,checkpoint=job['previous_checkpoint']))
    read_path=path if path.exists() else previous_path
    if read_path is not None and read_path.exists():
        if read_path.stat().st_size>16384:raise ValueError('Spawn checkpoint cap')
        anchor=validate_anchor(strict_json_loads(read_path.read_bytes()))
        if anchor['context']['identity']!=job['identity']:raise ValueError('Spawn checkpoint world/build differs')
        proof=digest(dict(estimator_binary_sha256=estimator.binary_sha256,source_sha256=estimator.source_sha256,
                          seed=job['identity']['seed'],coordinate=anchor['coordinate']))
        if anchor['context']['evidence_sha256']!=proof:raise ValueError('Spawn estimator checkpoint provenance differs')
        if read_path!=path:atomic_json(path,anchor)
    if anchor is None:
        try:anchor=validate_anchor(estimator.estimate(job['identity']))
        except (ValueError,OSError,SubprocessError) as error:
            raise OSError('World-spawn estimate unavailable; defer this public evaluation') from error
        if anchor['context']['identity']!=job['identity']:raise ValueError('Estimator returned another world/build')
        atomic_json(path,anchor)
    remaining=seconds-(time.monotonic()-start)
    if remaining<=0:raise TimeoutError('Spawn exhausted public evaluation allowance')
    return extract(job,remaining)


def publish_with_spawn(root,job,observation,*,publish):
    """Append a generation for the returned snapshot; old v1 inventory stays identical."""
    anchor=validate_anchor(strict_json_loads(_anchor_path(job).read_bytes()))
    if anchor['context']['identity']!=observation['identity']:raise ValueError('Spawn/publication identity differs')
    sid=publish(root,job,observation)
    from .segments import SegmentedCatalog
    with SegmentedCatalog(root)as store:
        stored=store.observation(sid,world_id(observation['identity']))
        entry=derive_anchor_layouts(stored,anchor)
        try:_,bundle=read_bundle(root,sid)
        except FileNotFoundError:
            parent=store.conn.execute('SELECT parent_id FROM snapshot_root WHERE snapshot_id=?',(sid,)).fetchone()[0]
            try:_,bundle=read_bundle(root,parent) if parent else (None,None)
            except FileNotFoundError:bundle=None
            bundle=dict(revision=REVISION,snapshot_id=sid,anchors=[] if bundle is None else bundle['anchors'],tiles=[] if bundle is None else bundle['tiles'],metadata=dict(public_harvest_spawn_before_evaluation=True))
        key=(entry['world_id'],entry['anchor']['mode'])
        prior=next((e for e in bundle['anchors']if(e['world_id'],e['anchor']['mode'])==key),None)
        if prior is None:bundle['anchors'].append(entry)
        elif prior!=entry:raise ValueError('Immutable spawn evidence changed within snapshot')
    write_bundle(root,bundle)
    return sid
