"""Bounded, counterbalanced same-policy atomic chunk comparison, including SQL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_blueprint_batch import build
from seed_search.realm.config import river_blueprint_config
from seed_search.realm.native_batch import Prototype,semantic_record
from seed_search.realm.store import canonical
from seed_search.seeds import seed_from_index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--openmp-prefix',type=Path,required=True)
    parser.add_argument('--count',type=int,default=50000)
    parser.add_argument('--trials',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.count<=100000 or not 3<=args.trials<=5:
        parser.error('Count 1–100000; trials 3–5')
    if args.output.exists():parser.error('Fresh output directory required')
    full_count=min(5000,args.count)
    projected=args.trials*3*(args.count+full_count)*65536
    free=shutil.disk_usage(ROOT).free
    if free<projected+(16<<30):raise RuntimeError('Insufficient disk reserve')
    args.output.mkdir(parents=True)
    prototypes={};rows=[];key=120267002000;fingerprints={}
    for chunk in (16,64,128):
        directory=args.output/f'native-{chunk}'
        build(directory,args.openmp_prefix,work_chunk=chunk)
        prototypes[chunk]=Prototype(directory,river_blueprint_config())
    # Owned parallel positives, near misses and late biome failures must match.
    fixture_fingerprint=None
    for chunk,prototype in prototypes.items():
        fixtures=[(-1,-7,-1),(0,0,11),(123,-321,13),(0,0,27)]*48
        seeds=list(range(len(fixtures)))
        with prototype.sweep(seeds,32,fixtures=fixtures,complete=True) as batch:
            digest=hashlib.sha256(canonical(list(map(semantic_record,batch.records()))).encode()).hexdigest()
        if fixture_fingerprint is not None:assert digest==fixture_fingerprint
        fixture_fingerprint=digest
    for phase in ('native_only','compact_cli','full_cli'):
        count=full_count if phase=='full_cli' else args.count
        for trial in range(args.trials):
            order=[16,64,128];order=order[trial%3:]+order[:trial%3]
            for chunk in order:
                tag=f'{phase}-{chunk}-{trial}';receipt=args.output/f'{tag}.json'
                if phase=='native_only':
                    elapsed=0.;receipts=[]
                    for first in range(0,count,4096):
                        seeds=[seed_from_index(i,key) for i in range(first,min(count,first+4096))]
                        with prototypes[chunk].sweep(seeds,32,retention='survivors',max_misses=1) as batch:
                            elapsed+=batch.native_seconds;receipts.append(batch.retention_receipt())
                    row={'wall_seconds':elapsed,'input_seeds_per_second':count/elapsed,
                         'fingerprint':hashlib.sha256(canonical(receipts).encode()).hexdigest(),
                         'retained_inputs':sum(r['retained_inputs'] for r in receipts)}
                    receipt.write_text(json.dumps(row,indent=2)+'\n')
                else:
                    command=[sys.executable,str(ROOT/'scripts/native_throughput_arm.py'),
                             '--entrypoint','--arm','native' if phase=='full_cli' else 'native-near',
                             '--river','--native',str(prototypes[chunk].directory),
                             '--run',str((args.output/tag).resolve()),'--receipt',str(receipt.resolve()),
                             '--count',str(count),'--key',str(key),'--threads','16' if phase=='full_cli' else '32']
                    if phase=='compact_cli':command+=['--max-misses','1']
                    child=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
                    (args.output/f'{tag}.log').write_text(child.stdout+child.stderr)
                    child.check_returncode();row=json.loads(receipt.read_text())
                if phase in fingerprints:assert row['fingerprint']==fingerprints[phase],(phase,chunk,'parity')
                else:fingerprints[phase]=row['fingerprint']
                rows.append({**row,'phase':phase,'chunk':chunk,'trial':trial,'count':count,'key':key})
                (args.output/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
                print(json.dumps({k:rows[-1][k] for k in ('phase','chunk','trial','input_seeds_per_second')}),flush=True)
    summary={phase:{str(chunk):{'median':statistics.median(r['input_seeds_per_second'] for r in rows if r['phase']==phase and r['chunk']==chunk),
                             'min':min(r['input_seeds_per_second'] for r in rows if r['phase']==phase and r['chunk']==chunk),
                             'max':max(r['input_seeds_per_second'] for r in rows if r['phase']==phase and r['chunk']==chunk)}
                    for chunk in prototypes} for phase in fingerprints}
    result={'policy':'locked-2048-1024-river-v2','summary':summary,'observations':rows,
            'distinct_inputs':args.count,'full_cohort_contained':True,'key':key,
            'disk_preflight':{'projected_bytes':projected,'free_bytes':free,'reserve_bytes':16<<30},
            'fixture_inputs_per_chunk':192,'semantic_differences':0,
            'scope':'Native C and FULL durable baseline screening; terrain and BDS excluded'}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
