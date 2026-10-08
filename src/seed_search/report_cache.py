"""Content-keyed report inputs and maps, verified before reuse."""
import hashlib
import json
import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path
import numpy as np
from .storage import backend_identity,semantic_hash


@lru_cache(maxsize=1)
def predictor_digest():
    return hashlib.sha256(json.dumps(backend_identity(),sort_keys=True).encode()).hexdigest()


def terrain_identity(seed,bounds,step,cfg):
    return {'format':1,'seed':str(seed),'bounds':list(bounds),'step':step,
            'config':semantic_hash(cfg),'predictor':predictor_digest()}


def terrain_path(root,identity):
    digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    return Path(root)/f'{digest}.npz'


def write_atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        temp=f.name;f.write(data)
    os.replace(temp,path)


def save_terrain(root,seed,bounds,terrain,cfg):
    identity=terrain_identity(seed,bounds,terrain['step'],cfg);path=terrain_path(root,identity)
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        name=f.name
        np.savez_compressed(f,height=terrain['height'],biomes=terrain['biomes'],
                            identity=json.dumps(identity,sort_keys=True),actual_bounds=terrain['bounds'],
                            points=terrain['points'],sea_level_stride1_points=terrain['sea_level_stride1_points'])
    os.replace(name,path)
    write_atomic(str(path)+'.sha256',hashlib.sha256(path.read_bytes()).hexdigest().encode())
    return path


def load_terrain(root,seed,bounds,step,cfg):
    identity=terrain_identity(seed,bounds,step,cfg);path=terrain_path(root,identity)
    try:
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=Path(str(path)+'.sha256').read_text():return None
        with np.load(path,allow_pickle=False) as data:
            if json.loads(str(data['identity']))!=identity:return None
            h=data['height'];b=data['biomes'];shape=((bounds[3]-bounds[1])//step+1,(bounds[2]-bounds[0])//step+1)
            if h.shape!=shape or b.shape!=shape or not np.issubdtype(h.dtype,np.integer) or not np.issubdtype(b.dtype,np.integer):return None
            return {'height':h,'biomes':b,'bounds':data['actual_bounds'].tolist(),'step':step,
                    'points':int(data['points']),'sea_level_stride1_points':int(data['sea_level_stride1_points']),
                    'report_cache_hit':True}
    except (OSError,ValueError,KeyError,EOFError):return None


def map_identity(candidate,cfg):
    from .storage import ROOT
    renderer=hashlib.sha256((ROOT/'src/seed_search/reports.py').read_bytes()).hexdigest()
    payload={'candidate':candidate,'config':cfg,'predictor':predictor_digest(),'renderer':renderer,'format':1}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


def reuse_maps(root,key,out):
    cache=Path(root)/key
    try:
        proof=json.loads((cache/'hashes.json').read_text())
        for name in ('overworld.png','nether.png'):
            if hashlib.sha256((cache/name).read_bytes()).hexdigest()!=proof[name]:return False
        for name in ('overworld.png','nether.png'):shutil.copyfile(cache/name,Path(out)/name)
        return True
    except (OSError,ValueError,KeyError):return False


def save_maps(root,key,out):
    cache=Path(root)/key;cache.mkdir(parents=True,exist_ok=True);hashes={}
    for name in ('overworld.png','nether.png'):
        data=(Path(out)/name).read_bytes();write_atomic(cache/name,data);hashes[name]=hashlib.sha256(data).hexdigest()
    write_atomic(cache/'hashes.json',json.dumps(hashes,sort_keys=True).encode())
