> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Cluster Economics & Scaling Audit: Dynamic Baseline

**Target Policy:** `dynamic-envelope-1664-v1`
**Reference Document:** `MASTER_SEED_BLUEPRINT.md` (Sections 7 & 8)
**Author:** Task 4: Distributed sweep and benchmark runbook
**Status:** Technical Audit & Capacity Planning Guide (Projections Uncertified)

---

## 1. Executive Summary & Core Findings

This audit reconciles the theoretical throughput and yield claims published in `MASTER_SEED_BLUEPRINT.md` against the physical constraints and measured behaviors of the `minecraft-seed-searcher` codebase.

| Metric / Dimension | Blueprint Assumption | Empirical Architecture Limit | Critical Finding / Risk |
| :--- | :---: | :---: | :--- |
| **Executor Scaling** | 210 Dedicated Cores (Single Pool) | **34-Thread Maximum** per scan process | Production executor hard-caps threads at 34 (`cpu_slots = T + 2 <= 36`). Single-node 192/210-thread execution is uncertified and unimplemented. |
| **Single-Core Throughput** | 1,100–1,350 seeds/sec/core | 1,100–1,350 seeds/s **(Kernel Only)** | Rate measures only pure C execution time (`nb_sweep`); excludes Python GIL, record marshaling, and SQLite fsync. |
| **Durable Cluster Rate** | 230,000–280,000 seeds/sec | **Analytical Projection: ~75,000–90,000 seeds/sec** (Unmeasured across 6 nodes) | Linear core extrapolation ignores memory bus saturation, SQLite WAL commit locks, and Python serialization. Must be validated via empirical cluster benchmarks. |
| **Campaign Duration (36B)** | 1.67 Days (~40 Hours) | **Projected ~4.6–5.5 Days (~110–130 Hours)** | Over-optimistic by ~3× due to linear scaling assumptions. Actual duration depends on measured durable throughput. |
| **Disk Storage (Full)** | Omitted | **2.36 Petabytes** (64 KiB / seed) | Full retention is impossible at 36-Billion scale. |
| **Disk Storage (Compact)** | "A few megabytes" | **Policy Baseline: ~1.15 TB** (32 B/seed across cluster) | Policy projection is 32 bytes/seed (`resources.disk_policy`). Analytical detailed model suggests ~20–25 GB unified + WAL/temp buffers. |
| **End Portal Certification** | "portal_room_present=true" | **UNSUPPORTED in Predictor** | Native C engine does not simulate 3D cave carvers or structure template placement; BDS verification required. |
| **Expected Survivor Yield** | 1 in 2.5–3.5 Billion seeds | **Statistically Unverified** | Assumes independent multiplicative probabilities; ignores climate noise spatial auto-correlation. |

---

## 2. Refutation of Linear Cluster Extrapolation

Section 7.3 of `MASTER_SEED_BLUEPRINT.md` presents the following throughput extrapolation:
$$\text{Single Core Rate} = 1,100\text{–}1,350\text{ seeds/sec/core}$$
$$\text{Cluster Throughput} = 210\text{ cores} \times (1,100\text{–}1,350\text{ seeds/sec/core}) \approx \mathbf{230,000\text{–}280,000\text{ seeds/sec}}$$
$$\mathbf{36\text{ Billion Campaign Duration}} = \frac{36 \times 10^9}{250,000 \times 86,400} \approx \mathbf{1.67\text{ Days}} \quad (\sim 40\text{ Hours})$$

This extrapolation is invalid in distributed computing for four fundamental reasons:

### 2.1 The Kernel vs. Durable Rate Disconnect
The rate of $1,100\text{–}1,350\text{ seeds/sec/core}$ measures only $t_{\text{native}}$ in C (`nb_sweep`). It measures the execution of PRNG coordinate checks and Perlin noise octaves in compute registers and local caches.
In a real execution environment:
1. Seeds must be dispatched from Python.
2. CFFI releases the GIL during `nb_sweep`, but reacquires it to return pointers.
3. Python extracts survivor records, builds dictionaries, and calculates SHA-256 digests.
4. Python executes SQLite transactions with `PRAGMA synchronous=FULL`. Every transaction requires an `fsync()` system call to flush WAL pages to persistent non-volatile storage.

