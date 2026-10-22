"""Build a private CPython SQLite adapter; do not replace global/live libraries."""
from pathlib import Path
import hashlib,json,sys,sysconfig,tarfile,subprocess,os
E=Path(__file__).parent;D=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022/sqlite-fixed'
with tarfile.open(D/'Python-3.13.15.tar.xz')as t:
 for member in t.getmembers():
  if '/Modules/_sqlite/'in member.name and member.isfile():
   target=D/'adapter'/member.name.split('/Modules/_sqlite/')[1];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(t.extractfile(member).read())
output=D/'runtime';output.mkdir(exist_ok=True)
sources=sorted((D/'adapter').glob('*.c'));assert len(sources)>=8
argv=['clang','-bundle','-undefined','dynamic_lookup','-O2','-DPy_BUILD_CORE_MODULE','-DMODULE_NAME="sqlite3"','-I'+sysconfig.get_paths()['include'],'-I'+sysconfig.get_paths()['include']+'/internal','-I'+str(D),*[str(p)for p in sources],str(D/'libsqlite3.0.dylib'),'-o',str(output/('_sqlite3'+sysconfig.get_config_var('EXT_SUFFIX')))]
r=subprocess.run(argv,capture_output=True,text=True,timeout=120);(E/'sqlite-adapter-build.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
probe=subprocess.run([sys.executable,'-c','import sqlite3;print(sqlite3.sqlite_version);assert sqlite3.sqlite_version=="3.54.1"'],env=dict(os.environ,PYTHONPATH=str(output)),capture_output=True,text=True,timeout=10);assert probe.returncode==0,probe.stderr+probe.stdout
report=dict(status='PASS',original_runtime='3.50.4',private_runtime='3.54.1',sqlite_source='https://www.sqlite.org/2026/sqlite-amalgamation-3540100.zip',official_sqlite_sha3_256=hashlib.sha3_256((D/'source.zip').read_bytes()).hexdigest(),cpython_source='https://www.python.org/ftp/python/3.13.15/Python-3.13.15.tar.xz',cpython_archive_sha256=hashlib.sha256((D/'Python-3.13.15.tar.xz').read_bytes()).hexdigest(),build_argv=argv,module_sha256=hashlib.sha256((output/('_sqlite3'+sysconfig.get_config_var('EXT_SUFFIX'))).read_bytes()).hexdigest(),library_sha256=hashlib.sha256((D/'libsqlite3.0.dylib').read_bytes()).hexdigest(),scope='Private PYTHONPATH override using CPython3.13.15 ownadapter + officialSQLite3.54.1; no global/live/projectnative library replacement',fixed_bug_source='https://www.sqlite.org/wal.html#walreset')
(E/'SQLITE_PRIVATE_RUNTIME.json').write_text(json.dumps(report,indent=2)+'\n');print('Private SQLite3.54.1 adapter PASS',flush=True)
