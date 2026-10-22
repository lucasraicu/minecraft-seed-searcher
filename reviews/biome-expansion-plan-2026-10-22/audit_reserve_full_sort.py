#!/usr/bin/env python3
"""Read-only 2K replay/full-sort audit using frozen legacy per-world offer semantics.

Independent of the new ledger/bulk merger. Per-world legacy/product scoring is
intentionally reused; exact rank normalization and whole-cohort sorting are local.
V3 atomic semantics are checked by the separate coordinate oracle audit.
"""
import argparse,json,sqlite3,sys,time
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.retention import automation_offers
from seed_search.catalog.reserve_policy import contract


def atom(value):
    if type(value)is int:return 0,Fraction(value)
    if type(value)is str:return 1,value
    if isinstance(value,dict) and set(value)=={'decimal'}:return 0,Fraction(Decimal(value['decimal']))
    if isinstance(value,dict) and set(value)=={'numerator','denominator'}:return 0,Fraction(value['numerator'],value['denominator'])
    raise ValueError('Unsupported exact rank atom')


def key(row):return tuple(atom(value) for value in row['rank']),row['world_id']


def comparable(row):
    # V2/V3 summary IDs differ by registry/profile/extension. Geometry and every
    # other member field must still agree; source/layout reachability is separately
    # checked in the full migration audit.
    if 'rank' in row['member'] and row['member']['rank']!=row['rank']:raise ValueError('Embedded member rank differs from authoritative rank')
    return dict(world_id=row['world_id'],rank=row['rank'],member={k:v for k,v in row['member'].items() if k not in ('layout_id','rank')})


def run(source,destination,output):
    started=time.monotonic();original=AutomationStore(source);target=AutomationStore(destination)
    old=original.snapshot();new=target.snapshot();groups={};caps=contract()['retained_objectives']
    actual={}
    for row in new['memberships']:
        if not row['objective_id'].startswith('v3.'):actual.setdefault(row['objective_id'],[]).append(row)
    db=sqlite3.connect((Path(source)/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    try:
        for i,entry in enumerate(old['worlds']):
            bundle=original.artifacts.get_json(entry['artifact'])
            evaluations=json.loads(db.execute('SELECT evaluations FROM automation_receipts WHERE world_id=?',(entry['world_id'],)).fetchone()[0])
            offers=automation_offers(bundle['observation'],bundle['summaries'],evaluations)
            for off in offers:
                row=dict(off,world_id=entry['world_id']);group=groups.setdefault(off['objective_id'],{})
                incumbent=group.get(entry['world_id'])
                if incumbent is None or key(row)<key(incumbent):group[entry['world_id']]=row
            if (i+1)%50==0:print(json.dumps(dict(worlds=i+1,seconds=time.monotonic()-started)),flush=True)
    finally:db.close()
    checked=memberships=0;failures=[]
    for oid,capacity in caps.items():
        if oid.startswith('v3.'):continue
        expected=sorted(groups.get(oid,{}).values(),key=key)[:capacity];observed=actual.get(oid,[])
        if [comparable(r) for r in expected]!=[comparable(r) for r in observed]:failures.append(dict(objective_id=oid,expected=len(expected),actual=len(observed)))
        checked+=1;memberships+=len(observed)
    report=dict(status='FAIL' if failures else 'PASS',source_snapshot=original._binding()['snapshot_id'],destination_snapshot=target._binding()['snapshot_id'],worlds=len(old['worlds']),objectives=checked,memberships=memberships,failures=failures,seconds=time.monotonic()-started,method='Frozen V2 per-world offer semantics plus independent exact whole-cohort sort; V3 atomic oracle audited separately. Versioned layout IDs and redundant embedded rank are normalized; every embedded rank must first equal the authoritative rank.')
    Path(output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    return not failures

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--destination',required=True);p.add_argument('--output',required=True);a=p.parse_args();raise SystemExit(0 if run(Path(a.source).absolute(),Path(a.destination).absolute(),a.output) else 1)
