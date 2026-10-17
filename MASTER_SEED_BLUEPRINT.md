# Master Seed Blueprint: Bedrock 15–20 Player Server (2048 × 2048)

> **Specification Status:** Approved Engineering Blueprint Specification (Revision 6.0 - Dynamic Envelope v3 2048x2048 Realm Scale - October 2026).
> **Pipeline Policy:** `dynamic-envelope-2048-v3` with sliding constrained-centroid cluster center $(C_X, C_Z)$ within a $4000 \times 4000$ Overworld macro-envelope ($[-2000, 2000)$) and $1268 \times 1268$ Nether preflight envelope ($[-634, 634)$).
> **Historical Archive Notice:** The previous $1664 \times 1664$ Overworld / $832 \times 832$ Nether specification is preserved as historical reference at [`MASTER_SEED_BLUEPRINT_1664_V2.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT_1664_V2.md) and [`docs/historical_reports/MASTER_SEED_BLUEPRINT_1664_V2.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/docs/historical_reports/MASTER_SEED_BLUEPRINT_1664_V2.md), alongside `dynamic-envelope-1664-v1`. Both remain fully readable and valid for historical database replay.
> **Target Game Version:** Minecraft Bedrock Edition 1.21+ (pinned `MC_26_50`; live BDS target 1.26.52.3).
> **Target Community:** 15–20 Players (High-density active server; shared central starter hub; distributed homestead districts; zero resource depletion).
> **Certification Decoupling:** Defines approved architectural targets, hard floors, and scoring models. In-engine verification (End Portal rooms, loot, cave carver entrances, initial player spawn) requires additional evidence. The current headless provider establishes bounded surface observations; it does not establish those other features.

---

## 1. World Boundaries & Exact Geometric Coordinates

The realm operates on a sliding-window coordinate system that decouples world spawn from the playable center while preserving strict integer coordinate validity, 8:1 dimensional scaling, and chunk-grid alignment where achievable.

| Dimension / Region | Exact Dimensions | Center Coordinate | Chunk Extent | Distance to Edge | Mathematical Definition & Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Overworld Macro Envelope** | **4000 × 4000** | Origin `(0, 0)` | $250 \times 250$ chunks | Radius 2,000m | Search bounds for Stage 1A preflight ($X, Z \in [-2000, 2000)$). |
| **Nether Preflight Envelope** | **1268 × 1268** | Origin `(0, 0)` | $79.25 \times 79.25$ chunks | Radius 634m | Fast chunk-grid PRNG search bounds for Stage 1A Nether checks ($X_N, Z_N \in [-634, 634)$). Exactly covers all possible Nether centers ($\pm 122\text{m}$) plus 512m half-width. |
| **Playable Overworld** | **2048 × 2048** | **Dynamic Center $(C_X, C_Z)$** | $128 \times 128$ chunks | Radius 1024m | Bounded within the half-open window $[C_X - 1024, C_X + 1024) \times [C_Z - 1024, C_Z + 1024)$, where $(C_X, C_Z) \in [-976, 976]^2$. Exactly 2048 blocks = 128 chunks. Border inclusions: West ($X = C_X - 1024$) and North ($Z = C_Z - 1024$) included; East ($X = C_X + 1024$) and South ($Z = C_Z + 1024$) excluded. Snapped to the nearest valid multiple of 16 per axis, falling back to 8 without leaving the safe cell $\mathcal{S}_{\text{safe}}$. |
| **Playable Nether** | **1024 × 1024** | **Scaled Center $(C_X/8, C_Z/8)$** | $64 \times 64$ chunks | Radius 512m | Bounded within the half-open window $[C_X/8 - 512, C_X/8 + 512) \times [C_Z/8 - 512, C_Z/8 + 512)$, where $(C_X/8, C_Z/8) \in [-122, 122]^2$. West and North included; East and South excluded. Guaranteed exact integer block coordinate for `/scriptevent worldborder:center nether <X> <Z>`. Radius 512m provides a $4\times$ area buffer relative to the 256-block portal-scaled Overworld footprint; geometry alone does not certify portal behavior. |

---

## 2. Dynamic Sliding Window: Three-Defense Geometric & Alignment Architecture

In a $2048 \times 2048$ bounding box, the outer boundary shell accounts for **75% of the total surface area**. Without spatial safeguards, unconstrained sliding windows place key structures at the border perimeter. The blueprint guarantees dense interior clustering and flawless world border alignment via a three-defense geometric architecture:

### Defense 1: 2D Event-Slab Interior Solver
- Projects every discovered structure coordinate into entry/exit slab events on half-open intervals:
  - Overworld structures at $(X_i, Z_i)$ are captured when $C_X - 1024 \le X_i < C_X + 1024$. For integer centers $C_X$, this yields entry at $X_i - 1023$ and exit past $X_i + 1024$ (candidate safe interval $[X_i - 1023, X_i + 1024]$ of width 2048). This produces an exact $+1$ entry-event asymmetry relative to continuous-space models ($[X_i - 1024, X_i + 1024]$).
  - Nether structures at $(X_{N,j}, Z_{N,j})$ are projected into Overworld center space via the 8:1 dimensional scale ($C_X/8 - 512 \le X_{N,j} < C_X/8 + 512 \iff C_X - 4096 \le 8X_{N,j} < C_X + 4096$). For integer centers $C_X$, this yields entry at $8X_{N,j} - 4095$ and exit past $8X_{N,j} + 4096$ (candidate safe interval $[8X_{N,j} - 4095, 8X_{N,j} + 4096]$ of width 8192).
- Solves 2D equivalence cells formed by the Cartesian product of event intervals where structure counts and lattice samples are strictly invariant, selecting the cell representative that minimizes distance to the coordinate midpoint.

### Defense 2: Centroid Magnet Pull with Feasible Safe-Zone Clamping
Once a valid equivalence cell is established, the exact center $(C_X, C_Z)$ is pulled toward the weighted center-of-mass (centroid) of the captured settlement structures, heavily concentrating villages and dungeons toward the center of the world:

$$C_X^* = \frac{\sum_{i=1}^N \omega_i X_i}{\sum_{i=1}^N \omega_i}, \qquad C_Z^* = \frac{\sum_{i=1}^N \omega_i Z_i}{\sum_{i=1}^N \omega_i}$$

#### Centroid Weight Distribution ($\omega_i$, Capped at 3)
To prevent massive structures from disproportionately dragging the center away from human settlements, pull weights are strictly capped at 3:
- 🏘️ **All Villages:** $\omega = 2$ each (Primary settlement anchor; rebalanced from 3 to prevent over-dominance)
- ⚔️ **All Trial Chambers:** $\omega = 1$ each (Rebalanced from 2 to prevent underground grid noise)
- 🏰 **Stronghold:** $\omega = 3$ (Elevated from 1 to prioritize End portal proximity)
- 🌌 **All Ancient Cities:** $\omega = 2$ each (Deep exploration anchor)
- 🏴‍☠️ **All Pillager Outposts:** $\omega = 1$ each
- 🏺 **All Desert Pyramids & Jungle Temples:** $\omega = 2$ each (v3 upgrade from 1 in v2)
- 🏛️ **Woodland Mansion:** $\omega = 2$ (v3 upgrade from 1 in v2)
- 🗿 **Ocean Monument:** $\omega = 1$
- 🌀 **All Ruined Portals:** $\omega = 0$ (zeroed to prevent pulling center away from human settlements)
- ⛵ **All Shipwrecks:** $\omega = 0$ (zeroed to prevent pulling center into open ocean)
- ⛏️ **All Mineshafts:** $\omega = 0$ (zeroed to prevent pulling center underground)

