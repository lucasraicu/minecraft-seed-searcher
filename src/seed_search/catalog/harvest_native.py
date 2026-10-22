"""Bounded native extraction child and idempotent segmented publisher adapters."""
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from .ingestion import atomic_json, atomic_bytes, verify_no_symlinks, tree_bytes, _get_aggregate_rss
from .models import validate_observation, world_id
from .registry import FEATURE_IDS, ENVELOPE, digest


def realm_runtime_pin(native_build=None,*,prototype=None):
    """Bind private Native/record interpretation without running a seed search."""
    if prototype is None:
        from ..realm.config import dynamic_v3_blueprint_config
        from ..realm.native_batch import Prototype
        prototype=Prototype(native_build,dynamic_v3_blueprint_config())
    return {key:prototype.identity[key] for key in ('extension_sha256','runtime_sha256',
            'record_adapter_sha256','record_sources_sha256','policy_sha256')}


def checkpoint_observation(path, *, protocol=1):
    path=verify_no_symlinks(path)
    if path.stat().st_size>32<<20:raise ValueError('Oversized checkpoint')
    value=json.loads(path.read_bytes())
    if (not isinstance(value,dict) or set(value)!={'sha256','observation'} or
            value['sha256']!=digest(value['observation'])):
        raise ValueError('Checkpoint checksum mismatch')
    if protocol==2:
        from .models import validate_observation_v2
        return validate_observation_v2(value['observation'])
    return validate_observation(value['observation'])


def save_checkpoint(path,value):
    # Hash and embed the exact same canonical bytes. Previously the full survey
    # was encoded once for its digest and again with expensive pretty indentation.
    # The envelope and reader stay compatible; every progress callback still
    # flushes/fsyncs its file and parent directory before returning.
    from .registry import canonical_json
    raw=canonical_json(value)
    checksum=hashlib.sha256(raw).hexdigest().encode('ascii')
    atomic_bytes(path,b'{"observation":'+raw+b',"sha256":"'+checksum+b'"}')


def require_complete(observation, expected):
    from .coverage import complete_for
    validate_observation(observation)
    if observation['identity'] != expected:
        raise ValueError('Extraction identity differs from scheduled world')
    if not all(complete_for(observation, feature, (0, 0), 8192) for feature in FEATURE_IDS):
        raise ValueError('Harvest observation is incomplete')
    if any(observation['coverage'][feature]['bounds'] != list(ENVELOPE) for feature in FEATURE_IDS):
        raise ValueError('Harvest observation lacks the full settlement envelope')
    # Biome coverage status alone is insufficient: summaries require entire lattice.
    if len(observation['biomes']) != 25600:
        raise ValueError('Harvest observation lacks the full biome lattice')
    if any(name.startswith('unknown') for name in observation['biome_names'].values()):
        raise ValueError('Harvest observation has unmapped biome witnesses')
    return observation


def _child(checkpoint):
    import resource
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        os.environ[key] = '1'
    request = json.loads(sys.stdin.buffer.read(16385))
    parent_pid=request['parent_pid']
    def watch_parent():
        while True:
            if os.getppid()!=parent_pid:os._exit(75)
            time.sleep(.25)
    threading.Thread(target=watch_parent,daemon=True).start()
    seconds = request['seconds']
    resource.setrlimit(resource.RLIMIT_CPU, (max(1, math.ceil(seconds)), max(1, math.ceil(seconds))))
    try:os.nice(10)
    except (OSError, AttributeError):pass
    from .. import _native
    from ..backend import Backend, configure_native_threads, native_runtime, model_metadata, biome_name
    from ..realm.native_identity import native_source_fingerprint
    from ..realm.biomes import canonical
    from .models import identity
    from .extract import extract_observation
    native_runtime()
    expected = request['identity']
    actual = identity(expected['seed'], model_id=model_metadata()['model'],
                      native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
                      source_sha256=native_source_fingerprint())
    if actual != expected:raise ValueError('Native extraction build identity mismatch')
    configure_native_threads(1)
    path = verify_no_symlinks(checkpoint)
    if request.get('protocol',1)==2:
        return _child_v2(request,path,actual)
    previous = None
    if path.exists():
        if path.stat().st_size > 32 << 20:raise ValueError('Oversized checkpoint')
        previous = checkpoint_observation(path)
        if previous['identity'] != actual:raise ValueError('Checkpoint identity mismatch')
    atomic_json(path.with_suffix('.settings.json'), dict(native_threads=1, numeric_threads=1,
                nice=os.getpriority(os.PRIO_PROCESS, 0) if hasattr(os, 'getpriority') else None))
    with Backend(actual['seed']) as backend:
        observation = extract_observation(actual, backend,
            name_for_id=lambda bid:canonical(biome_name(bid)), previous=previous,
            on_progress=lambda value:save_checkpoint(path, value))
    require_complete(observation, actual)
    return 0


