# Bedrock Dedicated Server: Production Deployment & Setup Guide
*20-Player Server • 2048×2048 Overworld / 1024×1024 Nether • VCMC Proximity Voice Chat • BedrockAdvancements • IP Masking • Dynamic Lighting • Console Cross-Play*

---

## Table of Contents
1. [Overview & Prerequisites](#1-overview--prerequisites)
2. [Server Configuration (`server.properties`)](#2-server-configuration-serverproperties)
3. [IP Masking & DDoS Protection (Hiding Your Home IP for Free)](#3-ip-masking--ddos-protection-hiding-your-home-ip-for-free)
4. [Addon Installation & Script Permissions](#4-addon-installation--script-permissions)
5. [Applying the Final Seed & First Boot](#5-applying-the-final-seed--first-boot)
6. [In-Game Configuration (Border & Rules)](#6-in-game-configuration-border--rules)
7. [World Border Rules & Exploit Prevention (Player Policy)](#7-world-border-rules--exploit-prevention-player-policy)
8. [Advancements & The "Signature 7" Pack](#8-advancements--the-signature-7-pack)
9. [Recommended Quality-of-Life (QOL) Addons](#9-recommended-quality-of-life-qol-addons)
10. [Seamless Client Connection Guide](#10-seamless-client-connection-guide)
11. [Host Maintenance & Verification Checklist](#11-host-maintenance--verification-checklist)
12. [Launch Day Preparation, Automated Backups & Allowlist](#12-launch-day-preparation-automated-backups--allowlist)

---

## 1. Overview & Prerequisites

This deployment guide operationalizes the active [`MASTER_SEED_BLUEPRINT.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md) specification for a 15–20 player Minecraft Bedrock Dedicated Server (BDS).

### Core Mandatory Addons (The Base 7):
* **Bedrock World Border** (by *myGen*): Behavior Pack (`.mcpack` / `.zip`) and Resource Pack enforcing 2048×2048 Overworld and 1024×1024 Nether.
* **VCMC Proximity Voice Chat**: Official Bedrock server pack (`behavior_packs/vcmc_bp` and `resource_packs/vcmc_rp`) with companion app.
* **BedrockAdvancements** (by *myGen*): Base engine pack bringing Java-style advancements, toast notifications, and progress trees to Bedrock.
* **Server Milestones Pack (`Server_Milestones.mcpack`)**: Custom expansion pack adding our 7 signature server achievements.
* **Raiyon's Dynamic Light**: Real-time handheld and off-hand dynamic lighting (Script API 1.21+).
* **The Land Claim Addon** (by *NasaRemix & Areed*): Non-invasive UI-based homestead territory protection and chest locking (teleport button removed).
* **Clear Glass** (from *Bedrock Tweaks*): Clean transparent window textures removing default diagonal glare scratches (~50 KB).
* **Brewing Guide** (by *DevAV*): Direct visual potion recipe overlay in the Brewing Stand interface (~200 KB resource pack).

### Optional Modular Addons (Enable / Disable as Desired):
* **(Optional) Twixxel's Stalkers** (by *PnTMC*): Psychological night horror entity; strictly Overworld-only with 7-heart jump-scare damage (14 HP), guaranteed 1-hit vanish, and 30-minute global cooldown.
* **(Optional) GraveStones** (by *Effect99*): Anti-despawn death chest protection with coordinate tracking key (no teleportation).

### Platform & Cross-Play Tools:
* **Minecraft Bedrock Dedicated Server (BDS)**: Official binary release (1.21+ / live target 1.26.x).
* **Console Bridge App (for console players)**: *BedrockTogether* (free on iOS/Android).

---

## 2. Server Configuration (`server.properties`)

Stop the server, open `server.properties`, and set the following values:

```properties
# Server Identity & World
server-name=My 20-Player SMP
level-name=world
# Insert your final approved seed here before first boot:
level-seed=

# Gameplay
gamemode=survival
force-gamemode=false
difficulty=normal
allow-cheats=false

# Visual & Simulation Distance
# 32 is the hard ceiling for Bedrock multiplayer (do not attempt higher)
view-distance=32

# CRITICAL: Keep tick-distance at 4 (the official BDS factory default).
# 4 chunks = 81 simulated chunks per player. Bumping to 6 more than doubles
# the load to 169 chunks per player (over 3,300 active ticking chunks for 20 players!).
# Leaving this at 4 protects your 20-player server from severe TPS lag.
tick-distance=4

# Offloads visual chunk terrain rendering to client devices
client-side-chunk-generation-enabled=true

# Multi-threading (0 = automatically use all CPU cores on the host machine)
max-threads=0

# Player Capacity (set to 25 to reserve admin slots when 20 players are online)
max-players=25

# Networking & Security
server-port=19132
server-portv6=19133
online-mode=true
allow-list=true
```

---

## 3. IP Masking & DDoS Protection (Hiding Your Home IP for Free)

When hosting from home, **never give out your raw home IP address**. Anyone who has your IP can see your approximate physical location, and a simple network flood (DDoS) can crash your entire household's internet connection.

Because Minecraft Bedrock requires **UDP traffic (port 19132)**, free web reverse proxies (like Cloudflare free CDN or TCPShield) do not work. Below are the two proven, 100% free options that fully support Bedrock UDP and 20+ concurrent players.

### Option A: Playit.gg (Recommended / 2-Minute Setup)
*Best for: Zero technical setup, no credit card, no router port-forwarding needed.*

1. **Download:** Go to [playit.gg](https://playit.gg) and download the free program for your operating system (Windows/Linux/macOS).
2. **Run & Claim:** Run the application. Click the claim link generated in the terminal to bind it to your free Playit account.
3. **Create Bedrock Tunnel:** 
   * In your Playit dashboard, select **Add Tunnel**.
   * Tunnel Type: **Minecraft Bedrock (UDP)**.
   * Local Port: **`19132`**.
4. **Result:** Playit assigns you a public address (e.g. `my-smp.gl.at.ply.gg:38492`).
5. **How Players Connect:** Players enter the domain and the assigned port into Minecraft or BedrockTogether. Your real home IP remains 100% hidden behind Playit’s DDoS-mitigated anycast network.

### Option B: Oracle Cloud Always Free + Rathole (Advanced / Standard Port 19132)
*Best for: Admins who want players to connect via the clean standard port `19132` (or a custom domain like `play.mysmp.com`).*

1. **Create Free Cloud VM:** Sign up for an **Oracle Cloud Always Free** account and launch a free Ubuntu instance (includes 10 TB free monthly bandwidth).
2. **Install Rathole:** Download [Rathole](https://github.com/rapiz1/rathole) (an ultra-fast, open-source UDP reverse proxy written in Rust) on both your Oracle VM and your home server PC.
3. **Configure Routing:**
   * On the Oracle Cloud VM (`server.toml`), bind incoming UDP port `19132`.
   * On your home PC (`client.toml`), point Rathole to the Oracle VM.
4. **Result:** All 20 players connect directly to your Oracle VM’s IP on standard port `19132`. Rathole forwards the UDP packets to your home PC in less than 2 milliseconds. Your home IP is never exposed.

*Bandwidth Verification:* A 20-player server uses ~5 Mbps during active play. Both options comfortably handle up to 50–100+ Mbps with zero bottlenecks.

---

## 4. Addon Installation & Script Permissions

### Step 1: Install Pack Files
Copy all behavior and resource packs into their respective server directories:

```text
bedrock_server/
├── behavior_packs/
│   ├── world_border_bp/
│   ├── vcmc_bp/
│   ├── bedrock_advancements_bp/
│   ├── server_milestones_bp/
│   ├── raiyons_dynamic_light_bp/
│   ├── land_claim_bp/
│   ├── gravestones_bp/ (optional)
│   └── stalker_bp/ (optional)
└── resource_packs/
    ├── world_border_rp/
    ├── vcmc_rp/
    ├── bedrock_advancements_rp/
    ├── server_milestones_rp/
    ├── raiyons_dynamic_light_rp/
    ├── land_claim_rp/
    ├── clear_glass_rp/
    ├── brewing_guide_rp/
    ├── gravestones_rp/ (optional)
    └── stalker_rp/ (optional)
```

Add the UUIDs for all packs into your world manifest files:
* `worlds/world/world_behavior_packs.json`
* `worlds/world/world_resource_packs.json`

### Step 2: Grant Script Network Permissions (CRITICAL FOR VCMC)
Bedrock Dedicated Server restricts addon network access by default. Without this module, VCMC cannot establish a voice bridge.

Create or edit **`config/default/permissions.json`**:

```json
{
  "allowed_modules": [
    "@minecraft/server",
    "@minecraft/server-gametest",
    "@minecraft/server-ui",
    "@minecraft/server-admin",
    "@minecraft/server-net"
  ]
}
```

### Step 3: Grant Operator Permissions
In the root `permissions.json` file of the server, add your Xbox User ID (XUID) as an operator so you can execute the setup commands:

```json
[
  {
    "permission": "operator",
    "xuid": "YOUR_XUID_HERE"
  }
]
```
*(Your XUID is displayed in the server console log when you connect).*

---

## 5. Applying the Final Seed & First Boot

1. Ensure the server is shut down.
2. If `worlds/world` exists from prior testing, archive or remove it to generate a clean world from the final seed.
3. In `server.properties`, set:
   ```properties
   level-seed=YOUR_FINAL_SEED_HERE
   ```
4. Start the server to generate the world and load the behavior/resource packs.

---

## 6. In-Game Configuration (Border & Rules)

Connect to the server with your operator account. Run these commands directly in chat or via the server console:

### 1. General Game Rules
```mcfunction
/gamerule playerssleepingpercentage 25
/gamerule showcoordinates true

# ONLY run this if using the optional GraveStones addon:
# /gamerule keepInventory true
```
*(With 20 players, 5 players sleeping passes the night instead of requiring unanimous sleep. `keepInventory true` is only needed if GraveStones is installed to transfer items into graves behind the scenes).*

### 2. World Border Configuration (2048 × 2048 Overworld / 1024 × 1024 Nether)
Replace `<CX>` and `<CZ>` with the certified blueprint centroid for your chosen seed:

```mcfunction
# 1. Enable Overworld and Nether borders
/scriptevent worldborder:enable overworld
/scriptevent worldborder:enable nether

# 2. Set Overworld to 2048x2048 blocks (2048 / 16 = 128 chunks)
# Replace <CX> <CZ> with your certified Overworld center coordinates
/scriptevent worldborder:size overworld 128
/scriptevent worldborder:center overworld <CX> <CZ>

# 3. Set Nether to 1024x1024 blocks (1024 / 16 = 64 chunks)
# Replace <NETHER_CX> <NETHER_CZ> with the 8:1 scaled integer center (CX/8, CZ/8)
/scriptevent worldborder:size nether 64
/scriptevent worldborder:center nether <NETHER_CX> <NETHER_CZ>

# 4. Enforce safe teleport and block interaction protection outside the border
/scriptevent worldborder:action all teleport
/scriptevent worldborder:interaction all on

# 5. Enable a 25-block boundary warning wall and verify status
/scriptevent worldborder:warning all on
/scriptevent worldborder:warndistance all 25
/scriptevent worldborder:status
```

---

## 7. World Border Rules & Exploit Prevention (Player Policy)

While the addon technically enforces boundaries via physics knockbacks and teleport scripts, players will inevitably attempt to test the limits.

### How the Addon Handles Exploit Attempts
* **Ender Pearls & Chorus Fruit:** If a player throws a pearl through the particle wall, the moment they arrive on coordinates outside the boundary, the script immediately detects the violation and **teleports them back inside facing inward**.
* **Vehicle / Bed Glitches:** If players push a boat or minecart across the border line or place a bed so the wake-up tile pushes them outward, the addon's `interaction on` setting disables block breaking and container opening outside, and dismounting immediately triggers the teleport rebound.
* **The Nether Portal 8:1 Traversal Trap:**
  * $1\text{ block in the Nether} = 8\text{ blocks in the Overworld}$.
  * The Overworld border radius is $1{,}024\text{m}$. That means an Overworld border coordinate ($X = C_X \pm 1024$) maps to only **$X = C_X/8 \pm 128$ in the Nether**.
  * Because our playable Nether border is $1{,}024 \times 1{,}024$ (radius $512\text{m}$), players can legally walk out to Nether coordinate $X = C_X/8 \pm 300$ inside the Nether.
  * **Warning:** If a player builds a portal at Nether $X = C_X/8 \pm 300$, stepping through will generate an Overworld exit portal at $X = C_X \pm 2400$ (**outside the Overworld border**).
  * The instant they load into the Overworld, the addon detects they are out of bounds and **snaps them back inside to $X = C_X \pm 1020$**. They will be stranded inside, separated from their portal, and unable to return.

---

### Official Server Boundary Rules (Copy-Paste to Discord `#rules`)

```markdown
### 🌐 Server World Border & Exploit Rules

1. **The Border is Final:**
   * The playable world is strictly bounded to **2048×2048 in the Overworld** and **1024×1024 in the Nether**.
   * Any attempt to deliberately bypass, breach, or glitch through the particle border via Ender Pearls, Chorus Fruit, vehicles (boats/minecarts), beds, or desync exploits is strictly prohibited.

2. **Nether Exploration & Portal Linking (The 8:1 Ratio):**
   * The Nether is 100% open and explorable across its entire **1024×1024 boundary**.
   * However, because 1 Nether block = 8 Overworld blocks, any portal built beyond **±128 blocks from the Nether Center** will exit outside the 2048×2048 Overworld border.
   * If you ignite a portal in the deep Nether, the Overworld border will snap you back inside, leaving your portal stranded outside. To return safely to the Overworld, use portals built within **±128 blocks of center**.

3. **Illegal Land & Loot:**
   * Any terrain, structures, or loot generated outside the particle wall are off-limits. Any items acquired past the boundary will be confiscated and deleted.

4. **Desync / Teleport Loop Protocol:**
   * If network lag or an accidental collision causes you to get stuck in a visual teleport loop at the border wall, relog immediately or ping an Admin in `#server-help` to reset your coordinates to the central town spawn.
```

---

## 8. Advancements & The "Signature 7" Pack

The server runs **BedrockAdvancements** by *myGen*. This provides:
* **100+ standard Java/Bedrock advancements** pre-loaded (all standard survival progression steps).
* **The Book of Advancements:** Crafted by surrounding a normal Book with 4 Amethyst Shards. Can be browsed in inventory or placed on a Lectern.
* **On-Screen Toasts:** Visual sliding banners appear privately on the screen of the player who completed the goal.
* **Server-Wide Chat Announcements:** Just like Java Edition, achievements broadcast to public chat by default (*"Player has completed the challenge [Edge of the Known World]"*).

### The Signature 7 Custom Milestones

Our custom companion pack (**`Server_Milestones.mcpack`**) injects a dedicated **"Server Milestones"** tab alongside the vanilla trees:

| # | Milestone Name | Frame Type | Trigger Description | Coordinate Logic |
| :-: | :--- | :---: | :--- | :--- |
| **1** | **"Welcome to the SMP"** | `task` | Join the world and step into the central starter town. | Radius $\le 64\text{m}$ of $(C_X, C_Z)$ |
| **2** | **"Loud & Clear"** | `task` | Successfully link to VCMC proximity voice chat. | Event: `/vcmc:verify` completed |
| **3** | **"Night Owl"** | `task` | Sleep in a bed and help skip the night under the 25% sleep rule. | Event: Bed sleep cycle |
| **4** | **"Staking Your Claim"** | `goal` | Place and sleep in a bed at your own homestead outside town. | Distance $> 200\text{m}$ from $(C_X, C_Z)$ |
| **5** | **"Edge of the Known World"** | `challenge` | Discover and approach the Overworld 2048×2048 world border. | Distance $\ge 1{,}014\text{m}$ from $C_X$ or $C_Z$ |
| **6** | **"Bounced Back"** | `task` | Get safely repelled by the world border particle wall. | Event: `worldborder:action:teleport` |
| **7** | **"Nether Frontier"** | `challenge` | Reach the outer edge of the 1024×1024 Nether boundary. | Nether distance $\ge 504\text{m}$ from center |

*Note on Compilation:* Because milestones #1, #4, #5, and #7 require exact center coordinates, `Server_Milestones.mcpack` is compiled directly after the final seed and its certified centroid $(C_X, C_Z)$ are confirmed from the blueprint search.

---

## 9. Recommended Quality-of-Life (QOL) Addons

To keep the 20-player server engaging and eliminate common causes of burnout, the following two addons are configured:

### 1. Raiyon's Dynamic Light (Visual Exploration)
* **What it Does:** Holding a torch, lantern, soul torch, or glowstone in the main hand or off-hand casts moving real-time illumination (Light Level 14–15).
* **Sneak-to-Place:** Crouching while holding an off-hand torch allows instant block placement on cave walls without swapping items.
* **Miner's Helmets:** Craftable headgear providing hands-free light.
* **Engine Safe:** Uses modern `@minecraft/server` scripting instead of laggy command blocks, leaving zero ghost blocks and causing no server tick delay.

### 2. The Land Claim Addon (by NasaRemix & Areed)
* **What it Does:** Provides non-invasive homestead territory protection in our compact 2048×2048 Overworld.
* **Overworld Only Policy:** Land claims are strictly restricted to the Overworld (`minecraft:overworld`). The Nether and The End remain 100% unclaimed public wilderness.
* **No-Teleport Patch (Pure Survival):** The "Teleport to Claim" button shown in the addon's gallery is **completely removed from the UI form**. Players are strictly required to travel by foot, horse, minecart, or Nether ice-boat highways—eliminating magic warp shortcuts.
* **Player Flow:** Players mark two opposite corners using a claim wand (Clock/Feather) to establish a particle-bounded homestead.
* **Visuals & Identity:** When anyone enters a claim, boundary particles briefly flash on entry, and an on-screen title displays the claim name (`Entering: [Name]`).
* **Security:** Blocks strangers from breaking/placing blocks, locks all containers (chests, barrels, furnaces), and prevents creeper explosions from damaging claimed builds.
* **Team Invites:** Opening the claim GUI displays a dropdown list of currently online players, letting owners assign Builder, Container Access, or Co-Owner roles with one click.

### 3. Clear Glass (from Bedrock Tweaks)
* **What it Does:** Replaces default vanilla glass and stained glass textures with clean, transparent textures by removing the diagonal white glare streaks across the center of blocks.
* **Impact:** Windows, glass domes, and modern buildings look crystal clear without obstructing your view of the landscape.
* **Lightweight:** Pure 16x vanilla resource pack (~50 KB), zero performance overhead on mobile or consoles.

### 4. Brewing Guide (by DevAV)
* **What it Does:** Overlays a visual recipe and ingredient tree directly inside the Brewing Stand interface.
* **Convenience:** Displays how to brew every potion (Invisibility, Strength, Weakness, Water Breathing, Speed, etc.) and ingredient modifiers (Redstone for duration, Glowstone for potency, Gunpowder for splash) without needing to alt-tab or look up external wikis.
* **Lightweight:** Pure UI resource pack (~200 KB), zero CPU overhead, works seamlessly on mobile, PC, and consoles.

### 5. (Optional) GraveStones (by Effect99) — Survival Death Protection
* **What it Does:** When a player dies, a locked gravestone spawns at their exact death coordinates holding all their items safely.
* **No Teleportation:** Players receive a **Grave Key** displaying coordinates and distance in meters. Players **cannot** teleport; they must make the corpse run back on foot to retrieve their items.
* **Lava & Void Proof:** Prevents gear from burning in lava or falling into the End void ($Y=1$ safety platform).
* **Anti-Theft:** Only the player holding the unique key can unlock the grave.
* **Engine Rule Requirement:** Requires `/gamerule keepInventory true`. The engine rule is used purely behind the scenes to transfer items into the grave without spilling on the ground; **players still respawn naked with an empty inventory**.
* **Modular / Optional:** If you prefer pure vanilla death penalties (where items drop on the ground and can despawn after 5 minutes), simply leave this addon uninstalled and keep `keepInventory false`.

### 6. (Optional) Twixxel's Stalkers (by PnTMC) — Psychological Night Horror
* **What it Does:** Introduces a rare, eerie watcher entity that silently observes players at night from afar (behind trees, ridge lines, or through glass base windows) and disappears when stared at or approached.
* **Multiplayer Dynamics & Concurrency:**
  * **One at a Time:** The addon script uses an internal global cooldown timer and targets **only one player at a time**. It will **not** spam 20 stalkers across your server.
  * **Visible to Everyone:** The Stalker is a true server-side network entity (`pntmc:stalker`). Any other player looking in the same direction can see it standing behind their friend, creating hilarious and terrifying organic reactions on **VCMC proximity voice chat**.
  * **Target Switching:** While spawned, it focuses on its chosen target. However, if a second player attacks it or gets significantly closer than the original target, the entity's target selector re-evaluates and switches focus to the closer player. If the original target logs off, dies, or sleeps, the entity despawns or redirects. On every fresh spawn cycle, the script randomly selects a new target from all active Overworld players.
* **Spawn Timing & Conditions (When Does it Spawn?):**
  * **Night Time & Low Light:** Spawns during the Minecraft night cycle (time $> 13000$ ticks) or inside deep unlit caves (block light level $\le 7$).
  * **Perimeter Distance:** Spawns at a perimeter of **24–48 blocks away** from the target player, specifically seeking spots with partial line of sight (behind tree trunks, over hill ridges, or right outside window glass).
  * **Overworld Only Enforcement:** Strictly restricted to `minecraft:overworld` via `behavior_packs/stalker_bp/spawn_rules/stalker.json` (or script check `player.dimension.id === "minecraft:overworld"`). It will never spawn in the Nether or End.
* **Despawn Triggers (How to Make It Despawn):**
  * **Player Eye Contact (Stare-Down):** Center your crosshair directly on its body/face and stare at it for $\approx 1.5–2$ seconds. The script registers the eye-contact vector, emits a loud screech, bursts into dark smoke particles, and instantly despawns (`entity.remove()`).
  * **Charging It (Sprinting Closer):** If you sprint directly toward it, crossing within **$\approx 12$ blocks** triggers its proximity flee response, causing it to vanish before you can touch it.
  * **Illumination & Sleeping:** Placing torches/lanterns nearby raises block light above 7, blocking attack pathing. Sleeping in a bed (under the 25% sleep rule) triggers daybreak, which immediately despawns it silently.
  * **Slaying It:** Shooting it from range with a bow/crossbow or hitting it mid-charge kills it (20–40 HP), granting XP and permanently despawning it for that cycle.
  * **Admin Emergency Command:** If an active stalker ever bugs out or an admin needs to banish it instantly, execute this in server console or chat:
    ```mcfunction
    /kill @e[type=pntmc:stalker]
    ```
* **AI Behavior & Attack Conditions (When Does It Charge?):**
  * **Case 1: Stare-Down (Repelled):** Player looks directly at it $\rightarrow$ Stalker screeches, turns to smoke, and vanishes. (Player successfully defends themselves).
  * **Case 2: Seen, Then Back Turned (The Ambush):** If a player catches a glimpse of it (crosshair passes over it) but then turns their back, ignores it, or runs away into the dark $\rightarrow$ The Stalker enters aggressive ambush mode, initiates a **silent high-speed sprint charge**, and hits for **7 hearts (14 HP)** with a jumpscare sting + temporary Darkness before instantly vanishing.
  * **Case 3: What If the Player Never Sees It? (Oblivious Target):** If the player is busy crafting, organizing chests, mining, or facing away and never registers line of sight during the 60–90 second observation window, **it will NOT charge**. Charging an unaware player feels cheap. Instead, it plays a faint eerie whisper/wind sound, **silently dissolves into the shadows, and immediately retargets another active Overworld player** (or resets into its cooldown). The entity never remains stuck outside an empty wall or an AFK player.
* **Can the Stalker Enter Houses? (Base Safety):**
  * **No Wall Phasing or Block Breaking:** The Stalker possesses standard solid collision boxes. It **cannot** phase through walls, break blocks, or glitch through glass.
  * **Closed Doors Protect You:** It cannot open closed wooden doors, iron doors, trapdoors, or fence gates. Closing your doors keeps you 100% physically safe.
  * **Interior Light Repulsion:** It will not enter well-lit rooms (light level $\ge 8$). Standard home lighting (torches, lanterns) keeps indoor spaces safe.
  * **Open Doors in Darkness:** If a player leaves their front door wide open and the room is pitch black, it can pathfind inside. Keep your front doors shut!
  * **Window Watching Synergy (Clear Glass):** Its intended design is lurking in the dark garden outside and staring *through* windows. With our **Clear Glass** pack active, players looking out their windows will get a crystal-clear, terrifying view of the Stalker staring right at them through the glass!
* **Combat Mechanics (Attacking & Defending):**
  * **How We Attack It:** 
    * *Ranged Sniping:* Players can shoot it with a Bow or Crossbow from 30+ blocks away before it triggers its flee mechanic.
    * *Cornering / Charge Counter:* If caught in a narrow cave tunnel or during its sprint charge, players can strike it with a sword or axe.
* **Damage Calibration: 7 Hearts (14 HP) + Guaranteed 1-Hit Vanish:**
  * In Minecraft Bedrock, 1 heart = 2 HP. To configure exactly **7 hearts** of base damage, edit `behavior_packs/stalker_bp/entities/stalker.json`:
    ```json
    "minecraft:attack": {
      "damage": 14
    }
    ```
  * **Guaranteed 1-Hit Vanish Guard (Impossible to Hit Twice):**
    To ensure players never get double-tapped in cave corners or desync traps, enforce instant deletion on hit in `behavior_packs/stalker_bp/scripts/main.js`:
    ```javascript
    // 1-Hit Guaranteed Vanish: Deletes stalker immediately on first contact
    world.afterEvents.entityHitEntity.subscribe((event) => {
        if (event.damagingEntity?.typeId === "pntmc:stalker") {
            // Spawn jump-scare smoke particles at impact location
            event.hitEntity.dimension.spawnParticle("minecraft:huge_explosion_emitter", event.damagingEntity.location);
            // Instantly delete the entity so a second strike is impossible
            event.damagingEntity.remove();
        }
    });
    ```
  * **Armor Damage Breakdown (Survival Impact):**
    * *Unarmored Player (Naked):* Takes 7 hearts, dropping to **3 hearts (6 HP)**. Pure adrenaline spike and panic, but 100% guaranteed survival for a full-health player!
    * *Full Iron Armor (60% reduction):* Takes $14 \times 0.40 = 5.6\text{ HP}$ ($\approx 2.8$ hearts), leaving them with **7.2 hearts**.
    * *Full Diamond Armor (80% reduction):* Takes $14 \times 0.20 = 2.8\text{ HP}$ ($\approx 1.4$ hearts), leaving them with **8.6 hearts**.
* **Enforced 30-Minute Global Cooldown (`36000` Ticks):**
  * The server enforces a strict **30-minute global cooldown** between stalker appearances.
  * In `behavior_packs/stalker_bp/scripts/main.js` (or `config.js`):
    ```javascript
    // Enforced 30-minute server cooldown (30 min * 60 sec * 20 ticks = 36000 ticks)
    const STALKER_COOLDOWN_TICKS = 36000;
    ```
  * *Why 30 minutes is optimal:* It strikes at most 1–2 times per real-time hour across the entire 20-player community. It guarantees that every encounter remains rare, shocking, and atmospheric, rather than becoming annoying spam.
* **Server Tick Rules:**
  * **Server Random Tick Speed (`/gamerule randomtickspeed`):** Keep strictly at **`1`** (Bedrock factory default). Do NOT raise this to 3 on a 20-player server.
  * **Server Simulation Distance (`tick-distance`):** Keep strictly at **`4`** in `server.properties`.
* **Modular / Optional:** Completely toggleable. Simply drop `stalker_bp/` and `stalker_rp/` into the server or leave them out according to community preference.

---

## 10. Seamless Client Connection Guide

Share these instructions with your players based on their hardware:

### A. Windows PC, Android, and iOS Players
1. Open Minecraft Bedrock.
2. Select **Play** → **Servers** → scroll to the bottom and click **Add Server**.
3. Enter your server's **Server Name**, **IP Address** (or your Playit/Oracle tunnel domain), and **Port** (e.g. `19132` or your Playit port).
4. Click **Play** or **Save**.

### B. Console Players (PlayStation 4/5, Xbox, Nintendo Switch)
Console platforms restrict direct IP connections. Players can connect seamlessly via the free **BedrockTogether** app:

1. **Download the App:** Install **BedrockTogether** (free on iOS App Store & Google Play). *(Alternatives: MC Server Connector, MC LAN Proxy, MCXboxBroadcast).*
2. **Wi-Fi Connection:** Connect the mobile device running the app to the **same Wi-Fi network** as the console.
3. **Configure the App:**
   * Enter your server's **IP Address** (or Playit domain).
   * Enter the **Port** (e.g. `19132` or your assigned Playit port).
   * Tap **Watch Ad and Run**.
4. **Join on Console:**
   * On your PlayStation/Xbox/Switch, launch Minecraft and go to **Play** → **Friends** (or **Worlds**).
   * Look under **LAN Games**. The server will appear automatically.
   * Click to join.
   * *(Once the world loads, the player can safely close the phone app).*

### C. Setting Up VCMC Proximity Voice Chat (All Players)
1. Download the **VCMC App** on PC, Android, or mobile.
2. Open the app and connect to your server's designated room.
3. Copy the personal verification command from the app (e.g., `/vcmc:verify <code>`).
4. Paste that command into Minecraft chat. Proximity audio will activate immediately with spatial distance falloff.

---

## 11. Host Maintenance & Verification Checklist

- [ ] `server.properties` verified: `view-distance=32`, `tick-distance=4`, `max-players=25`, `max-threads=0`.
- [ ] IP Masking active (Playit.gg agent running OR Oracle Cloud + Rathole reverse proxy active).
- [ ] `config/default/permissions.json` has `"@minecraft/server-net"` enabled.
- [ ] Final seed set in `server.properties` and fresh `worlds/world` created.
- [ ] Operator XUID added to root `permissions.json`.
- [ ] In-game setup executed:
  - [ ] `/gamerule playerssleepingpercentage 25` applied.
  - [ ] `/scriptevent worldborder:size overworld 128` applied with center `<CX> <CZ>`.
  - [ ] `/scriptevent worldborder:size nether 64` applied with center `<CX/8> <CZ/8>`.
  - [ ] `/scriptevent worldborder:status` verified in console/chat.
- [ ] Addons loaded:
  - [ ] Bedrock World Border (myGen) active.
  - [ ] VCMC proximity voice chat active.
  - [ ] BedrockAdvancements (base pack) active.
  - [ ] `Server_Milestones.mcpack` active with custom tab visible in the Book of Advancements.
  - [ ] Raiyon's Dynamic Light active.
  - [ ] The Land Claim Addon (NasaRemix & Areed) active.
  - [ ] Clear Glass resource pack active.
  - [ ] Brewing Guide (DevAV) resource pack active.
  - [ ] *(Optional)* GraveStones (Effect99) active with `/gamerule keepInventory true`.
  - [ ] *(Optional)* Twixxel's Stalkers (PnTMC) active (Overworld only, 7-heart damage, 1-hit vanish, 30-min cooldown verified).
- [ ] Boundary rules posted to server Discord `#rules`.
- [ ] Pre-generate terrain inside the 2048×2048 area prior to launch day to eliminate on-the-fly chunk generation lag.
- [ ] `allow-list=true` enabled in `server.properties` and 20 player Gamertags added.
- [ ] Automated backup script (`backup.bat` / `backup.sh`) tested with `backups/backup.log` verified.

---

## 12. Launch Day Preparation, Automated Backups & Allowlist

To ensure the server operates at a flawless 20.0 TPS and is completely protected against griefers and corruption, implement these three operational best practices:

### 1. Pre-Generating Chunks (The Launch Day Lag Shield)
* **The Problem:** On Day 1, 20 players will log in simultaneously and scatter in all directions exploring the world. Generating new chunks on the fly (calculating terrain noise, biomes, cave carvers, ores, and structures) for 20 players at once will push CPU usage to 100% and drop TPS down into the single digits.
* **The Solution:** Because our playable world is strictly bounded to **2048×2048** (128 chunks across = 16,384 total chunks), you can **pre-generate the entire world in 10–15 minutes** before players ever join!
* **How to Pre-Generate:**
  1. Log in with your Operator account before opening the server to friends.
  2. Switch to Creative or Spectator mode: `/gamemode creative`.
  3. Fly in a snake or spiral pattern across the $2048 \times 2048$ box (from $C_X - 1000$ to $C_X + 1000$), or use an auto-teleport macro hopping in 128-block increments ($X, Z$).
  4. Once pre-generated, all 16,384 chunks are permanently written to disk in `worlds/world/db/`. When players join on launch day, chunks load instantly from disk in milliseconds with **zero CPU worldgen lag** and locked at **20.0 TPS**.

* **Can We Add a Mod to Keep Previously Visited Chunks Rendered in the Horizon?**
  * **The Java Reality:** On Java Edition, mods like *Bobby* or *Distant Horizons* save visited chunks client-side to render extended Level-of-Detail (LOD) vistas far past the server render distance.
  * **Why Bobby / Distant Horizons Cannot Run as Bedrock Addons:**
    * Bedrock is written in native C++ using the closed **RenderDragon** graphics engine.
    * Bedrock client security and console platforms (PlayStation, Xbox, Switch, iOS) do not allow third-party client mods to intercept server network packets or inject custom LOD terrain meshes into local disk storage. Any third-party memory-injection hacks break console cross-play and fail on BDS.
  * **Why You Do Not Need It on Our Server:**
    * Because we have already set **`view-distance=32`** in `server.properties` and enabled **`client-side-chunk-generation-enabled=true`**, Bedrock natively renders a massive **512-block radius** around every player!
    * That is a **$1{,}024 \times 1{,}024$ circular field of vision**.
    * In our compact $2048 \times 2048$ world, standing near the center with a 32-chunk view distance allows players to literally see **halfway to the entire world border in all directions natively**!
    * Once chunks are pre-generated, the server feeds these pre-built chunks to client GPUs in fractions of a second, delivering the ultimate panoramic horizon without needing unstable third-party client mods.

### 2. Automated World Backups with Persistent Logging (Peace of Mind)
Bedrock Dedicated Server does not have an automatic backup engine. If power blinks, Windows updates, or a corrupt block occurs, you need a quick restore point with a verifiable audit log.

#### For Windows Host (`backup.bat`):
Create `backup.bat` inside your server folder:
```bat
@echo off
setlocal enabledelayedexpansion
set "BACKUP_DIR=backups"
set "LOG_FILE=%BACKUP_DIR%\backup.log"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set "ARCHIVE_NAME=world-backup-%mydate%-%mytime%.zip"

echo [%date% %time%] Starting backup of worlds\world... >> "%LOG_FILE%"
tar -a -c -f "%BACKUP_DIR%\%ARCHIVE_NAME%" "worlds\world"

if exist "%BACKUP_DIR%\%ARCHIVE_NAME%" (
    for %%F in ("%BACKUP_DIR%\%ARCHIVE_NAME%") do set /a size_mb=%%~zF/1048576
    echo [%date% %time%] [SUCCESS] Created %ARCHIVE_NAME% (!size_mb! MB) >> "%LOG_FILE%"
    echo [Backup Complete] Saved to %BACKUP_DIR%\%ARCHIVE_NAME% (!size_mb! MB)
) else (
    echo [%date% %time%] [ERROR] Failed to create backup archive! >> "%LOG_FILE%"
    echo [Backup Failed] Check permissions!
)
```

#### For Linux / macOS Host (`backup.sh`):
Create `backup.sh` inside your server folder and make it executable (`chmod +x backup.sh`):
```bash
#!/bin/bash
BACKUP_DIR="./backups"
LOG_FILE="$BACKUP_DIR/backup.log"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
ARCHIVE_NAME="world-backup-$TIMESTAMP.tar.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup of worlds/world..." >> "$LOG_FILE"
tar -czf "$BACKUP_DIR/$ARCHIVE_NAME" worlds/world

if [ -f "$BACKUP_DIR/$ARCHIVE_NAME" ]; then
    SIZE_MB=$(du -m "$BACKUP_DIR/$ARCHIVE_NAME" | cut -f1)
    # Prune backups older than 7 days (keep latest 28 runs on a 6-hour schedule)
    PRUNED=$(ls -t "$BACKUP_DIR"/world-backup-*.tar.gz | tail -n +29 | wc -l)
    ls -t "$BACKUP_DIR"/world-backup-*.tar.gz | tail -n +29 | xargs -r rm --
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] Created $ARCHIVE_NAME (${SIZE_MB} MB) | Pruned $PRUNED old archive(s)." >> "$LOG_FILE"
    echo "[Backup Complete] Saved to $BACKUP_DIR/$ARCHIVE_NAME (${SIZE_MB} MB)"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] Failed to create backup archive!" >> "$LOG_FILE"
fi
```

#### What the Log Looks Like (`backups/backup.log`):
```text
[2026-10-22 04:00:00] Starting backup of worlds/world...
[2026-10-22 04:00:03] [SUCCESS] Created world-backup-2026-10-22_04-00-00.tar.gz (48 MB) | Pruned 0 old archive(s).
[2026-10-22 10:00:00] Starting backup of worlds/world...
[2026-10-22 10:00:03] [SUCCESS] Created world-backup-2026-10-22_10-00-00.tar.gz (51 MB) | Pruned 1 old archive(s).
```

### 3. Server Allowlist / Whitelist Security
Automated port-scanning bots constantly scan Playit.gg tunnels and public UDP ports looking for open Bedrock servers to join, spam chat, or drop illegal items. Enforcing an allowlist guarantees only your 20 invited friends can ever enter.

* **Step 1: Enable in `server.properties`:**
  ```properties
  allow-list=true
  ```
* **Step 2: Add Your Players via Console or In-Game:**
  As Operator, add each of your 20 friends by their official Xbox Gamertag:
  ```mcfunction
  /whitelist on
  /whitelist add GamerTag1
  /whitelist add GamerTag2
  /whitelist list
  /whitelist reload
  ```
* **Step 3: Direct File Editing (`allowlist.json`):**
  Alternatively, you can populate the root `allowlist.json` file directly while the server is stopped:
  ```json
  [
    {
      "name": "FriendGamertag1",
      "ignoresPlayerLimit": false
    },
    {
      "name": "FriendGamertag2",
      "ignoresPlayerLimit": false
    }
  ]
  ```
* **Result:** Handshakes from unlisted Gamertags, network crawlers, or rogue scanners are instantly dropped at the network boundary with the message *"You are not whitelisted on this server!"* Only approved players can connect.