#### Feasible Safe-Zone Clamping ($\mathcal{S}_{\text{safe}} = \mathcal{S}_{\text{OW}} \cap \mathcal{S}_{\text{Nether}}$)
The centroid pull is strictly constrained to the Feasible Safe Zone to guarantee that no floor-qualifying structure is ever displaced across the border. Incorporating the half-open window boundary logic:
- **Overworld Safe Interval:** For every required Overworld structure $i$, $C_X \in [X_i - 1023, X_i + 1024]$ and $C_Z \in [Z_i - 1023, Z_i + 1024]$ (exact width 2048 integer coordinates per axis).
- **Nether Safe Interval:** For every required Nether Fortress and Bastion $j$, projected as $C_X \in [8X_{N,j} - 4095, 8X_{N,j} + 4096]$ and $C_Z \in [8Z_{N,j} - 4095, 8Z_{N,j} + 4096]$ (exact width 8192 integer coordinates per axis in Overworld scale).
- Clamping: $(C_X^*, C_Z^*) = \text{clamp}\big((C_X^*, C_Z^*),\; \mathcal{S}_{\text{safe}}\big)$, where $\mathcal{S}_{\text{safe}} = \mathcal{S}_{\text{OW}} \cap \mathcal{S}_{\text{Nether}} \cap [-976, 976]^2$. This projection guarantees that required Overworld and Nether structures can never be lost.

### Defense 3: Chunk-Grid & Addon-Safe Center Snapping Protocol
To ensure seamless integration with the server's [Bedrock World Border Addon](https://www.curseforge.com/minecraft-bedrock/addons/bedrock-world-border) while strictly maintaining structure retention, $(C_X^*, C_Z^*)$ is snapped per axis within $\mathcal{S}_{\text{safe}}$:

1. **Snapping Protocol (Evaluated Per Axis within $\mathcal{S}_{\text{safe}}$):**
   - For each axis interval $[lo, hi]$ defining the safe cell $\mathcal{S}_{\text{safe}}$:
     - **Primary Target (Multiple of 16):** Determine the valid integer range of multiples of 16 within $[lo, hi]$:
       $$\text{lower}_{16} = \left\lceil \frac{lo}{16} \right\rceil \times 16, \qquad \text{upper}_{16} = \left\lfloor \frac{hi}{16} \right\rfloor \times 16$$
       If $\text{lower}_{16} \le \text{upper}_{16}$, at least one valid multiple of 16 exists inside $\mathcal{S}_{\text{safe}}$. Round the weighted centroid coordinate to the nearest multiple of 16:
       $$C_{\text{snap}} = 16 \times \left\lfloor \frac{C^* + 8}{16} \right\rfloor$$
       and clamp $C_{\text{snap}}$ to $[\text{lower}_{16}, \text{upper}_{16}]$.
     - **Secondary Fallback (Multiple of 8):** In the rare event that no multiple of 16 falls within $[lo, hi]$ ($\text{lower}_{16} > \text{upper}_{16}$), fall back to the nearest valid multiple of 8 within $\mathcal{S}_{\text{safe}}$:
       $$\text{lower}_8 = \left\lceil \frac{lo}{8} \right\rceil \times 8, \qquad \text{upper}_8 = \left\lfloor \frac{hi}{8} \right\rfloor \times 8$$
       Round the centroid coordinate to the nearest multiple of 8 ($8 \times \lfloor (C^* + 4)/8 \rfloor$) and clamp to $[\text{lower}_8, \text{upper}_8]$. Snapping never leaves the safe cell $\mathcal{S}_{\text{safe}}$.

2. **Distinguishing Block Dimensions from Chunk Alignment:**
   - **Block Dimensions vs. Chunk Borders:** The Overworld window is fixed at exactly $2048 \times 2048$ blocks ($128 \times 128$ chunks, radius 1024m), and the Nether window is fixed at $1024 \times 1024$ blocks ($64 \times 64$ chunks, radius 512m).
   - **When Snapping to 16:** Because the Overworld half-width is $1024 = 64 \times 16$, snapping $C_X, C_Z$ to a multiple of 16 guarantees that both borders $[C \pm 1024]$ land exactly on chunk boundaries ($16k \pm 64 \times 16 = 16(k \pm 64) \equiv 0 \pmod{16}$). No chunk is split in half by the world border particle wall, and the scaled Nether center $(C_X/8, C_Z/8)$ is an even integer ($2k$).
   - **When Snapping to Fallback-8 (Odd Multiples of 8):** If $C$ is an odd multiple of 8 ($C = 16k + 8$), the outer boundary lands at $16k + 8 \pm 64 \times 16 \equiv 8 \pmod{16}$. **A fallback-8 border will cut a chunk in half** at block offset 8. Fallback-8 Overworld centers and integer Nether centers do *not* guarantee chunk-aligned borders.
   - **Addon Integer Command Requirement:** What fallback-8 *does* strictly guarantee is that $(C_X/8, C_Z/8)$ is an exact integer block coordinate ($(16k + 8)/8 = 2k + 1 \in \mathbb{Z}$). The deployment command target `/scriptevent worldborder:center nether <X> <Z>` is expressed using integer coordinates; addon behavior and portal safety still require runtime verification. Snapping to 8 prevents fractional Nether centers (which would occur if centers were not snapped) and preserves the selected starts within $\mathcal{S}_{\text{safe}}$.

---

## 3. Structure Inventory, Tolerance Matrix & Guaranteed Baseline ($B = 0$ Pure Additive System)

Every qualifying candidate **must strictly satisfy the Guaranteed Hard Floors under a Zero Miss Budget $B = 0$ (`max_misses = 0`) pure additive system**.

### The Guaranteed Baseline & Zero Miss Budget ($B = 0$)
1. **Instant Rejection (Hard Floors):** Any seed that drops below the **Hard Floor** for *any* structure category is instantly disqualified in Stage 1 C screening. Hard floors are non-negotiable baseline entry requirements; falling below any floor is fatal.
2. **Pure Additive Scoring (Zero Deficit Penalties):** Active v3 operates with Miss Budget $B = 0$ (`max_misses = 0`) where hard floors are non-negotiable baseline entry requirements, and deficit penalties are strictly 0. Every candidate meeting all hard floors qualifies for the pool with 0 surplus points, and every structure exceeding baseline adds stacking positive points.
3. **Historical Comparison:** Historical v2 permitted a miss budget $B \le 3$ with deficit deductions (-5 pts for Ruined Portal and Shipwreck; -10 pts for Village, Trial Chamber, Ancient City, Desert Pyramid, Jungle Temple, and Mineshaft). Historical v1 permitted at most $B \le 2$ deficits. Active v3 eliminates deficit deductions entirely in favor of a guaranteed baseline and pure additive scoring.

