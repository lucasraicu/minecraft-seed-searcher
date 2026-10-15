> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Distributed Seed Sweep & Validation Runbook: Dynamic Baseline

**Target Policy:** `dynamic-envelope-1664-v1`
**Deployment Envelope:** Overworld $1664 \times 1664$ (sliding center $C_X, C_Z \in [-1168, 1168]$), Nether $832 \times 832$ ($C_X/8, C_Z/8 \in [-146, 146]$)
**Search Space:** Master Macro Envelope $4000 \times 4000$ Overworld, $1124 \times 1124$ Nether
**Target Game Version:** Minecraft Bedrock Edition 1.21+ (`MC_26_50` predictor, live BDS 1.26.52.3)
**Repository Working Directory:** `/Users/lucasraicu/Downloads/minecraft-seed-searcher`
**Integrator correction:** Scan uses `--config`, with `search.run_key` in that YAML. The allocator now writes a validated per-shard policy file; it does not emit unsupported scan flags.

**Status:** Operational Runbook & Distributed Execution Guide (Projections Uncertified)

---

## 1. System Overview & Architectural Preflight

The Bedrock seed searcher implements a high-throughput, multi-stage screening pipeline for Minecraft Bedrock Edition realms. In the active dynamic baseline (`dynamic-envelope-1664-v1`), candidates are screened across a $4000 \times 4000$ Overworld macro-envelope ($[-2000, 2000]$) and an $1124 \times 1124$ Nether preflight envelope ($[-562, 562]$).

A fast native C engine (`cubiomes-bedrock` + `native/blueprint_batch.inc` + `native/blueprint_dynamic.inc`) executes pure-PRNG coordinate checks, 6D climate noise evaluations, 2D event-slab intersection solving, centroid magnet pulling, chunk-grid snapping (multiples of 16 Overworld, 8 Nether), and 13-Overworld + 5-Nether biome palette verification. Surviving candidates and their range receipts are streamed into an ACID-compliant SQLite WAL database.

```
                           [ 64-bit Seed Stream: seed_from_index(i, run_key) ]
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1A: NATIVE KERNEL (C / OpenMP)                                                                │
│ • Step 1: Nether PRNG + Co-Window (Fortress ≥ 2, Bastion ≥ 2 within 832×832)                       │
│ • Step 2: Outpost (≥ 2) & Trial Chamber (≥ 7) PRNG slot validation                                 │
│ • Step 3: Woodland Mansion 6D noise (Humidity, Continentalness, Temperature evaluation)             │
│ • Step 4: Secondary structure viability (Mansion, Monument ≥ 1, Outpost ≥ 2, Bastion, Fortress)     │
│ • Step 5: 2D Event-Slab Interior Solver + Centroid Magnet Pull (weights capped at 3)               │
│ • Step 6: Chunk-Grid Snapping: Overworld mod 16, Nether mod 8, Clamped to Safe Zone S_safe          │
│ • Step 7: 13-Biome Diversity (4-Y Lattice) + 5-Biome Nether Palette                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼ [Compact Survivors & Range Receipts]
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ PYTHON RUNTIME PIPELINE (seed_search.realm.native_batch.persist_pipeline)                            │
│ • Thread 1: Native CFFI caller (releases Python GIL during nb_sweep)                                │
│ • Thread 2: Record preparer & encoder (fast_records / prepare_retained_range)                       │
│ • Thread 3: SQLite WAL writer (PRAGMA synchronous=FULL, batch size B)                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ DURABLE STORAGE (RealmStore: runs/<node>/realm.sqlite)                                              │
│ • ranges (start, end, status='complete', digest)                                                    │
│ • retention_receipts (start, end, receipt, digest)                                                  │
│ • candidates (id, idx, seed, qualification='PREDICTED', result)                                     │
│ • variant_tasks, discovery_tasks, inventory_work                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Environment & Compilation Prerequisites

### 2.1 Hardware and Runtime Requirements
- **Python Version:** Pinned to **Python 3.13** (validated: `3.13.15`).
- **Dependencies:** Strictly pinned in `requirements.lock` (`cffi==1.17.1`, `numpy==2.1.2`, `pyyaml==6.0.2`, `pytest==8.3.3`, etc.).
- **C Compiler:** C11 compliant compiler (`clang` or `gcc`).
- **OpenMP Runtime:**
  - **macOS:** `libomp` via Homebrew (`brew --prefix libomp` $\to$ `/opt/homebrew/opt/libomp` or `/usr/local/opt/libomp`). Requires explicit `ARCHFLAGS="-arch $(uname -m)"`.
  - **Linux:** Distribution-packaged LLVM/GCC OpenMP (`libomp-dev` or `libgomp1`), providing `include/omp.h` and `libomp.so`. Note: `/usr` is not a universal location across distributions.

### 2.2 Compilation Procedures

The repository supports two compilation pathways. Production sweeps **must** use the explicit, isolated audited build pathway (`scripts/build_blueprint_batch.py`) to generate an immutable `identity.json` alongside the compiled shared object.

#### Method A: Packaged Extension (Serial Fallback / Quick Smoke Testing)
```sh
# Builds src/seed_search/_native.abi3.so and src/seed_search/_blueprint_batch.abi3.so
.venv/bin/python native/build.py
.venv/bin/python native/blueprint_build.py
```
> [!WARNING]
> By default, `native/build.py` produces a single-threaded serial extension unless `SEED_SEARCH_OPENMP_PREFIX` and `ARCHFLAGS` are explicitly exported in the environment. Serial execution is ~10–16× slower on multi-core hosts.

#### Method B: Audited Isolated Extension (Production & Multi-Core Nodes)
Execute the isolated builder to write the compiled library and full cryptographic provenance to a dedicated directory:

```sh
# macOS (with Homebrew libomp installed):
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/node-native-1664 \
  --openmp-prefix "$(brew --prefix libomp)" \
  --work-chunk 16 \
  --stronghold-after 4 \
  --experiment-order 0

