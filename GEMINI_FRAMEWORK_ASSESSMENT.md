# Framework assessment — 11 October 2026

The useful directions are reducing repeated terrain work and testing stronger
placement constraints. Neither a wholesale SciPy rewrite nor AVX flags currently
has evidence for a large end-to-end gain. Requiring every structure may make
finished worlds rare without making raw lower32 layouts rare.

This assessment changes no search requirements, detector behavior or native
compiler flags. Geometry stays 4000×4000 discovery, 1536×1536 Overworld deployment
and 896×896 Nether deployment. Earlier terrain preference edits remain present.

## Terrain evaluation

Gemini correctly identifies repeated array work in `terrain.py`. However,
`ndimage.label` is compiled Cython, EDT uses a compiled C feature transform, and
ConvexHull calls Qhull. These are not spatial algorithms executed entirely in
Python. Many SciPy operations release the GIL; baseline multiprocessing workers
also have separate interpreters. Calling a compiled routine with a NumPy array
does not inherently copy the entire input across the language boundary.

Primary references: [SciPy thread safety](https://docs.scipy.org/doc/scipy/tutorial/thread_safety.html),
[ConvexHull](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html),
[label source](https://github.com/scipy/scipy/blob/main/scipy/ndimage/src/_ni_label.pyx),
[EDT source](https://github.com/scipy/scipy/blob/main/scipy/ndimage/src/ni_morphology.c).

The current nomination loop repeatedly evaluates centers on the same raster.
V1 recomputes land/water labels each time, even though those labels do not depend
on center. Its distance transform and hull span can also be reused for centers
on the same island. V2 thresholds depend on interior elevation and distance from
each center, so its component labels cannot generally be shared indiscriminately.

A new four-case synthetic diagnostic used 50 profiled calls per case at an
8-block sampling resolution. V1 large/irregular islands took 7.58/8.32 ms per
post-raster call; V2 separate/rough mountain enclosures took 7.57/7.61 ms.
These include cProfile overhead and exclude raster generation, persistence,
parallel scheduling and actual-world acquisition. They are hotspot controls,
not production seeds/second or a natural terrain calibration.

V1's EDT used about 21–24% of inclusive evaluation time and component diameter
about 12–14%. V2 percentile calls used about 23%. Both included ray overhead of
about 10–11%. Inclusive entries overlap: do not sum nested profile rows.

Concrete priorities:

1. Build a bounded, immutable per-raster analysis workspace for coordinates,
   clipped cell areas, V1 labels and component statistics. Cache island EDTs by
   component only when repeated use justifies memory. Key reuse by exact raster
   content/known-water evidence and refresh when actual observations change.
2. Batch ray coordinates/indexing instead of constructing 32 small arrays for
   every center. Skip unknown-neighbor dilation when all cells are known, while
   preserving incomplete-raster behavior.
3. Defer diagnostic-only work in nomination. Active V1 qualification and scoring
   use area-equivalent diameter, not hull span. Active inclusive V2 does not use
   arc thickness/aspect to gate qualification or score. Preserve those values
   for detailed retained results and strict saved configurations; explicitly
   mark deferred metrics rather than inventing values. If exact hull diameter
   remains material, replace pairwise hull distances with an exact polygon
   diameter algorithm after profiling real footprints.
4. Profile the current real nomination/fine/halo stages after these changes.
   Move only residual expensive loops into native code. Compare qualification,
   score, footprints and known/unknown evidence with the current implementation;
   cover diagonal bridges, clipped edge cells and strict/inclusive ridge policy.
   Measure persisted multiworker throughput and memory before promoting a port.

## Compiler vectorization

The build already uses `-O3`. LLVM enables vectorizers by default; AVX flags allow
additional instructions but do not turn every noise loop into simultaneous
independent columns. Branches, permutation lookups and dependency chains matter.
[LLVM vectorizer documentation](https://llvm.org/docs/Vectorizers.html).

Existing matched measurements are stronger evidence than a generic speedup claim:

- The newer matched native workload had median portable 5.85898 s versus strict
  AVX2 5.72805 s: 2.23% less time, approximately 2.29% higher throughput.
  Public/raw arrays matched in that tested workload. See
  `runs/master-implementation-2026-10-10/isa/trials.json`.
- The earlier full three-seed workload gained another 2.6% after exact reuse with
  strict AVX2. Exact reuse itself saved 28.1%. Its explicit four-Y prototype was
  1.2% slower after reuse. These historical results use older geometry; they are
  not a new full-search benchmark.
- Gemini's earlier combined FMA/ISA policy changed 1162/6144 tested raw-density
  values. Sampled public outputs still matched, but exact density parity failed.
  This does not mean strict `-mavx2` alone changes results.

Recommendation: leave portable default flags intact. An optional strict AVX2
implementation with runtime CPU/OS dispatch and scalar fallback is reasonable
only after a meaningful current-geometry end-to-end gain. Keep FMA/fast-math
changes out of an exact-parity optimization. Universal2 and ARM builds also need
supported paths; `-march=native` is not a portable distribution policy.
See `SIMD_TEST_RESULTS.md` for earlier scope and artifacts.

## fnseedc

[SeedFinding/fnseedc](https://github.com/SeedFinding/fnseedc) is a collection of
resources, tutorials and links, rather than a Java implementation to integrate.
It includes RNG/lattice/reversal material and libraries in several languages.
The relevant ideas are RNG dependency audits, partial-bit reasoning and
constraint ordering. Much seed-cracking material starts from observed positions;
our search instead asks for any world satisfying broad regional constraints.
That difference limits direct transfer. Every linked implementation still needs
edition/version/RNG validation before use with our pinned Bedrock predictor.

## Expanded structures and lower32

The backend exposes 22 families: 18 Overworld, three Nether and one End. All
families cannot be required in the Overworld square. This diagnostic considered
13 region-based MT Overworld families plus the three MT Nether families. It did
not certify new families for the public lower32 adapter, which still accepts its
eight previously audited types. Stronghold, Mineshaft and the three LCG-based
Overworld families were excluded from this presence combination.

128 dispersed distinct lower32 values were scanned with the existing raw
full-context API, without biome viability:

| Query scope | Village/City/Fortress/Bastion raw positive | Expanded 16-family raw positive | Expanded raw rejection |
|---|---:|---:|---:|
| One fixed origin center, 1536 OW / 896 Nether | 97/128 | 86/128 | 32.81% |
| Union envelope of all allowed discovery centers | 126/128 | 126/128 | 1.56% |

At the fixed center, Outpost was present in 121/128 and Mansion in 118/128.
All other additional families were present in every layout there. Across the
larger envelope every additional family was present in all 128. The envelope
is a weak necessary predicate, not proof that one common center accommodates
every family. Origin is not a discovered Stronghold. Neither number is a
99.9% test, a full-family lossless rejection rate or a verified-world yield.

Desert pyramid, jungle temple, swamp hut and igloo had identical candidate
positions in all 128 layouts in each scope, consistent with their shared salt,
spacing and RNG in the vendor configuration. Their viable biome sets differ.
Thus raw presence does not provide four independent filters. A stronger
placement-only check can require at least four distinct common feature slots
inside the same square because one slot's sampled biome cannot satisfy those
four disjoint biome sets. That capacity constraint is a concrete next pilot,
not a feature implemented by this assessment.

Changing upper32 for 16 low values, with three upper choices each, produced
0/48 raw-layout differences per tested MT family. Trial chambers, trail ruins
and abandoned camps each differed in 48/48 comparisons. Their pinned placement
uses a 48-bit LCG: 16 bits from the upper32 affect placement. `JAVA_RANDOM` here
names the RNG algorithm inside the Bedrock fork, not the edition being searched.
Biome and terrain viability still need the full64 seed. Finite parity checks do
not replace source review or exact-world accuracy validation.

The promising lower32 work is therefore:

1. Audit and parity-test newly eligible MT families before extending the raw API.
2. Require a common allowed center for sparse families such as Mansion/Outpost
   and the Fortress/Bastion pair, with feature-slot capacity where applicable.
   Do not reject a whole lower32 family merely because one arbitrary center fails.
3. Study a bounded lower48 tier for the LCG families and reuse full48 placement
   only across siblings for which the dependency is proved. Benchmark its cost;
   a wider seed space is not automatically an acceleration.
4. On identical CPU budgets, compare independent full64 search with expanded
   placement screening plus siblings. Measure viable/verified candidates per
   CPU hour, time to first success and selection overhead. Requiring more rare
   structures changes the desired worlds and can lower useful yield; it cannot
   be justified solely as a way to inflate rejection percentages.

Reproduction and detailed profiles: `runs/gemini-assessment-2026-10-11/diagnostic.py`,
`diagnostic.json` and four `.prof` files. JSON records the sampled lower32 manifest
and installed native binary hash. No full production throughput benchmark or
actual Bedrock world acquisition was performed for this assessment.
