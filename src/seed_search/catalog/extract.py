"""CPU reference extraction; no personal admission gates or implicit certification."""
import copy
import time
from numbers import Integral
from .models import empty_observation, validate_observation, validate_identity
from .registry import STRUCTURES, BIOMES, ENVELOPE
from .coverage import STRUCTURE_METHOD, BIOME_METHOD
from .geometry import integer, inside


def extract_observation(identity, backend, *, name_for_id, previous=None, on_progress=None):
    validate_identity(identity)
    if previous is not None:
        validate_observation(previous)
        if previous['identity'] != identity:
            raise ValueError('Resume identity mismatch')
    obs = copy.deepcopy(previous) if previous is not None else empty_observation(identity)

    def state(feature, status, method):
        obs['coverage'][feature] = dict(status=status, bounds=list(ENVELOPE), method_id=method)

    def publish():
        validate_observation(obs)
        if on_progress:
            on_progress(copy.deepcopy(obs))

    for feature in STRUCTURES:
        fid = feature['id']
        if obs['coverage'].get(fid, {}).get('status') == 'complete' and obs['coverage'][fid]['method_id'] == STRUCTURE_METHOD:
            continue
        started = time.perf_counter(); cpu = time.process_time()
        try:
            x0, z0, x1, z1 = ENVELOPE
            points = backend.structures(feature['extractor_key'], (x0, z0, x1-1, z1-1), viable=True)
            if len(points) > 200000:
                raise ValueError('Structure inventory exceeds bounded reference capacity')
            unique = set()
            for point in points:
                if len(point) != 2:
                    raise ValueError('Invalid returned start')
                if any(isinstance(n, bool) or not isinstance(n, Integral) for n in point):
                    raise ValueError('Noninteger structure coordinate')
                x, z = (integer(int(n)) for n in point)
                if not inside(x, z, ENVELOPE):
                    raise ValueError('Backend returned out-of-envelope start')
                unique.add((x, z))
            obs['structures'][fid] = [list(p) for p in sorted(unique)]
            state(fid, 'complete', STRUCTURE_METHOD)
            obs['errors'].pop(fid, None)
        except Exception as error:
            obs['structures'].pop(fid, None)
            state(fid, 'failed', STRUCTURE_METHOD)
            obs['errors'][fid] = f'{type(error).__name__}: {error}'[:500]
        obs['metrics'][fid] = {'wall_seconds': time.perf_counter()-started, 'cpu_seconds': time.process_time()-cpu}
        publish()

    if not all(obs['coverage'].get(f['id'], {}).get('status') == 'complete' and
               obs['coverage'][f['id']]['method_id'] == BIOME_METHOD for f in BIOMES):
        obs['biomes'] = []; obs['biome_names'] = {}
        for f in BIOMES: state(f['id'], 'partial', BIOME_METHOD)
        started = time.perf_counter(); cpu = time.process_time()
        coords = [[x, 63, z] for z in range(ENVELOPE[1], ENVELOPE[3], 64)
                  for x in range(ENVELOPE[0], ENVELOPE[2], 64)]
        failed = None
        for offset in range(0, len(coords), 1024):
            batch = coords[offset:offset+1024]
            try:
                ids = backend.biome_points(batch)
                if len(ids) != len(batch):
                    raise ValueError('Truncated biome query')
                validated = []
                for point, raw in zip(batch, ids):
                    if isinstance(raw, bool) or not isinstance(raw, Integral):
                        raise ValueError('Noninteger biome ID')
                    bid = integer(int(raw), 0, 65535)
                    if str(bid) not in obs['biome_names']:
                        name = name_for_id(bid)
                        if not isinstance(name, str) or not name or len(name) > 128:
                            raise ValueError('Invalid biome mapping')
                        obs['biome_names'][str(bid)] = name
                    validated.append(point + [bid])
                obs['biomes'].extend(validated)
            except Exception as error:
                failed = f'{type(error).__name__}: {error}'[:500]
                break
            publish()
        mapped = not any(name.startswith('unknown_') for name in obs['biome_names'].values())
        for f in BIOMES:
            fid = f['id']
            state(fid, 'failed' if failed else ('complete' if mapped else 'partial'), BIOME_METHOD)
            if failed or not mapped: obs['errors'][fid] = failed or 'Unmapped predictor biome ID'
            else: obs['errors'].pop(fid, None)
        obs['metrics']['biome_plane'] = {'wall_seconds': time.perf_counter()-started,
                                       'cpu_seconds': time.process_time()-cpu, 'samples': len(obs['biomes'])}
        publish()
    return validate_observation(obs)


