CURRENT SOURCE AND ACTUAL EVIDENCE. Approved three-file optimization implemented; no worker-pool implementation. All18single cases<10s/exact. One8burstpassed but deterministic previous-failed pair5and10 and broadpair3and15 each yield2x503. Parent admission2active/4admitted and2s queue wait; deadline10s must notchange. Review multiprocessing proposal neutrally against alternatives; no approval yet.

src/seed_search/catalog/service.py
45:             del self.members[heapq.heappop(self.heap).wid]
46:         self.version+=1;self.members[wid]=(self.version,result)
47:         heapq.heappush(self.heap,_Worst(key,wid,self.version))
48:         if len(self.heap)>2*self.limit:
49:             self.heap=[_Worst(r['_sort_key'],w,v) for w,(v,r) in self.members.items()];heapq.heapify(self.heap)
50:     def results(self):return sorted((r for _,r in self.members.values()),key=lambda r:r['_sort_key'])
51: 
52: 
53: class CatalogService:
54:     def __init__(self,root=None,*,secret=None,query_seconds=10.,cache_bytes=64<<20):
55:         self.root=root;self.secret=secret or secrets.token_bytes(32);self.query_seconds=query_seconds
56:         self.cache_bytes=cache_bytes//2;self.cache=OrderedDict();self.cache_size=0;self.cache_lock=threading.Lock()
57:         self.result_bytes=cache_bytes-self.cache_bytes;self.result_cache=OrderedDict();self.result_size=0
58:         self.admission=threading.BoundedSemaphore(4);self.execution=threading.BoundedSemaphore(2)
59: 
60:     @contextmanager
61:     def _store(self):
62:         if self.root is None:raise ServiceError('Catalog root is not configured','unavailable',503)
63:         from pathlib import Path
64:         if not (Path(self.root)/'pilot.sqlite').is_file():
65:             raise ServiceError('Catalog has not been imported','unavailable',503)
66:         from .segments import SegmentedCatalog
67:         with SegmentedCatalog(self.root) as store:yield store
68: 
69:     @contextmanager
70:     def _slot(self):
71:         if not self.admission.acquire(blocking=False):raise ServiceError('Catalog is busy; try again','busy',429)
72:         acquired=False
73:         try:
74:             acquired=self.execution.acquire(timeout=2)
75:             if not acquired:raise ServiceError('Catalog query queue timed out','busy',429)
76:             yield
77:         finally:
78:             if acquired:self.execution.release()
79:             self.admission.release()
80: 
81:     def status(self):

src/seed_search/catalog/service.py
190:                 self.cache[key]=(index,size);self.cache_size+=size
191:                 while self.cache_size>self.cache_bytes:
192:                     _,(_,n)=self.cache.popitem(last=False);self.cache_size-=n
193:         return index,False
194: 
195:     def _cached_result(self,key):
196:         with self.cache_lock:
197:             found=self.result_cache.pop(key,None)
198:             if found is None:return None
199:             blob,expires=found
200:             if time.monotonic()>expires:self.result_size-=len(blob);return None
201:             self.result_cache[key]=found
202:         return json.loads(blob)
203: 
204:     def _save_result(self,key,ranked,matched,proof,extra=None):
205:         # Store immutable JSON bytes; page responses cannot mutate future pages.
206:         blob=canonical_json(dict(ranked=[dict(row,_sort_key=[str(v) for v in row['_sort_key']]) for row in ranked],matched=matched,proof=proof,**({'extra':extra} if extra is not None else {})))
207:         if len(blob)>self.result_bytes:return
208:         with self.cache_lock:
209:             old=self.result_cache.pop(key,None)
210:             if old:self.result_size-=len(old[0])
211:             self.result_cache[key]=(blob,time.monotonic()+3600);self.result_size+=len(blob)
212:             while len(self.result_cache)>8 or self.result_size>self.result_bytes:
213:                 _,(removed,_)=self.result_cache.popitem(last=False);self.result_size-=len(removed)
214: 
215:     def query(self,body):
216:         if isinstance(body,dict) and isinstance(body.get('request'),dict) and body['request'].get('request_revision')=='catalog-query-accuracy-v1':
217:             from .accuracy_query import query
218:             return query(self,body)
219:         if not isinstance(body,dict) or set(body)-{'request','page_size','cursor'} or 'request' not in body:
220:             raise ServiceError('Expected request, optional page_size and cursor')
221:         size=body.get('page_size',20)
222:         if type(size) is not int or not 1<=size<=50:raise ServiceError('page_size must be 1..50')
223:         start=time.monotonic();deadline=start+self.query_seconds
224:         def check():
225:             if time.monotonic()>deadline:raise ServiceError('Catalog query exceeded its time allowance','query_timeout',503)
226:         with self._slot(),self._store() as store:
227:             req=validate_request(body['request']);info=store.info(req['catalog_snapshot_id']);header=info['header']
228:             req=validate_request(req,snapshot_id=info['snapshot_id'],game_build_id=header['game_build_id'],world_settings_id=header['world_settings_id'])
229:             request_sha=digest(req);cursor=self._decode(body['cursor']) if body.get('cursor') else None
230:             if cursor and (cursor['request']!=request_sha or cursor['snapshot']!=info['snapshot_id'] or cursor['size']!=size):
231:                 raise ServiceError('Cursor belongs to another request or snapshot','cursor_mismatch')
232:             check();key=digest([info['snapshot_id'],request_sha])
233:             proof=digest(store.conn.execute('SELECT world_id,observation_id,seed,manifest_sha256 FROM observation_ref WHERE snapshot_id=? ORDER BY world_id',(info['snapshot_id'],)).fetchall())
234:             cached=self._cached_result(key);segments=decoded=eligible=cache_hits=0
235:             if cached is not None:
236:                 store._verified_membership(info['snapshot_id']);check()
237:                 if cached['proof']!=proof:raise ServiceError('Snapshot observation membership changed','integrity_error',503)
238:                 ranked=cached['ranked'];matched_count=cached['matched']

