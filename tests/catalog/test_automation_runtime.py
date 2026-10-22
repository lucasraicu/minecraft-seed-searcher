"""Controller tests use a fake extractor/publisher and real persistent queue/ledger."""
import pytest
from seed_search.catalog import automation,store,spawn_estimator,harvest_native
from seed_search.catalog.harvest import HarvestQueue,make_descriptor
from seed_search.catalog.models import identity,empty_observation_v2
from seed_search.catalog.registry import digest


class FakeStore:
    published=[]
    def __init__(self,root):pass
    def stage(self,obs,summaries):return {'sha256':digest(obs),'relative_key':'mock'}
    def publish(self,ledger):
        self.published.append(ledger.generation());return digest(['snapshot',ledger.generation()])
    def cleanup(self,ledger,**kwargs):return dict(candidates=[])
    def cleanup_completed_staging(self,ledger,**kwargs):return dict(candidates=[])
    def snapshot(self):raise FileNotFoundError('test store has no durable pointer')


@pytest.fixture
def root(tmp_path,monkeypatch):
    monkeypatch.setattr(spawn_estimator,'SpawnEstimator',lambda **kw:None)
    monkeypatch.setattr(harvest_native,'realm_runtime_pin',lambda *args,**kw:{'test_sha256':'f'*64})
    monkeypatch.setattr(store,'AutomationStore',FakeStore,raising=False)
    monkeypatch.setattr(automation,'ensure_supervisor',lambda root:{'started':False,'test':True})
    ident=identity('0',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64)
    automation.configure(tmp_path,ident,{'spawn':{'executable':'/mock','binary_sha256':'c'*64,'source_sha256':'b'*64}})
    descriptor=make_descriptor({'sequence':'manifest','manifest_seeds':['1','2','3','4','5','6','7']},0,7,ident,'d'*64,tmp_path)
    with HarvestQueue(tmp_path) as queue:queue.register(descriptor)
    return tmp_path


class Clock:
    def __init__(self):self.value=0
    def __call__(self):return self.value


def test_idle_reclamation_receipt_prevents_repeated_work(root,monkeypatch):
    clock=Clock()
    result=automation.run(root,extract=lambda job,seconds:empty_observation_v2(job['identity']),clock=clock)
    assert result['maintenance']['status']=='complete'
    monkeypatch.setattr(FakeStore,'cleanup',lambda *a,**k:pytest.fail('unchanged generation collected twice'))
    again=automation.run(root,clock=clock)
    assert again['maintenance']['status']=='unchanged'


def test_reclamation_reserves_persistent_budget_and_pauses_on_deadline(root,monkeypatch):
    clock=Clock()
    def cleanup(self,ledger,**kw):
        clock.value+=600
        kw['check']()
    monkeypatch.setattr(FakeStore,'cleanup',cleanup)
    result=automation.run(root,extract=lambda job,seconds:empty_observation_v2(job['identity']),clock=clock)
    assert result['stop_reason']=='maintenance_budget'
    assert automation.status(root)['consumed']==600
    assert automation.status(root)['state']=='paused'


def test_persistent_wall_budget_is_not_reset_by_new_drain(root):
    clock=Clock()
    def extract(job,seconds):
        clock.value+=100
        return empty_observation_v2(job['identity'])
    result=automation.run(root,extract=extract,clock=clock)
    assert result['completed']==5
    assert result['stop_reason']=='resource_or_storage_limit'
    saved=automation.status(root)
    assert saved['state']=='paused' and saved['consumed']==600
    again=automation.run(root,extract=lambda *a:pytest.fail('paused worker extracted'),clock=clock)
    assert again['completed']==0
    assert automation.status(root)['consumed']==600


def test_world_limit_publishes_partial_then_requires_explicit_resume(root):
    def extract(job,seconds):
        obs=empty_observation_v2(job['identity']);obs['metrics']['resource_stop']='world_time_budget_exhausted';return obs
    result=automation.run(root,extract=extract)
    assert result['completed']==1 and result['stop_reason']=='world_budget'
    assert automation.status(root)['state']=='paused'
    assert automation.control(root,'resume')['state']=='active'
    spent=automation.status(root)['consumed'];assert spent>0
    automation.control(root,'pause')
    assert automation.control(root,'allocate')['consumed']==0


