"""Disposable engine commit/recovery, integrity and concurrency checks."""
from pathlib import Path
import json,sys,os,subprocess,hashlib,sqlite3,time
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';D=B/'database-comparison';sys.path.insert(0,str(B/'engine-python'))
import duckdb

def connect(engine,path):
 if engine=='sqlite':
  c=sqlite3.connect(path,isolation_level=None,timeout=.05);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL');return c
 c=duckdb.connect(str(path));c.execute('SET threads=1');c.execute("SET memory_limit='128MB'");return c
checks=[]
for engine in ('sqlite','duckdb'):
 for committed in (False,True):
  path=D/f'recovery-{engine}-{int(committed)}.db';c=connect(engine,path);c.execute('CREATE TABLE receipt(id INTEGER PRIMARY KEY,value INTEGER)');c.execute('INSERT INTO receipt VALUES(1,10)');c.close()
  code='''import sys,os,signal,sqlite3
from pathlib import Path
engine,path,commit,marker=sys.argv[1:]
if engine=='sqlite':
 c=sqlite3.connect(path,isolation_level=None);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL')
else:
 import duckdb
 c=duckdb.connect(path);c.execute('SET threads=1');c.execute("SET memory_limit='128MB'")
c.execute('BEGIN');c.execute('INSERT INTO receipt VALUES(2,20)')
if commit=='1':c.execute('COMMIT')
with open(marker,'w')as f:f.write(commit);f.flush();os.fsync(f.fileno())
os.kill(os.getpid(),signal.SIGKILL)
'''
  marker=D/f'crash-{engine}-{int(committed)}.marker'
  r=subprocess.run([sys.executable,'-c',code,engine,str(path),str(int(committed)),str(marker)],env=dict(os.environ,PYTHONPATH=str(B/'engine-python')),capture_output=True,text=True,timeout=20)
  assert r.returncode==-9 and marker.read_text()==str(int(committed)),r.stderr
  c=connect(engine,path);actual=c.execute('SELECT id,value FROM receipt ORDER BY id').fetchall();assert actual==([(1,10),(2,20)]if committed else[(1,10)]),(engine,actual)
  c.execute('INSERT INTO receipt VALUES(2,20)ON CONFLICT(id)DO NOTHING');assert c.execute('SELECT count(*)FROM receipt').fetchone()[0]==2;c.close()
  checks.append(dict(engine=engine,acknowledged_commit=committed,owned_crash_exit=r.returncode,expected_rows_recovered=True,idempotent_retry=True))
# SQLite snapshot readers continue while one writer commits; another writer is bounded.
p=D/'concurrency-sqlite.db';a=connect('sqlite',p);a.execute('CREATE TABLE t(id INTEGER PRIMARY KEY,value INTEGER)');a.execute('INSERT INTO t VALUES(1,10)');b=connect('sqlite',p);c=connect('sqlite',p)
a.execute('BEGIN');assert a.execute('SELECT value FROM t').fetchone()[0]==10
b.execute('UPDATE t SET value=11');assert a.execute('SELECT value FROM t').fetchone()[0]==10
a.execute('COMMIT');assert a.execute('SELECT value FROM t').fetchone()[0]==11
b.execute('BEGIN IMMEDIATE');t=time.monotonic()
try:c.execute('BEGIN IMMEDIATE')
except sqlite3.OperationalError as exc:assert'locked'in str(exc)
else:raise AssertionError('Concurrent SQLite writer was not fenced')
wait=time.monotonic()-t;assert wait<1;b.execute('ROLLBACK');a.close();b.close();c.close()
# DuckDB embedded writer conflicts are explicit, with readers retaining their snapshot.
p=D/'concurrency-duckdb.db';db=connect('duckdb',p);db.execute('CREATE TABLE t(id INTEGER PRIMARY KEY,value INTEGER)');db.execute('INSERT INTO t VALUES(1,10)');a=db.cursor();b=db.cursor();reader=db.cursor();reader.execute('BEGIN');assert reader.execute('SELECT value FROM t').fetchone()[0]==10
a.execute('BEGIN');b.execute('BEGIN');a.execute('UPDATE t SET value=11')
try:b.execute('UPDATE t SET value=12')
except duckdb.TransactionException:b.execute('ROLLBACK')
else:raise AssertionError('Expected optimistic write conflict')
a.execute('COMMIT');assert reader.execute('SELECT value FROM t').fetchone()[0]==10;reader.execute('COMMIT');assert reader.execute('SELECT value FROM t').fetchone()[0]==11
a.close();b.close();reader.close();db.close()
# Source-bound generation checksums detect corruption before any engine query.
meta=json.loads((D/'generation.json').read_text());assert meta['snapshot_id']=='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d'
for name,expected in meta['files'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==expected
raw=(D/'facts.npy').read_bytes();corrupt=bytearray(raw);corrupt[-1]^=1;(D/'corrupt-facts-example.npy').write_bytes(corrupt);assert hashlib.sha256(corrupt).hexdigest()!=meta['files']['facts.npy']
report=dict(status='PASS',crash_recovery=checks,sqlite_concurrent_read_snapshot=True,sqlite_second_writer_wait_seconds=wait,duckdb_conflicting_writer_rejected=True,duckdb_reader_snapshot=True,index_source_binding_and_hashes_match=True,corrupt_index_detected=True,scope='Disposable local engine tables;notprojectqueueproof ornetworkfleet/Quack/PostgreSQLtests')
(E/'DATABASE_RECOVERY.json').write_text(json.dumps(report,indent=2)+'\n');print('Database recovery/integrity/concurrency PASS')
