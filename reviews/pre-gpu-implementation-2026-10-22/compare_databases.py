"""Disposable typed storage experiments; full scorer and source facts stay unchanged."""
from pathlib import Path
import sys,os,json,time,csv,sqlite3,statistics,collections,hashlib,subprocess
from decimal import Decimal
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';D=B/'database-comparison';D.mkdir();sys.path[:0]=[str(B/'engine-python'),str(R/'src')]
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
import numpy as np
import duckdb
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest,canonical_json
from seed_search.catalog.read_views import structure_rules
from seed_search.catalog.query import rank_v3
from seed_search.catalog.retention import automation_primary_objectives_v3
from seed_search.catalog.ingestion import atomic_json
assert sqlite3.sqlite_version=='3.54.1'and duckdb.__version__=='2.0.0'
started=time.monotonic();store=AutomationStore(B/'catalog-copy');m=store.snapshot();sid=digest(m);reg=m['registry'];rows=list(store.iter_query_summaries(m,8192,'recommended',lazy_features=True));n=len(rows);features=[f['id']for f in reg['features']if f['kind']=='structure_count'];fields=[('row_id','<i8')]
for fi,f in enumerate(features):
 for scope in range(4):fields.extend([(f'f{fi}c{scope}','<u4'),(f'f{fi}k{scope}','u1')])
array=np.zeros(n,dtype=np.dtype(fields));source=E/'SERVING_BEFORE.json';cases=[x for x in json.loads(source.read_text())['cases']if x['request']['border_side']==8192 and x['request']['anchor_mode']=='recommended'];original_oracles=json.loads((B/'ORACLES.json').read_text())
for i,row in enumerate(rows):
 array['row_id'][i]=i
 for fi,f in enumerate(features):
  block=row['features'][f]
  for scope in range(4):array[f'f{fi}c{scope}'][i]=block['counts'][scope];array[f'f{fi}k{scope}'][i]=int(block['complete'][scope])
print('typed real source rows',n,flush=True)
np.save(D/'facts.npy',array);names=[name for name,_ in fields];sqlcols=','.join(name+' INTEGER NOT NULL'for name in names[1:]);schema='(row_id BIGINT PRIMARY KEY,'+sqlcols+')'
s=sqlite3.connect(D/'facts.sqlite');s.execute('PRAGMA journal_mode=WAL');s.execute('PRAGMA synchronous=FULL');s.execute('PRAGMA cache_size=-16384');s.execute('PRAGMA mmap_size=0');s.execute('CREATE TABLE facts'+schema)
d=duckdb.connect(str(D/'facts.duckdb'));d.execute("SET memory_limit='512MB'");d.execute('SET threads=1');d.execute("SET max_temp_directory_size='256MiB'");d.execute("SET temp_directory='"+str(D/'duckdb-temp').replace("'","''")+"'");d.execute('CREATE TABLE facts'+schema)
with(D/'facts.csv').open('w',newline='')as f:
 writer=csv.writer(f);writer.writerows(tuple(int(row[name])for name in names)for row in array)
build={};t=time.perf_counter()
with s:s.executemany('INSERT INTO facts VALUES('+','.join('?'for _ in names)+')',(tuple(int(row[name])for name in names)for row in array))
build['sqlite_base_seconds']=time.perf_counter()-t;t=time.perf_counter();d.execute("COPY facts FROM '"+str(D/'facts.csv').replace("'","''")+"' (FORMAT CSV,HEADER false)");build['duckdb_base_seconds']=time.perf_counter()-t
# Identical row copies test scan/layout scaling only; source IDs/worlds are not invented.
for replica in range(1,4):
 select='SELECT row_id+'+str(replica*n)+','+','.join(names[1:])+' FROM facts WHERE row_id<'+str(n)
 with s:s.execute('INSERT INTO facts '+select)
 d.execute('INSERT INTO facts '+select)
replicas=np.tile(array,4);replicas['row_id']=np.arange(4*n);np.save(D/'facts-4x.npy',replicas);t=time.perf_counter()
indexed=set()
for case in cases:
 for fid,scope,minimum in structure_rules(case['request'],reg):
  fi=features.index(fid)
  for field in (f'f{fi}c{scope}',f'f{fi}k{scope}'):
   if field not in indexed:s.execute('CREATE INDEX i_'+field+' ON facts('+field+')');indexed.add(field)
s.commit();build['sqlite_indexes_seconds']=time.perf_counter()-t;s.execute('PRAGMA wal_checkpoint(TRUNCATE)');assert s.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
parquet=D/'facts.parquet';t=time.perf_counter();d.execute("COPY facts TO '"+str(parquet).replace("'","''")+"' (FORMAT PARQUET,COMPRESSION ZSTD)");build['parquet_export_seconds']=time.perf_counter()-t

def timed(fn):
 samples=[];value=None
 for _ in range(7):
  t=time.perf_counter();value=fn();samples.append(time.perf_counter()-t)
 return value,dict(median_seconds=statistics.median(samples),samples_seconds=samples)

