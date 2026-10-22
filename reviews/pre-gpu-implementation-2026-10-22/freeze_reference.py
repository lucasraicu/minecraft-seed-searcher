"""Freeze dirty source and a private, verified data reference without touching live state."""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,tarfile,sys,time,urllib.request
R=Path(__file__).resolve().parents[2]; E=Path(__file__).parent
B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022'
P=Path.home()/'.local/share/antigravity-worker-mcp/storage-query-profile-20261022'
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert not B.exists();B.mkdir()
 pre=json.loads((P/'PRE_STATE.json').read_text())
 assert all(H(p)==h for p,h in pre['protected_source_state'].items())
 config=json.loads((P/'source-config.json').read_text())
 files=[]
 for folder in ('src','tests','native','vendor','docs','fixtures','scripts','web-ui/src'):
  for p in (R/folder).rglob('*'):
   if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.profraw'):files.append(p)
 files.extend(p for p in R.glob('*') if p.is_file() and p.suffix in ('.md','.toml','.yaml','.lock','.py','.in'))
 files.extend(p for p in (R/'web-ui').glob('*') if p.is_file() and p.suffix in ('.json','.ts','.js','.html'))
 build=Path(config['options']['native_build'])
 files.extend(p for p in build.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 files=sorted(set(files)); manifest={str(p.relative_to(R)):H(p) for p in files}
 with tarfile.open(B/'source-before.tar.gz','w:gz')as t:
  for p in files:t.add(p,arcname=str(p.relative_to(R)),recursive=False)
 restore=B/'reference';restore.mkdir()
 with tarfile.open(B/'source-before.tar.gz')as t:t.extractall(restore,filter='data')
 assert all(H(restore/p)==h for p,h in manifest.items())
 subprocess.run([sys.executable,'-c',"import seed_search.catalog.harvest_native,seed_search.catalog.store;from seed_search.backend import native_runtime;native_runtime();print('restore imports/native runtime PASS')"],env=dict(os.environ,PYTHONPATH=str(restore/'src'),PYTHONDONTWRITEBYTECODE='1'),cwd=restore,check=True,capture_output=True)
 live=Path.home()/'.local/share/antigravity-worker-mcp/treasure-activation-approved-20261022/catalog'
 target=B/'catalog-copy'
 shutil.copytree(live,target,ignore=shutil.ignore_patterns('*.sqlite','*.sqlite-wal','*.sqlite-shm','*.lock','*.log'))
 for p in live.rglob('*.sqlite'):
  q=target/p.relative_to(live);q.parent.mkdir(parents=True,exist_ok=True)
  src=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);dst=sqlite3.connect(q);src.backup(dst);dst.close();src.close()
 assert all(H(p)==h for p,h in pre['live_hashes'].items())
 for name in ('source-config.json','source-registry.json','catalog-seeds.json'):
  shutil.copy2(P/name,B/name)
 for name in ('ORACLES.json','QUERIES.json','READMODELS.json','FIXED_REPLAY_PARITY.json'):
  shutil.copy2(R/'reviews/storage-query-profile-2026-10-22'/name,B/name)
 options=config['options']; spawn=Path(options['spawn']['executable']);shutil.copy2(spawn,B/'world-spawn-reference')
 native_deps=subprocess.check_output(['otool','-L',str(R/'src/seed_search/_native.abi3.so')],text=True)
 omp=Path('/opt/homebrew/opt/libomp/lib/libomp.dylib')
 if not omp.exists():omp=Path('/usr/local/opt/libomp/lib/libomp.dylib')
 report=dict(status='PASS',baseline_dir=str(B),source_files=len(manifest),source_manifest=manifest,archive_sha256=H(B/'source-before.tar.gz'),restore_all_hashes_match=True,restore_import_native_smoke=True,python=sys.version,packages=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),native_dependencies=native_deps,libomp_sha256=H(omp)if omp.exists()else None,config=config,oracle_files={name:H(B/name)for name in ('ORACLES.json','QUERIES.json','READMODELS.json','FIXED_REPLAY_PARITY.json')},live_pre_state=str(P/'PRE_STATE.json'),scope='Dirty/untracked source/build/tests/contracts/fixtures archive; complete private catalog copy with SQLite backup; existing exact-query oracles; no live writes/restart')
 (B/'SOURCE_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n');(E/'REFERENCE_FREEZE.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k]for k in ('status','source_files','baseline_dir','restore_all_hashes_match','restore_import_native_smoke')}),flush=True)
if __name__=='__main__':main()
