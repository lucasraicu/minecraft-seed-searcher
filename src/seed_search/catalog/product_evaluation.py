"""Exact finite public predicates over source-bound observations, never terrain."""
from fractions import Fraction
from itertools import combinations, product
import json
import time

from .geometry import contains, distance2, inside
from .models import world_id
from .products import launch_definitions
from .registry import CONTRACT_ROOT, FEATURE_BY_ID_V2, digest

DEFINITIONS=launch_definitions()
FAMILIES=json.loads((CONTRACT_ROOT.parent/'v2'/'biome_families.json').read_text())


def numeric(value):
    """JSON-preserving exact rational; ledger compares its numeric value."""
    value=Fraction(value)
    return value.numerator if value.denominator==1 else dict(numerator=value.numerator,denominator=value.denominator)


def minimum_circle(points):
    """Minimum enclosing circle of a small distinct group, with exact boundaries."""
    pts=tuple(sorted(set(tuple(p) for p in points)))
    if not 1<=len(pts)<=4:raise ValueError('Circle needs one to four distinct points')
    candidates=[(Fraction(x),Fraction(z)) for x,z in pts]
    candidates += [(Fraction(a[0]+b[0],2),Fraction(a[1]+b[1],2)) for a,b in combinations(pts,2)]
    for (ax,az),(bx,bz),(cx,cz) in combinations(pts,3):
        den=2*(ax*(bz-cz)+bx*(cz-az)+cx*(az-bz))
        if not den:continue
        aa=ax*ax+az*az;bb=bx*bx+bz*bz;cc=cx*cx+cz*cz
        candidates.append((Fraction(aa*(bz-cz)+bb*(cz-az)+cc*(az-bz),den),
                           Fraction(aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax),den)))
    return min((max((x-cx)**2+(z-cz)**2 for x,z in pts),cx,cz) for cx,cz in candidates)


