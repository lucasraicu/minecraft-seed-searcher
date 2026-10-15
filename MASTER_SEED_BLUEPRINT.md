# Master Seed Blueprint: Bedrock 15–20 Player Server (1664 × 1664)

> **Specification Status:** Approved Engineering Blueprint Specification (Revision 4.2 - Geometric Asymmetry, Snapping & Evidence Scope - October 2026).
> **Pipeline Policy:** `dynamic-envelope-1664-v1` with sliding optimal cluster center $(C_X, C_Z)$ within a $4000 \times 4000$ Overworld macro-envelope ($[-2000, 2000)$) and $1124 \times 1124$ Nether preflight envelope ($[-562, 562)$).
> **Target Game Version:** Minecraft Bedrock Edition 1.21+ (pinned `MC_26_50`; live BDS target 1.26.52.3).
> **Target Community:** 15–20 Players (High-density active server; shared central starter hub; distributed homestead districts; zero resource depletion).
> **Certification Decoupling:** Defines approved architectural targets, hard floors, and scoring models. In-engine verification (End Portal rooms, loot, cave carver entrances, initial player spawn) requires additional evidence. The current headless provider establishes bounded surface observations; it does not establish those other features.

---

## 1. World Boundaries & Exact Geometric Coordinates

The realm operates on a sliding-window coordinate system that decouples world spawn from the playable center while preserving strict integer coordinate validity, 8:1 dimensional scaling, and chunk-grid alignment where achievable.

| Dimension / Region | Exact Dimensions | Center Coordinate | Chunk Extent | Distance to Edge | Mathematical Definition & Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Overworld Macro Envelope** | **4000 × 4000** | Origin `(0, 0)` | $250 \times 250$ chunks | Radius 2,000m | Search bounds for Stage 1A preflight ($X, Z \in [-2000, 2000)$). |
| **Nether Preflight Envelope** | **1124 × 1124** | Origin `(0, 0)` | $70.25 \times 70.25$ chunks | Radius 562m | Fast chunk-grid PRNG search bounds for Stage 1A Nether checks ($X_N, Z_N \in [-562, 562)$). Exactly covers all possible Nether centers ($\pm 146\text{m}$) plus 416m half-width. |
| **Playable Overworld** | **1664 × 1664** | **Dynamic Center $(C_X, C_Z)$** | $104 \times 104$ chunks | Radius 832m | Bounded within the half-open window $[C_X - 832, C_X + 832) \times [C_Z - 832, C_Z + 832)$, where $(C_X, C_Z) \in [-1168, 1168]^2$. Exactly 1664 blocks = 104 chunks. Border inclusions: West ($X = C_X - 832$) and North ($Z = C_Z - 832$) included; East ($X = C_X + 832$) and South ($Z = C_Z + 832$) excluded. Snapped to the nearest valid multiple of 16 per axis, falling back to 8 without leaving the safe cell $\mathcal{S}_{\text{safe}}$. |
| **Playable Nether** | **832 × 832** | **Scaled Center $(C_X/8, C_Z/8)$** | $52 \times 52$ chunks | Radius 416m | Bounded within the half-open window $[C_X/8 - 416, C_X/8 + 416) \times [C_Z/8 - 416, C_Z/8 + 416)$, where $(C_X/8, C_Z/8) \in [-146, 146]^2$. West and North included; East and South excluded. Guaranteed exact integer block coordinate for `/scriptevent worldborder:center nether <X> <Z>`. Radius 416m provides a $4\times$ area buffer relative to the 208-block portal-scaled Overworld footprint; geometry alone does not certify portal behavior. |

---

## 2. Dynamic Sliding Window: Three-Defense Geometric & Alignment Architecture

In a $1664 \times 1664$ bounding box, the outer boundary shell accounts for **75% of the total surface area**. Without spatial safeguards, unconstrained sliding windows place key structures at the border perimeter. The blueprint guarantees dense interior clustering and flawless world border alignment via a three-defense geometric architecture:

