# Independent implementation audit prompt

Copy the text below into Claude or Gemini with access to the repository. Use a
separate fresh conversation for each reviewer and do not supply the other review
until both are finished. Gemini should use High reasoning. Record the model and
settings actually available; do not claim a setting was used without evidence.

---

Audit `https://github.com/lucasraicu/minecraft-seed-searcher` independently. Review
the checked-out implementation, not merely its plans or previous reviewers'
conclusions. Your task is a read-only audit; do not implement fixes, commit, push,
move files, delete evidence, modify live databases, or restart services.

First record the exact commit, dirty state, platform, Python/SQLite versions and
available native build/toolchain. Read `AGENTS.md`, `README.md`,
`CODEX_HANDOFF.md`, `docs/PROJECT_STATUS.md` and `docs/REPOSITORY_MAP.md`.
Treat handoff dates, process IDs and local paths as historical operational context,
not current-state guarantees or authorization. Follow applicable repository rules.
Use the source and tests to resolve conflicts with design documents. Report stale
specifications separately from actual runtime defects.

The project combines a Bedrock seed predictor/search engine in native C/CFFI/OpenMP,
Python orchestration and persistence, and a React/TypeScript UI. There is a personal
2048 search and a four-pillar public catalog, including Realm/Server products.
Identify which calculations and policies are shared and which remain separate.

## Audit scope

1. **Architecture and implementation completeness.** Trace input seed generation
   through native screening, refinement, scoring, candidate retention, checkpointing,
   public selection, observation extraction, summaries, membership publication,
   queries and displayed UI results. Identify implemented, gated, proposed and
   externally dependent components. Check fresh-checkout build/install instructions,
   package data, script root discovery, imports, licenses and required fixtures.

2. **Mathematical and numerical correctness.** Independently derive the active
   hard floors, score components, maxima and ordering from current configuration
   and code. Compare native and Python implementations; do not assume a historical
   score total in a blueprint is authoritative. Check signed seeds versus uint64
   bits, full-64 and strided sequence domains, overflow, integer square roots,
   distance precision, tie order, floor division for negative coordinates, 8:1
   Nether projection, half-open squares, inclusive circles and center-grid bounds.
   Distinguish exhaustive 16-block refinement from local 8-block refinement and
   a globally exhaustive optimum. Verify same-center qualification and witnesses.

3. **Prediction accuracy and evidence.** Trace Bedrock/version pins, source/build
   fingerprints and stale-build rejection. Review biome sampling coordinates and
   heights, structure starts versus generated blocks, spawn estimation, variant
   controls for igloo basements and treasure bastions, and partial stronghold
   coverage. Seek independent positive AND negative controls and counterexamples.
   Check that incomplete, unknown, unavailable and sampled-out remain distinguishable
   from proven absence. A predictor match does not certify terrain, landing safety,
   loot, habitability or actual game generation. Report support and limits per feature.

4. **Admission, ranking and reserves.** Verify public selection occurs independently
   of personal success and before personal rejection can lose public candidates.
   Check the default 2048 Realm blueprint binding and differences from configurable
   personal runs. Verify distinct-world deduplication, deterministic full ordering,
   per-objective 2K retention (primary plus reserve), pruning/cutoff correctness,
   promotion after invalidation, historical-capacity compatibility and checkpoint
   resume. Separate retained membership slots from unique worlds. Compare against
   a simple full-sort oracle, including ties and full-capacity boundary cases.

5. **Storage, queries and recovery.** Check SQLite transactions/WAL/runtime support,
   immutable CAS bindings and hashes, manifest publication, durable checkpoint
   encoding, leases/fencing/idempotency, crash/retry/resume, source-bound policies,
   and cache invalidation. Examine guarded read views and conservative typed masks:
   required rows must match the same anchor, unknowns must survive, biome ANY and
   preferences must not become unsafe exclusion predicates. Check pagination,
   primary/reserve isolation, historical snapshots, exact scores, corruption
   detection on warm paths, memory bounds, timeouts and backpressure. Distinguish
   serialized cache budgets from actual RSS.

