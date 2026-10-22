# Final evidence/finalization source review

User explicitly approved expansion+reserve; no newplancritique needed. Review actual staged implementation below. Model tool-free no tools/commands/edits/network/agents. <=650words identify concrete correctness gaps, scopeidentity/cachepromotion/pendingbudget risks; distinguish claims from code. Core+retention workers succeeded29/24checks but Codex rejected shallowextension and barepass finalization, hardened both. Correctiveworker f702e3ad0787 failed deniedRunCommand/noedits, Codex implemented. Gate behavior predicted until actualscoped receipts, no automaticBDS. ExistingRuntime ownsverificationbudget; callback trustedtoevaluateadvertisedrequirements. Structured proofmetadata is not cryptographic game attestation. New helper uses existing automation_meta and writerownership; no secondscheduler. Existing callbacks must provide scoped build/settings/provider/base/requirements identity + actualartifactsha. Does code preserve requirements/anchor/border/dimension failures, rankfrozenresume, retries/dedup2K, evidence-only nojobexecution and nullableextensionstrictvalidation? Summariesgroupunion/source checks captured separately below.

## src/seed_search/catalog/finalization.py
```python
"""Pure bounded advancement over existing scoped game-verification receipts.

No game jobs are launched here. The existing selected verifier owns its budget,
checks and artifacts; this adapter records rank progress and reserve promotion.
"""
from pathlib import Path
import json
from .registry import digest
from .ingestion import atomic_json,strict_json_loads,verify_no_symlinks
from ..seeds import parse_seed

STATUS_PASS='pass'
STATUS_FAIL='fail'
STATUS_INCONCLUSIVE='inconclusive'
STATUS_PENDING='pending'
STATUS_ERROR='error'
STATUSES=(STATUS_PASS,STATUS_FAIL,STATUS_INCONCLUSIVE,STATUS_PENDING,STATUS_ERROR)


def _sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def evidence_identity(seed, *, anchor=None,border=None,dimension='overworld',profile=None,build_id=None,
                      requirements=None,world_settings_id=None,source_observation_id=None,provider_id=None,
                      evidence_policy=None,objective_id=None):
    descriptor=dict(revision='catalog-finalist-scope-v3',seed=str(parse_seed(seed)),anchor=anchor,border=border,
        dimension=dimension,profile=profile,build_id=build_id,requirements=requirements,
        world_settings_id=world_settings_id,source_observation_id=source_observation_id,provider_id=provider_id,
        evidence_policy=evidence_policy)
    # Incomplete scopes are never reusable across unrelated objectives.
    if not requirements:descriptor['objective_id']=objective_id
    return digest(descriptor),descriptor


def _complete_scope(d):
    return (isinstance(d['anchor'],list) and len(d['anchor'])==2 and all(type(n)is int and abs(n)<=30000000 for n in d['anchor'])
        and type(d['border'])is int and d['border'] in (1024,2048,4096,8192)
        and d['dimension'] in ('overworld','nether') and isinstance(d['profile'],str) and bool(d['profile'])
        and isinstance(d['build_id'],str) and d['build_id'].startswith('1.') and bool(d['requirements'])
        and isinstance(d['world_settings_id'],str) and bool(d['world_settings_id'])
        and _sha(d['source_observation_id']) and _sha(d['provider_id'])
        and isinstance(d['evidence_policy'],str) and bool(d['evidence_policy']))


def make_evidence_receipt(evidence_id,world_id,seed,status,*,reason=None,details=None,timestamp=None):
    if not _sha(evidence_id) or not _sha(world_id) or status not in STATUSES:raise ValueError('Invalid verification receipt')
    return dict(revision='catalog-finalist-receipt-v3',evidence_id=evidence_id,world_id=world_id,
        seed=str(parse_seed(seed)),status=status,reason=reason,details=details or {},timestamp=timestamp)


def _valid_receipt(r,eid,cand,scope):
    if (not isinstance(r,dict) or r.get('revision')!='catalog-finalist-receipt-v3' or r.get('evidence_id')!=eid
        or r.get('world_id')!=cand['world_id'] or r.get('seed')!=str(parse_seed(cand['seed'])) or r.get('status') not in STATUSES):return False
    if r['status'] not in ('pass','fail'):return True
    proof=r.get('details',{})
    # These fields are provided by the existing scoped verifier after checking
    # every advertised requirement. Sparse/predictive receipts cannot certify it.
    return (_complete_scope(scope) and isinstance(proof,dict) and proof.get('scope')==scope
        and proof.get('actual') is True and proof.get('requirements_complete') is True
        and proof.get('source')=='actual' and proof.get('provider')=='official BDS '+scope['build_id']
        and isinstance(proof.get('evidence_artifacts'),list) and bool(proof['evidence_artifacts'])
        and all(_sha(v) for v in proof['evidence_artifacts']))


def advance_finalization(objective_id,candidates,primary_k,receipts,*,verifier=None,budget=0,build_id=None,
                         requirements_extractor=None,previous=None,retry_pending=False,on_progress=None):
    if type(primary_k)is not int or primary_k<0 or type(budget)is not int or budget<0:raise ValueError('Finite nonnegative target and budget required')
    if not isinstance(candidates,(list,tuple)) or len(candidates)>2*primary_k:raise ValueError('Candidate list exceeds retained2K capacity')
    frozen=digest([objective_id,primary_k,list(candidates),build_id])
    if previous is not None and previous.get('frozen_candidates_sha256')!=frozen:raise ValueError('Frozen rank/input changed')
    updated=dict(receipts);passed=[];promoted=[];failed=[];pending=[];unverified=[];seen=set();seen_worlds=set();checks=0
    for index,c in enumerate(candidates):
        seed=str(parse_seed(c['seed']));wid=c['world_id']
        if not _sha(wid):raise ValueError('Invalid candidate world')
        if seed in seen or wid in seen_worlds:continue
        seen.add(seed);seen_worlds.add(wid)
        if len(passed)>=primary_k:unverified.append(c);continue
        requirements=requirements_extractor(c) if requirements_extractor else c.get('requirements')
        eid,scope=evidence_identity(seed,anchor=c.get('anchor'),border=c.get('border_side',c.get('border')),
            dimension=c.get('dimension','overworld'),profile=c.get('profile'),build_id=build_id or c.get('build_id'),
            requirements=requirements,world_settings_id=c.get('world_settings_id'),source_observation_id=c.get('source_observation_id'),
            provider_id=c.get('provider_id'),evidence_policy=c.get('evidence_policy'),objective_id=objective_id)
        receipt=updated.get(eid)
        valid=_valid_receipt(receipt,eid,c,scope)
        retry=receipt is not None and receipt.get('status') not in ('pass','fail') and retry_pending
        if not valid or retry:
            if verifier is not None and checks<budget and _complete_scope(scope):
                checks+=1
                try:
                    receipt=verifier(c,eid)
                    if not _valid_receipt(receipt,eid,c,scope):raise ValueError('Unbound/incomplete game evidence')
                except Exception as exc:
                    receipt=make_evidence_receipt(eid,wid,seed,'error',reason=type(exc).__name__)
                updated[eid]=receipt
            else:receipt=None
        entry=dict(c,evidence_id=eid)
        status=receipt.get('status') if receipt else 'pending'
        if status=='pass':
            passed.append(entry)
            if index>=primary_k:promoted.append(entry)
        elif status=='fail':failed.append(dict(entry,failure_reason=receipt.get('reason')))
        else:pending.append(dict(entry,pending_reason=receipt.get('reason') if receipt else 'budget_or_evidence_pending'))
        if on_progress:on_progress(dict(frozen_candidates_sha256=frozen,receipts=updated,checks_performed=checks))
    progress=dict(frozen_candidates_sha256=frozen,objective_id=objective_id,target_k=primary_k,verified_count=len(passed),
        promoted_count=len(promoted),failed_count=len(failed),pending_count=len(pending),checks_performed=checks,
        is_complete=len(passed)>=primary_k)
    return dict(objective_id=objective_id,target_k=primary_k,status='complete' if progress['is_complete'] else 'pending',
        is_complete=progress['is_complete'],verified_count=len(passed),finalized=passed,promoted=promoted,failed=failed,
        pending=pending,unverified=unverified,checks_performed=checks,receipts=updated,progress=progress)


def generic_search_candidates(candidates_by_objective,*,pins=None):
    return sorted(set(pins or ())|{c['world_id'] if isinstance(c,dict) else c for rows in candidates_by_objective.values() for c in rows})


def save_finalization_progress(path,progress_data):
    from .registry import canonical_json
    if len(canonical_json(progress_data))>16<<20:raise ValueError('Progress artifact cap')
    atomic_json(verify_no_symlinks(Path(path).absolute()),progress_data)


def load_finalization_progress(path):
    path=verify_no_symlinks(Path(path).absolute())
    if path.stat().st_size>16<<20:raise ValueError('Progress artifact cap')
    return strict_json_loads(path.read_bytes())


def finalize_retained_objective(store,ledger,snapshot_id,objective_id,verification_context,*,verifier=None,budget=0,retry_pending=False):
    """Explicit operator path using existing SQLite receipts and writer ownership.

    verification_context supplies the existing verifier's actual build/provider,
    profile and advertised requirements. No verifier/budget means evidence-only
    advancement. This never starts a website-wide campaign or changes its budget.
    """
    from .retention import automation_primary_objectives_v3
    manifest=store.snapshot(snapshot_id)
    if manifest['revision']!='catalog-snapshot-v3' or manifest['policy_revision']!=ledger.policy_revision:raise ValueError('Finalization snapshot/policy differs')
    k=automation_primary_objectives_v3().get(objective_id)
    if k is None:raise ValueError('Unknown finite retention objective')
    required={'build_id','provider_id','profile','dimension','evidence_policy','requirements'}
    if not isinstance(verification_context,dict) or set(verification_context)!=required or not verification_context['requirements']:raise ValueError('Explicit advertised verification scope required')
    req=verification_context['requirements']
    if not isinstance(req,dict) or req.get('objective_id')!=objective_id or req.get('policy_revision')!=ledger.policy_revision:raise ValueError('Requirements do not bind advertised objective/policy')
    worlds={e['world_id']:e for e in manifest['worlds']};candidates=[]
    for row in manifest['memberships']:
        if row['objective_id']!=objective_id:continue
        e=worlds[row['world_id']];m=row['member']
        if not isinstance(m.get('anchor'),list):raise ValueError('Objective lacks a verification anchor')
        side=m.get('border_side')
        if side is None:
            bundle=store.world(snapshot_id,row['world_id'])
            summary=next((s for s in bundle['summaries'] if s['layout_id']==m.get('layout_id')),None)
            if summary is None:raise ValueError('Winning anchor binding unavailable')
            side=summary['border_side']
        candidates.append(dict(m,seed=e['identity']['seed'],border_side=side,world_settings_id=e['identity']['world_settings_id'],**verification_context))
    prefix='verification.objective.'+digest([snapshot_id,objective_id])
    old=ledger.conn.execute('SELECT value FROM automation_meta WHERE key=?',(prefix,)).fetchone()
    previous=strict_json_loads(old[0]) if old else None
    cache={}
    for c in candidates:
        eid,_=evidence_identity(c['seed'],anchor=c['anchor'],border=c['border_side'],dimension=c['dimension'],profile=c['profile'],build_id=c['build_id'],requirements=c['requirements'],world_settings_id=c['world_settings_id'],source_observation_id=c['source_observation_id'],provider_id=c['provider_id'],evidence_policy=c['evidence_policy'],objective_id=objective_id)
        row=ledger.conn.execute('SELECT value FROM automation_meta WHERE key=?',('verification.evidence.'+eid,)).fetchone()
        if row:cache[eid]=strict_json_loads(row[0])
    def persist(state):
        # Checkpoints contain scoped references, not another copy of world data.
        with ledger.queue.transaction():
            for eid,r in state.get('receipts',{}).items():
                raw=json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)
                if len(raw.encode())>16<<20:raise ValueError('Verification receipt artifact cap')
                ledger.conn.execute('INSERT INTO automation_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('verification.evidence.'+eid,raw))
            progress={key:value for key,value in state.items() if key!='receipts'}
            ledger.conn.execute('INSERT INTO automation_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(prefix,json.dumps(progress,sort_keys=True,allow_nan=False)))
    with ledger.queue.ownership():
        ledger.protect_verification([c['world_id'] for c in candidates])
        result=advance_finalization(objective_id,candidates,k,cache,verifier=verifier,budget=budget,previous=previous,
            retry_pending=retry_pending,on_progress=persist)
        persist(dict(result['progress'],receipts=result['receipts']))
        if result['is_complete']:ledger.protect_verification([c['world_id'] for c in candidates],release=True)
    return result

```

