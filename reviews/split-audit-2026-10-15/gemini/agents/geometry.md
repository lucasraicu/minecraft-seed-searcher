# Independent Systems and Software Audit Report: Geometry, Scoring, and Equivalence Selection (`dynamic-envelope-1664-v1`)

**Auditor:** G-GEO (Geometry, Scoring, and Independent Selection Auditor)  
**Specification:** Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes MC_26_50 (`dynamic-envelope-1664-v1`, Blueprint Revision 4.3)  
**Probe Directory:** `reviews/split-audit-2026-10-15/gemini/probes/geo/`  
**Master Probe Runner:** `reviews/split-audit-2026-10-15/gemini/probes/geo/run_all_probes.py`  
**Audit Date:** October 15, 2026  

---

## 1. Executive Summary

This audit evaluated the exact 2D sliding window geometry, equivalence cell slab generation, centroid pull and 16/8 snapping, conservative raw preflight culling, optional structure scoring, and 4-level hierarchical ranking for the active `dynamic-envelope-1664-v1` pipeline.

The audit verified that the primary geometric invariants—namely the 2D half-open window $[C_X-832, C_X+832)$, rational Nether scaling $[C_X/8-416, C_X/8+416)$, entry/exit event asymmetry, true negative integer floor division, raw Nether union bounds, and the 160 raw lattice event contributions—are mathematically sound and preserve all mandatory structure and biome transitions across equivalence cells.

However, the audit identified **one High-severity algorithmic divergence** in the Python reference oracle regarding optional structure counting during candidate selection, **one Medium-severity testing hole** in replay verification that masked this divergence, and **one Low-severity documentation contradiction** in `README.md` regarding Bastion and Shipwreck scoring formulas.

### Finding Summary Registry

