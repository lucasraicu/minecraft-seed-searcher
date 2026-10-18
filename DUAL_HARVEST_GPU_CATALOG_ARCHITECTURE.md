# Dual-Harvest Engine, GPU Acceleration & Catalog Database Architecture

> Superseded public-system proposal: use [PUBLIC_CATALOG_SYSTEM_SPEC.md](PUBLIC_CATALOG_SYSTEM_SPEC.md). The shared personal GPU rejection gate, free-harvest assumptions, authoritative 64-byte record and performance forecasts below are not accepted implementation contracts. Personal policy remains governed by the master blueprint.

**Document Version:** 1.0  
**Target Platform:** Bedrock 1.21.x / Dynamic v3 Search Framework  
**Status:** Historical architecture proposal; superseded for implementation  
**Date:** October 17, 2026  

---

## 1. Executive Summary & Strategy: "Harvest While Searching"

This document defines the unified systems architecture to execute large-scale seed campaigns (36 Billion to 1 Trillion seeds) across CPU and GPU hardware, serving two independent objectives from a single compute pass:

1. **Personal Realm Search:** Isolate Lucas's verified Top-50 Bedrock Realm worlds using the strict 14-floor, 1,250-point additive blueprint and localized center refinement.
2. **Public Seed Catalog:** Simultaneously capture and preserve high-utility consumer seeds across 16 play styles, 14 structure categories, and 256 combinatorial diversity cells without discarding non-conforming candidates.

```
                                 [ Candidate Seed Stream ]
                                             │
                                             ▼
                             [ Phase 1: GPU Screening (CUDA) ]
                             • Mersenne Twister & LCG structure starts
                             • Rejects 99.9% unremarkable in registers
                                             │
                                             ▼ (surviving uint64_t seeds via PCIe DMA)
                             [ Phase 2: CPU Native Engine (C) ]
                                             │
                        ┌────────────────────┴────────────────────┐
                        ▼                                         ▼
            [ Gate A: Personal Realm ]               [ Gate B: Consumer Harvest ]
            • All 14 mandatory floors                • Specialist triggers (≥6 Vil, ≥4 Trial)
            • Full center refinement                 • 16 Play Style archetypes (dot product)
            • Top-50 in-memory min-heap              • 256 Combinatorial diversity cells
                        │                                         │
                        ▼                                         ▼
            [ realm.sqlite Checkpoints ]             [ .sseg Staging Buffer (64-byte) ]
            • Finalist evidence files                             │
            • BDS ground-truth cert                               ▼
                                                     [ DuckDB + Zstd Parquet Lakehouse ]
                                                                  │
                                                                  ▼
                                                     [ In-Memory Roaring Bitmaps + NumPy ]
                                                     • Live Web UI queries (<5 ms)
```

---

## 2. The Dual-Gate Admission Engine (C Native Layer)

The dual-gate operates inside the native C evaluation loop (`native/blueprint_dynamic.inc`). Both branches inspect the exact same observations already recorded in the `NBAnchor` struct (all 18 structure types and 64-bit biome masks), avoiding redundant generation.

### Gate A: Personal Realm Qualification
* **Role:** Preserves the uncompromising standards of `MASTER_SEED_BLUEPRINT.md`.
* **Criteria:** Requires all 14 mandatory Overworld and Nether floors simultaneously (Mansion $\ge 1$, Stronghold $\ge 1$, Fortress $\ge 1$, Bastions $\ge 2$, Ancient Cities $\ge 2$, Villages $\ge 6$, Trials $\ge 8$, etc.).
* **Pass Rate:** $\sim 1$ in $1,000,000$ seeds.
* **Destination:** Surviving seeds undergo exhaustive 16- and 8-block centroid grid refinement, and if their score exceeds the current cutoff, they enter the in-memory min-heap (`Top50Tracker`).

### Gate B: Public Consumer Admission
* **Role:** Captures high-utility worlds that fail personal floors (e.g. a seed with 8 villages, 4 trial chambers, and cherry groves, but 0 mansions).
* **Criteria:** Evaluates three lightweight in-register triggers:
  1. **Specialist Triggers:** Any single structure count exceeding the launch floor (e.g., Villages $\ge 6$, Trials $\ge 4$, Ancient Cities $\ge 2$) OR extreme proximity (Mansion $\le 256\text{m}$, Monument $\le 256\text{m}$, Cherry Grove $\le 256\text{m}$).
  2. **Play Style Archetypes:** Computes integer dot-products against the 16 normalized profile vectors defined in `PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md` (e.g., *Ocean Explorer*, *Trial Adventurer*, *Archaeology*). Seeds landing in the upper tier qualify.
  3. **Combinatorial Diversity:** Evaluates an 8-bit feature tuple (Cherry, Mushroom, Jungle, Snowy, Village, Trial, Ancient City, Monument within $1024\text{m}$). Seeds satisfying under-represented cells qualify.
* **Pass Rate:** $\sim 0.1\%$ to $1.0\%$ of evaluated seeds.
* **Destination:** Writes a packed 64-byte `CatalogRecordV1` into a thread-local staging buffer.
* **Execution Overhead:** Gate B consists of integer comparisons and bitwise operations evaluated in $<25\text{ nanoseconds}$ per seed. It imposes zero measurable drag on personal screening throughput.