# Linux (adjust OpenMP prefix to your system path, e.g. /usr or /usr/lib/llvm-18):
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/node-native-1664 \
  --openmp-prefix /usr \
  --work-chunk 16 \
  --stronghold-after 4 \
  --experiment-order 0
```

#### Compilation Flag Audit
| Flag | Value | Architectural Purpose |
| :--- | :---: | :--- |
| `-O3` | Enabled | Maximum compiler optimization for noise octaves and PRNG inner loops. |
| `-std=c11` | C11 | Conformance to modern C standard. |
| `-fwrapv` | Enabled | Guarantees two's-complement signed 64-bit integer overflow wrapping. |
| `-DNB_WORK_CHUNK` | `16` (or `64`) | Chunk size for OpenMP atomic dynamic scheduling. Use `16` for $<64$ cores, `64` for $\ge 64$ cores. |
| `-DNB_EXPERIMENT_ORDER` | `0` | Standard audited structure filter order. |
| `-DNB_STRONGHOLD_AFTER` | `4` | Stronghold evaluated after 4 structure families (matches `dynamic-envelope-1664-v1`). |
| `-Xpreprocessor -fopenmp` | Platform-specific | Enables OpenMP threading. macOS requires `-Xpreprocessor` to avoid Apple Clang rejecting `-fopenmp`. |
| `-DSS_OPENMP_LIBRARY` | Absolute path | Hardcodes runtime `.dylib`/`.so` path into binary to prevent dynamic loader hijack. |

> [!IMPORTANT]
> The builder produces `runs/node-native-1664/identity.json` containing SHA-256 hashes of all C headers, sources, and compiler configurations. This identity is validated by `Prototype.__init__` and `merge_runs.py`. If source code is modified, the extension **must** be recompiled.

---

## 3. Distributed Sharding & Finite-Shard Execution

### 3.1 The Shared Run Key Invariant
In `seed_search`, the 64-bit seed corresponding to index $i$ is generated by:
$$\text{seed} = \text{seed\_from\_index}(i, K)$$
where $K = \text{search.run\_key}$. Internally, this evaluates:
$$\text{mix64}\big((i + K) \pmod{2^{64}}\big)$$

> [!CAUTION]
> **Varying `run_key` across nodes does NOT partition the search space.**
> If Node 1 runs with $K=0$ on $[0, 10^6)$ and Node 2 runs with $K=10^6$ on $[0, 10^6)$, both nodes evaluate the **exact same set of 1,000,000 seeds**.
> **RULE:** Every machine in a distributed sweep **MUST use the exact same `search.run_key` (default `'0'`)** and be assigned **mutually disjoint index intervals** $[S_k, S_k + C_k)$.

### 3.2 Exact Coverage Accounting
1. **Half-Open Intervals:** Shards are partitioned into half-open index ranges:
   $$\mathcal{I}_k = [S_k, S_k + C_k) \quad \text{such that} \quad \mathcal{I}_j \cap \mathcal{I}_k = \emptyset \quad \forall j \neq k$$
2. **Boundary Limits:** $0 \le S_k < S_k + C_k \le 2^{64}$.
3. **Pre-Allocation Registry:** Shard assignments must be recorded centrally before launching to prevent overlapping work.
4. **Range Receipts:** In compact survivor retention mode (`--retention survivors`), discarded non-qualifying seeds do **not** write individual rows to the `seeds` table (saving $>99.9\%$ disk space). Instead, every committed batch records:
   - A range row in `ranges` with `status='complete'` and `digest`.
   - A cryptographic range receipt in `retention_receipts` containing:
     $$\text{input\_decisions\_sha256} = \text{SHA256}\big(\text{NBVerdict}[0 \dots B-1]\big)$$
     alongside `inputs`, `retained_inputs`, `retained_anchors`, and `discovered_anchors`.
5. **Coverage Calculation:** `scripts/merge_runs.py` computes total coverage by computing the formal interval union:
   $$\text{Coverage} = \sum_{[a, b) \in \bigcup \text{ranges}} (b - a)$$

### 3.3 Finite Shard Launch Commands

#### Critical Configuration Preflight (Bug Notice & Resolution)
> [!WARNING]
> **Config Validation Blocker:** Running CLI commands with `--config config/realm.yaml` or `--config config/realm_1664.yaml` currently fails with:
> `ValueError: Centroid weights differ from the blueprint`
> This occurs because the static YAML files in the repository omit the 11-structure `centroid_weights` map and 5-family `biomes.nether_required` list introduced by Revision 4.1 in `src/seed_search/realm/config.py`.
>
> **Resolution:** When `--config` is omitted from the CLI, `src/seed_search/realm/cli.py` automatically loads `dynamic_blueprint_config()`, which conforms to Revision 4.1. Alternatively, supply an updated configuration file that includes all Revision 4.1 keys.

#### Correct CLI Production Commands (Disjoint Shards)

```sh
# Ensure virtual environment is active
source .venv/bin/activate

