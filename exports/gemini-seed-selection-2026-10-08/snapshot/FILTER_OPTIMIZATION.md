# Filter optimization — 8 October 2026

The user authorized the discussed shortcuts and fast Stronghold filtering.
The production iterator remains pinned and its known misses remain visible. A
rounding workaround that failed independent seed9 verification was not installed.
The large sweep remains unstarted. Prior sources/readiness are preserved in
`runs/filter-optimization/prior-sources.zip` and `prior-readiness.json`.

## New order

1. Enumerate Stronghold, then other required structure predictions before the
   discovery map. Intersect their allowed eight-block center windows. The Fortress
   window is converted to Overworld units exactly once.
2. Discover/nominates the same three landscape branches. Defer components whose
   nominal center envelope has no joint required prediction. Basin envelopes include
   all256-block recenters; island envelopes retain the64-block displacement margin.
   These nomination envelopes are heuristic, not an exhaustive shoreline guarantee.
3. Run bounded preliminary terrain only on retained nominees. Refine coast only
   for selected islands. Check finalized island-center required windows before the
   full3008-square terrain. Basin centers retain their recenter path before final
   eligibility is decided.
4. Before full basin terrain, check necessary dry/gentle upper bounds in a smaller
   lattice-aligned patch with gradient/5×5 kernel halo, including the exact original
   eight nearby floor proposals. Ignore local connectivity for these upper bounds:
   a connection outside the patch must remain possible. Percentile relief remains
   a full-raster test; it is not approximated using a misleading local subset.
5. Lazy mountain-ray checks count only proven misses. With180 rays and75% required,
  46 misses make success impossible. Unknown/unprocessed rays remain possible.
   Connectivity is ignored and113 is the minimum possible height threshold, so
   this is a necessary upper bound. Stop extra sampling at5000 ray points and let
   full terrain resolve the survivor. Accepted basins still require full-raster
   connectivity, dry/gentle fraction, relief and enclosing dry mountain bearings.
6. Reuse per-raster labels, gradients, coordinate meshes and local ranges across
   alternate build centers. Score survivors, checkpoint, and reuse verified cached
   terrain/maps on export.

Fast-mode missing predictions are **deferred, not proven absent**. Both seed-level
and location-level records are exported in `stronghold-deferred.json`; a distinct
seed list is `stronghold-deferred-seeds.txt`. A seed may also have successfully
analyzed locations and still appear there. Use `config/review-all.yaml` for a new
bounded recovery run, in batches of at most1000 supplied seeds. Do not resume a
fast checkpoint with changed configuration. Stronghold and Fortress remain required
for final matching-version website eligibility. No game evidence is inferred.

## Native shortcuts and bits

`ss_filter_starts` validates raw positions without rerunning placement. Its special
Stronghold/Mineshaft handling exactly matches the original adapters. Typed CFFI
buffers and the owned opaque Generator context are retained. The supported editable
native build recompiles the changed owned bridge; all pinned vendor hashes stay
unchanged. No fictional stronghold/fortress symbols or guessed ctypes layouts.

The bounded per-process128-entry raw layout cache uses `(family, seed & 0xffffffff,
bounds)` only for the eight pinned MT families: Village, Ancient City, Ruined Portal,
Shipwreck, Monument, Outpost, Fortress, Bastion. Every cache hit still reruns
viability with the complete world seed. Stronghold village positions, Mineshaft,
Trial Chamber, terrain, biomes and densities never use that cache. Trials keep their
different RNG dependency. Returned results cannot mutate the stored immutable raw
tuples. Negative coordinates, upper-bit worlds, cache eviction and closed handles
are tested. Full64-bit enumeration is unchanged. Random low32 collisions are rare;
the cache mainly helps workloads containing high-bit siblings and is not claimed
to accelerate ordinary random seeds materially.

No Java quad-hut mask, terrain-only lower-bit signature, SIMD/GPU noise rewrite or
unsafe coordinate-rounding patch was adopted. The first two lack applicable Bedrock
terrain guarantees; the latter changes need separate implementation/parity evidence.
No filter threshold, flatness/isolation condition, square, or secondary-score weight
was relaxed.18 workers were not forced simply because18 physical cores exist.

## Verification and measured results

112 meaningful tests pass, including all supported native-family combined-scan
parity on four seeds; low32 raw cache/full64 viability separation; joint windows
and exact negative borders; fast missing-Stronghold deferral before any terrain;
reference-positive/nearby-floor controls for early basin checks; shared raster
parity; the independent seed9 guard; checkpoint/resume and worker variation.
Frozen880 structure/159 point regression remains874 unique correspondences, six
known disagreements, no reused starts. Root Stronghold recall is not fixed.

Alternating-order isolated A/B on four saved failed basin nominations:
30.7207→1.3903 seconds (**95.47% stage time saving**),189268→11016 native density
columns (**94.18% reduction**). Every early rejection also fails the original
full-raster/recenter check. Combined native scans0.4255→0.2515s across four seeds and
all families (**40.88% stage saving**), with exact typed results. These small tests
do not establish universal speed or candidate yield.

Current interrupted/resumed20-input pilot:96 scored locations,49 enclosed/47 ocean,
zero positive dry basins. All95 prior locations with local required predictions
retain identical complete candidate records, metrics and scores.19 prior missing-
Stronghold locations are deferred, and one new location is reached.2082 nominal
locations are explicitly deferred, mostly before preliminary terrain.38 of40 basin
refinements fail the cheap necessary bound; no positive real basin yield is claimed.

Pilot345.58s total,310.89s analysis,34.69s reports;17.28s/input effective throughput,
worker mean80.79s, range40.88–129.15s. Prior20-input pilot387.62s/19.38s/input and
worker mean96.39s. New coverage differs, so the overall comparison is observational,
not an unchanged-workload causal A/B. A separate uninterrupted worker-count
comparison uses identical20 seeds/config/predictions and reusable report maps.
No performance claim is based on how many worthy worlds were found.

Uninterrupted analysis:8 workers233.65s versus12 workers212.59s, **9.01% less wall
time** with identical prediction hashes. Twelve is the current recommendation,
based on one measured trial per count, not a claim of global optimality. Measured
12-worker analysis projects about5.92h for2000 inputs plus amortized cold reports;
the interrupted8-worker pilot's complete overhead gives a conservative9.60h.
Use1.5× allowance(about8.87–14.40h) and add manual review.18 workers were not tested.

Independent20-input12-worker run exactly matches the interrupted/resumed8-worker
pilot, including predictions, metrics, point-cache counters, deferrals/rejections
and deterministic stage counts. Only timings/RSS/PIDs are excluded. Fresh actual
matching-version browser follow-ups re-confirm four required markers on two retained
ocean controls, including a high-bit seed and negative coordinates. Prior geometry
observations retain their original dates/scopes and are not relabeled as new blind
holdouts.150 unchanged PNGs refresh in1.18s with no native height/biome calls or
redraws, enforced by failing hooks. Website evidence remains distinct from Minecraft.

Exact current commands, worker comparison, finite runtime estimate and readiness
identity are in [SWEEP_READINESS.md](SWEEP_READINESS.md). The archived package does
not authorize the changed sources; only newly assembled verified readiness does.
