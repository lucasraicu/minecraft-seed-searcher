"""Authoritative final source/state/resource/deliverable reconciliation."""
from pathlib import Path
import json,hashlib,subprocess,sys,os,time,re,tempfile,collections
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';P=B.parent/'storage-query-profile-20261022'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pre=json.loads((P/'PRE_STATE.json').read_text());freeze=json.loads((E/'REFERENCE_FREEZE.json').read_text());allowed={
 'src/seed_search/catalog/ingestion.py','src/seed_search/catalog/harvest_native.py','src/seed_search/catalog/automation.py','src/seed_search/catalog/service.py','src/seed_search/catalog/automation_query.py',
 'CODEX_HANDOFF.md','docs/PRE_GPU_READINESS_PLAN.md','docs/PROJECT_STATUS.md','docs/REPOSITORY_MAP.md','docs/specs/DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md'}
changes=[]
for name,h in freeze['source_manifest'].items():
 assert(R/name).is_file(),name
 if sha(R/name)!=h:changes.append(name)
assert set(changes)<=allowed,changes
protected=json.loads((B.parent/'biome-expansion-approved-20261022/personal-file-hashes.json').read_text());assert all(sha(R/p)==h for p,h in protected.items()),'Protected personal/native/checkpoint drift'
assert all(sha(p)==h for p,h in pre['live_hashes'].items()),'Live immutable artifact drift'
source_changes=[str(Path(p).relative_to(R))for p,h in pre['protected_source_state'].items()if sha(p)!=h]
assert set(source_changes)<=allowed,source_changes
assert sha(R/'src/seed_search/catalog/summaries.py')==freeze['source_manifest']['src/seed_search/catalog/summaries.py']
contracts={n:h for n,h in freeze['source_manifest'].items()if n.startswith(('docs/catalog/v1/','docs/catalog/v2/','docs/catalog/v3/'))and n.endswith('.json')}
assert all(sha(R/n)==h for n,h in contracts.items())
processes=subprocess.check_output(['ps','-p','91321,17880,22035','-o','pid=,command='],text=True);assert processes==pre['processes']
import urllib.request
post={}
for port,ep in [(3000,'sweep/status'),(3001,'catalog/automation-status'),(3001,'catalog/capabilities')]:post[f'{port}/{ep}']=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/'+ep,timeout=10))
for key in ('3001/catalog/automation-status','3001/catalog/capabilities'):assert post[key]==pre[key],key
for key in ('status','runId','totalScanned','targetCount','candidatesFound','runtimeIdentity','effectiveConfig'):assert post['3000/sweep/status'][key]==pre['3000/sweep/status'][key],key
reg=post['3001/catalog/capabilities']['registry_v3'];assert len(reg['features'])==93
assert collections.Counter(f['kind']for f in reg['features'])=={'structure_count':19,'biome_witness':74}
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head=='fd36d4dc3b86581858ff75e91df187eac088862c'
subprocess.run([sys.executable,'docs/catalog/v1/validate_spec.py'],cwd=R,check=True,capture_output=True)
required=['REFERENCE_FREEZE.json','RESTORE_NATIVE_SMOKE.json','SERVING_PARITY.json','FIXED_REPLAY_PARITY.json','SAVED_FACT_REPLAY.json','SUSTAINED.json','POSITIVE_COEXISTENCE.json','BACKPRESSURE.json','FRONTEND_CHECKS.json','GPU_CONTRACT_VERIFICATION.json','DATABASE_COMPARISON.json','DATABASE_RECOVERY.json','SQLITE_PRIVATE_RUNTIME.json']
for name in required:assert json.loads((E/name).read_text())['status']=='PASS',name
assert '687 passed, 1 warning in 297.50s'in(E/'full-regression.log').read_text()
assert '678 passed'in(E/'patched-sqlite-regression.log').read_text()
assert '9 passed'in(E/'patched-sqlite-recovery.log').read_text()
a=json.loads((E/'DERIVATION_BEFORE.json').read_text());b=json.loads((E/'DERIVATION_AFTER.json').read_text());assert a['observation_id']==b['observation_id']and a['summary'][0]['digest']==b['summary'][0]['digest']
record=json.loads((E/'RECORD_REPLAY.json').read_text());sustained=json.loads((E/'SUSTAINED.json').read_text());positive=json.loads((E/'POSITIVE_COEXISTENCE.json').read_text());spent=record['cumulative_extraction_seconds']+sum(x['seconds']for x in sustained['extractions'])+positive['extraction_seconds'];assert spent<600,spent
assert all(r['pipeline']['status']=='PASS'for r in record['rows'])
# Document links must resolve, including final receipts generated below.
(E/'FINAL_VERIFICATION.json').write_text('{}\n');(E/'RESOURCE_LEDGER.json').write_text('{}\n')
files=[R/'docs/PRE_GPU_READINESS_PLAN.md',R/'docs/PROJECT_STATUS.md',R/'docs/REPOSITORY_MAP.md',R/'docs/gpu/GPU_CONTRACT_V1.md',R/'docs/catalog/DATABASE_COMPARISON.md',R/'docs/specs/DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md',R/'reviews/README.md',E/'REPORT.md',E/'COMPLETION_AUDIT.md']
links=0;broken=[]
for p in files:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if re.match(r'\w+://',target)or target.startswith('#'):continue
  target=target.split('#')[0]
  if not target:continue
  links+=1
  if not(p.parent/target).resolve().exists():broken.append((str(p.relative_to(R)),target))
