"""Bounded dynamic-policy compiler/tuning trials and five held-out durable pairs.

Run on an otherwise idle host. Each tuning call contains <=50,000 inputs;
validation uses five counterbalanced 100,000-input pairs. Results are empirical,
not a proof of optimality across arbitrary future algorithms or hardware.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.native_batch import Prototype, run_native_scan, semantic_record
from seed_search.realm.store import RealmStore, canonical
from seed_search.seeds import seed_from_index


def kernel_measure(name,prototype,threads,size,cohort):
    native_seconds=0.;wall=time.perf_counter();digest=hashlib.sha256();candidates=hashlib.sha256();retained=0
    for offset in range(0,len(cohort),size):
        with prototype.sweep(cohort[offset:offset+size],threads,retention='survivors') as batch:
            native_seconds+=batch.native_seconds
            digest.update(prototype.ffi.buffer(batch.pointer.verdicts,batch.pointer.count*prototype.ffi.sizeof('NBVerdict')))
            for record in batch.retained_records(offset):
                candidates.update(canonical(semantic_record(record)).encode());retained+=len(record['anchors'])
    return {'phase':'kernel','arm':name,'threads':threads,'batch_size':size,'inputs':len(cohort),
            'native_seconds':native_seconds,'wall_seconds':time.perf_counter()-wall,
            'kernel_inputs_per_second':len(cohort)/native_seconds,
            'fingerprint':(digest.hexdigest(),candidates.hexdigest(),retained)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--openmp-prefix',type=Path,required=True)
    parser.add_argument('--max-seconds',type=int,default=1200)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a fresh output directory')
    if not 1<=args.max_seconds<=1200:parser.error('Budget must be 1..1200 seconds')
    args.output.mkdir(parents=True)
    started=time.perf_counter();cfg=dynamic_blueprint_config();rows=[];failures=[];builds={}
    result={'policy':cfg,'rows':rows,'build_failures':failures,'builds':builds,
            'budget_seconds':args.max_seconds,'status':'running'}
    def save():
        result['elapsed_seconds']=time.perf_counter()-started
        (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    def budget():
        if time.perf_counter()-started>=args.max_seconds:
            result['status']='budget_exhausted';save();raise RuntimeError('Benchmark budget exhausted; no new settings adopted')
    def compile_arm(name,**options):
        budget();path=args.output/name
        try:
            identity=build(path,args.openmp_prefix,**options)
        except Exception as exc:
            failures.append({'arm':name,'error':str(exc)});save();return None
        builds[name]={k:identity[k] for k in ('source_digest','extension_sha256','flags','links','work_chunk','cpu_native','lto','pgo_profile_sha256','dynamic_preflight')}
        builds[name]['path']=str(path.resolve());save()
        return Prototype(path,cfg)
    control=compile_arm('control',dynamic_preflight=False)
    base=compile_arm('portable')
    if control is None or base is None:raise RuntimeError('Required comparison builds failed')
    arms={'control':control,'portable':base}
    for name,options in [('native',{'cpu_native':True}),('lto',{'lto':True}),
                         ('native-lto',{'cpu_native':True,'lto':True}),
                         ('chunk64',{'work_chunk':64}),('chunk128',{'work_chunk':128})]:
        arm=compile_arm(name,**options)
        if arm is not None:arms[name]=arm
    seeds=[seed_from_index(i,2026101401) for i in range(50000)]
    expected=None
    def kernel(name,prototype,threads,size,cohort=seeds):
        nonlocal expected
        budget();row=kernel_measure(name,prototype,threads,size,cohort)
        fp=row['fingerprint']
        if cohort is seeds:
            if expected is None:expected=fp
            elif fp!=expected:raise RuntimeError(f'Kernel decision/record mismatch: {name}')
        rows.append(row);save();print(json.dumps(row),flush=True);return row
    for trial in range(2):
        for name in (list(arms) if trial%2==0 else list(reversed(arms))):kernel(name,arms[name],34,16384)
    # Train PGO on disjoint inputs plus explicit late-stage fixtures. The final
    # held-out cohort is never used to train a compiler profile or select flags.
    training=compile_arm('pgo-training',cpu_native=True,lto=True,pgo_generate=True)
    if training is not None:
        env=os.environ.copy();env['LLVM_PROFILE_FILE']=str((args.output/'pgo-%p.profraw').resolve())
        code="""from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import seed_from_index