## src/seed_search/catalog/biome_extension.py
```python
"""Bounded extra XYZ evidence, explicitly isolated from frozen Realm observations."""
from numbers import Integral
import time
from .registry import digest, SAMPLING_PROFILE_REVISION_V3

PLANES = (-48,0,96,160,224)
MAX_POINTS = 8000


def provider_id(observation):
    identity=observation['identity']
    return digest(['catalog-biome-provider-v3',{k:identity[k] for k in
        ('edition','game_build_id','world_settings_id','model_id','native_sha256','source_sha256')}])


def validate_extension(value, observation):
    fields={'revision','base_observation_id','sampling_profile_revision','provider_id','bounds','biomes','biome_names'}
    if not isinstance(value,dict) or set(value)!=fields or value['revision']!='catalog-biome-extension-v3':
        raise ValueError('Invalid biome extension schema')
    if value['base_observation_id']!=digest(observation):raise ValueError('Extension base observation mismatch')
    if value['sampling_profile_revision']!=SAMPLING_PROFILE_REVISION_V3:raise ValueError('Unknown extension sampling profile')
    if value['provider_id']!=provider_id(observation):raise ValueError('Extension provider identity differs')
    if value['bounds']!=observation['bounds']['overworld']:raise ValueError('Extension envelope differs')
    names=value['biome_names'];biomes=value['biomes']
    if not isinstance(names,dict) or not isinstance(biomes,dict) or set(biomes)!={'overworld'}:
        raise ValueError('Invalid extension biome mapping/dimension')
    pts=biomes['overworld']
    if not isinstance(pts,list) or not 1<=len(pts)<=MAX_POINTS:raise ValueError('Extension point capacity; empty evidence uses null')
    for bid,name in names.items():
        if not isinstance(bid,str) or not bid.isascii() or not bid.isdigit() or str(int(bid))!=bid or not 0<=int(bid)<=65535 or not isinstance(name,str) or not 1<=len(name)<=128:raise ValueError('Invalid extension biome name')
        if bid in observation['biome_names'] and observation['biome_names'][bid]!=name:raise ValueError('Extension overwrites base biome namespace')
    base_xyz={tuple(p[:3]) for p in observation['biomes']['overworld']};seen=set();used=set();b=value['bounds']
    for pt in pts:
        if not isinstance(pt,list) or len(pt)!=4 or any(type(n)is not int for n in pt):raise ValueError('Invalid extension XYZ/ID')
        x,y,z,bid=pt;xyz=(x,y,z)
        if y not in PLANES or x%256 or z%256 or not b[0]<=x<b[2] or not b[1]<=z<b[3]:raise ValueError('Extension point outside declared profile/envelope')
        if xyz in base_xyz or xyz in seen:raise ValueError('Extension duplicates saved evidence')
        if str(bid) not in names:raise ValueError('Unmapped extension biome')
        seen.add(xyz);used.add(str(bid))
    if used!=set(names):raise ValueError('Unused extension biome names')
    return value


def extract_extension(observation, backend, *, name_for_id, deadline=None):
    """Compute only missing aligned points; no mutation of the original observation."""
    b=observation['bounds']['overworld'];known={tuple(p[:3]) for p in observation['biomes']['overworld']}
    points=[[x,y,z] for y in PLANES for z in range(-(-b[1]//256)*256,b[3],256)
            for x in range(-(-b[0]//256)*256,b[2],256) if (x,y,z) not in known]
    if len(points)>MAX_POINTS:raise ValueError('Extra survey exceeds the approved8000point cap')
    if not points:return None
    values=[];names={}
    for i in range(0,len(points),1024):
        if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Height evidence deadline')
        batch=points[i:i+1024];ids=backend.biome_points(batch,dimension=0)
        if len(ids)!=len(batch):raise ValueError('Truncated extension response')
        for pt,bid in zip(batch,ids):
            if isinstance(bid,bool) or not isinstance(bid,Integral):raise ValueError('Noninteger extension biome')
            bid=int(bid);name=name_for_id(bid);names[str(bid)]=name;values.append(pt+[bid])
    value=dict(revision='catalog-biome-extension-v3',base_observation_id=digest(observation),
        sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3,provider_id=provider_id(observation),
        bounds=list(b),biomes={'overworld':values},biome_names=names)
    return validate_extension(value,observation)

```

