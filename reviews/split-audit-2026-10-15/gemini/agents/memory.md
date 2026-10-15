# G-MEM Audit Report: Allocation, Ownership, Concurrency, and Recovery

**Auditor:** G-MEM (Independent Subagent)  
**Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`  
**Specification:** Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes `MC_26_50` / `dynamic-envelope-1664-v1`  
**Toolchain:** macOS Darwin 24.6.0 (x86_64), Apple clang version 17.0.0, Python 3.13.15  
**Probe Directory:** [`reviews/split-audit-2026-10-15/gemini/probes/mem/`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/)  
**Report Output:** [`reviews/split-audit-2026-10-15/gemini/agents/memory.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/agents/memory.md)  

---

## 1. Executive Summary

This independent audit conducted a systematic, code-level and empirical examination of dynamic-envelope memory allocation, ownership contracts, worker reuse across consecutive seeds, concurrency/atomics safety, and Python pipeline in-flight bounds.

Five material findings were identified and verified with deterministic reproductions:
1. **`G-MEM-01` (Severity: P1 / Critical Defect):** Capacity Poisoning in `NBWorker` Reusable Buffers (`dyn_ex_cap`, `dyn_cells_cap`) causing fatal NULL pointer dereference (`SIGSEGV`) when a worker evaluates subsequent seeds after an allocation failure.
2. **`G-MEM-02` (Severity: P2 / Major Violation):** Complete Bypass of Declared Reservation Contract (`max_buffer_bytes`) by dynamic envelope reusable buffers (`dyn_prefix`, `dyn_biome_grid`, `dyn_nether_prefix`, `dyn_nether_grid`, `dyn_ex`, `dyn_ez`, `dyn_cells`) via unchecked direct calls to `malloc()`.
3. **`G-MEM-03` (Severity: P2 / Concurrency Defect):** In-Flight Batch Overflow in `persist_pipeline` (`src/seed_search/realm/native_batch.py`) allowing active concurrent batches holding native memory to reach `inflight + 1` while reporting an artificially bounded count in database telemetry.
4. **`G-MEM-04` (Severity: P3 / Accounting Defect):** Permanent Reservation Counter Poisoning in `nb_alloc` where rejected allocations increment `*w->allocated_bytes` without rollback upon failure.
5. **`G-MEM-05` (Severity: P3 / Leak Defect):** Memory Leak on Asymmetric Reallocation Failure in `dyn_ex` / `dyn_ez`.

Worker-local generator state, mansion cache isolation, chunk index claiming, and post-sweep result compaction were audited and confirmed thread-safe under non-error conditions.

---

## 2. Allocation & Ownership Map

The following table provides the exhaustive map of all heap allocations in the native batch engine and dynamic predictor:

