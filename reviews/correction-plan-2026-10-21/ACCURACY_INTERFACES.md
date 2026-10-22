# Practical accuracy implementation interfaces (approved first option)

Additive version `catalog-accuracy-v1`; never reinterpret observation/summary/query-v1.
Codex owns `catalog/accuracy.py`, `anchors.py`, `refinement.py`, persistence,
query/service/UI migration, integration and BDS scheduling. Independent modules
below do not modify those files or native predictor. No live seed search/restart.

Shared context is an exact JSON object with keys `identity`, `dimension`,
`provider`, `observed_build`, `evidence_sha256`. `identity` is the existing validated
catalog observation identity, including full signed canonical seed and native/source
hashes. Dimension is overworld or nether. Providers: `procedural_model_v1`,
`bds_saved_runtime_v3`, `bds_script_api_v1`, `bds_locate_v1`,
`bds_feature_membership_v1`, `estimated_world_spawn_v1`, `observed_world_spawn_v1`.
Procedural/estimated have observed_build=null, others pinned `1.26.52.3`.
Evidence digest is a lowercase SHA256. Context never implies complete coverage.
`accuracy.validate_context(context)` validates and returns a defensive JSON copy.
`accuracy.context_id(context)` hashes the entire validated object. Different
providers/seed/settings/build/height/scope must not share negative proof caches.

## Chunk height provider ownership
Gemini owns only new `src/seed_search/catalog/biome_provider.py` and
`tests/catalog/test_biome_provider.py`. Public API:
`StoredBiomeProvider(context, records, *, names=None)`; context must be saved-runtime.
Records list of `{chunk_x:int, chunk_z:int, payload:bytes}` (<=256 records, <=1MiB
payload each, <=16MiB total); duplicates invalid. Decode using existing Data3D
floor -4/max25 OW, floor0/max8 Nether, existing sample_bedrock_runtime, never global
clamp, no procedural fallback. Names optional map strict uint32 int->canonical str,
no guessed ID namespace. `sample(x,y,z)` -> `{status:'observed'|'unknown', raw_id:
int|null, name:str|null, context_id:SHA, coordinate:[x,y,z], reason:str|null}`.
Y domain OW[-64,319],Nether[0,127]; negative chunk math must floor. Missing/unresolved
unknown. Explicit bytes copied on construction; caller mutations must not change
results. Any malformed input raises ValueError/TypeError. No disk/DB/BDS/API work.
Tests must cover variable per-chunk top, unknown interior, boundaries/negativeXZ,
wrong provider/build, namespace/no-name, duplicates/truncation/resource bounds.
Use only existing stdlib decoder and shared context, no native imports.

## Structure method registry ownership
Gemini owns only new `src/seed_search/catalog/structure_verification.py` and
`tests/catalog/test_structure_verification.py`. Build executable registry for ALL
21 supported OW/Nether types from original audit. Preserve predicted, navigation,
game-reported and point coordinates separately. Define explicit per-type routes
(exact locate type, grouped temple needing subtype witness, feature membership,
block/piece witness) with evidence scope and unresolved mechanisms. Registry must
not falsely activate unsupported methods or physical totals. Public API:
`verification_matrix()` -> defensive JSON list;
`assess_structure_evidence(structure_type, predicted:[x,z]|None, *, context,
reported:[x,z]|None=None, membership=None, subtype=None)` -> JSON with status,
raw_start, expected_reference, reported_reference, positive_type, physical_count
(always None), reason, context_id. `membership` is None or `{coordinate:[x,y,z],
types:[string,...]}` exact observed API names; unknown names never match fuzzily.
Use existing project_navigation_reference only for its pinned whitelist; other
exact reported==predicted is located reference, not count. Generic temple locate
never establishes subtype. Different/no locate never establishes absence. Point
membership is evidence of type at that point, cannot associate to a predicted
instance merely by proximity. No guessed stronghold/trial/trail/camp offsets.
Unsupported methods remain explicit unknown, not rejected seed. Match exact types
using known frozen evidence; document unproved mappings as unavailable. Tests
exercise all21 entries, wrong dimension/build/provider, grouped ambiguity, remote
membership not confirming a start, malformed/bool coords, no negative inference.
No BDS/native/source changes or network. No recursive workers/notification.

All workers High via bridge, <=480s/240CPU/1536MiB, exact allowlisted python3 pytest
command only through provided run-command wrapper. Codex independently checks
patches/tests. Do not change scopes to satisfy tests; report unresolved evidence.
