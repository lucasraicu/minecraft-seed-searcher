"""Offline, reviewed candidate exclusions; never a general native generation rule.

Only the pinned adjudication ledger is supported. Original observations, locate
outcomes and snapshots remain immutable. Numeric summaries are reused only for
worlds with unchanged facts. Game audits are rebound subsets, not new game runs.
"""
import copy
import hashlib
from pathlib import Path
import resource
import sys
import time

from . import codec, models
from .evidence import build_evidence, read_evidence, validate_evidence, write_evidence
from .product_views import derive_previews, read_previews, write_previews
from .registry import digest
from .summaries import summarize
from ..realm.predictor_diagnostics import _json
from ..realm.predictor_resolution import load_resolution, resolution_report

REVISION = 'catalog-reviewed-exclusions-v1'
METHOD = 'predictor_viable_starts_reviewed_exclusions_v1'
LEDGER_SHA256 = 'c7e33a51fc2efe5c2449e79dbd4105e0e37a51b490737d4ad121fbb03ed9fad7'
PROJECT = Path(__file__).resolve().parents[3]
LEDGER = PROJECT / 'reviews/predictor-resolution-2026-10-20/ADJUDICATIONS.json'
FIXTURES = PROJECT / 'fixtures/bedrock-26.52/predictor-resolution'
_SOURCE_FILES = ('corrections.py', 'coverage.py', 'summaries.py', 'codec.py', 'product_views.py')
_IMPLEMENTATION = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                   for name in _SOURCE_FILES}


def reviewed_ledger(path=LEDGER, fixtures=FIXTURES):
    """Require the exact reviewed decision and replay the underlying proof bundle."""
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 65536:
        raise ValueError('Invalid adjudication file')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEDGER_SHA256:
        raise ValueError('Adjudication is not the reviewed ledger')
    ledger = _json(raw)
    confirmation = PROJECT / 'reviews/predictor-resolution-2026-10-20/USER_CONFIRMATION.md'
    if confirmation.is_symlink() or hashlib.sha256(confirmation.read_bytes()).hexdigest() != ledger['user_confirmation_sha256']:
        raise ValueError('Player confirmation provenance differs')
    report = resolution_report(fixtures)  # validates all game identities/raw output
    _, data = load_resolution(fixtures)
    proof = _json(data['membership-volumes/world-0/report.json'])
    if (hashlib.sha256((Path(fixtures) / 'manifest.json').read_bytes()).hexdigest() != ledger['proof_manifest_sha256'] or
            hashlib.sha256(data['membership-volumes/world-0/report.json']).hexdigest() != ledger['proof_report_sha256'] or
            proof['controls']['settings_sha256'] != ledger['proof_settings_sha256'] or
            proof['controls']['script_api'] != ledger['script_api'] or
            report['game_build'] != ledger['bds_build']):
        raise ValueError('Adjudication proof identity mismatch')
    volumes = report['structure_membership_volumes']
    for removal in ledger['removals']:
        if volumes['seed'] != removal['seed']:
            raise ValueError('Adjudication seed mismatch')
        target = next(v for v in volumes['volumes'] if v['bounds'] == removal['membership_bounds'])
        control = next(v for v in volumes['volumes'] if v['bounds'] == removal['positive_control_bounds'])
        name = 'minecraft:' + ('pillager_outpost' if removal['feature_id'] == 'structure.outpost' else 'village')
        if target['counts'].get(name, 0) or control['counts'].get(name, 0) <= 0:
            raise ValueError('Adjudication target/control evidence differs')
    return ledger


def transformation(ledger):
    return dict(revision=REVISION, ledger_sha256=LEDGER_SHA256,
                implementation_sha256=digest(_IMPLEMENTATION),
                source_header=ledger['source_header'])


