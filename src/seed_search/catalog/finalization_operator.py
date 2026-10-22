"""Resolve saved legacy anchor bindings before the existing finalist adapter.

This is an explicit operator entry point, not a scheduler. It launches no BDS
work unless the caller supplies the existing scoped verifier and finite budget.
"""
import json
from .finalization import advance_finalization,evidence_identity
from .registry import digest
from .ingestion import strict_json_loads


def advance_ordered_finalization(objective_id,candidates,primary_k,receipts,**options):
    """Keep cached lower-ranked passes provisional behind an unresolved rank."""
    result=advance_finalization(objective_id,candidates,primary_k,receipts,**options)
    order={};seen=set()
    for candidate in candidates:
        if candidate['seed'] in seen or candidate['world_id'] in order:continue
        seen.add(candidate['seed']);order[candidate['world_id']]=len(order)
    first_pending=min((order[c['world_id']] for c in result['pending']),default=len(order))
    deferred=[c for c in result['finalized'] if order[c['world_id']]>first_pending]
    accepted=[c for c in result['finalized'] if order[c['world_id']]<first_pending]
    result.update(finalized=accepted,provisional_passes=deferred,verified_count=len(accepted),
        promoted=[c for c in result['promoted'] if order[c['world_id']]<first_pending],
        is_complete=len(accepted)>=primary_k,status='complete' if len(accepted)>=primary_k else 'pending')
    result['progress'].update(verified_count=len(accepted),promoted_count=len(result['promoted']),
        provisional_pass_count=len(deferred),is_complete=result['is_complete'])
    return result