# ==============================================================================
# NODE 1: Shard [0, 5,000,000) - 5 Million Seeds
# ==============================================================================
python -m seed_search --config config/realm_1664.yaml scan \
  --executor native \
  --native-build runs/node-native-1664 \
  --native-threads 16 \
  --native-batch-size 4096 \
  --retention survivors \
  --max-misses 2 \
  --prediction-scale \
  --start-index 0 \
  --count 5000000 \
  --output runs/shard-001

# ==============================================================================
# NODE 2: Shard [5,000,000, 10,000,000) - 5 Million Seeds (Disjoint, Same Run Key)
# ==============================================================================
python -m seed_search --config config/realm_1664.yaml scan \
  --executor native \
  --native-build runs/node-native-1664 \
  --native-threads 16 \
  --native-batch-size 4096 \
  --retention survivors \
  --max-misses 2 \
  --prediction-scale \
  --start-index 5000000 \
  --count 5000000 \
  --output runs/shard-002

# ==============================================================================
# NODE 3: Shard [10,000,000, 15,000,000) - 5 Million Seeds
# ==============================================================================
python -m seed_search --config config/realm_1664.yaml scan \
  --executor native \
  --native-build runs/node-native-1664 \
  --native-threads 16 \
  --native-batch-size 4096 \
  --retention survivors \
  --max-misses 2 \
  --prediction-scale \
  --start-index 10000000 \
  --count 5000000 \
  --output runs/shard-003