def derive_observation(obs, ledger, *, evidence=None):
    """Return a new research observation, bound to the original facts and audits."""
    models.validate_observation(obs)
    old_identity = obs['identity']
    if {k:v for k,v in old_identity.items() if k != 'seed'} != ledger['source_header']:
        raise ValueError('Correction source build/settings mismatch')
    oid = models.observation_id(obs)
    wid = models.world_id(old_identity)
    if 'transformation_provenance' in obs['metrics']:
        raise ValueError('Already derived observation')
    if evidence is not None:
        validate_evidence(evidence, observation=obs)
        if evidence['snapshot_id'] != ledger['source_snapshot_id']:
            raise ValueError('Source audit belongs to another snapshot')
    removals = [r for r in ledger['removals'] if r['seed'] == old_identity['seed']]
    result = copy.deepcopy(obs)
    removed_checks = []
    for r in removals:
        if wid != r['world_id'] or oid != r['observation_id']:
            raise ValueError('Adjudication source observation mismatch')
        points = result['structures'].get(r['feature_id'], [])
        if points.count(r['position']) != 1:
            raise ValueError('Adjudicated candidate missing/duplicated')
        points.remove(r['position'])
        coverage = result['coverage'].get(r['feature_id'])
        if coverage is None or coverage['method_id'] != 'predictor_viable_starts_v1':
            raise ValueError('Unsupported source coverage method')
        coverage['method_id'] = METHOD
        if evidence is not None:
            removed_checks += [c for c in evidence['structure_checks']
                               if c['feature_id'] == r['feature_id'] and c['predicted'] == r['position']]
    revision = digest(transformation(ledger))
    model = old_identity['model_id'] + '+reviewed-' + revision[:16]
    result['identity'] = models.identity(old_identity['seed'], model_id=model,
        native_sha256=old_identity['native_sha256'], source_sha256=revision,
        world_settings_id=old_identity['world_settings_id'])
    provenance = dict(revision=REVISION, source_snapshot_id=ledger['source_snapshot_id'],
        source_identity=copy.deepcopy(old_identity), source_world_id=wid, source_observation_id=oid,
        ledger_sha256=LEDGER_SHA256, transformation_sha256=revision,
        source_evidence_sha256=None if evidence is None else digest(evidence),
        excluded_structure_checks=copy.deepcopy(removed_checks),
        interpretation='Derived candidate inventory. Retained audit checks preserve original outcomes; no new game audit or physical census.')
    if removals:
        provenance['adjudication_ledger'] = copy.deepcopy(ledger)
    result['metrics']['transformation_provenance'] = provenance
    return models.validate_observation(result)


def rebind_summary(summary, original, derived):
    """Rebind identities only if all spatial facts and coverage are unchanged."""
    codec.validate_summary(summary)
    if (summary['world_id'] != models.world_id(original['identity']) or
            summary['observation_id'] != models.observation_id(original) or
            any(original[k] != derived[k] for k in ('structures','biomes','biome_names','coverage','bounds'))):
        raise ValueError('Summary reuse requires unchanged source facts')
    return _rebind_metadata(summary, models.world_id(original['identity']),
                            models.observation_id(original), models.world_id(derived['identity']),
                            models.observation_id(derived))


def _rebind_metadata(summary, source_wid, source_oid, target_wid, target_oid):
    if summary['world_id'] != source_wid or summary['observation_id'] != source_oid:
        raise ValueError('Summary source binding mismatch')
    row = copy.deepcopy(summary)
    row.update(world_id=target_wid, observation_id=target_oid)
    row['layout_id'] = codec.layout_id(row['observation_id'], row['anchor'], row['border_side'])
    codec.validate_summary(row)
    if codec.pack_summary(row) != codec.pack_summary(summary):
        raise ValueError('Numeric summary changed on rebind')
    return row


def rebind_evidence(evidence, original, derived, snapshot_id):
    validate_evidence(evidence, observation=original)
    p = derived['metrics']['transformation_provenance']
    if (p['source_observation_id'] != models.observation_id(original) or
            p['source_evidence_sha256'] != digest(evidence) or
            p['source_snapshot_id'] != evidence['snapshot_id']):
        raise ValueError('Audit derivation provenance mismatch')
    starts = {f: {tuple(x) for x in ps} for f,ps in derived['structures'].items()}
    checks = [c for c in evidence['structure_checks'] if tuple(c['predicted']) in starts.get(c['feature_id'], set())]
    return build_evidence(derived, snapshot_id, evidence['verifier'], checks, evidence['biome_checks'])


