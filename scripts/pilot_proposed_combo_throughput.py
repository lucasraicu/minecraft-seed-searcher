"""Matched serial stage timings for the proposed mixed-count combinations.

Private count kernels only; production configuration/native are not modified.
"""
from contextlib import ExitStack
import hashlib,json,statistics,time
from pathlib import Path
from seed_search.backend import Backend
from seed_search.realm.baseline import structure_observation
from seed_search.realm.config import default_config
from seed_search.realm.sampling import dispersed_indices
from scripts.count_pilot_api import CountBackend,lib
from scripts.biome_diversity_pilot_api import DiversityBackend
from scripts.pilot_count_bits_structures import family_masks
from scripts.pilot_count_bits_biomes import grid
from scripts.pilot_locked_stronghold import exact_bounds

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runs/count-bits-2026-10-11'
CORE={'stronghold':1,'village':3,'trial_chamber':3,'ancient_city':2,'mineshaft':5,'fortress':1,'bastion':1}
PROFILES={'recommended_core':CORE,'strict_expanded':{**CORE,'monument':1,'mansion':1,'jungle_temple':1,'desert_pyramid':1}}
BIO={'recommended_core':{'forest':3,'taiga':2},'strict_expanded':{'forest':3,'taiga':2,'desert':1,'jungle':1}}
ARMS={'full64_direct':(0,False),'fused_lower32':(32,False),'cached_lower32':(32,True)}

def prepare(counter,row,need,order,raw_order):
    p=counter.prepare_combo(row,order,1,raw_order)
    for i,name in enumerate(order):p[2][i]=need[name]
    return p

def learn(obs,need,raw=False):
    remaining=list(need);live=list(range(len(obs)));order=[]
    while remaining:
        def score(name):
            if name=='stronghold':return -1
            if raw and (name=='mineshaft' or name in ('trial_chamber','trail_ruins','abandoned_camp')):return -1
            n=need[name];field='raw_count' if raw else 'viable_count'
            failed=sum(obs[i][name][field]<n for i in live)
            seconds=sum(obs[i][name]['raw_seconds'][str(min(n,4))] if raw else obs[i][name]['count_seconds'][str(min(n,4))]['full64_direct'] for i in live)
            return failed/max(seconds,1e-12)
        chosen=max(remaining,key=score);remaining.remove(chosen);order.append(chosen)
        if chosen!='stronghold' and (not raw or (chosen!='mineshaft' and chosen!='trial_chamber')):
            live=[i for i in live if obs[i][chosen]['raw_count' if raw else 'viable_count']>=need[chosen]]
    return order

def med_rates(trials,key,n):
    med={a:statistics.median(x['seconds'] for x in trials if x['arm']==a) for a in key}
    return {'median_seconds':med,'per_second':{a:n/t for a,t in med.items()},'per_hour':{a:3600*n/t for a,t in med.items()},'trials':trials}

