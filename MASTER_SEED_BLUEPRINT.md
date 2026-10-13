# Master Seed Blueprint: Bedrock 8–11 Player Realm

**Active predictor model:** pinned `MC_26_50`; game target 26.52. Predicted features require actual-game verification.
**Active screening policy:** `origin-fixed-2048-v1` with one evaluation center at the world origin (0,0). The game’s actual spawn is not assumed to be (0,0). Earlier Stronghold-centered revisions remain historical controls.

**Target Game Version:** Minecraft Bedrock Edition 1.21+  
**Target Community:** 11 Players (intimate community, shared central hub, dedicated districts, zero resource depletion)

---

## 1. World Boundaries & Geometric Coordinates

| Dimension / Region | Exact Dimensions | Center Coordinate | Chunk Size | Distance to Edge | Notes & Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Stronghold query** | **2048 × 2048** | World origin `(0, 0)` | $128 \times 128$ chunks | Radius 1,024 to sides | The pinned predictor queries regional and village-associated starts; one distinct predicted Stronghold is mandatory. |
| **Playable Overworld** | **2048 × 2048** | **World origin (0,0)** | $128 \times 128$ chunks | Radius 1,024 | Exact grid multiple ($4 \times 512$). ~1 min 40 sec sprint to edge; intimate scale for 11 players with room for all biomes. |
| **Playable Nether** | **1024 × 1024** | **World origin (0,0)** | $64 \times 64$ chunks | Radius 512 | Intersects 6–9 Nether structure grid regions ($480 \times 480$). Triples yield of Fortresses & Bastions. |

---

## 2. Terrain Specification: "The Coastal Continent"

* **Primary Landmass:** Continuous mainland occupying **70% to 80%** of the 2048 × 2048 border (~3.0 to 3.3 million blocks² of solid land).
* **River Bridging Policy:** 8-way connectivity (`np.ones((3, 3))`) or freshwater enclosure is applied so natural rivers and inland lakes do **not** sever the continental landmass into sub-70% pieces.
* **Guaranteed Ocean Edge (Marine Prerequisite):** At least **one border edge** consists of open `deep_ocean` / `ocean` (250–350 block wide coastal strip) hosting Ocean Monuments and Shipwrecks.
  > [!IMPORTANT]
  > **Baseline Decoupling & Marine Gating:** Ocean Monuments and Shipwrecks are **deliberately deferred from Stage 1 Baseline screening** and do not disqualify seeds from the Baseline candidate pool. They are strictly evaluated in **Stage 3** as part of Coastal Continent Terrain verification. Seeds that meet Stage 1 & 2 criteria are persisted as valid Baseline Survivors regardless of marine presence. If a seed lacks an ocean edge or marine structures, it retains its Baseline Survivor status while the downstream marine qualification is recorded accordingly.
* **Guaranteed Inland River / Lake:** At least **1 major navigable river corridor** ($\ge 600\text{m}$ continuous channel at $Y \le 63$) or scenic inland lake nestled inside the mainland interior.
* **"River Highway" Jackpot Feature (+35 pts):** Direct river connectivity originating near the origin hub and flowing unobstructed out into the coastal ocean (enabling seamless boat travel from base to sea).
* **Coastal Features:** Natural beaches, harbors, sailing access, and sheer sea cliffs (`stony_shore`) dropping into the ocean.
* **No Enclosed Mountain Ring:** Natural rolling topography without restrictive crater/caldera walls.

---

## 3. Required Biome Palette & Luxury Biomes (Inside 2048 × 2048)

The predictor screens for **9 surface resource families and underground biome witnesses**. Generation, cave size and access remain unverified:

1. 🌾 **Plains Family:** Plains, Sunflower Plains, or Meadow (central base building / farming).
2. 🏜️ **Desert:** Sand, glass, cactus, hosting Desert Pyramids.
3. 🌲 **Forest / Birch Forest:** Standard wood supply and peaceful starter terrain.
4. 🐺 **Taiga:** Spruce wood, sweet berries, wolves.
5. 🌴 **Jungle:** Jungle wood, cocoa, hosting Jungle Temples.
6. 🐸 **Swamp / Mangrove Swamp:** Mud, clay, slime, mangrove wood.
7. ❄️ **Snowy / Ice Biome:** Packed ice and blue ice for high-speed Nether boat highways.
8. 🍄 **Dark Forest:** Dark oak wood, huge mushrooms, hosting the Woodland Mansion (surface-height verified).
9. 🏔️ **Jagged Peaks & Cliffs:** High peaks (`jagged_peaks`, `stony_peaks`) for elytra towers/goats, plus sheer sea cliffs (`stony_shore`) dropping into the ocean.
10. 💎 **Underground Mega-Cave Clusters:** Contiguous cavern systems ($\ge 128 \times 128\text{m}$ footprint at $Y = -16$ to $-52$) for **Lush Caves** (glow berries, axolotls, azalea) and **Dripstone Caves** (stalactites, infinite lava), plus **Deep Dark** ($Y \le -10$) around Ancient Cities.

