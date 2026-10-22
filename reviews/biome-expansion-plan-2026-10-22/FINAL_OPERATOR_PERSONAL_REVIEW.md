# Final supplemental implementation review
High read-only source reasoning; no tool calls, edits or tests. Scope already approved. Review concrete defects only. All source below from isolated implementation, authoritative. No automatic campaign: finalist adapter calls supplied existing scoped BDS verifier only with explicit finitebudget, persists existing SQLite automation_meta, uses pure advance_finalization (also included). queue.ownership is reentrant cross-process flock; queue.transaction is nested SQLite atomic transaction. All immutable snapshots remain GC roots; protect_verification is additional setroot. Saved receipts are structural actual-game proof references from trusted operator, not untrusted website input. UI personal view is only exposed when endpoint returns reserve_count and primary_count; historical runningserver unchanged. Candidate fetch effects already abort stale generations/changedrun. Backend validates view(primary/reserve), pages SQLite top_candidates rank1..2K; legacy primary unchanged/reserveempty. review the adapter contexts, cross-list shared receipt reuse, source/anchor/border/dimension scope, product anchor handling and personal UI selection/paging.

## src/seed_search/catalog/finalization_operator.py
```python
"""Resolve saved legacy anchor bindings before the existing finalist adapter.

This is an explicit operator entry point, not a scheduler. It launches no BDS
work unless the caller supplies the existing scoped verifier and finite budget.
"""
import json
from .finalization import advance_finalization,evidence_identity
from .registry import digest
from .ingestion import strict_json_loads


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
                if not isinstance(anchor,list) or len(anchor)!=2 or not all(type(n)is int and abs(n)<=30000000 for n in anchor) or side not in (2048,4096,8192):
                    raise ValueError('Reference sample verification requires an explicit anchor and border')
                member['anchor']=anchor;member['border_side']=side
            else:raise ValueError('Saved objective anchor is unavailable')
        if verification_context.get('dimension')=='nether' and not isinstance(product_anchor,dict):
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
    def persist(state):
        with ledger.queue.transaction():
            for eid,receipt in state.get('receipts',{}).items():
                raw=json.dumps(receipt,sort_keys=True,separators=(',',':'),allow_nan=False)
                if len(raw.encode())>16<<20:raise ValueError('Verification receipt artifact cap')
                ledger.conn.execute('INSERT INTO automation_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('verification.evidence.'+eid,raw))
            progress={key:value for key,value in state.items() if key!='receipts'}
            ledger.conn.execute('INSERT INTO automation_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(prefix,json.dumps(progress,sort_keys=True,allow_nan=False)))
    with ledger.queue.ownership():
        ledger.protect_verification([c['world_id'] for c in candidates])
        result=advance_finalization(objective_id,candidates,k,cache,verifier=verifier,budget=budget,previous=previous,
            retry_pending=retry_pending,on_progress=persist,build_id=context['build_id'])
        persist(dict(result['progress'],receipts=result['receipts']))
        if result['is_complete']:ledger.protect_verification([c['world_id'] for c in candidates],release=True)
    return result

```

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