### Defense 1: 2D Event-Slab Interior Solver
- Projects every discovered structure coordinate into entry/exit slab events on half-open intervals:
  - Overworld structures at $(X_i, Z_i)$ are captured when $C_X - 832 \le X_i < C_X + 832$. For integer centers $C_X$, this yields entry at $X_i - 831$ and exit past $X_i + 832$ (candidate safe interval $[X_i - 831, X_i + 832]$ of width 1664). This produces an exact $+1$ entry-event asymmetry relative to continuous-space models ($[X_i - 832, X_i + 832]$).
  - Nether structures at $(X_{N,j}, Z_{N,j})$ are projected into Overworld center space via the 8:1 dimensional scale ($C_X/8 - 416 \le X_{N,j} < C_X/8 + 416 \iff C_X - 3328 \le 8X_{N,j} < C_X + 3328$). For integer centers $C_X$, this yields entry at $8X_{N,j} - 3327$ and exit past $8X_{N,j} + 3328$ (candidate safe interval $[8X_{N,j} - 3327, 8X_{N,j} + 3328]$ of width 6656).
- Solves 2D equivalence cells formed by the Cartesian product of event intervals where structure counts and lattice samples are strictly invariant, selecting the cell representative that minimizes distance to the coordinate midpoint.

### Defense 2: Centroid Magnet Pull with Feasible Safe-Zone Clamping
Once a valid equivalence cell is established, the exact center $(C_X, C_Z)$ is pulled toward the weighted center-of-mass (centroid) of the captured settlement structures, heavily concentrating villages and dungeons toward the center of the world:

$$C_X^* = \frac{\sum_{i=1}^N \omega_i X_i}{\sum_{i=1}^N \omega_i}, \qquad C_Z^* = \frac{\sum_{i=1}^N \omega_i Z_i}{\sum_{i=1}^N \omega_i}$$

#### Centroid Weight Distribution ($\omega_i$, Capped at 3)
To prevent massive structures from disproportionately dragging the center away from human settlements, pull weights are strictly capped at 3:
- 🏘️ **All Villages:** $\omega = 3$ each (Primary settlement anchor)
- ⚔️ **All Trial Chambers:** $\omega = 2$ each (Primary midgame dungeon anchor)
- 🌀 **All Ruined Portals:** $\omega = 2$ each (Fast transit hub anchor)
- 🌌 **All Ancient Cities:** $\omega = 2$ each (Deep exploration anchor)
- 🏴‍☠️ **All Pillager Outposts:** $\omega = 1$ each
- 🏺 **All Desert Pyramids & Jungle Temples:** $\omega = 1$ each
- 🏛️ **Woodland Mansion:** $\omega = 1$
- 🗿 **Ocean Monument:** $\omega = 1$
- 🏰 **Stronghold:** $\omega = 1$
- ⛵ **All Shipwrecks:** $\omega = 1$ each

#### Feasible Safe-Zone Clamping ($\mathcal{S}_{\text{safe}} = \mathcal{S}_{\text{OW}} \cap \mathcal{S}_{\text{Nether}}$)
The centroid pull is strictly constrained to the Feasible Safe Zone to guarantee that no floor-qualifying structure is ever displaced across the border. Incorporating the half-open window boundary logic:
- **Overworld Safe Interval:** For every required Overworld structure $i$, $C_X \in [X_i - 831, X_i + 832]$ and $C_Z \in [Z_i - 831, Z_i + 832]$ (exact width 1664 integer coordinates per axis).
- **Nether Safe Interval:** For every required Nether Fortress and Bastion $j$, projected as $C_X \in [8X_{N,j} - 3327, 8X_{N,j} + 3328]$ and $C_Z \in [8Z_{N,j} - 3327, 8Z_{N,j} + 3328]$ (exact width 6656 integer coordinates per axis in Overworld scale).
- Clamping: $(C_X^*, C_Z^*) = \text{clamp}\big((C_X^*, C_Z^*),\; \mathcal{S}_{\text{safe}}\big)$, where $\mathcal{S}_{\text{safe}} = \mathcal{S}_{\text{OW}} \cap \mathcal{S}_{\text{Nether}} \cap [-1168, 1168]^2$. This projection guarantees that required Overworld and Nether structures can never be lost.

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
   - **Block Dimensions vs. Chunk Borders:** The Overworld window is fixed at exactly $1664 \times 1664$ blocks ($104 \times 104$ chunks, radius 832m), and the Nether window is fixed at $832 \times 832$ blocks ($52 \times 52$ chunks, radius 416m).
   - **When Snapping to 16:** Because the Overworld half-width is $832 = 52 \times 16$, snapping $C_X, C_Z$ to a multiple of 16 guarantees that both borders $[C \pm 832]$ land exactly on chunk boundaries ($16k \pm 52 \times 16 = 16(k \pm 52) \equiv 0 \pmod{16}$). No chunk is split in half by the world border particle wall, and the scaled Nether center $(C_X/8, C_Z/8)$ is an even integer ($2k$).
   - **When Snapping to Fallback-8 (Odd Multiples of 8):** If $C$ is an odd multiple of 8 ($C = 16k + 8$), the outer boundary lands at $16k + 8 \pm 52 \times 16 \equiv 8 \pmod{16}$. **A fallback-8 border will cut a chunk in half** at block offset 8. Fallback-8 Overworld centers and integer Nether centers do *not* guarantee chunk-aligned borders.
   - **Addon Integer Command Requirement:** What fallback-8 *does* strictly guarantee is that $(C_X/8, C_Z/8)$ is an exact integer block coordinate ($(16k + 8)/8 = 2k + 1 \in \mathbb{Z}$). The deployment command target `/scriptevent worldborder:center nether <X> <Z>` is expressed using integer coordinates; addon behavior and portal safety still require runtime verification. Snapping to 8 prevents fractional Nether centers (which would occur if centers were not snapped) and preserves the selected starts within $\mathcal{S}_{\text{safe}}$.

