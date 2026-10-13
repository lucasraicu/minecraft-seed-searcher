"""Bounded native stage/biome profiling; active and forced diagnostics stay separate."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

for name in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from seed_search.backend import biome_catalog
from seed_search.realm.native_batch import Prototype,Batch,NAMES,semantic_record
from seed_search.realm.config import blueprint_config,locked_blueprint_config,outpost_blueprint_config
from seed_search.realm.store import canonical
from seed_search.seeds import seed_from_index,MASK64

STAGES=('stronghold',*[f'structure_{n}' for n in NAMES[:10]],'nether_pair',
        'biome_palette_4y','ranking_inventory',*[f'ranking_inventory_{n}' for n in NAMES],
        'isolated_inventory_fortress','isolated_inventory_bastion','structure_outpost')


def merge(target, value, seed=None):
    """Merge raw count/sum/min/max/histograms; no dropped-stage zero timings."""
    count=int(value.count) if hasattr(value,'count') and not isinstance(value,dict) else value['count']
    if not count:return
    get=(lambda k:getattr(value,k)) if not isinstance(value,dict) else value.__getitem__
    if not target:
        target.update(count=0,total_seconds=0.,min_seconds=float(get('min_seconds')),max_seconds=-1.,
                      bins=[0]*32,max_seed=None,max_coordinate=None)
    target['count']+=count;target['total_seconds']+=float(get('total_seconds'))
    target['min_seconds']=min(target['min_seconds'],float(get('min_seconds')))
    if float(get('max_seconds'))>target['max_seconds']:
        target['max_seconds']=float(get('max_seconds'))
        target['max_seed']=str(seed) if seed is not None else get('max_seed')
        target['max_coordinate']=[int(get(k)) for k in ('max_x','max_y','max_z')] if not isinstance(value,dict) else get('max_coordinate')
    target['bins']=[a+int(b) for a,b in zip(target['bins'],get('bins'))]


def summarize(value):
    if not value:return {'count':0,'status':'not reached'}
    assert sum(value['bins'])==value['count']
    percentile=math.ceil(value['count']*.99);cumulative=0
    for i,n in enumerate(value['bins']):
        cumulative+=n
        if cumulative>=percentile:break
    lower=0 if i==0 else 2**i*1e-9
    upper=2**(i+1)*1e-9 if i<31 else None
    mean=value['total_seconds']/value['count']
    return {**value,'mean_seconds':mean,'p99_seconds_bounds':[lower,upper],
            'p99_scope':'entered calls; bounded power-of-two nanosecond histogram',
            'tail_flag':'investigate' if value['count']>=100 and lower>=4*mean else 'limited sample' if value['count']<100 else 'no large p99 tail by diagnostic threshold'}


def measured(prototype,seeds,threads,*,complete=False,profile=False):
    """Measure C call only; evidence extraction/aggregation happens afterward."""
    aggregate={section:{} for section in ('stages','biome_y','biome_ids','biome_families')}
    logical=0;unique=0;mansion_queries=mansion_cache_hits=0
    if profile:
        ffi,lib=prototype.ffi,prototype.lib
        policy=ffi.new('NBPolicy *');ffi.memmove(policy,prototype.policy,ffi.sizeof('NBPolicy'))
        policy.complete=int(complete);policy.retention=int(not complete);policy.max_misses=0 if complete else (1 if prototype.cfg.get('screening_revision') else 2)
        values=ffi.new('uint64_t[]',[s&MASK64 for s in seeds])
        started=time.perf_counter();handle=lib.nb_profile_sweep(values,len(seeds),policy,threads)
        seconds=time.perf_counter()-started
        if handle==ffi.NULL:raise RuntimeError('Profile capacity/policy failure')
        batch=Batch(prototype,handle.batch,seeds,seconds,complete,False,'full' if complete else 'survivors',0 if complete else (1 if prototype.cfg.get('screening_revision') else 2))
    else:
        batch=prototype.sweep(seeds,threads,complete=complete,retention='full' if complete else 'survivors',max_misses=0 if complete else (1 if prototype.cfg.get('screening_revision') else 2))
        seconds=batch.native_seconds
    try:
        pointer=batch.pointer
        if pointer.error or any(pointer.results[i].error for i in range(pointer.result_count)):
            raise RuntimeError('Native profile failed; no measurements accepted')
        if profile:
            ids={r['id']:r['name'] for r in biome_catalog()}
            sections=[('stages',STAGES),('biome_y',[str(y) for y in prototype.cfg['biomes']['sample_y_levels']]),
                      ('biome_ids',[ids.get(i,str(i)) for i in range(256)]),
                      ('biome_families',prototype.families)]
            for i,seed in enumerate(seeds):
                sample=handle.samples[i]
                if int(sample.seed)!=(seed&MASK64):raise RuntimeError('Profile seed identity differs')
                mansion_queries+=int(getattr(sample,'mansion_queries',0));mansion_cache_hits+=int(getattr(sample,'mansion_cache_hits',0))
                for section,names in sections:
                    values=getattr(sample,section)
                    for k,name in enumerate(names):
                        if values[k].count:merge(aggregate[section].setdefault(name,{}),values[k],seed)
        if complete:
            records=batch.records()
            for i in range(pointer.result_count):
                points=set();r=pointer.results[i]
                for j in range(r.nanchors):
                    a=r.anchors[j]
                    for k in range(a.biome_n):
                        logical+=1;points.add(tuple(int(a.biome_xyz[3*k+t]) for t in range(3)))
                unique+=len(points)
            digest=hashlib.sha256(canonical([semantic_record(r) for r in records]).encode()).hexdigest()
        else:
            digest=hashlib.sha256(canonical({'receipt':batch.retention_receipt(),'records':[semantic_record(r) for r in batch.retained_records()]}).encode()).hexdigest()
        return {'native_seconds':seconds,'fingerprint':digest,'inputs':len(seeds),
                'logical_palette_samples':logical,'unique_palette_coordinates_within_seed':unique,
                'mansion_queries':mansion_queries,'mansion_cache_hits':mansion_cache_hits,
                'raw_timings':aggregate,'retained_inputs':int(pointer.result_count)}
    finally:
        if profile:
            batch.pointer=None;prototype.lib.nb_profile_free(handle)
        else:batch.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',required=True,type=Path)
    parser.add_argument('--profile-native',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--locked',action='store_true')
    parser.add_argument('--outpost',action='store_true')
    parser.add_argument('--count',type=int,default=10000)
    parser.add_argument('--diagnostic-count',type=int,default=128)
    parser.add_argument('--threads',type=int,default=32)
    parser.add_argument('--diagnostic-threads',type=int,default=8)
    parser.add_argument('--trials',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.count<=100000 or not 1<=args.diagnostic_count<=512 or not 1<=args.trials<=5:
        parser.error('Bounded count 1–100,000, diagnostic count 1–512, trials 1–5 required')
    if args.output.exists():parser.error('Use a fresh output directory to retain earlier evidence')
    args.output.mkdir(parents=True)
    cfg=outpost_blueprint_config() if args.outpost else locked_blueprint_config() if args.locked else blueprint_config();normal=Prototype(args.native,cfg);profile=Prototype(args.profile_native,cfg)
    if not profile.identity.get('profiling'):raise ValueError('Instrumented --profile build required')
    if not 1<=args.threads<=36 or not 1<=args.diagnostic_threads<=36:raise ValueError('Invalid thread budget')
    active_phase='active_one_miss' if args.locked or args.outpost else 'active_two_miss'
    arms={'normal':normal,'profile':profile};trials=[];overall={phase:{s:{} for s in ('stages','biome_y','biome_ids','biome_families')} for phase in (active_phase,'forced_complete_diagnostic')}
    for phase,count,key in [(active_phase,args.count,120264001000),('forced_complete_diagnostic',args.diagnostic_count,120265001000)]:
        complete=phase.startswith('forced')
        threads=args.diagnostic_threads if complete else args.threads
        batch_size=128 if complete else 512
        for trial in range(args.trials):
            fingerprints={}
            for arm in (('normal','profile') if trial%2==0 else ('profile','normal')):
                native_seconds=0.;hashes=[];logical=unique=retained=0;mansion_queries=mansion_cache_hits=0
                raw={s:{} for s in overall[phase]}
                for start in range(0,count,batch_size):
                    seeds=[seed_from_index(i,key) for i in range(start,min(start+batch_size,count))]
                    row=measured(arms[arm],seeds,threads,complete=complete,profile=arm=='profile')
                    native_seconds+=row['native_seconds'];hashes.append(row['fingerprint'])
                    logical+=row['logical_palette_samples'];unique+=row['unique_palette_coordinates_within_seed'];retained+=row['retained_inputs']
                    mansion_queries+=row['mansion_queries'];mansion_cache_hits+=row['mansion_cache_hits']
                    for section,values in row['raw_timings'].items():
                        for name,value in values.items():merge(raw[section].setdefault(name,{}),value)
                fingerprint=hashlib.sha256(canonical(hashes).encode()).hexdigest();fingerprints[arm]=fingerprint
                observation={'phase':phase,'arm':arm,'trial':trial,'count':count,'key':key,'threads':threads,'native_seconds':native_seconds,
                             'native_inputs_per_second':count/native_seconds,'fingerprint':fingerprint,
                             'logical_palette_samples':logical,'unique_palette_coordinates_within_seed':unique,'retained_inputs':retained,
                             'mansion_queries':mansion_queries,'mansion_cache_hits':mansion_cache_hits,
                             'timings':{section:{name:summarize(value) for name,value in values.items()} for section,values in raw.items()}}
                trials.append(observation)
                (args.output/f'{phase}-{arm}-{trial}.json').write_text(json.dumps(observation,indent=2)+'\n')
                if arm=='profile':
                    for section,values in raw.items():
                        for name,value in values.items():merge(overall[phase][section].setdefault(name,{}),value)
                print(json.dumps({k:observation[k] for k in ('phase','arm','trial','native_seconds','native_inputs_per_second')}),flush=True)
            if len(set(fingerprints.values()))!=1:raise RuntimeError('Instrumented/control full-record parity differs')
    result={'scope':'C-only diagnostics, not persisted throughput; entered stages only; forced late-stage probes are not survivor evidence',
            'distinct_inputs':args.count+args.diagnostic_count,'repetitions_are_not_distinct':True,'threads':args.threads,'diagnostic_threads':args.diagnostic_threads,
            'profile_buffer_cap_bytes':64<<20,'outlier_threshold':'p99 lower bound >= 4x entered-call mean and >=100 calls; heuristic, not defect proof',
            'normal_identity':normal.identity,'profile_identity':profile.identity,'trials':trials,
            'summary':{phase:{section:{name:summarize(v) for name,v in values.items()} for section,values in data.items()} for phase,data in overall.items()},
            'active_profile_overhead_ratio':statistics.median(r['native_seconds'] for r in trials if r['phase']==active_phase and r['arm']=='profile')/statistics.median(r['native_seconds'] for r in trials if r['phase']==active_phase and r['arm']=='normal'),
            'parity_differences':0}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
