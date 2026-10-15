# Approved implementation status — 8 October 2026

Core source changes are implemented: geometry 2304/928, four category routing, mandatory Stronghold/Fortress, weighted biome bonus, exact quart land reuse, corrected MT initialization, lattice-safe basin bounds, atomic reports and deterministic low32/upper32 checkpoints. The default remains full64 reference; both enumeration modes are available.

Implementation and bounded verification are complete under `runs/implementation-2026-10-08`: two independently predeclared run keys × two 256-input modes; three alternating-order 20-seed quart trials; 1/8/12-worker resume checks; bounded review_all recovery; exactly matching 20-seed map pilot/repeat and refreshed readiness seal. Reference saves 9.2% measured CPU versus staged across the two-key comparison and has greater predicted category yield per CPU-hour in every category/key. Quart reuse saves 26.4% median wall / 25.0% CPU with exact parity. Sweep commands and 3–5 hour reference / 35–50 minute staged ETAs: [SWEEP_COMMANDS.md](SWEEP_COMMANDS.md). The final unit/native suite passed 141 tests in 102.23 seconds. Frozen 880 structure / 159 coordinate regression matches the explicit baseline; six known disagreements remain. A private Stronghold trace was recorded without installing coordinate exceptions.

Fresh matching-version Chunkbase marker evidence was saved for seeds 12853964 and 4294979641, including high bits and negative coordinates. Marker evidence is distinct from landscape suitability and actual game observations. No real mountain-basin positive is claimed. Early island bounds stay in shadow mode; production SIMD stays deferred after the recorded test. **No production sweep has started.**

The historical status log follows; its readiness packages and geometry are superseded.

---

# System audit and next implementation plan — 8 October 2026

Audit complete; production changes and sweep unstarted. The user approved a future 2304/928 geometry, lower32/upper32 search mode, and four categories: structures-only, enclosed inner island with water/mountains, ocean island, and dry flat mountain basin. [SYSTEM_AUDIT.md](SYSTEM_AUDIT.md) records code/online-source findings; [AUDIT_IMPLEMENTATION_PLAN.md](AUDIT_IMPLEMENTATION_PLAN.md) specifies changes, acceptance gates and the updated 26–48 hour implementation reserve, including weighted biome diversity across all four categories, a safe early-island-bound experiment and the newly demonstrated MT initialization fix; [SEED_SELECTION_WORKFLOW.md](SEED_SELECTION_WORKFLOW.md) explains each stage and structure policy. Only Stronghold and Fortress are mandatory. Structures-only will have its own qualifying list; failed terrain never qualifies for its original terrain category.

Requested pre-implementation native test complete: [SIMD_TEST_RESULTS.md](SIMD_TEST_RESULTS.md). Thirty-six complete-seed analyses measure 28.1% aggregate saving from exact land reuse, only 2.6% additional strict-AVX2 saving after reuse, and 1.2% slowdown from the four-Y SIMD prototype after reuse. Gemini flags change 1162/6144 raw-density samples. All retained variants pass the frozen regression and match their same-trial scalar controls, but six repeated -1 cases reveal a production MT initialization defect: cold Mineshaft results differ from warm results. The unchanged installed binary independently reproduces it. Fix this before optimization/readiness; the known Stronghold issue remains separate. No production optimizer, fourth category, border migration, or staged search was installed.

Fresh audit verification: 112 tests passed in 77.91 seconds; frozen regression retains 874 unique correspondences and six known disagreements. Isolated exact density-cell reuse preserves full seed-12345 candidate/decision records and reduces serial profiled analysis 65.51→39.72 seconds; no production optimization was installed. A 256-layout low32 diagnostic at the initial 2304/640 target rejects none using raw Fortress existence, even with joint optional Village/Bastion existence. Larger caches have no measured eviction problem in the old 20-input pilot. Synthetic cases expose nondefault 64-spacing basin lattice rejection and inconsistent ranking after unconfirmed required-marker review. Evidence and reproduction commands: [audit work record](runs/system-audit-2026-10-08/WORK.md).

