"""Finite bijective low32 enumeration, raw scheduling and full64 siblings.

Raw rankings are scheduling preferences, not full-seed eligibility. Raw selection
is checkpointed before any full64 work; exact completed siblings are parent-owned.
"""
import heapq
import math
import time
import numpy as np
from .backend import raw_layout,RAW_MT_TYPES
from .structures import envelope_bounds

MASK32=2**32-1

def permute32(index,key=0):
    if not 0<=index<=MASK32:raise ValueError('32-bit enumeration must not wrap')
    x=(index+key)&MASK32
    x=((x^(x>>16))*0x7feb352d)&MASK32
    x=((x^(x>>15))*0x846ca68b)&MASK32
    return x^(x>>16)

def compose_seed(low,high):
    if not 0<=low<=MASK32 or not 0<=high<=MASK32:raise ValueError('Seed halves must be uint32')
    value=(high<<32)|low
    return value if value<2**63 else value-2**64

def validate_staged(p):
    expected={'raw_layout_count','retained_layouts','exploration_layouts','siblings_per_layout','maximum_full64_evaluations','selection_version'}
    if set(p)!=expected or p['selection_version']!='raw-cluster-v1':raise ValueError('Invalid staged selection policy')
    for name in expected-{'selection_version','exploration_layouts'}:
        v=p[name]
        if isinstance(v,bool) or not isinstance(v,int) or v<1:raise ValueError(f'Invalid staged budget {name}')
    e=p['exploration_layouts']
    if isinstance(e,bool) or not isinstance(e,int) or not 0<=e<p['retained_layouts']:raise ValueError('Exploration count must be smaller than retained count')
    if p['retained_layouts']>p['raw_layout_count'] or p['retained_layouts']>4096 or p['raw_layout_count']>2**32 or p['siblings_per_layout']>2**32:
        raise ValueError('Staged budgets exceed finite enumeration or memory limits')
    if p['maximum_full64_evaluations']>p['retained_layouts']*p['siblings_per_layout']:raise ValueError('Full64 budget exceeds available siblings')

def evaluate_layout(low,cfg):
    ob,nb=envelope_bounds(cfg)
    scans={name:raw_layout(low,name,nb if name in ('fortress','bastion') else ob) for name in sorted(RAW_MT_TYPES)}
    lo,hi=cfg['search']['center_axis_bounds_blocks'];half=cfg['deployment']['nether_side_blocks']//2
    # Exact necessary Fortress window intersects the permitted eight-block grid.
    anchors=[]
    for x,z in scans['fortress']:
        a,b=max(lo,(x-half)*8),min(hi,(x+half)*8);c,d=max(lo,(z-half)*8),min(hi,(z+half)*8)
        if math.ceil(a/8)*8<=b and math.ceil(c/8)*8<=d:
            anchors.append((min(b,max(a,x*8))//8*8,min(d,max(c,z*8))//8*8))
    if not anchors:return None
    # Equal family budgets, nearest proximity within each candidate square;
    # missing optional families contribute zero, never a rejection.
    best=0.
    for center in anchors:
        value=0.
        for name,points in scans.items():
            if not points:continue
            scale=8 if name in ('fortress','bastion') else 1
            halfwidth=cfg['deployment']['nether_side_blocks' if scale==8 else 'overworld_side_blocks']//2
            delta=np.abs(np.asarray(points)-np.asarray(center)/scale)
            eligible=delta.max(axis=1)<=halfwidth
            if eligible.any():value+=max(0,1-float(np.linalg.norm(delta[eligible],axis=1).min())/(halfwidth*math.sqrt(2)))
        best=max(best,value/len(RAW_MT_TYPES))
    return {'low32':low,'raw_score':best,'raw_counts':{k:len(v) for k,v in scans.items()}}

def prepare(store,cfg,start_index,count):
    p=cfg['search']['staged'];validate_staged(p)
    if start_index+p['raw_layout_count']>2**32:raise ValueError('Raw layout interval must not wrap uint32')
    if count>p['maximum_full64_evaluations']:raise ValueError('Requested count exceeds configured full64 budget')
    saved=store.get_state('staged') or {'cursor':start_index,'top':[],'explore':[],'eligible_raw':0,'raw_seconds':0.,'raw_cpu_seconds':0.}
    if saved.get('selected') is not None:
        if len(saved['selected'])*p['siblings_per_layout']<count:raise ValueError('Too few eligible raw layouts for requested full64 count')
        return saved
    top=[tuple(v) for v in saved['top']];explore=[tuple(v) for v in saved['explore']]
    heapq.heapify(top);heapq.heapify(explore)
    key=int(cfg['search']['run_key']);k=p['retained_layouts']-p['exploration_layouts'];reserve=p['retained_layouts']
    t=time.perf_counter();cpu=time.process_time()
    for i in range(saved['cursor'],start_index+p['raw_layout_count']):
        low=permute32(i,key&MASK32);row=evaluate_layout(low,cfg)
        if row is not None:
            saved['eligible_raw']+=1
            item=(row['raw_score'],-i,low,row['raw_counts'])
            if len(top)<k:heapq.heappush(top,item)
            elif item[:2]>top[0][:2]:heapq.heapreplace(top,item)
            # Independent deterministic priority; hold enough reserves to exclude top selections.
            item=(permute32(i,(key>>32)^0x9e3779b9),-i,low,row['raw_score'],row['raw_counts'])
            if len(explore)<reserve:heapq.heappush(explore,item)
            elif item[:2]>explore[0][:2]:heapq.heapreplace(explore,item)
        saved.update(cursor=i+1,top=top,explore=explore)
        if (i-start_index+1)%100==0:
            saved['raw_seconds']+=time.perf_counter()-t;saved['raw_cpu_seconds']+=time.process_time()-cpu
            t=time.perf_counter();cpu=time.process_time();store.set_state('staged',saved)
        if (i-start_index+1)%1000==0:print(f'Raw layouts examined: {i-start_index+1}/{p["raw_layout_count"]}',flush=True)
    selected=[{'low32':v[2],'layout_index':-v[1],'raw_score':v[0],'raw_counts':v[3],'selection':'top'} for v in sorted(top,reverse=True)]
    lows={r['low32'] for r in selected}
    for v in sorted(explore,reverse=True):
        if len(selected)>=p['retained_layouts']:break
        if v[2] in lows:continue
        selected.append({'low32':v[2],'layout_index':-v[1],'raw_score':v[3],'raw_counts':v[4],'selection':'exploration'})
        lows.add(v[2])
        if len(selected)>=p['retained_layouts']:break
    saved['raw_seconds']+=time.perf_counter()-t;saved['raw_cpu_seconds']+=time.process_time()-cpu;saved['selected']=selected
    if len(selected)*p['siblings_per_layout']<count:
        store.set_state('staged',saved)
        raise ValueError('Too few eligible raw layouts for requested full64 count; use a new run/budget')
    store.set_state('staged',saved)
    return saved

def sibling_job(i,start_index,cfg,state):
    offset=i-start_index;siblings=cfg['search']['staged']['siblings_per_layout'];slot,number=divmod(offset,siblings)
    row=state['selected'][slot];key=int(cfg['search']['run_key'])
    high=permute32(number,(key>>32)^permute32(row['layout_index']))
    return compose_seed(row['low32'],high),{'layout_index':row['layout_index'],'retained_slot':slot,'sibling_index':number,'low32':row['low32'],'high32':high,'selection':row['selection']}