> **Custom palette searches:** The UI may explicitly select a subset (including none) of the 13 supported Overworld biome families for a v2/v3 search. The selection is saved in `biomes.required_families` and enforced by native and reference evaluation. These custom results satisfy the selected palette, not necessarily the full default blueprint palette. The default remains all 13; Nether requirements and structure viability are unchanged.

### Active v3 Structure Tolerance Matrix ($2048 \times 2048$ Overworld / $1024 \times 1024$ Nether)

Counts are complete predictor counts within the selected window. Hard floors constrain predictions; actual generation remains unverified. Bonuses below use the capped v2/v3 schedule in Section 5.1. Explicit historical v1 configurations retain their original scoring.

| Structure Category | Dimension | Guaranteed Hard Floor | Progressive Surplus Points Schedule (+) | Scoring & Realm Role |
| :--- | :---: | :---: | :--- | :--- |
| 🏰 **Stronghold** | Overworld | **$\ge 1$** | 2nd = **+30 pts**, 3rd = **+20 pts** (**+50 max**) | **Non-negotiable.** Predicted End-access start; portal room unverified. |
| 🏛️ **Woodland Mansion** | Overworld | **$\ge 1$** | 2nd = **+45 pts**, 3rd+ = **+25 pts** (**+70 max**) | **Mandatory $\ge 1$.** Guaranteed Dark Forest start at Y=63. |
| 🗿 **Ocean Monument** | Overworld | **$\ge 1$** | 2nd = **+25 pts**, 3rd = **+15 pts**, 4th+ = **+10 pts** (**+50 max**) | **Mandatory $\ge 1$.** Prismarine, sponges, conduit core. |
| 🏴‍☠️ **Pillager Outpost** | Overworld | **$\ge 1$** | 2nd = **+15**, 3rd = **+15**, 4th+ = **+10** (**+40 max**) | **Mandatory $\ge 1$.** Infinite Bad Omen & raid farming. |
| 🔥 **Nether Fortress** | Nether | **$\ge 1$** | 2nd = **+20**, 3rd = **+15**, 4th+ = **+15** (**+50 max**) | **Mandatory $\ge 1$** inside $1024 \times 1024$ Nether. Blaze rods & skulls. |
| 🐷 **Bastion Remnant** | Nether | **$\ge 2$** | 3rd = **+20**, 4th = **+15**, 5th+ = **+15** (**+50 max**; +20 Treasure variant) | **Mandatory $\ge 2$** inside $1024 \times 1024$ Nether. Piglin bartering & upgrade trims. |
| 🏘️ **Villages** | Overworld | **$\ge 6$** | 7th..11th+ = **+10 each** (**+50 max**) | Guaranteed baseline $\ge 6$. Rewards mega-settlements. |
| ⚔️ **Trial Chambers** | Overworld | **$\ge 8$** | 9th = **+10**, 10th = **+10**, 11th = **+10**, 12th = **+8**, 13th+ = **+7** (**+45 max**) | Guaranteed baseline $\ge 8$. Heavy Cores, maces, Ominous Vaults. |
| 🌌 **Ancient City** | Overworld | **$\ge 2$** | 3rd = **+20**, 4th = **+20**, 5th = **+15**, 6th+ = **+10** (**+65 max**) | Guaranteed baseline $\ge 2$. Swift Sneak, Silence Trim, Wardens. |
| 🏺 **Desert Pyramid** | Overworld | **$\ge 1$** | 2nd = **+25**, 3rd = **+20**, 4th+ = **+15** (**+60 max**) | Guaranteed baseline $\ge 1$. Desert archaeology & enchanted apples. |
| 🌿 **Jungle Temple** | Overworld | **$\ge 1$** | 2nd = **+25**, 3rd = **+20**, 4th+ = **+15** (**+60 max**) | Guaranteed baseline $\ge 1$. Redstone puzzle & jungle exploration. |
| ⛵ **Shipwrecks** | Overworld | **$\ge 4$** | 5th..8th+ = **+5 each** (**+20 max**) | Guaranteed baseline $\ge 4$. Early iron, emeralds, treasure maps. |
| 🌀 **Ruined Portals** | Overworld | **$\ge 8$** | 9th..12th+ = **+5 each** (**+20 max**) | Guaranteed baseline $\ge 8$. Fast Nether transit & crying obsidian. |
| ⛏️ **Mineshafts** | Overworld | **$\ge 10$** | +2 each over 10 (**+20 max**) | Guaranteed baseline $\ge 10$. Rails, mob spawners, chest minecarts. |
| 🧙 **Swamp Hut (Witch Hut)** | Overworld | $\ge 0$ | 1st = **+25 pts**, 2nd = **+15 pts**, 3rd+ = **+10 pts** (**+50 max**) | Optional Stage 4 bonus. Predicted witch-farm start. |
| 🛖 **Igloo (with Basement)**| Overworld | $\ge 0$ | 1st = **+30 pts**, 2nd+ = **+20 pts** (**+50 max**) | Optional Stage 4 bonus. Pinned MC_26_50 basement prediction. |
| 🏺 **Trail Ruins** | Overworld | $\ge 0$ | 1st = **+25 pts**, 2nd = **+15 pts**, 3rd+ = **+10 pts** (**+50 max**) | Optional Stage 4 bonus. Archaeology pottery sherds & armor trims. |

> [!IMPORTANT]
> **Implementation Capabilities vs. Approved Blueprint Design (Group D Audit Reconciliation):**
> - **Approved Design vs. Implementation Certification:** The blueprint defines the approved realm targets, hard floors, miss budget, and mathematical scoring architecture. Approved design targets must be strictly distinguished from runtime implementation certification.
> - **Predictor Support for Optional Structures:** Optional structures (Swamp Hut, Trail Ruins, Ocean Ruins, Buried Treasure) have predictors in the Python backend. Furthermore, the pinned vendor backend (`cubiomes-bedrock`) implements a dedicated Igloo basement PRNG predictor (`getVariant`, Igloo case, `StructureVariant.basement` flag).
> - **Prediction Does Not Establish Actual Generation:** Algorithmic PRNG candidate prediction establishes chunk coordinate eligibility, but does *not* establish actual physical block generation in Bedrock Edition. In live world generation, local terrain displacement, waterlogging, surface carvers, and chunk decoration can suppress or displace structure generation.
> - **Unverified Runtime Features:** Mega-cave entrances, complete End Portal rooms (`portal_room_present=true`), chest loot tables, and initial player spawn coordinates cannot be verified by algorithmic predictor stages (Stages 1–4) and remain unverified; the current bounded surface-point provider does not establish them.

