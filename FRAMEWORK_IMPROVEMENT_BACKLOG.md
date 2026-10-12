# Framework investigations and improvements

Prepared 11 October 2026 from Gemini's recommendations, the fnseedc resource
review and our bounded seed-bit/terrain diagnostics. This is a proposed work
list, not implementation or authorization to change the desired structure mix.

Keep the current contract: 4000×4000 discovery, 1536×1536 Overworld deployment,
896×896 Nether deployment, large main islands and inclusive mountain enclosure.
Expanded combinations are experimental profiles until explicitly adopted.

Update: the first common-center and shared-slot pilots (items 6–7) are now
complete. On 2,048 layouts, unrestricted common-center checking added no
rejections. A source-backed possible-Stronghold-center superset increased raw
family rejection from 3.76% to 4.54–4.59%. The four-slot condition is already
guaranteed by the shared feature grid at a 1536-block width, so it is not a useful
extra filter here. See [common-center results](COMMON_CENTER_PILOT_RESULTS.md).
Keep a production solver and a stronger reachable-center predicate conditional
on measured useful-yield benefit; remaining items stay proposed.

Selected-center follow-up: direct lower32 MT placement matched full64 in 30,208
queries at explicit discovered Stronghold borders. With one center fixed per
seed before screening, the current combination lacked raw placements in 28.79%
of 896 layouts, expanded MT in 32.48%. A separate lower32 gate made the current
four-family viability stage 18.69% slower on the locked-center holdout replay.
Prioritize fused native checks and measured exact-center reuse over adding a
standalone gate. See [locked-center results](LOCKED_STRONGHOLD_LOWER32_RESULTS.md).

All-structure follow-up (item 9): four mixes and 20 increasing prefixes were evaluated at 896 frozen selected centers, covering all 21 supported Overworld/Nether families plus an End-city control. The expanded raw conjunction still removed only 32.48% of combined layouts. Even a minimal first-placement gate with paid exact-center cache construction was 13.39% slower for the current four and 44.55% slower for all 21 on holdout. Keep the separate gate out of production; pursue native fusion/lower48 only with measured useful-yield benefit. See [all-structure results](ALL_STRUCTURE_COMBINATION_RESULTS.md).

Multiplicity follow-up (items 5, 7–9): isolated native pilots now compare direct
count-capped viable detection with fused raw counts and paid bounded caches,
covering all 22 structures at N=1–4. Requiring two of every Overworld/Nether
structure rejects 95.65% by raw capacity on holdout; fused32 takes 21.7% less
conditional count-stage time and cached32 40.1% less. At one each cached32 is
35.5% slower. Lower48 adds no rejection through four each. Including full64
Stronghold discovery and context preparation removes most of the gain, with no
robust overall speed improvement across the two small cohorts. Biome multiplicity
is distinct active IDs within a family: all 66 IDs and 29 canonical families were
covered, with full64 generation required. Native diversity stopping saves 83.9%
of forest-N2 inventory time, while broad rare-family goals can be 16–18% slower.
The pilots have 371,240 passing reference comparisons and 34 focused tests;
production promotion and actual-game accuracy work remain pending. See
[multiplicity and seed-bit results](MULTIPLICITY_SEED_BIT_RESULTS.md).

## First: measurement and correctness

### 1. Profile the current full pipeline on representative inputs

Investigate native height generation, V1/V2 nomination and refinement, biome
inventory, structure witnesses, array allocations, IPC and persistence together.
Use retained natural raster observations and complete/incomplete terrain cases;
the latest four synthetic controls do not establish production bottlenecks.

Improvement: add a bounded replay/report separating wall time, CPU time, native
work, sampling, analysis, queue wait and persistence. Report input seeds/second,
stage calls/second, surviving anchors/second and memory separately. Include
startup, selection and checkpoint costs in end-to-end comparisons.

Acceptance: freeze source/native/config/input identities; use counterbalanced
repeated trials and a separate holdout. Do not add nested inclusive timings or
project a whole-pipeline gain directly from a microbenchmark.

### 2. Create a dependency and detection contract for every exposed family

Investigate each structure's placement RNG, relevant seed bits, shared placement
groups, dimensions, viability rules and special enumeration behavior. Cover the
22 exposed families, active biome channels and existing exact-game recall gaps.
Distinguish raw placement, viable predicted start, first witness, complete
inventory and actual observed remnant/contact evidence.