Analytical models estimate that durable throughput typically tracks at a fraction of kernel throughput ($R_{\text{durable}} \approx 0.50\text{–}0.65 \times R_{\text{kernel}}$), but this ratio varies by platform and storage controller and must be measured empirically.

### 2.2 Memory Bus and Multi-Core Scaling Contention
Minecraft climate noise relies on Perlin noise octave lookups across 2D/3D grids. While PRNG is register-bound, noise evaluations frequently touch coordinate lookup tables.
- When many worker threads concurrently access memory buses on a multi-socket or multi-CCX server (e.g. AMD EPYC or Intel Xeon), cross-CCX interconnect latency and memory bus traffic can degrade per-core efficiency.
- Linear multi-threaded scaling ($100\%$ efficiency) cannot be assumed; actual scaling efficiency must be determined through controlled benchmarks on the specific target hardware.

### 2.3 The 34-Thread Hard Executor Limit
In `src/seed_search/realm/native_batch.py`:
```python
if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= 34:
    raise ValueError('Native pipeline reserves two of 36 CPU slots for preparation/writing')
```
The codebase explicitly limits a single scan instance to **34 native threads**.
- Even if a machine possesses 192 or 210 logical cores, a single instance can only utilize 34 threads.
- To utilize 210 cores, an operator must run **6 distinct instances** (e.g., 6 instances $\times$ 35 cores, or 6 separate virtual nodes).
- However, running multiple instances on the same host creates heavy I/O contention on the NVMe disk controller during parallel SQLite WAL flushes.

### 2.4 Analytical Cluster Throughput Modeling (Unmeasured Hypothesis)

> [!NOTE]
> The figures below represent **analytical capacity projections** for planning purposes and do **not** reflect measured cluster benchmarks. Actual multi-node throughput must be verified through empirical testing.

Assuming a cluster of 6 dedicated high-core nodes (utilizing 30–32 worker threads per node):

| Node / Host | Allocated Threads | Projected Kernel Rate (Analytical) | Projected Durable Rate (Analytical) | Projected Daily Volume |
| :---: | :---: | :---: | :---: | :---: |
| **Node 1** | 32 | ~24,000 seeds/s | ~14,500 seeds/s | ~1.25 Billion |
| **Node 2** | 32 | ~24,000 seeds/s | ~14,500 seeds/s | ~1.25 Billion |
| **Node 3** | 32 | ~24,000 seeds/s | ~14,500 seeds/s | ~1.25 Billion |
| **Node 4** | 32 | ~24,000 seeds/s | ~14,500 seeds/s | ~1.25 Billion |
| **Node 5** | 32 | ~24,000 seeds/s | ~14,500 seeds/s | ~1.25 Billion |
| **Node 6** | 32 | ~24,000 seeds/s | ~14,500 seeds/s | ~1.25 Billion |
| **Total Cluster** | **192** | **~144,000 seeds/s** | **~87,000 seeds/s** | **~7.52 Billion / Day** |

$$\mathbf{\text{Projected 36-Billion Campaign Duration}} = \frac{36 \times 10^9}{7.52 \times 10^9} \approx \mathbf{4.78\text{ Days}} \quad (\sim 115\text{ Hours})$$

> [!WARNING]
> Planning for a 40-hour campaign with a 210-core cluster is unrealistic. Operations and budget must allocate compute based on empirically demonstrated rates rather than unmeasured linear scaling.

---

## 3. Storage Economics: Full vs. Compact Retention