---

## 3. Structure Inventory, Tolerance Matrix & Miss Budget ($B \le 2$)

Every qualifying candidate **must strictly satisfy the Guaranteed Hard Floors under a total Miss Budget $B \le 2$**.

### The Miss Budget Rule ($B \le 2$)
1. **Instant Rejection (Hard Floors):** Any seed that drops below the **Hard Floor** for *any* structure category is instantly disqualified in Stage 1 C screening.
2. **Deficit Consumption:** If a structure meets its Hard Floor but falls below its **Ideal Target**, it consumes **1 Miss** from the seed's budget.
3. **Budget Limit:** A seed may possess at most **2 categories in deficit** across the entire realm ($\text{Total Misses} \le 2$). Any seed with $\ge 3$ deficits is disqualified.

### Structure Tolerance Matrix ($1664 \times 1664$ Overworld / $832 \times 832$ Nether)

| Structure Category | Dimension | Ideal Target | Tolerance | Guaranteed Hard Floor | Stage Evaluated | Scoring & Realm Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| 🏰 **Stronghold** | Overworld | **1** | **0** | **$\ge 1$** | Stage 1A | **Non-negotiable.** End portal access. **+50 pts** for 2nd Stronghold. |
| 🏛️ **Woodland Mansion** | Overworld | **1** | **0** | **$\ge 1$** | Stage 1A | **Mandatory $\ge 1$.** Guaranteed Dark Forest start at Y=63. **+50 pts** for 2nd Mansion. |
| 🗿 **Ocean Monument** | Overworld | **1** | **0** | **$\ge 1$** | Stage 1A | **Mandatory $\ge 1$.** Prismarine, sponges, conduit core. **+35 pts** for 2nd Monument. |
| 🏴‍☠️ **Pillager Outpost** | Overworld | **2** | **0** | **$\ge 2$** | Stage 1A | **Mandatory $\ge 2$.** Infinite Bad Omen & raid farming. **+20 pts** one-time milestone for 3rd (not linear). |
| 🔥 **Nether Fortress** | Nether | **2** | **0** | **$\ge 2$** | Stage 1A (1st) | **Mandatory $\ge 2$** inside $832 \times 832$ Nether. Blaze rods & skulls. **+20 pts** one-time milestone for 3rd (not linear). |
| 🐷 **Bastion Remnant** | Nether | **2** | **0** | **$\ge 2$** | Stage 1A (1st) | **Mandatory $\ge 2$** inside $832 \times 832$ Nether. Piglin bartering & upgrade trims. **+20 pts** one-time milestone for 3rd (not linear). |
| 🏘️ **Villages** | Overworld | **9** | **$-1$** | **$\ge 8$** | Stage 1B | Guaranteed $\ge 8$. 8 villages = 1 deficit. **+25 pts** each for 9th+ (linear surplus). |
| ⚔️ **Trial Chambers** | Overworld | **8** | **$-1$** | **$\ge 7$** | Stage 1B | Guaranteed $\ge 7$. 7 chambers = 1 deficit. **+10 pts** each for 8th+ (linear surplus). |
| 🌌 **Ancient City** | Overworld | **4** | **$-1$** | **$\ge 3$** | Stage 1B | Guaranteed $\ge 3$. 3 cities = 1 deficit. **+25 pts** one-time milestone for 4th (not linear). |
| 🏺 **Desert Pyramid** | Overworld | **3** | **$-1$** | **$\ge 2$** | Stage 1B | Guaranteed $\ge 2$. 2 pyramids = 1 deficit. **+20 pts** one-time milestone for 3rd (not linear). |
| 🌿 **Jungle Temple** | Overworld | **3** | **$-1$** | **$\ge 2$** | Stage 1B | Guaranteed $\ge 2$. 2 temples = 1 deficit. **+20 pts** one-time milestone for 3rd (not linear). |
| ⛵ **Shipwrecks** | Overworld | **6** | **$-2$** | **$\ge 4$** | Stage 1B | Guaranteed $\ge 4$. 4–5 wrecks = 1 deficit. **+5 pts** each above 6 (linear surplus). |
| 🌀 **Ruined Portals** | Overworld | **7** | **$-2$** | **$\ge 5$** | Stage 1B | Guaranteed $\ge 5$. 5–6 portals = 1 deficit. **+5 pts** each above 7 (linear surplus). |
| ⛏️ **Mineshafts** | Overworld | **15** | **$-3$** | **$\ge 12$** | Stage 1B | Guaranteed $\ge 12$. 12–14 shafts = 1 deficit. **+1 pt** each above 15 (linear surplus). |
| 🧙 **Swamp Hut (Witch Hut)** | Overworld | 1 | — | $\ge 0$ | Stage 4 Bonus | Automated witch/redstone farm; **+20 pts** (predicted placement). |
| 🛖 **Igloo (with Basement)**| Overworld | 1 | — | $\ge 0$ | Stage 4 Bonus | Starter brewing stand, golden apple & zombie curing; **+15 pts** (predicted via PRNG). |
| 🏺 **Trail Ruins** | Overworld | 1 | — | $\ge 0$ | Stage 4 Bonus | Archaeology trims & relic discs; **+15 pts** (predicted placement). |

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

