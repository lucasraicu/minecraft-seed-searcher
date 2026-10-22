from common import *
import collections,hashlib,sqlite3,zlib
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.artifacts import ArtifactStore

store=AutomationStore(DATA);manifest,load=timed(lambda:store.snapshot(SID));binding=store._binding(SID);index=store.artifacts.get_json(binding['artifact']);current={};category=collections.defaultdict(list)
def add(ref,kind):
 if ref['relative_key'] not in current:current[ref['relative_key']]=ref;category[kind].append(ref)
add(binding['artifact'],'manifest-index')
for p in index.get('pages',[]):add(p['artifact'],'manifest-'+p['kind'])
for w in manifest['worlds']:
 add(w['artifact'],'world-bundles')
 for ref in w.get('summary_artifacts',{}).values():add(ref,'query-projections')
allobjects=list((DATA/'automation/objects').rglob('*.gz'));stats={kind:dict(files=len(refs),compressed_bytes=sum(r['byte_length'] for r in refs),uncompressed_json_bytes=sum(r['uncompressed_length'] for r in refs)) for kind,refs in category.items()}
actual=sum(p.stat().st_size for p in allobjects);reachable=sum(r['byte_length'] for r in current.values())
layer=collections.defaultdict(lambda:dict(files=0,bytes=0))
for p in DATA.rglob('*'):
 if p.is_file():
  parts=p.relative_to(DATA).parts;k='/'.join(parts[:2]) if parts[0] in ['automation','artifacts','accuracy','evidence'] else parts[0];layer[k]['files']+=1;layer[k]['bytes']+=p.stat().st_size
# Read-only structural stats; timings here do not represent production latency.
dbs={}
for p in DATA.glob('*.sqlite'):
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as c:
  tables=[x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
  counts={t:c.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}
  stat={k:c.execute('PRAGMA '+k).fetchone()[0] for k in ['page_size','page_count','freelist_count','journal_mode']}
  try:stat['object_pages']=dict(c.execute('SELECT name,sum(pgsize) FROM dbstat GROUP BY name'))
  except sqlite3.OperationalError as e:stat['dbstat_unavailable']=str(e)
  dbs[p.name]=dict(bytes=p.stat().st_size,stats=stat,tables=counts)
# Same saved projection blobs, independently timed read/hash/inflate/strict parse.
refs=[w['summary_artifacts']['8192'] for w in manifest['worlds']];micro=[]
for trial in range(3):
 totals=collections.defaultdict(float);counts=collections.defaultdict(int)
 for ref in refs:
  path=store.artifacts.root/ref['relative_key'];raw,m=timed(path.read_bytes);totals['raw_fetch']+=m['wall_seconds'];counts['compressed_bytes']+=len(raw)
  h,m=timed(lambda:hashlib.sha256(raw).hexdigest());totals['hash']+=m['wall_seconds'];assert h==ref['sha256']
  plain,m=timed(lambda:zlib.decompress(raw,16+zlib.MAX_WBITS));totals['inflate']+=m['wall_seconds'];assert len(plain)==ref['uncompressed_length'];counts['json_bytes']+=len(plain)
  value,m=timed(lambda:json.loads(plain,object_pairs_hook=__import__('seed_search.catalog.artifacts',fromlist=['_unique_pairs'])._unique_pairs));totals['parse']+=m['wall_seconds'];counts['rows']+=len(value['rows'])
 micro.append(dict(trial=trial,stage_seconds=dict(totals),counts=dict(counts)))
# Full manifest retrieval/verification versus world-context cache init handled by query phase.
report=dict(status='PASS',snapshot_id=SID,worlds=len(manifest['worlds']),memberships=len(manifest['memberships']),manifest_load=load,current_snapshot_artifacts=stats,current_reachable_compressed_bytes=reachable,all_automation_object_bytes=actual,other_historical_shared_unreferenced_bytes=actual-reachable,current_fraction=reachable/actual,layer_bytes=dict(layer),sqlite=dbs,projection_8192_microbench=micro,scope='Current222world snapshot;other bytes include historical/shared/orphan objects and cannot be deleted without reachability proof')
save('STORAGE.json',report);save('current-artifact-references.json',current);print(json.dumps({k:v for k,v in report.items() if k not in ['layer_bytes','sqlite','projection_8192_microbench']}),flush=True)
