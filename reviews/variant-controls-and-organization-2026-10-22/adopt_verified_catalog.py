"""Adopt the approved, independently audited successor; preserve the personal service."""
import json,os,signal,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];R=Path(__file__).resolve().parent
BASE=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/treasure-activation-approved-20261022');target=BASE/'catalog'
assert json.loads((R/'FINAL_SUCCESSOR_AUDIT.json').read_text())['status']=='PASS'
assert json.loads((R/'UI_VERIFICATION.json').read_text())['ok']
assert json.loads((R/'FINAL_ORGANIZATION_VERIFICATION.json').read_text())['ok']
def command(pid):return subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
personal=command(91321);vite=command(17880)
for pid,port,expected in [(21638,3081,str(target)),(18349,3001,'biome-expansion-approved-20261022/catalog-corrected')]:
 c=command(pid);assert 'seed_search.catalog.http_server' in c and f'--port {port}' in c and expected in c,c
 os.kill(pid,signal.SIGTERM)
 for _ in range(100):
  if subprocess.run(['ps','-p',str(pid)],stdout=subprocess.DEVNULL).returncode:break
  time.sleep(.1)
 else:raise RuntimeError('Owned server did not exit')
with (BASE/'public-final.log').open('ab') as log:
 p=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-u','-m','seed_search.catalog.http_server','--root',str(target),'--port','3001','--query-processes','2'],cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(BASE/'public-final.pid').write_text(str(p.pid)+'\n')
for _ in range(60):
 assert p.poll() is None,'Public startup failed'
 try:
  d=json.load(urllib.request.urlopen('http://127.0.0.1:3001/api/catalog/capabilities',timeout=2))
  if d.get('ok'):break
 except (OSError,TimeoutError):pass
 time.sleep(.5)
else:raise RuntimeError('Public startup readiness timeout')
for fid in ['structure.igloo_with_basement','structure.bastion_treasure']:assert next(x for x in d['registry_v3']['features'] if x['id']==fid)['available']
assert command(91321)==personal and command(17880)==vite
out=dict(ok=True,pid=p.pid,root=str(target),port=3001,personal_pid=91321,vite_pid=17880,rollback_root='/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/catalog-corrected')
(R/'ADOPTION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
