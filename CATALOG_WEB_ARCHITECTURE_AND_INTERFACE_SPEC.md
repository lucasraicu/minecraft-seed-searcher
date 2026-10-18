# Minecraft Seed Searcher: Web Interface & Catalog System Architecture Spec

**Status:** Consolidated Technical & Product Specification  
**Platform:** Minecraft Bedrock Edition 1.21+ (Pinned `MC_26_50` / Live BDS Target 1.26.52.3)  
**Date:** October 2026  
**Target Hardware:** Trillion-Seed CUDA GPU Cluster + Lightweight High-Throughput Web Host  

---

## ⚡ FINAL VERDICT: AT-A-GLANCE SUMMARY

> [!IMPORTANT]
> **The 6 Core Decisions That Define This Architecture:**
> 
> 1. **The 4-Pillar Ecosystem:**
>    - **Pillar 1 (Optimal Realm God Seeds):** 10k seeds per border size (30k slots) evaluated under Lucas's strict 14-floor master blueprint. Locked behind the Vault.
>    - **Pillar 2 (Curated Presets):** 8 category cards on the homepage with the top 250 showcase seeds each (6k slots). 100% free marketing hook.
>    - **Pillar 3 (Flexible Personalized Search):** Universal multi-criteria search where players customize any combination of 30 features and distances with a dynamic % match score.
>    - **Pillar 4 (Record-Breakers / Hall of Fame):** Top 100 seeds for maximum structure counts (e.g. 16+ Villages) and freak spawns (Mansion at spawn, Quad Witch Huts) for viral traffic.
> 
> 2. **Dual-Audience Branding (Same Backend Geometry, Zero Code Duplication):**
>    - **For 140M+ Infinite Vanilla Players:** Branded as **Exploration Travel Radius** (Walking ~1,000m, Horse ~2,000m, Elytra ~4,000m) and **Starter Portal Hub** (~500m in Nether). Infinite vanilla terrain continues beyond with zero commands or addons needed.
>    - **For Server Admins:** Branded as **World Borders** (2048, 4096, 8192 Overworld + 1024 Nether) with 1-click `/scriptevent` command script export.
> 
> 3. **The 30-Bit Universal Feature Signature (`uint32_t`):**
>    - All 14 Overworld structures + 9 Overworld biomes + 2 Nether structures (Fortress, Bastion) + 5 Nether biomes = **30 bits**.
>    - Fits 100% into a single 32-bit unsigned integer. Search queries jump directly to the target slot via $O(1)$ constant-time memory indexing in $< 0.05$ microseconds.
> 
> 4. **Continuous Proximity ("No Rigid Distance Walls"):**
>    - The 30-bit mask checks feature existence inside the playable boundary.
>    - Distances are evaluated dynamically using a soft decay curve: features within target distance get 100% score; features slightly further decay smoothly (e.g. 92% match) instead of a frustrating 0% fail.
>    - Universal math across Recommended Base (81 candidate centers), World Spawn, and Origin (0,0).
> 
> 5. **GPU Sweep & Database Numbers:**
>    - GPU streams $\ge 100\text{M seeds/s}$ into an in-memory 369 MB direct table. Unremarkable seeds are dropped in registers (0 bytes written).
>    - Cross-pillar deduplication leaves **~70,000 unique physical worlds**.
>    - Total custom database (`.seedcat`) size is only **~11.2 GB raw (~3.8 GB compressed)**.
> 
> 6. **Monetization & Content Protection:**
>    - **Never expose the full 10k leaderboard:** Only Ranks #1–#3 are shown publicly as proof.
>    - **Asset-Specific Licensing:** 1 Purchase = 1 Seed dossier (never mass CSV dumps).
>    - **Anti-Scrape Limits:** Max 15–20 reveals per day for paid users.
>    - **Account Watermarking:** Buyer's username and order ID are visibly and steganographically stamped onto all exported maps and PDF dossiers.

---

## 1. Executive Summary: The 4-Pillar Architecture

The public catalog and search platform is structured around **Four Product Pillars**, catering to all segments of the Minecraft ecosystem: from casual vanilla players to large multi-player SMP server administrators and viral content creators.

