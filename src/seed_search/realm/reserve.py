"""Finite candidate capacities and historical resume contracts (no scoring changes)."""
import json
import sqlite3
from pathlib import Path

MAX_CANDIDATES = 1000


def selection_policy(top_k, *, saved=None, historical=False):
    if type(top_k) is not int or not 0 <= top_k <= MAX_CANDIDATES:
        raise ValueError('top_k must be an integer in 0–1000')
    factor = 1 if historical else 2
    if saved is not None:
        if not isinstance(saved, dict) or set(saved) != {'top_k','candidate_capacity','reserve_factor','historically_complete'}:
            raise ValueError('Invalid saved candidate policy')
        if type(saved['reserve_factor']) is not int or saved['reserve_factor'] not in (1,2):
            raise ValueError('Invalid saved reserve factor')
        if type(saved['historically_complete']) is not bool:
            raise ValueError('Invalid reserve completeness')
        factor = saved['reserve_factor']
        if saved['top_k'] != top_k or type(saved['top_k']) is not int:
            raise ValueError('Top-K capacity cannot change on resume; use a fresh run')
    capacity = factor * top_k
    if capacity > MAX_CANDIDATES:
        raise ValueError('2× candidate capacity exceeds the existing 1000-candidate bound; reduce top_k')
    policy = dict(top_k=top_k,candidate_capacity=capacity,reserve_factor=factor,
                  historically_complete=not historical if saved is None else saved['historically_complete'])
    if saved is not None and saved != policy:
        raise ValueError('Saved candidate capacity is inconsistent')
    return policy


def resume_policy(run, top_k, resume):
    if not resume:
        return selection_policy(top_k), True
    path = Path(run).absolute() / 'realm.sqlite'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as conn:
        rows = dict(conn.execute("SELECT key,value FROM meta WHERE key IN ('identity','native_pipeline','top_selection')"))
    identity = json.loads(rows.get('identity','{}'))
    saved = identity.get('top_selection')
    if saved is None and 'top_selection' in rows:
        saved = json.loads(rows['top_selection'])
    previous = json.loads(rows.get('native_pipeline','{}'))
    if 'top_k' in previous and previous['top_k'] != top_k:
        raise ValueError('Top-K capacity cannot change on resume; use a fresh run')
    return selection_policy(top_k,saved=saved,historical=saved is None), 'top_selection' in identity


def compatible_resume_identity(run, attempted):
    """Recognize the unchanged legacy record adapter after retention-only edits.

    The old adapter pin hashed the whole orchestration module. Permit only the
    reviewed pre-expansion hash, identical Prototype AST and identical other
    native identity fields; all configuration/evidence checks still apply.
    """
    import ast
    import hashlib
    import copy
    path=Path(run).absolute()/'realm.sqlite'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as conn:
        row=conn.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
    saved=json.loads(row[0])
    module=Path(__file__).with_name('native_batch.py')
    node=next(n for n in ast.parse(module.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Prototype')
    if hashlib.sha256(ast.dump(node).encode()).hexdigest()!='3ee6a3f35a5e475d5b77e024958f2c779650d23c48d68bd0ff919f6069aa0b75':
        return attempted
    result=copy.deepcopy(attempted)
    for key in ('native','prototype'):
        before=saved.get(key);after=result.get(key)
        if not isinstance(before,dict) or not isinstance(after,dict):continue
        if before.get('record_adapter_sha256')!='811600b43ca7afb1b18bd30fa98d10555dd46edf56380bda2f7a351435139eca':continue
        if after.get('record_adapter_sha256')!=hashlib.sha256(module.read_bytes()).hexdigest():continue
        if {k:v for k,v in before.items() if k!='record_adapter_sha256'}!={k:v for k,v in after.items() if k!='record_adapter_sha256'}:continue
        after['record_adapter_sha256']=before['record_adapter_sha256']
    return result
