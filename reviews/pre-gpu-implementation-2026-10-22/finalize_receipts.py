"""Close audit receipts after final verification and monitor termination."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
final=json.loads((E/'FINAL_VERIFICATION.json').read_text());assert final['status']=='PASS'
owned=[]
for line in subprocess.check_output(['ps','-axo','pid=,command='],text=True).splitlines():
 parts=line.strip().split(None,1)
 if len(parts)!=2:continue
 pid=int(parts[0]);cmd=parts[1];exe=cmd.split()[0].lower()
 if pid!=os.getpid()and'python'in exe and(str(B)in cmd or'reviews/pre-gpu-implementation-2026-10-22/'in cmd):owned.append((pid,cmd))
assert not owned,owned
paths=['src/seed_search/catalog/'+n for n in ('ingestion.py','harvest_native.py','automation.py','service.py','automation_query.py','summaries_fast.py','read_views.py')]+['tests/catalog/'+n for n in ('test_ingestion_optimization.py','test_guarded_read_views.py','test_versioned_derivation.py')]+['tests/test_readiness_reserve_capacity.py']
final['implementation_sha256']={name:sha(R/name)for name in paths};final['final_owned_benchmark_processes']=[];final['resource_monitor_terminated']=True
(E/'FINAL_VERIFICATION.json').write_text(json.dumps(final,indent=2)+'\n')
old=json.loads((E/'ARTIFACT_HASHES.json').read_text());files={R/name for name in old}|{R/name for name in paths}|{p for p in E.rglob('*')if p.is_file()and p.name!='ARTIFACT_HASHES.json'}
manifest={str(p.relative_to(R)):sha(p)for p in sorted(files)};(E/'ARTIFACT_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n')
assert all(sha(R/name)==h for name,h in manifest.items())
assert len((R/'CODEX_HANDOFF.md').read_text().splitlines())<=200
print(json.dumps(dict(status='PASS',hashed_files=len(manifest),implementation_files=len(paths),owned_benchmarks_running=0,resource_monitor_stopped=True,final_extraction_seconds=final['resource']['extraction_seconds_charged'],logical_peak_bytes=final['resource']['conservative_sampled_peak_including_static_extras'])))