| Finding ID | Severity | Title | Target File & Line Anchor | Status |
| :--- | :---: | :--- | :--- | :---: |
| **G-GEO-01** | **High** | Optional structure evaluation boundary drift during representative selection in Python oracle | [`src/seed_search/realm/dynamic.py#L82-L115`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L82-L115)<br>[`src/seed_search/realm/blueprint.py#L526`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L526) | Verified / Confirmed |
| **G-GEO-02** | **Medium** | Replay provider masks candidate selection divergence by bypassing equivalence cell solver | [`src/seed_search/realm/native_batch.py#L326`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L326)<br>[`src/seed_search/realm/blueprint.py#L483-L518`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L483-L518) | Verified / Confirmed |
| **G-GEO-03** | **Low** | Documentation contradiction in `README.md` for dynamic Bastion milestone and Shipwreck surplus | [`README.md#L16`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/README.md#L16) | Verified / Confirmed |

---

## 2. Detailed Findings

---

### Finding G-GEO-01: Optional Structure Evaluation Boundary Drift during Representative Candidate Selection in Python Reference Oracle

- **Severity:** High
- **Target File & Verbatim Anchors:**
  - [`src/seed_search/realm/dynamic.py#L81-L82`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L81-L82):
    ```python
    for name,points in inventories.items():
        if name in OPTIONAL_NAMES:continue
    ```
  - [`src/seed_search/realm/dynamic.py#L92-L95`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L92-L95):
    ```python
    center=(cx,cz);ow=overworld_bounds(center);nb=nether_bounds(center)
    counts={name:sum(contains(point,nb if name in NETHER_NAMES else ow)
                     for point in points) for name,points in inventories.items()}
    ```
  - [`src/seed_search/realm/dynamic.py#L112-L115`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L112-L115):
    ```python
    snapped=tuple(axes)
    radial=sum(w*math.hypot(x-snapped[0],z-snapped[1]) for x,z,w in captured)/weight if weight else 0.
    density=sum(weights[name]*counts.get(name,0) for name in DENSITY_NAMES)
    rows.append(Candidate(snapped,density,counts,deficits,radial))
    ```
  - [`src/seed_search/realm/blueprint.py#L526`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L526):
    ```python
    score=dynamic_score(item.counts,palette_index.luxuries(center),hub_bonus(structures,center))
    ```
  - Contrast with C implementation in [`native/blueprint_dynamic.inc#L440-L454`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L440-L454):
    ```c
    x=xx;z=zz;
    ...
    int score=nb_dynamic_score_values(counts,strong,mask>>13,hub);
    const int optional_points[5]={20,15,15,10,10};
    for(int k=0;k<5;k++)score+=optional_points[k]*nb_dynamic_count(&optional[k].viable,x,z,832,0,NULL,0);
    ```

#### Root Cause Analysis
1. In `dynamic.py`, `candidate_centers` excludes optional structures (`swamp_hut`, `igloo`, `trail_ruins`, `ocean_ruin`, `buried_treasure`) from the axis event lists `ex` and `ez`. Consequently, equivalence cell slabs $[ex[ix], ex[ix+1]-1] \times [ez[iz], ez[iz+1]-1]$ do **not** partition along optional structure boundaries.
2. Inside `candidate_centers`, `center = (cx, cz)` is chosen via `_nearest_zero(ex[xi], ex[xi+1]-1)` as the *unsnapped* representative center of the cell. Structure `counts` are then computed using `ow = overworld_bounds(center)` (the *unsnapped* window).
3. Next, centroid pull calculates `snapped = (xx, zz)` (snapped to multiples of 16 or 8). `Candidate` is instantiated as `Candidate(snapped, density, counts, deficits, radial)`, coupling the *snapped* coordinates with the *unsnapped* structure counts.
4. When `blueprint.py` ranks candidates in `center_key` (line 526), it calls `dynamic_score(item.counts, ...)` where `item.counts` provides the counts for optional structures.
5. In C (`native/blueprint_dynamic.inc:440-454`), lines 440 (`x=xx; z=zz;`) and 454 explicitly evaluate `nb_dynamic_count` for each optional structure at the **snapped** coordinates `(xx, zz)`, *not* at the unsnapped representative `(cx, cz)`.
6. Whenever an optional structure falls in the band between the unsnapped window $[cx-832, cx+832)$ and the snapped window $[xx-832, xx+832)$:
   - If the structure is outside $[cx-832, cx+832)$ but inside $[xx-832, xx+832)$, Python scores it as 0 while C awards full points (+15 for igloo/trail ruins, +20 for witch hut, +10 for ocean ruins/treasure).
   - If the structure is inside $[cx-832, cx+832)$ but outside $[xx-832, xx+832)$, Python erroneously awards points while C awards 0.
7. This causes candidate scores in Python to deviate from C by 10 to 35+ points, reordering candidates in Python's `center_key` and selecting a different representative anchor than C.

#### Concrete Reproduction Evidence
Run the dedicated probe:
```sh
PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task3_optional_drift.py
```
**Output:**
```
Found 754 candidate cells.
DIVERGENCE DETECTED!
  Candidate snapped center: (64, 0)
  Python candidate.counts['igloo']: 0
  C-style snapped count['igloo']:  1
  Score difference: 15 points
```
- Input: Equivalence cell with snapped center $C_X = 64, C_Z = 0$, unsnapped center $cx = 0, cz = 0$.
- Igloo position: $(840, 0)$.
- Unsnapped window $[0-832, 0+832) = [-832, 832)$: $840$ is OUTSIDE $\implies$ Python count = 0.
- Snapped window $[64-832, 64+832) = [-768, 896)$: $840$ is INSIDE $\implies$ C count = 1.
- Expected behavior: Python candidate scoring must count optional structures at `item.center` (snapped) to maintain parity with C.
- Actual behavior: Python uses frozen unsnapped counts from `item.counts`.

#### Minimal Unapplied Fix
In [`src/seed_search/realm/blueprint.py#L522-L527`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L522-L527):
```diff
--- a/src/seed_search/realm/blueprint.py
+++ b/src/seed_search/realm/blueprint.py
@@ -523,7 +523,9 @@ def evaluate_dynamic_seed(index,seed,cfg,*,backend_factory=Backend,combined=True
                 center=item.center
                 structures={name:[p for p in points if contains(p,overworld_bounds(center))]
                             for name,points in all_points.items() if name in OVERWORLD_NAMES}
-                score=dynamic_score(item.counts,palette_index.luxuries(center),hub_bonus(structures,center))
+                opt_counts={name:sum(contains(p,overworld_bounds(center)) for p in all_points.get(name,()))
+                            for name in OPTIONAL_NAMES}
+                score=dynamic_score({**item.counts,**opt_counts},palette_index.luxuries(center),hub_bonus(structures,center))
                 return (len(item.deficits),-score,round(item.radial,6),center[0]**2+center[1]**2,*center)
             eligible=sorted((item for item in eligible if palette_index.valid(item.center)),key=center_key)
```

---

### Finding G-GEO-02: Replay Provider Masks Candidate Selection Parity by Bypassing Equivalence Cell Solver

- **Severity:** Medium
- **Target File & Verbatim Anchors:**
  - [`src/seed_search/realm/native_batch.py#L326`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L326):
    ```python
    self.dynamic_center=(int(result.anchors[0].x),int(result.anchors[0].z)) if dynamic_policy(prototype.cfg) and result.nanchors else None
    ```
  - [`src/seed_search/realm/blueprint.py#L483-L485`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L483-L485):
    ```python
    replay_center=getattr(backend,'dynamic_center',None)
    if getattr(backend,'dynamic_no_anchor',False):eligible=[]
    elif replay_center is None:
        ...
    else:eligible=[type('Selected',(),{'center':tuple(replay_center)})()]
    ```
  - [`tests/test_dynamic_baseline.py#L31`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/tests/test_dynamic_baseline.py#L31):
    ```python
    if name in ('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure'):return [],[]
    ```
  - [`native/blueprint_dynamic.inc#L221`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L221):
    ```c
    if(w->fixture)return 0;
    ```

#### Root Cause Analysis
1. In `native_batch.py`, `ReplayProvider` sets `self.dynamic_center` directly from C's result anchor `result.anchors[0]`.
2. When `evaluate_dynamic_seed` runs against `ReplayProvider`, it detects `replay_center is not None` and creates a single dummy candidate `eligible = [Selected(replay_center)]`, bypassing `candidate_centers`, `center_key`, and `dynamic_score` during candidate search.
3. In `tests/test_dynamic_baseline.py`, `test_native_python_dynamic_fixture_agreement` tests `adapter='replay'` and `reference`. However:
   - For `adapter='replay'`, `candidate_centers` is never invoked.
   - For `reference` (`DynamicFixtureBackend`), all optional structures return empty lists `[], []`.
   - In C, `if (w->fixture) return 0;` bypasses optional structure scanning entirely.
4. As a result, the test suite never verified independent candidate selection between C and Python when optional structures are present, allowing G-GEO-01 to remain undetected.

#### Minimal Unapplied Fix
In `native_batch.py` or integration tests, execute candidate selection on the complete macro observations supplied by C and assert that Python's `candidate_centers` selects the exact same center as `result.anchors[0]` instead of bypassing candidate resolution.

---

### Finding G-GEO-03: Documentation Contradiction in `README.md` for Dynamic Bastion Milestone and Shipwreck Surplus

- **Severity:** Low (Documentation & Specification Alignment)
- **Target File & Verbatim Anchor:**
  - [`README.md#L16`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/README.md#L16):
    ```markdown
    The active score awards **50 points each for a second Mansion and a second distinct predicted Stronghold**, **30 for a second qualifying Monument**, **20 per Bastion above three**, and **5 per qualifying Shipwreck above five**.
    ```
  - Contrast with active code:
    - Bastion in C ([`native/blueprint_batch.inc#L262`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L262)): `(n[11]>=3?20:0)`
    - Bastion in Python ([`src/seed_search/realm/blueprint.py#L449`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L449)): `sum(20*(n(name)>=3) for name in ('desert_pyramid','jungle_temple','outpost','fortress','bastion'))`
    - Shipwreck in C ([`native/blueprint_batch.inc#L263`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L263)): `(n[8]>6?(n[8]-6)*5:0)`
    - Shipwreck in Python ([`src/seed_search/realm/blueprint.py#L450`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L450)): `max(0,n('shipwreck')-6)*5`
  - Approved Specification ([`MASTER_SEED_BLUEPRINT.md#L182, L193, L197-L198`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L182)):
    - Line 182: `3rd Bastion Remnant inside borders (one-time milestone; not linear): +20 pts`
    - Line 193: `Shipwrecks above 6: +5 pts each (linear surplus)`
    - Line 197-198: Explicit User Decision Record confirming milestones are one-time increments, not linear.

#### Root Cause Analysis
`README.md` line 16 contains stale wording carried over from historical Schema 3 / `locked` profile scoring (`native/blueprint_batch.inc:284, 290` where Bastion was `(n[11]>3?(n[11]-3)*20:0)` and Shipwreck was `(n[8]>5?(n[8]-5)*5:0)`). In the active `dynamic-envelope-1664-v1` pipeline:
1. Bastion is awarded as a **one-time milestone of +20 pts at count $\ge 3$**, NOT "+20 per Bastion above three" (which would award 0 for 3 Bastions and 20 for 4).
2. Shipwreck is awarded as **+5 pts each above six** (`n > 6`), NOT "above five" (which would award 5 pts for 6 Shipwrecks).

#### Concrete Reproduction Evidence
Run the dedicated probe:
```sh
PYTHONPATH=. ./.venv/bin/python reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task5_scoring.py
```
**Output:**
```
Testing Bastion scoring:
  Bastion count = 1: score = 0
  Bastion count = 2: score = 0
  Bastion count = 3: score = 20
  Bastion count = 4: score = 20
  Bastion count = 5: score = 20

Testing Shipwreck scoring:
  Shipwreck count = 4: score = 0
  Shipwreck count = 5: score = 0
  Shipwreck count = 6: score = 0
  Shipwreck count = 7: score = 5
  Shipwreck count = 8: score = 10
```

#### Minimal Unapplied Fix
In [`README.md#L16`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/README.md#L16):
```diff
--- a/README.md
+++ b/README.md
@@ -16,3 +16,3 @@
-The active score awards **50 points each for a second Mansion and a second distinct predicted Stronghold**, **30 for a second qualifying Monument**, **20 per Bastion above three**, and **5 per qualifying Shipwreck above five**. River evidence and its score commit with finest-resolution marine/terrain completion and survive rescoring.
+The active score awards **50 points each for a second Mansion and a second distinct predicted Stronghold**, **30 for a second qualifying Monument**, **20 for reaching three Bastions (one-time milestone)**, and **5 per qualifying Shipwreck above six**. River evidence and its score commit with finest-resolution marine/terrain completion and survive rescoring.
```

---

## 3. Systematic Section-by-Section Audit

### 3.1 Window Slabs, Boundaries, Integer Entry/Exit Events, and Negative Division

#### Geometric Half-Open Window Equations
The playable realm is defined by two centered rectangles:
1. **Overworld ($1664 \times 1664$):** $[C_X - 832, C_X + 832) \times [C_Z - 832, C_Z + 832)$.
2. **Nether ($832 \times 832$):** $[C_X/8 - 416, C_X/8 + 416) \times [C_Z/8 - 416, C_Z/8 + 416)$.
   Since snapped centers are multiples of 8 ($C_X, C_Z \in 8\mathbb{Z}$), the Nether center $C_X/8, C_Z/8$ is always an exact integer.

#### Entry and Exit Boundary Asymmetry
For an integer Overworld point $P_X$ to be captured by $[C_X - 832, C_X + 832)$:
$$C_X - 832 \le P_X < C_X + 832 \iff P_X - 831 \le C_X \le P_X + 832$$
As $C_X$ increases from $-\infty$:
- **Entry Event:** $C_X = P_X - 831$ (first integer inside window).
- **Exit Event:** $C_X = P_X + 833$ (first integer outside window; $C_X - 832 = P_X + 1 > P_X$).

For an integer Nether point $P_{N,X}$ to be captured by $[C_X/8 - 416, C_X/8 + 416)$:
$$C_X/8 - 416 \le P_{N,X} < C_X/8 + 416 \iff 8 \cdot (P_{N,X} - 416) < C_X \le 8 \cdot (P_{N,X} + 416)$$
- **Nether Entry Event:** $C_X = 8 \cdot (P_{N,X} - 416) + 1 = 8 \cdot P_{N,X} - 3327$.
- **Nether Exit Event:** $C_X = 8 \cdot (P_{N,X} + 416) + 1 = 8 \cdot P_{N,X} + 3329$.

Both C (`native/blueprint_dynamic.inc:400-403`) and Python (`src/seed_search/realm/dynamic.py:44-51, 58-60`) strictly generate and respect these asymmetric boundaries.

#### Audit of the 160 Raw Lattice Events per Axis
The world-aligned biome lattice evaluates samples at spacing 64:
- Overworld samples: $s \in [-1984, 1984]$ with step 64 $\implies \frac{1984 - (-1984)}{64} + 1 = 63$ sample points.
  Each point generates 2 events ($s - 831$ and $s + 833$) $\implies 63 \times 2 = 126$ raw Overworld lattice events.
- Nether samples: $n \in [-512, 512]$ with step 64 $\implies \frac{512 - (-512)}{64} + 1 = 17$ sample points.
  Each point generates 2 events ($8*(n - 416) + 1$ and $8*(n + 416) + 1$) $\implies 17 \times 2 = 34$ raw Nether lattice events.
- **Total raw lattice events per axis:** $126 + 34 = 160$.

Audited in [`reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task1_events.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task1_events.py):
- Exactly 160 raw lattice events are generated in C (`native/blueprint_dynamic.inc:386-393`) and Python (`dynamic.py:58-59`).
- Every raw event coordinate satisfies $E \equiv 1 \pmod{64}$ (since $-831 \equiv 833 \equiv -3327 \equiv 3329 \equiv 1 \pmod{64}$).
- When clipped to the center search domain $(-1168, 1168]$, exactly 82 events survive, collapsing to 37 unique coordinates due to window width alignment ($1664 = 26 \times 64$).
- No membership transitions are lost or distorted.

#### Mathematical Verification of Negative Floor Division
- Cubiomes `floordiv(int32_t a, int32_t b)` correctly implements mathematical flooring: `q = a / b; r = a % b; return q - ((a ^ b) < 0 && !!r);`.
- `nb_dynamic_floor64(int64_t value, int64_t divisor)` evaluates `q = value / divisor; return q - (value % divisor < 0);`. Since divisor is always positive (`step * weight > 0`), this correctly floors negative 64-bit coordinates.
- Snapping logic in C (`nb_dynamic_snap`) and Python (`dynamic.py:104-110`) clamps `rounded` within `[lower, upper]` (multiples of 16, falling back to 8).

---

### 3.2 Membership Invariance of Mandatory Structures and Biome Witnesses

1. **Equivalence Slabs:**
   Each 2D cell is formed by the Cartesian product $[ex[ix], ex[ix+1]-1] \times [ez[iz], ez[iz+1]-1]$.
2. **Invariance Guarantee:**
   Because all mandatory structure coordinates (Stronghold, Mansion, Outpost, Fortress, Bastion, etc.) and all 160 raw lattice coordinates are included in $ex$ and $ez$, **no mandatory structure or lattice point crosses into or out of the window for any integer coordinate within the cell**.
3. **Prefix Table Alignment:**
   Tested in [`probe_task2_invariance.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task2_invariance.py) and [`probe_task2_nether.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task2_nether.py):
   - Overworld prefix transitions for `x0` and `x1` match the raw lattice events with symmetric difference $\emptyset$.
   - Nether prefix transitions for `x0` and `x1` match the Nether lattice events with symmetric difference $\emptyset$.
   - Biome palette qualification evaluated at any point in the cell applies uniformly across the entire cell.

---

### 3.3 Conservative Raw Preflight Culling and Union Bounding Box

Audited [`native/blueprint_dynamic.inc#L241-L302`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L241-L302):
1. **Nether Raw Slabs:**
   `nb_dynamic_raw_bounds` collects raw Fortress and Bastion starts in $[-562, 562)^2$. It tests all cells with step-8 aligned centers against `fort_goal` and `bast_goal`.
2. **Union Bounding Box Soundness:**
   For all cells meeting the raw Nether goals, it accumulates the minimum and maximum multiple-of-8 centers:
   $xmin \le C_X \le xmax$ and $zmin \le C_Z \le zmax$.
   The union window is computed as:
   `feasible[0] = xmin - 832`, `feasible[1] = zmin - 832`, `feasible[2] = xmax + 831`, `feasible[3] = zmax + 831`.
   **Mathematical proof of safety:** Any viable center $C$ must satisfy $xmin \le C_X \le xmax$ and $zmin \le C_Z \le zmax$. Any Overworld structure captured by $C$ has coordinate $p_x \in [C_X - 832, C_X + 831]$. Since $xmin \le C_X \le xmax$, $feasible[0] \le p_x \le feasible[2]$. Therefore, no captured structure can exist outside `feasible`.
3. **Flexible Hard Floors vs. Strict Targets:**
   In line 296:
   `int goal = (w->p->flexible_mask & (1u << slot)) ? w->p->floors[slot] : (slot == 12 ? w->p->outpost_goal : w->p->goals[slot]);`
   For flexible structures (Villages, Trial Chambers, Ancient Cities), `nb_raw_atleast` checks against the **hard floor** (e.g. 8 for villages, 7 for trial chambers, 3 for ancient cities), *not* the ideal target. This guarantees that seeds requiring deficit consumption are never falsely culled.
4. **Conclusion:** Culling is strictly conservative; no valid viable seed can be rejected by preflight.

---

### 3.4 Comprehensive Scoring Matrix, Optional Bonuses, and Deficit Tiers

Audited in [`probe_scoring_matrix.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_scoring_matrix.py):
The active scoring engine in `native/blueprint_batch.inc:257-275` and `src/seed_search/realm/blueprint.py:443-456` matches the approved Revision 4.3 specification across all 27 audited test cases:

```
+---------------------------------------------------------------------------------------+
| Category / Feature           | Rule / Threshold          | Points Awarded             |
+---------------------------------------------------------------------------------------+
| 2nd Woodland Mansion         | Count >= 2                | +50 pts (one-time jackpot) |
| 2nd Stronghold               | Count >= 2                | +50 pts (one-time jackpot) |
| 2nd Ocean Monument           | Count >= 2                | +30 pts (one-time jackpot) |
| Villages (9th+)              | Count > 8                 | +25 pts each (linear)      |
| Trial Chambers (8th+)        | Count > 7                 | +10 pts each (linear)      |
| Ancient City (4th)           | Count >= 4                | +25 pts (one-time)         |
| Desert Pyramid (3rd)         | Count >= 3                | +20 pts (one-time)         |
| Jungle Temple (3rd)          | Count >= 3                | +20 pts (one-time)         |
| Pillager Outpost (3rd)       | Count >= 3                | +20 pts (one-time)         |
| Nether Fortress (3rd)        | Count >= 3                | +20 pts (one-time)         |
| Bastion Remnant (3rd)        | Count >= 3                | +20 pts (one-time)         |
| Shipwrecks (7th+)            | Count > 6                 | +5 pts each (linear)       |
| Ruined Portals (8th+)        | Count > 7                 | +5 pts each (linear)       |
| Mineshafts (16th+)           | Count > 15                | +1 pt each (linear)        |
| 512m Starter Hub Bonus       | Proximity d <= 512m       | Capped at +40 pts          |
| 10 Luxury Biomes             | Surface witness at Y=63   | Table 4.3 (10–30 pts each) |
| 5 Optional Structures        | Viable start in 1664 sq   | 20, 15, 15, 10, 10 pts     |
+---------------------------------------------------------------------------------------+
```

---

### 3.5 4-Level Leaderboard Sort Order Parity

Audited [`src/seed_search/realm/leaderboard.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/leaderboard.py) vs [`native/blueprint_dynamic.inc#L6-L17`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L6-L17) vs [`src/seed_search/realm/blueprint.py#L527`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L527):

1. **Level 1 (Deficit Tier ASC):**
   `ranking_tier = deficits` (0, 1, or 2 misses). C checks `a->deficits < b->deficits`.
2. **Level 2 (Score DESC):**
   `smart_score DESC`. C checks `a->score > b->score`.
3. **Level 3 (Weighted Radial Distance ASC):**
   `weighted_radial_dist ASC`. C rounds to 6 decimal places (`llround(a->radial * 1e6)`), matching Python's `round(item.radial, 6)`.
4. **Level 4 (Origin Distance ASC):**
   `origin_distance ASC`. C checks $x^2 + z^2$ (`da < db`), matching Python's `center[0]**2 + center[1]**2`.
5. **Tie-Breakers:**
   C breaks ties by `x` then `z`, matching Python's `*center`.

Database view `candidate_leaderboard_view` strictly orders by `ranking_tier, unmet_requirements, smart_score DESC, weighted_radial_dist, origin_distance, id`, preserving identical rank ordering in SQLite and native memory.

---

## 4. Verification Probe Catalog

All probe scripts reside in `reviews/split-audit-2026-10-15/gemini/probes/geo/` and are executable via `./.venv/bin/python`:

1. [`probe_task1_events.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task1_events.py): Enumerates all 160 raw lattice events, partitions domain boundaries, and verifies $64k+1$ lattice alignment.
2. [`probe_nether_equiv.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_nether_equiv.py): Tests integer inequality $8(P_X - 416) < x \le 8(P_X + 416)$ against rational bounds for all $x \in [-1168, 1168]$.
3. [`probe_task2_invariance.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task2_invariance.py): Proves Overworld biome prefix transitions match raw lattice events with zero symmetric difference.
4. [`probe_task2_nether.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task2_nether.py): Proves Nether biome prefix transitions match raw Nether lattice events with zero symmetric difference.
5. [`probe_task3_optional_drift.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task3_optional_drift.py): Demonstrates G-GEO-01 divergence between unsnapped candidate selection and snapped scoring.
6. [`probe_task5_scoring.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_task5_scoring.py): Proves G-GEO-03 discrepancy in `README.md` for Bastion and Shipwreck thresholds.
7. [`probe_scoring_matrix.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/probe_scoring_matrix.py): Runs 27 test cases comparing C formula against Python `dynamic_score`.
8. [`run_all_probes.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/split-audit-2026-10-15/gemini/probes/geo/run_all_probes.py): Master test runner executing all probes.
