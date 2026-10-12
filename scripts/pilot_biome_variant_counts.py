"""Primary clarified biome test: N DISTINCT active variants within each family."""
from __future__ import annotations
from collections import defaultdict
from contextlib import ExitStack
import hashlib,json,statistics,time
from pathlib import Path
import numpy as np
from seed_search.backend import Backend
from seed_search.realm.sampling import dispersed_indices
from scripts.biome_diversity_pilot_api import DiversityBackend,IDENTITY
from scripts.pilot_count_bits_biomes import grid,confusion
from scripts.pilot_count_bits_structures import family_masks,OUT,ROOT

COUNTS=(1,2,3,4)
PROFILES={'forest_variants':('forest',),'forest_and_taiga':('forest','taiga'),
          'forest_taiga_jungle':('forest','taiga','jungle'),
          'five_wooded_families':('forest','taiga','jungle','dark_pale','cherry')}


def variant_count(record,ids,arm):
    identity=json.loads((OUT/'biomes-identity.json').read_text())
    names={r['id']:r['name'] for r in identity['catalog']}
    return sum(record['items']['biome:'+names[i]]['support'][arm]>0 for i in ids)


def main():
    masks=family_masks();source=json.loads((OUT/'biome-observations.json').read_text())
    identity=json.loads((OUT/'biomes-identity.json').read_text());names={r['id']:r['name'] for r in identity['catalog']};dims={r['id']:r['dimension'] for r in identity['catalog']}
    for family,ids in masks.items():assert len({dims[i] for i in ids})==1
    proof={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native':json.loads(IDENTITY.read_text()),
           'input_sha256':hashlib.sha256((OUT/'biome-observations.json').read_bytes()).hexdigest(),
           'unit':'Distinct active biome IDs per family, independent of number of samples or connected patches.',
           'counts':COUNTS,'families':{f:{'ids':ids,'variants':[names[i] for i in ids],'capacity':len(ids),'dimension':dims[ids[0]]} for f,ids in masks.items()},
           'scope':'Same frozen 64-block sampling grid: OW Y=63,-48,0,160; Nether Y=33; End Y=63. Full64 reference presence on this defined grid; unseen actual-world biomes remain unknown.'}
    (OUT/'biome-variants-identity.json').write_text(json.dumps(proof,indent=2)+'\n')
    results={};all_records=[];comparisons=0
    parent={c:{r['seed']:r for r in json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{c}/centers.json').read_text()) if r['first_center']} for c in ('tuning','holdout')}
    for cohort in ('tuning','holdout'):
        records=[r for r in source if r['cohort']==cohort];measurements=[]
        for index,record in enumerate(records):
            row=parent[cohort][record['seed']]
            counts={f:{arm:sum(record['items']['biome:'+names[i]]['support'][arm]>0 for i in ids) for arm in ('full64','unsafe32','unsafe48')} for f,ids in masks.items()}
            data={'cohort':cohort,'seed':row['seed'],'variant_counts':counts,'native_query':{}}
            with DiversityBackend(row['seed']) as backend:
                grids={d:grid(row,d)[0] for d in (0,-1,1)}
                for family,ids in masks.items():
                    dim=dims[ids[0]];points=grids[dim];points=points[dispersed_indices(len(points))]
                    data['native_query'][family]={}
                    for n in COUNTS:
                        prepared=backend.prepare(points,dim,[ids],[n]);t=time.perf_counter()
                        answer,queried=backend.prepared(prepared);seconds=time.perf_counter()-t
                        assert answer==(counts[family]['full64']>=n),(cohort,index,family,n)
                        comparisons+=1
                        data['native_query'][family][str(n)]={'seconds':seconds,'queried':queried,'positive':answer}
            measurements.append(data);all_records.append(data)
            if (index+1)%8==0:print(json.dumps({'variant_cohort':cohort,'families_complete':index+1}),flush=True)
        families={}
        for family,ids in masks.items():
            families[family]={'capacity':len(ids),'variants':[names[i] for i in ids],'counts':{}}
            for n in COUNTS:
                full=sum(r['variant_counts'][family]['full64']>=n for r in measurements)
                entry={'full64_positive':full,'full64_rejection_percent':100*(1-full/len(measurements)),
                       'native_mean_microseconds':1e6*statistics.mean(r['native_query'][family][str(n)]['seconds'] for r in measurements),
                       'mean_queried_points':statistics.mean(r['native_query'][family][str(n)]['queried'] for r in measurements),
                       'catalog_impossible':n>len(ids),'unsafe_truncation':{}}
                for arm in ('unsafe32','unsafe48'):
                    combined={k:0 for k in ('tp','tn','fp','fn')}
                    for r in measurements:
                        c=confusion(r['variant_counts'][family]['full64'],r['variant_counts'][family][arm],n)
                        for k,v in c.items():combined[k]+=v
                    entry['unsafe_truncation'][arm]=combined
                families[family]['counts'][str(n)]=entry
        combos={}
        with ExitStack() as stack:
            handles=[stack.enter_context(DiversityBackend(r['seed'])) for r in records]
            reference_handles=[stack.enter_context(Backend(r['seed'])) for r in records]
            for profile,groups in PROFILES.items():
                combos[profile]={}
                for n in COUNTS:
                    expected=[all(r['variant_counts'][f]['full64']>=n for f in groups) for r in measurements]
                    prepared=[];plain=[]
                    for b,record in zip(handles,records):
                        points=grid(parent[cohort][record['seed']],0)[0];plain.append(points)
                        prepared.append(b.prepare(points[dispersed_indices(len(points))],0,[masks[f] for f in groups],[n]*len(groups)))
                    for b,p,want in zip(handles,prepared,expected):assert b.prepared(p)[0]==want
                    impossible=any(n>len(masks[f]) for f in groups)
                    if impossible:
                        combos[profile][str(n)]={'inputs':len(records),'positive':0,'catalog_impossible':True,'queries_required':0}
                        continue
                    trials=[]
                    for trial in range(3):
                        for arm in (('full_inventory','native_distinct_stop') if trial%2==0 else ('native_distinct_stop','full_inventory')):
                            t,cpu=time.perf_counter(),time.process_time();queried=0;answers=[]
                            for index,b in enumerate(handles):
                                if arm=='native_distinct_stop':answer,points=b.prepared(prepared[index]);queried+=points
                                else:
                                    values=reference_handles[index].biome_points(plain[index],0);queried+=len(plain[index]);seen=set(map(int,values))
                                    answer=all(len(seen.intersection(masks[f]))>=n for f in groups)
                                answers.append(answer)
                            assert answers==expected
                            trials.append({'arm':arm,'trial':trial,'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu,'queried_points':queried})
                    med={a:statistics.median(t['seconds'] for t in trials if t['arm']==a) for a in ('full_inventory','native_distinct_stop')}
                    combos[profile][str(n)]={'inputs':len(records),'positive':sum(expected),'catalog_impossible':False,'trials':trials,
                                            'layouts_per_second':{a:len(records)/v for a,v in med.items()},
                                            'time_change_percent':100*(med['native_distinct_stop']/med['full_inventory']-1)}
                    comparisons+=6*len(records)
        results[cohort]={'inputs':len(records),'families':families,'combinations':combos,
                         'all_family_maximums_observed':sum(all(r['variant_counts'][f]['full64']==len(ids) for f,ids in masks.items()) for r in measurements)}
    (OUT/'biome-variant-observations.json').write_text(json.dumps(all_records,indent=2)+'\n')
    (OUT/'biome-variants-report.json').write_text(json.dumps({'cohorts':results,'full64_comparisons':comparisons,'differences':0,'scope':proof['scope'],
                                                            'limits':'Safe lower32/lower48 structure filters leave these biome queries full64. Unsafe truncated-seed cases are negative accuracy controls. Inventory-versus-distinct-stop timings are three counterbalanced trials; individual-family microsecond means are exploratory single passes.'},indent=2)+'\n')
    print(json.dumps({'distinct_variants_complete':True,'comparisons':comparisons,'differences':0}),flush=True)

if __name__=='__main__':main()
