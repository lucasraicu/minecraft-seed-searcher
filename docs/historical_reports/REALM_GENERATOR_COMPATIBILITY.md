**Bedrock 26.52 generator compatibility assessment — 8 October 2026**

This is a pre-implementation inspection report for the new Realm baseline/V1/V2 plan. It does not certify the new pipeline or authorize a large sweep. No native rebuild, library replacement, runtime installation, or search was performed during this assessment.

**Pinned release and installed predictor**

The requested target is stable Minecraft Bedrock 26.52. Mojang's official [26.52 hotfix changelog](https://feedback.minecraft.net/hc/en-us/articles/49175370527501-Minecraft-Bedrock-Edition-26-52-Hotfix-Changelog) is dated 25 September 2026. Freeze this release/build for the proposed run rather than following future latest releases.

The installed native bridge explicitly initializes `MC_26_50`; `doctor` reports model `26.50`. The provider is `FragrantResult186/cubiomes-bedrock`, pinned commit `294c72ab0392dd818a91d293dbd5774d4874d64b`, with source/license hashes and reviewed MT initialization patch in [vendor/backend.json](vendor/backend.json). The enum includes 26.50 and preview 26.60 but no 26.52 enum. Existing metadata explicitly states the 26.52-to-26.50 mapping is supported by bounded predictor comparisons, not full game emulation.

The absence of a separately named 26.52 enum alone does not prove an incompatible generator; equally, a hotfix changelog without generation changes does not prove equivalence. Validate feature-specific behavior against the exact release before permitting a validated mapping. Never relabel `MC_26_50` as an exact 26.52 runtime or select `MC_NEWEST`, which points to preview 26.60 in this vendor snapshot.

**Current feature matrix**

| Feature | Available locally | Existing evidence/limitation | New-pipeline status |
|---|---|---|---|
| Overworld/Nether biome lookup | Native `getBiomeAt`, grid and point APIs | Bounded existing external comparisons; not exhaustive 26.52 game validation | Usable labeled prediction; exact-release verification required |
| Stronghold | Static and village-associated adapters | Two known missed Chunkbase Strongholds for seed -1; completeness unknown | Prediction supported, incomplete; missing result cannot confirm absence |
| Village | Raw placement and native viability | Included in frozen typed external comparisons | Prediction supported; generated footprints/complete recall unverified |
| Trial Chamber | Per-full-seed placement and viability | Upper-bit dependency covered by existing tests | Prediction supported; do not use low32 raw cache |
| Ancient City | Raw placement and biome viability | Two known external viability disagreements (-1 and 4294979641) | Disputed prediction path; retain raw starts and verification backlog |
| Mineshaft | Chunk-based adapter | Cold/warm MT initialization and state handling tested | Prediction supported; per-full-seed computation |
| Fortress | Raw placement and viability | False Bastion-to-Fortress promotion removed; bounded required-marker reviews exist | Prediction supported; exact final-region generation remains separate |
| Bastion | Raw placement and viability | Two known external viability disagreements for 12345 and 4294979641 | Disputed prediction path; final requirement needs verified evidence |
| Monument, Outpost, Shipwreck, Ruined Portal | Exposed by native/Python adapters | Bounded external structure comparisons | Optional predictions supported; no assertion of actual complete generation |
| Buried Treasure | Vendor has Bedrock-configured `Treasure` logic | Not exposed in current owned native/Python structure list; not covered as a current product feature | Product feature unsupported until adapter and Bedrock validation are added |
| Dungeon/Monster Room | Vendor has feature-specific `getDungeons()` | Not exposed by product; uses terrain/cave machinery; ordinary placement adapter cannot enumerate it | Deferred/manual verification; no baseline brute force |
| Dappled Forest | ID 188, canonical name, biome existence/version logic and biome-tree support | Stable game feature; existing fixtures do not establish targeted actual 26.52 biome-placement correctness | Implemented predictor feature, accuracy unverified |
| Sulfur Caves | ID 187, canonical name, biome-tree support | Stable game feature; cave geometry/placement not validated by current external fixture | Implemented predictor feature, accuracy unverified; manual cave checker only |
| Pale Garden and stated legacy wooded families | Enum/name and biome policy support | Modern names need canonical aliases; new five-family contract is not current scoring | Supported prediction input; new classification needed |
| Natural ground | Raw density top-column estimate | Omits actual chunk interpolation, caves, aquifers, decoration; source comments explicitly warn of limits | Approximate screening only |
| Actual liquid blocks, lake level and water depth | No current product provider | Current land/water classification derives from height versus sea level | Unsupported by current provider; cannot certify V1 water geometry |
| Tree/structure exclusion from heights | No actual block/provenance extraction | Woodland masks are biome proxies; no generated blocks/trees/footprints | Unsupported for verified natural ground |
| Exact Bedrock blocks and finished world generation | No current product integration | `doctor` labels actual-game observations separately and optional | External runtime/import dependency |