```

#### CLI Flag Requirements & Validation Matrix
| Flag | Setting | Requirement & Enforcement |
| :--- | :---: | :--- |
| `--config` | `config/realm_1664.yaml` | Explicit validated policy YAML. |
| `search.run_key` in YAML | `0` (or shared uint64 decimal key) | Must match across all nodes. No scan `--run-key` flag exists. |
| `--executor` | `native` | Mandatory for dynamic baseline CFFI pipeline. `python` executor does not support compact retention. |
| `--native-build` | `runs/node-native-1664` | Path to directory containing audited compiled extension and `identity.json`. |
| `--native-threads` | `1 <= T <= 34` | Number of OpenMP worker threads. **Strict hard ceiling: 34 threads** (2 threads reserved for prep and writing). |
| `--native-batch-size` | `1 <= B <= 16384` | Bounded batch size. Default `4096`. High-core machines may use `8192`. |
| `--retention` | `survivors` | Mandatory for large sweeps. Saves only predicted survivors and $B \le 2$ near-misses. |
| `--max-misses` | `2` | Must strictly match `search.max_misses: 2` in the resolved policy. |
| `--prediction-scale` | Explicit flag | Required for `--count > 1000`. The CLI automatically writes `compatibility.json` to the output folder. |
| `--start-index` | $S_k$ | Starting index of finite shard. Must be within $[0, 2^{64})$. |
| `--count` | $C_k$ | Total seeds in shard. Must satisfy $S_k + C_k \le 2^{64}$. |
| `--output` | `runs/<shard-id>` | Dedicated directory. Must not collide with another running or completed scan. |

---

## 4. Checkpoint, Recovery & Snapshot Governance

### 4.1 SQLite Storage Engine & Concurrency Control
- **Journal Mode:** `PRAGMA journal_mode=WAL` (Write-Ahead Logging). Concurrency model supports concurrent readers alongside a single connection-owned writer thread.
- **Synchronous Mode:** `PRAGMA synchronous=FULL`. Every transaction commit fsyncs the WAL file, guaranteeing zero data loss or partial writes upon power failure.
- **Cache & Buffer Bounds:**
  - `PRAGMA cache_size=-131072` (128 MiB page cache).
  - `PRAGMA wal_autocheckpoint=16384` (64 MiB checkpoint interval).
  - `PRAGMA journal_size_limit=134217728` (128 MiB WAL boundary).
- **Process Concurrency Protection:** Every scan acquires an advisory non-blocking OS lock on `.realm-scan.lock` using `fcntl.flock(LOCK_EX | LOCK_NB)`. If a secondary process attempts to open the same run, it aborts immediately with `ValueError("Another Realm scanner owns this run")`.

### 4.2 Crash Recovery & Resumption
Each shard maintains range leases in the `ranges` table:
```sql
CREATE TABLE ranges(
    start TEXT PRIMARY KEY,
    end TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'in_progress', 'retry', 'complete'
    worker TEXT,
    attempts INTEGER NOT NULL DEFAULT 1,
    digest TEXT
);
```

- **Lease Invalidation:** If a node crashes, loses power, or is killed (`SIGINT` / `SIGTERM`), any uncommitted batch left in status `'in_progress'` is orphaned.
- **Automatic Recovery:** Upon resuming, `store.recover_assignments()` executes:
  ```sql
  UPDATE ranges SET status='retry', worker=NULL WHERE status='in_progress';
  ```
  Orphaned ranges are safely returned to the dispatch queue and re-evaluated.
- **Resume Invocation:**
  ```sh
  python -m seed_search resume \
    --run runs/shard-001 \
    --native-threads 16 \
    --native-batch-size 4096 \
    --prediction-scale
  ```
  Resume preserves the original frozen `identity`, configuration, and start/count boundaries. Completed ranges are skipped; only uncompleted seeds are evaluated.

### 4.3 Safe Snapshot Transfer Protocol
> [!CAUTION]
> **DO NOT copy `realm.sqlite` directly while a scan is active.**
> In SQLite WAL mode, newly committed transactions reside in `realm.sqlite-wal`. Copying only `realm.sqlite` or copying while a write is occurring produces a corrupted, torn, or incomplete database.

#### Standard Online Snapshot (While Node is Actively Running)
Use SQLite's native online backup API, which acquires an internal read-lock and produces a consistent point-in-time snapshot:
```sh
# On the scanning node:
sqlite3 runs/shard-001/realm.sqlite ".backup runs/shard-001/export.sqlite"

# Transfer the clean snapshot to the aggregation host:
scp user@node-01:~/minecraft-seed-searcher/runs/shard-001/export.sqlite ./shards/shard-001.sqlite
```

#### Cold Offline Snapshot (After Node Halts)
Only after the scan process has completely exited, verified by `status` showing `ranges` with zero `in_progress` batches:
```sh
# Verify process has exited, then checkpoint WAL into main database:
sqlite3 runs/shard-001/realm.sqlite "PRAGMA wal_checkpoint(TRUNCATE);"
scp user@node-01:~/minecraft-seed-searcher/runs/shard-001/realm.sqlite ./shards/shard-001.sqlite
```

---

## 5. Merging Runs & Read-Only Aggregate Restrictions

### 5.1 Merging Disjoint Shards
The merge tool `scripts/merge_runs.py` consolidates multiple independent Realm databases into a unified read-only leaderboard.

```sh
.venv/bin/python scripts/merge_runs.py \
  --inputs ./shards/shard-001.sqlite ./shards/shard-002.sqlite ./shards/shard-003.sqlite \
  --output runs/master-unified