`DISTRIBUTED_README.md` correctly notes:
> *"Compact output size depends on survivor rate, range receipts, evidence and WAL growth; a multi-billion-input database is not guaranteed to fit in a few megabytes."*

Storage planning requires separating **conservative policy projections** (enforced by `src/seed_search/realm/resources.py`) from **detailed analytical component models** and **measured disk usage**.

### 3.1 Mode A: Full Retention (`--retention full`)
In full retention mode, every single evaluated seed is recorded in `seeds`, `discovery_tasks`, and associated metadata.
- Policy projected rate: **65,536 bytes/seed (64 KiB)**.
- **Projected Storage for 36 Billion seeds:**
  $$\text{Storage} = 36 \times 10^9 \times 65,536\text{ bytes} \approx 2.359 \times 10^{15}\text{ bytes} = \mathbf{2,359\text{ Terabytes}} \quad (\mathbf{2.36\text{ Petabytes}})$$
- **Conclusion:** Completely unviable. Full retention cannot be used for any production run exceeding 100,000 seeds.

### 3.2 Mode B: Compact Survivor Retention (`--retention survivors --max-misses 2`)

#### 1. Conservative Policy Projection (`resources.disk_policy`)
- Default baseline: **32 projected bytes per input**.
- For 36 Billion seeds across the cluster:
  $$\text{Policy Projected Disk} = 36 \times 10^9 \times 32\text{ bytes} = \mathbf{1,152\text{ Gigabytes}} \quad (\mathbf{1.152\text{ Terabytes}})$$
  Across 6 nodes, this projects $\approx 192\text{ GB}$ per node.

#### 2. Detailed Analytical Component Breakdown
In compact retention mode, non-surviving seeds write zero rows to the `seeds` table. Analytical modeling estimates:
1. **Range Lease Rows (`ranges`):**
   - Batch size $B = 4096 \implies \approx 8,789,062\text{ batches}$.
   - Row size: $\approx 80\text{ bytes}$. Total: $\approx \mathbf{703\text{ MB}}$.
2. **Cryptographic Range Receipts (`retention_receipts`):**
   - Stored per batch: JSON receipt + SHA-256 digest $\approx 220\text{ bytes}$.
   - Total: $\approx \mathbf{1.93\text{ GB}}$.
3. **Candidate Records (`candidates`, `variant_tasks`, `inventory_work`):**
   - High-tier survivors ($B=0$ or $B=1$): ~15–50 candidates.
   - Near-misses ($B \le 2$): Filter pass rate modeled at $\approx 0.005\%$.
   - Modeled retained candidates: $36 \times 10^9 \times 0.00005 \approx 1,800,000\text{ rows}$.
   - Encoded payload: $\approx 1.5\text{ KB/row} \implies \approx \mathbf{2.7\text{ GB}}$.
   - Associated tasks: $\approx \mathbf{1.5\text{ GB}}$.
4. **B-Tree Index Overhead & Page Framing:** $\approx \mathbf{4\text{ GB}}$.
5. **WAL and Checkpoint Overhead:**
   - Active WAL per shard: 64–128 MiB.
   - For 60 shards: $60 \times 128\text{ MB} \approx \mathbf{7.68\text{ GB}}$.

$$\mathbf{\text{Total Modeled Database Footprint}} \approx \mathbf{18.5\text{–}25\text{ Gigabytes}}$$

#### 3. Measured Disk Telemetry
- Physical disk usage must be continuously monitored via `disk_status()` in `src/seed_search/realm/resources.py`.
- Shards enforce `free_disk_reserve_bytes` (16 GiB default) and `run_disk_limit_bytes` (128 GiB default per run).

> [!TIP]
> Compact survivor retention achieves massive storage compression over full retention, making the 36-Billion campaign physically feasible on local NVMe SSDs. However, storage must be planned with appropriate headroom: local temporary workspace requires at least **150–200 GB** across all nodes.

---

## 4. Uncertified Engineering Assumptions & Missing Evidence