Source anchors: [native/bridge.c](native/bridge.c), [backend.py](src/seed_search/backend.py), [vendor biome enums](vendor/cubiomes-bedrock/biomes.h), [vendor biome selection](vendor/cubiomes-bedrock/biomenoise.c), [vendor structure/feature adapters](vendor/cubiomes-bedrock/finders.c), and [known regression disagreements](fixtures/bedrock-26.52/regression-expectations-v1.json).

Mojang's [26.50 release notes](https://www.minecraft.net/nl-nl/article/minecraft--bedrock-edition-26-50-changelog) include the stable Dappled Forest feature. [26.30 release notes](https://www.minecraft.net/ru-ru/article/minecraft-26-30-bedrock-changelog) introduce Sulfur Caves. Game feature existence does not establish accuracy of this installed predictor.

**Evidence already available**

The frozen external dataset contains 880 structure rows and 159 coordinate comparisons; the documented regression matches 874 typed correspondences with six known structure disagreements. Historical height comparisons have mean absolute error one block and maximum error five on the recorded columns. Existing tests cover signed/high-bit seeds, MT state, combined structure scans, geometry, caches, and resume behavior. These are useful controls, not a verified actual-block generator, full Stronghold recall, or water-depth validation.

The new search uses different bounds, five mandatory Overworld structures, new required biome policy, independent variants, final Bastion eligibility, and actual-generation requirements. The previous sweep readiness record cannot certify it. A new compatibility report must identify verified capabilities and unresolved ones before any large launch.

**Recommended verified-generation path**

Planning update, 9 October 2026: Docker Desktop is the agreed host approach, with native macOS prediction workers and one initial BDS verifier in an Ubuntu x86_64 container inside Docker's Linux VM. Installation/startup remain on hold. Begin measurements with approximately 4 vCPUs/8 GB for Docker, within the combined 25–30 GB task budget; no performance or chunk-generation throughput has been measured. Validate the installed border add-on independently: the new agreed dimensions are 2688 × 2688 Overworld centered on the Stronghold and 1024 × 1024 Nether centered on Stronghold/8. These geometry decisions do not establish generator compatibility. The expanded proof-of-concept and calibration gates are in [REALM_BASELINE_IMPLEMENTATION_PLAN.md](REALM_BASELINE_IMPLEMENTATION_PLAN.md).

Add a provider/import contract for a pinned actual Bedrock 26.52 runtime. Prefer official Bedrock Dedicated Server on a supported external/virtualized host, or snapshots generated by that exact runtime and settings. Mojang's [server download page](https://www.minecraft.net/en-us/download/server/bedrock) provides Windows and Ubuntu builds; it does not provide a native macOS build. The current host reports Intel macOS 15.8, and inspection found no `bedrock_server` or `docker` command in PATH. This is an availability finding, not a claim that no suitable runtime exists elsewhere.

Microsoft documents biome, block, and topmost-block queries in the [Bedrock Dimension API](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/dimension?view=minecraft-bedrock-stable). They are an extraction approach to validate on the pinned build; current online API documentation alone is not proof of availability or complete structure coverage in a particular installed build. Loaded chunks, exact seed fidelity, module version, world creation settings, foliage/structure masks, fluid columns, and coverage must be recorded. Unloaded or unsupported queries remain unknown. Topmost block is not automatically natural ground.

A small runtime/extraction proof should demonstrate positive structure generation, actual ground/fluid columns, Dappled Forest, Sulfur Caves, negative/high-bit seed identity, and cache/replay provenance before selecting this as the verification backend. Do not introduce Java rules, guessed native layouts, coordinates copied into the algorithm, or browser predictions as replacements for actual generated blocks.

**Required compatibility gates**

The new pipeline must distinguish placement candidate, predicted viable start, independently reviewed marker, actual generated start, footprint/access, and confirmed absence. Validate bounds and each mandatory family separately. A capped positive marker list or single nearest locate result does not prove absence elsewhere. Add precise modern biome aliases and verify new biome IDs with independent exact-release fixtures. Remove automatic cave-variety scans; an Ancient City validity check is still part of mandatory structure generation checks.

