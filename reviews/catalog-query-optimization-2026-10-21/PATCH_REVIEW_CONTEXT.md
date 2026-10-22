Approved plan implemented, no native/frontend/schema/score/admission/timeout changes. Codex independently ran118 focused regression tests in52.72s, all pass. Matched benchmarks and full frozen-code oracle running, so no speedup/capacity claim yet. Current scorer creates candidate dictionaries; it never mutates input layouts. Empty fast path uses dict(layout), nested read-only vectors; shared public apply_witnesses keeps deepcopy.

src/seed_search/catalog/codec.py
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

src/seed_search/catalog/index.py
320:     entry point validates index schema/digest/bit lengths but has no raw layouts
321:     to independently rederive semantics; untrusted callers use candidate_indices.
322:     """
323:     req=load_request(request) if isinstance(request,str) else validate_request(request)
324:     validate_index(index)
325:     return _select_index(index,req)
326: 
327: 
328: def _select_index(idx,req):
329:     N=idx['num_rows']
330:     if N == 0:
331:         return []
332: 
333:     mask = (1 << N) - 1
334: 
335:     # 1. Border side filtering
336:     req_side = req['border_side']
337:     side_hex = idx['bitsets']['sides'][str(req_side)]
338:     side_val = decode_bitset(side_hex, N)
339:     mask &= side_val
340:     if mask == 0:
341:         return []
342: 
343:     # 2. Anchor mode filtering
344:     if req['anchor_mode'] == 'origin':
345:         origin_hex = idx['bitsets']['origin']
346:         origin_val = decode_bitset(origin_hex, N)

src/seed_search/catalog/query.py
273:         unsigned_seed = int(layout['seed']) & ((1 << 64) - 1)
274:         sort_key = (
275:             -total_units,
276:             distance_tie,
277:             unsigned_seed,
278:             layout['anchor'][0],
279:             layout['anchor'][1],
280:             layout['layout_id'],
281:         )
282: 
283:         candidate = {
284:             'world_id': layout['world_id'],
285:             'seed': layout['seed'],
286:             'layout_id': layout['layout_id'],
287:             'anchor': list(layout['anchor']),
288:             'border_side': layout['border_side'],
289:             'score': score,
290:             'utility_units': int(total_units),
291:             'distance_tie': distance_tie,
292:             'contributions': contributions,
293:             '_sort_key': sort_key,
294:         }
295:         candidate_layouts.append(candidate)
296: 
297:     # Group best layout by world BEFORE applying Top-K limit
298:     best_by_world = {}
299:     for cand in candidate_layouts:
300:         wid = cand['world_id']
301:         if wid not in best_by_world or cand['_sort_key'] < best_by_world[wid]['_sort_key']:
302:             best_by_world[wid] = cand
303: 
304:     ranked = sorted(best_by_world.values(), key=lambda c: c['_sort_key'])
305:     results = ranked[:limit]
306:     if not keep_keys:
307:         for r in results:
308:             r.pop('_sort_key', None)
309:     return results

src/seed_search/catalog/accuracy_query.py
63:             return _page(service,body,req,size,cached['ranked'],cached['matched'],cached['extra'],start,cached=True)
64:         by_layout={};provenance={};unavailable=0
65:         from .refined_witnesses import model_witnesses,apply_witnesses
66:         fine={};fine_rows={}
67:         def add_layout(layout):
68:             observation={'identity':dict(info['header'],seed=layout['seed'])}
69:             wid=layout['world_id']
70:             if wid not in fine:fine[wid]=model_witnesses(observation,bundle['tiles'])
71:             if any(fine[wid].values()):
72:                 row,witnesses=apply_witnesses(layout,fine[wid])
73:             else:
74:                 # Query-local rows remain read-only during scoring. Isolate the
75:                 # top-level mapping without copying unused nested inventories.
76:                 row,witnesses=dict(layout),[]
77:             by_layout[row['layout_id']]=row;fine_rows[row['layout_id']]=witnesses
78:         if req['anchor_mode'] in ('origin','recommended'):
79:             baseline=dict(req,request_revision='catalog-query-v1',evidence_policy='predicted_observations_v1');baseline.pop('accuracy_generation')
80:             # Coarse biome indexes cannot prune newly recovered fine witnesses.
81:             # Keep structure predicates only in the coarse prefilter.
82:             baseline['rows']=[r for r in baseline['rows'] if r['kind']=='structure_count']
83:             for segment in store.iter_segments(sid,request=baseline):

