# Codex targeted patch review

Original worker93ba15b1adf2 terminal succeeded tests24, but finalization NOT accepted. Use embedded source below as starting point; create ONLY finalization.py + newtest_finalization_scopes.py. Existing original tests are in original worker snapshot, not main; preserve public signatures where sound.

Fix defects: pass/fail receipt must verify evidence_id/world_id/canonicalseed and actual evidence provenance from existing BDS receipt (a bare pass string/predictivecheck is not verified BDS); evidence identity bind worldsettings/sourceobservation/provider/evidence policy + seed/anchor/dimension/border/profile/build/requirements. Missing actual requirements/anchor/build must never reuse across unrelated objectives; safe fallback include objectiveID when requirements not explicit, pending when insufficient scope for actual verification. Keep compatible explicit scoped evidence shareable across lists. Deduplicate candidates by world/seed in frozen rank order before counting passes. Freeze rank input digest in progress and reject alteredresume input. Budget integer>=0 explicit when verifier supplied, increment exactlyonce per attempt including exception/invalid response. Errors/inconclusive/pending must be retryable under budget on later invocation; terminal pass/fail reusable only validated complete scope. Do not silently treat malformedreceipt as pass. Persist using existing ingestion.atomic_json strictbounded read (16MiB), no customneworchestration framework. Remain pure advancement helper, no BDS launch or websitecampaign. Remove extraneous global orchestration helpers if unnecessary but preserve original API tests where safe. New tests meaningful regression mismatched receipt identity, forgedbarepass, crossproduct leakage, duplicate world, exceptionbudget, retry, frozeninput mismatch, scoped promotion evidence. Tests can construct actual-shaped fixture BDS receipts; no Docker/network/native/search.