def test_pause_does_not_cancel_personal_or_public_campaigns(root):
    paused=automation.control(root,'pause')
    assert paused['state']=='paused'
    assert all(c['state']=='active' for c in paused['queue']['campaigns'])
    result=automation.run(root,extract=lambda *a:pytest.fail('paused worker extracted'))
    assert result['completed']==0


def test_membership_commit_pointer_failure_recovers_on_next_run(root):
    def broken(store,ledger):raise OSError('fault after membership commit')
    result=automation.run(root,extract=lambda job,seconds:empty_observation_v2(job['identity']),publisher=broken,max_worlds=1)
    assert result['stop_reason']=='resource_or_storage_limit'
    generation=automation.status(root)['generation'];assert generation>0
    FakeStore.published=[]
    automation.run(root,extract=lambda *a:pytest.fail('paused worker extracted'))
    assert FakeStore.published==[generation]


class FakeClock:
    def __init__(self, start=1000.0):
        self.value = float(start)
        self.sleeps = []

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


@pytest.fixture
def single_root(tmp_path, monkeypatch):
    monkeypatch.setattr(spawn_estimator, 'SpawnEstimator', lambda **kw: None)
    monkeypatch.setattr(harvest_native,'realm_runtime_pin',lambda *args,**kw:{'test_sha256':'f'*64})
    monkeypatch.setattr(store, 'AutomationStore', FakeStore, raising=False)
    monkeypatch.setattr(automation, 'ensure_supervisor', lambda root: {'started': False, 'test': True})
    ident = identity('0', model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64)
    automation.configure(tmp_path, ident, {'spawn': {'executable': '/mock', 'binary_sha256': 'c'*64, 'source_sha256': 'b'*64}})
    descriptor = make_descriptor({'sequence': 'manifest', 'manifest_seeds': ['1']}, 0, 1, ident, 'd'*64, tmp_path)
    with HarvestQueue(tmp_path) as queue:
        queue.register(descriptor)
    return tmp_path


def test_retry_eventual_success_under_single_supervisor(single_root):
    clock = FakeClock(1000.0)
    attempts = 0

    def extract(job, seconds):
        nonlocal attempts
        attempts += 1
        obs = empty_observation_v2(job['identity'])
        if attempts == 1:
            obs['coverage']['structure.village'] = {
                'status': 'failed',
                'bounds': list(obs['bounds']['overworld']),
                'method_id': 'mock'
            }
        return obs

    result = automation.run(
        single_root,
        extract=extract,
        clock=clock,
        wallclock=clock,
        sleep=clock.sleep,
        max_worlds=10
    )
    assert attempts == 2
    assert result['completed'] == 2
    assert result['stop_reason'] == 'no_ready_work'
    assert result['queue']['jobs'].get('complete') == 1
    assert result['control']['state'] == 'active'
    assert result['control']['consumed'] > 0
    assert clock.sleeps
    assert all(0 < s <= 1.0 for s in clock.sleeps)
    assert sum(clock.sleeps) == pytest.approx(2.0)


def test_wait_budget_exhaustion_pauses_automation(single_root):
    clock = FakeClock(1000.0)

    # Pre-populate consumed to 597.5 so 2.5s of total budget remains.
    with HarvestQueue(single_root) as q, q.ownership(), q.transaction():
        q.conn.execute('UPDATE automation_control SET consumed=597.5 WHERE id=1')

    def extract(job, seconds):
        # Extract takes 1.0s (less than the 2.5s remaining), leaving 1.5s
        clock.value += 1.0
        obs = empty_observation_v2(job['identity'])
        obs['coverage']['structure.village'] = {
            'status': 'failed',
            'bounds': list(obs['bounds']['overworld']),
            'method_id': 'mock'
        }
        return obs

    result = automation.run(
        single_root,
        extract=extract,
        clock=clock,
        wallclock=clock,
        sleep=clock.sleep,
        max_worlds=10
    )
    saved = automation.status(single_root)
    assert result['stop_reason'] == 'wall_budget'
    assert saved['state'] == 'paused'
    assert saved['consumed'] == pytest.approx(600.0)
    assert saved['reason'] == 'total wall budget'
    assert all(0 < s <= 1.0 for s in clock.sleeps)
    assert sum(clock.sleeps) == pytest.approx(1.5)