Verified terrain/Realm results require a demonstrated pinned generation provider or imported actual-generation evidence. Approximate candidate exploration can be implemented with explicit prediction/pending status and retained baselines, but cannot permanently reject candidates solely on unvalidated geometry or claim final exact qualification. Unsupported optional features remain visible and never reject a baseline.

**Inspection verification**

`doctor` completed successfully with the existing environment and confirmed the installed model and callable native backend. The current full suite passed: **141 tests in 98.82 seconds**. Neither command installs or rebuilds the project. These checks verify the current implementation, not the unimplemented migration. Planning-task source/configuration hashes are checked afterward to ensure the implementation remains unchanged.

**Authorized isolated setup update — 9 October 2026**

The installation hold above records the earlier planning state. The user subsequently authorized Docker/BDS installation and an isolated feasibility test, while keeping seed-finder implementation on hold. Docker Desktop 4.94.0 and official BDS 1.26.52.3 are now installed, using Ubuntu 22.04, 4 VM CPUs and 8192 MiB VM RAM. No Docker account sign-up was needed.

The test preserved signed seed `-1234567890123456789`, loaded distant regions without connected players, read 384 distinct surface columns using actual block APIs, and passed 18 direct console block comparisons after correcting the grass-block vegetation mask. The final server shut down cleanly. This establishes a working actual-generation experiment, not a complete production verification provider.

Stopped-world LevelDB coverage remains incomplete: the latest measured snapshots contain 44/64, 62/256 and 7/64 requested chunks in three regions, despite successful sampled block reads. The cause is unresolved. Complete saved-raster extraction, natural-ground structure exclusion, predictor calibration, and required-structure verification remain unproven. Missing cells must remain unknown. See the isolated [setup results](/Users/lucasraicu/Downloads/bedrock-verification-setup/SETUP_RESULTS.md) for measurements and evidence. The new project scope now contains V1 and V2 only; the combined island-water-mountains variant is retired.

**Follow-up investigation — 9 October 2026**

The initial coverage limitation above is now understood operationally: BDS can serve generated chunks that have not been persisted. A controlled restored-sky-marker test saved 64/64 requested chunks versus 29/64 in the read-only control. Both later benchmark worlds saved 401/401 requested chunks; 18812 snapshot/API block comparisons and 3072 restart column comparisons passed. The standalone extractor also provides read-only streaming data and explicitly checks settling because some water changed between whole scans. These tested capabilities are outside the product and do not replace its predictor or certify its new pipeline.

Measured extraction improved 6.7–13.6× inside BDS (5.7–9.3× including command/result transfer) across three repeated region benchmarks. Four-CPU loading/readiness was approximately twice as fast as two CPUs in the measured paired cases; these are bounded BDS experiments, not seed-search throughput or broad scaling claims. Ground/structure masks, waterlogged-depth handling, predictor calibration, and required-structure verification remain unverified. Full details and raw evidence are in the [investigation report](/Users/lucasraicu/Downloads/bedrock-verification-setup/investigation/INVESTIGATION_RESULTS.md).

**Product integration — 10 October 2026**

The schema5 Realm modules now expose the installed MC_26_50 predictor and official BDS1.26.52.3 as separate sources. New baseline, storage/resume, independent V1/V2, selected verification, manual caves and conservative final Nether evidence interfaces are implemented. Latest capability reports are generated by `python -m seed_search compatibility`; the new output marks every unsupported/unverified feature explicitly. Earlier planning/install-hold statements above are historical.

The bundled BDS adapter passed a small actual terrain extraction (16columns,9/9finalizedchunks,64/64snapshot/APIblocks) and explicitly initiated underground biome sample. The selected16column comparison had heightMAE2.3125blocks,maximum7 and16/16exposed-water proxy agreement. These controls do not establish rare-terrain recall, complete natural ground, full-sized formation connectivity, or exhaustive structure enumeration. Natural-ground structure provenance, waterlogging/ice policy, and all actual Realm eligibility remain unverified. Final Nether can verify positive imported exact-build evidence; without that evidence it remains partial. No approximate prediction is promoted to verified by configuration.

Large native benchmarks are explicitly prediction-only; their reports include compatibility, seed-bit aliases, real distinct full64 coverage and pending counts. Historical sweep readiness does not certify this new contract.