def finalize_objective(store, ledger, snapshot_id, objective_id, verification_context, *, verifier=None,budget=0,retry_pending=False):
    if not isinstance(verification_context,dict):raise ValueError('Explicit advertised verification scope required')
    manifest=store.snapshot(snapshot_id)
    worlds={e['world_id']:e for e in manifest['worlds']}
    members=[]
    for row in manifest['memberships']:
        if row['objective_id']!=objective_id:
            members.append(row);continue
        member=dict(row['member'])
        product_anchor=member.get('anchor')
        if isinstance(product_anchor,dict):
            dim=verification_context.get('dimension')
            if member.get('scope',{}).get('dimension')!=dim:raise ValueError('Product verification dimension differs')
            coordinate=product_anchor.get('nether' if dim=='nether' else 'overworld')
            if not isinstance(coordinate,list):raise ValueError('Product verification anchor unavailable')
            member['anchor']=coordinate
            radius=member.get('scope',{}).get('radius')
            from .products import product_registry_v2
            product=next((p for p in product_registry_v2()['products'] if p['id']==objective_id),None)
            sides=product.get('scope',{}).get('border_sides',[]) if product else []
            side=1024 if dim=='nether' else (sides[0] if len(sides)==1 else next((n for n in (2048,4096,8192) if type(radius)is int and n//2>=radius),None))
            if side is None:raise ValueError('Product verification window unavailable')
            member['border_side']=side
        if not isinstance(member.get('anchor'),list) or member.get('border_side') is None:
            bundle=store.world(snapshot_id,row['world_id'])
            selected=next((s for s in bundle['summaries'] if member.get('layout_id') in
                (s['layout_id'],s.get('legacy',{}).get('layout_id'))),None) if member.get('layout_id') is not None else None
            if selected is not None:
                member['anchor']=selected['anchor'];member['border_side']=selected['border_side']
            elif objective_id=='reference_sample':
                # Reference samples advertise no winning layout. A verifier must
                # explicitly name its inspected scope; never invent a winner.
                requirements=verification_context.get('requirements',{})
                anchor=requirements.get('verification_anchor');side=requirements.get('verification_border_side')
                if not isinstance(anchor,list) or len(anchor)!=2 or not all(type(n)is int and abs(n)<=30000000 for n in anchor) or side not in ((1024,) if verification_context.get('dimension')=='nether' else (2048,4096,8192)):
                    raise ValueError('Reference sample verification requires an explicit anchor and border')
                member['anchor']=anchor;member['border_side']=side
            else:raise ValueError('Saved objective anchor is unavailable')
        if verification_context.get('dimension')=='nether' and objective_id!='reference_sample' and not isinstance(product_anchor,dict):
            member['anchor']=[n//8 for n in member['anchor']];member['border_side']=1024
        members.append(dict(row,member=member))
    from .retention import automation_primary_objectives_v3
    if manifest['revision']!='catalog-snapshot-v3' or manifest['policy_revision']!=ledger.policy_revision:raise ValueError('Finalization snapshot/policy differs')
    k=automation_primary_objectives_v3().get(objective_id)
    if k is None:raise ValueError('Unknown finite retention objective')
    required={'build_id','provider_id','profile','dimension','evidence_policy','requirements'}
    if not isinstance(verification_context,dict) or set(verification_context)!=required:raise ValueError('Explicit advertised verification scope required')
    req=verification_context['requirements']
    if not isinstance(req,dict) or req.get('objective_id')!=objective_id or req.get('policy_revision')!=ledger.policy_revision:raise ValueError('Requirements do not bind advertised objective/policy')
    # Objective labels do not change the physical condition. Equivalent conditions
    # at the same source/anchor/border/dimension may reuse one actual-game receipt.
    physical={key:value for key,value in req.items() if key not in ('objective_id','policy_revision','verification_anchor','verification_border_side')}
    if not physical:raise ValueError('Actual advertised conditions are required')
    context=dict(verification_context,requirements=physical)
    candidates=[]
    for row in members:
        if row['objective_id']!=objective_id:continue
        entry=worlds[row['world_id']]
        candidates.append(dict(row['member'],world_id=entry['world_id'],seed=entry['identity']['seed'],
            source_observation_id=entry['observation_id'],world_settings_id=entry['identity']['world_settings_id'],
            objective_id=objective_id,**context))
    prefix='verification.objective.'+digest([snapshot_id,objective_id])
    old=ledger.conn.execute('SELECT value FROM automation_meta WHERE key=?',(prefix,)).fetchone()
    previous=strict_json_loads(old[0]) if old else None
    cache={}
    for c in candidates:
        eid,_=evidence_identity(c['seed'],anchor=c['anchor'],border=c['border_side'],dimension=c['dimension'],profile=c['profile'],build_id=c['build_id'],requirements=c['requirements'],world_settings_id=c['world_settings_id'],source_observation_id=c['source_observation_id'],provider_id=c['provider_id'],evidence_policy=c['evidence_policy'],objective_id=objective_id)
        row=ledger.conn.execute('SELECT value FROM automation_meta WHERE key=?',('verification.evidence.'+eid,)).fetchone()
        if row:cache[eid]=strict_json_loads(row[0])
    persisted_objects=dict(cache);last_progress=None
    def persist(state):
        nonlocal last_progress
        progress={key:value for key,value in state.items() if key!='receipts'}
        encoded_progress=json.dumps(progress,sort_keys=True,allow_nan=False)
        changed=[(eid,r) for eid,r in state.get('receipts',{}).items() if persisted_objects.get(eid) is not r]
        if not changed and encoded_progress==last_progress:return
        with ledger.queue.transaction():
            for eid,receipt in changed:
                raw=json.dumps(receipt,sort_keys=True,separators=(',',':'),allow_nan=False)
                if len(raw.encode())>16<<20:raise ValueError('Verification receipt artifact cap')
                ledger.conn.execute('INSERT INTO automation_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('verification.evidence.'+eid,raw))
            ledger.conn.execute('INSERT INTO automation_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(prefix,encoded_progress))
        persisted_objects.update(changed);last_progress=encoded_progress
    with ledger.queue.ownership():
        ledger.protect_verification([c['world_id'] for c in candidates])
        result=advance_ordered_finalization(objective_id,candidates,k,cache,verifier=verifier,budget=budget,previous=previous,
            retry_pending=retry_pending,on_progress=persist,build_id=context['build_id'])
        persist(dict(result['progress'],receipts=result['receipts']))
        if result['is_complete']:ledger.protect_verification([c['world_id'] for c in candidates],release=True)
    return result