---

## 4. Stage 2: 13-Biome Diversity Palette (4-Y Lattice Verification)

Evaluated across four vertical reference planes ($Y = 63, -48, 0, 160$) using 2D prefix sums:
1. 🌾 **Plains Family:** Plains, Sunflower Plains, or Meadow (starter agriculture & flat building).
2. 🏜️ **Desert:** Sand, cactus, glass production, pyramids.
3. 🌲 **Forest / Birch Forest:** Primary timber and starter survival resources.
4. 🐺 **Taiga:** Spruce timber, sweet berries, wolves.
5. 🌴 **Jungle:** Jungle wood, cocoa, bamboo, temples.
6. 🐸 **Swamp:** Slimeballs, mud bricks, clay, frogs.
7. ❄️ **Snowy / Ice Biome:** Packed ice and blue ice for high-speed Nether transportation.
8. 🍄 **Dark Forest:** Dark oak wood, huge mushrooms, Woodland Mansion biome envelope.
9. 🏔️ **High Peaks & Cliffs:** Dramatic high-altitude summits (`jagged_peaks | frozen_peaks | stony_peaks`) for elytra launch towers and goats.
10. 🌊 **Stony Shore:** Sheer cliffs dropping into coastal water.
11. 🌿 **Lush Caves:** Azalea, glow berries, axolotls ($Y = -16$ to $-48$).
12. 💧 **Dripstone Caves:** Pointed dripstone, infinite lava cauldrons ($Y = 0$ to $-48$).
13. 🌌 **Deep Dark:** Sculk catalysts, shriekers, Ancient City foundation zone ($Y \le -10$).

### Complete 5-Biome Nether Palette (Inside 1024 × 1024 Playable Nether)
Because players cannot travel or mine outside the $1024 \times 1024$ Nether border, Stage 2 enforces that all **5 Nether biomes** exist within the half-open window $[C_X/8 - 512, C_X/8 + 512) \times [C_Z/8 - 512, C_Z/8 + 512)$ via a fast half-open $16 \times 16$ lattice check ($256$ interior sample points at $Y = 64$ with 64-block spacing, taking $<0.3\text{ ms}$, preventing boundary overflow):
1. 🔥 **Nether Wastes:** Quartz, glowstone, zombie piglins.
2. 🌲 **Crimson Forest:** Crimson wood/fungus, shroomlights, weeping vines, hoglins (essential renewable food/leather).
3. 🍄 **Warped Forest:** Warped wood/fungus, twisting vines, safe haven from piglins/hoglins, enderman pearl farming.
4. 💀 **Soul Sand Valley:** Soul sand, soul soil (soul speed highways), ghasts, bone blocks.
5. 🌋 **Basalt Deltas:** Basalt, blackstone, magma cubes.

### Stage 2 Multi-Plane Short-Circuiting Protocol
To minimize sampling overhead, Stage 2 evaluates vertical planes with aggressive early exits:
- **Plane $Y = 160$ (High Peaks):** Breaks immediately upon detecting the first cell of `jagged_peaks`, `frozen_peaks`, or `stony_peaks`.
- **Planes $Y = 0$ & $Y = -48$ (Underground Caverns):** Deep Dark is already certified by $\ge 2$ Ancient Cities. The underground scan breaks immediately once at least 1 cell of `lush_caves` and 1 cell of `dripstone_caves` (plus the 512m hub mega-cave witness) are confirmed. *(Note: Cave witnesses verify underground biome cell occupancy; physical cavern entrances, opening geometry, and navigability remain unverified by predictor models.)*
- **Plane $Y = 63$ (Surface):** Dark Forest, Desert, and Jungle are already certified by Stage 1B structures. Only remaining surface families are evaluated.

---

## 5. Stage 3/4: Dynamic Starter Hub & Comprehensive Scoring

### 5.1 Active `dynamic-envelope-2048-v3` Player Scoring Architecture (1,250-Point Pure Additive System)

Under the active `dynamic-envelope-2048-v3` specification, scoring operates on a **pure additive dynamic system** with **zero deficit penalties** and a **1,250-Point Master Architecture** (`Core Surplus: 650 max` + `Optional Structures: 200 max` + `Luxury Biomes: 265 max` + `Spatial & Nether Core: 135 max`). Every candidate that satisfies all 14 Guaranteed Hard Floors qualifies for the candidate pool. Beyond the guaranteed baseline, every extra structure, optional feature, luxury biome, and spatial amenity progressively adds stacking points. A baseline qualifying seed meeting hard floors receives exactly **0 surplus points**.

$$\mathbf{Total\ Smart\ Score} = \text{Core Surplus (650)} + \text{Optional Structures (200)} + \text{Luxury Biomes (265)} + \text{Spatial Layout \& Nether Core (135)} = \mathbf{1,250\ Pts\ Max}$$

- **No Deficit Minuses (-):** You never subtract points. The deficit penalty is strictly $0$, and Miss Budget is $B = 0$ (`max_misses = 0`).
- **Hard Floor = Baseline Entry Ticket:** Meeting every hard floor guarantees baseline qualification. A seed below any floor is fatal.
- **Top-50 Ratchet Cutoff Bar ($S_{50}$):** The in-memory Top-50 Tracker maintains a size-50 min-heap. Once 50 candidates are found, the 50th score ($S_{50}$) automatically acts as an upper-bound cutoff to prune non-competitive seeds in C before allocation.

#### A. Core Structure Surplus Schedule (14 Categories | $F = 0\text{ pts}$ | 650 Pts Max)
Structure points start accumulating the moment a structure exceeds its Guaranteed Hard Floor ($F$). All categories have concave diminishing returns and hard caps:

| Category | Dim | Hard Floor ($F$) | Pts at $F$ | Surplus Schedule ($F+1$ onward) | Category Cap | Lookup Array (`LUT`) |
| :--- | :---: | :---: | :---: | :--- | :---: | :--- |
| 🏛️ **Woodland Mansion** | OW | **1** | 0 pts | 2nd = **+45**, 3rd+ = **+25** | **+70 pts** *(at 3+)* | `{0, 45, 70}` |
| 🏺 **Desert Pyramid** | OW | **1** | 0 pts | 2nd = **+25**, 3rd = **+20**, 4th+ = **+15** | **+60 pts** *(at 4+)* | `{0, 25, 45, 60}` |
| 🌿 **Jungle Temple** | OW | **1** | 0 pts | 2nd = **+25**, 3rd = **+20**, 4th+ = **+15** | **+60 pts** *(at 4+)* | `{0, 25, 45, 60}` |
| 🌌 **Ancient City** | OW | **2** | 0 pts | 3rd = **+20**, 4th = **+20**, 5th = **+15**, 6th+ = **+10** | **+65 pts** *(at 6+)* | `{0, 20, 40, 55, 65}` |
| 🏰 **Stronghold** | OW | **1** | 0 pts | 2nd = **+30**, 3rd+ = **+20** | **+50 pts** *(at 3+)* | `{0, 30, 50}` |
| 🗿 **Ocean Monument** | OW | **1** | 0 pts | 2nd = **+25**, 3rd = **+15**, 4th+ = **+10** | **+50 pts** *(at 4+)* | `{0, 25, 40, 50}` |
| 🐷 **Bastion Remnant** | Nether | **2** | 0 pts | 3rd = **+20**, 4th = **+15**, 5th+ = **+15** | **+50 pts** *(at 5+)* | `{0, 20, 35, 50}` |
| 🔥 **Nether Fortress** | Nether | **1** | 0 pts | 2nd = **+20**, 3rd = **+15**, 4th+ = **+15** | **+50 pts** *(at 4+)* | `{0, 20, 35, 50}` |
| 🏘️ **Village** | OW | **6** | 0 pts | 7th..11th+ = **+10 each** | **+50 pts** *(at 11+)* | `{0, 10, 20, 30, 40, 50}` |
| 🏴‍☠️ **Pillager Outpost** | OW | **1** | 0 pts | 2nd = **+15**, 3rd = **+15**, 4th+ = **+10** | **+40 pts** *(at 4+)* | `{0, 15, 30, 40}` |
| ⚔️ **Trial Chamber** | OW | **8** | 0 pts | 9th = **+10**, 10th = **+10**, 11th = **+10**, 12th = **+8**, 13th+ = **+7** | **+45 pts** *(at 13+)* | `{0, 10, 20, 30, 38, 45}` |
| 🌀 **Ruined Portal** | OW | **8** | 0 pts | 9th..12th+ = **+5 each** | **+20 pts** *(at 12+)* | `{0, 5, 10, 15, 20}` |
| ⛵ **Shipwreck** | OW | **4** | 0 pts | 5th..8th+ = **+5 each** | **+20 pts** *(at 8+)* | `{0, 5, 10, 15, 20}` |
| ⛏️ **Mineshaft** | OW | **10** | 0 pts | 11th..20th+ = **+2 each** | **+20 pts** *(at 20+)* | `min(20, max(0, count - 10) * 2)` |

*(Sum of all core surplus caps: $70 + 60 + 60 + 65 + 50 + 50 + 50 + 50 + 50 + 40 + 45 + 20 + 20 + 20 = \mathbf{650\text{ pts}}$).*

#### B. Optional Structure Schedule (5 OW Categories | $F = 0$ | 200 Pts Max)
No hard floors. Discovered qualifying structures award bonuses up to individual category caps:
- 🧙 **Swamp Huts:** 1st = **+25 pts**, 2nd = **+15 pts**, 3rd+ = **+10 pts** (**+50 pts max** at 3+).
- 🏺 **Trail Ruins:** 1st = **+25 pts**, 2nd = **+15 pts**, 3rd+ = **+10 pts** (**+50 pts max** at 3+).
- 🛖 **Basement Igloos:** 1st = **+30 pts**, 2nd+ = **+20 pts** (**+50 pts max** at 2+).
- 💎 **Buried Treasure:** 1st = **+10 pts**, 2nd = **+10 pts**, 3rd = **+5 pts**, 4th+ = **+5 pts** (**+30 pts max** at 4+).
- 🌊 **Ocean Ruins:** 1st = **+10 pts**, 2nd+ = **+10 pts** (**+20 pts max** at 2+).

*(Sum of all optional bonuses: $50 + 50 + 50 + 30 + 20 = \mathbf{200\text{ pts}}$).*

#### C. Luxury Biomes (10 Categories + Tiered Diversity Jackpot | 265 Pts Max)
Evaluated on the 64-block world lattice at $Y=63$:
- 🍄 **Mushroom Fields (Mooshroom Island):** **+40 pts**
- 👻 **Pale Garden:** **+35 pts**
- 🏜️ **Badlands / Mesa / Eroded Badlands:** **+35 pts**
- 🌸 **Cherry Grove:** **+25 pts**
- 🧊 **Ice Spikes:** **+25 pts**
- 🪸 **Warm Ocean / Coral Reef:** **+20 pts**
- 🌲 **Old Growth Taiga:** **+20 pts**
- 🌺 **Flower Forest:** **+15 pts**
- 🌾 **Windswept Savanna / Plateau (including ordinary Savanna):** **+15 pts** (matches `savanna`, `savanna_plateau`, `windswept_savanna`, and `shattered_savanna`)
- 🎋 **Bamboo Jungle:** **+10 pts**
- 💎 **Tiered Diversity Jackpot:**
  - Presence of $\ge 5$ distinct luxury biomes inside window: **+10 pts**
  - Presence of $\ge 7$ distinct luxury biomes inside window: **+25 pts** *(extra +15 pts)*

*(Sum of 10 individual luxury biomes: $40 + 35 + 35 + 25 + 25 + 20 + 20 + 15 + 15 + 10 = 240\text{ pts}$ + Jackpot $25\text{ pts} = \mathbf{265\text{ pts max}}$).*

#### D. Spatial, Layout & Nether Core Bonuses (135 Pts Max)
- 📍 **Starter Hub Proximity (+45 pts max):**
  - Village within 256m (**+15 pts**) or 512m (**+10 pts**).
  - Hub structures within 512m of $(C_X, C_Z)$: Desert Pyramid, Jungle Temple, Outpost, and Ancient City at **+6 pts each**; Ruined Portal at **+4 pts each** (matching C `nb_dynamic_v3_hub` and Python `hub_bonus_v3`, combined non-village cap **+30 pts max**).
- 🔥 **Nether 256m Portal Core & Treasure Bastion (+40 pts max):**
  - **Treasure Bastion Variant:** **+20 pts** if a viable Treasure Bastion is captured inside the Nether window.
  - **Nether Fortress Core:** **+10 pts** if a Fortress is within $\le 256\text{m}$ of the scaled Nether portal $(C_X/8, C_Z/8)$.
  - **Bastion Remnant Core:** **+10 pts** if a Bastion is within $\le 256\text{m}$ of the scaled Nether portal $(C_X/8, C_Z/8)$.
- 🏞️ **Scenic River Pairing Bonus (+25 pts max):**
  - **+25 pts** if a surface scenic biome at $Y=63$ (Plains, Sunflower Plains, Meadow, Cherry Grove) within 192m of dynamic center $(C_X, C_Z)$ is paired with a River within 128m.
- 🏘️ **Village Quadrant Spread Bonus (+25 pts max):**
  - **+25 pts** if $\ge 3$ distinct captured Villages occupy $\ge 3$ separate quadrants of the window and are spaced $\ge 256\text{m}$ apart pairwise.

*(Sum of spatial and layout bonuses: $45 + 40 + 25 + 25 = \mathbf{135\text{ pts}}$).*