src/seed_search/catalog/service.py
239:             else:
240:                 from .index import candidate_indices
241:                 collector=TopWorlds();matched=set()
242:                 for segment in store.iter_segments(info['snapshot_id'],request=req):
243:                     check();rows=segment['layouts'];segments+=1;decoded+=len(rows)
244:                     index=segment.get('index')
245:                     if index is None:
246:                         index,hit=self._cached_index(rows)
247:                     else:hit=True
248:                     cache_hits+=int(hit)
249:                     indices=list(range(len(rows))) if segment.get('prefiltered') else candidate_indices(rows,req,index=index,trusted=True)
250:                     eligible+=len(indices)
251:                     by_layout={r['layout_id']:r for r in rows}
252:                     for result in _rank([rows[i] for i in indices],req,1000,validate_records=False,keep_keys=True):
253:                         check();matched.add(result['world_id']);layout=by_layout[result['layout_id']]
254:                         for field in ('counts','structure_nearest_d2','biome_nearest_d2','complete'):result[field]=layout[field]
255:                         result['bounds']=list(bounds_for(layout['anchor'],layout['border_side']));collector.offer(result)
256:                 ranked=collector.results();matched_count=len(matched)
257:                 self._save_result(key,ranked,matched_count,proof)
258:             check();offset=0
259:             if cursor:
260:                 # Canonical rank serialized as decimal text; reranking compares the
261:                 # exact original tuple, including deterministic50-digit profile H.
262:                 last=cursor['last']
263:                 matches=[i for i,r in enumerate(ranked) if [str(v) for v in r['_sort_key']]==last]
264:                 if not matches:raise ServiceError('Saved page boundary is unavailable','cursor_mismatch',409)
265:                 offset=matches[0]+1
266:             page=ranked[offset:offset+size];next_cursor=None
267:             if offset+size<len(ranked):
268:                 next_cursor=self._token(dict(snapshot=info['snapshot_id'],request=request_sha,size=size,
269:                     last=[str(v) for v in page[-1]['_sort_key']],expires=cursor['expires'] if cursor else time.time()+3600))
270:             for row in page:row.pop('_sort_key')
271:             return dict(ok=True,snapshot_id=info['snapshot_id'],request_sha256=request_sha,results=page,
272:                 next_cursor=next_cursor,truncated=matched_count>1000,matched_worlds=matched_count,
273:                 stats=dict(segments=segments,decoded_layouts=decoded,eligible_layouts=eligible,index_cache_hits=cache_hits,
274:                     result_cache_hit=cached is not None,wall_seconds=time.monotonic()-start),evidence_label=EVIDENCE)
275: 
276:     def biome_scope(self,body):

src/seed_search/catalog/http_server.py
48:         except KeyboardInterrupt:pass
49: 
50: 
51: if __name__=='__main__':main()

Exact admitted-pair observations:
[
  {
    "case": "previous_failed_admitted_pair",
    "requests": [
      {
        "query_id": 5,
        "status": 503,
        "seconds": 10.039695132058114,
        "code": "query_timeout"
      },
      {
        "query_id": 10,
        "status": 503,
        "seconds": 10.013279389007948,
        "code": "query_timeout"
      }
    ],
    "passed": false,
    "query_seconds": 10,
    "execution_limit": 2
  },
  {
    "case": "two_broad_recommended",
    "requests": [
      {
        "query_id": 3,
        "status": 503,
        "seconds": 10.034933864022605,
        "code": "query_timeout"
      },
      {
        "query_id": 15,
        "status": 503,
        "seconds": 10.037903412943706,
        "code": "query_timeout"
      }
    ],
    "passed": false,
    "query_seconds": 10,
    "execution_limit": 2
  }
]