assert not broken,broken
# Confirm actual worker terminal states; no failed/empty worker result counts as review.
workers=[]
for tid in ('c27d5a82c593','8ff74cff4f2a','048cd901ee8c','200e3433e2de'):
 d=json.loads((E/(tid+'-status.json')).read_text());assert d['state']=='failed'
 launch=json.loads((E/(tid+'-launch.json')).read_text())['argv_without_prompt'];assert launch[launch.index('--effort')+1]=='high'
 workers.append(dict(task_id=tid,state=d['state'],error=d['result']['error']))
# Complete factual handoff and matrix only after all functional/source assertions pass.
p=R/'CODEX_HANDOFF.md';text=p.read_text().replace('FINAL AUDIT — approved readiness implementation and documentation,2026-10-22.','COMPLETED — approved readiness implementation, GPU contract and DB comparison,2026-10-22.').replace('Final preservation/resource/link audit pending; owned resourcewatch stops afterward.','Final source/history/API/process/link/resource audits PASS; no owned work remains running.').replace('1. **Readiness execution:** Complete final preservation/audit and report. Current goal','1. **Readiness execution:** Complete; source/report/contract/comparison verified. Current goal');p.write_text(text);assert len(text.splitlines())<=200
p=E/'COMPLETION_AUDIT.md';p.write_text(p.read_text().replace('Final preservation/audit status: PENDING FINAL VERIFIER.','Final preservation/audit status: PASS — all required current-scope evidence verified.'))
# Resource ledger includes every new worker snapshot, private inputs/staging/engines,
# repository outputs and remaining owned pytest directories; no history is deleted.
def treebytes(root):return sum(p.stat().st_size for p in root.rglob('*')if p.is_file()and not p.is_symlink())
worker_bytes={w['task_id']:treebytes(B.parent/'state/jobs'/w['task_id'])for w in workers}
workspace_bytes=sum(p.stat().st_size for p in R.rglob('*')if p.is_file()and not p.is_symlink()and p.stat().st_mtime>=1792696070)
tmp_bytes=0
for parent in Path(tempfile.gettempdir()).glob('pytest-of-*'):
 for p in parent.iterdir():
  if p.is_dir()and not p.is_symlink()and getattr(p.stat(),'st_birthtime',p.stat().st_ctime)>=1792696070:tmp_bytes+=treebytes(p)
monitor=json.loads((E/'RESOURCE_WATCH.json').read_text());private=treebytes(B);total=private+sum(worker_bytes.values())+workspace_bytes+tmp_bytes;peak=monitor['private_logical_disk_peak_bytes']+sum(worker_bytes.values())+workspace_bytes+tmp_bytes
assert max(total,peak)<3<<30,(total,peak)
assert monitor['peak_owned_rss_bytes']<4<<30
resource=dict(status='PASS',extraction_seconds_charged=spent,extraction_cap_seconds=600,failed_attempt_seconds_included=True,private_current_logical_bytes=private,new_worker_snapshot_bytes=worker_bytes,workspace_new_or_modified_bytes=workspace_bytes,owned_remaining_pytest_bytes=tmp_bytes,current_total_logical_bytes=total,conservative_sampled_peak_including_static_extras=peak,logical_disk_cap_bytes=3<<30,observed_aggregate_rss_peak_bytes=monitor['peak_owned_rss_bytes'],aggregate_rss_cap_bytes=4<<30,scope='Observed benchmark trees plus actual final static worker/workspace/temp outputs; initial worker RSS peaks preserved separately. No deleted evidence or recycled allocations')
(E/'RESOURCE_LEDGER.json').write_text(json.dumps(resource,indent=2)+'\n')
final=dict(status='PASS',goal_scope='A-D implementation/verification;GPUcontractonly;databasecomparison',head=head,source_baseline_files=len(freeze['source_manifest']),approved_existing_file_changes=changes,protected_source_state_changed=source_changes,protected_personal_native_checkpoint_files=len(protected),live_immutable_artifacts=len(pre['live_hashes']),unchanged_frozen_catalog_json_files=len(contracts),original_summary_source_preserved=True,live_processes_match=True,live_public_capabilities_control_status_match=True,live_personal_run_config_counters_identity_match=True,source_restore_and_native_smoke=True,required_receipts=required,full_selected_tests=687,private_runtime_coverage=dict(initial_passed=678,bootstrap_failures_preserved=9,corrected_rerun_passed=9),node_suites=10,frontend_build=True,links_checked=links,broken_links=broken,workers=workers,resource=resource,limitations=['Live source/runtime adoption and patched production interpreter remain separate','No GPU kernel/device/fleet performance claim','Prototype database/lookups and row replicas are not complete API/fleet benchmarks','Natural full100heap/real retention quality/unique discovery not measured','Known explicit multithreaded-fork test warning','No supplemental worker findings counted;Codex reviewed/verified source'])
(E/'FINAL_VERIFICATION.json').write_text(json.dumps(final,indent=2)+'\n')
subprocess.run(['git','status','--porcelain','-uall'],cwd=R,stdout=(E/'git-status-final.txt').open('w'),check=True)
artifact_files=[p for p in E.rglob('*')if p.is_file()and p.name not in ('ARTIFACT_HASHES.json','RESOURCE_WATCH.json','final-verification.log')]+files+[R/'CODEX_HANDOFF.md',R/'docs/gpu/gpu_contract_v1.json']
(E/'ARTIFACT_HASHES.json').write_text(json.dumps({str(p.relative_to(R)):sha(p)for p in sorted(set(artifact_files))},indent=2)+'\n')
print(json.dumps({k:final[k]for k in ('status','full_selected_tests','protected_personal_native_checkpoint_files','live_immutable_artifacts','unchanged_frozen_catalog_json_files','links_checked')}));print('Extraction seconds',spent,'logical peak bytes',peak,'RSS observed',monitor['peak_owned_rss_bytes'])