```mermaid
flowchart TD
    subgraph "The 4 Product Pillars"
        P1["<b>PILLAR 1: Optimal Realm God Seeds</b><br>• Lucas's Strict 14-Floor Master Blueprint<br>• 10k Seeds for 2048 | 10k for 4096 | 10k for 8192<br>• Perfect 8:1 Nether Alignment & Chunk-16 Borders<br><i>(Target: 15-20 Player Dedicated Realms)</i>"]
        
        P2["<b>PILLAR 2: Curated Play-Style Presets</b><br>• 8 Core Archetypes (Builders, Survival, Adventure, Ocean...)<br>• Top 250 Showcase Seeds per Category<br>• 1-Click Launchpad for Casual Players<br><i>(Target: Instant Discovery & Marketing Hook)</i>"]
        
        P3["<b>PILLAR 3: Flexible Personalized Search</b><br>• 30-Bit Universal Multi-Dimensional Detection Engine<br>• Continuous Proximity Distance Sliders (Any Distance)<br>• Proximity % Match & Dynamic Anchor Selection<br><i>(Target: Friend groups with custom checklists)</i>"]
        
        P4["<b>PILLAR 4: Record-Breakers & The Rarest</b><br>• Extreme Structure Count Champions (16+ Villages, 12+ Trials)<br>• Freak Proximity Spawns (Mansion at Spawn, Quad Witch Huts)<br><i>(Target: Speedrunners, YouTubers & Technical Redstoners)</i>"]
    end

    GPU["Single Trillion-Seed CUDA GPU Sweep"] --> P1
    GPU --> P2
    GPU --> P3
    GPU --> P4

    P1 --> Dedup["Cross-Pillar Deduplication Engine<br>(A God Seed in P1 also satisfies P2, P3, and P4)"]
    P2 --> Dedup
    P3 --> Dedup
    P4 --> Dedup

    Dedup --> CustomDB[("<b>Unified Custom Binary Database (.seedcat)</b><br>~70,000 Unique Worlds | ~11.2 GB Raw (~3.8 GB Compressed)<br>Memory-Mapped (mmap) for Sub-Millisecond SIMD Queries")]
```

### 1.1 Pillar 2: Curated Play-Style Presets ("The Sweet 16 Launchpad")

To provide an instant, 1-click on-ramp for casual players without forcing them through 30 search sliders, the homepage features **16 Curated Presets** organized into 5 thematic archetypes.

> [!IMPORTANT]
> **NO World Border Options for Presets (100% Infinite Vanilla):**  
> Curated Presets have **ZERO world border options, ZERO travel radius selectors, and ZERO configuration forms**. World borders strictly belong to **Pillar 1 (Optimal Realm God Seeds)** and the server addon mode in Pillar 3. For Presets, a player simply clicks a card (e.g. *"Cherry Blossom Haven"* or *"The Triple Start"*), instantly gets the top 250 seeds, copies a seed, and plays pure **infinite vanilla Minecraft** with zero setup.

> [!NOTE]
> **Feasibility & Geometry Integrity (Why No "True Survival Islands" in v1):**  
> True survival islands (a lone 20-block island surrounded by vast open ocean) require 2D/3D surface heightmap and coastline contour extraction. Because v1 uses a 64-block horizontal $Y=63$ biome lattice and predicted structure bounding boxes, claiming an isolated island without elevation data would risk landing players on a continental peninsula. Therefore, true survival islands are gated for a future terrain update. In v1, ocean gameplay is anchored to **mathematically verified aquatic structures** (Shipwreck Bay, Mushroom Haven & Ocean Monument).

#### The 16 Curated Presets:

1. **🎰 The Jackpot & God Starts**
   * **The Six-Pack:** Village + Ruined Portal + Desert Pyramid + Outpost + Trial Chamber + Ancient City within 300m.
   * **The Loot Run:** Ancient City + Trial Chamber within 200m (Instant underground progression).
   * **Mansion Village:** Woodland Mansion + Plains Village within 300m.

2. **⚡ Speedrun & Fast Starts**
   * **The Triple Start:** Village + Shipwreck + Ruined Portal within 200m (Instant iron, food, obsidian).
   * **Temple Rush:** Desert Pyramid + Ruined Portal within 150m.
   * **Nether Duo:** Nether Fortress + Bastion Remnant within 200m of starter portal.

3. **🌸 Builders' & Biome Specialists**
   * **Cherry Blossom Haven:** Cherry Grove + Plains Village within 150m.
   * **Alpine Meadow:** Mountain Meadow + Cherry Grove within 300m.
   * **Bamboo Temple:** Bamboo Jungle + Jungle Pyramid within 300m.
   * **❄️ The Frozen Frontier:** Snowy Village + Igloo (with basement) + Ice Spikes + Ruined Portal within 300m.
   * **🏜️ Badlands & Desert Empire:** Badlands (Mesa) + Desert Pyramid + Desert Village + Trail Ruins within 300m.

4. **🌊 Ocean & Aquatic Riches (Verified Geometry)**
   * **Shipwreck Bay & Village:** Coastal Village + 2 Shipwrecks in bay within 200m.
   * **Mushroom Haven:** Mushroom Fields touching Ocean Monument within 300m (Safe zero-hostile base + guardian farm).

