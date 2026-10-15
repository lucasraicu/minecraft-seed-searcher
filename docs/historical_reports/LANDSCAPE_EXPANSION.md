# Ocean islands and flat mountain basins: work record

User requested a computation audit before edits, a test of seed 12853964 at spawn, and additional ocean island / dry flat mountain-ring searches. Subsequent instruction makes Fortress and Stronghold required and Bastion optional with less scoring influence. The 3008/992 squares stay fixed.

The prior 100-seed pilot and its external accuracy evidence are retained. Its readiness is superseded by the changed requirements; the large sweep remains unstarted. Original verified sources/config/report and readiness record are saved in `runs/landscape-expansion/verified-source-before-changes.zip` and `prior-readiness.json`.

## Audit completed before algorithm edits

Original pilot: 100 seeds, 781 centers, 2474.178 s total (41.24 min), 1890.544 s analysis, 583.634 s reports; eight workers. Throughput is 24.742 s/seed including reports, 18.905 s/seed analysis. Individual worker seed average 139.51 s, median 138.02, range 90.63–220.50. Coast 51.22%, landscape 43.82%, preliminary 3.72%, structure scans 0.84%, discovery 0.29%, scoring 0.11% of summed worker time.

Unchanged seed 12853964 with observation overhead: 129.01 s; 8 candidates. Height stride 8: 471628 calls to point computations, 35486 duplicates (7.52%); stride 1: 92523 points, 5742 duplicates (6.21%). Exact coast land: 263244 points, no same-operation repeats; 10155 points overlap stride-one height samples. Detailed evidence: `runs/landscape-expansion/baseline-12853964.json`.

Reports recompute full terrain for shortlisted candidates and regenerate maps on refresh/resume. The cost is measurable and avoidable using persisted terrain and content-keyed maps. Structure scans already run once per seed/envelope. Scoring is negligible. Sharing cached values across different seeds, dimensions or height strides would be incorrect. Approximate-height land classification cannot replace exact coast connectivity.

The supplied screenshot's source is https://www.reddit.com/r/minecraftseeds/comments/1d3ivlr/ . It describes a 1400-square majority ocean-biome filter followed by non-Deep-Dark 64-square / mostly Deep-Dark 200-square at Y=-32. This is a candidate hint, not proof of terrain, isolation or flatness. Original demonstration is Java 1.20.1, so current Bedrock terrain and structure checks are required. Actual matching-version Chunkbase predicts spawn at (0,0); (0,0) is Snowy Slopes Y149, nearby (-128,-128) is Plains Y71.

## Expanded implementation

The measured bounded per-seed exact cache is enabled. Three separately ranked branches retain enclosed islands and add ocean islands and dry flat mountain basins. Fortress and Stronghold are required, Bastion is optional, and exact squares, finite budgets and unresolved predictor evidence remain explicit.

## Supplied Cubiomes guide and implementation blueprint

The Google Docs guide was read through its actual browser export and saved as `runs/landscape-expansion/cubiomes-user-guide.md`. It discusses Cubiomes Viewer 3.2.1 / Java 1.18+, so its optimization principles apply more broadly than its placement shortcuts. The staged filtering, coarse nomination before fine terrain, spatially referenced structure queries and measuring useful survivors are applicable. The screenshot's majority-ocean and underground contrast are now nomination/ranking hints, followed by density terrain and coast connectivity; neither biome labels nor Deep Dark alone establish the landscape.

| Blueprint suggestion | Decision for this project |
|---|---|
| Python + compiled Bedrock fork | Already implemented with typed CFFI and an opaque native context. Keep the pinned fork and supported build rather than changing to ctypes with a guessed Generator layout. |
| `getStrongholdPositions` / `isFortressPos` | Neither symbol exists in the pinned headers. Use the existing Bedrock static/village-associated Stronghold enumeration and region placement plus viability. `setupGenerator` also needs the third flags argument. |
| First three concentric-ring Strongholds | Java-specific rule; do not apply it to Bedrock. Missing local Strongholds remain reviewable because the saved comparison proves incomplete enumeration. |
| 3000/900 squares at spawn or Stronghold | Preserve the user's exact 3008/992 squares at the chosen land center and its exact center/8. A 900-block Nether window has half-width 450, not 56; do not divide a Nether distance by eight again. |
| 18 processes and 50000-seed chunks | Eighteen physical cores do not establish optimal worker count. Keep the measured eight-worker recommendation, disable numerical-library nested threading, and checkpoint/stream each seed. Native point batches are already bounded; 50000 expensive seeds per pool item would obstruct timely progress and resume. |
| 70% peak-biome circle and flat center | Added dry flat mountain-basin branch with actual sampled height, relief, slope and connected ground, plus mountain bearing coverage. Biome membership alone does not prove height/flatness. |
| Peak/meadow/grove integer IDs | Blueprint swaps several IDs. Pinned headers have meadow177, grove178, snowy_slopes179, jagged_peaks180, frozen_peaks181, stony_peaks182. Code uses backend names. |
| 100% deep-ocean outer samples | Use majority ocean in a 1400-square window and exact coast separation; shallow/cold/lukewarm ocean can surround valid islands. A few radial biome samples cannot prove full separation. |
| Secondary structure placeholder | Real scoring already covers Trial Chamber, Stronghold, Mineshaft, Ancient City, Village, Ruined Portal, Shipwreck, Monument and Outpost. Fortress/Stronghold required; Bastion gives a small optional bonus. |
| Print critical matches immediately | Existing parent-owned streaming completion/checkpoint and ranked packets retained. Local predictions stay distinct from fresh website-supported candidates and actual Minecraft evidence. |

