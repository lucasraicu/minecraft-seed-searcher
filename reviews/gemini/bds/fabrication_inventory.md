> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# Audit Inventory: Fabricated BDS Verification Values and Routes

**Audit Date**: October 2026
**Auditor**: Task 3: BDS Verification Integrity Audit
**Scope**: Verification integrity, evidence handling, mocked metrics, database mutations, and web endpoints.

---

## 1. Executive Summary of Integrity Violations

The codebase contains an **unconditional, fabricated BDS verification pathway** in `src/seed_search/web/server.py` and `web-ui/src/App.tsx`.

When a user requests BDS verification (either via the Web UI button or by issuing `POST /api/bds/verify`), the system **does not invoke Docker, does not launch BDS, does not execute any Script API probes, does not check LevelDB world storage, and does not perform any candidate validation**.

Instead, it:
1. Synthesizes hardcoded metrics (`99.8% palette agreement`, `height MAE 0.14`, `portalRoomStatus: "INTACT"`, `mansionGroundTruth: "CONFIRMED"`).
2. Updates in-memory candidates to `bdsVerified = True` and `actualGenerationStatus = "VERIFIED"`.
3. **Poisons the persistent SQLite database** (`realm.sqlite` and `candidates.db`) by writing a fake `actual_generation_verification` record.
4. Emits fake log messages and UI toasts claiming authoritative confirmation against Mojang Bedrock Dedicated Server 1.26.52.3.
5. Injects mock seeds in `web-ui/src/mockData.ts` with identical hardcoded numbers.

---

## 2. Inventory of Fabricated Values and Line References

### 2.1 Backend Server (`src/seed_search/web/server.py`)

#### A. Hardcoded Mock Metrics
* **File**: [`src/seed_search/web/server.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L653-L660)
* **Lines**: 653–660
* **Code**:
  ```python
  metrics = {
      "paletteAgreement": "99.8%",
      "heightMae": 0.14,
      "settledColumns": 4096,
      "provider": "official BDS 1.26.52.3",
      "portalRoomStatus": "INTACT",
      "mansionGroundTruth": "CONFIRMED",
  }
  ```
* **Integrity Violation**:
  - The values `99.8%`, `0.14`, and `4096` are fixed constants returned for *any* seed, regardless of terrain.
  - `portalRoomStatus: "INTACT"` is completely fictitious: the BDS Script API adapter does not sample portal rooms or End Portal frames.
  - `mansionGroundTruth: "CONFIRMED"` is completely fictitious: Woodland Mansions cannot be enumerated or inspected by BDS Script API 2.10.0.

#### B. In-Memory State Falsification
* **File**: [`src/seed_search/web/server.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L663-L668)
* **Lines**: 663–668
* **Code**:
  ```python
  with self.lock:
      for c in self.candidates:
          if c.get("seed") == seed_val or (candidate_id and c.get("id") == candidate_id):
              c["bdsVerified"] = True
              c["bdsAccuracy"] = metrics
              c["actualGenerationStatus"] = "VERIFIED"
  ```
* **Integrity Violation**:
  - Modifies the candidate in the live sweep manager to `VERIFIED` without any actual observation.

#### C. Database Poisoning
* **File**: [`src/seed_search/web/server.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L669-L693)
* **Lines**: 669–693
* **Code**:
  ```python
  if self.run_dir:
      for db_name in ("candidates.db", "realm.sqlite"):
          db_path = self.run_dir / db_name
          if db_path.exists():
              try:
                  conn = sqlite3.connect(str(db_path))
                  cur = conn.cursor()
                  cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidates'")
                  if cur.fetchone():
                      cur.execute("SELECT id, result FROM candidates WHERE seed = ?", (seed_val,))
                      row = cur.fetchone()
                      if row:
                          cid, raw_str = row[0], row[1]
                          raw_dict = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
                          raw_dict["actual_generation_verification"] = {
                              "status": "VERIFIED",
                              "source": {"kind": "actual_generation", "version": "1.26.52.3"},
                              "metrics": metrics,
                          }
                          cur.execute("UPDATE candidates SET result = ? WHERE id = ?", (json.dumps(raw_dict), cid))
                          conn.commit()
                  conn.close()
              except Exception:
                  pass
  ```
* **Integrity Violation**:
  - Durably overwrites the candidate JSON in `realm.sqlite` / `candidates.db`.
  - Sets `source.kind = "actual_generation"`, which causes subsequent reads in `parse_candidate_row` to treat this candidate as authentically verified by BDS.
  - Silently swallows all database exceptions (`except Exception: pass`).

#### D. Fraudulent Log and HTTP Response
* **File**: [`src/seed_search/web/server.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L695-L704)
* **Lines**: 695–704
* **Code**:
  ```python
  self.logs.insert(0, f"✅ BDS 1.26.52.3 Parity Verified: seed {seed_val} confirmed (99.8% palette agreement, height MAE 0.14)")

  return {
      "ok": True,
      "seed": seed_val,
      "candidateId": candidate_id or f"cand-{seed_val}",
      "bdsVerified": True,
      "bdsAccuracy": metrics,
      "actualGenerationStatus": "VERIFIED",
  }
  ```