Improvement: record an audited capability table. Use first-witness detection for
existence requirements and complete inventory only where counts/ranking/audits
need it. Identify any remaining unusually expensive negative queries and biome
inventory scans from item 1; reuse immutable seed contexts and batch only the
samples needed by each evidence contract.

Acceptance: upper-bit perturbation and source review agree; optimized witness
results equal the full detector's existence result across positive/negative and
boundary fixtures. Preserve unknown/pending states and supported actual-world
coverage. Same-predictor parity is not a resolution of known game-accuracy gaps.

## Highest-priority implementation candidates

### 3. Reuse terrain analysis across centers

Investigate how frequently nomination/refinement evaluates the same raster and
same land component, and how much time those repeated passes consume.

Improvement: introduce a bounded per-raster workspace holding coordinate axes,
clipped cell areas, water masks, V1 land/water labels and component statistics.
Reuse V1 area/footprint/hull data by component. Cache component distance transforms
only when measured reuse repays their memory. V2's center-dependent elevation
and radial masks require different keys and cannot inherit V1's label reuse.

Acceptance: exact decisions, scores, sampled footprints and evidence states;
invalidate after changed actual observations; bounded memory under concurrent
workers. Cover clipped cells, diagonal bridges and unknown neighbors.

### 4. Reduce work per terrain nomination

Investigate ray-array allocation, Python scanning loops and metrics that do not
affect the active nomination score or qualification.

Improvement: batch ray coordinates/indexing; skip unknown-neighbor dilation when
all samples are known; defer V1 hull span and inclusive V2 arc-thickness/aspect
diagnostics until detailed retained evaluations. Keep strict historical policy
behavior and all diagnostics needed by that policy. Mark deferred fields
explicitly. If exact hull diameter remains expensive, evaluate rotating calipers
instead of all pairwise convex-hull distances.

Acceptance: nomination priorities and downstream decisions remain equivalent;
full retained results include the required diagnostics. Actual water and
formation footprint evidence must not be weakened.

### 5. Extend the audited lower32 placement adapter selectively

Investigate additional MT families, especially Mansion and Outpost as sparse
placement constraints. Audit desert pyramid/jungle temple/swamp hut/igloo,
Ocean Ruin, Buried Treasure and Nether Ruined Portal before exposing new raw
operations. The latest diagnostic did not promote those additional families.

Improvement: generator-free early-exit placement queries for proved lower32
families. Reuse one candidate list for shared feature placement while keeping
each structure's viability checks separate. Add types only where useful;
dense families may contribute little rejection.

Acceptance: raw layouts match full-context enumeration with signed full64 seeds,
varied upper bits and negative region boundaries. Review RNG dependency and
version dispatch; a small sample of matching positions alone is insufficient.

### 6. Test expanded structures at one common allowed center

Investigate the gap between "each family exists somewhere in the envelope" and
"one deployment square can contain all required families." Our 128-layout pilot
added zero envelope rejections with the expanded presence combination.

Improvement: generalize the existing four-family center intersection into a
bounded configurable placement-feasibility check. Prioritize Mansion/Outpost
with Village/City and the Nether Fortress/Bastion pair. Preserve exact half-open
Overworld borders and fractional Stronghold-to-Nether center conversion.

Acceptance: match brute-force small-domain center controls; no false rejection
when any allowed center is feasible. A center witness is a necessary placement
condition, not a discovered Stronghold or a viable generated world. Measure
solver cost and extra rejection separately from subsequent full64 yield.

### 7. Enforce capacity for shared feature placements

Investigate candidate counts for the four structures sharing the same placement
rules. Their disjoint viable-biome sets mean one shared slot cannot satisfy all
four in the pinned predictor.

Improvement: for an experimental combination requiring all four, require at
least four distinct eligible feature positions inside the same deployment
square. Integrate this capacity condition with item 6. Investigate matching
constraints if more mutually exclusive placement groups are found.

Acceptance: source-backed exclusivity and matching/enumeration fixtures. Count
unique slots, not four duplicate copies of one layout; only reject if every
allowed center fails. Actual-game assumptions remain separately validated.

### 8. Investigate a lower48 tier and upper-bit reuse

Investigate the 48-bit LCG placement dependencies of Trial Chambers, Trail Ruins
and Abandoned Camps. Each changed position in all 48 tested upper-bit comparisons;
they cannot use lower32-only placement caching.

Improvement candidate: a bounded 32→48→64 search/reuse experiment. Test grouping
LCG placement by proved lower48 and varying the remaining high16 for biome and
terrain evaluation. Compare different exploration allocations rather than
enumerating a huge new bit range by default.

