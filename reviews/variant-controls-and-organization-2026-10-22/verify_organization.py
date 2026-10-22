"""Verify approved moves, rollback bytes, navigation and protected payloads."""
import hashlib,json,re,tarfile
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2];R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
links=0
for name in ['docs/REPOSITORY_MAP.md','scripts/README.md','tests/README.md','reviews/README.md']:
 p=ROOT/name
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  dest=unquote(target.split('#')[0]);assert (p.parent/dest).exists(),(name,target);links+=1
moves=[]
for n in ['ORGANIZATION_BATCH1_RESULT.json','ORGANIZATION_BATCH2_RESULT.json']:
 d=json.loads((R/n).read_text());rows=d.get('moves',d.get('changes'))
 for x in rows:
  if x['source']==x['destination']:continue
  assert not (ROOT/x['source']).exists();assert sha(ROOT/x['destination'])==x.get('sha256',x.get('after_sha256'));moves.append(x)
for n in ['ORGANIZATION_BATCH1_RESULT.json','ORGANIZATION_BATCH2_REVIEWED.json']:
 d=json.loads((R/n).read_text());p=Path(d['backup']);assert sha(p)==d['backup_sha256']
 with tarfile.open(p) as t:
  assert t.getmembers();[t.extractfile(m).read() for m in t.getmembers() if m.isfile()]
inv=json.loads((R/'INVENTORY.json').read_text())['move_candidate_baseline'];changed=[]
for rel,h in inv.items():
 p=ROOT/rel
 if not p.exists() or sha(p)!=h:changed.append(rel)
allowed={x['source'] for x in moves}|{'CODEX_HANDOFF.md','REPO_ORGANIZATION_PLAN.md','PUBLIC_CATALOG_SYSTEM_SPEC.md','docs/PROJECT_STATUS.md','docs/catalog/v1/README.md'}
assert set(changed)<=allowed,changed
b=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022')
protected=json.loads((b/'personal-file-hashes.json').read_text());bad=[p for p,h in protected.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h];assert not bad,bad
baseline=json.loads((b/'baseline-hashes.json').read_text());native={p:h for p,h in baseline.items() if p.startswith(('native/','vendor/'))};bad=[p for p,h in native.items() if sha(ROOT/p)!=h];assert not bad,bad
out=dict(ok=True,index_links_checked=links,document_moves=len(moves),root_markdown=len(list(ROOT.glob('*.md'))),deleted_payloads=0,preexisting_payload_changes=changed,protected_files=len(protected),native_files=len(native))
(R/'FINAL_ORGANIZATION_VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
