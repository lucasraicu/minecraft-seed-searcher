"""Immutable accuracy generations attached to an existing immutable catalog snapshot."""
from pathlib import Path
import fcntl
from .artifacts import ArtifactStore
from .ingestion import atomic_json, strict_json_loads, verify_no_symlinks
from .accuracy import sha256
from .anchors import validate_anchor, validate_anchor_summary
from .refinement import decode_tile
from .registry import digest

REVISION='catalog-accuracy-bundle-v1'


def validate_bundle(bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'revision','snapshot_id','anchors','tiles','metadata'} or bundle['revision']!=REVISION:
        raise ValueError('Invalid accuracy bundle')
    sha256(bundle['snapshot_id'])
    if not isinstance(bundle['anchors'],list) or len(bundle['anchors'])>4000:
        raise ValueError('Anchor bundle cap')
    seen=set()
    for entry in bundle['anchors']:
        if not isinstance(entry,dict) or set(entry)!={'anchor','observation_id','world_id','layouts'}:
            raise ValueError('Invalid anchor entry')
        a=validate_anchor(entry['anchor']);sha256(entry['observation_id']);sha256(entry['world_id'])
        from .models import world_id
        if entry['world_id']!=world_id(a['context']['identity']):raise ValueError('Anchor world mismatch')
        key=(entry['world_id'],a['mode'])
        if key in seen:raise ValueError('Duplicate anchor mode/world')
        seen.add(key)
        if not isinstance(entry['layouts'],list) or sorted(r['border_side'] for r in entry['layouts'])!=[2048,4096,8192]:
            raise ValueError('Expected all three border layouts')
        for row in entry['layouts']:
            validate_anchor_summary(row)
            if (row['anchor']!=a['coordinate'] or row['observation_id']!=entry['observation_id'] or
                row['world_id']!=entry['world_id'] or row['seed']!=a['context']['identity']['seed']):
                raise ValueError('Anchor summary binding mismatch')
    if not isinstance(bundle['tiles'],list) or len(bundle['tiles'])>256:raise ValueError('Tile bundle cap')
    ids=set()
    for tile in bundle['tiles']:
        decode_tile(tile)
        if tile['tile_id'] in ids:raise ValueError('Duplicate tile')
        ids.add(tile['tile_id'])
    if not isinstance(bundle['metadata'],dict):raise ValueError('Invalid accuracy metadata')
    digest(bundle)
    return bundle


def _write_bundle(root,bundle):
    """Offline-only publication. Old generations remain addressable by digest."""
    validate_bundle(bundle);directory=verify_no_symlinks(Path(root)/'accuracy');directory.mkdir(exist_ok=True)
    from .segments import SegmentedCatalog
    with SegmentedCatalog(root) as store:
        info=store.info(bundle['snapshot_id']);store._verified_membership(bundle['snapshot_id'])
        members={r[0]:(r[1],r[2]) for r in store.conn.execute(
            'SELECT world_id,observation_id,seed FROM observation_ref WHERE snapshot_id=?',(bundle['snapshot_id'],))}
        for entry in bundle['anchors']:
            ident=entry['anchor']['context']['identity']
            if members.get(entry['world_id'])!=(entry['observation_id'],ident['seed']):
                raise ValueError('Accuracy anchor is not in the pinned snapshot')
            if {k:v for k,v in ident.items() if k!='seed'}!=info['header']:
                raise ValueError('Accuracy build differs from snapshot')
        from .models import world_id
        for tile in bundle['tiles']:
            ident=tile['context']['identity'];wid=world_id(ident)
            if wid not in members or members[wid][1]!=ident['seed'] or {k:v for k,v in ident.items() if k!='seed'}!=info['header']:
                raise ValueError('Accuracy tile is not bound to the pinned snapshot build/world')
    try:_,old=read_bundle(root,bundle['snapshot_id'])
    except FileNotFoundError:old=None
    if old is not None:
        # Existing share links do not include a generation. Keep prior anchor
        # records addressable in every later generation of this base snapshot.
        entries={(e['world_id'],e['anchor']['mode']):e for e in bundle['anchors']}
        tiles={t['tile_id'] for t in bundle['tiles']}
        if any(entries.get((e['world_id'],e['anchor']['mode']))!=e for e in old['anchors']):
            raise ValueError('Published anchor records cannot be removed or replaced')
        if not {t['tile_id'] for t in old['tiles']}<=tiles:
            raise ValueError('Published tiles cannot be removed')
    artifact=ArtifactStore(directory/'objects');manifest=artifact.put_json(bundle)
    generation=digest(bundle)
    binding=dict(revision=REVISION,snapshot_id=bundle['snapshot_id'],generation=generation,artifact=manifest)
    path=verify_no_symlinks(directory/(generation+'.json'))
    if path.exists():
        if strict_json_loads(path.read_bytes())!=binding:raise ValueError('Immutable accuracy generation differs')
    else:atomic_json(path,binding)
    atomic_json(verify_no_symlinks(directory/(bundle['snapshot_id']+'.latest.json')),binding)
    return generation


def write_bundle(root,bundle):
    directory=verify_no_symlinks(Path(root)/'accuracy');directory.mkdir(parents=True,exist_ok=True)
    path=verify_no_symlinks(directory/'publication.lock')
    with path.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:return _write_bundle(root,bundle)
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def read_bundle(root,snapshot_id,generation=None):
    sha256(snapshot_id)
    if generation is not None:sha256(generation)
    directory=verify_no_symlinks(Path(root)/'accuracy')
    path=verify_no_symlinks(directory/((generation+'.json') if generation else (snapshot_id+'.latest.json')))
    if path.stat().st_size>4096:raise ValueError('Oversized accuracy binding')
    binding=strict_json_loads(path.read_bytes())
    if (set(binding)!={'revision','snapshot_id','generation','artifact'} or binding['revision']!=REVISION or
            binding['snapshot_id']!=snapshot_id or (generation is not None and binding['generation']!=generation)):
        raise ValueError('Accuracy generation binding mismatch')
    bundle=ArtifactStore(directory/'objects').get_json(binding['artifact']);validate_bundle(bundle)
    if digest(bundle)!=binding['generation'] or bundle['snapshot_id']!=snapshot_id:
        raise ValueError('Accuracy content digest mismatch')
    return binding['generation'],bundle