#### E. Centroid Magnet ($\omega_i$) Weights
To prevent flat plains villages from monopolizing the sliding window center $(C_X, C_Z)$, rare temple structures exert strong centroid pull:
- Stronghold: $\omega = 3$
- Ancient City, Woodland Mansion, Desert Pyramid, Jungle Temple, Village: $\omega = 2$
- Trial Chamber, Pillager Outpost, Ocean Monument: $\omega = 1$
- Ruined Portal, Shipwreck, Mineshaft: $\omega = 0$

#### F. In-Memory Top-50 Tracker & Persistence
- **Zero Disk Overhead:** An in-memory min-heap (`Top50Tracker`) tracks the top 50 candidates in RAM, completely eliminating per-seed database write locks during high-throughput search.
- **Dynamic Cutoff:** When 50 qualified candidates exist, incoming candidates with scores below the 50th-best are instantly discarded with $O(1)$ complexity.
- **Atomic Persistence:** Periodic checkpointing flushes the current Top 50 to JSON or SQLite transactionally without interrupting search workers.

---

### 5.2 Historical `dynamic-envelope-1664-v1` Scoring Reference

*(Retained for backward compatibility and legacy database validation)*:
- Mansion jackpot (+50), Stronghold jackpot (+50), Monument (+30).
- Mangrove (+25) and legacy luxury palette.
- 512m Starter Hub (+40 max): Village (+6), Pyramid (+6), Temple (+6), Outpost (+6), Portal (+4), Mega-Cave (+4).
- Two-group tolerance matrix ($B \le 2$).

---

## 6. Leaderboard Sort Order

### 6.1 Active v3 Sort Order (Score-First Ranking)
Under `dynamic-envelope-2048-v3`, leaderboard sorting prioritizes overall feature wealth:
$$\text{Rank Order}_{\text{v2}} = \Big( \text{smart\_score DESC},\; \text{deficit\_count ASC},\; \text{radial\_key ASC},\; \text{origin\_distance\_squared ASC},\; C_X\text{ ASC},\; C_Z\text{ ASC},\; \text{candidate ID ASC} \Big)$$

The ID tie-breaker uses binary lexical order. `radial_key` is weighted radial distance multiplied by 1,000,000, rounded to nearest with exact halves away from zero. The squared origin distance and center coordinates are exact integers. Only eligible results participate in this score comparison; inspection status does not promote an eligible result ahead of a better score.

Supported by the optimized SQLite index `candidate_leaderboard_v2` with zero temporary B-trees.

### 6.2 Historical v1 Sort Order (Deficit-First Ranking)
$$\text{Rank Order}_{\text{v1}} = \Big( \text{Deficit Tier ASC},\; \text{smart\_score DESC},\; \text{weighted\_radial\_dist ASC},\; \text{Origin Dist ASC} \Big)$$
Supported by the SQLite index `candidate_leaderboard`.

```
                                  LEADERBOARD SORT FLOW
                                            │
                                            ▼
                  ┌──────────────────────────────────────────────────┐
                  │ LEVEL 1: Deficit Tier ASC (Integrity Guarantee)   │
                  │ • Tier 0: 0 deficits (Perfect Target Seed)        │
                  │ • Tier 1: 1 deficit  (e.g., 8 Villages)          │
                  │ • Tier 2: 2 deficits (e.g., 8 Vill + 7 Chambers) │
                  └──────────────────────────────────────────────────┘
                                            │ (If Deficit Tiers match)
                                            ▼
                  ┌──────────────────────────────────────────────────┐
                  │ LEVEL 2: smart_score DESC (Feature Wealth)        │
                  │ • Sum of base structure points, surplus points,  │
                  │   luxury biomes, and 512m Starter Hub bonus      │
                  └──────────────────────────────────────────────────┘
                                            │ (If smart_scores match)
                                            ▼
                  ┌──────────────────────────────────────────────────┐
                  │ LEVEL 3: weighted_radial_dist ASC (Walkability)  │
                  │ • Average commute distance from center to        │
                  │   captured settlement structures                 │
                  │ • Tighter, more compact realms win tie-breaks    │
                  └──────────────────────────────────────────────────┘
                                            │ (If walkability matches)
                                            ▼
                  ┌──────────────────────────────────────────────────┐
                  │ LEVEL 4: Origin Distance ASC (Spawn Proximity)   │
                  │ • Euclidean distance from (C_X, C_Z) to (0, 0)   │
                  └──────────────────────────────────────────────────┘
```

---

## 7. Execution Pipeline & Performance Engineering

> **Implementation evidence:** This is the approved search design. The measured implementation and its limits are recorded in `LATEST_PUSH_REVIEW.md`. Section 7's performance percentages, climate-noise shortcut and automatic biome credits are proposals or projections, not proofs. The current engine keeps exact biome lookup and explicit four-Y witnesses, and does not enable those unproven shortcuts. Native center selection ranks the defined constrained-centroid representatives. The independent finalist command `scripts/refine_candidate_centers.py` additionally searches every valid 16-block center (or, explicitly, every 8-block center), using the same predictor score. Neither path certifies actual generation or player preferences. See `reviews/framework-fixes-2026-10-16/IMPLEMENTATION.md` for current deployment and validation status.

### 7.1 Top 5 Zero-Loss Pipeline Optimizations

| Optimization | What Changes in the Pipeline | Why It's Safe (Zero False Rejects) | Throughput & Speedup Impact |
| :--- | :--- | :--- | :--- |
| **1. Enforce $1024 \times 1024$ Nether Co-Window Compatibility in Step 1** | Stage 1A Step 1 checks if $\ge 1$ Fortress and $\ge 2$ Bastions exist in $[-634, 634]$. Add a `50 ns` bounding-box check requiring that at least 2 Fortresses and 2 Bastions fit inside a single $1024 \times 1024$ sub-window ($\Delta X_N \le 1024, \Delta Z_N \le 1024$) and calculate the valid Overworld center interval $[C_{X,\min}^{\text{Nether}}, C_{X,\max}^{\text{Nether}}]$. | If two Fortresses are $>1024\text{m}$ apart in $[-634, 634]$, they can never be co-captured in an $1024 \times 1024$ Nether box in Stage 1B. | **Cuts seeds entering Mansion biome checks by ~45–55%** (`~1.8×` speedup). |
| **2. Clamp Overworld Preflight Bounds to the Nether Safe Interval** | Instead of scanning the full $[-2000, 2000]$ box for Mansions, Monuments, and Outposts, only test regions within $[C_{X,\min}^{\text{Nether}} - 1024,\; C_{X,\max}^{\text{Nether}} + 1024]$. | Any Overworld structure outside $[C_{\min}^{\text{Nether}} - 1024,\; C_{\max}^{\text{Nether}} + 1024]$ cannot be captured without losing a mandatory Nether structure. | **Skips ~40% of Mansion & Monument noise lookups** (`~1.3×` speedup). |
| **3. Move Pure-PRNG Outpost & Trial Chamber Grid Counts *Before* Mansion Biome Noise** | Pillager Outposts roll a pure-PRNG region spawn check *before* biome viability, and Trial Chambers ($\ge 8$ required) use pure chunk-grid PRNG. Verify that $\ge 1$ Outpost PRNG roll and $\ge 8$ Trial Chamber PRNG slots fall inside the feasible box **before** initializing Overworld climate noise for the Mansion. | Pure PRNG coordinate generation takes $<0.5\,\mu\text{s}$ in C; seeds lacking enough raw PRNG slots can never satisfy floors regardless of biomes. | **Rejects ~70% of remaining seeds before any biome noise runs** (`~1.5×` speedup). |
| **4. Short-Circuit 6D Climate Noise on Mansion Checks** | A Dark Forest requires specific Continentalness ($C > -0.11$, inland), Temperature (temperate), and Humidity ($H > 0.1$). Evaluate noise parameters one octave at a time (`Humidity` $\to$ `Continentalness` $\to$ `Temperature`) and abort immediately on the first miss. | Evaluating 1 Perlin octave tree instead of all 6 on non-matching points is mathematically identical to a full biome lookup. | **Cuts Mansion & Bastion biome check CPU time by ~65–75%**. |
| **5. Skip Redundant Biomes, Multi-Plane Short-Circuit & 5-Biome Nether** | Seeds reaching Stage 2 already certified Dark Forest, Desert, Jungle, and Deep Dark via Stage 1B structures. Short-circuit $Y = 160$ on first `*_peaks` cell (`jagged_peaks | frozen_peaks | stony_peaks`), short-circuit $Y = 0, -48$ on first `lush_caves` & `dripstone_caves`, and verify all 5 Nether biomes exist in $[C_X/8 \pm 512, C_Z/8 \pm 512)$. | Structure placement in Stage 1B certifies those 4 Overworld biomes; early-exit on boolean witnesses avoids full rasterization; Nether check takes $<0.3\text{ ms}$. | **Cuts Stage 2 sampling time by ~60%** while guaranteeing zero Nether resource lock-outs. |

