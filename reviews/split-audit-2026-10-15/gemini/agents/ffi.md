# Audit Report: CFFI Boundary, Native Lifetimes, and Survivor Evidence

**Agent ID:** G-FFI  
**Audit Scope:** CFFI Boundary, Native Batch Lifetimes, GIL Boundaries, Survivor Retention, and Parity Checking  
**Policy / Specification:** `dynamic-envelope-1664-v1` (Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes MC_26_50)  
**Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`  
**Probe Directory:** `reviews/split-audit-2026-10-15/gemini/probes/ffi/`  
**Report Output:** `reviews/split-audit-2026-10-15/gemini/agents/ffi.md`  

---

## 1. Executive Summary

This independent audit evaluated the CFFI boundary, native memory lifecycle management, GIL release boundaries, survivor record evidence completeness, and decision parity between native C evaluation and Python record reconstruction under the `dynamic-envelope-1664-v1` configuration.

### Key Audit Conclusions:
1. **Replay vs. Independent Selection Parity (P1):** The claimed "independent oracle" parity check in `native_batch.py` and `native_records.py` is circular under `dynamic_policy`. When `ReplayProvider` wraps native results, it supplies `dynamic_center` directly to `evaluate_dynamic_seed`, which completely bypasses candidate center generation (`candidate_centers`), deficit sorting, score evaluation, and `PaletteIndex.valid` checking. Python merely replays and accepts the C-selected center. Furthermore, on rejects (`native.nanchors == 0`), `ReplayProvider.dynamic_no_anchor` forces `eligible = []` without inspecting any macro structures.
2. **Retention Receipt Accounting Discrepancy (P2):** In `blueprint_batch.inc:586`, `NBVerdict.anchors` is assigned via `(p->origin ? r->discovery.n : r->nanchors)`. In dynamic mode, `p->origin == 0`, causing `v->anchors` to record `r->nanchors` (1 if qualified, 0 if rejected) instead of `r->discovery.n` (the count of discovered strongholds in the macro window). As a result, `discovered_anchors` in compact retention receipts always equals `retained_anchors`, misreporting discovery yields.
3. **Synthetic Survivor Fixture Omission (P2):** In `blueprint_dynamic.inc:221`, `nb_dynamic_optional` immediately returns 0 when `w->fixture != NULL`. Synthetic survivor fixtures produce completely empty observations for all 5 optional structure categories (`swamp_hut`, `igloo`, `trail_ruins`, `ocean_ruin`, `buried_treasure`). `NBFixture` lacks any fields for optional structure mocking, leaving optional structure retention untested by fixtures.
4. **Native Batch Lifetime & Destructor Leak (P2):** Class `Batch` in `native_batch.py` wraps heap-allocated native batches (`NBBatch *`) allocated via `malloc`/`calloc`. `Batch` does not define `__del__` or register a `weakref.finalize` callback. Dropping a `Batch` instance without an explicit `.close()` or outside a `with` block causes permanent native memory leaks.
5. **Asymmetric Nether Biome Witness State (P3):** Unlike Overworld biomes which maintain `biome_mask` and `first_witness[13]` in `NBAnchor`, Nether biomes have no bitmask or witness indices in `NBAnchor`. Native retention parity checks in Python verify `c.biome_mask == 8191` but perform no native check on Nether biomes.
6. **Verified Contracts (Sound):** Full64 seed identity (`parse_seed` signed 64-bit, `MASK64` unsigned 64-bit conversion, seed string IDs), GIL release (`Py_BEGIN_ALLOW_THREADS` across all CFFI calls), call-local policy isolation (`ffi.memmove` clone per sweep), and Ocean Monument scoring (+30 points for second monument) were thoroughly verified and found mathematically and operationally correct.

---

## 2. Findings Matrix

| Finding ID | Severity | File & Verbatim Line Anchor | Brief Title |
|---|---|---|---|
| **G-FFI-01** | **P1** | [`src/seed_search/realm/blueprint.py:483-485, 520-528`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L483-L485) | Circular Replay Verification in `evaluate_dynamic_seed`: Replay Provider Bypasses Candidate Center Selection |
| **G-FFI-02** | **P2** | [`native/blueprint_batch.inc:586`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L586) | Discovered Anchors Count Discrepancy in Dynamic Retention Receipts (`v->anchors` Records Retained Centers) |
| **G-FFI-03** | **P2** | [`native/blueprint_dynamic.inc:219-222`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L219-L222) | Synthetic Fixtures Truncate Optional Structure Inventories in Dynamic Survivor Evaluation |
| **G-FFI-04** | **P2** | [`src/seed_search/realm/native_batch.py:177-187`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L177-L187) | Absence of Destructor / Finalizer in `Batch` Causes Native Memory Leak on Unhandled Drop |
| **G-FFI-05** | **P3** | [`native/blueprint_batch.h:8-21`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.h#L8-L21) | Asymmetric Nether Biome Witness Representation in `NBAnchor` (Missing Bitmask & Witness Table) |

---

## 3. Detailed Findings and Concrete Reproductions

### G-FFI-01: Circular Replay Verification in `evaluate_dynamic_seed`
- **Severity:** P1 (High)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **File Anchors:**
  - [`src/seed_search/realm/blueprint.py:483-485, 520-528`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L483-L485)
  - [`src/seed_search/realm/native_batch.py:215-224, 280-284, 326`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L215-L224)
  - [`src/seed_search/realm/native_records.py:101-113`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_records.py#L101-L113)
- **Verbatim Anchor:**
  ```python
  # blueprint.py:483-485
  replay_center=getattr(backend,'dynamic_center',None)
  if getattr(backend,'dynamic_no_anchor',False):eligible=[]
  elif replay_center is None:
      ...
  else:eligible=[type('Selected',(),{'center':tuple(replay_center)})()]
  ...
  # blueprint.py:520
  if replay_center is None and eligible:
      palette_index=timed('biome_palette_4y',lambda:PaletteIndex(sampler,cfg['biomes']))
      def center_key(item): ...
      eligible=sorted((item for item in eligible if palette_index.valid(item.center)),key=center_key)
  ```
- **Description & Observable Behavior:**
  The contract documentation in `native_batch.py:4` asserts:
  > *"All discovery/filter/inventory calculations happen in C. Python prepares owned records directly; the replay provider remains an independent oracle."*
  
  Under `dynamic_policy(cfg)`, `build_record(native, ...)` routes directly to `evaluate_dynamic_seed` using `ReplayProvider(native)`. `ReplayProvider` sets `self.dynamic_center = (native.anchors[0].x, native.anchors[0].z)`.
  When `evaluate_dynamic_seed` runs:
  1. It discovers `replay_center` is non-None.
  2. It overrides `eligible = [type('Selected', (), {'center': tuple(replay_center)})()]`.
  3. It skips candidate center generation (`candidate_centers`), deficit sorting, score optimization, and prefix validity (`PaletteIndex.valid`).
  4. It evaluates localized checks only at `replay_center`.
  5. The parity check in `native_batch.py` asserts `a['evaluation_center'] == [c.x, c.z]`, which is guaranteed to succeed because `a['evaluation_center']` was populated directly from `replay_center`.
  6. On rejects (`native.nanchors == 0`), `ReplayProvider.dynamic_no_anchor` forces `eligible = []`, causing Python to confirm the reject without performing any structure scans or center searches.
  7. Furthermore, because C clears `macro[13]` observations upon exit from `nb_eval_dynamic`, `NBResult` only retains structures subsetted to `[c.x-832, c.z-832, c.x+831, c.z+831]`. `ReplayProvider` does not possess macro window data to independently execute candidate selection.
- **Concrete Reproduction Command:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_replay_verification.py
  ```
