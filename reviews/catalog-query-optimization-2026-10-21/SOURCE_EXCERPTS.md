src/seed_search/catalog/index.py lines 35-90
35: ]
36: 
37: 
38: def encode_bitset(val, num_rows):
39:     """Serialize a bitset integer of length num_rows into canonical lowercase hex."""
40:     if not isinstance(val, int) or val < 0:
41:         raise ValueError('Invalid bitset integer')
42:     if num_rows == 0:
43:         if val != 0:
44:             raise ValueError('Bitset for 0 rows must be 0')
45:         return ""
46:     if val >= (1 << num_rows):
47:         raise ValueError('Bitset value exceeds declared row capacity')
48:     byte_len = (num_rows + 7) // 8
49:     hex_len = byte_len * 2
50:     return f"{val:0{hex_len}x}"
51: 
52: 
53: def decode_bitset(hex_str, num_rows):
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
86:     if not isinstance(layouts, (list, tuple)):
87:         layouts = list(layouts)
88:     if len(layouts) > 256:
89:         raise ValueError('At most 256 layouts')
90:     entries = [layout_descriptor(l) for l in layouts]

src/seed_search/catalog/index.py lines 195-290
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
289:     return True
290: 

src/seed_search/catalog/index.py lines 317-346
317:     Integrity and content provenance are verified by the segment reader. This
318:     entry point validates index schema/digest/bit lengths but has no raw layouts
319:     to independently rederive semantics; untrusted callers use candidate_indices.
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

src/seed_search/catalog/segments.py lines 811-907
811:                 "worlds": row[1],
812:                 "layouts": row[2],
813:                 "header": json.loads(row[3]),
814:             }
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
907: 

src/seed_search/catalog/codec.py lines 15-85
15: def validate_summary(summary):
16:     expected = {'revision', 'observation_id', 'world_id', 'layout_id', 'seed', 'anchor',
17:                 'border_side', 'counts', 'structure_nearest_d2', 'biome_nearest_d2',
18:                 'biome_witness_refs', 'complete'}
19:     if not isinstance(summary, dict) or set(summary) != expected or summary['revision'] != SUMMARY_REVISION:
20:         raise ValueError('Invalid summary schema')
21:     from ..seeds import parse_seed
22:     if not isinstance(summary['seed'], str) or summary['seed'] != str(parse_seed(summary['seed'])):
23:         raise ValueError('Invalid summary seed')
24:     if not isinstance(summary['anchor'], list) or tuple(summary['anchor']) not in anchors():
25:         raise ValueError('Unsupported anchor')
26:     bounds_for(summary['anchor'], summary['border_side'])
27:     for field in ('observation_id', 'world_id', 'layout_id'):
28:         v = summary[field]
29:         if not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v):
30:             raise ValueError('Invalid summary identity')
31:     if summary['layout_id'] != layout_id(summary['observation_id'], summary['anchor'], summary['border_side']):
32:         raise ValueError('Layout identity mismatch')
33:     validate_summary_numbers(summary)
34:     return summary
35: 
36: 
37: def validate_summary_numbers(summary):
38:     """Validate numeric payload only, independent of versioned anchor geometry."""
39:     if not isinstance(summary['counts'], list) or len(summary['counts']) != 14:
40:         raise ValueError('Invalid count matrix')
41:     for row in summary['counts']:
42:         if not isinstance(row, list) or len(row) != 4:
43:             raise ValueError('Invalid count scopes')
44:         for v in row:
45:             integer(v, 0, MISSING)
46:         if row != sorted(row):
47:             raise ValueError('Counts must increase with nested scopes')
48:     for field, n in (('structure_nearest_d2', 14), ('biome_nearest_d2', 9), ('biome_witness_refs', 9)):
49:         values = summary[field]
50:         if not isinstance(values, list) or len(values) != n:
51:             raise ValueError('Invalid distance/witness vector')
52:         for v in values:
53:             integer(v, 0, MISSING)
54:     if not isinstance(summary['complete'], list) or len(summary['complete']) != len(FEATURE_IDS):
55:         raise ValueError('Invalid completion matrix')
56:     for row in summary['complete']:
57:         if not isinstance(row, list) or len(row) != 4 or any(type(v) is not bool for v in row):
58:             raise ValueError('Invalid completion flags')
59:     return summary
60: 
61: 
62: def pack_summary(summary):
63:     validate_summary(summary)
64:     nums = [v for row in summary['counts'] for v in row]
65:     for key in ('structure_nearest_d2', 'biome_nearest_d2', 'biome_witness_refs'):
66:         nums.extend(summary[key])
67:     bits = sum(int(v) << i for i, v in enumerate(v for row in summary['complete'] for v in row))
68:     return _NUMERIC.pack(*nums) + bits.to_bytes(12, 'little')
69: 
70: 
71: def summary_metadata(summary):
72:     validate_summary(summary)
73:     return {k: summary[k] for k in ('revision', 'observation_id', 'world_id', 'layout_id', 'seed', 'anchor', 'border_side')}
74: 
75: 
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