### Luxury Ranking Biomes (High Bonus Points)
Seeds rolling these additional aesthetic biomes receive top leaderboard placement:
* 🌸 **Cherry Grove:** +15 pts (Scenic pink petal mountain slopes).
* 🏜️ **Badlands / Mesa:** +15 pts (Terracotta, red sand, extra surface gold).
* 🌺 **Flower Forest:** +10 pts (All flower variants, bee nests, dye production).
* 🎋 **Bamboo Jungle:** +10 pts (Dense bamboo stalks, pandas).

*Excluded from constraints:* Nether biome variants and flat world templates.

---

## 4. Structures: Guaranteed Floors, Tolerance Matrix & Miss Budget Policy

Every qualifying seed **MUST pass the Guaranteed Baseline Hard Floors under Budget $B = 2$**.

> [!IMPORTANT]
> **Baseline Decoupling & Marine Gating Rule:** Ocean Monuments and Shipwrecks are **deliberately deferred from Stage 1 Baseline screening**. They are queried in **Stage 3** only after confirming the Coastal Continent ocean edge footprint. Seeds that pass Stage 1 and Stage 2 are saved as valid **Baseline Survivors** regardless of marine structures. If a seed lacks an ocean edge or marine structures in Stage 3, it retains its Baseline Survivor status rather than being eliminated.

### The Miss Budget Rule ($B = 2$)
1. **Instant Rejection (Hard Floors):** Any seed that drops below the **Hard Floor** for *any* structure is instantly disqualified in Stage 1 C screening (zero compute wasted).
2. **Deficit Tolerance:** If a structure meets its Hard Floor but falls below its **Ideal Target**, it consumes **1 Miss** from the seed's budget.
3. **Budget Limit:** A seed may have at most **2 structures in deficit** across the entire world ($\text{Total Misses} \le 2$). Any seed with $\ge 3$ deficits is disqualified.

### Structure Specification & Tolerance Matrix

