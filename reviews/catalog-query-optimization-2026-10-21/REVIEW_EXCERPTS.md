src/seed_search/catalog/index.py lines 54-85
54:     """Deserialize and validate a bitset hex string with strict length and reserved bit checks."""
55:     if not isinstance(hex_str, str):
56:         raise ValueError('Bitset must be a string')
57:     byte_len = (num_rows + 7) // 8
58:     expected_hex_len = byte_len * 2
59:     if len(hex_str) != expected_hex_len:
60:         raise ValueError(f'Bitset length mismatch: expected {expected_hex_len}, got {len(hex_str)}')
61:     if any(c not in '0123456789abcdef' for c in hex_str):
62:         raise ValueError('Bitset must be lowercase hex')
63:     val = int(hex_str, 16) if hex_str else 0
64:     if num_rows == 0:
65:         if val != 0:
66:             raise ValueError('Bitset for 0 rows must be 0')
67:     else:
68:         if val >= (1 << num_rows):
69:             raise ValueError(f'Reserved bits set: value exceeds {num_rows} bits')
70:     return val
71: 
72: 
73: def layout_descriptor(summary):
74:     """Derive deterministic metadata and 364-byte payload SHA for one layout."""
75:     meta = summary_metadata(summary)
76:     payload = pack_summary(summary)
77:     payload_sha256 = hashlib.sha256(payload).hexdigest()
78:     return {
79:         'metadata': meta,
80:         'payload_sha256': payload_sha256,
81:     }
82: 
83: 
84: def index_identity(layouts):
85:     """Derive canonical reusable content binding across layouts and revisions."""

src/seed_search/catalog/index.py lines 195-288
195:     }
196: 
197: 
198: def validate_index(index, *, layouts=None, trusted=False):
199:     """Validate index schema, bitlength, reserved bits, digests, and layout bindings."""
200:     if not isinstance(index, dict):
201:         raise ValueError('Index must be a dict')
202:     expected_keys = {'revision', 'num_rows', 'content_digest', 'index_digest', 'bitsets'}
203:     if set(index) != expected_keys:
204:         raise ValueError('Invalid index schema')
205:     if index['revision'] != INDEX_REVISION:
206:         raise ValueError('Invalid index revision')
207:     num_rows = index['num_rows']
208:     if type(num_rows) is not int or not 0 <= num_rows <= 256:
209:         raise ValueError('Invalid num_rows')
210:     for d_field in ('content_digest', 'index_digest'):
211:         val = index[d_field]
212:         if not isinstance(val, str) or len(val) != 64 or any(c not in '0123456789abcdef' for c in val):
213:             raise ValueError(f'Invalid {d_field}')
214: 
215:     # Independently verify index_digest
216:     body = {
217:         'bitsets': index['bitsets'],
218:         'content_digest': index['content_digest'],
219:         'num_rows': index['num_rows'],
220:         'revision': index['revision'],
221:     }
222:     if digest(body) != index['index_digest']:
223:         raise ValueError('Corrupt index: index_digest mismatch')
224: 
225:     # Validate bitsets container
226:     bitsets = index['bitsets']
227:     if not isinstance(bitsets, dict) or set(bitsets) != {'sides', 'origin', 'coverage', 'structure_thresholds', 'biome_witnesses'}:
228:         raise ValueError('Invalid bitsets container')
229: 
230:     # Sides
231:     sides = bitsets['sides']
232:     if not isinstance(sides, dict) or set(sides) != {str(s) for s in SIDES}:
233:         raise ValueError('Invalid sides in bitset')
234:     for s_str in sides:
235:         decode_bitset(sides[s_str], num_rows)
236: 
237:     # Origin
238:     decode_bitset(bitsets['origin'], num_rows)
239: 
240:     # Coverage
241:     cov = bitsets['coverage']
242:     if not isinstance(cov, dict) or set(cov) != set(FEATURE_IDS):
243:         raise ValueError('Invalid coverage in bitset')
244:     for feat_id in FEATURE_IDS:
245:         scopes = cov[feat_id]
246:         if not isinstance(scopes, list) or len(scopes) != 4:
247:             raise ValueError('Invalid coverage scopes in bitset')
248:         for h in scopes:
249:             decode_bitset(h, num_rows)
250: 
251:     # Structure thresholds
252:     st = bitsets['structure_thresholds']
253:     expected_struct_ids = {f['id'] for f in STRUCTURES}
254:     if not isinstance(st, dict) or set(st) != expected_struct_ids:
255:         raise ValueError('Invalid structure_thresholds in bitset')
256:     for feat_id in expected_struct_ids:
257:         scopes = st[feat_id]
258:         if not isinstance(scopes, list) or len(scopes) != 4:
259:             raise ValueError('Invalid structure scopes in bitset')
260:         for thresh_list in scopes:
261:             if not isinstance(thresh_list, list) or len(thresh_list) != 16:
262:                 raise ValueError('Invalid structure thresholds list')
263:             for h in thresh_list:
264:                 decode_bitset(h, num_rows)
265: 
266:     # Biome witnesses
267:     bw = bitsets['biome_witnesses']
268:     expected_biome_ids = {b['id'] for b in BIOMES}
269:     if not isinstance(bw, dict) or set(bw) != expected_biome_ids:
270:         raise ValueError('Invalid biome_witnesses in bitset')
271:     for feat_id in expected_biome_ids:
272:         scopes = bw[feat_id]
273:         if not isinstance(scopes, list) or len(scopes) != 4:
274:             raise ValueError('Invalid biome scopes in bitset')
275:         for h in scopes:
276:             decode_bitset(h, num_rows)
277: 
278:     if layouts is not None:
279:         if len(layouts) != num_rows:
280:             raise ValueError('Row count mismatch between layouts and index')
281:         expected_content_digest = index_identity(layouts)
282:         if index['content_digest'] != expected_content_digest:
283:             raise ValueError('Index content_digest mismatch with layouts')
284:         if not trusted:
285:             expected_index = build_index(layouts)
286:             if index['bitsets'] != expected_index['bitsets']:
287:                 raise ValueError('Tampered bitset in index')
288: 

