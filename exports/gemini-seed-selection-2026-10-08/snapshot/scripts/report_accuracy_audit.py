"""Recompute biome/terrain metrics and produce a bounded external comparison."""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib, json
import numpy as np
from seed_search.backend import Backend, biome_name, STRUCTURES, model_metadata
import seed_search._native as native

D=Path('runs/accuracy-audit')
plan=json.loads((D/'plan.json').read_text())
cb={i:(y,name) for i,y,name in json.loads((D/'chunkbase-points.compact.json').read_text())}
caves={r['id']:r for r in json.loads((D/'chunkbase-caves.json').read_text())}
normalize=lambda name:name.lower().replace(' ','_')
assert len(cb)==len(plan['points'])==159
rows=[]
for seed in plan['seeds']:
 with Backend(seed) as b:
  for i,v in enumerate(plan['points']):
   if v['seed']!=seed:continue
   v=dict(v,id=i)
   y,name=cb[i]
   v.update(chunkbase_marker_y=y,chunkbase_marker_biome=normalize(name))
   if v['mode']=='bottom':
    c=caves[i]
    assert c['min_y']<=v['sample_y']<=c['max_y']
    v.update(chunkbase_biome=normalize(c['biome']),chunkbase_cave_range=[c['min_y'],c['max_y']])
   else:v['chunkbase_biome']=normalize(name)
   v['biome_match']=v['local_biome']==v['chunkbase_biome']
   if v['mode']=='surface':
    h1,ids=b.heights([[v['x'],v['z']]],1)
    assert int(h1[0])==v['local_height'] and int(ids[0])==v['biome_id']
    h8,_=b.heights([[v['x'],v['z']]],8)
    proxy=float(b.grid(v['x'],v['z'],1,1)['approx_height'][0,0])
    v.update(height_delta=v['local_height']-y,local_biome_at_cb_height=biome_name(b.biome(v['x'],max(63,y+1),v['z'])),default_stride8_height=int(h8[0]),stride8_equals_stride1=int(h8[0])==v['local_height'],cheap_height_proxy=proxy,cheap_proxy_height_error=proxy-y,height_land_water_match=(v['local_height']>=63)==(y>=63),cheap_proxy_land_water_match=(proxy>=63)==(y>=63))
    v['biome_match_at_cb_height']=v['local_biome_at_cb_height']==v['chunkbase_biome']
   rows.append(v)
