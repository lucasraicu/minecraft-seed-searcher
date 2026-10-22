from pathlib import Path
import json,os,subprocess,sys
B=Path(__file__).parent;seeds=json.loads((B/'catalog-seeds.json').read_text());seed=seeds[0]
for mode in ['baseline','profiled']:
 with (B/(mode+'-world.log')).open('w') as log:
  code=subprocess.call([sys.executable,str(B/'measure_world.py'),str(B/(mode+'-world')),json.dumps([seed]),str(B/(mode+'-world.json'))],env=dict(os.environ,PROFILE='1' if mode=='profiled' else '0'),stdout=log,stderr=subprocess.STDOUT)
 assert code==0,(mode,code)
 print(mode,'complete',flush=True)