- **Probe Output:**
  ```text
  C native selected center: (-784, -816)
  Provider dynamic_center: (-784, -816)
  Queries in provider: [('mansion', (-1616, -1648, 47, 15)), ...]
  evaluate_dynamic_seed returned center: [-784, -816]
  Reject provider dynamic_center: None
  Reject provider dynamic_no_anchor: True
  evaluate_dynamic_seed on reject returned anchors: []
  ```
- **Expected vs. Actual Behavior:**
  - *Expected:* The reconstruction and parity check independently derives qualifying candidate centers from macro inventories, verifies optimal representative selection according to `dynamic-envelope-1664-v1` tie-breaking, and asserts that C chose the true policy-optimal center.
  - *Actual:* Python accepts the C-provided center blindly, skipping candidate selection and center ranking entirely.
- **Minimal Unapplied Fix:**
  To provide genuine independent selection verification, `NBResult` must retain macro start coordinates in `r->discovery` and `r->macro_starts`, and `evaluate_dynamic_seed` must run `candidate_centers` and `center_key` against those starts, asserting `oracle_center == [c.x, c.z]`.

---

### G-FFI-02: Discovered Anchors Count Discrepancy in Dynamic Retention Receipts
- **Severity:** P2 (Medium)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **File Anchor:**
  [`native/blueprint_batch.inc:586`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L586)
