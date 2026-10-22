"""Offline, checksummed research lists. Serving never scans raw observations."""
from pathlib import Path
import json
import resource
import sys
import time

from .coverage import STRUCTURE_METHODS
from .geometry import contains
from .ingestion import atomic_json, strict_json_dumps, _reject_constant, verify_no_symlinks
from .request import _unique
from .models import validate_identity, validate_observation, world_id
from .products import product_registry, RESEARCH_FEATURES, SCOPE
from .registry import canonical_json, digest
from ..seeds import parse_seed

REVISION = 'catalog-product-results-v1'
MAX_BYTES = 32 << 20


def _hex(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _definitions():
    return digest(product_registry())


def derive_previews(store, snapshot_id, *, deadline=None):
    deadline=time.monotonic()+300 if deadline is None else deadline
    def check_budget():
        if time.monotonic() >= deadline:raise TimeoutError('Research derivation budget exhausted')
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if peak*(1 if sys.platform=='darwin' else 1024)>4<<30:raise MemoryError('Research derivation RSS cap exceeded')
    check_budget()
    info=store.info(snapshot_id);store._verified_membership(snapshot_id)
    if info['worlds'] > 10000:raise ValueError('Offline derivation population exceeds bounded milestone')
    lists={f'research.origin.{f}.r2000':[] for f in RESEARCH_FEATURES}
    for ident in store.identities(snapshot_id):
        check_budget()
        wid=world_id(ident);obs=validate_observation(store.observation(snapshot_id,wid))
        if obs['identity'] != ident:raise ValueError('Observation identity mismatch')
        for feature in RESEARCH_FEATURES:
            fid='structure.'+feature;coverage=obs['coverage'].get(fid,{})
            if (coverage.get('status')!='complete' or coverage.get('method_id') not in STRUCTURE_METHODS or
                    not contains(coverage.get('bounds',()),(-2000,-2000,2001,2001))):continue
            points=sorted([x,z] for x,z in obs['structures'][fid] if x*x+z*z <= 4000000)
            if not points:continue
            rows=lists[f'research.origin.{feature}.r2000']
            rows.append(dict(world_id=wid,seed=ident['seed'],count=len(points),
                witnesses=points[:5000],witnesses_truncated=len(points)>5000,scope=dict(SCOPE)))
            rows.sort(key=lambda r:(-r['count'],r['world_id']))
            del rows[100:]
    check_budget()
    return _validate(dict(revision=REVISION,snapshot_id=snapshot_id,definition_sha256=_definitions(),
        population_worlds=info['worlds'],header=info['header'],lists=lists))


def _validate(payload, *, expected_header=None):
    if not isinstance(payload,dict) or set(payload)!={'revision','snapshot_id','definition_sha256','population_worlds','header','lists'}:
        raise ValueError('Invalid research artifact schema')
    if payload['revision']!=REVISION or not _hex(payload['snapshot_id']) or payload['definition_sha256']!=_definitions():
        raise ValueError('Research definition/snapshot mismatch')
    population=payload['population_worlds']
    if type(population) is not int or not 0 <= population <= 10000:raise ValueError('Invalid population')
    header=payload['header'];validate_identity(dict(header,seed='0'))
    if expected_header is not None and header != expected_header:raise ValueError('Research build header mismatch')
    expected={f'research.origin.{f}.r2000' for f in RESEARCH_FEATURES}
    if not isinstance(payload['lists'],dict) or set(payload['lists'])!=expected:raise ValueError('Invalid research lists')
    for rows in payload['lists'].values():
        if not isinstance(rows,list) or len(rows)>min(100,population):raise ValueError('Oversized research ranking')
        seen=set();keys=[]
        for row in rows:
            if not isinstance(row,dict) or set(row)!={'world_id','seed','count','witnesses','witnesses_truncated','scope'}:
                raise ValueError('Invalid research row')
            if not isinstance(row['seed'],str) or str(parse_seed(row['seed']))!=row['seed']:raise ValueError('Invalid seed string')
            if row['world_id']!=world_id(dict(header,seed=row['seed'])) or row['world_id'] in seen:raise ValueError('Invalid duplicate world')
            seen.add(row['world_id']);count=row['count'];points=row['witnesses']
            if type(count) is not int or not 1 <= count <= 200000:raise ValueError('Invalid start count')
            if row['scope']!=SCOPE or type(row['witnesses_truncated']) is not bool or row['witnesses_truncated']!=(count>5000):raise ValueError('Invalid circle scope')
            if not isinstance(points,list) or len(points)!=min(count,5000):raise ValueError('Witness count mismatch')
            for p in points:
                if not isinstance(p,list) or len(p)!=2 or any(type(n) is not int for n in p) or p[0]*p[0]+p[1]*p[1]>4000000:
                    raise ValueError('Invalid circle witness')
            if points!=sorted(points) or len({tuple(p) for p in points})!=len(points):raise ValueError('Duplicate/unsorted witnesses')
            keys.append((-count,row['world_id']))
        if keys!=sorted(keys):raise ValueError('Research ranking is unsorted')
    return payload


def _path(root, snapshot_id):
    if not _hex(snapshot_id):raise ValueError('Invalid snapshot ID')
    return verify_no_symlinks(Path(root)/'product-previews'/(snapshot_id+'.json'))


def write_previews(root, payload):
    _validate(payload)
    envelope=dict(sha256=digest(payload),payload=payload)
    if len(strict_json_dumps(envelope)) > MAX_BYTES:raise ValueError('Research artifact exceeds32MiB')
    target=_path(root,payload['snapshot_id'])
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if read_previews(root,payload['snapshot_id'])!=payload:raise ValueError('Immutable research artifact differs')
        return target
    atomic_json(target,envelope)
    if target.stat().st_size > MAX_BYTES:
        target.unlink();raise ValueError('Encoded research artifact exceeds32MiB')
    return target


def read_previews(root, snapshot_id, *, expected_header=None):
    target=_path(root,snapshot_id)
    with target.open('rb') as stream:blob=stream.read(MAX_BYTES+1)
    if len(blob)>MAX_BYTES:raise ValueError('Oversized research artifact')
    value=json.loads(blob,object_pairs_hook=_unique,parse_constant=_reject_constant)
    if not isinstance(value,dict) or set(value)!={'sha256','payload'} or value['sha256']!=digest(value['payload']):
        raise ValueError('Research checksum mismatch')
    payload=_validate(value['payload'],expected_header=expected_header)
    if payload['snapshot_id']!=snapshot_id:raise ValueError('Research snapshot mismatch')
    return payload
