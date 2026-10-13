"""Retained losing spawned-preparation experiment; production uses threads."""
import json
import time
from scripts.blueprint_batch_prototype import Prototype
from seed_search.realm.store import RealmStore

_PROCESS_STATE=None


def _process_prepared(directory,cfg,policy,first,end,hint,threads,encoded,max_bytes):
    """Spawn-safe experimental preparer; no SQLite connection or C pointer IPC."""
    global _PROCESS_STATE
    from concurrent.futures import ThreadPoolExecutor
    from seed_search.realm.runner import _seed,_validate_batch_seeds
    from seed_search.realm.native_encoding import fast_records
    if _PROCESS_STATE is None:
        p=Prototype(directory,cfg)
        assembler=RealmStore.__new__(RealmStore)
        assembler.retention={"mode":"full","max_misses":0}
        assembler._preparation_policy=policy
        assembler._digest_version,assembler._inventory_backend_digest,assembler.active_variants=policy
        _PROCESS_STATE=(p,assembler,ThreadPoolExecutor(max_workers=1),{})
    p,assembler,pool,ready=_PROCESS_STATE
    if p.cfg!=cfg or assembler._preparation_policy!=policy:raise ValueError('Spawn preparer policy changed')
    def compute(bounds):
        start=time.perf_counter();seeds=[_seed(i,cfg['search']) for i in range(*bounds)]
        seed_seconds=time.perf_counter()-start
        return p.sweep(seeds,threads),seed_seconds
    current=(first,end)
    if current not in ready:ready[current]=pool.submit(compute,current)
    if hint is not None and tuple(hint) not in ready:ready[tuple(hint)]=pool.submit(compute,tuple(hint))
    future=ready.pop(current);batch,seed_seconds=future.result()
    with batch:
        before=time.perf_counter();records=fast_records(batch,first,assembler) if encoded else batch.records(first)
        record_seconds=time.perf_counter()-before
        _validate_batch_seeds(first,end,records,cfg['search'])
        before=time.perf_counter();prepared=assembler.prepare_range(first,end,records)
        prepare_seconds=time.perf_counter()-before
        owned=prepared.payload_bytes*2+sum(len(r)*64 for r in prepared.seed_rows+prepared.candidate_rows)
        if owned>max_bytes:raise RuntimeError('Prepared batch exceeds owned byte budget')
        return prepared,{'seed_preparation_seconds':seed_seconds,'native_seconds':batch.native_seconds,
                         'record_seconds':record_seconds,'preparation_wall_seconds':prepare_seconds},owned


def persist_process_pipeline(prototype,run,count,*,run_key=0,threads=18,batch_size=4096,prepare_workers=1):
    """Bounded tuning experiment for preparation IPC, not production dispatch."""
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    from collections import deque,Counter
    from seed_search.realm.runner import _scan_lock,_numerical_threads
    from seed_search.realm.resources import disk_policy,disk_status
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=100000:raise ValueError('Bounded count required')
    if not 1<=batch_size<=16384 or not 1<=threads<=34:raise ValueError('Invalid batch/CPU budget')
    if type(prepare_workers) is not int or not 1<=prepare_workers<=4 or prepare_workers*(threads+1)+1>36:
        raise ValueError('Invalid spawned preparation CPU budget')
    cfg=json.loads(json.dumps(prototype.cfg));cfg['search']['run_key']=str(run_key)
    identity={'config':cfg,'prototype':prototype.identity,'count':count,'adapter':'spawned-preparer-experiment-v1'}
    wall=time.perf_counter();service=Counter();latencies=[];pending=deque();claimed=[];max_payload=0
    with _scan_lock(run),_numerical_threads(),RealmStore(run,identity) as store:
        store.configure_range(0,count,batch_size);disk_status(store.run,disk_policy(cfg['search']),remaining_seeds=count)
        with ProcessPoolExecutor(max_workers=prepare_workers,mp_context=get_context('spawn')) as pool:
            for _ in range(3):
                lease=store.claim_range('spawn-native')
                if lease:claimed.append(lease)
            def dispatch(bounds,hint):
                return pool.submit(_process_prepared,str(prototype.directory),cfg,store._preparation_policy,
                                   *bounds,hint if prepare_workers==1 else None,threads,True,256<<20)
            for i,bounds in enumerate(claimed):
                pending.append((*bounds,dispatch(bounds,claimed[i+1] if i+1<len(claimed) else None),time.perf_counter()))
            while pending:
                first,end,future,submitted=pending.popleft()
                before=time.perf_counter();prepared,times,owned=future.result()
                service['queue_wait_seconds']+=time.perf_counter()-before;service.update(times);max_payload=max(max_payload,owned)
                before=time.perf_counter();store.complete_prepared(prepared,lease=('spawn-native',1),
                    capacity_check=lambda n:disk_status(store.run,disk_policy(cfg['search']),additional_bytes=n))
                service['writer_wall_seconds']+=time.perf_counter()-before;service.update(store.last_range_timings)
                latencies.append(time.perf_counter()-submitted)
                assigned=store.claim_range('spawn-native')
                if assigned:pending.append((*assigned,dispatch(assigned,None),time.perf_counter()))
        status=store.status()
    seconds=time.perf_counter()-wall
    return {'wall_seconds':seconds,'input_seeds_per_second':count/seconds,'count':count,'threads':threads,
            'batch_size':batch_size,'status':status,**dict(service),'batch_latencies_seconds':latencies,
            'max_prepared_owned_estimate_bytes':max_payload}
