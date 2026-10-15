> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Geometry & Snapping Oracle Findings

**Document Version:** 1.0
**Audit Target:** `MASTER_SEED_BLUEPRINT.md` (Revision 4.1)
**Author:** Task 1 Independent Geometry & Snapping Oracle
**Artifacts Generated:**
- Reference Implementation: [`oracle.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/gemini/geometry/oracle.py)
- Test Suite: [`test_cases.json`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/reviews/gemini/geometry/test_cases.json)

---

## 1. Executive Summary & Verification Verdict

An independent mathematical oracle was developed to verify the geometry, center bounds, safe intervals, centroid weighting, and snapping protocols specified in `MASTER_SEED_BLUEPRINT.md`. The oracle uses pure rational arithmetic (`fractions.Fraction`) and was validated against discrete brute-force scans over synthetic domains and a 38-case test suite.

### Core Verdict
The sliding-window concept ($1664 \times 1664$ Overworld, $832 \times 832$ Nether) is **mathematically sound and geometrically feasible**, but the blueprint text contains **one critical boundary specification contradiction** and **two subtle snapping edge cases (traps)** that must be formally clarified to avoid false seed rejections or inadvertent structure loss.

| Component | Blueprint Text | Discrete Reality | Impact / Risk |
| :--- | :--- | :--- | :--- |
| **Overworld Window** | Closed: $[C_X \pm 832, C_Z \pm 832]$ | Half-Open: $[C_X - 832, C_X + 832)$ | Closed window spans **1,665 blocks** (not 1,664; not $104 \times 16$). |
| **Overworld Safe Interval** | $[X_i - 832, X_i + 832]$ | $[X_i - 831, X_i + 832]$ | Setting $C = X_i - 832$ leaves $X_i$ on the excluded East border, **losing the structure**. |
| **Nether Safe Interval** | $[8X_{N,j} - 3328, 8X_{N,j} + 3328]$ | $[8X_{N,j} - 3327, 8X_{N,j} + 3328]$ | Setting $C = 8X_N - 3328$ **loses the Nether structure**. |
| **Defense 3 Snapping Formula** | Unconstrained: $16 \lfloor (C^* + 8)/16 \rfloor$ | Constrained interval search | Naive formula rounds outside $\mathcal{S}_{\text{safe}}$ even when valid multiples of 16 exist (**False Reject**). |
| **Tight Safe Intervals** | Multiple-of-8 fallback | Interval width $< 8$ | If width $< 8$, no multiple of 8 exists; forced snapping **violates hard floors**. |

---

## 2. Geometry: Continuous vs Discrete & Half-Open vs Closed Bounds

### 2.1 The 1,664 vs 1,665 Block Discrepancy
In `MASTER_SEED_BLUEPRINT.md` Section 1, the Playable Overworld is defined as:
> *"Bounded within $[C_X - 832, C_Z - 832, C_X + 832, C_Z + 832]$... Perfect chunk multiple ($104 \times 16$)."*

In discrete block coordinates:
- A **closed** integer interval $[A, B]$ contains $(B - A + 1)$ blocks.
  $$(C_X + 832) - (C_X - 832) + 1 = 1664 + 1 = \mathbf{1665\text{ blocks}}$$
  $1665$ blocks is $104.0625$ chunks, which does **not** cleanly align to 16-block chunk borders.
- A **half-open** interval $[C_X - 832, C_X + 832)$ contains:
  $$(C_X + 832) - (C_X - 832) = \mathbf{1664\text{ blocks}} = 104 \times 16\text{ blocks}$$
  This exactly equals 104 chunks.

### 2.2 Four-Border Containment Behavior
Under the half-open chunk-aligned convention $[C_X - 832, C_X + 832) \times [C_Z - 832, C_Z + 832)$:
1. **West Border ($X = C_X - 832$):** **INCLUDED**.
2. **North Border ($Z = C_Z - 832$):** **INCLUDED**.
3. **East Border ($X = C_X + 832$):** **EXCLUDED** (point is on outer boundary). The easternmost playable block is $X = C_X + 831$.
4. **South Border ($Z = C_Z + 832$):** **EXCLUDED** (point is on outer boundary). The southernmost playable block is $Z = C_Z + 831$.

> [!IMPORTANT]
> The Bedrock World Border particle barrier is rendered at block boundaries. An Overworld border centered at $C$ with radius 832 encloses coordinates $X \in [C - 832, C + 832)$. Structure bounding boxes placed exactly at $X = C + 832$ are technically outside the playable volume.

---

## 3. Safe Interval Formulation: The $+1$ Asymmetry Contradiction

### 3.1 Mathematical Derivation
Let structure coordinate be $X_i$. For the structure to be contained in the Overworld window centered at $C_X$:
$$C_X - 832 \le X_i < C_X + 832$$

Solving for $C_X$:
1. From $C_X - 832 \le X_i \implies C_X \le X_i + 832$.
2. From $X_i < C_X + 832 \implies C_X > X_i - 832$.

Because $C_X$ is constrained to integer block coordinates:
$$C_X > X_i - 832 \iff C_X \ge X_i - 832 + 1 = \mathbf{X_i - 831}$$

Thus, the exact safe interval for $C_X$ is:
$$\mathcal{S}_{\text{OW}, i} = [X_i - 831,\; X_i + 832]$$

### 3.2 The Blueprint Contradiction
`MASTER_SEED_BLUEPRINT.md` Section 2 (lines 53–54) states:
> *"Overworld Safe Interval: For every required Overworld structure $i$, $[X_i - 832, X_i + 832]$"*
> *"Nether Safe Interval: For every required Nether Fortress and Bastion $j$, projected as $[8X_{N,j} - 3328, 8X_{N,j} + 3328]$"*

**Failure Demonstration:**
Suppose an Overworld structure is at $X_i = 100$.
- Blueprint safe interval lower bound: $C_X = 100 - 832 = -732$.
- Center window at $C_X = -732$:
  $$[-732 - 832,\; -732 + 832) = [-1564,\; 100)$$
- Does $[-1564, 100)$ contain $100$?
  $$100 < 100 \implies \mathbf{FALSE}$$
The structure is **excluded and lost**.

**Nether Asymmetry:**
For Nether structure at $X_N$:
$$\frac{C_X}{8} - 416 \le X_N < \frac{C_X}{8} + 416 \iff 8X_N - 3328 < C_X \le 8X_N + 3328$$
$$\implies C_X \in [8X_N - 3327,\; 8X_N + 3328]$$
At the blueprint's lower bound $C_X = 8X_N - 3328$, the Nether structure is **excluded and lost**.

> [!NOTE]
> Codebase inspection reveals that production code (`native/blueprint_dynamic.inc` line 160 and `src/seed_search/realm/dynamic.py` line 45) already uses `x - 831` and `8*(x-416) + 1 = 8*x - 3327`. Production code silently implemented the correct half-open boundary logic, while the blueprint documentation remained uncorrected.

---

## 4. Macro-Envelope Derivation & Bounds Verification

The blueprint specifies:
- Overworld Macro-Envelope: $4000 \times 4000$ centered at $(0, 0)$, i.e., $X, Z \in [-2000, 2000]$.
- Overworld Playable Window: $1664 \times 1664$, radius $832$.
- Nether Preflight Envelope: $1124 \times 1124$ centered at $(0, 0)$, radius $562$.
- Nether Playable Window: $832 \times 832$, radius $416$.

### 4.1 Derivation of $C \in [-1168, 1168]$
For the playable Overworld to remain completely within the macro-envelope:
$$\begin{aligned}
C_X - 832 &\ge -2000 \implies C_X \ge -1168 \\
C_X + 832 &\le 2000 \implies C_X \le 1168
\end{aligned}$$
Thus, $(C_X, C_Z) \in [-1168, 1168]^2$ is **exact and optimal**.

### 4.2 Derivation of Nether Envelope $[-562, 562]$
Because Nether center is $(C_X/8, C_Z/8)$:
$$\frac{C_X}{8} \in \left[ \frac{-1168}{8}, \frac{1168}{8} \right] = [-146, 146]$$
Adding the Nether half-width ($416\text{m}$):
$$\text{Max Nether Extent} = 146 + 416 = \mathbf{562\text{m}}$$
Thus, the Nether preflight envelope of $1124 \times 1124$ ($[-562, 562]$) is mathematically exact.

---

## 5. Nether Coordinate Scaling & Addon Constraints

1. **8:1 Coordinate Mapping:**
   Each Nether block corresponds to 8 Overworld blocks. The Nether window center $(C_X/8, C_Z/8)$ is rational.
2. **Addon Integer Requirement:**
   The Bedrock World Border Addon command:
   ```mcfunction
   /scriptevent worldborder:center nether <X> <Z>
   ```
   requires integer block coordinates.
3. **Fractional Center Drift:**
   If $C_X$ is not a multiple of 8, $C_X/8$ is fractional (e.g. $C_X = 4 \implies C_N = 0.5$).
   In game, the addon rounds $0.5$ to $0$ or $1$, introducing an Overworld discrepancy of up to $4$ blocks between the solver's assumed window and the actual in-game barrier.
4. **Snapping Mandate:**
   Snapping $C_X$ to a multiple of 16 (or fallback 8) ensures $C_X / 8 = 2k$, guaranteeing that the Nether center is an **exact integer block coordinate**.

---

## 6. Centroid Magnet Pull & Structure Weights

Section 2 (Defense 2) defines the pull target:
$$C_X^* = \frac{\sum_{i=1}^N \omega_i X_i}{\sum_{i=1}^N \omega_i}, \qquad C_Z^* = \frac{\sum_{i=1}^N \omega_i Z_i}{\sum_{i=1}^N \omega_i}$$

### 6.1 Weight Analysis
The 11 structure categories and weights are:
- **Weight 3:** Villages
- **Weight 2:** Trial Chambers, Ruined Portals, Ancient Cities
- **Weight 1:** Pillager Outposts, Desert Pyramids, Jungle Temples, Woodland Mansions, Ocean Monuments, Strongholds, Shipwrecks

All weights are strictly $\le 3$, capping the pull of rare mega-structures and ensuring settlement density dominates center selection.

### 6.2 Nether Structures Omission
Nether Fortresses and Bastions are **not** included in the centroid pull formula (they have no assigned $\omega_i$). Instead, they act exclusively as bounding constraints on $\mathcal{S}_{\text{safe}}$. This is intentional and correct: Overworld center $(C_X, C_Z)$ anchors player activity and world border rendering in the Overworld, while Nether structures only require retention within $[C_X/8 \pm 416]$.

---

## 7. Snapping Arithmetic, Rounding Ties, and Trap Analysis

### 7.1 Floor Division & Negative Ties
The blueprint snapping formula is:
$$C_{X,\text{snap}} = 16 \times \left\lfloor \frac{C_X^* + 8}{16} \right\rfloor$$

Under integer floor division:
- $C^* = 8 \implies 16 \times \lfloor 16/16 \rfloor = 16$ (tie rounds up).
- $C^* = -8 \implies 16 \times \lfloor 0/16 \rfloor = 0$ (tie rounds up towards $+\infty$).
- $C^* = -24 \implies 16 \times \lfloor -16/16 \rfloor = -16$ (tie rounds up towards $+\infty$).

Ties always break towards $+\infty$ (round-half-up).

### 7.2 Trap 1: Naive Snapping Formula vs Constrained Search
The blueprint states:
1. Compute $C_{\text{snap}} = 16 \lfloor (C^* + 8)/16 \rfloor$.
2. If $C_{\text{snap}} \in \mathcal{S}_{\text{safe}}$, accept.
3. Else, fallback to 8: $C_{\text{snap}} = 8 \lfloor (C^* + 4)/8 \rfloor$.

**The False-Reject Failure Mode:**
Suppose $\mathcal{S}_{\text{safe}} = [17, 35]$.
- Multiples of 16 in $[17, 35]$: **$32$** exists!
- Multiples of 8 in $[17, 35]$: **$24, 32$** exist!
- Suppose clamped centroid $C^* = 18 \in [17, 35]$.
- Naive 16 formula: $16 \lfloor (18+8)/16 \rfloor = 16 \times 1 = \mathbf{16}$.
  $16 \notin [17, 35]$ (fails retention check).
- Naive 8 formula: $8 \lfloor (18+4)/8 \rfloor = 8 \times 2 = \mathbf{16}$.
  $16 \notin [17, 35]$ (fails fallback check).

The literal blueprint procedure **rejects the seed**, despite the fact that a valid multiple of 16 ($32$) and multiple of 8 ($24$) exist inside $\mathcal{S}_{\text{safe}}$.

> [!TIP]
> **Resolution:** Snapping must be implemented as a **constrained nearest-grid search**:
> Find $\arg\min_{k} |k \cdot 16 - C^*|$ subject to $k \cdot 16 \in \mathcal{S}_{\text{safe}}$.
> Only fall back to 8 if $\{k \cdot 16 \mid k \cdot 16 \in \mathcal{S}_{\text{safe}}\} = \emptyset$.

### 7.3 Trap 2: Ultra-Tight Intervals (No Valid Snapped Center)
When multiple floor structures severely restrict the center window, $\mathcal{S}_{\text{safe}}$ can have width $< 8$.
- Example: $\mathcal{S}_{\text{safe}} = [91, 95]$ (width 5).
- Nearest multiples of 16: $80, 96$. Neither is in $[91, 95]$.
- Nearest multiples of 8: $88, 96$. Neither is in $[91, 95]$.

If an algorithm forces snapping to 88 or 96:
- The structure requiring $C \ge 91$ or $C \le 95$ is placed outside the border.
- **A mandatory hard-floor structure is lost.**

---

## 8. Synthetic Domain Exhaustive Validation

The oracle implementation was validated by brute-force scanning:
1. For 7 coordinate cases spanning $[-1200, 1200]$, every integer center $C \in [X - 1000, X + 1000]$ was tested against `is_in_overworld`. The brute-force set of valid centers matched `overworld_safe_interval_1d` with **100% exactness**.
2. For 5 Nether coordinate cases spanning $[-150, 150]$, every integer center $C \in [8X_N - 3500, 8X_N + 3500]$ was tested against `is_in_nether`. The brute-force set matched `nether_safe_interval_1d` with **100% exactness**.
3. Multi-structure joint intersections were validated by 2D brute-force grid testing.
4. All 38 test cases in `test_cases.json` passed with zero errors.

---

## 9. Mathematical Checks vs Minecraft Generation Realities

It is vital to distinguish geometric bounding box checks from in-game structure generation:
1. **Point Coordinates vs Physical Structure Volumes:**
   The sliding window operates on structure registration points (usually the start chunk or bounding box origin). Large structures (Woodland Mansions: $64 \times 64$; Ocean Monuments: $58 \times 58$; Strongholds: extensive room chains) can cross the world border even if their registration coordinate is inside the boundary.
2. **Biome Noise vs PRNG Grid Viability:**
   A center that geometrically encompasses all PRNG slots does not guarantee structure generation if the local terrain or biome noise is invalid.
3. **End Portal Room Integrity:**
   Stronghold registration inside the boundary does not guarantee an intact End Portal room (which can be clipped by cave carvers or village wells in Bedrock). Stage 5 BDS verification remains necessary.

---

## 10. Summary of Actionable Recommendations

1. **Update `MASTER_SEED_BLUEPRINT.md` Sections 1 & 2:**
   - Explicitly define window intervals as half-open: $[C_X - 832, C_X + 832)$.
   - Correct the safe interval formulas to $[X_i - 831, X_i + 832]$ (Overworld) and $[8X_N - 3327, 8X_N + 3328]$ (Nether).
2. **Specify Constrained Grid Search for Defense 3:**
   - Update Defense 3 to specify picking the nearest multiple of 16 *within* $\mathcal{S}_{\text{safe}}$, rather than unconstrained rounding followed by rejection.
3. **Handle Empty Grid Intersections:**
   - Explicitly define the failure behavior when $\mathcal{S}_{\text{safe}}$ contains no multiple of 8 (seed must be classified as unviable for addon border snapping).
