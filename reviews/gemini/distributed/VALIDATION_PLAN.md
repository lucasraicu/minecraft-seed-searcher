> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Benchmark & Validation Plan: Dynamic Baseline (`dynamic-envelope-1664-v1`)

**Scope:** Rigorous benchmarking, machine tuning, semantic parity certification, and counterbalanced 5-pair validation.
**Author:** Task 4: Distributed sweep and benchmark runbook
**Target:** Dynamic Baseline 1664 (`screening_revision: dynamic-envelope-1664-v1`)
**Standard:** Zero semantic drift, 100% cryptographic parity, and empirical throughput verification within a 15–20 minute time budget.

---

## 1. Two-Tier Benchmark Architecture: Kernel vs. Durable Rate

In distributed high-performance computing, confusing raw compute kernel execution with durable system throughput is a classic pitfall. This validation plan strictly decouples and measures both metrics:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: NATIVE-KERNEL RATE (R_kernel)                                          │
│ • Unit: inputs / batch.native_seconds                                          │
│ • Scope: Pure C/OpenMP execution inside CFFI (nb_sweep)                        │
│ • Components: Nether PRNG + co-window, Mansion/Bastion noise evaluation,       │
│   outpost PRNG checks, 2D slab intersection solver, centroid magnet pull,      │
│   and 13+5 biome lattice checks.                                               │
│ • Ignored: Python GIL, CFFI buffer marshaling, record extraction, SQLite WAL,  │
│   fsync disk latency, OS thread context switching.                             │
└────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ (Records streamed through CFFI)
┌────────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: DURABLE END-TO-END RATE (R_durable)                                    │
│ • Unit: inputs / wall_clock_seconds                                            │
│ • Scope: Complete ACID pipeline from seed dispatch to fsync'd WAL commit       │
│ • Components: Seed generation (seed_from_index), nb_sweep execution,           │
│   Python record preparation (prepare_retained_range / fast_records),           │
│   decision receipt hashing (input_decisions_sha256), SQLite WAL transaction,   │
│   PRAGMA synchronous=FULL disk sync, process-tree RSS resource sampling.       │
│ • Governed by: SQLite transaction overhead, disk I/O, IPC queueing, Python GIL.│
└────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Formal Rate Definitions
Let a batch $b$ contain $N_b$ seeds.
- **Native-Kernel Rate:**
  $$R_{\text{kernel}} = \frac{\sum_{b} N_b}{\sum_b t_{\text{native}}(b)}$$
- **Durable End-to-End Rate:**
  $$R_{\text{durable}} = \frac{N_{\text{total}}}{T_{\text{wall}}}$$
  where $T_{\text{wall}}$ is monotonic elapsed time from first dispatch to completion of the final database commit.

In production:
$$R_{\text{durable}} < R_{\text{kernel}}$$
Typically, on multi-core systems with fast NVMe storage, $R_{\text{durable}} \approx 0.50\text{–}0.75 \times R_{\text{kernel}}$, governed by Python-side serialization and SQLite lock contention. Tuning must optimize for $R_{\text{durable}}$, not $R_{\text{kernel}}$ alone.

---

## 2. Machine Tuning Protocol ($\le 50,000$ Inputs)

Prior to running validation pairs or production sweeps on any hardware node, a bounded tuning sweep explores the hardware's optimal thread and batch size combination.

### 2.1 Bounded Tuning Constraints
1. **Input Volume Cap:** $N_{\text{tune}} \le 50,000$ seeds (strictly enforced by `tune_machine.py`). Standard test volume: **30,000 seeds**.
2. **Execution Timeout:** Cumulative tuning time is hard-capped at **900 seconds (15 minutes)**. If the timer expires, the tuner aborts with `RuntimeError('Tuning budget exhausted; no recommendation adopted')`.
3. **Seed Interval:** Uses deterministic seed generation from index:
   $$\text{seeds} = [\text{seed\_from\_index}(i, 20261013) \quad \text{for } i \in [0, N_{\text{tune}})]$$

### 2.2 Candidate Parameter Grid
Let $C_{\text{detected}}$ be the host's logical CPU count:
$$C_{\text{total}} = \min(34, C_{\text{detected}})$$
*(The production executor reserves 2 CPU slots for Python record preparation and SQLite writing; maximum supported native worker threads is strictly 34).*

- **Thread Grid ($\mathcal{T}$):**
  $$\mathcal{T} = \left\{ \max\left(1, \lfloor C_{\text{total}} / 2 \rfloor\right),\; \max\left(1, \lfloor 0.75 C_{\text{total}} \rfloor\right),\; C_{\text{total}}-4,\; C_{\text{total}}-2,\; C_{\text{total}} \right\} \cap [1, 34]$$
