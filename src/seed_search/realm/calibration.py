"""Formation-level diagnostics on complete, paired actual terrain evidence.

Selected/ranked verification is a biased cohort. Its confusion matrix is useful
for debugging a detector, but is never presented as population precision/recall.
"""
import math

import numpy as np


def _ratio(numerator, denominator):
    return numerator/denominator if denominator else None


def _ranks(values):
    values=np.asarray(values, dtype=float)
    unique, inverse, counts=np.unique(values, return_inverse=True, return_counts=True)
    return (np.cumsum(counts)-counts+(counts-1)/2)[inverse]


def summarize_pairs(pairs, *, target_version, backend_version):
    """Each pair must identify its same seed/anchor/center and actual observation.

    VERIFIED here refers to complete terrain geometry, independent of weighted
    baseline bonuses and final Nether eligibility. Partial actual geometry is
    excluded from both positive and negative truth labels.
    """
    groups={v:{'tp':0,'fp':0,'tn':0,'fn':0,'scores':[]} for v in ('v1','v2')}
    excluded=[]; seen=set()
    for pair in pairs:
        variant=pair.get('variant')
        if variant not in groups:raise ValueError('Calibration supports V1/V2 only')
        identity=(str(pair['seed']),tuple(pair['stronghold']),tuple(pair['center']),variant)
        if identity in seen:raise ValueError('Duplicate formation calibration pair')
        seen.add(identity)
        prediction=pair.get('prediction',{});actual=pair.get('actual',{})
        reason=None
        if pair.get('game_version')!=target_version or pair.get('bds_version')!=backend_version:
            reason='Generation version mismatch'
        elif not pair.get('observation_id'):
            reason='Missing actual observation provenance'
        elif actual.get('evidence')!='VERIFIED' or not actual.get('border_fit',{}).get('complete'):
            reason='Actual geometry or formation footprint incomplete/unverified'
        elif prediction.get('center')!=pair['center'] or actual.get('center')!=pair['center']:
            reason='Prediction and actual terrain centers differ'
        elif any(not isinstance(r.get('geometry_pass'),bool) for r in (prediction,actual)):
            reason='Missing explicit qualification labels'
        elif any(isinstance(r.get('geometry_score'),bool) or not isinstance(r.get('geometry_score'),(int,float)) or
                 not math.isfinite(r['geometry_score']) or not 0<=r['geometry_score']<=100 for r in (prediction,actual)):
            reason='Invalid geometry score'
        if reason:
            excluded.append({'identity':identity,'reason':reason});continue
        predicted=prediction['geometry_pass'];truth=actual['geometry_pass']
        key=('tp' if predicted else 'fn') if truth else ('fp' if predicted else 'tn')
        groups[variant][key]+=1
        groups[variant]['scores'].append((prediction['geometry_score'],actual['geometry_score']))
    results={}
    for variant,group in groups.items():
        tp,fp,tn,fn=(group[k] for k in ('tp','fp','tn','fn'))
        scores=group['scores'];n=len(scores);correlation=None
        if n>1:
            predicted,actual=np.asarray(scores).T
            pr,ar=_ranks(predicted),_ranks(actual)
            if pr.std()>0 and ar.std()>0:correlation=float(np.corrcoef(pr,ar)[0,1])
        results[variant]={'pairs':n,'confusion':{'true_positive':tp,'false_positive':fp,'true_negative':tn,'false_negative':fn},
                          'cohort_precision':_ratio(tp,tp+fp),'cohort_recall':_ratio(tp,tp+fn),
                          'cohort_false_negative_rate':_ratio(fn,tp+fn),
                          'geometry_score_mae':sum(abs(a-b) for a,b in scores)/n if n else None,
                          'geometry_rank_spearman':correlation}
    return {'status':'COMPLETE' if any(g['pairs'] for g in results.values()) else 'UNSUPPORTED',
            'game_version':target_version,'bds_version':backend_version,'variants':results,'excluded':excluded,
            'population_estimate':False,
            'limitations':['Complete actual formation evidence is required; partial observations are not negative labels.',
                           'These are selected-cohort diagnostics, not population precision, recall, or rarity.',
                           'Random/borderline verification must cover the defined population before population inference.']}


def summarize_store(store):
    from .reports import _read_snapshot
    with _read_snapshot(store) as snapshot:
        return _summarize_store(snapshot)


def _summarize_store(store):
    from .raster import Raster
    from .reports import ensure_score_revision_complete
    ensure_score_revision_complete(store)
    game=store.identity['config']['game']
    def pairs():
        for wrapper in store.iter_variants():
            prediction=wrapper['result'];actual=prediction.get('actual_evaluation')
            if actual is None:continue
            candidate=store.get_candidate(wrapper['candidate_id'])
            key=prediction.get('actual_observation_id')
            observation=store.get_observation(key) if key else None
            # A saved label alone cannot upgrade raw partial block observations.
            trusted=bool(observation and str(observation.get('seed'))==str(candidate['seed']) and
                         observation.get('id')==key and observation.get('raster') and
                         Raster(**observation['raster']).quality()=='VERIFIED')
            if not trusted:actual={**actual,'evidence':'PARTIAL'}
            yield {'variant':wrapper['variant'],'seed':candidate['seed'],'stronghold':candidate['stronghold'],
                   'center':wrapper['center'],'game_version':candidate.get('game_version'),
                   'bds_version':observation.get('identity',{}).get('bds_version') if observation else None,
                   'observation_id':key,'prediction':prediction,'actual':actual}
    return summarize_pairs(pairs(),target_version=game['target_version'],backend_version=game['bds_version'])
