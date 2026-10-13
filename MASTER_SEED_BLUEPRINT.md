# Master Seed Blueprint: Bedrock 8–11 Player Realm

**Target Game Version:** Minecraft Bedrock Edition 1.21+  
**Target Community:** 11 Players (intimate community, shared central hub, dedicated districts, zero resource depletion)

---

## 1. World Boundaries & Geometric Coordinates

| Dimension / Region | Exact Dimensions | Center Coordinate | Chunk Size | Distance to Edge | Notes & Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Discovery Envelope** | **4000 × 4000** | Spawn `(0, 0)` | $250 \times 250$ chunks | Radius 2,000 | Captures entire Ring-1 Stronghold radius (640–1152). 100% guarantees 3 Strongholds to pick from. |
| **Playable Overworld** | **2048 × 2048** | **Stronghold Center** | $128 \times 128$ chunks | Radius 1,024 | Exact grid multiple ($4 \times 512$). ~1 min 40 sec sprint to edge; intimate scale for 11 players with room for all biomes. |
| **Playable Nether** | **1024 × 1024** | `(SH.X / 8, SH.Z / 8)` | $64 \times 64$ chunks | Radius 512 | Intersects 6–9 Nether structure grid regions ($480 \times 480$). Triples yield of Fortresses & Bastions. |

---

## 2. Terrain Specification: "The Coastal Continent"

* **Primary Landmass:** Continuous mainland occupying **70% to 80%** of the 2048 × 2048 border (~3.0 to 3.3 million blocks² of solid land).
* **River Bridging Policy:** 8-way connectivity (`np.ones((3, 3))`) or freshwater enclosure is applied so natural rivers and inland lakes do **not** sever the continental landmass into sub-70% pieces.
* **Guaranteed Ocean Edge:** At least **one border edge** consists of open `deep_ocean` / `ocean` (250–350 block wide coastal strip) hosting Ocean Monuments and Shipwrecks.
* **Guaranteed Inland River / Lake:** At least **1 major navigable river corridor** ($\ge 600\text{m}$ continuous channel at $Y \le 63$) or scenic inland lake nestled inside the mainland interior.
* **"River Highway" Jackpot Feature (+20 pts):** Direct river connectivity originating near the central Stronghold/Plains hub and flowing unobstructed out into the coastal ocean (enabling seamless boat travel from base to sea).
* **Coastal Features:** Natural beaches, harbors, sailing access, and sheer sea cliffs (`stony_shore`) dropping into the ocean.
* **No Enclosed Mountain Ring:** Natural rolling topography without restrictive crater/caldera walls.

---

## 3. Required Biome Palette & Luxury Biomes (Inside 2048 × 2048)

All **9 surface resource families + underground mega-cave clusters** are guaranteed:

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

## 4. Structures: Guaranteed Floors & Smart Ranking Matrix

Every qualifying seed **MUST pass the Guaranteed Baseline Floor**. 

> [!IMPORTANT]
> **Stage 1 Optimization Rule:** Ocean Monuments and Shipwrecks are **deliberately deferred from Stage 1 screening**. They are queried in **Stage 3** only after confirming the ocean biome and coastal water footprint, preventing false rejections and wasted computation.

| Structure | Dimension | Guaranteed Baseline Floor | Target "Jackpot" Count | Stage Queried | Smart Ranking Bonus Points |
| :--- | :---: | :---: | :---: | :---: | :--- |
| 🏰 **Stronghold** | Overworld | **$\ge 1$ (Centered)** | **1** | Stage 1 | Core Anchor (Mandatory world center) |
| 🏛️ **Woodland Mansion** | Overworld | **$\ge 1$** | **1 to 2** | Stage 1 | Mandatory Anchor in Dark Forest; **+50 pts** jackpot bonus for rare 2nd |
| 🏘️ **Villages** | Overworld | **$\ge 6$** | **7 to 10** | Stage 1 | **+5 pts** per village above 6 |
| ⚔️ **Trial Chambers** | Overworld | **$\ge 5$** | **8 to 12+** | Stage 1 | **+10 pts** for 6th and beyond |
| 🌌 **Ancient Cities** | Overworld | **$\ge 2$** | **3 to 4** | Stage 1 | **+15 pts** for 3rd and 4th |
| 🏺 **Desert Pyramids** | Overworld | **$\ge 1$** | **2 to 3** | Stage 1 | **+20 pts** for 2nd; **+10 pts** for 3rd |
| 🌿 **Jungle Temples** | Overworld | **$\ge 1$** | **2** | Stage 1 | **+20 pts** for 2nd |
| 🌀 **Ruined Portals** | Overworld | **$\ge 6$** | **8 to 10+** | Stage 1 | **+5 pts** per portal above 6 |
| ⛏️ **Mineshafts** | Overworld | **$\ge 15$** | **25 to 40+** | Stage 1 | **+1 pt** per extra mineshaft above 15 |
| 🔥 **Nether Fortresses**| Nether | **$\ge 2$** | **3 to 4** | Stage 1 | **+15 pts** for 3rd and 4th |
| 🐷 **Bastion Remnants** | Nether | **$\ge 3$** | **3 to 4** | Stage 1 | **+15 pts** for 4th and beyond |
| 🗿 **Ocean Monument** | Overworld | **$\ge 1$** *(in coastal water)*| **2** | **Stage 3 (Post-Terrain)**| **+25 pts** if 100% in coastal sea; **+25 pts** for 2nd |
| ⛵ **Shipwrecks** | Overworld | **$\ge 5$** *(coastal/beach)* | **6 to 8+** | **Stage 3 (Post-Terrain)**| **+5 pts** per shipwreck above 5 |
| 🛶 **Inland River / Lake** | Overworld | **$\ge 1$ Corridor** ($\ge 600\text{m}$) | **2 to 3** | **Stage 3 (Terrain)** | Mandatory Inland Waterway; **+20 pts** for "River Highway" Hub-to-Sea link |
| 🏴‍☠️ **Pillager Outpost**| Overworld | **$\ge 2$** | **2 to 3** | Stage 1 | Mandatory Raid Bases; **+15 pts** for 3rd and beyond |

