# Completed Sol experiments — reproduction commands

Run from the repository root with `.venv/bin/python`. CPU-heavy operations ran sequentially after the user's release. No production edits or end-to-end validation occurred. Preparation refuses to overwrite `/tmp/minecraft-sol-audit-20261015`; preserve existing evidence or choose another `WORK` path consistently when reproducing.

## Matched PGO builds

```sh
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py prepare
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py build --allow-heavy --arm control --chunk 16 --phase training
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py train --allow-heavy --arm control --chunk 16
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py merge --allow-heavy --arm control --chunk 16
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py build --allow-heavy --arm control --chunk 16 --phase optimized
```

The build/train/merge/optimized sequence ran for `control`, `lazy`, `no-surface-init`, `lazy-no-surface-init`, and `dark-gate` at chunk 16, and `lazy-no-surface-init` at chunks 64 and 128. Separate processes flush PGO data before merging. Training is 10,000 permutation inputs at key 2026101402, indices 0–9999, four threads, plus one positive fixture. Sources/profiles/flags/hashes are retained in `builds/` and checked again at final assembly.

## Attribution and parity

```sh
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/prepare_diagnostics.py
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py build-diag --allow-heavy
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/profile.py --allow-heavy --count 256 --threads 1
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/profile.py --allow-heavy --count 100000 --threads 34
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/parity.py --allow-heavy --arms control lazy no-surface-init lazy-no-surface-init
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/parity.py --allow-heavy --arms lazy-no-surface-init dark-gate --component-count 256
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/optional_parity.py
```

Optional parity uses 134 archived positive-Mansion seeds plus 128 new inputs. It checks nonempty optional inventories and igloo basements after Mansion in the same context, separately from NBFixture. It does not claim complete natural survivor eligibility.

Sampling used `probes/collect_sampling.py` and `probes/sample_workload.py`: production binary, one thread, indices 70M–70M+16,384. `/usr/bin/sample` ran four seconds at 5ms intervals; `xctrace record --template 'CPU Counters'` attached for three seconds. The exported TOC was sanitized by removing the target environment; only `counters-toc-sanitized.xml` is retained in the review. No usable PMU event values were exported. Do not print the unsanitized trace environment.

## Screens and confirmation

```sh
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py bench --allow-heavy --arms control lazy no-surface-init lazy-no-surface-init --count 100000 --start 51000000 --trials 3 --output screen-main.json
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py bench --allow-heavy --arms control lazy no-surface-init lazy-no-surface-init --count 1200000 --start 52000000 --trials 5 --output confirm-main.json
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py bench --allow-heavy --arms lazy-no-surface-init dark-gate --count 200000 --start 75000000 --trials 3 --output screen-dark-gate.json
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py bench --allow-heavy --arms lazy-no-surface-init dark-gate --count 1500000 --start 100000000 --trials 5 --output confirm-dark-gate.json
```

Defaults: 34 threads/chunk 16/batch 16,384, survivors retention, max_misses 2, key 2026101401. Odd trials reverse arm order. Each long trial exceeds five seconds per arm. Seed preparation, record walking, and hashing are outside native timing. The gate includes both initialization changes and is compared against their combined arm.

## Scheduling and Codex replication

```sh
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/scheduling.py --allow-heavy
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/scheduling.py --allow-heavy --confirm
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py bench --allow-heavy --arms control lazy no-surface-init lazy-no-surface-init --count 300000 --start 90000000 --trials 2 --output codex-performance-recheck.json
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py bench --allow-heavy --arms lazy-no-surface-init dark-gate --count 300000 --start 120000000 --trials 2 --output codex-gate-recheck.json
```

Scheduling reuses a fixed cohort across configurations/trials: 200k screen and 1.5M confirmation. Per-row CPU/wall, latency arrays, hashes, and variability are in `scheduling.json`. Short Codex pairs replicate direction/parity; they do not replace long trials.

## Survivor components and remaining attribution

These extend/rebuild the diagnostic copy. The earlier diagnostic identity/raw measurements are retained, but that exact original executable was overwritten for S4.

```sh
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/prepare_survivor.py
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/experiment.py build-diag --allow-heavy
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/survivor.py --allow-heavy
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/remaining_profile.py
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/profile.py --allow-heavy --count 100000 --threads 34 --build /tmp/minecraft-sol-audit-20261015/diagnostic-optimized/native-build --output profile-optimized.json
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/profile_gate.py
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/profile.py --allow-heavy --count 100000 --threads 34 --build /tmp/minecraft-sol-audit-20261015/diagnostic-gate/native-build --output profile-gate.json
.venv/bin/python -m pytest tests/test_dynamic_baseline.py tests/test_dynamic_integration.py -q -k 'not web_bds_job'
.venv/bin/python reviews/split-audit-2026-10-15/sol/probes/allocation_boundary.py
```

Tests: **30 passed, 1 deselected in 10.21s**. Diagnostic variants are non-PGO attribution builds, not throughput comparisons. The non-gated variant retains an empty initializer timing hook; the gate removes it and uses slot 12 for raw witnesses. Allocation probes reuse the original private fault-injection module; recreate it with `reviews/codex-audit-2026-10-15/probes/build_probe.py` if `/tmp` was removed.

`measurements.json` contains medians, paired ratios, variability, raw-file references, and final identity checks. `probes/summarize.py` is the one-time report assembly/calculation script. Raw measurements are authoritative.
