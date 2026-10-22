"""Disposable exact-query ablations and narrow read-index prototypes; no integration."""
from common import *
import collections,hashlib,sqlite3,statistics,signal
import numpy as np
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.query import rank_v3
from seed_search.catalog.registry import canonical_json,digest
from seed_search.catalog.retention import automation_primary_objectives_v3
signal.alarm(300);store=AutomationStore(DATA);manifest=store.snapshot(SID);oracles={};query_report=json.loads((B/'QUERIES.json').read_text())
path=B/'read-models.sqlite';assert not path.exists();c=sqlite3.connect(path);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL')
c.execute('CREATE TABLE member(snapshot TEXT,objective TEXT,ordinal INTEGER,payload BLOB,PRIMARY KEY(snapshot,objective,ordinal)) WITHOUT ROWID')
c.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT) WITHOUT ROWID')
c.executemany('INSERT INTO metadata VALUES(?,?)',[('snapshot',SID),('policy',manifest['policy_revision']),('registry',digest(manifest['registry']))]);ordinals=collections.Counter();start=time.monotonic();cpu=time.process_time()
with c:
 for entry in manifest['memberships']:
  oid=entry['objective_id'];ordinal=ordinals[oid];ordinals[oid]+=1
  c.execute('INSERT INTO member VALUES(?,?,?,?)',(SID,oid,ordinal,canonical_json(entry['member'])))
member_build=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,rows=sum(ordinals.values()))
product=[];capacities=automation_primary_objectives_v3()
for case in query_report['products']:
 body=case['request'];pid=body['product_id'];view=body['view'];k=capacities[pid];lo=0 if view=='primary' else k;hi=k if view=='primary' else 2*k
 sql='SELECT payload FROM member WHERE snapshot=? AND objective=? AND ordinal>=? AND ordinal<? ORDER BY ordinal LIMIT ?';params=(SID,pid,lo,hi,body['page_size'])
 def lookup():
  assert dict(c.execute('SELECT key,value FROM metadata'))=={'snapshot':SID,'policy':manifest['policy_revision'],'registry':digest(manifest['registry'])}
  return [dict(json.loads(row[0]),candidate_role=view,evidence_status='predicted') for row in c.execute(sql,params)]
 cached_blobs=[x[0] for x in c.execute(sql,params)]
 def memory_lookup():return [dict(json.loads(raw),candidate_role=view,evidence_status='predicted') for raw in cached_blobs]
 memory_samples=[]
 for _ in range(7):
  value,m=timed(memory_lookup);assert value==case['results']['results'];memory_samples.append(m)
 samples=[]
 for _ in range(7):
  result,m=timed(lookup);assert result==case['results']['results'];samples.append(m)
 cached=[dict(x['member'],candidate_role=view,evidence_status='predicted') for x in manifest['memberships'] if x['objective_id']==pid][lo:hi][:body['page_size']]
 assert cached==result
 product.append(dict(product_id=pid,view=view,rows=len(result),sqlite_lookup=samples,in_memory_blob_lookup=memory_samples,query_plan=c.execute('EXPLAIN QUERY PLAN '+sql,params).fetchall(),scope='Lookup+JSON decode+role+metadata guard only;notfullHTTP/cursors/provenance/corruption/recovery validation'))
print('Membership index complete',flush=True)
# Predecode the exact same saved projections; rowIDs bind to this snapshot/side/mode.
rows,predecode=timed(lambda:list(store.iter_query_summaries(manifest,8192,'recommended',lazy_features=True)))
features=['structure.village','structure.igloo_with_basement','structure.bastion_treasure'];fields=[]
for fi,f in enumerate(features):
 for scope in range(4):fields += [(f'f{fi}c{scope}','<i4'),(f'f{fi}k{scope}','u1')]
columns=','.join(name+' INTEGER NOT NULL' for name,typ in fields);c.execute('CREATE TABLE filters(rowid INTEGER PRIMARY KEY,'+columns+')');numeric=np.zeros(len(rows),dtype=np.dtype(fields));start=time.monotonic();cpu=time.process_time()
with c:
 for index,row in enumerate(rows):
  values=[]
  for fi,f in enumerate(features):
   block=row['features'][f]
   for scope in range(4):
    values.extend([block['counts'][scope],int(block['complete'][scope])]);numeric[f'f{fi}c{scope}'][index]=block['counts'][scope];numeric[f'f{fi}k{scope}'][index]=int(block['complete'][scope])
  c.execute('INSERT INTO filters VALUES('+','.join('?' for _ in range(1+len(values)))+')',(index,*values))
 for name,typ in fields:c.execute('CREATE INDEX "i_'+name+'" ON filters('+name+')')