The previous readiness package is historical for 3008/992, and updated documentation invalidates its hashed manifest. New geometry, mode, evidence and launch commands must pass fresh readiness before any sweep.

# Historical filter optimization — complete, 8 October 2026

Implemented and verified the user-requested shortcuts and fast Stronghold screening. Stronghold/Fortress joint-window checks precede expensive terrain; incomplete predictions are deferred with recovery exports. Combined native enumeration, bounded typed raw-MT caching, conservative basin bounds and shared raster intermediates are complete. All 112 tests and the frozen external regression pass. The 20-input pilot has 96 predicted-required locations; all 95 common qualifying prior locations retain identical complete candidate records. Independent 20-input runs match exactly across checkpoint/resume and 8 versus 12 workers. The controlled 12-worker run saves 9.01% analysis wall time. Fresh Chunkbase follow-ups confirm required markers for two ocean controls, preserving original geometry evidence and prediction limits. The exact finite 2000-input command passes dry-run validation from /tmp, and missing/tampered/stale readiness and over-budget requests fail. Current package: `runs/filter-optimization/readiness.json`; prior identities are superseded. The large sweep remains unstarted. Details: `SWEEP_READINESS.md`, `FILTER_OPTIMIZATION.md`, and `runs/filter-optimization/WORK.md`.

# Historical completed landscape expansion goal — 7 October 2026

The expanded search and required verification are complete: 99 tests, frozen external regression, a 20-seed end-to-end checkpoint/resume pilot, an exactly matching independent ten-seed repeat, actual matching-version Chunkbase reviews and the evidence-derived readiness gate. Three landscape branches are implemented; Fortress and Stronghold are required, Bastion optional. The current finite 2000-seed launch and resume equivalent pass dry runs from /tmp, and no large-sweep output directory exists. This sample supports two ocean candidates and contains no accepted dry flat mountain basin; no positive basin yield or game-level accuracy is claimed.

Current measured details, remaining limits and commands: [SWEEP_READINESS.md](SWEEP_READINESS.md), [LANDSCAPE_EXPANSION.md](LANDSCAPE_EXPANSION.md), and `runs/landscape-expansion/readiness.json`. Pilot 387.62s for20 inputs/114 locations, exact-cache A/B saving5.83%, unchanged full report refresh1.09s/152 identical PNGs with no native queries/redraws. Original sources/evidence are preserved; prior readiness is superseded. The large sweep remains unstarted.

The following records describe the prior completed implementation and its history.

# Sweep readiness progress

Persistent goal created 2026-10-07. Objective and completion criteria: SWEEP_READY_HANDOFF.md.

## Current state

- Sweep-ready implementation and required verification complete; final readiness seal verified before native-goal completion/notification.
- 80 meaningful tests pass; additional gate checks pass. Supported native build, all 33 vendor/license hashes and 21 locked package versions verified.
- Frozen external 159 coordinate/880 structure rows repeat without exact local drift;874 typed correspondences and six managed discrepancies remain explicit.
- Current 100-seed checkpoint/resume pilot completed: 781 centers, 287 all-three-core centers, eight actual processes, 41.24minutes including exports.
- Four independent holdout both-dimension Chunkbase reviews plus one separate calibration near miss/two Overworld controls saved. One supported candidate, one holdout near miss and two unresolved holdouts; no actual-game evidence invented.
- Exact finite2000-seed start flags and resume flags tested; current readiness record validates source/test/evidence identities, exported statuses/maps and finite budget. Large sweep remains unstarted.

## Ordered work

1. Complete: edition/model/capabilities/configuration/review-policy alignment.
2. Complete: immutable baseline regression and per-type marker conventions.
3. Complete: structure diagnostics and tested visible disagreement review.
4. Complete: density topology/coasts, water/mountains/wood/openness and explicit unknowns.
5. Complete: deterministic multi-center scoring/ranking/search/reports and strict resume.
6. Complete: measured initial/repeated ten pilots and finite 100-seed expansion, within recorded budgets.
7. Complete: new matching-version website both-dimension candidate/near-miss and rejection-control checks.
8. Complete: readiness package, exact finite command dry-run and evidence gate checks; final completion notification is sent only after the seal check.

