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
        and proof.get('actual') is True and (proof.get('requirements_complete') is True or (r['status']=='fail' and proof.get('scope_failed') is True and isinstance(r.get('reason'),str) and bool(r['reason'])))
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
            if len(seen)>primary_k:promoted.append(entry)
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
        candidates.append(dict(m,world_id=e['world_id'],source_observation_id=e['observation_id'],seed=e['identity']['seed'],border_side=side,world_settings_id=e['identity']['world_settings_id'],**verification_context))
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
            retry_pending=retry_pending,on_progress=persist,build_id=verification_context['build_id'])
        persist(dict(result['progress'],receipts=result['receipts']))
        if result['is_complete']:ledger.protect_verification([c['world_id'] for c in candidates],release=True)
    return result