rows.sort(key=lambda v:v['id'])
source=dict(source_url='https://www.chunkbase.com/apps/seed-map',version='Bedrock 26.50 - 26.52',recorded_date='2026-10-07',source_kind='UI_predictions_not_in_game')
(D/'biome-terrain-comparison.json').write_text(json.dumps(dict(**source,points=rows),indent=2)+'\n')
s=[v for v in rows if v['mode']=='surface'];n=[v for v in rows if v['mode']=='nether'];c=[v for v in rows if v['mode']=='bottom']
e=np.array([v['height_delta'] for v in s]);pe=np.array([v['cheap_proxy_height_error'] for v in s])
structures=json.loads((D/'structure-comparison.json').read_text())
rs=structures['records']
assert len(rs)==880 and len({(v['seed'],v['type'],tuple(v['chunkbase_xz'])) for v in rs})==880
assert set(structures['statistics'])==set(STRUCTURES)
assert all(Counter(v['type'] for v in rs if v['seed']==seed)==Counter({t:20 for t in STRUCTURES}) for seed in plan['seeds'])
metrics=dict(surface_biomes=dict(samples=len(s),exact_matches=sum(v['biome_match'] for v in s),types=len({v['local_biome'] for v in s})),nether_biomes=dict(samples=len(n),exact_matches=sum(v['biome_match'] for v in n),types=len({v['local_biome'] for v in n})),cave_biomes=dict(samples=len(c),exact_matches_at_minus51=sum(v['biome_match'] for v in c),types=len({v['local_biome'] for v in c})),height=dict(samples=len(s),mean_absolute_error=float(abs(e).mean()),median_absolute_error=float(np.median(abs(e))),p95_absolute_error=float(np.percentile(abs(e),95)),max_absolute_error=int(abs(e).max()),exact=int((e==0).sum()),within2=int((abs(e)<=2).sum()),within3=int((abs(e)<=3).sum()),land_water_threshold_agreement=sum(v['height_land_water_match'] for v in s),stride8_vs_stride1_agreement=sum(v['stride8_equals_stride1'] for v in s)),cheap_proxy=dict(mean_absolute_error=float(abs(pe).mean()),max_absolute_error=float(abs(pe).max()),land_water_threshold_agreement=sum(v['cheap_proxy_land_water_match'] for v in s)),structures=dict(samples=len(rs),matches_within64=sum(v['matched_within_64'] for v in rs),exact_coordinate_matches=sum(v['viable_offset']==0 for v in rs)))
paths=['native/bridge.c','native/bridge.h','vendor/backend.json',native.__file__,'search.example.yaml','scripts/prepare_accuracy_audit.py','scripts/compare_accuracy_audit.py','scripts/report_accuracy_audit.py','scripts/plot_accuracy_audit.py',*map(str,D.glob('chunkbase-*.json'))]
meta=dict(**source,model=model_metadata(),backend=json.loads(Path('vendor/backend.json').read_text()),seeds=plan['seeds'],hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths})
(D/'metrics.json').write_text(json.dumps(dict(metadata=meta,metrics=metrics),indent=2)+'\n')
external_points=[dict(id=v['id'],seed=v['seed'],dimension=v['dimension'],x=v['x'],z=v['z'],mode=v['mode'],sample_y=v.get('sample_y'),chunkbase_marker_y=v['chunkbase_marker_y'],chunkbase_marker_biome=v['chunkbase_marker_biome'],chunkbase_comparison_biome=v['chunkbase_biome'],chunkbase_cave_range=v.get('chunkbase_cave_range')) for v in rows]
external_structures=json.loads((D/'chunkbase-structures.compact.json').read_text())
Path('fixtures/bedrock-26.52/chunkbase-accuracy-audit.json').write_text(json.dumps(dict(**source,seeds=plan['seeds'],points=external_points,structure_queries=external_structures,unused_biome_UI_label='Deep Warm Ocean unused',sampling='20 parsable coordinate rows per structure type/seed, from UI result lists; not necessarily nearest; capped search lists do not establish absence'),indent=2)+'\n')
lines=['# Bedrock 26.52 accuracy audit — 7 October 2026','',
'Our prototype agrees closely with Chunkbase on the tested samples, but this is a bounded comparison between predictors, not proof of whole-world Minecraft accuracy. Six structure disagreement records and six surface biome disagreements remain. The broader preflight goal remains incomplete.','',
'## Scope and method','',
'- Chunkbase Seed Map was read through its interactive UI with **Bedrock 26.50–26.52** selected. Local model: pinned `MC_26_50` backend. Seeds: `12345`, `0`, `-1`, `4294979641`.',
'- The upper-bit seed equals `12345 + 2^32`; some structure families repeat, so these are not four statistically independent worlds for every family.',
'- A deterministic local grid surveyed 65,536 points at each of Y=63 and Y=-51 per seed, from -32,768 to 32,512 at 256-block spacing. It selected surface representatives, four cave representatives, 40 random terrain columns and five Nether biome representatives per seed.',
'- 159 unique coordinate checks cover **52 surface biome types, four cave types, and all five Nether types**. These are representatives; their complete area, boundaries and vertical extent are not validated.',
'- Chunkbase labels **Deep Warm Ocean** as **unused**. The backend enum retains it, but it did not occur in the surveyed grids and was not given an invented passing sample.',
'- Structures: 20 parsable UI coordinate rows per type per seed, 880 total, across all 11 wrapper-supported types. Search lists are capped and their order is not distance order. Portal variant labels can make some rows unparsable; this is a convenience sample, not a random sample.',
'- Correspondence rule: nearest viable local start within 64 blocks; a ±160-block diagnostic window also checks raw placements. Starts and website entrance/room markers can differ. Unmatched records were rechecked in 6,000-block-wide local windows.',
'- The radius is a declared matching heuristic, not a correctness tolerance certified by Minecraft. Complete structure footprints, types/variants, entrances and safe access were not checked.',
'- Local density ground Y is compared directly with Chunkbase marker Y, with no added global offset. Marker Y is a website estimate, not an observed game block. Land/water means the prototype’s Y>=63 threshold; it does not establish actual liquid blocks.',
'- All external rows are stored as third-party predictions. Existing phone observations remain separate. No large seed search was run.','',
'## Quantitative results','',
'| Measurement | Agreement/error |','|---|---:|',
f"| Surface biome, exact X/Z | {metrics['surface_biomes']['exact_matches']}/{len(s)} = {100*metrics['surface_biomes']['exact_matches']/len(s):.1f}% |",
f"| Nether biome, sampled Y=33 | {sum(v['biome_match'] for v in n)}/{len(n)} |",
f"| Cave biome, sampled Y=-51 | {sum(v['biome_match'] for v in c)}/{len(c)} |",
f"| Terrain height, mean / median absolute difference | {abs(e).mean():.1f} / {np.median(abs(e)):.1f} blocks |",
f"| Terrain height, 95th percentile / maximum difference | {np.percentile(abs(e),95):.1f} / {abs(e).max()} blocks |",
f"| Terrain heights within 2 blocks / exact | {int((abs(e)<=2).sum())}/{len(s)} / {int((e==0).sum())}/{len(s)} |",
f"| Density height land/water threshold agreement | {sum(v['height_land_water_match'] for v in s)}/{len(s)} |",
f"| Cheap discovery proxy, mean / maximum absolute difference | {abs(pe).mean():.2f} / {abs(pe).max():.2f} blocks |",
f"| Cheap proxy land/water threshold agreement | {sum(v['cheap_proxy_land_water_match'] for v in s)}/{len(s)} |",
f"| Default stride-eight versus stride-one heights | {sum(v['stride8_equals_stride1'] for v in s)}/{len(s)} identical |",
f"| Structure correspondences within 64 blocks | {sum(v['matched_within_64'] for v in rs)}/{len(rs)} = {100*sum(v['matched_within_64'] for v in rs)/len(rs):.2f}% |",
f"| Structures with exactly equal marker/start coordinates | {sum(v['viable_offset']==0 for v in rs)}/{len(rs)} |",'',
'These percentages describe this sample. They are not a false-positive rate, complete recall, or a guarantee that a candidate island fits. Capped positive lists cannot certify missing structures or extra local predictions.','',
'## Structure results','',
'| Type | Corresponding viable starts | Exact coordinates | Maximum offset among matches |','|---|---:|---:|---:|']
for t in STRUCTURES:
 a=structures['statistics'][t];lines.append(f"| {t} | {a['matched']}/{a['samples']} | {a['exact']} | {a['max_matched_offset']:.2f} blocks |")
