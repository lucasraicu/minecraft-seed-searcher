"""Verify the fresh five-pair validation receipts and summarize scoped rates."""
import hashlib,json,math,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'cpu-completion-2026-10-13'))
from summarize_final_holdout import bootstrap_geomean_ci

def main():
 pairs=[];ratios=[];rates=[];checkpoint=[]
 for i in range(5):
  root=HERE/'final-validation'/f'pair-{i:02d}'
  p=json.loads((root/'pair.json').read_text())
  assert p['mode']=='final' and p['start_index']==14345670000 and p['count']==100000
  assert p['order']==(['control','selected'] if i%2==0 else ['selected','control'])
  receipts=[json.loads((root/a/'receipt.json').read_text()) for a in ('control','selected')]
  for r in receipts:
   assert r['sqlite_integrity']=='ok' and r['checkpointed_completed_inputs']==100000 and r['retention_receipt_inputs']==100000
  assert receipts[0]['record_semantics_sha256']==receipts[1]['record_semantics_sha256']
  ratios.append(p['speedup_control_over_selected']);rates.append(p['selected']['external_cli_rate']);checkpoint.append(p['selected']['checkpointed_input_rate']);pairs.append(p)
 identity=HERE/'final-runtime-identity.json'
 result={'scope':'fresh counterbalanced heldout on final Python runtime; fixed policy acceptance/scoring with different filter order','cohort':[14345670000,14345770000],'count_per_arm':100000,'pairs':pairs,'paired_geomean_speedup':math.exp(statistics.mean(map(math.log,ratios))),'paired_bootstrap_95_ci':bootstrap_geomean_ci(ratios),'selected_median_external_inputs_per_second':statistics.median(rates),'selected_median_checkpointed_inputs_per_second':statistics.median(checkpoint),'all_coverage_integrity_and_semantic_checks_pass':True,'runtime_identity_sha256':hashlib.sha256(identity.read_bytes()).hexdigest()}
 (HERE/'final-heldout-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='pairs'}))
if __name__=='__main__':main()
