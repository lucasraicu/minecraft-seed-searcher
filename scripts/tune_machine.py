"""Bounded native-kernel thread/batch comparison; durable sweep throughput is measured separately."""
import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.seeds import seed_from_index


def find_default_openmp_prefix() -> Path | None:
    if platform.system() == "Darwin":
        try:
            res = subprocess.run(["brew", "--prefix", "libomp"], capture_output=True, text=True, check=True)
            prefix = Path(res.stdout.strip())
            if (prefix / "include/omp.h").is_file():
                return prefix
        except Exception:
            pass
        common = [
            ROOT / "runs/master-implementation-2026-10-10/openmp/install",
            Path("/opt/homebrew/opt/libomp"),
            Path("/usr/local/opt/libomp"),
        ]
        for p in common:
            if (p / "include/omp.h").is_file():
                return p
    else:
        # Linux standard paths
        common_linux = [Path("/usr"), Path("/usr/local")]
        for p in common_linux:
            if (p / "include/omp.h").is_file():
                return p
    return None


def tune_machine(native_dir: Path, openmp_prefix: Path | None, count: int = 30000):
    if type(count) is not int or not 1 <= count <= 50000:
        raise ValueError("Tuning trials must contain 1–50,000 inputs")
    detected_cpus = os.cpu_count() or 1
    # The production sweep accepts at most 34 native threads, even on larger hosts.
    total_cpus = min(34, detected_cpus)
    system = platform.system()
    machine = platform.machine()

    print(f"\n=======================================================")
    print(f"  Hardware Detection: {system} ({machine}) with {detected_cpus} Logical Cores")
    print(f"  Supported native sweep threads: 1–{total_cpus}")
    print(f"=======================================================\n")

    native_dir = native_dir.resolve()
    rebuild = True
    if (native_dir / "identity.json").is_file():
        try:
            import json
            meta = json.loads((native_dir / "identity.json").read_text())
            import hashlib
            inputs=meta.get('inputs') or {}
            current=bool(inputs) and all((ROOT/name).is_file() and hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in inputs.items())
            if current and (not openmp_prefix or meta.get("openmp")):
                rebuild = False
        except Exception:
            rebuild = True

    if rebuild:
        print(f"[*] Building native OpenMP engine in {native_dir}...")
        prefix_arg = str(openmp_prefix) if openmp_prefix else None
        build(native_dir, openmp_prefix=prefix_arg, cpu_native=machine.lower() in ("x86_64", "amd64"), work_chunk=64 if detected_cpus >= 64 else 16)
        print("[*] Build complete.\n")

    prototype = Prototype(native_dir, dynamic_blueprint_config())

    # Build an intelligent candidate thread grid based on core count
    candidate_threads = set()
    candidate_threads.add(max(1, total_cpus // 2))
    candidate_threads.add(max(1, int(total_cpus * 0.75)))
    if total_cpus > 8:
        candidate_threads.add(total_cpus - 2)
        candidate_threads.add(total_cpus - 4)
    candidate_threads.add(total_cpus)
    thread_list = sorted([t for t in candidate_threads if 1 <= t <= total_cpus]) if prototype.identity["openmp"] else [1]

    # Batch sizes to test
    batch_sizes = [4096, 8192] if detected_cpus < 64 else [8192, 16384]

    print(f"Benchmarking OpenMP thread and batch scaling on {count:,} seeds...")
    print(f"{'Threads':<10} | {'Batch Size':<12} | {'Time (s)':<10} | {'Seeds/Second':<15}")
    print("-" * 55)

    seeds = [seed_from_index(i, 20261013) for i in range(count)]
    results = []

    import statistics
    grid = [(t, size) for t in thread_list for size in batch_sizes]
    measurements = {pair: [] for pair in grid}
    benchmark_start = time.perf_counter()
    for trial in range(3):
        for threads, batch_size in (grid if trial % 2 == 0 else list(reversed(grid))):
            if time.perf_counter() - benchmark_start > 900:
                raise RuntimeError('Tuning budget exhausted; no recommendation adopted')
            with prototype.sweep(seeds[:min(64, count)], threads, retention='survivors', max_misses=2):
                pass
            native_sec = 0.0
            for offset in range(0, count, batch_size):
                with prototype.sweep(seeds[offset:offset + batch_size], threads, retention='survivors', max_misses=2) as batch:
                    native_sec += batch.native_seconds
            measurements[threads, batch_size].append(count / max(0.001, native_sec))
    for (threads, batch_size), rates in measurements.items():
        rate = statistics.median(rates)
        results.append({'threads': threads, 'batch_size': batch_size,
                        'seeds_per_sec': rate, 'trial_rates': rates})
        print(f'{threads:<10} | {batch_size:<12} | {count / rate:<10.3f} | {rate:<15,.1f}')

    # Sort results
    results.sort(key=lambda r: r["seeds_per_sec"], reverse=True)
    winner = results[0]

    print("\n" + "=" * 55)
    print(f"[*] Best measured native-kernel settings in this bounded grid:")
    print(f"    Threads    : {winner['threads']} (out of {total_cpus} supported threads; {detected_cpus} detected cores)")
    print(f"    Batch Size : {winner['batch_size']}")
    print(f"    Kernel rate: {winner['seeds_per_sec']:,.1f} seeds/second")
    print("=" * 55)
    print(f"\nRecommended production command for this machine:")
    print(f"  python -m seed_search --config config/realm.yaml scan \\")
    print(f"    --executor native \\")
    print(f"    --native-threads {winner['threads']} \\")
    print(f"    --native-batch-size {winner['batch_size']} \\")
    print(f"    --native-build {native_dir} \\")
    print(f"    --prediction-scale --retention survivors \\")
    print(f"    --start-index <START_INDEX> --count <COUNT> --output runs/my-sweep\n")
    print("Confirm semantic parity and durable held-out throughput before adopting these kernel-only settings.")
    return winner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-dir", type=Path, default=Path("runs/tune-native"),
                        help="Directory to build or load native extension")
    parser.add_argument("--openmp-prefix", type=Path,
                        help="Path to OpenMP runtime prefix (auto-detected if omitted)")
    parser.add_argument("--count", type=int, default=30000,
                        help="Sample seed volume per benchmark trial")
    args = parser.parse_args()

    openmp_prefix = args.openmp_prefix or find_default_openmp_prefix()
    tune_machine(args.native_dir, openmp_prefix, args.count)


if __name__ == "__main__":
    main()
