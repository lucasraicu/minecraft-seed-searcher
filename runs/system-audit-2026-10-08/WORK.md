# Audit work record — 8 October 2026

## Scope and decisions

User requested a system-wide code audit, primary online-source research, a specific implementation plan with estimated impact/time, and a documented seed-picking workflow before the sweep. The second user reply approved **2304/640** as the future target. Two Gemini attachments were preserved locally. Follow-up questions clarified that lower32/upper32 mode belongs in the plan, that required structures remain Stronghold/Fortress, and that Village must not be treated as a universal Stronghold prerequisite.

No production Python module, native source/binary, vendor file or configuration was changed. No full64 sweep or generated-game verifier was run. The only executable addition is `scripts/audit_system.py`, an isolated bounded diagnostic/prototype driver. The new documents are the deliverable, and old entry-point documents now link to them. This intentionally makes the old hashed readiness artifacts stale.

## Work completed

1. Inventoried application/native/configuration/test/report/review/checkpoint/readiness modules and existing evidence. Initial revision `840d28cc6f210fa118a479512dac44254234eb14`; pre-existing untracked `exports/` left intact.
2. Read both user-provided Gemini proposals. Compared them with current code: existing lazy basin bounds, required structure windows, raw MT cache, owned CFFI handles and rejected Stronghold patches.
3. Reran the existing full suite: **112 passed in 77.91 s**. This result was captured in the execution-tool output during the audit; no separate pytest log was created for that invocation. Reran frozen external regression, doctor and `pip check` successfully.
4. Inspected the historical 20-input SQLite checkpoint read-only for aggregate cache behavior. No evictions; 58.22 MiB maximum allocated tile data. No claim about universal working-set size.
5. Traced the pinned density equations and tested exact quart-cell land sharing on ten 4096-point patches, three alternating-order trials each, across five seeds. Exact boolean parity; both negative and positive coordinates, water/mixed/land cases.
6. Ran an isolated complete-seed A/B for 12345 with cProfile. Production reference: 65.512 s; experimental cache: 39.724 s. Identical candidates, scores, near misses, decision counts and filter policy; native computed-cell/cache statistics intentionally differ. Two candidates in this run. No process-pool/export/yield inference.
7. Tested 256 distinct low32 layouts from fixed SplitMix indices 100–355 using the new target geometry. Raw Fortress feasible in every layout; joint raw Fortress/Bastion/Village feasible in every layout. No full64 terrain search in this diagnostic. Existing wrapper/setup cost measured, not a generator-free API.
8. Reproduced a synthetic accepted-64-spacing basin shortcut false rejection and an in-memory review-routing inconsistency. These are diagnostic counterexamples; no fabricated website evidence was imported into a run.
9. Consulted primary source code/documentation for density and structure algorithms, SciPy morphology, NumPy rounding, CFFI buffers, Clang floating-point behavior, author-published base-seed research, Bedrock locate and the MyGen author page. Citations and applicability limits are in the audit report.
10. Wrote the audit, ordered implementation/verification plan, and workflow/structure contract. Marked the previous sweep package historical and verified the stale gate rejects it. Checked new document links, diagnostic syntax/results, production-file scope and absence of the sweep directory.

## Artifacts

| Artifact | Meaning |
|---|---|
| `GEMINI_RECOMMENDATION.txt` | First corrected comprehensive proposal supplied by the user |
| `GEMINI_STRUCTURE_FOLLOWUP.txt` | Later proposal emphasizing structure filtering |
| `audit-summary.json` | Baseline verification, source identity, script identity and no-sweep scope |
| `regression/regression.json` | Fresh 880-structure/159-point replay |
| `doctor.json` | Native/platform/configuration metadata |
| `cache-audit.json` | Read-only aggregation of old 20-input cache counters |
| `land-cell-ab.json` | Three-trial fixed-patch exact-land A/B |
| `profile-12345-reference.json`, `profile-12345-quart.json` | Full per-seed records for the isolated A/B |
| `profile-12345-comparison.json` | Exact compared-field result and measured serial runtime |
| `profile-12345-*.txt`, `profile-12345-*.pstats` | Profile tables and machine-readable profiles |
| `raw-layout-selectivity.json` | 256-layout raw-placement experiment, target 2304/640 |
| `basin-lattice-counterexample.json` | Nondefault spacing 64: full reference passes, early bound rejects |
| `review-ranking-counterexample.json` | Synthetic required-marker review unresolved, old numeric list still ranked |
| `documentation-validation.json` | Local link/syntax/scope checks and stale readiness rejection |

Some `.log`/`.pstats` files are ignored by the repository's existing bulk-output rules but retained in this workspace. JSON/text evidence and the audit driver are available for review.

## Reproduce the bounded diagnostics

Run from the repository root against the **audited 3008/992 source/configuration**. These commands are diagnostics, not production sweep commands. `--checks` deliberately asserts the two baseline counterexamples; after fixing production code, replace these historical reproductions with permanent regression tests rather than expecting this audit script to continue describing the new implementation.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m seed_search regression --output runs/system-audit-2026-10-08/regression
.venv/bin/python -m seed_search doctor --output runs/system-audit-2026-10-08/doctor.json
.venv/bin/python -m pip check
.venv/bin/python scripts/audit_system.py
.venv/bin/python scripts/audit_system.py --profile-seed 12345
.venv/bin/python scripts/audit_system.py --checks
```

Run timing experiments sequentially. The single-seed profile includes instrumentation overhead, uses the old geometry, and excludes pool startup/reporting. Future optimization acceptance must compare equivalent **new-border** workloads and include independent seeds, worker variation, resume and external quality evidence.

## Outstanding implementation

All production steps P0–P5 in [the plan](../../AUDIT_IMPLEMENTATION_PLAN.md) remain pending. Neither copied Gemini code nor the audit prototype is installed in the search path. The 2–4 working day estimate covers core implementation and evidence refresh; an externally validated Stronghold root fix and speculative SIMD work are separate. A new finite sweep ETA and exact commands follow the new pilot, not the old manifest.
