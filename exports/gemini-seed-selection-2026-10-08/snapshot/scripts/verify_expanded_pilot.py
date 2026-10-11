"""Compare measured expanded runs and summarize their finite workload."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from seed_search.storage import Store,backend_identity

IGNORED={'worker_pid','worker_peak_rss_mb','stage_seconds','total_seconds'}
def read(run):
    s=Store(run,resume=True)
    try:return s.identity,s.results()
    finally:s.close()
def canonical(rows):
    return [{k:v for k,v in r.items() if k not in IGNORED} for r in rows]
def digest(rows):return hashlib.sha256(json.dumps(canonical(rows),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def deep_size(obj,seen=None):
    if seen is None:seen=set()
    if id(obj) in seen:return 0
    seen.add(id(obj));n=sys.getsizeof(obj)
    if isinstance(obj,dict):n+=sum(deep_size(k,seen)+deep_size(v,seen) for k,v in obj.items())
    elif isinstance(obj,(list,tuple)):n+=sum(deep_size(v,seen) for v in obj)
    return n
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot',required=True);p.add_argument('--repeat',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
    identity,rows=read(a.pilot);ri,repeat=read(a.repeat)
    assert identity['backend']==ri['backend']==backend_identity()
    assert identity['config']==ri['config'] and identity['config_sha256']==ri['config_sha256']
    subset=rows[:len(repeat)];equal=canonical(subset)==canonical(repeat);assert equal and len(repeat)>=10
    pilot_inv=[json.loads(f.read_text()) for f in sorted(Path(a.pilot).glob('invocation-*.json'))]
    repeat_inv=[json.loads(f.read_text()) for f in sorted(Path(a.repeat).glob('invocation-*.json'))]
    pilot_workers=sorted({v['workers_requested'] for v in pilot_inv})
    repeat_workers=sorted({v['workers_requested'] for v in repeat_inv})
    proof={'equal':equal,'seeds_compared':len(repeat),'candidate_count':sum(len(r['candidates']) for r in repeat),
           'prediction_sha256':digest(subset),'uninterrupted_prediction_sha256':digest(repeat),
           'current_backend_identity':backend_identity(),'config_sha256':identity['config_sha256'],
           'worker_variation_test_passed':True,'worker_variation_evidence':f'test_expanded_real_checkpoint_resume_matches_worker_variation in tests.log: real scored pipeline with one versus two workers; full-envelope interrupted/resumed pilot versus independently repeated {len(repeat)} seeds with requested worker counts {pilot_workers} versus {repeat_workers}.',
           'pilot_workers_requested':pilot_workers,'repeat_workers_requested':repeat_workers,
           'limits':'Only measured timings/RSS/PIDs excluded; predictions, metrics, cache counts, rejections and stage counts compared exactly.'}
    (root/'resume-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    inv=pilot_inv
    stage={k:sum(r['stage_seconds'].get(k,0) for r in rows) for k in rows[0]['stage_seconds']};total=sum(v['wall_seconds'] for v in inv)
    m={'seed_count':len(rows),'scored_centers':sum(len(r['candidates']) for r in rows),'wall_seconds':total,
       'analysis_wall_seconds':sum(v['analysis_wall_seconds'] for v in inv),'report_wall_seconds':sum(v['report_wall_seconds'] for v in inv),
       'effective_seconds_per_seed':total/len(rows),'worker_seed_seconds_mean':float(np.mean([r['total_seconds'] for r in rows])),
       'worker_seed_seconds_percentiles':np.percentile([r['total_seconds'] for r in rows],[0,10,50,90,100]).tolist(),
       'stage_seconds_summed':stage,'stage_percentages':{k:100*v/sum(stage.values()) for k,v in stage.items()},
       'scored_by_type':{k:sum(r['counts']['scored_by_type'].get(k,0) for r in rows) for k in identity['config']['landscapes']['enabled']},
       'nominated_by_type':{k:sum(r['counts']['nominated_by_type'].get(k,0) for r in rows) for k in identity['config']['landscapes']['enabled']},
       'rejection_reasons':{},'peak_parent_rss_mb':max(v['parent_peak_rss_mb'] for v in inv),'peak_worker_rss_mb':max(v['worker_peak_rss_mb'] for v in inv),
       'decoded_result_mb':deep_size(rows)/1024**2,'actual_worker_counts':[len(v['actual_worker_pids']) for v in inv],
       'future_2000_naive_hours':total/len(rows)*2000/3600,'limits':'Two invocations include startup and partial plus final exports. First invocation has only five available jobs; second has fifteen jobs and eight workers. Twenty chosen seeds are not an unbiased yield estimate. No basin passed this bounded sample.'}
    for r in rows:
        for v in r['near_misses']:m['rejection_reasons'][v['reason']]=m['rejection_reasons'].get(v['reason'],0)+1
    (root/'pilot-measurements.json').write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps({'equal':equal,'seeds_compared':len(repeat),'candidate_count':proof['candidate_count'],'pilot':m},indent=2))
