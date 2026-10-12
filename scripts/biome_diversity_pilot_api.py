"""Full64 distinct-biome witnesses; sampled-lattice negatives only."""
import importlib.util,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
IDENTITY=ROOT/'runs/count-bits-2026-10-11/native-biomes/identity.json'
spec=importlib.util.spec_from_file_location('_biome_diversity_pilot',json.loads(IDENTITY.read_text())['extension'])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ffi,lib=module.ffi,module.lib

class DiversityBackend:
    def __init__(self,seed):
        self.ctx=ffi.gc(lib.ss_create(int(seed)&((1<<64)-1)),lib.ss_destroy)
        if self.ctx==ffi.NULL:raise MemoryError('Generator allocation failed')
    def close(self):
        if self.ctx is not None:ffi.release(self.ctx);self.ctx=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def prepare(self,points,dimension,groups,goals):
        points=np.ascontiguousarray(points,dtype=np.int32)
        if points.ndim!=2 or points.shape[1]!=3 or not 0<len(points)<=100000 or dimension not in (-1,0,1):raise ValueError('Invalid points/dimension')
        if len(groups)!=len(goals) or not 1<=len(groups)<=66 or any(isinstance(n,bool) or not isinstance(n,int) or n<1 for n in goals):raise ValueError('Invalid diversity requirements')
        allow=ffi.new('int[]',len(groups)*256)
        for j,group in enumerate(groups):
            for ident in group:
                if isinstance(ident,bool) or not isinstance(ident,(int,np.integer)) or not 0<=int(ident)<256:raise ValueError('Invalid biome ID')
                allow[j*256+int(ident)]=1
        return points,dimension,allow,ffi.new('int[]',goals),len(groups)
    def prepared(self,prepared):
        if self.ctx is None:raise RuntimeError('Closed backend')
        points,dimension,allow,goals,n=prepared;queried=ffi.new('int[1]')
        if n==1:
            count=lib.bd_count(self.ctx,dimension,ffi.from_buffer('int[]',points),len(points),allow,goals[0],queried)
            if count<0:raise RuntimeError('Diversity query failed')
            return count>=goals[0],int(queried[0])
        result=lib.bd_combo(self.ctx,dimension,ffi.from_buffer('int[]',points),len(points),allow,goals,n,queried)
        if result<0:raise RuntimeError('Diversity combination failed')
        return bool(result),int(queried[0])
