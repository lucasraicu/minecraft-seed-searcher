> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# BDS Provider Capabilities vs Unsupported Claims Matrix

**Audit Date**: October 2026
**Subject**: BDS 1.26.52.3 / Script API 2.10.0 Verification Scope
**Reference Files**:
- [`src/seed_search/realm/verification.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/verification.py)
- [`src/seed_search/realm/surface.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/surface.py)
- [`src/seed_search/realm/spawn.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/spawn.py)
- [`src/seed_search/realm/bds_tools/main.js`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/main.js)
- [`src/seed_search/realm/bds_tools/column_policy.js`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/column_policy.js)
- [`src/seed_search/realm/bds_tools/COLUMN_POLICY.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/COLUMN_POLICY.md)

---

## 1. Overview

Bedrock Dedicated Server (BDS) 1.26.52.3 with Script API 2.10.0 provides a sandboxed headless Bedrock runtime. The repository includes an actual testing harness in `src/seed_search/realm/bds_tools/` that interacts with this server using `@minecraft/server` behavioral pack scripts and a Python host harness (`probe_tools.py`, `poc_control.py`).

However, there is a fundamental disparity between what this provider **can actually observe** and the claims surfaced in the web interface and API.

---

## 2. Capability Matrix

| Feature / Dimension | Current BDS Provider Capability | Claimed in Web UI / API | Actual Ground Truth Status |
| :--- | :--- | :--- | :--- |
| **Voxel Column Height & Water** | **Supported (Bounded)**: Queries `dim.getBlock()`, `Block.isWaterlogged`, and scans topmost non-air columns on a requested 2D lattice. Compares against LevelDB saved blocks. | "99.8% palette agreement, height MAE 0.14 blocks" (Hardcoded) | **Partial & Local**: Can measure actual height MAE and liquid occupancy on a sampled tile, but metrics must be derived from real run outputs, not hardcoded. |
| **Surface Biome Names** | **Supported (Pointwise)**: Queries `dim.getBiome({x, y, z})` at $Y = \text{support}+1$. Returns string identifiers (e.g. `"minecraft:plains"`). | Displayed in Biome Witness / Catalog | **Point Existence Only**: Proves biome existence at discrete sampled $(X, Z)$ points; **cannot prove absence** across unsampled areas or full polygon boundaries. |
| **Numeric Biome IDs** | **Unsupported**: Script API 2.10.0 provides only namespaced string names; does not expose internal Bedrock numeric biome IDs. | N/A | **Unmapped**: Names must remain strings without guessing internal numeric IDs. |
| **Generated Structures (Overworld)** | **Unsupported**: In Script API 2.10.0, `dim.getGeneratedStructures` is `undefined` (logged explicitly in `main.js:128`). No structure bounding box enumeration exists. | "Woodland Mansion Ground Truth: CONFIRMED" | **Completely Unsupported**: BDS cannot enumerate or confirm mansions, villages, outposts, or strongholds. |
| **Portal Rooms & Strongholds** | **Unsupported**: The BDS Script API does not locate stronghold portal rooms, count ender eyes, or inspect frame blocks. | "Portal Room Status: INTACT" | **Completely Unsupported**: Fictitious claim. The Script API has no structure locator API in this build. |
| **Nether Structures (Fortress / Bastion)** | **Unsupported via Online Script API**: `verification.py:748` explicitly states: *"Stable Script API does not support exhaustive structure enumeration; import actual pinned-generation evidence"*. | N/A (Evaluated via imported JSON) | **Offline Import Only**: Requires external LevelDB / NBT parser evidence from pre-generated worlds. |
| **Container / Structure Loot** | **Unsupported**: Script API probe does not spawn players, open chests, or inspect loot tables. | N/A | **Completely Unsupported**: Loot generation cannot be certified by the current adapter. |
| **Initial-Player Spawn Placement** | **Classification Supported; Generation Unsupported**: `spawn.py` defines predicate checks (`within_radius`, `y>=63`, `dry`, `solid_support`), but BDS container runs headless with 0 players (`world.getAllPlayers().length == 0`). | N/A | **External Evidence Required**: Cannot be established by BDS container without an automated player client connecting and joining the world. |