Keep new evidence under runs/sweep-readiness and fixtures/bedrock-26.52; do not rewrite historical observations.

## Implementation milestone

- Configuration and metadata now enforce Bedrock 26.52 -> MC_26_50, fixed squares, full seeds, separate website/game evidence and implemented methods.
- Frozen regression command reproduces all 159 coordinate and 880 structure rows: 874 unique type correspondences, six explicit known disagreements, no reused starts or changed exact local predictions.
- Native diagnostics expose Bastion rotated-piece quart samples and Ancient City Y=-27 quart sampling. Evidence saved in runs/sweep-readiness/structure-diagnostics.json. No unproven generation-rule or coordinate-exception change.
- Search implements cheap whole-possible-center Nether screening, raw rejection review, bounded multi-center coast/landscape analysis, one-block adaptive coast continuation, all configured scores, distinct-seed lists, maps/JSON/CSV, SQLite checkpoints and strict resume identity.
- A meaningful one-block bridge regression caught and corrected shoreline-band truncation. 57 tests now pass; test suite includes real bounded process search/resume and frozen external regression.
- Direct native build verification underway. Next: measured initial ten-seed pilot and actual fresh Chunkbase selection/near-miss review.

## Finite pilot budget before launch

Initial workload: automatic indices 0..9, full default center envelope, four spawned workers, at most eight refined centers per seed. Allow up to 15 minutes for this ten-seed end-to-end measurement, including regenerated shortlist maps. This is a bounded pilot, not the large sweep. Any expansion to 100/1000 unique seeds must first use this measured runtime/yield and record a further finite budget.

## Pilot diagnosis and measured optimization

The initial ten-seed core pipeline completed all indices 0..9 with four actual process workers. Per-seed complete analysis took 101–330 seconds; full report/map export is finishing. Candidate quality is not yet established: the first fresh new-seed review supports isolation and both required Nether markers but shows weak mountains, so it is recorded as a calibration near miss.

CPU profiling of a real worker and per-stage timings identify density columns as the dominant cost. Implemented an exact raw-density land classifier: scan Y=63..319 upward, stopping on the first solid density. This is mathematically equivalent to `stride_one_height >= 63` within this model, including overhangs; no monotonic-density shortcut or weaker landscape assertion. It avoids computing unused full heights/biomes for every one-block coast column. 1,200 independent random columns over four seeds pass equivalence tests; a larger bounded timing/equality comparison is underway.

Added the missing preliminary 16-block density topology stage before expensive one-block coasts. It can review up to 32 coarse components and selects at most eight refined coasts using density area rather than cheap-proxy area. Finite/clipped/budget rejections remain explicit. Numeric preferences, weights and all fixed requirements remain unchanged. 73 tests pass after the optimized native rebuild.

## Next bounded pilot budget

The first full ten-seed run completed with maps/reports. An exact optimization comparison tested 30,603 columns on three seeds with identical masks; local classification speedups were 1.32×–2.87×. This is a stage measurement, not an invented full-pipeline speedup.

Before any 100-seed expansion, rerun the same ten unique seeds through the preliminary-topology/optimized-coast pipeline with eight processes. Finite budget: 15 minutes including shortlist exports. This repeat validates the changed stages and measures actual worker behavior; it does not expand seed coverage or start a sweep. Keep the initial pilot artifact/version separate from the optimized pilot.

Prediction/checkpoint identity now hashes all prediction, configuration, seed, evidence-policy and persistence modules plus native source/binary/vendor provenance. Report rendering, CLI presentation and readiness assembly are verified separately in the final evidence manifest. This avoids invalidating completed predictions for a plot/title or readiness-packaging change, while algorithm/config/backend/seed changes still reject resume. The early optimized pilot records the prior broader identity format; the final measured pilot and resume proof will use the current identity format.