5. **⚔️ Survival, Raids & Safe Nether**
   * **Villagers & Pillagers:** Village + Pillager Outpost within 300m (Day-1 raid farm starter).
   * **Witch Next Door:** Village + Swamp Hut within 200m (Early automated witch farm).
   * **Safe Nether Outpost:** Warped Forest (zero hostile piglins/hoglins) + Bastion Remnant within 200m of starter portal.

### 1.2 Pillar 4: The Hall of Fame & Record-Breakers (Statistical Outliers & Freak Spawns)

Pillar 4 is the **Viral Growth Engine** and **Content Creator Goldmine**. While Pillar 1 serves serious realm hosts and Pillar 2 serves casual vanilla players, Pillar 4 produces the jaw-dropping, shareable content that drives YouTube videos, TikTok clips, and Reddit discussions.

These are **pure infinite vanilla seeds** (Zero border options) tracking the absolute statistical extremes discovered across the 1-trillion seed sweep across **50 Leaderboards** (Top 100 seeds each = 5,000 slots):

#### Hall 1: 🏆 Maximum Structure Density Champions ("The Megacity Worlds")
*Ranked by total validated structure count within the exploration travel envelope ($\le 2,000\text{m}$ / 4096 area):*
1. **The Megacity (Most Villages):** Worlds with the highest Village count (18–24+ Villages).
2. **The Trial Gauntlet (Most Trial Chambers):** Worlds with 14–18+ Trial Chambers (infinite ominous vaults & maces).
3. **The Deep Dark Metropolis (Most Ancient Cities):** Worlds with 6–8+ Ancient Cities clustered in the deep slate.
4. **The Outpost Siege (Most Pillager Outposts):** Worlds with 8–10+ Pillager Outposts.
5. **The Nether Fortress Empire:** Worlds with the highest count of Nether Fortresses within the starter portal zone.
6. **The Bastion Fleet:** Worlds with 4–5+ Bastion Remnants packed together in the Nether.
7. **The Ruined Kingdom (Most Ruined Portals):** Worlds with 16+ Ruined Portals.
8. **The Desert Dynasty (Most Desert Pyramids):** Worlds with 8–10+ Desert Pyramids.
9. **The Sunken Armada (Most Shipwrecks):** Worlds with 12–15+ Shipwrecks along coastlines and ocean floor.

#### Hall 2: 🤯 Freak Proximity Spawns ("Impossible" Day-1 Starts)
*Ranked by minimum horizontal Euclidean distance from Day-1 natural world spawn $(X=0, Z=0 \pm 100\text{m})$:*
1. **The 0m Woodland Mansion Spawn:** Spawning with a Woodland Mansion directly touching or within 50 blocks of spawn (odds: $< 1 \text{ in } 500,000$).
2. **The 0m Ancient City Spawn:** Spawning directly above an Ancient City at $Y=-51$ directly beneath world spawn.
3. **The 0m Ocean Monument Spawn:** Spawning on a sandbar directly facing an Ocean Monument within 50m.
4. **The Quadruple Structure Overlap:** 4 different structures physically colliding or within 100m of each other at spawn (e.g. Village + Desert Pyramid + Pillager Outpost + Ruined Portal).
5. **The Direct-Drop Nether Portal:** Building a portal at $(0,0)$ drops you straight inside a Nether Fortress corridor or Bastion treasure room.

#### Hall 3: ⚙️ Technical Redstone & Automated Farm Wonders
*Worlds that enable extreme multi-structure industrial farms that are impossible in ordinary seeds:*
1. **The Quad Witch Hut (The Holy Grail):** 4 Swamp Huts located close enough to be simultaneously loaded by a single AFK player within a 128-block sphere (up to 40,000+ drops/hour).
2. **The Triple / Double Ocean Monument Farm:** 2 or 3 Ocean Monuments within loading radius for unprecedented automated prismarine and guardian XP generation.
3. **The Fortress + Bastion Overlap:** A Nether Fortress and Bastion Remnant generating within 64 blocks of each other (dual wither skeleton skull farm + automated piglin bartering in one chunk loading zone).
4. **The Intersecting Triple Mineshaft:** 3 separate Mineshafts colliding into a subterranean cave spider spawner matrix.

#### Hall 4: 🌍 Biome Rarity & Extreme Exploration Wonders
*Statistical extremes in Bedrock's biome generator:*
1. **The "All-Biome" 1,000m Sprint:** Seeds containing 14+ distinct biome families within a 1,000m walking radius of spawn (ideal for speedrunners completing the "Adventuring Time" advancement in under 15 minutes).
2. **The Mega Cherry Grove:** The single largest contiguous Cherry Grove biome discovered in the sweep (spanning over 1,200 blocks across mountain peaks).
3. **The Badlands Continental Spine:** Massive, unbroken Badlands / Mesa continent stretching across multiple kilometers with endless exposed terracotta and gold.
4. **The Endless Deep Dark Void:** Continuous Deep Dark cave trench connecting multiple Ancient Cities underground.

