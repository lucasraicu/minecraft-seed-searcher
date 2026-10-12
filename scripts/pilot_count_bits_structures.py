"""Exact-center count-N: full64 direct versus fused lower32/lower48 gates."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from contextlib import ExitStack
import hashlib,json,statistics,time
from pathlib import Path
import numpy as np
from seed_search import _native
from seed_search.backend import Backend,STRUCTURES,biome_catalog,biome_name
from seed_search.realm.biomes import PRIMARY,SAVANNA,canonical
from scripts.count_pilot_api import CountBackend,lib,TYPES,DIM,Y,NETHER,IDENTITY

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/count-bits-2026-10-11'
COUNTS=(1,2,3,4)
PROFILES={'current_four':('village','ancient_city','fortress','bastion'),
          'all_16_mt':('village','ancient_city','ruined_portal','shipwreck','monument','outpost','fortress','bastion','desert_pyramid','jungle_temple','swamp_hut','igloo','ocean_ruin','mansion','buried_treasure','ruined_portal_nether'),
          'all_21_ow_nether':tuple(n for n in STRUCTURES if n!='end_city'),
          'all_22_with_end_control':STRUCTURES}
ARMS={'full64_direct':(0,False),'fused_lower32':(32,False),'fused_lower48':(48,False),'cached_lower32':(32,True),'cached_lower48':(48,True)}


def family_for_id(ident):
    name=canonical(biome_name(int(ident)))
    if name in PRIMARY:return PRIMARY[name]
    if name in SAVANNA:return 'savanna'
    return name


def family_masks():
    groups=defaultdict(list)
    for row in biome_catalog():
        if row['version_active'] and row['generates']:
            groups[family_for_id(row['id'])].append(row['id'])
    return dict(groups)


def bounds_for(row,name):return row['bounds']['nether' if name in NETHER else 'overworld']


def greedy(observations,names,n,raw=False,bits=64,profile=None):
    left=list(names);survivors=list(range(len(observations)));order=[]
    shared={'desert_pyramid','jungle_temple','swamp_hut','igloo'}
    def succeeds(o,name):
        threshold=4*n if raw and set(names)>=shared and name in shared else n
        return o[name]['raw_count' if raw else 'viable_count']>=threshold
    while left:
        def score(name):
            if raw and (lib.pc_bits(TYPES[name])>bits or name=='mineshaft'):return -1
            failed=sum(not succeeds(observations[i],name) for i in survivors)
            seconds=sum(observations[i][name]['raw_seconds'][str(n)] if raw else observations[i][name]['count_seconds'][str(n)]['full64_direct'] for i in survivors)
            return failed/max(seconds,1e-12)
        chosen=max(left,key=score);order.append(chosen);left.remove(chosen)
        if not raw or (lib.pc_bits(TYPES[chosen])<=bits and chosen!='mineshaft'):
            survivors=[i for i in survivors if succeeds(observations[i],chosen)]
    return order


def profile_raw_positive(o,names,n,bits):
    relevant=[k for k in names if lib.pc_bits(TYPES[k])<=bits and k!='mineshaft']
    ok=all(o[k]['raw_count']>=n for k in relevant)
    if set(names)>={'desert_pyramid','jungle_temple','swamp_hut','igloo'}:
        ok=ok and o['desert_pyramid']['raw_count']>=4*n
    return ok


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repeats',type=int,default=4)
    p.add_argument('--family-audit',type=int,default=24)
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    inputs={c:[r for r in json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{c}/centers.json').read_text()) if r['first_center']] for c in ('tuning','holdout')}
    masks=family_masks()
    identity={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'native':json.loads(IDENTITY.read_text()),'reference_native_sha256':hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
              'geometry':'4000-square discovery; selected first Stronghold; 1536-square OW / 896-square Nether exact /8; End 1536-square same-coordinate diagnostic only',
              'families':masks,'structure_placement_bits':{n:int(lib.pc_bits(TYPES[n])) for n in STRUCTURES},
              'structure_biome_y':Y,'profiles':PROFILES,'counts':COUNTS,
              'scope':'Single process conditional count-N stage. Native context construction and Stronghold discovery are excluded; cache reset/construction and misses are included. Count1 Stronghold uses the preselected anchor; count2+ enumerates/deduplicates its bounded predicted anchors.',
              'parent_sha256':{c:hashlib.sha256((ROOT/f'runs/locked-stronghold-2026-10-11/{c}/centers.json').read_bytes()).hexdigest() for c in inputs}}
    (OUT/'structures-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    all_observations={};results={};orders={};raw_orders={};comparisons=0;dependency=[];family_results=[]
    for cohort,rows in inputs.items():
        obs=[];lib.pc_cache_reset(0)
        start=time.perf_counter()
        for i,row in enumerate(rows):
            item={}
            with Backend(row['seed']) as full,CountBackend(row['seed']) as counted:
                lower32=Backend(int(row['seed'])&0xffffffff) if i<32 else None
                lower48=Backend(int(row['seed'])&0xffffffffffff) if i<32 else None
                try:
                    for name in STRUCTURES:
                        bounds=bounds_for(row,name)
                        raw=full.structures(name,bounds,False)
                        viable=full.structures(name,bounds,True)
                        record={'raw_count':len(raw),'viable_count':len(viable),'count_seconds':{},'raw_seconds':{},
                                'reference_sha256':hashlib.sha256(json.dumps(viable).encode()).hexdigest()}
                        if viable:
                            pts=np.array([(x,Y[name],z) for x,z in viable],np.int32)
                            ids=full.biome_points(pts,DIM[name])
                            family_counts=Counter(family_for_id(v) for v in ids)
                        else:family_counts={}
                        record['family_counts']=dict(family_counts)
                        for n in COUNTS:
                            record['count_seconds'][str(n)]={}
                            t=time.perf_counter();raw_answer=counted.count(name,bounds,n,raw_only=True)[0]
                            record['raw_seconds'][str(n)]=time.perf_counter()-t
                            assert raw_answer==(len(raw)>=n),(cohort,i,name,n,'raw')
                            comparisons+=1
                            for arm,bits in [('full64_direct',0),('fused_lower32',32),('fused_lower48',48)]:
                                t=time.perf_counter();answer,stats,_=counted.count(name,bounds,n,gate_bits=bits)
                                record['count_seconds'][str(n)][arm]=time.perf_counter()-t
                                assert answer==(len(viable)>=n),(cohort,i,name,n,arm)
                                comparisons+=1
                        if lower32 is not None:
                            raw32=lower32.structures(name,bounds,False);raw48=lower48.structures(name,bounds,False)
                            bits=int(lib.pc_bits(TYPES[name]))
                            if bits<=32:assert raw32==raw48==raw
                            elif bits<=48:assert raw48==raw
                            dependency.append({'cohort':cohort,'seed':row['seed'],'structure':name,'bits':bits,
                                               'raw32_equal':raw32==raw,'raw48_equal':raw48==raw})
                            comparisons+=int(bits<=32)+int(bits<=48)
                        if i<args.family_audit:
                            candidates=set(family_counts)|{next(f for f in masks if f not in family_counts)}
                            for family in sorted(candidates):
                                expected=family_counts.get(family,0)
                                for n in (1,2,4):
                                    for arm,bits in [('full64_direct',0),('fused_lower32',32),('fused_lower48',48)]:
                                        t=time.perf_counter();actual,work,_=counted.count(name,bounds,n,gate_bits=bits,allow=masks[family])
                                        seconds=time.perf_counter()-t
                                        assert actual==(expected>=n),(cohort,i,name,family,n,arm,expected)
                                        comparisons+=1
                                        family_results.append({'cohort':cohort,'structure':name,'family':family,'count':n,'arm':arm,'seconds':seconds,'positive':actual})
                        item[name]=record
                finally:
                    if lower32 is not None:lower32.close();lower48.close()
            obs.append(item)
            if (i+1)%32==0:print(json.dumps({'cohort':cohort,'complete_inventory':i+1,'seconds':round(time.perf_counter()-start,1)}),flush=True)
        all_observations[cohort]=obs
        (OUT/f'{cohort}-structure-observations.json').write_text(json.dumps(obs,indent=2)+'\n')
        if cohort=='tuning':
            for profile,names in PROFILES.items():
                for n in COUNTS:
                    key=f'{profile}:{n}'
                    orders[key]=greedy(obs,names,n)
                    raw_orders[key]={str(bits):greedy(obs,names,n,True,bits) for bits in (32,48)}
        cohort_results={}
        with ExitStack() as stack:
            handles=[stack.enter_context(CountBackend(r['seed'])) for r in rows]
            for profile,names in PROFILES.items():
                cohort_results[profile]={}
                for n in COUNTS:
                    key=f'{profile}:{n}';order=orders[key]
                    expected=[all(o[k]['viable_count']>=n for k in names) for o in obs]
                    prepared={bits:[b.prepare_combo(row,order,n,raw_orders[key][str(bits)]) for b,row in zip(handles,rows)] for bits in (32,48)}
                    for arm,(bits,cached) in ARMS.items():
                        lib.pc_cache_reset(cached)
                        answers=[b.combo_prepared(prepared[bits or 32][i],bits)[0] for i,b in enumerate(handles)]
                        assert answers==expected,(cohort,profile,n,arm)
                    trials=[]
                    names_arms=tuple(ARMS)
                    for trial in range(5):
                        rotation=names_arms[trial:]+names_arms[:trial]
                        if trial%2:rotation=tuple(reversed(rotation))
                        for arm in rotation:
                            bits,cached=ARMS[arm];t,cpu=time.perf_counter(),time.process_time();work=[0]*8
                            for repetition in range(args.repeats):
                                lib.pc_cache_reset(cached)
                                answers=[]
                                for i,b in enumerate(handles):
                                    answer,stats=b.combo_prepared(prepared[bits or 32][i],bits)
                                    answers.append(answer)
                                    for j,value in enumerate(stats):work[j]+=value
                                assert answers==expected
                            trials.append({'trial':trial,'arm':arm,'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu,'native_work':work})
                    med={a:statistics.median(t['seconds'] for t in trials if t['arm']==a) for a in ARMS}
                    data={'inputs':len(rows),'viable_positive':sum(expected),'full64_rejection_percent':100*(1-sum(expected)/len(rows)),
                          'raw_rejection_percent':{str(bits):100*(1-sum(profile_raw_positive(o,names,n,bits) for o in obs)/len(rows)) for bits in (32,48)},
                          'median_seconds':med,'layouts_per_second':{a:len(rows)*args.repeats/t for a,t in med.items()},
                          'time_change_percent':{a:100*(t/med['full64_direct']-1) for a,t in med.items()},
                          'trials':trials,'direct_order':order,'raw_order':raw_orders[key]}
                    cohort_results[profile][str(n)]=data
                    print(json.dumps({'cohort':cohort,'profile':profile,'n':n,'raw_rejection':data['raw_rejection_percent'],'time_change':data['time_change_percent']}),flush=True)
        individual={name:{str(n):{'raw_positive':sum(o[name]['raw_count']>=n for o in obs),
                                'viable_positive':sum(o[name]['viable_count']>=n for o in obs),
                                'mean_microseconds':{a:1e6*statistics.mean(o[name]['count_seconds'][str(n)][a] for o in obs) for a in ('full64_direct','fused_lower32','fused_lower48')}} for n in COUNTS} for name in STRUCTURES}
        cohort_results['individual_structures']=individual
        cohort_results['structure_family_counts']={name:{family:{str(n):sum(o[name]['family_counts'].get(family,0)>=n for o in obs) for n in COUNTS} for family in masks} for name in STRUCTURES}
        results[cohort]=cohort_results
        (OUT/'structures-report.json').write_text(json.dumps({'cohorts':results,'comparisons':comparisons,'differences':0,'family_audit_rows_per_cohort':args.family_audit},indent=2)+'\n')
    (OUT/'dependency-controls.json').write_text(json.dumps(dependency,indent=2)+'\n')
    (OUT/'structure-family-query-timings.json').write_text(json.dumps(family_results,indent=2)+'\n')
    report={'cohorts':results,'comparisons':comparisons,'differences':0,'family_audit_rows_per_cohort':args.family_audit,
            'dependency_control_cases':len(dependency),'structure_family_query_cases':len(family_results),
            'limits':identity['scope']+' Individual family timings are single-pass means and exploratory; combination timings are five counterbalanced repeated trials. Structure family association is the biome at the logged start column and declared Y, not a claim that every structure piece lies in that family. Predictor parity is not actual-world certification.'}
    (OUT/'structures-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'finished':True,'comparisons':comparisons,'differences':0}),flush=True)

if __name__=='__main__':main()