---

## 3. Deep-Dive on Specific Subsystems

### 3.1 Biome Sampling
* **Implementation**: [`src/seed_search/realm/bds_tools/main.js`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/main.js#L169), [`column_policy.js`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/column_policy.js#L110-L135).
* **Mechanism**:
  ```javascript
  const surfaceBiome = observeSurfaceBiome(result, x, z, pos => dim.getBiome(pos));
  ```
  The query is executed at exactly one block above the highest observed support, open-water top, or snow/ice cover.
* **Limitations**:
  - The API returns string names (e.g. `minecraft:cherry_grove`).
  - As noted in `src/seed_search/realm/surface.py:30`:
    `result.get('existence_only') is True and result.get('absence_verified') is False`
  - A sparse sample (e.g. 16 coordinates) cannot confirm that a candidate lacks an undesired biome.

### 3.2 Generated Structures
* **Implementation**: `src/seed_search/realm/bds_tools/main.js` line 128:
  ```javascript
  world.afterEvents.worldLoad.subscribe(() => {
    dim = world.getDimension('overworld');
    console.warn('PROBE_READY ' + JSON.stringify({
      versionModule: '2.10.0',
      players: world.getAllPlayers().length,
      maxChunkCount: world.tickingAreaManager.maxChunkCount,
      getTopmostBlock: typeof dim.getTopmostBlock,
      getGeneratedStructures: typeof dim.getGeneratedStructures // Evaluates to "undefined"
    }));
  });
  ```
* **Status**:
  - `dim.getGeneratedStructures` is `undefined` in Bedrock Script API 2.10.0.
  - There is no script method to inspect structure starts, structure references, or bounding boxes.
  - The web server's injection of `"mansionGroundTruth": "CONFIRMED"` and `"portalRoomStatus": "INTACT"` has zero backing in the provider.

### 3.3 Initial-Player Spawn
* **Implementation**: [`src/seed_search/realm/spawn.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/spawn.py#L26-L50).
* **Mechanism**:
  - `classify_spawn` takes an imported evidence dict:
    ```python
    if (source.get('kind') != 'actual_generation' or
        source.get('provider') != 'bds' or
        source.get('version') != cfg['game']['bds_version'] or
        evidence.get('placement_kind') != 'initial_player' or
        str(parse_seed(evidence.get('seed'))) != candidate['seed']):
        raise ValueError('Initial-player evidence needs the pinned BDS source/version/seed')
    ```
  - It validates predicates: within 100 blocks of center, $Y \ge 63$, non-ocean biome, dry, solid support, headroom.
* **Limitation**:
  - The headless BDS container cannot generate this evidence on its own. Bedrock's initial player spawn algorithm calculates spawn upon the first player joining the world. Without a connected client, no initial player spawn coordinates are written. World spawn in `level.dat` is an approximate compass target, not initial player placement.

### 3.4 Terrain and Voxel Verification
* **Implementation**: [`src/seed_search/realm/verification.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/verification.py#L513-L644).
* **Capabilities**:
  - Allocates a ticking area (`createTickingArea`).
  - Reads non-air blocks in vertical columns.
  - Verifies multi-tick stability across 4 passes (`stability` check in `verification.py:561-572`).
  - Takes a world snapshot from the container LevelDB.
  - Uses `compare_saved_blocks.py` inside a reader container to compare in-memory column block states against LevelDB chunk palettes.
  - Computes `Raster` height and liquid occupancy.
* **Limitations**:
  - Max region size is strictly bounded (256 blocks per request).
  - High resource usage (requires 4 dedicated CPUs, 6 GiB RAM, and 16 GiB free disk space per container run).
  - Status is always provisional (`PARTIAL`), never certifying full Realm membership without complete multi-tile coverage.
