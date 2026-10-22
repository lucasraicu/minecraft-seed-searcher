"""Frozen request corpus and explicitly denominated retention-loss measurements."""
import copy
import json
from pathlib import Path
import random
import statistics
import time
from .registry import CONTRACT_ROOT, STRUCTURES, BIOMES, SIDES, RADII, digest


def heldout_cases(*, seed=2026102004, count=200):
    """No catalog input: case selection cannot adapt to observed retained results."""
    presets=json.loads((CONTRACT_ROOT/'ui_presets.json').read_text())['presets']
    rng=random.Random(seed); cases=[]
    for index in range(count):
        preset=presets[index%len(presets)]
        rows=copy.deepcopy(preset['rows'])
        if index>=48:
            for _ in range(1+int(index%7==0)):
                scope=({'kind':'inside_border'} if rng.random()<0.25 else
                       {'kind':'near_base','radius':rng.choice(RADII)})
                if rng.random()<0.35:
                    row={'kind':'biome_witness','any_of':rng.sample([f['id'] for f in BIOMES],rng.choice((1,2,3))),
                         'rule':'required','scope':scope}
                else:
                    row={'kind':'structure_count','feature':rng.choice(STRUCTURES)['id'],
                         'at_least':rng.choice((1,2,3,6,16)),'rule':'required','scope':scope}
                rows.append(row)
        template={'request_revision':'catalog-query-v1','edition':'bedrock','game_build_id':'research:pending',
            'catalog_snapshot_id':'pending','world_settings_id':'default','dimension':'overworld',
            'anchor_mode':('origin','recommended')[(index//8)%2],
            'border_side':SIDES[(index//16)%3], 'evidence_policy':'predicted_observations_v1',
            'fallback_profile':preset['fallback_profile'],'rows':rows}
        cases.append({'case_id':index,'category':preset['id'],'template':template})
    return {'revision':f'catalog-heldout-{count}-v1','cases':cases,'sha256':digest(cases),
            'selection':'Fixed presets and pseudorandom requests frozen before observing records; not player demand evidence'}


def bind(case,view):
    query=copy.deepcopy(case['template'])
    query['game_build_id']=view._header['game_build_id']
    query['world_settings_id']=view._header['world_settings_id']
    query['catalog_snapshot_id']=view.snapshot_id
    return query


def metrics(rows):
    eligible=[r for r in rows if r['reference_count']]
    return {'queries':len(rows),'reference_nonempty':len(eligible),
        'reference_empty':len(rows)-len(eligible),
        'preserved_nonempty':sum(r['retained_count']>0 for r in eligible),
        'nonempty_preservation':sum(r['retained_count']>0 for r in eligible)/len(eligible) if eligible else None,
        'mean_top10_recall':statistics.mean(r['top10_recall'] for r in eligible) if eligible else None,
        'mean_normalized_score_regret':statistics.mean(r['normalized_score_regret'] for r in eligible) if eligible else None}


def evaluate(view, selected_world_ids, corpus, *, reference_results=None, deadline=None):
    if corpus['sha256']!=digest(corpus['cases']): raise ValueError('Held-out corpus was changed')
    if reference_results is not None:
        if (reference_results.get('snapshot_id')!=view.snapshot_id or
            reference_results.get('corpus_sha256')!=corpus['sha256'] or
            len(reference_results.get('results',[]))!=len(corpus['cases']) or
            reference_results.get('results_sha256')!=digest(reference_results.get('results',[]))):
            raise ValueError('Reference-result cache identity mismatch')
    declared=frozenset(selected_world_ids)
    selected=declared&view.world_ids
    rows=[]; references=[]
    for case in corpus['cases']:
        if deadline is not None and time.monotonic()>deadline: raise TimeoutError('Evaluation wall budget exhausted')
        q=bind(case,view);before=time.perf_counter()
        baseline=view.search(q,limit=10) if reference_results is None else reference_results['results'][len(rows)]
        references.append(baseline)
        baseline_seconds=time.perf_counter()-before
        before=time.perf_counter();retained=view.search(q,limit=10,world_ids=selected)
        if not baseline and retained:raise ValueError('Retained subset produced a match absent from reference')
        actual_ids={r['world_id'] for r in retained}; expected_ids={r['world_id'] for r in baseline}
        overlap=len(actual_ids&expected_ids)
        rows.append({'case_id':case['case_id'],'category':case['category'],'border_side':q['border_side'],
            'anchor_mode':q['anchor_mode'],'request_sha256':digest(q),'reference_count':len(baseline),
            'retained_count':len(retained),'top10_overlap':overlap,
            'top10_recall':overlap/len(baseline) if baseline else None,
            'normalized_score_regret':(max(0.,baseline[0]['score']-retained[0]['score'])/100 if retained else 1.) if baseline else None,
            'reference_seconds':baseline_seconds,'retained_seconds':time.perf_counter()-before,
            'reference_world_ids':[r['world_id'] for r in baseline],'retained_world_ids':[r['world_id'] for r in retained]})
    groups={}
    for category in sorted({r['category'] for r in rows}):groups['category:'+category]=metrics([r for r in rows if r['category']==category])
    for side in SIDES:groups['border:'+str(side)]=metrics([r for r in rows if r['border_side']==side])
    for mode in ('origin','recommended'):groups['mode:'+mode]=metrics([r for r in rows if r['anchor_mode']==mode])
    return {'corpus_sha256':corpus['sha256'],'population_worlds':len(view.world_ids),'retained_queryable_worlds':len(selected),
            'retained_identity_worlds':len(declared),'retained_unqueryable_worlds':len(declared-view.world_ids),
            'discriminating':len(selected)<len(view.world_ids),'summary':metrics(rows),'groups':groups,'rows':rows,
            'empty_retained_regret_convention':'1 when reference nonempty and retained empty; empty references excluded',
            'scope':'Declared observation corpus only; not production capacity recall or actual-game accuracy'}, {
                'snapshot_id':view.snapshot_id,'corpus_sha256':corpus['sha256'],'results':references,
                'results_sha256':digest(references)}