---

## 3. GPU Acceleration Pipeline (CUDA / PCIe / CPU Handoff)

Minecraft world generation divides into two distinct mathematical phases. The GPU acceleration pipeline maps these phases to their optimal hardware targets:

| Pipeline Stage | Mathematical Operation | Hardware Target | Throughput Target |
| :--- | :--- | :--- | :--- |
| **Phase 1: Structure Start RNG** | Mersenne Twister (MT19937), LCG, Xoroshiro bitwise PRNG | **GPU (CUDA Warps)** | $\ge 100,000,000\text{ seeds/sec}$ |
| **Phase 2: Climate & Scoring** | 3D Perlin/Voronoi noise octaves, terrain heights, centroid weights | **CPU (C / OpenMP)** | $\sim 50,000\text{–}100,000\text{ candidates/sec}$ |

### 3.1 GPU Compute Kernel (`cuda_screen.cu`)
* Each CUDA thread evaluates a single 64-bit seed.
* Evaluates structure placement chunk grids within the $[-2000, 2000]$ bounding box using ported SIMD routines from `native/filters.inc` (`ss_first3`, `ss_twist`, `ss_temper`).
* Applies raw structure floors (e.g. seed must contain raw starts for $\ge 6$ villages, $\ge 1$ mansion, $\ge 8$ trials).
* Rejection is immediate: failing threads terminate in registers, writing zero bytes to memory.

### 3.2 In-Kernel Stream Compaction
* Surviving threads write their 64-bit seed ID to a block-level shared memory buffer using `atomicAdd` or CUB stream compaction (`cub::DeviceSelect::Flagged`).
* The device buffer accumulates only surviving seeds, reducing data volume by $99.9\%$ to $99.99\%$.

### 3.3 Asynchronous PCIe DMA Streaming (`cudaMemcpyAsync`)
* Host allocates double-buffered pinned RAM (`cudaHostAlloc`) to enable concurrent compute and transfer.
* **Bandwidth Arithmetic:**
  $$\text{Throughput} = 100,000,000\text{ seeds/sec} \times 0.01\%\text{ survival rate} = 10,000\text{ seeds/sec}$$
  $$\text{Data Transferred} = 10,000\text{ seeds/sec} \times 8\text{ bytes} (\text{uint64\_t}) = \mathbf{80\text{ KB/sec}}$$
* An 80 KB/sec transfer rate occupies **$0.0005\%$** of a 16 GB/sec PCIe 4.0 link. The bus remains completely unsaturated, eliminating all host-device transfer bottlenecks.
* Stream 0 executes the compute kernel for Batch $N$, while Stream 1 transfers the survivors of Batch $N-1$ via Direct Memory Access (DMA).

### 3.4 Direct Zero-Copy CPU Handoff
* The pinned host memory buffer is already a contiguous array of 64-bit integers (`const uint64_t *`).
* The CPU host thread passes this buffer directly into `sweep(seeds)` in `src/seed_search/realm/native_batch.py`.
* Zero serialization, zero intermediate disk I/O, zero JSON encoding.
* **CPU Multiplier:** The CPU never evaluates climate noise for unremarkable seeds. 36 Billion seeds screened by GPU yields only 3.6 Million candidates for the CPU, reducing end-to-end CPU runtime from 100 hours to under 40 seconds.

---

## 4. The 4-Layer Database & Storage Specification

```
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Worker Staging Buffer                                         │
│ • Local 4 MB RAM buffer per worker thread                              │
│ • Sequential fwrite() -> fsync() -> atomic rename (.tmp -> .sseg)      │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Shard Coordinator                                              │
│ • SQLite WAL (checkpoints.db)                                          │
│ • Tracks 2^24-seed shard leases, worker IDs, and status at ~10 w/s     │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Primary Columnar Lakehouse                                    │
│ • DuckDB + Zstd Parquet (catalog.parquet)                              │
│ • Asynchronous compaction: .sseg -> Parquet (2.1x compression, 1.08 GB) │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Live Web Query Serving                                        │
│ • NumPy array (2.3 GB RAM) + pyroaring Bitmaps (650 MB RAM)            │
│ • Sub-5 ms interactive query evaluation without database disk I/O      │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Strict 64-Byte Binary Struct (`CatalogRecordV1`)
To ensure cross-platform ABI stability across x86_64, ARM64 (Apple Silicon), and CUDA NVPTX, the record is packed with fixed little-endian alignment:

```c
#pragma pack(push, 1)
typedef struct {
    uint64_t seed;               //  8 bytes: World seed
    int16_t  center_x;           //  2 bytes: Snapped optimal settlement center X
    int16_t  center_z;           //  2 bytes: Snapped optimal settlement center Z
    uint16_t composite_score;    //  2 bytes: Scaled score (0 - 1250)
    uint8_t  archetype_id;       //  1 byte:  Primary archetype classification (0 - 15)
    uint8_t  flags;              //  1 byte:  Bit flags (scenic pairing, cavern status)
    uint64_t biome_mask_64;      //  8 bytes: Bitmask of 64 observed biomes
    uint32_t structure_mask_32;  //  4 bytes: Bitmask of observed structure categories
    uint8_t  counts[18];         // 18 bytes: Feature counts (villages, trials, etc.)
    uint8_t  distances[18];      // 18 bytes: Quantized distance buckets (0 - 255)
} CatalogRecordV1;               // Total: Exactly 64 bytes
#pragma pack(pop)

