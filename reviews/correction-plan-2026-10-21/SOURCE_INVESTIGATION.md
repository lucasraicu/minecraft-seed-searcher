# Source investigation and approved corrections

BDS reference is the pinned Linux 1.26.52.3 binary SHA256
`0a490c711d4a2ce075debcd979e8862b7eaba008373f9970f0edbb67f98f9207`.
Disassembly and standalone probes are retained externally under
`~/.local/share/antigravity-worker-mcp/correction-plan-20261021/`.
The user approved B_NATIVE_PROPOSAL.md after High review, before implementation.

The Nether constructor at515fdd0..5161a90 constructs a Pos2d climate source and
Zoom4xVoronoi node, vtableee9df88. The constructor's layer salt is
`getLayerSalt(10)`; seed initialization retains the full64 bits. Range51a1ef0
subtracts two and floor-divides X/Z by four. Jitter51a1f60 uses the classic
quadratic LCG, ten-bit binary32 offsets with amplitude3.6. The original chunk
state supplies X and the next state supplies Z. Scalar register ordering initially
led to an incorrect diagnostic prototype; V1 remains preserved, V2 corrected the
ordering before freezing the new game controls. Y is absent from this selector.
The raw Nether climate function already fixes Y to zero; scale4 continues to
return that raw quart source. The new generator route is only MC_26_50 scale1.
Explicit float rounding prevents contraction; strict corner comparisons preserve
the source's fallback. Integer-edge inputs that cannot represent the source's
subtract-two/corner arithmetic return an error; normal world coordinates fit.

Ancient City feature4e3e390 calls containsOnly at the chunk origin, exactY=-27,
radius0. Sampling the raw navigation center instead can select a different biome;
rounding -27 to a quart plane is another discrepancy. The new gate samples the
raw chunk-origin node at exact blockY. It retains the Deep Dark requirement.
Public jittered getBiome observations are not the same oracle as this raw gate.

Bastion helper4fd0b70 calls the Pos2d containsOnly implementation51a2f00 at chunk
origin, Y1, radius2. Its inclusive quart rectangle covers the four cells just
before/on the chunk origin. The old variant-center sample could lie in basalt
while the actual gate rectangle passes. The correction keeps the existing biome
allowlist and shared fortress/bastion RNG selection. getStructurePos already
selects fortress versus bastion; failed bastion viability does not introduce a
new fortress candidate. Frozen800 raw selection records cover400 regions.

Fresh controls were frozen before game execution: two SHA256 seeds and their
bit40/bit32 partners, disjoint from the original24 worlds. Eight fresh default
stable-API starts completed in87.98s, all saves/shutdowns/container removals clean.
Nether:100/100 corrected matches versus73/100 old. These comprise60 fixed points
and40 deliberately selected disagreement/neighbor points, across16/64/112heights.
Paired seeds are correlated. These observations support the mechanism; they are
not a random-population accuracy estimate. All13 proposed-positive query controls
locate exactly, including four previously missed bastion references and one city.
The16 other locates include discovery queries/different references; they do not
prove absence. Existing diagnostic reanalysis also matches216 original Nether
points and the default/Beta copied-world rechecks. No new volume census occurred.

Portable `source-corrections-v1` fixtures preserve the manifest, reports, console,
settings, observers, prototypes and legacy controls. Existing audit evidence is
unchanged. The actual isolated O3 CFFI matches100 new points and13 positives,
preserves8320 stored/330 direct Overworld controls,51 older positives,2 negatives,
14 restored villages and95 outpost cases. Of3411 original block predictions,
exactly3 change, all the previously failing Nether coordinates for one seed.

Overworld cached lookup remains a distinct semantic boundary. Existing dynamic
stored-volume decoding explains21 runtime rows in one chunk; its Y95 bound is
local to that stored chunk. No global Y95 clamp is implemented. The procedural
raw model cannot promise arbitrary-Y stored-runtime equivalence from this witness.
The catalog's declared biome witnesses remain Y63/stride64, not every block.
Temple subtypes, trial/trail/stronghold reference offsets, abandoned camps, spawn
accuracy and physical structure census retain their existing explicit method gaps.

High patch review9e871d337876 succeeded,exit0,denied[],27531tokens,no edits/tests.
Codex reconciles its findings: scale4 is already raw Pos2d because getNetherBiome
setsY=0; the alleged scale4 3D selection gap is incorrect. Negative integer edges
are safely rejected by the helper; genBiomes may return after a partially filled
buffer, whose contents are invalid on error. There is no partial-success contract.
New tests now check every frozen candidate's gate, including invalid-biome
rejections. They test algorithmic exclusions, not game-certified absence.
An explicit exact-distance tie game witness is not available; no universal tie/
population guarantee follows. A bounded source-only tie search found none.
The reviewer ran no tests; all reported executions are Codex's checks.
