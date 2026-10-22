"""Bounded, owned CPU query processes; no search, extraction or shell dispatch."""
from collections import OrderedDict, deque
from dataclasses import dataclass, field
import hashlib
import json
import math
import multiprocessing
import os
import socket
import struct
import threading
import time
import uuid

PROTOCOL = 'catalog-query-worker-v1'
MAX_REQUEST = 1 << 20
MAX_REPLY = 4 << 20


def _remaining(deadline):
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Query deadline exhausted')
    return remaining


def _send(sock, value, deadline, cap):
    raw = json.dumps(value, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > cap:
        raise ValueError('IPC message exceeds its byte allowance')
    sock.settimeout(_remaining(deadline))
    sock.sendall(struct.pack('!I', len(raw)) + raw)
    _remaining(deadline)


def _receive(sock, deadline, cap):
    def read(n):
        parts = bytearray()
        while len(parts) < n:
            sock.settimeout(_remaining(deadline))
            chunk = sock.recv(min(n - len(parts), 65536))
            if not chunk:
                raise EOFError('Query worker closed its channel')
            parts.extend(chunk)
        return bytes(parts)
    length = struct.unpack('!I', read(4))[0]
    if not 2 <= length <= cap:
        raise ValueError('Invalid IPC frame length')
    from .request import _unique
    value = json.loads(read(length), object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite IPC value')))
    if not isinstance(value, dict):
        raise ValueError('Expected IPC object')
    _remaining(deadline)
    return value


def _worker_main(channel, config):
    """Spawn target. Secret/config are local process arguments, never CLI/logs."""
    parent = config['parent']
    def parent_watch():
        while True:
            if os.getppid() != parent:
                os._exit(0)
            time.sleep(.1)
    threading.Thread(target=parent_watch, daemon=True).start()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[key] = '1'
    from .service import CatalogService, ServiceError
    try:
        service = CatalogService(config['root'], secret=config['secret'], cache_bytes=config['cache_bytes'])
        with service._store() as store:
            store.info()
        # Load the compact immutable serving index before readiness.  Query result
        # and projection caches remain cold.  Startup retains its original deadline.
        from .automation_query import available,_store
        if available(service.root) and service.cache_bytes:
            automation_store=_store(service)
            service._query_snapshot(automation_store,automation_store._binding()['snapshot_id'])
        _send(channel, dict(protocol=PROTOCOL, kind='ready', generation=config['generation']), config['startup_deadline'], MAX_REPLY)
        while True:
            job = _receive(channel, None, MAX_REQUEST)
            if (set(job) != {'protocol', 'kind', 'generation', 'id', 'deadline', 'body'}
                    or job['protocol'] != PROTOCOL or job['kind'] != 'query'
                    or job['generation'] != config['generation']
                    or not isinstance(job['id'], str) or len(job['id']) != 32
                    or type(job['deadline']) not in (float, int) or not math.isfinite(job['deadline'])):
                raise ValueError('Invalid query worker protocol')
            deadline = job['deadline']
            service.query_seconds = min(config['query_seconds'], _remaining(deadline))
            envelope = dict(protocol=PROTOCOL, generation=config['generation'], id=job['id'])
            try:
                reply = dict(envelope, kind='result', payload=service.query(job['body']))
            except ServiceError as exc:
                reply = dict(envelope, kind='error', payload=dict(message=str(exc), code=exc.code, status=exc.status))
            except (ValueError, TypeError, KeyError):
                reply = dict(envelope, kind='error', payload=dict(message='Invalid request or unavailable snapshot', code='invalid_request', status=400))
            except Exception:
                reply = dict(envelope, kind='error', payload=dict(message='Catalog data is unavailable; inspect the local audit', code='catalog_unavailable', status=503))
            try:
                _send(channel, reply, deadline, MAX_REPLY)
            except ValueError:
                _send(channel, dict(envelope, kind='error', payload=dict(message='Query response exceeds the IPC allowance', code='response_too_large', status=503)), deadline, MAX_REPLY)
    except (EOFError, OSError, ValueError):
        pass
    finally:
        channel.close()


@dataclass
class _Worker:
    slot: int
    process: object
    channel: socket.socket
    generation: str
    busy: bool = False
    stop_lock: object = field(default_factory=threading.Lock)


def _stop(worker):
    with worker.stop_lock:
        try:
            worker.channel.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        worker.channel.close()
        if worker.process.is_alive():
            worker.process.terminate()
        worker.process.join(.2)
        if worker.process.is_alive():
            worker.process.kill()
            worker.process.join(.2)


class QueryWorkerPool:
    """No job backlog: an idle healthy process lease is required for dispatch."""
    def __init__(self, root, *, secret, workers=2, query_seconds=10., cache_bytes=64 << 20, startup_seconds=5.):
        if type(workers) is not int or workers not in (1, 2):
            raise ValueError('Query process count must be one or two')
        if (not math.isfinite(query_seconds) or not 0 < query_seconds <= 10
                or type(cache_bytes) is not int or not 0 <= cache_bytes <= 64 << 20
                or not 0 < startup_seconds <= 10):
            raise ValueError('Invalid query process resource allowance')
        self.root = str(root)
        self.secret = secret
        self.query_seconds = query_seconds
        self.cache_bytes = cache_bytes
        self.startup_seconds = startup_seconds
        self._condition = threading.Condition()
        self._workers = [None] * workers
        self._starting = set(range(workers))
        self._starting_processes = {}
        self._affinity = OrderedDict()
        self._failures = deque()
        self._exhausted = False
        self._closed = False
        self._managers = set()
        self.startup_seconds_actual = 0.
        start = time.monotonic()
        try:
            for slot in range(workers):
                self._spawn(slot)
        except Exception:
            self.close()
            raise
        self.startup_seconds_actual = time.monotonic() - start

    def _spawn(self, slot):
        parent, child = socket.socketpair()
        generation = uuid.uuid4().hex
        deadline = time.monotonic() + self.startup_seconds
        config = dict(root=self.root, secret=self.secret, cache_bytes=self.cache_bytes,
                      query_seconds=self.query_seconds, parent=os.getpid(), generation=generation, startup_deadline=deadline)
        process = multiprocessing.get_context('spawn').Process(target=_worker_main, args=(child, config), daemon=True)
        worker = _Worker(slot, process, parent, generation)
        try:
            with self._condition:
                if self._closed:
                    raise RuntimeError('Query worker pool closed')
                process.start()
                self._starting_processes[slot] = worker
            child.close()
            ready = _receive(parent, deadline, MAX_REPLY)
            if ready != dict(protocol=PROTOCOL, kind='ready', generation=generation):
                raise ValueError('Invalid query worker readiness')
            with self._condition:
                if self._closed:
                    raise RuntimeError('Query worker pool closed during startup')
                self._workers[slot] = worker
                self._starting_processes.pop(slot, None)
                self._starting.discard(slot)
                self._condition.notify_all()
        except Exception:
            child.close()
            if process.pid is not None:
                _stop(worker)
            else:
                parent.close()
            with self._condition:
                self._starting_processes.pop(slot, None)
                self._starting.discard(slot)
                self._condition.notify_all()
            raise

    def _replace(self, slot):
        try:
            self._spawn(slot)
        except Exception:
            with self._condition:
                self._record_failure()
        finally:
            with self._condition:
                self._managers.discard(threading.current_thread())

    def _record_failure(self):
        now = time.monotonic()
        while self._failures and self._failures[0] < now - 300:
            self._failures.popleft()
        self._failures.append(now)
        if len(self._failures) >= 3:
            self._exhausted = True

    def _retire(self, worker):
        with self._condition:
            if self._workers[worker.slot] is not worker:
                return
            self._workers[worker.slot] = None
            self._affinity = OrderedDict((key, slot) for key, slot in self._affinity.items() if slot != worker.slot)
            self._record_failure()
            restart = not self._closed and not self._exhausted
            if restart:
                self._starting.add(worker.slot)
            self._condition.notify_all()
        _stop(worker)
        if restart:
            manager = threading.Thread(target=self._replace, args=(worker.slot,), daemon=True)
            with self._condition:
                if self._closed:
                    self._starting.discard(worker.slot)
                    return
                self._managers.add(manager)
                manager.start()

    def _lease(self, key, acquire_deadline):
        from .service import ServiceError
        while True:
            stale = None
            with self._condition:
                if self._closed:
                    raise ServiceError('Catalog query workers are closed', 'query_workers_unavailable', 503)
                if time.monotonic() >= acquire_deadline:
                    raise ServiceError('Catalog query queue timed out', 'busy', 429)
                for worker in self._workers:
                    if worker is not None and not worker.busy and not worker.process.is_alive():
                        worker.busy = True
                        stale = worker
                        break
                if stale is None:
                    idle = [w for w in self._workers if w is not None and not w.busy]
                    if idle:
                        preferred = self._affinity.get(key)
                        worker = next((w for w in idle if w.slot == preferred), idle[0])
                        worker.busy = True
                        return worker
                    if not any(self._workers) and not self._starting:
                        raise ServiceError('Catalog query workers are unavailable', 'query_workers_unavailable', 503)
                    wait = acquire_deadline - time.monotonic()
                    if wait <= 0:
                        raise ServiceError('Catalog query queue timed out', 'busy', 429)
                    self._condition.wait(wait)
            if stale is not None:
                self._retire(stale)

    def query(self, body, *, deadline, acquire_deadline):
        from .service import ServiceError
        try:
            raw = json.dumps(body, separators=(',', ':'), allow_nan=False).encode()
            if len(raw) > MAX_REQUEST - 512:
                raise ValueError('Oversize query')
        except (ValueError, TypeError):
            raise ServiceError('Invalid or over-budget query request') from None
        try:
            key = hashlib.sha256(json.dumps(body.get('request') if isinstance(body, dict) else body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        except (TypeError, ValueError):
            raise ServiceError('Invalid query request') from None
        worker = self._lease(key, acquire_deadline)
        job_id = uuid.uuid4().hex
        try:
            _send(worker.channel, dict(protocol=PROTOCOL, kind='query', generation=worker.generation, id=job_id, deadline=deadline, body=body), deadline, MAX_REQUEST)
            reply = _receive(worker.channel, deadline, MAX_REPLY)
            if (set(reply) != {'protocol', 'kind', 'generation', 'id', 'payload'}
                    or reply['protocol'] != PROTOCOL or reply['generation'] != worker.generation
                    or reply['id'] != job_id or reply['kind'] not in ('result', 'error')
                    or not isinstance(reply['payload'], dict)):
                raise ValueError('Invalid query worker reply')
            _remaining(deadline)
            if reply['kind'] == 'error':
                error = reply['payload']
                if (set(error) != {'message', 'code', 'status'} or type(error['status']) is not int
                        or not 400 <= error['status'] <= 599 or not isinstance(error['code'], str)
                        or len(error['code']) > 64 or not isinstance(error['message'], str) or len(error['message']) > 4096):
                    raise ValueError('Invalid query worker error')
                raise ServiceError(error['message'], error['code'], error['status'])
            result = reply['payload']
            if (result.get('ok') is not True or not isinstance(result.get('results'), list)
                    or len(result['results']) > 50 or type(result.get('matched_worlds')) is not int
                    or result['matched_worlds'] < len(result['results'])
                    or not isinstance(result.get('stats'), dict)):
                raise ValueError('Malformed query result')
            with self._condition:
                self._affinity.pop(key, None)
                self._affinity[key] = worker.slot
                while len(self._affinity) > 16:
                    self._affinity.popitem(last=False)
            return reply['payload']
        except ServiceError:
            raise
        except (TimeoutError, EOFError, OSError, ValueError):
            expired = time.monotonic() >= deadline
            self._retire(worker)
            raise ServiceError('Catalog query exceeded its time allowance' if expired else 'Catalog query worker failed',
                               'query_timeout' if expired else 'query_worker_failed', 503) from None
        finally:
            with self._condition:
                worker.busy = False
                self._condition.notify_all()

    def status(self):
        with self._condition:
            healthy = [w for w in self._workers if w is not None and w.process.is_alive()]
            return dict(limit=len(self._workers), ready=len(healthy), busy=sum(w.busy for w in healthy),
                        starting=len(self._starting), restart_exhausted=self._exhausted,
                        pids=[w.process.pid for w in healthy], startup_seconds=self.startup_seconds_actual)

    def close(self):
        with self._condition:
            if self._closed:
                return
            self._closed = True
            workers = [w for w in self._workers if w is not None] + list(self._starting_processes.values())
            managers = list(self._managers)
            self._workers = [None] * len(self._workers)
            self._affinity.clear()
            self._condition.notify_all()
        for worker in workers:
            _stop(worker)
        for manager in managers:
            manager.join(.5)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
