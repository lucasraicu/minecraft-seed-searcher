"""Independent bounded campaign queue. Personal admission is never consulted."""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fcntl
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import time

from .ingestion import verify_no_symlinks, strict_json_loads
from .models import validate_identity, world_id
from .registry import canonical_json, digest
from ..seeds import parse_seed, validate_sequence_range

DEFAULT_CAPS = dict(sample_cap=100, pending_cap=100, world_seconds=120,
                    total_seconds=600, rss_bytes=4<<30, output_bytes=2<<30, max_attempts=3)


def _hex(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def make_descriptor(search, start, count, observation_identity, personal_identity_sha256, root, *, caps=None, pipeline_revision=None):
    validate_identity(observation_identity)
    if observation_identity['seed'] != '0' or not _hex(personal_identity_sha256):
        raise ValueError('Invalid campaign identity template')
    if not isinstance(search, dict):raise ValueError('Invalid seed sequence')
    sequence = search.get('sequence', 'permutation')
    if sequence not in ('permutation','sequential','strided','manifest'):raise ValueError('Unsupported seed sequence')
    validate_sequence_range(start, count, sequence)
    clean = {'sequence':sequence}
    if sequence == 'permutation':
        key = search.get('run_key', '0')
        if isinstance(key, bool) or not isinstance(key, (str,int)) or len(str(key)) > 256:raise ValueError('Invalid run key')
        clean['run_key'] = str(key)
    if sequence == 'strided':clean['low32'] = str(parse_seed(search.get('low32', 0)))
    if sequence == 'manifest':
        seeds = search.get('manifest_seeds')
        if not isinstance(seeds,list) or not 1 <= len(seeds) <= 10000 or start+count > len(seeds):raise ValueError('Invalid manifest range')
        if any(not isinstance(s,str) or str(parse_seed(s)) != s for s in seeds) or len(set(seeds)) != len(seeds):raise ValueError('Manifest requires unique canonical seeds')
        clean['manifest_seeds'] = list(seeds)
    limits = dict(DEFAULT_CAPS)
    if caps is not None:
        if not isinstance(caps, dict) or set(caps)-set(limits):raise ValueError('Unknown harvest cap')
        limits.update(caps)
    if any(type(v) is not int or not 1 <= v <= DEFAULT_CAPS[k] for k,v in limits.items()):raise ValueError('Caps may only be lowered')
    destination = verify_no_symlinks(Path(root).absolute())
    value = dict(revision='catalog-harvest-v1', search=clean, start=str(start), count=str(count),
        observation_identity=dict(observation_identity), personal_identity_sha256=personal_identity_sha256,
        root=str(destination), caps=limits, sampling=dict(offset=0,stride=max(1,(count+limits['sample_cap']-1)//limits['sample_cap'])))
    if pipeline_revision is not None:
        if not _hex(pipeline_revision):raise ValueError('Invalid pipeline revision')
        value['pipeline_revision']=pipeline_revision
    value['campaign_id'] = digest(value)
    if len(canonical_json(value)) > 1<<20:raise ValueError('Campaign descriptor exceeds 1MiB')
    return value


def validate_descriptor(value):
    if not isinstance(value,dict):raise ValueError('Invalid descriptor')
    try:
        result = make_descriptor(value['search'], int(value['start']), int(value['count']),
            value['observation_identity'], value['personal_identity_sha256'], value['root'], caps=value['caps'],pipeline_revision=value.get('pipeline_revision'))
    except (KeyError, TypeError, OverflowError) as exc:raise ValueError('Invalid descriptor') from exc
    if result != value:raise ValueError('Descriptor is not canonical or checksum changed')
    return result


def write_descriptor(spool_dir, descriptor):
    validate_descriptor(descriptor)
    directory = verify_no_symlinks(spool_dir);directory.mkdir(parents=True,exist_ok=True)
    target = verify_no_symlinks(directory/(descriptor['campaign_id']+'.json'))
    blob = canonical_json(descriptor)
    if target.exists():
        if target.stat().st_size > 1<<20 or target.read_bytes() != blob:raise ValueError('Immutable descriptor differs')
        return target
    fd, name = tempfile.mkstemp(prefix='.handoff-',dir=directory)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(blob);stream.flush();os.fsync(stream.fileno())
        try:os.link(name,target)
        except FileExistsError:
            if target.read_bytes() != blob:raise ValueError('Concurrent descriptor differs')
        parent = os.open(directory,os.O_RDONLY)
        try:os.fsync(parent)
        finally:os.close(parent)
    finally:Path(name).unlink(missing_ok=True)
    return target


class HarvestQueue:
    def __init__(self, root, *, busy_ms=5000, clock=time.time):
        self.root = verify_no_symlinks(root);self.root.mkdir(parents=True,exist_ok=True)
        if type(busy_ms) is not int or not 0 <= busy_ms <= 5000:raise ValueError('Invalid busy timeout')
        for name in ('realm.sqlite','seeds.db','personal.db','runs.db'):
            if (self.root/name).exists():raise ValueError('Personal database root prohibited')
        for name in ('harvest.sqlite','harvest.sqlite-wal','harvest.sqlite-shm','harvest.lock','harvest-drain.lock'):
            verify_no_symlinks(self.root/name)
        self.clock=clock;self._mutex=threading.RLock();self._depth=0
        self.lockfile=(self.root/'harvest.lock').open('a+b')
        self.conn=sqlite3.connect(self.root/'harvest.sqlite',timeout=busy_ms/1000,isolation_level=None)
        self.conn.row_factory=sqlite3.Row
        try:
            self.conn.execute(f'PRAGMA busy_timeout={busy_ms}')
            schema='''
              CREATE TABLE IF NOT EXISTS harvest_meta(revision TEXT PRIMARY KEY);
              INSERT OR IGNORE INTO harvest_meta VALUES('harvest-v1');
              CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,descriptor TEXT NOT NULL,state TEXT NOT NULL,cursor INTEGER NOT NULL DEFAULT 0);
              CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,identity TEXT NOT NULL,seed TEXT NOT NULL,state TEXT NOT NULL,
                worker TEXT,generation INTEGER NOT NULL DEFAULT 0,expires REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,next_after REAL NOT NULL DEFAULT 0,reason TEXT,
                checkpoint TEXT NOT NULL,snapshot_id TEXT,caps TEXT NOT NULL,process_start TEXT);
              CREATE TABLE IF NOT EXISTS membership(task_id TEXT NOT NULL,campaign_id TEXT NOT NULL,PRIMARY KEY(task_id,campaign_id));
            '''
            # DDL + marker are one atomic bootstrap; SQLite wait stays bounded,
            # unlike taking the publication flock during personal registration.
            with self.transaction():
                tables={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tables and 'harvest_meta' not in tables:raise ValueError('Incompatible queue database')
                if tables:
                    revisions=self.conn.execute('SELECT revision FROM harvest_meta').fetchall()
                    if [tuple(r) for r in revisions]!=[('harvest-v1',)]:raise ValueError('Queue revision mismatch')
                for statement in schema.split(';'):
                    if statement.strip():self.conn.execute(statement)
            self.conn.execute('PRAGMA journal_mode=WAL');self.conn.execute('PRAGMA synchronous=FULL')
        except BaseException:self.close();raise

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        if getattr(self,'conn',None) is not None:self.conn.close();self.conn=None
        if getattr(self,'lockfile',None) is not None:self.lockfile.close();self.lockfile=None

    @contextmanager
    def ownership(self):
        with self._mutex:
            if not self._depth:fcntl.flock(self.lockfile,fcntl.LOCK_EX)
            self._depth+=1
            try:yield
            finally:
                self._depth-=1
                if not self._depth:fcntl.flock(self.lockfile,fcntl.LOCK_UN)

    @contextmanager
    def supervisor(self):
        """One explicit drain/native child globally; registration stays independent."""
        path=verify_no_symlinks(self.root/'harvest-drain.lock')
        with path.open('a+b') as stream:
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:yield True
            finally:fcntl.flock(stream,fcntl.LOCK_UN)

    @contextmanager
    def transaction(self):
        self.conn.execute('BEGIN IMMEDIATE')
        try:yield;self.conn.commit()
        except BaseException:self.conn.rollback();raise

    def register(self, descriptor):
        validate_descriptor(descriptor)
        if Path(descriptor['root']) != self.root:raise ValueError('Campaign queue root mismatch')
        # No publisher flock: personal registration is bounded by SQLite busy timeout.
        with self.transaction():
            old=self.conn.execute('SELECT descriptor FROM campaigns WHERE id=?',(descriptor['campaign_id'],)).fetchone()
            text=canonical_json(descriptor).decode()
            if old and old[0] != text:raise ValueError('Campaign identity collision')
            self.conn.execute("INSERT OR IGNORE INTO campaigns(id,descriptor,state) VALUES(?,?,'active')",(descriptor['campaign_id'],text))

    def expand(self):
        from ..realm.runner import _seed
        with self.ownership(),self.transaction():
            campaigns=self.conn.execute("SELECT * FROM campaigns WHERE state='active' ORDER BY id").fetchall()
            for campaign in campaigns:
                desc=validate_descriptor(strict_json_loads(campaign['descriptor']));caps=desc['caps']
                cursor=campaign['cursor'];count=int(desc['count']);stride=desc['sampling']['stride']
                while cursor*stride < count:
                    identity=dict(desc['observation_identity'],seed=str(_seed(int(desc['start'])+cursor*stride,desc['search'])))
                    task_id=digest([identity,desc['pipeline_revision']]) if 'pipeline_revision' in desc else digest(identity)
                    old=self.conn.execute('SELECT caps,state FROM jobs WHERE id=?',(task_id,)).fetchone()
                    pending=self.conn.execute("SELECT count(*) FROM jobs WHERE state NOT IN ('complete','failed','cancelled')").fetchone()[0]
                    if (old is None or old['state']=='cancelled') and pending >= caps['pending_cap']:break
                    if old:
                        previous=json.loads(old['caps']);merged={k:min(previous[k],caps[k]) for k in caps}
                        self.conn.execute('UPDATE jobs SET caps=? WHERE id=?',(json.dumps(merged),task_id))
                        if old['state']=='cancelled':
                            self.conn.execute("UPDATE jobs SET state='pending',generation=generation+1,attempts=0,next_after=0,worker=NULL,reason=NULL WHERE id=?",(task_id,))
                    else:
                        path=str(self.root/'staging'/task_id/'observation.json')
                        self.conn.execute("INSERT INTO jobs(id,identity,seed,state,checkpoint,caps) VALUES(?,?,?,'pending',?,?)",
                            (task_id,json.dumps(identity),identity['seed'],path,json.dumps(caps)))
                    self.conn.execute('INSERT OR IGNORE INTO membership VALUES(?,?)',(task_id,campaign['id']))
                    cursor+=1
                    self.conn.execute('UPDATE campaigns SET cursor=? WHERE id=?',(cursor,campaign['id']))

    def _job(self, row):
        result=dict(row);result['task_id']=result.pop('id');result['root']=str(self.root)
        result['identity']=json.loads(result['identity']);result['caps']=json.loads(result['caps'])
        result['worker_id']=result['worker']
        member=self.conn.execute("""SELECT m.campaign_id FROM membership m JOIN campaigns c ON c.id=m.campaign_id
            WHERE m.task_id=? AND c.state='active' ORDER BY m.campaign_id LIMIT 1""",(result['task_id'],)).fetchone()
        result['campaign_id']=member[0] if member else None
        return result

    def claim(self, worker_id, *, now=None, lease_seconds=150):
        if not isinstance(worker_id,str) or not 1 <= len(worker_id) <= 128:raise ValueError('Invalid worker ID')
        if type(lease_seconds) not in (int,float) or not math.isfinite(lease_seconds) or not 0 < lease_seconds <= 600:raise ValueError('Invalid lease')
        now=self._time(now)
        self.expand()
        with self.ownership(),self.transaction():
            rows=self.conn.execute("""SELECT j.* FROM jobs j WHERE
              (j.state IN ('pending','partial','deferred') OR (j.state='leased' AND j.expires<=?))
              AND j.next_after<=? AND EXISTS(SELECT 1 FROM membership m JOIN campaigns c ON c.id=m.campaign_id
              WHERE m.task_id=j.id AND c.state='active') ORDER BY j.id""",(now,now)).fetchall()
            for row in rows:
                caps=json.loads(row['caps'])
                if row['attempts'] >= caps['max_attempts']:
                    self.conn.execute("UPDATE jobs SET state='failed',reason='attempt cap reached',generation=generation+1 WHERE id=?",(row['id'],));continue
                self.conn.execute("UPDATE jobs SET state='leased',worker=?,generation=generation+1,expires=?,attempts=attempts+1,process_start=? WHERE id=?",
                    (worker_id,now+lease_seconds,f'{os.getpid()}:{time.monotonic_ns()}',row['id']))
                checkpoint=str(self.root/'staging'/row['id']/str(row['generation']+1)/'observation.json')
                self.conn.execute('UPDATE jobs SET checkpoint=? WHERE id=?',(checkpoint,row['id']))
                result=self._job(self.conn.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone())
                result['previous_checkpoint']=row['checkpoint']
                return result
        return None

    def _time(self,now=None):
        value=self.clock() if now is None else now
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid lease clock')
        return value

    def _guard(self,job,*,now=None):
        row=self.conn.execute('SELECT * FROM jobs WHERE id=?',(job['task_id'],)).fetchone()
        if not row or row['state']!='leased' or row['worker']!=job['worker_id'] or row['generation']!=job['generation'] or row['expires']<=self._time(now):
            raise ValueError('Stale or expired harvest lease')
        return row

    def heartbeat(self,job,*,now=None):
        with self.ownership(),self.transaction():
            self._guard(job,now=now)
            self.conn.execute('UPDATE jobs SET expires=? WHERE id=?',(self._time(now)+150,job['task_id']))

    @contextmanager
    def publication(self,job):
        with self.ownership():
            self._guard(job)
            yield

    def acknowledge(self,job,snapshot_id):
        if not _hex(snapshot_id):raise ValueError('Invalid published snapshot')
        with self.ownership(),self.transaction():
            self._guard(job)
            self.conn.execute("UPDATE jobs SET state='complete',snapshot_id=?,reason=NULL WHERE id=?",(snapshot_id,job['task_id']))

    def fail(self,job,reason,*,partial=False,now=None):
        with self.ownership(),self.transaction():
            row=self._guard(job,now=now);caps=json.loads(row['caps']);now=self._time(now)
            state='failed' if row['attempts']>=caps['max_attempts'] else ('partial' if partial else 'pending')
            self.conn.execute('UPDATE jobs SET state=?,reason=?,next_after=? WHERE id=?',
                (state,str(reason)[:500],now+min(60,2**row['attempts']),job['task_id']))

    def defer(self,job,reason):
        with self.ownership(),self.transaction():
            self._guard(job)
            self.conn.execute("UPDATE jobs SET state='deferred',reason=?,next_after=? WHERE id=?",
                              (str(reason)[:500],self.clock()+60,job['task_id']))

    def set_campaign_state(self,campaign_id,state):
        if state not in ('active','paused','cancelled'):raise ValueError('Invalid campaign state')
        with self.ownership(),self.transaction():
            current=self.conn.execute('SELECT state FROM campaigns WHERE id=?',(campaign_id,)).fetchone()
            if not current:raise ValueError('Unknown campaign')
            if current[0]=='cancelled' and state!='cancelled':raise ValueError('Cancelled campaign cannot resume')
            self.conn.execute('UPDATE campaigns SET state=? WHERE id=?',(state,campaign_id))
            if state=='active':
                self.conn.execute("UPDATE jobs SET next_after=0 WHERE state='deferred' AND id IN (SELECT task_id FROM membership WHERE campaign_id=?)",(campaign_id,))
            # Fence only tasks with no remaining active owner, including shared jobs.
            self.conn.execute("""UPDATE jobs SET state='deferred',generation=generation+1,worker=NULL,reason='campaign inactive'
              WHERE state NOT IN ('complete','failed') AND NOT EXISTS(SELECT 1 FROM membership m JOIN campaigns c ON c.id=m.campaign_id
              WHERE m.task_id=jobs.id AND c.state='active')""")
            self.conn.execute("""UPDATE jobs SET state='cancelled',reason='all owning campaigns cancelled'
              WHERE state='deferred' AND NOT EXISTS(SELECT 1 FROM membership m JOIN campaigns c ON c.id=m.campaign_id
              WHERE m.task_id=jobs.id AND c.state!='cancelled')""")

    def status(self):
        return dict(revision='catalog-harvest-status-v1',jobs={r[0]:r[1] for r in self.conn.execute('SELECT state,count(*) FROM jobs GROUP BY state')},
            campaigns=[dict(id=r['id'],state=r['state'],scheduled_samples=r['cursor'],
                target_count=json.loads(r['descriptor'])['count']) for r in self.conn.execute('SELECT * FROM campaigns ORDER BY id')])


_DECIMAL_RE = re.compile(r'^-?(?:0|[1-9]\d*)(?:\.\d+)?$')


def _validate_rank_item(item):
    if isinstance(item, bool):
        raise ValueError('Booleans are prohibited in rank keys')
    if isinstance(item, float):
        raise ValueError('Floats are prohibited in rank keys')
    if type(item) is int:
        return (0, Fraction(item, 1))
    if isinstance(item, str):
        return (1, item)
    if isinstance(item, dict):
        keys = set(item.keys())
        if keys == {'numerator', 'denominator'}:
            num = item['numerator']
            den = item['denominator']
            if type(num) is not int or isinstance(num, bool):
                raise ValueError('Rational numerator must be an integer (not bool)')
            if type(den) is not int or isinstance(den, bool) or den <= 0:
                raise ValueError('Rational denominator must be a positive integer')
            return (0, Fraction(num, den))
        elif keys == {'decimal'}:
            dec = item['decimal']
            if not isinstance(dec, str):
                raise ValueError('Decimal key value must be a string')
            if not _DECIMAL_RE.match(dec):
                raise ValueError(f'Invalid decimal string: {dec!r}')
            try:
                d = Decimal(dec)
            except (InvalidOperation, TypeError) as exc:
                raise ValueError(f'Invalid decimal value: {dec!r}') from exc
            if not d.is_finite():
                raise ValueError(f'Non-finite decimal value: {dec!r}')
            if d.is_zero() and dec.startswith('-'):
                raise ValueError(f'Negative zero is not canonical: {dec!r}')
            return (0, Fraction(d))
        else:
            raise ValueError(f'Unsupported dict in rank: {keys}')
    raise ValueError(f'Unsupported rank item type: {type(item).__name__}')


def _validate_rank(rank):
    if not isinstance(rank, list):
        raise ValueError('rank must be a list')
    return tuple(_validate_rank_item(x) for x in rank)


class AutomationLedger:
    def __init__(self, queue, *, policy_revision, objectives, policy_contract=None):
        if not isinstance(queue, HarvestQueue) and not (hasattr(queue, 'conn') and hasattr(queue, 'transaction')):
            raise ValueError('Invalid queue: expected HarvestQueue instance')
        if getattr(queue, 'conn', None) is None:
            raise ValueError('Queue connection is closed or uninitialized')
        if not _hex(policy_revision):
            raise ValueError('Invalid policy_revision: must be 64-character lowercase hex string')
        if not isinstance(objectives, dict):
            raise ValueError('objectives must be a dictionary')
        max_objectives,max_slots=7027,105644
        if policy_contract is not None:
            from .reserve_policy import validate_contract,contract
            max_objectives,max_slots=validate_contract(policy_contract)
            if objectives!=contract()['retained_objectives']:
                raise ValueError('Expanded objectives differ from known policy')
        self.policy_contract=policy_contract
        if not (0 <= len(objectives) <= max_objectives):
            raise ValueError('objectives count exceeds known policy')

        total_slots = 0
        cleaned_objectives = {}
        for obj_id, cap in objectives.items():
            if not isinstance(obj_id, str) or not obj_id or len(obj_id) > 256:
                raise ValueError(f'Invalid objective ID: {obj_id!r}')
            if type(cap) is not int or isinstance(cap, bool) or not (1 <= cap <= (20000 if policy_contract is not None else 10000)):
                raise ValueError(f'Invalid capacity for objective {obj_id!r}: {cap!r}')
            total_slots += cap
            cleaned_objectives[obj_id] = cap

        if total_slots > max_slots:
            raise ValueError(f'Aggregate capacity {total_slots} exceeds declared limit of {max_slots} slots')

        self.queue = queue
        self.conn = queue.conn
        self.policy_revision = policy_revision
        self.objectives = cleaned_objectives

        with self.queue.transaction():
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS automation_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS automation_receipts (
                    world_id TEXT PRIMARY KEY,
                    identity TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    artifact TEXT NOT NULL,
                    evaluations TEXT NOT NULL,
                    replay TEXT NOT NULL
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS automation_members (
                    objective_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    rank_json TEXT NOT NULL,
                    member_json TEXT NOT NULL,
                    PRIMARY KEY (objective_id, world_id)
                )
            ''')
            meta_rows = dict(self.conn.execute('SELECT key, value FROM automation_meta').fetchall())
            if meta_rows:
                if meta_rows.get('policy_revision') != self.policy_revision:
                    raise ValueError(f"Incompatible policy revision: {meta_rows.get('policy_revision')} != {self.policy_revision}")
                if meta_rows.get('objectives') != canonical_json(self.objectives).decode('utf-8'):
                    raise ValueError('Incompatible objectives definition')
                if meta_rows.get('schema_revision') != 'automation-ledger-v1':
                    raise ValueError('Incompatible automation schema revision')
            else:
                self.conn.execute("INSERT INTO automation_meta (key, value) VALUES ('schema_revision', 'automation-ledger-v1')")
                self.conn.execute('INSERT INTO automation_meta (key, value) VALUES (\'policy_revision\', ?)', (self.policy_revision,))
                self.conn.execute('INSERT INTO automation_meta (key, value) VALUES (\'objectives\', ?)', (canonical_json(self.objectives).decode('utf-8'),))
                self.conn.execute("INSERT INTO automation_meta (key, value) VALUES ('generation', '0')")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def generation(self):
        row = self.conn.execute("SELECT value FROM automation_meta WHERE key='generation'").fetchone()
        return int(row[0]) if row else 0

    def population(self):
        row = self.conn.execute('SELECT count(*) FROM automation_receipts').fetchone()
        return int(row[0]) if row else 0

    def protect_verification(self,world_ids,*,release=False):
        """Existing ledger metadata keeps in-flight finalist observations reachable."""
        if not self.queue._depth:raise ValueError('Verification protection requires writer ownership')
        wanted=set(world_ids)
        if any(not _hex(wid) or self.receipt(wid) is None for wid in wanted):raise ValueError('Unknown verification world')
        with self.queue.transaction():
            row=self.conn.execute("SELECT value FROM automation_meta WHERE key='verification_worlds'").fetchone()
            current=set(strict_json_loads(row[0])) if row else set()
            current=current-wanted if release else current|wanted
            self.conn.execute("INSERT INTO automation_meta VALUES('verification_worlds',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(canonical_json(sorted(current)).decode(),))

    def retained_worlds(self):
        rows = self.conn.execute('SELECT DISTINCT world_id FROM automation_members ORDER BY world_id').fetchall()
        return [r[0] for r in rows]

    def receipt(self, world_id):
        if not _hex(world_id):
            raise ValueError('Invalid world_id: must be 64-character lowercase hex string')
        row = self.conn.execute(
            'SELECT world_id, identity, observation_id, artifact, evaluations, replay FROM automation_receipts WHERE world_id=?',
            (world_id,)
        ).fetchone()
        if not row:
            return None
        return {
            'world_id': row[0],
            'identity': strict_json_loads(row[1]),
            'observation_id': row[2],
            'artifact': strict_json_loads(row[3]),
            'evaluations': strict_json_loads(row[4]),
            'replay': strict_json_loads(row[5])
        }

    def receipts(self):
        rows = self.conn.execute(
            'SELECT world_id, identity, observation_id, artifact, evaluations, replay FROM automation_receipts ORDER BY world_id'
        ).fetchall()
        return [
            {
                'world_id': r[0],
                'identity': strict_json_loads(r[1]),
                'observation_id': r[2],
                'artifact': strict_json_loads(r[3]),
                'evaluations': strict_json_loads(r[4]),
                'replay': strict_json_loads(r[5])
            }
            for r in rows
        ]

    def members(self, objective_id=None):
        if objective_id is not None:
            if objective_id not in self.objectives:
                raise ValueError(f'Unregistered objective ID: {objective_id!r}')
            rows = self.conn.execute(
                'SELECT objective_id, world_id, rank_json, member_json FROM automation_members WHERE objective_id=?',
                (objective_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                'SELECT objective_id, world_id, rank_json, member_json FROM automation_members'
            ).fetchall()

        entries = []
        for r in rows:
            rk = strict_json_loads(r[2])
            mem = strict_json_loads(r[3])
            entries.append({
                'objective_id': r[0],
                'world_id': r[1],
                'rank': rk,
                'member': mem,
                '_sort_key': _validate_rank(rk)
            })

        if objective_id is not None:
            entries.sort(key=lambda e: (e['_sort_key'], e['world_id']))
        else:
            entries.sort(key=lambda e: (e['objective_id'], e['_sort_key'], e['world_id']))

        for e in entries:
            del e['_sort_key']
        return entries

    def offer(self, receipt, offers):
        if not isinstance(receipt, dict):
            raise ValueError('receipt must be a dict')
        required_receipt_keys = {'world_id', 'identity', 'observation_id', 'artifact', 'evaluations', 'replay'}
        if set(receipt.keys()) != required_receipt_keys:
            raise ValueError(f'Invalid receipt schema; expected keys {required_receipt_keys}')

        wid = receipt['world_id']
        if not _hex(wid):
            raise ValueError('receipt world_id must be 64-character lowercase hex string')

        obs_id = receipt['observation_id']
        if not _hex(obs_id):
            raise ValueError('receipt observation_id must be 64-character lowercase hex string')

        bound_world_id = world_id(receipt['identity'])
        if bound_world_id != wid:
            raise ValueError(f'receipt world_id {wid} does not match computed models.world_id {bound_world_id}')

        if not isinstance(receipt['evaluations'], list):
            raise ValueError('receipt evaluations must be a list')
        if not isinstance(receipt['replay'], dict):
            raise ValueError('receipt replay must be a dict')

        artifact_json = canonical_json(receipt['artifact']).decode('utf-8')
        evaluations_json = canonical_json(receipt['evaluations']).decode('utf-8')
        replay_json = canonical_json(receipt['replay']).decode('utf-8')
        identity_json = canonical_json(receipt['identity']).decode('utf-8')

        if not isinstance(offers, list):
            raise ValueError('offers must be a list')

        required_offer_keys = {'objective_id', 'rank', 'member'}
        validated_offers = []
        for off in offers:
            if not isinstance(off, dict) or set(off.keys()) != required_offer_keys:
                raise ValueError('Invalid offer entry schema; must contain objective_id, rank, member')
            obj_id = off['objective_id']
            if obj_id not in self.objectives:
                raise ValueError(f'Unregistered objective ID: {obj_id!r}')
            rank = off['rank']
            sort_key = _validate_rank(rank)
            member = off['member']
            if not isinstance(member, dict):
                raise ValueError('offer member must be a dict')
            if member.get('world_id') != wid:
                raise ValueError('Member must bind same world_id as receipt')
            if 'source_observation_id' in member and member['source_observation_id'] != obs_id:
                raise ValueError(
                    f'Member source_observation_id {member["source_observation_id"]!r} does not match receipt observation_id {obs_id!r}'
                )
            member_json = canonical_json(member).decode('utf-8')
            rank_json = canonical_json(rank).decode('utf-8')
            validated_offers.append({
                'objective_id': obj_id,
                'rank': rank,
                'rank_json': rank_json,
                'sort_key': sort_key,
                'member': member,
                'member_json': member_json,
            })

        best_by_obj = {}
        for off in validated_offers:
            oid = off['objective_id']
            if oid not in best_by_obj or off['sort_key'] < best_by_obj[oid]['sort_key']:
                best_by_obj[oid] = off

        with self.queue.transaction():
            existing_receipt_row = self.conn.execute(
                'SELECT identity, observation_id, artifact, evaluations, replay FROM automation_receipts WHERE world_id=?',
                (wid,)
            ).fetchone()

            is_new_world = (existing_receipt_row is None)
            is_new_obs = (not is_new_world and existing_receipt_row[1] != obs_id)

            if is_new_world:
                receipt_changed = True
            else:
                receipt_changed = (
                    existing_receipt_row[0] != identity_json or
                    existing_receipt_row[1] != obs_id or
                    existing_receipt_row[2] != artifact_json or
                    existing_receipt_row[3] != evaluations_json or
                    existing_receipt_row[4] != replay_json
                )

            old_winner_rows = self.conn.execute(
                'SELECT objective_id, rank_json, member_json FROM automation_members WHERE world_id=?',
                (wid,)
            ).fetchall()
            old_winning_objs = {r[0]: (strict_json_loads(r[1]), strict_json_loads(r[2])) for r in old_winner_rows}

            if is_new_obs:
                missing = set(old_winning_objs.keys()) - set(best_by_obj.keys())
                if missing:
                    raise ValueError(
                        f'New observation ID for world {wid} missing required offers for previously winning objectives: {sorted(missing)}'
                    )
                for oid, (old_rank, _) in old_winning_objs.items():
                    old_sort_key = _validate_rank(old_rank)
                    new_sort_key = best_by_obj[oid]['sort_key']
                    if new_sort_key > old_sort_key:
                        raise ValueError(
                            f'New observation ID for world {wid} has worse rank for previously winning objective {oid!r}: '
                            f'{best_by_obj[oid]["rank"]} is worse than {old_rank}'
                        )

            if is_new_world:
                self.conn.execute('''
                    INSERT INTO automation_receipts (world_id, identity, observation_id, artifact, evaluations, replay)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (wid, identity_json, obs_id, artifact_json, evaluations_json, replay_json))
            elif receipt_changed:
                self.conn.execute('''
                    UPDATE automation_receipts
                    SET identity=?, observation_id=?, artifact=?, evaluations=?, replay=?
                    WHERE world_id=?
                ''', (identity_json, obs_id, artifact_json, evaluations_json, replay_json, wid))

            membership_changed = False
            for oid, off in best_by_obj.items():
                cap = self.objectives[oid]
                rows = self.conn.execute(
                    'SELECT world_id, rank_json, member_json FROM automation_members WHERE objective_id=?',
                    (oid,)
                ).fetchall()

                old_members_map = {r[0]: (r[1], r[2]) for r in rows}

                existing_members = []
                current_winner_idx = None
                for idx, r in enumerate(rows):
                    rw_id = r[0]
                    rrank = strict_json_loads(r[1])
                    rmember = strict_json_loads(r[2])
                    rsort_key = _validate_rank(rrank)
                    entry = {
                        'world_id': rw_id,
                        'rank': rrank,
                        'rank_json': r[1],
                        'sort_key': rsort_key,
                        'member': rmember,
                        'member_json': r[2]
                    }
                    existing_members.append(entry)
                    if rw_id == wid:
                        current_winner_idx = idx

                if current_winner_idx is not None:
                    old_sort_key = existing_members[current_winner_idx]['sort_key']
                    should_update = (
                        (is_new_obs and off['sort_key'] <= old_sort_key) or
                        (not is_new_obs and off['sort_key'] < old_sort_key)
                    )
                    if should_update:
                        existing_members[current_winner_idx] = {
                            'world_id': wid,
                            'rank': off['rank'],
                            'rank_json': off['rank_json'],
                            'sort_key': off['sort_key'],
                            'member': off['member'],
                            'member_json': off['member_json']
                        }
                else:
                    existing_members.append({
                        'world_id': wid,
                        'rank': off['rank'],
                        'rank_json': off['rank_json'],
                        'sort_key': off['sort_key'],
                        'member': off['member'],
                        'member_json': off['member_json']
                    })

                existing_members.sort(key=lambda e: (e['sort_key'], e['world_id']))
                surviving = existing_members[:cap]

                new_members_map = {s['world_id']: (s['rank_json'], s['member_json']) for s in surviving}
                if new_members_map != old_members_map:
                    membership_changed = True
                    self.conn.execute('DELETE FROM automation_members WHERE objective_id=?', (oid,))
                    for s in surviving:
                        self.conn.execute(
                            'INSERT INTO automation_members (objective_id, world_id, rank_json, member_json) VALUES (?, ?, ?, ?)',
                            (oid, s['world_id'], s['rank_json'], s['member_json'])
                        )

            if receipt_changed or membership_changed:
                cur_gen = int(self.conn.execute("SELECT value FROM automation_meta WHERE key='generation'").fetchone()[0])
                self.conn.execute("UPDATE automation_meta SET value=? WHERE key='generation'", (str(cur_gen + 1),))
