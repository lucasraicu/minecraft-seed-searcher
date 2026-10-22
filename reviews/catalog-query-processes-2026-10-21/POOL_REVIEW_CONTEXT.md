Approved two-process plan, Codex implementation.10 actual spawn/IPC tests passed3.94s:1then2 workers, exact/cached/cursor/error contracts, blocked large IPC-write timeout, busy-workerSIGKILL no replay, restartexhaustion, wrong-jobreply, warmmembershipcorruption, IPC limits, actual HTTPparentSIGTERM/SIGKILL. Testdependencypsutil was absent; tests now use standardps and owned birth identity, no newdependency. Heavy500query acceptance pending. Review source alone, notworkerclaimedresults.

src/seed_search/catalog/service.py
47:         heapq.heappush(self.heap,_Worst(key,wid,self.version))
48:         if len(self.heap)>2*self.limit:
49:             self.heap=[_Worst(r['_sort_key'],w,v) for w,(v,r) in self.members.items()];heapq.heapify(self.heap)
50:     def results(self):return sorted((r for _,r in self.members.values()),key=lambda r:r['_sort_key'])
51: 
52: 
53: class CatalogService:
54:     def __init__(self,root=None,*,secret=None,query_seconds=10.,cache_bytes=64<<20,query_processes=0):
55:         self.root=root;self.secret=secret or secrets.token_bytes(32);self.query_seconds=query_seconds
56:         self.cache_bytes=cache_bytes//2;self.cache=OrderedDict();self.cache_size=0;self.cache_lock=threading.Lock()
57:         self.result_bytes=cache_bytes-self.cache_bytes;self.result_cache=OrderedDict();self.result_size=0
58:         self.admission=threading.BoundedSemaphore(4);self.execution=threading.BoundedSemaphore(2)
59:         self.query_workers=None
60:         if query_processes:
61:             from .query_workers import QueryWorkerPool
62:             self.query_workers=QueryWorkerPool(root,secret=self.secret,workers=query_processes,
63:                 query_seconds=query_seconds,cache_bytes=cache_bytes)
64: 
65:     def close(self):
66:         if self.query_workers is not None:self.query_workers.close()
67: 
68:     @contextmanager
69:     def _store(self):
70:         if self.root is None:raise ServiceError('Catalog root is not configured','unavailable',503)
71:         from pathlib import Path
72:         if not (Path(self.root)/'pilot.sqlite').is_file():
73:             raise ServiceError('Catalog has not been imported','unavailable',503)
74:         from .segments import SegmentedCatalog
75:         with SegmentedCatalog(self.root) as store:yield store
76: 
77:     @contextmanager
78:     def _slot(self,wait_seconds=2):
79:         if not self.admission.acquire(blocking=False):raise ServiceError('Catalog is busy; try again','busy',429)
80:         acquired=False
81:         try:
82:             acquired=self.execution.acquire(timeout=wait_seconds)
83:             if not acquired:raise ServiceError('Catalog query queue timed out','busy',429)
84:             yield
85:         finally:
86:             if acquired:self.execution.release()
87:             self.admission.release()
88: 
89:     def status(self):
90:         try:
91:             with self._store() as store:
92:                 result=dict(ok=True,available=True,**store.info())
93:                 if self.query_workers is not None:result['query_workers']=self.query_workers.status()
94:                 return result
95:         except ServiceError as exc:return dict(ok=True,available=False,reason=str(exc))
96: 
97:     def _accuracy(self, snapshot_id):

src/seed_search/catalog/service.py
222:             self.result_cache[key]=(blob,time.monotonic()+3600);self.result_size+=len(blob)
223:             while len(self.result_cache)>8 or self.result_size>self.result_bytes:
224:                 _,(removed,_)=self.result_cache.popitem(last=False);self.result_size-=len(removed)
225: 
226:     def query(self,body):
227:         if self.query_workers is not None:
228:             start=time.monotonic();deadline=start+self.query_seconds
229:             with self._slot(wait_seconds=min(2,self.query_seconds)):
230:                 return self.query_workers.query(body,deadline=deadline,acquire_deadline=min(start+2,deadline))
231:         if isinstance(body,dict) and isinstance(body.get('request'),dict) and body['request'].get('request_revision')=='catalog-query-accuracy-v1':
232:             from .accuracy_query import query
233:             return query(self,body)
234:         if not isinstance(body,dict) or set(body)-{'request','page_size','cursor'} or 'request' not in body:
235:             raise ServiceError('Expected request, optional page_size and cursor')

src/seed_search/catalog/http_server.py
48:     catalog=CatalogService(args.root,query_processes=args.query_processes)
49:     previous=None
50:     def stop(*_):raise KeyboardInterrupt
51:     if threading.current_thread() is threading.main_thread():
52:         previous=signal.signal(signal.SIGTERM,stop)
53:     try:
54:         with ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(catalog)) as server:
55:             server.daemon_threads=True
56:             print(f'Private Catalog backend http://127.0.0.1:{server.server_port}',flush=True)
57:             try:server.serve_forever()
58:             except KeyboardInterrupt:pass
59:     finally:
60:         catalog.close()
61:         if previous is not None:signal.signal(signal.SIGTERM,previous)
62: 
63: 
64: if __name__=='__main__':main()