_Static_assert(sizeof(CatalogRecordV1) == 64, "CatalogRecordV1 must be exactly 64 bytes");
```

### 4.2 Worker Staging (`.sseg` Files)
* Each worker maintains a local 4 MB staging buffer in RAM.
* Surviving Gate B records are appended sequentially.
* At the conclusion of a $2^{24}$-seed shard ($\sim 16,777$ surviving records $\approx 1.07\text{ MB}$):
  1. Writes buffer to `runs/staging/shard_{id}.tmp` via standard C `fwrite()`.
  2. Issues `fsync()`.
  3. Executes atomic POSIX `rename("shard_{id}.tmp", "shard_{id}.sseg")`.
* **Zero Locking:** No concurrent multi-worker file access. No SQLite `SQLITE_BUSY` contention. Writes run at full NVMe sequential bandwidth ($>3\text{ GB/s}$).

### 4.3 Primary Columnar Lakehouse (DuckDB + Zstd Parquet)
* An independent background compaction job monitors `runs/staging/` for completed `.sseg` files.
* Ingests binary structs into DuckDB via zero-copy NumPy memory maps (`np.fromfile(sseg, dtype=catalog_dtype)`).
* Merges records into `catalog.parquet` using dictionary encoding, bit-packing, and Zstandard compression (level 3).
* **Storage Footprint:** 36 Million retained records shrink from 2.30 GB raw uncompressed to **$\sim 1.08\text{ GB}$ on disk**.
* **Zero Daemons:** Embedded DuckDB library operates in-process with no database cluster management.

### 4.4 Shard Coordinator (`checkpoints.db`)
* SQLite in WAL mode is retained exclusively for coordination, not seed payload storage:
  ```sql
  CREATE TABLE shard_checkpoints (
      shard_id INTEGER PRIMARY KEY,
      start_index INTEGER NOT NULL,
      seed_count INTEGER NOT NULL,
      worker_id TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('PENDING', 'LEASED', 'COMPLETED', 'FAILED')),
      lease_time TIMESTAMP,
      completed_time TIMESTAMP,
      surviving_count INTEGER DEFAULT 0,
      sseg_path TEXT
  );
  ```
* Low write frequency ($\sim 10$ commits/sec across a multi-node cluster) ensures 100% crash durability and zero lock conflicts.

### 4.5 Live Web Query Engine (NumPy + pyroaring in RAM)
* Directly querying Parquet from disk requires $40\text{–}80\text{ ms}$ due to metadata parsing, dictionary decoding, and Zstd block decompression.
* For interactive customer search, the web server loads the 1.08 GB Parquet catalog into RAM at startup:
  1. **Numerical/Distance Arrays:** 2.3 GB contiguous NumPy structured array.
  2. **Categorical Bitmaps:** 650 MB of Roaring Bitmaps (`pyroaring`) indexing boolean structure presence and biome occurrences.
* **Query Latency Breakdown:**
  - Multi-attribute bitmap intersection (`mask = bm['cherry'] & bm['village_gte_6']`): **$\sim 1.2\text{ ms}$**
  - NumPy vectorized user-preference dot-product scoring: **$<0.8\text{ ms}$**
  - Native C coordinate verification for Top-25 finalists: **$\sim 2.8\text{ ms}$**
  - **Total API response time:** **$<5.0\text{ ms}$**.
* **Total RAM Required:** $\sim 3.0\text{ GB}$ (negligible on a 64 GB iMac Pro or standard cloud instance).

---

## 5. Phased Graduation Roadmap

To avoid premature optimization and maintain system stability, implementation proceeds in two distinct phases:

### Phase 1: CPU Pilot Validation (Current Focus)
* **Scope:** Follows `PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md` (Phases 0–3).
* **Execution:** Single-machine CPU sweep on the iMac Pro.
* **Storage:** SQLite catalog store capped at **70,384 distinct worlds** (~50 MB).
* **Goal:** Validate public search API contracts, UI sliders, feature extractors, and user demand before investing in multi-node infrastructure.

### Phase 2: Production Scale & GPU Acceleration
* **Scope:** 36-Billion to 1-Trillion seed multi-node campaign.
* **Execution:** Activate CUDA screening kernel (`cuda_screen.cu`) streaming survivors to OpenMP CPU workers.
* **Storage:** Activate `.sseg` worker staging buffers, background DuckDB Parquet compaction, and in-memory `pyroaring` index.
* **Goal:** Execute full-cluster high-throughput production run, simultaneously finalizing Lucas's Top-50 Realm world and populating the 36-Million seed commercial catalog.

