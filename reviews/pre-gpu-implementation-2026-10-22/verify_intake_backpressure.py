"""Fast-emitter metadata fixture over frozen existing seeds; never run extraction."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'src'));E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022'
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue,make_descriptor
from seed_search.catalog.registry import digest
m=AutomationStore(B/'catalog-copy').snapshot();seeds=[w['identity']['seed']for w in m['worlds'][:32]];ident=json.loads((B/'source-config.json').read_text())['identity'];root=B/'pressure-metadata'
with HarvestQueue(root)as q:
 ids=[]
 for i in range(8):
  descriptor=make_descriptor(dict(sequence='manifest',manifest_seeds=seeds),0,len(seeds),ident,digest(['bounded-pressure-fixture',i]),root,caps=dict(sample_cap=32,pending_cap=4,total_seconds=600,world_seconds=120,output_bytes=16<<20,max_attempts=1))
  q.register(descriptor);ids.append(descriptor['campaign_id'])
 for _ in range(32):
  q.expand();assert sum(v for k,v in q.status()['jobs'].items()if k in ('pending','active'))<=4
 saturated=q.status();assert saturated['jobs']=={'pending':4}
 for cid in ids:q.set_campaign_state(cid,'cancelled')
 cancelled=q.status();assert cancelled['jobs']=={'cancelled':4}
# Retire only the owned sustained handoff descriptor; preserve all queue bytes.
with HarvestQueue(B/'sustained-handoff')as q:
 q.expand();handoff=q.status();assert sum(handoff['jobs'].values())<=2
 for c in handoff['campaigns']:q.set_campaign_state(c['id'],'cancelled')
 retired=q.status()
report=dict(status='PASS',input_existing_worlds=32,independent_descriptors=8,expand_calls=32,pending_cap=4,saturated=saturated,cancelled=cancelled,sustained_handoff_after_expand=handoff,sustained_handoff_retired=retired,scope='Private metadata pressure/cancellation fixture using existing frozen seeds;no extractor/no new seed search;all earlier files retained')
(E/'BACKPRESSURE.json').write_text(json.dumps(report,indent=2)+'\n');print('bounded intake/cancellation PASS')
