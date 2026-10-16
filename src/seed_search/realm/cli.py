"""Additive CLI for the new Realm profile; historical commands retain their parser."""
import argparse
import copy
import hashlib
import heapq
import math
import json
import random
import sys
import time
from pathlib import Path
import yaml
from .config import dynamic_blueprint_config, dynamic_v2_blueprint_config, dynamic_v3_blueprint_config, marine_baseline_blueprint_config, two_group_blueprint_config, two_group_policy, origin_blueprint_config, outpost_blueprint_config, river_blueprint_config, locked_blueprint_config, default_config, blueprint_config, validate_config
from .capabilities import report, identity as provider_identity
from .store import RealmStore, canonical
from .reports import ranked, export, rescore

COMMANDS={'compatibility','baseline','scan','status','terrain','verify-terrain','verify-biomes','verify-realm','verify-caves','results','rescore','calibration','inventory','raw-scan','raw-siblings','raw-adaptive'}


def handles(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    command=None
    offset=0
    while offset<len(args):
        value=args[offset]
        if value in ('--config', '--profile'):offset+=2;continue
        if value.startswith('--config=') or value.startswith('--profile='):offset+=1;continue
        command=value;break
    if command in COMMANDS:return True
    if '--run' in args:
        i=args.index('--run')
        if i+1<len(args) and (Path(args[i+1])/'realm.sqlite').is_file():return True
    path=None
    if '--config' in args:
        i=args.index('--config')
        if i+1<len(args):path=args[i+1]
    for a in args:
        if a.startswith('--config='):path=a.split('=',1)[1]
    if path and Path(path).is_file():
        cfg=yaml.safe_load(Path(path).read_text())
        return isinstance(cfg,dict) and cfg.get('schema_version')==5
    if '--profile' in args or any(a.startswith('--profile=') for a in args):
        return True
    if path is None and command in (None,'-h','--help','search','doctor','benchmark'):
        return True
    return False


def resolve_profile(name):
    if not name or name in ('dynamic2048', 'v3', 'dynamic-envelope-2048-v3'):
        return dynamic_v3_blueprint_config()
    if name in ('dynamic1664', 'v2', 'dynamic-envelope-1664-v2'):
        return dynamic_v2_blueprint_config()
    if name in ('dynamic1664_v1', 'v1', 'dynamic-envelope-1664-v1'):
        return dynamic_blueprint_config()
    if name in ('marine2048', 'marine'):
        return marine_baseline_blueprint_config()
    if name in ('twoGroup2048', 'two_group', 'origin'):
        return two_group_blueprint_config()
    raise ValueError(f'Unknown profile: {name}')


def load(path=None, profile=None):
    if profile:
        cfg = resolve_profile(profile)
    elif path and path in ('dynamic2048', 'v3', 'dynamic-envelope-2048-v3', 'dynamic1664', 'v2', 'dynamic-envelope-1664-v2', 'dynamic1664_v1', 'v1', 'marine2048', 'marine', 'twoGroup2048', 'two_group'):
        cfg = resolve_profile(path)
    elif path:
        cfg = yaml.safe_load(Path(path).read_text())
    else:
        cfg = dynamic_v3_blueprint_config()
    validate_config(cfg)
    return cfg


def make_identity(cfg,count,start):
    return {'schema':1,'config':cfg,'config_sha256':hashlib.sha256(canonical(cfg).encode()).hexdigest(),
            'backend':provider_identity(),'count':count,'start_index':start,'evaluator':'seed_search.realm.baseline:evaluate_seed'}


def progress_printer():
    last=[0.]
    def progress(status):
        if time.monotonic()-last[0]<10:return
        last[0]=time.monotonic()
        print(json.dumps({'progress':status}),file=sys.stderr,flush=True)
    return progress


def qualified_pool_digest(store, batch_size=512):
    """Hash qualified IDs without decoding full saved world observations."""
    digest=hashlib.sha256();last=''
    while True:
        # Filter a primary-key page after reading it; an IN predicate makes SQLite
        # repeatedly sort the remaining qualification-index rows on each page.
        rows=store.db.execute("SELECT id,qualification FROM candidates WHERE id>? ORDER BY id LIMIT ?",(last,batch_size)).fetchall()
        if not rows:break
        for candidate_id,qualification in rows:
            if qualification in ('PREDICTED','VERIFIED'):digest.update((candidate_id+'\n').encode())
        last=rows[-1][0]
    return digest.hexdigest()


def run_benchmark(cfg,output,count,workers):
    if count<=0:raise ValueError('Benchmark count must be positive')
    if count==1000000 and len(workers)!=1:
        raise ValueError('One-million benchmark requires one selected worker configuration')
    from .runner import run_scan
    root=Path(output);root.mkdir(parents=True,exist_ok=True);rows=[]
    for number in workers:
        run=root/f'workers-{number}'
        if (run/'realm.sqlite').exists():raise ValueError('Benchmark output exists; choose a fresh output directory')
        run.mkdir(exist_ok=True)
        (run/'compatibility.json').write_text(json.dumps(report(cfg),indent=2)+'\n')
        start=time.perf_counter()
        status=run_scan(cfg,run,count,workers=number,identity=make_identity(cfg,count,0),
                        progress=progress_printer(),allow_prediction_scale=True)
        wall=time.perf_counter()-start
        if status['completed_seeds']!=count or status.get('interrupted'):
            raise RuntimeError('Benchmark did not complete its exact input coverage; checkpoint retained')
        with RealmStore(run,resume=True) as store:
            # Keep compact hashes rather than loading the full result pool.
            qualified=qualified_pool_digest(store)
        storage=sum(p.stat().st_size for p in run.glob('realm.sqlite*'))
        row={'workers':number,'count':count,'wall_seconds':wall,'seeds_per_second':count/wall,
             'completed_seeds':status['completed_seeds'],'qualified_pool_sha256':qualified,
             'candidate_counts':status['candidate_counts'],'counts':status['counts'],
             'memory':status['memory'],'worker_statistics':status['worker_statistics'],'storage_bytes':storage}
        rows.append(row)
        (root/'benchmark.json').write_text(json.dumps({'workload':'universal baseline prediction including spawn/checkpoint; no terrain/BDS',
                                                       'rows':rows,'distinct_full64_inputs':count,
                                                       'total_evaluations':count*len(rows)},indent=2)+'\n')
        print(json.dumps({'benchmark_step':number,'seconds':wall,'seeds_per_second':count/wall}),file=sys.stderr,flush=True)
    if len({r['qualified_pool_sha256'] for r in rows})!=1:raise ValueError('Worker-count reproducibility mismatch')
    return {'output':str(root.resolve()),'rows':[{k:r[k] for k in ('workers','count','wall_seconds','seeds_per_second','storage_bytes','candidate_counts')} for r in rows],
            'distinct_full64_inputs':count,'worker_reproducibility':True}


def select_verification(store, variant, cfg, *, top=1, borderline=0, unusual=0, random_count=0, sampling_key=0,
                        adapter=None, spacing=16, include_cached=False, retry_failed=False, require_footprint=False):
    """Bounded deterministic picks plus a reservoir audit of the remaining qualified pool."""
    counts = {'top':top, 'borderline':borderline, 'unusual':unusual, 'random_low_rank':random_count}
    if any(isinstance(n,bool) or not isinstance(n,int) or n<0 for n in counts.values()):
        raise ValueError('Verification selection counts must be nonnegative integers')
    remaining = max(0,cfg['bds']['verification_budget']-(store.get_state('bds_verification_used') or 0))
    from .verification import VerificationAdapter
    from .verification_plan import verification_region
    adapter = adapter or VerificationAdapter(cfg,store)
    slots = cfg['bds']['verification_budget'] if include_cached else remaining
    selected = []
    ids = set()
    new_selected = 0
    visits={'missing_footprint_visits':0,'cached_exclusion_visits':0}
    if variant not in cfg['terrain'].get('variants', ('v1','v2')):
        raise ValueError('Requested terrain variant is inactive in this saved configuration')
    thresholds = cfg['terrain'].get(variant,{})
    def identity(wrapper):
        return wrapper['candidate_id'],tuple(wrapper['center'])
    def eligible():
        for wrapper in store.iter_variants(variant=variant):
            row = store.db.execute('SELECT qualification,seed FROM candidates WHERE id=?',(wrapper['candidate_id'],)).fetchone()
            if not row or row[0] not in ('PREDICTED','VERIFIED') or identity(wrapper) in ids:
                continue
            prediction={**wrapper['result'],'center':wrapper['center']}
            bounds=verification_region(prediction,variant,cfg,spacing)
            if bounds is None and require_footprint:
                visits['missing_footprint_visits']+=1
                continue
            cached=adapter.get_cached(row[1],bounds,spacing) if bounds is not None else None
            retry=bool(cached and cached.get('status')=='FAILED' and retry_failed and new_selected<remaining)
            review=bool(cached and not retry)
            if review and not include_cached:
                visits['cached_exclusion_visits']+=1
                continue
            if not review and new_selected>=remaining:
                continue
            yield {**wrapper,'verification_bounds':list(bounds) if bounds else None,
                   'verification_cached':review,'verification_retry':retry}
    def tie(wrapper):
        return wrapper['candidate_id'],tuple(wrapper['center'])
    def top_key(wrapper):
        r = wrapper['result']
        return ({'VERIFIED':0,'PREDICTED':1}.get(r.get('evidence'),2), not r.get('geometry_pass',False), -r.get('score',0), *tie(wrapper))
    pairs = [('diameter','diameter_min'),('diameter','diameter_max'),('island_area','area'),('water_rays','water_rays'),('median_water_width','water_width')] if variant=='v1' else [('ridge_rays','ridge_rays'),('relative_relief','relief'),('ridge_distance','distance_min'),('ridge_distance','distance_max'),('largest_gap_rays','largest_gap_rays')]
    if variant=='v1' and thresholds.get('mode')=='coastal_continent':
        thresholds=thresholds.get('coastal_continent',{})
        pairs=[('mainland_fraction','land_fraction_min'),('mainland_fraction','land_fraction_max')]
    def margin(wrapper):
        metrics = wrapper['result'].get('metrics',{})
        values = [abs(metrics[m]-thresholds[t])/thresholds[t] for m,t in pairs
                  if isinstance(metrics.get(m),(int,float)) and not isinstance(metrics.get(m),bool)
                  and math.isfinite(metrics[m]) and thresholds.get(t,0)>0]
        return min(values,default=math.inf)
    def unusual_weight(wrapper):
        r = wrapper['result'];border = r.get('border_fit',{})
        return (4*int(r.get('evidence') in ('PARTIAL','UNSUPPORTED','FAILED'))+
                3*int(border.get('state',border.get('status')) in ('outside','unknown'))+
                2*int(not r.get('geometry_pass',False) and r.get('geometry_score',0)>=70)+
                int(any('uncertain' in reason or 'truncat' in reason for reason in r.get('reasons',[]))))
    rules = {'top':'Existing evidence/geometry/score ordering among qualified baseline anchors',
             'borderline':'Closest normalized measured geometry threshold within 25 percent',
             'unusual':'Partial/unsupported data, outside/unknown border, high-score geometry failure, or uncertainty',
             'random_low_rank':'Uniform reservoir from qualified variants remaining after deterministic selections'}
    for reason,key,accept in [('top',top_key,lambda w:True),
                              ('borderline',lambda w:(margin(w),*tie(w)),lambda w:margin(w)<=.25),
                              ('unusual',lambda w:(-unusual_weight(w),*tie(w)),lambda w:unusual_weight(w)>0)]:
        number = min(counts[reason],slots-len(selected))
        picks = heapq.nsmallest(number,(w for w in eligible() if accept(w)),key=key) if number else []
        for wrapper in picks:
            if not wrapper['verification_cached'] and new_selected>=remaining:
                continue
            ids.add(identity(wrapper));selected.append((wrapper,reason,1.0))
            new_selected+=int(not wrapper['verification_cached'])
    rng = random.Random(sampling_key);seen=0;cached_seen=0;random_picks=0
    def reservoir(number,cached):
        picks=[];population=0
        if number:
            for wrapper in eligible():
                if wrapper['verification_cached']!=cached:
                    continue
                population+=1
                if len(picks)<number:picks.append(wrapper)
                else:
                    j=rng.randrange(population)
                    if j<number:picks[j]=wrapper
        return picks,population
    number=min(random_count,slots-len(selected),remaining-new_selected)
    picks,seen=reservoir(number,False)
    for wrapper in picks:
        selected.append((wrapper,'random_low_rank',min(1,number/seen)))
        ids.add(identity(wrapper));new_selected+=1;random_picks+=1
    if include_cached:
        number=min(random_count-random_picks,slots-len(selected))
        picks,cached_seen=reservoir(number,True)
        selected.extend((w,'random_low_rank',min(1,number/cached_seen)) for w in picks)
    return selected, {'requested':counts,'remaining_attempt_budget':remaining,'sampling_key':sampling_key,
                      'new_attempt_selections':new_selected,'cached_reviews':len(selected)-new_selected,
                      'include_cached':include_cached,'retry_failed':retry_failed,'spacing':spacing,
                      'eligibility_scan_visits':visits,
                      'random_unselected_population':seen,'random_cached_population':cached_seen,'rules':rules,
                      'probability_policy':'Deterministic conditional inclusion=1; random inclusion=k/N separately for new-attempt and cached-review strata after deterministic exclusions; not population accuracy'}


def main(argv=None):
    from ..seeds import parse_seed
    parser=argparse.ArgumentParser(description='Stronghold-anchored Bedrock Realm predictions and explicit verification')
    parser.add_argument('--config')
    parser.add_argument('--profile', help='Blueprint configuration profile (e.g. dynamic2048, v3, dynamic1664)')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('compatibility');p.add_argument('--output');p.add_argument('--profile')
    p=sub.add_parser('doctor');p.add_argument('--output');p.add_argument('--profile')
    p=sub.add_parser('benchmark');p.add_argument('--count',type=int,default=1000);p.add_argument('--workers',type=int,nargs='+',default=[1,12,16,18,24,30,36]);p.add_argument('--output',default='runs/realm-benchmark');p.add_argument('--profile')
    for name in ('baseline','search','scan'):
        p=sub.add_parser(name);p.add_argument('--count',type=int,required=True);p.add_argument('--start-index',type=int,default=0)
        p.add_argument('--output',required=True);p.add_argument('--workers',type=int);p.add_argument('--stop-after',type=int)
        p.add_argument('--dry-run',action='store_true')
        p.add_argument('--prediction-scale',action='store_true',help='Explicitly run larger prediction-only ranges after compatibility report; never certifies generation')
        p.add_argument('--profile')
    p=sub.add_parser('resume');p.add_argument('--run',required=True);p.add_argument('--workers',type=int);p.add_argument('--stop-after',type=int);p.add_argument('--prediction-scale',action='store_true');p.add_argument('--profile')
    for command in ('baseline','search','scan','resume'):
        native=sub.choices[command]
        native.add_argument('--executor',choices=['python','native'],default=None)
        native.add_argument('--native-build',type=Path,help='Explicit audited native build directory; otherwise use packaged extension')
        native.add_argument('--native-threads',type=int)
        native.add_argument('--native-batch-size',type=int)
        native.add_argument('--retention',choices=['full','survivors'],default=None,help='Compact survivors mode omits rejected per-input evidence')
        native.add_argument('--max-misses',type=int,default=None,help='Compact retention budget; v2 counts flexible deficit categories and must match the resolved policy (default B=2)')
    p=sub.add_parser('inventory');p.add_argument('--run',required=True);p.add_argument('--limit',type=int)
    p.add_argument('--candidate');p.add_argument('--include-pending',action='store_true')
    p.add_argument('--all-starts',action='store_true',help='Explicit complete predictor start inventory for one candidate')
    p=sub.add_parser('raw-scan');p.add_argument('--output',required=True);p.add_argument('--start',type=int,default=0)
    p.add_argument('--count',type=int,required=True);p.add_argument('--threads',type=int,default=18)
    p.add_argument('--mode',choices=['presence','capped','complete','reference'],default='capped')
    p.add_argument('--resume',action='store_true');p.add_argument('--top',type=int,default=64);p.add_argument('--exploration',type=int,default=16)
    p.add_argument('--ranking',choices=['legacy','geometry'],default='legacy');p.add_argument('--feature-pool',type=int,default=1024)
    p=sub.add_parser('raw-siblings');p.add_argument('--selection',required=True);p.add_argument('--output',required=True)
    p.add_argument('--limit',type=int,default=128);p.add_argument('--siblings',type=int,default=4);p.add_argument('--key',default='0')
    p.add_argument('--resume',action='store_true')
    p=sub.add_parser('raw-adaptive');p.add_argument('--selection',required=True);p.add_argument('--output',required=True)
    p.add_argument('--budget',type=int,default=4096);p.add_argument('--key',default='0');p.add_argument('--resume',action='store_true')
    p=sub.add_parser('status');p.add_argument('--run',required=True)
    p=sub.add_parser('calibration');p.add_argument('--run',required=True)
    p=sub.add_parser('terrain');p.add_argument('--run','--baseline-run',dest='run',required=True);p.add_argument('--variant',choices=['v1','v2','all'],default='all');p.add_argument('--limit',type=int)
    terrain_pool=p.add_mutually_exclusive_group()
    terrain_pool.add_argument('--pool-revision',help='Use a saved baseline membership identifier, such as pool-00000001')
    terrain_pool.add_argument('--new-pool-revision',action='store_true',help='Explicitly snapshot current baseline membership for both variants')
    p.add_argument('--continue-deferred-halos',action='store_true',help='Authorize one additional queued halo expansion per center beyond the automatic resource cap')
    p=sub.add_parser('results');p.add_argument('--run',required=True);p.add_argument('--variant',choices=['baseline','v1','v2'],default='baseline');p.add_argument('--limit',type=int,default=20);p.add_argument('--export',action='store_true')
    p=sub.add_parser('rescore');p.add_argument('--run',required=True)
    scoring_source=p.add_mutually_exclusive_group(required=True)
    scoring_source.add_argument('--policy')
    scoring_source.add_argument('--resume',dest='resume_revision',action='store_true',help='Resume an interrupted revision using its persisted policy')
    p=sub.add_parser('verify-terrain');p.add_argument('--run',required=True);p.add_argument('--variant',choices=['v1','v2'],required=True);p.add_argument('--top',type=int,default=1)
    p.add_argument('--borderline',type=int,default=0);p.add_argument('--unusual',type=int,default=0)
    p.add_argument('--random',type=int,default=0);p.add_argument('--sampling-key',type=int,default=0);p.add_argument('--spacing',type=int,default=16)
    p.add_argument('--include-cached',action='store_true',help='Review cached observations without charging new-attempt slots')
    p.add_argument('--retry-failed',action='store_true',help='Explicitly retry failed observations within the remaining attempt budget')
    p=sub.add_parser('verify-realm');p.add_argument('--run',required=True);p.add_argument('--candidate',required=True);p.add_argument('--evidence',help='Actual pinned-generation structure evidence JSON')
    p=sub.add_parser('verify-biomes');p.add_argument('--run',required=True);p.add_argument('--candidate',required=True)
    p.add_argument('--points',required=True,help='JSON file containing 1..16 explicit [x,z] surface points within the Realm')
    p.add_argument('--retry-failed',action='store_true')
    p=sub.add_parser('verify-caves');p.add_argument('--seed',type=parse_seed,required=True);p.add_argument('--stronghold-x',type=int,required=True);p.add_argument('--stronghold-z',type=int,required=True);p.add_argument('--provider',choices=['predictor','bds'],default='predictor');p.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    store=None
    try:
        profile_arg = getattr(args, 'profile', None)
        if hasattr(args,'run'):
            store=RealmStore(args.run,resume=True)
            cfg=store.identity['config']
            if args.config or profile_arg:
                explicit=load(args.config, profile_arg)
                from .store import semantic_identity
                if semantic_identity({'config':cfg})!=semantic_identity({'config':explicit}):raise ValueError('Run configuration differs from supplied Realm profile')
                cfg=explicit
        else:cfg=load(args.config, profile_arg)
        if store and args.command in ('resume','terrain','verify-terrain','verify-biomes','verify-realm'):
            from .reports import ensure_score_revision_complete
            ensure_score_revision_complete(store)
        # Baseline resume retains its original computation identity. The saved
        # reporting policy is reapplied generation-free after new rows commit.
        if store and args.command!='resume' and store.get_state('score_policy'):
            cfg=copy.deepcopy(cfg);cfg['scoring']=store.get_state('score_policy')['scoring']
        if args.command in ('compatibility','doctor'):
            result=report(cfg)
            if args.output:Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        elif args.command=='benchmark':
            result=run_benchmark(cfg,args.output,args.count,args.workers)
        elif args.command in ('baseline','search','scan','resume'):
            from .runner import run_scan
            resume=args.command=='resume'
            run=Path(args.run if resume else args.output)
            run.mkdir(parents=True,exist_ok=True)
            count=store.identity['count'] if resume else args.count
            first=store.identity['start_index'] if resume else args.start_index
            execution=args.executor or ((store.identity or {}).get('execution','python') if store else 'python')
            native_build=args.native_build or ((store.identity or {}).get('native_build') if store and execution=='native' else None)
            native_threads=args.native_threads if args.native_threads is not None else ((store.get_state('native_pipeline') or {}).get('threads',16) if store else 16)
            native_batch=args.native_batch_size if args.native_batch_size is not None else (store.get_state('batch_size') if store and execution=='native' else 4096)
            saved_retention=(store.identity or {}).get('retention',{}) if store else {}
            retention=args.retention or saved_retention.get('mode','survivors' if execution=='native' else 'full')
            misses=args.max_misses if args.max_misses is not None else saved_retention.get('max_misses',(cfg['search']['max_misses'] if two_group_policy(cfg) else 1 if cfg.get('screening_revision') else 2) if retention=='survivors' else 0)
            if not resume and execution=='native' and retention=='survivors' and two_group_policy(cfg):
                cfg=copy.deepcopy(cfg)
                cfg['search']['max_misses']=misses
                validate_config(cfg)
            ident=make_identity(cfg,count,first)
            (run/'compatibility.json').write_text(json.dumps(report(cfg),indent=2)+'\n')
            if execution=='python' and (retention!='full' or misses):raise ValueError('Compact retention requires --executor native')
            if execution=='python' and any(v is not None for v in (args.native_build,args.native_threads,args.native_batch_size)):
                raise ValueError('Native options require --executor native')
            execution_options={'execution':execution,'native_build':native_build,'native_threads':native_threads,'native_batch_size':native_batch,'retention':retention,'max_misses':misses} if execution=='native' else {}
            if store:store.close();store=None
            if getattr(args,'dry_run',False):
                result={'planned_seeds':count,'start_index':first,'workers':args.workers or cfg['search']['workers'],
                        'output':str(run.resolve()),'executed_seeds':0,'qualification':'predictions only',
                        'executor':execution,'retention':retention,'max_misses':misses,'above_pilot_limit':count>cfg['search']['pilot_limit'],'requires_explicit_prediction_scale':count>cfg['search']['pilot_limit']}
            else:
                result=run_scan(cfg,run,count,first,args.workers,resume,ident,stop_after=args.stop_after,
                                progress=progress_printer(),allow_prediction_scale=args.prediction_scale,**execution_options)
                with RealmStore(run,resume=True) as saved:
                    if saved.get_state('score_policy'):rescore(saved,saved.get_state('score_policy'))
        elif args.command=='inventory':
            from .inventory import run_inventory,complete_start_audit
            if args.all_starts:
                if not args.candidate:raise ValueError('--all-starts requires --candidate')
                result=complete_start_audit(store,cfg,args.candidate)
            else:
                result=run_inventory(store,cfg,limit=args.limit,candidate_id=args.candidate,include_pending=args.include_pending,progress=progress_printer())
        elif args.command=='raw-scan':
            from .raw import run_raw,rank_geometry
            result=run_raw(args.output,args.start,args.count,threads=args.threads,top=max(args.top,args.feature_pool) if args.ranking=='geometry' else args.top,exploration=args.exploration,resume=args.resume,mode=args.mode)
            if args.ranking=='geometry':
                result=rank_geometry(result,top=args.top,exploration=args.exploration)
                path=Path(args.output)/'geometry-selection.json';temp=path.with_suffix('.tmp')
                temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(path)
        elif args.command=='raw-siblings':
            from .raw import evaluate_siblings,dispersed_high32
            selection=json.loads(Path(args.selection).read_text())
            result=evaluate_siblings(cfg,args.output,selection,high32=dispersed_high32(args.siblings,args.key),limit=args.limit,resume=args.resume)
        elif args.command=='raw-adaptive':
            from .siblings import run_adaptive
            from .capabilities import identity
            selection=json.loads(Path(args.selection).read_text())
            if selection.get('backend')!=identity() or selection.get('geometry')!={'deployment':cfg['deployment'],'discovery':cfg['discovery']}:
                raise ValueError('Adaptive selection identity/geometry changed')
            layouts=[r['low32'] for r in selection['selected'][:256]]
            result=run_adaptive(cfg,args.output,layouts,budget=args.budget,key=args.key,resume=args.resume,progress=progress_printer())
        elif args.command=='status':result=store.status()
        elif args.command=='calibration':
            from .calibration import summarize_store
            result=summarize_store(store)
        elif args.command=='terrain':
            from .config import dynamic_v2_policy
            if dynamic_v2_policy(cfg):
                raise ValueError("Terrain workflow is not applicable to dynamic-envelope-1664-v2 (no active terrain variants)")
            from .terrain import run_terrain
            policy=store.get_state('score_policy')
            if policy:
                cfg=copy.deepcopy(cfg);cfg['scoring']=policy['scoring']
            result=run_terrain(store,cfg,tuple(cfg['terrain'].get('variants',('v1','v2'))) if args.variant=='all' else (args.variant,),args.limit,progress=progress_printer(),
                               pool_revision=args.pool_revision,new_pool_revision=args.new_pool_revision,
                               continue_deferred_halos=args.continue_deferred_halos)
        elif args.command=='results':
            if args.limit<0:raise ValueError('Result limit cannot be negative')
            result=export(store) if args.export else {'status':store.status(),'variant':args.variant,'results':ranked(store,args.variant,args.limit)}
        elif args.command=='rescore':
            if args.resume_revision:
                revision=store.get_state('rescore_revision')
                if not revision or revision.get('status')!='running':
                    raise ValueError('No interrupted score revision to resume')
                policy=revision['policy']
            else:policy=load(args.policy)
            result=rescore(store,policy)
        elif args.command=='verify-caves':
            from .caves import verify_caves
            from .verification import VerificationAdapter
            if args.provider=='bds':result=verify_caves(args.seed,(args.stronghold_x,args.stronghold_z),cfg,adapter=VerificationAdapter(cfg))
            else:
                from ..backend import Backend
                with Backend(args.seed) as backend:result=verify_caves(args.seed,(args.stronghold_x,args.stronghold_z),cfg,predictor=backend)
            Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        elif args.command=='verify-biomes':
            from .surface import verify_surface_families,save_surface_verification
            from .verification import VerificationAdapter
            candidate=store.get_candidate(args.candidate)
            if candidate is None:raise ValueError('Unknown candidate')
            points=json.loads(Path(args.points).read_text())
            if not isinstance(points,list):raise ValueError('Surface points JSON must be an array')
            result=verify_surface_families(candidate,cfg,VerificationAdapter(cfg,store),points,retry_failed=args.retry_failed)
            # Patch only the new evidence channel; preserve prediction eligibility,
            # scores and all previously saved observations.
            save_surface_verification(store,candidate['id'],result)
        elif args.command=='verify-realm':
            from .inventory import run_inventory
            run_inventory(store,cfg,candidate_id=args.candidate,include_pending=True)
            from .verification import VerificationAdapter
            row=store.db.execute('SELECT result FROM candidates WHERE id=?',(args.candidate,)).fetchone()
            if not row:raise ValueError('Unknown candidate')
            candidate=json.loads(row[0]);evidence=json.loads(Path(args.evidence).read_text()) if args.evidence else None
            result=VerificationAdapter(cfg,store).verify_final_nether(candidate['seed'],candidate.get('evaluation_center',candidate['stronghold']),evidence=evidence)
            candidate['final_nether']=result;candidate['final_nether_status']=result['status']
            candidate['realm_eligibility']='PENDING; Overworld generated structure/terrain evidence still required'
            with store.db:store.db.execute('UPDATE candidates SET result=? WHERE id=?',(canonical(candidate),candidate['id']))
            store.upsert_observation(candidate['id'],{'kind':'final_nether','candidate_id':candidate['id'],**result})
        else:
            from .config import dynamic_v2_policy
            if dynamic_v2_policy(cfg):
                raise ValueError("Terrain verification is not applicable to dynamic-envelope-1664-v2 (no active terrain variants)")
            from .verification import VerificationAdapter,calibrate_prediction
            from .terrain import evaluate_v1,evaluate_v2,apply_score_policy,attach_actual_evaluation
            from .raster import Raster
            from ..backend import Backend
            if args.spacing not in (1,4,8,16,32,64):raise ValueError('Invalid verification spacing')
            adapter=VerificationAdapter(cfg,store)
            selected,selection_policy=select_verification(store,args.variant,cfg,top=args.top,borderline=args.borderline,
                                                         unusual=args.unusual,random_count=args.random,sampling_key=args.sampling_key,
                                                         adapter=adapter,spacing=args.spacing,include_cached=args.include_cached,
                                                         retry_failed=args.retry_failed,require_footprint=True)
            observations=[]
            for wrapper,reason,probability in selected:
                candidate=json.loads(store.db.execute('SELECT result FROM candidates WHERE id=?',(wrapper['candidate_id'],)).fetchone()[0])
                if candidate.get('inventory',{}).get('tasks'):
                    from .inventory import run_inventory
                    run_inventory(store,cfg,candidate_id=candidate['id'],include_pending=True)
                    candidate=store.get_candidate(candidate['id'])
                if candidate['qualification'] not in ('PREDICTED','VERIFIED'):continue
                selection={'kind':'verification_selection','candidate_id':candidate['id'],'variant':args.variant,
                           'center':wrapper['center'],'selection_reason':reason,'selection_probability':probability,
                           'selection_policy':selection_policy}
                selection['id']=hashlib.sha256(canonical(selection).encode()).hexdigest()
                store.upsert_observation(candidate['id'],selection)
                prediction=wrapper['result'];footprint=wrapper.get('verification_bounds')
                if footprint is None:
                    observations.append({'candidate_id':candidate['id'],'status':'PARTIAL','reason':'No measured formation footprint; run terrain first'})
                    continue
                observation=adapter.verify_candidate(candidate,bounds=footprint,spacing=args.spacing,selection_reason=reason,
                                                     selection_probability=probability,retry_failed=wrapper['verification_retry'])
                if 'raster' in observation:
                    raster=Raster(**observation['raster']);evaluate=evaluate_v1 if args.variant=='v1' else evaluate_v2
                    # Generated blocks do not certify the predictor's biome IDs.
                    from .biomes import raster_variant_fit
                    fit,biome_status,biome_provenance=raster_variant_fit(raster,args.variant,target_version=cfg['game']['target_version'])
                    from .coastal import coastal_mode, monument_inputs
                    coastal_options={'monuments':monument_inputs(candidate)} if args.variant=='v1' and coastal_mode(cfg) else {}
                    actual=evaluate(raster,wrapper['center'],candidate['bounds']['overworld'],candidate.get('evaluation_center',candidate['stronghold']),thresholds=cfg['terrain'].get(args.variant),rays=cfg['terrain'].get('rays',32),biome_fit=fit,baseline_quality=min(100.,100.*(candidate.get('baseline_score') if candidate.get('baseline_score') is not None else candidate.get('baseline_score_observed',0))/cfg['scoring']['baseline_quality_cap']),**coastal_options)
                    actual['biome_fit_provenance']=biome_provenance
                    apply_score_policy(actual,cfg['scoring'],source='actual',biome_fit=fit,component_status={
                        'geometry':actual['evidence'],'biome_fit':biome_status,
                        'baseline_quality':candidate.get('qualification','PENDING') if candidate.get('baseline_score_complete',True) else 'PARTIAL'})
                    attach_actual_evaluation(prediction,actual,cfg['scoring'])
                    prediction['actual_observation_id']=observation['id']
                    with Backend(candidate['seed']) as backend:observation['calibration']=calibrate_prediction(backend,observation)
                    store.upsert_variant(wrapper['candidate_id'],args.variant,wrapper['center'],prediction)
                    store.upsert_observation(candidate['id'],observation)
                observations.append({'id':observation.get('id'),'candidate_id':candidate['id'],'status':observation['status'],'reason':observation.get('reason'),'calibration':observation.get('calibration')})
            result={'selected':len(selected),'selection_policy':selection_policy,'observations':observations}
        print(json.dumps(result,indent=2,allow_nan=False),flush=True)
        return result
    except (ValueError,KeyError,FileNotFoundError) as exc:parser.error(str(exc))
    finally:
        if store:store.close()


if __name__ == '__main__':
    main()
