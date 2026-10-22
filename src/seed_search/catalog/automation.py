"""One independently budgeted public worker; never owns a personal search process."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

from .harvest import HarvestQueue, AutomationLedger, DEFAULT_CAPS
from .ingestion import atomic_json, strict_json_loads, verify_no_symlinks
from .models import validate_identity, validate_observation_v2, world_id
from .registry import digest
from .retention import automation_objectives, automation_policy_revision, automation_offers


def derivation_pin():
    """Bind the additive accelerator without changing historical policy sources."""
    import hashlib
    path=Path(__file__).with_name('summaries_fast.py')
    return dict(revision='catalog-derivation-v3-int64-v1',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def _configuration_path(root):
    return verify_no_symlinks(Path(root).absolute()/'automation'/'configuration.json')


def configuration(root):
    path=_configuration_path(root)
    if not path.is_file():return None
    if path.stat().st_size>16384:raise ValueError('Oversized automation configuration')
    value=strict_json_loads(path.read_bytes())
    v3=isinstance(value,dict) and value.get('revision')=='catalog-automation-config-v3'
    fields={'revision','identity','options','policy_revision'}
    if v3:fields|={'registry_artifact','policy_contract'}
    if not isinstance(value,dict) or set(value)!=fields or value['revision'] not in ('catalog-automation-config-v2','catalog-automation-config-v3'):
        raise ValueError('Invalid automation configuration')
    validate_identity(value['identity'])
    if value['identity']['seed']!='0':raise ValueError('Expected seed-independent identity template')
    options=value['options']
    if not isinstance(options,dict) or set(options)-{'spawn','native_build','native_pin','derivation'} or not isinstance(options.get('spawn'),dict):
        raise ValueError('Missing pinned spawn configuration')
    if 'derivation'in options and (not v3 or options['derivation']!=derivation_pin()):
        raise ValueError('Derivation source differs; rebuild in a new policy workspace')
    if set(options['spawn'])!={'executable','binary_sha256','source_sha256'}:raise ValueError('Invalid spawn configuration')
    if not isinstance(options.get('native_pin'),dict):raise ValueError('Missing private Realm runtime pin')
    if v3:
        from .retention import automation_policy_revision_v3
        from .reserve_policy import validate_contract
        validate_contract(value['policy_contract']);reg=policy_registry(root,value)
        expected=digest([automation_policy_revision_v3(registry=reg),value['identity'],options,value['policy_contract'],digest(reg)])
    else:expected=digest([automation_policy_revision(),value['identity'],options])
    if value['policy_revision']!=expected:
        raise ValueError('Automation policy or native identity differs; rebuild in a new policy workspace')
    return value


def configure(root,identity,options,*,catalog_registry=None):
    """Explicit operator setup; changing policy cannot silently reuse old winners."""
    from .spawn_estimator import SpawnEstimator
    from .harvest_native import realm_runtime_pin
    validate_identity(identity)
    if identity['seed']!='0':raise ValueError('Expected template identity')
    SpawnEstimator(**options['spawn'])
    if options['spawn']['source_sha256']!=identity['source_sha256']:raise ValueError('Estimator source differs')
    options=dict(options,native_pin=realm_runtime_pin(options.get('native_build')))
    if catalog_registry is not None and 'derivation'not in options:
        # Existing roots retain their exact declared implementation. New roots
        # explicitly bind the faster numerical-equivalent implementation.
        existing=configuration(root)
        if existing is None:options['derivation']=derivation_pin()
        elif 'derivation'in existing['options']:options['derivation']=existing['options']['derivation']
    value=dict(revision='catalog-automation-config-v2',identity=identity,options=options,
               policy_revision=digest([automation_policy_revision(),identity,options]))
    if catalog_registry is not None:
        from .retention import automation_policy_revision_v3
        from .reserve_policy import contract_id
        from .store import AutomationStore
        value.update(revision='catalog-automation-config-v3',registry_artifact=AutomationStore(root).artifacts.put_json(catalog_registry),policy_contract=contract_id())
        value['policy_revision']=digest([automation_policy_revision_v3(registry=catalog_registry),identity,options,value['policy_contract'],digest(catalog_registry)])
    path=_configuration_path(root)
    if path.exists() and configuration(root)!=value:raise ValueError('Immutable automation configuration differs')
    atomic_json(path,value)
    configuration(root)
    with HarvestQueue(root) as queue:
        ledger=_ledger(queue,value)
        with queue.ownership(),queue.transaction():
            queue.conn.execute('CREATE TABLE IF NOT EXISTS automation_control (id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL, consumed REAL NOT NULL, reason TEXT)')
            queue.conn.execute("INSERT OR IGNORE INTO automation_control VALUES(1,'active',0,NULL)")
    return status(root)


def policy_registry(root,config):
    if config['revision']!='catalog-automation-config-v3':return None
    from .store import AutomationStore
    value=AutomationStore(root).artifacts.get_json(config['registry_artifact'])
    if not isinstance(value,dict) or value.get('revision')!='catalog-features-v3':raise ValueError('Invalid configured registry')
    return value


def _ledger(queue,config):
    if config['revision']=='catalog-automation-config-v3':
        from .retention import automation_objectives_v3
        return AutomationLedger(queue,policy_revision=config['policy_revision'],objectives=automation_objectives_v3(),policy_contract=config['policy_contract'])
    return AutomationLedger(queue,policy_revision=config['policy_revision'],objectives=automation_objectives())


def publish(store,ledger,config):
    if config['revision']=='catalog-automation-config-v3':
        from .registry import SAMPLING_PROFILE_REVISION_V3
        return store.publish(ledger,registry_v3=policy_registry(store.root,config),sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3)
    return store.publish(ledger)


def _control(queue):
    row=queue.conn.execute('SELECT state,consumed,reason FROM automation_control WHERE id=1').fetchone()
    if row is None:raise ValueError('Automation budget is not configured')
    return dict(row)


def status(root):
    config=configuration(root)
    if config is None:return dict(configured=False,state='unconfigured')
    with HarvestQueue(root) as queue:
        control=_control(queue)
        ledger=_ledger(queue,config)
        return dict(configured=True,**control,queue=queue.status(),generation=ledger.generation(),
                    population_worlds=ledger.population(),retained_worlds=len(ledger.retained_worlds()),
                    policy_revision=config['policy_revision'],total_budget_seconds=DEFAULT_CAPS['total_seconds'])


def control(root,action):
    if action not in ('pause','resume','allocate'):raise ValueError('Expected public pause, resume or allocate')
    if configuration(root) is None:raise ValueError('Configure automation first')
    with HarvestQueue(root) as queue,queue.ownership(),queue.transaction():
        # Ordinary resume preserves spend; only explicit allocation grants a fresh budget.
        if action in ('resume','allocate'):
            if _control(queue)['state']!='active':
                with queue.supervisor() as acquired:
                    if not acquired:raise ValueError('Current public world is draining; resume after it stops')
                    queue.conn.execute("UPDATE automation_control SET state='active',reason=NULL WHERE id=1")
                    if action=='allocate':queue.conn.execute('UPDATE automation_control SET consumed=0 WHERE id=1')
        else:queue.conn.execute("UPDATE automation_control SET state='paused',reason='operator pause; current world drains' WHERE id=1")
    if action in ('resume','allocate'):ensure_supervisor(root)
    return status(root)


def ensure_supervisor(root):
    """Nonblocking opt-in launch; supervisor flock elects the sole extractor."""
    config=configuration(root)
    if config is None:return dict(started=False,reason='automation_not_configured')
    if status(root)['state']!='active':return dict(started=False,reason='public_worker_paused')
    destination=_configuration_path(root).parent
    log=verify_no_symlinks(destination/'supervisor.log')
    if log.exists() and log.stat().st_size>1<<20:return dict(started=False,reason='supervisor_log_budget')
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]))
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):env[key]='1'
    with log.open('ab') as output:
        child=subprocess.Popen([sys.executable,'-m','seed_search.catalog.automation','--root',str(Path(root).absolute())],
            stdin=subprocess.DEVNULL,stdout=output,stderr=output,env=env,start_new_session=True,close_fds=True)
    return dict(started=True,pid=child.pid,policy_revision=config['policy_revision'])


def _pause(queue,reason):
    with queue.ownership(),queue.transaction():
        queue.conn.execute("UPDATE automation_control SET state='paused',reason=? WHERE id=1",(str(reason)[:500],))


def _maintenance(queue,ledger,store,clock,*,force=False):
    """Ordinary idle reclamation uses the existing durable allocation, never a reset."""
    path=verify_no_symlinks(queue.root/'automation'/'maintenance.json')
    try:
        if path.exists():
            if path.stat().st_size>16384:raise ValueError('Maintenance metadata cap')
            previous=strict_json_loads(path.read_bytes())
            if (not isinstance(previous,dict) or set(previous)!={'status','policy_revision','generation','staged_jobs','orphan_objects'}
                    or previous['status']!='complete' or type(previous['generation']) is not int or previous['generation']<0):
                raise ValueError('Invalid maintenance receipt')
            if previous['policy_revision']==ledger.policy_revision and previous['generation']==ledger.generation() and not force:
                return dict(status='unchanged')
    except (OSError,ValueError) as error:
        _pause(queue,error);return dict(status='error',reason=str(error)[:300])
    if not queue.conn.execute("SELECT 1 FROM jobs WHERE state='complete' LIMIT 1").fetchone() and not force:
        return dict(status='no_completed_jobs')
    remaining=max(0.,DEFAULT_CAPS['total_seconds']-_control(queue)['consumed'])
    if remaining<=0:
        _pause(queue,'maintenance wall budget');return dict(status='budget')
    with queue.ownership(),queue.transaction():
        queue.conn.execute('UPDATE automation_control SET consumed=consumed+? WHERE id=1',(remaining,))
    started=clock()
    def check():
        if clock()-started>=remaining:raise TimeoutError('maintenance wall budget')
    try:
        with queue.ownership():
            store.cleanup(ledger,check=check)
            store.cleanup_completed_staging(ledger,check=check)
            # Staging is checked/reclaimed while its candidate CAS still exists.
            staged=store.cleanup_completed_staging(ledger,mode='quarantine',check=check)
            deleted=store.cleanup_completed_staging(ledger,mode='delete',check=check)
            orphan=store.cleanup(ledger,mode='reclaim',check=check)
        result=dict(status='complete',policy_revision=ledger.policy_revision,generation=ledger.generation(),
            staged_jobs=len(deleted['candidates']),orphan_objects=len(orphan['candidates']))
        check();atomic_json(path,result)
        return result
    except (OSError,ValueError,MemoryError,TimeoutError) as error:
        _pause(queue,error)
        return dict(status='budget' if isinstance(error,TimeoutError) else 'error',reason=str(error)[:300])
    finally:
        with queue.ownership(),queue.transaction():
            queue.conn.execute('UPDATE automation_control SET consumed=max(0,consumed+?) WHERE id=1',(max(0.,clock()-started)-remaining,))


def _next_retry_after(queue,now=None):
    with queue.ownership():
        rows=queue.conn.execute("""SELECT j.state,j.next_after,j.expires,j.caps,j.attempts FROM jobs j
            WHERE (j.state IN ('pending','partial','deferred','leased'))
            AND EXISTS(SELECT 1 FROM membership m JOIN campaigns c ON c.id=m.campaign_id
                       WHERE m.task_id=j.id AND c.state='active')""").fetchall()
        candidates=[]
        for row in rows:
            caps=json.loads(row['caps'])
            if row['state']!='leased' and row['attempts']>=caps.get('max_attempts',DEFAULT_CAPS['max_attempts']):continue
            ready_at=row['next_after'] if row['state']!='leased' else max(row['next_after'],row['expires'])
            candidates.append(ready_at)
        return min(candidates) if candidates else None


def run(root,*,extract=None,publisher=None,clock=time.monotonic,wallclock=None,sleep=time.sleep,max_worlds=100):
    """Drain one finite budget, retaining its spend across crashes/restarts."""
    if type(max_worlds) is not int or not 1<=max_worlds<=100:raise ValueError('Expected 1..100 worlds')
    config=configuration(root)
    if config is None:raise ValueError('Configure public automation before dispatch')
    from .store import AutomationStore
    from .harvest_native import extract_native,tree_bytes
    from .summaries import summarize_v2
    from .product_evaluation import evaluate_products
    store=AutomationStore(root)
    queue_kwargs=dict(clock=wallclock) if wallclock is not None else {}
    with HarvestQueue(root,**queue_kwargs) as queue,queue.supervisor() as acquired:
        if not acquired:return dict(stop_reason='worker_already_running',completed=0)
        ledger=_ledger(queue,config)
        # A committed membership generation with an old/missing pointer is recoverable.
        if ledger.generation():
            try:current=store.snapshot()
            except FileNotFoundError:current=None
            if current is None or current['generation']!=ledger.generation():
                remaining=max(0.,DEFAULT_CAPS['total_seconds']-_control(queue)['consumed'])
                if remaining<=0:
                    _pause(queue,'publication recovery wall budget')
                    return dict(completed=0,failed=0,stop_reason='wall_budget',control=_control(queue),queue=queue.status())
                with queue.ownership(),queue.transaction():
                    queue.conn.execute('UPDATE automation_control SET consumed=consumed+? WHERE id=1',(remaining,))
                recovery_started=clock()
                try:
                    with queue.ownership():publish(store,ledger,config)
                finally:
                    with queue.ownership(),queue.transaction():
                        queue.conn.execute('UPDATE automation_control SET consumed=max(0,consumed+?) WHERE id=1',
                            (max(0.,clock()-recovery_started)-remaining,))
            elif current['policy_revision']!=ledger.policy_revision:
                raise ValueError('Published policy differs from membership ledger')
        completed=failed=0;reason='max_worlds';worker=f'public-v2-{os.getpid()}'
        for _ in range(max_worlds):
            job=None
            while True:
                state=_control(queue)
                if state['state']!='active':reason=state['reason'] or 'paused';break
                if tree_bytes(Path(root))>=DEFAULT_CAPS['output_bytes']:
                    _pause(queue,'output_bytes budget');reason='output_bytes';break
                if state['consumed']>=DEFAULT_CAPS['total_seconds']:
                    _pause(queue,'total wall budget');reason='wall_budget';break
                job=queue.claim(worker)
                if job is not None:break
                q_now=queue._time()
                next_ready=_next_retry_after(queue,q_now)
                if next_ready is None:reason='no_ready_work';break
                wait_seconds=max(0.0,next_ready-q_now)
                if wait_seconds>0:
                    remaining_budget=max(0.0,DEFAULT_CAPS['total_seconds']-state['consumed'])
                    if remaining_budget<=0:
                        _pause(queue,'total wall budget');reason='wall_budget';break
                    slice_seconds=min(1.0,wait_seconds,remaining_budget)
                    # Reserve even short waits before sleeping, so a crash cannot
                    # repeatedly reclaim its previous wait allocation.
                    with queue.ownership(),queue.transaction():
                        queue.conn.execute('UPDATE automation_control SET consumed=consumed+? WHERE id=1',(slice_seconds,))
                    sleep_start=clock()
                    sleep(slice_seconds)
                    sleep_elapsed=max(0.,clock()-sleep_start)
                    with queue.ownership(),queue.transaction():
                        queue.conn.execute('UPDATE automation_control SET consumed=max(0,consumed+?) WHERE id=1',(sleep_elapsed-slice_seconds,))
            if job is None:break
            for key,value in config['identity'].items():
                if key!='seed' and job['identity'].get(key)!=value:
                    queue.fail(job,'configured native/source identity differs');failed+=1;break
            else:
                remaining=min(DEFAULT_CAPS['total_seconds'],job['caps']['total_seconds'])-state['consumed']
                reserved=min(job['caps']['world_seconds'],remaining)
                if reserved<=0:
                    queue.defer(job,'persistent total wall budget');_pause(queue,'total wall budget');reason='wall_budget';break
                # Reserve before launching. A crash conservatively charges the reservation.
                with queue.ownership(),queue.transaction():
                    queue.conn.execute('UPDATE automation_control SET consumed=consumed+? WHERE id=1',(reserved,))
                begin=clock();membership_committed=False
                try:
                    observation=(extract(job,reserved) if extract else extract_native(job,reserved,
                        heartbeat=queue.heartbeat,protocol=2,options=config['options']))
                    validate_observation_v2(observation)
                    if observation['identity']!=job['identity']:raise ValueError('Extracted identity differs')
                    v3=config['revision']=='catalog-automation-config-v3';reg=policy_registry(root,config);extension=None
                    if v3:
                        from .summaries import summarize_v3
                        if 'derivation'in config['options']:
                            from .summaries_fast import summarize_v3
                        from .biome_extension import extract_extension
                        from ..backend import Backend,biome_name,configure_native_threads
                        from ..realm.biomes import canonical
                        configure_native_threads(1)
                        if any(f.get('available') and f['id'].startswith('biome.exact.') and f.get('eligible_y')!=[63] for f in reg['features']):
                            with Backend(observation['identity']['seed']) as backend:
                                extension=extract_extension(observation,backend,name_for_id=lambda n:canonical(biome_name(n)),deadline=begin+reserved)
                        summaries=summarize_v3(observation,extension=extension,registry=reg)
                    else:summaries=summarize_v2(observation)
                    evaluations=evaluate_products(observation)
                    artifact=store.stage(observation,summaries,extension=extension,registry_v3=reg) if v3 else store.stage(observation,summaries)
                    partial=bool(observation['metrics'].get('resource_stop')) or any(
                        cov['status']=='failed' for cov in observation['coverage'].values())
                    receipt=dict(world_id=world_id(observation['identity']),identity=observation['identity'],
                        observation_id=digest(observation),artifact=artifact,evaluations=evaluations,
                        replay=dict(resumable=partial,task_id=job['task_id']))
                    if clock()-begin>=remaining:raise TimeoutError('Total public budget exhausted before publication')
                    with queue.publication(job):
                        if v3:
                            from .retention import automation_offers_v3
                            offers=automation_offers_v3(observation,summaries,evaluations,registry=reg)
                        else:offers=automation_offers(observation,summaries,evaluations)
                        ledger.offer(receipt,offers)
                        membership_committed=True
                        snapshot=publish(store,ledger,config) if publisher is None else publisher(store,ledger)
                        if partial:queue.fail(job,'partial observations published; bounded retry',partial=True)
                        else:queue.acknowledge(job,snapshot)
                    completed+=1
                    if observation['metrics'].get('resource_stop'):
                        _pause(queue,'world time budget; explicit resume required');reason='world_budget';break
                except (KeyboardInterrupt,SystemExit):
                    try:queue.defer(job,'operator interruption')
                    except ValueError:pass
                    _pause(queue,'operator interruption');reason='interrupted';break
                except (OSError,MemoryError,TimeoutError) as error:
                    try:queue.defer(job,f'{type(error).__name__}: {error}')
                    except ValueError:pass
                    _pause(queue,error);reason='resource_or_storage_limit';break
                except Exception as error:
                    try:queue.fail(job,f'{type(error).__name__}: {error}',partial=bool(job.get('checkpoint') and Path(job['checkpoint']).is_file()))
                    except ValueError:pass
                    failed+=1
                    if membership_committed:
                        _pause(queue,'membership committed; publication recovery required')
                        reason='publication_recovery_needed';break
                finally:
                    elapsed=max(0.,clock()-begin)
                    with queue.ownership(),queue.transaction():
                        queue.conn.execute('UPDATE automation_control SET consumed=max(0,consumed+?) WHERE id=1',(elapsed-reserved,))
        maintenance=None
        if reason in ('no_ready_work','output_bytes'):
            maintenance=_maintenance(queue,ledger,store,clock,force=reason=='output_bytes')
            if maintenance['status'] in ('budget','error'):reason='maintenance_'+maintenance['status']
            elif reason=='output_bytes' and tree_bytes(Path(root))<DEFAULT_CAPS['output_bytes']:
                with queue.ownership(),queue.transaction():
                    queue.conn.execute("UPDATE automation_control SET state='active',reason=NULL WHERE id=1")
                reason='max_worlds'  # Supervisor resumes dispatch after reclaiming space.
        return dict(completed=completed,failed=failed,stop_reason=reason,maintenance=maintenance,control=_control(queue),queue=queue.status())


def supervise(root):
    """Continue finite chunks after retries; never reset the durable budget."""
    completed=failed=0
    while True:
        result=run(root)
        completed+=result.get('completed',0);failed+=result.get('failed',0)
        if result['stop_reason']!='max_worlds':
            return dict(result,completed=completed,failed=failed)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(supervise(args.root)),flush=True)


if __name__=='__main__':main()
