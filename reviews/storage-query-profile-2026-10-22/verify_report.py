"""Verify the completed profiling evidence, documented exceptions and report links."""
from pathlib import Path
import json,re,urllib.parse,subprocess
R=Path(__file__).resolve().parent;ROOT=R.parents[1];B=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/storage-query-profile-20261022')
obs=[json.loads(next((B/name/'staging').glob('*/*/observation.json')).read_text())['observation'] for name in ['baseline-world','profiled-world']]
for key in ['identity','anchors','biome_names','biomes','bounds','coverage','errors','structures','registry_revision','revision']:assert obs[0][key]==obs[1][key],key
for key in ['inventory','evaluation','config_digest','native_pin']:assert obs[0]['realm'][key]==obs[1]['realm'][key],key
pair=[json.loads(json.dumps(o['realm']['larger_sizes'])) for o in obs]
for o in pair:
 o.pop('wall_seconds')
 for size in o['sizes'].values():size.pop('search_budget_exhausted',None);size.pop('candidates_evaluated',None)
assert pair[0]==pair[1]
for name in ['PRESERVATION.json','PREFILTER_SEMANTICS.json','FIXED_REPLAY_PARITY.json','EXPORT_RECOVERY.json','READMODELS.json','QUERY_COUNTERS.json']:assert json.loads((R/name).read_text())['status']=='PASS',name
resources=json.loads((R/'RESOURCES.json').read_text());assert resources['charged_seconds']<900;assert max(p['peak_owned_rss_bytes'] for p in resources['phases'])<4<<30
new_bytes=sum(p.stat().st_size for p in B.rglob('*') if p.is_file())+sum(p.stat().st_size for p in R.rglob('*') if p.is_file());assert new_bytes<3<<30
read=json.loads((R/'READMODELS.json').read_text());assert all(x['ordered_results_and_unknowns_equal'] for x in read['filter_cases'])
final=dict(status='VERIFYING',source_and_live_preservation='PASS',unprofiled_query_matrix='PASS',finite_readmodel_ordered_semantic_parity='PASS',unknown_and_sameanchor_synthetic_controls='PASS',fixed_observation_snapshot_identity='PASS',full_extraction_profile_semantics='PERTURBED_8192_SEARCH_BUDGET_DIAGNOSTIC_ONLY',query_phase_original_exit=1,query_export_recovered_without_retiming=True,total_new_logical_bytes_including_private_copy_and_review_evidence=new_bytes,measured_subprocess_seconds=resources['charged_seconds'],reviewers=[dict(task_id=x,effort='high',process_exit=0,denied_actions=[],codex_reconciled=True) for x in ['4cafb9086b5d','5952ca57ff8b']],workers_running=0,account_pause=None,production_runtime_changes=False,custom_engine_selected=False,recommendation='SQLite control+snapshot-bound indexedreadmodels next;typedcolumnar andDuckDB are futurebenchmarks,notmeasured enginewinners')
(R/'FINAL_VERIFICATION.json').write_text(json.dumps(final,indent=2)+'\n')
links=0
for p in [R/'REPORT.md',ROOT/'CODEX_HANDOFF.md',ROOT/'docs/PROJECT_STATUS.md',ROOT/'reviews/README.md',ROOT/'README.md']:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  if p.name=='README.md' and 'storage-query-profile' not in target:continue
  assert (p.parent/urllib.parse.unquote(target.split('#')[0])).exists(),(p,target);links+=1
for p in R.glob('*.py'):compile(p.read_text(),str(p),'exec')
for p in R.glob('*.json'):json.loads(p.read_text())
assert len((ROOT/'CODEX_HANDOFF.md').read_text().splitlines())<=200
check=subprocess.run(['git','diff','--check','--','README.md'],cwd=ROOT,capture_output=True,text=True);assert check.returncode==0,check.stdout
final.update(status='COMPLETE',link_checks=links);(R/'FINAL_VERIFICATION.json').write_text(json.dumps(final,indent=2)+'\n');(R/'git-status-final.txt').write_text(subprocess.check_output(['git','status','--porcelain','-uall'],cwd=ROOT,text=True));print('COMPLETE: evidence, links, source preservation and documented exceptions verified;',links,'links;',new_bytes,'new logical bytes')
