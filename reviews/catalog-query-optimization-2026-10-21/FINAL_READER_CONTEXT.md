NARROW FINAL READER REVIEW. All original3files remain scoped. First patch exactness passed but2coldconcurrent queries timedout. No timeout/admission/score/data change. New changes in updated PATCH: request-local seed->worldID derivation reuse AFTER membership checking, still compare each row; remove outer layoutID derivation because unpack_summary->validate_summary alreadychecks it. No shared/persistent trust cache. Check adversarial member/header/ID/legacy behavior, not speedup promises.

src/seed_search/catalog/codec.py
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

src/seed_search/catalog/segments.py
816:     def iter_segments(self, snapshot_id: str | None = None, *, request=None, layout_key=None):
817:         """Stream read leaf segments with fully validated summary dicts."""
818:         self._check_open()
819:         if request is not None:
820:             from .request import load_request, validate_request
821:             request = load_request(request) if isinstance(request, str) else validate_request(request)
822:         if layout_key is not None and (not isinstance(layout_key,tuple) or len(layout_key)!=2 or
823:             any(not isinstance(value,str) or not _HEX64_RE.fullmatch(value) for value in layout_key)):
824:             raise ValueError('Invalid exact layout key')
825:         resolved_info = self.info(snapshot_id)
826:         sid = resolved_info["snapshot_id"]
827: 
828:         leaf_rows=self._verified_membership(sid)
829:         obs_refs={r[0]:(r[1],r[2]) for r in self.conn.execute('SELECT world_id,observation_id,seed FROM observation_ref WHERE snapshot_id=?',(sid,))}
830:         seen=set()
831:         world_ids_by_seed={}
832: 
833:         for seg_id, sha, rk, bl, ul, codec_name in leaf_rows:
834:             manifest = {
835:                 "sha256": sha,
836:                 "relative_key": rk,
837:                 "byte_length": bl,
838:                 "uncompressed_length": ul,

src/seed_search/catalog/segments.py
862:                     layouts=entries,policy_revision=registry.digest(registry.POLICY),registry_revision=registry.REGISTRY_REVISION))
863:                 if index['content_digest']!=expected or index['num_rows']!=len(raw_layouts):raise ValueError('Leaf index row/content mismatch')
864:                 # The index and request are already fully validated here. Public
865:                 # filter_index keeps its independent validation boundary.
866:                 if request is not None:selected=_select_index(index,request)
867:             if layout_key is not None:
868:                 selected=[i for i in selected if (raw_layouts[i]['world_id'],raw_layouts[i]['layout_id'])==layout_key]
869:             decoded_layouts = []
870:             for position in selected:
871:                 item=raw_layouts[position]
872:                 if obs_refs.get(item['world_id'])!=(item['observation_id'],item['seed']):
873:                     raise ValueError('Layout/observation membership identity mismatch')
874:                 # The header is fixed for this iterator. Reuse only its derived
875:                 # world identity for identical, membership-checked seed strings.
876:                 seed=item['seed']
877:                 if seed not in world_ids_by_seed:
878:                     world_ids_by_seed[seed]=models.world_id(dict(resolved_info['header'],seed=seed))
879:                 if world_ids_by_seed[seed]!=item['world_id']:
880:                     raise ValueError('Layout/build identity mismatch')
881:                 geometry_key=(item['world_id'],item['border_side'],*item['anchor'])
882:                 if geometry_key in seen:raise ValueError('Duplicate geometry across snapshot leaves')
883:                 seen.add(geometry_key)
884:                 b64_payload = item["payload_b64"]
885:                 try:
886:                     packed_blob = base64.b64decode(b64_payload,validate=True)
887:                 except Exception as exc:
888:                     raise ValueError(f"Corrupt layout base64 payload in {seg_id}: {exc}") from exc
889: 
890:                 if len(packed_blob) != 364:
891:                     raise ValueError(f"Corrupt layout blob length in {seg_id}: {len(packed_blob)}")
892:                 actual_sha = hashlib.sha256(packed_blob).hexdigest()
893:                 if actual_sha != item["payload_sha256"]:
894:                     raise ValueError(f"Corrupt layout payload sha in {seg_id}")
895: 
896:                 metadata = {
897:                     "revision": item["revision"],
898:                     "observation_id": item["observation_id"],
899:                     "world_id": item["world_id"],
900:                     "layout_id": item["layout_id"],
901:                     "seed": item["seed"],
902:                     "anchor": item["anchor"],
903:                     "border_side": item["border_side"],
904:                 }
905:                 if metadata["revision"] != models.SUMMARY_REVISION:
906:                     raise ValueError(f"Incompatible summary revision in layout {item['layout_id']}")
907: 
908:                 summary = codec.unpack_summary(packed_blob, metadata)
909:                 # unpack_summary validates the schema, numeric payload and the
910:                 # layout ID derived from observation, anchor and border side.
911:                 decoded_layouts.append(summary)
912: 
913:             yield {"segment_id":seg_id,"layouts":decoded_layouts,"index":index,
914:                    "total_rows":len(raw_layouts),"prefiltered":request is not None and index is not None}
915: 
916:     def identities(self, snapshot_id: str | None = None) -> list[dict]:
917:         """Derive pinned manifest metadata for all worlds in canonical order."""
918:         self._check_open()
919:         resolved_info = self.info(snapshot_id)
920:         sid = resolved_info["snapshot_id"]

