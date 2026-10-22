"""Scoped same-cohort refresh. Default prepares an isolated catalog; --execute publishes.

Never discovers new seeds, edits personal checkpoints, or rewrites old snapshots.
Only the reviewed local engine and frozen existing 200-seed cohort are accepted.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

BASE = Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/predictor-engine-20261020')
RUNTIME = BASE / 'integrated-runtime'
sys.path.insert(0, str(RUNTIME / 'src'))
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.harvest_native import checkpoint_observation, require_complete, save_checkpoint
from seed_search.catalog.models import observation_id, world_id, validate_observation
from seed_search.catalog.registry import digest
from seed_search.catalog.summaries import summarize
from seed_search.catalog.evidence import build_evidence, read_evidence, validate_evidence, write_evidence
from seed_search.catalog.product_views import derive_previews, read_previews, write_previews
from seed_search.catalog.ingestion import atomic_json, tree_bytes
from seed_search.realm.biomes import canonical
from seed_search.realm.native_identity import native_source_fingerprint

SOURCE = 'f51d3b3b48375ddd2c1f6a3c1b3b94ac0b2e0c246865962d19d5b8df134c3fef'
BINARY = 'aac26a213aa9a56de51f7d4de21977fa4a171c43947127dc7f8a7ebc163f0209'
FROZEN = '5aa265ce1f23b51591922d714fa21f68bc0de1dc555c9856a6999a7fb90424ec'
IMPLEMENTATION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
TASK = BASE / 'catalog-reextract'
REHEARSAL = TASK / ('rehearsal-' + IMPLEMENTATION[:12])
RESULT = TASK / ('prepared-' + IMPLEMENTATION[:12] + '.json')
VERIFIED = TASK / ('verified-' + IMPLEMENTATION[:12] + '.json')
START = time.monotonic()


def check():
    if time.monotonic() - START > 900:
        raise TimeoutError('Refresh phase exceeded 900 seconds')
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss * (1 if sys.platform == 'darwin' else 1024) > 4 << 30:
        raise MemoryError('Refresh phase exceeded 4GiB RSS')
    if native_source_fingerprint() != SOURCE:
        raise ValueError('Reviewed isolated native sources changed')
    if tree_bytes(TASK) > 2 << 30:
        raise OSError('Refresh task output exceeds 2GiB')


def frozen():
    from seed_search import _native
    from seed_search.backend import native_runtime
    native_runtime()
    if hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest() != BINARY:
        raise ValueError('Reviewed native binary differs')
    raw = (BASE / 'reextract-frozen.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN:
        raise ValueError('Frozen source cohort differs')
    value = json.loads(raw)
    if len(value['worlds']) != 200 or len({r['seed'] for r in value['worlds']}) != 200:
        raise ValueError('Expected exactly the original 200 unique seeds')
    return value


def latest(store):
    return store.snapshots()[-1]['snapshot_id']


def inherited_evidence(old, new, audit, sid):
    """Rebind only same-world raw game observations, with explicit old binding."""
    if audit is None:
        return None
    validate_evidence(audit, observation=old)
    p = new['metrics']['engine_refresh']
    if (p['source_world_id'] != world_id(old['identity']) or
            p['source_observation_id'] != observation_id(old) or
            p['source_snapshot_id'] != audit['snapshot_id'] or
            p['source_evidence_sha256'] != digest(audit)):
        raise ValueError('Game observation predecessor binding differs')
    for key in ('edition', 'seed', 'world_settings_id'):
        if old['identity'][key] != new['identity'][key]:
            raise ValueError('Game observation belongs to different world/settings')
    starts = {f: {tuple(v) for v in points} for f, points in new['structures'].items()}
    checks = [c for c in audit['structure_checks'] if tuple(c['predicted']) in starts.get(c['feature_id'], set())]
    # All outcome values and verifier/report digests stay byte-for-byte equivalent.
    return build_evidence(new, sid, audit['verifier'], checks, audit['biome_checks'])


def readiness(store, sid, observations, old, audits):
    check()
    for seed, audit in audits.items():
        payload = inherited_evidence(old[seed], observations[seed], audit, sid)
        write_evidence(store.root, payload)
        if read_evidence(store.root, sid, payload['world_id'], payload['observation_id']) != payload:
            raise ValueError('Game overlay readback differs')
    previews = derive_previews(store, sid, deadline=START + 900)
    write_previews(store.root, previews)
    if read_previews(store.root, sid) != previews:
        raise ValueError('Product preview readback differs')
    target = next(r for r in previews['lists']['research.origin.village.r2000'] if r['seed'] == '-3509659830737203357')
    if target['count'] != 27:
        raise ValueError('Known village control changed')
    check()


def prepare():
    f = frozen(); check()
    progress = json.loads((TASK / 'extraction-progress.json').read_bytes())
    if progress['status'] != 'complete' or len(progress['completed']) != 200:
        raise ValueError('The frozen native extraction is not complete')
    paths = {r['seed']: Path(r['checkpoint']) for r in progress['completed']}
    if set(paths) != {r['seed'] for r in f['worlds']}:
        raise ValueError('Completed extraction cohort differs')
    observations, rows, old_audited, audits = {}, [], {}, {}
    changed_biomes = 0; deltas = {}; derived = TASK / ('derived-' + IMPLEMENTATION[:12])
    derived.mkdir(exist_ok=True)
    with SegmentedCatalog(f['source_root']) as source:
        if latest(source) != f['source_snapshot_id']:
            raise ValueError('Source catalog advanced; reconcile before preparing')
        for index, member in enumerate(f['worlds']):
            check(); seed = member['seed']
            original = source.observation(f['source_snapshot_id'], member['world_id'])
            if observation_id(original) != member['observation_id'] or original['identity']['seed'] != seed:
                raise ValueError('Frozen source observation differs')
            obs = checkpoint_observation(paths[seed])
            if (obs['identity']['source_sha256'] != SOURCE or obs['identity']['native_sha256'] != BINARY or
                    obs['identity']['seed'] != seed or obs['identity']['model_id'] != '26.50'):
                raise ValueError('New observation does not use reviewed native source/build')
            require_complete(obs, obs['identity'])
            for key in ('edition', 'seed', 'world_settings_id'):
                if obs['identity'][key] != original['identity'][key]:
                    raise ValueError('Extraction changed the frozen world/settings')
            if set(obs['structures']) != set(original['structures']):
                raise ValueError('Extraction changed the supported structure inventory')
            audit = read_evidence(source.root, f['source_snapshot_id'], member['world_id'], member['observation_id'])
            if audit is not None:
                validate_evidence(audit, observation=original)
                audits[seed] = audit; old_audited[seed] = original
            obs['metrics']['engine_refresh'] = dict(revision='native-engine-correction-refresh-v1',
                source_snapshot_id=f['source_snapshot_id'], source_world_id=member['world_id'],
                source_observation_id=member['observation_id'], source_evidence_sha256=None if audit is None else digest(audit),
                implementation_sha256=IMPLEMENTATION,
                excluded_predecessor_structure_checks=[] if audit is None else [c for c in audit['structure_checks']
                    if tuple(c['predicted']) not in {tuple(p) for p in obs['structures'].get(c['feature_id'], [])}],
                interpretation='Fresh extraction of the same seed. Retained game checks are unchanged observations, not new game runs or a census.')
            validate_observation(obs)
            if [p[:3] for p in original['biomes']] != [p[:3] for p in obs['biomes']]:
                raise ValueError('Biome lattice coordinates changed')
            changed_biomes += sum(canonical(original['biome_names'][str(a[3])]) != canonical(obs['biome_names'][str(b[3])])
                                  for a, b in zip(original['biomes'], obs['biomes'], strict=True))
            for feature, points in obs['structures'].items():
                before = {tuple(v) for v in original['structures'][feature]}; after = {tuple(v) for v in points}
                delta = deltas.setdefault(feature, dict(added=0, removed=0))
                delta['added'] += len(after - before); delta['removed'] += len(before - after)
            save_checkpoint(derived / (member['world_id'] + '.json'), obs)
            observations[seed] = obs; rows.extend(summarize(obs))
            if (index + 1) % 20 == 0:
                print(json.dumps(dict(prepared=index + 1, seconds=time.monotonic() - START)), flush=True)
    if len(rows) != 48600:
        raise ValueError('Expected all 200 x 243 same-anchor layouts')
    with SegmentedCatalog(REHEARSAL) as store:
        sid = store.publish(list(observations.values()), rows,
            prepare_publication=lambda current, ident: readiness(current, ident, observations, old_audited, audits))
        audit = store.audit(sid)
        info = store.info(sid)
        if info['worlds'] != 200 or info['layouts'] != 48600:
            raise ValueError('Rehearsal population differs')
        # A separate reader must see an entirely ready committed snapshot.
        with SegmentedCatalog(REHEARSAL) as reader:
            if reader.info(sid) != info or read_previews(reader.root, sid) is None:
                raise ValueError('Independent reader cannot see prepared snapshot')
    result = dict(revision='native-engine-correction-refresh-v1', implementation_sha256=IMPLEMENTATION,
        source_snapshot_id=f['source_snapshot_id'], source_root=f['source_root'], snapshot_id=sid,
        rehearsal=str(REHEARSAL), derived=str(derived), worlds=200, layouts=48600,
        source_sha256=SOURCE, native_sha256=BINARY, changed_biome_points=changed_biomes,
        structure_deltas=deltas, rebound_game_worlds=len(audits), audit=audit,
        wall_seconds=time.monotonic() - START)
    atomic_json(RESULT, result); print(json.dumps(result), flush=True)


def publish():
    f = frozen(); check()
    result = json.loads(RESULT.read_bytes())
    if result['implementation_sha256'] != IMPLEMENTATION or result['source_snapshot_id'] != f['source_snapshot_id']:
        raise ValueError('Prepared implementation/source differs')
    verified = json.loads(VERIFIED.read_bytes())
    verifier = Path(__file__).with_name('ENGINE_VERIFY_SCRIPT.py')
    if (verified['snapshot_id'] != result['snapshot_id'] or verified['root'] != str(REHEARSAL) or
            verified['verifier_sha256'] != hashlib.sha256(verifier.read_bytes()).hexdigest() or
            verified['worlds'] != 200 or verified['layouts'] != 48600 or
            not all(verified[k] is True for k in ('all_numeric_fields_match', 'same_anchor_and_border_scope',
                'all_preview_rankings_match', 'perturbation_detected', 'query_paths_match'))):
        raise ValueError('Independent prepared-catalog verification is missing or differs')
    observations, rows, old_audited, audits = {}, [], {}, {}
    with SegmentedCatalog(REHEARSAL) as ready:
        ready.audit(result['snapshot_id'])
        for ident in ready.identities(result['snapshot_id']):
            obs = ready.observation(result['snapshot_id'], world_id(ident))
            observations[ident['seed']] = obs
        rows = [row for segment in ready.iter_segments(result['snapshot_id']) for row in segment['layouts']]
    with SegmentedCatalog(f['source_root']) as store:
        if latest(store) != f['source_snapshot_id']:
            raise ValueError('Live catalog changed; publication requires reconciliation')
        for member in f['worlds']:
            seed = member['seed']; obs = store.observation(f['source_snapshot_id'], member['world_id'])
            if observation_id(obs) != member['observation_id']:
                raise ValueError('Live source observation differs')
            audit = read_evidence(store.root, f['source_snapshot_id'], member['world_id'], member['observation_id'])
            if audit is not None:
                old_audited[seed] = obs; audits[seed] = audit
        def prepare_commit(current, sid):
            if sid != result['snapshot_id']:
                raise ValueError('Live publication differs from the verified rehearsal')
            previous = current.conn.execute('SELECT snapshot_id FROM snapshot_root WHERE snapshot_id != ? ORDER BY rowid DESC LIMIT 1', (sid,)).fetchone()
            if previous != (f['source_snapshot_id'],):
                raise ValueError('Concurrent publication detected')
            readiness(current, sid, observations, old_audited, audits)
        sid = store.publish(list(observations.values()), rows, prepare_publication=prepare_commit)
        store.audit(sid)
    with SegmentedCatalog(f['source_root']) as reader:
        if latest(reader) != sid or reader.info(sid)['worlds'] != 200 or read_previews(reader.root, sid) is None:
            raise ValueError('Committed live catalog is not ready')
        reader.info(f['source_snapshot_id'])
    atomic_json(TASK / 'live-publication.json', dict(snapshot_id=sid, previous_snapshot_id=f['source_snapshot_id'],
                worlds=200, layouts=48600, source_sha256=SOURCE, native_sha256=BINARY,
                wall_seconds=time.monotonic() - START, previous_preserved=True))
    print(json.dumps(dict(published=sid, previous_preserved=True)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Publish already verified rehearsal to the original catalog')
    args = parser.parse_args()
    publish() if args.execute else prepare()
