"""Read-only derivation from frozen probes; no native/game execution or exclusions."""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.generalization_biome_probe import compare_biomes,summarize_biomes
from scripts.generalization_structure_probe import assess_locates,summarize_structures
from seed_search.realm.structure_coordinates import project_navigation_reference

def require(condition, message):
 if not condition:
  raise ValueError(message)

def analyze(campaign, partial=False):
 BASE=Path(campaign)
 raw=(BASE/'manifest.json').read_bytes();sha=hashlib.sha256(raw).hexdigest();manifest=json.loads(raw)
 require(sha==(BASE/'manifest.sha256').read_text().strip(), 'Manifest checksum differs')
 worlds=[];mismatches=[];rejected_matches=[];discovery=[];all_structure_rows=[];all_biome_rows=[]
 ledger={r['index']:r for r in json.loads((BASE/'game/ledger.json').read_bytes())}
 for world in manifest['worlds']:
  entry=ledger.get(world['index'],{})
  if entry.get('state')!='complete':
   if partial:continue
   raise ValueError('World ledger not complete '+str(world['index']))
  path=BASE/'game'/entry.get('report_path',f'world-{world["index"]:02}/report.json')
  if not path.exists():
   if partial:continue
   raise ValueError('Missing world '+str(world['index']))
  report_raw=path.read_bytes()
  require(hashlib.sha256(report_raw).hexdigest()==entry.get('report_sha256'), 'Report checksum differs')
  report=json.loads(report_raw)
  if report['status']!='observed':
   if partial:continue
   raise ValueError('World not observed '+str(world['index']))
  require(all(report[k] is True for k in ('clean_shutdown','owned_container_removed','save_confirmed','game_build_observed')), 'Lifecycle verification failed')
  require(report['seed']==world['seed'] and report['manifest_sha256']==sha and report['image_id']==manifest['image_id'], 'Report identity differs')
  require(report['world_identity']['seed']==world['seed'] and report['world_identity']['api']==manifest['script_api'] and report['world_identity']['players']==0, 'Observed world identity differs')
  settings=Path(report.get('work_directory', str(path.parent/'worlds/world')))/'server.properties'
  require(hashlib.sha256(settings.read_bytes()).hexdigest()==report['settings_sha256'], 'Settings checksum differs')
  require(hashlib.sha256((path.parent/'observer.js').read_bytes()).hexdigest()==report['observer_sha256'], 'Observer checksum differs')
  console=(path.parent/'console.log').read_text()
  require('Version: 1.26.52.3' in console, 'Missing observed BDS version')
  raw_batches=[json.loads(line.split('GENERALIZATION_RESULT ',1)[1]) for line in console.splitlines() if 'GENERALIZATION_RESULT ' in line]
  require(all(batch in raw_batches and batch['chunksAfterUnload']==0 for batch in report['biome_batches']), 'Biome batch console binding or cleanup differs')
  wanted={c['case_id']:c for c in world['structures']}
  require(set(wanted)=={q['case_id'] for q in report['queries']}, 'Locate case inventory differs')
  for q in report['queries']:
   c=wanted[q['case_id']]
   require(q['query']==c['origin'] and q['dimension']==c['dimension'] and q['command_id']==c['command_id'], 'Locate query identity differs')
   require(all(line in console for line in q['output']), 'Locate response missing from console')
  structures=assess_locates(world['structures'],report['queries'],prediction_revision=manifest['prediction_revision'],bds_build=manifest['bds_build'])
  biomes=[]
  for dim in ('overworld','nether','the_end'):
   predicted=[{k:v for k,v in p.items() if k!='dimension'} for p in world['predictions'] if p['dimension']==dim]
   observed=[r for batch in report['biome_batches'] if batch['dimension']==dim for r in batch['rows']]
   require(len(predicted)==len(observed), 'Biome point inventory differs')
   rows=compare_biomes(predicted,observed,aliases=manifest['aliases'],non_comparable=manifest['non_comparable'])
   for row in rows:row.update(dimension=dim,seed=world['seed'],cohort=world['group'])
   biomes.extend(rows)
  for row in structures:row.update(seed=world['seed'],cohort=world['group'],rejection_basis=('removed_by_engine_fix' if world['group']=='targeted' else 'current_raw_placement_rejection') if row['disposition']=='rejected' else None)
  for row in structures:
   if row['disposition']=='rejected' and row['outcome'] in ('reference_exact','navigation_exact'):rejected_matches.append(row)
   if row['disposition']!='discovery' or row['reported'] is None:continue
   feature=row['structure_type'];p=row['reported'];inventory=world['inventory'][feature]
   raw_points={tuple(p) for p in inventory}
   nav=[]
   for point in inventory:
    v=project_navigation_reference(feature,*point,prediction_revision=manifest['prediction_revision'],bds_build=manifest['bds_build'],dimension=row['dimension'])
    if v is not None:nav.append((v.navigation_x,v.navigation_z))
   if tuple(p) in raw_points:relation='raw_inventory_reference'
   elif tuple(p) in set(nav):relation='declared_navigation_reference'
   elif max(abs(p[0]),abs(p[1]))>5120:relation='outside_inventory_envelope'
   elif row['grouped_command']:relation='grouped_subtype_unresolved'
   elif feature in ('stronghold','trial_chamber','trail_ruins','end_city'):relation='reference_semantics_unresolved'
   else:relation='possible_omission_requires_followup'
   discovery.append(dict(row,inventory_relation=relation))
  mismatches.extend(r for r in biomes if r['outcome']=='mismatch')
  all_structure_rows.extend(structures);all_biome_rows.extend(biomes)
  worlds.append(dict(index=world['index'],seed=world['seed'],cohort=world['group'],wall_seconds=report.get('cumulative_world_wall_seconds',report['wall_seconds']),structures=summarize_structures(structures),biomes=summarize_biomes(biomes)))
 cohorts={}
 for group in ('blind','targeted'):
  bs=[r for r in all_biome_rows if r['cohort']==group];ss=[r for r in all_structure_rows if r['cohort']==group]
  cohorts[group]=dict(worlds=sum(w['cohort']==group for w in worlds),biomes=summarize_biomes(bs),structures=summarize_structures(ss),biomes_by_dimension={dim:dict(collections.Counter(r['outcome'] for r in bs if r['dimension']==dim)) for dim in ('overworld','nether','the_end')})
 result=dict(revision='generalization-results-v1',status='partial' if partial else 'complete',manifest_sha256=sha,worlds=worlds,cohorts=cohorts,
  prediction_verdict=('counterexamples_observed' if rejected_matches or mismatches or
    any(r['inventory_relation']=='possible_omission_requires_followup' for r in discovery)
    else 'no_counterexample_observed_in_this_sample'),
  all_supported_features_verified=False,
  possible_over_rejections=rejected_matches,biome_mismatches=mismatches,independent_discovery=discovery,
  discovery_relations=dict(collections.Counter(r['inventory_relation'] for r in discovery)),
  biome_rows=all_biome_rows,structure_rows=all_structure_rows,
  policy_changes=[],generated_count=None,exhaustive_count=None,recall=None,
  limitations=['Blind and targeted seed groups and point-selection groups are separate; no population accuracy claim.',
  'Reference agreement and membership are not physical completeness or unique instance counts.',
  'No extra seed rejection or admission changes are made by this audit.'])
 if not partial:require(len(worlds)==len(manifest['worlds']), 'Incomplete cohort')
 (BASE/('partial-results.json' if partial else 'results.json')).write_text(json.dumps(result,indent=2)+'\n')
 return dict(completed=len(worlds),biomes=len(all_biome_rows),structures=len(all_structure_rows),possible_over_rejections=len(rejected_matches),biome_mismatches=len(mismatches),discovery_relations=result['discovery_relations'],game_wall_seconds=sum(w['wall_seconds'] for w in worlds))
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--partial',action='store_true')
 args=parser.parse_args();print(json.dumps(analyze(args.campaign,partial=args.partial)),flush=True)