---

## 2. Dual-Mode Experience: Infinite Vanilla Worlds vs. Bordered Realms

A single underlying spatial geometry serves both infinite vanilla players and hardcore server administrators through differentiated presentation:

```mermaid
flowchart LR
    subgraph "Backend Engine (Unified Geometry)"
        B1["Bounding Box: 2048 x 2048 (Radius: 1,024 blocks)"]
        B2["Bounding Box: 4096 x 4096 (Radius: 2,048 blocks)"]
        B3["Bounding Box: 8192 x 8192 (Radius: 4,096 blocks)"]
        BN["Nether Box: 1024 x 1024 (Radius: 512 blocks)"]
    end

    subgraph "Track A: Vanilla / Infinite World (140M+ Players)"
        V1["<b>Walking Range:</b> ~1,000m radius from base"]
        V2["<b>Horse Range:</b> ~2,000m radius from base"]
        V3["<b>Elytra Range:</b> ~4,000m radius from base"]
        VN["<b>Nether Portal Hub:</b> ~500m sprint from portal"]
        VDesc["100% pure vanilla Minecraft. No addons, no commands.<br>High-density core zone; infinite world continues beyond."]
    end

    subgraph "Track B: Border Addon (Server Hosts)"
        R1["<b>2048 x 2048 World Border</b>"]
        R2["<b>4096 x 4096 World Border</b>"]
        R3["<b>8192 x 8192 World Border</b>"]
        RN["<b>1024 x 1024 Nether Border</b>"]
        RDesc["Physical barrier enforced by addon particle wall.<br>1-Click /scriptevent command script export."]
    end

    B1 -.-> V1 & R1
    B2 -.-> V2 & R2
    B3 -.-> V3 & R3
    BN -.-> VN & RN
```

### Pillar-to-Track Mapping Matrix

| Pillar | Mode / Track | Border Options Shown? | Target Audience |
|---|---|---|---|
| **Pillar 1: Optimal Realm God Seeds** | **Track B (Border Addon)** | ✅ **YES** (2048, 4096, 8192 options + `/scriptevent` scripts) | Dedicated SMP/Realm server hosts |
| **Pillar 2: Curated Play-Style Presets** | **Track A (Infinite Vanilla)** | ❌ **NO BORDERS** (Zero border dropdowns, 100% infinite vanilla) | Casual players seeking instant 1-click themed starts |
| **Pillar 3: Flexible Custom Search** | **Dual (Track A Default)** | ⚙️ **Optional Toggle** (Defaults to Travel Radius; Addon toggle for hosts) | Players/crews with custom feature wishlists |
| **Pillar 4: Record-Breakers & Outliers**| **Track A (Infinite Vanilla)** | ❌ **NO BORDERS** (Pure statistical records & freak spawns) | YouTubers, speedrunners, technical redstoners |

### The 8:1 Nether Coordinate Synchronization
Because 1 block in the Nether equals 8 blocks in the Overworld:
$$\text{Radius}_{\text{Nether}} \times 8 = 512 \times 8 = \mathbf{4,096 \text{ blocks in the Overworld}}$$
A single **$1024 \times 1024$ Nether border (512m radius)** naturally covers Overworld travel up to an **8192 border (4096m radius)**. Portals built anywhere inside the Overworld boundary are mathematically guaranteed to land inside the Nether boundary.

---

## 3. The 30-Bit Universal Multi-Dimensional Bitmask

The entire feature set of Minecraft (14 Overworld structures, 9 Overworld biomes, 2 Nether structures, and 5 Nether biomes) is mapped to a single 32-bit unsigned integer (`uint32_t`):

```text
================================= OVERWORLD (Bits 0 - 22) =================================
[Bit 00] Village              [Bit 06] Desert Pyramid      [Bit 12] Shipwreck
[Bit 01] Trial Chamber        [Bit 07] Jungle Temple       [Bit 13] Mineshaft
[Bit 02] Ancient City         [Bit 08] Swamp Hut           [Bit 14] Cherry Grove
[Bit 03] Woodland Mansion     [Bit 09] Igloo               [Bit 15] Mushroom Fields
[Bit 04] Ocean Monument       [Bit 10] Trail Ruins         [Bit 16] Bamboo Jungle
[Bit 05] Pillager Outpost     [Bit 11] Ruined Portal       [Bit 17] Desert
                                                           [Bit 18] Badlands
                                                           [Bit 19] Snowy Terrain
                                                           [Bit 20] Mangrove Swamp
                                                           [Bit 21] Forest / Birch
                                                           [Bit 22] Plains / Meadow

================================== NETHER (Bits 23 - 29) ==================================
[Bit 23] Nether Fortress      [Bit 25] Nether Wastes       [Bit 28] Soul Sand Valley
[Bit 24] Bastion Remnant      [Bit 26] Crimson Forest      [Bit 29] Basalt Deltas
                              [Bit 27] Warped Forest

*(Bits 30 & 31 reserved for future capability expansion)*
```