| Structure / Buffer | File & Line Anchor | Allocator | Sizing Expression | Typical / Peak Bytes | Owner & Lifetime | Accounted in `max_buffer_bytes`? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `NBBatch` | `blueprint_batch.inc:554` | `calloc` | `sizeof(NBBatch)` | 40 B | Batch root, freed in `nb_free` | Yes (upfront at `batch.inc:552`) |
| `batch->results` | `blueprint_batch.inc:555` | `calloc` | `count * sizeof(NBResult)` | `count * 168 B` | Batch root, freed in `nb_free` | Yes (upfront at `batch.inc:552`) |
| `batch->verdicts` | `blueprint_batch.inc:557` | `calloc` | `count * sizeof(NBVerdict)` | `count * 16 B` | Batch root, freed in `nb_free` | Yes (upfront at `batch.inc:552`) |
| `w.ctx` (`SeedContext`) | `bridge.c:50` / `batch.inc:569` | `calloc` | `sizeof(SeedContext)` | ~2.5 KiB + tables | Worker-local, freed in `ss_destroy` | No (fixed per-worker overhead) |
| `w.scratch` / `w.flags` | `blueprint_batch.inc:107` | `nb_alloc` | `n * 20 B` | ~1.27 MiB | Worker-local, freed at worker exit | **Yes** (via `nb_alloc`) |
| `r->discovery.xz` | `blueprint_batch.inc:95` | `nb_alloc` | `n * 8 B` | ~16 B - 1 KiB | Result-owned, freed in `nb_clear_points` | **Yes** (via `nb_alloc`) |
| `a->biome_xyz` | `blueprint_batch.inc:228` | `nb_alloc` | `n * 48 B` | ~32.4 KiB | Anchor-owned, freed in `nb_clear_anchor` | **Yes** (via `nb_alloc`) |
| `a->biome_ids` | `blueprint_batch.inc:228` | `nb_alloc` | `n * 16 B` | ~10.8 KiB | Anchor-owned, freed in `nb_clear_anchor` | **Yes** (via `nb_alloc`) |
| `a->nether_biome_xyz` | `blueprint_dynamic.inc:152` | `nb_alloc` | `169 * 12 B` | 2,028 B | Anchor-owned, freed in `nb_clear_anchor` | **Yes** (via `nb_alloc`) |
| `a->nether_biome_ids` | `blueprint_dynamic.inc:153` | `nb_alloc` | `169 * 4 B` | 676 B | Anchor-owned, freed in `nb_clear_anchor` | **Yes** (via `nb_alloc`) |
| `r->anchors` | `blueprint_dynamic.inc:467` | `nb_alloc` | `1 * sizeof(NBAnchor)` | 2,824 B | Result-owned, freed in `nb_clear_result` | **Yes** (via `nb_alloc`) |
| `w->dyn_prefix` | `blueprint_dynamic.inc:78` | **`malloc`** | `23 * 64 * 64 * 4 B` | **376,832 B** (~368 KiB) | Worker-local, freed at worker exit | **NO (BYPASSED)** |
| `w->dyn_biome_grid` | `blueprint_dynamic.inc:82` | **`malloc`** | `4 * 64 * 64 * 4 B` | **65,536 B** (64 KiB) | Worker-local, freed at worker exit | **NO (BYPASSED)** |
| `w->dyn_nether_prefix`| `blueprint_dynamic.inc:123` | **`malloc`** | `5 * 18 * 18 * 4 B` | **6,480 B** (~6.3 KiB) | Worker-local, freed at worker exit | **NO (BYPASSED)** |
| `w->dyn_nether_grid` | `blueprint_dynamic.inc:127` | **`malloc`** | `18 * 18 * 4 B` | **1,296 B** (~1.3 KiB) | Worker-local, freed at worker exit | **NO (BYPASSED)** |
| `w->dyn_ex` / `w->dyn_ez` | `blueprint_dynamic.inc:380` | **`malloc`** | `2 * (total*2+2048)*4 B`| **23,008 B - 100 KiB** | Worker-local, freed at worker exit | **NO (BYPASSED)** |
| `w->dyn_cells` | `blueprint_dynamic.inc:412` | **`malloc`** | `(maxcells+1024) * 24 B`| **76 KiB - 240 MiB** | Worker-local, freed at worker exit | **NO (BYPASSED)** |

---

## 3. Detailed Audit Findings

### `G-MEM-01`: Reusable Worker Dynamic Buffer Capacity Poisoning Leading to Fatal NULL Pointer Dereference (`SIGSEGV`)

- **Severity:** P1 (Critical Defect / Process Crash)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **Component:** Native Dynamic Predictor Worker Lifetime (`native/blueprint_dynamic.inc`, `native/blueprint_batch.inc`)
- **Exact File & Line Anchors:**
  - [`native/blueprint_dynamic.inc:377-383`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L377-L383):
    ```c
    377:     size_t ex_need=(size_t)(total*2+2048)*sizeof(int);
    378:     if(w->dyn_ex_cap<ex_need) {
    379:         free(w->dyn_ex);free(w->dyn_ez);
    380:         w->dyn_ex=malloc(ex_need);w->dyn_ez=malloc(ex_need);
    381:         w->dyn_ex_cap=ex_need;
    382:         if(!w->dyn_ex||!w->dyn_ez){code=-3;goto done;}
    383:     }
    ```
  - [`native/blueprint_dynamic.inc:409-414`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L409-L414):
    ```c
    409:     if(w->dyn_cells_cap<maxcells) {
    410:         free(w->dyn_cells);
    411:         w->dyn_cells_cap=maxcells+1024;
    412:         w->dyn_cells=malloc(w->dyn_cells_cap*sizeof(NBDynamicCell));
    413:         if(!w->dyn_cells){code=-3;goto done;}
    414:     }
    ```
  - [`native/blueprint_batch.inc:580-597`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L580-L597):
    ```c
    580:             for(int i=first;i<end;i++) {
    581:                 w.fixture=fixtures?fixtures+i:NULL;
    582:                 NB_PROFILE_BIND(&w,profiles,i);
    583:                 NBResult *r=batch->results+i;r->input_offset=i;
    584:                 r->error=nb_eval(&w,seeds[i],r);
    ...
    597:             }
    ```