### 4.1 Missing Evidence: Live End Portal Room Generation
- **The Blueprint Assumption:** Section 7.2 Step 5 states:
  > *"Explicitly verify End Portal Room presence (portal_room_present=true) to protect against Bedrock village/stronghold portal clipping bugs."*
- **The Code Reality:**
  - In `cubiomes-bedrock` and `src/seed_search/backend.py`, stronghold detection calculates only the initial starting stairway chunk coordinate $(X, Z)$.
  - The internal room layout, corridor branching, and portal room placement are generated dynamically at runtime by Minecraft's internal structure generator.
  - In Bedrock Edition, strongholds generated beneath deep oceans, ravines, ancient cities, or trial chambers can suffer from room clipping where the End Portal room fails to generate or is severed by a cave carver.
  - **Verdict:** Automatic portal room verification cannot be performed in native screening. Every candidate passing Stage 1/2 **must** be verified in Stage 5 using Bedrock Dedicated Server (BDS) Docker automation.

### 4.2 Missing Evidence: Joint Probability & Yield Predictions
- **The Blueprint Assumption:** Section 8 states:
  > *"Joint Target Probability: ~1 in 2.5–3.5 Billion seeds... Expected Total Predictor Survivors: ~10–15 High-Tier Seeds."*
- **The Reality:**
  - This yield was derived by multiplying independent probabilities:
    $$P(\text{Target}) = P(\text{Nether Co-Window}) \times P(\text{Outposts}) \times P(\text{Mansion}) \times P(\text{13 Biomes}) \times P(\text{Structures})$$
  - In Minecraft Bedrock world generation, multi-octave Perlin noise is **not independent**. Continentalness, Erosion, Temperature, and Humidity are spatially coupled.
  - A seed that produces cold mountainous biomes is statistically less likely to produce jungle temples or desert pyramids in the same localized radius.
  - **Verdict:** True survivor yield could be lower by an order of magnitude. Shard operators must monitor candidate discovery rates after the first 100 Million seeds to calibrate true empirical yield.

### 4.3 Missing Evidence: 192-Thread Single-Node Execution
- **The Blueprint Assumption:**
  References high-core dedicated servers operating at 192 or 210 threads.
- **The Code Reality:**
  - No benchmark in `runs/` or test in `tests/` has ever executed $>36$ threads.
  - `persist_pipeline` in `native_batch.py` explicitly throws an error for `threads > 34`.
  - Multi-threaded lock contention and scaling on `NBPolicy.results` buffers beyond 36 threads has not been established.

### 4.4 Missing Evidence: Network Filesystem (NFS) Distributed Locking
- If multiple cluster nodes attempt to write to a single centralized NFS/SMB share, SQLite WAL locking will encounter fatal deadlocks or severe I/O delays.
- SQLite WAL mode requires POSIX shared-memory primitives (`shm_open`) and specific `fcntl` lock semantics that are unreliable across network shares.
- **Mandate:** Every cluster node **must** store its active shard database on **local, host-attached NVMe storage**. Merging is strictly an offline batch process using `scripts/merge_runs.py`.

---

## 5. Architectural Recommendations for Distributed Deployment

1. **Partition into 60–100 Distinct Shards:**
   Instead of a few massive shards, divide 36 Billion seeds into shards of **400M–600M seeds each**. Smaller shards limit blast radius upon hardware failure.
2. **Pre-flight Local NVMe Space:**
   Verify $>25\text{ GB}$ of free local disk space per node before launching.
3. **Automate Online Snapshot Syncing:**
   Set up a cron job on worker nodes to execute `sqlite3 <db> ".backup export.sqlite"` every 2 hours and rsync the export to the central coordinator.
4. **Monitor Empirical Yield:**
   After the first completed shards, compute the empirical survivor frequency in the unified aggregate to evaluate whether the Miss Budget ($B \le 2$) requires adjustment.
