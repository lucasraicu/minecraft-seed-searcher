"""Validated Python boundary around isolated native count-N kernels."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import numpy as np
from seed_search.backend import STRUCTURES
ROOT=Path(__file__).resolve().parents[1]
IDENTITY=ROOT/'runs/count-bits-2026-10-11/native/identity.json'
module_path=json.loads(IDENTITY.read_text())['extension']
spec=importlib.util.spec_from_file_location('_count_pilot',module_path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ffi,lib=module.ffi,module.lib
TYPES={name:int(lib.ss_structure_type(name.encode())) for name in STRUCTURES}
NETHER={'fortress','bastion','ruined_portal_nether'}
DIM={name:-1 if name in NETHER else 1 if name=='end_city' else 0 for name in STRUCTURES}
Y={name:33 if name in NETHER else -48 if name=='ancient_city' else 0 if name in ('mineshaft','trial_chamber') else 63 for name in STRUCTURES}

def checked_bounds(bounds):
    if len(bounds)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,np.integer)) or not -(1<<30)<=int(x)<(1<<30) for x in bounds):
        raise ValueError('Four safe inclusive integer coordinates required')
    b=tuple(map(int,bounds))
    if b[0]>b[2] or b[1]>b[3] or b[2]-b[0]>14000 or b[3]-b[1]>14000:raise ValueError('Invalid bounds')
    return b

def checked_goal(goal):
    if isinstance(goal,bool) or not isinstance(goal,int) or not 1<=goal<=32:raise ValueError('Count must be 1–32')
    return goal

def checked_allow(ids):
    if ids is None:return ffi.NULL
    values=list(ids)
    if any(isinstance(x,bool) or not isinstance(x,(int,np.integer)) or not 0<=int(x)<256 for x in values):raise ValueError('Invalid biome IDs')
    array=ffi.new('int[256]')
    for value in values:array[int(value)]=1
    return array

class CountBackend:
    def __init__(self,seed):
        self.seed=int(seed)&((1<<64)-1)
        self.ctx=ffi.gc(lib.ss_create(self.seed),lib.ss_destroy)
        if self.ctx==ffi.NULL:raise MemoryError('Generator allocation failed')
    def close(self):
        if self.ctx is not None:ffi.release(self.ctx);self.ctx=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def count(self,name,bounds,goal,*,gate_bits=0,raw_only=False,allow=None,y=None):
        if self.ctx is None:raise RuntimeError('Closed backend')
        if name not in TYPES:raise ValueError('Unknown structure')
        checked_goal(goal);bounds=checked_bounds(bounds)
        if gate_bits not in (0,32,48):raise ValueError('Gate bits must be 0,32,48')
        allow=checked_allow(allow)
        b=ffi.new('int[4]',bounds);stats=ffi.new('int[8]')
        result=lib.pc_count(self.ctx,TYPES[name],b,goal,int(raw_only),gate_bits,allow,Y[name] if y is None else int(y),stats)
        if result<0 and result!=-3:raise RuntimeError(f'Count failed: {name} {result}')
        return result>=goal,list(stats),max(0,result)
    def prepare_combo(self,row,order,goal,raw_order=None):
        if len(order)!=len(set(order)) or not 1<=len(order)<=22 or any(n not in TYPES for n in order):raise ValueError('Unique supported names required')
        checked_goal(goal)
        raw_order=order if raw_order is None else raw_order
        if set(raw_order)!=set(order) or len(raw_order)!=len(order):raise ValueError('Raw order must be a permutation')
        types=ffi.new('int[]',[TYPES[n] for n in order])
        bounds=ffi.new('int[]',[v for n in order for v in checked_bounds(row['bounds']['nether' if n in NETHER else 'overworld'])])
        goals=ffi.new('int[]',[goal]*len(order))
        indices=ffi.new('int[]',[order.index(n) for n in raw_order])
        return types,bounds,goals,indices,len(order)
    def combo_prepared(self,prepared,gate_bits=0,known_anchor=True):
        if self.ctx is None:raise RuntimeError('Closed backend')
        if gate_bits not in (0,32,48):raise ValueError('Gate bits must be 0,32,48')
        types,bounds,goals,indices,n=prepared;stats=ffi.new('int[8]')
        result=lib.pc_combo(self.ctx,types,bounds,goals,n,gate_bits,int(known_anchor),indices,stats)
        if result<0:raise RuntimeError(f'Combination failed {result}')
        return bool(result),list(stats)
    def biome_count(self,points,dimension,ids,goal):
        points=np.ascontiguousarray(points,dtype=np.int32)
        if points.ndim!=2 or points.shape[1]!=3 or len(points)>100000 or dimension not in (-1,0,1):raise ValueError('Invalid biome points/dimension')
        if isinstance(goal,bool) or not isinstance(goal,int) or goal<1:raise ValueError('Positive biome count needed')
        allow=checked_allow(ids);queried=ffi.new('int[1]')
        result=lib.pc_biome_count(self.ctx,dimension,ffi.from_buffer('int[]',points),len(points),allow,goal,queried)
        if result<0:raise RuntimeError('Biome count failed')
        return result>=goal,int(queried[0]),result