### Complete 5-Biome Nether Palette (Inside 832 × 832 Playable Nether)
Because players cannot travel or mine outside the $832 \times 832$ Nether border, Stage 2 enforces that all **5 Nether biomes** exist within $[C_X/8 \pm 416, C_Z/8 \pm 416]$ via a fast $13 \times 13$ lattice check ($169$ sample points at $Y = 64$, taking $<0.2\text{ ms}$):
1. 🔥 **Nether Wastes:** Quartz, glowstone, zombie piglins.
2. 🌲 **Crimson Forest:** Crimson wood/fungus, shroomlights, weeping vines, hoglins (essential renewable food/leather).
3. 🍄 **Warped Forest:** Warped wood/fungus, twisting vines, safe haven from piglins/hoglins, enderman pearl farming.
4. 💀 **Soul Sand Valley:** Soul sand, soul soil (soul speed highways), ghasts, bone blocks.
5. 🌋 **Basalt Deltas:** Basalt, blackstone, magma cubes.

### Stage 2 Multi-Plane Short-Circuiting Protocol
To minimize sampling overhead, Stage 2 evaluates vertical planes with aggressive early exits:
- **Plane $Y = 160$ (High Peaks):** Breaks immediately upon detecting the first cell of `jagged_peaks`, `frozen_peaks`, or `stony_peaks`.
- **Planes $Y = 0$ & $Y = -48$ (Underground Caverns):** Deep Dark is already certified by $\ge 3$ Ancient Cities. The underground scan breaks immediately once at least 1 cell of `lush_caves` and 1 cell of `dripstone_caves` (plus the 512m hub mega-cave witness) are confirmed. *(Note: Cave witnesses verify underground biome cell occupancy; physical cavern entrances, opening geometry, and navigability remain unverified by predictor models.)*
- **Plane $Y = 63$ (Surface):** Dark Forest, Desert, and Jungle are already certified by Stage 1B structures. Only remaining surface families are evaluated.

---

## 5. Stage 3/4: Dynamic Starter Hub & Comprehensive Scoring

