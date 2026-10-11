"""Resumable bounded lower32 ranking experiment for the fixed Realm contract."""
import fcntl
import hashlib
import heapq
import json
from pathlib import Path
import sqlite3
import time
import numpy as np

from ..backend import sweep_raw,configure_native_threads,raw_layout
from .capabilities import identity as backend_identity
from .store import canonical, RealmStore
from .resources import disk_policy,disk_status

# Derive the raw envelopes from the same fixed contract as the baseline.
# Bounds passed to native placement queries have inclusive integer maxima.
from .config import DEFAULT
from .bounds import square, nether_square, native_bounds

CENTER_BOUNDS = native_bounds(DEFAULT['discovery']['overworld_bounds'])
OW_SIDE = DEFAULT['deployment']['overworld_side_blocks']
NETHER_SIDE = DEFAULT['deployment']['nether_side_blocks']
_ow_lo = square(CENTER_BOUNDS[:2], OW_SIDE)
_ow_hi = square(CENTER_BOUNDS[2:], OW_SIDE)
_nether_lo = nether_square(CENTER_BOUNDS[:2], NETHER_SIDE)
_nether_hi = nether_square(CENTER_BOUNDS[2:], NETHER_SIDE)
OW_ENVELOPE = native_bounds((*_ow_lo[:2], *_ow_hi[2:]))
NETHER_ENVELOPE = native_bounds((*_nether_lo[:2], *_nether_hi[2:]))
FAMILIES = (('village', OW_ENVELOPE), ('ancient_city', OW_ENVELOPE),
            ('fortress', NETHER_ENVELOPE), ('bastion', NETHER_ENVELOPE),
            ('fortress', native_bounds(DEFAULT['discovery']['nether_bounds'])))


