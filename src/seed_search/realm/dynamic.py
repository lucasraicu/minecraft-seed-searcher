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

OVERWORLD_HALF_V3=1024
NETHER_HALF_V3=512
MIN_CENTER_V3=-976
MAX_CENTER_V3=976

DENSITY_NAMES=('village','trial_chamber','ancient_city','desert_pyramid',
               'jungle_temple','outpost')
OVERWORLD_NAMES=('stronghold','mansion','village','trial_chamber','ancient_city',
                 'desert_pyramid','jungle_temple','monument','ruined_portal',
                 'shipwreck','mineshaft','outpost')
OVERWORLD_NAMES_V3=('stronghold','mansion','village','trial_chamber','ancient_city',
                    'desert_pyramid','monument','ruined_portal',
                    'shipwreck','mineshaft','outpost')
NETHER_NAMES=('fortress','bastion')
OPTIONAL_NAMES=('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')
OPTIONAL_NAMES_V3=('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure','jungle_temple')
CENTROID_WEIGHTS={'village':3,'trial_chamber':2,'ruined_portal':2,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':1}
DYNAMIC_V2_CENTROID_WEIGHTS={'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':0}
DYNAMIC_V3_CENTROID_WEIGHTS={'village':2,'trial_chamber':1,'ruined_portal':0,'ancient_city':2,'outpost':1,'desert_pyramid':2,'jungle_temple':2,'mansion':2,'monument':1,'stronghold':3,'shipwreck':0}
NETHER_BIOMES=('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas')


def overworld_bounds(center, overworld_half=None):
    half = OVERWORLD_HALF if overworld_half is None else overworld_half
    x,z=center
    return x-half,z-half,x+half,z+half


def nether_bounds(center, nether_half=None):
    """Exact rational center/8; return inclusive lower and exclusive upper ints."""
    half = NETHER_HALF if nether_half is None else nether_half
    x,z=center
    return ((x-8*half+7)//8,(z-8*half+7)//8,
            (x+8*half+7)//8,(z+8*half+7)//8)


def _axis_events(points,half,nether=False,min_c=MIN_CENTER,max_c=MAX_CENTER):
    events={min_c,max_c+1}
    for value in points:
        if nether:
            lo=8*(value-half)+1
            hi=8*(value+half)+1
        else:
            lo=value-half+1
            hi=value+half+1
        if min_c<lo<=max_c:events.add(lo)
        if min_c<hi<=max_c:events.add(hi)
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


def candidate_centers(inventories, floors, ideals, weights, max_misses=2, centroid_weights=None,
                      overworld_half=None, nether_half=None):
    """Yield all floor/budget-eligible equivalence cells in exact density order.

    ``inventories`` are complete, viable macro-envelope coordinates. The
    mansion list must already be filtered to Dark Forest starts at Y=63.
    Biome lattice events are included here; a palette check on the returned
    representative therefore applies to the entire event rectangle.
    """
    cw = centroid_weights if centroid_weights is not None else CENTROID_WEIGHTS
    ow_half = OVERWORLD_HALF if overworld_half is None else overworld_half
    nw_half = NETHER_HALF if nether_half is None else nether_half
    min_c = -2000 + ow_half
    max_c = 2000 - ow_half
    lat_events = {v for s in range(-1984, 1985, 64) for v in (s - (ow_half - 1), s + (ow_half + 1))} | \
                 {v for n in range(-((max_c // 8 + nw_half) // 64) * 64, ((max_c // 8 + nw_half) // 64) * 64 + 1, 64)
                  for v in (8 * n - (8 * nw_half - 1), 8 * n + (8 * nw_half + 1))}
    lat_events = {v for v in lat_events if min_c < v <= max_c}
    xs=[];zs=[];nether_x=[];nether_z=[]
    opt_names = OPTIONAL_NAMES_V3 if ow_half == OVERWORLD_HALF_V3 else OPTIONAL_NAMES
    for name,points in inventories.items():
        if name in opt_names:continue
        target_x,target_z=(nether_x,nether_z) if name in NETHER_NAMES else (xs,zs)
        for x,z in points:target_x.append(x);target_z.append(z)
    ex=sorted(set(_axis_events(xs,ow_half,False,min_c,max_c)+_axis_events(nether_x,nw_half,True,min_c,max_c))|lat_events)
    ez=sorted(set(_axis_events(zs,ow_half,False,min_c,max_c)+_axis_events(nether_z,nw_half,True,min_c,max_c))|lat_events)
    rows=[]
    for xi in range(len(ex)-1):
        cx=_nearest_zero(ex[xi],ex[xi+1]-1)
        for zi in range(len(ez)-1):
            cz=_nearest_zero(ez[zi],ez[zi+1]-1)
            center=(cx,cz);ow=overworld_bounds(center,ow_half);nb=nether_bounds(center,nw_half)
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
            s_ow=overworld_bounds(snapped,ow_half)
            c=dict(counts)
            for name in opt_names:
                if name in inventories:c[name]=sum(contains(p,s_ow) for p in inventories[name])
            radial=sum(w*math.hypot(x-snapped[0],z-snapped[1]) for x,z,w in captured)/weight if weight else 0.
            density=sum(weights[name]*c.get(name,0) for name in DENSITY_NAMES)
            rows.append(Candidate(snapped,density,c,deficits,radial))
    rows.sort(key=lambda row:(len(row.deficits),-row.density,row.radial,row.center[0]**2+row.center[1]**2,
                              row.center[0],row.center[1]))
    return rows


def grid_candidate_centers(inventories, floors, ideals, weights, max_misses=0, *,
                           overworld_half=1024, nether_half=512, step=16):
    """Exhaustive bounded finalist oracle; never used by the raw native sweep.

    Step 16 searches all chunk-aligned centers. Step 8 explicitly permits all
    integer Nether centers, independently of the centroid policy's fallback.
    """
    import numpy as np
    if step not in (8,16) or type(step) is not int:raise ValueError('Center grid step must be 8 or 16')
    limit=2000-overworld_half
    axis=np.arange(-(-(-limit)//step)*step,limit+1,step,dtype=np.int64)
    cx,cz=np.meshgrid(axis,axis,indexing='ij')
    centers=np.column_stack((cx.ravel(),cz.ravel()))
    counts={}
    for name,points in inventories.items():
        pts=np.asarray(points,dtype=np.int64).reshape(-1,2)
        scaled=pts*8 if name in NETHER_NAMES else pts
        half=nether_half*8 if name in NETHER_NAMES else overworld_half
        totals=np.zeros(len(centers),dtype=np.int64)
        # Bound temporary arrays even for an unusually large macro inventory.
        for first in range(0,len(pts),64):
            chunk=scaled[first:first+64]
            captured=((chunk[None,:,:]>=centers[:,None,:]-half)&
                      (chunk[None,:,:]<centers[:,None,:]+half)).all(axis=2)
            totals+=captured.sum(axis=1)
        counts[name]=totals
    valid=np.ones(len(centers),dtype=bool)
    for name,floor in floors.items():valid &= counts.get(name,np.zeros(len(centers)))>=floor
    misses=np.zeros(len(centers),dtype=np.int64)
    for name,ideal in ideals.items():misses+=counts.get(name,np.zeros(len(centers)))<ideal
    valid &= misses<=max_misses
    rows=[]
    for i in np.flatnonzero(valid):
        c={name:int(values[i]) for name,values in counts.items()}
        deficit=tuple(name for name,ideal in ideals.items() if c.get(name,0)<ideal)
        density=sum(weight*c.get(name,0) for name,weight in weights.items())
        rows.append(Candidate(tuple(map(int,centers[i])),density,c,deficit))
    return rows


def nether_palette(backend,center,nether_half=None):
    from ..backend import biome_name
    bounds=nether_bounds(center,nether_half)
    x0=-(-bounds[0]//64)*64;z0=-(-bounds[1]//64)*64
    nh=NETHER_HALF if nether_half is None else nether_half
    side=16 if nh==512 else 13
    points=[(x0+x*64,64,z0+z*64) for z in range(side) for x in range(side)]
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


def hub_bonus_v3(structures,center):
    villages=structures.get('village',())
    d2=lambda p:(p[0]-center[0])**2+(p[1]-center[1])**2
    v_hub=15 if any(d2(p)<=256**2 for p in villages) else 10 if any(d2(p)<=512**2 for p in villages) else 0
    other_pts={'desert_pyramid':6,'jungle_temple':6,'outpost':6,'ancient_city':6}
    other_hub=sum(6 for name in other_pts for p in structures.get(name,()) if d2(p)<=512**2)
    other_hub+=sum(4 for p in structures.get('ruined_portal',()) if d2(p)<=512**2)
    return v_hub+min(30,other_hub)


def nether_core_bonus_v3(nether_points,center):
    pnx = center[0] // 8
    pnz = center[1] // 8
    bonus = 0
    d2 = lambda p: (p[0] - pnx)**2 + (p[1] - pnz)**2
    if any(d2(p) <= 256**2 for p in nether_points.get('fortress', ())):
        bonus += 10
    if any(d2(p) <= 256**2 for p in nether_points.get('bastion', ())):
        bonus += 10
    return bonus


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


ORDER_V2_RADIAL = (
    ('stronghold', 1),
    ('mansion', 1),
    ('jungle_temple', 1),
    ('desert_pyramid', 1),
    ('monument', 1),
    ('ancient_city', 2),
    ('village', 3),
    ('trial_chamber', 2),
    ('outpost', 1),
)


def weighted_radial_v2(structures, center, dark_forest_mansions=None, overworld_half=None):
    cx, cz = center
    ow = overworld_bounds(center, overworld_half)
    total_weight = 0
    distance = 0.0
    for name, weight in ORDER_V2_RADIAL:
        pts = structures.get(name, ())
        for p in pts:
            x, z = p[0], p[1]
            if name == 'mansion' and dark_forest_mansions is not None and (x, z) not in dark_forest_mansions:
                continue
            if contains((x, z), ow):
                total_weight += weight
                distance += weight * math.hypot(x - cx, z - cz)
    return distance / total_weight if total_weight else 0.0


ORDER_V3_RADIAL = (
    ('stronghold', 3),
    ('mansion', 2),
    ('jungle_temple', 2),
    ('desert_pyramid', 2),
    ('monument', 1),
    ('ancient_city', 2),
    ('village', 2),
    ('trial_chamber', 1),
    ('outpost', 1),
)


def weighted_radial_v3(structures, center, dark_forest_mansions=None, overworld_half=None):
    cx, cz = center
    ow = overworld_bounds(center, overworld_half)
    total_weight = 0
    distance = 0.0
    for name, weight in ORDER_V3_RADIAL:
        pts = structures.get(name, ())
        for p in pts:
            x, z = p[0], p[1]
            if name == 'mansion' and dark_forest_mansions is not None and (x, z) not in dark_forest_mansions:
                continue
            if contains((x, z), ow):
                total_weight += weight
                distance += weight * math.hypot(x - cx, z - cz)
    return distance / total_weight if total_weight else 0.0


SCENIC_BIOMES=frozenset(('plains','sunflower_plains','meadow','cherry_grove'))
RIVER_OFFSETS=sorted([(dix,diz) for dix in range(-2,3) for diz in range(-2,3) if dix*dix+diz*diz<=4],
                     key=lambda o:(o[0],o[1]))


def scenic_pair_bonus_v2(surface_grid,center,overworld_half=None):
    """Exact scenic river pairing on the 64-block grid; surface_grid is 63x63 names at Y=63."""
    cx,cz=center
    ow=overworld_bounds(center,overworld_half)
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


def retained_scenic_pair_v2(samples, center, overworld_half=None):
    """Recompute the pair from a complete retained selected-window surface grid."""
    from .biomes import canonical
    grid = {}
    ow = overworld_bounds(center, overworld_half)
    for row in samples:
        x, y, z = row['coordinate']
        if y == 63 and x % 64 == 0 and z % 64 == 0 and contains((x, z), ow):
            grid[((z + 1984) // 64, (x + 1984) // 64)] = canonical(row['biome'])
    for x in range(-(-ow[0] // 64) * 64, ow[2], 64):
        for z in range(-(-ow[1] // 64) * 64, ow[3], 64):
            if ((z + 1984) // 64, (x + 1984) // 64) not in grid:
                raise ValueError('Incomplete retained Y=63 evidence; re-evaluate this seed before rescoring')
    return scenic_pair_bonus_v2(grid, center, overworld_half)


def village_spread_bonus_v2(villages,center,overworld_half=None):
    cx,cz=center
    ow=overworld_bounds(center,overworld_half)
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


def treasure_bastion_bonus_v2(bastions,center,get_variant_fn,nether_half=None):
    nb=nether_bounds(center,nether_half)
    captured=[tuple(p) for p in bastions if contains(p,nb)]
    variants=[]
    for p in captured:
        var=get_variant_fn(p[0],p[1])
        if var<0:
            raise RuntimeError(f'Bastion variant prediction failed at {p}: code {var}')
        variants.append((p[0],p[1],var))
    has_treasure=any(var==2 for _,_,var in variants)
    return (15 if has_treasure else 0),variants


class PaletteIndex:
    """Independent prefix counts over the fixed macro lattice for cheap windows."""
    def __init__(self,sampler,policy,v2=False,overworld_half=None,nether_half=None):
        import numpy as np
        from ..backend import biome_name
        from .biomes import canonical
        from .blueprint import PALETTE,CAVE_FAMILIES,DYNAMIC_LUXURIES,DYNAMIC_V2_LUXURIES
        from .sampling import grid_points
        self.np=np
        self.v2=v2
        self.ow_half = policy.get('overworld_half', OVERWORLD_HALF if overworld_half is None else overworld_half)
        self.nw_half = policy.get('nether_half', NETHER_HALF if nether_half is None else nether_half)
        self.required_indices=[i for i,f in enumerate(PALETTE) if f in policy['required_families']]
        luxuries_table=DYNAMIC_V2_LUXURIES if v2 else DYNAMIC_LUXURIES
        masks=np.zeros((23,63,63),dtype=np.int32)
        for y in policy['sample_y_levels']:
            points=grid_points((-2000,-2000,2000,2000),64,y,'world')
            values=sampler.sample(points)
            names=np.array([canonical(biome_name(int(v))) for v in values]).reshape(63,63)
            for i,family in enumerate(PALETTE):
                if y in ((-48,0) if family in CAVE_FAMILIES else (63,160)):
                    members=PALETTE[family]|({'frozen_peaks'} if family=='peaks' and policy.get('include_frozen_peaks') else set())
                    masks[i]|=np.isin(names,list(members))
            if y==63:
                self.surface=names
                for i,(_,members) in enumerate(luxuries_table):masks[13+i]=np.isin(names,members)
        self.prefix=np.pad(masks,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)
        nw_bound = 640 if self.nw_half == 512 else 512
        points=grid_points((-nw_bound,-nw_bound,nw_bound+1,nw_bound+1),64,64,'world')
        values=sampler.sample(points,dimension=-1)
        grid_side = (2 * nw_bound) // 64 + 1
        names=np.array([biome_name(int(v)) for v in values]).reshape(grid_side,grid_side)
        mask=np.array([names==name for name in NETHER_BIOMES],dtype=np.int32)
        self.nether=np.pad(mask,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)

    @staticmethod
    def counts(prefix,x0,z0,x1,z1):
        return prefix[:,z1,x1]-prefix[:,z0,x1]-prefix[:,z1,x0]+prefix[:,z0,x0]

    def window(self,center):
        x,z=center
        return self.counts(self.prefix,-(-(x-self.ow_half+1984)//64),-(-(z-self.ow_half+1984)//64),
                           -(-(x+self.ow_half+1984)//64),-(-(z+self.ow_half+1984)//64))

    def valid(self,center):
        x,z=center
        half_span = 8 * self.nw_half
        grid_min = -640 if self.nw_half == 512 else -512
        grid_offset = -grid_min * 8
        return bool(self.np.all(self.window(center)[self.required_indices]>0) and self.np.all(self.counts(self.nether,
            -(-(x-half_span+grid_offset)//512),-(-(z-half_span+grid_offset)//512),
            -(-(x+half_span+grid_offset)//512),-(-(z+half_span+grid_offset)//512))>0))

    def luxuries(self,center):
        from .blueprint import DYNAMIC_LUXURIES,DYNAMIC_V2_LUXURIES
        table=DYNAMIC_V2_LUXURIES if self.v2 else DYNAMIC_LUXURIES
        return [members[0] for count,(_,members) in zip(self.window(center)[13:],table) if count]

    def scenic_pair(self,center):
        return scenic_pair_bonus_v2(self.surface,center,overworld_half=self.ow_half)