## Source summary sections
```python
def summarize_v3(obs, *, extension=None, base_summaries=None, registry=None):
    """Additive summaries preserving legacy payload and anchor modes.

    Fields same as v2 plus source_extension_id (nullable), sampling_profile_revision.
    Layout ID binds revision/base/extension/profile/registry/anchor/modes/side.
    Reuses base_summaries v2 when supplied to avoid recomputation.
    """
    _validate_obs_v2(obs)
    obs_id = digest(obs)
    w_id = world_id(obs['identity'])
    seed_str = str(parse_seed(obs['identity']['seed']))

    active_registry = registry if registry is not None else REGISTRY_V3
    active_features = active_registry['features']
    active_feature_by_id = {f['id']: f for f in active_features}
    reg_rev = digest(active_registry)

    # 1. Validate extension if provided
    source_extension_id = None
    sampling_prof_rev = SAMPLING_PROFILE_REVISION_V3
    ext_ow_biomes = []
    ext_nether_biomes = []
    ext_biome_names = {}

    if extension is not None:
        from .biome_extension import validate_extension
        validate_extension(extension,obs)
        source_extension_id=digest(extension)
        ext_ow_biomes=extension['biomes']['overworld']
        ext_biome_names=extension['biome_names']


    for f in active_features:
        if f['id'].startswith('biome.group.'):
            points=set()
            for member in f['atomic_members']:
                if active_feature_by_id[member].get('available',True):
                    points.update(biome_points_by_feature[member])
            biome_points_by_feature[f['id']]=sorted(points)

    ow_radii = tuple(active_registry.get('overworld_radii', (256, 512, 1024)))
    nether_radii = tuple(active_registry.get('nether_radii', (64, 128, 256)))


```

Store validates extension via validate_extension before bundlepublication, checks summary source_extension_id==digest(extension), protects extension CAS artifacts through publishedhistory and verificationreceipt reachability. Knownpolicy contract enforces7543/231928 objectiveslots. No globalworldreserveflag. Allcode currently staged isolated; Codex tests strictscope/storage/groupcases pass. No new BDS campaign automatically launched by finalization.
