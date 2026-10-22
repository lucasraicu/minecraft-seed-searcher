"""Bounded larger-world Realm evaluation over shared saved predictor observations."""
from bisect import bisect_left
from collections import defaultdict
from itertools import combinations
import json
import math
import time

from .geometry import contains,inside,anchors
from .registry import CONTRACT_ROOT,digest


class EvaluationBudget(TimeoutError):pass


def load_calibration():
    path=CONTRACT_ROOT.parent/'v2'/'realm_calibration.json'
    from .ingestion import strict_json_loads
    if not path.is_file():return None
    if path.stat().st_size>1<<20:raise ValueError('Calibration artifact cap')
    value=strict_json_loads(path.read_bytes())
    if value.get('revision')!='catalog-realm-calibration-v1':raise ValueError('Unknown calibration revision')
    if value.get('budgets')!={'total':1250,'overworld':845,'luxury_biomes':265,'nether':140}:
        raise ValueError('Calibration changed frozen score budgets')
    return value if value.get('status')=='active' else None


def _box(center,half):return (center[0]-half,center[1]-half,center[0]+half,center[1]+half)


class BiomeIndex:
    """Presence/coverage prefix sums preserve the exact declared world lattice."""
    def __init__(self,obs):
        import numpy as np
        from ..realm.blueprint import PALETTE,CAVE_FAMILIES,DYNAMIC_V3_LUXURIES
        self.obs=obs;self.prefix={};self.axes={};self.coverage={};self.surface=defaultdict(lambda:'unknown')
        families=list(PALETTE.items())
        self.required=[name for name,_ in families];self.luxuries=DYNAMIC_V3_LUXURIES
        for dimension,levels in [('overworld',(-48,0,63,160)),('nether',(64,))]:
            bounds=obs['bounds'][dimension]
            xs=list(range(-(-bounds[0]//64)*64,bounds[2],64));zs=list(range(-(-bounds[1]//64)*64,bounds[3],64));self.axes[dimension]=(xs,zs)
            raw=np.full((len(levels),len(zs),len(xs)),-1,dtype=np.int32)
            for x,y,z,bid in obs['biomes'][dimension]:
                if xs and zs and y in levels and x%64==0 and z%64==0:
                    raw[levels.index(y),(z-zs[0])//64,(x-xs[0])//64]=bid
                    if dimension=='overworld' and y==63:self.surface[((z+1984)//64,(x+1984)//64)]=obs['biome_names'].get(str(bid),'unknown')
            masks=[];labels=[]
            if dimension=='overworld':
                for name,members in families:
                    ys=(-48,0) if name in CAVE_FAMILIES else (63,160)
                    ids=[int(bid) for bid,label in obs['biome_names'].items() if label in members]
                    masks.append(np.isin(raw[[levels.index(y) for y in ys]],ids).any(axis=0));labels.append(name)
                for i,(_,members) in enumerate(self.luxuries):
                    ids=[int(bid) for bid,label in obs['biome_names'].items() if label in members]
                    masks.append(np.isin(raw[levels.index(63)],ids));labels.append('luxury.'+str(i))
            else:
                for name in ('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas'):
                    ids=[int(bid) for bid,label in obs['biome_names'].items() if label==name]
                    masks.append(np.isin(raw[0],ids));labels.append(name)
            arrays=np.asarray(masks,dtype=np.int32)
            self.prefix[dimension]=(labels,np.pad(arrays,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2))
            known_ids=[int(bid) for bid,name in obs['biome_names'].items() if not name.startswith('unknown')]
            self.coverage[dimension]=np.pad(np.isin(raw,known_ids).astype(np.int32),((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)

    def _window(self,dimension,box):
        xs,zs=self.axes[dimension]
        return bisect_left(xs,box[0]),bisect_left(zs,box[1]),bisect_left(xs,box[2]),bisect_left(zs,box[3])

    def counts(self,dimension,box):
        labels,prefix=self.prefix[dimension];x0,z0,x1,z1=self._window(dimension,box)
        values=prefix[:,z1,x1]-prefix[:,z0,x1]-prefix[:,z1,x0]+prefix[:,z0,x0]
        return dict(zip(labels,map(int,values)))

    def complete(self,dimension,box):
        if not contains(self.obs['bounds'][dimension],box):return False
        x0,z0,x1,z1=self._window(dimension,box);p=self.coverage[dimension]
        counts=p[:,z1,x1]-p[:,z0,x1]-p[:,z1,x0]+p[:,z0,x0]
        return bool((counts==(x1-x0)*(z1-z0)).all())


class RealmScene:
    def __init__(self,obs,calibration):
        import numpy as np
        self.obs=obs;self.calibration=calibration;self.biomes=BiomeIndex(obs)
        self.points={f.removeprefix('structure.'):np.array(points,dtype=np.int64).reshape(-1,2) for f,points in obs['structures'].items()}
        self.aux=(obs.get('realm') or {}).get('inventory',{})
        for name in ('ocean_ruin','buried_treasure','igloo_basement'):
            self.points[name]=np.array(self.aux.get(name,{}).get('points',[]),dtype=np.int64).reshape(-1,2)
        self.variants={(x,z):variant for x,z,variant in self.aux.get('bastion_variant',{}).get('points',[])}

    def captured(self,name,box):
        points=self.points.get(name)
        if points is None:return []
        selected=points[(points[:,0]>=box[0])&(points[:,0]<box[2])&(points[:,1]>=box[1])&(points[:,1]<box[3])]
        return [tuple(map(int,p)) for p in selected]

    def complete(self,name,box):
        if name in self.aux:entry=self.aux[name]
        else:entry=self.obs['coverage'].get('structure.'+name,{})
        # The stronghold list is deliberately a bounded predictor domain, never proof of absence.
        bounded=name=='stronghold' and entry.get('status')=='partial' and entry.get('method_id')=='predictor_bounded_strongholds_v2'
        return (entry.get('status')=='complete' or bounded) and len(entry.get('bounds',()))==4 and contains(entry['bounds'],box)

    @staticmethod
    def _spread(villages,center,deadline):
        villages=sorted(villages)
        quadrant=lambda p:(p[0]>=center[0],p[1]>=center[1])
        if len({quadrant(p) for p in villages})<3:return False,None
        # A qualifying triple is a triangle of separated, different-quadrant
        # villages. Pair pruning avoids enumerating every possible triple.
        edges={i:set() for i in range(len(villages))}
        for work,(i,j) in enumerate(combinations(range(len(villages)),2)):
            if work%128==0 and (work>100000 or time.monotonic()>=deadline):raise EvaluationBudget('Village spread work cap')
            a,b=villages[i],villages[j]
            if quadrant(a)!=quadrant(b) and (a[0]-b[0])**2+(a[1]-b[1])**2>=256**2:
                edges[i].add(j);edges[j].add(i)
        for i in range(len(villages)):
            for j in sorted(n for n in edges[i] if n>i):
                common=[n for n in edges[i]&edges[j] if n>j]
                if common:return True,(villages[i],villages[j],villages[min(common)])
        return False,None

    def evaluate(self,center,side,deadline):
        from .calibration import map_count
        from ..realm.blueprint import dynamic_v3_score
        from ..realm.config import dynamic_v3_blueprint_config
        from ..realm.dynamic import hub_bonus_v3,nether_core_bonus_v3,scenic_pair_bonus_v2
        table=self.calibration['thresholds']['sizes'][str(side)]
        ow=_box(center,side//2);nether_center=[n//8 for n in center];nw=_box(nether_center,512)
        if not contains(self.obs['bounds']['overworld'],ow) or not contains(self.obs['bounds']['nether'],nw):
            return dict(status='pending',reason='survey_bounds',center=list(center),score=0,missing=99,shortfall=999999)
        names=set(table)|{'fortress','bastion'}
        captured={name:self.captured(name,nw if name in ('fortress','bastion') else ow) for name in names}
        counts={name:len(points) for name,points in captured.items()}
        if 'igloo_basement' in self.points:
            counts['igloo']=len(self.captured('igloo_basement',ow))
        floors={name:entry['thresholds'][0] for name,entry in table.items() if entry['base_levels'][0]>0}
        floors.update(fortress=1,bastion=2)
        deficits=[name for name,floor in floors.items() if counts.get(name,0)<floor]
        palette=self.biomes.counts('overworld',ow);npalette=self.biomes.counts('nether',nw)
        cfg=dynamic_v3_blueprint_config();missing_ow=[f for f in cfg['biomes']['required_families'] if not palette.get(f)]
        missing_nether=[f for f in cfg['biomes']['nether_required'] if not npalette.get(f)]
        complete=all(self.complete(name,ow if name not in ('fortress','bastion','bastion_variant') else nw) for name in names|{'igloo_basement','bastion_variant'})
        complete=complete and self.biomes.complete('overworld',ow) and self.biomes.complete('nether',nw)
        normalized={name:map_count(counts[name],entry) for name,entry in table.items()}
        normalized.update(fortress=counts['fortress'],bastion=counts['bastion'])
        luxury=self.biomes.counts('overworld',ow)
        luxury_names=[members[0] for i,(_,members) in enumerate(self.biomes.luxuries) if luxury['luxury.'+str(i)]]
        local={name:self.captured(name,_box(center,1024)) for name in ('village','desert_pyramid','jungle_temple','outpost','ancient_city','ruined_portal')}
        hub=hub_bonus_v3(local,center);nether_core=nether_core_bonus_v3(captured,center)
        scenic=bool(scenic_pair_bonus_v2(self.biomes.surface,center,overworld_half=1024)[0])
        spread,spread_witness=self._spread(captured.get('village',[]),center,deadline)
        treasure=any(self.variants.get(point)==2 for point in captured['bastion'])
        score,components,_=dynamic_v3_score(normalized,luxury_names,hub=hub,nether_core=nether_core,scenic=scenic,village_spread=spread,treasure_bastion=treasure)
        nether_points=dynamic_v3_score({name:counts[name] for name in ('fortress','bastion')},nether_core=nether_core,treasure_bastion=treasure)[0]
        groups=dict(overworld=score-components['luxury_biomes']-nether_points,luxury_biomes=components['luxury_biomes'],nether=nether_points)
        if score>1250 or any(groups[name]>maximum for name,maximum in [('overworld',845),('luxury_biomes',265),('nether',140)]):raise ValueError('Frozen score budget violated')
        return dict(status=('match' if not deficits and not missing_ow and not missing_nether else 'no_match') if complete else 'pending',
            reason=None if complete else 'incomplete_predictor_inventory',center=list(center),score=score,score_complete=bool(complete),
            counts=counts,floors=floors,missing=len(deficits)+len(missing_ow)+len(missing_nether),
            shortfall=sum(max(0,floor-counts.get(name,0)) for name,floor in floors.items()),
            missing_structures=deficits,missing_overworld_biomes=missing_ow,missing_nether_biomes=missing_nether,
            components=components,group_scores=groups,spread_witness=spread_witness)

    def axis_events(self,center,side,axis):
        result=set();half=side//2
        for name,points in self.points.items():
            for p in points:
                value=int(p[axis]);limits=(8*(value-511),8*(value+513)) if name in ('fortress','bastion') else (value-half+1,value+half+1)
                for edge in limits:
                    if -1024<=edge<=1024 and abs(edge-center[axis])<=256:
                        # Supported refinement uses the existing eight-block center lattice.
                        result.update((max(-1024,min(1024,(edge//8)*8)),max(-1024,min(1024,-(-edge//8)*8))))
        result.update(v for v in range(max(-1024,center[axis]-256),min(1024,center[axis]+256)+1,64))
        return sorted(result,key=lambda n:(abs(n-center[axis]),n))


def evaluate_large_realms(obs,calibration=None,*,max_centers=1024,seconds=5):
    """Exact predicates at bounded candidate centers, without a global-best claim."""
    if type(max_centers) is not int or not 81<=max_centers<=4096 or type(seconds) not in (int,float) or not 0<seconds<=30:raise ValueError('Invalid public center allowance')
    calibration=load_calibration() if calibration is None else calibration
    if calibration is None:return dict(revision='catalog-large-realm-evaluation-v1',status='calibration_pending',sizes={})
    started=time.monotonic();scene=RealmScene(obs,calibration)
    remaining=max(0,seconds-(time.monotonic()-started));per_size=remaining/2
    result=dict(revision='catalog-large-realm-evaluation-v1',calibration_id=digest(calibration),candidate_policy='grid81-plus-coordinate-events-v1',
        domain=[-1024,-1024,1024,1024],center_step=8,luxury_side='selected_overworld',nether_side=1024,sizes={})
    for side in (4096,8192):
        deadline=time.monotonic()+per_size
        evaluated={};exhausted=False
        key=lambda row:(row['status']!='match',row.get('missing',99),row.get('shortfall',999999),-row['score'],sum(n*n for n in row['center']),*row['center'])
        def visit(center):
            nonlocal exhausted
            center=tuple(center)
            if center in evaluated:return evaluated[center]
            if len(evaluated)>=max_centers or time.monotonic()>=deadline:exhausted=True;return None
            try:row=scene.evaluate(center,side,deadline)
            except EvaluationBudget:exhausted=True;return None
            evaluated[center]=row;return row
        for center in anchors():
            if visit(center) is None and exhausted:break
        leaders=sorted(evaluated.values(),key=key)[:4]
        for leader in leaders:
            current=leader
            for _ in range(2):
                for axis in (0,1):
                    candidates=[]
                    for value in scene.axis_events(current['center'],side,axis):
                        center=list(current['center']);center[axis]=value
                        row=visit(center)
                        if row is not None:candidates.append(row)
                        if exhausted:break
                    if candidates:current=min([current,*candidates],key=key)
                    if exhausted:break
                if exhausted:break
            if exhausted:break
        best=min(evaluated.values(),key=key) if evaluated else dict(status='pending',reason='center_budget',score=0,center=None)
        result['sizes'][str(side)]=dict(best,candidates_evaluated=len(evaluated),search_budget_exhausted=exhausted)
    result['wall_seconds']=time.monotonic()-started
    return result
