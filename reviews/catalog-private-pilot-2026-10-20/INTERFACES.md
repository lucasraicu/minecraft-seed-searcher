# Frozen private-pilot interfaces

New files only for workers. Codex integrates shared files. Research identities,
request vocabulary, scoring and full seed strings remain unchanged. No worker
may run native extraction, Docker, installs, servers, agents, Git mutations or
notification hooks. Builtin file readers/writers allowed in owned paths; terminal
only exact provided immutable command wrappers. All tasks High in isolated copies.

## Storage: segments.py

`SegmentedCatalog(root, *, leaf_entries=256, fanout=128)` context manager, `.close()`.
Dedicated `pilot.sqlite`, marked schema, never existing catalog.sqlite/personalDB.
Uses existing ArtifactStore for immutable JSON/gzip, artifacts root under newroot.
`publish(observations, layouts, *, parent=None, replace_worlds=()) -> snapshot_id`:
input lists. Append to explicitly pinned parent; duplicateidentical input idempotent.
One observation/world/generation; conflict requires explicit replace_worlds IDs.
Never mutate old roots/memberships. Full input validation/hash bindings and uniform
identityheader excludingseed. World leaves keep up to243 unique geometry layouts,
or fewer when partial; custom smaller leaf_entries splitsworld for tests. Immutable
leaf stores descriptors including codecmetadata, base64packedpayload and SHA;
bounded byentry and1MiB JSON; treefanout<=128 and1MiB. Leaf ordering canonical
world_id/side/anchor/layout, deterministic publish independentinputorder. Reuse
unchanged worldleaves on append. Root tree plus compatibleheader/revisions bindsID.
SQLite tables roots/rootmetadata/observationrefs/leaves/membership/artifactrefs as
needed; atomicpromotion after durable artifacts; SQLtransaction serialized, never
destructive cleanup. Refuse symlinkcomponents and wrongexistingroot markers.

`.snapshots() -> list[dict]` each `{snapshot_id,worlds,layouts,header}` creationorder.
`.info(snapshot_id=None) -> dict` same, None latest, ValueError ifmissing.
`.iter_segments(snapshot_id=None)` yields `{segment_id,layouts}` with fullyvalidated
summarydicts decoded from boundedleaf, theirmetadata/hash/revisions verified.
Includes each layoutonce, no duplicateworldgeometry, no rawbiome loads.
`.identities(snapshot_id=None) -> list[identitydict]` derived pinnedmanifestmetadata.
`.observation(snapshot_id,world_id) -> validatedrawobs` lazy; provegenerationmembership.
`.audit(snapshot_id=None) -> dict` fullreachability/rawvalidation/layoutbindingaudit,
returns `{passed:True,worlds,layouts,snapshot_id}` orraises. Ideally rederive facts
or clearly distinguish integrity audit from derivedsummary oracle; Codex handles
raw-coordinate parity separately. `.backup(destination)` verifiedreachabilitycopy
and metadataSQLitebackup; freshdestonly. Never purgeorphans/WAL. `publish` returns
after completegeneration durable; SQLiteFULL, readerconsistent roots retained.

## Index: index.py (independent pure artifact module)

`build_index(layouts) -> dict` canonical JSON serializable index schema and content
digest binding fullorderedsummarymetadata+payloadsha, policy/registry/geometry/index
revisions, no globalroot. No externalpackages. Up to256rows; bitsetint serialized
hex with length/reservedbits checks. Index structure count thresholds1..16 x4scopes,
coverage and biomepositivewitnesses x4scopes. Side/origin filtering atsame row.
For insideborder biome witness: MISSINGmeansnone; nearest_d2 is distance to nearest
sample INSIDE that layout'ssquare (summaryconstructors ensure), so presence only
requires!=MISSING, notcircle<=halfside². Near radii use distance<=r² ANDcoverage.
`candidate_indices(layouts,request,*,index=None) -> list[int]` exactlayoutindices
passingallRequired and requestedside/mode; validate request; Preferrednotfilter.
If suppliedindextampered/stale/differentrows -> ValueError, no silent omission.
`index_identity(layouts) -> str` contentbinding, reusableacrossroots.
Worker tests must use independentlycoded predicateoracle, boundarycorners/unknown/
OR/sameanchor/reorderedrows/corruption, signedseed extremes, allscope/thresholds.
No queryscoring changes and no dependency on not-yet-integratedsegments module.

## HTTP/UI contract (Codex implements Pythonservice/routes)

Base `/api/catalog`. JSONerrors `{ok:false,error,code}`; no rawpaths/tracebacks.
GET `/status` -> `{ok:true,available:boolean,snapshot_id?:str,worlds?:number,
layouts?:number,header?:identitywithoutseed,reason?:str}`.
GET `/capabilities` -> `{ok:true,registry:{categories,features},presets:[...],
profiles:[{id,label?}],border_sides:[2048,4096,8192],near_radii:[256,512,1024],
anchor_modes:['recommended','origin'],max_rows:12,max_compare:4,evidence_label:str}`.
GET `/snapshots` -> `{ok:true,snapshots:[info...]}`.
POST `/query` body `{request:exactcatalog-query-v1,page_size?:1..50,cursor?:str}`
-> `{ok:true,snapshot_id,request_sha256,results:[candidate],next_cursor:str|null,
truncated:boolean,matched_worlds:number,stats:{...},evidence_label:str}`.
Candidate frozenexistingquery fields world_id/seed(str)/layout_id/anchor/border_side/
score/utility_units/distance_tie/contributions, PLUS `counts`14x4,
`structure_nearest_d2`14,`biome_nearest_d2`9,`complete`23x4,`bounds`[lox,loz,hix,hiz].
Backendrankauthoritative; UIneverNumber(seed)orsortbyroundedscore.
GET `/detail?snapshot_id=...&world_id=...&layout_id=...` ->
`{ok:true,snapshot_id,world_id,identity,layout:summary,structures:{featureID:[[x,z],...]},
biome_witnesses:[{feature,x,y,z,distance_squared}],coverage,evidence_label}`.
Detailwitnessesuse persistedrefs, coordinatesabsolute, startsnotfullfootprints.
Onlyboundedstructurepoints insideborderreturned (cap5000, truncatedflagifneeded).

Frontend uses requestJson from existing utils/network, fetchfallback okaywith
AbortController/errors/timeouts. `CatalogWorkspace` namedexportdefaultpropfree.
URL `#catalog?snapshot=<id>&world=<id>&layout=<id>` for detailshare; approot detects
hashprefixcatalog. Catalog manages namespacedhash and browserbackforward.
Defaultstatussnapshot; deep link oldsnapshot firstloadresolvespinnedheader via
snapshots. Do not querynewgenerationwitholdrequest. Atmost4compare, favoriteslocal
key`seed-search.catalog.favorites.v1`; provide export/importmetadata,delete.
Catalog owns itscomponents/types/styles/utils; worker NOT App.tsx,network.ts,vite.
Catalogworkspace fullresponsive existingdarkemeraldtheme, readableforms/errorstates,
eightcategorybuttons/editablepresetrows, add/remove/RequiredPreferred/importance/
structurecount/biomeOR/scope/radius; bothmodes andthreeborders; optionalprofiledropdown.
Results/detailmapcanbesimpleSVGabsolute starts/samples withaccuratelabels.
Seedcopy/favorite/share/detail/compare; empty/loading/stale/oldgenerationstates.
Favorites ondeviceonly, CSV/JSONexport optional JSONrequired. Annotationexport
queryfeedbacklocal only, userinitiated, no hidden telemetry.
