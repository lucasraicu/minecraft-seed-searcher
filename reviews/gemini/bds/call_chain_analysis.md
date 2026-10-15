> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# BDS Verification: Pinned Call Chain Architecture vs Mock Bypass

**Audit Date**: October 2026
**Subject**: End-to-End Call Chain for Pinned BDS Observations

---

## 1. The Pinned BDS Verification Architecture

To obtain authentic, cryptographically pinned BDS ground-truth observations, the system was designed with a rigorous multi-stage pipeline:

```
[User / CLI / Web Request]
          │
          ▼
1. Validation & Preflight Checks
   - Seed validation (parse_seed)
   - Candidate eligibility in active run
   - Pinned settings check (BUILD 1.26.52.3, IMAGE_ID, tooling hashes)
   - Host resources preflight (4 CPUs, 6 GiB RAM, >=16 GiB + growth disk)
          │
          ▼
2. Attempt Reservation (Transactional)
   - Store: `BEGIN IMMEDIATE` on `realm.sqlite`
   - Check `bds_verification_used < verification_budget`
   - Increment and commit `bds_verification_used` BEFORE execution
          │
          ▼
3. Process Serialization & Guard Locking
   - File lock: `fcntl.flock(LOCK_EX)` on `/tmp/realm-pinned-bds-verifier.lock`
   - Check `/tmp/realm-pinned-bds-verifier.blocked.json` for dirty crash recovery
   - Write cleanup guard with active container metadata
          │
          ▼
4. Docker BDS Lifecycle Execution (`_extract_locked`)
   - `probe_tools.create(name, seed, cpus=4)`:
     * Creates Docker volume `<name>-data`
     * Mounts behavior pack (`main.js`, `column_policy.js`, `manifest.json`)
     * Writes `server.properties` with pinned world settings and `level-seed`
     * Creates and starts container with `--cpus 4 --memory 6g`
   - Attach console & follow logs (`poc_control.Console`):
     * Wait for `"Server started."` (timeout 60s)
     * Wait for `"PROBE_READY"` (timeout 30s)
          │
          ▼
5. Script API Probing via scriptevents
   - `scriptevent bds_probe:load`: Creates ticking area, waits for chunks
   - `scriptevent bds_probe:scan`: Scans non-air column blocks
   - Stability check: 4 passes, 1-second intervals; verifies 0 changed columns
   - Sky check: Verifies non-air markers and restoration
          │
          ▼
6. Bounded Graceful Shutdown & Snapshotting
   - Console command `stop` (timeout 5s); wait for clean exit (code 0)
   - Fallback: `docker stop --time 10` -> `docker rm --force`
   - Clear cleanup guard on confirmed exit
   - Copy world folder LevelDB from container volume to host evidence directory
   - Check LevelDB chunk coverage and signed seed
          │
          ▼
7. Authoritative Paletted Ground Truth & Semantics
   - Compare in-memory columns against LevelDB chunks (`compare_saved_blocks.py`)
   - If state mismatches: restart container, run `permutations_resolve`
   - Raster conversion: construct `Raster` with actual heights, liquid depth, surface biomes
          │
          ▼
8. Persistence & Score Policy Integration
   - Save observation to SQLite `observations` table
   - Update candidate `variants` or `surface_biome_verification`
   - Record data status as `PARTIAL` (sparse observation, never full certified membership)
```

---

## 2. The Current Mock Bypass (Defect Analysis)

In contrast to the rigorous chain above, the current web server implementation completely bypasses all 8 stages:

```
[Web UI "Begin BDS Parity" Button]
          │
          ▼
   POST /api/bds/verify
          │
          ▼
`SweepManager.verify_bds_candidate(seed, candidate_id)`
  - Acquires `self.lock` (internal threading lock only)
  - Sets `self.status = "bds_verifying"`
  - Synthesizes static dictionary:
      paletteAgreement: "99.8%"
      heightMae: 0.14
      settledColumns: 4096
      portalRoomStatus: "INTACT"
      mansionGroundTruth: "CONFIRMED"
  - Mutates candidate in `self.candidates`:
      bdsVerified = True
      actualGenerationStatus = "VERIFIED"
  - Injects fake record into `candidates` table in `realm.sqlite`:
      raw_dict["actual_generation_verification"] = {"status": "VERIFIED", ...}
  - Emits fake log: "✅ BDS 1.26.52.3 Parity Verified..."
  - Resets `self.status`
  - Returns HTTP 200 with fake metrics
```

### Breakdown of Missing Checks:

1. **Zero Validation of Environment**:
   - `docker` is never invoked. The server will happily return "VERIFIED" even on a machine without Docker installed or without network access.
2. **Zero Budget Accounting**:
   - `_reserve_attempt` is never called. Unlimited verification clicks can occur without consuming the configured `verification_budget`.
3. **No Process Serialization**:
   - Concurrently calling `/api/bds/verify` bypasses `realm-pinned-bds-verifier.lock` and directly mutates the SQLite database with uncoordinated writes.
4. **False Parity Certification**:
   - Claims portal rooms and mansions are intact and confirmed, which the real provider cannot even detect.
5. **Irreversible Database Corruption**:
   - Writing `actual_generation_verification: {status: "VERIFIED"}` corrupts the scientific integrity of the run dataset. Any subsequent resume or analysis script inspecting `realm.sqlite` treats this candidate as empirically verified against BDS ground truth.

---

## 3. Required Remediation Architecture

To connect the Web API to the actual BDS verification adapter safely:

```
                          ┌────────────────────────┐
                          │  POST /api/bds/verify  │
                          └───────────┬────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │ Validate Run & Candidate  │
                        │ - Active run selected?    │
                        │ - Candidate in DB?        │
                        │ - Seed matches candidate? │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Check Docker Daemon     │
                        │   docker info / inspect   │
                        └─────────────┬─────────────┘
                                      │
                         Available? ──┴── Not Available? ──► Return 503 Service Unavailable
                                      │                     (status: "UNSUPPORTED")
                                      ▼
                        ┌───────────────────────────┐
                        │   Spawn Background Task   │
                        │   (Do not block HTTP)     │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   VerificationAdapter     │
                        │   - Reserve attempt slot  │
                        │   - Acquire file lock     │
                        │   - Run BDS container     │
                        │   - Extract column raster │
                        │   - Clean up container    │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Persist Real Evidence   │
                        │   - Write observation row │
                        │   - Status: PARTIAL       │
                        │   - Real measured MAE     │
                        └───────────────────────────┘
```
