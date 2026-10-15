# Execution and Reproduction Commands

This document records the exact reproduction and validation commands for the Gemini independent audit (`dynamic-envelope-1664-v1`, baseline `54b7d631b8bdb481894980a31be16aaa02901b18`).

All commands must be run from the repository root: `/Users/lucasraicu/Downloads/minecraft-seed-searcher`.
Runtime Python: `./.venv/bin/python`
Compiler: `Apple clang version 17.0.0 (clang-1700.6.4.2)`

---

## 1. Baseline Test Suite Verification

Run the full existing test suite:
```bash
./.venv/bin/pytest -v
```

Run targeted pipeline and retention tests:
```bash
./.venv/bin/pytest tests/test_native_retention.py tests/test_native_throughput.py -v
```

---

## 2. Geometry and Selection Probes (G-GEO)

Run the master G-GEO verification suite:
```bash
./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/run_all_probes.py
```

Run individual probes:
- **Boundary, Lattice & Snapping Invariance:**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_boundaries_lattice.py
  ```
- **Equivalence Cell Biome & Mandatory Invariance:**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_cell_invariance.py
  ```
- **Optional Structure Boundary Drift (G-GEO-01):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_optional_selection_drift.py
  ```
- **Raw Preflight & Union Bounds Correctness:**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_preflight_union_bounds.py
  ```
- **Scoring Parity & Leaderboard Ranking Order:**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_scoring_leaderboard.py
  ```
- **Centroid Arithmetic & Rational Snapping Quantization:**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_centroid_quantization.py
  ```

---

## 3. Memory, Ownership, and Recovery Probes (G-MEM)

- **Worker Dynamic Buffer Capacity Poisoning SIGSEGV Crash (G-MEM-01):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/mem/test_capacity_poisoning.py
  ```
- **Direct Standalone Malloc Fault Injection (G-MEM-01):**
  ```bash
  clang -O2 -I native -I vendor/cubiomes-bedrock reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_poisoning.c vendor/cubiomes-bedrock/{noise,biomes,layers,biomenoise,cave,generator,finders,util,quadbase,mt}.c -lm -o /tmp/probe_capacity_poisoning && /tmp/probe_capacity_poisoning
  ```
- **Verified Capacity Poisoning Fix Probe:**
  ```bash
  clang -O2 -I native -I vendor/cubiomes-bedrock reviews/split-audit-2026-10-15/gemini/probes/mem/probe_capacity_fixed.c vendor/cubiomes-bedrock/{noise,biomes,layers,biomenoise,cave,generator,finders,util,quadbase,mt}.c -lm -o /tmp/probe_capacity_fixed && /tmp/probe_capacity_fixed
  ```
- **Reservation Contract Bypass Measurement (G-MEM-02):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/mem/probe_buffer_reservation.py
  ```
- **In-Flight Queue Limit Exceeded by 1 (G-MEM-03):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/mem/probe_inflight_bounds.py
  ```

---

## 4. FFI Boundary and Evidence Retention Probes (G-FFI)

- **Survivor Evidence Completeness & Retention Metadata:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_retained_records.py
  ```
- **Concurrent Sweeps Policy Isolation:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_concurrency.py
  ```
- **Encoder Template Caching Under Concurrency:**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_encoder_concurrency.py
  ```
- **Tautological Replay Provider Verification (G-FFI-01):**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_replay_verification.py
  ```
- **Batch Lifetime, Missing Finalizer & Discovered Anchors Mismatch (G-FFI-02, G-FFI-04):**
  ```bash
  PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/ffi/probe_batch_lifetime_receipt.py
  ```

---

## 5. Storage and Web Control Plane Probes (G-STORE)

- **Web UI Stale Candidate Cache Invalidation (G-STORE-01):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_candidate_cache_invalidation.py
  ```
- **TOCTOU Lease Validation & Blind Overwrite in complete_prepared (G-STORE-02):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_toctou_lease_overwrite.py
  ```
- **complete_range Missing Lease Validation (G-STORE-03):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_complete_range_no_lease.py
  ```
- **Deferred Transactions in claim_range (G-STORE-04):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_deferred_transaction_lock.py
  ```
- **Web Server Global Lock Starvation During Pause/Stop (G-STORE-05):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_web_server_lock_starvation.py
  ```
- **WAL Checkpoint Blockage Under Concurrent Readers (G-STORE-06):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_wal_checkpoint_growth.py
  ```
- **Connection Thread Confinement Violations (G-STORE-07):**
  ```bash
  ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/store/probe_connection_thread_confinement.py
  ```

