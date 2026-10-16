# Master Framework Audit & Aggregated System Review — October 16, 2026

## 1. Executive Decision

**The `dynamic-envelope-2048-v3` implementation is not ready to be treated as a fully integrated, correctly ranked production system.** 

While its core additive score arithmetic and raw C11 kernel functions operate in mathematical parity with Python, critical integration gaps, geometry leaks, rescoring regressions, and Web UI desynchronizations undermine the system:
1. **Deployment & Default Disconnect:** The web UI, backend server defaults, and CLI still launch `dynamic-envelope-1664-v2`. The active UI has no v3 profile.
2. **Rescore & Oracle Drift:** Rescoring v3 candidates silently applies v2 rules (demoting a real 281-pt candidate to 176 pts), and independent reference scoring omits v3 window geometry (dropping outer village-spread bonuses).
3. **Out-of-Bounds Nether Evidence:** The selected-window Nether sampler constructs an unaligned 17×17 grid over a half-open 1024m box, recording 33 out-of-bounds sample points and saving out-of-bounds witnesses.
4. **Specification Arithmetic Error:** The blueprint document claims a 600-point Core Surplus cap and 1,200-point total; the actual mathematical sum of its defined caps is **650 points Core Surplus** and **1,250 points Grand Total**.
5. **Zero-Yield Floor Bottlenecks:** In pilot sweeps totaling over 2,786,000 distinct seeds, **exactly zero seeds survived**. Requiring all 14 hard floors simultaneously in a single $2048 \times 2048$ window with zero miss tolerance ($B=0$) demands mutually exclusive climate extremes (Desert Pyramid, Jungle Temple, Mansion, Ancient City, Ocean Monument) that occur at an estimated rate of $< 1 \text{ in } 2.5 \times 10^9$ seeds.
6. **Top-50 Framework Gaps:** The in-memory Top-50 tracker exists only as a pilot script utility; it is neither wired into the C kernel for cutoff pruning nor persisted periodically with durable SQLite state. Furthermore, its internal comparator and the Web UI comparator regress to wrong sort keys.

The correct path forward is **systematic correctness and UI integration**, followed by floor/budget calibration and native pruning.

---

## 2. Audit Scope & Reproduction Baseline

- **Base Commit:** `233fad76fddc5667e77c27ab7e5cc83d3669a7a2` (Dirty working tree).
- **Host Architecture:** Intel Xeon / Apple Silicon test hosts; OpenMP multi-threaded runtime.
- **Test Baseline:** Entire existing Python test suite (**1,159 tests passed**, 358s in `pytest.log`); 10 JS contract tests passed.
- **Empirical Sweeps Evaluated:**
  - 2,000,000-seed pilot run (`runs/v3_pilot_2m/pilot_summary.json`).
  - 786,432-seed interleaved 34-thread benchmark cohort (`benchmark.jsonl`, `durable.jsonl`).
  - 100,000-seed native diagnostic funnel probe (`read_diagnostics.py`).
  - 2,688-window empirical sliding-center bottleneck failure probe.
  - 10,000-seed randomized C-vs-Python arithmetic verification (`score-parity.json`).
  - Real natural survivor seed `-3336796033057908633` (evaluated under custom empty Overworld palette to verify retention mechanics).

---

## 3. Prioritized Audit Findings

### F1 — P1: Web UI & Server Launch Historical v2 Policy Instead of v3
- **Evidence:** `contracts.json`, `legacy-binary.json`, `web-ui/src/constants/searchProfiles.json`, `src/seed_search/web/server.py:41`.
- **Detail:**
  - `web-ui/src/constants/searchProfiles.json` contains only `dynamic1664`, `marine2048`, and `twoGroup2048`. There is **no `dynamic2048` profile** for the active v3 system.
  - `src/seed_search/web/server.py:41` still points to `runs/dynamic-baseline-1664/native` with HTTP defaults set to v2 / 3 misses. `src/seed_search/realm/cli.py:49` also defaults to v2.
  - Fresh Python code recognizes `dynamic2048`, but previewing it without an explicit zero miss budget fails validation.
  - The older packaged native build rejects v3 sweeps with `Native batch allocation or policy error`.
  - The completed 10-billion-seed web sweep was executed under `dynamic-envelope-1664-v2`; its zero results reflect v2, not v3.
