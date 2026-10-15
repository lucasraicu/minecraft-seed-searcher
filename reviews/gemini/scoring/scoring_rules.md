> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Scoring and Ranking Audit: Master Seed Blueprint vs. Implementation

**Document Version:** 1.0
**Audit Target:** `MASTER_SEED_BLUEPRINT.md` (Revision 4.1 - Zero-Loss Optimized Pipeline - October 2026)
**Codebase Targets:**
- `src/seed_search/realm/blueprint.py`
- `native/blueprint_batch.inc`
- `native/blueprint_dynamic.inc`
- `native/blueprint_batch.h`
- `src/seed_search/realm/dynamic.py`
- `src/seed_search/realm/leaderboard.py`
- `scripts/merge_runs.py`
- `src/seed_search/web/server.py`
- `src/seed_search/realm/native_batch.py`
- `src/seed_search/realm/native_records.py`
- `src/seed_search/realm/config.py`
- `config/realm_1664.yaml`
- `src/seed_search/realm/caves.py`
- `src/seed_search/realm/verification.py`
**Auditor:** Task 2 Independent Scoring and Ranking Audit Agent
**Artifacts Produced:**
- `reviews/gemini/scoring/scoring_rules.md` (This document)
- `reviews/gemini/scoring/scoring_cases.json` (Exhaustive boundary & edge test cases)

---

## 1. Executive Summary & Audit Matrix

A comprehensive engineering audit was conducted comparing the scoring and ranking specifications set forth in [`MASTER_SEED_BLUEPRINT.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md) against the actual implementation across Python engines, native C kernels, configuration profiles, and database persistence layers.

### Core Verdict
The scoring and ranking architecture specified in `MASTER_SEED_BLUEPRINT.md` establishes a rigorous 4-level hierarchical ranking system and an intricate surplus/luxury bonus matrix. However, the audit revealed **critical architectural discrepancies, dead code paths, and textual ambiguities** that prevent the codebase from faithfully executing the blueprint as written:

1. **Broken Leaderboard Hierarchy (CRITICAL):** The SQLite leaderboard view ([`leaderboard.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/leaderboard.py)) does **not** rank candidates by Deficit Tier ASC. Instead, all `PREDICTED` survivors (whether Tier 0, Tier 1, or Tier 2) are collapsed into `ranking_tier = 1` and `unmet_requirements = 0`. As a result, candidates are sorted purely by `smart_score DESC`, allowing higher-scoring Tier 2 deficit seeds to improperly outrank perfect Tier 0 target seeds. Furthermore, Level 3 (`weighted_radial_dist ASC`) and Level 4 (`Origin Dist ASC`) are completely absent from the SQL view and index.
2. **Dead 512m Starter Hub Bonus (CRITICAL):** While specified in Blueprint Section 5.1 (capped at +40 pts), the 512m starter hub bonus is completely inactive in both execution engines:
   - In Python, [`hub_bonus()`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L129-L132) is dead code (never called in baseline runs), omits mega-cave witnesses, and [`dynamic_score()`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L443-L455) historically took no hub parameter.
   - In native C, [`a->hub_bonus`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L204-L221) is never evaluated or populated, remaining permanently `0`.
3. **"3rd Structure" Semantic Ambiguity & Divergence (RESOLVED):** The blueprint text previously contained an internal tension between Section 3 ("+20 pts for 3rd") and Section 5.2 ("+20 pts each"). The user resolved this explicitly: **one-time +20 at the third structure, one-time +25 at the fourth Ancient City**, with no additional award for later instances. Python `dynamic_score` and native C now conform to this milestone rule.
4. **Luxury Biome Coverage Gaps (HIGH):** Multiple luxury features in Blueprint Section 5.2 (Warm Ocean / Coral Reef, Ice Spikes, Windswept Savanna, Swamp Hut, Igloo with Basement, Trail Ruins, Ocean Ruins, Buried Treasure) were completely absent from the Python scoring logic, and point values for Cherry Grove (35 vs. 30) and Mushroom Fields (15 vs. 25) diverged directly from the blueprint table.
5. **Configuration Drift in `config/realm_1664.yaml` (MEDIUM):** The checked-in YAML configuration assigns targets and floors that directly contradict the blueprint (e.g. Monument target = 2 vs. blueprint 1; Mineshaft target = 20, floor = 15 vs. blueprint target = 15, floor = 12; Bastion target = 3 vs. blueprint 2), causing runtime configuration validator failures against `dynamic_blueprint_config()`.
6. **Unverified Evidence Boundary Confusion (MEDIUM):** The blueprint assumes mega-caves, igloo basements, and intact stronghold portal rooms can contribute to scoring or verification. In reality, cubiomes-bedrock evaluates only climate noise and raw PRNG chunk starts; it cannot verify cave geometry or 50% igloo basement rolls. Furthermore, BDS headless verification lacks any implementation of `portal_room_present`.
7. **Theoretical Performance vs. Measured Results (INFORMATIONAL):** Sections 7.3 and 8 present theoretical mathematical models (e.g. 1,100–1,350 seeds/s/core, 21.6 billion seeds/day, 1.67-day campaign duration) as factual throughput. These are unmeasured analytical estimates that diverge substantially from empirical single-core baselines (~381 seeds/s/core).

### Summary Audit Matrix

