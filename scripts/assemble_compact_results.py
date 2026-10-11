"""Assemble final evidence without modifying frozen computational inputs."""
import json
import statistics as st
from pathlib import Path
from collections import defaultdict
from seed_search.realm.store import RealmStore
from seed_search.realm.capabilities import identity

ROOT=Path('runs/compact-implementation-2026-10-10')
def read(name):return json.loads((ROOT/name).read_text())
def med(rows,key):return st.median(r[key] for r in rows)

def main():
 audit=read('detection-audit.json');completion=read('completion-verification.json');end=read('end-parity.json');raw=read('raw-benchmark.json')
 persisted=read('raw-selection-final.json');selection=read('selection/experiment.json');terrain=read('inventory-terrain-followup.json')
 names=['final-reference-border-tuning','final-eligibility-border-tuning','final-eligibility-world-tuning',
        'final-reference-border-holdout','final-eligibility-border-holdout','final-eligibility-world-holdout',
        'final-complete-border','final-schedule-9x4','final-schedule-2x18']
 benchmarks={name:read(name+'/benchmark.json') for name in names}
 chosen=benchmarks['final-eligibility-world-holdout'];ref=benchmarks['final-reference-border-holdout']
 lines=['# Compact search implementation results','',
 '10 October 2026. Geometry remains **4000×4000 discovery, 1536×1536 Overworld and 896×896 Nether**, with exact fractional Stronghold/8 centers. The native filters, deferred inventory, stable biome sampling, recovery integration and bounded sibling allocator are implemented. **Independent full64 remains the default.** No new million-input or full32 sweep ran.','',
 '## Accuracy contract','',
 'A first-start observation uses the same pinned placement and viability rules as a complete scan and stops at the first positive. It establishes bounded **predictor presence**, not a total count, full footprint, a remnant crossing the border from an outside start, or actual Bedrock generation. Misses remain PENDING. The complete native start API and `inventory --all-starts --candidate` remain available. Stronghold discovery is unchanged and retains its known recall limitations; the existing Ancient City/Bastion fixture disagreements remain disclosed.','',
 f"The 64-seed, four-boundary audit made **{audit['checks']:,} comparisons with zero differences**, including {21*64*4:,} first-witness tests across 21 families (Stronghold stays fully enumerated). All 22 exposed structure families had positive cases. Every one of the **66 IDs marked generating by the pinned model** was observed. The other 28 named IDs are not marked currently generating; this is a catalog distinction, not an absence claim. End predictions use a correct End generator; old End raw-start coordinates were checked separately from corrected viability.", '',
 f"Frozen-lattice qualification, pending reasons and bounds matched across both 1000-input cohorts ({completion['decision_anchor_checks']:,} anchor/completion checks; zero differences). Completing 64 sampled inventories reproduced the reference's canonical biome counts, first coordinates and original bonuses. Newly supported buried treasure deliberately contributes its configured bonus. {completion['thread_point_checks']:,} point comparisons matched at 1/4/18 native threads. The final End optimization added {end['checks']:,} scalar/batch comparisons against the saved correct pre-optimization End adapter, with zero differences.", '',
 'Scoring inventory COMPLETE means predictor family presence and a complete **defined canonical biome sample**. Individual first-witness records still say remaining starts are unqueried. Supplemental witnesses and refined points have separate provenance and never inflate canonical frequency counts. No actual-world or exhaustive biome coverage claim is made. Monster rooms, End gateways and terrain/decorator features (ravines, lava lakes, geodes and desert wells) lack a reviewed bounded adapter and remain explicitly unsupported.','',
 '## Implemented changes','',
 '- Mineshaft first-witness API with exact +8 chunk-center bounds and reference RNG; complete scans use an exact portable four-lane MT kernel with scalar fallback.','- Other regional families use first viable starts when once-per-family presence suffices. Shared Fortress/Bastion placement avoids duplicated complementary draws. Audited regular-region halos are trimmed; Stronghold halos remain.','- Wooded eligibility visits dispersed 16-point batches and stops at two families. Exact full-seed point caching, world-aligned grids, retained in-border witnesses and bounded 128-point refinement prevent the known moving-border witness loss. NULL climate hints preserve biome tie behavior.','- Correct End generator and End biome-name classes; dense End queries share one bounded height map. Supplemental Nether/End inventories stop when all active model classes have witnesses, retaining unresolved misses.','- Transactional inventory tasks have fenced leases, recovery and atomic patches. Partial scores retain uncertainty. Terrain and final verification complete scoring inventories before use; generation-free rescoring and exports preserve partial status.','- Persistence avoids repeated whole-batch JSON decoding/encoding and streams a versioned content digest. Old digest/checkpoint semantics remain guarded.','- Native lower32 presence, capped-score and complete modes have separate contracts. Batched raw selection and a versioned exploration permutation remove per-row Python ranking work. Geometry ranking remains experimental; adaptive siblings use durable 1/4/16 rounds and an exploration reserve. Canonical full64 manifests and actual spawned-worker resume are tested.','',
 '## Persisted throughput','',
 'Three timing trials per row. Reference and frozen-lattice eligibility trials were counterbalanced on identical manifests. Each cohort has 1000 distinct full64 inputs; timing repeats add evaluations, not new independent seeds. Baseline timing includes process startup and SQLite persistence, and excludes deferred inventory, terrain and BDS.','',
 '| Workload | Inputs/sec median | Worker CPU sec/1000 | Biome points | Predicted anchors | Distinct qualifying seeds | Disk MiB |',
 '|---|---:|---:|---:|---:|---:|---:|']
 for name,rows in benchmarks.items():
  row=rows[1];anchors=row['status']['candidate_counts'].get('PREDICTED',0)
  lines.append(f"| {name} | {med(rows,'inputs_per_second'):.1f} | {med(rows,'worker_cpu_seconds'):.3f} | {row['biome_points']:,} | {anchors} | {row['qualified_seeds']} | {med(rows,'bytes')/2**20:.2f} |")
 lines+=['','The complete profile includes newly supported buried-treasure enumeration and fuller sampling provenance; it measured 378 inputs/sec and did not outperform the old complete reference. First-witness speedups do not make exhaustive inventory free. The active world-grid holdout is approximately 1.50× the reference; the exact frozen-lattice pass is the one that met the ≥1.5× decision-preserving gate.']
 ratios={cohort:med(benchmarks[f'final-eligibility-border-{cohort}'],'inputs_per_second')/med(benchmarks[f'final-reference-border-{cohort}'],'inputs_per_second') for cohort in ('tuning','holdout')}
 lines+=['',f"Exact-contract persisted speedup: **{ratios['tuning']:.2f}× tuning, {ratios['holdout']:.2f}× holdout**. The ≥1.5× gate is {'met' if min(ratios.values())>=1.5 else 'not met consistently'}. Active world-grid/refinement changes are separately versioned: {len(completion['sampling_revision_changes']['tuning'])} tuning and {len(completion['sampling_revision_changes']['holdout'])} holdout anchors changed qualification; details are in completion-verification.json. The schedule with the best bounded wall throughput remains the selected default; 30×1 avoids multiplying process/native thread counts beyond 36.",'',
 'The older million-input result, 173.37 inputs/sec, used 5000/2688/1024 geometry and is not the denominator of this compact optimization speedup. These final measurements are bounded pilots, not a new massive benchmark.','',
 '### Filtering stages','',
 'Rates below are calls divided by summed worker service seconds on the median active holdout trial. They describe serial service work, not additional independent seeds/sec at each gate. Later stages receive only surviving anchors.','',
 '| Stage | Calls | Summed worker sec | Calls/service sec |', '|---|---:|---:|---:|']
 representative=sorted(chosen,key=lambda r:r['seconds'])[1]
 path=Path(representative.get('path',ROOT/'final-eligibility-world-holdout'/f"trial-{representative['trial']}"))
 with RealmStore(path,resume=True) as store:results=list(store.iter_results())
 calls={'stronghold':1000,'initial_fortress':1000}
 for r in results:
  for c in r['anchors']:
   calls['final_nether_pair']=calls.get('final_nether_pair',0)+1
   for family in ('ancient_city','village','trial_chamber','mineshaft'):
    if c['required_structures'][family].get('verification')!='DEFERRED':calls[family]=calls.get(family,0)+1
   if c.get('biomes') is not None:calls['wooded_biomes']=calls.get('wooded_biomes',0)+1
 for stage,n in calls.items():
  seconds=representative['stages'][stage];lines.append(f'| {stage} | {n} | {seconds:.4f} | {n/seconds:,.0f} |')
 inventory=completion['completion_sample'];peak=max(r['status']['memory']['peak_process_tree_rss_bytes'] for rows in benchmarks.values() for r in rows)
 lines+=['',f"Expanded scoring inventory (22 supported families plus unsupported monster-room record and supplemental dimensions): sampled median **{st.median(r['seconds'] for r in inventory)*1000:.2f} ms/anchor**, CPU {st.median(r['cpu_seconds'] for r in inventory)*1000:.2f} ms/anchor, separately paid after eligibility. It is a sample, not all deferred tasks completed. The durable terrain follow-up completed 48 inventory tasks for 24 sampled anchors. Deferred cost has not vanished; completing every pending anchor would add work. Peak sampled process-tree RSS was {peak/2**30:.2f} GiB, plus the configured 8 GiB Docker reserve, below the 25/30 GiB target/ceiling. RSS may double-count shared pages.",'',
 '## Structure compute audit','',
 'Median milliseconds in the 1536-sized control square, 64 seeds including negatives. Reference is a direct old C call; current full/witness values include Python wrapper overhead, so ratios are local scan measurements rather than pipeline speedups. End comparison is raw starts versus corrected viable scans, not an old viable-scan speed ratio.','',
 '| Family | Reference full ms | Current full ms | First witness ms |', '|---|---:|---:|---:|']
 for name,r in audit['structures'].items():
  a=st.median(r['reference_ms'][::4]);b=st.median(r['complete_ms'][::4]);c=st.median(r['witness_ms'][::4]) if r['witness_ms'] else None
  lines.append(f"| {name} | {a:.4f} | {b:.4f} | {c:.4f} |" if c is not None else f'| {name} | {a:.4f} | {b:.4f} | unchanged full enumeration |')
 lines+=['','Mineshaft fell from 6.01 ms to 0.126 ms (~48×) in this control; complete vector scans took 3.31 ms (~1.81×). Buried treasure was another major outlier (3.91→0.272 ms, ~14×): dense candidate regions and repeated biome checks caused the cost. Shipwrecks (1.15→0.331 ms, ~3.5×) and ocean ruins (0.237→0.061 ms, ~3.9×) also benefited. Shipwreck/monument viability retains its necessary nearby-biome/structure tests. Rare negative mansions gained little; accuracy checks were not removed.','',
 'OW biome classes share climate/noise work rather than having a separate expensive algorithm per biome. Most scalar OW calls were about 8 μs. End scalar calls were a separate outlier, about 17–35 μs, because of repeated height maps; the final dense 3969-point End batch was **6.7× faster**. Minimal supplemental witnesses further reduce the query count. The pinned End planar Voronoi helper is preserved exactly; the Overworld 3D nearest-cell rule must not replace it.','',
 '## Lower32 / upper32 result','',
 f"The exact mode benchmark checked {raw['parity_checks']:,} layout-mode comparisons over 262,144 distinct dispersed layouts, at 18 and 36 threads, three counterbalanced trials. Complete counts equal reference; capped values equal min(count,32); presence equals count>0. **{100*raw['records'][0]['necessary_missing']/262144:.3f}%** failed the necessary predicate. The original expectation of 99.9% lossless rejection is not supported by this geometry.",'',
 '| Mode / implementation | Layouts/sec | Full32 forecast min |', '|---|---:|---:|']
 for mode in ('reference','complete','capped','presence'):
  rows=[r for r in raw['records'] if r['threads']==36 and r['mode']==mode]
  lines.append(f"| Native {mode}, 36 threads | {med(rows,'layouts_per_second'):,.0f} | {med(rows,'full32_compute_minutes'):.1f} |")
 for r in raw['persisted']:lines.append(f"| Old persisted {r['mode']} selection | {r['inputs_per_second']:,.0f} | {r['full32_end_to_end_minutes']:.1f} |")
 for mode in ('presence','capped'):
  rows=[r for r in persisted['records'] if r['mode']==mode]
  lines.append(f"| Final persisted {mode} selection | {med(rows,'inputs_per_second'):,.0f} | {med(rows,'full32_end_to_end_minutes'):.1f} |")
 lines+=['','Forecasts extrapolate bounded measurements and exclude full64 siblings, inventory, terrain and BDS. The 45-minute target needs 1.591 million layouts/sec end to end. Native presence passed that compute rate; the final persisted presence median forecast of 49.6 minutes still **misses the 45-minute target**. Capped ranking remains far slower. Batched selection improved persisted presence about 10× and capped ranking about 2.9×. These forecasts do not justify a full32 ranking sweep.','',
 'Village raw presence is guaranteed at every permitted center at widths ≥944; Ancient City at ≥624. Both are universal at 1536, so their old capped ranking contributes a constant 64. Fortress/Bastion placements are complementary and common in the envelope; mere presence does not prove co-location at an actual Stronghold. Counts cannot resolve full64 biome viability, wooded families, Trial placement, Stronghold recall or terrain. Upper32 siblings change those unresolved properties, so a promising low32 is a family of possibilities rather than a known good world. Mineshaft starts are common as well; adding an expensive raw Mineshaft veto offers little selectivity.','',
 f"The four-arm experiment used two disjoint 4096-layout pools, three allocation keys and at most 256 selected layouts / 4096 full64 inputs per arm. It performed {sum(r['inputs'] for r in selection['records']):,} evaluations of {len(set(row['seed'] for r in selection['records'] for row in r['rows'])):,} distinct full64 seeds. Adaptive rounds used about 1400 inputs/arm and did not force expenditure of the maximum. Entire raw/feature CPU was charged to each ranked arm/key without amortization. CPU prefixes apportion parent work per input; they are analytical budget truncations of completed bounded runs, not live CPU stops.",'',
 '| Held-out allocation key | Uniform / independent anchors | Legacy / independent anchors | Geometry / independent anchors |', '|---|---:|---:|---:|']
 for r in selection['analysis']:
  if r['pool']=='holdout':lines.append('| '+r['key']+' | '+' | '.join(f"{r['ratios'][m]['ratio']:.3f}×" for m in ('uniform','legacy','geometry'))+' |')
 lines+=['','These are matched measured CPU-prefix yield ratios. Geometry feature construction alone exhausted the smallest holdout CPU budgets, hence zero evaluated siblings at those prefixes; it did find richer layouts when more CPU was spent. The layout-cluster bootstrap intervals and complete yield curves are in selection/experiment.json. No arm met the ≥20% heldout advantage with an interval excluding no advantage. More reuse could amortize feature cost, but that benefit has not been demonstrated. Independent full64 is retained.','',
 'All four arms received the same two-anchor/eight-refinement V1/V2 budget for each of three heldout keys (24 anchors total). Counts below are distinct anchors with any predicted geometry pass, not verified formations; many durable refinement tasks remain pending.','',
 '| Arm | Sampled anchors | Anchors with V1 geometry pass | Anchors with V2 geometry pass |', '|---|---:|---:|---:|']
 grouped=defaultdict(lambda:{'anchors':0,'v1':set(),'v2':set()})
 for r in terrain:
  g=grouped[r['arm']];g['anchors']+=len(r['anchors'])
  for v in r['variant_results']:
   if v['result'].get('geometry_pass'):g[v['variant']].add(v['candidate_id'])
 for name,g in grouped.items():lines.append(f"| {name} | {g['anchors']} | {len(g['v1'])} | {len(g['v2'])} |")
 lines+=['','This sample cannot demonstrate terrain noninferiority or verified-world advantage. No new BDS worlds were generated: the CPU adoption gate failed and no fully verified nomination was established. Generated-world advantage remains unmeasured. The deliberately interrupted serial follow-up is retained separately and excluded from the matched sample.','',
 '## Biomes observed','',
 'Names below are pinned-predictor IDs observed in the dense surface/cave-layer/dimension audit. End classes are internal model names rather than certified Bedrock biome strings.','']
 for dimension,label in ((0,'Overworld'),(-1,'Nether'),(1,'End')):
  active=[r for r in audit['catalog'] if r['generates'] and r['dimension']==dimension]
  lines.append(f"**{label} ({len(active)}):** "+', '.join(sorted(r['name'] for r in active))+'.');lines.append('')
 lines+=['## Verification and evidence','',
 'Final verification: **658 tests passed in 98.87 seconds**, native ASan/UBSan PASS, exact decision/completion and End/thread comparisons PASS, doctor and CLI baseline/inventory/full-start/rescore/export/raw/sibling/adaptive smoke checks PASS, and git diff --check PASS. Frozen source/native/config integrity checked 113 unchanged files; 11 linker intermediate .o files were intentionally not archived. Timing manifests retain their measured identities. The later explicit Stronghold full-start audit fix was exercised by the final tests and fresh CLI run; the cheap eligibility path is unchanged. Sanitizer checks use the serial path; Apple leak detection is disabled and the run is not an exhaustive race/leak proof. New computational identities reject incompatible resumes. Historical runs and the frozen reference are preserved.','',
 '- [Detailed audit](runs/compact-implementation-2026-10-10/detection-audit.json)',
 '- [Completion and sampling changes](runs/compact-implementation-2026-10-10/completion-verification.json)',
 '- [Raw-mode benchmark](runs/compact-implementation-2026-10-10/raw-benchmark.json)',
 '- [Final persisted selection](runs/compact-implementation-2026-10-10/raw-selection-final.json)',
 '- [Four-arm selection experiment](runs/compact-implementation-2026-10-10/selection/experiment.json)',
 '- [Inventory / terrain follow-up](runs/compact-implementation-2026-10-10/inventory-terrain-followup.json)',
 '- [Native safety](runs/compact-implementation-2026-10-10/safety/report.json)',
 '- [End parity](runs/compact-implementation-2026-10-10/end-parity.json)',
 '- [Final tests](runs/compact-implementation-2026-10-10/full-tests-final.log)','']
 lines+=['- [CLI checks](runs/compact-implementation-2026-10-10/cli-final.json)', '- [Reference integrity](runs/compact-implementation-2026-10-10/reference-integrity.json)','']
 text='\n'.join(lines);Path('COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md').write_text(text)
 (ROOT/'REPORT.md').write_text(text.replace('](runs/compact-implementation-2026-10-10/', ']('))
 (ROOT/'final-summary.json').write_text(json.dumps({'backend':identity(),'speedups':ratios,'benchmarks':benchmarks,
   'accuracy_checks':{'all_family':audit['checks'],'end':end['checks'],'thread':completion['thread_point_checks'],'differences':len(completion['differences'])},
   'selection_default':'independent full64','actual_generation_verified':False},indent=2)+'\n')
 print('Wrote COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md',flush=True)

if __name__=='__main__':main()