### Direct $O(1)$ Array Indexing Mechanics
```mermaid
flowchart LR
    A["Player Selects:<br>Village (0) + Trial (1) + Cherry (14) + Fortress (23)"] --> B["Compute Bitwise OR:<br>(1<<0) | (1<<1) | (1<<14) | (1<<23)"]
    B --> C["Single 32-Bit Integer:<br><b>Mask = 8,404,995</b>"]
    C --> D["Direct Memory Jump:<br><b>table[8404995]</b>"]
    D --> E["Returns Top 5 Verified Worlds in < 0.0001 ms!"]
```

---

## 4. Two-Tier Search Engine: Mask Existence + Continuous Proximity

To prevent rigid distance cutoffs from eliminating high-quality seeds, the engine separates **feature existence** from **proximity ranking**:

```mermaid
flowchart TD
    UserQuery["Player Custom Query:<br>• Range: ~2,000m (4096 area)<br>• Features: Village + Cherry Grove + Ancient City<br>• Desired Distance: ~500m (Flexible)"] --> T1
    
    subgraph "Tier 1: 30-Bit Mask Filter (Existence in Boundary)"
        T1["Convert Selection to 30-Bit Integer Mask<br>Query Table[mask] for 4096 Boundary"] --> CandPool["Returns Top Candidate Worlds possessing all 3 features in bounds (< 0.01 ms)"]
    end

    subgraph "Tier 2: Continuous Proximity Engine (Ranking & % Match)"
        CandPool --> CenterSolver["Check 81 Precalculated Centers per World:<br>Select the anchor that minimizes feature distances"]
        CenterSolver --> DistDecay["Calculate Soft Proximity Decay Score:<br>• Observed d <= Target D: 100% Score<br>• Observed d > Target D: Score = 1.0 - (d - D) / D"]
        DistDecay --> FinalSort["Rank Candidates by Weighted Match %:<br>1. Seed A: 98% Match (Village @ 180m, Cherry @ 90m)<br>2. Seed B: 91% Match (Village @ 420m, Cherry @ 310m)<br>3. Seed C: 74% Match (Village @ 1100m, Cherry @ 850m)"]
    end

    FinalSort --> UI["Deliver Top 50 Ranked Worlds with Interactive Visual Map"]
```

### Universal Anchor Coordinates & The "Borderless Vanilla" Model

> [!TIP]
> **Why the World Border Does NOT Constrain Vanilla Players:**  
> For 99% of normal players, there is **no world border** in their game. The world generates infinitely out to 30 million blocks with zero addons or commands. The bounding boxes ($2048, 4096, 8192$) exist purely as the **Search / Exploration Envelope** (how far the player wants to travel from their home base).

Every distance calculation uses Euclidean block geometry from the active anchor $(X_A, Z_A)$:
$$d = \sqrt{(X_F - X_A)^2 + (Z_F - Z_A)^2}$$

The user selects between three intuitive Starting Anchors:
1. **`Recommended Base` (Centroid in Envelope):** Our solver evaluates all 81 precalculated candidate centers in `[-976, 976]²` and picks the location with the absolute highest structure density and biome accessibility. Best for players who want the ultimate home base location.
2. **`World Spawn`:** Sets $(X_A, Z_A) = (X_{\text{spawn}}, Z_{\text{spawn}})$. Evaluates all features relative to where the player naturally steps into the world on Day 1.
3. **`World Origin (0,0)`:** Sets $(X_A, Z_A) = (0, 0)$. Evaluates features relative to the absolute map center coordinate (ideal for mapmakers and coordinated SMP nether hub builders).

Players can toggle between all three anchor modes instantly on any result card with zero page reloads.

---

## 5. High-Throughput GPU Ingestion Architecture

