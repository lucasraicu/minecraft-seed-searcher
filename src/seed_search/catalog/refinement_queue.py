"""Bounded offline tile spool with crash recovery and fenced results. No daemon."""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import time
import threading

_PROCESS_LOCK=threading.RLock()
from .ingestion import atomic_json,strict_json_loads,verify_no_symlinks
from .refinement import make_tile,decode_tile
from .accuracy import integer
from .registry import digest


class RefinementQueue:
    def __init__(self,root,*,clock=time.time):
        self.root=verify_no_symlinks(root);self.root.mkdir(parents=True,exist_ok=True);self.clock=clock
        self.lock=verify_no_symlinks(self.root/'refinement.lock')

    @contextmanager
    def _locked(self):
        with _PROCESS_LOCK,self.lock.open('a+b')as handle:
            fcntl.flock(handle,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(handle,fcntl.LOCK_UN)

    def _path(self,key):
        from .accuracy import sha256
        return verify_no_symlinks(self.root/(sha256(key)+'.json'))

    def _read(self,key):
        p=self._path(key)
        if p.stat().st_size>1<<20:raise ValueError('Refinement record cap')
        value=strict_json_loads(p.read_bytes())
        if digest(value['spec'])!=key:raise ValueError('Refinement descriptor changed')
        return value

    def submit(self,context,bounds,y):
        # Validate exact geometry/provider/height before recording work.
        if not isinstance(bounds,list)or len(bounds)!=4:raise ValueError('Invalid bounds')
        n=(bounds[2]-bounds[0])*(bounds[3]-bounds[1])
        integer(n,1,4096)
        tile=make_tile(context,bounds,y,[None]*n)
        spec=dict(revision='catalog-refinement-job-v1',context=tile['context'],bounds=tile['bounds'],y=y)
        key=digest(spec)
        with self._locked():
            if self._path(key).exists():return key
            if len(list(self.root.glob('*.json')))>=100:raise ValueError('Offline refinement spool cap100')
            atomic_json(self._path(key),dict(spec=spec,state='queued',generation=0,attempts=0,expires=0,result=None,error=None))
        return key

    def claim(self,*,lease_seconds=90):
        integer(lease_seconds,1,300)
        with self._locked():
            for path in sorted(self.root.glob('*.json')):
                key=path.stem;row=self._read(key)
                ready=row['state']=='queued' or (row['state']=='active' and row['expires']<=self.clock())
                if not ready:continue
                if row['attempts']>=3:
                    row.update(state='failed',error='Attempt cap after expired leases');atomic_json(path,row);continue
                row.update(state='active',generation=row['generation']+1,attempts=row['attempts']+1,expires=self.clock()+lease_seconds)
                atomic_json(path,row);return dict(task_id=key,generation=row['generation'],spec=row['spec'])
        return None

    def complete(self,claim,tile):
        decode_tile(tile)
        with self._locked():
            row=self._read(claim['task_id'])
            if row['state']!='active' or row['generation']!=claim['generation'] or row['expires']<=self.clock():
                raise ValueError('Expired/cancelled/replaced refinement claim')
            if any(tile[k]!=row['spec'][k]for k in ('context','bounds','y')):raise ValueError('Refinement result scope differs')
            row.update(state='complete',result=tile,expires=0);atomic_json(self._path(claim['task_id']),row)

    def cancel(self,key):
        with self._locked():
            row=self._read(key)
            if row['state']=='complete':raise ValueError('Completed immutable result cannot be cancelled')
            row.update(state='cancelled',generation=row['generation']+1,expires=0);atomic_json(self._path(key),row)

    def result(self,key):
        with self._locked():
            row=self._read(key)
            if row['state']!='complete':return dict(status=row['state'],tile=None)
            decode_tile(row['result']);return dict(status='complete',tile=row['result'])
