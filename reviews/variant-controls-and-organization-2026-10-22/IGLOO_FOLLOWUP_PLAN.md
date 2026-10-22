# Narrow igloo observer correction and request-cap amendment

The eight-world validation is complete. No new seed search or native change.
Initial BDS time214.3613/1200s, all owned servers stopped. Source observations and
all failed/inconclusive results remain retained. Treasure2positive+2negative pass.

Evidence establishes an observer geometry mistake, not a predictor defect:
igloo top templates rotate around their placement origin. Frozen point24,56
has actual bed coordinates11/12,67,53 and furnace13,67,49 (top origin16,66,48,
rotation90). Point24,152 has bed11,106,139/140 and furnace15,106,141 (origin16,105,144,
rotation180). Initial API scan started at point-8 and omitted these westward parts.
Old archived actual igloo independently shows the same placement behavior. Do not
interpret the empty partial API volumes or generic locate failures as negatives.

Existing saved case2 has actual BrewingStand[-156,46,11] and an unopened chest
[-156,45,15] with loot_tables/chests/igloo_chest.json. This matches the pinned
basement template's brewing/chest displacement rotated270 degrees, below the
actual matching surface bed/furnace layout. It is a positive physical basement
signal, independent of the saved predicted=true. No actual negative yet.

Corrected bounded work, preserving all original caps except the explicit request
amendment below:
1. Resume OWNED existing case0 world (same seed/directory, no new disposable world
   or seed), after archiving its exact prior world bytes. Original attempt used
   9.61s and zero observer requests. Allow at most its remaining170.38s, and at most
   its eight unused requests. Correct box to point-16..point+7; Y0..111 unchanged.
   Old failed attempt remains a failed attempt. Freeze corrected protocol before
   observation. Positive requires real basement signatures, not a predicted label.
2. Cases3/4 already used eight requests each. REQUEST AMENDMENT: allow exactly ONE
   additional observer request per world (nine cumulative each), <=59 frozen block
   positions/request, from the independently anchored rigid surface template.
   These confirm full furniture/floor and the trapdoor-versus-solid-floor cell.
   No absence-only basement conclusion. If either template does not match, UNKNOWN.
   This is far below the unchanged8192reads/request and ten chunks/request limits.
3. Resume those same OWNED worlds only, archiving before mutation. Count all startup,
   shutdown and cleanup against each world's cumulative180s and global1200s. Preserve
   original report/log/request counts and source hashes. Enforce2CPU/2GiB, one server
   at a time, existing2GiB output cap, zero players and pinned BDS1.26.52.3/API2.10.
4. Use the grouped Bedrock temple locate only as supplemental navigation evidence;
   the rigid actual hut/laboratory signatures establish igloo/subtype identity.
   Exact seed/settings, sourceWorld, geometric association and block/entity signals
   must bind controls. No increased block volume, world count or elapsed allocation.
5. Require two actual positive worlds and two positively recognized plain-top worlds
   to activate igloo. Keep all earlier unknowns/failures in the chain. If any case
   contradicts its prediction or remains unsupported, retain that gate and report.

All signatures and probe locations freeze before the followup labels; no case
replacement or discarding contradictions. New positive evidence from stopped data
is marked a separate diagnostic from the original clipped API result. Do not call
this random-population accuracy or complete physical-instance coverage.

The conditional600s derived rebuild allocation is cumulative for BOTH features.
Any later igloo activation reuses only the unspent remainder after treasure; it
does not reset that budget. Successor history/temp bytes are charged in aggregate
to its2GiB allocation; preflight before any second stage. If insufficient, stop
with a concrete amendment proposal rather than expanding a cap silently.
