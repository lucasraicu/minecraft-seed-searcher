Narrow controlled retry after fullpoolreviewtimeout180s; no validated failedresult. New realtests1then2workers+SIGSTOP IPCwrite deadlines+SIGKILL/no-replay+restartbudget+affinitybypass+onehealthyworker+parentSIGTERM/SIGKILL allpass36focused11.66s(including12pooltests). Matched deterministic500failedpairs nowpass6.76/3.94and7.68/7.66s. Review only lifecycle/lease races in actual slices; no tools/edits/tests. Parent.admission4/execution2 and absolute10s deadline include<=2s totalqueue, pool.query finallyreleasesworker.busy via conditionnotify, allsocketIOboundedwithabsolute deadline.

query_workers.py
63:     def parent_watch():
64:         while True:
65:             if os.getppid() != parent:
66:                 os._exit(0)
67:             time.sleep(.1)
68:     threading.Thread(target=parent_watch, daemon=True).start()
69:     for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
70:         os.environ[key] = '1'
71:     from .service import CatalogService, ServiceError
72:     try:
73:         service = CatalogService(config['root'], secret=config['secret'], cache_bytes=config['cache_bytes'])
74:         with service._store() as store:
75:             store.info()
76:         _send(channel, dict(protocol=PROTOCOL, kind='ready', generation=config['generation']), config['startup_deadline'], MAX_REPLY)
77:         while True:
78:             job = _receive(channel, None, MAX_REQUEST)
79:             if (set(job) != {'protocol', 'kind', 'generation', 'id', 'deadline', 'body'}
80:                     or job['protocol'] != PROTOCOL or job['kind'] != 'query'
81:                     or job['generation'] != config['generation']
82:                     or not isinstance(job['id'], str) or len(job['id']) != 32
83:                     or type(job['deadline']) not in (float, int) or not math.isfinite(job['deadline'])):
84:                 raise ValueError('Invalid query worker protocol')
85:             deadline = job['deadline']