def exact_json(value):return json.loads(json.dumps(value,default=lambda x:{'__decimal_exact__':str(x)}if isinstance(x,Decimal)else (_ for _ in()).throw(TypeError(type(x).__name__))))
measurements=[];parity=[]
for factor in (1,4):
 count=n*factor;numeric=np.load(D/('facts.npy'if factor==1 else'facts-4x.npy'),mmap_mode='r')
 for case in cases:
  rules=structure_rules(case['request'],reg);clauses=['row_id<?'];params=[count];specs=[]
  for fid,scope,minimum in rules:
   fi=features.index(fid);cn=f'f{fi}c{scope}';kn=f'f{fi}k{scope}';clauses.append('('+cn+'>=? OR '+kn+'=0)');params.append(minimum);specs.append((cn,kn,minimum))
  sql='SELECT row_id FROM facts WHERE '+' AND '.join(clauses)+' ORDER BY row_id'
  def mask():
   allowed=np.ones(len(numeric),dtype=bool)
   for cn,kn,minimum in specs:allowed&=(numeric[cn]>=minimum)|(numeric[kn]==0)
   return np.flatnonzero(allowed).tolist()
  expected,nt=timed(mask);a,st=timed(lambda:[r[0]for r in s.execute(sql,params)]);b,dt=timed(lambda:[r[0]for r in d.execute(sql,params).fetchall()]);psql=sql.replace('FROM facts',"FROM read_parquet('"+str(parquet).replace("'","''")+"')");c,pt=timed(lambda:[r[0]for r in d.execute(psql,params).fetchall()]);assert a==b==c==expected,(factor,case['name'])
  measurements.append(dict(factor=factor,row_count=count,world_equivalent_row_copies=222*factor,case=case['name'],candidate_rows=len(expected),sqlite=st,duckdb=dt,duckdb_parquet=pt,numpy_mmap=nt,sqlite_query_plan=s.execute('EXPLAIN QUERY PLAN '+sql,params).fetchall(),duckdb_query_plan=d.execute('EXPLAIN '+sql,params).fetchall()))
  if factor==1:
   result=rank_v3((rows[i]for i in expected),case['request'],limit=1000,keep_keys=True,registry=reg);assert exact_json(result)==original_oracles[case['name']],case['name'];parity.append(dict(case=case['name'],full_original_scorer_equal=True,candidates=len(expected)))
  print('engine predicates',factor,case['name'],len(expected),flush=True)
# Narrow membership lookup, explicitly not full API/integrity/cursor serving.
s.execute('CREATE TABLE member(objective TEXT,ordinal INTEGER,payload BLOB,PRIMARY KEY(objective,ordinal))WITHOUT ROWID');d.execute('CREATE TABLE member(objective VARCHAR,ordinal INTEGER,payload VARCHAR,PRIMARY KEY(objective,ordinal))');ordinals=collections.Counter();members=[]
for row in m['memberships']:
 oid=row['objective_id'];ordinal=ordinals[oid];ordinals[oid]+=1;members.append((oid,ordinal,canonical_json(row['member'])))
t=time.perf_counter()
with s:s.executemany('INSERT INTO member VALUES(?,?,?)',members)
build['sqlite_members_seconds']=time.perf_counter()-t
with(D/'members.csv').open('w',newline='')as f:csv.writer(f).writerows((oid,ordinal,payload.decode())for oid,ordinal,payload in members)
t=time.perf_counter();d.execute("COPY member FROM '"+str(D/'members.csv').replace("'","''")+"' (FORMAT CSV,HEADER false)");build['duckdb_members_seconds']=time.perf_counter()-t
products=[];caps=automation_primary_objectives_v3();queries=json.loads((B/'QUERIES.json').read_text())
for case in queries['products']:
 body=case['request'];pid=body['product_id'];view=body['view'];lo=0 if view=='primary'else caps[pid];hi=caps[pid]if view=='primary'else 2*caps[pid]
 sql='SELECT payload FROM member WHERE objective=? AND ordinal>=? AND ordinal<? ORDER BY ordinal LIMIT ?';args=(pid,lo,hi,body['page_size'])
 def lookup(conn):return[dict(json.loads(row[0]),candidate_role=view,evidence_status='predicted')for row in conn.execute(sql,args).fetchall()]
 a,st=timed(lambda:lookup(s));b,dt=timed(lambda:lookup(d));assert a==b==case['results']['results'];products.append(dict(product_id=pid,view=view,sqlite=st,duckdb=dt,scope='narrow ordered lookup+decode+role only;complete guardedHTTP measured separately'))
s.execute('PRAGMA wal_checkpoint(TRUNCATE)');d.execute('CHECKPOINT');s.close();d.close()
# Checksum and stage a source-bound private index generation; no live pointer changes.
files=[D/'facts.sqlite',D/'facts.duckdb',D/'facts.npy',D/'facts-4x.npy',parquet];hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
for p in files:
 with p.open('r+b')as f:os.fsync(f.fileno())
fd=os.open(D,os.O_RDONLY);os.fsync(fd);os.close(fd)
binding=dict(revision='readiness-index-generation-v1',snapshot_id=sid,registry_id=digest(reg),source_observation_ids=[w['observation_id']for w in m['worlds']],files=hashes,schema=names,real_rows=n,replica_factor=4)
atomic_json(D/'generation.json',binding);assert all(hashlib.sha256((D/name).read_bytes()).hexdigest()==h for name,h in hashes.items())
report=dict(status='PASS',versions=dict(sqlite=sqlite3.sqlite_version,duckdb=duckdb.__version__,numpy=np.__version__),build=build,predicates=measurements,full_scorer_parity=parity,products=products,source=dict(snapshot_id=sid,worlds=222,memberships=len(m['memberships']),real_rows=n,structure_features=len(features),typed_fields=len(names)),storage_bytes={p.name:p.stat().st_size for p in D.iterdir()if p.is_file()},index_binding_sha256=hashlib.sha256((D/'generation.json').read_bytes()).hexdigest(),seconds=time.monotonic()-started,scope='Real source+4xidentical row replicas;warmOS cache;predicate/lookup microbenchmarks notcompleteAPI/SLA;originalscorercompletefiniteoutputparity;PostgreSQL/Quack/ArrowIPC notbenchmarked')
(E/'DATABASE_COMPARISON.json').write_text(json.dumps(report,indent=2)+'\n');print('database comparison PASS',flush=True)
