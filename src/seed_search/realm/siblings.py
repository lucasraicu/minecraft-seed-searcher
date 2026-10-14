"""Bounded adaptive sibling allocation; statistical selection never proves absence."""
import copy
import fcntl
import hashlib
import json
import math
from pathlib import Path
import time

from ..staged import compose_seed
from .raw import dispersed_high32
from .runner import run_scan
from .store import RealmStore
from .capabilities import identity as backend_identity


def allocation_members(layouts, stats, limit, key, exploration_fraction=.2):
    """Promote observed yield with a deterministic uniform exploration reserve."""
    if not 0 <= exploration_fraction <= 1:
        raise ValueError('Invalid exploration fraction')
    def rank(low):
        row=stats[str(low)]
        # A smoothed rate avoids promoting a layout solely on one fortunate
        # sibling. This is a ranking hint, never a full64 viability veto.
        rate=(row['qualified']+.5)/(row['evaluated']+1)
        return (-rate,-row['anchors'],row['evaluated'],low)
    exploration=math.ceil(limit*exploration_fraction)
    random=sorted(layouts,key=lambda low:hashlib.sha256(f'{key}:{low}'.encode()).digest())[:exploration]
    remaining=[low for low in sorted(layouts,key=rank) if low not in set(random)]
    return random+remaining[:max(0,limit-len(random))]


def run_adaptive(cfg, output, layouts, *, budget=4096, key='0', resume=False, workers=None,
                 promotion=(256,128,64), progress=None):
    """Recoverable rounds 1/4/16; total inputs may be below the maximum budget."""
    if not layouts or len(layouts)>256 or len(set(layouts))!=len(layouts) or any(
            isinstance(low,bool) or not isinstance(low,int) or not 0<=low<2**32 for low in layouts):
        raise ValueError('Adaptive search requires 1–256 distinct lower32 layouts')
    if isinstance(budget,bool) or not isinstance(budget,int) or not 1<=budget<=10000:
        raise ValueError('Adaptive budget must be 1–10000 full64 inputs')
    if len(promotion)!=3 or any(isinstance(n,bool) or not isinstance(n,int) or n<1 or n>256 for n in promotion):
        raise ValueError('Invalid promotion counts')
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    lock=(root/'adaptive.lock').open('a+')
    try:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another adaptive allocator owns this checkpoint') from None
        identity={'policy':'adaptive-siblings-v1','config':cfg,'backend':backend_identity(),
                  'layouts':layouts,'budget':budget,'key':str(key),'promotion':list(promotion)}
        with RealmStore(root,identity,resume) as parent:
            stats=parent.get_state('adaptive_stats') or {str(low):{'evaluated':0,'qualified':0,'anchors':0} for low in layouts}
            next_round=parent.get_state('adaptive_next_round') or 0
            used=sum(r['evaluated'] for r in stats.values())
            highs=dispersed_high32(16,key)
            records=parent.get_state('adaptive_rounds') or []
            partial_round=parent.get_state('adaptive_partial_round')
            for number,target in enumerate((1,4,16)):
                if number<next_round or used>=budget:continue
                if partial_round is not None and partial_round.get('round')==number:
                    chosen=partial_round['chosen']
                    rows=partial_round['rows']
                else:
                    chosen=layouts if number==0 else allocation_members(layouts,stats,min(len(layouts),promotion[number]),f'{key}:round:{number}')
                    rows=[]
                    # Round-robin siblings prevents an exhausted budget favoring the
                    # first selected layout with many more upper32 evaluations.
                    for sibling in range(target):
                        for low in chosen:
                            if sibling>=stats[str(low)]['evaluated'] and len(rows)<budget-used:
                                rows.append({'low32':low,'high32':highs[sibling],
                                             'seed':str(compose_seed(low,highs[sibling])),'round':number})
                if not rows:continue
                run_cfg=copy.deepcopy(cfg)
                run_cfg['search'].update(sequence='manifest',manifest_seeds=[r['seed'] for r in rows])
                child=root/f'round-{number}'
                if not child.exists():
                    from .capabilities import report
                    child.mkdir(parents=True)
                    (child/'compatibility.json').write_text(json.dumps(report(run_cfg),indent=2)+'\n')
                begin=time.perf_counter();cpu=time.process_time()
                child_identity={'policy':'adaptive-round-v1','config':run_cfg,'backend':identity['backend'],'inputs':rows}
                with parent.db:
                    parent._set('adaptive_partial_round', {
                        'round': number,
                        'target': target,
                        'chosen': chosen,
                        'rows': rows,
                        'child_identity': child_identity,
                    })
                status=run_scan(run_cfg,child,len(rows),workers=workers or cfg['search']['workers'],
                                resume=(child/'realm.sqlite').exists(),identity=child_identity,allow_prediction_scale=True)
                elapsed=time.perf_counter()-begin;parent_cpu=time.process_time()-cpu
                with RealmStore(child,resume=True) as store:
                    completed=store.status()['completed_seeds']
                    if status.get('interrupted') or completed<len(rows):
                        # Child batch was interrupted; do not advance round counter by planned batch size.
                        break
                    from itertools import zip_longest
                    for row,result in zip_longest(rows,store.iter_results()):
                        if row is None or result is None:raise ValueError('Adaptive sibling result coverage mismatch')
                        if result['seed']!=row['seed']:raise ValueError('Adaptive sibling manifest mismatch')
                        record=stats[str(row['low32'])]
                        qualified=sum(a['qualification']=='PREDICTED' for a in result['anchors'])
                        record['evaluated']+=1;record['qualified']+=int(qualified>0);record['anchors']+=qualified
                used+=len(rows)
                record={'round':number,'target_siblings':target,'admitted_layouts':len(chosen),'new_inputs':len(rows),
                        'cumulative_inputs':used,'seconds':elapsed,'parent_cpu_seconds':parent_cpu,
                        'worker_cpu_seconds':status['worker_statistics']['worker_cpu_seconds'],
                        'qualified_seeds':sum(r['qualified'] for r in stats.values()),
                        'qualifying_anchors':sum(r['anchors'] for r in stats.values()),'run':str(child)}
                records.append(record)
                with parent.db:
                    parent._set('adaptive_stats',stats);parent._set('adaptive_next_round',number+1);parent._set('adaptive_rounds',records)
                    parent._set('adaptive_partial_round',None)
                partial_round=None
                if progress:progress(record)
            summary={'policy':identity['policy'],'budget':budget,'evaluated_inputs':used,'rounds':records,
                     'qualified_seeds':sum(r['qualified'] for r in stats.values()),
                     'qualifying_anchors':sum(r['anchors'] for r in stats.values()),'stats':stats,
                     'selection_semantics':'finite heuristic allocation with 20% uniform exploration; no lossless world rejection'}
            if partial_round is not None or parent.get_state('adaptive_partial_round') is not None:
                summary['interrupted']=True
            parent.set_state('adaptive_summary',summary)
            return summary
    finally:lock.close()