#### Root Cause Analysis
OpenMP threads allocate an `NBWorker w` on their stack and reuse that same worker instance to process a series of seeds in chunks of `NB_WORK_CHUNK` (16).
In `nb_eval_dynamic`:
1. **`dyn_ex` / `dyn_ez`**: Line 381 assigns `w->dyn_ex_cap = ex_need;` *before* checking whether both `w->dyn_ex` and `w->dyn_ez` succeeded. If either `malloc(ex_need)` returns `NULL`, line 382 sets `code = -3` and jumps to `done:`. Worker capacity `w->dyn_ex_cap` is now committed to `ex_need` while one or both pointers are `NULL`.
2. **`dyn_cells`**: Line 411 sets `w->dyn_cells_cap = maxcells + 1024;` *before* `malloc()` is even called. If `malloc` fails, `w->dyn_cells` remains `NULL` while `w->dyn_cells_cap` holds the inflated capacity.
3. **Subsequent Execution on Reused Worker**: When seed `i + 1` runs on the same worker, `nb_eval_dynamic` executes. Because the worker capacity was poisoned to the larger value on seed `i`, `w->dyn_ex_cap < ex_need` and `w->dyn_cells_cap < maxcells` evaluate to `false`. The allocation block is skipped. At lines 384-385 (`ex[nx++] = -1168;`) and line 455 (`cells[ncells++] = ...;`), the worker attempts to write into a `NULL` pointer, immediately triggering a segmentation fault (`SIGSEGV`).