- **Required Remediation:**
  1. Add `dynamic2048` to `searchProfiles.json` with exact 2048/1024 geometry and v3 floors.
  2. Set default miss budget to 0 for v3 in web launch contracts.
  3. Rebuild and bind native C binary with v3 policy support.
  4. Update `server.py` and `cli.py` defaults to active v3.

---

### F2 — P1: Rescoring Silently Applies v2 Rules to v3 Candidates
- **Evidence:** `probe_rescore.py`, `rescore.json`, `src/seed_search/realm/reports.py:327–375`.
- **Detail:**
  - `dynamic_v2_policy()` returns `True` for v3 revisions, but `_candidate_rescore()` unconditionally invokes `dynamic_v2_score()`, v2 radial helpers, and old 1664/832 geometry defaults.
  - Natural candidate seed `-3336796033057908633` (center `-480, 0`) scores **281 pts** in native v3. Rescoring this candidate overwrites its score to **176 pts** and assigns obsolete v2 score components while leaving `screening_revision: "dynamic-envelope-2048-v3"`.
- **Required Remediation:**
  1. Implement explicit revision dispatch in `_candidate_rescore()`:
     ```python
     if dynamic_v3_policy(cfg):
         score, components, deficits = dynamic_v3_score(...)
     ```
  2. Add an idempotence regression test: a saved v3 candidate rescored under its own policy must strictly preserve its score, components, evaluation center, and canonical rank key.

---

### F3 — P1: Nether Selected-Window Evidence Includes Out-of-Bounds Points
- **Evidence:** `probe_nether_bounds.py`, `nether-bounds.json`, `src/seed_search/realm/dynamic.py:144–159`, `native/blueprint_dynamic.inc:213–236`.
- **Detail:**
  - Both C and Python construct a fixed **17 × 17 grid** (289 points) for a half-open $1024 \times 1024$ Nether window.
  - On a 64-block world-aligned lattice, a half-open $[lo, lo+1024)$ window contains exactly **16 intervals = 16 sample points**, NOT 17. The 17th point lands on the excluded eastern/southern boundary ($lo + 1024$).
  - This injects **33 out-of-bounds sample points** into the retained Nether evidence.
  - In candidate `-3336796033057908633`, **4 of the 5 saved Nether witnesses** are located outside the legal playable window. In synthetic tests, Basalt Deltas on the excluded boundary falsely certified the Nether palette.
- **Required Remediation:**
  1. Generate Nether samples using exact half-open intervals ($X \in [lo, hi)$, $Z \in [lo, hi)$) yielding $16 \times 16 = 256$ valid lattice points.
  2. Restrict all witness reporting strictly to interior points.
  3. Correct the blueprint documentation claim of a "289-point lattice".

---

### F4 — P1: Independent Oracle Scoring Uses v2 Geometry Defaults
- **Evidence:** `natural.jsonl`, `contracts.json`, `src/seed_search/realm/blueprint.py:862, 868`.
- **Detail:**
  - During independent reference evaluation in `evaluate_dynamic_seed()`, helper functions `village_spread_bonus_v2()` and `treasure_bastion_bonus_v2()` are called without passing the v3 half-widths (`overworld_half=1024`, `nether_half=512`).
  - They default to historical v2 sizes (832 and 416).
  - Consequently, candidate `-3336796033057908633` receives **281 pts in native evaluation and replay**, but drops to **256 pts in independent evaluation**. Its +25 Village Spread bonus is lost because qualifying villages between radius 832m and 1024m are ignored by the default parameters.
  - A Treasure Bastion located at Nether $X=480$ is captured by native v3 (radius 512), but dropped by the independent oracle (radius 416).
