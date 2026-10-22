"""Bounded extra XYZ evidence, explicitly isolated from frozen Realm observations."""
from numbers import Integral
import time
from .registry import digest, SAMPLING_PROFILE_REVISION_V3

PLANES = (-48,0,96,160,224)
MAX_POINTS = 8000


def provider_id(observation):
    identity=observation['identity']
    return digest(['catalog-biome-provider-v3',{k:identity[k] for k in
        ('edition','game_build_id','world_settings_id','model_id','native_sha256','source_sha256')}])


def validate_extension(value, observation):
    fields={'revision','base_observation_id','sampling_profile_revision','provider_id','bounds','biomes','biome_names'}
    if not isinstance(value,dict) or set(value)!=fields or value['revision']!='catalog-biome-extension-v3':
        raise ValueError('Invalid biome extension schema')
    if value['base_observation_id']!=digest(observation):raise ValueError('Extension base observation mismatch')
    if value['sampling_profile_revision']!=SAMPLING_PROFILE_REVISION_V3:raise ValueError('Unknown extension sampling profile')
    if value['provider_id']!=provider_id(observation):raise ValueError('Extension provider identity differs')
    if value['bounds']!=observation['bounds']['overworld']:raise ValueError('Extension envelope differs')
    names=value['biome_names'];biomes=value['biomes']
    if not isinstance(names,dict) or not isinstance(biomes,dict) or set(biomes)!={'overworld'}:
        raise ValueError('Invalid extension biome mapping/dimension')
    pts=biomes['overworld']
    if not isinstance(pts,list) or not 1<=len(pts)<=MAX_POINTS:raise ValueError('Extension point capacity; empty evidence uses null')
    for bid,name in names.items():
        if not isinstance(bid,str) or not bid.isascii() or not bid.isdigit() or str(int(bid))!=bid or not 0<=int(bid)<=65535 or not isinstance(name,str) or not 1<=len(name)<=128:raise ValueError('Invalid extension biome name')
        if bid in observation['biome_names'] and observation['biome_names'][bid]!=name:raise ValueError('Extension overwrites base biome namespace')
    base_xyz={tuple(p[:3]) for p in observation['biomes']['overworld']};seen=set();used=set();b=value['bounds']
    for pt in pts:
        if not isinstance(pt,list) or len(pt)!=4 or any(type(n)is not int for n in pt):raise ValueError('Invalid extension XYZ/ID')
        x,y,z,bid=pt;xyz=(x,y,z)
        if y not in PLANES or x%256 or z%256 or not b[0]<=x<b[2] or not b[1]<=z<b[3]:raise ValueError('Extension point outside declared profile/envelope')
        if xyz in base_xyz or xyz in seen:raise ValueError('Extension duplicates saved evidence')
        if str(bid) not in names:raise ValueError('Unmapped extension biome')
        seen.add(xyz);used.add(str(bid))
    if used!=set(names):raise ValueError('Unused extension biome names')
    return value


def extract_extension(observation, backend, *, name_for_id, deadline=None):
    """Compute only missing aligned points; no mutation of the original observation."""
    b=observation['bounds']['overworld'];known={tuple(p[:3]) for p in observation['biomes']['overworld']}
    points=[[x,y,z] for y in PLANES for z in range(-(-b[1]//256)*256,b[3],256)
            for x in range(-(-b[0]//256)*256,b[2],256) if (x,y,z) not in known]
    if len(points)>MAX_POINTS:raise ValueError('Extra survey exceeds the approved8000point cap')
    if not points:return None
    values=[];names={}
    for i in range(0,len(points),1024):
        if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Height evidence deadline')
        batch=points[i:i+1024];ids=backend.biome_points(batch,dimension=0)
        if len(ids)!=len(batch):raise ValueError('Truncated extension response')
        for pt,bid in zip(batch,ids):
            if isinstance(bid,bool) or not isinstance(bid,Integral):raise ValueError('Noninteger extension biome')
            bid=int(bid);name=name_for_id(bid);names[str(bid)]=name;values.append(pt+[bid])
    value=dict(revision='catalog-biome-extension-v3',base_observation_id=digest(observation),
        sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3,provider_id=provider_id(observation),
        bounds=list(b),biomes={'overworld':values},biome_names=names)
    return validate_extension(value,observation)
