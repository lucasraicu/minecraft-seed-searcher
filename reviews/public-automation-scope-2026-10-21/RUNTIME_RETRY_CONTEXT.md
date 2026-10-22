Approved runtime gap: queued partial failures use future next_after; run() currently exits no_ready_work rather than auto retrying. Fix only retry scheduling within existing durable600s allocation, cancellable short sleeps, explicitwall budget, samequeuelease rules. max_worlds counts actual attempts, not sleeps. Preserve explicit worldtime resource pause. Do not change config identity in this task; Codex owns later source pin work.

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