6. **Performance and scaling.** Read the measurement scripts and raw receipts,
   not only headline figures. Separate raw input screening, qualifying candidates,
   full public records, newly retained unique useful worlds and query latency.
   Attribute native computation, Python loops, JSON/copy/validation, hashing,
   checkpoints, disk I/O, summarization and publication without double-counting
   nested timings. Check worker counts, thread counts, CPU/RSS, cache state,
   startup costs, thermal evidence, repeated cohorts, time-budget partial work and
   fair before/after conditions. Identify demonstrated bottlenecks and experiments
   needed; do not invent fleet throughput, GPU speedups or cold-cache SLAs.

7. **GPU/database readiness.** Review `docs/gpu/GPU_CONTRACT_V1.md` and its JSON
   contract for exact CPU parity, wire widths, endianness, source/config identity,
   wide arithmetic, batch bounds, independently selected populations, overflow,
   failure handling, durable progress and CPU fallback. It defines a contract;
   no GPU kernel or device performance is established. Review the database
   comparison for equivalent semantics, complete API costs, recovery/concurrency
   coverage and scale limits. Distinguish real worlds from replicated benchmark
   rows. Determine whether a different engine is justified by measured needs.

8. **API/UI and security.** Trace request validation, malformed inputs, path/symlink
   handling, seed/coordinate bounds, export/evidence trust boundaries, local admin
   versus public routes, snapshot negotiation, stale-response races and error/status
   labels. Verify UI arithmetic and ordering match the backend. Assess current
   local deployment and separately identify work required before public hosting.

## Evidence and execution rules

Start with focused source inspection and existing tests/fixtures. Run only bounded
offline checks in a disposable checkout or temporary directories. Document exact
commands, exit codes, pass/fail/skip counts, runtime and actual import/build paths.
Do not change assertions or weaken acceptance to obtain a pass. Keep existing
logs, failed attempts and contrary evidence. Stop an individual command after
10 minutes; report the limit. Do not run a new seed-search campaign, BDS/game
world validation, live-service mutation, dependency upgrade or long benchmark
without separate user authorization. Do not execute completion notifications as
part of this read-only review. Request permission before installing dependencies
or using resources beyond these offline limits.

Some historical reports reference private catalogs, binaries or replay data outside
Git. Identify exactly what is missing; classify affected claims as historical
receipts or not independently reproducible from this checkout. Do not present
private-runtime results as freshly reproduced or assume missing evidence proves
the algorithm false. Check self-contained source/unit/fixture controls independently.

Historical benchmark context to verify, not assume: about 67,000 personal INPUTS/sec
was measured with a 34-thread search alongside ONE sequential catalog extraction
worker and two mostly-cache-hit HTTP clients. The loaded public record took about
45 seconds; the isolated updated record about 25 seconds. These replayed known
inputs/worlds, not a unique-world discovery campaign or a parallel extraction
scaling test. New readiness changes were tested privately; preserved live services
did not automatically adopt them. Consult the actual reports for qualifications.

Useful entry points:

- `src/seed_search/realm/`, `native/`, `vendor/cubiomes-bedrock/`
- `src/seed_search/catalog/`, `src/seed_search/web/server.py`, `web-ui/src/`
- `tests/README.md`, `scripts/README.md`, `fixtures/bedrock-26.52/`
- `docs/catalog/ACCURACY.md`, `docs/catalog/DATABASE_COMPARISON.md`
- `reviews/pre-gpu-implementation-2026-10-22/REPORT.md` and `COMPLETION_AUDIT.md`
- `reviews/storage-query-profile-2026-10-22/REPORT.md`
- `reviews/variant-controls-and-organization-2026-10-22/RELEASE_REPORT.md`

## Required deliverable

Lead with concrete findings ordered by severity: critical/high/medium/low. For each,
give file and line, trigger and affected inputs, expected versus actual behavior,
mathematical derivation or executable minimal reproduction, impact, confidence,
and smallest suggested correction. Label confirmed bugs, plausible risks, stale
documentation and unverified claims separately. Do not pad the report with generic
advice. If no defect is found in a component, state what was actually checked.

Then provide a compact component matrix covering correctness, evidence/accuracy,
performance and coverage gaps; commands/results; an explanation of the measured
throughput units and bottlenecks; and an ordered list of prerequisites before GPU
implementation, database migration and public launch. Give a supported readiness
assessment for each transition, including unresolved risks and tests that could
change your assessment. No fixes or publication actions during this audit.