---

### 7.2 Revised Stage 1A Execution Order & Fast-Reject Cascade

```
                          [ Bounded 36-Billion Seed Stream ]
                                          │
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1A, STEP 1: Nether PRNG + Co-Window Check (~1.6 µs, Pure PRNG)   │
      │ • Find Fortresses & Bastions in [-634, 634].                           │
      │ • Verify ≥ 2 of each fit inside a single 1024 × 1024 co-window.        │
      │ • Output exact Overworld feasible center range [C_min^N, C_max^N].     │
      │ • Rejects ~91% of all seeds with zero climate noise.                   │
      └────────────────────────────────────────────────────────────────────────┘
                                          │ (9% of seeds survive)
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1A, STEP 2: Outpost & Trial Chamber PRNG Slots (~0.6 µs, PRNG)   │
      │ • Verify ≥ 1 Outpost roll & ≥ 8 Trial Chamber PRNG chunk slots fall   │
      │   inside [C_min^N - 1024, C_max^N + 1024].                             │
      │ • Rejects ~70% of survivors. Only ~2.7% of raw seeds reach Step 3.     │
      └────────────────────────────────────────────────────────────────────────┘
                                          │ (2.7% of seeds survive)
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1A, STEP 3: Woodland Mansion Check (~0.8 ms, Short-Circuited)    │
      │ • Test candidate Mansion chunks within Nether-clamped bounding box.    │
      │ • Short-circuit noise: evaluate Humidity & Continentalness first.      │
      │ • Rejects ~99% of remaining candidates.                                │
      └────────────────────────────────────────────────────────────────────────┘
                                          │ (< 0.02% of seeds survive)
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1A, STEP 4: Secondary Biome Checks (Bastion, Monument, Outpost)  │
      │ • Confirm Bastion biome != basalt_deltas, Ocean Monument deep ocean,   │
      │   and Outpost surface biome eligibility on surviving < 0.02% of seeds. │
      └────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1B: Exact 2D Event-Slab Solver & Centroid Magnet ($2048 \times 2048$)│
      │ • Half-open Overworld safe interval [X_i - 1023, X_i + 1024] (width 2048).│
      │ • Nether safe interval [8X_N,j - 4095, 8X_N,j + 4096] (width 8192).    │
      │ • Enforce Guaranteed Hard Floors and Zero Miss Budget ($B = 0$).       │
      │ • Pull $(C_X, C_Z)$ toward centroid; clamp to Safe Zone S_safe.        │
      │ • Snap to nearest 16 per axis, fallback to 8 without leaving S_safe.   │
      └────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 2: 13-Biome Diversity & 5-Biome Nether Palette Check             │
      │ • Overworld: Short-circuit Y = 160 on first peak (*_peaks), short-     │
      │   circuit Y = 0, -48 on Lush/Dripstone witnesses. Skip 4 certified     │
      │   families (Dark Forest, Desert, Jungle, Deep Dark).                   │
      │ • Nether: Verify all 5 Nether biomes exist inside 1024 × 1024 box.     │
      │ • Seeds passing Stages 1 & 2 are saved as BASELINE SURVIVORS.          │
      └────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 3/4: Hub Scoring, Luxury Biomes & SQLite WAL Batch Persistence   │
      │ • Compute Dynamic 512m Starter Hub Bonus (capped at +40 pts).          │
      │ • Tally luxury biome bonuses and structure surplus scores.             │
      │ • Batch commit to SQLite WAL database every 4,096 evaluated seeds.     │
      └────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 5: Headless BDS Docker Verification (Top 50 / All Survivors)     │
      │ • Run automated verification on bedrock-verification-poc:1.26.52.3     │
      │ • Confirm live structure generation, foundation heights, and loot.     │
      │ • Explicitly verify End Portal Room presence (portal_room_present=true)│
      │   and first-player spawn, which remain unverified by predictor stages. │
      └────────────────────────────────────────────────────────────────────────┘
```

---

### 7.3 Throughput & Execution Economics (Analytical Projections & Theoretical Models)