def extract_observation_v2(identity,backend,*,name_for_id,previous=None,anchors=(),bounds=None,on_progress=None):
    """One typed survey reused by all anchors/products; caller owns native budget."""
    from .models import empty_observation_v2,validate_observation_v2
    from .registry import FEATURES_V2
    validate_identity(identity)
    obs=empty_observation_v2(identity) if previous is None else copy.deepcopy(validate_observation_v2(previous))
    wanted=copy.deepcopy(obs['bounds'] if bounds is None else bounds)
    if obs['identity']!=identity or (previous is not None and obs['bounds']!=wanted):raise ValueError('V2 resume identity/bounds mismatch')
    obs['bounds']=wanted
    if anchors:
        if previous is not None and obs['anchors']!=list(anchors):raise ValueError('V2 resume anchors differ')
        obs['anchors']=copy.deepcopy(list(anchors))
    validate_observation_v2(obs)
    def publish():
        if on_progress:
            validate_observation_v2(obs)
            on_progress(copy.deepcopy(obs))
    for f in FEATURES_V2:
        if f['kind']!='structure_count':continue
        fid=f['id'];b=obs['bounds'][f['dimension']]
        cov=obs['coverage'].get(fid,{})
        if cov.get('status')=='complete' and cov.get('bounds')==b and cov.get('method_id')=='predictor_viable_starts_v1':continue
        begin=time.monotonic()
        try:
            result=backend.structures(f['extractor_key'],(b[0],b[1],b[2]-1,b[3]-1),viable=True)
            if len(result)>200000:raise ValueError('Structure cap')
            unique=set()
            for pt in result:
                if len(pt)!=2 or any(isinstance(v,bool) or not isinstance(v,Integral) for v in pt):raise ValueError('Noninteger start')
                x,z=map(int,pt)
                if not inside(x,z,b):raise ValueError('Start outside survey')
                unique.add((x,z))
            obs['structures'][fid]=[list(p) for p in sorted(unique)]
            partial=fid=='structure.stronghold'
            obs['coverage'][fid]=dict(status='partial' if partial else 'complete',bounds=list(b),
                method_id='predictor_bounded_strongholds_v2' if partial else 'predictor_viable_starts_v1')
            obs['errors'].pop(fid,None)
        except Exception as exc:
            obs['structures'].pop(fid,None)
            obs['coverage'][fid]=dict(status='failed',bounds=list(b),method_id='predictor_viable_starts_v1')
            obs['errors'][fid]=f'{type(exc).__name__}: {exc}'[:500]
        obs['metrics'][fid]=dict(wall_seconds=time.monotonic()-begin)
        publish()
    for dimension,y,did in [('overworld',63,0),('nether',64,-1)]:
        features=[f for f in FEATURES_V2 if f['kind']=='biome_witness' and f['dimension']==dimension]
        b=obs['bounds'][dimension];method=f'predictor_world_lattice_y{y}_stride64_v2'
        if all(obs['coverage'].get(f['id'],{}).get('status')=='complete' and
               obs['coverage'][f['id']]['method_id']==method for f in features):continue
        # Keep additional layers and dense positive witnesses on resume.
        obs['biomes'][dimension]=[p for p in obs['biomes'][dimension] if p[1]!=y or p[0]%64 or p[2]%64]
        for f in features:obs['coverage'][f['id']]=dict(status='partial',bounds=list(b),method_id=method)
        points=[[x,y,z] for z in range(-(-b[1]//64)*64,b[3],64) for x in range(-(-b[0]//64)*64,b[2],64)]
        failed=None
        if len(points)+len(obs['biomes'][dimension])>200000:failed='Biome point budget exceeded'
        else:
            for start in range(0,len(points),1024):
                try:
                    batch=points[start:start+1024];values=backend.biome_points(batch,dimension=did)
                    if len(values)!=len(batch):raise ValueError('Truncated biome batch')
                    validated=[]
                    for p,v in zip(batch,values):
                        if isinstance(v,bool) or not isinstance(v,Integral):raise ValueError('Noninteger biome')
                        bid=integer(int(v),0,65535);name=name_for_id(bid)
                        if not isinstance(name,str) or not name or len(name)>128:raise ValueError('Invalid biome name')
                        if str(bid) in obs['biome_names'] and obs['biome_names'][str(bid)]!=name:raise ValueError('Biome namespace changed')
                        obs['biome_names'][str(bid)]=name;validated.append(p+[bid])
                    obs['biomes'][dimension].extend(validated)
                except Exception as exc:
                    failed=f'{type(exc).__name__}: {exc}'[:500];break
                publish()
        unknown=any(obs['biome_names'].get(str(p[3]),'unknown').startswith('unknown') for p in obs['biomes'][dimension])
        for f in features:
            obs['coverage'][f['id']]['status']='failed' if failed else ('partial' if unknown else 'complete')
            if failed or unknown:obs['errors'][f['id']]=failed or 'Unknown biome mapping'
            else:obs['errors'].pop(f['id'],None)
        publish()
    return validate_observation_v2(obs)
