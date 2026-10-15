# Codex final review evidence

Commit and production source/binary/runtime hashes were checked after experiments. Seven optimized arm/chunk identities match their isolated sources and fresh PGO metadata. Production is unchanged; untracked changes are review artifacts only.

## Critical and disputed findings

```sh
.venv/bin/python reviews/split-audit-2026-10-15/codex/reproduce.py
.venv/bin/python reviews/split-audit-2026-10-15/codex/reproduce_cache.py
```

These reuse the exact-baseline private malloc/optional-instrumented modules. Recreate them using `reviews/codex-audit-2026-10-15/probes/build_probe.py` and `build_optional_probe.py` if `/tmp/minecraft-audit-20261015` has been removed. Failures are subprocess-isolated, core dumps disabled. [reproductions.json](reproductions.json) records:

- Optional hut `(56,-800)`, label 123: native `(-752,-816),434`, Python `(-784,-816),422`; recount restores parity.
- Cap 1,400,000 succeeds at requested-live peak 1,872,336; cleanup returns zero.
- Two same-worker fixtures, allocation failures 34/35/36: all exit -11/SIGSEGV.
- One fixture, second event allocation fails: error -3, zero live bytes after cleanup. This refutes the separate asymmetric-leak claim.
- Dropped unmanaged Batch leaves 48,956 requested bytes; explicit free returns zero. Managed production use remains normal.
- Candidate cache: database 55/PREDICTED updated to 99/VERIFIED; manager retains 55/PREDICTED.
- Status waits 1.921s behind a two-second child termination wait.
- Lease callback deliberately recovers/reassigns between check and commit. Final completed count is 10; conflicting retry is rejected. The production ownership path rejects a second scanner using its OS lock. Production reachability of Gemini's claimed multiwriter race is unverified.
- DB-free prepare works off-thread. Injected SQL correctly raises thread-confinement error; that does not demonstrate a present preparer defect.
- Four of five Gemini patches fail `git apply --check`; the stale-cache patch applies. None is adopted.

Inflight analysis reuses the prior targeted reproduction against unchanged source, avoiding an excluded end-to-end persistence rerun. The loop still refills after popping the outstanding owned batch.

## Performance and coverage

All commands/trials are in [Sol's command log](../sol/commands.md). Codex's additional alternating pairs are in `sol/codex-performance-recheck.json` and `sol/codex-gate-recheck.json`. Within-trial fingerprints match. Long confirmations have five trials and at least five seconds of native work per arm. No throughput comparison uses diagnostic instrumentation.

Positive coverage: 134 viable-Mansion seeds among 2,000 component inputs; nonempty optional inventories on 262 natural inputs, including 441 positive igloo basements. Synthetic survivors match across arms in full/compact retention. No compatible complete retained natural survivor was found in the bounded attribution cohort; no BDS generation claim is made. Focused tests: **30 passed, 1 deselected**.

The original diagnostic executable was overwritten when adding S4 hooks; its earlier identity and raw results remain. This limitation does not affect seven retained uninstrumented PGO comparison builds. No usable PMU values were exported; cache/branch/bandwidth saturation claims are withheld.

## Disposition

All 21 Gemini entries have a disposition or evidence gap in [dispositions.json](dispositions.json): three accepted P1s, three accepted P2 operational findings, one validation gap, two P3s, and the prior optimization. Others are duplicate, rejected, or unresolved. Gemini's own summary severity subtotals disagree with its entries; the reviewed ledger governs this handoff.

Two new performance proposals remain: remove redundant Mansion setup and add the necessary raw witness gate. Prior delayed seeding is reconfirmed. Readiness is **FAIL in the audited scope** until P1s are addressed. Audit completion does not implement changes.
