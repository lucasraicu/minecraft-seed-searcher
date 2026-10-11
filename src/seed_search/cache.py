"""Bounded per-seed exact caches; no reuse across seeds or height strides."""
from collections import OrderedDict, defaultdict
import numpy as np
from .backend import Backend


class CachedBackend(Backend):
    def __init__(self,seed,cache_mb=64,raw_cache_entries=0,quart_land_reuse=True):
        super().__init__(seed,raw_cache_entries)
        self.limit=int(cache_mb*1024**2)
        if self.limit<32768:raise ValueError('Cache must hold at least one 32 KiB tile')
        self.tiles=OrderedDict();self.bytes=0;self.peak_bytes=0;self.evictions=0
        self.stats=defaultdict(lambda:{'requested_points':0,'computed_points':0,'reused_points':0})
        self.quart_land_reuse=quart_land_reuse

    def _sample(self,points,kind,scale,side,fields,dtype,missing,compute):
        points=np.asarray(points)
        # Preserve Backend validation even when every requested point is cached.
        if points.ndim!=2 or points.shape[1]!=2 or len(points)>100000 or not np.issubdtype(points.dtype,np.integer):
            raise ValueError('Expected up to 100,000 integer X/Z pairs')
        if np.any(points<-(1<<30)) or np.any(points>=(1<<30)):raise ValueError('Point outside safe range')
        self._handle()
        points=points.astype(np.int32);out=np.empty((len(points),fields),dtype=dtype)
        if not len(points):return out
        xy=points.astype(np.int64)//scale;tile=xy//side
        keys=(tile[:,0]<<32)|(tile[:,1]&0xffffffff)
        unique,inverse=np.unique(keys,return_inverse=True)
        order=np.argsort(inverse,kind='stable');edges=np.r_[0,np.cumsum(np.bincount(inverse))]
        st=self.stats[kind];st['requested_points']+=len(points)
        for i,_ in enumerate(unique):
            rows=order[edges[i]:edges[i+1]];tx,tz=tile[rows[0]]
            key=(kind,scale,int(tx),int(tz))
            data=self.tiles.pop(key,None)
            if data is None:
                data=np.full((side*side,fields),missing,dtype=dtype)
                while self.bytes+data.nbytes>self.limit and self.tiles:
                    _,old=self.tiles.popitem(last=False);self.bytes-=old.nbytes;self.evictions+=1
                self.bytes+=data.nbytes;self.peak_bytes=max(self.peak_bytes,self.bytes)
            self.tiles[key]=data
            local=xy[rows]%side;slots=local[:,1]*side+local[:,0]
            absent=data[slots,0]==missing
            if absent.any():
                slots_missing,first,back=np.unique(slots[absent],return_index=True,return_inverse=True)
                batch=points[rows[absent][first]]
                values=np.asarray(compute(batch),dtype=dtype).reshape(len(batch),fields)
                data[slots_missing]=values;st['computed_points']+=len(batch)
            out[rows]=data[slots]
        st['reused_points']=st['requested_points']-st['computed_points']
        return out

    def heights(self,points,vertical_step=8):
        if isinstance(vertical_step,bool) or not isinstance(vertical_step,int) or not 1<=vertical_step<=16:
            raise ValueError('Vertical step must be an integer in 1–16')
        # Height and block-selected surface biome remain keyed by original X/Z.
        p=np.asarray(points);scale=1
        def compute(p):
            h,b=super(CachedBackend,self).heights(p,vertical_step)
            return np.column_stack((h,b))
        out=self._sample(p,f'height_stride_{vertical_step}',scale,64,2,np.int32,-2147483648,compute)
        return out[:,0].copy(),out[:,1].copy()

    def land(self,points):
        out=self._sample(points,'exact_land',4 if self.quart_land_reuse else 1,128,1,np.int8,-128,
                         lambda p:super(CachedBackend,self).land(p))
        return out[:,0].astype(bool)

    def cache_statistics(self):
        return {'operations':dict(self.stats),'maximum_bytes':self.limit,'peak_bytes':self.peak_bytes,'evictions':self.evictions,
                'raw_land_capability':'pinned_raw_density_quart_xz_v1' if self.quart_land_reuse else 'original_xz',
                'scope':'One seed/backend instance; raw land only shares quart cells; surface biomes and height strides remain separate.'}

    def close(self):
        self.tiles.clear();self.bytes=0
        super().close()