```mermaid
flowchart TD
    subgraph "Phase 1: CUDA Streaming Kernel (≥100M seeds/sec)"
        Stream["Trillion-Seed PRNG Generator"] --> PRNG["Evaluate 16 Structures & 14 Biomes in Registers"]
        PRNG --> Mask30["Compute 30-Bit Signature Integer"]
        Mask30 --> Filter{"Meets Admission Threshold?"}
        Filter -- "No (Common terrain, 0 dungeons)" --> Discard["Drop in Registers (0 bytes written)"]
        Filter -- "Yes (Meets Realm, Preset, Combo, or Record)" --> Compaction["Block-Level CUDA Stream Compaction"]
    end

    subgraph "Phase 2: Host Tracking Table (<400 MB RAM)"
        Compaction -->|PCIe DMA| RingBuffer["Pinned Host RAM Buffer"]
        RingBuffer --> DirectArray["Direct Array: Table[2^30] (Sparse Hash / Dense Buffer)<br>O(1) Direct Indexing in ~10 ns"]
        DirectArray --> Heaps["Maintain Top-K Min-Heaps:<br>• Pillar 1: Top 10k Realm Heaps (3 sizes)<br>• Pillar 2: Top 250 Preset Heaps (8 categories)<br>• Pillar 3: Top 5 Combinatorial Heaps (~100k masks)<br>• Pillar 4: Top 100 Record-Breaker Heaps (16 structures)"]
    end

    subgraph "Phase 3: Database Serialization"
        Heaps -->|End of Run| DedupEngine["Deduplicate ~101,000 Slots by Seed ID"]
        DedupEngine --> MasterSeeds["Final Corpus: ~70,000 Unique Worlds"]
        MasterSeeds --> Extractor["One-Time Full Extraction Pass (~2 hours):<br>• Absolute structure coordinates<br>• Y=63 64-block stride biome lattice<br>• Precomputed 81 centers x 46-byte distance cards"]
        Extractor --> DBFile[("catalog.seedcat (11.2 GB)")]
    end
```

---

## 6. Storage Sizing & Custom Binary Layout (`.seedcat`)

### Per-Seed Data Allocation
* **Raw Structure Starts:** ~250 coordinates $\times$ 10 bytes = **2.5 KB**
* **Y=63 Biome Grid (64-block stride, $160 \times 160$ samples):** **51.2 KB**
* **81 Center Layout Cards:** 81 centers $\times$ 46 bytes = **3.7 KB**
* **Metadata & Headers:** **0.6 KB**
* **Total per World:** $\approx \mathbf{150 \text{ KB raw}}$ ($\mathbf{\sim 50 \text{ KB compressed}}$).

### Catalog Totals (After Cross-Pillar Deduplication)
* **Pillar 1 (Realm God Seeds):** 30,000 slots $\rightarrow$ ~22,000 unique worlds
* **Pillar 2 (Curated Presets):** 6,000 slots $\rightarrow$ ~4,000 unique worlds
* **Pillar 3 (Flexible Combinations):** ~60,000 slots $\rightarrow$ ~40,000 unique worlds
* **Pillar 4 (Record Outliers):** 5,000 slots $\rightarrow$ ~4,000 unique worlds
* **Total Unique Physical Seeds:** $\mathbf{\approx 70,000 \text{ Worlds}}$
* **Total Disk Footprint:** $\mathbf{11.2 \text{ GB uncompressed}}$ ($\mathbf{\sim 3.8 \text{ GB compressed with Zstandard}}$).

---

## 7. Complete Web Interface Specification

### Navigation Hierarchy
```text
[Header: LOGO | Bedrock 1.21.x | Search Mode: (•) Infinite Vanilla  ( ) Bordered Realm | User / Quota]
├── / (Home / Landing): Hero Search, 8 Preset Cards, Top 3 Realm God Teasers, Hall of Fame Records
├── /realms (Pillar 1): Certified Realm God Vault, "Roll a God Seed" Randomizer, Starter Vibe Filter
├── /search (Pillar 3): Full Flexible 30-Bit Workspace, Split-Pane Sliders, Synchronized 2D Map
├── /records (Pillar 4): Hall of Fame Leaderboards (Max Villages, Max Trials, Quad Huts)
├── /seed/{id} (Detail): Full Single-World Dossier, Alternate Base Locations, Addon Script Export
└── /library: User Saved Worlds, Custom Seed Collections, Daily Digest Alerts
```

### Pillar 1: Realm God Seed Launcher Interface
```text
+-----------------------------------------------------------------------------------------------+
|  CERTIFIED REALM GOD SEEDS                                                                    |
|  Guaranteed in every seed: Stronghold, Mansion, Fortress, 2 Bastions, 2 Ancient Cities,       |
|  Villages >=6, Trials >=8, and Chunk-Aligned Borders. Zero resource depletion.               |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|  1. Playable Area / Border:       [ 1,000m (2048) ]   [ (2,000m (4096)) ]   [ 4,000m (8192) ] |
|                                                                                               |
|  2. Starting Location:           [ (Start Directly at Base) ]   [ Normal World Spawn ]        |
|                                                                                               |
|  3. Starter Base Vibe (Optional): [ (Surprise Me) ]  [ Cherry Mountain ]  [ Ocean ]  [Valley] |
|                                                                                               |
|                 [ 🎲 ROLL A CERTIFIED GOD SEED ]    or    [ View Top 3 Free Showcase ]        |
+-----------------------------------------------------------------------------------------------+
|  REVEALED RESULT (Rank #14 in 4096 Category):                                                 |
|  Seed: 849204810294   (Bedrock 1.21.x)                                Score: 1,180 / 1250 pts |
|  Base Anchor: X: 512, Z: 256  [Copy /tp]                              Addon Center: Chunk #32 |
|                                                                                               |
|  OVERWORLD HIGHLIGHTS:                        NETHER HIGHLIGHTS (Within 500m of Portal):      |
|  • 9 Villages within exploration range        • Nether Fortress at X: 64, Z: 32 (85m walk!)   |
|  • 11 Trial Chambers                          • 2 Bastion Remnants inside portal radius       |
|  • 2 Ancient Cities in Deep Dark              • Warped Forest & Crimson Forest adjacent       |
|  • Woodland Mansion at 380m                   • Chunk-aligned border particle walls           |
|                                                                                               |
|  [ Download Server Addon Scripts ]   [ Export Branded Discord Map Pack ]                      |
+-----------------------------------------------------------------------------------------------+
```