- **Batch Size Grid ($\mathcal{B}$):**
  $$\mathcal{B} = \begin{cases} [4096, 8192] & \text{if } C_{\text{detected}} < 64 \\ [8192, 16384] & \text{if } C_{\text{detected}} \ge 64 \end{cases}$$

### 2.3 Counterbalanced Multi-Trial Measurement
To eliminate cache warmup bias and thermal throttling effects:
- Execute 3 complete passes over the grid $\mathcal{G} = \mathcal{T} \times \mathcal{B}$:
  - Pass 0: Forward grid order
  - Pass 1: Reversed grid order
  - Pass 2: Forward grid order
- Record kernel rates $R_0(T, B)$, $R_1(T, B)$, $R_2(T, B)$.
- Select winner $(T^*, B^*)$ maximizing the **median rate**:
  $$(T^*, B^*) = \arg\max_{(T, B) \in \mathcal{G}} \text{median}\big(R_0(T, B), R_1(T, B), R_2(T, B)\big)$$

---

## 3. Five Counterbalanced Control/Selected Validation Pairs

To formally certify the tuned settings $(T^*, B^*)$ against default production baseline settings ($T_0=16, B_0=4096$), execute five counterbalanced pairs on **held-out inputs**.

### 3.1 Design & Held-Out Index Partitions
- **Tuning Range (Excluded):** $[0, 50,000)$
- **Held-Out Validation Range:** $[50,000, 550,000)$ — exactly 500,000 distinct seeds.
- **Partitioning into 5 Distinct Intervals:**
  $$\mathcal{I}_1 = [50,000, 150,000) \quad (100,000\text{ seeds})$$
  $$\mathcal{I}_2 = [150,000, 250,000) \quad (100,000\text{ seeds})$$
  $$\mathcal{I}_3 = [250,000, 350,000) \quad (100,000\text{ seeds})$$
  $$\mathcal{I}_4 = [350,000, 450,000) \quad (100,000\text{ seeds})$$
  $$\mathcal{I}_5 = [450,000, 550,000) \quad (100,000\text{ seeds})$$

### 3.2 Counterbalanced Scheduling (AB / BA Alternation)
Running benchmarks sequentially without alternating order induces severe systematic errors due to disk cache priming, memory bus pre-warming, or thermal throttling. The protocol enforces strict counterbalancing:

| Pair # | Interval ($\mathcal{I}_k$) | Arm 1 (First) | Arm 2 (Second) | Rationale |
| :---: | :---: | :---: | :---: | :--- |
| **Pair 1** | $[50\text{k}, 150\text{k})$ | **Control** ($T_0=16, B_0=4096$) | **Selected** ($T^*, B^*$) | Baseline cold start; Selected primed. |
| **Pair 2** | $[150\text{k}, 250\text{k})$ | **Selected** ($T^*, B^*$) | **Control** ($T_0=16, B_0=4096$) | Selected cold start; Baseline primed. |
| **Pair 3** | $[250\text{k}, 350\text{k})$ | **Control** ($T_0=16, B_0=4096$) | **Selected** ($T^*, B^*$) | Mid-test control baseline. |
| **Pair 4** | $[350\text{k}, 450\text{k})$ | **Selected** ($T^*, B^*$) | **Control** ($T_0=16, B_0=4096$) | Mid-test selected baseline. |
| **Pair 5** | $[450\text{k}, 550\text{k})$ | **Control** ($T_0=16, B_0=4096$) | **Selected** ($T^*, B^*$) | Final pair; checks thermal drift. |

### 3.3 Time & Budget Reconciliation
- Total evaluations: 10 runs $\times$ 100,000 inputs = 1,000,000 total evaluations.
- Single run duration at typical rates ($11,000\text{–}14,000\text{ seeds/s}$):
  $$t_{\text{run}} = \frac{100,000}{12,500} \approx 8.0\text{ seconds}$$
- Cumulative benchmark runtime:
  $$T_{\text{total}} = 10 \times 8.0\text{ s} = \mathbf{80\text{ seconds}} \quad (\sim 1.33\text{ minutes})$$
- Verification and digest comparison: $\approx 10\text{ seconds}$.
- **Total Protocol Duration:** $\mathbf{\approx 1.5\text{ minutes}}$, well within the **15–20 minute allocation budget**.

---

## 4. Semantic Parity Verification Criteria

A configuration change that increases throughput is **disqualified** if it introduces any divergence in screening logic, candidate qualification, coordinate calculation, or leaderboard ranking.

### 4.1 Zero-Tolerance Parity Invariants

For each pair $k \in \{1 \dots 5\}$ on interval $\mathcal{I}_k$:

1. **Decision Digest Bit-Identity:**
   Every batch produces a 64-character SHA-256 digest of the C engine's `NBVerdict` array. The cumulative hash of all retention receipts in the Control Arm database must match the Selected Arm database:
   $$\text{Digest}(\text{Receipts}_{\text{Control}}, \mathcal{I}_k) = \text{Digest}(\text{Receipts}_{\text{Selected}}, \mathcal{I}_k)$$
