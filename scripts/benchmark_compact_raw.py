"""Dispersed lower32 exact-mode parity and compute/checkpoint measurements."""
import json
from pathlib import Path
import statistics
import time
import numpy as np
from seed_search.backend import sweep_raw
from seed_search.realm.raw import FAMILIES,run_raw
from seed_search.realm.capabilities import identity

OUT=Path('runs/compact-implementation-2026-10-10')
STARTS=[0,0x12340000,0x34560000,0x56780000,0x789A0000,0x9ABC0000,0xBCDE0000,0xEFFE0000]


def main():
 records=[];checks=0;first_reference=None
 for threads in (18,36):
  for trial in range(3):
   modes=['reference','complete','capped','presence']
   modes=modes[trial:]+modes[:trial]
   values={}
   for mode in modes:
    wall=time.perf_counter();cpu=time.process_time()
    result=np.concatenate([sweep_raw(start,32768,FAMILIES,threads,mode=mode) for start in STARTS])
    elapsed=time.perf_counter()-wall;cost=time.process_time()-cpu
    values[mode]=result
    r={'threads':threads,'trial':trial,'mode':mode,'inputs':len(result),'seconds':elapsed,'cpu_seconds':cost,
       'layouts_per_second':len(result)/elapsed,'necessary_missing':int((result==0).any(axis=1).sum()),
       'full32_compute_minutes':2**32/(len(result)/elapsed)/60}
    records.append(r);print(json.dumps(r),flush=True)
   assert np.array_equal(values['reference'],values['complete'])
   assert np.array_equal(np.minimum(values['reference'],32),values['capped'])
   assert np.array_equal(values['reference']>0,values['presence']>0)
   checks+=len(values['reference'])*3
   if first_reference is None:
    first_reference=values['reference'];np.save(OUT/'raw-reference-counts.npy',first_reference)
 persisted=[]
 for mode in ('presence','capped'):
  begin=time.perf_counter();cpu=time.process_time()
  report=run_raw(OUT/f'raw-persisted-{mode}',0x12340000,262144,threads=36,chunk_size=32768,top=256,exploration=64,mode=mode)
  seconds=time.perf_counter()-begin
  persisted.append({'mode':mode,'seconds':seconds,'cpu_seconds':time.process_time()-cpu,
                    'inputs_per_second':262144/seconds,'full32_end_to_end_minutes':2**32/(262144/seconds)/60,
                    'report':report})
 data={'backend':identity(),'starts':STARTS,'block_count':32768,'records':records,'parity_checks':checks,'persisted':persisted,
       'scope':'Native exact count/presence contracts; checkpoint forecasts include selection/IO. Neither includes full64, terrain or BDS.'}
 (OUT/'raw-benchmark.json').write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':main()