### Pillar 2: Curated Play-Style Presets Interface (Zero-Friction 1-Click Launchpad)

> [!NOTE]
> Presets have **NO world border selectors, NO distance radius sliders, and NO setup forms**.
> One click on any theme card instantly queries the precomputed catalog and displays verified infinite vanilla seeds.

```text
+-----------------------------------------------------------------------------------------------+
|  CURATED PLAY-STYLE PRESETS  (100% Free • Pure Infinite Vanilla Worlds • 1-Click Discovery)   |
+-----------------------------------------------------------------------------------------------+
|  [ 🌸 Cherry Blossom ]  [ 🎰 The Six-Pack ]  [ ⚡ Triple Start ]  [ ❄️ Frozen Frontier ]      |
|  [ 🏜️ Badlands Empire]  [ 🌊 Shipwreck Bay ] [ ⚔️ Raid Farm    ]  [ 🔥 Safe Nether   ] ...    |
+-----------------------------------------------------------------------------------------------+
|  SELECTED: 🌸 Cherry Blossom Haven (Cherry Grove + Plains Village <= 150m)                   |
|                                                                                               |
|  #1  Seed: 59281048201948   [ Copy Seed ]    [ View Interactive 2D Map ]                      |
|      Spawn: X: 120, Z: -64                                                                    |
|      • Plains Village at X: 160, Z: -40 (52m from spawn!)                                     |
|      • Cherry Grove Blossom Mountain at X: 180, Z: 20 (95m from spawn!)                        |
|                                                                                               |
|  #2  Seed: -1928401928401   [ Copy Seed ]    [ View Interactive 2D Map ]                      |
|      Spawn: X: -32, Z: 180                                                                    |
|      • Plains Village at X: 10, Z: 190 (43m from spawn!)                                      |
|      • Cherry Grove Blossom Valley at X: -90, Z: 240 (85m from spawn!)                        |
+-----------------------------------------------------------------------------------------------+
```

### Pillar 3: Flexible Personalized Search Interface
```text
+-----------------------------------------------------------------------------------------------+
|  PLAY STYLE:  (•) Infinite Vanilla World      ( ) World Border Addon                          |
|  Starter Radius: [ 1,000m (Walking) ]  [ (2,000m (Horse)) ]  [ 4,000m (Elytra) ]              |
+-----------------------------------+-----------------------------+-----------------------------+
| CONDITIONS PANEL                  | MATCHING WORLDS (Top 50)    | SYNCHRONIZED INTERACTIVE MAP|
|                                   |                             |                             |
| Overworld Structures:             | > World #1  (96% Match)     | +-------------------------+ |
| [x] Village >= 2   Near ~500m [X] |   Seed: 849204810294        | | [4096 Starter Boundary] | |
| [x] Trial Chamber  Near ~500m [X] |   Base: X: 512, Z: -256     | |     (1000m Ring)        | |
| [x] Ancient City   Inside Area    |   * 3 Villages @ 180m, 390m | |       (500m Ring)       | |
|                                   |   * Cherry Grove @ 95m      | |         [ Base: 512,-256] | |
| Overworld Biomes:                 |   * Trial Chamber @ 620m    | |  * Village                | |
| [x] Cherry Grove   Near ~250m [X] |   [Copy Seed] [Compare]     | |  # Trial Chamber          | |
|                                   | --------------------------- | |  ~ Cherry Grove (Sampled) | |
| Nether Objectives:                | > World #2  (91% Match)     | +-------------------------+ |
| [x] Nether Fortress Near Portal   |   Seed: -401928401924       | Alternate Bases in Seed:    |
| [x] Warped Forest   Near Portal   |   Base: X: 0, Z: 768        | [ Base 2: (0, 0) ] [Base 3] |
|                                   |                             |                             |
| [ + Add Feature ] [ Reset ]       |                             | Anchor Mode:                |
| [       SEARCH WORLDS       ]     |                             | [ (Base) ] [Spawn] [Origin] |
+-----------------------------------+-----------------------------+-----------------------------+
```

