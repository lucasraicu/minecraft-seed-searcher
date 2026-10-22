"""Current configured v3 automation replay, fresh private output only."""
from pathlib import Path
import json,os,signal,sys,time
ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher');sys.path.insert(0,str(ROOT/'src'))
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
from seed_search.catalog import automation
from seed_search.catalog.harvest import HarvestQueue,make_descriptor
from seed_search.catalog.harvest_native import extract_native
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest
import cProfile,subprocess
from instrument import Probe,stats_json
import seed_search.catalog.biome_extension as extensions
import seed_search.catalog.summaries as summaries
P=Path(__file__).parent

def main():
 signal.alarm(300)
 root=Path(sys.argv[1]);seeds=json.loads(sys.argv[2]);target=Path(sys.argv[3]);assert not root.exists()
 cfg=json.loads((P/'source-config.json').read_text());reg=json.loads((P/'source-registry.json').read_text())
 automation.configure(root,cfg['identity'],cfg['options'],catalog_registry=reg)
 assert automation.configuration(root)['policy_revision']==cfg['policy_revision']
 desc=make_descriptor(dict(sequence='manifest',manifest_seeds=seeds),0,len(seeds),cfg['identity'],digest(['current-framework-replay-benchmark']),root,caps=dict(sample_cap=2,pending_cap=2,world_seconds=120,total_seconds=450,output_bytes=1<<30,max_attempts=1),pipeline_revision=cfg['policy_revision'])
 with HarvestQueue(root) as q:q.register(desc)
 rows=[]
 def extract(job,remaining):
  start=time.monotonic();row=dict(seed=job['seed'],extraction_started=start);rows.append(row)
  if os.environ.get('REPLAY_OBSERVATION'):
   obs=json.loads(Path(os.environ['REPLAY_OBSERVATION']).read_text())['observation'];row['replayed_frozen_observation']=True
  else:
   with HarvestQueue(root) as q:obs=extract_native(job,min(120,remaining),heartbeat=q.heartbeat,protocol=2,options=cfg['options'])
  row.update(extraction_ended=time.monotonic(),extraction_seconds=time.monotonic()-start,biome_points={dim:len(pts) for dim,pts in obs['biomes'].items()},feature_families=len(obs['coverage']),resource_stop=obs['metrics'].get('resource_stop'),native_threads=1,numeric_threads=1)
  return obs
 original_ext=extensions.extract_extension;original_sum=summaries.summarize_v3
 def ext(*args,**kwargs):
  start=time.monotonic();value=original_ext(*args,**kwargs);rows[-1].update(extension_seconds=time.monotonic()-start,extension_points=len(value['biomes']['overworld']) if value else 0);return value
 def summ(*args,**kwargs):
  start=time.monotonic();value=original_sum(*args,**kwargs);rows[-1].update(summary_seconds=time.monotonic()-start,summary_rows=len(value));return value
 extensions.extract_extension=ext;summaries.summarize_v3=summ
 def publish(store,ledger):
  start=time.monotonic();sid=automation.publish(store,ledger,cfg);rows[-1].update(publication_started=start,publication_ended=time.monotonic(),publication_seconds=time.monotonic()-start,snapshot_id=sid,population_worlds=ledger.population(),retained_worlds=len(ledger.retained_worlds()));return sid
 profiling=os.environ.get('PROFILE')=='1';prof=cProfile.Profile();probe=Probe();original_popen=subprocess.Popen
 if profiling:
  def popen(args,*a,**kw):
   if isinstance(args,list) and len(args)>3 and args[1:3]==['-m','seed_search.catalog.harvest_native']:
    args=[args[0],str(P/'profile_child.py'),args[-1],str(root/'child.prof')]
   return original_popen(args,*a,**kw)
  subprocess.Popen=popen;probe.start();prof.enable()
 cpu=time.process_time();start=time.monotonic()
 try:result=automation.run(root,extract=extract,publisher=publish,max_worlds=len(seeds))
 finally:
  wall=time.monotonic()-start;parent_cpu=time.process_time()-cpu
  if profiling:
   prof.disable();subprocess.Popen=original_popen;counters=probe.stop();prof.dump_stats(root/'parent.prof');(root/'parent-profile.json').write_text(json.dumps(dict(wall_seconds=wall,parent_cpu_seconds=parent_cpu,counters=counters,profile=stats_json(root/'parent.prof')),indent=2)+'\n')
 report=dict(parent_cpu_seconds=parent_cpu,profiled=profiling,status='PASS' if result['completed']==len(seeds) and result['failed']==0 else 'FAIL',rows=rows,seconds=wall,seconds_per_world=wall/len(seeds),worlds_per_second=len(seeds)/wall,result=result,policy_revision=cfg['policy_revision'],registry_revision=digest(reg),scope='Current configured v3 native/Realm/spawn/height extraction,summary,products,7543objectives2Kretention,immutablepublication;fresh private catalog,not222world incremental history')
 target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 assert report['status']=='PASS',result
 assert not any(row['resource_stop'] for row in rows),'Partial extraction is not complete-record throughput'
 store=AutomationStore(root);manifest=store.snapshot();assert len(manifest['worlds'])==len(seeds),len(manifest['worlds'])

if __name__=='__main__':main()
