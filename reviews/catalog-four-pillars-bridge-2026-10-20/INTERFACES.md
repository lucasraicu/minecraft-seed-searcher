# Approved Stage B/C interfaces

User explicitly approved PLAN.md: “i approve. go ahead”. Prior High critiques
adea4a21cc67 and109c192cfe33 reconciled. Implementation authorized, no new approval
needed within plan. No new seed campaign/live restart/native rebuild/public launch.

## Product Python

products.py exports product_registry() returning JSON dict:
{ok:true, revision:'catalog-products-v1', pillars:[{id,label,description}],
 products:[{id,pillar_id,kind,label,category,criteria_summary,availability_status,
 missing_dependencies:[string],evidence_needed:[string],scope:object,
 predicates:[object],ranking:object}], evidence_label:string}.
Pillar IDs realm,presets,personalized,rare. Kinds realm,preset,record,research.
Exactly16preset and22record definitions matching platform sections4/5, one realm
entry, five separate research entries. All product/preset/record promises gated;
research availability_status='research', others='gated'. Personalized operates
through existing query API (no extra product required). Gated inspector mandatory.
Research IDs research.origin.{village,trial_chamber,ruined_portal,desert_pyramid,shipwreck}.r2000.
Scope {scope_type:'origin_euclidean_circle',anchor:[0,0],radius:2000} for research.
Seeds signed64decimal strings, no numeric JSON seeds. No billing fields.

product_views.py exports:
- derive_previews(store,snapshot_id,*,deadline=None) -> payload
  {revision:'catalog-product-results-v1',snapshot_id,definition_sha256,
   population_worlds,header,lists:{product_id:[{world_id,seed,count,witnesses:[[x,z]],
   scope:<research scope>}]}}. Uses SegmentedCatalog observations from immutable
  selected snapshot, each world once; validates full identity/coverage, no extraction.
  Only complete feature coverage containing circle permits count; unique start
  points, <=2000 closed Euclidean circle, count>0, rank(-count,world_id), Top100.
  witnesses bounded<=5000/list row, count remains exact, indicate truncation.
  header binds snapshot build/settings/model/source identities as available.
- write_previews(root,payload) -> Path. Content checksum envelope
  {sha256:<digest canonical payload>,payload}; atomic/fsync under
  root/product-previews/<snapshot_id>.json. Reject symlinks/oversize paths/artifacts.
- read_previews(root,snapshot_id,*,expected_header=None) -> payload. Validate schema,
  digest, snapshot, definition digest, expected header, structure/count/sort/bounds,
  bounded reads<=32MiB. No raw scan. Derived artifact may be absent => FileNotFound.
Service returns per-product Top100 with scope and witnesses directly; research
detail/map uses this circle, not existing square layout/detail semantics.

## HTTP/UI

GET /api/catalog/products returns product_registry().
POST /api/catalog/product-results strict body
{revision:'catalog-product-request-v1',snapshot_id:<hex64>,product_id:<registered>}
Response {ok:true,revision:'catalog-product-results-v1',snapshot_id,product_id,
scope,results:[research rows],population_worlds,evidence_label}.
Gated => structured409 unavailable with missing_dependencies; missing precompute
=>503 preview_unavailable. No raw scans, user paths, arbitrary metrics or launch.
Bounded same service admission slots; selected snapshot validates membership/header.

New UI components only under catalog/pillars. Export PillarNavigation({value,
onChange}) and ProductPillar({pillarId,snapshotId}) from index.tsx, typed value as
'realm'|'presets'|'personalized'|'rare'. ProductPillar owns bounded requests with
AbortController and stale generation guard; uses ../utils/network via correct
relative path, not new dependencies. No seed Number coercion. Gated criteria
inspector; research list seed/copy/count and actual2000circle SVG witnesses.
Codex owns CatalogWorkspace mounting/tabs. Keep Personalized mounted hidden across
pillar switches. UI worker does not edit shared files, App, service or API modules.

## Queue

Queue worker later receives focused schema contract before its task begins.
Codex owns all realm/native CLI integration. Existing frozen ingestion harness
unchanged. Read approved plan for full durability/budget constraints.
