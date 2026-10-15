> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Task 3: BDS Verification Integrity & Evidence Handling Audit

**Audit Status**: COMPLETED
**Target Review Directory**: `reviews/gemini/bds/`
**Auditor**: Gemini Agent (Task 3: BDS Verification Integrity Audit)
**Date**: October 2026
**Applicable Standards**: Scientific reproducibility, empirical ground-truth isolation, bounded observation semantics.

---

## 1. Executive Summary

This audit examined the end-to-end implementation of Bedrock Dedicated Server (BDS) verification, from web endpoints and frontend user interfaces down to core realm adapters, subprocess controllers, and behavioral pack Script API code.

### Critical Finding
The web service layer (`src/seed_search/web/server.py`) and frontend client (`web-ui/src/App.tsx`, `web-ui/src/components/SeedDetailModal.tsx`) implement an **entirely fabricated verification flow**. When a user requests BDS verification:
1. No Docker container or server process is ever started.
2. Hardcoded metrics (`99.8% palette agreement`, `height MAE 0.14`, `portalRoomStatus: "INTACT"`, `mansionGroundTruth: "CONFIRMED"`) are returned unconditionally in milliseconds.
3. The live candidate in memory and the persistent SQLite database (`realm.sqlite` and `candidates.db`) are **permanently updated to `VERIFIED` with `kind: "actual_generation"`**, poisoning the dataset with false ground truth.
4. UI alerts, log entries, and toasts falsely report that runtime voxel blocks have been confirmed against official Mojang server binaries.

In stark contrast, the repository contains a genuine, rigorously engineered verification adapter (`src/seed_search/realm/verification.py` and `src/seed_search/realm/bds_tools/`) that enforces image pins, CPU/RAM allocations, disk limits, multi-pass stability, and LevelDB block comparisons. However, **this real adapter is completely bypassed by the web server**. Furthermore, even the genuine BDS adapter cannot verify structures, portal rooms, or loot, because Bedrock Script API 2.10.0 does not support structure enumeration.

---

## 2. Hardcoded and Fabricated Verification Values

The following table catalogues all hardcoded and fabricated verification artifacts discovered in the audit:

| Location | Component | Fabricated Value / Behavior | Severity |
| :--- | :--- | :--- | :--- |
| [`src/seed_search/web/server.py:653-660`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L653-L660) | `verify_bds_candidate` | Static dictionary: `paletteAgreement: "99.8%"`, `heightMae: 0.14`, `settledColumns: 4096`, `portalRoomStatus: "INTACT"`, `mansionGroundTruth: "CONFIRMED"` | **CRITICAL** |
| [`src/seed_search/web/server.py:663-668`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L663-L668) | `verify_bds_candidate` | Sets `c["bdsVerified"] = True`, `c["actualGenerationStatus"] = "VERIFIED"` in memory without provider execution | **CRITICAL** |
| [`src/seed_search/web/server.py:669-693`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L669-L693) | `verify_bds_candidate` | Updates `candidates` table in `realm.sqlite` with forged `actual_generation_verification` record | **CRITICAL** |
| [`src/seed_search/web/server.py:695`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L695) | `verify_bds_candidate` | Logs: `✅ BDS 1.26.52.3 Parity Verified: seed {seed_val} confirmed (99.8% palette agreement, height MAE 0.14)` | **HIGH** |
| [`web-ui/src/App.tsx:322-326`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/App.tsx#L322-L326) | `handleBeginBDSParity` | Fallback object hardcoded in client: `paletteAgreement: '99.8%'`, `heightMae: 0.14`, `settledColumns: 4096` | **HIGH** |
| [`web-ui/src/App.tsx:328-336`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/App.tsx#L328-L336) | `handleBeginBDSParity` | Forces client-side state: `bdsVerified: true`, `actualGenerationStatus: 'VERIFIED'` | **HIGH** |
| [`web-ui/src/App.tsx:342-346`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/App.tsx#L342-L346) | `handleBeginBDSParity` | Injects false log: `[BDS] Seed ${cand.seed} confirmed: 99.8% palette agreement, height MAE 0.14 blocks, portal room intact.` | **MEDIUM** |
| [`web-ui/src/components/SeedDetailModal.tsx:386,427,436`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/components/SeedDetailModal.tsx#L386) | Modal UI | Claims clicking button runs Docker BDS 1.26.52.3 container verification against official Mojang bedrock server binary | **MEDIUM** |
| [`web-ui/src/mockData.ts:117-123,170-176`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/mockData.ts#L117-L123) | Mock Seeds | Seeds `-839210492817492` and `4920194820194` have hardcoded `bdsVerified: true` and identical fake accuracy numbers | **LOW** |

---

## 3. Routes Marking Candidates VERIFIED Without Provider Evidence

### Route: `POST /api/bds/verify`
* **Handler**: [`src/seed_search/web/server.py:1166-1175`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L1166-L1175) -> [`SweepManager.verify_bds_candidate`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L637-L705).
* **Defect Flow**:
  1. Receives JSON payload `{"seed": "...", "candidateId": "..."}`.
  2. Bypasses `VerificationAdapter`.
  3. Synthesizes `metrics`.
  4. Returns:
     ```json
     {
       "ok": true,
       "seed": "...",
       "candidateId": "...",
       "bdsVerified": true,
       "bdsAccuracy": {
         "paletteAgreement": "99.8%",
         "heightMae": 0.14,
         "settledColumns": 4096,
         "provider": "official BDS 1.26.52.3",
         "portalRoomStatus": "INTACT",
         "mansionGroundTruth": "CONFIRMED"
       },
       "actualGenerationStatus": "VERIFIED"
     }
     ```
  5. Directly executes an SQL UPDATE query on `candidates` table in `realm.sqlite`:
     ```sql
     UPDATE candidates SET result = ? WHERE id = ?
     ```
     where `result` is injected with:
     ```json
     {
       "actual_generation_verification": {
         "status": "VERIFIED",
         "source": {"kind": "actual_generation", "version": "1.26.52.3"},
         "metrics": {...}
       }
     }
     ```
  6. Subsequent queries by `_query_sqlite_candidates()` parse this row via `parse_candidate_row()` (lines 827, 900), which reads `actual_verified = True` and sets `bdsVerified: True`.
  7. **Result**: The candidate is permanently and authoritatively recorded as BDS-verified across all future sessions, despite no BDS binary ever running.

---

## 4. The Actual Call Chain Required to Obtain Pinned BDS Observations

To obtain authentic BDS observations, the system must execute the full pipeline implemented in `src/seed_search/realm/verification.py`:

```
Client Request (POST /api/bds/verify)
  │
  ├─► 1. Parameter & Context Validation
  │     - Parse seed: parse_seed(seed)
  │     - Verify candidate exists in active run's RealmStore
  │     - Verify candidate has baseline status PREDICTED or VERIFIED
  │
  ├─► 2. Pin & Configuration Check
  │     - validate_bds_pins(cfg): version == '1.26.52.3', image == 'bedrock-verification-poc:1.26.52.3',
  │       image_id == 'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8',
  │       cpus == 4, memory_gib == 6
  │     - Tooling identity check: tooling_identity() SHA256 hashes of JS scripts, properties, and adapters
  │
  ├─► 3. Atomic Attempt Reservation
  │     - VerificationAdapter._reserve_attempt(budget):
  │       BEGIN IMMEDIATE on realm.sqlite
  │       Query bds_verification_used from meta table
  │       If used >= budget: abort with PARTIAL (reason: 'Verification budget exhausted')
  │       Increment and commit bds_verification_used BEFORE starting Docker
  │
  ├─► 4. Cross-Process Mutex & Recovery Guard
  │     - Acquire file lock on /tmp/realm-pinned-bds-verifier.lock via fcntl.flock(LOCK_EX)
  │     - Check CLEANUP_GUARD (/tmp/realm-pinned-bds-verifier.blocked.json). If uncleaned container exists, raise error
  │     - Write active container info to CLEANUP_GUARD
  │
  ├─► 5. Preflight Environment Checks
  │     - Docker inspect image ID == IMAGE_ID
  │     - Docker info host CPU count >= 4
  │     - Docker disk check: df -Pk /srv/bds >= 16 GiB + estimated growth
  │
  ├─► 6. Container Lifecycle & Script Execution
  │     - probe_tools.create(name, seed, cpus=4):
  │       Create volume, copy behavioral pack (main.js, column_policy.js), write poc-server.properties
  │       docker create and docker start
  │     - Console attach: wait for "Server started." (60s) and "PROBE_READY" (30s)
  │     - Execute scriptevents:
  │       * bds_probe:load: Create ticking areas for requested tiles (<= 256 side)
  │       * bds_probe:scan: Scan non-air column blocks
  │       * Stability audit: 4 passes, 1-second intervals, ensure 0 changes
  │       * Sky audit: Verify markers at Y=319
  │
  ├─► 7. Bounded Shutdown & Saved World Extraction
  │     - poc_control.cleanup_container:
  │       Send 'stop' command to console pipe, wait 20s
  │       Fallback to docker stop --time 10, then docker rm --force
  │       Require clean exit code 0
  │     - Snapshot world folder LevelDB
  │     - Run LevelDB comparison (compare_saved_blocks.py) in reader container
  │     - If palette state mismatches: restart container, run bds_probe:permutations_resolve
  │
  ├─► 8. Observation Assembly & Evidence Scope
  │     - Convert columns to Raster object (raster_from_columns)
  │     - Calculate height MAE, liquid presence, and surface biome names
  │     - Status is marked PARTIAL (sparse observations never certify absence or full Realm eligibility)
  │     - Persist observation in SQLite observations table
```

---

## 5. What BDS Provider Actually Establishes vs Unsupported Claims

| Domain | What Current BDS Provider CAN Establish | What Provider CANNOT Establish (Unsupported) |
| :--- | :--- | :--- |
| **Surface Columns & Voxel Height** | - Height ($Y$) of topmost non-air support block<br>- Liquid occupancy (`Block.isWaterlogged`)<br>- Multi-tick block stability<br>- LevelDB chunk palette consistency | - Continuous fractional fluid surface height<br>- Natural ground provenance (cannot distinguish terrain from structure blocks)<br>- Full formation closure between sampled columns |
| **Biomes** | - Surface biome string name at $(X, Z)$ via `dim.getBiome()`<br>- Point existence of biome families | - Numerical biome IDs (Script API exposes only names)<br>- Absence of a biome (sparse points cannot prove absence)<br>- Full 2D/3D biome boundaries across candidate envelope |
| **Generated Structures** | **NOTHING**: Script API 2.10.0 does NOT have structure enumeration (`dim.getGeneratedStructures` is `undefined`) | - Woodland Mansions ("mansionGroundTruth: CONFIRMED" is fake)<br>- Villages, Outposts, Witch Huts, Ancient Cities, Trial Chambers<br>- Strongholds and End Portal frames |
| **Portal Rooms** | **NOTHING**: No API to detect or inspect stronghold portal rooms | - Portal room status ("portalRoomStatus: INTACT" is fake)<br>- Eye of ender counts |
| **Nether Structures** | **NOTHING via BDS Script API**: Requires offline imported LevelDB evidence | - Fortress / Bastion generation via online container |
| **Loot** | **NOTHING**: No chest looting or entity inventory inspection | - Chest contents, eye counts, item generation |
| **Initial-Player Spawn** | - Downstream predicate classification on imported coordinates (`spawn.py`) | - Spawn point generation (BDS container runs headless with 0 players; initial player spawn is never calculated) |

---

## 6. Checks Needed to Harden the Verification System

To prevent unverified status inflation and system instability, the following checks must be implemented:

1. **Seed and Candidate Identity**:
   - Validate seed syntax with `parse_seed(seed)`.
   - Validate that `candidateId` belongs to the currently active or selected run.
   - Verify candidate satisfies baseline criteria (`qualification in ('PREDICTED', 'VERIFIED')`).
2. **Run Ownership and Concurrency**:
   - Verify caller has ownership of `runId`.
   - Prevent launching BDS verification if an OpenMP sweep is running with full resource allocation.
   - Enforce single-verifier lock using `/tmp/realm-pinned-bds-verifier.lock`.
   - Reject concurrent verification requests with HTTP 409 Conflict.
3. **Pinned Environment Verification**:
   - Query Docker daemon for image existence and check `IMAGE_ID == 'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'`.
   - If Docker is unavailable, return HTTP 503 with status `UNSUPPORTED`. Never fallback to mock data.
   - Verify `poc-server.properties` matches `pinned_world_settings()`.
   - Verify tooling hashes match `tooling_identity()`.
4. **Attempt Budgeting**:
   - Atomically reserve attempt in `realm.sqlite` table `meta` under `bds_verification_used` using `BEGIN IMMEDIATE`.
   - If `used >= budget`, return status `PARTIAL` with reason `"Verification budget exhausted"`.
   - Interrupted or failed runs must remain consumed.
5. **Observation Bounds**:
   - Require explicit integer bounds with maximum side $\le 256$ blocks.
   - Bound tile count to `max_tiles_per_request` (default 16).
6. **Subprocess Cleanup & Retries**:
   - Enforce timeouts on all Docker operations (60s on commands, 45s on console events).
   - In `finally` block, call `cleanup_container` with graceful console `stop`, followed by `docker stop --time 10`, then `docker rm --force`.
   - Manage `/tmp/realm-pinned-bds-verifier.blocked.json` cleanup guard.
   - Cache failures; require `retry_failed=True` to re-attempt.

---

## 7. Regression-Test Scenarios

The test specifications detailed in `reviews/gemini/bds/regression_test_plan.md` must be incorporated into automated test suites:

1. **Unavailable Docker**:
   - Mock `docker` CLI failure or stopped daemon.
   - Verify endpoint returns `status: "UNSUPPORTED"`, does not modify `realm.sqlite`, and does not set `bdsVerified = True`.
2. **Provider Failure / Container Crash**:
   - Simulate container crash during column scan.
   - Verify cleanup handler kills container, consumes attempt in `bds_verification_used`, records observation as `FAILED`, and leaves candidate unverified.
3. **Partial Observation**:
   - Return valid columns for a $128 \times 128$ tile.
   - Verify returned status is `PARTIAL`, measured metrics reflect actual columns, and structures/portal rooms are marked `UNSUPPORTED`.
4. **Repeated Requests**:
   - Issue consecutive requests for the same candidate.
   - Verify second request returns cached observation without consuming additional attempt slots or re-running Docker.
5. **Concurrent Sweep / Verification**:
   - Attempt verification while sweep is active.
   - Verify system enforces mutual exclusion or resource checks and does not encounter SQLite database locks.

---

## 8. Proposed Code Fixes

### 8.1 Remove Mock Fabrication from `src/seed_search/web/server.py`
In `src/seed_search/web/server.py`, replace lines 637–705 with a truthful delegation to `VerificationAdapter`:
```python
    def verify_bds_candidate(self, seed: str | int | None = None, candidate_id: str | None = None) -> dict:
        with self.lock:
            # 1. Validate active run and candidate
            if not self.run_dir or not (self.run_dir / "realm.sqlite").is_file():
                return {"ok": False, "status": "UNSUPPORTED", "error": "No active run directory"}
            cand = next((c for c in self.candidates if str(c.get("seed")) == str(seed) or c.get("id") == candidate_id), None)
            if not cand:
                return {"ok": False, "status": "UNSUPPORTED", "error": "Candidate not found in active sweep"}
            seed_val = str(cand["seed"])

        # 2. Check Docker availability without blocking
        from seed_search.realm.bds_tools import poc_control as control
        try:
            control.docker("info", capture_output=True, text=True, timeout=5)
        except Exception as exc:
            return {"ok": False, "status": "UNSUPPORTED", "error": f"Docker unavailable: {exc}"}

        # 3. Delegate to genuine VerificationAdapter (or defer to background queue)
        # Note: Must NOT fabricate portalRoomStatus or mansionGroundTruth
        return {
            "ok": False,
            "status": "UNSUPPORTED",
            "error": "Real-time BDS container verification requires background task queue integration; simulated metrics disabled.",
        }
```

### 8.2 Cleanse Frontend Handlers in `web-ui/src/App.tsx`
Remove lines 322–326 and 342–345 that inject fake accuracy and claims of portal rooms:
```typescript
        if (data && data.ok && data.bdsVerified) {
          // Update only with verified provider data from server
          ...
        } else {
          showToast(`BDS verification unsupported or failed: ${data?.error || 'Unknown error'}`);
        }
```

### 8.3 Update SeedDetailModal Copy
Change `web-ui/src/components/SeedDetailModal.tsx` line 386 and 427:
- Clarify that BDS verifies surface voxel columns and liquid presence only.
- Remove references claiming BDS verifies structure generation or portal rooms.

---

## 9. File References & Check Results

- [`src/seed_search/web/server.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py): Contains mock metrics (lines 653-660), in-memory mutation (lines 665-667), database poisoning (lines 670-692), and `/api/bds/verify` route (lines 1166-1175).
- [`web-ui/src/App.tsx`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/App.tsx): Contains client fallback fabrication (lines 322-326) and fake log messages (line 343).
- [`web-ui/src/components/SeedDetailModal.tsx`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/components/SeedDetailModal.tsx): Displays hardcoded accuracy metrics and misleading button tooltips (lines 374-441).
- [`web-ui/src/mockData.ts`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/mockData.ts): Injects mock seeds with `bdsVerified: true` and identical fake accuracy numbers (lines 117-124, 170-176).
- [`src/seed_search/realm/verification.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/verification.py): Genuine verification adapter with image pins, budget accounting, and LevelDB comparisons.
- [`src/seed_search/realm/bds_tools/main.js`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/main.js): Script API probe demonstrating that `getGeneratedStructures` is `undefined` (line 128).
- [`src/seed_search/realm/bds_tools/COLUMN_POLICY.md`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/realm/bds_tools/COLUMN_POLICY.md): Documents that structure enumeration is unavailable and observations remain sparse evidence.

---

## 10. Unresolved Questions

1. **Asynchronous Verification Architecture**: BDS world creation and chunk loading take 10–30 seconds. Should `/api/bds/verify` be converted into an asynchronous polling job (e.g. `POST /api/bds/verify/jobs` returning a `jobId`), or should BDS verification remain strictly a CLI / offline tool (`seed_search verify-terrain`, `seed_search verify-biomes`)?
2. **Handling Legacy Poisoned Databases**: Existing runs that had BDS verification triggered via the UI now have `actual_generation_verification: {status: "VERIFIED"}` in their SQLite `candidates` table. A database cleanup migration script is needed to purge fabricated verification records from historical `realm.sqlite` files.
3. **Structure Ground Truth Provider**: Since BDS Script API 2.10.0 cannot inspect structures, will structure ground truth be provided via offline NBT LevelDB parsers, or will structures remain strictly at the PREDICTED level?
