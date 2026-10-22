# Frozen additive interfaces — approved public automation

Owner Codex. Scope approved by user2026-10-21 through the active implementation
goal. Use PUBLIC_CATALOG_AUTOMATION_PLAN.md; do not invent terrain/BDS guarantees.
v1 model/registry/codec hashes and functions retain existing behavior.

## Observation functions (worker A)

Append to existing models.py, leaving v1 validation and identity unchanged:

`empty_observation_v2(identity)` and `validate_observation_v2(obs)`.
V2 identity is the existing validated v1 world/build identity, not relabeled slot
metadata; additive obs revision is `catalog-observation-v2` and `registry_revision`
is REGISTRY_REVISION_V2. World ID stays existing world_id(identity).

Exact fields:
```
revision, registry_revision, identity,
bounds: {overworld:[loX,loZ,hiX,hiZ],nether:[...]},
structures: {structure.feature:[[x,z],...]},
biomes: {overworld:[[x,y,z,raw_id],...],nether:[...]},
biome_names: {canonical_raw_id_string:canonical_name},
coverage: {feature_id:{status:unknown|partial|complete|failed,bounds:[...],method_id:str}},
anchors: [{mode:origin|recommended|world_spawn_estimated|world_spawn_observed,
           coordinate:[x,z],source_id:64hex}],
realm: null | JSON object,
metrics: {}, errors:{}
```
Require exact schema and valid finite JSON; no duplicate positions per dimension,
feature, or biome XYZ; bounded worldcoords ±30million, Y OW[-64,319]/Nether[0,127].
Max200000 starts/type,200000 total biome points/dimension. Empty default bounds
OW[-5120,-5120,5120,5120], Nether[-640,-640,640,640]. Coverage inside dimension
bounds. Names map raw IDs0..65535; incomplete name mapping cannot claim complete
biome coverage. Complete structures must have an inventory (empty is permitted).
An anchor source hash binds its provider/context; estimated != observed.

Append to extract.py:
`extract_observation_v2(identity, backend, *, name_for_id, previous=None,
                         anchors=(), bounds=None, on_progress=None)`.
Backend signatures: structures(name,inclusive_box,viable=True),
biome_points(xyz,dimension=0|-1). Scan15 OW structures plus2 Nether structures,
using v2feature registry. Stronghold coverage defaults partial with bounded-method
tag (positives usable). Other successful full-scope scans complete under predictor
method only. Scan world-aligned stride64 OW Y63 and Nether Y64 in configured boxes,
batch<=1024; canonical name_for_id callback. Per-feature failure keeps unknown/
failed and removes its stale starts; preserve other ready facts. Resume only exact
identity/bounds/revision; skip only complete compatible work. Dedup starts; reject
bad backend coordinates/types. Progress callback exceptions propagate, not swallowed.
No native imports or job launch; caller owns backend/time/RSS lifecycle.

Tests worker owns: tests/catalog/test_v2_observation.py, test_v2_extract.py. Stub
backend only; v1 test_extract/tests_models unaffected. Codex adds summaries/query
and runtime integration after review. Worker owns onlymodels.py/extract.py+2tests.

## Membership ledger (worker B)

Append `AutomationLedger` to harvest.py. Reuse a supplied `HarvestQueue` connection
and its bounded transaction, but keep new `automation_*` tables separate from the
existing task/campaign membership table. No supervisor/publisher changes in this
task. No global connections, runtime jobs, native imports or background threads.

Constructor `AutomationLedger(queue, *, policy_revision, objectives)` where
objectives maps registered ID->positive integer capacity<=10000. Validate SHA64
policy, registered max7027 objectives, aggregate<=105644 slots, immutable schema/
policy definition; incompatible definitions cannot silently reuse winners.

`offer(receipt, offers)` atomically records a world evaluation receipt and updated
membership generation. receipt has world_id64hex, identity, observation_id64hex,
artifact (JSON artifact reference), evaluations(list), replay(dict). Validate world
binding using models.world_id and source observation identity equality supplied by
caller. Do not pretend the receipt alone proves physical world evidence.

offers list entries: `{objective_id, rank:list, member:dict}`. Member must bind same
world_id. Only one best entry per objective/world; improve-only within this policy
generation (worsening corrections require explicit rebuild). Ranks lexicographic:
integers, strings, or exact numeric objects `{numerator:int,denominator:positiveint}`
and `{decimal:canonical_finite_string}`. No float/NaN, booleans or arbitrary objects.
Numeric keys compare numerically; do not SQL-sort raw JSON strings. Best ranks
ascending, then worldID ascending. At mostcapacity winners/objective. Sameworld
may win manyobjectives; losing one never removes others. Replays don't increase
population count. Receipts retain evaluated losers for population/replay, but
membership references alone determine which full observations remain wanted.

`members(objective_id=None)` returns deterministic list of entries
`{objective_id,world_id,rank,member}`; `receipt(world_id)` returns saved receipt;
`population()` returns evaluated world count. `generation()` returns latest committed
integer generation. `retained_worlds()` returns sorted union of winning worldIDs.
No auto-delete observations; no publication pointer in this task. Use a locked
transaction so failedoffer rolls back receipt and allmemberships. Keep bounded
ordered sets; no plugin/heap service. Unit tests under
tests/catalog/test_automation_ledger.py compare to independent full sort, ties,
replay, multiobjective losses, invalid revisions/inputs and transactionrollback.

## Worker execution

Read/edit owned files only. Exact allowed tests are provided via per-job
run-command wrappers; do not invent raw shell invocations. No builds/install/BDS/
network/seed scans/agents/notification. Gemini modelmustbe High. Primaryworkspace
is not writable. Return concise changedfiles, actualtests, limitations, marker.