def refresh_catalog(store, *, ledger_path=LEDGER, fixtures=FIXTURES):
    """Publish all facts and dependent files before making the new snapshot visible.

    Bounded to the reviewed 200-world generation; no native execution or game runs.
    The source snapshot is pinned, so replay derives the same immutable generation.
    """
    deadline = time.monotonic() + 600
    def check_budget():
        if time.monotonic() >= deadline:
            raise TimeoutError('Reviewed refresh wall budget exhausted')
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if peak * (1 if sys.platform == 'darwin' else 1024) > 4 << 30:
            raise MemoryError('Reviewed refresh exceeds 4GiB RSS budget')
    check_budget()
    ledger = reviewed_ledger(ledger_path, fixtures)
    parent = ledger['source_snapshot_id']
    info = store.info(parent)
    if info['header'] != ledger['source_header'] or info['worlds'] != 200 or info['layouts'] != 48600:
        raise ValueError('Expected the reviewed source population')
    expected_latest = store.info()['snapshot_id']
    expected_model = ledger['source_header']['model_id'] + '+reviewed-' + digest(transformation(ledger))[:16]
    if expected_latest != parent and store.info()['header']['model_id'] != expected_model:
        raise ValueError('Latest generation advanced beyond the reviewed source')
    source = {}
    derived = {}
    audits = {}
    for ident in store.identities(parent):
        check_budget()
        wid = models.world_id(ident)
        obs = store.observation(parent, wid)
        e = read_evidence(store.root, parent, wid, models.observation_id(obs))
        source[wid] = obs
        derived[wid] = derive_observation(obs, ledger, evidence=e)
        if e is not None:
            audits[wid] = e
    if not {r['world_id'] for r in ledger['removals']} <= set(source):
        raise ValueError('Adjudicated world absent from source')
    rows = []
    changed = {r['world_id'] for r in ledger['removals']}
    reused = 0
    bindings = {}
    for wid, obs in source.items():
        if wid in changed:
            continue
        new = derived[wid]
        if any(obs[k] != new[k] for k in ('structures','biomes','biome_names','coverage','bounds')):
            raise ValueError('Unchanged-world spatial facts differ')
        bindings[wid] = (wid, models.observation_id(obs), models.world_id(new['identity']), models.observation_id(new))
    for segment in store.iter_segments(parent):
        check_budget()
        for row in segment['layouts']:
            wid = row['world_id']
            if wid not in changed:
                rows.append(_rebind_metadata(row, *bindings[wid]))
                reused += 1
    for wid in sorted(changed):
        rows.extend(summarize(derived[wid]))
    if len(rows) != 48600 or reused != 48357:
        raise ValueError('Unexpected layout population')

    prepared = False

    def prepare(current, sid):
        nonlocal prepared
        check_budget()
        if any(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != sha for name,sha in _IMPLEMENTATION.items()):
            raise ValueError('Transformation source changed during refresh')
        if current.conn.in_transaction:
            previous = current.conn.execute('SELECT snapshot_id FROM snapshot_root WHERE snapshot_id != ? ORDER BY rowid DESC LIMIT 1', (sid,)).fetchone()
            if previous != (expected_latest,):
                raise ValueError('Concurrent catalog publication; refusing stale refresh')
        for old_wid, e in audits.items():
            rebased = rebind_evidence(e, source[old_wid], derived[old_wid], sid)
            write_evidence(current.root, rebased)
            actual = read_evidence(current.root, sid, rebased['world_id'], rebased['observation_id'])
            if actual != rebased:
                raise ValueError('Derived audit readback failed')
            validate_evidence(actual, observation=derived[old_wid])
        preview = derive_previews(current, sid)
        write_previews(current.root, preview)
        check_budget()
        if read_previews(current.root, sid) != preview:
            raise ValueError('Preview readback failed')
        prepared = True

    # A different header requires an independent root, not a mixed-header parent.
    sid = store.publish(list(derived.values()), rows, prepare_publication=prepare)
    # Idempotent publication returns early; always verify its dependent files.
    if not prepared:
        prepare(store, sid)
    return dict(revision=REVISION, snapshot_id=sid, source_snapshot_id=parent,
                worlds=len(derived), layouts=len(rows), unchanged_numeric_layouts=reused,
                recomputed_layouts=243, excluded_candidates=len(ledger['removals']),
                rebound_evidence_worlds=len(audits), ledger_sha256=LEDGER_SHA256)