src/seed_search/catalog/index.py lines 320-346
320:     """
321:     req=load_request(request) if isinstance(request,str) else validate_request(request)
322:     validate_index(index)
323:     return _select_index(index,req)
324: 
325: 
326: def _select_index(idx,req):
327:     N=idx['num_rows']
328:     if N == 0:
329:         return []
330: 
331:     mask = (1 << N) - 1
332: 
333:     # 1. Border side filtering
334:     req_side = req['border_side']
335:     side_hex = idx['bitsets']['sides'][str(req_side)]
336:     side_val = decode_bitset(side_hex, N)
337:     mask &= side_val
338:     if mask == 0:
339:         return []
340: 
341:     # 2. Anchor mode filtering
342:     if req['anchor_mode'] == 'origin':
343:         origin_hex = idx['bitsets']['origin']
344:         origin_val = decode_bitset(origin_hex, N)
345:         mask &= origin_val
346:         if mask == 0:

src/seed_search/catalog/segments.py lines 815-906
815: 
816:     def iter_segments(self, snapshot_id: str | None = None, *, request=None, layout_key=None):
817:         """Stream read leaf segments with fully validated summary dicts."""
818:         self._check_open()
819:         if layout_key is not None and (not isinstance(layout_key,tuple) or len(layout_key)!=2 or
820:             any(not isinstance(value,str) or not _HEX64_RE.fullmatch(value) for value in layout_key)):
821:             raise ValueError('Invalid exact layout key')
822:         resolved_info = self.info(snapshot_id)
823:         sid = resolved_info["snapshot_id"]
824: 
825:         leaf_rows=self._verified_membership(sid)
826:         obs_refs={r[0]:(r[1],r[2]) for r in self.conn.execute('SELECT world_id,observation_id,seed FROM observation_ref WHERE snapshot_id=?',(sid,))}
827:         seen=set()
828: 
829:         for seg_id, sha, rk, bl, ul, codec_name in leaf_rows:
830:             manifest = {
831:                 "sha256": sha,
832:                 "relative_key": rk,
833:                 "byte_length": bl,
834:                 "uncompressed_length": ul,
835:                 "codec": codec_name,
836:             }
837:             leaf_json = self.artifacts.get_json(manifest)
838:             if leaf_json.get("kind") != "leaf" or leaf_json.get("revision") != "catalog-segment-leaf-v1":
839:                 raise ValueError(f"Corrupt leaf manifest {seg_id}: invalid kind or revision")
840: 
841:             raw_layouts = leaf_json.get("layouts")
842:             if not isinstance(raw_layouts, list) or len(raw_layouts) > self.leaf_entries:
843:                 raise ValueError(f"Corrupt leaf manifest {seg_id}: invalid layout count")
844: 
845:             if len(registry.canonical_json(leaf_json))>1<<20 or leaf_json.get('layout_count')!=len(raw_layouts):
846:                 raise ValueError('Invalid leaf byte/count limit')
847:             index=None
848:             selected=range(len(raw_layouts))
849:             if leaf_json.get('index_manifest') is not None:
850:                 from .index import validate_index,filter_index,INDEX_REVISION
851:                 index=self.artifacts.get_json(leaf_json['index_manifest'])
852:                 validate_index(index)
853:                 # Recompute row ordering/content binding from saved metadata and
854:                 # payload hashes, without unpacking every nonmatching row.
855:                 entries=[dict(metadata={k:item[k] for k in ('revision','observation_id','world_id','layout_id','seed','anchor','border_side')},
856:                               payload_sha256=item['payload_sha256']) for item in raw_layouts]
857:                 expected=registry.digest(dict(geometry_revision=models.GEOMETRY_REVISION,index_revision=INDEX_REVISION,
858:                     layouts=entries,policy_revision=registry.digest(registry.POLICY),registry_revision=registry.REGISTRY_REVISION))
859:                 if index['content_digest']!=expected or index['num_rows']!=len(raw_layouts):raise ValueError('Leaf index row/content mismatch')
860:                 if request is not None:selected=filter_index(index,request)
861:             if layout_key is not None:
862:                 selected=[i for i in selected if (raw_layouts[i]['world_id'],raw_layouts[i]['layout_id'])==layout_key]
863:             decoded_layouts = []
864:             for position in selected:
865:                 item=raw_layouts[position]
866:                 if obs_refs.get(item['world_id'])!=(item['observation_id'],item['seed']):
867:                     raise ValueError('Layout/observation membership identity mismatch')
868:                 if models.world_id(dict(resolved_info['header'],seed=item['seed']))!=item['world_id']:
869:                     raise ValueError('Layout/build identity mismatch')
870:                 geometry_key=(item['world_id'],item['border_side'],*item['anchor'])
871:                 if geometry_key in seen:raise ValueError('Duplicate geometry across snapshot leaves')
872:                 seen.add(geometry_key)
873:                 b64_payload = item["payload_b64"]
874:                 try:
875:                     packed_blob = base64.b64decode(b64_payload,validate=True)
876:                 except Exception as exc:
877:                     raise ValueError(f"Corrupt layout base64 payload in {seg_id}: {exc}") from exc
878: 
879:                 if len(packed_blob) != 364:
880:                     raise ValueError(f"Corrupt layout blob length in {seg_id}: {len(packed_blob)}")
881:                 actual_sha = hashlib.sha256(packed_blob).hexdigest()
882:                 if actual_sha != item["payload_sha256"]:
883:                     raise ValueError(f"Corrupt layout payload sha in {seg_id}")
884: 
885:                 metadata = {
886:                     "revision": item["revision"],
887:                     "observation_id": item["observation_id"],
888:                     "world_id": item["world_id"],
889:                     "layout_id": item["layout_id"],
890:                     "seed": item["seed"],
891:                     "anchor": item["anchor"],
892:                     "border_side": item["border_side"],
893:                 }
894:                 if metadata["revision"] != models.SUMMARY_REVISION:
895:                     raise ValueError(f"Incompatible summary revision in layout {item['layout_id']}")
896: 
897:                 expected_lid = codec.layout_id(metadata["observation_id"], metadata["anchor"], metadata["border_side"])
898:                 if metadata["layout_id"] != expected_lid:
899:                     raise ValueError(f"Layout ID mismatch in {item['layout_id']}")
900: 
901:                 summary = codec.unpack_summary(packed_blob, metadata)
902:                 codec.validate_summary(summary)
903:                 decoded_layouts.append(summary)
904: 
905:             yield {"segment_id":seg_id,"layouts":decoded_layouts,"index":index,
906:                    "total_rows":len(raw_layouts),"prefiltered":request is not None and index is not None}

src/seed_search/catalog/codec.py lines 76-85
76: def unpack_summary(payload, metadata):
77:     if not isinstance(payload, bytes) or len(payload) != 364 or payload[-1] & 0xf0:
78:         raise ValueError('Invalid summary payload size/reserved bits')
79:     values = _NUMERIC.unpack(payload[:352])
80:     bits = int.from_bytes(payload[352:], 'little')
81:     result = dict(metadata, counts=[list(values[i:i+4]) for i in range(0, 56, 4)],
82:                   structure_nearest_d2=list(values[56:70]), biome_nearest_d2=list(values[70:79]),
83:                   biome_witness_refs=list(values[79:88]),
84:                   complete=[[bool(bits & (1 << (f*4+s))) for s in range(4)] for f in range(23)])
85:     return validate_summary(result)

src/seed_search/catalog/accuracy_query.py lines 60-94
60:         cached=service._cached_result(cache_key)
61:         if cached is not None:
62:             if cached['proof']!=proof:raise ServiceError('Snapshot membership changed','integrity_error',503)
63:             return _page(service,body,req,size,cached['ranked'],cached['matched'],cached['extra'],start,cached=True)
64:         by_layout={};provenance={};unavailable=0
65:         from .refined_witnesses import model_witnesses,apply_witnesses
66:         fine={};fine_rows={}
67:         def add_layout(layout):
68:             observation={'identity':dict(info['header'],seed=layout['seed'])}
69:             wid=layout['world_id']
70:             if wid not in fine:fine[wid]=model_witnesses(observation,bundle['tiles'])
71:             row,witnesses=apply_witnesses(layout,fine[wid])
72:             by_layout[row['layout_id']]=row;fine_rows[row['layout_id']]=witnesses
73:         if req['anchor_mode'] in ('origin','recommended'):
74:             baseline=dict(req,request_revision='catalog-query-v1',evidence_policy='predicted_observations_v1');baseline.pop('accuracy_generation')
75:             # Coarse biome indexes cannot prune newly recovered fine witnesses.
76:             # Keep structure predicates only in the coarse prefilter.
77:             baseline['rows']=[r for r in baseline['rows'] if r['kind']=='structure_count']
78:             for segment in store.iter_segments(sid,request=baseline):
79:                 if time.monotonic()-start>service.query_seconds:raise ServiceError('Accuracy query time allowance exhausted','query_timeout',503)
80:                 if not segment['layouts']:continue
81:                 for layout in segment['layouts']:
82:                     if layout['border_side']==req['border_side'] and (req['anchor_mode']!='origin' or layout['anchor']==[0,0]):
83:                         add_layout(layout)
84:         for entry in entries:
85:             if entry['anchor']['mode']!=req['anchor_mode']:continue
86:             for layout in entry['layouts']:
87:                 if layout['border_side']!=req['border_side']:continue
88:                 # Out-of-envelope layouts remain saved and can receive coverage
89:                 # later, but cannot rank as a complete user-selected world area.
90:                 box=bounds_for(layout['anchor'],layout['border_side'])
91:                 from .registry import ENVELOPE
92:                 if not (ENVELOPE[0]<=box[0] and ENVELOPE[1]<=box[1] and box[2]<=ENVELOPE[2] and box[3]<=ENVELOPE[3]):
93:                     unavailable+=1;continue
94:                 add_layout(layout);provenance[layout['layout_id']]=entry['anchor']

src/seed_search/catalog/accuracy_query.py lines 130-152
130: 
131: def _page(service,body,req,size,ranked,matched_worlds,extra,start,*,cached):
132:         from .service import ServiceError,EVIDENCE
133:         if time.monotonic()-start>service.query_seconds:raise ServiceError('Accuracy query time allowance exhausted','query_timeout',503)
134:         sid=req['catalog_snapshot_id'];request_sha=digest(req);cursor=service._decode(body['cursor']) if body.get('cursor') else None
135:         if cursor and (cursor['request']!=request_sha or cursor['snapshot']!=sid or cursor['size']!=size):
136:             raise ServiceError('Cursor belongs to another request','cursor_mismatch')
137:         offset=0
138:         if cursor:
139:             positions=[i for i,row in enumerate(ranked) if [str(v) for v in row['_sort_key']]==cursor['last']]
140:             if not positions:raise ServiceError('Page boundary unavailable','cursor_mismatch',409)
141:             offset=positions[0]+1
142:         page=[dict(r) for r in ranked[offset:offset+size]];next_cursor=None
143:         if offset+size<len(ranked):
144:             next_cursor=service._token(dict(snapshot=sid,request=request_sha,size=size,
145:                 last=[str(v) for v in page[-1]['_sort_key']],expires=cursor['expires'] if cursor else time.time()+3600))
146:         for row in page:row.pop('_sort_key')
147:         return dict(ok=True,snapshot_id=sid,request_sha256=request_sha,results=page,next_cursor=next_cursor,
148:             truncated=matched_worlds>1000,matched_worlds=matched_worlds,unavailable_layouts=extra['unavailable'],
149:             unresolved_worlds=extra['unresolved'],unresolved_candidates=extra['potential'],accuracy_generation=req['accuracy_generation'],
150:             evidence_label=EVIDENCE+' World-spawn coordinates do not establish player landing or safety.',
151:             stats=dict(wall_seconds=time.monotonic()-start,accuracy_layouts=extra['layouts'],result_cache_hit=cached))

src/seed_search/catalog/refined_witnesses.py lines 24-48
24: def apply_witnesses(layout,points):
25:     """Return a scoring copy and explicit witnesses; never invent absence/coverage."""
26:     import copy
27:     result=copy.deepcopy(layout);witnesses=[]
28:     lo_x,lo_z,hi_x,hi_z=bounds_for(layout['anchor'],layout['border_side']);cx,cz=layout['anchor']
29:     for feature in BIOMES:
30:         slot=feature['slot'];best=None
31:         for x,y,z,tile_id in points[feature['id']]:
32:             if lo_x<=x<hi_x and lo_z<=z<hi_z:
33:                 key=((x-cx)**2+(z-cz)**2,x,z,tile_id)
34:                 if best is None or key<best:best=key
35:         if best is not None and best[0]<result['biome_nearest_d2'][slot]:
36:             result['biome_nearest_d2'][slot]=best[0]
37:             # Keep coarse source references unchanged in persisted summaries.
38:             # This transient scoring copy's fine witness is served separately.
39:             result['biome_witness_refs'][slot]=MISSING
40:             witnesses.append(dict(feature=feature['id'],x=best[1],y=63,z=best[2],tile_id=best[3],distance_squared=best[0],provider='procedural_model_v1'))
41:     return result,witnesses