lines+=['','The consistent offsets for Outpost and Fortress, and varying offsets for Trial Chamber, Portal and Bastion, are compatible with different marker conventions. They are still recorded, and do not prove in-game generation.','',
'### Structure disagreements','',
'| Seed | Type | Chunkbase X,Z | Local finding |','|---|---|---|---|']
for r in rs:
 if r['matched_within_64']:continue
 raw=r['local_raw_start'];found=f"Raw start {tuple(raw)} rejected by viability" if raw else 'No raw or viable start within ±160 blocks'
 lines.append(f"| {r['seed']} | {r['type']} | {tuple(r['chunkbase_xz'])} | {found} |")
lines+=['',
'- The bastion disagreement repeats for the two seeds with identical lower bits. Local start `(1208,408)` is rejected; the nearest viable local bastion is `(1272,600)`, 240 blocks from the website marker. The marker’s local biome at Y=33 is Basalt Deltas, while the raw start’s is Nether Wastes. The structure marker and viability sampling point differ; actual presence has not been established.',
'- Both missing seed -1 strongholds remain absent in local 6,000-block-wide windows centered on the website markers. This is not a small coordinate offset.',
'- Both ancient cities have exact raw placement matches. The backend viability check samples the biome at Y=-27, using quart coordinates, and rejects those starts. This is a viability disagreement, not a placement-RNG failure. It needs an actual generation check before changing the rule.',
'- The previously user-confirmed absent seed-12345 Fortress at `(-152,120)` is now excluded by the corrected adapter and regression test. That is separate in-game negative evidence; none of the new disagreements are silently treated as Minecraft observations.','',
'## Biome disagreements and cave boundaries','',
'| Seed | X,Z | Local surface biome | Chunkbase surface biome |','|---|---|---|---|']
for v in s:
 if not v['biome_match']:lines.append(f"| {v['seed']} | {(v['x'],v['z'])} | {v['local_biome']} | {v['chunkbase_biome']} |")