| Structure | Group / Category | Dimension | Ideal Target | Tolerance | Hard Floor (Absolute Min) | Stage Queried | Condition & Realm Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🏰 **Stronghold** | **Strictly Required** | Overworld | **1** | **$0$** | **$\ge 1$** | Stage 1 | **Non-negotiable.** End portal access. +50 pts for 2nd start. |
| 🌿 **Jungle Temple** | **Strictly Required** | Overworld | **1** | **$0$** | **$\ge 1$** | Stage 1 | **Mandatory.** Redstone & jungle loot. +10 pts for 2nd. |
| 🏺 **Desert Pyramid** | **Strictly Required** | Overworld | **1** | **$0$** | **$\ge 1$** | Stage 1 | **Mandatory.** Suspicious sand & desert loot. +10 pts for 2nd. |
| 🏴‍☠️ **Pillager Outpost** | **Strictly Required** | Overworld | **1** | **$0$** | **$\ge 1$** | Stage 1 | **Mandatory.** Infinite stacking raid farm. +10 pts for 2nd. |
| 🏛️ **Woodland Mansion** | Flexible (Budget = 2) | Overworld | **1** | **$-1$** | **$\ge 0$** | Stage 1 | Allowed to be 0 (counts as 1 miss). **+50 pts if 1**; +100 pts for 2nd. |
| 🌌 **Ancient City** | Flexible (Budget = 2) | Overworld | **2** | **$-1$** | **$\ge 1$** | Stage 1 | **Guaranteed $\ge 1$**. 1 city counts as 1 miss. +25 pts for 3rd/4th. |
| 🔥 **Nether Fortress** | Flexible (Budget = 2) | Nether | **2** | **$-1$** | **$\ge 1$** | Stage 1 | **Guaranteed $\ge 1$**. 1 fortress counts as 1 miss. +20 pts for 3rd/4th. |
| 🐷 **Bastion Remnant** | Flexible (Budget = 2) | Nether | **3** | **$-1$** | **$\ge 2$** | Stage 1 | **Guaranteed $\ge 2$**. 2 bastions counts as 1 miss. +20 pts for 4th+. |
| ⚔️ **Trial Chambers** | Flexible (Budget = 2) | Overworld | **10** | **$-2$** | **$\ge 8$** | Stage 1 | **Guaranteed $\ge 8$**. 8–9 chambers counts as 1 miss. +10 pts for 11th+. |
| 🏘️ **Villages** | Flexible (Budget = 2) | Overworld | **7** | **$-2$** | **$\ge 5$** | Stage 1 | **Guaranteed $\ge 5$**. 5–6 villages counts as 1 miss. +5 pts for 8th+. |
| 🌀 **Ruined Portals** | Flexible (Budget = 2) | Overworld | **7** | **$-2$** | **$\ge 5$** | Stage 1 | **Guaranteed $\ge 5$**. 5–6 portals counts as 1 miss. +5 pts for 8th+. |
| ⛏️ **Mineshafts** | Flexible (Budget = 2) | Overworld | **20** | **$-3$** | **$\ge 17$** | Stage 1 | **Guaranteed $\ge 17$**. 17–19 shafts counts as 1 miss. +1 pt above 20. |
| 🗿 **Ocean Monument** | **Marine Dependent** | Overworld | **1** | **$0$** | **$\ge 1$** | **Stage 3** | **Stage 3 Only.** Evaluated **ONLY** if coastal ocean confirmed; +25 pts for 2nd. |
| ⛵ **Shipwrecks** | **Marine Dependent** | Overworld | **5** | **$-2$** | **$\ge 3$** | **Stage 3** | **Stage 3 Only.** Evaluated **ONLY** if coastal ocean confirmed; +5 pts above 5. |
| 🛶 **Inland River / Lake** | Terrain Dependent | Overworld | **$\ge 1$ Corridor** ($\ge 600\text{m}$) | **0** | **$\ge 1$** | **Stage 3** | Mandatory Inland Waterway; +35 pts for "River Highway" link. |

### Ocean Gating Rules (Marine Structures)

| Structure | Coastal Ocean Verified in Stage 3? | Behavior & Candidate Status |
| :--- | :---: | :--- |
| 🗿 **Ocean Monument** | **NO** | Marine stage marked `PENDING` / `NEAR_MATCH`. **Seed retains Baseline Survivor status.** |
| 🗿 **Ocean Monument** | **YES** | Evaluates $\ge 1$ monument inside coastal sea envelope (+25 for 2nd). |
| ⛵ **Shipwrecks** | **NO** | Marine stage marked `PENDING` / `NEAR_MATCH`. **Seed retains Baseline Survivor status.** |
| ⛵ **Shipwrecks** | **YES** | Evaluates 3 to 5 shipwrecks along confirmed coast and beaches (+5 above 5). |

> [!TIP]
> **Baseline Inland Exemption:** When running in **Baseline Only** mode and no ocean biome is selected, **Shipwrecks and Ocean Monuments are completely exempted** from search floors and do not consume tolerance budget or penalize candidate feasibility.

### Active origin policy ranking (predictor evidence only)

| Tier | Feature | Bonus |
|---|---|---:|
| 1 | Second Woodland Mansion; second distinct Stronghold in the fixed square | +50 each |
| 1 | First Woodland Mansion (Jackpot presence over baseline 0) | +50 |
| 1 | River corridor model connects the origin hub (within 250 blocks) to coastal ocean | +35 |
| 1 | Mega Ravine Fissure intersecting origin hub (within ≤200m) | +35 |
| 2 | Third and fourth Ancient Cities | +25 each |
| 2 | Third and fourth Nether Fortresses; fourth and later Bastions | +20 each |
| 2 | Second Ocean Monument (in coastal water) | +25 |
| 3 | Sampled Cherry Grove, Badlands family, Mushroom Fields at Y=63 | +15 each |
| 3 | Every Village above seven | +5 each |
| 3 | Every Ruined Portal above seven; extra Trial Chambers above ten | +5 each / +10 each |
| 4 | Second Pillager Outpost | +10 |
| 4 | Second Desert Pyramid; second Jungle Temple | +10 each |