### Dynamic 512m Starter Hub Bonus (Capped at +40 pts)
To ensure immediate player engagement without requiring 15-minute treks on day one, structures located within visual render distance ($d \le 512\text{m}$, 32 chunks) of the dynamic center $(C_X, C_Z)$ receive dynamic hub bonuses:
- 🏘️ **Village within 512m:** **+6 pts** each (Starter trading post & bed respawn)
- 🏺 **Desert Pyramid within 512m:** **+6 pts** each (Early diamonds & golden apples)
- 🌿 **Jungle Temple within 512m:** **+6 pts** each (Early redstone & exploration trim)
- 🏴‍☠️ **Pillager Outpost within 512m:** **+6 pts** each (Proximity Bad Omen / raid farm)
- 🌀 **Ruined Portal within 512m:** **+4 pts** each (Immediate Nether access)
- 💎 **Mega-Cave Witness within 512m:** **+4 pts** (requires an actual cavern-entry witness; deferred without that evidence, never credited from a cave biome ID alone)
- **Maximum Dynamic Hub Bonus:** Strictly capped at **+40 pts**.

### Luxury Biomes & Surplus Leaderboard Matrix

| Tier | Category / Feature | Points Awarded |
| :---: | :--- | :---: |
| **Tier 1 (Jackpot)** | 2nd Woodland Mansion within $1664 \times 1664$ (one-time jackpot) | **+50 pts** |
| **Tier 1 (Jackpot)** | 2nd Stronghold within $1664 \times 1664$ (one-time jackpot) | **+50 pts** |
| **Tier 1 (Jackpot)** | 2nd Ocean Monument within coastal ocean (one-time jackpot) | **+35 pts** |
| **Tier 2 (Elite)** | 🌸 **Cherry Grove** biome inside borders | **+30 pts** |
| **Tier 2 (Elite)** | 👻 **Pale Garden** biome inside borders | **+30 pts** |
| **Tier 2 (Elite)** | 🌿 **Mangrove Swamp** biome inside borders | **+25 pts** |
| **Tier 2 (Elite)** | 🍄 **Mushroom Fields (Mooshroom Island)** | **+25 pts** |
| **Tier 2 (Elite)** | 4th Ancient City inside borders (one-time milestone; not linear) | **+25 pts** |
| **Tier 2 (Elite)** | Every Village above 8 (9th, 10th...) | **+25 pts each** (linear surplus) |
| **Tier 2 (Elite)** | 3rd Pillager Outpost inside borders (one-time milestone; not linear) | **+20 pts** |
| **Tier 2 (Elite)** | 3rd Desert Pyramid inside borders (one-time milestone; not linear) | **+20 pts** |
| **Tier 2 (Elite)** | 3rd Jungle Temple inside borders (one-time milestone; not linear) | **+20 pts** |
| **Tier 2 (Elite)** | 3rd Nether Fortress inside borders (one-time milestone; not linear) | **+20 pts** |
| **Tier 2 (Elite)** | 3rd Bastion Remnant inside borders (one-time milestone; not linear) | **+20 pts** |
| **Tier 2 (Elite)** | 🏜️ **Badlands / Mesa** biome | **+20 pts** |
| **Tier 2 (Elite)** | Swamp Hut (Witch Hut) inside borders (predicted placement) | **+20 pts** |
| **Tier 3 (Quality)** | 🪸 **Warm Ocean / Coral Reef** | **+15 pts** |
| **Tier 3 (Quality)** | 🧊 **Ice Spikes** biome | **+15 pts** |
| **Tier 3 (Quality)** | 🌾 **Windswept / Shattered Savanna** | **+15 pts** |
| **Tier 3 (Quality)** | Igloo with Basement inside borders (predicted via PRNG) | **+15 pts** |
| **Tier 3 (Quality)** | Trail Ruins site inside borders (predicted placement) | **+15 pts** |
| **Tier 3 (Quality)** | Every Trial Chamber above 7 (8th, 9th...) | **+10 pts each** (linear surplus) |
| **Tier 3 (Quality)** | Flower Forest; Bamboo Jungle | **+10 pts each** |
| **Tier 3 (Quality)** | Ocean Ruins; Buried Treasure | **+10 pts each** |
| **Tier 3 (Quality)** | Every Ruined Portal above 7; Shipwrecks above 6 | **+5 pts each** (linear surplus) |
| **Tier 3 (Quality)** | Mineshafts above 15 | **+1 pt each** (linear surplus) |