- **Verbatim Anchor:**
  ```c
  if(p->retention && !r->error) {
      NBVerdict *v=batch->verdicts+i;v->seed=seeds[i];v->anchors=(uint32_t)(p->origin?r->discovery.n:r->nanchors);
      int kept=0,original=r->nanchors;
      ...
  ```
- **Description & Observable Behavior:**
  When survivor retention is enabled, C computes `NBVerdict` for each input seed, storing `v->anchors` and `v->retained`. In origin mode (`p->origin == 1`), `r->discovery.n` represents the count of discovered Strongholds in `[-1024, 1024]`, while `r->nanchors` is 1 (the world origin). Line 586 uses the ternary `p->origin ? r->discovery.n : r->nanchors`.
  However, for `dynamic-envelope-1664-v1`, `p->origin == 0` and `p->dynamic == 1`. As a result, the ternary condition evaluates `r->nanchors`.
  In dynamic mode, `r->nanchors` is set to 1 if a qualifying center was found, and 0 if rejected. Consequently, `v->anchors` is set to 1 or 0, rather than `r->discovery.n` (the number of discovered Strongholds in `[-2000, 2000]`).
  When `retention_receipt()` is generated:
  `receipt['discovered_anchors']` always equals `receipt['retained_anchors']`. Discovered stronghold yields are obscured in compact retention receipts.