## Starting implementation
```python
"""Authoritative candidate finalization and scoped verification engine.

Implements bounded finalization selection and promotion over frozen rank orders.
Keyed by scoped requirements + anchor + border + dimension + profile + build identity.
Passing candidates advance to target K; failures are scoped to the specific objective;
inconclusive and error states remain pending.
Reuses existing receipts and store/queue interfaces without a second orchestrator or new DB.
"""
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from .models import world_id
from .registry import canonical_json, digest


STATUS_PASS = 'pass'
STATUS_FAIL = 'fail'
STATUS_INCONCLUSIVE = 'inconclusive'
STATUS_PENDING = 'pending'
STATUS_ERROR = 'error'

VALID_RECEIPT_STATUSES = (
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_INCONCLUSIVE,
    STATUS_PENDING,
    STATUS_ERROR,
)


def evidence_identity(
    seed: Any,
    *,
    anchor: Optional[Sequence[int]] = None,
    border: Optional[int] = None,
    dimension: str = 'overworld',
    profile: Optional[str] = None,
    build_id: Optional[str] = None,
    requirements: Optional[Any] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Derive deterministic identity digest for scoped candidate verification conditions."""
    descriptor = {
        'revision': 'catalog-evidence-identity-v1',
        'seed': str(seed),
        'anchor': [int(a) for a in anchor] if anchor is not None else None,
        'border': int(border) if border is not None else None,
        'dimension': str(dimension),
        'profile': str(profile) if profile is not None else None,
        'build_id': str(build_id) if build_id is not None else None,
        'requirements': requirements if requirements is not None else {},
    }
    ident = digest(descriptor)
    return ident, descriptor


def make_evidence_receipt(
    evidence_id: str,
    world_id: str,
    seed: Any,
    status: str,
    *,
    reason: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    timestamp: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a canonical serializable evidence receipt."""
    if status not in VALID_RECEIPT_STATUSES:
        raise ValueError(f"Invalid receipt status {status!r}; expected one of {VALID_RECEIPT_STATUSES}")
    if not isinstance(evidence_id, str) or len(evidence_id) != 64:
        raise ValueError("Invalid evidence_id: expected 64-char hex digest")
    if not isinstance(world_id, str) or len(world_id) != 64:
        raise ValueError("Invalid world_id: expected 64-char hex digest")

    return {
        'revision': 'catalog-evidence-receipt-v1',
        'evidence_id': evidence_id,
        'world_id': world_id,
        'seed': str(seed),
        'status': status,
        'reason': str(reason) if reason is not None else None,
        'details': details or {},
        'timestamp': float(timestamp if timestamp is not None else time.time()),
    }


def advance_finalization(
    objective_id: str,
    candidates: Sequence[Dict[str, Any]],
    primary_k: int,
    receipts: Dict[str, Dict[str, Any]],
    *,
    verifier: Optional[Callable[[Dict[str, Any], str], Any]] = None,
    budget: Optional[int] = None,
    build_id: Optional[str] = None,
    requirements_extractor: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> Dict[str, Any]:
    """Advance finalization over a frozen rank-ordered candidate sequence.

    - Consumes candidates in frozen rank order.
    - Evaluates scoped evidence identity for each candidate.
    - Reuses existing cached receipts; only invokes verifier if uncached and within budget.
    - Passes advance to target K.
    - Failures are scoped to this objective/evidence and do not blacklist the seed globally.
    - Inconclusive/error outcomes remain pending.
    - Promotes passing reserves when primary candidates fail.
    - If budget exhausts before K passing candidates are found, records actual count and pending status.
    """
    if primary_k < 0:
        raise ValueError("primary_k must be non-negative")

    finalized: List[Dict[str, Any]] = []
    promoted: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    unverified: List[Dict[str, Any]] = []

    updated_receipts = dict(receipts)
    checks_performed = 0

    for idx, cand in enumerate(candidates):
        # Once target K is fully satisfied, stop verifying further candidates
        if len(finalized) >= primary_k:
            unverified.append(cand)
            continue

        wid = cand['world_id']
        seed = cand['seed']
        anchor = cand.get('anchor')
        border = cand.get('border_side') or cand.get('border')
        dimension = cand.get('dimension', 'overworld')
        profile = cand.get('profile')

        reqs = requirements_extractor(cand) if requirements_extractor else cand.get('requirements')
        ev_id, _ = evidence_identity(
            seed,
            anchor=anchor,
            border=border,
            dimension=dimension,
            profile=profile,
            build_id=build_id,
            requirements=reqs,
        )

        receipt = updated_receipts.get(ev_id)
        if receipt is None:
            if verifier is not None and (budget is None or checks_performed < budget):
                try:
                    res = verifier(cand, ev_id)
                    checks_performed += 1
                    if isinstance(res, dict) and 'status' in res:
                        receipt = res
                        if 'evidence_id' not in receipt:
                            receipt['evidence_id'] = ev_id
                        if 'world_id' not in receipt:
                            receipt['world_id'] = wid
                        if 'seed' not in receipt:
                            receipt['seed'] = str(seed)
                    elif isinstance(res, str):
                        receipt = make_evidence_receipt(ev_id, wid, seed, res)
                    else:
                        receipt = make_evidence_receipt(ev_id, wid, seed, STATUS_ERROR, reason='invalid_verifier_response')
                except Exception as exc:
                    checks_performed += 1
                    receipt = make_evidence_receipt(ev_id, wid, seed, STATUS_ERROR, reason=f'verifier_exception: {exc}')
                updated_receipts[ev_id] = receipt
            else:
                # Budget reached or no verifier available
                cand_copy = dict(cand, pending_reason='budget_exhausted_or_unverified', evidence_id=ev_id)
                pending.append(cand_copy)
                continue

        status = receipt.get('status', STATUS_PENDING)
        cand_entry = dict(cand, evidence_id=ev_id)

        if status == STATUS_PASS:
            finalized.append(cand_entry)
            if idx >= primary_k:
                promoted.append(cand_entry)
        elif status == STATUS_FAIL:
            failed_entry = dict(cand_entry, failure_reason=receipt.get('reason', 'verification_failed'))
            failed.append(failed_entry)
        else:
            # Inconclusive, pending, or error
            pending_entry = dict(cand_entry, pending_reason=receipt.get('reason', status))
            pending.append(pending_entry)

    is_complete = (len(finalized) >= primary_k)
    status_label = 'complete' if is_complete else 'pending'

    return {
        'objective_id': objective_id,
        'target_k': primary_k,
        'status': status_label,
        'is_complete': is_complete,
        'verified_count': len(finalized),
        'finalized': finalized,
        'promoted': promoted,
        'failed': failed,
        'pending': pending,
        'unverified': unverified,
        'checks_performed': checks_performed,
        'receipts': updated_receipts,
        'progress': {
            'objective_id': objective_id,
            'target_k': primary_k,
            'verified_count': len(finalized),
            'promoted_count': len(promoted),
            'failed_count': len(failed),
            'pending_count': len(pending),
            'is_complete': is_complete,
            'checks_performed': checks_performed,
        },
    }


def finalize_all_objectives(
    objective_candidates: Dict[str, Sequence[Dict[str, Any]]],
    primary_capacities: Dict[str, int],
    receipts: Dict[str, Dict[str, Any]],
    *,
    verifier: Optional[Callable[[Dict[str, Any], str], Any]] = None,
    total_budget: Optional[int] = None,
    build_id: Optional[str] = None,
    requirements_extractor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
) -> Dict[str, Any]:
    """Execute finalization across multiple objectives with shared receipts and shared budget."""
    shared_receipts = dict(receipts)
    results_by_objective = {}
    remaining_budget = total_budget
    total_checks = 0

    for obj_id, candidates in objective_candidates.items():
        k = primary_capacities.get(obj_id, 0)
        req_fn = (lambda c: requirements_extractor(obj_id, c)) if requirements_extractor else None

        res = advance_finalization(
            obj_id,
            candidates,
            k,
            shared_receipts,
            verifier=verifier,
            budget=remaining_budget,
            build_id=build_id,
            requirements_extractor=req_fn,
        )
        checks = res['checks_performed']
        total_checks += checks
        if remaining_budget is not None:
            remaining_budget = max(0, remaining_budget - checks)

        shared_receipts = res['receipts']
        results_by_objective[obj_id] = res

    all_complete = all(r['is_complete'] for r in results_by_objective.values())

    return {
        'status': 'complete' if all_complete else 'pending',
        'is_complete': all_complete,
        'objectives': results_by_objective,
        'total_checks_performed': total_checks,
        'receipts': shared_receipts,
    }


def generic_search_candidates(
    candidates_by_objective: Dict[str, Sequence[Dict[str, Any]]],
    *,
    pins: Optional[Sequence[str]] = None,
) -> List[str]:
    """Deduplicated sorted union of all retained candidates (primary + reserve + pins) for generic search.

    Ensures reserve candidate status for an objective never masks matching worlds from generic search.
    """
    wids: Set[str] = set()
    if pins:
        wids.update(pins)
    for cands in candidates_by_objective.values():
        for c in cands:
            wid = c.get('world_id') if isinstance(c, dict) else c
            if isinstance(wid, str):
                wids.add(wid)
    return sorted(list(wids))


def save_finalization_progress(path: str | Path, progress_data: Dict[str, Any]) -> None:
    """Durably persist serializable finalization progress atomically without new database."""
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    blob = canonical_json(progress_data)
    fd, tmp_name = tempfile.mkstemp(prefix='.finalization-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def load_finalization_progress(path: str | Path) -> Dict[str, Any]:
    """Load previously persisted finalization progress from durable JSON file."""
    target = Path(path).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"Finalization progress file not found: {target}")
    return json.loads(target.read_text())

```
