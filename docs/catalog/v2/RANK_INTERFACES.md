# Worker: additive query scorer

High, approved goal. Own ONLY catalog/query.py + tests/catalog/test_v2_rank.py.
Append functions; do not modify existing rank/_rank or legacytests. No terminal
RunCommand calls: coordinator runs exact declared check after final. Builtin
read/edit owned paths only, no jobs/network/builds/agents/notification.

Request and summary schemas are defined in QUERY_INTERFACES.md. Real validated
models and summarize_v2 are now in primary snapshot. Existing query.py source is
embedded for exact legacy math/ties. Follow requested sameanchor typed31features.

Implement `rank_v2(summaries, request, limit=1000, *, keep_keys=False)` returning
ALWAYS dict {results:list,unresolved_candidates:list,matched_worlds:int}. Validate
request using validate_request_v2. Only requested border and anchor mode in
row.anchor_modes. Every required condition binds SAME summary, including OW and
Nether. Required structure can pass observed count>=N even if completeFalse;
if fewer thanN, known-complete=>no_match, otherwise pending. Required biomeOR
passes any positive scopedwitness; unseen=>pending, neverphysicalabsence. An
anchor with any definitefailedrequired is no_match evenif otherrowsunknown.

Scopecolumn inside_border=3, near using feature dimension's radii. Existing
summary.features[featureid] has dimension/counts4/complete4/nearest_d2/witness.
Preferred utility: weights1/3/5 ×LCM720720; structures min(count,N)/N (integermath),
biomes witness=>full else0. Missing preferred evidence yields unknowncontribution,
not physicalabsence. Knownpartialcounts can contribute explicit lowerbound units;
include contribution complete/status/count/at_least/max_units and positivewitness.
If zero Preferred use existing scoring.profile_units(summary.legacy,profile), no
new fallbackweights or expanded31feature score. Preserve legacyrow resultfields
counts/nearest/complete arrays from summary.legacy for compatibility, add typed
feature_counts/feature_complete/nether_anchor soUIcanrendernewfieldsaccurately.

Distance tie acrossallselectedrows matches existing isqrt(d²*10^12)//normalizer,
clamped1million perrow; unknown/noin-scopewitness=>1million. Normalizer near=rowradius,
inside OW=border_side/2, insideNether=512. No rawcrossdimensiondistance comparison.
Sortkey=(-utility_units,distance_tie,unsigned64seed,anchorx,anchorz,layout_id),
identicalexistingtiecontract. Select bestqualifying anchor perworld THENToplimit.
matched_worlds count full uniquepop beforelimit. Keep pendingbestanchors for worlds
with no confirmedmatch, include seed/worldID/layoutID/anchor/border/status/reason;
do not let unknowns displace matches. _sort_key only whenkeep_keysTrue. candidate
fields score,utility_units,distance_tie,contributions,world_id,seed,layout_id,
anchor,border_side,bounds plus typed/legacyfields above. Utilityunits mayDecimal:
return int/stringJSON-compatible like existing query; _sort_key canDecimalinternal.

Acceptance tests independent raw fixtures: sameanchor crossdim, 64vs256Nether,
negativeprojection preserved, partialstrongholdpositive, missingbiomepending,
zeroPreferred oldfallback parity and deterministicunique-worldties/paginationkeys.
Do not import native engine or rewrite request/service/storage. <=400word final
marker V2_RANK_IMPLEMENTED, disclose tests are run automatically by bridge.
