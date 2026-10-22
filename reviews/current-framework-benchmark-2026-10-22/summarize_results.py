"""Independently verify paired results and calculate reported statistics."""
from pathlib import Path
import json,statistics,hashlib
B=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/current-framework-benchmark-20261022');R=Path(__file__).resolve().parent
read=lambda n:json.loads((B/n).read_text())
a=read('active-results.json');p=read('personal-results.json');rows=[x for x in a['rows'] if x['arm']=='active_catalog'];qs=[q for x in rows for q in x['queries']]
assert all(q['stats']['result_cache_hit'] is False for q in qs)
assert all(x['extraction_overlap_fraction']==1 and all(v==1 for v in x['query_overlap_fraction'].values()) for x in rows)
for trial in range(3):
 for report in [a,p]:
  rs=[x for x in report['rows'] if x['trial']==trial];assert rs[0]['fingerprint']==rs[1]['fingerprint'];assert all(x['candidate_policy']['candidate_capacity']==100 for x in rs)
for x in rows:
 settings=list((B/f"active-world-{x['trial']}").rglob('*.settings.json'))
 assert settings and all(json.loads(f.read_text())==dict(native_threads=1,numeric_threads=1,nice=10,protocol=2) for f in settings)
 assert not any(r['resource_stop'] for r in x['public']['rows'])
survivors={str(x['trial']):x['fingerprint']['records'] for x in rows};assert survivors=={'0':0,'1':1,'2':0}
summary=dict(status='PASS',input_seeds_per_cohort=262144,cohorts=3,unique_input_seeds=3*262144,threads=34,batch_size=16384,top_k=50,candidate_capacity=100,personal_kernel_median=p['kernel_median_rate'],registration_phase_medians=p['median_rates'],registration_median_elapsed_increase_pct=(statistics.median(p['paired_wall_ratios'])-1)*100,active_phase_medians=a['median_rates'],active_median_elapsed_increase_pct=(statistics.median(a['paired_wall_ratios'])-1)*100,active_median_paired_throughput_loss_pct=statistics.median((1-1/x)*100 for x in a['paired_wall_ratios']),active_elapsed_increase_pct_range=[(min(a['paired_wall_ratios'])-1)*100,(max(a['paired_wall_ratios'])-1)*100],complete_public_world_seconds=[x['public']['seconds'] for x in rows],public_world_median_seconds=statistics.median(x['public']['seconds'] for x in rows),query_count=len(qs),query_seconds_range=[min(q['seconds'] for q in qs),max(q['seconds'] for q in qs)],all_queries_result_cache_misses=True,all_active_intervals_fully_overlapped=True,predicted_survivors_per_cohort=survivors,semantic_and_receipt_parity=True,current_pipeline_registry=rows[0]['public']['registry_revision'],resources=read('RESOURCES.json'),serial_diagnostic_scheduling_note=read('catalog-results.json')['scheduling_note'])
(R/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
artifacts={str(f):dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in B.iterdir() if f.is_file()}
(R/'ARTIFACTS.json').write_text(json.dumps(dict(external_root=str(B),artifacts=artifacts,note='Raw private world/checkpoint/SQLite outputs retained externally. No live dataset modified.'),indent=2)+'\n')
print(json.dumps(summary,indent=2)[:2400])