def main():
    sources={};rows={};observations={};known={}
    for cohort in ('tuning','holdout'):
        cp=ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/centers.json';op=OUT/f'{cohort}-structure-observations.json'
        rows[cohort]=[r for r in json.loads(cp.read_text()) if r['first_center']]
        observations[cohort]=json.loads(op.read_text());assert len(rows[cohort])==len(observations[cohort])
        known[cohort]={r['seed']:(r,o) for r,o in zip(rows[cohort],observations[cohort])}
        for p in (cp,op):sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    orders={name:{'direct':learn(observations['tuning'],need),'raw':learn(observations['tuning'],need,True)} for name,need in PROFILES.items()}
    masks=family_masks();structure={};biomes={};discovery={};comparisons=0
    for cohort in ('tuning','holdout'):
        structure[cohort]={};biomes[cohort]={};discovery[cohort]={}
        with ExitStack() as stack:
            handles=[stack.enter_context(CountBackend(r['seed'])) for r in rows[cohort]]
            for name,need in PROFILES.items():
                expected=[all(o[k]['viable_count']>=g for k,g in need.items()) for o in observations[cohort]]
                prepared=[prepare(b,r,need,orders[name]['direct'],orders[name]['raw']) for b,r in zip(handles,rows[cohort])]
                for arm,(bits,cached) in ARMS.items():
                    lib.pc_cache_reset(cached);answers=[b.combo_prepared(p,bits)[0] for b,p in zip(handles,prepared)];assert answers==expected;comparisons+=len(expected)
                trials=[]
                for trial in range(5):
                    arms=list(ARMS);arms=arms[trial%3:]+arms[:trial%3]
                    if trial%2:arms.reverse()
                    for arm in arms:
                        bits,cached=ARMS[arm];t=time.perf_counter();cpu=time.process_time();work=[0]*8
                        for repetition in range(4):
                            lib.pc_cache_reset(cached);answers=[]
                            for b,p in zip(handles,prepared):
                                answer,stats=b.combo_prepared(p,bits);answers.append(answer)
                                for i,x in enumerate(stats):work[i]+=x
                            assert answers==expected;comparisons+=len(expected)
                        trials.append({'arm':arm,'trial':trial,'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu,'work':work})
                result=med_rates(trials,ARMS,len(expected)*4);result.update({'layouts':len(expected),'viable_positive':sum(expected),'raw_lower32_rejection_percent':100*(1-sum(all(o[k]['raw_count']>=g for k,g in need.items() if k not in ('stronghold','mineshaft','trial_chamber')) for o in observations[cohort])/len(expected)),'order':orders[name]})
                structure[cohort][name]=result
                print(json.dumps({'stage':'structures','cohort':cohort,'profile':name,'per_second':result['per_second'],'positives':sum(expected)}),flush=True)
        # Reuse the same 24-layout biome cohort, with independent batch inventories as oracle.
        bp=OUT/'biome-variant-observations.json';brows=[known[cohort][r['seed']][0] for r in json.loads(bp.read_text()) if r['cohort']==cohort]
        with ExitStack() as stack:
            bios=[stack.enter_context(DiversityBackend(r['seed'])) for r in brows]
            plain=[stack.enter_context(Backend(r['seed'])) for r in brows]
            points=[grid(r,0)[0] for r in brows]
            for name,need in BIO.items():
                goals=list(need.values());groups=[masks[k] for k in need]
                prepared=[b.prepare(p[dispersed_indices(len(p))],0,groups,goals) for b,p in zip(bios,points)]
                sets=[set(map(int,b.biome_points(p,0))) for b,p in zip(plain,points)]
                expected=[all(len(s.intersection(masks[k]))>=g for k,g in need.items()) for s in sets]
                assert [b.prepared(p)[0] for b,p in zip(bios,prepared)]==expected;comparisons+=len(expected)
                trials=[]
                for trial in range(3):
                    arms=('full_inventory','native_distinct_stop') if trial%2==0 else ('native_distinct_stop','full_inventory')
                    for arm in arms:
                        t=time.perf_counter();cpu=time.process_time();queried=0;answers=[]
                        for i,b in enumerate(bios):
                            if arm=='native_distinct_stop':answer,n=b.prepared(prepared[i]);queried+=n
                            else:
                                seen=set(map(int,plain[i].biome_points(points[i],0)));queried+=len(points[i]);answer=all(len(seen.intersection(masks[k]))>=g for k,g in need.items())
                            answers.append(answer)
                        assert answers==expected;comparisons+=len(expected)
                        trials.append({'arm':arm,'trial':trial,'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu,'queried_points':queried})
                result=med_rates(trials,('full_inventory','native_distinct_stop'),len(brows));result.update({'layouts':len(brows),'sample_positive':sum(expected),'points_per_layout':len(points[0])})
                biomes[cohort][name]=result
                print(json.dumps({'stage':'biomes','cohort':cohort,'profile':name,'per_second':result['per_second'],'positives':sum(expected)}),flush=True)
        manifest=json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/identity.json').read_text())['manifest'][:128]
        for name,need in PROFILES.items():
            expected=[all(known[cohort][item['seed']][1][k]['viable_count']>=g for k,g in need.items()) if item['seed'] in known[cohort] else None for item in manifest]
            def run(arm):
                bits,cached=ARMS[arm];lib.pc_cache_reset(cached);answers=[]
                for item in manifest:
                    with Backend(item['seed']) as b:
                        starts=structure_observation(b,'stronghold',default_config()['discovery']['overworld_bounds'],combined=True)['predicted_viable']
                    if not starts:answers.append(None);continue
                    assert starts[0]==known[cohort][item['seed']][0]['center']
                    with CountBackend(item['seed']) as b:
                        row={'bounds':exact_bounds(starts[0])};p=prepare(b,row,need,orders[name]['direct'],orders[name]['raw']);answers.append(b.combo_prepared(p,bits)[0])
                assert answers==expected
            for arm in ARMS:run(arm)
            trials=[]
            for trial in range(3):
                arms=list(ARMS);arms=arms[trial:]+arms[:trial]
                if trial%2:arms.reverse()
                for arm in arms:
                    t=time.perf_counter();cpu=time.process_time();run(arm);comparisons+=len(expected)
                    trials.append({'arm':arm,'trial':trial,'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu})
            result=med_rates(trials,ARMS,len(manifest));result.update({'input_seeds':len(manifest),'without_discovered_anchor':sum(x is None for x in expected),'structure_positive':sum(x is True for x in expected)})
            discovery[cohort][name]=result
            print(json.dumps({'stage':'discovery_and_structures','cohort':cohort,'profile':name,'per_second':result['per_second']}),flush=True)
    report={'requirements':PROFILES,'biome_requirements':BIO,'structures':structure,'biomes':biomes,'discovery_and_structures':discovery,'comparisons':comparisons,'differences':0,'source_sha256':sources,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':{'geometry':'4000 discovery, 1536 Overworld, 896 Nether at exact Stronghold/8','workers':1,'structure_stage':'Precreated full64 contexts and first-selected Stronghold; count caps per type, five counterbalanced trials/four repetitions. Paid raw cache starts empty per repetition. All raw-positive cases still use full64 viability. Trial Chamber stays full64 in the lower32 arm. No terrain, biome inventory, discovery, context creation, IPC or persistence.','biome_stage':'24 correlated sibling layouts per cohort, 2304 world-aligned points at Y=63,-48,0,160; three counterbalanced trials. Both inventory and count-capped native use full64. Oracle is independent full64 batch inventory. Not conditioned on structure success.','discovery_and_structures':'128 inputs per cohort; three counterbalanced trials. Includes full64 anchor discovery, both diagnostic contexts and preparation. Excludes biomes, terrain, IPC, persistence and game verification. Missing anchors unresolved.','policy':'Strict expanded profile treats all core count preferences as hard requirements for timing only; production requirements are unchanged. Ordering heuristic learned on tuning using saved count timings (N5 Mineshaft uses N4 cost proxy), frozen for holdout. Hourly rates are serial pilot capacity projections, not sustained measured hours or qualifying-world yield.'}}
    (OUT/'proposed-combination-throughput.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'finished':True,'comparisons':comparisons,'differences':0}),flush=True)

if __name__=='__main__':main()