lines+=['',
'All six disagreements persist at the website’s estimated surface height. The website biome occurs one or two blocks away in our local biome map (see boundary diagnostics). This suggests boundary sampling differences; it does not resolve which predictor is correct at the exact block.',
'','The four cave names agree at Y=-51, but vertical ranges do not all agree. Chunkbase ranges versus local exact-block ranges:','',
'- Dripstone: website -56..51; local -56..49 plus a separate 54..55 interval.',
'- Lush: website -64..11; local -64..9.',
'- Deep Dark: both -64..-49.',
'- Sulfur: website -60..31; local -59..31.','',
'## Terrain implications','',
'The density estimator is close enough in this sample for preliminary terrain screening. It does not establish block-perfect coastline geometry. Four columns disagree on the Y=63 land/water threshold; the cheaper discovery proxy disagrees at six. Such errors can create or remove thin apparent land bridges. The prototype excludes caves, aquifers, decorations and actual chunk interpolation. Nether terrain heights, caves/overhang geometry, tree/log abundance, whole-island connectivity and surrounding mountain coverage remain unverified.','',
'| Seed | X,Z | Local density Y | Website Y |','|---|---|---:|---:|']
for v in s:
 if not v['height_land_water_match']:lines.append(f"| {v['seed']} | {(v['x'],v['z'])} | {v['local_height']} | {v['chunkbase_marker_y']} |")
lines+=['','## Unsupported coverage','',
'End biomes, End terrain, End Cities and End Gateways are not implemented by this wrapper. Other website structures/features outside the 11-type adapter include Woodland Mansion, Dungeon, Jungle Temple, Desert Temple, Witch Hut, Buried Treasure, Igloo, Ocean Ruins, Fossil, Nether Fossil, Nether Ruined Portal, Trail Ruins and Abandoned Camp. Spawn, slime chunks, geodes, ore veins, desert wells and cave features are also outside this audit’s implemented capabilities. These are missing coverage, not passing checks.','',
'## Evidence and reproduction','',
'- [Durable external observations](../../fixtures/bedrock-26.52/chunkbase-accuracy-audit.json)',
'- [Biome/terrain rows](biome-terrain-comparison.json), [structure rows](structure-comparison.json), [metrics and source hashes](metrics.json)',
'- [Exported terrain figure](terrain-comparison.png)',
'- [Biome boundary diagnostics](biome-boundary-diagnostics.json), [cave range diagnostics](cave-range-diagnostics.json), [structure failure diagnostics](structure-disagreement-diagnostics.json)',
'- [Existing phone observations](../../fixtures/bedrock-26.52/seed-12345.user-observations.json) remain separate.',
'- Recompute local structure comparisons: `.venv/bin/python scripts/compare_accuracy_audit.py`.',
'- Recompute biome/terrain metrics and this report: `.venv/bin/python scripts/report_accuracy_audit.py`.',
'- The deterministic survey can be regenerated with `scripts/prepare_accuracy_audit.py`; external UI observations are a frozen snapshot and must not be regenerated from our predictor.',
'- Full local suite: 44 tests pass after the Fortress correction. Audit integrity checks enforce all 159 unique point rows, all 880 unique seed/type/coordinate rows and 20 samples per supported type per seed.','',
'## Per-biome coverage','',
'| Biome | Exact matches / samples | Mode |','|---|---:|---|']
groups=defaultdict(list)
for v in rows:groups[(v['local_biome'],v['mode'])].append(v)
for (name,mode),vs in sorted(groups.items()):lines.append(f"| {name} | {sum(v['biome_match'] for v in vs)}/{len(vs)} | {mode} |")
(D/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(metrics,indent=2))