numeric_path=B/'filters.npy';np.save(numeric_path,numeric);index_build=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,rows=len(rows),npy_bytes=numeric_path.stat().st_size)
c.execute('PRAGMA wal_checkpoint(TRUNCATE)');assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
# Exact same scorer remains authoritative after conservative structure-only prefilter.
comparisons=[]
for name,req in cases()[1:]:
 baseline,base_time=timed(lambda:rank_v3(iter(rows),req,limit=1000,keep_keys=True,registry=REG));oracles[name]=baseline;assert baseline['matched_worlds']==next(x for x in query_report['cases'] if x['name']==name)['trials'][0]['matched_worlds']
 clauses=[];args=[];specs=[]
 for rule in req['rows']:
  if rule['rule']!='required' or rule['kind']!='structure_count':continue
  assert rule['feature'] in features;fi=features.index(rule['feature']);dim='nether' if rule['feature']=='structure.bastion_treasure' else 'overworld'
  scope=3 if rule['scope']['kind']=='inside_border' else ([64,128,256] if dim=='nether' else [256,512,1024]).index(rule['scope']['radius']);threshold=rule['at_least'];cn=f'f{fi}c{scope}';kn=f'f{fi}k{scope}'
  clauses.append('('+cn+'>=? OR '+kn+'=0)');args.append(threshold);specs.append((cn,kn,threshold))
 sql='SELECT rowid FROM filters'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY rowid'
 def numeric_lookup():
  mask=np.ones(len(rows),dtype=bool)
  for cn,kn,threshold in specs:mask &= (numeric[cn]>=threshold)|(numeric[kn]==0)
  return np.flatnonzero(mask).tolist()
 ids,select_time=timed(lambda:[x[0] for x in c.execute(sql,args)]);array_ids,array_time=timed(numeric_lookup);assert ids==array_ids
 filtered,score_time=timed(lambda:rank_v3((rows[i] for i in ids),req,limit=1000,keep_keys=True,registry=REG));assert filtered==baseline,name
 # Whole-world blob access lower-bound: only fetch projection blobs for worlds
 # with at least one retained row, then retain exact bound layoutIDs.
 allowed={rows[i]['layout_id'] for i in ids};world_ids={rows[i]['world_id'] for i in ids};sub=dict(manifest,worlds=[w for w in manifest['worlds'] if w['world_id'] in world_ids])
 actual,io_score=timed(lambda:rank_v3((r for r in store.iter_query_summaries(sub,8192,'recommended',lazy_features=True) if r['layout_id'] in allowed),req,limit=1000,keep_keys=True,registry=REG));assert actual==baseline,name
 comparisons.append(dict(name=name,total_rows=len(rows),candidate_rows=len(ids),candidate_worlds=len(world_ids),predecoded_full_scorer=base_time,sqlite_filter=select_time,numeric_filter=array_time,filtered_same_scorer=score_time,selective_blob_load_plus_same_scorer=io_score,ordered_results_and_unknowns_equal=True,query_plan=c.execute('EXPLAIN QUERY PLAN '+sql,args).fetchall()))
 print(name,'rows',len(ids),'worlds',len(world_ids),flush=True)
# Real prefix sizes, same broad request/scorer; no invented world population.
prefix=[];req=dict(cases())['broad-recommended']
for size in [25,100,222]:
 ids={w['world_id'] for w in manifest['worlds'][:size]};subrows=[r for r in rows if r['world_id'] in ids];_,m=timed(lambda:rank_v3(iter(subrows),req,limit=1000,registry=REG));prefix.append(dict(worlds=size,rows=len(subrows),scorer=m))
report=dict(status='PASS',membership_index_build=member_build,products=product,projection_predecode=predecode,filter_index_build=index_build,filter_cases=comparisons,prefix_scaling=prefix,sqlite_bytes=path.stat().st_size,numeric_array_bytes=numeric_path.stat().st_size,limitations=['Narrow disposable projections,notproductionengine','Exactfiniteworkloadparity,notgeneralreplacementproof','No crash/corruption/recovery/multiversion writer-concurrency tests','OS cache warm;222world dataset;no arbitrary scale claim','Derived index trust/build cost outside lookup timings'])
save('ORACLES.json',oracles);save('EXPORT_RECOVERY.json',dict(status='PASS',original_error='Final ORACLES JSON export could not serialize exact Decimal sort keys; all query timing/parity checks already passed',repair='Rebuilt full original-scorer oracles during read-model stage; exact Decimal values persisted as tagged decimal strings; direct Python equality checks retain full sort precision'));save('READMODELS.json',report);c.close();print('Read models pass',flush=True)
