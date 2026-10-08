# Structure discrepancy diagnosis and handling

The 880 frozen website rows are compared using exact local-output regression checks plus per-type diagnostic marker conventions. Coordinate tolerance never changes a border decision. Starts remain typed, and a local start cannot be reused for two website rows.

Bastion cases 12345 and 4294979641 share the same lower seed bits. Their raw start (1208,408) selects a rotated Hoglin Stable piece: rotation 2, offset (-29,-47), size (30,48). The actual viability sample is quart (296,8,94), Basalt Deltas; the raw start itself samples Nether Wastes. Thus a start-biome shortcut would hide the disagreement. No evidence here establishes the correct game rule or justifies changing this pinned implementation. All rejected raw starts remain visible in the candidate review path, and a required disputed target cannot become website-confirmed eligible without recorded fresh matching-version review.

Ancient City uses un-Voronoi quart coordinates and Y=-27 (quart Y=-7). At seed -1, raw (-3048,3256), this sample is Birch Forest although the exact-block biome is Deep Dark. For seed 4294979641, (-680,6216), both the sampled and exact-start biome are Savanna Plateau. Changing the quart convention solely to fix the first row would not explain the second. Both raw starts remain reviewable.

Strongholds enumerate the static regional path with displacement halo and the first three village-associated starts. The two seed -1 website markers remain missing in the frozen comparison. No known general rule correction was established. Stronghold completeness is explicitly unknown; a missing local start contributes an unknown preference interval, not a known-absence score. Optional Stronghold uncertainty never rejects an island.

The corrected absent seed-12345 Fortress (-152,120) remains excluded for raw and viable scans. Rejected Bastions are never promoted to Fortress. Existing positive locate anchors stay separate from website markers and from visited footprints.

Evidence: structure-diagnostics.json, regression/regression.json and tests/test_search_pipeline.py. Sources inspected: [pinned backend](https://github.com/FragrantResult186/cubiomes-bedrock/blob/294c72ab0392dd818a91d293dbd5774d4874d64b/finders.c), [Chunkbase prediction limits](https://www.chunkbase.com/apps/seed-map#troubleshooting). These predictor comparisons do not determine which remaining disputed prediction matches generated game structures.