- **Required Remediation:**
  1. Explicitly thread `ow_half` and `nw_half` through all spatial and variant bonus helpers in `blueprint.py`.
  2. Add differential tests comparing native `NBAnchor` bonus fields against standalone Python helpers.

---

### F5 — P1: Top-50 Framework Is a Pilot Script Utility, Not an Active Search Cutoff
- **Evidence:** `src/seed_search/realm/top_tracker.py:14–187`, `native/blueprint_batch.h:43–61`, `scripts/pilot_v3_2048.py:101–155`.
- **Detail:**
  - The Top-50 min-heap (`Top50Tracker`) is only instantiated in `scripts/pilot_v3_2048.py`.
  - The C kernel struct `NBPolicy` contains no `cutoff_score` field. Native batch execution (`nb_sweep`) computes all seeds meeting hard floors regardless of score.
  - The pilot script only observes candidates *after* they pass all 14 floors and all 18 biome gates, and flushes results only at exit.
  - "Zero disk overhead", periodic SQLite snapshotting, and native cutoff pruning are not implemented in the production engine.
- **Required Remediation:**
  1. Add `int cutoff_score` to `NBPolicy` in `blueprint_batch.h`.
  2. In `blueprint_dynamic.inc`, evaluate candidate upper bounds in Stage 1B and prune evaluation if $\text{Score}_{\max} < \text{cutoff\_score}$.
  3. Integrate `Top50Tracker` into `persist_pipeline()` with transactional SQLite checkpointing.

---

### F6 — P2: Top-50 Tracker and Web UI Ordering Regress from Canonical v3 Order
- **Evidence:** `src/seed_search/realm/top_tracker.py:27–98`, `web-ui/src/utils/ranking.ts:7–30`, `web-ranking.json`.
- **Detail:**
  - **Tracker Seed Ordering:** `Top50Tracker._extract_key()` orders tied candidates by numeric `seed` value instead of binary lexical ID (`id ASC`), inverting ordering relative to SQLite (`candidate_leaderboard_v2`).
  - **SQLite Zero-Score Bug:** `Top50Tracker.save_to_sqlite()` reads top-level `rec.get('baseline_score_observed')`. For standard nested candidate records, the score is located at `rec['anchors'][0]['baseline_score_observed']`. Consequently, `save_to_sqlite()` writes **score = 0** into the database table!
  - **Mutable Heap State & Duplication:** Records are inserted by reference without deep copying, allowing external mutations to corrupt the heap. Inserting identical seeds creates duplicate slots.
  - **Web UI Ranking Regression:** `web-ui/src/utils/ranking.ts` line 7 checks:
    ```typescript
    if (a.screeningRevision === 'dynamic-envelope-1664-v2' && b.screeningRevision === a.screeningRevision)
    ```
    Candidates with `screeningRevision: 'dynamic-envelope-2048-v3'` fall through to legacy line 20, which places `unmetRequirements` ahead of `score` and discards `radialKey` and `originDistanceSquared` tie-breaks.
- **Required Remediation:**
  1. Fix `ranking.ts` to include `'dynamic-envelope-2048-v3'`.
  2. Update `Top50Tracker` to parse nested anchor scores, copy records on entry, and order ties by binary lexical ID.

---

