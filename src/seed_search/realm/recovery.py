"""Explicit imports of actual positive starts; never infer discovery absence.

Original input/lease records remain immutable. Additional anchors, their actual
source proofs and both variant tasks commit together. Frozen terrain pools need
an explicit new revision to include subsequent recovered candidates.
"""
import copy
import hashlib
import json
from pathlib import Path

from ..backend import Backend,configure_native_threads
from ..seeds import parse_seed
from .baseline import evaluate_seed
from .bounds import contains,json_bounds
from .capabilities import identity as backend_identity
from .resources import disk_policy,disk_status
from .store import RealmStore,canonical,index_key
from .verification import pinned_world_settings

POLICY='actual-positive-anchor-recovery-v1'


def _validate(evidence,cfg,seed,bounds,kind):
    source=evidence.get('source',{});points=evidence.get('coordinates')
    provider=source.get('provider') if isinstance(source,dict) else None
    version=cfg['game']['bds_version'] if provider=='bds' else cfg['game']['target_version']
    expected_convention='stronghold_stairway_block_xz' if kind=='stronghold' else 'structure_start_block_xz'
    if (not isinstance(source,dict) or source.get('kind')!='actual_generation'
        or not isinstance(provider,str) or not provider.strip() or provider.lower() in ('native','chunkbase','cubiomes')
        or source.get('version')!=version or source.get('target_version')!=cfg['game']['target_version']
        or str(parse_seed(evidence.get('seed')))!=seed or evidence.get('structure')!=kind
        or evidence.get('actual') is not True or evidence.get('verification')!='VERIFIED'
        or evidence.get('confirmed_absent') is not False or evidence.get('anchor_convention')!=expected_convention
        or evidence.get('bounds')!=json_bounds(bounds) or evidence.get('world_settings')!=pinned_world_settings()
        or not isinstance(evidence.get('artifact'),str) or not evidence['artifact'].strip()
        or not isinstance(evidence.get('artifact_sha256'),str) or len(evidence['artifact_sha256'])!=64
        or any(c not in '0123456789abcdef' for c in evidence['artifact_sha256'])
        or not isinstance(points,list) or not 1<=len(points)<=100
        or any(not isinstance(p,list) or len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,int) for v in p) for p in points)
        or any(not contains(p,bounds) for p in points)):
        raise ValueError('Positive recovery requires exact seed/build/settings/bounds, actual start convention and artifact provenance')
    return sorted({tuple(p) for p in points})


