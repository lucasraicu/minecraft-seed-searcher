# System Architecture & Flow Diagrams: Minecraft Seed Searcher

This document contains the visual architecture diagrams for the **Minecraft Seed Searcher** public platform, custom database engine, and GPU trillion-seed harvest pipeline.

---

## Diagram 1: The 4-Pillar Product Ecosystem

```mermaid
flowchart TD
    subgraph "The 4 Product Pillars (The Minecraft Seed Platform)"
        P1["<b>PILLAR 1: Optimal Realm God Seeds</b><br>• Lucas's Strict 14-Floor Master Blueprint<br>• 10k Seeds for 2048 | 10k for 4096 | 10k for 8192<br>• Perfect 8:1 Nether Alignment & Chunk-16 Borders<br><i>(Target: 15-20 Player Dedicated Realms)</i>"]
        
        P2["<b>PILLAR 2: Curated Play-Style Presets</b><br>• 16 Curated Presets across 5 Themes (Builders, Speedrun, Combat...)<br>• Top 250 Showcase Seeds per Preset<br>• 1-Click Launchpad for Infinite Vanilla Players (Zero Border Options)<br><i>(Target: Instant Discovery & Free Marketing Hook)</i>"]
        
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

---

## Diagram 2: Dual-Mode Experience (Infinite Vanilla Worlds vs. Bordered Realms)

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

---

## Diagram 3: The 30-Bit Universal Bitmask & $O(1)$ Search Engine

```mermaid
flowchart TD
    UserQuery["Player Custom Query:<br>• Range: ~2,000m (4096 area)<br>• Overworld: Village + Cherry Grove + Ancient City<br>• Nether: Nether Fortress + Warped Forest<br>• Desired Distance: ~500m (Flexible)"] --> T1
    
    subgraph "Tier 1: 30-Bit Mask Filter (Existence in Boundary)"
        T1["Convert Selection to 30-Bit Integer Mask<br>Bitwise OR: (1<<0) | (1<<14) | (1<<2) | (1<<23) | (1<<27)<br>Query Table[mask] for 4096 Boundary"] --> CandPool["Returns Top Candidate Worlds possessing all features in bounds (< 0.01 ms)"]
    end

    subgraph "Tier 2: Continuous Proximity Engine (Ranking & % Match)"
        CandPool --> CenterSolver["Check 81 Precalculated Centers per World:<br>Select the anchor that minimizes feature distances"]
        CenterSolver --> DistDecay["Calculate Soft Proximity Decay Score:<br>• Observed d <= Target D: 100% Score<br>• Observed d > Target D: Score = 1.0 - (d - D) / D"]
        DistDecay --> FinalSort["Rank Candidates by Weighted Match %:<br>1. Seed A: 98% Match (Village @ 180m, Cherry @ 90m, Fortress @ 80m)<br>2. Seed B: 91% Match (Village @ 420m, Cherry @ 310m, Fortress @ 210m)"]
    end

    FinalSort --> UI["Deliver Top 50 Ranked Worlds with Interactive Visual Map (< 1 ms Latency)"]
```

---

## Diagram 4: GPU Trillion-Seed Harvest & Anti-Leak Commercial Model

```mermaid
flowchart TD
    subgraph "GPU CUDA Cluster"
        Seeds["Trillions of Seeds Stream"] --> CUDA["CUDA Warps (≥100M seeds/sec)<br>Check 16 Structures + 14 Biomes across Overworld & Nether"]
        CUDA --> M30["Pack into 30-Bit Integer Mask"]
        M30 --> Drop["Discard Unremarkable Seeds in Registers (0 bytes written)"]
        M30 --> DMA["PCIe DMA Stream Compaction (Interesting seeds only)"]
    end

    subgraph "Host Memory Tracker (<400 MB RAM)"
        DMA --> DirectTable["369 MB Direct Array: Table[2^30]<br>Maintain Top-K Min-Heaps in ~10 ns"]
        DirectTable --> Extraction["End of Sweep: One-time full extraction of ~70k unique seeds"]
        Extraction --> File[("Custom Binary Database: catalog.seedcat (11.2 GB)")]
    end

    subgraph "Commercial Security & Anti-Scraping Layer"
        File --> WebApp["Web Application"]
        WebApp --> PublicAccess["Free Tier: Top 3 Realm God Teasers + 1 Daily Roll"]
        WebApp --> PaidVault["Plus & Realm Master Bundle: Gated Access"]
        PaidVault --> Protection["<b>Anti-Theft Protection:</b><br>1. 1 Purchase = 1 Seed License (Never bulk dumps)<br>2. Max 20 reveals/day (Stops bots & scrapers)<br>3. Visible & Invisible Account Watermarking on maps/PDFs<br>4. Raw binary matrices stay on server behind firewall"]
    end
```