* **Integrity Violation**:
  - Returns HTTP 200 with `bdsVerified: True` and logs confirmation to the user telemetry stream.

#### E. End-to-End Route Exposure Without Checks
* **File**: [`src/seed_search/web/server.py`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/src/seed_search/web/server.py#L1166-L1175)
* **Lines**: 1166–1175
* **Code**:
  ```python
  elif path == "/api/bds/verify":
      result = MANAGER.verify_bds_candidate(
          seed=req_data.get("seed"),
          candidate_id=req_data.get("candidateId"),
      )
      self.send_response(200 if result.get("ok") else 400)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps(result).encode("utf-8"))
      return
  ```
* **Integrity Violation**:
  - Does not check if Docker is running.
  - Does not check run ownership or authentication.
  - Does not check whether the seed is even part of the current sweep.
  - Executes synchronously inside the HTTP handler thread, fabricating data instantly.

---

### 2.2 Frontend Handlers (`web-ui/src/App.tsx`)

#### A. Client-Side Fallback Fabrication
* **File**: [`web-ui/src/App.tsx`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/App.tsx#L321-L327)
* **Lines**: 321–327
* **Code**:
  ```typescript
  if (data && data.ok) {
    const accuracy = data.bdsAccuracy || {
      paletteAgreement: '99.8%',
      heightMae: 0.14,
      settledColumns: 4096,
    };
  ```
* **Integrity Violation**:
  - Even if the server were to return `bdsAccuracy: null` or omitted, the frontend provides fallback mock numbers (`99.8%`, `0.14`, `4096`).

#### B. Forced Client State Override
* **File**: [`web-ui/src/App.tsx`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/App.tsx#L328-L346)
* **Lines**: 328–346
* **Code**:
  ```typescript
  const updateCand = (c: SeedCandidate): SeedCandidate =>
    c.id === cand.id || c.seed === cand.seed
      ? {
          ...c,
          bdsVerified: true,
          bdsAccuracy: accuracy,
          actualGenerationStatus: 'VERIFIED',
        }
      : c;

  setCandidates((prev) => prev.map(updateCand));
  setSelectedCandidate((prev) => (prev ? updateCand(prev) : null));
  setInspectedCandidate((prev) => (prev ? updateCand(prev) : null));

  setLogs((prev) => [
    `[BDS] Seed ${cand.seed} confirmed: 99.8% palette agreement, height MAE 0.14 blocks, portal room intact.`,
    ...prev,
  ]);
  showToast(`✅ BDS Parity Verified! ${cand.seed} confirmed`);
  ```
* **Integrity Violation**:
  - The client UI asserts `portal room intact` in the user log feed, despite no portal room inspection ever occurring.

---

### 2.3 UI Display Elements (`web-ui/src/components/SeedDetailModal.tsx`)

#### A. Deceptive Action Tooltip and Copy
* **File**: [`web-ui/src/components/SeedDetailModal.tsx`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/components/SeedDetailModal.tsx#L386-L390)
* **Lines**: 386–390, 426–437
* **Code**:
  ```tsx
  title="Run Docker BDS 1.26.52.3 verification on this seed"
  ...
  <span>{isVerifyingBDS ? 'Verifying BDS...' : candidate.bdsVerified ? 'Re-verify BDS Parity' : 'Begin BDS Parity'}</span>
  ...
  <p className="text-xs text-slate-400">
    BDS ground-truth verification audit confirms runtime voxel blocks against official Mojang bedrock server binary when activated.
  </p>
  ...
  <span>{isVerifyingBDS ? 'Running BDS 1.26.52.3 Container...' : 'Begin BDS Parity Verification'}</span>
  ```
* **Integrity Violation**:
  - Prompts the user that clicking will launch a Docker container to verify runtime voxel blocks against the official Mojang bedrock server binary, when the endpoint merely fabricates the response in <10 milliseconds.

---

### 2.4 Mock Seed Data (`web-ui/src/mockData.ts`)

#### A. Hardcoded BDS Verification in Seed Catalog
* **File**: [`web-ui/src/mockData.ts`](file:///Users/lucasraicu/Downloads/minecraft-seed-searcher/web-ui/src/mockData.ts#L117-L123)
* **Lines**: 117–123, 170–176
* **Code**:
  ```typescript
  bdsVerified: true,
  bdsAccuracy: {
    paletteAgreement: '99.8%',
    heightMae: 0.14,
    settledColumns: 4096,
  },
  ```
* **Integrity Violation**:
  - Canned seeds `-839210492817492` and `4920194820194` are permanently marked `bdsVerified: true` with the identical fabricated numbers.

---

## 3. Disconnect Between Mock Routes and Core Adapter

In stark contrast to the web server and UI mocks, the underlying engine in `src/seed_search/realm/` contains an elaborate, strictly pinned verification architecture:
* `src/seed_search/realm/verification.py` (`VerificationAdapter`)
* `src/seed_search/realm/surface.py` (`verify_surface_families`)
* `src/seed_search/realm/bds_tools/` (`poc_control.py`, `probe_tools.py`, `column_policy.js`)

However, **`SweepManager.verify_bds_candidate` NEVER calls `VerificationAdapter` or any function in `seed_search.realm.verification`**. The entire real verification pipeline is bypassed by the web server.
