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
DYNAMIC_V2_CENTROID_WEIGHTS={'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':0}
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


_LAT = {v for s in range(-1984, 1985, 64) for v in (s - 831, s + 833)} | \
       {v for n in range(-512, 513, 64) for v in (8 * n - 3327, 8 * n + 3329)}
_LAT = {v for v in _LAT if MIN_CENTER < v <= MAX_CENTER}


@dataclass(frozen=True)
class Candidate:
    center:tuple[int,int]
    density:int
    counts:dict[str,int]
    deficits:tuple[str,...]
    radial:float=0.


def candidate_centers(inventories, floors, ideals, weights, max_misses=2, centroid_weights=None):
    """Yield all floor/budget-eligible equivalence cells in exact density order.

    ``inventories`` are complete, viable macro-envelope coordinates. The
    mansion list must already be filtered to Dark Forest starts at Y=63.
    Biome lattice events are included here; a palette check on the returned
    representative therefore applies to the entire event rectangle.
    """
    cw = centroid_weights if centroid_weights is not None else CENTROID_WEIGHTS
    xs=[];zs=[];nether_x=[];nether_z=[]
    for name,points in inventories.items():
        if name in OPTIONAL_NAMES:continue
        target_x,target_z=(nether_x,nether_z) if name in NETHER_NAMES else (xs,zs)
        for x,z in points:target_x.append(x);target_z.append(z)
    ex=sorted(set(_axis_events(xs,OVERWORLD_HALF)+_axis_events(nether_x,NETHER_HALF,True))|_LAT)
    ez=sorted(set(_axis_events(zs,OVERWORLD_HALF)+_axis_events(nether_z,NETHER_HALF,True))|_LAT)
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
            captured=[(x,z,cw[name]) for name,points in inventories.items() if name in cw and cw[name]>0
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
            s_ow=overworld_bounds(snapped)
            c=dict(counts)
            for name in OPTIONAL_NAMES:
                if name in inventories:c[name]=sum(contains(p,s_ow) for p in inventories[name])
            radial=sum(w*math.hypot(x-snapped[0],z-snapped[1]) for x,z,w in captured)/weight if weight else 0.
            density=sum(weights[name]*c.get(name,0) for name in DENSITY_NAMES)
            rows.append(Candidate(snapped,density,c,deficits,radial))
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


def hub_bonus_v2(structures,center):
    villages=structures.get('village',())
    d2=lambda p:(p[0]-center[0])**2+(p[1]-center[1])**2
    v_hub=10 if any(d2(p)<=256**2 for p in villages) else 6 if any(d2(p)<=512**2 for p in villages) else 0
    other_pts={'desert_pyramid':6,'jungle_temple':6,'outpost':6}
    other_hub=sum(6 for name in other_pts for p in structures.get(name,()) if d2(p)<=512**2)
    other_hub+=sum(4 for p in structures.get('ruined_portal',()) if d2(p)<=512**2)
    return v_hub+min(30,other_hub)


def hub_village_v2(structures,center):
    villages=structures.get('village',())
    d2=lambda p:(p[0]-center[0])**2+(p[1]-center[1])**2
    nearby=[(d2(p),p[0],p[1]) for p in villages if d2(p)<=512**2]
    if not nearby:return None
    nearby.sort()
    return (nearby[0][1],nearby[0][2])


def weighted_radial(structures,center):
    total=sum(weight*len(structures.get(name,())) for name,weight in CENTROID_WEIGHTS.items())
    return sum(weight*math.hypot(x-center[0],z-center[1]) for name,weight in CENTROID_WEIGHTS.items()
               for x,z in structures.get(name,()))/total if total else 0.


def weighted_radial_v2(structures,center):
    weights=DYNAMIC_V2_CENTROID_WEIGHTS
    total=sum(weight*len(structures.get(name,())) for name,weight in weights.items() if weight>0)
    return sum(weight*math.hypot(x-center[0],z-center[1]) for name,weight in weights.items() if weight>0
               for x,z in structures.get(name,()))/total if total else 0.


SCENIC_BIOMES=frozenset(('plains','sunflower_plains','meadow','cherry_grove'))
RIVER_OFFSETS=sorted([(dix,diz) for dix in range(-2,3) for diz in range(-2,3) if dix*dix+diz*diz<=4],
                     key=lambda o:(o[0],o[1]))


def scenic_pair_bonus_v2(surface_grid,center):
    """Exact scenic river pairing on the 64-block grid; surface_grid is 63x63 names at Y=63."""
    cx,cz=center
    ow=overworld_bounds(center)
    c_ix=(cx+1984)//64
    c_iz=(cz+1984)//64
    min_ix=max(0,c_ix-3);max_ix=min(62,c_ix+4)
    min_iz=max(0,c_iz-3);max_iz=min(62,c_iz+4)
    scenic_candidates=[]
    for ix in range(min_ix,max_ix+1):
        for iz in range(min_iz,max_iz+1):
            sx=-1984+ix*64
            sz=-1984+iz*64
            if (sx-cx)**2+(sz-cz)**2<=192**2 and contains((sx,sz),ow):
                if surface_grid[iz,ix] in SCENIC_BIOMES:
                    scenic_candidates.append((sx,sz,ix,iz))
    scenic_candidates.sort(key=lambda c:(c[0],c[1]))
    for sx,sz,ix,iz in scenic_candidates:
        for dix,diz in RIVER_OFFSETS:
            rix=ix+dix;riz=iz+diz
            if 0<=rix<63 and 0<=riz<63:
                rx=-1984+rix*64;rz=-1984+riz*64
                if contains((rx,rz),ow) and surface_grid[riz,rix]=='river':
                    return 20,(sx,sz),(rx,rz)
    return 0,None,None


def village_spread_bonus_v2(villages,center):
    cx,cz=center
    ow=overworld_bounds(center)
    captured=[tuple(p) for p in villages if contains(p,ow)]
    q_villages=[[] for _ in range(4)]
    for x,z in captured:
        if x>=cx:q=0 if z>=cz else 3
        else:q=1 if z>=cz else 2
        q_villages[q].append((x,z))
    occupied=[q for q in range(4) if q_villages[q]]
    if len(occupied)<3:return 0,None
    quad_combos=[(0,1,2),(0,1,3),(0,2,3),(1,2,3)]
    qualifying=[]
    for qa,qb,qc in quad_combos:
        if not (q_villages[qa] and q_villages[qb] and q_villages[qc]):continue
        for va in q_villages[qa]:
            for vb in q_villages[qb]:
                if (va[0]-vb[0])**2+(va[1]-vb[1])**2<256**2:continue
                for vc in q_villages[qc]:
                    if ((va[0]-vc[0])**2+(va[1]-vc[1])**2>=256**2 and
                        (vb[0]-vc[0])**2+(vb[1]-vc[1])**2>=256**2):
                        qualifying.append(tuple(sorted([va,vb,vc])))
    if not qualifying:return 0,None
    qualifying.sort()
    return 15,qualifying[0]


def treasure_bastion_bonus_v2(bastions,center,get_variant_fn):
    nb=nether_bounds(center)
    captured=[tuple(p) for p in bastions if contains(p,nb)]
    treasure=[]
    for p in captured:
        var=get_variant_fn(p[0],p[1])
        if var==2:treasure.append(p)
    return (15 if treasure else 0),treasure


class PaletteIndex:
    """Independent prefix counts over the fixed macro lattice for cheap windows."""
    def __init__(self,sampler,policy,v2=False):
        import numpy as np
        from ..backend import biome_name
        from .biomes import canonical
        from .blueprint import PALETTE,CAVE_FAMILIES,DYNAMIC_LUXURIES,DYNAMIC_V2_LUXURIES
        from .sampling import grid_points
        self.np=np
        self.v2=v2
        luxuries_table=DYNAMIC_V2_LUXURIES if v2 else DYNAMIC_LUXURIES
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
                for i,(_,members) in enumerate(luxuries_table):masks[13+i]=np.isin(names,members)
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
        from .blueprint import DYNAMIC_LUXURIES,DYNAMIC_V2_LUXURIES
        table=DYNAMIC_V2_LUXURIES if self.v2 else DYNAMIC_LUXURIES
        return [members[0] for count,(_,members) in zip(self.window(center)[13:],table) if count]

    def scenic_pair(self,center):
        return scenic_pair_bonus_v2(self.surface,center)