```

### 5.2 Mandatory Identity Verifications
Before merging, `scripts/merge_runs.py` strictly validates the following invariants:
1. **Source Policy Identity:** `signature['policy']` (SHA-256 of `semantic_identity(config)`) must match identically across all shards.
2. **Seed Domain & Sequence:** `signature['sequence']` must be `'permutation'`, and `signature['run_key']` must match identically.
3. **Native Engine Source Identity:** `signature['native']` must match:
   - Identical SHA-256 hashes for all `.py`, `.c`, `.h`, `.inc`, and `.json` files in `record_computation_identity`.
   - Identical `policy_sha256` (hash of C `NBPolicy` memory buffer).
   - Identical `record_adapter_sha256` and `record_sources_sha256`.
   - Identical `stronghold_after` filter position.
4. **Record Conflict Rejection:** In default `strict=True` mode, if two shards contain the same candidate ID or observation ID with differing payload contents, `merge_runs` **aborts immediately** with `ValueError('Found incompatible records')`.
5. **Coverage Calculation:** `merge_runs` aggregates all completed ranges, calculates their formal union via `union_intervals()`, and records `total_seeds_scanned`.

### 5.3 Read-Only Aggregate Contract & Prohibitions
The output database contains:
```sql
INSERT INTO meta VALUES ('aggregate_contract', 'aggregate-leaderboard-v1');
```

> [!CAUTION]
> **STRICT DOWNSTREAM PROHIBITIONS ON AGGREGATES:**
> An aggregate database is **NOT** a resumable Realm checkpoint. Original source databases must be retained indefinitely.
>
> 1. **DO NOT pass the aggregate to `resume`:** `RealmStore(run, resume=True)` detects `aggregate_contract` and raises:
>    `ValueError: Read-only aggregate is not a resumable Realm checkpoint; use the original source run`
> 2. **DO NOT pass the aggregate to downstream stages:** Commands requiring original owning checkpoints will fail:
>    - `python -m seed_search terrain --run runs/master-unified` (Forbidden)
>    - `python -m seed_search verify-terrain --run runs/master-unified` (Forbidden)
>    - `python -m seed_search verify-realm --run runs/master-unified` (Forbidden)
>    - `python -m seed_search verify-biomes --run runs/master-unified` (Forbidden)
> 3. **DO NOT point the Web Server to the aggregate:** `python -m seed_search.web.server` relies on active run selection and mutate operations. Downstream verification must be performed against the **original shard** that discovered the candidate.

---

## 6. Machine Tuning Protocol ($\le 50,000$ Inputs)

### 6.1 The Tuning Script Bug & Resolution
In the existing repository, `scripts/tune_machine.py` line 14 imports:
```python
from seed_search.realm.config import marine_baseline_blueprint_config
```
This hardcodes `marine_baseline_blueprint_config()` (`screening_revision: origin-fixed-2048-two-group-marine-v3`), where `stronghold_after` is 3. Running `tune_machine.py` against an extension built for `dynamic-envelope-1664-v1` (`stronghold_after=4`) causes `Prototype.__init__` to fail with:
`ValueError: Native Stronghold placement differs from the resolved filter order`

To tune for the dynamic baseline without editing production code:
1. When running standalone tuning, pass the dynamic configuration via a dedicated runner or use the standalone reference validator provided in this runbook.
2. In accordance with task constraints, **do not modify `scripts/tune_machine.py` in-place**.

### 6.2 Tuning Constraints & Execution Bounds
- **Input Cap:** Tuning trials are strictly capped at $1 \le N \le 50,000$ seeds (enforced by `tune_machine.py`). Recommended trial volume: **30,000 inputs**.
- **Time Budget Cap:** 900 seconds (15 minutes). If cumulative benchmark time exceeds 900s, tuning raises `RuntimeError('Tuning budget exhausted; no recommendation adopted')`.
- **Thread Grid:** Dynamically selected based on detected logical cores $C$:
  $$\mathcal{T} = \Big\{ \lfloor C/2 \rfloor,\; \lfloor 0.75 C \rfloor,\; C-4,\; C-2,\; C \Big\} \cap [1, 34]$$
  *(Always capped at 34 threads max).*
- **Batch Grid:** $\mathcal{B} = [4096, 8192]$ (or $[8192, 16384]$ on systems with $\ge 64$ cores).
- **Counterbalanced Trials:** 3 complete passes across the candidate grid $(\mathcal{T} \times \mathcal{B})$:
  - Trial 0: Forward grid order
  - Trial 1: Reversed grid order
  - Trial 2: Forward grid order
- **Selection Metric:** Median native-kernel rate:
  $$R_{\text{median}}(T, B) = \text{median}\big(R_0(T, B), R_1(T, B), R_2(T, B)\big)$$

> [!IMPORTANT]
> `tune_machine.py` measures **native-kernel rate only** (`batch.native_seconds`). It does **not** measure durable end-to-end rate. Settings identified by `tune_machine.py` are candidates only; they must be validated through the 5-pair held-out durable validation protocol before production adoption.

---

## 7. Final Validation Protocol: 5 Counterbalanced Held-Out Pairs

To evaluate candidate settings $(T^*, B^*)$ against default production baseline settings ($T_0=16, B_0=4096$), execute five counterbalanced pairs of 100,000 held-out inputs each.

### 7.1 Protocol Architecture
- **Held-Out Intervals:** Evaluated on seeds strictly disjoint from the tuning range $[0, 50,000)$:
  - Pair 1: $[50,000, 150,000)$ — 100,000 seeds
  - Pair 2: $[150,000, 250,000)$ — 100,000 seeds
  - Pair 3: $[250,000, 350,000)$ — 100,000 seeds
  - Pair 4: $[350,000, 450,000)$ — 100,000 seeds
  - Pair 5: $[450,000, 550,000)$ — 100,000 seeds
- **Counterbalanced Arm Ordering:** Alternating AB / BA order to neutralize OS disk caching, page cache priming, thermal throttling, and CPU frequency governor warm-up:
  - **Pair 1:** Control ($T_0, B_0$) $\longrightarrow$ Selected ($T^*, B^*$)
  - **Pair 2:** Selected ($T^*, B^*$) $\longrightarrow$ Control ($T_0, B_0$)
  - **Pair 3:** Control ($T_0, B_0$) $\longrightarrow$ Selected ($T^*, B^*$)
  - **Pair 4:** Selected ($T^*, B^*$) $\longrightarrow$ Control ($T_0, B_0$)
  - **Pair 5:** Control ($T_0, B_0$) $\longrightarrow$ Selected ($T^*, B^*$)

### 7.2 Budget & Time Reconciliation

> [!NOTE]
> The rates ($11,000\text{–}14,000\text{ seeds/sec}$) and runtimes ($\sim 85\text{ seconds}$) below are **analytical modeling projections** for planning purposes, not guaranteed benchmark measurements. Actual durable throughput must be recorded directly from live run telemetry during the validation protocol.

- Total evaluations: 10 runs $\times$ 100,000 inputs = 1,000,000 total evaluations.
- Projected durable rate (analytical): $11,000\text{–}14,000\text{ seeds/sec}$.
- Projected duration per 100,000-seed run: $\approx 7.1\text{–}9.1\text{ seconds}$.
- Projected cumulative execution time: $\approx 10 \times 8.5\text{ s} \approx \mathbf{85\text{ seconds}}$ ($\sim 1.4\text{ minutes}$).
- Allocation within existing budget: Consumes $<10\%$ of the allowed **15–20 minute budget**, leaving ample headroom for database integrity verification.

### 7.3 Required Metrics to Record per Run
For each run $i \in \{1 \dots 10\}$:
1. `wall_seconds`: High-precision monotonic elapsed time.
2. `durable_seeds_per_second`: $\frac{100,000}{\text{wall\_seconds}}$.
3. `native_kernel_seconds`: Cumulative C execution time ($\sum \text{batch.native\_seconds}$).
4. `sql_writer_seconds`: Time spent inside SQLite transactions and fsync.
5. `peak_rss_bytes`: Monitored via `process_tree_resources()`.
6. `storage_bytes`: Sum of `realm.sqlite` + `realm.sqlite-wal`.
7. `candidate_count`: Total qualifying survivor records.
8. `decision_digest`: Cryptographic hash of range receipts (`input_decisions_sha256`).

---

## 8. Semantic Parity Verification Protocol

Faster settings (different thread counts, batch sizes, work chunk flags, or compiler optimizations) must **never** alter search semantics or candidate qualification.

### 8.1 Acceptance Criteria (Zero Semantic Drift)
1. **Decision Digest Identity:** For every held-out range $[S_k, S_k + 100,000)$, the range receipt SHA-256 digest produced by the Control Arm must be bit-for-bit identical to the digest produced by the Selected Arm:
   $$\text{Digest}_{\text{Control}}(\mathcal{I}_k) \equiv \text{Digest}_{\text{Selected}}(\mathcal{I}_k)$$
2. **Candidate Identity & Set Parity:** The set of surviving candidates must be identical:
   $$\mathcal{C}_{\text{Control}} = \mathcal{C}_{\text{Selected}}$$
3. **Coordinate & Dynamic Center Parity:** For every candidate, the chosen dynamic center $(C_X, C_Z)$ must match exactly:
   $$(C_X, C_Z)_{\text{Control}} = (C_X, C_Z)_{\text{Selected}}$$
4. **Deficit Tier & Score Invariance:** Every candidate must have identical deficit tier, unmet requirement mask, and `smart_score`.
5. **Replay Verification:** A sample of 10 random survivors from the validation runs must be evaluated through the Python reference oracle `evaluate_dynamic_seed()`, confirming $100\%$ decision agreement.

---

## 9. Hardware Limits, Disk Estimates & Capacity Preflight

### 9.1 Thread and CPU Limits
- **34-Thread Hard Production Ceiling:** In `seed_search.realm.native_batch.persist_pipeline`:
  ```python
  if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= 34:
      raise ValueError('Native pipeline reserves two of 36 CPU slots for preparation/writing')
  ```
  The pipeline reserves 1 thread for native C execution, 1 thread for Python record preparation, and 1 thread for SQLite writing. Total CPU slot reservation is $T + 2 \le 36$.
- **High-Core Servers ($>36$ Cores):** Running on a 64-core, 128-core, or 192-core host **cannot** utilize $>34$ threads in a single instance.
- **Multi-Instance Deployment:** On high-core hosts, run multiple independent shards in parallel (e.g. 2 instances of 30 threads each on a 64-core machine), each with its own disjoint index interval and distinct output directory.

### 9.2 Memory Management & RSS Ceilings
- Monitored continuously via `process_tree_resources()` (sampling `ps -axo pid=,ppid=,rss=,pcpu=`).
- Configured in `config/realm.yaml`:
  - `memory_target_gib: 25` (Soft throttling target)
  - `memory_ceiling_gib: 30` (Hard ceiling; halts dispatch and checkpoints)
  - `docker_reserve_gib: 8` (Reserved for downstream BDS Docker containers)
- If RSS exceeds ceiling, `persist_pipeline` halts dispatch, drains in-flight work, and exits cleanly with checkpoint retained.

### 9.3 Disk Footprint & Workspace Capacity Preflight
Disk usage is validated prior to every batch commit via `disk_status()` in `src/seed_search/realm/resources.py`.

#### Storage Estimation Formulas

##### Mode 1: Full Retention (`--retention full`)
Every evaluated seed writes full JSON payloads to `seeds` and `discovery_tasks`.
- Conservative policy baseline (`resources.disk_policy`): **65,536 bytes/seed (64 KiB)**.
- Shard of $10,000,000$ seeds:
  $$\text{Storage} = 10^7 \times 65,536\text{ B} \approx \mathbf{655\text{ GB}}$$
- Exceeds the default `run_disk_limit_bytes` (128 GiB). **Unviable for large campaigns.**

##### Mode 2: Compact Survivor Retention (`--retention survivors --max-misses 2`)
Only qualifying survivors ($B \le 2$) and range receipts are written.

1. **Conservative Policy Baseline (`resources.disk_policy`):**
   - Base projected rate: **32 projected bytes per input**.
   - Shard of $10,000,000$ seeds:
     $$\text{Policy Projected Storage} = 10^7 \times 32\text{ B} = \mathbf{320\text{ MB}}$$

2. **Detailed Analytical Component Breakdown:**
   - Range receipts ($2,442$ batches $\times 128\text{ B}$): $\approx 312\text{ KB}$
   - Range lease table ($2,442$ rows $\times 64\text{ B}$): $\approx 156\text{ KB}$
   - Discarded seeds in `seeds` table: **0 bytes** (zero rows stored)
   - Expected survivors ($10^7 \times 0.005\%$ near-misses $\approx 500$ rows $\times 1.5\text{ KB}$): $\approx 750\text{ KB}$
   - SQLite metadata, schema, and indexes: $\approx 2\text{ MB}$
   - Active WAL buffer: $\approx 64\text{–}128\text{ MB}$
   - **Total Modeled Component Footprint per 10M Shard:** $\mathbf{\approx 70\text{–}135\text{ MB}}$.

3. **Measured Disk Telemetry:**
   - Active physical disk usage is tracked continuously via `disk_status()` in `src/seed_search/realm/resources.py`.

#### Physical Disk Preflight Checks
Before launching a shard of size $C$, ensure:
1. `free_disk_space > free_disk_reserve_bytes + projected_growth` (requires at least **16 GiB free disk space** by default).
2. Projected shard size $< \text{run\_disk\_limit\_bytes}$ (default **128 GiB**).
If free disk space drops below 16 GiB, `disk_status()` raises `WorkspaceCapacityError` and immediately suspends the scan.

---

## 10. Audit of Unsupported Throughput & Yield Assumptions

The engineering projections in `MASTER_SEED_BLUEPRINT.md` contain several unverified extrapolations that must be formally flagged:

### 10.1 Refutation of Linear Cluster Extrapolation
- **Blueprint Claim:**
  > *"Distributed Cluster Performance (210 Dedicated CPU Cores): Cluster Throughput = 210 cores × (1,100–1,350 seeds/sec/core) ≈ 230,000–280,000 seeds/sec... 36 Billion Seed Campaign Duration ≈ 1.67 Days (~40 Hours)."*
- **Engineering Reality:**
  1. **Amortized Single-Core Kernel vs Durable Multi-Core:** The rate of 1,100–1,350 seeds/sec/core is a native-kernel timing without Python IPC, memory bus saturation, SQLite transaction management, or WAL fsync.
  2. **Thread Scaling Non-Linearity:** On multi-core CPUs, interconnect latency and memory bus traffic can reduce multi-threaded scaling efficiency; linear scaling cannot be assumed and must be benchmarked directly on target hardware.
  3. **Amdahl's Law & Python Serialization:** In `persist_pipeline`, record preparation and SQLite WAL commits run through Python. Even with multi-threading, GIL acquisition during CFFI buffer decoding limits durable single-node throughput to $\approx 12,000\text{–}18,000\text{ seeds/sec}$, regardless of core count.
  4. **The 34-Thread Executor Limit:** The production executor cannot allocate 210 threads in a single process. Running six 34-thread nodes across a cluster is modeled analytically at $\approx 6 \times 14,000 \approx \mathbf{84,000\text{ seeds/sec}}$, projecting $\approx \mathbf{5\text{ days}}$ for 36 billion seeds (not 40 hours); actual throughput must be confirmed via live multi-node benchmark telemetry.
  5. **Network Filesystem Hazard:** If cluster nodes write to a shared NFS/SMB volume, SQLite WAL locking will encounter high latency, lock contention, or filesystem corruption. **Each node MUST write to local NVMe storage.**

### 10.2 Refutation of Automatic Portal Room Certification
- **Blueprint Claim:**
  > *"Confirm live structure generation... Explicitly verify End Portal Room presence (portal_room_present=true) to protect against Bedrock village/stronghold portal clipping bugs."*
- **Engineering Reality:**
  - Neither `cubiomes-bedrock` nor the native C engine simulates Bedrock cave carvers or piece-by-piece structure template generation.
  - End Portal rooms can be overwritten by underground ravines, dripstone mega-caves, or trial chambers.
  - **No seed can be certified as having an intact portal room based on predictor evidence.** The current headless surface provider does not inspect portal rooms. Additional verification tooling or appropriately scoped manual evidence is required.

### 10.3 Yield Probability Unverifiability
- **Blueprint Claim:**
  > *"Joint Target Probability: ~1 in 2.5–3.5 Billion seeds... Expected Total Predictor Survivors: ~10–15 High-Tier Seeds."*
- **Engineering Reality:**
  - This yield assumes independent feature probabilities. In Minecraft world generation, climate noise parameters (temperature, humidity, continentalness, erosion, weirdness) exhibit strong spatial auto-correlation.
  - True empirical yield cannot be mathematically certified until a multi-billion seed sample has been completed and verified.

---

## 11. Step-by-Step Operator Checklist

Follow this checklist for executing any production shard:

```
[ ] STEP 1: Verify Host Platform & Python Version
    python3 --version  # Must be Python 3.13.x
    uname -m           # Record architecture (x86_64 or arm64)

