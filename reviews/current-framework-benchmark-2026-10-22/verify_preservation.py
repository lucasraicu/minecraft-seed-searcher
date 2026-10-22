"""Read-only after-benchmark source, snapshot, run and service preservation checks."""
from pathlib import Path
import hashlib,json,subprocess,sys,urllib.request
ROOT=Path(__file__).resolve().parents[2];B=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/current-framework-benchmark-20261022');R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pre=json.loads((B/'PRE_STATE.json').read_text());bad=[p for p,h in pre['protected_hashes'].items() if sha(p)!=h];assert not bad,bad
immutable=json.loads((B/'IMMUTABLE_PRE_HASHES.json').read_text());bad=[p for p,h in immutable.items() if sha(p)!=h];assert not bad,bad
live=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/treasure-activation-approved-20261022/catalog')
actual={str(p) for folder in ['automation/objects','automation/snapshots','automation/generations'] for p in (live/folder).rglob('*') if p.is_file()}|{str(live/'automation/current.json')};assert actual==set(immutable)
protected=json.loads(Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/personal-file-hashes.json').read_text());assert all(sha(ROOT/p)==h for p,h in protected.items())
proc=subprocess.check_output(['ps','-p','91321,17880,22035','-o','pid=,command='],text=True);assert proc==pre['processes']
post={}
for port,endpoint in [(3000,'system/info'),(3000,'sweep/status'),(3001,'catalog/automation-status'),(3001,'catalog/capabilities')]:post[f'{port}/{endpoint}']=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/'+endpoint,timeout=10))
for name in ['3000/system/info','3001/catalog/automation-status','3001/catalog/capabilities']:assert post[name]==pre[name],name
for k in ['runId','totalScanned','targetCount','status','runtimeIdentity','candidatesFound','effectiveConfig']:assert post['3000/sweep/status'][k]==pre['3000/sweep/status'][k],k
# Registration must not have created/executed public extraction work.
import sqlite3
for q in sorted(B.glob('queue-only-*'))+sorted(B.glob('active-handoff-*')):
 with sqlite3.connect(q/'harvest.sqlite') as conn:assert conn.execute('SELECT count(*) FROM jobs').fetchone()[0]==0
 assert not (q/'staging').exists() and not (q/'automation').exists()
thermal=subprocess.run(['pmset','-g','therm'],capture_output=True,text=True)
report=dict(status='PASS',source_build_state_files=len(pre['protected_hashes']),immutable_catalog_files=len(immutable),protected_personal_checkpoint_native_files=len(protected),personal_pid=91321,public_pid=22035,vite_pid=17880,snapshot_id='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d',public_automation_unchanged=post['3001/catalog/automation-status'],registration_queues_have_zero_jobs=True,thermal_after=thermal.stdout)
(R/'PRESERVATION.json').write_text(json.dumps(report,indent=2)+'\n');(B/'POST_STATE.json').write_text(json.dumps(post,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['public_automation_unchanged','thermal_after']}))
