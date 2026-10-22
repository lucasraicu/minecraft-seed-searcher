"""Small deterministic CPU oracle vectors; no GPU implementation or seed search."""
from pathlib import Path
import json,struct,sys,hashlib
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';sys.path.insert(0,str(R/'src'))
from seed_search.seeds import seed_from_index,seed_strided,MASK64
from seed_search.catalog.geometry import bounds_for,inside,distance2
from seed_search.catalog.registry import digest
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.catalog.store import AutomationStore
from seed_search.backend import Backend
store=AutomationStore(B/'catalog-copy');m=store.snapshot();vectors={}
vectors['full64']=[dict(index=str(i),run_key=str(k),seed=str(seed_from_index(i,k)))for i in (0,1,2**32-1,2**32,2**63-1,2**64-1)for k in (0,2026101630,2**64-1)]
vectors['strided']=[dict(index=str(i),low32=str(k),seed=str(seed_strided(i,k)))for i in (0,1,2**32-1)for k in (0,-1,2**31-1,-2**63)]
vectors['signed_identity']=[dict(seed=str(s),little_endian_u64_hex=struct.pack('<Q',s&MASK64).hex())for s in (-2**63,-1,0,1,2**63-1)]
vectors['floor8']=[dict(overworld=n,nether=n//8)for n in (-30000000,-9,-8,-7,-1,0,1,7,8,9,30000000)]
vectors['borders']=[]
for anchor in ([-9,-1],[0,0],[30000000,-30000000]):
 for side in (2048,4096,8192):
  bounds=bounds_for(anchor,side)
  vectors['borders'].append(dict(anchor=anchor,side=side,bounds=list(bounds),points=[dict(point=[x,z],inside=inside(x,z,bounds),distance_squared=distance2(x,z,anchor))for x,z in ((bounds[0],bounds[1]),(bounds[2],bounds[3]),(bounds[2]-1,bounds[3]-1),tuple(anchor))]))
vectors['native_raw_village_attempts']=[]
for entry in m['worlds'][::max(1,len(m['worlds'])//5)][:5]:
 with Backend(entry['identity']['seed'])as backend:
  for rx,rz in ((-2,-1),(-1,0),(0,0),(1,1)):
   point=backend.attempt('village',rx,rz)
   vectors['native_raw_village_attempts'].append(dict(seed=entry['identity']['seed'],region=[rx,rz],position=list(point)if point is not None else None,source_identity=entry['identity']))
report=dict(revision='cpu-gpu-reference-vectors-v1',snapshot_id=digest(m),registry_revision=digest(m['registry']),personal_config=dynamic_v3_blueprint_config(),vectors=vectors,scope='CPU-only seed/index/coordinate/rawvillage oracle; rawpositions are notviability/absence/gamecertification;5existingworlds20single-regionrawattempts,notcompleteextractions')
(E/'CPU_REFERENCE_VECTORS.json').write_text(json.dumps(report,indent=2)+'\n');print('CPU vectors',sum(len(v)for v in vectors.values()),'PASS')