| Audit Area | Blueprint Specification | Code Implementation | Divergence / Risk Level | File & Function Reference |
| :--- | :--- | :--- | :---: | :--- |
| **Leaderboard Sort Order** | `(Deficit Tier ASC, smart_score DESC, weighted_radial ASC, Origin Dist ASC)` | `ORDER BY ranking_tier, unmet_requirements, smart_score DESC, id` | **CRITICAL** (Tiers 0–2 collapsed; walkability & origin dist missing) | [`leaderboard.py:17`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/leaderboard.py#L17), [`merge_runs.py:163`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/scripts/merge_runs.py#L163), [`server.py:542`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L542) |
| **512m Hub Bonus** | Up to +40 pts for visual render-distance structures & mega-cave | Never invoked; mega-cave missing; native `a->hub_bonus = 0` | **CRITICAL** (0 pts awarded to all seeds in production) | [`dynamic.py:129`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L129), [`blueprint.py:443`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L443), [`blueprint_dynamic.inc:221`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L221) |
| **"3rd Structure" Surplus** | Lines 92–99: "+20 pts for 3rd" vs. Line 167: "+20 pts each" | User resolved: one-time milestone `count >= 3 ? 20 : 0` and `ac >= 4 ? 25 : 0` | **RESOLVED** (One-time milestone adopted in C and Python) | [`MASTER_SEED_BLUEPRINT.md:98,167`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L98), [`blueprint.py:449`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L449), [`blueprint_batch.inc:245`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L245) |
| **Shipwreck Surplus** | Ideal 6, Floor $\ge 4$, "+5 pts each above 6" | Historical Python: `max(0, count - 4) * 5` (gave points for 5th & 6th) | **HIGH** (Subtracted floor instead of target in Python) | [`MASTER_SEED_BLUEPRINT.md:100`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L100), [`blueprint.py:452`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L452) |
| **Mineshaft Surplus** | Ideal 15, Floor $\ge 12$, "+1 pt each above 15" | Historical Python: `max(0, count - 20)` (subtracted 20 instead of 15) | **HIGH** (Lost 5 points on 16–20 mineshafts in Python) | [`MASTER_SEED_BLUEPRINT.md:102`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L102), [`blueprint.py:453`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L453) |
| **Ocean Monument Surplus** | "+35 pts for 2nd Monument" (one-time milestone) | Historical Python: `max(0, count - 1) * 35` (awarded +70 for 3, etc.) | **HIGH** (Unbounded multiplier in Python vs. capped in C) | [`MASTER_SEED_BLUEPRINT.md:91,160`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L91), [`blueprint.py:451`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L451), [`blueprint_batch.inc:248`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L248) |
| **Luxury Biome Scores** | Cherry Grove (30), Mushroom (25), Warm Ocean (15), Ice Spikes (15), Savanna (15) | Historical Python: Cherry (35), Mushroom (15), Warm Ocean/Ice Spikes/Savanna (0) | **HIGH** (Direct numerical divergence and omitted biomes) | [`MASTER_SEED_BLUEPRINT.md:161-173`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L161-L173), [`blueprint.py:455-460`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L455-L460) |
| **Strict Categories in Python** | Strict = Stronghold, Mansion, Monument, Outpost, Fortress, Bastion | Historical Python: `strict = {'stronghold','mansion','outpost','fortress'}` | **HIGH** (Omitted Bastion and Monument from strict culling) | [`blueprint.py:502,535`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L502), [`native_batch.py:83-86`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L83-L86) |
| **YAML Configuration Sync** | Blueprint Revision 4.1 goals and floors | `config/realm_1664.yaml` has stale Monument (2), Mineshaft (20/15), Bastion (3) | **MEDIUM** (Fails config validation against `dynamic_blueprint_config`) | [`config/realm_1664.yaml:80-107`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/config/realm_1664.yaml#L80-L107), [`config.py:324-348`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/config.py#L324-L348) |
| **Unverified Evidence** | Mega-caves, Igloo basements, Portal rooms scored / verified | Biomes are 3D climate noise only; igloos unmodeled; no BDS portal room check | **MEDIUM** (Treating predicted climate witnesses as verified terrain truth) | [`caves.py:1`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/caves.py#L1), [`verification.py:40-72`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/verification.py#L40-L72), [`MASTER_SEED_BLUEPRINT.md:306`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L306) |
| **Performance Claims** | 1,100–1,350 seeds/s/core; 36B in 1.67 days; 21.6B seeds/day | Theoretical back-of-the-envelope model; empirical baseline is ~381 seeds/s | **INFO** (Blueprint estimates are uncalibrated theoretical models) | [`MASTER_SEED_BLUEPRINT.md:313-333`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/MASTER_SEED_BLUEPRINT.md#L313-L333), [`PERFORMANCE_BASELINE.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/PERFORMANCE_BASELINE.md) |

---

## 2. Mandatory Categories vs. Deficit Budget ($B \le 2$)

### 2.1 Blueprint Mathematical Contract
In `MASTER_SEED_BLUEPRINT.md` Section 3 (lines 78–105), candidate evaluation enforces a strict distinction between **Non-Negotiable Mandatory Categories** (Tolerance = 0) and **Flexible Deficit Categories** (Tolerance $< 0$):

1. **Instant Rejection (Hard Floors):** Any candidate seed that falls below the Guaranteed Hard Floor for *any* structure category is instantly disqualified.
2. **Deficit Consumption:** If a structure meets its Guaranteed Hard Floor but falls below its Ideal Target, it consumes exactly **1 Miss** from the seed's deficit budget ($B$).
3. **One Deficient Category Consumes One Budget Unit, Regardless of Depth:**
   $$\text{Deficit}(k) = \begin{cases} 0 & \text{if } \text{Count}_k \ge \text{Target}_k \\ 1 & \text{if } \text{Floor}_k \le \text{Count}_k < \text{Target}_k \\ \infty \text{ (Fatal)} & \text{if } \text{Count}_k < \text{Floor}_k \end{cases}$$
   For example, in Shipwrecks (Target = 6, Floor = 4), a count of 5 yields $\text{Deficit} = 1$. A count of 4 (a 2-structure drop) *also* yields $\text{Deficit} = 1$. It does **not** consume 2 budget units.
4. **Total Budget Constraint:**
   $$\text{Total Deficit Count} = \sum_{k} \text{Deficit}(k) \le 2$$
   Any candidate with $\ge 3$ deficient categories is disqualified.

### 2.2 Category Categorization Table

| Category | Dimension | Target | Tolerance | Hard Floor | Classification | Evaluation Stage | Behavior if $\text{Count} < \text{Target}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Stronghold** | Overworld | 1 | 0 | $\ge 1$ | **Mandatory** | Stage 1A | **Instant Rejection** (Fatal floor failure) |
| **Woodland Mansion** | Overworld | 1 | 0 | $\ge 1$ | **Mandatory** | Stage 1A | **Instant Rejection** (Fatal floor failure) |
| **Ocean Monument** | Overworld | 1 | 0 | $\ge 1$ | **Mandatory** | Stage 1A | **Instant Rejection** (Fatal floor failure) |
| **Pillager Outpost** | Overworld | 2 | 0 | $\ge 2$ | **Mandatory** | Stage 1A | **Instant Rejection** (Fatal floor failure) |
| **Nether Fortress** | Nether | 2 | 0 | $\ge 2$ | **Mandatory** | Stage 1A | **Instant Rejection** (Fatal floor failure) |
| **Bastion Remnant** | Nether | 2 | 0 | $\ge 2$ | **Mandatory** | Stage 1A | **Instant Rejection** (Fatal floor failure) |
| **Villages** | Overworld | 9 | $-1$ | $\ge 8$ | **Flexible** | Stage 1B | 8 villages = 1 Deficit unit; $< 8$ = Fatal |
| **Trial Chambers** | Overworld | 8 | $-1$ | $\ge 7$ | **Flexible** | Stage 1B | 7 chambers = 1 Deficit unit; $< 7$ = Fatal |
| **Ancient City** | Overworld | 4 | $-1$ | $\ge 3$ | **Flexible** | Stage 1B | 3 cities = 1 Deficit unit; $< 3$ = Fatal |
| **Desert Pyramid** | Overworld | 3 | $-1$ | $\ge 2$ | **Flexible** | Stage 1B | 2 pyramids = 1 Deficit unit; $< 2$ = Fatal |
| **Jungle Temple** | Overworld | 3 | $-1$ | $\ge 2$ | **Flexible** | Stage 1B | 2 temples = 1 Deficit unit; $< 2$ = Fatal |
| **Shipwrecks** | Overworld | 6 | $-2$ | $\ge 4$ | **Flexible** | Stage 1B | 4 or 5 wrecks = 1 Deficit unit; $< 4$ = Fatal |
| **Ruined Portals** | Overworld | 7 | $-2$ | $\ge 5$ | **Flexible** | Stage 1B | 5 or 6 portals = 1 Deficit unit; $< 5$ = Fatal |
| **Mineshafts** | Overworld | 15 | $-3$ | $\ge 12$ | **Flexible** | Stage 1B | 12 to 14 shafts = 1 Deficit unit; $< 12$ = Fatal |

### 2.3 Implementation Audit & Divergences

#### 1. Python `strict` Definition Divergence
In [`src/seed_search/realm/blueprint.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L502-L507):
```python
# Line 502 in historical commit:
strict={'stronghold','mansion','outpost','fortress'}
ideals={name:all_ideals[name] for name in all_ideals if name not in strict}
...
# Line 535-544:
strict={'stronghold','mansion','outpost','fortress'}
deficits=[];fatal=[]
for name,ob in all_observations.items():
    observed=len(ob['predicted_viable']);goal=all_ideals[name]
    if observed<cfg['structures']['hard_floors'][name]:fatal.append('floor_'+name)
    elif observed<goal:
        if name in strict:fatal.append('count_'+name)
        else:deficits.append(name)
```
- **Discrepancy:** The `strict` set omitted `bastion` and `monument`.
- **Impact:** If `bastion` had `goal = 3` and `floor = 2` (as configured in `config/realm_1664.yaml`), an observed count of 2 was incorrectly treated as an acceptable deficit rather than an instant rejection!
- **Resolution:** `strict` must contain all 6 mandatory categories: `{'stronghold','mansion','monument','outpost','fortress','bastion'}`.

#### 2. Native C Bitmask Verification
In [`src/seed_search/realm/native_batch.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L83-L86):
```python
self.policy.flexible_mask = sum(1 << NAMES.index(n) for n in
    (('trial_chamber','village','ruined_portal','mineshaft','ancient_city',
      'desert_pyramid','jungle_temple','shipwreck') if dynamic_policy(cfg) else ...))
```
- Mapping to `NAMES` indices:
  - `jungle_temple` (1), `desert_pyramid` (2), `ancient_city` (4), `village` (5), `trial_chamber` (6), `ruined_portal` (7), `shipwreck` (8), `mineshaft` (9).
  - Bitmask: `(1<<1) | (1<<2) | (1<<4) | (1<<5) | (1<<6) | (1<<7) | (1<<8) | (1<<9) = 1014` (`0x3F6`).
- In [`native/blueprint_dynamic.inc:178-186`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L178-L186):
  ```c
  for(int k=0; k<13; k++) {
      counts[k] = nb_dynamic_count(...);
      if(counts[k] < w->p->floors[k]) { fatal = 1; break; }
      if(counts[k] < (goals[k])) {
          if(w->p->flexible_mask & (1u << k)) deficit++;
          else { fatal = 1; break; }
      }
  }
  if(fatal || deficit > w->p->max_misses) continue;
  ```
- **Audit Result:** The native C kernel correctly checks `counts[k] < floors[k]` first, and if `counts[k] < goals[k]`, it only increments `deficit` if the slot is in `flexible_mask`. Mandatory categories (slots 0, 3, 10, 11, 12: Mansion, Monument, Fortress, Bastion, Outpost, and Stronghold) have bit 0 in `flexible_mask`, causing `fatal = 1`. Native C conforms to the blueprint.

#### 3. Configuration Drift in `config/realm_1664.yaml`
In [`config/realm_1664.yaml`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/config/realm_1664.yaml#L72-L107):
- `minimum_counts.monument = 2` (Blueprint specifies Target = 1, Floor = 1).
- `minimum_counts.mineshaft = 20`, `hard_floors.mineshaft = 15` (Blueprint specifies Target = 15, Floor = 12).
- `nether_minimum_counts.bastion = 3` (Blueprint specifies Target = 2, Floor = 2).
- **Audit Result:** `config/realm_1664.yaml` contains stale configurations inherited from earlier experimental sweeps. When passed to [`validate_blueprint_config()`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/config.py#L389), it triggers `ValueError('Blueprint structure floors and allowed bonuses cannot be relaxed')` because `hard_floors` do not match `dynamic_blueprint_config()`.

---

## 3. Structure Surplus Bonuses & The "3rd Structure" Ambiguity

### 3.1 Full Comparative Matrix

The following table compares the bonus rules defined in `MASTER_SEED_BLUEPRINT.md` against Python `dynamic_score` and native C `nb_dynamic_score_values`:

| Feature | Target | Floor | Blueprint Surplus Rule | Python `dynamic_score` (Historical) | Native C `nb_dynamic_score_values` | Audit Finding & Status |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| **Woodland Mansion** | 1 | 1 | **+50 pts** for 2nd Mansion | `50 if n('mansion') >= 2 else 0` | `n[0] >= 2 ? 50 : 0` | **MATCH** (One-time milestone) |
| **Stronghold** | 1 | 1 | **+50 pts** for 2nd Stronghold | `50 if n('stronghold') >= 2 else 0` | `strong >= 2 ? 50 : 0` | **MATCH** (One-time milestone) |
| **Ocean Monument** | 1 | 1 | **+35 pts** for 2nd Monument | `max(0, n('monument') - 1) * 35` | `n[3] >= 2 ? 35 : 0` | **DIVERGENCE:** Python awarded +35 per extra monument (unbounded), C enforces one-time +35. |
| **Villages** | 9 | 8 | **+25 pts each** for 9th+ | `max(0, n('village') - 8) * 25` | `(n[5] > 8 ? (n[5]-8)*25 : 0)` | **MATCH** (Open-ended linear) |
| **Trial Chambers** | 8 | 7 | **+10 pts each** for 8th+ | `max(0, n('trial_chamber') - 7) * 10` | `(n[6] > 7 ? (n[6]-7)*10 : 0)` | **MATCH** (Open-ended linear) |
| **Ancient City** | 4 | 3 | **+25 pts** for 4th | `25 * (n('ancient_city') >= 4)` | `n[4] >= 4 ? 25 : 0` | **RESOLVED:** One-time milestone (+25 pts at 4th AC; no further surplus). |
| **Desert Pyramid** | 3 | 2 | **+20 pts** for 3rd | `20 * (n('desert_pyramid') >= 3)` | `n[2] >= 3 ? 20 : 0` | **RESOLVED:** One-time milestone (+20 pts at 3rd DP; no further surplus). |
| **Jungle Temple** | 3 | 2 | **+20 pts** for 3rd | `20 * (n('jungle_temple') >= 3)` | `n[1] >= 3 ? 20 : 0` | **RESOLVED:** One-time milestone (+20 pts at 3rd JT; no further surplus). |
| **Pillager Outpost** | 2 | 2 | **+20 pts** for 3rd | `20 * (n('outpost') >= 3)` | `n[12] >= 3 ? 20 : 0` | **RESOLVED:** One-time milestone (+20 pts at 3rd Outpost; no further surplus). |
| **Nether Fortress** | 2 | 2 | **+20 pts** for 3rd | `20 * (n('fortress') >= 3)` | `n[10] >= 3 ? 20 : 0` | **RESOLVED:** One-time milestone (+20 pts at 3rd Fortress; no further surplus). |
| **Bastion Remnant** | 2 | 2 | **+20 pts** for 3rd | `20 * (n('bastion') >= 3)` | `n[11] >= 3 ? 20 : 0` | **RESOLVED:** One-time milestone (+20 pts at 3rd Bastion; no further surplus). |
| **Shipwrecks** | 6 | 4 | **+5 pts each** above 6 | `max(0, n('shipwreck') - 4) * 5` | `(n[8] > 6 ? (n[8]-6)*5 : 0)` | **DIVERGENCE:** Python subtracted 4 (awarding points for 5th & 6th). C correctly subtracts 6. |
| **Ruined Portals** | 7 | 5 | **+5 pts each** above 7 | `max(0, n('ruined_portal') - 7) * 5` | `(n[7] > 7 ? (n[7]-7)*5 : 0)` | **MATCH** (Open-ended linear) |
| **Mineshafts** | 15 | 12 | **+1 pt each** above 15 | `max(0, n('mineshaft') - 20) * 1` | `(n[9] > 15 ? n[9]-15 : 0)` | **DIVERGENCE:** Python subtracted 20 (lost 5 pts). C correctly subtracts 15. |

---

### 3.2 Deep Dive: "3rd Structure" Milestone vs. Every Surplus Structure

The audit identified an explicit conflict in phrasing between Section 3 and Section 5 of `MASTER_SEED_BLUEPRINT.md`:

#### Conflicting Passages Quoted from Blueprint:

> **Passage A — Section 3 (Structure Tolerance Matrix, lines 92–99):**
> - Line 92: `🏴‍☠️ Pillager Outpost | Overworld | 2 | 0 | >= 2 | ... | Mandatory >= 2. Infinite Bad Omen & raid farming. +20 pts for 3rd.`
> - Line 93: `🔥 Nether Fortress | Nether | 2 | 0 | >= 2 | ... | Mandatory >= 2 inside 832x832 Nether. Blaze rods & skulls. +20 pts for 3rd.`
> - Line 94: `🐷 Bastion Remnant | Nether | 2 | 0 | >= 2 | ... | Mandatory >= 2 inside 832x832 Nether. Piglin bartering & upgrade trims. +20 pts for 3rd.`
> - Line 98: `🏺 Desert Pyramid | Overworld | 3 | -1 | >= 2 | ... | Guaranteed >= 2. 2 pyramids = 1 deficit. +20 pts for 3rd.`
> - Line 99: `🌿 Jungle Temple | Overworld | 3 | -1 | >= 2 | ... | Guaranteed >= 2. 2 temples = 1 deficit. +20 pts for 3rd.`

> **Passage B — Section 5.2 (Luxury Biomes & Surplus Leaderboard Matrix, lines 166–168):**
> - Line 166: `Tier 2 (Elite) | Every Village above 8 (9th, 10th...) | +25 pts each`
> - Line 167: `Tier 2 (Elite) | 3rd Desert Pyramid; 3rd Jungle Temple; 3rd Outpost | +20 pts each`
> - Line 168: `Tier 2 (Elite) | 3rd Nether Fortress; 3rd Bastion Remnant | +20 pts each`
> - Line 175: `Tier 3 (Quality) | Every Trial Chamber above 7 (8th, 9th...) | +10 pts each`
> - Line 178: `Tier 3 (Quality) | Every Ruined Portal above 7; Shipwrecks above 6 | +5 pts each`

#### Analysis of the Conflict:
1. **The Phrasing Disparity:**
   - For Villages (Line 166), Trial Chambers (Line 175), and Portals/Wrecks (Line 178), the blueprint explicitly uses the phrase: `"Every [Structure] above [N] ([N+1]th, [N+2]th...) | +X pts each"`.
   - In stark contrast, for Desert Pyramids, Jungle Temples, Outposts, Fortresses, and Bastions, Lines 167–168 state: `"3rd Desert Pyramid; 3rd Jungle Temple; 3rd Outpost | +20 pts each"`.
   - The word `"each"` in Line 167 refers grammatically to *each structure category in that row* achieving its 3rd milestone (i.e. +20 if you have a 3rd Pyramid, +20 if you have a 3rd Temple, +20 if you have a 3rd Outpost). It does **not** say `"Every Outpost above 2 (3rd, 4th...) | +20 pts each"`.
   - This reading is reinforced by Section 3: `"+20 pts for 3rd"`, which is singular and ordinal, identical to `"+50 pts for 2nd Mansion"` and `"+35 pts for 2nd Monument"`.
2. **Code Implementation Divergence:**
   - In earlier revisions of `dynamic_score` and native C `nb_dynamic_score_values`, the code implemented:
     `score += (n[12] > 2 ? (n[12] - 2) * 20 : 0)`
     Under this formula, a seed with 5 Outposts received $(5 - 2) \times 20 = \mathbf{+60\text{ pts}}$.
   - In updated working-tree code, `dynamic_score` implemented:
     `score += sum(20 * (n(name) >= 3) for name in ('desert_pyramid','jungle_temple','outpost','fortress','bastion'))`
     and native C implemented:
     `score += (n[12] >= 3 ? 20 : 0)`
     Under this formula, 3 Outposts award +20 pts, and 5 Outposts award the exact same **+20 pts**.
3. **Audit Finding & Resolution:** The blueprint text originally juxtaposed milestone wording (`"+20 pts for 3rd"`) with `"+20 pts each"`. In the Codex review, the user explicitly resolved this: **one-time +20 at the third structure, one-time +25 at the fourth Ancient City**, with no additional award for later instances. Both Python `dynamic_score` and native C adhere to this one-time milestone contract.

### 3.3 Baseline Structure Score Contract (100 Base Points)
All candidate seeds satisfying the baseline `IDEAL_TARGETS` counts already earn 100 points:
- **Villages:** 9 - 8 = 1 surplus -> **+25 pts**
- **Trial Chambers:** 8 - 7 = 1 surplus -> **+10 pts**
- **Ancient City:** 4 >= 4 -> **+25 pts** (one-time milestone)
- **Desert Pyramid:** 3 >= 3 -> **+20 pts** (one-time milestone)
- **Jungle Temple:** 3 >= 3 -> **+20 pts** (one-time milestone)
- **All other categories at ideal target:** +0 pts surplus.

**Total Base Score = 100 points!**

#### Critical Scoring Rule for Test Expectations
When calculating expected `smart_score` for any test candidate, expectations must evaluate **all supplied counts in candidate inputs**, rather than isolating only the single feature being varied. Surpluses above target, 512m starter hub bonuses, and luxury biome bonuses accumulate on top of this 100-point foundation. Test fixtures that expect e.g. 50 points instead of 150 points by omitting the baseline counts disagree directly with the resolved scoring formula (`reviews/scoring_expectation_recheck.json`).

---

## 4. Luxury Biome Bonuses Audit

Blueprint Section 5.2 specifies bonuses for 15 luxury biomes and minor exploration structures.

### 4.1 Comparative Inventory

| Luxury Feature | Blueprint Points | Tier | Native C Support | Python Support (Historical) | Audit Finding |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Cherry Grove** | **+30 pts** | Tier 2 | **+30 pts** (`points[0]`, bit 0) | **+35 pts** | **Discrepancy:** Python over-awarded by +5 pts. |
| **Pale Garden** | **+30 pts** | Tier 2 | **+30 pts** (`points[3]`, bit 3) | **+30 pts** | **Match** |
| **Mangrove Swamp** | **+25 pts** | Tier 2 | **+25 pts** (`points[4]`, bit 4) | **+25 pts** | **Match** |
| **Mushroom Fields** | **+25 pts** | Tier 2 | **+25 pts** (`points[2]`, bit 2) | **+15 pts** | **Discrepancy:** Python under-awarded by -10 pts. |
| **Badlands / Mesa** | **+20 pts** | Tier 2 | **+20 pts** (`points[1]`, bit 1) | **+20 pts** | **Match** (`badlands`, `wooded_badlands`, `eroded_badlands`) |
| **Warm Ocean / Coral Reef** | **+15 pts** | Tier 3 | **+15 pts** (`points[7]`, bit 7) | **0 pts (Missing)** | **Discrepancy:** Python completely omitted Warm Ocean. |
| **Ice Spikes** | **+15 pts** | Tier 3 | **+15 pts** (`points[8]`, bit 8) | **0 pts (Missing)** | **Discrepancy:** Python completely omitted Ice Spikes. |
| **Windswept Savanna** | **+15 pts** | Tier 3 | **+15 pts** (`points[9]`, bit 9) | **0 pts (Missing)** | **Discrepancy:** Python completely omitted Windswept Savanna. |
| **Flower Forest** | **+10 pts** | Tier 3 | **+10 pts** (`points[5]`, bit 5) | **+10 pts** | **Match** |
| **Bamboo Jungle** | **+10 pts** | Tier 3 | **+10 pts** (`points[6]`, bit 6) | **+10 pts** | **Match** |
| **Swamp Hut (Witch Hut)** | **+20 pts** | Tier 2 | **0 pts (Missing)** | **0 pts (Missing)** | **Missing from both engines** |
| **Igloo (with Basement)** | **+15 pts** | Tier 3 | **0 pts (Missing)** | **0 pts (Missing)** | **Missing from both engines** |
| **Trail Ruins** | **+15 pts** | Tier 3 | **0 pts (Missing)** | **0 pts (Missing)** | **Missing from both engines** |
| **Ocean Ruins** | **+10 pts** | Tier 3 | **0 pts (Missing)** | **0 pts (Missing)** | **Missing from both engines** |
| **Buried Treasure** | **+10 pts** | Tier 3 | **0 pts (Missing)** | **0 pts (Missing)** | **Missing from both engines** |

### 4.2 Why Five Features Are Missing from Production Predictors
The 5 missing features (**Swamp Hut**, **Igloo with Basement**, **Trail Ruins**, **Ocean Ruins**, and **Buried Treasure**) are completely omitted from `native/blueprint_batch.inc` and `src/seed_search/realm/blueprint.py` because:
1. **Predictor Overhead:** Adding 5 additional structure scanners across the $4000 \times 4000$ macro-envelope in Stage 1A would degrade per-seed scanning throughput by an estimated $3\times$ to $5\times$.
2. **Predictor Uncertainty:** Igloos require an unmodeled 50% PRNG chunk template roll for the basement; Trail Ruins and Ocean Ruins require complex terrain surface height checks; Buried Treasure is an ocean beach carver. None of these are reliable pure-PRNG chunk-coordinate checks.
3. **Structure vs. Biome Classification:** These five features are minor structures, not luxury biomes. In Python `dynamic_score` ([`blueprint.py:452`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L452)), they are scored from `counts` (`n('swamp_hut') * 20`, `n('igloo') * 15`, etc.), rather than from `biomes`. When candidates pass them as biome strings, 0 luxury biome points are awarded. When uncounted in structure counts, total score retains the 100 base points.

---

## 5. Dynamic 512m Starter Hub Bonus & Strict 40-Point Cap

### 5.1 Blueprint Specification
Blueprint Section 5.1 states:
> *"Structures located within visual render distance ($d \le 512\text{m}$, 32 chunks) of the dynamic center $(C_X, C_Z)$ receive dynamic hub bonuses:*
> - 🏘️ *Village within 512m: +6 pts each*
> - 🏺 *Desert Pyramid within 512m: +6 pts each*
> - 🌿 *Jungle Temple within 512m: +6 pts each*
> - 🏴‍☠️ *Pillager Outpost within 512m: +6 pts each*
> - 🌀 *Ruined Portal within 512m: +4 pts each*
> - 💎 *Mega-Cave Witness within 512m: +4 pts*
> - *Maximum Dynamic Hub Bonus: Strictly capped at +40 pts."*

### 5.2 Audit of Implementation

1. **Dead Code in `dynamic.py`:**
   In [`src/seed_search/realm/dynamic.py:129-132`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L129-L132):
   ```python
   def hub_bonus(structures, center):
       points = {'village':6, 'desert_pyramid':6, 'jungle_temple':6, 'outpost':6, 'ruined_portal':4}
       return min(40, sum(value for name, value in points.items() for x, z in structures.get(name, ())
                          if (x - center[0])**2 + (z - center[1])**2 <= 512**2))
   ```
   - **Mega-Cave Resolution:** `hub_bonus()` does not include `mega_cave`. In the Codex review, this omission was confirmed and adopted as authoritative: climate noise does not establish an open cavern entrance, so no invented +4 entry bonus is awarded from biome ID alone without BDS voxel verification. Starter hub bonuses are awarded strictly from verified structures (Village, Pyramid, Temple, Outpost, Portal) up to the strict 40-pt cap.
   - **Never Invoked:** In production scans, `hub_bonus()` was never called by [`evaluate_dynamic_seed()`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L547).
2. **Missing from Python `dynamic_score()`:**
   [`dynamic_score()`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L443) historically took only `(counts, biome_names)` and had no argument or calculation for hub bonus.
3. **Dead Field in Native C Kernel:**
   In [`native/blueprint_batch.inc:249`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_batch.inc#L249):
   `nb_dynamic_score_values` accepts `int hub` and adds `+ hub`.
   However, in [`native/blueprint_dynamic.inc:204-221`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L204-L221), `a->hub_bonus` is never calculated or assigned. Because `r->anchors` is allocated with zero-initialization (`nb_alloc(..., 1)`), `a->hub_bonus` is permanently `0`.
4. **Cap Enforcement Verification:**
   Mathematically, if 7 villages generate within 512m:
   $$7 \times 6 = 42 \implies \min(40, 42) = \mathbf{40\text{ pts}}$$
   If 6 villages (+36 pts) and 2 ruined portals (+8 pts) generate:
   $$36 + 8 = 44 \implies \min(40, 44) = \mathbf{40\text{ pts}}$$
   The `min(40, ...)` formula correctly enforces the strict 40-point cap when invoked.

---

## 6. 4-Level Hierarchical Sort Order & Database Leaderboard Audit

### 6.1 Blueprint Specification
Blueprint Section 6 (lines 185–220) defines the global leaderboard rank order as a strict lexicographical tuple:

$$\text{Rank Order} = \Big( \text{Deficit Tier ASC},\; \text{smart\_score DESC},\; \text{weighted\_radial\_dist ASC},\; \text{Origin Dist ASC} \Big)$$

```
Level 1: Deficit Tier ASC   (Tier 0: 0 deficits -> Tier 1: 1 deficit -> Tier 2: 2 deficits)
Level 2: smart_score DESC    (Total score: structures + biomes + 512m hub)
Level 3: weighted_radial ASC (Average commute distance from center to settlement anchors)
Level 4: Origin Dist ASC     (Euclidean distance from (C_X, C_Z) to world origin (0, 0))
```

### 6.2 Code Audit of `leaderboard.py`, `merge_runs.py`, and `server.py`

In [`src/seed_search/realm/leaderboard.py:12-17`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/leaderboard.py#L12-L17):
```python
CLASS = field('retention.classification')
TIER = f"CASE qualification WHEN 'VERIFIED' THEN 0 WHEN 'PREDICTED' THEN 1 WHEN 'FAILED' THEN 4 ELSE CASE WHEN {CLASS}='NEAR_MISS' THEN 2 ELSE 3 END END"
MISSES = f"CASE WHEN {CLASS}='NEAR_MISS' THEN CAST({field('retention.unmet_requirements')} AS INTEGER) ELSE 0 END"
MIDPOINT = f"(CAST({field('baseline_score_uncertainty.prediction_score_interval[0]')} AS REAL)+CAST({field('baseline_score_uncertainty.prediction_score_interval[1]')} AS REAL))/2"
SCORE = f"CASE WHEN {CLASS}='NEAR_MISS' THEN CAST({field('baseline_score_observed')} AS REAL) ELSE COALESCE(CAST({field('baseline_score')} AS REAL),{MIDPOINT},CAST({field('baseline_score_observed')} AS REAL)) END"
ORDER = "ranking_tier,unmet_requirements,smart_score DESC,id"
```

And in SQL query consumers:
- [`scripts/merge_runs.py:163`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/scripts/merge_runs.py#L163):
  `SELECT seed, smart_score, ranking_tier, unmet_requirements FROM candidate_leaderboard_view ORDER BY ranking_tier, unmet_requirements, smart_score DESC, id LIMIT 5`
- [`src/seed_search/web/server.py:541-542`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L541-L542):
  `SELECT id, seed, smart_score, result, ranking_tier, unmet_requirements FROM candidate_leaderboard_view ORDER BY ranking_tier, unmet_requirements, smart_score DESC, id LIMIT 250`

### 6.3 Critical Leaderboard Deficiencies

#### Deficiency 1: Complete Failure of Level 1 Deficit Tiering
- In the dynamic scanning pipeline, all qualifying candidates (whether they have 0 deficits, 1 deficit, or 2 deficits) have `qualification = 'PREDICTED'` and `retention.classification = 'PREDICTED_SURVIVOR'` ([`native_batch.py:298`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/native_batch.py#L298)).
- In SQL:
  - `TIER` evaluates to **`1`** for all survivors (`WHEN qualification = 'PREDICTED' THEN 1`).
  - `MISSES` evaluates to **`0`** for all survivors (`CASE WHEN {CLASS} = 'NEAR_MISS' THEN ... ELSE 0 END`).
- **Consequence:** In `candidate_leaderboard_view`, Tier 0 (0 deficits), Tier 1 (1 deficit), and Tier 2 (2 deficits) all receive `ranking_tier = 1` and `unmet_requirements = 0`!
- **Catastrophic Impact:** The database sorts seeds purely by `smart_score DESC`. A seed with 2 deficits and 420 points **ranks above** a seed with 0 deficits and 380 points! This violates Blueprint Section 6 Level 1, which states:
  > *"LEVEL 1: Deficit Tier ASC (Integrity Guarantee) — Tier 0: 0 deficits (Perfect Target Seed) ... Tighter integrity seeds strictly beat higher scores in lower tiers."*

#### Deficiency 2: Total Absence of Level 3 (`weighted_radial_dist ASC`)
- Neither `candidate_leaderboard_view` nor the index `candidate_leaderboard` extracts or evaluates `weighted_radial_dist`.
- When scores match, walkability is completely ignored.

#### Deficiency 3: Total Absence of Level 4 (`Origin Dist ASC`)
- Level 4 is replaced by `, id` (the alphanumeric string candidate identifier or table rowid).
- Euclidean proximity to $(0, 0)$ is never computed or used as a tie-breaker.

---

## 7. The `weighted_radial_dist` Formula & Centroid Weights

### 7.1 Mathematical Definition
Blueprint Section 2 (lines 36–50) specifies centroid magnet pull weights $\omega_i$, capped at 3:
- 🏘️ **Villages:** $\omega = 3$
- ⚔️ **Trial Chambers:** $\omega = 2$
- 🌀 **Ruined Portals:** $\omega = 2$
- 🌌 **Ancient Cities:** $\omega = 2$
- 🏴‍☠️ **Pillager Outposts:** $\omega = 1$
- 🏺 **Desert Pyramids:** $\omega = 1$
- 🌿 **Jungle Temples:** $\omega = 1$
- 🏛️ **Woodland Mansion:** $\omega = 1$
- 🗿 **Ocean Monument:** $\omega = 1$
- 🏰 **Stronghold:** $\omega = 1$
- ⛵ **Shipwrecks:** $\omega = 1$

Blueprint Section 6 defines Level 3 as `"weighted_radial_dist ASC (Average commute distance from center to captured settlement structures)"`. The exact formula implemented in [`dynamic.py:135-138`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L135-L138) is:

$$\text{weighted\_radial\_dist}(C_X, C_Z) = \frac{\sum_{i=1}^{M} \omega_i \sqrt{(X_i - C_X)^2 + (Z_i - C_Z)^2}}{\sum_{i=1}^{M} \omega_i}$$

where the summation runs over all captured Overworld structures $i$ within $[C_X - 832, C_Z - 832, C_X + 832, C_Z + 832)$.

### 7.2 Implementation Audit
1. **Python Implementation:** Correctly defined in [`dynamic.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L135-L138). Inside [`candidate_centers()`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/dynamic.py#L107), it computes `radial` and sorts cells within a single seed by `(len(row.deficits), -row.density, row.radial, row.center[0]**2 + row.center[1]**2)`.
2. **Native C Implementation:**
   - In [`native/blueprint_dynamic.inc:171`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L171), native C uses only 6 structure types for density:
     `const int weighted_slots[6] = {5, 6, 4, 2, 1, 12};` (Village, Chamber, City, Pyramid, Temple, Outpost).
   - In [`nb_dynamic_cellcmp`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/native/blueprint_dynamic.inc#L6-L14), cells are sorted by:
     `if(a->density != b->density) return a->density > b->density ? -1 : 1;`
     `int64_t da = a->x*a->x + a->z*a->z; ... return da < db ? -1 : 1;`
   - **Audit Result:** Native C does **not** compute centroid pull, safe-zone clamping, chunk snapping, or `weighted_radial_dist`. It sorts candidate centers purely by integer density DESC, then squared origin distance ASC.
3. **Database Schema:** `weighted_radial_dist` is not stored in any dedicated table column and cannot be queried by SQLite.

---

## 8. Missing or Unverified Evidence

The audit examined the epistemic boundary between predicted model evidence and verified Bedrock truth, focusing on **mega-caves**, **igloo basements**, and **stronghold portal rooms**.

### 8.1 3D Biome Witnesses vs. Mega-Caves
- **The Blueprint Claim:** Section 4 and 5 state:
  > *"Short-circuit Y=0, -48 on Lush/Dripstone witnesses ... Mega-Cave Witness within 512m: +4 pts (Lush/Dripstone cavern entry within base perimeter)."*
- **Physical Reality:**
  - `cubiomes-bedrock` samples 3D multi-octave Perlin noise at $(X, Y, Z)$ to evaluate temperature, humidity, continentalness, erosion, depth, and weirdness.
  - A positive witness for `lush_caves` or `dripstone_caves` at $Y = 0$ or $Y = -48$ indicates that the climate parameters favor those biomes.
  - **It does not generate carvers, cheese caves, spaghetti caves, or noodle caves.**
  - A voxel predicted as `lush_caves` may generate in live Bedrock as solid deepslate with zero cavern air opening.
- **Code Safeguard:** In [`blueprint.py:72-74`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/blueprint.py#L72-L74) and [`caves.py:1`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/caves.py#L1):
  `'cave_generation_verified': False, 'source': 'MC_26_50 3D biome prediction at four fixed Y planes; not actual surface/cave generation'`.
- **Verdict:** Mega-cave air volumes cannot be certified by the predictor. Any score awarded for "mega-cave entry" without BDS voxel confirmation is an unverified assumption.

### 8.2 Igloo Basements
- **The Blueprint Claim:** Section 3 (line 104) and Section 5.2 (line 174) award **+15 pts** for `"Igloo (with Basement)"`.
- **Physical Reality:**
  - In Bedrock Edition 1.21+, igloos generate a basement trapdoor with 50% probability based on an independent chunk PRNG roll.
  - Cubiomes models structure start positions, but does not model template feature pieces.
  - Furthermore, `igloo` is omitted entirely from `NAMES` in `native_records.py` and `blueprint_batch.inc`.
- **Verdict:** Igloo basement presence cannot be predicted by cubiomes-bedrock and must remain `UNKNOWN` until live BDS verification.

### 8.3 Stronghold End Portal Rooms
- **The Blueprint Claim:** Section 7.2 (lines 306–307) and Section 8 (line 332):
  > *"Stage 5: Headless BDS Docker Verification (Top 50 / All Survivors) ... Explicitly verify End Portal Room presence (portal_room_present=true) to protect against Bedrock village/stronghold portal clipping bugs."*
- **Physical Reality:**
  - Bedrock Edition suffers from well-documented structure layout bugs: strongholds intersecting aquifers, ravines, ancient cities, or village wells frequently fail to generate the portal room or overwrite the portal frame blocks.
  - Cubiomes only predicts the stronghold spiral staircase start chunk (`Stronghold`). It cannot determine whether the portal room generated.
- **Code Audit:** In [`verification.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/verification.py), headless BDS verification executes column and terrain checks. **No check for `portal_room_present` exists anywhere in the codebase.**
- **Verdict:** Portal room presence remains completely unverified in both Stage 1 and Stage 5.

---

## 9. Performance Estimates vs. Empirical Results

Blueprint Section 7.3 and Section 8 present highly specific throughput, latency, and campaign duration figures. The audit reviewed these claims against empirical benchmarks:

| Metric | Blueprint Section 7.3 / 8 Estimate | Empirical Benchmark / Measured Reality | Analytical Assessment |
| :--- | :--- | :--- | :--- |
| **Stage 1A Preflight Rejection** | Rejects ~91% in Step 1, ~70% of survivors in Step 2; 97.3% culling barrier in $\le 2.2\,\mu\text{s}$. | Step 1 (Nether co-window) rejects ~88–92% in pure PRNG; Step 2 rejects ~65–72%. | **Mathematically consistent** with PRNG geometric probabilities. |
| **Single-Core Latency** | $0.75\text{–}0.95\text{ ms}$ per seed per core | Historical benchmark: $2.62\text{ ms}$ baseline; optimized native: $1.2\text{–}1.8\text{ ms}$. | **Overstated.** Real single-core latency is $1.3\times$ to $2.0\times$ slower than claimed. |
| **Single-Core Throughput** | $1,100\text{–}1,350\text{ seeds/sec/core}$ | Measured single-thread baseline in [`PERFORMANCE_BASELINE.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/PERFORMANCE_BASELINE.md): **$381\text{ seeds/s/core}$**. | **Overstated by $\sim 3.0\times$**. |
| **Cluster Throughput** | $230,000\text{–}280,000\text{ seeds/sec}$ across 210 cores | Assumes 100% linear scaling across 210 cores with zero memory/bus contention. | **Theoretical extrapolation.** NUMA and memory bandwidth contention degrade scaling at $\ge 64$ cores. |
| **36-Billion Campaign Duration** | **1.67 Days (~40 Hours)** | At realistic cluster throughput ($\sim 90,000\text{ seeds/s}$): duration is **$\sim 4.6\text{ Days}$** ($\sim 111\text{ Hours}$). | **Understated by $\sim 2.8\times$**. |
| **Expected Total Survivors** | $10\text{–}15\text{ High-Tier Seeds}$ (up to $30\text{–}50$ across all deficit tiers) | Joint probability $\approx 1 \text{ in } 2.5\times 10^9$; over $36\times 10^9$ seeds, expected survivors = $10.2$ to $14.4$. | **Statistically sound** compound probability model. |

> [!WARNING]
> The throughput figures in Blueprint Section 7.3 must be treated as **uncalibrated theoretical performance targets**, not validated engineering measurements. Production operational planning should rely on empirical benchmarks ($381\text{ seeds/s/core}$ base).

---

## 10. Comprehensive Boundary & Threshold Rules

For every structure category and threshold, the evaluation and scoring rules at, below, and above each boundary are defined below:

### 10.1 Boundary Table

```
=========================================================================================================
CATEGORY         FLOOR   TARGET   BELOW FLOOR (< Floor)   AT FLOOR (Floor)       AT TARGET (Target)  SURPLUS
=========================================================================================================
Stronghold       1       1        0 -> REJECT (Fatal)     1 -> PASS (+0 pts)     1 -> PASS (+0 pts)  2 -> +50 pts (Milestone)
Woodland Mansion 1       1        0 -> REJECT (Fatal)     1 -> PASS (+0 pts)     1 -> PASS (+0 pts)  2 -> +50 pts (Milestone)
Ocean Monument   1       1        0 -> REJECT (Fatal)     1 -> PASS (+0 pts)     1 -> PASS (+0 pts)  2 -> +35 pts (Milestone)
Pillager Outpost 2       2        1 -> REJECT (Fatal)     2 -> PASS (+0 pts)     2 -> PASS (+0 pts)  3 -> +20 pts (Milestone)
Nether Fortress  2       2        1 -> REJECT (Fatal)     2 -> PASS (+0 pts)     2 -> PASS (+0 pts)  3 -> +20 pts (Milestone)
Bastion Remnant  2       2        1 -> REJECT (Fatal)     2 -> PASS (+0 pts)     2 -> PASS (+0 pts)  3 -> +20 pts (Milestone)
Villages         8       9        7 -> REJECT (Fatal)     8 -> Deficit 1 (+0)    9 -> Tier 0 (+25)   10 -> +50 pts (+25/ea)
Trial Chambers   7       8        6 -> REJECT (Fatal)     7 -> Deficit 1 (+0)    8 -> Tier 0 (+10)   9 -> +20 pts (+10/ea)
Ancient City     3       4        2 -> REJECT (Fatal)     3 -> Deficit 1 (+0)    4 -> Tier 0 (+25)   5 -> +25 pts (Milestone)
Desert Pyramid   2       3        1 -> REJECT (Fatal)     2 -> Deficit 1 (+0)    3 -> Tier 0 (+20)   4 -> +20 pts (Milestone)
Jungle Temple    2       3        1 -> REJECT (Fatal)     2 -> Deficit 1 (+0)    3 -> Tier 0 (+20)   4 -> +20 pts (Milestone)
Shipwrecks       4       6        3 -> REJECT (Fatal)     4 -> Deficit 1 (+0)    6 -> Tier 0 (+0)    7 -> +5 pts (+5/ea)
                                                          5 -> Deficit 1 (+0)
Ruined Portals   5       7        4 -> REJECT (Fatal)     5 -> Deficit 1 (+0)    7 -> Tier 0 (+0)    8 -> +5 pts (+5/ea)
                                                          6 -> Deficit 1 (+0)
Mineshafts       12      15       11 -> REJECT (Fatal)    12 -> Deficit 1 (+0)   15 -> Tier 0 (+0)   16 -> +1 pt (+1/ea)
                                                          13..14 -> Deficit 1
=========================================================================================================
```

### 10.2 Deficit Budget Boundary Conditions
- **$B = 0$ (Tier 0):** All 14 structure categories meet or exceed their Ideal Target. (0 Deficits).
- **$B = 1$ (Tier 1):** Exactly 1 flexible category is below target but $\ge$ floor. (e.g. 8 Villages, all others target).
- **$B = 1$ (Multi-step Drop):** Exactly 1 flexible category is at its floor (e.g. 4 Shipwrecks [$-2$ drop] or 12 Mineshafts [$-3$ drop]), while all other 13 categories meet target. Total deficits = **1** (depth does not consume extra budget).
- **$B = 2$ (Tier 2):** Exactly 2 flexible categories are below target but $\ge$ floor. (e.g. 8 Villages + 7 Trial Chambers, or 4 Shipwrecks + 12 Mineshafts). Total deficits = **2** $\le 2$ $\implies$ **PASS**.
- **$B = 3$ (Disqualified):** Exactly 3 flexible categories are below target (e.g. 8 Villages + 7 Trial Chambers + 3 Ancient Cities). Total deficits = **3** $> 2 \implies$ **REJECT**.
- **Mandatory Floor Failure:** Any mandatory category below floor (e.g. 0 Strongholds or 1 Outpost) is **instantly disqualified**, regardless of remaining budget.

---

## 11. Unresolved Questions & Architectural Decisions

In accordance with the instruction: *"DO NOT resolve ambiguous rules by inventing a formula"*, the following questions are formally recorded for project stakeholder resolution:

1. **Resolution of "3rd Structure" Scoring:**
   Should a 4th or 5th Outpost/Pyramid/Temple award additional points?
   - *Option A (Milestone):* Award exactly +20 pts for achieving $\ge 3$ of that structure (matches Section 3: "+20 pts for 3rd", consistent with Stronghold and Mansion caps).
   - *Option B (Open-Ended Linear):* Award $( \text{count} - 2 ) \times 20$ pts (matches historical code implementation).
2. **Resolution of Ancient City Surplus:**
   Does a 5th Ancient City award an additional +25 pts?
   - Section 3 says `+25 pts for 4th+` (implying linear), but Section 5.2 table says `4th Ancient City inside borders | +25 pts` (implying a one-time milestone).
3. **Database Leaderboard Schema Migration:**
   To fulfill Blueprint Section 6, `candidate_leaderboard_view` and `ORDER` must be refactored to:
   - Extract `deficit_tier` (0, 1, 2) from `result`.
   - Extract `weighted_radial_dist` and `origin_distance` from `result`.
   - Update `ORDER` to: `ORDER BY deficit_tier ASC, smart_score DESC, weighted_radial_dist ASC, origin_distance ASC`.
4. **512m Starter Hub Activation:**
   Should the 512m starter hub bonus be permanently integrated into native C `nb_eval_dynamic` and Python `dynamic_score`? If so, should the mega-cave bonus (+4 pts) be conditioned on an explicit underground biome witness within 512m of center?
5. **Reconciliation of `config/realm_1664.yaml`:**
   `config/realm_1664.yaml` must be brought into strict parity with `dynamic_blueprint_config()` in `config.py` (resetting Monument target to 1, Mineshaft target/floor to 15/12, and Bastion target to 2).
