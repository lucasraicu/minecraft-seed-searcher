"""Durable, compatible checkpoint encoding and exact integer derivation indexes."""
import copy
import json
import random
import pytest
from seed_search.catalog import ingestion,harvest_native
from seed_search.catalog.registry import canonical_json,digest
from seed_search.catalog.models import empty_observation_v2,identity
from seed_search.catalog.summaries_fast import _biome_arrays,_indexed_biome_summary


def observation():
 return empty_observation_v2(identity(0,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))


def test_checkpoint_one_encoding_compatible_with_old_reader(tmp_path,monkeypatch):
 obs=observation();path=tmp_path/'new.json';calls=[]
 import seed_search.catalog.registry as registry
 original=registry.canonical_json
 def encode(value):calls.append(value);return original(value)
 monkeypatch.setattr(registry,'canonical_json',encode)
 harvest_native.save_checkpoint(path,obs)
 assert calls==[obs]
 expected={'sha256':digest(obs),'observation':obs}
 assert json.loads(path.read_bytes())==expected
 assert harvest_native.checkpoint_observation(path,protocol=2)==obs
 legacy=tmp_path/'legacy.json';ingestion.atomic_json(legacy,expected)
 assert harvest_native.checkpoint_observation(legacy,protocol=2)==obs
 value=json.loads(path.read_bytes());value['observation']['metrics']['tampered']=1
 path.write_text(json.dumps(value))
 with pytest.raises(ValueError,match='checksum'):harvest_native.checkpoint_observation(path,protocol=2)


def test_checkpoint_replace_failure_preserves_acknowledged_bytes(tmp_path,monkeypatch):
 obs=observation();path=tmp_path/'checkpoint.json';harvest_native.save_checkpoint(path,obs);before=path.read_bytes()
 calls=[];real_fsync=ingestion.os.fsync
 def fsync(fd):calls.append(fd);return real_fsync(fd)
 monkeypatch.setattr(ingestion.os,'fsync',fsync)
 def fail(*args):raise OSError('disk/pointer failure')
 monkeypatch.setattr(ingestion.os,'replace',fail)
 obs['metrics']['later']=1
 with pytest.raises(OSError):harvest_native.save_checkpoint(path,obs)
 assert path.read_bytes()==before and len(calls)==1
 assert not list(tmp_path.glob('.*.tmp.*'))


def test_checkpoint_durability_boundaries_and_nan_rejection(tmp_path,monkeypatch):
 calls=[];real=ingestion.os.fsync
 monkeypatch.setattr(ingestion.os,'fsync',lambda fd:(calls.append(fd),real(fd))[1])
 obs=observation();path=tmp_path/'checkpoint.json';harvest_native.save_checkpoint(path,obs)
 assert len(calls)==2
 raw=path.read_bytes();obs['metrics']['bad']=float('nan')
 with pytest.raises(ValueError):harvest_native.save_checkpoint(path,obs)
 assert path.read_bytes()==raw
 with pytest.raises(TypeError):ingestion.atomic_bytes(path,bytearray(b'bad'))


def test_integer_index_matches_independent_scalar_boundaries_and_xyz_ties():
 rng=random.Random(7)
 pts=[[rng.randrange(-10000,10000),rng.choice([-48,0,63,160]),rng.randrange(-10000,10000),i]for i in range(400)]
 pts += [[-8,160,0,999],[-8,-48,0,998],[8,0,0,997],[0,0,8,996]]
 original=copy.deepcopy(pts);arrays=_biome_arrays({'x':pts,'empty':[]})
 for cx,cz in [(-1,-1),(0,0),(512,-512)]:
  for half in [8,512,4096,8192]:
   box=(cx-half,cx+half,cz-half,cz+half);radii=[64,128,256]
   inside=[p for p in pts if box[0]<=p[0]<box[1]and box[2]<=p[2]<box[3]]
   if inside:
    best=min(inside,key=lambda p:((p[0]-cx)**2+(p[2]-cz)**2,*p[:3]));d=(best[0]-cx)**2+(best[2]-cz)**2
    expected=([int(d<=r*r)for r in radii]+[1],d,best[:3])
   else:expected=([0]*4,None,None)
   assert _indexed_biome_summary(arrays['x'],cx,cz,box,radii)==expected
 assert pts==original