### F7 — P2: Blueprint Specification Arithmetic Error & Text Contradictions
- **Evidence:** `MASTER_SEED_BLUEPRINT.md` lines 96–115, 170–190, 221–234; `blueprint.py:593–675`; `native/blueprint_dynamic.inc:316–344`.
- **Detail:**
  1. **Arithmetic Addition Error:**
     Section 5.1 itemizes 14 core structure surplus schedules:
     $$85 + 60 + 60 + 65 + 50 + 50 + 50 + 50 + 50 + 40 + 30 + 20 + 20 + 20 = \mathbf{650\text{ pts}}$$
     The blueprint states: `Sum of all core surplus caps = 600 pts`. The actual sum is **650 pts**.
     Consequently, the true maximum score is:
     $$\mathbf{Total} = 650\text{ (Core)} + 200\text{ (Optional)} + 265\text{ (Luxury)} + 135\text{ (Spatial/Nether)} = \mathbf{1,250\text{ Pts Max}}$$
  2. **Section 3 vs. Section 5.1 Clash:**
     Section 3 specifies Village floor $\ge 8$ and Ancient City floor $\ge 3$. Section 5.1, `config.py`, and the C kernel implement Village floor $\mathbf{\ge 6}$ and Ancient City floor $\mathbf{\ge 2}$.
  3. **Ruined Portal Hub Point Discrepancy:**
     Blueprint text specifies Ruined Portals within 512m of center earn **+6 pts**. Both C (`nb_dynamic_v3_hub`) and Python (`blueprint.py:499`) award **+4 pts**.
  4. **Savanna Luxury Categorization:**
     In C and Python, ordinary `savanna` is credited under the Windswept Savanna luxury category (+15 pts) and contributes to the Luxury Diversity Jackpot.
- **Required Remediation:**
  1. Update `MASTER_SEED_BLUEPRINT.md` to state the correct mathematical caps: **650 Core Surplus** and **1,250 Total Points**.
  2. Reconcile Section 3 tables to match Section 5.1 (Villages 6, Ancient Cities 2).
  3. Align Portal hub wording to +4 pts, and document `savanna` inclusion in luxury biomes.

---

### F8 — P2: Stale and Broken Diagnostic Scripts
- **Evidence:** `diagnose-probe.log`, `floor-probe.log`, `scripts/diagnose_v3_funnel.py`, `scripts/measure_v3_floors.py`.
- **Detail:**
  - `diagnose_v3_funnel.py` reads `res['counts'][name]`, but `evaluate_dynamic_seed()` returns summary fields (`stronghold_anchors`), not raw structure counts. Missing keys default to 0, falsely reporting 0% pass rates across all structures.
  - `measure_v3_floors.py` crashes with `ValueError: Blueprint structure floors and allowed bonuses cannot be relaxed` because it attempts to mutate immutable blueprint configuration.
  - `probe_macro_probabilities.py` tests obsolete v1 thresholds (Outpost 1, Bastion 1, Trial Chamber 6, Portal 4) rather than active v3 floors.
- **Required Remediation:**
  1. Fix `diagnose_v3_funnel.py` to inspect `res['anchors'][0]['required_structures']`.
  2. Use `native/blueprint_batch.inc` diagnostic counters (`nb_diag_get`) for native-level stage attribution.

---

### F9 — P2: Web UI Detail Modal and Sidebar Feature Desynchronization
- **Evidence:** `web-ui/src/components/SeedDetailModal.tsx:324–394`, `web-ui/src/components/FilterSidebar.tsx:36`.
- **Detail:**
  - `SeedDetailModal.tsx` labels candidate breakdowns as `(dynamic-v2)` instead of v3.
  - Displays Treasure Bastion bonus as `+15` (v3 awards `+20`).
  - Omits the **Nether Portal Core (+20 max)** bonus indicator entirely.
  - Displays a "Deficits" penalty card, even though deficits and penalties are strictly zero in v3.
  - `FilterSidebar.tsx:36` blocks custom biome toggling with `if (sweepRunning || config.profile !== 'dynamic1664') return;`.
- **Required Remediation:**
  1. Update `SeedDetailModal.tsx` to render the 1,250 pt breakdown (Core Surplus, Optional, Luxury, Hub, Scenic, Village Spread, Treasure Bastion, Nether Core).
  2. Remove deficit penalty display for v3 candidates.
  3. Enable interactive biome selection for `dynamic2048`.

---

## 4. Empirical Speed & Throughput Analysis

Comprehensive benchmarks were executed on an Intel Xeon / macOS host using 34 OpenMP threads, batches of 16,384, and interleaved test cohorts across 786,432 inputs:

| Arm / Configuration | Median Throughput | Observed Range | Notes |
| :--- | :---: | :---: | :--- |
| **V2 Current Binary (Compact Kernel)** | **232,028 seeds/s** | 193,927 – 232,507 | 1664×1664 Overworld / 832×832 Nether |
| **V3 Current Binary (Compact Kernel)** | **57,551 seeds/s** | 56,697 – 58,865 | 2048×2048 Overworld / 1024×1024 Nether |
| **V3 Isolated Build (No Diagnostic Atomics)** | **58,258 seeds/s** | 56,335 – 59,295 | Diagnostic counters cost < 1.2% |
| **V3 Durable Compact Pipeline** | **54,752 seeds/s** | 54,292 – 56,445 | Native + Python + SQLite WAL + Disk Monitor |

### Multi-Threaded Scaling Curve (V3 vs. V2)
Measured across thread counts over 16,384-seed batches:

```
  Threads │ dynamic-v3 (2048×2048) │ dynamic-v2 (1664×1664) │ Ratio (v2 vs v3)
  ────────┼────────────────────────┼────────────────────────┼─────────────────
    1     │         3,697 seeds/s  │        13,469 seeds/s  │      3.64×
    4     │        13,965 seeds/s  │        53,445 seeds/s  │      3.83×
    8     │        24,771 seeds/s  │        97,502 seeds/s  │      3.94×
   16     │        44,242 seeds/s  │       176,750 seeds/s  │      4.00×
   34     │        57,551 seeds/s  │       232,028 seeds/s  │      4.03×
```

### Root Cause of the 4.0× Throughput Gap
1. **Search Area Expansion:**
   - Overworld macro search box expanded from $[-2000, 2000]$ ($4\text{M m}^2$) to $[-2000, 2000)$ ($16\text{M m}^2$) — a **$4.0\times$ increase in evaluation area**.
   - Nether preflight box expanded from $[-416, 416]$ ($0.69\text{M m}^2$) to $[-634, 634]$ ($1.61\text{M m}^2$) — a **$2.32\times$ increase**.
2. **Event-Slab Density:**
   - Discovered Mineshafts per seed increased from ~50 to ~220+; Ruined Portals from ~10 to ~40. The 2D event-slab partitioner evaluates $4\times$ more Cartesian slabs per seed.
3. **PGO Optimization Status:**
   - The shipped v3 binary is built with AVX2/FMA and LTO, but **does not have a PGO profile** (`pgo_profile_sha256: null`), whereas the historical v2 binary was PGO-optimized.

---

## 5. Feature-to-Bonus Relationships & Bottleneck Decomposition

### Complete Stage-by-Stage Funnel on 786,432 Seeds
```
  Funnel Stage                                          Survivors    Stage Pass %   Total Pass %
  ──────────────────────────────────────────────────────────────────────────────────────────────
  Total Input Seeds                                       786,432        100.00%        100.00%
  Stage 1A: Raw Preflight (Nether / Outpost / Mansion)    713,033         90.67%         90.67%
  Stage 1A: Mansion Phase 1/2 Dark Forest Check           219,928         30.84%         27.96%
  Stage 1A: Macro Mansion Viable (≥1 in 4000×4000)         31,938         14.52%          4.06%
  Stage 1A: Macro Stronghold (≥1)                          27,089         84.82%          3.44%
  Stage 1A: Macro Outpost Viable (≥2)                      20,393         75.28%          2.59%
  Stage 1A: Macro Nether Viable (Fortress ≥1, Bastion ≥2)  19,587         96.05%          2.49%
  Stage 1B: All 14 Macro Floors Met in 4000×4000           2,401         12.26%          0.31%
  Stage 1B: ≥1 Cell Meeting All 14 Floors in 2048×2048          1          0.04%         0.0001%
  Stage 2:  Meeting All 13 Overworld + 5 Nether Biomes          0          0.00%         0.0000%
  Final Qualifying Survivors                                    0          0.00%         0.0000%
```