> [!NOTE]
> **Milestone vs. Linear Scoring Rules (User Decision Record):**
> Per the user's explicit specification, bonuses awarded at the 3rd Outpost, 3rd Desert Pyramid, 3rd Jungle Temple, 3rd Nether Fortress, 3rd Bastion Remnant (+20 pts each milestone) and the 4th Ancient City (+25 pts milestone) are strictly **one-time milestone bonuses** awarded upon reaching that structure count, not recurring linear increments. In contrast, surplus Villages (+25 pts each for 9th+), Trial Chambers (+10 pts each for 8th+), Ruined Portals (+5 pts each above 7), Shipwrecks (+5 pts each above 6), and Mineshafts (+1 pt each above 15) scale linearly per surplus structure.

---

## 6. 4-Level Hierarchical Sort Order

Every seed that satisfies the Guaranteed Hard Floors and Miss Budget ($B \le 2$) is saved directly to the SQLite database. Candidates are ranked on the global leaderboard using a strict 4-level hierarchical tuple:

$$\text{Rank Order} = \Big( \text{Deficit Tier ASC},\; \text{smart\_score DESC},\; \text{weighted\_radial\_dist ASC},\; \text{Origin Dist ASC} \Big)$$

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

> **Implementation evidence:** This is the approved search design. The measured implementation and its limits are recorded in `LATEST_PUSH_REVIEW.md`. Section 7's performance percentages, climate-noise shortcut and automatic biome credits are proposals or projections, not proofs. The current engine keeps exact biome lookup and explicit four-Y witnesses, and does not enable those unproven shortcuts. Center selection ranks the defined constrained-centroid representatives; it is not a proof of globally optimal center placement over arbitrary alternative rules.

### 7.1 Top 5 Zero-Loss Pipeline Optimizations

| Optimization | What Changes in the Pipeline | Why It's Safe (Zero False Rejects) | Throughput & Speedup Impact |
| :--- | :--- | :--- | :--- |
| **1. Enforce $832 \times 832$ Nether Co-Window Compatibility in Step 1** | Stage 1A Step 1 checks if $\ge 2$ Fortresses and $\ge 2$ Bastions exist in $[-562, 562]$. Add a `50 ns` bounding-box check requiring that at least 2 Fortresses and 2 Bastions fit inside a single $832 \times 832$ sub-window ($\Delta X_N \le 832, \Delta Z_N \le 832$) and calculate the valid Overworld center interval $[C_{X,\min}^{\text{Nether}}, C_{X,\max}^{\text{Nether}}]$. | If two Fortresses are $>832\text{m}$ apart in $[-562, 562]$, they can never be co-captured in an $832 \times 832$ Nether box in Stage 1B. | **Cuts seeds entering Mansion biome checks by ~45–55%** (`~1.8×` speedup). |
| **2. Clamp Overworld Preflight Bounds to the Nether Safe Interval** | Instead of scanning the full $[-2000, 2000]$ box for Mansions, Monuments, and Outposts, only test regions within $[C_{X,\min}^{\text{Nether}} - 832,\; C_{X,\max}^{\text{Nether}} + 832]$. | Any Overworld structure outside $[C_{\min}^{\text{Nether}} - 832,\; C_{\max}^{\text{Nether}} + 832]$ cannot be captured without losing a mandatory Nether structure. | **Skips ~40% of Mansion & Monument noise lookups** (`~1.3×` speedup). |
| **3. Move Pure-PRNG Outpost & Trial Chamber Grid Counts *Before* Mansion Biome Noise** | Pillager Outposts roll a pure-PRNG region spawn check *before* biome viability, and Trial Chambers ($\ge 7$ required) use pure chunk-grid PRNG. Verify that $\ge 2$ Outpost PRNG rolls and $\ge 7$ Trial Chamber PRNG slots fall inside the feasible box **before** initializing Overworld climate noise for the Mansion. | Pure PRNG coordinate generation takes $<0.5\,\mu\text{s}$ in C; seeds lacking enough raw PRNG slots can never satisfy floors regardless of biomes. | **Rejects ~70% of remaining seeds before any biome noise runs** (`~1.5×` speedup). |
| **4. Short-Circuit 6D Climate Noise on Mansion Checks** | A Dark Forest requires specific Continentalness ($C > -0.11$, inland), Temperature (temperate), and Humidity ($H > 0.1$). Evaluate noise parameters one octave at a time (`Humidity` $\to$ `Continentalness` $\to$ `Temperature`) and abort immediately on the first miss. | Evaluating 1 Perlin octave tree instead of all 6 on non-matching points is mathematically identical to a full biome lookup. | **Cuts Mansion & Bastion biome check CPU time by ~65–75%**. |
| **5. Skip Redundant Biomes, Multi-Plane Short-Circuit & 5-Biome Nether** | Seeds reaching Stage 2 already certified Dark Forest, Desert, Jungle, and Deep Dark via Stage 1B structures. Short-circuit $Y = 160$ on first `*_peaks` cell (`jagged_peaks | frozen_peaks | stony_peaks`), short-circuit $Y = 0, -48$ on first `lush_caves` & `dripstone_caves`, and verify all 5 Nether biomes exist in $[C_X/8 \pm 416, C_Z/8 \pm 416]$. | Structure placement in Stage 1B certifies those 4 Overworld biomes; early-exit on boolean witnesses avoids full rasterization; Nether check takes $<0.2\text{ ms}$. | **Cuts Stage 2 sampling time by ~60%** while guaranteeing zero Nether resource lock-outs. |