Native API and IDs were checked against local pinned sources and the primary upstream headers:
https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.h
https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/generator.h
https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/biomes.h

## Exact computation reuse and tests

Implemented a bounded 64 MiB per-seed, per-worker exact tile cache. Heights are keyed by stride/scale/coordinates; land queries have a separate cache. Values never cross seeds or approximate/exact operations. Report terrain is persisted with predictor/configuration/content identities and integrity checks; unchanged PNGs are reused with hashes. Changed reviews invalidate maps, and damaged caches fall back to recalculation.

Controlled alternating A/B: identical six-center predictions for seeds12853964 and0; 160.2392 seconds uncached versus150.8928 cached, a 5.83% analysis reduction. This is a single-process legacy-workload comparison, not a universal throughput claim. Evidence: `runs/landscape-expansion/cache-ab.json`. The final full suite covers 99 tests; frozen external regression remains874/880 unique typed correspondences, six known disagreements, zero reused starts;153/159 biomes and one-block height MAE (maximum five). Tests cover exact cache semantics/eviction, optional Bastion policy, missing Stronghold review, three landscape branches, dry floor versus water moat/steep ground, finite bounds, report integrity, actual renderer cache reuse and real interrupted/resumed worker variation.

## Fresh expanded-workload browser evidence

Four candidate reviews use actual Chunkbase Bedrock26.50–26.52 UI with Terrain and both dimensions. Seed12853964 near predicted spawn is detected as an ocean mountain island (localD604), with website Stronghold(228,-828) and Fortress(155,11) inside the exact squares. Its western build core and small central caldera do not establish a broad flat floor; it remains a checked buildability near miss. Actual Terrain has a longer southern appendage than the raw-density coast model, so local dimensions/isolation are predictions.

The southern ocean island on12853964 at(0,960) has gentle low forest ground and nearby wood; website Stronghold(-1292,1396) and Fortress(155,11) fit both squares. It needs tree clearing and does not meet the open-island/mountain-circle preference. Independent positional holdout4294979641 at(-2304,-4480) shows a compact separated ocean forest island with usable rolling ground; Stronghold(-1116,-5324) and Fortress(-469,-853) fit the exact borders. Neither is advertised as an ideal dry flat mountain basin. Top-ranked3471015484745077182 at(4432,-2080) has supported island/ocean/wood geometry and required markers, but uneven heavily wooded build ground remains unresolved rather than being promoted merely for its score.

Seven unique newly reviewed required structure markers all have the established type-specific native correspondence. Five newly retained terrain points match5/5 biome labels; raw stride-one height MAE2.6 blocks and maximum9. The nine-block discrepancy is the snowy mountain point12853964(-208,32): Chunkbase154, local145 across strides1/4/8/16. It is not a cache or resume discrepancy; raw density excludes actual chunk interpolation/caves/aquifers/decoration, and exact game ground remains unknown. The historical baseline's maximumfive was a bounded sample, not a universal error bound. Keep the new larger observed error visible in terrain estimates and final review. New data are saved separately in `fresh-prediction-comparison.json`; no tolerance was widened to hide it.

Actual Terrain control12853964(1792,-960) shows ridges/uneven ground, a nearby pond and an incomplete enclosing ring. This supports the fine dry-basin rejection (gentle fraction0.204, relief36.3, ring0.139). A separated upper-bit ocean-island control and the user's small-floor mountain island are separately retained. These are qualitative geometry checks with another predictor; they do not prove block-level isolation, trees, access or complete recall.

The first20-seed pilot and ten-seed repeat exposed a floating-point score-order discrepancy when YAML configuration is restored from sorted checkpoint JSON. Terrain/structures/centers/metrics/cache counters/rejections matched; only score endpoints differed around1e-14. Scoring now uses a canonical order and a dedicated checkpoint-serialization test covers totals, intervals and unknown components. The new current-source20-seed checkpoint/resume run exactly matches the independent ten-seed repeat across57 candidates plus rejections, metrics and cache counts. Earlier runs remain diagnostic evidence; predictions were not rounded to make the comparison pass.

Final renderer verification exposed a shadowed cache key, which prevented PNG reuse even though terrain reuse worked. A distinct cache key fixes it generally. A renderer-level regression and full report refresh prohibit native height/biome queries and plot creation, and require every copied PNG hash to match. Changed review/configuration/predictor/renderer or corrupted images still invalidate reuse.

## Measured expanded pilot

Twenty input seeds produced114 scored locations in387.62s (6.46minutes):328.51s analysis and59.11s initial/checkpoint/final reports. Effective throughput19.38s per input seed; individual worker mean96.39s, median96.14s, range64.34–131.16s. Coast39.20%, landscape34.09%, preliminary24.56%, structures1.21%; eight processes actually ran during resume. Peak parent631.04MiB and individual worker400.01MiB are separate process peaks.

There were58 enclosed-island and56 ocean-island scored locations,95 locations with both required structures, and93 with all three preferred core Overworld structures. Four fresh reviews yield two website-supported ocean candidates, one checked near miss and one unresolved buildability case. No dry flat mountain basin passed; its positive quality/yield and the time to find twenty worthy seeds are unknown. Twenty input seeds are a bounded implementation sample, not twenty compatible matches or an unbiased yield estimate. The future finite2000-seed command is documented in SWEEP_READINESS.md and remains unstarted.

Final report reuse proof: all 152 PNG hashes unchanged in 1.09s, zero native height/biome queries and zero plot redraws. Full suite99 passed in78.16s. Current evidence-derived readiness and the exact2000-seed launch dry run from/tmp pass; no sweep output directory was created.