### Empirical Single-Window Failure Rates (2,688 Realm Windows)
Testing sliding candidate centers across seeds with macro viability reveals the structure bottlenecks:

```
  Structure Category       Hard Floor    Single-Window Failure Rate   Realm Role
  ──────────────────────────────────────────────────────────────────────────────────
  🏺 Desert Pyramid           ≥ 1                 89.47%              High desert aridity
  🏴‍☠️ Pillager Outpost         ≥ 2                 85.01%              Rare region grid
  🌿 Jungle Temple            ≥ 1                 80.47%              High humidity jungle
  🏘️ Village                 ≥ 6                 76.82%              High density settlement
  🏛️ Woodland Mansion         ≥ 1                 74.81%              Dark forest requirement
  🌌 Ancient City             ≥ 2                 73.36%              Deep dark mountain roots
  🏰 Stronghold               ≥ 1                 63.17%              Ring coordinate target
  🗿 Ocean Monument           ≥ 1                 57.55%              Deep ocean basin
  ⛵ Shipwreck                ≥ 4                 45.39%              Ocean / coast water
  🐷 Bastion Remnant          ≥ 2                 14.40%              Nether piglin bartering
  🔥 Nether Fortress          ≥ 1                 10.16%              Blaze rod access
  🌀 Ruined Portal            ≥ 8                  1.00%              Transit access
  ⚔️ Trial Chamber            ≥ 8                  0.41%              Midgame combat dungeon
  ⛏️ Mineshaft                ≥ 10                 0.00%              Subterranean rails
```

### Key Mechanical Insights:
1. **Climate Polarization:** In Bedrock PRNG noise, climate parameters vary over 1,500–3,000 block continental wavelengths. Forcing hot arid Desert (Pyramid), hot humid Jungle (Temple), temperate Dark Forest (Mansion), and Deep Ocean (Monument) into a single $2048 \times 2048$ box with $B=0$ miss tolerance requires an extreme, vanishingly rare climate gradient ($\approx 1 \text{ in } 2.5\times 10^9$ seeds).
2. **Centroid Magnet Bias:** Centroid magnet pull assigns weight $\omega = 3$ to Villages. Pulling the center toward settlement hubs drags window borders away from peripheral Desert Pyramids and Jungle Temples.
3. **Bonus Allocation:** The 1,250-point score allocates **52.0% Core Surplus**, **16.0% Optional Structures**, **21.2% Luxury Biomes**, and **10.8% Spatial/Nether Core**. Because zero seeds pass baseline hard floors under $B=0$, seeds cannot enter the candidate pool to earn surplus or luxury points.

---

## 6. Actionable System & UI Remediation Roadmap

### System Engine Remediation