def center_rectangle(point,nether=False):
    """Inclusive integer center domain producing exact half-open membership."""
    scale,half=(8,4*NETHER_SIDE) if nether else (1,OW_SIDE//2)
    x,z=point
    bounds=(max(CENTER_BOUNDS[0],scale*x-half+1),max(CENTER_BOUNDS[1],scale*z-half+1),
            min(CENTER_BOUNDS[2],scale*x+half),min(CENTER_BOUNDS[3],scale*z+half))
    return bounds if bounds[0]<=bounds[2] and bounds[1]<=bounds[3] else None


def joint_center_witness(layouts):
    """Exact necessary raw-placement intersection for four required families.

    A witness is an allowed center, not a discovered Stronghold or viable world.
    Sweep integer X event boundaries; intersect merged inclusive Z intervals.
    """
    if len(layouts)!=4:raise ValueError('Joint layout needs Village/City/Fortress/Bastion')
    rectangles=[[r for p in points if (r:=center_rectangle(p,j>=2)) is not None] for j,points in enumerate(layouts)]
    if any(not group for group in rectangles):return None
    events=sorted({r[0] for group in rectangles for r in group}|{r[2]+1 for group in rectangles for r in group})
    def merged(intervals):
        out=[]
        for lo,hi in sorted(intervals):
            if out and lo<=out[-1][1]+1:out[-1]=(out[-1][0],max(hi,out[-1][1]))
            else:out.append((lo,hi))
        return out
    def intersect(a,b):
        i=j=0;out=[]
        while i<len(a) and j<len(b):
            lo=max(a[i][0],b[j][0]);hi=min(a[i][1],b[j][1])
            if lo<=hi:out.append((lo,hi))
            if a[i][1]<b[j][1]:i+=1
            else:j+=1
        return out
    for x in events:
        if x>CENTER_BOUNDS[2]:break
        common=[(CENTER_BOUNDS[1],CENTER_BOUNDS[3])]
        for group in rectangles:
            common=intersect(common,merged((r[1],r[3]) for r in group if r[0]<=x<=r[2]))
            if not common:break
        if common:return [x,common[0][0]]
    return None


def _score(counts):
    # Versioned ranking hint only; no permanent world rejection.
    return sum(min(int(v),32) for v in counts)


def _hash(seed,key):
    return int.from_bytes(hashlib.sha256(f'{key}:{seed}'.encode()).digest()[:8],'big')


def exploration_keys(lows,key):
    """Versioned bijective 64-bit mixing; bounded deterministic exploration."""
    values=np.asarray(lows,dtype=np.uint64)^np.uint64(_hash(0,key))
    # Vector uint64 arithmetic deliberately wraps. This changes exploration
    # policy, not raw counts or the exact legacy capped density score.
    values=values+np.uint64(0x9e3779b97f4a7c15)
    values=(values^(values>>np.uint64(30)))*np.uint64(0xbf58476d1ce4e5b9)
    values=(values^(values>>np.uint64(27)))*np.uint64(0x94d049bb133111eb)
    return values^(values>>np.uint64(31))


def run_raw(output,start,count,*,threads=1,chunk_size=256,top=64,exploration=16,key='0',resume=False,stop_after=None,mode='capped'):
    if mode not in ('reference','complete','presence','capped'):raise ValueError('Invalid raw mode')
    if (isinstance(start,bool) or not isinstance(start,int) or isinstance(count,bool) or not isinstance(count,int)
        or not 0<=start<=start+count<=2**32):raise ValueError('Raw range must fit [0,2**32)')
    for value,lo,hi in ((chunk_size,1,65536),(top,1,10000),(exploration,1,10000),(threads,1,36)):
        if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:raise ValueError('Invalid raw batching/retention/thread budget')
    if stop_after is not None and (isinstance(stop_after,bool) or not isinstance(stop_after,int) or stop_after<0):raise ValueError('Invalid raw stop budget')
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    ident={'version':'raw-count-rank-v4-batched','mode':mode,'exploration_policy':'splitmix64-permutation-v1','geometry':{'deployment':DEFAULT['deployment'],'discovery':DEFAULT['discovery']},'start':start,'count':count,'families':FAMILIES,
           'top':top,'exploration':exploration,'key':str(key),'backend':backend_identity()}
    ident=json.loads(canonical(ident))
    with (root/'raw.lock').open('a+') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another raw scanner owns this checkpoint') from None
        path=root/'raw.sqlite'
        if path.exists()!=resume:raise ValueError('Raw checkpoint exists; choose resume or a fresh output')
        with sqlite3.connect(path) as db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
            db.executescript('CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL);'
                             'CREATE TABLE IF NOT EXISTS chunks(start INTEGER PRIMARY KEY,end INTEGER NOT NULL,summary TEXT NOT NULL);')
            def save(k,v):db.execute('INSERT OR REPLACE INTO state VALUES (?,?)',(k,canonical(v)))
            def get(k,default=None):
                row=db.execute('SELECT value FROM state WHERE key=?',(k,)).fetchone()
                return json.loads(row[0]) if row else default
            if resume:
                if get('identity')!=ident:raise ValueError('Raw computation/selection/range identity changed')
            else:
                with db:save('identity',ident);save('next',start)
            ranked=[tuple(r) for r in get('ranked',[])];random=[tuple(r) for r in get('exploration',[])]
            heapq.heapify(ranked);heapq.heapify(random)
            at=get('next');new=0;seconds=0.;necessary_missing=get('necessary_missing',0)
            def retain(heap,item,limit):
                if len(heap)<limit:heapq.heappush(heap,item)
                elif item>heap[0]:heapq.heapreplace(heap,item)
            while at<start+count and (stop_after is None or new<stop_after):
                n=min(chunk_size,start+count-at,stop_after-new if stop_after is not None else chunk_size)
                disk_status(root,disk_policy({}),additional_bytes=(top+exploration)*2048)
                begin=time.perf_counter();values=sweep_raw(at,n,FAMILIES,threads,mode=mode);elapsed=time.perf_counter()-begin
                zeros=int((values==0).any(axis=1).sum());necessary_missing+=zeros
                scores=np.minimum(values,32).sum(axis=1)
                hashes=exploration_keys(np.arange(at,at+n,dtype=np.uint64),key)
                # Only a batch's best K can enter the global best K. Stable
                # sorting preserves the smaller-low32 tie rule and allows
                # arbitrary batch sizes across recovery without changing output.
                for offset in np.argsort(-scores,kind='stable')[:top]:
                    low=at+int(offset);v=tuple(map(int,values[offset]))
                    retain(ranked,(int(scores[offset]),-low,v),top)
                for offset in np.argsort(hashes,kind='stable')[:exploration]:
                    low=at+int(offset);v=tuple(map(int,values[offset]))
                    retain(random,(-int(hashes[offset]),-low,v),exploration)
                with db:
                    db.execute('INSERT INTO chunks VALUES (?,?,?)',(at,at+n,canonical({'inputs':n,'seconds':elapsed,'necessary_missing':zeros})))
                    save('ranked',ranked);save('exploration',random);save('next',at+n);save('necessary_missing',necessary_missing)
                at+=n;new+=n;seconds+=elapsed
            rows={}
            for label,heap in (('ranked',ranked),('exploration',random)):
                for score,negative_seed,counts in sorted(heap,reverse=True):
                    low=-negative_seed
                    rows.setdefault(low,{'low32':low,'raw_counts':list(counts),'ranking_hint':_score(counts),'selection':[]})['selection'].append(label)
            summary={'status':'COMPLETE' if at==start+count else 'PARTIAL','version':ident['version'],'range':[start,start+count],
                     'completed_lower32_inputs':at-start,'invocation_inputs':new,'invocation_raw_seconds':seconds,
                     'raw_inputs_per_second':new/seconds if seconds else None,'necessary_missing':necessary_missing,
                     'selected':sorted(rows.values(),key=lambda r:(-r['ranking_hint'],r['low32'])),
                     'policy':'shadow/ranking only; absent raw placements are not actual-world absence; joint centers not inferred',
                     'backend':ident['backend'],'threads':threads}
            summary['geometry']=ident['geometry']
            summary['exploration_policy']=ident['exploration_policy']
            summary['count_mode']=mode
            summary['count_semantics']='presence booleans' if mode=='presence' else 'min(full_count,32); saturated values are lower bounds' if mode=='capped' else 'complete bounded predictor count'
            summary['ranking_semantics']='presence-only diagnostic; not legacy density ranking' if mode=='presence' else 'legacy capped-density hint; not viability or verified yield'
            temp=root/'raw-selection.json.tmp';temp.write_text(json.dumps(summary,indent=2)+'\n');temp.replace(root/'raw-selection.json')
            return summary


def prepare_siblings(selection,high32=(0,1),limit=128):
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=10000:raise ValueError('Sibling limit must be 1–10000')
    if len(set(high32))!=len(high32) or any(isinstance(h,bool) or not isinstance(h,int) or not 0<=h<2**32 for h in high32):raise ValueError('High32 siblings must be distinct uint32 values')
    seeds=[]
    for row in selection['selected']:
        for high in high32:
            unsigned=(high<<32)|row['low32'];seed=unsigned if unsigned<2**63 else unsigned-2**64
            seeds.append({'seed':str(seed),'low32':row['low32'],'high32':high,'selection':row['selection']})
            if len(seeds)>=limit:return seeds
    return seeds


def dispersed_high32(count=4,key='0'):
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=65536:
        raise ValueError('Sibling count must be 1–65536')
    offset=_hash(0,key)&0xffffffff
    # Odd multiplier is a permutation modulo 2**32; prefixes are dispersed.
    return tuple((offset+i*0x9e3779b1)&0xffffffff for i in range(count))


def nether_center_coverage(layouts):
    """Exact integer feasible-center area, shared by both required Nether types."""
    if len(layouts)!=2:raise ValueError('Need Fortress and Bastion layouts')
    groups=[[r for p in points if (r:=center_rectangle(p,True)) is not None] for points in layouts]
    if any(not g for g in groups):return {'area':0,'fraction':0.,'witness':None,'regions':[]}
    events=sorted({r[0] for g in groups for r in g}|{r[2]+1 for g in groups for r in g})
    regions=[];area=0
    for x,next_x in zip(events,events[1:]):
        intersections=[]
        for a in groups[0]:
            if not a[0]<=x<=a[2]:continue
            for b in groups[1]:
                if b[0]<=x<=b[2]:
                    lo,hi=max(a[1],b[1]),min(a[3],b[3])
                    if lo<=hi:intersections.append((lo,hi))
        merged=[]
        for lo,hi in sorted(intersections):
            if merged and lo<=merged[-1][1]+1:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
            else:merged.append((lo,hi))
        for lo,hi in merged:
            regions.append([x,lo,next_x-1,hi]);area+=(next_x-x)*(hi-lo+1)
    total=(CENTER_BOUNDS[2]-CENTER_BOUNDS[0]+1)*(CENTER_BOUNDS[3]-CENTER_BOUNDS[1]+1)
    return {'area':area,'fraction':area/total,'witness':regions[0][:2] if regions else None,'regions':regions}


def rank_geometry(selection, *, top=64, exploration=16, key='0'):
    """Re-rank a bounded raw pool; feature overhead is explicit and charged."""
    if len(selection.get('selected',[]))>10000 or top<1 or exploration<1:
        raise ValueError('Geometry ranking needs a bounded pool and positive retention')
    if selection.get('geometry')!={'deployment':DEFAULT['deployment'],'discovery':DEFAULT['discovery']}:
        raise ValueError('Geometry selection contract changed')
    if selection.get('backend')!=backend_identity():raise ValueError('Geometry ranking backend changed')
    begin=time.perf_counter();cpu=time.process_time();rows=[]
    for row in selection['selected']:
        low=row['low32']
        coverage=nether_center_coverage([raw_layout(low,name,NETHER_ENVELOPE) for name in ('fortress','bastion')])
        rows.append({**row,'geometry_hint':coverage,'ranking_hint':coverage['fraction'],'selection':[]})
    ranked=sorted(rows,key=lambda r:(-r['ranking_hint'],r['low32']))[:top]
    random=sorted(rows,key=lambda r:_hash(r['low32'],key))[:exploration]
    retained={}
    for label,group in (('geometry',ranked),('exploration',random)):
        for row in group:
            retained.setdefault(row['low32'],row)['selection'].append(label)
    return {**selection,'selected':sorted(retained.values(),key=lambda r:(-r['ranking_hint'],r['low32'])),
            'ranking_policy':'nether-feasible-center-area-v1','feature_pool_inputs':len(rows),
            'feature_seconds':time.perf_counter()-begin,'feature_cpu_seconds':time.process_time()-cpu,
            'ranking_semantics':'bounded geometric ranking experiment; full64 viability and actual Stronghold centers unresolved'}


def evaluate_siblings(cfg,output,selection,*,high32=(0,1),limit=128,resume=False):
    """Finite full64 handoff with durable per-input baseline/anchor evidence."""
    from .baseline import evaluate_seed
    expected={'deployment':cfg['deployment'],'discovery':cfg['discovery']}
    if selection.get('geometry')!=expected:raise ValueError('Raw selection geometry differs from full64 contract')
    if selection.get('backend')!=backend_identity():raise ValueError('Raw selection backend identity changed')
    configure_native_threads(cfg['search'].get('native_threads_per_worker',1))
    inputs=prepare_siblings(selection,high32,limit)
    import copy
    from .runner import run_scan
    cfg=copy.deepcopy(cfg);cfg['search'].update(sequence='manifest',manifest_seeds=[r['seed'] for r in inputs])
    root=Path(output)
    if not root.exists():
        from .capabilities import report
        root.mkdir(parents=True)
        (root/'compatibility.json').write_text(json.dumps(report(cfg),indent=2)+'\n')
    identity={'policy':'raw-full64-siblings-v2','config':cfg,'backend':backend_identity(),'inputs':inputs}
    run_scan(cfg,output,len(inputs),workers=cfg['search']['workers'],resume=resume,identity=identity,allow_prediction_scale=True)
    with RealmStore(output,resume=True) as store:
        store.set_state('raw_selection_provenance',{'inputs':inputs,'raw_range':selection['range'],'bias':'finite selected lower32/high32 siblings; not exhaustive'})
        return store.status()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    scan=commands.add_parser('scan');scan.add_argument('--output',required=True);scan.add_argument('--start',type=int,default=0)
    scan.add_argument('--count',type=int,required=True);scan.add_argument('--threads',type=int,default=1)
    scan.add_argument('--top',type=int,default=64);scan.add_argument('--exploration',type=int,default=16)
    scan.add_argument('--chunk-size',type=int,default=256);scan.add_argument('--resume',action='store_true')
    sibling=commands.add_parser('siblings');sibling.add_argument('--selection',required=True);sibling.add_argument('--output',required=True)
    sibling.add_argument('--config');sibling.add_argument('--limit',type=int,default=128);sibling.add_argument('--high32',type=int,nargs='+',default=[0,1]);sibling.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if args.command=='scan':result=run_raw(args.output,args.start,args.count,threads=args.threads,top=args.top,exploration=args.exploration,chunk_size=args.chunk_size,resume=args.resume)
    else:
        from .cli import load
        result=evaluate_siblings(load(args.config),args.output,json.loads(Path(args.selection).read_text()),high32=args.high32,limit=args.limit,resume=args.resume)
    print(json.dumps(result,indent=2))