#### Empirical Reproduction & Evidence
A deterministic crash probe was constructed:
- Probe source: [`reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_poisoning.c`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_poisoning.c)
- Subprocess runner: [`reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py)
- Command:
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py
  ```
- Subprocess environment: `RLIMIT_CORE` set to `(0, 0)` (core dumps disabled).
- Observed Output:
  - **Test Case 1 (Target malloc #31 - `dyn_ex` fails on Seed 0):**
    `Seed 0 result: code=-3, dyn_ex=0x0, dyn_ez=0x7fd102009200, dyn_ex_cap=11504`
    `Exit code: -11 (SIGSEGV)`
  - **Test Case 2 (Target malloc #32 - `dyn_ez` fails on Seed 0):**
    `Seed 0 result: code=-3, dyn_ex=0x7fe2ad809200, dyn_ez=0x0, dyn_ex_cap=11504`
    `Exit code: -11 (SIGSEGV)`
  - **Test Case 3 (Target malloc #33 - `dyn_cells` fails on Seed 0):**
    `Seed 0 result: code=-3, dyn_cells=0x0, dyn_cells_cap=3169`
    `Exit code: -11 (SIGSEGV)`

#### Expected vs Actual Behavior
- **Expected:** An allocation failure on seed N sets `r->error = -3`, preserves worker invariants or resets capacity to 0, and permits the worker to process seed N+1 cleanly or reattempt allocation without crashing.
- **Actual:** Worker capacity fields are poisoned with non-zero values while pointers remain NULL. Processing seed N+1 immediately crashes the host process with `SIGSEGV` (exit code -11 / 139).

#### Minimal Proposed Fix
In [`native/blueprint_dynamic.inc`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc):
```diff
--- a/native/blueprint_dynamic.inc
+++ b/native/blueprint_dynamic.inc
@@ -376,11 +376,14 @@ static int nb_eval_dynamic(NBWorker *w,uint64_t seed,NBResult *r) {
     total+=r->discovery.n*2;
     size_t ex_need=(size_t)(total*2+2048)*sizeof(int);
     if(w->dyn_ex_cap<ex_need) {
+        int *new_ex = malloc(ex_need);
+        int *new_ez = malloc(ex_need);
+        if(!new_ex || !new_ez) {
+            free(new_ex); free(new_ez);
+            code = -3; goto done;
+        }
         free(w->dyn_ex);free(w->dyn_ez);
-        w->dyn_ex=malloc(ex_need);w->dyn_ez=malloc(ex_need);
+        w->dyn_ex=new_ex; w->dyn_ez=new_ez;
         w->dyn_ex_cap=ex_need;
-        if(!w->dyn_ex||!w->dyn_ez){code=-3;goto done;}
     }
     ex=w->dyn_ex; ez=w->dyn_ez;
@@ -407,9 +410,11 @@ static int nb_eval_dynamic(NBWorker *w,uint64_t seed,NBResult *r) {
     size_t maxcells=(size_t)(nx-1)*(size_t)(nz-1);
     if(maxcells>10000000){code=-3;goto done;}
     if(w->dyn_cells_cap<maxcells) {
+        size_t new_cap = maxcells + 1024;
+        void *new_cells = malloc(new_cap * sizeof(NBDynamicCell));
+        if(!new_cells){code=-3;goto done;}
         free(w->dyn_cells);
-        w->dyn_cells_cap=maxcells+1024;
-        w->dyn_cells=malloc(w->dyn_cells_cap*sizeof(NBDynamicCell));
-        if(!w->dyn_cells){code=-3;goto done;}
+        w->dyn_cells = new_cells;
+        w->dyn_cells_cap = new_cap;
     }
```
**Verification of Fix:** Implemented and compiled in [`reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_fixed.c`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_fixed.c). Executing all 3 failure cases against the fixed function resulted in Seed 0 returning `-3` and Seed 1 succeeding with `0` (exit code 0, no crash, no leaks).

---

### `G-MEM-02`: Dynamic Reusable Buffers Completely Bypass Declared Reservation Contract (`max_buffer_bytes`)

- **Severity:** P2 (Major Contract & Accounting Violation)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **Component:** Native Memory Reservation Accounting (`native/blueprint_dynamic.inc`, `native/blueprint_batch.inc`)
- **Exact File & Line Anchors:**
  - [`native/blueprint_dynamic.inc:78, 82`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L78):
    ```c
    78:         w->dyn_prefix=malloc(23*side*side*sizeof(int));
    ...
    82:         w->dyn_biome_grid=malloc(4*side*side*sizeof(int));
    ```
  - [`native/blueprint_dynamic.inc:123, 127`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L123):
    ```c
    123:         w->dyn_nether_prefix=malloc(5*18*18*sizeof(int));
    ...
    127:         w->dyn_nether_grid=malloc(18*18*sizeof(int));
    ```
  - [`native/blueprint_dynamic.inc:380`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L380):
    ```c
    380:         w->dyn_ex=malloc(ex_need);w->dyn_ez=malloc(ex_need);
    ```
  - [`native/blueprint_dynamic.inc:412`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L412):
    ```c
    412:         w->dyn_cells=malloc(w->dyn_cells_cap*sizeof(NBDynamicCell));
    ```
  - Contrast with [`native/blueprint_batch.inc:66-74`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L66-L74):
    ```c
    66: static void *nb_alloc(NBWorker *w,size_t bytes,int zero) {
    ...
    72:     if(previous>w->p->max_buffer_bytes || bytes>w->p->max_buffer_bytes-previous)return NULL;
    73:     return zero?calloc(1,bytes):malloc(bytes);
    74: }
    ```

#### Root Cause Analysis
The declared blueprint architecture enforces a hard reservation cap `max_buffer_bytes` (`src/seed_search/realm/native_batch.py:69` sets `256 << 20`, 256 MiB). In `blueprint_batch.inc:107`, worker scratch arrays call `nb_alloc(w, ..., 0)` which atomically captures `*w->allocated_bytes` and returns `NULL` if `max_buffer_bytes` is exceeded.
In contrast, every single dynamic envelope working buffer in `native/blueprint_dynamic.inc` calls raw `malloc()` directly. These buffers are never charged to `*w->allocated_bytes` and are never checked against `max_buffer_bytes`.

#### Empirical Measurement
Using the trace harness [`reviews/split-audit-2026-10-15/gemini/probes/mem/trace_allocs.c`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/trace_allocs.c) and [`reviews/split-audit-2026-10-15/gemini/probes/mem/sum_allocs.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/sum_allocs.py), exact allocations per worker were measured:
- `dyn_prefix`: 376,832 bytes
- `dyn_biome_grid`: 65,536 bytes
- `dyn_nether_prefix`: 6,480 bytes
- `dyn_nether_grid`: 1,296 bytes
- `dyn_ex` + `dyn_ez`: 23,008 bytes
- `dyn_cells`: 76,056 bytes
- **Total unmonitored raw malloc per worker:** **549,208 bytes (~536.3 KiB)**.
- **For 16 OpenMP threads:** **8,787,328 bytes (~8.38 MiB)**.
In dense batches where `maxcells` approaches 250,000, `dyn_cells` allocates 6,000,000 bytes per worker (96 MiB across 16 threads), all escaping `max_buffer_bytes`.

Furthermore, in [`reviews/split-audit-2026-10-15/gemini/probes/mem/probe_buffer_reservation.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_buffer_reservation.py), setting `max_buffer_bytes = 1,780,000` bytes allows the sweep to succeed while actual live worker heap reaches **2,317,368 bytes**, exceeding the configured reservation limit by **537,368 bytes (30.2%)** without any error or detection.

#### Expected vs Actual Behavior
- **Expected:** `max_buffer_bytes` strictly bounds all owned heap memory (outputs + worker scratch) allocated during the execution of a batch.
- **Actual:** Dynamic envelope worker buffers bypass `nb_alloc`, causing actual heap consumption to exceed `max_buffer_bytes`.

#### Minimal Proposed Fix
Charge worker dynamic buffer capacity against `max_buffer_bytes` upon creation or reserve a fixed per-thread buffer budget during batch initialization (`blueprint_batch.inc:552`):
```c
uint64_t worker_cap = (uint64_t)threads * (p->dynamic ? DYNAMIC_WORKER_RESERVATION : 0);
uint64_t allocated_bytes = sizeof(NBBatch) + count * sizeof(NBResult) + worker_cap;
if (p->max_buffer_bytes < allocated_bytes) return NULL;
```

---

### `G-MEM-03`: In-Flight Pipeline Queue Allows Active Batches to Exceed Configured `inflight` Limit by 1

- **Severity:** P2 (Concurrency & Memory Cap Violation)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **Component:** Python Native Pipeline Concurrency (`src/seed_search/realm/native_batch.py`)
- **Exact File & Line Anchors:**
  - [`src/seed_search/realm/native_batch.py:501-504`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L501-L504):
    ```python
    501:             while len(pending)<inflight and submit(store):pass
    502:             while pending:
    503:                 first,end,attempt,future,queued,native_future=pending.popleft()
    504:                 while len(pending)<inflight and submit(store):pass
    ```
  - and lines 521-522:
    ```python
    521:                 del prepared
    522:                 native_futures.discard(native_future)
    ```
  - and line 532:
    ```python
    532:                 while len(pending)<inflight and submit(store):pass
    ```

#### Root Cause Analysis
At line 501, `pending` is filled with `inflight` batches (e.g. 2). At line 503, `pending.popleft()` pops the first batch so the main thread can resolve its futures, prepare database rows, and write to SQLite (`lines 505-520`).
Immediately at line 504, the loop checks `while len(pending) < inflight and submit(store): pass`. Because `len(pending)` is now `inflight - 1`, `submit(store)` is called immediately, submitting another batch to the ThreadPool.
However, the popped batch has not completed. It still holds its CFFI native memory buffer (`pointer`), ThreadPool futures, and Python prepared rows.
Consequently, during lines 505-521, there are:
- `inflight` batches queued in `pending`
- 1 popped batch currently being processed
- **Total active batches in flight:** `inflight + 1`.

Furthermore, line 487 updates telemetry as:
```python
max_pending = max(max_pending, len(pending))
```
Because `len(pending)` never exceeds `inflight`, the database checkpoint state at line 553 (`'max_outstanding_batches': max_pending`) reports `2` when `inflight=2`, masking the fact that 3 batches were concurrently outstanding.

#### Empirical Reproduction
Probe: [`reviews/split-audit-2026-10-15/gemini/probes/mem/probe_inflight_bounds.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_inflight_bounds.py)
Command:
```bash
./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/mem/probe_inflight_bounds.py
```
Observed Results:
- When configured for `inflight = 2`:
  - `len(pending)`: 2
  - `len(native_futures)`: 3
  - Actual active batches: **3**
  - Telemetry reported `max_pending`: **2**
- When configured for `inflight = 3`:
  - `len(pending)`: 3
  - `len(native_futures)`: 4
  - Actual active batches: **4**
  - Telemetry reported `max_pending`: **3**

#### Expected vs Actual Behavior
- **Expected:** Setting `inflight = K` guarantees that at most `K` batches are concurrently outstanding across computation, preparation, and storage.
- **Actual:** `K + 1` batches are concurrently outstanding, consuming up to 50% more native and prepared memory than budgeted.

#### Minimal Proposed Fix
Remove the premature refill at line 504. Batches should only be submitted once the completed batch has finished writing and released its native resources (which is already executed at line 532):
```diff
--- a/src/seed_search/realm/native_batch.py
+++ b/src/seed_search/realm/native_batch.py
@@ -501,7 +501,6 @@ def persist_pipeline(prototype,run,count,*,run_key=0,threads=30,batch_size=1024
             while len(pending)<inflight and submit(store):pass
             while pending:
                 first,end,attempt,future,queued,native_future=pending.popleft()
-                while len(pending)<inflight and submit(store):pass
                 before=time.perf_counter()
```

---

### `G-MEM-04`: Monotonic Reservation Counter `allocated_bytes` Poisoned on Allocation Check Rejection

- **Severity:** P3 (Accounting & Denial of Service Defect)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **Component:** Native Batch Memory Allocator (`native/blueprint_batch.inc:66-74`)
- **Exact File & Line Anchor:**
  [`native/blueprint_batch.inc:66-74`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L66-L74):
  ```c
  static void *nb_alloc(NBWorker *w,size_t bytes,int zero) {
      uint64_t previous;
  #ifdef _OPENMP
      #pragma omp atomic capture
  #endif
      {previous=*w->allocated_bytes;*w->allocated_bytes+=bytes;}
      if(previous>w->p->max_buffer_bytes || bytes>w->p->max_buffer_bytes-previous)return NULL;
      return zero?calloc(1,bytes):malloc(bytes);
  }
  ```

#### Root Cause Analysis
`*w->allocated_bytes` is atomically incremented by `bytes` before the check against `w->p->max_buffer_bytes`. If the check fails, `nb_alloc` returns `NULL`, but does not decrement `*w->allocated_bytes`.
If a single thread requests an oversized allocation that exceeds the remaining budget, the rejected bytes remain permanently added to the counter. As a result, subsequent allocations by other threads that would have fit in the remaining budget will also fail.

#### Minimal Proposed Fix
Atomically subtract `bytes` from `*w->allocated_bytes` if the reservation check fails:
```diff
--- a/native/blueprint_batch.inc
+++ b/native/blueprint_batch.inc
@@ -69,5 +69,12 @@ static void *nb_alloc(NBWorker *w,size_t bytes,int zero) {
     #pragma omp atomic capture
 #endif
     {previous=*w->allocated_bytes;*w->allocated_bytes+=bytes;}
-    if(previous>w->p->max_buffer_bytes || bytes>w->p->max_buffer_bytes-previous)return NULL;
+    if(previous>w->p->max_buffer_bytes || bytes>w->p->max_buffer_bytes-previous) {
+#ifdef _OPENMP
+        #pragma omp atomic
+#endif
+        *w->allocated_bytes -= bytes;
+        return NULL;
+    }
     return zero?calloc(1,bytes):malloc(bytes);
 }
```

---

### `G-MEM-05`: Asymmetric Allocation Failure Memory Leak in `dyn_ex` / `dyn_ez`

- **Severity:** P3 (Resource Leak Defect)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **Component:** Native Dynamic Worker Memory Management (`native/blueprint_dynamic.inc:378-382`)
- **Exact File & Line Anchor:**
  [`native/blueprint_dynamic.inc:378-382`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L378-L382):
  ```c
  378:     if(w->dyn_ex_cap<ex_need) {
  379:         free(w->dyn_ex);free(w->dyn_ez);
  380:         w->dyn_ex=malloc(ex_need);w->dyn_ez=malloc(ex_need);
  381:         w->dyn_ex_cap=ex_need;
  382:         if(!w->dyn_ex||!w->dyn_ez){code=-3;goto done;}
  383:     }
  ```

#### Root Cause Analysis
If `w->dyn_ex = malloc(ex_need);` succeeds, but `w->dyn_ez = malloc(ex_need);` fails, `w->dyn_ex` is non-NULL while `w->dyn_ez` is NULL. Line 382 jumps to `done:`. At `done:`, neither `w->dyn_ex` nor `w->dyn_ez` is freed. If the worker encounters another failure or if `w->dyn_ex` is reassigned, the successfully allocated buffer is leaked.
Demonstrated in [`reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py) (Target malloc #32), where `dyn_ex` was allocated at `0x7fe2ad809200` and orphaned.

#### Minimal Proposed Fix
Addressed directly by the fix for `G-MEM-01` (allocating into temporary pointers and freeing any non-NULL temporary if either fails).

---

## 4. Concurrency, Worker State, and Thread Safety Audit

In accordance with task instructions, the following shared and worker-local states were audited:

### 1. Worker-Local Generator State (`ctx`)
- **Finding:** Verified Clean (None Verified).
- **Evidence:** In `native/blueprint_batch.inc:569`, each OpenMP thread creates its own independent context (`w.ctx = ss_create(0)`). Each worker owns its generators (`overworld`, `nether`) and noise structures. At line 599, `ss_destroy(w.ctx)` cleans up worker-local state. No generator buffers or spline tables cross thread boundaries.

### 2. Viability Cache State (`mansion_cache`)
- **Finding:** Verified Clean (None Verified).
- **Evidence:** In `native/blueprint_batch.inc:50`, `mansion_cache` is a member of `NBWorker` and is allocated per thread. Lines 318 and 356 explicitly execute `w->mansion_cache_n = 0;` at the start of evaluating every seed. No viability decisions leak across seeds or threads.

### 3. Dynamic Work Distribution & Index Claiming
- **Finding:** Verified Clean (None Verified).
- **Evidence:** In `native/blueprint_batch.inc:572-578`, chunk distribution uses:
  ```c
  #ifdef _OPENMP
      #pragma omp atomic capture
  #endif
      {first=next;next+=NB_WORK_CHUNK;}
  ```
  Claimed ranges `[first, end)` are strictly disjoint across threads. Each thread writes only to `batch->results[i]` and `batch->verdicts[i]`. There is zero write contention or racing on result structures during the parallel sweep.

### 4. Post-Sweep Result Compaction & Cleanup
- **Finding:** Verified Clean under non-error conditions (None Verified).
- **Evidence:** Lines 604-616 run serially on the master thread after all OpenMP workers have joined at the end of the parallel block. In survivor retention mode, qualified results are packed into `batch->results[kept]`, and vacant slots are zeroed out with `memset(r, 0, sizeof(*r))`. `nb_free` loops from 0 to `batch->count` and safely ignores zeroed slots.

### 5. Policy Sharing
- **Finding:** Verified Clean (None Verified).
- **Evidence:** `NBPolicy` is passed as `const NBPolicy *p`. Workers only read from the policy struct. In Python, `Prototype.sweep` (`src/seed_search/realm/native_batch.py:148`) creates a call-local copy of `NBPolicy` via `memmove` before invoking native code, ensuring that concurrent sweeps in different Python threads do not mutate shared policy state.

---

## 5. Artifact and Probe Index

All audit probes and test harnesses are located in [`reviews/split-audit-2026-10-15/gemini/probes/mem/`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/):

1. **[`test_capacity_poisoning.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py)**:
   Deterministic Python subprocess runner with `RLIMIT_CORE=0`. Reproduces fatal `SIGSEGV` for `dyn_ex`, `dyn_ez`, and `dyn_cells` poisoning.
2. **[`probe_capacity_poisoning.c`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_poisoning.c)**:
   C fault-injection harness intercepting target malloc calls and demonstrating worker capacity corruption.
3. **[`probe_capacity_fixed.c`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_fixed.c)**:
   C verification harness demonstrating clean recovery and 100% test pass on Seed 1 under the minimal proposed fix.
4. **[`probe_buffer_reservation.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_buffer_reservation.py)**:
   Python probe testing live heap bytes against `max_buffer_bytes` and measuring dynamic allocations bypassing `nb_alloc`.
5. **[`probe_inflight_bounds.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/probe_inflight_bounds.py)**:
   Python probe verifying in-flight queue overflow (`inflight + 1`) and diagnostic reporting in `persist_pipeline`.
6. **[`trace_allocs.c`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/trace_allocs.c)**:
   Allocation tracer mapping exact call indices and sizes during a dynamic seed evaluation.
7. **[`sum_allocs.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/mem/sum_allocs.py)**:
   Calculates monitored `nb_alloc` vs unmonitored raw `malloc` bytes.
