# Continued predictor investigation

The targeted catalog correction remains intact. This continuation establishes
better biome counterexamples, not a general production fix. Cave-boundary and
general village/outpost rejection rules remain unresolved.

## New biome evidence

A frozen four-chunk domain uses 128 columns and 8,320 stored block positions across
two existing seeds, with discovery, spatial-holdout and seed-holdout groups.
An isolated diagnostic sampled 3,920 unique quart nodes. An independent Python
implementation reproduced all614prior native Java-Voronoi outputs before use.

Initially eight named stored points could not be produced by selecting any of
27adjacent native nodes. Direct stable BDS checks confirmed all eight at exact
XYZ; 25total direct reads including ±12Ycontrols agree with the saved data.
The previously unmapped stored ID1 is `plains` in the recorded second world/copy,
completing the same fixed dataset's name associations. It now contains30such
stored-data counterexamples; nine were among the direct game reads. This does not
mean all8,320points or all30counterexamples were individually queried by BDS.

| Group | Stored points | Raw quart matches | Java block matches | Removed-offset block matches | Name carried by any27nodes |
|---|---:|---:|---:|---:|---:|
| Discovery, seed1 | 4,160 | 3,861 | 3,800 | 3,815 | 4,158 |
| Spatial holdout, seed1 | 2,080 | 1,859 | 1,868 | 1,863 | 2,079 |
| Seed holdout, seed2 | 2,080 | 1,846 | 1,838 | 1,903 | 2,053 |

These are targeted biome-boundary samples, not representative world accuracy.
The result excludes a bounded class choosing from floor(block/4)+[-1,1] labels.
It does not distinguish wider/anisotropic grids, wrong climate inputs/table,
or other postprocessing. Expanding vertical candidates from3to5 can carry the
original missing labels, but simple4×8×4parents fail other known points. The
broader mechanism remains uncertain.

The eight original cases also fail direct continuous noise and trilinear climate
interpolation; all nine paired named controls pass those center variants. Current
native tree classification agrees with exhaustive distance across7,776leaves;
none of these centers has a tied best biome. Do not patch global Yoffsets, jitter
hashes, tie-breaking or interpolation merely to improve one aggregate score.

## Structure findings

The review's proposed Grove/Frozen Peaks rejection was contradicted by current
source: `isViableFeatureBiome` explicitly accepts both for 1.18+ Outposts. The
negative outpost's sky sample is Frozen Peaks, so calling this a sky-to-surface
biome bug is unsupported. Official village documentation describes the village
biome component, but does not establish a terrain-slope rejection threshold.
[Village generation documentation](https://learn.microsoft.com/en-us/minecraft/creator/documents/managing-villages?view=minecraft-bedrock-stable).

Predicted start-piece footprints often cross absent neighboring records: negative
village72/99availablecells, positivevillage81/396, negativeoutpost15/225. Only the
positiveoutpost is fully covered225/225; its saved heightmap delta is22. The
negative village's covered region has delta24, while covered positive examples
already show13–22blocks of variation. These post-generation maps include structure
changes, so they cannot validate a6-block original-terrain threshold. Footprint
anchors/variants also need independent Bedrock confirmation. No universal slope/city/height veto was implemented.

The static stronghold remains confirmed; no further rejection changes there.
Current native source's terrain check handles temples and returns success for
other types. Pending upstream PRs reviewed concern temples/monuments and mansion
positions, not an established fix for these village/outpost cases.
[Upstream pull requests](https://github.com/FragrantResult186/cubiomes-bedrock/pulls).

## Delivered and verification

New `scripts/biome_node_probe.c`, optional `--mode nodes` in the existing external
builder, separate hashed predictor-mechanism fixture, and regression tests.
Neither serving native code nor published catalog data was changed. Native helper
limits (4096rows, strict signedseed/coordinates/trailing text) were checked directly;
the portable build exactly matched all3,920recorded node outputs.

Two new stable-API world copies consumed25biome/28block reads,0locates,28.10seconds
gamewall; both clean saved/stopped/removed. All original saved worlds stayed unchanged.
No random seed search, serving restart, GPU or database changes occurred. The
personalSweep60144 remained active. The earlier catalog/Vite preview processes
were absent on reconciliation and were not restarted. BrowserQA remains deferred.

85focusedtests+14subtests passed; the external native builds,3,920node parity,
parser limits, standard-library replay and direct BDS checks passed. Final High
review9b20307c3367 found no critical defect; it ran no tools/tests. Codex separately
verified runtime results. Preservation found only the intended existing diagnostic
builder/doc edits, no native/serving-source changes, and the sameHEAD/catalogSID/
personalrun. Full details are in CONTINUATION_RESULTS.json. The full native-correction objective remains partially unresolved.

## Next executable correctness work

1. Use the compact9directcounterexamples and full8320frozen plane as acceptance
   evidence for an independently justified Bedrock depth/climate/zoom algorithm.
   A new phase/window fit alone is insufficient; preserve the existing positives.
2. For structures, obtain complete original-terrain/actual-start footprint controls
   across independently located positive villages/outposts, including high terrain.
   Do not estimate a universal threshold from one known negative or modified terrain.
3. Integrate only a causally supported, High-reviewed, isolated native change with
   held-out parity and a new source identity. Until then retain the existing
   evidence-aware catalog and versioned exclusions, with no accuracy promotion.

Model/version boundary: the native model is labeled research26.50; the observed
game build is1.26.52.3. These results do not decide whether the discrepancy is a
version-compatibility change, climate data difference or sampler/postprocess issue.
No public game-build acceptance is implied.