def import_positive(store,index,evidence,*,candidate_id=None,backend_factory=Backend):
    """Trust explicitly supplied positive provenance, without certifying a provider.

    No native/website negative is upgraded to absence. A positive import can
    supply an otherwise missed required start for provisional evaluation, but
    cannot establish actual Realm eligibility, natural terrain or discovery recall.
    """
    if store.db.in_transaction:raise ValueError('Finish caller transaction before positive recovery')
    if not isinstance(evidence,dict):raise ValueError('Positive recovery evidence must be a JSON object')
    evidence_bytes=len(canonical(evidence).encode())
    if evidence_bytes>1<<20:raise ValueError('Positive evidence must be at most 1 MiB; reference larger artifacts by hash')
    cfg=store.identity['config'];idx=index_key(index)
    kind=evidence.get('structure')
    if kind not in cfg['structures']['required']+cfg['structures'].get('nether_required',['fortress','bastion']):
        raise ValueError('Positive recovery supports required structures only')
    provider=backend_identity()
    if 'backend' in store.identity and store.identity['backend']!=provider:
        raise ValueError('Recovery backend differs from the baseline checkpoint')
    implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    proof_id=hashlib.sha256(canonical({'policy':POLICY,'index':index,'evidence':evidence,'candidate_id':candidate_id}).encode()).hexdigest()
    with store.db:
        store.db.execute('BEGIN IMMEDIATE')
        seed_row=store.db.execute('SELECT seed FROM seeds WHERE idx=?',(idx,)).fetchone()
        if not seed_row:raise ValueError('Recover only a completed input index')
        seed=seed_row[0]
        target=store.get_candidate(candidate_id) if candidate_id else None
        if candidate_id and (target is None or target['index']!=index or target['seed']!=seed):
            raise ValueError('Recovery candidate does not belong to this completed input')
        from .config import origin_policy
        origin=origin_policy(cfg)
        if target is None and (kind!='stronghold' or origin):raise ValueError('Origin recovery needs an existing candidate ID')
        bounds=cfg['discovery']['overworld_bounds'] if target is None else target['bounds']['final_nether' if kind in ('fortress','bastion') else 'overworld']
        points=_validate(evidence,cfg,seed,bounds,kind)
        if target and kind=='stronghold' and not origin and tuple(target['stronghold']) not in points:
            raise ValueError('Stronghold evidence must establish the candidate center')
        saved=store.get_observation(proof_id)
        if saved:
            if saved.get('implementation_sha256')!=implementation or saved.get('backend')!=provider:
                raise ValueError('Positive recovery implementation changed; original proof retained')
            return {**saved['result'],'replayed':True}
        from .reports import ensure_score_revision_complete
        ensure_score_revision_complete(store)
        previous_revision=store.get_state('rescore_revision')
        centers=points if target is None else [tuple(target['stronghold'])]
        configure_native_threads(cfg['search'].get('native_threads_per_worker',1))
        # DDL is transactional too; a failed evaluation/commit leaves no half import.
        store.db.execute('CREATE TABLE IF NOT EXISTS actual_anchor_recovery(candidate_id TEXT PRIMARY KEY,idx TEXT NOT NULL,observation_id TEXT NOT NULL)')
        store.db.execute('CREATE INDEX IF NOT EXISTS actual_anchor_recovery_idx ON actual_anchor_recovery(idx,candidate_id)')
        added=[];updated=[];pool_refresh=False;rescore_required=bool(previous_revision);pending_bytes=evidence_bytes+8192
        for center in centers:
            cid=f'{seed}:{center[0]}:{center[1]}'
            previous=store.get_candidate(cid)
            actual=copy.deepcopy((previous or {}).get('actual_required_structure_evidence',{}))
            accepted=[list(p) for p in points if kind!='stronghold' or origin or p==center]
            actual.setdefault(kind,[]).append({'observation_id':proof_id,'coordinates':accepted})
            known={name:sorted({tuple(p) for entry in entries for p in entry['coordinates']}) for name,entries in actual.items()}
            class RecoveredBackend:
                def __init__(self,value):self.inner=backend_factory(value)
                def __enter__(self):self.inner.__enter__();return self
                def __exit__(self,*args):return self.inner.__exit__(*args)
                def __getattr__(self,name):return getattr(self.inner,name)
                def structure_pair(self,name,query):
                    if name=='stronghold' and not origin:return [list(center)],[list(center)]
                    raw,viable=self.inner.structure_pair(name,query)
                    extra=[p for p in known.get(name,[]) if query[0]<=p[0]<=query[2] and query[1]<=p[1]<=query[3]]
                    return sorted({tuple(p) for p in raw}|set(extra)),sorted({tuple(p) for p in viable}|set(extra))
            result=evaluate_seed(index,seed,cfg,backend_factory=RecoveredBackend)
            if len(result['anchors'])!=1:raise ValueError('Recovery did not evaluate exactly its declared anchor')
            candidate=result['anchors'][0]
            candidate['actual_required_structure_evidence']=actual
            candidate['actual_recovery']={'policy':POLICY,'implementation_sha256':implementation,'backend':provider,
                                          'anchor_origin':(previous or {}).get('actual_recovery',{}).get('anchor_origin','baseline' if previous else 'actual_positive'),
                                          'discovery_recall':'UNRESOLVED','realm_eligibility':'UNVERIFIED'}
            for name,entries in actual.items():
                observation=(candidate['required_nether_structures'] if name in ('fortress','bastion') else candidate['required_structures'])[name]
                positive=sorted({tuple(p) for entry in entries for p in entry['coordinates'] if contains(p,observation['bounds'])})
                observation['actual_positive_coordinates']=[list(p) for p in positive]
                observation['actual_presence']='VERIFIED_POSITIVE' if positive else 'UNKNOWN'
                observation['actual_observation_ids']=[entry['observation_id'] for entry in entries]
            if previous:
                snapshot_id=hashlib.sha256(canonical({'kind':'pre_actual_recovery','candidate':previous}).encode()).hexdigest()
                store.db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?)',(snapshot_id,cid,canonical({'id':snapshot_id,'kind':'pre_actual_recovery','candidate':previous})))
                pending_bytes+=len(canonical(previous).encode())
                # Preserve independent terrain/actual verification fields; refresh
                # only baseline predictions justified by the newly supplied start.
                candidate={**previous,**candidate}
                for field in ('final_nether','final_nether_status','terrain_status','realm_eligibility'):
                    if field in previous:candidate[field]=previous[field]
                if previous['qualification']=='VERIFIED':candidate['qualification']='VERIFIED'
                pool_refresh|=previous['qualification'] not in ('PREDICTED','VERIFIED') and candidate['qualification'] in ('PREDICTED','VERIFIED')
                rescore_required|=bool(store.db.execute('SELECT 1 FROM variants WHERE candidate_id=? LIMIT 1',(cid,)).fetchone())
                store._upsert_candidate_locked(candidate,allow_qualification_change=True);updated.append(cid)
            else:
                store.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?)',(cid,idx,seed,candidate['qualification'],canonical(candidate)))
                store.db.execute('INSERT INTO actual_anchor_recovery VALUES (?,?,?)',(cid,idx,proof_id))
                store.db.executemany("INSERT INTO variant_tasks VALUES (?,?,'pending')",[(cid,v) for v in ('v1','v2')])
                added.append(cid)
            pending_bytes+=len(canonical(candidate).encode())
            disk_status(store.run,disk_policy(cfg['search']),additional_bytes=pending_bytes*3)
        pool_refresh|=bool(added)
        result={'policy':POLICY,'observation_id':proof_id,'completed_input_index':index,'seed':seed,
                'added_candidates':added,'updated_candidates':updated,'discovery_recall':'UNRESOLVED',
                'actual_realm_eligibility':'UNVERIFIED','terrain_pool_refresh_required':pool_refresh,
                'rescore_required':rescore_required,'replayed':False}
        proof={'id':proof_id,'kind':'actual_positive_structure_import','candidate_id':candidate_id,'evidence':evidence,
               'implementation_sha256':implementation,'backend':provider,'result':result}
        store.db.execute('INSERT INTO observations VALUES (?,?,?)',(proof_id,candidate_id,canonical(proof)))
        if pool_refresh:
            store._set('terrain_pool_refresh_required',True)
        if rescore_required:
            # Block stale ranked/export views until generation-free rescore finishes.
            policy=(previous_revision or {}).get('policy',cfg)
            policy_hash=hashlib.sha256(canonical(policy).encode()).hexdigest()
            number=(previous_revision or {}).get('number',0)+1
            store._set('rescore_revision',{'id':f'{number}-{policy_hash[:16]}','number':number,
                'status':'running','phase':'candidates','candidate_cursor':'','variant_cursor':['','',''],
                'policy':policy,'policy_sha256':policy_hash,'rescored_candidates':0,'rescored_variants':0})
            store._set('actual_recovery_rescore_required',True)
        if added:
            store._set('recovered_stronghold_anchors',store.db.execute('SELECT count(*) FROM actual_anchor_recovery').fetchone()[0])
        return result


if __name__=='__main__':
    import argparse
    from .runner import _scan_lock
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True);parser.add_argument('--index',required=True,type=int)
    parser.add_argument('--candidate');parser.add_argument('--evidence',required=True)
    args=parser.parse_args()
    if Path(args.evidence).stat().st_size>1<<20:parser.error('Positive evidence JSON must be at most 1 MiB')
    with _scan_lock(args.run),RealmStore(args.run,resume=True) as store:
        result=import_positive(store,args.index,json.loads(Path(args.evidence).read_text()),candidate_id=args.candidate)
        if result['rescore_required'] and store.get_state('actual_recovery_rescore_required'):
            from .reports import rescore
            revision=store.get_state('rescore_revision')
            if revision['status']!='complete':
                result['rescore']=rescore(store,revision['policy'])
            store.set_state('actual_recovery_rescore_required',False)
    print(json.dumps(result,indent=2))