## Current-identity pilot and finite expansion budget

Optimized ten-seed repeat: 74 centers, 29 centers with all three core Overworld starts; eight actual worker processes, max individual worker RSS 130.5 MiB. Analysis wall 249.95s plus measured map export 122.63s = 372.58s total, 37.26s/seed for this workload. Corrected invocation wall accounting to include complete export, and added parent peak RSS. The old invocation wall excluded map export; old stage timings remain valid and the total above explicitly adds the saved export cost.

Fresh second-seed review shows a separated steep forest/stony island with surrounding mountains, but buildability remains uncertain. Candidate quality is not yet established. Before expansion: authorized finite current-identity pilot of indices 0..99, eight workers, maximum 60 minutes including reports, checkpoint after the first ten completed seeds. Initial ten repeat validates current checkpoint identity and true end-to-end accounting; resume adds only 90 new unique seeds after reviewing measured timing. The estimate is workload-specific (100×37.26s plus checkpoint export overhead ~64 minutes); analysis scaling suggests ~45 minutes, so stop and diagnose if the 60-minute budget is exceeded. No broad sweep is started.

## Evidence gate and review-path verification

Readiness now derives checks from the completed current-identity checkpoint, invocation timings/RSS/process IDs, frozen external comparison, deterministic prediction hashes, actual fresh review outcomes and recorded command verification. It rejects an incomplete source/test/evidence hash manifest even if all booleans say true, and detects artifacts changed after verification. A bounded positive candidate-quality check remains required; current holdout seed 2185194620014831856 is explicitly unresolved for settlement buildability.

Added tests for resolving a rejected raw Bastion via exact website markers without inventing local viability or game evidence; website markers one block outside the square remain ineligible; unknown buildability remains unresolved; surrounding woodland denominator excludes water and island supply; distinct-seed ranking honors mountain tie rules. 78 tests pass before the additional manifest/tamper test. Pilot checkpoint-after-ten is exporting reports.

Current-identity first-ten checkpoint completed: 359.65s total including117.17s reports, analysis242.49s, eight actual processes, max worker126.22MiB and parent459.14MiB. All74 candidate predictions plus rejection/count fields exactly equal the uninterrupted optimized ten-seed run (only measured timing/RSS/PID excluded). Resume CLI dry-run passes and sees ten completed indices. Resume the remaining90 indices with eight workers within the previously recorded60-minute combined budget; expected about35–45 minutes including final maps based on measured analysis throughput and report depth. Prediction hash/equivalence proof: runs/sweep-readiness/resume-proof.json. No large sweep launched.

Frozen current sweep configuration copied byte-for-byte to runs/sweep-readiness/config/sweep.yaml. The CLI parses the finite sweep flags in a one-seed dry-run equivalent (no output directory created). A10,000-seed dry-run with those flags and no readiness record is correctly rejected with exit2. Doctor and pip dependency check still pass. The full sweep command will be dry-run again through the evidence gate after all requirements pass; no sweep run directory exists.

Small-envelope real-pipeline check recovers seed0 center(-3456,-3080) in19.94s. Strengthening the varied-worker resume regression to compare actual scored candidates (one versus two processes), rather than only no-island execution paths. Additional supplied-seed rank CLI smoke budget60seconds, one already-tested seed, center axes[-4000,-3000], one refinement and full maps; this checks supplied-seed input/export independently and adds no new seed coverage.

Fresh positive holdout candidate: seed514794171988716146, center(-4424,3688), local equivalent diameter295.2 (soft300–700 preference remains unchanged), open Plains land, external woodland0.485, water enclosure1.0, median gap88, high-terrain directional fraction0.322 (preferred0.75 unmet). Actual fine Terrain screenshot shows a full continuous channel including the narrow northwest side, gentle useful terrain, external forests and nearby high terrain/scarps. Both required Nether marker types independently observed inside the exactsquare; the chosen Bastion is comfortably inside, while another sits13blocks from an edge and remains a footprint/access risk. This supports candidate selection at website-prediction scope; no actual game/tree/footprint evidence invented.

