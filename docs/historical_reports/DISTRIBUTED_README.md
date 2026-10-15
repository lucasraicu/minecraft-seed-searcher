# Distributed seed sweeps

Each machine screens its own finite index range and writes an independent Realm checkpoint. Use the same resolved policy, seed sequence and `search.run_key`, and allocate disjoint half-open intervals `[start_index, start_index + count)`. Different run keys do **not** guarantee disjoint seeds: `seed_from_index(i, k)` mixes `i + k` modulo 2^64. Keep each interval within the full 64-bit boundary and record the assigned ranges before launching.

## Setup and tuning

Use Python **3.13**, the pinned dependencies in `requirements.lock`, and a compiler supporting C11. The existing dependency lock and benchmark evidence primarily target Intel macOS; validate dependency installation, native parity and performance on each new platform before a production run. A high-core server is currently subject to the production executor's **34-thread maximum** and **16,384-input batch maximum**; 192-thread execution has not been implemented or certified.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python native/build.py
.venv/bin/python native/blueprint_build.py
```

Build an isolated OpenMP extension on macOS after installing `libomp`:

```sh
.venv/bin/python scripts/build_blueprint_batch.py --output runs/node-native --openmp-prefix "$(brew --prefix libomp)"
.venv/bin/python scripts/tune_machine.py --native-dir runs/node-native --count 30000
```

On Linux, provide an OpenMP prefix whose `include/omp.h` and runtime library are actually present; `/usr` is not a universal location for distribution-packaged LLVM headers. Portable serial builds require no OpenMP prefix. The tuner compares a bounded grid using repeated native-kernel timings; it does not certify global optimality or durable end-to-end speed. Run correctness parity and held-out durable benchmarks before adopting different settings. Host-specific compiler flags, LTO, PGO and chunk-size changes require their own evidence; they do not automatically provide SIMD acceleration or eliminate contention.

## Launch disjoint ranges

Use separate directories and supply the explicitly built native extension. The CLI writes a compatibility report and requires the prediction-scale opt-in for a run above the pilot limit. All retained outputs remain predictor evidence until their actual-generation checks are complete.

```sh
# First node: [0, 1,000,000)
.venv/bin/python -m seed_search --config config/realm.yaml scan --executor native \
  --native-build runs/node-native --native-threads 16 --native-batch-size 4096 \
  --retention survivors --max-misses 2 --prediction-scale \
  --start-index 0 --count 1000000 --output runs/node-one

# Second node: [1,000,000, 2,000,000), with matching policy/run key
.venv/bin/python -m seed_search --config config/realm.yaml scan --executor native \
  --native-build runs/node-native --native-threads 16 --native-batch-size 4096 \
  --retention survivors --max-misses 2 --prediction-scale \
  --start-index 1000000 --count 1000000 --output runs/node-two
```

Choose a measured thread count supported by that node. Compact output size depends on survivor rate, range receipts, evidence and WAL growth; a multi-billion-input database is not guaranteed to fit in a few megabytes. Disk preflight and live physical limits still apply. Native screening, downstream terrain/marine prediction and actual BDS evidence have different costs; no throughput is promised for an unmeasured machine.

## Transfer consistent snapshots

Use SQLite's online backup while a run is active; copying only `realm.sqlite` can omit committed WAL data. Retain the original complete run directory and evidence files. Copying a raw database is acceptable only after all writers have stopped, a checkpoint has succeeded, and connections have closed.

```sh
sqlite3 runs/node-one/realm.sqlite ".backup runs/node-one/export.sqlite"
scp user@node:~/minecraft-seed-searcher/runs/node-one/export.sqlite ./node-one.sqlite
```

The backup is a database snapshot; external evidence files must be copied separately with their provenance if needed for later verification.

## Aggregate leaderboards

```sh
.venv/bin/python scripts/merge_runs.py --inputs ./node-one.sqlite ./node-two.sqlite --output runs/master-unified
```

The merger creates an **explicit read-only aggregate**, not a resumable Realm scan. It validates policy, seed-domain and computational source identity, retains source provenance, streams candidate/variant/observation records and computes coverage from completed interval unions. Conflicting evidence fails by default; an aggregate must never overwrite an original source. Different native binaries can be compared through recorded source/policy identity, but this does not substitute for cross-platform parity validation.

Do not pass the aggregate to `resume`, `terrain`, `verify-realm`, or `--run` on the website: those commands require an original Realm checkpoint and the website does not implement arbitrary aggregate selection. The merger prints the canonical top five; SQL readers can query `candidate_leaderboard_view` ordered by `ranking_tier, unmet_requirements, smart_score DESC, id`.

## Verification and website

Use the original owning checkpoint when verifying a selected candidate. Inspect command help for the specific evidence stage:

```sh
.venv/bin/python -m seed_search verify-realm --help
.venv/bin/python -m seed_search verify-terrain --help
.venv/bin/python -m seed_search.web.server 3000
```

The website serves at `http://127.0.0.1:3000`; port 5173 is the optional Vite development server. Imported Nether structure evidence uses `verify-realm --run <original-run> --candidate <candidate-id> --evidence <actual-evidence.json>`. A bounded BDS host can provide supported actual block/surface observations. Automatic portal-room, spawner, chest-loot and first-player-spawn certification is not implied; absent evidence remains pending. Preserve exact seed/build/settings/bounds provenance and the original run when selecting finalists across machines.
