"""Fixed observation checkpoint+summary comparison, no native search/extraction."""
from pathlib import Path
import sys,os,json,time,statistics
R=Path(__file__).resolve().parents[2];B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';P=B.parent/'storage-query-profile-20261022'
mode=sys.argv[1];sys.path.insert(0,str((B/'reference' if mode=='before' else R)/'src'))
from seed_search.catalog.harvest_native import save_checkpoint,checkpoint_observation
if mode=='before':
 from seed_search.catalog.summaries import summarize_v3
else:
 from seed_search.catalog.summaries_fast import summarize_v3
from seed_search.catalog.registry import digest
obs=json.loads(next((P/'baseline-world/staging').glob('*/*/observation.json')).read_text())['observation'];reg=json.loads((B/'source-registry.json').read_text())
rows=[];times=[]
for i in range(3):
 start=time.perf_counter();summaries=summarize_v3(obs,registry=reg);times.append(time.perf_counter()-start)
 sid=digest(summaries)
 if rows:assert rows[-1]['digest']==sid
 rows.append(dict(seconds=times[-1],digest=sid,rows=len(summaries)))
times=[];size=[]
for i in range(3):
 start=time.perf_counter();path=B/f'checkpoint-{mode}-{i}.json';save_checkpoint(path,obs);times.append(time.perf_counter()-start);assert checkpoint_observation(path,protocol=2)==obs;size.append(path.stat().st_size)
out=dict(mode=mode,summary=rows,checkpoint_seconds=times,checkpoint_bytes=size,median_summary=statistics.median(x['seconds']for x in rows),median_checkpoint=statistics.median(times),observation_id=digest(obs))
(Path(__file__).parent/f'DERIVATION_{mode.upper()}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
