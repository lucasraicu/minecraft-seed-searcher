"""Rebuild the dynamic-baseline-1664 native engine with PGO + LTO and measure throughput."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.seeds import seed_from_index

OPENMP = ROOT / "runs/master-implementation-2026-10-10/openmp/install"
OUTPUT = ROOT / "runs/dynamic-baseline-1664/native"
TRAIN_DIR = ROOT / "runs/dynamic-baseline-1664/pgo-training"
PROF_DIR = ROOT / "runs/dynamic-baseline-1664/prof"

def main():
    print("[1/5] Building instrumented PGO training binary...")
    if TRAIN_DIR.exists():
        shutil.rmtree(TRAIN_DIR)
    if PROF_DIR.exists():
        shutil.rmtree(PROF_DIR)
    PROF_DIR.mkdir(parents=True, exist_ok=True)

    build(TRAIN_DIR, openmp_prefix=str(OPENMP), work_chunk=16, cpu_native=True, lto=True, pgo_generate=True)

    print("[2/5] Running training workload on 10,000 seeds + synthetic fixtures...")
    env = os.environ.copy()
    env["LLVM_PROFILE_FILE"] = str(PROF_DIR / "train-%p.profraw")
    code = """
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.seeds import seed_from_index
import sys
p = Prototype(sys.argv[1], dynamic_v2_blueprint_config())
with p.sweep([seed_from_index(i, 2026101402) for i in range(10000)], 4, retention='survivors'): pass
with p.sweep([1], fixtures=[(0, 0, -1)], retention='survivors'): pass
"""
    subprocess.run([sys.executable, "-c", code, str(TRAIN_DIR)], env=env, check=True)

    print("[3/5] Merging llvm profile data...")
    tool = shutil.which("llvm-profdata") or subprocess.check_output(["xcrun", "--find", "llvm-profdata"], text=True).strip()
    profile = PROF_DIR / "trained.profdata"
    raw_files = list(PROF_DIR.glob("train-*.profraw"))
    subprocess.run([tool, "merge", "-output", str(profile), *[str(p) for p in raw_files]], check=True)

    # Write manifest matching training build
    meta = json.loads((TRAIN_DIR / "identity.json").read_text())
    meta["profile_sha256"] = hashlib.sha256(profile.read_bytes()).hexdigest()
    profile.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")

    print("[4/5] Compiling final optimized PGO + LTO production binary...")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    build(OUTPUT, openmp_prefix=str(OPENMP), work_chunk=16, cpu_native=True, lto=True, pgo_use=profile)

    # Copy to src/seed_search production location
    so_files = list(OUTPUT.glob("*.so"))
    if so_files:
        dest = ROOT / "src/seed_search/_blueprint_batch.abi3.so"
        shutil.copy2(so_files[0], dest)
        print(f"  Copied production binary to {dest}")

    # Cleanup temporary training dirs
    shutil.rmtree(TRAIN_DIR, ignore_errors=True)
    shutil.rmtree(PROF_DIR, ignore_errors=True)

    print("[5/5] Measuring kernel throughput on 34 threads with batch sizes 8192 & 16384...")
    p = Prototype(OUTPUT, dynamic_v2_blueprint_config())
    seeds = [seed_from_index(i, 2026101401) for i in range(50000)]
    for batch_size in (8192, 16384):
        total_time = 0.0
        for offset in range(0, 50000, batch_size):
            cohort = seeds[offset:offset + batch_size]
            with p.sweep(cohort, 34, retention="survivors") as b:
                total_time += b.native_seconds
        rate = 50000 / total_time
        print(f"  34 threads | Batch {batch_size:<6} | 50,000 seeds in {total_time:.3f}s -> {rate:,.1f} seeds/sec")

if __name__ == "__main__":
    main()

