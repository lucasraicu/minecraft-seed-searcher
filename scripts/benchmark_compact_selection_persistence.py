"""Final raw checkpoint performance and exact legacy-rank selection parity."""
import json
from pathlib import Path
import time
from seed_search.realm.raw import run_raw
from seed_search.realm.capabilities import identity

ROOT=Path('runs/compact-implementation-2026-10-10')

def main():
 rows=[];checks=[]
 for trial in range(3):
  for mode in (('presence','capped') if trial%2==0 else ('capped','presence')):
   begin=time.perf_counter();cpu=time.process_time()
   report=run_raw(ROOT/f'raw-selection-final-{mode}-{trial}',0x12340000,262144,threads=36,chunk_size=32768,top=256,exploration=64,mode=mode)
   elapsed=time.perf_counter()-begin
   old=json.loads((ROOT/f'raw-persisted-{mode}'/'raw-selection.json').read_text())
   old_rank={r['low32']:r['raw_counts'] for r in old['selected'] if 'ranked' in r['selection']}
   new_rank={r['low32']:r['raw_counts'] for r in report['selected'] if 'ranked' in r['selection']}
   assert old_rank==new_rank;assert old['necessary_missing']==report['necessary_missing']
   checks.append({'trial':trial,'mode':mode,'ranked_layouts':len(new_rank),'parity':'exact old rank score/selected set; exploration deliberately versioned'})
   row={'trial':trial,'mode':mode,'seconds':elapsed,'cpu_seconds':time.process_time()-cpu,
        'inputs_per_second':262144/elapsed,'full32_end_to_end_minutes':2**32/(262144/elapsed)/60,'report':report}
   rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='report'}),flush=True)
 (ROOT/'raw-selection-final.json').write_text(json.dumps({'backend':identity(),'records':rows,'parity':checks},indent=2)+'\n')

if __name__=='__main__':main()