def extract_native(job, remaining_seconds, *, heartbeat=None, protocol=1, options=None):
    """Only the directly owned child process group is signaled; never a DB PID."""
    if type(protocol) is not int or protocol not in (1,2):raise ValueError('Unknown harvest protocol')
    caps = job['caps']
    checkpoint = verify_no_symlinks(job['checkpoint'])
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    root = verify_no_symlinks(job['root'])
    if protocol==1 and (root/'pilot.sqlite').is_file():
        from .segments import SegmentedCatalog
        with SegmentedCatalog(root) as store:
            snapshots=store.snapshots()
            if snapshots:
                sid=snapshots[-1]['snapshot_id'];wid=world_id(job['identity'])
                if store.conn.execute('SELECT 1 FROM observation_ref WHERE snapshot_id=? AND world_id=?',(sid,wid)).fetchone():
                    return require_complete(store.observation(sid,wid),job['identity'])
    if not checkpoint.is_relative_to(root/'staging'):
        raise ValueError('Checkpoint escapes private staging')
    previous = verify_no_symlinks(job.get('previous_checkpoint', checkpoint))
    if previous != checkpoint and previous.exists() and not checkpoint.exists():
        if not previous.is_relative_to(root/'staging') or previous.stat().st_size > 32 << 20:
            raise ValueError('Invalid previous checkpoint')
        value = checkpoint_observation(previous,protocol=protocol)
        if value['identity'] != job['identity']:raise ValueError('Checkpoint identity mismatch')
        save_checkpoint(checkpoint, value)
    log = checkpoint.with_suffix('.log')
    verify_no_symlinks(log)
    seconds = min(float(remaining_seconds), caps['world_seconds'])
    if seconds <= 0:raise TimeoutError('Harvest wall budget exhausted')
    if tree_bytes(root) >= caps['output_bytes']:raise OSError('Harvest output cap reached')
    env = dict(os.environ)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        env[key] = '1'
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2])
    started = time.monotonic()
    process = None
    with log.open('wb') as output:
        try:
            process = subprocess.Popen([sys.executable, '-m', 'seed_search.catalog.harvest_native',
                '--child', str(checkpoint)], stdin=subprocess.PIPE, stdout=output, stderr=output,
                env=env, start_new_session=True)
            process.stdin.write(json.dumps(dict(identity=job['identity'], seconds=seconds,parent_pid=os.getpid(),
                protocol=protocol,options={k:v for k,v in (options or {}).items()if k!='derivation'})).encode())
            process.stdin.close()
            last_beat = started
            while process.poll() is None:
                now = time.monotonic()
                if now-started >= seconds:raise TimeoutError('Harvest world timed out')
                if _get_aggregate_rss(process.pid) > caps['rss_bytes']:raise MemoryError('Harvest RSS cap reached')
                if log.stat().st_size > 1 << 20 or tree_bytes(root) > caps['output_bytes']:
                    raise OSError('Harvest output cap reached')
                if heartbeat and now-last_beat >= 2:
                    heartbeat(job);last_beat = now
                time.sleep(.05)
            if process.returncode != 0:raise RuntimeError(f'Extraction child failed with exit {process.returncode}; inspect bounded local log')
            if time.monotonic()-started >= seconds:raise TimeoutError('Harvest world timed out')
            if not checkpoint.is_file() or checkpoint.stat().st_size > 32 << 20:
                raise ValueError('Missing or oversized harvest checkpoint')
            if tree_bytes(root) > caps['output_bytes']:raise OSError('Harvest output cap reached')
            value=checkpoint_observation(checkpoint,protocol=protocol)
            if value['identity']!=job['identity']:raise ValueError('Extraction identity mismatch')
            return require_complete(value,job['identity']) if protocol==1 else value
        except TimeoutError:
            if protocol!=2 or not checkpoint.exists():raise
            _stop_owned_child(process)
            value=checkpoint_observation(checkpoint,protocol=2)
            if value['identity']!=job['identity']:raise ValueError('Partial checkpoint identity differs')
            value['metrics']['resource_stop']='world_time_budget_exhausted'
            save_checkpoint(checkpoint,value)
            return value
        finally:
            _stop_owned_child(process)


def _stop_owned_child(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)