Three holdout both-dimension reviews are now separate from one calibration near miss and two Overworld-only geometry/filter controls. Fresh review data imported into the pilot so its final export will expose supported candidates separately. At the current checkpoint every derived readiness check except complete end-to-end100-seed pilot is passing. Readiness is not marked ready while that bounded run remains unfinished.

All100 pilot seed analyses finished; full report export is underway. Final meaningful suite:80 tests pass, including missing Stronghold/rejected Ancient City as unknown preference intervals without rejecting required-Nether-eligible islands. A new test initially referenced the wrong result-key name, was corrected to the implemented completeness field, and the complete80-test suite reran cleanly.

The fifth reviewed seed7300246764159736452 has an excellent water/mountain setting but remains unresolved for the narrow Stony Shore neck. Five live website neck samples showY39/46 and62/63 despite stone-colored land-like rendering; all eight new retained coordinate samples match biome labels, heightMAE1,max3. This is a predictor-level sea/shore ambiguity, not an established dry bridge, not a falsely confirmed isolated island. Both required Nether marker types were independently confirmed inside its exact square. Four holdout both-dimension reviews plus one historical-configuration calibration review are retained separately; two original Overworld-only filter controls remain separate.

Report grouping now keeps explicit website rejection outcomes in near misses and preserves unresolved reviews; website-supported candidates have their own distinct-seed list/maps. Need final review CLI refresh after pilot export so all four holdouts are present in exported status/maps, then final identity/evidence gate, runtime package and command validation. No broad sweep started.

Complete100-seed pilot export finished. One final report issue found: earlier shortlist folder ordinals could remain after resume, even when the current rankings changed. Report refresh now archives the previous generated shortlist under report-history and creates a clean current view. This preserves prior evidence while preventing stale candidates from appearing as current selections. Rerunning the meaningful suite for the final source state, and invoking the actual review CLI with all four holdout records. Finite refresh budget15minutes, no new seed analyses/coverage; record its duration separately from pilot throughput.

Measured100-seed totals:781 scored centers,100 seeds with predicted both required Nether starts,287 centers with all three core Overworld starts. Two invocations total2474.18s (41.24min), analysis1890.54s, reporting583.63s. Actual8-worker maximum individual peak244.10MiB and parent1062.86MiB. Exact finite sweep budget chosen2000 seeds, indices 100..2099; estimates about10.7–13.7h,1.5× envelope16–20.6h, excluding external review. Host verified18physical/36logical Xeon W-2191B,64GiB RAM. Decoded100-seed result object size114.98MiB;2000-seed scaling2.25GiB, four-buffer allowance9GiB plus approximate3GiB worker/report overhead. Limit2000 as initial finite pass to bound wall time/export memory, instead of10000. Source/config preferences unchanged; large_search_enabled remainsfalse. Tiny command parsing and expected missing-readiness rejection retested for the exact2000-seed output path; completed-pilot resume dry-run passes.

Gate additionally ties maximumcount and saved start/resume commands to their hashed command evidence, and checks current exported review statuses, distinct list seeds, packet counts and both PNGs. This prevents a ready flag with stale pre-review outputs or an enlarged budget from passing. Final review refresh still underway; no ready record issued yet.

## Final verification

Current active shortlist has 61 complete packets/maps, with prior generated views archived. Review CLI refresh passed in 472.16s without new seed analyses. Frozen configurationSHA256 is 2e588a59bc0e9a0962d5eb2555849b7e9c93cadcb8d576bddc0e83c9e317894e. Exact 2000-seed command passed evidence-gated --dry-run from /tmp and created no sweep output directory. Modified readiness records with enlarged budget, changed artifact hash, unready status or wrong backend identity are rejected. All proof artifacts and managed limits are in SWEEP_READINESS.md and runs/sweep-readiness. Completion notification is the final shell action; large sweep remains unstarted.