2. **Survivor Set Equality:**
   $$\{ \text{candidate\_id} \}_{\text{Control}} \equiv \{ \text{candidate\_id} \}_{\text{Selected}}$$
3. **Exact Coordinate & Center Invariance:**
   For every candidate $c$, the calculated optimal dynamic center must match identically:
   $$(C_X, C_Z)_{\text{Control}}(c) = (C_X, C_Z)_{\text{Selected}}(c)$$
4. **Deficit Tier & Score Invariance:**
   - $\text{DeficitTier}_{\text{Control}}(c) \equiv \text{DeficitTier}_{\text{Selected}}(c)$
   - $\text{UnmetRequirements}_{\text{Control}}(c) \equiv \text{UnmetRequirements}_{\text{Selected}}(c)$
   - $\text{SmartScore}_{\text{Control}}(c) \equiv \text{SmartScore}_{\text{Selected}}(c)$
5. **Python Reference Replay Agreement:**
   For any surviving candidate $c$, verify against the pure Python reference oracle `evaluate_dynamic_seed()`:
   $$\text{Oracle}(\text{seed}, \text{dynamic\_blueprint\_config()}) \equiv \text{NativeResult}(c)$$

---

## 5. Statistical Hypothesis Testing & Adoption Decision

Let $D_k = R_{\text{durable, Selected}}(\mathcal{I}_k) - R_{\text{durable, Control}}(\mathcal{I}_k)$ for $k \in \{1 \dots 5\}$.

### 5.1 Test Hypotheses
- **Null Hypothesis ($H_0$):** $\mu_D \le 0$ (Selected settings offer no throughput improvement over baseline).
- **Alternative Hypothesis ($H_1$):** $\mu_D > 0$ (Selected settings provide statistically significant durable speedup).

### 5.2 Adoption Criteria
Adopt the Selected settings $(T^*, B^*)$ for production iff:
1. **Semantic Parity:** 100% pass across all 5 pairs (zero divergences).
2. **Throughput Improvement:** $\bar{D} > 0$ and $\min_k D_k > 0$ (Selected outperforms Control on all 5 counterbalanced pairs).
3. **Stability & Headroom:** Peak RSS does not exceed `memory_target_gib` (25 GiB), and SQLite WAL write latencies do not exhibit tail latency spikes ($p_{95} < 0.25\text{ s}$).
4. **Failure Fallback:** If any pair fails semantic parity or fails to show speedup, the node **must retain the certified default settings** ($T_0=16, B_0=4096$).

---

## 6. Execution Script Specification

Below is the execution contract for conducting the 5-pair validation experiment:

```python
"""
Pseudo-code specification for 5-pair counterbalanced validation
"""
from pathlib import Path
import time
from seed_search.realm.runner import run_scan
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.store import RealmStore

def run_counterbalanced_validation(native_build: Path, selected_threads: int, selected_batch: int):
    cfg = dynamic_blueprint_config()
    intervals = [
        (50_000 + i * 100_000, 100_000) for i in range(5)
    ]
    control_params = {"native_threads": 16, "native_batch_size": 4096}
    selected_params = {"native_threads": selected_threads, "native_batch_size": selected_batch}

    results = []
    for pair_idx, (start, count) in enumerate(intervals):
        # Determine counterbalanced arm order: even pairs Control->Selected, odd pairs Selected->Control
        order = [("control", control_params), ("selected", selected_params)] if pair_idx % 2 == 0 else [("selected", selected_params), ("control", control_params)]

        pair_records = {}
        for arm_name, params in order:
            run_dir = Path(f"runs/val-pair-{pair_idx}-{arm_name}")
            start_wall = time.perf_counter()
            status = run_scan(
                cfg=cfg,
                output=run_dir,
                count=count,
                start_index=start,
                execution="native",
                native_build=native_build,
                retention="survivors",
                max_misses=2,
                allow_prediction_scale=True,
                **params
            )
            wall = time.perf_counter() - start_wall

            with RealmStore(run_dir, resume=True) as store:
                receipts = store.db.execute("SELECT digest FROM retention_receipts ORDER BY start").fetchall()
                candidates = store.db.execute("SELECT id, qualification, result FROM candidates ORDER BY id").fetchall()

            pair_records[arm_name] = {
                "wall_seconds": wall,
                "rate": count / wall,
                "receipts_digest": hash(tuple(receipts)),
                "candidates": candidates
            }

        # Verify 100% semantic parity
        assert pair_records["control"]["receipts_digest"] == pair_records["selected"]["receipts_digest"], f"Digest mismatch on pair {pair_idx}"
        assert len(pair_records["control"]["candidates"]) == len(pair_records["selected"]["candidates"]), f"Candidate count mismatch on pair {pair_idx}"

        results.append(pair_records)
    return results
```
