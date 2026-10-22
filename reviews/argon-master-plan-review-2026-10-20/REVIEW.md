# Review of Argon's Public_Catalog_Master_Plan.md

2026-10-20, America/Los_Angeles. Review only; no implementation authorized or
started. The attached document is a proposal to assess, not an instruction to
replace existing contracts or launch its roadmap.

## Verdict

We can build a CPU-only public catalog using the existing SQLite engine and
standard compressed observation files. Argon's document is useful product vision,
but is not an adequate implementation contract as written. Its first milestone
explicitly builds a custom .seedcat database, while most production stages assume
GPU execution. Removing GPU boxes alone does not fix its data/query semantics.

Using SQLite still requires a new, separate public-catalog database/schema and
observation files. This avoids writing a new database ENGINE; it does not eliminate
the need to model, persist, query and recover catalog data. Never attach public
ingestion to the personal checkpoint database merely to avoid creating a file.

Keep: independent public selection, shared absolute observations, three border
side lengths, alternative centers, editable player presets, explicit provenance,
bounded retention experiments and potential future column/bitmap serving indexes.

## Blocking conflicts and corrections

1. **The compact record cannot represent the promised queries.**
   Argon sections3/6/7 index worlds by presence bits and store one base and one
   distance/count vector. A player needs a layout identity: world + anchor + border
   + observation revision. Recommended settlement must examine all eligible saved
   anchors for each request, not one universally best base. Conjoin requirements
   at that layout, then choose each world's best layout, then take unique-world K.
   World-presence intersections can be conservative prefilters, but cannot be the
   final same-anchor/count/radius test. Checking coordinates only for the initial
   top50 cannot recover good matches excluded by incorrect earlier ranking.

   Concrete counterexample: village distances100/200/400 and100/800/900 both have
   nearest100 and border count3, yet have respectively3 and1 starts within512.
   One nearest distance plus one border count cannot answer the predicate. Save
   counts for256/512/1024 and whole border at each layout, or evaluate all candidate
   coordinates exactly. Arbitrary distance sliders require additional exact
   coordinate work or a different complete summary contract; fixed radii are v1.

2. **Required constraints become soft scores.**
   Section6 requires selected features somewhere in the border, then assigns
   positive credit even beyond their requested distances. This cannot implement
   Required village>=3 within512. Preserve the established Required/Preferred
   distinction and existing versioned scoring/ties. A continuous preference curve
   can be a later explicit scoring experiment, never a way to relax Required rows.
   Define zero-row fallback, missing features, invalid radii, D>=Rmax and square
   corners before adopting any new formula. A square's corner distance exceeds
   its half-side; square scope and circular exploration radius are not identical.

3. **Custom storage is front-loaded and under-specified.**
   The header and section9 Phase1 explicitly require .seedcat and mmap. Use the
   proposed separate SQLite metadata + packed summaries + immutable checksummed
   observation bundles first. Later indexes can be derived and rebuildable.
   Add feature-specific coverage, world settings, exact compatibility acceptance,
   predictor/extractor/registry revisions, manifests, idempotent receipts and
   snapshot publication/recovery. A seed alone is not a sufficient cross-version
   world/observation key. Sequential world IDs must be snapshot scoped; saved user
   references must survive rebuilding/reordering. Heap checkpoints alone do not
   establish scan progress, leases, durable publication or restart correctness.

4. **The 96-byte/RAM claims do not follow from the schema.**
   Independent parsing and size arithmetic of the packed C fields yields98 bytes,
   not96. Reducing two reserved bytes would fix that sum but not the missing data.
   uint8 distances in16-block units max out at4080; an8192-square corner can be
   about5792.62 blocks away. Quantization also changes exact threshold/rank answers
   inside that range. No rounding rule, saturation treatment or missing-data state
   is defined. uint8 counts lose values above255; preserve full uint32 counts.
   Coordinate ranges and out-of-domain spawn anchors also require explicit guards.

   Existing contract sizing is illustrative, not an alternative measured promise:
   243 layouts x400 bytes =97,200 bytes/world before sharing/compression; the raw
   one-plane biome grid adds51,200 bytes/world, excluding structure coordinates,
   metadata and indexes. This is disk/logical payload, not a requirement to hold
   every layout and observation in RAM. A small hot index may be much smaller, but
   the document has not designed or measured one with the promised semantics.

5. **Retention guarantees are unsupported and some capacities are unbounded.**
   Presence of25 features does not guarantee every subset's requested counts,
   radii, anchor or optimal rank. Singles/pairs/diversity buckets are candidate
   strategies, not proof of complete coverage. The per-observed-mask hash table
   needs a global distinct-mask capacity/eviction policy; top5 per key alone has
   no small fixed memory bound. Freeze objective definitions, comparison tuples,
   per-mode/per-scope lists and deduplication before K, plus a stable-hash sample
   selected before relevance filtering. Do not estimate unique worlds from slots
   without measuring overlap. Current proposed retention bound is83,944 slots
   before pins/dedup; adding spawn changes it. Replacing that policy is a design
   change, not an implementation detail.

   Nonempty preservation must be measured against a separately held-out reference,
   with unique-world top10 recall and score regret per request family. Keeping an
   entire10000-world cohort cannot validate retention budgets larger than that
   cohort; use reduced-cap experiments and later larger-than-cap references.