import sys
p=Prototype(sys.argv[1],dynamic_blueprint_config())
for offset in range(0,50000,16384):
 with p.sweep([seed_from_index(i,2026101402) for i in range(offset,min(50000,offset+16384))],34,retention='survivors'):pass
with p.sweep([1],fixtures=[(0,0,-1)],retention='survivors'):pass
"""
        budget()
        try:
            subprocess.run([sys.executable,'-c',code,str((args.output/'pgo-training').resolve())],env=env,check=True,timeout=max(1,int(args.max_seconds-(time.perf_counter()-started))))
            tool=shutil.which('llvm-profdata')
            if tool is None:tool=subprocess.check_output(['xcrun','--find','llvm-profdata'],text=True).strip()
            profile=args.output/'trained.profdata'
            subprocess.run([tool,'merge','-output',str(profile),*[str(p) for p in args.output.glob('pgo-*.profraw')]],check=True,timeout=30)
            meta=json.loads((args.output/'pgo-training/identity.json').read_text())
            meta['profile_sha256']=hashlib.sha256(profile.read_bytes()).hexdigest()
            profile.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
            pgo=compile_arm('pgo',cpu_native=True,lto=True,pgo_use=profile)
            if pgo is not None:
                arms['pgo']=pgo
                for _ in range(2):kernel('pgo',pgo,34,16384)
        except (OSError,subprocess.SubprocessError,ValueError) as exc:
            failures.append({'arm':'pgo','error':str(exc)});save()
    scores={name:statistics.median(r['kernel_inputs_per_second'] for r in rows if r['arm']==name) for name in arms}
    best=max((name for name in arms if name!='control'),key=scores.get)
    selected=arms[best]
    grid=[(threads,size) for threads in (16,24,30,32,34) for size in (4096,8192,16384)]
    for trial in range(2):
        for threads,size in (grid if trial%2==0 else list(reversed(grid))):kernel(best,selected,threads,size)
    settings=max(grid,key=lambda pair:statistics.median(r['kernel_inputs_per_second'] for r in rows if r['arm']==best and (r['threads'],r['batch_size'])==pair))
    result['proposed']={'arm':best,'threads':settings[0],'batch_size':settings[1]};save()
    durable=[];result['durable_pairs']=durable
    for trial in range(5):
        cohort=[seed_from_index(i,2027101403) for i in range(trial*100000,(trial+1)*100000)]
        receipt=None;persisted=None
        for name in (('control','selected') if trial%2==0 else ('selected','control')):
            prototype=control if name=='control' else selected
            threads,size=(16,4096) if name=='control' else settings
            decision=kernel('heldout-'+name,prototype,threads,size,cohort)['fingerprint']
            if receipt is None:receipt=decision
            elif receipt!=decision:raise RuntimeError('Held-out decision/record mismatch')
            budget();run=args.output/f'pair-{trial}-{name}'
            policy=dynamic_blueprint_config();policy['search']['run_key']='2027101403'
            from seed_search.realm.capabilities import report
            run.mkdir()
            (run/'compatibility.json').write_text(json.dumps(report(policy),indent=2)+'\n')
            before=time.perf_counter()
            status=run_native_scan(policy,run,100000,start_index=trial*100000,
                native_build=prototype.directory,native_threads=threads,native_batch_size=size,
                retention='survivors',allow_prediction_scale=True)
            elapsed=time.perf_counter()-before
            with RealmStore(run,resume=True) as store:
                digest=hashlib.sha256()
                for record in store.iter_candidates():digest.update(canonical(record).encode())
                fp=digest.hexdigest()
                assert store.status()['completed_seeds']==100000
            if persisted is None:persisted=fp
            elif fp!=persisted:raise RuntimeError('Held-out durable candidate mismatch')
            row={'trial':trial,'arm':name,'threads':threads,'batch_size':size,
                 'inputs':100000,'wall_seconds':elapsed,'durable_inputs_per_second':100000/elapsed,
                 'candidate_fingerprint':fp,'execution':status['execution']}
            durable.append(row);save();print(json.dumps(row),flush=True)
    result['median_durable_inputs_per_second']={name:statistics.median(r['durable_inputs_per_second'] for r in durable if r['arm']==name) for name in ('control','selected')}
    result['status']='complete';save()


if __name__=='__main__':main()