> [!NOTE]
> **Analytical Projection Notice:** The throughput figures, amortized latencies, and cluster scaling estimates below are theoretical performance models and analytical projections based on algorithmic short-circuit mathematics, NOT empirically measured benchmarks from live production runs. Actual hardware performance varies with CPU microarchitecture, memory bus contention, native OpenMP scheduling, and OS cache dynamics. Crucially, unmeasured figures must remain labeled as projections, and must not be conflated with verified empirical benchmarks (nor replaced by arbitrary unverified claims such as the audit report's '87k/sec').

- **Pure-PRNG Culling Barrier (Theoretical Model):** $\approx 97.3\%$ of all input seeds are eliminated in $\le 2.2\,\mu\text{s}$ before initializing Overworld climate noise.
- **Short-Circuited Biome Noise (Theoretical Model):** Only $\approx 2.7\%$ of seeds ever reach Woodland Mansion 6D noise sampling, where 1D short-circuiting cuts per-seed evaluation time from $\sim 2.5\text{ ms}$ down to $\sim 0.8\text{ ms}$.
- **Amortized Single-Core Throughput (Analytical Projection):**
  $$\text{Amortized Latency} \approx 0.75\text{–}0.95\text{ ms per input seed per core} \implies \mathbf{1,100\text{–}1,350\text{ seeds/sec/core}}$$
  *(Theoretical model based on short-circuit cascade).*
- **Distributed Cluster Performance Model (Theoretical 210 Dedicated CPU Cores Model):**
  $$\text{Cluster Throughput} = 210 \text{ cores} \times (1,100\text{–}1,350 \text{ seeds/sec/core}) \approx \mathbf{230,000\text{–}280,000\text{ seeds/sec}}$$
  $$\text{Daily Volume} = 250,000 \times 86,400 \approx \mathbf{21.6\text{ Billion seeds/day}}$$
  $$\mathbf{36\text{ Billion Seed Campaign Duration} = \frac{36 \times 10^9}{21.6 \times 10^9} \approx 1.67\text{ Days}} \quad (\sim 40\text{ Hours})$$
- **SQLite WAL Write Overhead (Analytical Model):** Retained at $<0.01\%$ total CPU time via 4,096-seed batch transactions.

---

### 7.4 Empirical Host Benchmarks & Production Validation (October 2026)

#### Active Revision 6.0 (`dynamic-envelope-2048-v3`) Host Throughput
Under the expanded active $2048 \times 2048$ Overworld envelope and $1024 \times 1024$ Nether window with all 14 hard floors, 4-plane Overworld biome validation, 5-biome Nether lattice check, and pure additive 1,250-point scoring:
- **Active v3 Native Pipeline Throughput (34 OpenMP Threads):** **~55,000–58,000 seeds/sec** ($\sim 1.75\text{s}$ per 100K seeds, $\sim 17.5\text{s}$ per 1M seeds, $\sim 29.5\text{ mins}$ per 100M-seed shard). The throughput shift from historical ~215k seeds/sec (v2 1664×1664) to ~55k–58k seeds/sec in v3 reflects the substantially expanded $2048 \times 2048$ window area ($1.51\times$ larger block footprint), full 14-category hard floor preflight, 4-plane vertical biome sampling, and full $1024 \times 1024$ 5-biome Nether evaluation.
- **Analytical Projections vs. Empirical Host Benchmarks:** The theoretical cluster scaling figures in Section 7.3 (e.g. 230k–280k seeds/sec across hypothetical 210-core clusters) are analytical projections; the **~55k–58k seeds/sec** figure represents the verified empirical single-host throughput measured on the 34 OpenMP worker thread hardware configuration.

#### Historical Revision 5.0 (`dynamic-envelope-1664-v2`) Benchmark Archive
For historical reference, benchmarks executed on the $1664 \times 1664$ configuration directly on an **Intel Xeon W-2191B (18 physical cores / 36 threads @ 2.30 GHz)** with 30–34 OpenMP worker threads yielded:

| Execution Arm | Measured Speed | Time per 100K Seeds | Time per 1M Seeds | Time per 100M Seeds (Shard) |
| :--- | :---: | :---: | :---: | :---: |
| **Pure Native OpenMP Kernel (PGO+LTO)** | **~215,000 seeds/sec** | $\sim 0.46\text{s}$ | $\sim 4.6\text{s}$ | $\sim 7.7\text{ mins}$ |
| **Durable Compact Pipeline (`retention='survivors'`)**<br>*(Native + Python + SQLite WAL + Disk Monitor)* | **220,000 – 229,000 seeds/sec** | $\sim 0.44\text{s}$ | $\sim 4.4\text{s}$ | $\sim 7.4\text{ mins}$ |
| **Durable Full Pipeline (`retention='full'`)**<br>*(All seeds recorded to SQLite WAL)* | **32,500 – 38,000 seeds/sec** | $\sim 2.6\text{s}$ | $\sim 26\text{s}$ | $\sim 44\text{ mins}$ |
| *Previous Control Baseline (Pre-Audit)* | *$\sim 5,400 - 5,700$ seeds/sec* | *$\sim 18.0\text{s}$* | *$\sim 180\text{s}$* | *$\sim 5.1\text{ hours}$* |

#### Implemented Performance Architectures
1. **Low-32 PRNG Structure Preflight:** Evaluates pure PRNG positions for Woodland Mansion, Ancient City, Outpost, Trial Chamber, and Village against universal fatal floors. Rejects $\approx 70\%$ of candidate seeds in $\sim 50\text{ns}$ before climate noise generation.
2. **Lazy Deferred 2D Prefix Sums:** Skips 15,876 Overworld 3D noise evaluations and 256 Nether queries (half-open $16 \times 16$ lattice) per rejected seed by calculating prefix sums only when candidate sliding-window cells pass structure floors.
3. **Overlapping Pipeline Dispatch:** Queue depth raised to 4 with immediate background dispatch upon `pending.popleft()`, keeping OpenMP compute 100% saturated during SQLite range writes.
4. **Iterative `os.scandir` Accounting:** Replaced recursive `os.walk` to eliminate $>40\text{s}$ of redundant `stat()` syscalls per 100k seeds during continuous workspace capacity monitoring.
5. **Clang PGO + LTO Native Compilation:** Profile-Guided Optimization training on representative seed batches merged with Link-Time Optimization (`-fprofile-instr-use`, `-flto=thin`) unlocks high-throughput native kernel execution.
6. **Zero-Copy Vectorized Batching & Pruned Kernel Teardown:** Vectorized SplitMix64 batch generation (`seeds_np`) directly into contiguous uint64 CFFI buffers completely eliminates serial Python loops between C calls, while pruned `nb_free` skips 16,384 cleared `NBResult` struct traversals. This closes the gap between native compute and pipeline persistence with full crash-safe SQLite WAL durability.

---

## 8. Expected Yield & Campaign Economics (Theoretical Models & Projections)

> [!NOTE]
> **Theoretical Models & Ground-Truth Verification Notice:** Expected survivor yields and joint target probabilities are statistical combinatorial projections, not empirically measured counts. Candidate prediction does not establish actual in-engine world generation; approved blueprint design targets must be kept strictly distinct from runtime implementation certification.

- **Joint Target Probability (Analytical Projection):** $\approx 1 \text{ in } 2.5\text{–}3.5\text{ Billion seeds}$.
- **Projected Total Predictor Survivors (Theoretical Model):** $\approx \mathbf{10\text{–}15\text{ High-Tier Seeds}}$ (up to $\sim 30\text{–}50$ across all deficit tiers) across a 36-Billion seed campaign.
- **Stage 5 Verification Objectives:** Top **50 finalists (or 100% of all survivors)** are intended for follow-up verification against the pinned Bedrock server.
  - **Currently implemented:** bounded surface point/block observations, with partial evidence and provider identity recorded.
  - **Not established by the current automated provider:** complete generated structure inventories, intact End Portal rooms, loot, mega-cave entrances or initial-player spawn. Those objectives require additional tooling or appropriately scoped observations; a headless surface job does not certify them.