src/seed_search/catalog/accuracy_query.py lines 50-120
50:     with service._slot(),service._store() as store:
51:         req=validate_accuracy_request(body['request']);sid=req['catalog_snapshot_id'];info=store.info(sid)
52:         if info['worlds']>2000:raise ServiceError('Accuracy query cohort cap exceeded','capacity_limit',503)
53:         req=validate_accuracy_request(req,snapshot_id=sid,game_build_id=info['header']['game_build_id'],world_settings_id=info['header']['world_settings_id'])
54:         try:bundle=_bound_bundle(store,sid,req['accuracy_generation'])
55:         except FileNotFoundError:raise ServiceError('Pinned accuracy generation is unavailable','accuracy_unavailable',409) from None
56:         except (ValueError,KeyError,TypeError,OSError):raise ServiceError('Accuracy generation failed integrity validation','integrity_error',503) from None
57:         entries=bundle['anchors']
58:         cache_key=digest(['accuracy-query',req])
59:         proof=digest([req['accuracy_generation'],store.conn.execute('SELECT world_id,observation_id,seed,manifest_sha256 FROM observation_ref WHERE snapshot_id=? ORDER BY world_id',(sid,)).fetchall()])
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
95:         scoring=dict(req,anchor_mode=req['anchor_mode'] if req['anchor_mode'] in ('origin','recommended') else 'recommended',request_revision='catalog-query-v1');scoring.pop('accuracy_generation')
96:         ranked=_rank(list(by_layout.values()),scoring,4000,validate_records=False,keep_keys=True,positive_witnesses=True)
97:         matched_ids={r['world_id'] for r in ranked}
98:         from .query import STRUCTURE_SLOTS,BIOME_SLOTS,RADII_MAP
99:         from .codec import MISSING
100:         potential={}
101:         for layout in by_layout.values():
102:             unknown=False;impossible=False
103:             for predicate in req['rows']:
104:                 if predicate['rule']!='required':continue
105:                 scope=predicate['scope'];slot=3 if scope['kind']=='inside_border' else RADII_MAP[scope['radius']]
106:                 if predicate['kind']=='structure_count':
107:                     feature=STRUCTURE_SLOTS[predicate['feature']]
108:                     if not layout['complete'][feature][slot]:unknown=True
109:                     elif layout['counts'][feature][slot]<predicate['at_least']:
110:                         impossible=True;break
111:                 else:
112:                     radius=None if scope['kind']=='inside_border' else scope['radius']
113:                     present=any(layout['biome_nearest_d2'][BIOME_SLOTS[f]]!=MISSING and
114:                         (radius is None or layout['biome_nearest_d2'][BIOME_SLOTS[f]]<=radius*radius) for f in predicate['any_of'])
115:                     # No sparse witness is UNKNOWN, even if its lattice was
116:                     # fully evaluated. No seed is removed from catalog retention.
117:                     if not present or not all(layout['complete'][14+BIOME_SLOTS[f]][slot] for f in predicate['any_of']):unknown=True
118:             if unknown and not impossible and layout['world_id']not in matched_ids:
119:                 potential.setdefault(layout['world_id'],dict(world_id=layout['world_id'],seed=layout['seed'],layout_id=layout['layout_id'],anchor=layout['anchor'],border_side=layout['border_side'],status='unresolved',reason='Required evidence is incomplete; this is not a matching result or a rejected seed'))
120:         matched_worlds=len(ranked);ranked=ranked[:1000]

src/seed_search/catalog/refined_witnesses.py lines 24-55
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
