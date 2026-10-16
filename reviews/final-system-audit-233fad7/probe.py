"""Bounded independent probes; writes only this audit's evidence directory."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.native_batch import Prototype,seeds_np
from seed_search.realm.config import dynamic_v2_blueprint_config,validate_config
from seed_search.realm.runner import _seed
from seed_search.realm.blueprint import dynamic_v2_score
from seed_search.realm.dynamic import scenic_pair_bonus_v2,treasure_bastion_bonus_v2
from seed_search.realm.reports import _candidate_rescore
from seed_search.web import server
from seed_search.seeds import MASK64
OUT=Path(__file__).parent
p=Prototype('/tmp/final-audit-233fad7-build',dynamic_v2_blueprint_config())
evidence={'commit':'233fad76fddc5667e77c27ab7e5cc83d3669a7a2','build':p.identity}
permutations=[]
for first,end in [(0,8),(2**53-2,2**53+6),(2**63-2,2**63+6),(2**64-8,2**64)]:
    for key in [0,123,-1,2**64+5]:
        try:
            actual=list(map(int,seeds_np(first,end,key)))
            expected=[_seed(i,{'sequence':'permutation','run_key':str(key)}) for i in range(first,end)]
            permutations.append({'first':str(first),'end':str(end),'run_key':str(key),'equal':actual==expected,'length':len(actual)})
        except Exception as e:permutations.append({'first':str(first),'end':str(end),'run_key':str(key),'error':repr(e)})
evidence['vectorized_seed_parity']=permutations
with p.sweep(np.array([1.0],dtype=np.float64),retention='survivors',max_misses=3) as batch:
    evidence['float_input']={'input':1.0,'native_seed':str(int(batch.pointer.verdicts[0].seed)),
                             'returned_without_error':True,'retained':batch.pointer.result_count}
class Captured(Exception):pass
class LibraryBoundary:
    def nb_sweep(self,values,count,*args):
        evidence['short_numpy_buffer']={'dtype':'int32','buffer_uint64_elements':len(values),'native_count':count}
        raise Captured()
old_lib=p.lib
p.lib=LibraryBoundary()
try:p.sweep(np.array([1,2],dtype=np.int32))
except Captured:pass
finally:p.lib=old_lib
for name,target in [('village',10),('ruined_portal',8),('trial_chamber',9)]:
    cfg=dynamic_v2_blueprint_config();cfg['structures']['minimum_counts'][name]=target;validate_config(cfg)
    custom=Prototype('/tmp/final-audit-233fad7-build',cfg)
    from seed_search.realm.native_batch import NAMES
    with custom.sweep([456],fixtures=[(0,0,NAMES.index(name))]) as batch:
        result={'configuration_accepted':True,'native_anchors':batch.pointer.results[0].nanchors}
        if batch.pointer.results[0].nanchors:
            a=batch.pointer.results[0].anchors[0]
            result.update(native_score=int(a.score),native_penalty=int(a.deficit_penalty))
        try:
            records=batch.records();result['record_success']=True
        except Exception as e:result['record_error']=repr(e)
        evidence['custom_target_'+name]=result
with p.sweep([456],fixtures=[(0,0,-1)]) as batch:
    record=batch.records()[0]
anchor=record['anchors'][0]
(OUT/'positive-fixture.json').write_text(json.dumps(record,indent=2)+'\n')
evidence['saved_evidence']={'center':anchor['evaluation_center'],
    'bastion_inventory_keys':list(anchor['required_nether_structures']['bastion']),
    'treasure_keys':[k for k in anchor if 'bastion' in k],
    'inspection_keys':[k for k in anchor if 'inspection' in k or 'portal' in k or 'ice' in k],
    'suggested_spawn':anchor.get('suggested_spawn')}
# Fixed-window rescore should derive a pair from retained samples, not trust an old score flag.
changed=copy.deepcopy(anchor);cx,cz=changed['evaluation_center'];sx=64*round(cx/64);sz=64*round(cz/64)
for x,z,name in [(sx,sz,'plains'),(sx+64,sz,'river')]:
    for row in changed['biomes']['sampling']['samples']:
        if row['coordinate']==[x,63,z]:row['biome']=name
changed['scenic_bonus']=0;changed['scenic_witness']=None;changed['river_witness']=None
before=_candidate_rescore(copy.deepcopy(changed),{},'audit-rescore')['ranking']['score']
changed['scenic_bonus']=20
flagged=_candidate_rescore(copy.deepcopy(changed),{},'audit-rescore')['ranking']['score']
evidence['rescore_uses_flag']={'same_retained_surface_pair':[[sx,63,sz],[sx+64,63,sz]],'with_zero_flag':before,'with_twenty_flag':flagged,'difference':flagged-before}
# The backend default factory is resolved before spawning a process; intercept it.
captured={}
class StopProbe(Exception):pass
def capture_config(cfg):
    captured.update(revision=cfg['screening_revision'],budget=cfg['search']['max_misses'],terrain_variants=cfg['terrain']['variants'])
    raise StopProbe()
manager=server.SweepManager.__new__(server.SweepManager)
with patch.object(server,'validate_config',capture_config):
    try:manager.start_sweep(count=1,threads=1)
    except StopProbe:pass
evidence['web_start_default']=captured
# Variant failure is treated as ordinary absence by the current helper.
evidence['variant_error_as_absence']=treasure_bastion_bonus_v2([(0,0)],(0,0),lambda x,z:-1)
# Record score component additivity separately from the correct aggregate arithmetic.
base={'mansion':1,'stronghold':1,'monument':1,'village':9,'trial_chamber':8,'ancient_city':4,'desert_pyramid':3,'jungle_temple':3,'outpost':2,'fortress':2,'bastion':2,'ruined_portal':7,'shipwreck':6,'mineshaft':15}
score,components,_=dynamic_v2_score(base,treasure_bastion=1)
evidence['treasure_component_overlap']={'score':score,'components':components}
(OUT/'probe-results.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({k:v for k,v in evidence.items() if k!='build'},indent=2))