def test_true_empty_queue_exits_without_waiting(root):
    clock = FakeClock(1000.0)
    result1 = automation.run(
        root,
        extract=lambda job, sec: empty_observation_v2(job['identity']),
        clock=clock,
        wallclock=clock,
        sleep=clock.sleep,
        max_worlds=100
    )
    assert result1['completed'] == 7
    assert result1['stop_reason'] == 'no_ready_work'
    assert len(clock.sleeps) == 0

    clock.sleeps.clear()
    result2 = automation.run(
        root,
        extract=lambda job, sec: pytest.fail('unexpected extraction on empty queue'),
        clock=clock,
        wallclock=clock,
        sleep=clock.sleep,
        max_worlds=10
    )
    assert result2['completed'] == 0
    assert result2['stop_reason'] == 'no_ready_work'
    assert len(clock.sleeps) == 0


def test_operator_pause_noticed_during_retry_wait(single_root):
    clock = FakeClock(1000.0)

    def fake_sleep_with_pause(seconds):
        clock.sleep(seconds)
        automation.control(single_root, 'pause')

    def extract(job, seconds):
        obs = empty_observation_v2(job['identity'])
        obs['coverage']['structure.village'] = {
            'status': 'failed',
            'bounds': list(obs['bounds']['overworld']),
            'method_id': 'mock'
        }
        return obs

    result = automation.run(
        single_root,
        extract=extract,
        clock=clock,
        wallclock=clock,
        sleep=fake_sleep_with_pause,
        max_worlds=10
    )
    assert result['stop_reason'] == 'operator pause; current world drains'
    assert result['control']['state'] == 'paused'
    assert result['control']['consumed'] == pytest.approx(1.0)
    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(1.0)


def test_transient_exception_retry_eventual_success(single_root):
    clock = FakeClock(1000.0)
    attempts = 0

    def extract(job, seconds):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError('transient glitch')
        return empty_observation_v2(job['identity'])

    result = automation.run(
        single_root,
        extract=extract,
        clock=clock,
        wallclock=clock,
        sleep=clock.sleep,
        max_worlds=10
    )
    assert attempts == 2
    assert result['completed'] == 1
    assert result['failed'] == 1
    assert result['stop_reason'] == 'no_ready_work'
    assert result['queue']['jobs'].get('complete') == 1
    assert all(0 < s <= 1.0 for s in clock.sleeps)
    assert sum(clock.sleeps) == pytest.approx(2.0)




def test_supervisor_continues_attempt_chunks_without_new_allocation(monkeypatch):
    calls=[]
    def run(root):
        calls.append(root)
        return dict(stop_reason='max_worlds' if len(calls)==1 else 'no_ready_work',completed=100 if len(calls)==1 else 1,failed=0)
    monkeypatch.setattr(automation,'run',run)
    result=automation.supervise('/mock')
    assert result['completed']==101 and calls==['/mock','/mock']


def test_last_attempt_orphan_lease_waits_then_terminalizes(single_root):
    clock=FakeClock(1000)
    with HarvestQueue(single_root,clock=clock) as queue:
        job=queue.claim('stale-worker',lease_seconds=2)
        with queue.ownership(),queue.transaction():
            queue.conn.execute('UPDATE jobs SET attempts=3 WHERE id=?',(job['task_id'],))
    result=automation.run(single_root,extract=lambda *a:pytest.fail('attempt cap bypassed'),clock=clock,wallclock=clock,sleep=clock.sleep)
    assert result['queue']['jobs']['failed']==1
    assert sum(clock.sleeps)==2


def test_configuration_binds_spawn_and_private_native_options(root):
    import json
    path=root/'automation/configuration.json'
    config=json.loads(path.read_text())
    config['options']['spawn']['binary_sha256']='e'*64
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError,match='policy or native identity differs'):
        automation.configuration(root)
