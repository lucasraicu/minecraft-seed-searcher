"""Verify live source/state immutability after all disposable profiling work."""
from pathlib import Path
import json,hashlib,subprocess,urllib.request
ROOT=Path(__file__).resolve().parents[2];B=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/storage-query-profile-20261022');R=Path(__file__).resolve().parent
pre=json.loads((B/'PRE_STATE.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(p)==h for p,h in pre['live_hashes'].items()),'Live non-SQLite artifact drift'
assert all(sha(p)==h for p,h in pre['protected_source_state'].items()),'Source/build/personal state drift'
manifest=json.loads(Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/personal-file-hashes.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest.items()),'Protected files drift'
assert subprocess.check_output(['ps','-p','91321,17880,22035','-o','pid=,command='],text=True)==pre['processes']
post={}
for port,ep in [(3000,'sweep/status'),(3001,'catalog/automation-status'),(3001,'catalog/capabilities')]:post[f'{port}/{ep}']=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/'+ep,timeout=10))
for key in ['3001/catalog/automation-status','3001/catalog/capabilities']:assert post[key]==pre[key],key
for key in ['status','runId','totalScanned','targetCount','candidatesFound','runtimeIdentity','effectiveConfig']:assert post['3000/sweep/status'][key]==pre['3000/sweep/status'][key],key
out=dict(status='PASS',live_non_sqlite_files_verified=len(pre['live_hashes']),source_build_state_files=len(pre['protected_source_state']),protected_personal_native_checkpoint_files=len(manifest),personal_pid=91321,public_pid=22035,vite_pid=17880,live_automation=post['3001/catalog/automation-status'],scope='All measured writes stayed private;livequerycaches may change in memory;mutable catalog DB semantic control/status unchanged')
(R/'PRESERVATION.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='live_automation'})
