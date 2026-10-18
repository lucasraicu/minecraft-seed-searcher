import sys,json,subprocess,shutil,time,hashlib
import bds_runner
from bds_runner import RunningWorld,BASE,DOCKER
original_prepare=bds_runner.prepare
def prepare_net(seed,label):
 w=original_prepare(seed,label)
 p=w/"server.properties"
 p.write_text(p.read_text().replace("transport=raknet","transport=nethernet"))
 return w
bds_runner.prepare=prepare_net
seed=int(sys.argv[1]);label=sys.argv[2]
w=RunningWorld(seed,label)
r={'seed':str(seed),'kind':'real_initial_player_join','label':label}
c=None
try:
 r['before']=w.wait('world_tick40')
 c=subprocess.Popen([DOCKER,'run','--rm','--name','codex-spawn-client-'+label,'--network','container:'+w.name,'--mount',f'type=bind,src={BASE}/client,dst=/client','--workdir','/client','node:24-bookworm-slim','node','join.js','19132'],stdout=(w.work/'client.log').open('w'),stderr=subprocess.STDOUT)
 r['player_spawn']=w.wait('player_spawn',timeout=55)
 r['player_tick20']=w.wait('player_tick20',timeout=10)
 c.wait(timeout=15)
 r['status']='observed';r['client_exit']=c.returncode
except Exception as e:
 r['status']='failed';r['error']=str(e)
finally:
 if c and c.poll() is None:c.terminate();c.wait(timeout=5)
 r['clean_shutdown']=w.stop();r['rows']=w.rows
 for name in ['console.log','client.log']:
  if (w.work/name).exists():r[name+'_sha256']=hashlib.sha256((w.work/name).read_bytes()).hexdigest()
 (w.work/'join_result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
