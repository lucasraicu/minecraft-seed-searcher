"""Same frozen observation paired replay avoids profiler's time-budget perturbation."""
from pathlib import Path
import json,os,subprocess,sys
B=Path(__file__).parent;checkpoint=next((B/'baseline-world/staging').glob('*/*/observation.json'));obs=json.loads(checkpoint.read_text())['observation'];seed=obs['identity']['seed']
for mode in ['fixed-baseline','fixed-profiled']:
 with (B/(mode+'.log')).open('w') as log:
  code=subprocess.call([sys.executable,str(B/'measure_world.py'),str(B/mode),json.dumps([seed]),str(B/(mode+'.json'))],env=dict(os.environ,PROFILE='1' if mode=='fixed-profiled' else '0',REPLAY_OBSERVATION=str(checkpoint)),stdout=log,stderr=subprocess.STDOUT)
 assert code==0,(mode,code)
a=json.loads((B/'fixed-baseline.json').read_text());b=json.loads((B/'fixed-profiled.json').read_text());assert a['rows'][0]['snapshot_id']==b['rows'][0]['snapshot_id'],'Frozen-observation outputs differ'
(B/'FIXED_REPLAY_PARITY.json').write_text(json.dumps(dict(status='PASS',same_frozen_observation=True,snapshot_id=a['rows'][0]['snapshot_id'],baseline_seconds=a['seconds'],profiled_seconds=b['seconds'],runtime_ratio=b['seconds']/a['seconds'],scope='Identical frozen base observation;current height extension,summaries,products,retention,publish;no base re-extraction'),indent=2)+'\n');print('fixed replay exact snapshot parity pass',flush=True)
