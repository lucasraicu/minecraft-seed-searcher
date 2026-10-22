# Biome mechanism counterexamples

This is a separate frozen bundle. The existing predictor-resolution manifest,
reviewed exclusions and published catalog snapshot are unchanged.

The fixed domain contains four saved chunks across two signed seeds, 128 sampled
vertical columns and 8,320 stored points (Y16..80). The first two chunks are the
discovery set; another chunk and the second seed are spatial/seed holdouts. The
native probe records 3,920 unique quart nodes, names, numeric native IDs, SHA seed
and six climate parameters. Stored numeric IDs are never equated with native IDs.

Initial per-world API associations left 171 points unnamed. One direct stable BDS
read of stored ID1 established `plains` within this recorded world/copy, completing
all 8,320 associations. Historical v2 groups retain that earlier unknown count;
current groups and names are separate fields. This is not a global numeric map.

There are 30 stored-data points whose observed name is absent from all 27 adjacent
native quart nodes. Eight original witnesses were selected before direct testing;
all eight match stable BDS at exact XYZ. In total, 25 direct game reads (including
same-column controls) match the original stored data; nine of these direct points
lack their observed name among the 27 predicted parents. Do not describe all
8,320 points or all 30 counterexamples as independently queried by BDS.

The parent neighborhood is explicitly floor(block/4)+[-1,1] on each axis. It
covers the standard Java -2 offset and the tested removed-offset convention.
It does not encompass every imaginable zoomer, grid spacing, or postprocessor.
All eight original witnesses still fail continuous native noise and trilinear
climate interpolation at the same block coordinates. Nine paired controls match.
A wider vertical neighborhood can carry the labels, but a simple 4×8×4 parent grid
fails other controls. None of these observations establishes the Bedrock algorithm.
The current native tree agrees with exhaustive search of its 7,776 climate leaves
at the eight centers, so a tie-breaking-only patch is unsupported there.

Direct world copies used BDS1.26.52.3, stable API2.10.0, no markers or player actions,
25biome/28block reads, 0locates and28.10seconds total game wall. Both saved/stopped
cleanly and removed owned containers. Original world hashes match before/after.
Reports, raw console, frozen requests, observer and settings are retained here.

Rebuild the raw-node diagnostic at a new external path:

```sh
python3 scripts/build_biome_sampling_probe.py --mode nodes --output /tmp/new-biome-nodes
```

Input is `signed_seed quart_x quart_y quart_z`, one line each, at most4096 rows.
Output is `native_id name voronoi_sha T H C E D W`. The quart Y=-17 margin
is a virtual climate halo below physical world bounds; it is not an in-game read. This is diagnostic only; it is
not linked into serving. The default builder mode remains the prior block probe.
The independent portable helper reproduced all3,920 recorded node outputs.
`original-build.json`/`original-probe.c` preserve the original producer; `build.json`
records the portable reproducer. Original absolute build paths are historical
metadata; use the supplied builder for replay on another checkout.

```sh
.venv/bin/python -m pytest -q tests/test_predictor_mechanism.py
```

Tests bind the saved records and API associations, preserve the historical native
counterexamples, validate direct game identities/raw output, and check builder
output guards. They do not require a future corrected algorithm to remain wrong.
Native implementation/version parity needs a new separately identified output.

Model/version boundary: the native model is labeled research26.50; the observed
game build is1.26.52.3. These results do not decide whether the discrepancy is a
version-compatibility change, climate data difference or sampler/postprocess issue.
No public game-build acceptance is implied.