query_workers.py
123:         if worker.process.is_alive():
124:             worker.process.terminate()
125:         worker.process.join(.2)
126:         if worker.process.is_alive():
127:             worker.process.kill()
128:             worker.process.join(.2)
129: 
130: 
131: class QueryWorkerPool:
132:     """No job backlog: an idle healthy process lease is required for dispatch."""
133:     def __init__(self, root, *, secret, workers=2, query_seconds=10., cache_bytes=64 << 20, startup_seconds=5.):
134:         if type(workers) is not int or workers not in (1, 2):
135:             raise ValueError('Query process count must be one or two')
136:         if (not math.isfinite(query_seconds) or not 0 < query_seconds <= 10
137:                 or type(cache_bytes) is not int or not 0 <= cache_bytes <= 64 << 20
138:                 or not 0 < startup_seconds <= 10):
139:             raise ValueError('Invalid query process resource allowance')
140:         self.root = str(root)
141:         self.secret = secret
142:         self.query_seconds = query_seconds
143:         self.cache_bytes = cache_bytes
144:         self.startup_seconds = startup_seconds
145:         self._condition = threading.Condition()
146:         self._workers = [None] * workers
147:         self._starting = set(range(workers))
148:         self._starting_processes = {}
149:         self._affinity = OrderedDict()
150:         self._failures = deque()
151:         self._exhausted = False
152:         self._closed = False
153:         self._managers = set()
154:         self.startup_seconds_actual = 0.
155:         start = time.monotonic()
156:         try:
157:             for slot in range(workers):
158:                 self._spawn(slot)
159:         except Exception:
160:             self.close()
161:             raise
162:         self.startup_seconds_actual = time.monotonic() - start
163: 
164:     def _spawn(self, slot):
165:         parent, child = socket.socketpair()
166:         generation = uuid.uuid4().hex
167:         deadline = time.monotonic() + self.startup_seconds
168:         config = dict(root=self.root, secret=self.secret, cache_bytes=self.cache_bytes,
169:                       query_seconds=self.query_seconds, parent=os.getpid(), generation=generation, startup_deadline=deadline)
170:         process = multiprocessing.get_context('spawn').Process(target=_worker_main, args=(child, config), daemon=True)
171:         worker = _Worker(slot, process, parent, generation)
172:         try:
173:             with self._condition:
174:                 if self._closed:
175:                     raise RuntimeError('Query worker pool closed')
176:                 process.start()
177:                 self._starting_processes[slot] = worker
178:             child.close()
179:             ready = _receive(parent, deadline, MAX_REPLY)
180:             if ready != dict(protocol=PROTOCOL, kind='ready', generation=generation):
181:                 raise ValueError('Invalid query worker readiness')
182:             with self._condition:
183:                 if self._closed:
184:                     raise RuntimeError('Query worker pool closed during startup')
185:                 self._workers[slot] = worker
186:                 self._starting_processes.pop(slot, None)
187:                 self._starting.discard(slot)
188:                 self._condition.notify_all()
189:         except Exception:
190:             child.close()
191:             if process.pid is not None:
192:                 _stop(worker)
193:             else:
194:                 parent.close()
195:             with self._condition:
196:                 self._starting_processes.pop(slot, None)
197:                 self._starting.discard(slot)
198:                 self._condition.notify_all()
199:             raise
200: 
201:     def _replace(self, slot):
202:         try:
203:             self._spawn(slot)
204:         except Exception:
205:             with self._condition:
206:                 self._record_failure()
207:         finally:
208:             with self._condition:
209:                 self._managers.discard(threading.current_thread())
210: 
211:     def _record_failure(self):
212:         now = time.monotonic()
213:         while self._failures and self._failures[0] < now - 300:
214:             self._failures.popleft()
215:         self._failures.append(now)
216:         if len(self._failures) >= 3:
217:             self._exhausted = True
218: 
219:     def _retire(self, worker):
220:         with self._condition:
221:             if self._workers[worker.slot] is not worker:
222:                 return
223:             self._workers[worker.slot] = None
224:             self._affinity = OrderedDict((key, slot) for key, slot in self._affinity.items() if slot != worker.slot)
225:             self._record_failure()
226:             restart = not self._closed and not self._exhausted
227:             if restart:
228:                 self._starting.add(worker.slot)
229:             self._condition.notify_all()
230:         _stop(worker)
231:         if restart:
232:             manager = threading.Thread(target=self._replace, args=(worker.slot,), daemon=True)
233:             with self._condition:
234:                 if self._closed:
235:                     self._starting.discard(worker.slot)
236:                     return
237:                 self._managers.add(manager)
238:                 manager.start()
239: 
240:     def _lease(self, key, acquire_deadline):
241:         from .service import ServiceError
242:         while True:
243:             stale = None
244:             with self._condition:
245:                 if self._closed:
246:                     raise ServiceError('Catalog query workers are closed', 'query_workers_unavailable', 503)
247:                 if time.monotonic() >= acquire_deadline:
248:                     raise ServiceError('Catalog query queue timed out', 'busy', 429)
249:                 for worker in self._workers:
250:                     if worker is not None and not worker.busy and not worker.process.is_alive():
251:                         worker.busy = True
252:                         stale = worker
253:                         break
254:                 if stale is None:
255:                     idle = [w for w in self._workers if w is not None and not w.busy]
256:                     if idle:
257:                         preferred = self._affinity.get(key)
258:                         worker = next((w for w in idle if w.slot == preferred), idle[0])
259:                         worker.busy = True
260:                         return worker
261:                     if not any(self._workers) and not self._starting:
262:                         raise ServiceError('Catalog query workers are unavailable', 'query_workers_unavailable', 503)
263:                     wait = acquire_deadline - time.monotonic()
264:                     if wait <= 0:
265:                         raise ServiceError('Catalog query queue timed out', 'busy', 429)
266:                     self._condition.wait(wait)
267:             if stale is not None:
268:                 self._retire(stale)
269: 
270:     def query(self, body, *, deadline, acquire_deadline):
271:         from .service import ServiceError

query_workers.py
337:             managers = list(self._managers)
338:             self._workers = [None] * len(self._workers)
339:             self._affinity.clear()
340:             self._condition.notify_all()
341:         for worker in workers:
342:             _stop(worker)
343:         for manager in managers:
344:             manager.join(.5)
345: 
346:     def __enter__(self):
347:         return self
348: 
349:     def __exit__(self, *args):
350:         self.close()