- **Concrete Reproduction Command:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_batch_lifetime_receipt.py
  ```
- **Probe Output:**
  ```text
  Native discovery strongholds (r.discovery.n): 2
  Native nanchors: 1
  Verdict anchors (v.anchors): 1
  Verdict retained (v.retained): 1
  Receipt discovered_anchors: 1
  Receipt retained_anchors: 1
  DISCREPANCY CONFIRMED: r.discovery.n (2) != receipt.discovered_anchors (1)
  ```
- **Expected vs. Actual Behavior:**
  - *Expected:* `receipt['discovered_anchors']` reports the total number of candidate anchor features discovered (2 Strongholds in `[-2000, 2000]`), while `retained_anchors` reports the survivors (1 center).
  - *Actual:* `receipt['discovered_anchors']` reports 1, identical to `retained_anchors`.
- **Minimal Unapplied Fix:**
  ```c
  --- a/native/blueprint_batch.inc
  +++ b/native/blueprint_batch.inc
  @@ -586,3 +586,3 @@
  -    NBVerdict *v=batch->verdicts+i;v->seed=seeds[i];v->anchors=(uint32_t)(p->origin?r->discovery.n:r->nanchors);
  +    NBVerdict *v=batch->verdicts+i;v->seed=seeds[i];v->anchors=(uint32_t)((p->origin||p->dynamic)?r->discovery.n:r->nanchors);
  ```

---

### G-FFI-03: Synthetic Fixtures Truncate Optional Structure Inventories in Dynamic Survivor Evaluation
- **Severity:** P2 (Medium)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **File Anchors:**
  - [`native/blueprint_dynamic.inc:219-222`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L219-L222)
  - [`native/blueprint_batch.h:54`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.h#L54)
- **Verbatim Anchor:**
  ```c
  // blueprint_dynamic.inc:219-222
  static int nb_dynamic_optional(NBWorker *w,const int *bounds,int slot,NBObservation *o) {
      o->full=o->evaluated=1;
      if(w->fixture)return 0;
      ...
  ```
- **Description & Observable Behavior:**
  In `blueprint_dynamic.inc:221`, `nb_dynamic_optional` explicitly short-circuits whenever a fixture is present (`if (w->fixture) return 0;`), leaving `o->raw.n = 0` and `o->viable.n = 0`.
  In `native/blueprint_batch.h:54`, `NBFixture` is defined as:
  ```c
  typedef struct NBFixture { int x, z, missing; uint32_t extra_mask; int deficit_depth; } NBFixture;
  ```
  `NBFixture` supports slots 0–12 (mandatory structures) and slots 13–33 (biomes), but provides no mechanism for specifying optional structure counts or positions.
  Consequently, all synthetic survivor fixture runs produce records where `optional_structures` (`swamp_hut`, `igloo`, `trail_ruins`, `ocean_ruin`, `buried_treasure`) have 0 starts, `complete=False`, and `count_is_complete=True`. Synthetic testing cannot validate optional structure bonus retention or Igloo basement logic in survivor records.
- **Concrete Reproduction Command:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_retained_records.py
  ```
- **Probe Output:**
  ```text
  Optional swamp_hut: viable=0, raw=0, complete=False, count_is_complete=True
  Optional igloo: viable=0, raw=0, complete=False, count_is_complete=True
  Optional trail_ruins: viable=0, raw=0, complete=False, count_is_complete=True
  Optional ocean_ruin: viable=0, raw=0, complete=False, count_is_complete=True
  Optional buried_treasure: viable=0, raw=0, complete=False, count_is_complete=True
  ```
- **Expected vs. Actual Behavior:**
  - *Expected:* Synthetic survivor fixtures allow configurable testing of optional structures, or documentation states that optional structure evidence is unexercised in fixture tests.
  - *Actual:* `nb_dynamic_optional` silently returns 0 starts for fixtures, masking optional structure verification in test suites.
- **Minimal Unapplied Fix:**
  Document fixture-only scope explicitly in `native_batch.py`, and extend `NBFixture` with an optional structure bitmask/count if fixture validation of optional bonuses is required.

---

### G-FFI-04: Absence of Destructor / Finalizer in `Batch` Causes Native Memory Leak on Unhandled Drop
- **Severity:** P2 (Medium)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **File Anchor:**
  [`src/seed_search/realm/native_batch.py:177-187`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L177-L187)
- **Verbatim Anchor:**
  ```python
  class Batch:
      def __init__(self,prototype,pointer,seeds,seconds,complete,synthetic,retention="full",max_misses=0):
          self.prototype=prototype;self.pointer=pointer;self.seeds=seeds
          self.native_seconds=seconds;self.complete=complete;self.synthetic=synthetic
          self.retention=retention;self.max_misses=max_misses

      def __enter__(self):return self
      def __exit__(self,*args):self.close()
      def close(self):
          if self.pointer is not None:self.prototype.lib.nb_free(self.pointer);self.pointer=None
  ```
- **Description & Observable Behavior:**
  `Batch` encapsulates `pointer`, which is an unmanaged raw C pointer (`NBBatch *`) allocated on the C heap by `malloc`/`calloc`.
  `Batch` implements `__enter__` and `__exit__`, calling `self.close()`. However, `Batch` defines no `__del__` method and does not register a `weakref.finalize` callback.
  If an exception is raised after `prototype.sweep()` returns but before entering `with batch:`, or if a user drops a `batch` reference without calling `.close()`, Python's cyclic garbage collector frees the Python `Batch` object, but `lib.nb_free(self.pointer)` is never executed. The entire batch allocation (up to 256 MiB of `NBBatch`, results, anchors, and verdicts) leaks into the process space permanently.
- **Concrete Reproduction Command:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_batch_lifetime_receipt.py
  ```
- **Probe Output:**
  ```text
  Batch allocated at pointer: 0x600003194090
  Batch class defines __del__: False
  ```
- **Expected vs. Actual Behavior:**
  - *Expected:* Wrapper classes managing raw C heap pointers implement a destructor (`__del__` or `weakref.finalize`) to free native resources upon garbage collection if `.close()` was omitted.
  - *Actual:* Native buffers leak permanently if `close()` is not explicitly called.
- **Minimal Unapplied Fix:**
  ```python
  --- a/src/seed_search/realm/native_batch.py
  +++ b/src/seed_search/realm/native_batch.py
  @@ -184,2 +184,3 @@
       def __exit__(self,*args):self.close()
  +    def __del__(self):self.close()
       def close(self):
  ```

---

### G-FFI-05: Asymmetric Nether Biome Witness Representation in `NBAnchor`
- **Severity:** P3 (Low)
- **Baseline Commit:** `54b7d631b8bdb481894980a31be16aaa02901b18`
- **File Anchors:**
  - [`native/blueprint_batch.h:8-21`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.h#L8-L21)
  - [`src/seed_search/realm/native_batch.py:295`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L295)
- **Verbatim Anchor:**
  ```c
  // blueprint_batch.h:13,16-17
  unsigned int biome_mask;
  ...
  int first_witness[13];
  int nether_biome_n, *nether_biome_xyz, *nether_biome_ids;
  ```
- **Description & Observable Behavior:**
  In `NBAnchor`, Overworld biomes are compactly tracked using `unsigned int biome_mask` (13 bits) and `int first_witness[13]` (indices of first positive witnesses).
  In contrast, the 5 required Nether biomes in dynamic mode have no bitmask (`nether_biome_mask`) or witness index table in `NBAnchor`. `NBAnchor` only retains raw arrays of 169 coordinates and IDs (`nether_biome_xyz`, `nether_biome_ids`).
  Furthermore, in `native_batch.py:295`:
  `if (two_group_policy(cfg) and (c.fatal_missing or c.biome_mask!=8191)): raise RuntimeError(...)`
  The native retention check checks `c.biome_mask == 8191` (the 13 Overworld biomes), but does not verify Nether biomes natively on `c`. Nether biome presence is verified only downstream during Python record construction via `nether_palette`.
- **Expected vs. Actual Behavior:**
  - *Expected:* Symmetrical tracking of Overworld and Nether biome witnesses, with native bitmask verification in `NBAnchor`.
  - *Actual:* Nether biomes lack bitmask and witness fields on `NBAnchor`, relying on downstream Python dictionary lookups.
- **Minimal Unapplied Fix:**
  Add `unsigned int nether_biome_mask` and `int nether_first_witness[5]` to `NBAnchor`, populate them during `nb_dynamic_nether_evidence`, and verify `c.nether_biome_mask == 31` in `native_batch.py:295`.

---

## 4. Boundary and Lifetime Contract Verification Table

| Boundary Interface | Python Source | C / Native Sink | Data Copy vs View | GIL State | Lifetime Contract | Audit Verdict |
|---|---|---|---|---|---|---|
| **Input Seeds** | `Prototype.sweep(seeds)` | `nb_sweep(values, ...)` | Copy (Python list to `uint64_t[]`) | Released (`Py_BEGIN_ALLOW_THREADS`) | C array owned by CFFI GC during call | **VERIFIED SOUND** |
| **Call Policy** | `Prototype.sweep` | `policy` (`NBPolicy*`) | Copy (`ffi.memmove` from `self.policy`) | Released | C struct owned by CFFI GC per call | **VERIFIED SOUND** |
| **Receipt Buffer** | `batch.retention_receipt()` | `batch.pointer.verdicts` | Zero-copy view (`ffi.buffer`) | Held (Python SHA256) | Valid until `batch.close()` | **VERIFIED SOUND** |
| **Records (Dynamic)** | `batch.records(adapter='direct')` | `ReplayProvider(native)` | Copy (C structs to Python dicts/lists) | Held (Python evaluation) | Records own data after `batch.close()` | **VERIFIED SOUND** |
| **Replay Selection** | `evaluate_dynamic_seed` | `backend.dynamic_center` | Tautological replay | Held | Replays C center; skips candidate search | **DEFECT (G-FFI-01)** |
| **Receipt Anchors** | `nb_run:586` | `v->anchors` | In C verdict buffer | Released | Records `r->nanchors`, not `r->discovery.n` | **DEFECT (G-FFI-02)** |
| **Optional Fixtures**| `nb_dynamic_optional:221`| `NBObservation.viable` | In C worker | Released | Truncates to 0 for fixtures | **DEFECT (G-FFI-03)** |
| **Batch Cleanup** | `Batch.__exit__` | `nb_free(pointer)` | C free | Released | Leaks if `close()` omitted | **DEFECT (G-FFI-04)** |
| **Nether Biome Mask**| `NBAnchor` | `c.biome_mask` | Struct field | N/A | Missing Nether mask & witnesses | **DEFECT (G-FFI-05)** |
| **Full64 Seed Identity**| `parse_seed` & `MASK64` | `ctx->seed` | Bitwise preserved | Released | Signed `int` in Python, `uint64_t` in C | **VERIFIED SOUND** |
| **Ocean Monument** | `dynamic_score` | `nb_dynamic_score_values` | Numerical evaluation | N/A | +30 pts for 2nd monument | **VERIFIED SOUND** |
| **Thread Isolation** | `ThreadPoolExecutor` | `Prototype.sweep` | Local `NBPolicy` per call | Released | Safe under concurrent sweeps | **VERIFIED SOUND** |

---

## 5. Artifact and Probe Verification Summary

All five audit probes have been implemented, verified, and preserved in `reviews/split-audit-2026-10-15/gemini/probes/ffi/`:

1. [`probe_retained_records.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_retained_records.py):
   Validates survivor record schema completeness, receipt hashing, optional structure truncation, qualification, deficit tracking (`['village']`), scoring (422), and parity against full retention.
2. [`probe_concurrency.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_concurrency.py):
   Executes 8 concurrent threads across full and survivor retention on a shared `Prototype` instance without data races or cross-thread policy corruption.
3. [`probe_encoder_concurrency.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_encoder_concurrency.py):
   Tests template compilation and encoder caching under concurrent synthetic and natural sweeps.
4. [`probe_replay_verification.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_replay_verification.py):
   Proves that `evaluate_dynamic_seed` with `ReplayProvider` short-circuits candidate selection, skips `candidate_centers` and `center_key`, and blindly adopts the supplied C decision.
5. [`probe_batch_lifetime_receipt.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_batch_lifetime_receipt.py):
   Confirms context manager closing, verifies the absence of `__del__`, and reproduces the `discovered_anchors` count discrepancy in `NBVerdict`.
