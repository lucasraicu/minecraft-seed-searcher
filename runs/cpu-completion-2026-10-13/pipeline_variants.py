#!/usr/bin/env python3
"""Bounded paired pipeline scheduling experiment, preserving raw receipts."""
import argparse, hashlib, json, time
from pathlib import Path
from seed_search.realm.config import two_group_blueprint_config
from seed_search.realm.native_batch import Prototype, persist_pipeline
from seed_search.realm.store import RealmStore

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ledger',type=Path,required=True)
    p.add_argument('--encoding-only',action='store_true')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    cfg=two_group_blueprint_config(); proto=Prototype(a.build,cfg)
    results=[]
    variants=[('control',3,False),('queue2',2,False),
                               ('queue2-repeat',2,False),('control-repeat',3,False),
                               ('writer',3,True),('control-writer',3,False),
                               ('control-writer-repeat',3,False),('writer-repeat',3,True)]
    if a.encoding_only:
        variants=[('encoded',3,False),('plain',3,False),('plain-repeat',3,False),('encoded-repeat',3,False)]
    for label,queue,writer in variants:
        ledger=json.loads(a.ledger.read_text())
        if ledger['total_measured_seconds']+60>ledger['hard_cap_seconds']:
            raise RuntimeError('Insufficient remaining shared budget')
        run=a.output/label
        started=time.monotonic(); ok=False
        try:
            stats=persist_pipeline(proto,run,50000,start_index=3000000,threads=34,
                    batch_size=16384,retention='survivors',max_misses=2,
                    inflight=queue,prepare_on_writer=writer,encoded=not label.startswith('plain'))
            with RealmStore(run,resume=True) as store:
                integrity=store.db.execute('PRAGMA integrity_check').fetchone()[0]
                rows=[r for r in store.iter_candidates()]
                status=store.status()
            if status['completed_seeds']!=50000 or integrity!='ok':
                raise RuntimeError('Incomplete pipeline experiment')
            ok=True
        finally:
            wall=time.monotonic()-started
            event={'kind':'pipeline_variant','label':label,'inputs':50000,
                   'inflight':queue,'prepare_on_writer':writer,'encoded':not label.startswith('plain'),
                   'wall_seconds':wall,'ok':ok}
            ledger['measured_profile_seconds']+=wall
            ledger['total_measured_seconds']=ledger['measured_profile_seconds']+ledger['measured_cli_seconds']
            ledger['events'].append(event);a.ledger.write_text(json.dumps(ledger,indent=2)+'\n')
        results.append({'event':event,'pipeline':stats,'sqlite_integrity':integrity,
                        'retained':len(rows),'records_sha256':hashlib.sha256(
                        json.dumps(rows,sort_keys=True).encode()).hexdigest()})
        (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(label,round(wall,4),len(rows),flush=True)

if __name__=='__main__':main()