All biome bonuses use the complete configured four-Y lattice for retained origin candidates. The river and marine bonuses remain deferred to terrain/marine processing. These are score points, not proof of usable loot, navigability, portal rooms or actual spawn position. Strongholds cannot miss; flexible structures can miss up to the $B = 2$ budget.

### Excluded Structures (Zero Wasted Compute)
* **No End Cities** (End dimension unconstrained).
* **No Igloos, Witch Huts, Nether Ruined Portals, Abandoned Camps, Trail Ruins, Buried Treasure, or Ocean Ruins.**

---

## 5. Execution Pipeline & Search Workflow

```
                        [ Bounded input-seed stream ]
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ STAGE 1: Fast Native C Structure Screening (Budget B = 2 Gate)         │
   │ • Fixed origin square [-1024, -1024, 1024, 1024) at (0, 0)             │
   │ • Mandatory: Stronghold ≥ 1, Pyramid ≥ 1, Temple ≥ 1, Outpost ≥ 1.     │
   │   (If any are 0 → instant reject)                                      │
   │ • Hard Floors: Cities ≥ 1, Fortresses ≥ 1, Bastions ≥ 2,               │
   │   Chambers ≥ 8, Villages ≥ 5, Portals ≥ 5, Mineshafts ≥ 17.            │
   │   (If any drop below Hard Floor → instant reject)                      │
   │ • Deficit Budget: Tally deficits against Ideal Targets.                │
   │   (If Deficits > 2 → reject)                                           │
   │ • [Ocean Monuments & Shipwrecks DEFERRED to Stage 3]                   │
   └────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ STAGE 2: 4-Y Biome Diversity Lattice Check                             │
   │ • Lattice planes at Y = 63, -48, 0, 160                                │
   │ • Verifies Plains, Forest, Taiga, Swamp, Snowy, Peaks/Cliffs,          │
   │   and Cave clusters (Lush, Dripstone, Deep Dark)                       │
   │ • Seeds passing Stages 1 & 2 are saved as BASELINE SURVIVORS.          │
   └────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ STAGE 3: Terrain, Coastline, River & Marine Structure Verification     │
   │ • Multi-Resolution Cascade: 128m coarse check verifies 70–80% mainland │
   │ • 8-Way Mainland Bridging: Rivers/lakes do not sever continent         │
   │ • Inland Waterway: Confirm ≥ 1 navigable river corridor (≥ 600m)       │
   │ • COASTAL OCEAN BIOME GATE:                                            │
   │   ├── If coastal ocean absent → Marine stage PENDING; baseline kept.   │
   │   └── If coastal ocean confirmed → Query Monument (≥ 1) & Wrecks (≥ 3).│
   └────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ STAGE 4: Smart Ranking & Database Export                               │
   │ • Tally bonus points: River Highway (+35), Mansion (+50), SH #2 (+50)  │
   │ • Tally bonus points: 3rd/4th Fortresses (+20), 4th+ Bastions (+20)    │
   │ • Tally bonus points: Extra Chambers (>10), Villages (>7), Luxury Biomes│
   │ • Export top-ranked candidates with coordinates to SQLite database     │
   │ • Display on interactive Web Dashboard                                 │
   └────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ STAGE 5: Headless BDS Docker Verification (Top 20 Finalists Only)      │
   │ • Bounded budget: Runs ONLY on top 10–20 candidates from Leaderboard   │
   │ • Fast headless container / LevelDB inspection (<8s per seed)          │
   │ • Validates exact NBT loot tables, spawners, and portal room geometry  │
   └────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Time & Machine Expectations
* **Throughput:** Measure the active origin policy separately. Historical raw C and persisted rates used different geometry and cannot predict this policy's world yield.
* **Stage 2:** A sparse sample can establish a positive biome witness, but absence at 32 points cannot safely reject a seed. The configured lattice and required four-Y roles remain authoritative.
* **Stage 3:** The coastal terrain cascade is measured separately from baseline screening. Coarse rejection must preserve exact final-decision parity.
* **Stage 5:** BDS verification does not run during seed screening and uses a bounded, explicitly selected budget. Full-world verification time remains unmeasured.
* **Storage mode:** Compact mode saves predicted survivors and selected near misses, plus durable range checkpoints. Full-evidence mode remains available.
* **Expected runtime:** No complete-world discovery time is established; survivor probability and actual Bedrock validity remain unverified.