### Excluded Structures (Zero Wasted Compute)
* **No End Cities** (End dimension unconstrained).
* **No Igloos, Witch Huts, Nether Ruined Portals, Abandoned Camps, Trail Ruins, Buried Treasure, or Ocean Ruins.**

---

## 5. Execution Pipeline & Search Workflow

```
                        [ Seed Stream (~19,800 seeds/sec in C) ]
                                       │
                                       ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 1: Ultra-Fast Core Structure Screening (Native C)                │
  │ • Locate Ring-1 Stronghold in 4000×4000 discovery square               │
  │ • Recenter 2048×2048 Overworld box on Stronghold                       │
  │ • Check Overworld: ≥6 Villages, ≥5 Trial Chambers, ≥2 Ancient Cities   │
  │ • Check Overworld: ≥1 Mansion (+50 for 2), ≥1 Pyramid, ≥1 Jungle Temple│
  │ • Check Overworld: ≥2 Pillager Outposts, ≥6 Portals, ≥15 Mineshafts    │
  │ • Check 1024×1024 Nether: ≥2 Fortresses + ≥3 Bastions                  │
  │ • [Ocean Monuments & Shipwrecks DEFERRED to Stage 3]                   │
  └────────────────────────────────────────────────────────────────────────┘
                                       │ (Rejects 99.85% of duds in microseconds)
                                       ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 2: 4-Y Biome Diversity Lattice Check (Rare-First Optimized)      │
  │ • Fast Coarse Filter (32-point check): Verify rare biomes (Dark Forest,│
  │   Snowy/Ice, Desert, Jungle) in <0.4ms; short-circuit fails immediately│
  │ • Full Lattice (Y=63, -48, 0, 160): Plains, Forest, Taiga, Swamp,      │
  │   Jagged Peaks/Cliffs, and Deep Mega-Cave Clusters (Lush/Dripstone)    │
  └────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 3: Terrain, Coastline, River & Marine Structure Verification     │
  │ • Multi-Resolution Cascade: 128m coarse check (1-2ms) verifies 70–80%  │
  │   landmass & edge ocean; fine 32m/4m confirms beaches/cliffs           │
  │ • 8-Way Mainland Bridging: Rivers/lakes do not sever continent         │
  │ • Inland Waterway: Confirm ≥1 navigable river corridor (≥600m)         │
  │ • Query Ocean Monuments (≥1 inside confirmed coastal sea; +25 for 2nd) │
  │ • Query Shipwrecks (≥5 along confirmed coast & beaches)                │
  └────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 4: Smart Ranking & Database Export                               │
  │ • Tally bonus points: River Highway (+20), Cherry Grove (+15), Mesa (+15)│
  │ • Tally bonus points: 2nd Mansion (+50), 2nd Monument (+25), extra SH │
  │ • Tally bonus points: 3rd/4th Fortresses (+15), 4th+ Bastions (+15)    │
  │ • Export top-ranked candidates with coordinates to SQLite database     │
  │ • Display on interactive Web Dashboard                                │
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
* **Throughput:** ~19,800 seeds/second raw C filter; ~3,000+ seeds/second persisted throughput on this machine.
* **Stage 2 Speedup:** Rare-first 32-sample early-exit reduces biome evaluation from ~24 ms to <0.8 ms per candidate.
* **Stage 3 Speedup:** 128m coarse height-map culls invalid terrain in 1–2 ms before fine resolution.
* **Stage 5 Isolation:** BDS Docker verification never touches search screening; bounded to top 20 finalists (~2.5 minutes total).
* **Storage Mode:** Compact candidate persistence (winners-only rich records, zero disk bloat).
* **Expected Runtime:** **~20 to 35 minutes** of continuous scanning to produce a ranked leaderboard of world-class candidate seeds.