[ ] STEP 2: Verify OpenMP Runtime & Compiler
    # macOS: brew --prefix libomp
    # Linux: test -f /usr/include/omp.h

[ ] STEP 3: Compile Audited Native Extension
    .venv/bin/python scripts/build_blueprint_batch.py \
      --output runs/node-native-1664 \
      --openmp-prefix <PREFIX> \
      --work-chunk 16 \
      --stronghold-after 4
    # Verify runs/node-native-1664/identity.json exists and openmp is true

[ ] STEP 4: Run Machine Tuning (Max 50,000 Seeds)
    # Record optimal threads (<= 34) and batch size (4096 or 8192)

[ ] STEP 5: Run 5 Counterbalanced Held-Out Validation Pairs
    # Confirm 100% semantic parity, identical decision digests, and durable throughput

[ ] STEP 6: Pre-flight Disk & Allocate Disjoint Shard
    # Confirm > 16 GiB free on local NVMe disk
    # Register disjoint interval [S, S + C) with central coordinator

[ ] STEP 7: Launch Finite Shard
    python -m seed_search --config config/realm_1664.yaml scan \
      --executor native \
      --native-build runs/node-native-1664 \
      --native-threads <T*> \
      --native-batch-size <B*> \
      --retention survivors \
      --max-misses 2 \
      --prediction-scale \
      --start-index <S> \
      --count <C> \
      --output runs/<shard-id>

[ ] STEP 8: Export Clean SQLite Snapshot
    sqlite3 runs/<shard-id>/realm.sqlite ".backup runs/<shard-id>/export.sqlite"

[ ] STEP 9: Merge Shard Snapshots on Central Coordinator
    .venv/bin/python scripts/merge_runs.py \
      --inputs ./shards/*.sqlite \
      --output runs/master-unified

[ ] STEP 10: Retain Original Shard Checkpoints
    # DO NOT delete original shard directories.
    # Downstream BDS verification MUST target the original discovering shard.
```
