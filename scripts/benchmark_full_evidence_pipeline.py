"""Bounded same-policy full-record pipeline scheduling comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from seed_search.realm.config import outpost_blueprint_config
from seed_search.realm.native_batch import Prototype,persist_pipeline,semantic_record
from seed_search.realm.store import RealmStore,canonical


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--count',type=int,default=10000)
    args=parser.parse_args()
    if args.output.exists() or not 1<=args.count<=100000:parser.error('Fresh directory and count 1–100000 required')
    estimate=12*args.count*65536
    if shutil.disk_usage(ROOT).free<estimate+(16<<30):raise RuntimeError('Insufficient disk reserve')
    args.output.mkdir(parents=True)
    arms=[(False,1024),(True,1024),(False,4096),(True,4096)]
    observations=[];expected=None
    for trial in range(3):
        for writer,batch in arms[trial:]+arms[:trial]:
            path=args.output/f'{trial}-{writer}-{batch}'
            p=Prototype(args.native,outpost_blueprint_config())
            result=persist_pipeline(p,path,args.count,run_key=120280003000,threads=16,
                                    batch_size=batch,prepare_on_writer=writer)
            with RealmStore(path,resume=True) as store:
                digest=hashlib.sha256()
                for record in store.iter_results():digest.update(canonical(semantic_record(record)).encode())
                for table in ('discovery_tasks','inventory_work','variant_tasks'):
                    for row in store.db.execute(f'SELECT * FROM {table} ORDER BY 1,2'):digest.update(canonical(row).encode())
                assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert store.db.execute('PRAGMA synchronous').fetchone()[0]==2
                fingerprint=digest.hexdigest()
                if expected is None:expected=fingerprint
                assert expected==fingerprint
                service=store.get_state('native_pipeline')
            row={'trial':trial,'prepare_on_writer':writer,'batch':batch,'result':result,'pipeline':service,
                 'fingerprint':fingerprint,'rate':args.count/result['wall_seconds']}
            observations.append(row)
            (args.output/'results.json').write_text(json.dumps(observations,indent=2)+'\n')
            print(trial,writer,batch,row['rate'],flush=True)
    print({f'{w}-{b}':statistics.median(r['rate'] for r in observations if r['prepare_on_writer']==w and r['batch']==b) for w,b in arms})


if __name__=='__main__':main()
