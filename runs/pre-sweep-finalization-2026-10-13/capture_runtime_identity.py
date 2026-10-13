#!/usr/bin/env python3
"""Capture frozen source, policy and native identities before final holdout."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    control = ROOT / "runs/pre-sweep-v2-2026-10-13/control-native"
    selected = ROOT / "runs/cpu-completion-2026-10-13/final-portable"
    policies = {
        "control": ROOT / "runs/pre-sweep-v2-2026-10-13/control-policy-before-order.yaml",
        "selected": ROOT / "config/realm.yaml",
    }
    files = sorted((ROOT / "src/seed_search").rglob("*.py"))
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in files}
    hashes.update({str(path.relative_to(ROOT)): sha(path) for path in policies.values()})
    builds = {}
    for name, path in (("control", control), ("selected", selected)):
        identity_path = path / "identity.json"
        identity = json.loads(identity_path.read_text())
        builds[name] = {
            "path": str(path), "identity_sha256": sha(identity_path),
            "extension_sha256": identity["extension_sha256"],
            "source_digest": identity["source_digest"],
            "builder_script_sha256": identity["inputs"].get("scripts/build_blueprint_batch.py"),
            "openmp_runtime_sha256": identity["runtime_sha256"],
            "flags": identity["flags"],
            "experiment_order": identity.get("experiment_order"),
            "stronghold_after": identity.get("stronghold_after"),
        }
    report = {
        "schema": "cpu-completion-final-runtime-identity-v1",
        "freeze_captured_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "platform": platform.platform(), "python_version": sys.version,
        "policy_sha256": {name: sha(path) for name, path in policies.items()},
        "python_source_sha256": hashes,
        "runtime_source_digest": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
        "builds": builds,
        "native_build_identity_sha256": builds["selected"]["identity_sha256"],
        "native_extension_sha256": builds["selected"]["extension_sha256"],
        "native_source_digest": builds["selected"]["source_digest"],
        "openmp_runtime_sha256": builds["selected"]["openmp_runtime_sha256"],
    }
    (HERE / "final-runtime-identity.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"runtime_source_digest": report["runtime_source_digest"],
                      "selected_extension": builds["selected"]["extension_sha256"]}))


if __name__ == "__main__":
    main()