---

### 7.2 Revised Stage 1A Execution Order & Fast-Reject Cascade

```
                          [ Bounded 36-Billion Seed Stream ]
                                          │
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1A, STEP 1: Nether PRNG + Co-Window Check (~1.6 µs, Pure PRNG)   │
      │ • Find Fortresses & Bastions in [-562, 562].                           │
      │ • Verify ≥ 2 of each fit inside a single 832 × 832 co-window.          │
      │ • Output exact Overworld feasible center range [C_min^N, C_max^N].     │
      │ • Rejects ~91% of all seeds with zero climate noise.                   │
      └────────────────────────────────────────────────────────────────────────┘
                                          │ (9% of seeds survive)
                                          ▼
      ┌────────────────────────────────────────────────────────────────────────┐
      │ STAGE 1A, STEP 2: Outpost & Trial Chamber PRNG Slots (~0.6 µs, PRNG)   │
      │ • Verify ≥ 2 Outpost rolls & ≥ 7 Trial Chamber PRNG chunk slots fall   │
      │   inside [C_min^N - 832, C_max^N + 832].                               │
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
      │ STAGE 1B: Exact 2D Event-Slab Solver & Centroid Magnet ($1664 \times 1664$)│
      │ • Half-open Overworld safe interval [X_i - 831, X_i + 832] (width 1664).│
      │ • Nether safe interval [8X_N,j - 3327, 8X_N,j + 3328] (width 6656).    │
      │ • Enforce Guaranteed Hard Floors and Miss Budget ($B \le 2$).          │
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
      │ • Nether: Verify all 5 Nether biomes exist inside 832 × 832 box.       │
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

## 8. Expected Yield & Campaign Economics (Theoretical Models & Projections)

> [!NOTE]
> **Theoretical Models & Ground-Truth Verification Notice:** Expected survivor yields and joint target probabilities are statistical combinatorial projections, not empirically measured counts. Candidate prediction does not establish actual in-engine world generation; approved blueprint design targets must be kept strictly distinct from runtime implementation certification.

- **Joint Target Probability (Analytical Projection):** $\approx 1 \text{ in } 2.5\text{–}3.5\text{ Billion seeds}$.
- **Projected Total Predictor Survivors (Theoretical Model):** $\approx \mathbf{10\text{–}15\text{ High-Tier Seeds}}$ (up to $\sim 30\text{–}50$ across all deficit tiers) across a 36-Billion seed campaign.
- **Stage 5 Verification Objectives:** Top **50 finalists (or 100% of all survivors)** are intended for follow-up verification against the pinned Bedrock server.
  - **Currently implemented:** bounded surface point/block observations, with partial evidence and provider identity recorded.
  - **Not established by the current automated provider:** complete generated structure inventories, intact End Portal rooms, loot, mega-cave entrances or initial-player spawn. Those objectives require additional tooling or appropriately scoped observations; a headless surface job does not certify them.
