"""No behavior pack controls; persisted BDS metadata is read independently."""
import json,time,subprocess
import bds_runner
from bds_runner import BASE,DOCKER,IMAGE,RunningWorld
original=bds_runner.prepare
def prepare(seed,label):
 p=original(seed,label)
 (p/'worlds/spawn_audit/world_behavior_packs.json').write_text('[]\n')
 props=p/'server.properties'
 props.write_text(props.read_text().replace('transport=raknet','transport=nethernet'))
 return p
bds_runner.prepare=prepare
results=[]
for i,seed in enumerate([12345,-9223372036854775808,7958955049054603978]):
 w=RunningWorld(seed,'control-'+str(i))
 row={'seed':str(seed),'label':w.label,'kind':'no_active_behavior_pack'}
 try:
  deadline=time.monotonic()+40
  while not any('Server started.' in line for line in w.lines):
   if w.process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Control failed startup')
   time.sleep(.1)
  time.sleep(2)
  assert not w.rows
  row['status']='started_without_observer'
 finally:row['clean_shutdown']=w.stop()
 results.append(row)
 (BASE/'controls.json').write_text(json.dumps(results,indent=2)+'\n')
 print(row,flush=True)
code='''import json,pathlib,amulet_nbt
rows=[]
for p in sorted(pathlib.Path('/audit/worlds').glob('*/worlds/spawn_audit/level.dat')):
 d=amulet_nbt.load(p.read_bytes()[8:],compressed=False,little_endian=True).compound
 rows.append({'label':p.parents[2].name,'seed':str(d['RandomSeed']),'spawn':{a:int(str(d['Spawn'+a.upper()])) for a in ['x','y','z']}})
print(json.dumps(rows))'''
r=subprocess.run([DOCKER,'run','--rm','--mount',f'type=bind,src={BASE},dst=/audit,readonly','--entrypoint','/opt/reader/bin/python',IMAGE,'-c',code],capture_output=True,text=True,check=True,timeout=30)
rows=json.loads(r.stdout)
(BASE/'persisted-metadata.json').write_text(json.dumps(rows,indent=2)+'\n')
cohort=json.loads((BASE/'bds-cohort.json').read_text());bylabel={r['label']:r for r in rows}
for r in cohort:
 actual=bylabel[r['label']]
 assert actual['seed']==r['seed']
 assert actual['spawn']==r['rows'][-1]['defaultSpawn']
byseed={r['seed']:r for r in cohort}
for r in results:
 assert bylabel[r['label']]['spawn']==byseed[r['seed']]['rows'][-1]['defaultSpawn']
 assert r['clean_shutdown']
print('Persisted metadata agrees with all cohort worlds and all no-pack controls.',flush=True)
