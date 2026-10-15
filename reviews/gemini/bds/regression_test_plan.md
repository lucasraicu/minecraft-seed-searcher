> Historical Gemini review snapshot. Claims may describe an earlier working tree; see `reviews/CODEX_INTEGRATION_REVIEW.md` and `LATEST_PUSH_REVIEW.md` for accepted findings, corrections and executed checks. This document is not a production certificate.

# BDS Verification: Regression-Test Scenarios & Hardening Specification

**Audit Date**: October 2026
**Subject**: Test Scenarios for BDS Verification Integrity and Fault Tolerance
**Target Test Suite**: `tests/test_bds_web_verification_regression.py` (Proposed)

---

## 1. Regression Scenario Specifications

### Scenario 1: Unavailable Docker Daemon or CLI
* **Failure Trigger**: Docker CLI missing from PATH, Docker daemon stopped, or `docker info` fails with connection error.
* **Expected System Behavior**:
  1. `/api/bds/verify` returns HTTP 503 or `{ok: False, status: "UNSUPPORTED", error: "Docker daemon unavailable"}`.
  2. Candidate state remains unchanged (`bdsVerified` remains `None` or `False`).
  3. No fake metrics are synthesized.
  4. Persistent database (`realm.sqlite`) is NOT modified.
  5. Verification attempt budget is NOT consumed.
* **Current Defect**: Currently returns HTTP 200 with `bdsVerified: True`, `paletteAgreement: "99.8%"`, and poisons the database even if Docker is not installed.

### Scenario 2: Provider Failure / Container Crash
* **Failure Trigger**: BDS server crashes during extraction (SIGSEGV, out of memory, or Script API unhandled rejection).
* **Expected System Behavior**:
  1. Cleanup handler (`poc_control.cleanup_container`) invokes graceful `stop`, followed by `docker stop --time 10`, followed by `docker rm --force` if necessary.
  2. Cleanup guard file (`/tmp/realm-pinned-bds-verifier.blocked.json`) records status or is cleanly unlinked.
  3. Attempt slot is counted as consumed in `meta` (`bds_verification_used`).
  4. Candidate observation status is marked `FAILED` in SQLite `observations` table.
  5. The candidate is NOT marked `VERIFIED`.
  6. Return payload explicitly reports `{ok: False, status: "FAILED", error: "..."}`.
* **Current Defect**: The web handler catches no provider failures because it never runs the provider.

### Scenario 3: Partial Observation & Bounded Sampling
* **Context**: BDS verifies a bounded $128 \times 128$ or $256 \times 256$ tile. Column observations succeed, but only cover the sampled lattice.
* **Expected System Behavior**:
  1. Observation status is `PARTIAL`.
  2. Measured metrics (e.g. `sample_count`, `height_mae_blocks`) reflect the actual column comparison.
  3. Generated structures (mansions, fortresses, portal rooms) are marked `UNSUPPORTED` or omitted.
  4. Candidate `realm_eligibility` remains `PENDING` or `UNCHANGED`.
* **Current Defect**: Web handler claims `mansionGroundTruth: "CONFIRMED"` and `portalRoomStatus: "INTACT"`.

### Scenario 4: Repeated Requests & Idempotent Cache Replay
* **Context**: Client triggers `/api/bds/verify` multiple times for the same candidate.
* **Expected System Behavior**:
  1. First request executes verification, consumes 1 attempt budget slot, and records the observation.
  2. Second request identifies identical observation key (`observation_id`) in SQLite or memory cache.
  3. Returns cached result without launching a second Docker container and without incrementing `bds_verification_used`.
  4. If first request failed, returns cached `FAILED` record unless client explicitly specifies `retry_failed=True`.
* **Current Defect**: Web handler does not cache observations; it repeatedly re-poisons the DB on every click.

### Scenario 5: Concurrent Sweep and Verification Attempts
* **Context**:
  - Case A: A high-throughput OpenMP sweep is running when `/api/bds/verify` is triggered.
  - Case B: Two `/api/bds/verify` requests arrive simultaneously for different seeds.
* **Expected System Behavior**:
  1. Resource reservation check: BDS requires 4 CPUs and 6 GiB RAM. If sweep uses 34 threads and all system RAM, verification must be rejected with 409 Conflict / 503 or cleanly queued.
  2. Concurrency lock: Only one BDS container may run at a time per host. The second request must block on `realm-pinned-bds-verifier.lock` or return 409.
  3. Database writes must use `BEGIN IMMEDIATE` or WAL mode to prevent SQLite lock collisions between the scanner and the verifier.
* **Current Defect**: Web handler acquires only a local Python `threading.Lock()` inside `SweepManager`, then writes directly to `realm.sqlite` without handling potential `sqlite3.OperationalError: database is locked`.

---

## 2. Concrete Test Code Blueprint

Here is the concrete test suite blueprint to prevent these regressions:

```python
"""Regression tests verifying BDS endpoint integrity and preventing mock fabrications."""
import json
import sqlite3
import pytest
from seed_search.web import server

def test_bds_verify_endpoint_rejects_missing_candidate(monkeypatch, tmp_path):
    """BDS verification must reject requests for candidates not in the active run."""
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path)
    manager = server.SweepManager()

    # Empty manager without active run
    result = manager.verify_bds_candidate(seed="12345", candidate_id="cand-12345")
    # Must fail or return unsupported, NOT synthesize fake 99.8% metrics
    assert not result.get("ok") or result.get("status") in ("UNSUPPORTED", "FAILED")
    assert "portalRoomStatus" not in result.get("bdsAccuracy", {})

def test_bds_verify_does_not_fabricate_unsupported_structures(monkeypatch, tmp_path):
    """BDS verification metrics must never claim mansion or portal room ground truth."""
    manager = server.SweepManager()
    result = manager.verify_bds_candidate(seed="99999")
    if result.get("ok"):
        accuracy = result.get("bdsAccuracy", {})
        assert "mansionGroundTruth" not in accuracy, "Mansion ground truth cannot be established by BDS"
        assert "portalRoomStatus" not in accuracy, "Portal room status cannot be established by BDS"

def test_bds_verify_fails_gracefully_when_docker_unavailable(monkeypatch):
    """When docker CLI fails, verify endpoint must report UNSUPPORTED, not VERIFIED."""
    def fake_check_docker():
        raise RuntimeError("Docker daemon not running")

    # When docker is unavailable, verification must report failure
    manager = server.SweepManager()
    # Ensure no DB corruption occurs
    # Candidate status must remain PENDING / UNVERIFIED
```