```

## App candidate loading
```tsx
  // Candidate page loading with bounded timeout, abort on cleanup, and bounded backoff
  useEffect(() => {
    let active = true;
    let timerId: any = null;
    let controller: AbortController | null = null;
    let loading = false;

    const loadPage = async () => {
      if (!active) return;
      if (loading || commandInFlight.current) { scheduleNextPage(); return; }
      loading = true;
      const generation = apiGeneration.current;
      controller = new AbortController();

      try {
        const result = await requestJson<{
          total: number;
          primary_count?:number;reserve_count?:number;view?:'primary'|'reserve';
          candidates: SeedCandidate[];
          runId?: string | null;
          generation?: number;
        }>(`/api/candidates?limit=${candidatePageSize}&offset=${candidateOffset}&view=${candidateView}`, {
          timeoutMs: 6000,
          signal: controller.signal,
        });

        if (!active || isResponseStale(generation, apiGeneration.current)) {
          return;
        }

        const data = result.data;
        if (!validCandidatePage(data)) throw new Error('Backend returned an invalid candidate page');
        if (snapshotMismatch(data, latestBackend.current)) return;
        if(data.view!==undefined&&data.view!==candidateView)return;
        setCandidateCounts(data.primary_count!==undefined&&data.reserve_count!==undefined?{primary:data.primary_count,reserve:data.reserve_count}:null);
        consecutivePageFailures.current = 0;
        setCandidatePageError(null);

        if (
          candidateRunId.current !== undefined &&
          data.runId !== undefined &&
          candidateRunId.current !== data.runId
        ) {
          candidateRunId.current = data.runId;
          if (candidateOffset !== 0) {
            setCandidateOffset(0);
            return;
          }
        } else if (candidateRunId.current === undefined && data.runId !== undefined) {
          candidateRunId.current = data.runId;
        }

        setCandidateTotal(data.total);
        if (data.total > 0 && candidateOffset >= data.total) {
          setCandidateOffset(Math.floor((data.total - 1) / candidatePageSize) * candidatePageSize);
          return;
        }

        setCandidates(data.candidates);
        setSelectedCandidate(
          (current) =>
            data.candidates.find((c: SeedCandidate) => c.id === current?.id) ??
            data.candidates[0] ??
            null
        );
      } catch (err: any) {
        if (!active || isResponseStale(generation, apiGeneration.current) || controller?.signal.aborted) {
          return;
        }
        consecutivePageFailures.current += 1;
        setCandidatePageError('Candidate list could not refresh. Showing the last loaded page; retrying.');
        // Do not flood toasts on polling failure; only show once if manual page change failed
        if (candidateOffset > 0 && consecutivePageFailures.current === 1) {
          showToast(`Failed to load page: ${err instanceof Error ? err.message : String(err)}`);
        }
      } finally {
        loading = false;
        scheduleNextPage();
      }
    };

    const scheduleNextPage = () => {
      if (!active) return;
      const delay = calculateBackoff(consecutivePageFailures.current, 3000, 10000);
      timerId = setTimeout(loadPage, delay);
    };

    void loadPage();

    return () => {
      active = false;
      if (timerId !== null) clearTimeout(timerId);
      if (controller) controller.abort();
    };
  }, [candidateOffset, candidateView, telemetry.runId, showToast]);

  // Bounded status polling loop with adaptive backoff
  useEffect(() => {
    let active = true;
    let timerId: any = null;
    let controller: AbortController | null = null;

    const scheduleNext = () => {
      if (!active) return;
      const baseInterval =
        telemetry.status === 'running' || telemetry.status === 'bds_verifying' ? 650 : 3000;
      const delay = calculateBackoff(consecutiveStatusFailures.current, baseInterval, 10000);
      timerId = setTimeout(async () => {
        if (!active || commandInFlight.current) {
          scheduleNext();
          return;
        }
        controller = new AbortController();
        await pollStatus(controller.signal);
        scheduleNext();
      }, delay);
    };

    // Initial immediate poll on mount
    const initialController = new AbortController();
    controller = initialController;
    void Promise.resolve().then(() => pollStatus(initialController.signal)).finally(() => {
      scheduleNext();
    });

    return () => {
      active = false;
      if (timerId !== null) clearTimeout(timerId);
      if (controller) controller.abort();
    };
  }, [telemetry.status, pollStatus]);

  // Freshness ages even when the browser receives no fetch completion.
  useEffect(() => {
    const timer = setInterval(() => {
      let mode = determineConnectionStatus({ hasEverConnected: hasEverConnected.current,
        consecutiveFailures: consecutiveStatusFailures.current,
        lastContactTimestamp: lastContactTimestampRef.current });
      if (progressError.current && mode === 'live') mode = 'stale';
      setDataMode(mode);
      setTelemetry(previous => previous.isStale === (mode !== 'live') ? previous
        : { ...previous, isStale: mode !== 'live' });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleToggleSweep = useCallback(async () => {
    try {
      if (telemetry.status === 'running' || telemetry.status === 'paused') {
        await postCommand('/api/sweep/stop');
        setTelemetry((prev) => ({ ...prev, status: 'idle', seedsPerSec: 0 }));
        showToast('Sweep stopped; checkpoint retained');
        return;
      }
      const data = await postCommand('/api/sweep/start', () => resolvePublicCatalogRoot(buildSweepRequest(config)));
      applyLaunch(data, true);
      setTelemetry((prev) => ({
        ...prev,
        status: 'running',
        runId: data.runId,
        totalScanned: 0,
        targetCount: config.sweepSeedCount,
        elapsedSeconds: 0,
        sweepProgress: 0,
        isStale: false,
      }));
      setDataMode('live');
      setCandidates([]);
      setSelectedCandidate(null);
      setCandidateOffset(0);
      setCandidateTotal(0);
      showToast(`Native sweep started (${config.sweepSeedCount.toLocaleString()} seeds)`);
    } catch (error) {
      showToast(`Sweep command failed: ${error instanceof Error ? error.message : String(er
```

App state: candidateView defaults primary; counts null. URL includes &view=${candidateView}. Effect dependency includes candidateView, offset, runId. On run change resetviewprimary/countsnull. Feed reserve selection onChange sets offset0 and view. Feed selectors hidden when countsnull. validCandidatePage rejects negative/noninteger counts >1000 and unknownview.
