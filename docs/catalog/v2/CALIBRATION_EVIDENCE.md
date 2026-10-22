# Measured size calibration and next procedure

User-approved fixed budgets:1250 total, OW845, luxury265, Nether140; Nether square1024.
Existing immutable200-world natural cohort:167development/33heldout. Fixed Origin windows, not optimized centers.
No source data or personal results changed. Native/source identities must match before enrichment.

|Feature|2048 floor/cap|dev floor hits/cap hits|4096 cap hits|8192 cap hits|
|---|---|---|---|---|
|mansion|1/3|6/0 of167|0|0|
|village|6/11|46/1 of167|140|167|
|trial_chamber|8/13|167/143 of167|167|167|
|ancient_city|2/6|35/6 of167|26|148|
|monument|1/4|73/5 of167|89|166|
|outpost|1/4|109/2 of167|64|167|
|mineshaft|10/20|167/166 of167|167|167|

Exact baseline max mansion count is1 in development; absence of higher tiers is sampling evidence, not a universal upper bound.
Stronghold, Nether and four-height OW coverage are missing from legacy observations; do not infer them from zero counts.

Proposed bounded next procedure (within approved calibration scope):
1. Enrich the SAME200seeds with bounded stronghold starts, Nether inventories/biome lattice, and missing three OW planes (-48,0,160) at stride64. No new personal run, seed campaign, BDS or GPU. One serial native child, total600s, RSS4GiB, incremental external checkpoints and immutable source pins. Broader survey observations remain shared once per world.
2. Fit integer floor/bonus thresholds per OWfeature using development-only count distributions. Keep rare presence floors at least1 and optional-feature floor0. Compare empirical survival matching with a feature-specific affine mean/standard-deviation mapping; use the affine prediction to resolve integer ties and unobserved tails, label the statistical modeling explicitly. Reject unsupported zero-variance/zero-coverage fits rather than inventing data. Do not multiply all counts by area.
3. Freeze fitted thresholds BEFORE checking heldout data. Evaluate threshold monotonicity, fixed total/group ceilings, count-bonus saturation and heldout group-score distributions. Report marginal/selected-control statistics separately from unmeasurable joint population rarity; zerojointnaturalqualifiers is not itself a semantic predictor failure.
4. Preserve2048 exactnativecenter/scoring. For larger worlds, do not call existing dynamic.candidate_centers unchanged: it hardcodes min_center=-2000+half,max_center=2000-half, so larger halves produce empty domains. Use declared public candidate centers inside[-1024,1024], with a bounded local event refinement around leading candidates; every qualified result still uses exact saved points at ONEanchor. Make no exhaustive-global-best-center claim. This search-domain choice must be independently reviewed before implementation.
5. Keep Nether rules/local spatial bonus rules unchanged; reuse dynamic_v3_score by mapping OW counts through frozen threshold schedules, leaving all point increments and caps intact. Qualification uses full requestedOWsquare and fixedprojectedNether square; fourYfamilyroles preserved. Verify on qualified personal controls separately; never use winner frequencies to infer unbiased tail rates.
6. Allocate existing P1budget10000 as3334/3333/3333 per2048/4096/8192. Version policies/objectives and checkpoints; no silentextra10000 slots perboard. Largerboards remain gated until measured heldout checks and Highreview pass.
