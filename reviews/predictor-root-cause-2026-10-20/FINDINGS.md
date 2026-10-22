# Source and stopped-world investigation

Continued after the UI-link interruption. No application/native source or original
catalog evidence changed; only research artifacts and the handoff are updated.

## What is now known

1. The failed static stronghold is seed-9103892851552028103 at(820,-1708), from
   region(0,-1). native/bridge.c:ss_scan bypasses biome viability for all stronghold
   starts and appends the village-linked iterator separately. BDS instead located
   (98,-2030), corresponding to another predictor reference(100,-2028), near its
   village(104,-2024). This establishes which path needs investigation, not why
   the static structure failed the game query.
2. The failed outpost seed-3509659830737203357 at(528,512) is admitted by the vendor's
   Y319 raw-quart biome check (grove in block lookup); it is not checked for a
   complete generated building. The snowy village(-296,-312) likewise passes its
   biome eligibility path. Calling the vendor's isViableStructureTerrain would not
   fix these families: that function returns1 for them. No proposed blanket veto
   based on terrain, grove or cave proximity is supported yet.
3. Independent stopped-world reads corroborate two cave/noncave disputes at the
   persisted-data level. At(-256,63,-256), stored ID12 matches observed ice_plains
   controls atY0/120; at(-448,63,320), stored ID30 matches cold_taiga controls.
   The predictor's raw/block paths instead report dripstone/lush caves there.
   This weakens an API-only explanation for those two cases but does not establish
   the missing Bedrock rule. Below atY-48 both store190 and API reports deep_dark.
   No assumption that Bedrock numeric IDs equal predictor IDs is permissible.
4. Saved-data coverage is incomplete: direct cells decoded for85/256pilot and10/28
   vertical observations. Third cave column and failing boundary points448..451
   remain unknown. Do not fill negative-header sections using an invented rule.
5. A depth-zero or Y319 replacement fails the full fixed controls: cohort310/330,
   pilot239/256; rawquart311/330,253/256. All3correct deep_dark controls disappear
   under flattening. A surface-only switch is not a general 3D correction.

The external alternative helper reused pinned vendor sources and was compiled
outside the repository, with source/binary/command digests. It did not replace
serving libraries or edit vendor tables. Comparison observations are reused data,
not an independently held-out accuracy population.

## Storage method and limits

Mounted two already-stopped saved worlds read-only into the existing pinned image,
overriding its entrypoint to the installed Python reader. Network disabled, no
published ports, read-only filesystem,1CPU/512MiB,256MiB temporary DB copy. No game
server ran. Exact seed checked in level.dat; original DBs never opened for writes.
One first identity-reader attempt failed because /inspect.py shadowed stdlib
inspect; corrected mount name /stopped_probe.py succeeded. All owned readers removed.

Direct little-endian bit arithmetic was cross-checked against Amulet1.9.25's two
reviewed arithmetic decoder methods on1,166populated sections;105pilot chunks and
3vertical-world chunks decoded. The old Amulet API downsamples to4×4×4, so those
array cross-checks compare the corresponding4-block lattice. The experiment is not
production decoder validation, a fully specified inheritance implementation, or
global Bedrock name mapping.
[Amulet decoder source](https://github.com/Amulet-Team/Amulet-Core/blob/1.9.25/amulet/level/formats/leveldb_world/interface/chunk/base_leveldb_interface.py),
[packed format research](https://team-lodestone.github.io/Documentation/Bedrock/LevelDB_Output_Array_Formats/Data3D_Format.html).
Full decoder source SHA2568ef6c5213a1f32d5a953f83f355fe790472bd1a676f2f89b8c09050870d24004.
Compact raw/source-derived evidence is adjacent; full copied-record hex, scripts,
build information and runtime outputs remain external under
~/.local/share/antigravity-worker-mcp/predictor-root-cause-20261020/.

## Personal UI follow-up

User recalled281points. Identified seed-3336796033057908633, center(-480,0), in the
saved natural.jsonl/rescore evidence. The historical281score used required biome
families=[], and default palette evaluation produced no qualifying candidate.
Do not label it a fully qualified winner of the10billion run: that original run's
checkpoint has10billion completed inputs and0candidates/seed records.

For inspection only, copied the latest retained diagnostic checkpoint (same seed,
center, later saved score336) using SQLite backup into a NEW direct run directory
web-sweep-20261020-143452-e5161c27. Original source untouched. Stored restore receipt
with historical score/provenance and relaxed scope. Selected this view using the
existing API, verified candidate seed/score/center and total1. Personal UI3000 will
poll/display it; catalog5173 unchanged. No new search, seed recomputation or source
patch used. User was told why336differs from281 and why neither certifies current
full eligibility. A redundant older-million-run ranking read was terminated once
the exact281source was found; only that owned read process was stopped.