6. **Unavailable capabilities are presented as launched features.**
   Sections2/3 enable estimated spawn, verified igloo basement, public Nether and
   mandatory stronghold information that the current public registry gates.
   Estimated world spawn has useful108-world evidence on BDS1.26.52.3, but its
   maximum observed error11.32 is not a universal bound or exact player placement.
   The badge Estimated Spawn ±11m overstates the audit and even rounds below its
   observed maximum. The3.04ms timing and108-world accuracy come from different
   experiments; the latter audit recorded3.83ms median. Keep runtime integration,
   coverage, version acceptance and complete-record cost gates explicit.

   Certified Realm God Seeds needs actual scoped verification, not just predictor
   floors or LevelDB presence. A stronghold presence bit is not proof of the other
   blueprint floors. Quad-hut farm claims need relation/game-mechanics evidence;
   world-record claims should mean best in the declared evaluated corpus. A pinned
   model/BDS experiment cannot establish support for every Bedrock1.21+ build.

7. **Product choices conflict with existing public policy.**
   Section8 limits Free to the smallest area; section6 removes all Pillar1 worlds
   from Free search via a membership bit, including worlds shared with other
   categories. Existing policy gives Free/Plus identical supported borders,
   observations and score semantics; tiers differ in capacity/convenience. This
   can be changed by an explicit product decision, but must not slip into code.
   Treat pricing/licensing/monetization and five-theme versus eight-category UI
   organization as unvalidated alternatives. Presets need not partition worlds.
   Quotas and watermarks can deter abuse; they do not prove scraping impossible.

8. **Geometry and performance guarantees need evidence.**
   Infinite vanilla is useful presentation: a catalog's observed search area need
   not impose an in-game border. Preserve distinct square/radius meanings and do
   not present informal walking/elytra labels as measured travel time. Border-addon
   execution is a separate integration, not implied by a catalog picker.

   A1024 Nether square matches the nominal scale of an8192 Overworld square only
   with correctly transformed centers; for center976, the Nether center is122.
   If fixed at origin, the corresponding Overworld edge near5072 scales near634,
   outside[-512,512). Even correctly transformed centers do not prove actual
   portal placement obeys an addon border. Remove that guarantee pending tests.

   600M seeds/s,0.01% survival,0.5ms searches,2ms maps,0.9KB/world compression and
   sub110MB total RAM are unvalidated scenarios.60k survivors/s at480KB/s budgets
   only8 bytes/survivor: the seed alone. Seed plus three uint32 masks already needs
   1.2MB/s, before coordinates/framing. The existing CPU reject profile cannot be
   used as public complete-record throughput. O(1) array access describes an
   individual lookup, not full query scoring/ranking/map/API latency.

   Additional arithmetic: all-pillar slots sum to99000 pilot /1016000 production,
   not a demonstrated70000/1000000 unique-world capacity. GroupD production
   19136x3x5 is287040, ten less than stated. These are secondary to schema gaps.

## Recommended path to proceed

1. Reconcile this vision into one CPU-first execution specification; keep
   PUBLIC_CATALOG_SYSTEM_SPEC.md and docs/catalog/v1 as the proposed contract
   authority until replacements are explicitly accepted. Keep Argon's file intact
   as reviewed input. Resolve hard-vs-soft requests, finite radii vs sliders,
   capability activation and tier access before changing their contracts.
2. Implement the separately proposed reference slice: contracts, CPU extraction,
   coverage, separate SQLite/artifacts,243 layouts/world and an independent raw-
   coordinate query oracle. First synthetic fixtures, then at most2 independently
   selected real seeds under<=4CPU threads /5minutes total extraction wall time.
   No personal-survivor filter, production UI, GPU, billing or custom engine.
3. After correctness and measured complete-record cost, approve expansion to100
   worlds; only then size a10000-world reference/retention experiment. Save every
   reference world's observations before testing loss from retention. No automatic
   sweep or assumption all planned features successfully extract.
4. Build a read-only catalog API, eight-category search/detail UI, then free-beta
   request evidence. Use measured workloads to choose batching, optional bitmap
   indexes and later GPU acceleration. A GPU port and new durable engine are not
   prerequisites for the CPU reference or a bounded beta; feasible scale awaits
   measurements. Authentication/security and hosting remain separate acceptance
   work before making a public service live.

Initial reference-slice estimate remains2–4 focused working days after approval;
that is not an ETA for the entire beta, commercial product or10000-world run.
Codex freezes contracts and integrates; High Gemini workers separately own
extraction, storage and summaries/query after interfaces permit independent work.
See ../catalog-cpu-plan-2026-10-20/PLAN.md for acceptance tests and ownership.

## Independent critique and validation limits

High Gemini review7c8bfba0c9fe: gemini-3.8-flash-high --effort high, launch inspected,
exit0, nonempty SUCCESS, no denied actions, no changed files. Raw tool response:
gemini-review.json. Worker ran no commands/tests. Codex independently checked
record arithmetic, distance range, counterexamples and current source/contracts.

Accepted reviewer concerns: lost anchor/radius/count semantics, premature custom
engine, lossy distances, parity conflicts, unsupported retention/performance claims.
Corrections to reviewer overstatements:
- User reports access to16 V100s; calling that fleet non-existent is unsupported.
  GPU implementation is deferred; hardware absence is not the reason.
- Its7173-block corner example lies outside the selected8192-square layout.
  The correct maximal nominal anchor-relative corner distance is~5792.62.
- The document does not establish that every bitmap is origin-relative. The
  blocker is missing per-layout identity, regardless of its chosen global base.
- Existing SQLite/catalog layouts are proposed, not an implemented unified catalog.
  Preserve separate public metadata storage; do not reuse the personal database.
- A submillisecond requirement is not a justified gate for100-world expansion.
  Require correct answers and measured bounded costs instead. A predictor oracle
  is not game-world ground truth; use the existing uint32/squared-distance contract
  rather than introducing a new int16-distance variant without need.

No full project suite, benchmark, BDS world, real seed extraction, deployment or
new implementation ran during this review. Earlier1274 passing tests remain
historical Phase1/2 evidence, not evidence that this catalog has been built.
