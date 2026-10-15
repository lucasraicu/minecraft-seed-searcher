"""Exact integer-center selection for the 1664/832 predictor policy.

Every event is a coordinate where a structure or a world-lattice biome sample
enters or leaves a window. Counts and sampled biome sets are constant between
events. Each rectangle uses its captured weighted centroid, constrained to
the valid 16/8 grid, before palette and score ranking.
"""
from dataclasses import dataclass
import math

from .bounds import contains

OVERWORLD_HALF=832
NETHER_HALF=416
MIN_CENTER=-1168
MAX_CENTER=1168
DENSITY_NAMES=('village','trial_chamber','ancient_city','desert_pyramid',
               'jungle_temple','outpost')
OVERWORLD_NAMES=('stronghold','mansion','village','trial_chamber','ancient_city',
                 'desert_pyramid','jungle_temple','monument','ruined_portal',
                 'shipwreck','mineshaft','outpost')
NETHER_NAMES=('fortress','bastion')
OPTIONAL_NAMES=('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')
CENTROID_WEIGHTS={'village':3,'trial_chamber':2,'ruined_portal':2,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':1}
NETHER_BIOMES=('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas')


def overworld_bounds(center):
    x,z=center
    return x-OVERWORLD_HALF,z-OVERWORLD_HALF,x+OVERWORLD_HALF,z+OVERWORLD_HALF


def nether_bounds(center):
    """Exact rational center/8; return inclusive lower and exclusive upper ints."""
    x,z=center
    return ((x-8*NETHER_HALF+7)//8,(z-8*NETHER_HALF+7)//8,
            (x+8*NETHER_HALF+7)//8,(z+8*NETHER_HALF+7)//8)


def _axis_events(points,half,nether=False):
    events={MIN_CENTER,MAX_CENTER+1}
    for value in points:
        if nether:
            lo=8*(value-half)+1
            hi=8*(value+half)+1
        else:
            lo=value-half+1
            hi=value+half+1
        if MIN_CENTER<lo<=MAX_CENTER:events.add(lo)
        if MIN_CENTER<hi<=MAX_CENTER:events.add(hi)
    return sorted(events)


def _nearest_zero(lo,hi):
    return 0 if lo<=0<=hi else hi if hi<0 else lo


@dataclass(frozen=True)
class Candidate:
    center:tuple[int,int]
    density:int
    counts:dict[str,int]
    deficits:tuple[str,...]
    radial:float=0.


def candidate_centers(inventories, floors, ideals, weights, max_misses=2):
    """Yield all floor/budget-eligible equivalence cells in exact density order.

    ``inventories`` are complete, viable macro-envelope coordinates. The
    mansion list must already be filtered to Dark Forest starts at Y=63.
    Biome lattice events are included here; a palette check on the returned
    representative therefore applies to the entire event rectangle.
    """
    xs=[];zs=[];nether_x=[];nether_z=[]
    for name,points in inventories.items():
        target_x,target_z=(nether_x,nether_z) if name in NETHER_NAMES else (xs,zs)
        for x,z in points:target_x.append(x);target_z.append(z)
    # World-aligned four-Y sampling: a lattice point is present throughout an
    # interval between its entry/exit events, independent of the sampled ID.
    xs.extend(range(-1984,1985,64));zs.extend(range(-1984,1985,64))
    nether_x.extend(range(-512,513,64));nether_z.extend(range(-512,513,64))
    ex=sorted(set(_axis_events(xs,OVERWORLD_HALF)+_axis_events(nether_x,NETHER_HALF,True)))
    ez=sorted(set(_axis_events(zs,OVERWORLD_HALF)+_axis_events(nether_z,NETHER_HALF,True)))
    rows=[]
    for xi in range(len(ex)-1):
        cx=_nearest_zero(ex[xi],ex[xi+1]-1)
        for zi in range(len(ez)-1):
            cz=_nearest_zero(ez[zi],ez[zi+1]-1)
            center=(cx,cz);ow=overworld_bounds(center);nb=nether_bounds(center)
            counts={name:sum(contains(point,nb if name in NETHER_NAMES else ow)
                             for point in points) for name,points in inventories.items()}
            if any(counts.get(name,0)<floor for name,floor in floors.items()):continue
            deficits=tuple(name for name,ideal in ideals.items() if counts.get(name,0)<ideal)
            if len(deficits)>max_misses:continue
            captured=[(x,z,CENTROID_WEIGHTS[name]) for name,points in inventories.items() if name in CENTROID_WEIGHTS
                      for x,z in points if contains((x,z),ow)]
            weight=sum(row[2] for row in captured)
            sx=sum(x*w for x,z,w in captured);sz=sum(z*w for x,z,w in captured)
            axes=[]
            for lo,hi,total in ((ex[xi],ex[xi+1]-1,sx),(ez[zi],ez[zi+1]-1,sz)):
                value=None
                for step in (16,8):
                    lower=-(-lo//step)*step;upper=(hi//step)*step
                    if lower>upper:continue
                    rounded=((total+(step//2)*weight)//(step*weight))*step if weight else 0
                    value=min(upper,max(lower,rounded));break
                axes.append(value)
            if any(value is None for value in axes):continue
            snapped=tuple(axes)
            radial=sum(w*math.hypot(x-snapped[0],z-snapped[1]) for x,z,w in captured)/weight if weight else 0.
            density=sum(weights[name]*counts.get(name,0) for name in DENSITY_NAMES)
            rows.append(Candidate(snapped,density,counts,deficits,radial))
    rows.sort(key=lambda row:(len(row.deficits),-row.density,row.radial,row.center[0]**2+row.center[1]**2,
                              row.center[0],row.center[1]))
    return rows


def nether_palette(backend,center):
    from ..backend import biome_name
    bounds=nether_bounds(center)
    x0=-(-bounds[0]//64)*64;z0=-(-bounds[1]//64)*64
    points=[(x0+x*64,64,z0+z*64) for z in range(13) for x in range(13)]
    values=backend.sample(points,dimension=-1)
    if len(values)!=len(points):raise ValueError('Incomplete Nether biome sample batch')
    samples=[{'coordinate':list(point),'id':int(value),'biome':biome_name(int(value))} for point,value in zip(points,values)]
    found={row['biome']:row for row in samples if row['biome'] in NETHER_BIOMES}
    return {'status':'PREDICTED' if len(found)==5 else 'PENDING','required_families':list(NETHER_BIOMES),
            'missing_families':[name for name in NETHER_BIOMES if name not in found],
            'witnesses':found,'sample_count':len(samples),'sampling':{'lattice':'world','spacing':64,'y':64,'samples':samples},
            'actual_generation_verified':False}


def hub_bonus(structures,center):
    points={'village':6,'desert_pyramid':6,'jungle_temple':6,'outpost':6,'ruined_portal':4}
    return min(40,sum(value for name,value in points.items() for x,z in structures.get(name,())
                      if (x-center[0])**2+(z-center[1])**2<=512**2))


def weighted_radial(structures,center):
    total=sum(weight*len(structures.get(name,())) for name,weight in CENTROID_WEIGHTS.items())
    return sum(weight*math.hypot(x-center[0],z-center[1]) for name,weight in CENTROID_WEIGHTS.items()
               for x,z in structures.get(name,()))/total if total else 0.


class PaletteIndex:
    """Independent prefix counts over the fixed macro lattice for cheap windows."""
    def __init__(self,sampler,policy):
        import numpy as np
        from ..backend import biome_name
        from .biomes import canonical
        from .blueprint import PALETTE,CAVE_FAMILIES,DYNAMIC_LUXURIES
        from .sampling import grid_points
        self.np=np
        masks=np.zeros((23,63,63),dtype=np.int32)
        for y in policy['sample_y_levels']:
            points=grid_points((-2000,-2000,2000,2000),64,y,'world')
            values=sampler.sample(points)
            names=np.array([canonical(biome_name(int(v))) for v in values]).reshape(63,63)
            for i,family in enumerate(policy['required_families']):
                if y in ((-48,0) if family in CAVE_FAMILIES else (63,160)):
                    members=PALETTE[family]|({'frozen_peaks'} if family=='peaks' and policy.get('include_frozen_peaks') else set())
                    masks[i]|=np.isin(names,list(members))
            if y==63:
                self.surface=names
                for i,(_,members) in enumerate(DYNAMIC_LUXURIES):masks[13+i]=np.isin(names,members)
        self.prefix=np.pad(masks,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)
        points=grid_points((-512,-512,513,513),64,64,'world')
        values=sampler.sample(points,dimension=-1)
        names=np.array([biome_name(int(v)) for v in values]).reshape(17,17)
        mask=np.array([names==name for name in NETHER_BIOMES],dtype=np.int32)
        self.nether=np.pad(mask,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)

    @staticmethod
    def counts(prefix,x0,z0,x1,z1):
        return prefix[:,z1,x1]-prefix[:,z0,x1]-prefix[:,z1,x0]+prefix[:,z0,x0]

    def window(self,center):
        x,z=center
        return self.counts(self.prefix,-(-(x-832+1984)//64),-(-(z-832+1984)//64),
                           -(-(x+832+1984)//64),-(-(z+832+1984)//64))

    def valid(self,center):
        x,z=center
        return bool(self.np.all(self.window(center)[:13]>0) and self.np.all(self.counts(self.nether,
            -(-(x-3328+4096)//512),-(-(z-3328+4096)//512),
            -(-(x+3328+4096)//512),-(-(z+3328+4096)//512))>0))

    def luxuries(self,center):
        from .blueprint import DYNAMIC_LUXURIES
        return [members[0] for count,(_,members) in zip(self.window(center)[13:],DYNAMIC_LUXURIES) if count]