def _child_v2(request,path,actual):
    from .spawn_estimator import SpawnEstimator
    from .models import validate_observation_v2
    from .extract import extract_observation_v2
    from ..backend import Backend,biome_name
    from ..realm.biomes import canonical
    from ..realm.config import dynamic_v3_blueprint_config
    from ..realm.native_batch import Prototype
    options=request.get('options',{})
    if set(options)-{'spawn','native_build','native_pin'} or not isinstance(options.get('spawn'),dict):
        raise ValueError('Configure a pinned spawn estimator before public automation')
    pin=options['spawn']
    if set(pin)!={'executable','binary_sha256','source_sha256'}:raise ValueError('Invalid estimator configuration')
    estimator=SpawnEstimator(**pin)
    started=time.monotonic();deadline=started+request['seconds']
    estimated=estimator.estimate(actual)
    anchor=dict(mode=estimated['mode'],coordinate=estimated['coordinate'],source_id=estimated['anchor_id'])
    previous=checkpoint_observation(path,protocol=2) if path.exists() else None
    boxes=dict(overworld=list(ENVELOPE),nether=[-640,-640,640,640])
    pending_scopes=[]
    for dimension,center,half in [('overworld',anchor['coordinate'],4096),
            ('nether',[n//8 for n in anchor['coordinate']],512)]:
        b=boxes[dimension];wanted=[min(b[0],center[0]-half),min(b[1],center[1]-half),
                                  max(b[2],center[0]+half),max(b[3],center[1]+half)]
        if wanted[2]-wanted[0]<=14000 and wanted[3]-wanted[1]<=14000:boxes[dimension]=wanted
        else:pending_scopes.append(dict(dimension=dimension,bounds=wanted,reason='outlier_enrichment_budget'))
    if previous is not None and previous['bounds']!=boxes:raise ValueError('Resume survey bounds changed')
    def checkpoint(value):save_checkpoint(path,value)
    atomic_json(path.with_suffix('.settings.json'),dict(native_threads=1,numeric_threads=1,
        nice=os.getpriority(os.PRIO_PROCESS,0),protocol=2))
    with Backend(actual['seed']) as backend:
        obs=extract_observation_v2(actual,backend,name_for_id=lambda bid:canonical(biome_name(bid)),
            previous=previous,anchors=previous['anchors'] if previous is not None else [anchor],bounds=boxes,on_progress=checkpoint)
        obs['metrics']['pending_scopes']=pending_scopes
        checkpoint(obs)
        from .realm_observations import extract_realm_inventory
        if time.monotonic()<deadline:
            extract_realm_inventory(obs,backend)
            checkpoint(obs)
        if 'evaluation' not in (obs['realm'] or {}) and time.monotonic()<deadline:
            cfg=dynamic_v3_blueprint_config()
            proto=Prototype(options.get('native_build'),cfg)
            native_pin=realm_runtime_pin(prototype=proto)
            if options.get('native_pin') is not None and options['native_pin']!=native_pin:
                raise ValueError('Configured private Realm runtime differs')
            with proto.sweep([int(actual['seed'])],threads=1,retention='survivors',
                             max_misses=0,refine_centers=True) as batch:
                records=batch.retained_records()
                evaluation=records[0] if records else dict(anchors=[],execution_complete=True)
            evaluation['execution_complete']=True
            obs['realm'].update(config_digest=digest(cfg),evaluation=evaluation,native_pin=native_pin)
            for evidence in evaluation.get('anchors',[]):
                if evidence.get('qualification')=='PREDICTED' and evidence.get('baseline_score_complete') is True:
                    coordinate=list(evidence['evaluation_center'])
                    if not any(a['mode']=='recommended' and a['coordinate']==coordinate for a in obs['anchors']):
                        obs['anchors'].append(dict(mode='recommended',coordinate=coordinate,
                            source_id=digest(['realm-refined-center-v2',actual,digest(cfg),coordinate])))
            checkpoint(obs)
        _realm_layers_v2(obs,backend,deadline,checkpoint)
        from .realm_evaluation import evaluate_large_realms
        if time.monotonic()<deadline:
            obs['realm']['larger_sizes']=evaluate_large_realms(obs,seconds=min(5,deadline-time.monotonic()))
            checkpoint(obs)
        _refine_v2(obs,backend,path,deadline,checkpoint)
        if time.monotonic()>=deadline or obs['metrics'].get('refinement',{}).get('reason')=='world_time_budget_exhausted':
            obs['metrics']['resource_stop']='world_time_budget_exhausted'
    validate_observation_v2(obs);checkpoint(obs)
    return 0


def _realm_layers_v2(obs,backend,deadline,checkpoint):
    """Reuse full world-aligned coarse planes; no per-border rescan or terrain."""
    from ..backend import biome_name
    from ..realm.biomes import canonical
    bounds=obs['bounds']['overworld']
    known={tuple(point[:3]) for point in obs['biomes']['overworld']}
    for y in (-48,0,160):
        missing=[[x,y,z] for z in range(-(-bounds[1]//64)*64,bounds[3],64)
                 for x in range(-(-bounds[0]//64)*64,bounds[2],64) if (x,y,z) not in known]
        for first in range(0,len(missing),1024):
            if time.monotonic()>=deadline:
                obs['metrics']['resource_stop']='world_time_budget_exhausted';checkpoint(obs);return
            points=missing[first:first+1024];values=backend.biome_points(points)
            if len(values)!=len(points):raise ValueError('Truncated Realm height plane')
            for point,bid in zip(points,values):
                bid=int(bid);obs['biome_names'][str(bid)]=canonical(biome_name(bid))
                obs['biomes']['overworld'].append(point+[bid])
        checkpoint(obs)


def _refinement_biome_index(obs):
    from collections import defaultdict
    result={dimension:defaultdict(list) for dimension in ('overworld','nether')}
    for dimension,points in obs['biomes'].items():
        for x,y,z,bid in points:
            result[dimension][obs['biome_names'].get(str(bid),'unknown')].append((x,y,z))
    return result


def _refinement_biome_pending(product,anchor,index):
    from .product_evaluation import FAMILIES
    from .geometry import distance2
    record=product.get('kind')=='biome_sampler';dimension=product['dimension']
    families=FAMILIES['record_families' if record else 'features']
    for family in (families if record else product['biomes']):
        levels=((-48,0) if family in FAMILIES['cave_families'] else (63,160)) if record else ((64,) if dimension=='nether' else (63,))
        if not any(y in levels and distance2(x,z,anchor)<=product['radius']**2
                   for name in families[family] for x,y,z in index[dimension].get(name,())):return True
    return False


def _refine_v2(obs,backend,path,deadline,checkpoint):
    """Shared bounded tile queue, four-height coarse record pass, positive witnesses."""
    from .product_evaluation import DEFINITIONS,spawn_reference,structure_points
    from .geometry import inside,distance2
    from .refinement_queue import RefinementQueue
    from .refinement_worker import execute_one,NativeProvider
    from .refinement import decode_tile
    from ..backend import biome_name
    from ..realm.biomes import canonical
    anchor=spawn_reference(obs,'overworld')
    if anchor is None:return
    known={d:{tuple(p[:3]) for p in pts} for d,pts in obs['biomes'].items()}
    meta=obs['metrics'].setdefault('refinement',dict(tiles=[],coarse_done=False,reason=None))
    if not meta['coarse_done']:
        ax,az=anchor['overworld']
        coords=[[x,y,z] for y in (-48,0,160)
            for z in range(-(-(az-1000)//64)*64,az+1001,64)
            for x in range(-(-(ax-1000)//64)*64,ax+1001,64)
            if distance2(x,z,[ax,az])<=1000**2 and inside(x,z,obs['bounds']['overworld']) and (x,y,z) not in known['overworld']]
        for first in range(0,len(coords),1024):
            if time.monotonic()>=deadline:meta['reason']='world_time_budget_exhausted';checkpoint(obs);return
            points=coords[first:first+1024];values=backend.biome_points(points)
            if len(values)!=len(points):raise ValueError('Truncated record biome batch')
            for p,bid in zip(points,values):
                bid=int(bid);obs['biome_names'][str(bid)]=canonical(biome_name(bid))
                obs['biomes']['overworld'].append(p+[bid]);known['overworld'].add(tuple(p))
            checkpoint(obs)
        meta['coarse_done']=True;checkpoint(obs)
    q=RefinementQueue(path.parent.parent/'refinement')
    loaded={t['tile_id'] for t in meta['tiles']}
    definitions=sorted([p for p in DEFINITIONS['presets'] if p['biomes']]+[
        p for p in DEFINITIONS['records'] if p['kind']=='biome_sampler'],key=lambda p:p['id'])
    requests=[]
    indexed=_refinement_biome_index(obs)
    for p in definitions:
        ref=spawn_reference(obs,p['dimension'])
        if ref is None:continue
        a=ref['coordinate'];r=p['radius']
        if any(len(structure_points(obs,feature,a,r))<n for feature,n in p.get('structures',{}).items()):continue
        layers=(-48,0,63,160) if p.get('kind')=='biome_sampler' else ((64,) if p['dimension']=='nether' else (63,))
        tiles=[]
        for y in layers:
            for z in range((a[1]-r)//64*64,a[1]+r+1,64):
                for x in range((a[0]-r)//64*64,a[0]+r+1,64):
                    nearest=(max(x,min(a[0],x+63)),max(z,min(a[1],z+63)))
                    if distance2(*nearest,a)<=r*r and inside(x,z,obs['bounds'][p['dimension']]) and inside(x+63,z+63,obs['bounds'][p['dimension']]):
                        tiles.append((distance2(x+32,z+32,a),x,z,y))
        requests.append((p,iter(sorted(tiles))))
    progress=True
    while progress and time.monotonic()<deadline:
        progress=False
        pending={p['id']:_refinement_biome_pending(p,spawn_reference(obs,p['dimension'])['coordinate'],indexed) for p,_ in requests}
        for p,tiles in requests:
            if not pending[p['id']]:continue
            try:_,x,z,y=next(tiles)
            except StopIteration:continue
            progress=True
            if time.monotonic()>=deadline:break
            dimension=p['dimension']
            context=dict(identity=obs['identity'],dimension=dimension,provider='procedural_model_v1',
                observed_build=None,evidence_sha256=digest(['catalog-procedural-model-v2',obs['identity']]))
            spec=dict(revision='catalog-refinement-job-v1',context=context,bounds=[x,z,x+64,z+64],y=y)
            key=digest(spec);existing=q._path(key).exists()
            if not existing and len(list(q.root.glob('*.json')))>=64:
                meta['reason']='tile_budget_exhausted';checkpoint(obs);return
            q.submit(context,[x,z,x+64,z+64],y)
            result=q.result(key)
            if result['status']!='complete':
                seconds=min(60,int(deadline-time.monotonic()))
                if seconds<1:meta['reason']='world_time_budget_exhausted';checkpoint(obs);return
                execute_one(q,NativeProvider,seconds=seconds)
                result=q.result(key)
            if result['status']!='complete':continue
            tile=result['tile']
            if tile['tile_id'] in loaded:continue
            values=decode_tile(tile);best={};a=spawn_reference(obs,dimension)['coordinate']
            for offset,bid in enumerate(values):
                if bid is None:continue
                px=x+offset%64;pz=z+offset//64
                candidate=(distance2(px,pz,a),px,pz)
                if bid not in best or candidate<best[bid]:best[bid]=candidate
            for bid,(_,px,pz) in best.items():
                obs['biome_names'][str(bid)]=canonical(biome_name(bid))
                if (px,y,pz) not in known[dimension]:
                    obs['biomes'][dimension].append([px,y,pz,bid]);known[dimension].add((px,y,pz))
                    indexed[dimension][obs['biome_names'][str(bid)]].append((px,y,pz))
            meta['tiles'].append(tile);loaded.add(tile['tile_id']);checkpoint(obs)
    if time.monotonic()>=deadline:meta['reason']='world_time_budget_exhausted'
    checkpoint(obs)


def publish_observation(root, job, observation):
    """Called under queue publication ownership; replay after publication is safe."""
    from .segments import SegmentedCatalog
    from .summaries import summarize
    from .registry import canonical_json
    require_complete(observation, job['identity'])
    wid = world_id(observation['identity'])
    with SegmentedCatalog(root) as store:
        snapshots = store.snapshots()
        parent = snapshots[-1]['snapshot_id'] if snapshots else None
        if parent:
            member = store.conn.execute('SELECT 1 FROM observation_ref WHERE snapshot_id=? AND world_id=?',
                                         (parent, wid)).fetchone()
            if member:
                existing = store.observation(parent, wid)
                require_complete(existing, job['identity'])
                return parent
        layouts=summarize(observation)
        # Reserve space for immutable artifacts, indexes, SQLite WAL and temp files.
        reserve=(64<<20)+2*len(canonical_json(observation))+4*len(canonical_json(layouts))
        if tree_bytes(Path(root))+reserve > job['caps']['output_bytes']:
            raise OSError('Insufficient harvest publication headroom')
        snapshot=store.publish([observation], layouts, parent=parent)
        if tree_bytes(Path(root)) > job['caps']['output_bytes']:
            raise OSError('Publication output cap exceeded; valid snapshot retained for replay')
        return snapshot


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--child':raise SystemExit('Internal extraction child only')
    raise SystemExit(_child(Path(sys.argv[2])))
