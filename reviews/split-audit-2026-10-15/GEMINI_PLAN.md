# Gemini assignment: independent audit with subagents

Use this document as the execution prompt for Gemini. Read `CODEX_REVIEW.md` in this directory for the common evidence and final-review requirements.

## Objective and scope

Coordinate independent, evidence-based reviews of the remaining correctness, memory, concurrency, native/Python boundary, storage, and control-plane gaps in `dynamic-envelope-1664-v1`. Use focused subagents, verify their findings, and deliver one consolidated package to Codex for final review.

This is an audit assignment. Use isolated probes, temporary databases, and experimental copies when necessary. Exclude production fixes, replacement production binaries, live sweeps, combined generation-to-persistence runs, BDS verification, and deployment. Sol owns performance measurements and optimization builds.

The reference commit when this assignment was prepared is:

```text
54b7d631b8bdb481894980a31be16aaa02901b18
```

Verify the actual baseline with Sol before work begins. Both teams must use the same commit and resolved configuration. Record any deviation rather than silently carrying forward historical conclusions.

## Coordinator responsibilities

1. Freeze commit, policy, backend/version pins, and relevant build identities in `gemini/manifest.json`.
2. Launch the four discovery agents below. Give each agent the specification and its assignment, but withhold the prior audit's findings and Sol's new conclusions until its first independent report is saved.
3. Give agents separate output directories. They may read overlapping source, but must not edit shared production files or each other's probes.
4. Coordinate heavy tests, builds, and fault injection. During Sol's exclusive timing windows, permit light source review only. Agent count does not justify CPU oversubscription or contaminated measurements.
5. Collect initial reports, then reveal the prior audit and classify findings as new, independently reproduced, superseded, or unverified.
6. Launch the adversarial verification agent in the second phase. Independently check material findings before consolidation.
7. Send one consistent package to Codex. Agent agreement is not a substitute for reproduction.

Prior evidence, to reveal after first-pass reports: `reviews/codex-audit-2026-10-15/AUDIT.md`, `evidence.json`, and `probes/`. Do not rerun every old test. Select the checks necessary to establish whether a finding remains relevant to the frozen baseline.

## Fixed specification for every agent

- Bedrock 26.52 / BDS 1.26.52.3 / Cubiomes `MC_26_50`.
- Overworld square: `[C_X-832,C_X+832)` by `[C_Z-832,C_Z+832)`.
- Nether square: `[C_X/8-416,C_X/8+416)` by `[C_Z/8-416,C_Z/8+416)`. Rational scaling and `center // 8` agree at production centers snapped to multiples of eight; do not assume agreement for arbitrary diagnostic inputs.
- Integer entry events: `X_i-831` and `8*X_N,j-3327`. Preserve the correct exit asymmetry as well.
- All 160 raw lattice event contributions per axis must be represented before legitimate clipping/deduplication. Every membership transition must survive.
- Second qualifying Ocean Monument awards +30 points.
- Floors, strict goals, flexible deficits, 16/8 snapping, full64 viability, and retained evidence completeness are fixed.

Do not relax bounds, remove lattice transitions, or change scoring to simplify a proof. Do not recommend new spatial indexes without measured evidence. Report ambiguity between specification and implementation explicitly instead of silently choosing a new contract.

## Phase 1 — Four independent discovery agents

### G-GEO — Geometry, scoring, and independent selection

**Primary files:** `native/blueprint_dynamic.inc`, scoring in `native/blueprint_batch.inc`, `src/seed_search/realm/dynamic.py`, `blueprint.py`, and the relevant configuration/blueprint specification.

Audit:

- Entry/exit boundaries, negative division, center limits, rational scaling, and 16/8 snapping.
- Membership invariance for mandatory structures and biome witnesses throughout cells.
- Which optional or distance-dependent quantities are actually invariant, and what optimality the representative-selection policy guarantees.
- Conservative raw preflight culling and union bounds: a rejected seed must not hide a viable allowed center.
- Scoring milestones, optional bonuses, deficit tiers, and final ranking order.
- Native/Python centroid arithmetic, radial accumulation, quantization, and tie-breaking.

Use an independent Python selection path. Replay of a C-selected center does not prove independent selection parity. Test boundary coordinates, optional starts crossing during snapping, fallback-to-eight cells, and score/rank ties. Report floating-point discrepancies only with concrete reproducible values and observable consequences.

**Output:** proofs/check coverage for the invariants examined, and numerical counterexamples for defects. Distinguish policy-defined representative selection from an unproven global optimum over all snapped coordinates.

### G-MEM — Allocation, ownership, concurrency, and recovery

**Primary files:** `native/blueprint_batch.inc`, `native/blueprint_dynamic.inc`, relevant context creation/destruction in `native/bridge.c`, and pipeline ownership in `native_batch.py`.

Audit:

- All owned heap allocations versus the declared reservation contract.
- Peak live bytes, conservative cumulative reservation, fixed worker/context costs, and allocation-size arithmetic.
- Pointer/capacity consistency after failed growth and subsequent worker reuse.
- Partial initialization, cleanup, native output compaction, and double-free/use-after-free risks.
- Worker-local generator/cache state, shared policy access, atomic counters, output index ownership, and fixture isolation.
- Repeated batch execution and retained memory after all owned results close.
- Actual outstanding batches versus reported limits.