def spawn_reference(obs,dimension):
    found=[a for a in obs['anchors'] if a['mode']=='world_spawn_estimated']
    if not found:return None
    if len(found)!=1:raise ValueError('Ambiguous estimated spawn')
    anchor=found[0]
    x,z=anchor['coordinate']
    return dict(mode='world_spawn_estimated',overworld=[x,z],nether=[x//8,z//8],
                source_id=anchor['source_id'],dimension=dimension,
                coordinate=[x//8,z//8] if dimension=='nether' else [x,z],
                nether_reference='projected_overworld_anchor_nether')


def complete_scope(obs,feature,anchor,radius):
    cov=obs['coverage'].get(feature,{})
    box=[anchor[0]-radius,anchor[1]-radius,anchor[0]+radius+1,anchor[1]+radius+1]
    return cov.get('status')=='complete' and contains(cov.get('bounds',()),box)


def structure_points(obs,feature,anchor,radius):
    return sorted((tuple(p) for p in obs['structures'].get(feature,[]) if
                   distance2(*p,anchor)<=radius*radius),
                  key=lambda p:(distance2(*p,anchor),*p))


def biome_points(obs,family,dimension,anchor,radius,*,record=False):
    members=set(FAMILIES['record_families' if record else 'features'][family])
    levels=((-48,0) if family in FAMILIES['cave_families'] else (63,160)) if record else ((64,) if dimension=='nether' else (63,))
    return sorted((tuple(p) for p in obs['biomes'][dimension]
                   if p[1] in levels and obs['biome_names'].get(str(p[3])) in members
                   and distance2(p[0],p[2],anchor)<=radius*radius),
                  key=lambda p:(distance2(p[0],p[2],anchor),*p))


def witness(obs,feature,point,anchor,dimension,oid):
    if len(point)==2:
        coordinate=[point[0],None,point[1]]
        method=obs['coverage'].get(feature,{}).get('method_id','unknown')
    else:
        coordinate=list(point[:3]);method='procedural_model_v1'
    body=dict(feature=feature,dimension=dimension,coordinate=coordinate,
              observation_id=oid,provider=method)
    return dict(body,witness_id=digest(body),distance_squared=distance2(coordinate[0],coordinate[2],anchor))


def _base(obs,p,oid,ref):
    return dict(product_id=p['id'],world_id=world_id(obs['identity']),seed=obs['identity']['seed'],
        observation_id=oid,status='pending',rank=None,anchor=ref,witnesses=[],metric=None,
        reason='estimated_spawn_unavailable' if ref is None else 'missing_evidence',
        scope=dict(dimension=p.get('dimension','overworld'),radius=p.get('radius')))


def _match(row,rank,witnesses,metric=None):
    def encoded(v):
        if isinstance(v,Fraction):return numeric(v)
        if type(v) is float:
            if v.is_integer():return int(v)
            return dict(decimal=str(v))
        return v
    row.update(status='match',rank=[encoded(v) for v in rank],
               witnesses=witnesses,metric=metric,reason=None)
    return row


def _preset(obs,p,oid):
    ref=spawn_reference(obs,p['dimension']);row=_base(obs,p,oid,ref)
    if ref is None:return row
    a=ref['coordinate'];r=p['radius'];ws=[]
    for feature,n in p['structures'].items():
        points=structure_points(obs,feature,a,r)
        if len(points)<n:
            if complete_scope(obs,feature,a,r):row.update(status='no_match',reason='structure_requirement_not_met')
            return row
        ws.extend(witness(obs,feature,pt,a,p['dimension'],oid) for pt in points[:n])
    for family in p['biomes']:
        points=biome_points(obs,family,p['dimension'],a,r)
        if not points:return row
        ws.append(witness(obs,'biome.'+family,points[0],a,p['dimension'],oid))
    distances=[w['distance_squared'] for w in ws]
    return _match(row,[max(distances),sum(distances)],ws,
                  dict(farthest_witness_d2=max(distances),ranking='saved_witness_compactness'))


class EvaluationBudget(TimeoutError):pass


def _cluster(obs,p,oid,ref,deadline):
    a=ref['coordinate'];radius=p['radius'];kind=p['kind'];best=None
    operations=0
    def step():
        nonlocal operations
        operations+=1
        if operations>1_000_000 or (operations%32==0 and time.monotonic()>=deadline):
            raise EvaluationBudget('Bounded cluster evaluation exhausted')
    def offer(rank,group,center=None):
        nonlocal best
        canonical=tuple(sorted((f,*pt) for f,pt in group))
        key=(*rank,canonical)
        if best is None or key<best[0]:best=(key,rank,group,center)
    if kind=='four_types':
        points=[(f,pt) for f,definition in FEATURE_BY_ID_V2.items()
                if definition['kind']=='structure_count' and definition['dimension']=='overworld'
                for pt in structure_points(obs,f,a,radius)]
        # Exact cliques in the 100-block neighbor graph avoid enumerating all C(n,4).
        buckets={}
        for i,(_,pt) in enumerate(points):buckets.setdefault((pt[0]//100,pt[1]//100),[]).append(i)
        edges=[set() for _ in points]
        for i,(feature,pt) in enumerate(points):
            bx,bz=pt[0]//100,pt[1]//100
            for dx in (-1,0,1):
                for dz in (-1,0,1):
                    for j in buckets.get((bx+dx,bz+dz),[]):
                        step()
                        if j>i and feature!=points[j][0] and distance2(*pt,points[j][1])<=100**2:edges[i].add(j)
        for i in range(len(points)):
            for j in sorted(edges[i]):
                common=edges[i]&edges[j]
                for k in sorted(common):
                    if len({points[i][0],points[j][0],points[k][0]})<3:continue
                    for n in sorted(common&edges[k]):
                        step();group=[points[t] for t in (i,j,k,n)]
                        if len({f for f,_ in group})!=4:continue
                        ds=[distance2(*x,z) for (_,x),(_,z) in combinations(group,2)]
                        offer((max(ds),sum(ds)),group)
    elif kind in ('four_huts','monument_cluster'):
        f='structure.swamp_hut' if kind=='four_huts' else 'structure.monument'
        pts=structure_points(obs,f,a,radius)
        for n in ((4,) if kind=='four_huts' else (3,2)):
            for group in combinations(pts,n):
                step()
                # Any two points more than a diameter apart cannot share this circle.
                if any(distance2(*x,z)>256**2 for x,z in combinations(group,2)):continue
                r2,cx,cz=minimum_circle(group)
                if r2<=128**2:offer((r2,) if kind=='four_huts' else (-n,r2),[(f,pt) for pt in group],(cx,cz))
    else:
        for x,z in product(structure_points(obs,'structure.fortress',a,radius),
                           structure_points(obs,'structure.bastion',a,radius)):
            step()
            d=distance2(*x,z)
            if d<=64**2:offer((d,),[('structure.fortress',x),('structure.bastion',z)])
    if best is None:return None
    _,rank,group,center=best
    ws=[witness(obs,f,pt,a,p['dimension'],oid) for f,pt in sorted(group)]
    metric=dict(group_size=len(group),geometry='horizontal_predicted_starts')
    if center is not None:metric['candidate_center']=[numeric(c) for c in center]
    return rank,ws,metric


def _record(obs,p,oid,deadline):
    ref=spawn_reference(obs,p['dimension']);row=_base(obs,p,oid,ref)
    if ref is None:return row
    a=ref['coordinate'];r=p['radius'];kind=p['kind']
    if kind in ('density','proximity'):
        feature=p['feature'];points=structure_points(obs,feature,a,r)
        if kind=='density' and not complete_scope(obs,feature,a,r):return row
        if not points:
            if complete_scope(obs,feature,a,r):row.update(status='no_match',reason='no_predicted_starts_in_scope')
            return row
        chosen=points if kind=='density' else points[:1]
        ws=[witness(obs,feature,pt,a,p['dimension'],oid) for pt in chosen]
        rank=[-len(points)] if kind=='density' else [ws[0]['distance_squared']]
        return _match(row,rank,ws,dict(count=len(points),count_complete=complete_scope(obs,feature,a,r)))
    if kind=='biome_sampler':
        ws=[]
        for family in FAMILIES['record_families']:
            pts=biome_points(obs,family,'overworld',a,r,record=True)
            if not pts:return row
            ws.append(witness(obs,'realm.biome.'+family,pts[0],a,'overworld',oid))
        ds=[w['distance_squared'] for w in ws]
        return _match(row,[max(ds),sum(ds)],ws,dict(families=14,ranking='saved_witness_compactness'))
    try:match=_cluster(obs,p,oid,ref,deadline)
    except EvaluationBudget:
        row['reason']='evaluation_budget_exhausted';return row
    return _match(row,*match) if match else row


def _realm(obs,oid):
    from ..realm.config import dynamic_v3_blueprint_config
    p=DEFINITIONS['realm'];row=_base(obs,p,oid,None)
    realm=obs.get('realm')
    if not realm:return row
    if realm.get('config_digest')!=digest(dynamic_v3_blueprint_config()):
        row['reason']='realm_configuration_mismatch';return row
    anchors=realm.get('evaluation',{}).get('anchors',[])
    candidates=[a for a in anchors if a.get('qualification')=='PREDICTED' and
                a.get('baseline_score_complete') is True and a.get('baseline_score') is not None]
    if not candidates:
        if realm.get('evaluation',{}).get('execution_complete'):
            row.update(status='no_match',reason='realm_blueprint_not_qualified')
        return row
    chosen=min(candidates,key=lambda a:(-a['baseline_score'],a['evaluation_center']))
    center=list(chosen['evaluation_center'])
    ref=dict(mode='realm_qualified_center',coordinate=center,overworld=center,
             nether=[v//8 for v in center],nether_reference='projected_overworld_anchor_nether')
    row['anchor']=ref
    components=chosen.get('ranking',{}).get('components',{})
    luxury=components.get('luxury_biomes');nether=None
    inventory=chosen.get('required_nether_structures',{})
    counts={name:inventory.get(name,{}).get('predicted_count') for name in ('fortress','bastion')}
    if all(type(n) is int and n>=0 for n in counts.values()) and all(type(components.get(k)) is int for k in ('nether_core_bonus','treasure_bastion_bonus')):
        from ..realm.blueprint import dynamic_v3_score
        nether=dynamic_v3_score(counts,nether_core=components['nether_core_bonus'],treasure_bastion=bool(components['treasure_bastion_bonus']))[0]
    groups=dict(luxury_biomes=luxury,nether=nether,overworld=chosen['baseline_score']-luxury-nether if type(luxury) is int and nether is not None else None)
    return _match(row,[-chosen['baseline_score']],[],dict(score=chosen['baseline_score'],group_scores=groups,
        qualifying_core=2048,nether_core=1024,outer_borders=[2048],calibration_pending=[4096,8192],
        config_digest=realm['config_digest'],components=chosen.get('ranking',{}).get('components',{})))


def evaluate_products(observation,*,seconds=5):
    """Launch predicates and gated size boards, with explicit pending evidence."""
    from .models import validate_observation_v2
    if type(seconds) not in (int,float) or not 0<seconds<=30:raise ValueError('Evaluation allowance must be positive and <=30s')
    deadline=time.monotonic()+seconds
    obs=validate_observation_v2(observation);oid=digest(obs)
    rows=[_realm(obs,oid)]
    rows += [_large_realm(obs,p,oid) for p in DEFINITIONS.get('realm_sizes',[])]
    rows += [_preset(obs,p,oid) for p in DEFINITIONS['presets']]
    for p in DEFINITIONS['records']:
        if time.monotonic()>=deadline:
            row=_base(obs,p,oid,spawn_reference(obs,p['dimension']));row['reason']='evaluation_budget_exhausted'
            rows.append(row)
        else:rows.append(_record(obs,p,oid,deadline))
    return rows


def _large_realm(obs,p,oid):
    from .realm_evaluation import load_calibration
    calibration=load_calibration();row=_base(obs,p,oid,None)
    row['reason']='size_calibration_pending'
    if calibration is None:return row
    realm=obs.get('realm') or {};evidence=realm.get('larger_sizes',{})
    if (evidence.get('calibration_id')!=digest(calibration) or realm.get('native_pin')!=calibration['native_realm_pin']
            or dict(obs['identity'],seed='0')!=calibration['source_identity']):
        row['reason']='size_calibration_source_mismatch';return row
    result=evidence.get('sizes',{}).get(str(p['overworld_core']))
    if not isinstance(result,dict):return row
    if result.get('status')!='match':
        row.update(status='pending' if result.get('search_budget_exhausted') else result.get('status','pending'),
                   reason='supported_center_budget' if result.get('search_budget_exhausted') else 'no_qualifying_supported_center')
        return row
    center=result.get('center');score=result.get('score');groups=result.get('group_scores',{})
    if (not isinstance(center,list) or len(center)!=2 or any(type(n) is not int or not -1024<=n<=1024 for n in center)
            or type(score) is not int or not 0<=score<=1250 or result.get('score_complete') is not True
            or set(groups)!={'overworld','luxury_biomes','nether'}
            or any(type(groups[name]) is not int or not 0<=groups[name]<=cap for name,cap in [('overworld',845),('luxury_biomes',265),('nether',140)])
            or sum(groups.values())!=score):raise ValueError('Invalid calibrated Realm score evidence')
    row['anchor']=dict(mode='realm_calibrated_center',coordinate=center,overworld=center,
        nether=[n//8 for n in center],nether_reference='projected_overworld_anchor_nether')
    return _match(row,[-score],[],dict(score=score,group_scores=groups,qualifying_core=p['overworld_core'],
        nether_core=1024,calibration_id=digest(calibration),components=result.get('components'),
        floors=result.get('floors'),counts=result.get('counts'),candidate_policy=evidence.get('candidate_policy'),
        candidates_evaluated=result.get('candidates_evaluated'),search_budget_exhausted=result.get('search_budget_exhausted')))


def product_offers(evaluations):
    return [dict(objective_id=e['product_id'],rank=e['rank'],member=e)
            for e in evaluations if e['status']=='match']
