"""Complete bounded adoption after a reviewed shared-Nether refinement.

Includes earlier tuning time in the 20-minute cap, re-trains incompatible PGO
profiles, measures chunk interactions, and validates five durable held-out pairs.
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
from scripts.benchmark_dynamic_baseline import kernel_measure
from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.capabilities import report
from seed_search.realm.native_batch import Prototype,run_native_scan
from seed_search.realm.store import RealmStore,canonical
from seed_search.seeds import seed_from_index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--openmp-prefix',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Fresh output required')
    previous=json.loads(args.prior.read_text())
    offset=previous.get('cumulative_benchmark_seconds',previous.get('elapsed_seconds'))
    if 'policy' not in previous:
        original=json.loads(Path(previous['prior']).read_text());original['elapsed_seconds']=offset;previous=original
    prior_seconds=previous['elapsed_seconds']
    cfg=dynamic_blueprint_config()
    if previous['policy']!=cfg:raise ValueError('Prior tuning policy differs')
    args.output.mkdir(parents=True);started=time.perf_counter();rows=[];builds={};failures=[];durable=[]
    result={'status':'running','prior':str(args.prior.resolve()),'prior_seconds':prior_seconds,
            'budget_seconds':1200,'rows':rows,'builds':builds,'failures':failures,'durable_pairs':durable}
    def save():
        result['cumulative_benchmark_seconds']=prior_seconds+time.perf_counter()-started
        (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    def budget():
        if prior_seconds+time.perf_counter()-started>=1200:
            result['status']='budget_exhausted';save();raise RuntimeError('Total benchmark budget exhausted')
    def compile_arm(name,**kwargs):
        budget();path=args.output/name
        identity=build(path,args.openmp_prefix,**kwargs)
        builds[name]={k:identity[k] for k in ('source_digest','extension_sha256','flags','links','work_chunk','cpu_native','lto','pgo_profile_sha256','dynamic_preflight')}
        builds[name]['path']=str(path.resolve());save();return Prototype(path,cfg)
    control=Prototype(previous['builds']['control']['path'],cfg)
    portable=compile_arm('shared-portable');arms={'shared-portable':portable}
    seeds=[seed_from_index(i,2026101401) for i in range(50000)]
    expected=tuple(previous['rows'][0]['fingerprint'])
    def measure(name,prototype,threads,size,cohort=seeds):
        budget();row=kernel_measure(name,prototype,threads,size,cohort)
        if cohort is seeds and row['fingerprint']!=expected:raise RuntimeError('Tuning decision or candidate mismatch')
        rows.append(row);save();print(json.dumps(row),flush=True);return row
    for _ in range(2):measure('shared-portable',portable,34,16384)
    tool=shutil.which('llvm-profdata') or subprocess.check_output(['xcrun','--find','llvm-profdata'],text=True).strip()
    for chunk in (16,64,128):
        name=f'shared-pgo{chunk}'
        try:
            training=compile_arm(name+'-training',cpu_native=True,lto=True,work_chunk=chunk,pgo_generate=True)
            env=os.environ.copy();env['LLVM_PROFILE_FILE']=str((args.output/f'train-{chunk}-%p.profraw').resolve())
            code="""from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import seed_from_index
import sys
p=Prototype(sys.argv[1],dynamic_blueprint_config())
with p.sweep([seed_from_index(i,2026101402) for i in range(10000)],4,retention='survivors'):pass
with p.sweep([1],fixtures=[(0,0,-1)],retention='survivors'):pass
"""
            budget();timeout=min(120,max(1,int(1200-prior_seconds-(time.perf_counter()-started))))
            subprocess.run([sys.executable,'-c',code,str(training.directory)],env=env,check=True,timeout=timeout)
            profile=args.output/f'chunk{chunk}.profdata'
            subprocess.run([tool,'merge','-output',str(profile),*[str(p) for p in args.output.glob(f'train-{chunk}-*.profraw')]],check=True,timeout=30)
            meta=json.loads((training.directory/'identity.json').read_text());meta['profile_sha256']=hashlib.sha256(profile.read_bytes()).hexdigest()
            profile.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
            arms[name]=compile_arm(name,cpu_native=True,lto=True,work_chunk=chunk,pgo_use=profile)
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            failures.append({'arm':name,'error':str(exc)});save()
    for trial in range(3):
        for name in (list(arms) if trial%2==0 else list(reversed(arms))):measure(name,arms[name],34,16384)
    best=max(arms,key=lambda name:statistics.median(r['kernel_inputs_per_second'] for r in rows if r['arm']==name))
    selected=arms[best]
    grid=[(threads,size) for threads in (16,24,30,32,34) for size in (4096,8192,16384)]
    for trial in range(2):
        for threads,size in (grid if trial%2==0 else list(reversed(grid))):measure(best,selected,threads,size)
    settings=max(grid,key=lambda pair:statistics.median(r['kernel_inputs_per_second'] for r in rows if r['arm']==best and (r['threads'],r['batch_size'])==pair))
    result['selected']={'arm':best,'threads':settings[0],'batch_size':settings[1],'path':str(selected.directory)};save()
    for trial in range(5):
        cohort=[seed_from_index(i,2027101403) for i in range(trial*100000,(trial+1)*100000)]
        decision=None;candidate_digest=None
        for name in (('control','selected') if trial%2==0 else ('selected','control')):
            prototype=control if name=='control' else selected
            threads,size=(16,4096) if name=='control' else settings
            fp=measure('heldout-'+name,prototype,threads,size,cohort)['fingerprint']
            if decision is None:decision=fp
            elif fp!=decision:raise RuntimeError('Held-out decision mismatch')
            budget();policy=dynamic_blueprint_config();policy['search']['run_key']='2027101403'
            run=args.output/f'pair-{trial}-{name}';before=time.perf_counter()
            run.mkdir();(run/'compatibility.json').write_text(json.dumps(report(policy),indent=2)+'\n')
            status=run_native_scan(policy,run,100000,start_index=trial*100000,native_build=prototype.directory,
                native_threads=threads,native_batch_size=size,retention='survivors',allow_prediction_scale=True)
            elapsed=time.perf_counter()-before
            with RealmStore(run,resume=True) as store:
                digest=hashlib.sha256()
                for candidate in store.iter_candidates():digest.update(canonical(candidate).encode())
                persisted=digest.hexdigest()
                assert store.status()['completed_seeds']==100000
            if candidate_digest is None:candidate_digest=persisted
            elif candidate_digest!=persisted:raise RuntimeError('Durable candidate mismatch')
            row={'trial':trial,'arm':name,'threads':threads,'batch_size':size,'wall_seconds':elapsed,
                 'durable_inputs_per_second':100000/elapsed,'candidate_fingerprint':persisted,'execution':status['execution']}
            durable.append(row);save();print(json.dumps(row),flush=True)
    result['median_durable_inputs_per_second']={arm:statistics.median(r['durable_inputs_per_second'] for r in durable if r['arm']==arm) for arm in ('control','selected')}
    result['status']='complete';save()


if __name__=='__main__':main()