Use deterministic allocation-failure injection, including failures followed by another seed on the same worker. Run crash probes in subprocesses with core dumps disabled. Use sanitizers where supported; document tool/runtime limitations and do not infer race freedom from a passing functional test.

**Output:** allocation/ownership map, fault matrix, and deterministic failure reproductions. Refer performance hypotheses to Sol rather than proposing padding or new allocators without measurements.

### G-FFI — CFFI boundary and survivor evidence

**Primary files:** `src/seed_search/realm/native_batch.py`, `runner.py`, `native_records.py`, `native_encoding.py`, relevant native ABI headers, and their callers.

Audit:

- Native allocation lifetime across record preparation, receipt hashing, exceptions, and close/cancellation paths.
- Call-local policy isolation under concurrent calls through a shared Prototype.
- Full64 seed identity, offsets, signed/unsigned conversion, result count, and error propagation.
- GIL-release boundaries and which operations actually copy data.
- Complete versus capped inventory semantics and full versus survivor retention.
- Whether reconstruction/parity checks independently verify decisions or only replay supplied decisions.
- Qualification, deficits, optional inventories, score, and biome witness consistency in retained records.

Use valid survivor fixtures and compatible archived natural inputs where available. Clearly label fixture-only conclusions. Exercise exceptional paths and repeated calls without launching a complete scan/persistence pipeline.

**Output:** boundary/lifetime contract table, missing coverage, and precise reproductions. Coordinate any ownership overlap with G-MEM rather than duplicating large test matrices.

### G-STORE — SQLite and web control plane

**Primary files:** `src/seed_search/realm/store.py`, `src/seed_search/web/server.py`, and relevant leaderboard/state callers.

Audit:

- Atomicity of records, receipts, counts, and completed range state.
- Rollback, duplicate completion, stale leases, interrupted work, and retry identity.
- Connection ownership and any preparation path that unexpectedly accesses SQLite from another thread.
- Lock ordering, process-generation checks, pause/stop/resume races, and concurrent request handling.
- Candidate cache invalidation after updates to scores or verification evidence.
- Bounded logging, short-lived reader transactions, WAL/checkpoint assumptions, and long-running state growth.

Use temporary databases, deterministic state/interleaving tests, and injected transaction failures. Test actual claimed invariants rather than assuming every public method supports arbitrary concurrent writers. Do not run combined generation-to-SQLite validation or weaken WAL/FULL durability.

**Output:** transaction/control-state coverage table and reproducible failures, including expected versus observed database/UI state.

## Phase 2 — Adversarial verification agent

Launch a separate agent, `G-VERIFY`, after the four initial reports exist. Give it the frozen baseline, raw reproductions, prior findings, and Sol's available proposals.

Its task is to challenge the strongest claims:

- Reproduce every proposed P0/P1 before the consolidated report calls it verified.
- Check whether fixtures are valid, whether a numerical trigger reaches the claimed code path, and whether diagnostic modifications introduce the failure.
- Check whether an expected result follows from the fixed specification.
- Distinguish current defects from prior findings already fixed or deliberately unsupported inputs.
- Check that performance proposals preserve the invariants, full64 identity, selection, and retained evidence.
- Reject proposed speed-ups whose assumptions contradict Sol's measurements; leave timing confirmation to Sol.

For each finding, return `REPRODUCED`, `REFUTED`, or `UNRESOLVED` with reasons and evidence. A failed reproduction is unresolved unless the reason actually disproves the claim. If verification capacity is limited, prioritize severity and keep unchecked findings explicitly provisional.

## Evidence requirements and stopping rules

Every defect must include:

1. Stable ID, severity, baseline commit, exact file, and verbatim anchor.
2. Concrete coordinates, seed/input list, bitmask, allocation failure number, or deterministic interleaving.
3. Reproduction command, toolchain/build identity, and probe source.
4. Expected behavior grounded in the contract and actual observed behavior.
5. Minimal proposed fix and its required verification.
6. Natural versus synthetic provenance and verifier disposition.

For areas with no finding, say `None verified` and list what was checked. Do not claim exhaustive safety from source review or a finite seed corpus. Stop speculative optimization discussions without evidence and avoid duplicating already completed broad suites.

## Required handoff to Codex

Write:

```text
gemini/
  REPORT.md
  manifest.json
  findings.json
  commands.md
  agents/
    geometry.md
    memory.md
    ffi.md
    storage-web.md
    verification.md
  probes/
  proposals/              # minimal unapplied fixes, where justified
```

Use identifiers `G-GEO-01`, `G-MEM-01`, `G-FFI-01`, and `G-STORE-01`. Consolidate duplicate root causes while preserving cross-references to agents' evidence. Separate verified defects, unresolved questions, prior findings, and performance hypotheses.

The coordinator must check that reports agree about commit/configuration, remove unsupported severity claims, and highlight disagreements with Sol. Gemini's report is provisional: Codex performs the final review of both teams and issues the final combined verdict.