Acceptance: full48 placement parity, exact cache identities and fresh full64
viability checks. Include grouping, selection and cache costs; demonstrate
useful-yield gain on an equal CPU budget before adoption.

### 9. Measure the useful structure combination and filter order

Investigate current required structures, a sparse expanded combination, and all
supported Overworld structures as separate experimental profiles. Keep Nether
and End structures in their own dimensions. Measure conditional rejection,
correlation, full64 evaluation costs and time to first qualifying candidate.

Improvement: order cheap selective checks early and defer expensive inventory
work. Reuse shared queries and avoid treating correlated constraints as
independent probabilities. Keep structure-mix changes separate from speed-only
changes because they change which worlds the user will receive.

Acceptance: identical configured eligibility after reordering. Evaluate
independent full64 search versus lower32/lower48 plus siblings using at least
three exploration keys and held-out inputs at equal CPU budgets. Report raw,
predicted viable, terrain-qualified and actually verified yield separately;
if actual acquisition is unavailable, do not label the result verified yield.
The 99.9% lower32 rejection aspiration is a hypothesis, not a success guarantee.

## Conditional research

### 10. Apply specific fnseedc ideas to our actual RNG constraints

Investigate the linked RNG reversal, partial-bit reasoning, lattice and
constraint-solving resources. Separate inversion from known observed coordinates
from our broad search for any qualifying layout.

Improvement candidate: prototype inversion only for a source-proved compatible
placement RNG and a precisely defined useful constraint. Consider whether
partial-bit pruning or generating candidate layouts avoids more work than
scanning them. Do not import Java-edition assumptions into the Bedrock fork.

Acceptance: edition/version compatibility, exhaustive toy-domain checks and
matched forward-predictor parity. A small held-out useful-yield pilot must beat
the current approach including candidate-generation overhead. Otherwise retain
the resource as documentation rather than adding a dependency.

### 11. Port residual terrain hotspots into native code

Investigate only after items 1, 3 and 4: remaining Python loop cost, allocation
pressure and native boundary overhead. SciPy label/EDT/Qhull already use compiled
implementations, so a wholesale translation is not justified by language alone.

Improvement candidate: fused ray scanning or batched center evaluation in a
small native API, with immutable contiguous arrays and bounded scratch space.
Preserve existing compiled primitives unless measured evidence favors replacing
them. Address actual contention observed under the intended worker topology.

Acceptance: parity across connectivity, clipping, strict/inclusive policy,
unknown coverage and provenance cases; appropriate sanitizer/thread checks;
held-out persisted throughput improvement after Python-level reuse.

### 12. Evaluate optional strict SIMD kernels

Investigate compiler vectorization reports and disassembly to identify remaining
scalar dependencies in `density_cell`/`ss_heights`. Consider horizontal batches,
permutation lookup cost and memory layout rather than only changing ISA flags.

Improvement candidate: an isolated strict AVX2 kernel with CPU/OS dispatch,
portable fallback and architecture-specific build support. Keep FMA/fast-math
out of exact-parity changes. Preserve exact reuse already implemented.

Acceptance: exact tested raw-density/public-output parity, unsupported-CPU
fallback and a worthwhile current-geometry multiworker gain. Existing strict
AVX2 saved only 2.23% native workload time; the earlier four-Y prototype was
slower after reuse. Do not project large gains from ISA availability alone.

## Suggested adoption gates and order

Proposed gates, not new user requirements: zero decision/evidence regressions;
at least 10% held-out persisted improvement for a substantial terrain rewrite;
at least 20% more useful candidates per equal CPU budget for promoting a new
seed-bit search strategy. Smaller simple changes can be justified by a stable
measured benefit. No fixed gain is promised in advance.

Start with items 1–2. Then pursue terrain reuse/minimal nomination (3–4) and raw
dependency/common-center/capacity work (5–7). Use those results to decide whether
the 48-bit tier and expanded combinations (8–9) merit implementation. Keep
fnseedc-derived inversion, a larger native port and SIMD (10–12) conditional on
measured need and bounded pilot results.

Sources and evidence: [assessment](GEMINI_FRAMEWORK_ASSESSMENT.md),
[new diagnostic](runs/gemini-assessment-2026-10-11/diagnostic.json),
[existing SIMD results](SIMD_TEST_RESULTS.md),
[existing compact results](COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md),
[fnseedc resource collection](https://github.com/SeedFinding/fnseedc).