| Priority | Action Item | File / Target | Specific Fix |
| :---: | :--- | :--- | :--- |
| **P1** | **Fix v3 Rescore Dispatch** | `src/seed_search/realm/reports.py:327` | Dispatch to `dynamic_v3_score` when `dynamic_v3_policy(cfg)`. Prevent score degradation from 281 to 176. |
| **P1** | **Fix Half-Open Nether Sampler** | `native/blueprint_dynamic.inc:213`, `src/seed_search/realm/dynamic.py:144` | Sample $16 \times 16$ lattice (256 points) instead of $17 \times 17$ (289 points) to eliminate 33 out-of-bounds points. |
| **P1** | **Pass Window Geometry to Oracle** | `src/seed_search/realm/blueprint.py:862, 868` | Pass `overworld_half=1024, nether_half=512` to `village_spread_bonus_v2` and `treasure_bastion_bonus_v2`. |
| **P1** | **Align Server & CLI Defaults** | `src/seed_search/web/server.py:41`, `src/seed_search/realm/cli.py:49` | Set default revision to `dynamic-envelope-2048-v3`, default miss budget to 0, and bind to current binary. |
| **P2** | **Reconcile Blueprint Arithmetic** | `MASTER_SEED_BLUEPRINT.md:170–190` | Correct Core Surplus sum to 650 pts and Grand Total to 1,250 pts. Harmonize Section 3 floors (Village 6, Ancient City 2). |
| **P2** | **Repair Top-50 Tracker Ordering** | `src/seed_search/realm/top_tracker.py:97, 160` | Order ties by binary lexical ID (`id ASC`); parse nested anchor scores in `save_to_sqlite()`; snapshot records on insert. |
| **P2** | **Implement Native Cutoff Pruning** | `native/blueprint_batch.h`, `native/blueprint_dynamic.inc` | Add `cutoff_score` to `NBPolicy`. Prune candidates whose theoretical maximum score cannot exceed the 50th-best score. |
| **P2** | **Repair Diagnostic Scripts** | `scripts/diagnose_v3_funnel.py`, `scripts/measure_v3_floors.py` | Read nested `required_structures` counts; use native diagnostic counters (`nb_diag_get`). |
| **P3** | **Floor Calibration / Miss Budget** | `src/seed_search/realm/config.py:389` | Consider a balanced campaign profile with Outpost floor $= 1$ or Miss Budget $B \le 2$ to enable discovery every ~250k seeds. |

### Web UI Remediation

| Priority | Action Item | File / Target | Specific Fix |
| :---: | :--- | :--- | :--- |
| **P1** | **Add `dynamic2048` Search Profile** | `web-ui/src/constants/searchProfiles.json` | Add profile with `dynamic-envelope-2048-v3`, Overworld 2048, Nether 1024, v3 floors, and default misses = 0. |
| **P1** | **Fix Candidate Ranking Comparator** | `web-ui/src/utils/ranking.ts:7` | Add `'dynamic-envelope-2048-v3'` to score-first comparator branch with `radialKey` and `originDistanceSquared` tie-breaks. |
| **P2** | **Overhaul Seed Detail Modal** | `web-ui/src/components/SeedDetailModal.tsx:324` | Render 1,250 pt breakdown (Core Surplus, Optional, Luxury, Hub, Scenic, Village Spread, Treasure Bastion [+20], Nether Core [+20]); hide deficit penalties. |
| **P2** | **Unlock Biome Palette Selection** | `web-ui/src/components/FilterSidebar.tsx:36` | Allow biome toggling for `dynamic2048` profile in addition to `dynamic1664`. |
| **P3** | **Add Top-50 Ratchet Telemetry** | `web-ui/src/components/TelemetryBar.tsx` | Display current 50th-best cutoff score ($S_{50}$) and Top-50 saturation indicator in the live telemetry bar. |

---

## 7. Acceptance Criteria for Production Readiness

1. **Scoring & Evidence Idempotence:**
   - A natural or synthetic candidate evaluated under `dynamic-envelope-2048-v3` must yield the identical score, score components, evaluation center, and rank key across:
     - Direct native sweep output.
     - Native compact replay.
     - Standalone independent Python evaluation.
     - SQLite export, reload, and rescoring.
   - 100% of recorded Nether biome sample points and witnesses must lie strictly within half-open coordinates $[C_X/8 - 512, C_X/8 + 512) \times [C_Z/8 - 512, C_Z/8 + 512)$.
2. **Web UI End-to-End Integrity:**
   - Selecting `dynamic2048` in the UI generates an exact v3 launch command (`--profile dynamic2048 --max-misses 0`).
   - Candidates displayed in the candidate feed sort strictly by score DESC, radialKey ASC, originDistanceSquared ASC, and lexical ID ASC.
   - The Seed Detail Modal renders the exact 1,250-point score component breakdown matching the native evaluation receipt.
3. **Durable Top-50 Cutoff Integration:**
   - Once 50 candidates are discovered, `cutoff_score` ($S_{50}$) is propagated into native batches.
   - Re-running with different thread counts or batch sizes produces the identical top-50 candidate set and canonical ranking.
