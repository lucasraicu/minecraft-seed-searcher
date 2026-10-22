"""Slow diagnostic oracle: global layout sorting, then unique-world truncation.

Independent of retention.py rank/admission/profile/merge implementations. Uses
only declared registry/policy data and saved summary facts, not the production
engine's predicate helpers. Intended for bounded validation, not serving.
"""
from decimal import Decimal,localcontext
import hashlib
import json
import time
from .registry import POLICY,STRUCTURES,BIOMES,SIDES
from .models import world_id

MISSING=(1<<32)-1


def _profile(row,profile):
    coeff=next(p['coefficients_VTAOEBHR'] for p in POLICY['profiles'] if p['id']==profile)
    groups=((0,),(1,),(2,),(4,12),tuple(range(14)),tuple(range(14,23)),(0,),(7,8,9,10))
    if any(c and not all(row['complete'][s][2] for s in slots) for c,slots in zip(coeff,groups)):return None
    counts=[r[2] for r in row['counts']]
    values=[min(counts[0],6)*120120,min(counts[1],4)*180180,min(counts[2],2)*360360,
        min(counts[4]+counts[12],6)*120120,sum(n>0 for n in counts)*51480,
        min(sum(d!=MISSING and d<=1048576 for d in row['biome_nearest_d2']),8)*90090,0,
        min(sum(counts[i] for i in (7,8,9,10)),4)*180180]
    with localcontext() as ctx:
        ctx.prec=50
        if counts[0] and row['structure_nearest_d2'][0]!=MISSING:
            values[6]=max(Decimal(0),1-Decimal(row['structure_nearest_d2'][0]).sqrt()/1024)*720720
        result=sum(c*v for c,v in zip(coeff,values))
    return -result


def objective_ids():
    ids=[]
    for side in SIDES:
        for mode in ('origin','recommended'):
            for f in STRUCTURES:
                ids.extend(f"structure_count:{f['id']}:{scope}:{side}:{mode}" for scope in range(4))
                ids.append(f"structure_proximity:{f['id']}:{side}:{mode}")
            for f in BIOMES:
                ids.append(f"biome_proximity:{f['id']}:{side}:{mode}")
                for landmark in POLICY['retention']['biome_landmark_pairs']['landmarks']:
                    ids.append(f"biome_landmark_pairs:{f['id']}:{landmark}:{side}:{mode}")
            ids.extend(f"profiles:{p['id']}:{side}:{mode}" for p in POLICY['profiles'])
            ids.extend(f'diversity:{cell}:{profile}:{side}:{mode}' for cell in range(256)
                for profile in POLICY['retention']['diversity']['profiles'])
    return ids+['reference_sample']


def oracle_memberships(layouts,identities,capacities,*,pins=(),deadline=None):
    structures={f['id']:f['slot'] for f in STRUCTURES};biomes={f['id']:f['slot'] for f in BIOMES}
    buckets={(side,mode):[r for r in layouts if r['border_side']==side and (mode=='recommended' or r['anchor']==[0,0])]
        for side in SIDES for mode in ('origin','recommended')}
    profile_cache={};cells={}
    def profile(row,pid):
        key=(row['layout_id'],pid)
        if key not in profile_cache:profile_cache[key]=_profile(row,pid)
        return profile_cache[key]
    bits=POLICY['retention']['diversity']['bits']
    for row in layouts:
        value=0;known=True
        for index,fid in enumerate(bits):
            slot=structures.get(fid,14+biomes.get(fid,-14))
            if not row['complete'][slot][2]:known=False;break
            present=(row['counts'][slot][2]>0 if slot<14 else row['biome_nearest_d2'][slot-14]<=1048576)
            value+=int(present)<<index
        cells[row['layout_id']]=value if known else None
    result={};retained=set(pins)
    for oid in objective_ids():
        if deadline is not None and time.monotonic()>deadline:raise TimeoutError('Retention oracle deadline')
        family=oid.split(':')[0];k=capacities[family]
        if not k:result[oid]=[];continue
        candidates=[]
        if oid=='reference_sample':
            for ident in identities:
                key=[POLICY['retention']['reference_sample']['salt'],ident['edition'],ident['game_build_id'],ident['world_settings_id'],ident['seed']]
                hashed=hashlib.sha256(json.dumps(key,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                wid=world_id(ident)
                # Reference-hash collisions resolve by the declared full identity.
                rank=(hashed,ident['edition'],ident['game_build_id'],ident['world_settings_id'],int(ident['seed'])&((1<<64)-1),wid)
                candidates.append((rank,{'world_id':wid,'layout_id':None,'rank':list(rank)}))
        else:
            fields=oid.split(':');side=int(fields[-2]);mode=fields[-1]
            for row in buckets[(side,mode)]:
                prefix=None
                if family=='structure_count':
                    s=structures[fields[1]];scope=int(fields[2]);n=row['counts'][s][scope]
                    if row['complete'][s][scope] and n:prefix=(-n,row['structure_nearest_d2'][s])
                elif family=='structure_proximity':
                    s=structures[fields[1]];d=row['structure_nearest_d2'][s]
                    if row['complete'][s][0] and row['complete'][s][3] and d<=65536:prefix=(d,-row['counts'][s][3])
                elif family=='biome_proximity':
                    s=biomes[fields[1]];d=row['biome_nearest_d2'][s]
                    if row['complete'][14+s][2] and d<=1048576:prefix=(d,)
                elif family=='biome_landmark_pairs':
                    b=biomes[fields[1]];s=structures[fields[2]];d=row['biome_nearest_d2'][b];n=row['counts'][s][1]
                    if row['complete'][14+b][0] and row['complete'][s][1] and d<=65536 and n:
                        prefix=(-n,d,row['structure_nearest_d2'][s])
                elif family=='profiles':
                    units=profile(row,fields[1])
                    if units is not None:prefix=(units,)
                elif family=='diversity' and cells[row['layout_id']]==int(fields[1]):
                    units=profile(row,fields[2])
                    if units is not None:prefix=(units,)
                if prefix is not None:
                    rank=(*prefix,int(row['seed'])&((1<<64)-1),*row['anchor'],row['layout_id'])
                    serial=list(rank)
                    if family in ('profiles','diversity'):serial[0]=str(serial[0])
                    candidates.append((rank,{'world_id':row['world_id'],'layout_id':row['layout_id'],'rank':serial}))
        chosen=[];seen=set()
        for _,member in sorted(candidates,key=lambda item:item[0]):
            if member['world_id'] not in seen:
                chosen.append(member);seen.add(member['world_id'])
                if len(chosen)==k:break
        result[oid]=chosen;retained.update(m['world_id'] for m in chosen)
    return {'objectives':result,'world_ids':sorted(retained)}