### Pillar 4: Hall of Fame & World Records Interface (/records)

> [!NOTE]
> The Hall of Fame displays the Top 100 verified seeds for each of the 50 statistical records discovered across the trillion-seed GPU sweep. All seeds are 100% infinite vanilla worlds.

```text
+-----------------------------------------------------------------------------------------------+
|  HALL OF FAME & WORLD RECORDS  (Bedrock 1.21.x • Powered by 1-Trillion Seed GPU Sweep)        |
+-----------------------------------------------------------------------------------------------+
|  SELECT LEADERBOARD:                                                                          |
|  [ 🏆 Most Villages (22) ]  [ ⚡ Most Trials (16) ]  [ 🏰 Mansion at Spawn ]  [ 🧙 Quad Huts ]|
|  [ 🏛️ Ancient City Cluster ] [ 💀 Fortress Overlap ] [ 🌸 Mega Cherry Grove ] [ 🌊 Sunken Fleet]|
+-----------------------------------------------------------------------------------------------+
|  CURRENT LEADERBOARD: 🏰 0m Woodland Mansion at Natural Spawn                                |
|                                                                                               |
|  #1  Seed: 84920194810294   [ Copy Seed ]    [ View Interactive Map ]  Distance: 18 blocks!   |
|      Spawn: X: 144, Z: -208  |  Biomes: Dark Forest + Meadow                                  |
|      Dossier: You literally spawn looking at the front entrance cobblestone steps.            |
|                                                                                               |
|  #2  Seed: -3901928401928   [ Copy Seed ]    [ View Interactive Map ]  Distance: 34 blocks!   |
|      Spawn: X: -64, Z: 512   |  Biomes: Dark Forest + Birch Forest                            |
|      Dossier: Mansion roof overhang directly above Day-1 spawn coordinate.                    |
|                                                                                               |
|  #3  Seed: 10492840192849   [ Copy Seed ]    [ View Interactive Map ]  Distance: 42 blocks!   |
|      Spawn: X: 0, Z: 12      |  Biomes: Dark Forest + Plains                                  |
+-----------------------------------------------------------------------------------------------+
```

---

## 8. Commercial Protection, Anti-Scraping & Monetization

### Asset-Specific Licensing (The Anti-Leak Guarantee)
* **1 Purchase = 1 Seed License:** Purchasing the Realm Master Bundle unlocks the dossier, coordinate sheets, and addon scripts for **that single chosen seed only**. Users never obtain bulk database access.
* **Daily Reveal Limits:** Paid Plus accounts are restricted to revealing full coordinate dossiers for a maximum of **15 to 20 seeds per day**, preventing automated web scraping.
* **Dynamic Watermarking:**
  * **Visible Watermark:** Every exported map PNG and PDF dossier contains permanent footer stamps:  
    `Licensed to: [Username] | Order #[ID] | Single-Realm License`.
  * **Invisible Watermarking:** The purchaser's account ID is steganographically embedded into image pixel LSBs and zero-width text formatting. Any unauthorized online distribution can be traced back to the exact user account.
* **Cloud-Only Raw Geometry:** Raw binary observation matrices stay behind the server firewall; user browsers receive only compressed viewport rendering coordinates.

### Commercial Tier Matrix

| Feature | Free Visitor ($0) | Explorer Plus ($4.99/mo or $2.99/wk) | Realm Master Bundle ($9.99 One-Time) |
|---|---|---|---|
| **Presets (Pillar 2)** | Full Access (Top 250) | Full Access (Top 250) | Full Access (Top 250) |
| **Realm God Seeds (Pillar 1)** | Top 3 Showcase Seeds | Full Vault Access (10k seeds) | **Single Seed Full Claim & License** |
| **"Roll a God Seed"** | 1 Roll / Day | Unlimited Rolls | Unlimited Rolls |
| **Search Sliders (Pillar 3)** | Up to 3 Filters | **All 30 Sliders Unlocked** | **All 30 Sliders Unlocked** |
| **Searches per Day** | 20 / day | 200 / day | 200 / day |
| **Maximum Search Range** | 1,000m (2048) | 4,000m (8192) | 4,000m (8192) |
| **Interactive Map & Compare** | Basic View (2 Worlds) | Advanced View (5 Worlds) | Advanced View (5 Worlds) |
| **Addon Scripts (`/scriptevent`)**| Locked | Locked | **1-Click Command Script Pack** |
| **Branded Discord Map Pack** | Locked | Locked | **High-Res PNG/PDF Dossier** |
